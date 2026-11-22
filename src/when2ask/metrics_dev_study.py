"""Bounded nine-task, four-policy Dev experiment; preserves all earlier records."""
import copy
import hashlib
import json
import multiprocessing
import random
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .accounting import SessionLedger
from .api import DeepSeekClient,JevClient
from .config import ROOT,Config
from .grounded_dev_health import SchemaAwareSession
from .nine_task_data import write,digest,STUDY
from .nine_task_world import Adapter
from .task6_protocol import Question
from .user_simulator import PreferenceResolver
from .unified_dev_study import TimedAudit
from .metrics_dev_data import VERSION,DATA,OUT,load,entries,audit_rows
from .metrics_dev_agents import components,view,Unified,prompt_hashes,build_prompt

METHODS=('llm_noask','llm_gate','jev_gate','llm_unified')
LIMITS=dict(rounds=20,robot_actions=12,slot_requests=12,api_attempts=32)
MAX_ATTEMPTS,MAX_EPISODES=1600,108


class Ledger(SessionLedger):
    def __init__(self,directory=OUT/'session',max_attempts=MAX_ATTEMPTS,max_episodes=MAX_EPISODES):
        self.directory=directory;directory.mkdir(parents=True,exist_ok=True)
        self.path=directory/'session_budget.json';self.policy=VERSION
        self.ceilings=(MAX_ATTEMPTS,MAX_EPISODES)
        self.max_attempts=min(max_attempts,MAX_ATTEMPTS);self.max_episodes=min(max_episodes,MAX_EPISODES)


def oracle_one(sid):
    from .task6_protocol import payload,scripted_next
    from .study_evaluator import expected_targets
    s=next(s for s in load() if s.sample_id==sid)
    dest=OUT/'oracle'/sid;dest.mkdir(parents=True,exist_ok=False)
    a=None;actions=[];proposals=[];error=None;score=None
    try:
        a=Adapter(replace(s,initial_disclosed_slots=list(s.slots)))
        a.world.render().save(dest/'scene.png')
        for _ in range(12):
            if a.family=='study':
                targets=expected_targets(s,a.world)
                roles=['block','cup'] if s.dag['order']=='block_first' else ['cup','block']
                plan=[dict(kind='pick_place',object_id=s.theta_star[r+'_choice'],target_id=targets[r],relation='inside') for r in roles]
                if s.template_id=='pack_and_cover':plan.append(dict(kind='cover',object_id=s.theta_star['lid_choice'],target_id='box'))
                proposed=plan[len(actions)] if len(actions)<len(plan) else dict(kind='DONE')
            elif a.family=='navigation':proposed=dict(kind='search',location_id=s.target_location) if not actions else dict(kind='DONE')
            else:proposed=scripted_next(payload(s.u0,a.world.observation(),[]))
            if proposed['kind']=='DONE':break
            proposals.append(proposed);result=a.execute(proposed);actions.append(result)
            if not result['success']:break
        score=a.score(0,actions,'offline_oracle');a.world.render().save(dest/'final.png')
        write(dest/'trace.json',dict(sample_id=sid,group_id=s.group_id,partition='dev',evidence_kind='real_pybullet_oracle',
            proposed_actions=proposals,actions=actions,execution_log=a.world.events,evaluation=score,api_attempts=0))
    except Exception as exc:
        error=repr(exc);write(dest/'error.json',dict(error=error,actions=actions,api_attempts=0))
    finally:
        if a:a.close()
    row=dict(sample_id=sid,template=s.template_id,success=bool(score and score['task_success']),error=error)
    print(json.dumps(row),flush=True);return row


def oracle():
    (OUT/'oracle').mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        rows=list(pool.map(oracle_one,[s.sample_id for s in load()]))
    result=dict(successes=sum(r['success'] for r in rows),total=len(rows),rows=rows,api_attempts=0)
    write(OUT/'oracle/summary.json',result);return result


