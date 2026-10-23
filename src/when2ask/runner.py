"""Owns the private task boundary, physics execution, QA, recording and final scoring."""
from __future__ import annotations

import json
import traceback
from pathlib import Path

import pybullet as p

from .environment import Environment
from .evaluator import Evaluator
from .recording import Recorder
from .scripted_agent import ScriptedAgent
from .skills import RobotSkills
from .task import INSTRUCTION, PrivateTaskSpec, PublicState
from .user_simulator import UserSimulator


def run_episode(mode="ask", seed=0, output_dir=None, *, gui=False, record=False,
                private_spec=None, quiet=False, realtime=True):
    aliases = {"ask": "scripted_ask", "noask": "scripted_noask",
               "scripted_ask": "scripted_ask", "scripted_noask": "scripted_noask"}
    if mode not in aliases:
        raise ValueError("Mode must be ask or noask")
    canonical = aliases[mode]
    out = Path(output_dir or f"outputs/{'ask' if canonical == 'scripted_ask' else 'noask'}_demo")
    out.mkdir(parents=True, exist_ok=True)
    spec = private_spec or PrivateTaskSpec()
    agent = ScriptedAgent(canonical)
    # NoAsk has no user-simulator instance at all.
    simulator = UserSimulator(spec) if canonical == "scripted_ask" else None
    history, decisions, actions, trajectory, ask_checks = [], [], [], [], []
    burden, termination, error = 0, "max_decisions", None
    env, recorder = None, None
    episode = dict(schema_version=1, mode=canonical, seed=seed, instruction=INSTRUCTION,
                   physics=dict(time_step=Environment.DT, solver_iterations=150,
                                deterministic_overlapping_pairs=True, grasp_mode="constraint",
                                connection_mode="GUI" if gui else "DIRECT"))

    def say(text):
        if not quiet:
            print(text, flush=True)

    try:
        env = Environment(seed=seed, gui=gui, realtime=realtime)
        if gui:
            camera = p.getDebugVisualizerCamera(physicsClientId=env.client)
            episode["physics"]["gui_viewport"] = dict(width=camera[0], height=camera[1])
        skills = RobotSkills(env)
        recorder = Recorder(env) if record else None

        def observe_tick():
            if env.step_count % 120 == 0:
                trajectory.append(env.snapshot())
            if recorder:
                recorder.on_step()

        env.frame_callback = observe_tick
        episode["initial_observation"] = env.snapshot()
        trajectory.append(env.snapshot())
        env.save_scene(out / "scene.png")
        if recorder:
            recorder.capture(700)
        say(f"OBSERVE mode={canonical} seed={seed} simulation_step={env.step_count}")
        for _ in range(12):
            # The complete input to any future model policy is this public value.
            state = PublicState.build(env.snapshot(), history)
            decision = agent.decide(state)
            decisions.append(dict(step=env.step_count, **decision.to_dict()))
            if decision.kind == "DONE":
                termination = "done"
                say("DONE -> independent evaluator")
                break
            if decision.kind == "ASK":
                if simulator is None:
                    raise RuntimeError("NoAsk policy attempted a forbidden ASK")
                before = env.snapshot()
                say(f"ASK slots={list(decision.slots)}: {decision.explanation}")
                if recorder:
                    recorder.label = "ASK " + " + ".join(decision.slots)
                    recorder.capture(1200)
                answer = simulator.answer(decision.slots)
                burden += len(decision.slots)  # Each requested slot, including repeats.
                history.append(dict(kind="ask", slots=list(decision.slots),
                                    simulation_step=env.step_count))
                history.append(dict(kind="user_answer", answers=answer,
                                    simulation_step=env.step_count))
                say(f"USER {answer}")
                if recorder:
                    recorder.label = "USER " + " + ".join(answer.values())
                    recorder.capture(1200)
                after = env.snapshot()
                check = dict(before_step=before["simulation_step"], after_step=after["simulation_step"],
                             state_unchanged=before == after, requested_slots=list(decision.slots),
                             disclosed_slots=list(answer), burden=len(decision.slots))
                ask_checks.append(check)
                if before != after:
                    raise RuntimeError("World changed during ASK")
                continue
            if decision.kind != "CONTINUE" or decision.skill not in ("pick_place", "cover"):
                raise RuntimeError("Invalid public policy decision")
            say(f"CONTINUE {decision.skill}({decision.object_id}, {decision.target_id}) grasp_mode=constraint")
            if recorder:
                recorder.label = f"{decision.skill} {decision.object_id}"
            result = getattr(skills, decision.skill)(decision.object_id, decision.target_id).to_dict()
            actions.append(result)
            history.append(dict(kind="action", result=result))
            trajectory.append(env.snapshot())
            env.save_scene(out / f"action_{len(actions):02d}_{decision.skill}.png")
            say(f"RESULT success={result['success']} reason={result['reason']} "
                f"steps={result['end_step'] - result['start_step']}")
            if not result["success"]:
                termination = f"skill_failed:{result['reason']}"
                break
    except KeyboardInterrupt:
        termination, error = "interrupted", "KeyboardInterrupt"
    except Exception as exc:
        termination, error = f"execution_error:{type(exc).__name__}", traceback.format_exc()
        say(error)
    finally:
        if env is not None:
            try:
                episode["evaluation"] = Evaluator().evaluate(env, spec, clarification_burden=burden,
                                                              actions=actions, termination=termination)
                episode["final_observation"] = env.snapshot()
                episode["execution_log"] = env.events
            except Exception:
                episode["evaluation"] = dict(task_success=False, termination_reason="evaluation_error",
                                              clarification_burden=burden, action_count=len(actions))
                error = (error or "") + traceback.format_exc()
            try:
                env.save_scene(out / "final.png")
                if recorder:
                    recorder.label = (f"{episode['evaluation']['termination_reason']} "
                                      f"task_success={episode['evaluation']['task_success']}")
                    recorder.capture(1800)
                    episode["recording"] = recorder.save(out / "demo.gif")
            except Exception:
                # Artifact failures must not erase a valid physical evaluator result.
                episode["artifact_error"] = traceback.format_exc()
                error = (error or "") + traceback.format_exc()
            finally:
                env.close()
        else:
            episode["evaluation"] = dict(task_success=False, termination_reason=termination,
                                          clarification_burden=burden, action_count=len(actions))
        episode.update(decisions=decisions, public_history=history, actions=actions,
                       trajectory=trajectory, ask_checks=ask_checks, error=error)
        (out / "episode.json").write_text(json.dumps(episode, indent=2) + "\n")
        (out / "evaluation.json").write_text(json.dumps(episode["evaluation"], indent=2) + "\n")
    say("SCORE " + json.dumps(episode["evaluation"], ensure_ascii=False))
    say(f"Saved {out.resolve()}")
    return episode
