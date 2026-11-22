"""Model requests with per-attempt latency, usage and separate user accounting."""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .api import http_transport
from .config import ROOT, read_env


def resolve_models(settings, names, env=None):
    values = {**read_env(ROOT / ".env"), **os.environ} if env is None else env
    profiles = {}
    for name in names:
        definition = settings[name]
        model, url, key = (values.get(definition[field], "") for field in ("model_env", "url_env", "key_env"))
        if not model or not url or not key or any("replace" in v.lower() for v in (model, url, key)):
            raise ValueError("Configure model ID, base URL and credential for " + name)
        if not url.startswith("https://"):
            raise ValueError("Model endpoint must use HTTPS")
        profiles[name] = dict(model=model, url=url.rstrip("/"), key=key,
                              protocol=definition["protocol"], options=definition.get("options", {}),
                              token_limit_field=definition.get("token_limit_field", "max_tokens"))
    return profiles


def public_models(profiles):
    return {name: {k: v for k, v in profile.items() if k != "key"} for name, profile in profiles.items()}


def token_usage(body):
    usage = body.get("usage") or {}
    inputs = usage.get("prompt_tokens", usage.get("input_tokens"))
    outputs = usage.get("completion_tokens", usage.get("output_tokens"))
    details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    cached = usage.get("prompt_cache_hit_tokens", details.get("cached_tokens", 0))
    valid = lambda v: isinstance(v, int) and not isinstance(v, bool) and v >= 0
    if not all(valid(v) for v in (inputs, outputs, cached)) or cached > inputs:
        return None
    return dict(input_tokens=inputs, output_tokens=outputs, cached_input_tokens=cached)


def estimated_cost(usage, prices):
    if usage is None or prices is None:
        return None
    rates = [prices.get(k) for k in ("input_per_million", "cached_input_per_million", "output_per_million")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in rates):
        return None
    return ((usage["input_tokens"] - usage["cached_input_tokens"]) * rates[0]
            + usage["cached_input_tokens"] * rates[1] + usage["output_tokens"] * rates[2]) / 1_000_000


class RequestLimit(RuntimeError):
    def __init__(self, message, actor):
        super().__init__(message)
        self.actor = actor


class ModelOutputError(RequestLimit):
    pass


class Client:
    def __init__(self, profiles, pricing, path=None, limit=180, transport=None, *, user_limit=120, retries=1, timeout_s=60, max_output_tokens=512):
        self.profiles, self.pricing, self.path = profiles, pricing, Path(path) if path else None
        self.limits = {"agent":limit, "user_simulator":user_limit}
        self.transport = transport or http_transport
        self.retries, self.timeout_s, self.max_output_tokens = retries, timeout_s, max_output_tokens
        self.records = []

    def _clean(self, value):
        encoded = json.dumps(value, default=str)
        for profile in self.profiles.values():
            if profile["key"]:
                encoded = encoded.replace(profile["key"], "[REDACTED]")
        return json.loads(encoded)

    def request(self, name, stage, instructions, state, validator, *, actor="agent"):
        profile = self.profiles[name]
        if profile["protocol"] == "noul":
            endpoint = "/v1/systemone"
            payload = dict(model=profile["model"], state=state,
                           questions={"needs_clarification": dict(type="noul", instructions=instructions)})
        else:
            endpoint = "/chat/completions"
            payload = dict(model=profile["model"], messages=[dict(role="system", content=instructions),
                           dict(role="user", content=json.dumps(state))], response_format={"type": "json_object"},
                           **profile["options"])
            token_field = profile.get("token_limit_field", "max_tokens")
            payload.setdefault(token_field,self.max_output_tokens)
        error = None
        for attempt in range(self.retries+1):
            if sum(r["actor"]==actor for r in self.records) >= self.limits[actor]:
                raise RequestLimit("Episode request limit reached for "+actor,actor)
            record = dict(actor=actor, backend=name, stage=stage, attempt=attempt + 1,
                          timestamp=datetime.now(timezone.utc).isoformat(), requested_model=profile["model"],
                          request=self._clean(payload), estimated_usd=None, usage=None, status="started")
            self.records.append(record)
            start = time.perf_counter()
            permanent, output_error = False, False
            try:
                status, raw = self.transport(profile["url"] + endpoint,
                    {"Authorization": "Bearer " + profile["key"], "Content-Type": "application/json"}, payload, self.timeout_s)
                record["api_time_s"] = time.perf_counter() - start
                record["http_status"] = status
                permanent = status in (400, 401, 402, 403, 404, 422)
                output_error = status < 400
                body = json.loads(raw)
                record["response"] = self._clean(body)
                if status >= 400:
                    raise RuntimeError(f"Model endpoint returned HTTP {status}")
                record["returned_model"] = body.get("model")
                if not isinstance(record["returned_model"], str):
                    raise ValueError("Missing returned model identifier")
                record["usage"] = token_usage(body)
                record["estimated_usd"] = estimated_cost(record["usage"], self.pricing.get(name))
                if profile["protocol"] == "noul":
                    answer = body["answers"]["needs_clarification"]
                    value = answer["noul"]
                    if answer["type"] != "noul" or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError("Invalid Noul probability")
                else:
                    value = json.loads(body["choices"][0]["message"]["content"])
                result = validator(value)
                record["status"] = "ok"
                return result
            except Exception as exc:
                error = str(self._clean(str(exc)))
                record.update(status="error", error=error, error_kind="model_output" if output_error else "transport")
            finally:
                record.setdefault("api_time_s", time.perf_counter() - start)
                if self.path:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    with self.path.open("a") as stream:
                        stream.write(json.dumps(self._clean(record)) + "\n")
            if permanent:
                break
        raise ModelOutputError(error,actor) if output_error else RuntimeError(error)

    def totals(self, actor="agent"):
        rows = [r for r in self.records if r["actor"] == actor]
        return dict(requests=len(rows), api_time_s=sum(r["api_time_s"] for r in rows),
                    estimated_usd=sum(r["estimated_usd"] for r in rows)
                    if all(r["estimated_usd"] is not None for r in rows) else None,
                    usage_complete=all(r["usage"] is not None for r in rows))
