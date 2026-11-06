"""Independent live Dev loop reusing unchanged physics, simulator and evaluator."""
import json
import time
from dataclasses import asdict
from pathlib import Path

from .accounting import Audit, BackendBlocked, BudgetExceeded, Limits
from .api import DeepSeekClient, JevClient
from .dev_public_summary import digest, encode
from .dev_summary_agents import components, prompt_hashes
from .diverse_world import DiverseEnvironment, DiverseSkills
from .protocol import public_payload
from .recording import Recorder
from .study_evaluator import evaluate_study
from .study_protocol import StudyQuestion, disclosed_choices, observe
from .user_simulator import PreferenceResolver


def run_episode(sample, case_id, profile, output, *, config, session, live=False, record=False,
                expected_models=None, method='jev_gate'):
    if not live or sample.partition != 'dev':
        raise ValueError('Independent diagnostics require explicit live=True and Dev only')
    out = Path(output)
    if out.exists():
        raise FileExistsError('Never overwrite a diagnostic episode; use its saved evidence')
    out.mkdir(parents=True)
    episode_id = case_id + '__' + profile
    session.start_episode(episode_id)
    limits = Limits()
    audit = Audit(episode_id, config, session, out / 'api_attempts.jsonl', limits.max_api_attempts)
    gate, planner = components(method, DeepSeekClient(config, audit), JevClient(config, audit), config.threshold, profile)
    resolver = PreferenceResolver(sample.slots, sample.theta_star)
    turns, history, actions, ask_checks = [], [], [], []
    burden, repeated, redundant, simulator_ms = 0, 0, 0, 0.0
    requested_before = set()
    start = time.perf_counter()
    termination, error, env, recorder = 'round_limit', None, None, None
    episode = dict(schema_version=3, experiment_version='dev_public_summary_v1', episode_id=episode_id,
        case_id=case_id, profile=profile, sample_id=sample.sample_id, group_id=sample.group_id,
        template_id=sample.template_id, partition='dev', method=method,
        evidence_kind='live_model_and_physics', instruction=sample.u0, scene_seed=sample.scene_seed,
        planner_configuration=config.public_config(), budgets=asdict(limits), prompt_hashes=prompt_hashes(profile))

    def check_models():
        for row in audit.records:
            expected = (expected_models or {}).get(row['backend'])
            if row.get('status') == 'ok' and expected and row.get('returned_model') != expected:
                session.outcome(row['backend'], False, 'unexpected_returned_model')
                raise BackendBlocked('Unexpected returned model; stop this version, do not silently retune')

    try:
        env = DiverseEnvironment(seed=sample.scene_seed, scene_spec=sample.scene())
        skills = DiverseSkills(env)
        recorder = Recorder(env) if record else None
        if recorder:
            env.frame_callback = recorder.on_step
            recorder.capture(600)
        env.save_scene(out / 'scene.png')
        episode['initial_observation'] = env.snapshot()
        for round_index in range(limits.max_rounds):
            if len(actions) >= limits.max_robot_actions:
                raise BudgetExceeded('robot_action_limit')
            audit.round = round_index
            state = observe(env, sample.u0, history)
            canonical, sent = public_payload(state), encode(state, profile)
            turn = dict(round=round_index, public_payload=canonical, model_payload=sent,
                        payload_sha256=digest(canonical), model_payload_sha256=digest(sent))
            turns.append(turn)
            result = gate.decide(state) if gate else None
            check_models()
            decision = result.decision if result else 'CONTINUE'
            turn['gate'] = dict(decision=decision, p_ask=result.p_ask if result else None, called=gate is not None)
            print(f'{episode_id} round={round_index} {decision} p={turn["gate"]["p_ask"]}', flush=True)
            if decision == 'ASK':
                if burden >= limits.max_slot_requests:
                    raise BudgetExceeded('slot_request_limit')
                question = StudyQuestion.parse(planner.generate_question(state).to_dict(), state)
                check_models()
                count = len(set(resolver.resolve(question).values()))
                if burden + count > limits.max_slot_requests:
                    raise BudgetExceeded('slot_request_limit')
                before = env.snapshot()
                simulator_start = time.perf_counter()
                response, charged = resolver.answer(question)
                simulator_ms += (time.perf_counter()-simulator_start)*1000
                assert count == charged
                burden += count
                roles = question.roles()
                repeated += len(roles & requested_before)
                redundant += len(roles & set(disclosed_choices(state)))
                requested_before.update(roles)
                history.extend([dict(kind='ask', question=question.to_dict(), simulation_step=env.step_count),
                                dict(kind='user_answer', response=response, simulation_step=env.step_count)])
                after = env.snapshot()
                check = dict(before_step=before['simulation_step'], after_step=after['simulation_step'],
                             state_unchanged=before == after, charged_slots=count)
                ask_checks.append(check)
                turn.update(question=question.to_dict(), user_answer=response, ask_check=check)
                if before != after:
                    raise RuntimeError('ASK advanced physics')
                if recorder:
                    recorder.label = 'ASK ' + ','.join(sorted(roles));recorder.capture(1000)
                    recorder.label = 'USER ' + json.dumps(response)[:70];recorder.capture(1000)
            else:
                action = planner.generate_action(state)
                check_models()
                turn['action'] = action.to_dict()
                if action.kind == 'DONE':
                    if audit.records:
                        audit.records[-1]['completion_kind'] = 'DONE';audit.flush()
                    termination = 'done'
                    break
                if recorder:
                    recorder.label = action.kind + ' ' + action.object_id
                result = (skills.pick_place(action.object_id, action.target_id, action.relation)
                          if action.kind == 'pick_place' else skills.cover(action.object_id, action.target_id))
                physical = result.to_dict()
                actions.append(physical)
                history.append(dict(kind='action', result=physical))
                turn['physical_result'] = physical
    except KeyboardInterrupt:
        termination, error = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        termination, error = type(exc).__name__, config.sanitize(str(exc))
    finally:
        if env is not None:
            try:
                episode['evaluation'] = evaluate_study(env, sample, clarification_burden=burden,
                                                       actions=actions, termination=termination)
                episode.update(final_observation=env.snapshot(), execution_log=env.events)
                env.save_scene(out / 'final.png')
                if recorder:
                    recorder.label = f'{termination} success={episode["evaluation"]["task_success"]}'
                    recorder.capture(1500)
                    episode['recording'] = recorder.save(out / 'demo.gif')
            except Exception as exc:
                episode['artifact_or_evaluator_error'] = config.sanitize(str(exc))
            finally:
                env.close()
        episode.setdefault('evaluation', dict(task_success=False, termination_reason='environment_unavailable'))
        episode.update(turns=turns, actions=actions, public_history=history, ask_checks=ask_checks,
            termination_reason=termination, error=error, cost=audit.summary(), api_attempts=audit.records,
            diagnostics=dict(ask_turns=len(ask_checks), redundant_slot_requests=redundant,
                repeated_slot_requests=repeated, physical_execution_failures=sum(not a['success'] for a in actions)),
            user_simulator_cost=dict(calls=len(ask_checks), wall_time_ms=simulator_ms, api_attempts=0,
                                     input_tokens=None, output_tokens=None),
            wall_time_s=time.perf_counter() - start)
        episode = config.sanitize(episode)
        (out / 'episode.json').write_text(json.dumps(episode, ensure_ascii=False) + '\n')
        (out / 'evaluation.json').write_text(json.dumps(episode['evaluation'], indent=2) + '\n')
    return episode
