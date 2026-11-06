"""Independent real-physics episodes. Shared model planner; no oracle gate overrides."""
import copy
import hashlib
import json
import time
from pathlib import Path

from .accounting import Audit
from .api import DeepSeekClient,JevClient
from .config import Config
from .navigation_protocol import parse_action,parse_question
from .nav2_agents import components,hashes
from .nav2_public import payload
from .nav2_task import settings
from .nav2_world import World


def write_json(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def run_episode(sample,method,output,ledger,*,realtime=True,component_factory=components):
    cfg=settings();limits=cfg['limits'];config=Config.load();output=Path(output);output.mkdir(parents=True,exist_ok=False)
    eid=output.name;ledger.start_episode(eid);api=Audit(eid,config,session=ledger,path=output/'api_attempts.jsonl',limit=limits['episode_api_attempts'])
    turns=[];history=[];actions=[];burden=0;reply_wait=0.;motion_wall=0.;world=None;error=None;evaluation=None
    termination='round_limit';start=time.monotonic()
    try:
        gate,planner=component_factory(method,DeepSeekClient(config,api),JevClient(config,api),
            cfg['full_episode_contract'],cfg['gate_threshold'])
        world=World(sample);world.render().save(output/'scene.png')
        for round_index in range(limits['rounds']):
            api.round=round_index;public=payload(sample.u0,world.observation(),history,sample.public_contract(),cfg['full_episode_payload'])
            turn=dict(round=round_index,public_payload=public,payload_sha256=hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest())
            turns.append(turn)
            decision=gate.decide(public) if gate else None
            turn['gate']=dict(decision=decision.decision if decision else 'CONTINUE',p_ask=decision.p_ask if decision else None,called=gate is not None)
            print(json.dumps(dict(event='gate',episode=eid,round=round_index,**turn['gate'])),flush=True)
            if decision and decision.decision=='ASK':
                if burden>=limits['slot_requests']:termination='slot_request_limit';break
                question=parse_question(planner.generate_question(public));before=copy.deepcopy(world.observation());target_before=world.target_pose()
                turn['question']=question;burden+=1;history.append(dict(kind='ask',question=question,simulation_step=world.step_count))
                wait_start=time.monotonic();time.sleep(sample.answer_delay_s);waited=time.monotonic()-wait_start;reply_wait+=waited
                # Private answer resolver is reached only for this single parsed location request.
                answer={'choices':{'target_location':sample.target_location}}
                after=world.observation()
                if before!=after or target_before!=world.target_pose():raise RuntimeError('Physics changed during ASK')
                history.append(dict(kind='user_answer',response=answer,source='auto',simulation_step=world.step_count))
                turn.update(user_answer=answer,answer_wait_s=waited,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=1))
            else:
                action=parse_action(planner.generate_action(public));turn['action']=action
                if action['kind']=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
                if len(actions)>=limits['robot_actions']:termination='robot_action_limit';break
                if world.distance_m>=limits['distance_m']:termination='distance_limit';break
                step=world.step_count;wall=time.monotonic()
                def pace():
                    delay=wall+(world.step_count-step)*world.DT-time.monotonic()
                    if delay>0:time.sleep(delay)
                world.frame_callback=pace if realtime else None
                result=world.search(action['location_id']);world.frame_callback=None
                elapsed=time.monotonic()-wall;motion_wall+=elapsed
                turn.update(physical_result=result,physical_wall_s=elapsed)
                actions.append(result);history.append(dict(kind='action',result=result))
        evaluation=world.evaluate(burden,actions,termination)
    except Exception as exc:
        termination=type(exc).__name__;error=config.sanitize(str(exc))
        if world:world.frame_callback=None;evaluation=world.evaluate(burden,actions,termination)
    finally:
        motion_s=(world.step_count-240)*World.DT if world else 0.
        operational=motion_s+reply_wait+cfg['burden_equivalent_s']*burden
        cost=dict(motion_sim_s=motion_s,motion_wall_s=motion_wall,reply_wait_wall_s=reply_wait,
            burden_equivalent_s=cfg['burden_equivalent_s']*burden,operational_seconds=operational,
            penalized_seconds=operational+(0 if evaluation and evaluation['task_success'] else cfg['failure_penalty_s']),
            definition='Physical simulation seconds + actual reply-wait seconds + declared interruption seconds. API time reported separately.')
        episode=dict(schema_version=cfg['version'],episode_id=eid,sample_id=sample.sample_id,group_id=sample.group_id,
            partition='navigation_dev_v2_only',method=method,evidence_kind='live_models_real_pybullet' if component_factory is components else 'injected_offline_test_policy_real_pybullet',
            public_contract=sample.public_contract(),prompt_hashes=hashes(),planner_configuration=config.public_config(),
            turns=turns,actions=actions,public_history=history,evaluation=evaluation,
            execution_log=world.events if world else [],termination_reason=termination,error=error,
            clarification_burden=burden,api_cost=api.summary(),operational_cost=cost,wall_time_s=time.monotonic()-start,
            realtime_physics=realtime)
        if world:world.render().save(output/'final.png');world.close()
        write_json(output/'episode.json',config.sanitize(episode));write_json(output/'evaluation.json',evaluation)
    return episode
