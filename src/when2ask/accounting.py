"""Inference attempts, a persisted session ceiling, and backend circuit breakers."""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class BudgetExceeded(RuntimeError):
    pass


class BackendBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    max_rounds: int = 20
    max_robot_actions: int = 12
    max_slot_requests: int = 12
    max_api_attempts: int = 64

    def __post_init__(self):
        if any(v < 0 for v in vars(self).values()):
            raise ValueError("Budgets must be nonnegative")


class SessionLedger:
    """All authenticated HTTP attempts, including discovery and retries, debit here.

    The file lock prevents concurrent CLI invocations from bypassing the ceiling.
    Never resets itself; a new study needs a deliberately separate session directory.
    """
    def __init__(self, directory: Path, max_attempts=200, max_episodes=12, *, policy="phase2"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "session_budget.json"
        policies = {"phase2": (200, 12), "phase3_dev": (600, 40)}
        if policy not in policies:
            raise ValueError("Unknown bounded study policy")
        self.policy, self.ceilings = policy, policies[policy]
        self.max_attempts = min(max_attempts, self.ceilings[0])
        self.max_episodes = min(max_episodes, self.ceilings[1])

    @contextmanager
    def _state(self):
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            raw = handle.read()
            state = json.loads(raw) if raw else dict(attempts=0, episodes=0, backends={})
            if state.get("policy", self.policy) != self.policy:
                raise ValueError("Cannot reuse a session across study policies")
            state["policy"] = self.policy
            state["max_attempts"] = min(state.get("max_attempts", self.ceilings[0]), self.max_attempts)
            state["max_episodes"] = min(state.get("max_episodes", self.ceilings[1]), self.max_episodes)
            try:
                yield state
            finally:
                handle.seek(0)
                json.dump(state, handle, indent=2)
                handle.write("\n")
                handle.truncate()
                handle.flush()
                fcntl.flock(handle, fcntl.LOCK_UN)

    def reserve(self, backend):
        with self._state() as state:
            circuit = state["backends"].get(backend, {})
            if circuit.get("blocked"):
                raise BackendBlocked(f"{backend}: {circuit['reason']}")
            if state["attempts"] >= state["max_attempts"]:
                raise BudgetExceeded("session_api_attempt_limit")
            state["attempts"] += 1
            return state["attempts"]

    def start_episode(self, episode_id):
        with self._state() as state:
            if state["episodes"] >= state["max_episodes"]:
                raise BudgetExceeded("session_episode_limit")
            state["episodes"] += 1
            state.setdefault("episode_ids", []).append(episode_id)

    def outcome(self, backend, success, permanent_reason=None):
        with self._state() as state:
            circuit = state["backends"].setdefault(backend, dict(consecutive_errors=0, blocked=False))
            circuit["consecutive_errors"] = 0 if success else circuit["consecutive_errors"] + 1
            if permanent_reason or circuit["consecutive_errors"] >= 3:
                circuit.update(blocked=True, reason=permanent_reason or "three_consecutive_api_errors")

    def snapshot(self):
        with self._state() as state:
            return json.loads(json.dumps(state))


class Audit:
    def __init__(self, episode_id, config, session=None, path=None, limit=64):
        self.episode_id, self.config, self.session = episode_id, config, session
        self.path = Path(path) if path else None
        self.limit = min(limit, 200 if episode_id == "api_smoke" else 64)
        self.records = ([json.loads(line) for line in self.path.read_text().splitlines() if line]
                        if self.path and self.path.exists() else [])
        self.round = 0

    def reserve(self, backend):
        if len(self.records) >= self.limit:
            raise BudgetExceeded("episode_api_attempt_limit")
        number = self.session.reserve(backend) if self.session else None
        # Write a reservation BEFORE the network call, so a process interruption
        # remains visible as an unknown-usage attempt rather than a free retry.
        record = dict(episode_id=self.episode_id, round=self.round, backend=backend,
                      session_attempt=number, status="reserved", input_tokens=None,
                      output_tokens=None, latency_ms=None, returned_model=None)
        self.records.append(record)
        self.flush()
        return record

    def flush(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            clean = self.config.sanitize(self.records)
            self.path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in clean))

    def summary(self):
        result = {}
        for backend in ("deepseek", "jev"):
            rows = [r for r in self.records if r["backend"] == backend]
            result[backend] = dict(attempts=len(rows))
            for kind in ("input_tokens", "output_tokens", "latency_ms"):
                values = [r[kind] for r in rows if r.get(kind) is not None]
                result[backend][kind] = sum(values) if values else None
                result[backend][f"unknown_{kind}_attempts"] = sum(r.get(kind) is None for r in rows)
        values = [r["latency_ms"] for r in self.records if r.get("latency_ms") is not None]
        result.update(api_attempts=len(self.records), api_latency_ms=sum(values) if values else None,
                      retries=sum(r.get("attempt", 1) > 1 for r in self.records),
                      schema_errors=sum(r["status"] == "schema_error" for r in self.records),
                      api_errors=sum(r["status"] == "api_error" for r in self.records))
        return result