def freeze():
    if (OUT/'manifest.json').exists():raise FileExistsError('Never overwrite a locked study')
    validation=json.loads((OUT/'oracle/summary.json').read_text())
    if validation['successes']!=27:raise ValueError('Require 27/27 actual physical oracle passes')
    paths=list((ROOT/'src/when2ask').glob('*.py'))+[ROOT/'script/benchmark.py']
    jobs=[dict(sample_id=s.sample_id,method=m,episode_id=s.sample_id+'__'+m) for s in load() for m in METHODS]
    random.Random(42781123).shuffle(jobs)
    from . import tabletop_dev_agents,task6_agents,navigation_agents,gate_ready_dev
    plan=dict(study_version=VERSION,status='LOCKED_BEFORE_ANY_NEW_PAID_CALLS',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        dataset_sha256=hashlib.sha256((DATA/'samples.json').read_bytes()).hexdigest(),
        pricing_sha256=hashlib.sha256((OUT/'pricing.json').read_bytes()).hexdigest(),
        configuration=Config.load().public_config(),expected_returned_models=dict(deepseek='deepseek-flash',jev='jev-1.14.0'),
        dataset_audit=audit_rows(entries()),unified_prompt_hashes=prompt_hashes(),
        baseline_prompt_hashes=dict(tabletop=tabletop_dev_agents.PROFILES['facts_contract'].hashes(),
            task6=task6_agents.prompt_hashes(),navigation=navigation_agents.prompt_hashes(),memory=gate_ready_dev.prompt_hashes()),
        profiles=dict(tabletop='facts_contract',memory_tasks='memory_v6_planner_gate_v7',others='unchanged_existing_task_family'),
        global_limits=dict(authenticated_requests=MAX_ATTEMPTS,full_episodes=MAX_EPISODES),per_episode_limits=LIMITS,
        max_workers=3,launch_order_seed=42781123,jobs=jobs,
        parameters='DeepSeek temperature0, non-thinking JSON. Existing family action/question limits preserved; Unified takes max(action,question): tabletop500, memory650, other tasks300. Separate Gate64. Jev threshold0.5.',
        retry_policy='One retry per API/schema failure, all attempts counted. Permanent or three consecutive network/API errors block backend. HTTP200 schema errors are not backend outages. No whole-episode reruns or post-outcome prompt changes.',
        main_metrics=dict(success='Physical successes / scored episodes, independent of DONE.',
            speed='Mean cumulative API HTTP seconds per started episode, including retries/DONE. Not physical motion speed.',
            cost='Mean estimated USD per started episode from real usage/cache split and official prices; unknown is null.',
            fpr='Task-level: any explicit ASK on the 18 prelabelled fully disclosed negatives. NoAsk N/A. Technical interruption with no observed ASK is censored, never counted TN. Explicit ASK remains FP even if question generation fails. Denominators and censoring reported.'),
        scope='27 Dev variants, 18 existing Dev layout groups, nine templates. Contrast shares its template second layout. Seven required-preference contrasts, one optional search hint, one observable-fact hard negative. No new Test claim or pooling of old episodes.',
        inference_boundary='Stratum/FPR labels, sample/group IDs, private preferences and evaluator results never enter policy payloads.',
        simulator='Unchanged structured resolver; physical stepping freezes during ASK. Burden retained in raw logs only, not main tables.',
        scheduling='Three fixed worker processes, frozen globally shuffled order. API time includes actual HTTP latency; wall time also includes contention/physics. No latency isolation claim.')
    write(OUT/'manifest.json',plan)
    d=OUT/'prompts';d.mkdir()
    for t in prompt_hashes():(d/(t+'.txt')).write_text(build_prompt(t))
    return plan


