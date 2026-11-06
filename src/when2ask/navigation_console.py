"""Navigation model loop over public HTTP observations, using the existing queue."""
import copy
import hashlib
import json
import time
import uuid

from .api import DeepSeekClient, JevClient
from .console_state import Cancelled, LIVE_METHODS
from .navigation_agents import VERSION, ScriptedGate, ScriptedPlanner, components, prompt_hashes
from .navigation_map import LOCATIONS
from .navigation_protocol import location_claim, parse_action, parse_question, public_payload


def run_agent(manager, task):
    start=time.monotonic();termination='round_limit';api=task.audit

    def update(status):
        with manager.changed:
            if task.cancel:raise Cancelled('cancelled_by_user')
            task.status=status;manager.log(task,'status',status=status);manager.publish(task)

    try:
        if task.method in LIVE_METHODS:
            gate,planner=components(task.method,DeepSeekClient(manager.config,api),JevClient(manager.config,api),manager.config.threshold)
        else:
            gate=ScriptedGate() if task.method=='scripted_ask' else None;planner=ScriptedPlanner()
        manager.wait(task,lambda:task.observation is not None or task.error is not None)
        if task.error:raise RuntimeError(task.error)
        for round_index in range(20):
            task.round=api.round=round_index
            payload=public_payload(task.sample.u0,task.observation,task.history)
            turn=dict(round=round_index,public_payload=payload,
                payload_sha256=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest())
            task.turns.append(turn)
            update('gate' if gate else 'planning_action')
            result=gate.decide(payload) if gate else None
            decision=result.decision if result else 'CONTINUE'
            with manager.changed:
                task.gate=dict(decision=decision,p_ask=result.p_ask if result else None,round=round_index,
                    called=gate is not None,backend='jev' if task.method=='jev_gate' else 'deepseek' if task.method=='llm_gate' else 'scripted' if gate else 'none')
                turn['gate']=copy.deepcopy(task.gate);manager.log(task,'gate_decision',gate=copy.deepcopy(task.gate));manager.publish(task)
            if decision=='ASK':
                if task.burden>=12:termination='slot_request_limit';break
                update('planning_question')
                question=parse_question(planner.generate_question(payload));qid=uuid.uuid4().hex[:16]
                before=copy.deepcopy(task.observation)
                with manager.changed:
                    task._question=question;task._question_state=payload
                    claim=location_claim(task.sample.u0,task.history)
                    task.pending=dict(question,id=qid,candidates={k:v['name'] for k,v in LOCATIONS.items()},
                        known_choices={},simulation_step=before['simulation_step'],created=time.time(),requested_slot_count=1,
                        fact_type='fixed_world_location',previous_claim=claim)
                    task.burden+=1;turn.update(question=copy.deepcopy(question),question_id=qid)
                    task.history.append(dict(kind='ask',question=copy.deepcopy(question),question_id=qid,simulation_step=before['simulation_step']))
                    task.status='waiting_answer';manager.log(task,'question',question_id=qid,text=question['text'],charged_slots=1);manager.publish(task)
                if task.answer_mode=='auto':
                    # A real, declared reply delay; never advances the Bullet world.
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline:
                        if task.cancel:raise Cancelled('cancelled_by_user')
                        time.sleep(min(.1,max(0,deadline-time.monotonic())))
                    manager.answer(task.id,qid,source='auto')
                manager.wait(task,lambda:qid in task.answers,timeout=1800)
                answer=task.answers[qid]
                with manager.changed:
                    if task.observation!=before:raise RuntimeError('Navigation physics changed during ASK')
                    task.history.append(dict(kind='user_answer',response=copy.deepcopy(answer['response']),source=answer['source'],
                        question_id=qid,simulation_step=before['simulation_step']))
                    turn.update(user_answer=copy.deepcopy(answer['response']),answer_source=answer['source'],
                        ask_check=dict(before_step=before['simulation_step'],after_step=task.observation['simulation_step'],state_unchanged=True,charged_slots=1))
                    manager.publish(task)
            else:
                update('planning_action');action=parse_action(planner.generate_action(payload));turn['action']=action
                with manager.changed:manager.log(task,'planned_action',action=action)
                if action['kind']=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
                if len(task.actions)>=8:termination='robot_action_limit';break
                if task.observation['distance_travelled_m']>=36:termination='distance_limit';break
                cid=manager.command(task,'action',action=action,expected_step=task.observation['simulation_step'])
                update('dispatching');manager.wait(task,lambda:cid in task.results or task.error is not None,timeout=180)
                if task.error:raise RuntimeError(task.error)
                physical=task.results[cid]['result'];task.history.append(dict(kind='action',result=physical))
                turn['physical_result']=copy.deepcopy(physical)
    except Cancelled:termination='cancelled_by_user'
    except Exception as exc:
        termination=type(exc).__name__;task.error=manager.config.sanitize(str(exc))
    finally:
        with manager.changed:
            task.pending=None;task.termination_reason=termination;task.status='finalizing';manager.publish(task)
        manager.command(task,'finalize',termination=termination,clarification_burden=task.burden)
        try:manager.wait(task,lambda:task.finalization is not None,timeout=35,allow_cancel=True)
        except Exception as exc:task.error=task.error or manager.config.sanitize(str(exc))
        with manager.changed:
            task.status='cancelled' if task.cancel else 'error' if task.error or task.finalization is None else 'done'
            episode=dict(schema_version=VERSION,episode_id=task.id,task_template=task.template,method=task.method,
                answer_mode=task.answer_mode,comparison_id=task.comparison_id,partition='navigation_dev_only',
                source_sample_id=task.sample.sample_id,layout_group=task.sample.group_id,scene_seed=task.sample.scene_seed,
                evidence_kind=task.public()['evidence_kind'],evaluation_protocol='fixed_world_location',
                planner_configuration=manager.config.public_config() if task.method in LIVE_METHODS else None,
                prompt_hashes=prompt_hashes(),public_instruction=task.sample.u0,turns=task.turns,
                actions=task.actions,public_history=task.history,trace=task.trace,worker_events=task.events,
                execution_log=(task.finalization or {}).get('execution_log',[]),evaluation=(task.finalization or {}).get('evaluation'),
                termination_reason=termination,error=task.error,cost=api.summary(),wall_time_s=time.monotonic()-start,
                budgets=dict(rounds=20,robot_actions=8,slot_requests=12,api_attempts=64,distance_m=36),
                motion_time_scale=1,auto_answer_delay_s=3)
            (task.output/'episode.json').write_text(json.dumps(manager.config.sanitize(episode),indent=2)+'\n')
            if task.finalization:(task.output/'evaluation.json').write_text(json.dumps(task.finalization['evaluation'],indent=2)+'\n')
            manager.publish(task)
