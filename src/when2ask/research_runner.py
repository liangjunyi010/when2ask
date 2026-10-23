"""Budgeted real-model loop; private task data stays on the execution side."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .accounting import Audit, BackendBlocked, BudgetExceeded, Limits, SessionLedger
from .agents import GateResult, components
from .api import APIError, DeepSeekClient, JevClient, SchemaError
from .config import Config, ROOT
from .environment import Environment
from .evaluator import Evaluator
from .prompts import ACTION_PROMPT, GATE_RULES, QUESTION_PROMPT
from .protocol import Question, disclosed_choices, observe, payload_hash, public_payload
from .recording import Recorder
from .skills import RobotSkills
from .user_simulator import PreferenceResolver


METHODS = ("llm_noask", "llm_gate", "jev_gate")


def run_sample(sample, method, output_dir=None, *, live=False, config=None,
               limits=None, session=None, test_components=None, record=False, gui=False, quiet=False):
    if method not in METHODS:
        raise ValueError("Unknown comparison method")
    if not live and test_components is None:
        raise ValueError("Model episodes require explicit --live; offline tests must inject labeled test components")
    if live and test_components is not None:
        raise ValueError("A live result may not use test doubles")
    config, limits = config or Config.load(), limits or Limits()
    if live and (limits.max_rounds > 20 or limits.max_api_attempts > 64):
        raise ValueError("Online safety ceiling: 20 rounds / 64 API attempts")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    episode_id = f"{sample.sample_id}__{method}__{stamp}"
    out = Path(output_dir or ROOT / "outputs/phase2_live/episodes" / episode_id)
    if (out / "episode.json").exists() or (out / "api_attempts.jsonl").exists():
        raise FileExistsError("Refusing to overwrite an existing episode/audit; choose a fresh output directory")
    out.mkdir(parents=True, exist_ok=True)
    if live:
        session = session or SessionLedger(ROOT / "outputs/phase2_live")
        session.start_episode(episode_id)
    audit = Audit(episode_id, config, session if live else None, out / "api_attempts.jsonl",
                  limits.max_api_attempts)
    gate, planner = (components(method, DeepSeekClient(config, audit), JevClient(config, audit), config.threshold)
                     if live else test_components)
    if method == "llm_noask" and gate is not None:
        raise ValueError("NoAsk must have no gate")
    resolver = PreferenceResolver(sample.slots, sample.theta_star)
    history, turns, actions, trajectory, asks = [], [], [], [], []
    burden, repeated, redundant, simulator_time_ms = 0, 0, 0, 0.0
    previously_requested = set()
    termination, error = "round_limit", None
    env, recorder = None, None
    start = time.perf_counter()
    episode = dict(schema_version=2, episode_id=episode_id, sample_id=sample.sample_id,
                   group_id=sample.group_id, partition=sample.partition, method=method,
                   evidence_kind="live_model_and_physics" if live else "offline_test_double_with_real_physics",
                   planner_configuration=config.public_config(), budgets=asdict(limits),
                   prompt_hashes={name: hashlib.sha256(text.encode()).hexdigest() for name, text in
                                  (("action", ACTION_PROMPT), ("question", QUESTION_PROMPT), ("gate_rules", GATE_RULES))},
                   scene_seed=sample.scene_seed, instruction=sample.u0)

    def say(text):
        if not quiet:
            print(text, flush=True)

    try:
        env = Environment(seed=sample.scene_seed, scene_spec=sample.scene(), gui=gui)
        skills = RobotSkills(env)
        recorder = Recorder(env) if record else None

        def tick():
            if env.step_count % 120 == 0:
                trajectory.append(env.snapshot())
            if recorder:
                recorder.on_step()

        env.frame_callback = tick
        env.save_scene(out / "scene.png")
        if recorder:
            recorder.capture(700)
        episode["initial_observation"] = env.snapshot()
        for round_index in range(limits.max_rounds):
            if len(actions) >= limits.max_robot_actions:
                termination = "robot_action_limit"
                break
            audit.round = round_index
            state = observe(env, sample.u0, history)
            payload = public_payload(state)
            turn = dict(round=round_index, public_payload=payload, payload_sha256=payload_hash(payload))
            turns.append(turn)
            # Nothing is generated before this gate. NoAsk has no gate instance.
            result = GateResult("CONTINUE") if gate is None else gate.decide(state)
            turn["gate"] = dict(**result.to_dict(), called=gate is not None)
            say(f"{sample.sample_id} {method} round={round_index} GATE {result.decision} p={result.p_ask}")
            if result.decision == "ASK":
                if burden >= limits.max_slot_requests:
                    raise BudgetExceeded("slot_request_limit")
                before = env.snapshot()
                question = planner.generate_question(state)
                question = Question.parse(question.to_dict(), state)
                routing = resolver.resolve(question)
                requested_roles = question.roles()
                request_count = len(set(routing.values()))
                if burden + request_count > limits.max_slot_requests:
                    raise BudgetExceeded("slot_request_limit")
                # Check is before user disclosure, not after charging the budget.
                simulator_start = time.perf_counter()
                response, charged = resolver.answer(question)
                simulator_time_ms += (time.perf_counter() - simulator_start) * 1000
                assert charged == request_count
                burden += charged
                repeated += len(requested_roles & previously_requested)
                redundant += len(requested_roles & set(disclosed_choices(state)))
                previously_requested.update(requested_roles)
                history.extend([dict(kind="ask", question=question.to_dict(), simulation_step=env.step_count),
                                dict(kind="user_answer", response=response, simulation_step=env.step_count)])
                after = env.snapshot()
                check = dict(before_step=before["simulation_step"], after_step=after["simulation_step"],
                             state_unchanged=before == after, requested_roles=sorted(requested_roles),
                             charged_slots=charged)
                asks.append(check)
                turn.update(question=question.to_dict(), user_answer=response, ask_check=check)
                if before != after:
                    raise RuntimeError("Physical world changed during ASK")
                say(f"ASK {question.to_dict()} USER {response} burden+={charged}")
                if recorder:
                    recorder.label = "ASK " + ",".join(sorted(requested_roles))
                    recorder.capture(1200)
                    recorder.label = "USER " + json.dumps(response, separators=(",", ":"))[:70]
                    recorder.capture(1200)
            else:
                action = planner.generate_action(state)
                turn["action"] = action.to_dict()
                if action.kind == "DONE":
                    if audit.records:
                        audit.records[-1]["completion_kind"] = "DONE"
                        audit.flush()
                    termination = "done"
                    break
                if len(actions) >= limits.max_robot_actions:
                    raise BudgetExceeded("robot_action_limit")
                if recorder:
                    recorder.label = f"{action.kind} {action.object_id}"
                if action.kind == "pick_place":
                    physical = skills.pick_place(action.object_id, action.target_id, action.relation)
                else:
                    physical = skills.cover(action.object_id, action.target_id)
                outcome = physical.to_dict()
                actions.append(outcome)
                history.append(dict(kind="action", result=outcome))
                turn["physical_result"] = outcome
                trajectory.append(env.snapshot())
                say(f"ACTION {action.to_dict()} RESULT {outcome['success']} {outcome['reason']}")
                # A skill failure is public feedback. The next round may repair it.
    except (BudgetExceeded, BackendBlocked, APIError, SchemaError) as exc:
        termination = (str(exc) if isinstance(exc, BudgetExceeded) else
                       f"{type(exc).__name__}:{config.sanitize(str(exc))}")
        error = config.sanitize(str(exc))
        say(f"TERMINATE {termination}")
    except KeyboardInterrupt:
        termination, error = "interrupted", "KeyboardInterrupt"
    except Exception as exc:
        termination, error = f"execution_error:{type(exc).__name__}", config.sanitize(str(exc))
        say(f"TERMINATE {termination}: {error}")
    finally:
        if env is not None:
            try:
                episode["evaluation"] = Evaluator().evaluate(env, sample.private_spec(),
                    clarification_burden=burden, actions=actions, termination=termination)
                episode.update(final_observation=env.snapshot(), execution_log=env.events)
                env.save_scene(out / "final.png")
                if recorder:
                    recorder.label = f"{termination} success={episode['evaluation']['task_success']}"
                    recorder.capture(1800)
                    episode["recording"] = recorder.save(out / "demo.gif")
            except Exception as exc:
                error = config.sanitize(str(exc))
                episode.setdefault("evaluation", dict(task_success=False, termination_reason="evaluation_error"))
                episode["artifact_or_evaluator_error"] = error
            finally:
                env.close()
        episode.setdefault("evaluation", dict(task_success=False, termination_reason=termination))
        episode.update(termination_reason=termination, error=error, turns=turns, actions=actions,
                       public_history=history, trajectory=trajectory, ask_checks=asks,
                       cost=audit.summary(), api_attempts=audit.records,
                       diagnostics=dict(ask_turns=len(asks), clarification_burden=burden,
                                        redundant_slot_requests=redundant, repeated_slot_requests=repeated,
                                        physical_execution_failures=sum(not a["success"] for a in actions)),
                       user_simulator_cost=dict(calls=len(asks), wall_time_ms=simulator_time_ms,
                                                api_attempts=0, input_tokens=None, output_tokens=None),
                       wall_time_s=time.perf_counter() - start)
        episode = config.sanitize(episode)
        (out / "episode.json").write_text(json.dumps(episode, separators=(",", ":")) + "\n")
        (out / "evaluation.json").write_text(json.dumps(episode["evaluation"], indent=2) + "\n")
    say(f"SCORE success={episode['evaluation']['task_success']} burden={burden} "
        f"attempts={episode['cost']['api_attempts']} -> {out}")
    return episode