def checked():
    plan=json.loads((OUT/'manifest.json').read_text())
    if Config.load().public_config()!=plan['configuration']:raise ValueError('Model configuration changed')
    for p,h in plan['source_hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('Source changed: '+p)
    for p,key in [(DATA/'samples.json','dataset_sha256'),(OUT/'pricing.json','pricing_sha256')]:
        if hashlib.sha256(p.read_bytes()).hexdigest()!=plan[key]:raise ValueError('Data/pricing changed')
    return plan


def run_episode(job):
    plan=checked();budget=Ledger().snapshot()
    blocked=budget.get('backends',{})
    reason=('global_request_limit' if budget['attempts']>=MAX_ATTEMPTS else
            'deepseek_blocked' if blocked.get('deepseek',{}).get('blocked') else
            'jev_blocked' if job['method']=='jev_gate' and blocked.get('jev',{}).get('blocked') else None)
    if reason:return dict(**job,not_run=reason)
    s=next(s for s in load() if s.sample_id==job['sample_id'])
    dest=OUT/'episodes'/job['episode_id'];dest.mkdir(parents=True,exist_ok=False)
    Ledger().start_episode(job['episode_id']);config=Config.load()
    api=TimedAudit(job['episode_id'],config,path=dest/'api_attempts.jsonl',limit=LIMITS['api_attempts'])
    api.session=SchemaAwareSession(Ledger(),api)
    deepseek,jev=DeepSeekClient(config,api),JevClient(config,api)
    unified=Unified(s.template_id,deepseek) if job['method']=='llm_unified' else None
    gate,planner=(None,None) if unified else components(s.template_id,job['method'],deepseek,jev)
    a=None;history=[];prior=[];turns=[];actions=[];burden=0;score=None;error=None;final=None;events=[]
    termination='round_limit';start=time.monotonic()
    def models():
        for r in api.records:
            if r.get('returned_model') and r['returned_model']!=plan['expected_returned_models'][r['backend']]:
                Ledger().outcome(r['backend'],False,'returned_model_drift');raise RuntimeError('returned_model_drift')
    try:
        a=Adapter(s);a.world.render().save(dest/'scene.png')
        for i in range(LIMITS['rounds']):
            api.round=i;state,public=view(a,history,prior)
            turn=dict(round=i,public_payload=public,payload_sha256=digest(public));turns.append(turn)
            q=None;action=None
            if unified:
                q,action=unified.decide(state);models()
                turn.update(unified_output=copy.deepcopy(unified.last_output),
                    unified_decision=dict(kind='ASK' if q is not None else 'ACTION',separate_gate_called=False))
                if unified.last_model_plan is not None:turn['model_plan']=copy.deepcopy(unified.last_model_plan)
            else:
                result=gate.decide(state) if gate else None;models()
                turn['gate']=dict(called=gate is not None,decision=result.decision if result else 'CONTINUE',p_ask=result.p_ask if result else None)
                if hasattr(gate,'last_payload'):turn['gate_payload']=copy.deepcopy(gate.last_payload)
                if turn['gate']['decision']=='ASK':
                    if burden>=LIMITS['slot_requests']:termination='slot_request_limit';break
                    q=planner.generate_question(state)
                else:
                    action=planner.generate_action(state)
                    if hasattr(planner,'last_model_plan'):turn['model_plan']=copy.deepcopy(planner.last_model_plan)
                models()
            if q is not None:
                if isinstance(q,dict):q=Question(q['type'],q['text'],q['requests'],('target_location',))
                resolver=PreferenceResolver(s.slots,s.theta_star);charge=len(set(resolver.resolve(q).values()))
                turn['proposed_question']=q.to_dict()
                if burden+charge>LIMITS['slot_requests']:termination='slot_request_limit';break
                before=a.state(history);before=before.observation if a.family=='study' else before
                answer,_=resolver.answer(q)
                after=a.state(history);after=after.observation if a.family=='study' else after
                if before!=after:raise RuntimeError('ASK changed physics')
                burden+=charge;history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=answer)])
                turn.update(question=q.to_dict(),user_answer=answer,
                    ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
            else:
                action=action.to_dict() if hasattr(action,'to_dict') else action
                turn['action']=action
                if action['kind']=='DONE':
                    api.records[-1]['completion_kind']='DONE';api.flush();termination='done';break
                if len(actions)>=LIMITS['robot_actions']:termination='robot_action_limit';break
                result=a.execute(action);actions.append(result)
                history.append(dict(kind='action',result=result));turn['physical_result']=copy.deepcopy(result)
    except Exception as exc:
        termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        if a:
            try:
                score=a.score(burden,actions,termination);a.world.render().save(dest/'final.png')
                final=a.state(history);final=final.observation if a.family=='study' else final
                events=copy.deepcopy(a.world.events)
            finally:a.close()
        e=dict(**job,study_version=VERSION,partition='dev',group_id=s.group_id,template_id=s.template_id,
            evidence_kind='real_api_real_pybullet',instruction=s.u0,turns=turns,actions=actions,public_history=history,
            evaluation=score,termination_reason=termination,error=error,cost=api.summary(),wall_time_s=time.monotonic()-start,
            final_observation=final,execution_log=events,configuration=config.public_config())
        write(dest/'episode.json',config.sanitize(e));write(dest/'evaluation.json',score)
    row=dict(**job,success=score['task_success'] if score else None,actions=len(actions),attempts=len(api.records),termination=termination,error=error)
    print(json.dumps(row),flush=True);return row


def run(live=False):
    if not live:raise ValueError('Explicit --live required')
    plan=checked();(OUT/'episodes').mkdir(exist_ok=False)
    rows=[]
    with ProcessPoolExecutor(max_workers=plan['max_workers'],mp_context=multiprocessing.get_context('spawn')) as pool:
        for row in pool.map(run_episode,plan['jobs'],chunksize=1):
            rows.append(row);write(OUT/'progress.json',dict(rows=rows,session=Ledger().snapshot()))
    result=dict(planned=len(plan['jobs']),rows=rows,session=Ledger().snapshot())
    write(OUT/'run_summary.json',result);return result
