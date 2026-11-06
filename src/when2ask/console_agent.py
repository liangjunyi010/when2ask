"""Controller-side model loop. Receives public observations, never Bullet objects."""
import copy
import hashlib
import json
import time
import uuid

from .api import DeepSeekClient, JevClient
from .console_policy import ConsoleScriptedGate, ConsoleScriptedPlanner
from .console_state import Cancelled, LIVE_METHODS
from .protocol import public_payload
from .study_agents import components, prompt_hashes
from .study_protocol import StudyAction, StudyQuestion, disclosed_choices, role_candidates
from .task import PublicState
from .user_simulator import PreferenceResolver


def run_agent(manager, task):
    if task.template == 'find_and_approach':
        from .navigation_console import run_agent as navigation_agent
        return navigation_agent(manager, task)
    start = time.monotonic()
    termination = 'round_limit'
    history = task.history
    api = task.audit

    def update(status):
        with manager.changed:
            if task.cancel:
                raise Cancelled('cancelled_by_user')
            task.status = status
            manager.log(task, 'status', status=status)
            manager.publish(task)

    def state():
        with manager.lock:
            return PublicState.build(task.observation, history, task.sample.u0)

    try:
        if task.method in LIVE_METHODS:
            gate, planner = components(task.method, DeepSeekClient(manager.config, api),
                                       JevClient(manager.config, api), manager.config.threshold)
        else:
            planner = ConsoleScriptedPlanner()
            gate = ConsoleScriptedGate(planner) if task.method == 'scripted_ask' else None
        manager.wait(task, lambda: task.observation is not None or task.error is not None)
        if task.error:
            raise RuntimeError(task.error)
        for round_index in range(20):
            if len(task.actions) >= 12:
                termination = 'robot_action_limit'
                break
            task.round = api.round = round_index
            current = state()
            payload = public_payload(current)
            turn = dict(round=round_index, public_payload=payload,
                        payload_sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
            task.turns.append(turn)
            update('gate' if gate else 'planning_action')
            result = gate.decide(current) if gate else None
            decision = result.decision if result else 'CONTINUE'
            with manager.changed:
                task.gate = dict(decision=decision, p_ask=result.p_ask if result else None,
                    round=round_index,
                    called=gate is not None, backend=('jev' if task.method == 'jev_gate' else
                        'deepseek' if task.method == 'llm_gate' else 'scripted' if gate else 'none'))
                turn['gate'] = copy.deepcopy(task.gate)
                manager.log(task, 'gate_decision', gate=copy.deepcopy(task.gate))
                manager.publish(task)
            if decision == 'ASK':
                if task.burden >= 12:
                    termination = 'slot_request_limit'
                    break
                update('planning_question')
                question = StudyQuestion.parse(planner.generate_question(current).to_dict(), current)
                routing = PreferenceResolver(task.sample.slots, task.sample.theta_star).resolve(question)
                charge = len(set(routing.values()))
                if task.burden + charge > 12:
                    termination = 'slot_request_limit'
                    break
                question_id = uuid.uuid4().hex[:16]
                requests = question.to_dict()['requests']
                if question.type == 'all_preferences':
                    requests = [dict(role=r, candidate_ids=role_candidates(current, r)) for r in sorted(question.roles())]
                names = {k: f"{v['color']} {v['category']}" for k, v in current.observation['objects'].items()}
                with manager.changed:
                    task._question, task._question_state = question, current
                    task.pending = dict(question.to_dict(), id=question_id, requests=requests,
                        candidates=names, known_choices=disclosed_choices(current), simulation_step=current.observation['simulation_step'],
                        created=time.time(), requested_slot_count=charge)
                    task.burden += charge
                    turn.update(question=question.to_dict(), question_id=question_id)
                    history.append(dict(kind='ask', question=question.to_dict(), question_id=question_id,
                                        simulation_step=current.observation['simulation_step']))
                    task.status = 'waiting_answer'
                    manager.log(task, 'question', question_id=question_id, text=question.text, charged_slots=charge)
                    manager.publish(task)
                if task.answer_mode == 'auto':
                    manager.answer(task.id, question_id, source='auto')
                manager.wait(task, lambda: question_id in task.answers, timeout=1800)
                answer = task.answers[question_id]
                response = answer['response']
                before = current.observation
                with manager.changed:
                    if task.observation != before:
                        raise RuntimeError('Physics changed while awaiting a clarification')
                    history.append(dict(kind='user_answer', response=response, source=answer['source'],
                                        question_id=question_id, simulation_step=before['simulation_step']))
                    if answer['source'] == 'human':
                        disclosed = disclosed_choices(PublicState.build(before, history, task.sample.u0))
                        for role, slot in routing.items():
                            if role in disclosed:
                                task.goal_overrides[slot] = disclosed[role]
                    turn.update(user_answer=copy.deepcopy(response), answer_source=answer['source'],
                        ask_check=dict(before_step=before['simulation_step'], after_step=task.observation['simulation_step'],
                                       state_unchanged=True, charged_slots=charge))
                    manager.publish(task)
            else:
                update('planning_action')
                proposed = planner.generate_action(current)
                wire = {'kind': 'DONE'} if proposed.kind == 'DONE' else proposed.to_dict()
                action = StudyAction.parse(wire, current)
                turn['action'] = action.to_dict()
                with manager.changed:
                    manager.log(task, 'planned_action', action=action.to_dict())
                if action.kind == 'DONE':
                    if api.records:
                        api.records[-1]['completion_kind'] = 'DONE'
                        api.flush()
                    termination = 'done'
                    break
                if len(task.actions) >= 12:
                    termination = 'robot_action_limit'
                    break
                command_id = manager.command(task, 'action', action=action.to_dict(),
                    expected_step=current.observation['simulation_step'], evaluation_overrides=copy.deepcopy(task.goal_overrides))
                update('dispatching')
                manager.wait(task, lambda: command_id in task.results or task.error is not None)
                if task.error:
                    raise RuntimeError(task.error)
                physical = task.results[command_id]['result']
                history.append(dict(kind='action', result=physical))
                turn['physical_result'] = copy.deepcopy(physical)
    except Cancelled:
        termination = 'cancelled_by_user'
    except Exception as exc:
        termination = type(exc).__name__
        task.error = manager.config.sanitize(str(exc))
    finally:
        with manager.changed:
            task.pending = None
            task.termination_reason = termination
            task.status = 'finalizing'
            manager.publish(task)
        manager.command(task, 'finalize', termination=termination, clarification_burden=task.burden,
                        evaluation_overrides=copy.deepcopy(task.goal_overrides))
        try:
            manager.wait(task, lambda: task.finalization is not None, timeout=35, allow_cancel=True)
        except Exception as exc:
            task.error = task.error or manager.config.sanitize(str(exc))
        with manager.changed:
            task.pending = None
            task.status = 'cancelled' if task.cancel else 'error' if task.error or task.finalization is None else 'done'
            if task.finalization:
                task.finalization['evaluation']['clarification_burden'] = task.burden
            episode = dict(schema_version='interactive_console_v1', episode_id=task.id, task_template=task.template,
                method=task.method, answer_mode=task.answer_mode, source_sample_id=task.sample.sample_id,
                comparison_id=task.comparison_id, unknown_preferences=task.unknown_preferences,
                public_instruction=task.sample.u0, trace=task.trace,
                partition='interactive_demo', evidence_kind=task.public()['evidence_kind'],
                planner_configuration=manager.config.public_config() if task.method in LIVE_METHODS else None,
                evaluation_protocol=task.public()['evaluation_protocol'], prompt_hashes=prompt_hashes() if task.method in LIVE_METHODS else None,
                turns=task.turns, actions=task.actions, public_history=task.history,
                worker_events=task.events, execution_log=(task.finalization or {}).get('execution_log', []),
                evaluation=(task.finalization or {}).get('evaluation'), termination_reason=termination,
                error=task.error, cost=api.summary(), wall_time_s=time.monotonic() - start)
            (task.output / 'episode.json').write_text(json.dumps(manager.config.sanitize(episode), indent=2) + '\n')
            if task.finalization:
                (task.output / 'evaluation.json').write_text(json.dumps(task.finalization['evaluation'], indent=2) + '\n')
            manager.publish(task)
