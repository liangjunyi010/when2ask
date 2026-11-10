"""New task controller loop, with the existing task/question routing and budgets."""
import copy
import hashlib
import json
import time
import uuid

from .api import DeepSeekClient,JevClient
from .console_state import Cancelled,LIVE_METHODS
from .task6_agents import components,prompt_hashes,ScriptedGate,ScriptedPlanner
from .task6_protocol import payload,question,action,known_choices,names
from .task6_spec import VERSION
from .user_simulator import PreferenceResolver


def run_agent(manager,task):
    start=time.monotonic();termination='round_limit';api=task.audit
    def update(status):
        with manager.changed:
            if task.cancel:raise Cancelled('cancelled_by_user')
            task.status=status;manager.log(task,'status',status=status);manager.publish(task)
    try:
        if task.method in LIVE_METHODS:
            gate,planner=components(task.method,DeepSeekClient(manager.config,api),JevClient(manager.config,api),manager.config.threshold)
        else:gate=ScriptedGate() if task.method=='scripted_ask' else None;planner=ScriptedPlanner()
        manager.wait(task,lambda:task.observation is not None or task.error is not None)
        if task.error:raise RuntimeError(task.error)
        for index in range(20):
            task.round=api.round=index
            current=payload(task.sample.u0,task.observation,task.history)
            turn=dict(round=index,public_payload=current,payload_sha256=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest())
            task.turns.append(turn);update('gate' if gate else 'planning_action')
            result=gate.decide(current) if gate else None
            with manager.changed:
                task.gate=dict(decision=result.decision if result else 'CONTINUE',p_ask=result.p_ask if result else None,
                    round=index,called=gate is not None,backend='jev' if task.method=='jev_gate' else 'deepseek' if task.method=='llm_gate' else 'scripted' if gate else 'none')
                turn['gate']=copy.deepcopy(task.gate);manager.log(task,'gate_decision',gate=copy.deepcopy(task.gate));manager.publish(task)
            if task.gate['decision']=='ASK':
                if task.burden>=12:termination='slot_request_limit';break
                update('planning_question');q=question(planner.generate_question(current).to_dict(),current)
                routing=PreferenceResolver(task.sample.slots,task.sample.theta_star).resolve(q);charge=len(set(routing.values()))
                if task.burden+charge>12:termination='slot_request_limit';break
                qid=uuid.uuid4().hex[:16];before=copy.deepcopy(task.observation)
                requests=q.requests if q.type!='all_preferences' else [dict(role=r,candidate_ids=current['observation']['task']['preference_slots'][r]['candidate_ids']) for r in sorted(q.roles())]
                with manager.changed:
                    task._question,task._question_state=q,current
                    task.pending=dict(q.to_dict(),id=qid,requests=requests,candidates=names(before),known_choices=known_choices(current),
                        simulation_step=before['simulation_step'],created=time.time(),requested_slot_count=charge)
                    task.burden+=charge;turn.update(question=q.to_dict(),question_id=qid)
                    task.history.append(dict(kind='ask',question=q.to_dict(),question_id=qid,simulation_step=before['simulation_step']))
                    task.status='waiting_answer';manager.log(task,'question',question_id=qid,text=q.text,charged_slots=charge);manager.publish(task)
                if task.answer_mode=='auto':manager.answer(task.id,qid,source='auto')
                manager.wait(task,lambda:qid in task.answers,timeout=1800)
                answer=task.answers[qid]
                with manager.changed:
                    if task.observation!=before:raise RuntimeError('Physical world changed during ASK')
                    task.history.append(dict(kind='user_answer',response=copy.deepcopy(answer['response']),source=answer['source'],question_id=qid,simulation_step=before['simulation_step']))
                    disclosed=known_choices(payload(task.sample.u0,before,task.history))
                    if answer['source']=='human':
                        for role,slot in routing.items():
                            if task.sample.slots[slot].get('kind')!='world_fact' and role in disclosed:task.goal_overrides[slot]=disclosed[role]
                    turn.update(user_answer=copy.deepcopy(answer['response']),answer_source=answer['source'],ask_check=dict(before_step=before['simulation_step'],after_step=task.observation['simulation_step'],state_unchanged=True,charged_slots=charge))
                    manager.publish(task)
            else:
                update('planning_action');proposed=action(planner.generate_action(current),current);turn['action']=proposed
                with manager.changed:manager.log(task,'planned_action',action=proposed)
                if proposed['kind']=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
                if len(task.actions)>=12:termination='robot_action_limit';break
                cid=manager.command(task,'action',action=proposed,expected_step=task.observation['simulation_step'],evaluation_overrides=copy.deepcopy(task.goal_overrides))
                update('dispatching');manager.wait(task,lambda:cid in task.results or task.error is not None,timeout=180)
                if task.error:raise RuntimeError(task.error)
                physical=task.results[cid]['result'];task.history.append(dict(kind='action',result=physical));turn['physical_result']=copy.deepcopy(physical)
    except Cancelled:termination='cancelled_by_user'
    except Exception as exc:termination=type(exc).__name__;task.error=manager.config.sanitize(str(exc))
    finally:
        with manager.changed:
            task.pending=None;task.termination_reason=termination;task.status='finalizing';manager.publish(task)
        manager.command(task,'finalize',termination=termination,clarification_burden=task.burden,evaluation_overrides=copy.deepcopy(task.goal_overrides))
        try:manager.wait(task,lambda:task.finalization is not None,timeout=45,allow_cancel=True)
        except Exception as exc:task.error=task.error or manager.config.sanitize(str(exc))
        with manager.changed:
            task.status='cancelled' if task.cancel else 'error' if task.error or task.finalization is None else 'done'
            episode=dict(schema_version=VERSION,episode_id=task.id,task_template=task.template,method=task.method,
                source_sample_id=task.sample.sample_id,scene_seed=task.sample.scene_seed,group_id=task.sample.group_id,
                partition=task.sample.partition,answer_mode=task.answer_mode,comparison_id=task.comparison_id,
                evidence_kind=task.public()['evidence_kind'],planner_configuration=manager.config.public_config() if task.method in LIVE_METHODS else None,
                prompt_hashes=prompt_hashes(),public_instruction=task.sample.u0,turns=task.turns,actions=task.actions,
                public_history=task.history,trace=task.trace,execution_log=(task.finalization or {}).get('execution_log',[]),
                evaluation=(task.finalization or {}).get('evaluation'),termination_reason=termination,error=task.error,
                cost=api.summary(),wall_time_s=time.monotonic()-start,review=task.public()['review'],
                artifacts=(task.finalization or {}).get('artifacts'),budgets=dict(rounds=20,robot_actions=12,slot_requests=12,api_attempts=32))
            (task.output/'episode.json').write_text(json.dumps(manager.config.sanitize(episode),indent=2)+'\n')
            if task.finalization:(task.output/'evaluation.json').write_text(json.dumps(task.finalization['evaluation'],indent=2)+'\n')
            manager.publish(task)
