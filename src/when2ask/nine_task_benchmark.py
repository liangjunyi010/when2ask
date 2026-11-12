"""Bounded real-API, real-physics nine-task coverage pilot; no legacy mutations."""
from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import random
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .accounting import Audit, SessionLedger
from .api import DeepSeekClient, JevClient
from .config import ROOT, Config
from .grounded_dev_health import SchemaAwareSession
from .nine_task_data import DATA, OUT, STUDY, VERSION, audit, digest, load, write
from .nine_task_world import Adapter
from .protocol import public_payload
from .user_simulator import PreferenceResolver

METHODS = ('llm_noask','llm_gate','jev_gate')
MEMORY = ('buffer_exchange','retrieve_restore','occlusion_inspection')
LIMITS = dict(rounds=20,robot_actions=12,slot_requests=12,api_attempts=32)


class Ledger(SessionLedger):
    def __init__(self,directory=OUT/'session',max_attempts=900,max_episodes=57):
        # New explicit study policy; reuse the tested file locks/circuit breaker,
        # without altering the phase2/phase3 ceilings or their session files.
        self.directory=directory;self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/'session_budget.json'
        self.policy=VERSION;self.ceilings=(900,57)
        self.max_attempts=min(max_attempts,900);self.max_episodes=min(max_episodes,57)


def view(adapter,history,prior):
    s=adapter.sample;state=adapter.state(history)
    if adapter.family=='study':return state,public_payload(state)
    if adapter.family=='navigation':
        from .navigation_protocol import public_payload as navigation_payload
        value=navigation_payload(s.u0,state,history)
        return value,value
    from .task6_protocol import payload
    value=payload(s.u0,state,history)
    if s.template_id in MEMORY:
        from .memory_dev_public import serialize
        value=serialize(value,prior)
    prior.append(copy.deepcopy(state))
    return value,value


def components(template,method,deepseek,jev,threshold=.5):
    if template in STUDY:
        from .study_agents import components as factory
    elif template=='find_and_approach':
        from .navigation_agents import components as factory
    elif template in MEMORY:
        from .gate_ready_dev import components as factory
    else:
        from .task6_agents import components as factory
    return factory(method,deepseek,jev,threshold)


def oracle_one(sample_id):
    from .task6_protocol import payload,scripted_next
    from .study_evaluator import expected_targets
    s=next(s for s in load() if s.sample_id==sample_id)
    dest=OUT/'oracle'/sample_id;dest.mkdir(parents=True,exist_ok=False)
    a=None;actions=[];proposals=[];error=None;start=time.monotonic()
    try:
        # Oracle alone may disclose truth. The ORIGINAL sample is scored.
        oracle=replace(s,initial_disclosed_slots=list(s.slots))
        a=Adapter(oracle);a.world.render().save(dest/'scene.png')
        initial=a.state([])
        initial=initial.observation if a.family=='study' else initial
        for _ in range(12):
            if a.family=='study':
                targets=expected_targets(s,a.world)
                roles=['block','cup'] if s.dag['order']=='block_first' else ['cup','block']
                plan=[dict(kind='pick_place',object_id=s.theta_star[r+'_choice'],target_id=targets[r],relation='inside') for r in roles]
                if s.template_id=='pack_and_cover':plan.append(dict(kind='cover',object_id=s.theta_star['lid_choice'],target_id='box'))
                proposed=plan[len(actions)] if len(actions)<len(plan) else dict(kind='DONE')
            elif a.family=='navigation':
                proposed=dict(kind='search',location_id=s.target_location) if not actions else dict(kind='DONE')
            else:proposed=scripted_next(payload(s.u0,a.world.observation(),[]))
            if proposed['kind']=='DONE':break
            proposals.append(proposed);result=a.execute(proposed);actions.append(result)
            if not result['success']:break
        score=a.score(0,actions,'offline_physical_oracle')
        a.world.render().save(dest/'final.png')
        trace=dict(evidence_kind='deterministic_oracle_real_pybullet',sample_id=s.sample_id,group_id=s.group_id,
            partition=s.partition,template_id=s.template_id,initial_observation=initial,
            final_observation=a.state([]).observation if a.family=='study' else a.state([]),
            proposed_actions=proposals,actions=actions,execution_log=a.world.events,
            checkpoints=getattr(a.world,'checkpoints',[]),evaluation=score,api_attempts=0)
    except Exception as exc:
        error=repr(exc);score=dict(task_success=False,conditions={})
        trace=dict(error=error,actions=actions,evaluation=score,api_attempts=0)
    finally:
        if a:a.close()
    write(dest/'trace.json',trace)
    row=dict(sample_id=s.sample_id,group_id=s.group_id,template=s.template_id,partition=s.partition,
        unknown_slots=s.unknown_slots,success=score['task_success'],conditions=score['conditions'],
        error=error,actions=len(actions),wall_time_s=time.monotonic()-start)
    print(json.dumps(row),flush=True);return row


def run_oracle():
    (OUT/'oracle').mkdir(parents=True,exist_ok=False)
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        rows=list(pool.map(oracle_one,[s.sample_id for s in load()]))
    result=dict(successes=sum(r['success'] for r in rows),total=len(rows),rows=rows,api_attempts=0)
    write(OUT/'oracle/summary.json',result);return result


def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src/when2ask').glob('*.py'))}


def freeze():
    path=OUT/'manifest.json'
    if path.exists():raise FileExistsError('Never replace an existing experimental freeze')
    samples=load();checks=audit(samples)
    oracle=json.loads((OUT/'oracle/summary.json').read_text())
    if oracle['successes']!=36 or oracle['total']!=36:raise ValueError('Require 36/36 physical oracle successes')
    jobs=[dict(sample_id=s.sample_id,method=m,episode_id=s.sample_id+'__'+m,partition='test')
          for s in samples if s.partition=='test' for m in METHODS]
    random.Random(42781120).shuffle(jobs)
    smoke=[dict(sample_id=sample_id,method=method,episode_id=sample_id+'__'+method,partition='dev')
           for sample_id,method in [('n9_dev_00_1','llm_gate'),('n9_dev_06_1','jev_gate'),('n9_dev_02_1','llm_noask')]]
    from . import study_agents,task6_agents,navigation_agents,gate_ready_dev
    plan=dict(experiment_id=VERSION,status='FROZEN_BEFORE_ONLINE_TEST',created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes=hashes(),dataset_hashes={p:hashlib.sha256((DATA/(p+'.jsonl')).read_bytes()).hexdigest() for p in ('dev','test')},
        audit=checks,oracle_summary_sha256=hashlib.sha256((OUT/'oracle/summary.json').read_bytes()).hexdigest(),
        configuration=Config.load().public_config(),threshold=.5,
        prompt_hashes=dict(study=study_agents.prompt_hashes(),task6=task6_agents.prompt_hashes(),
            memory=gate_ready_dev.prompt_hashes(),navigation=navigation_agents.prompt_hashes()),
        planner_policy='Same family-specific shared planner, public serialization, prompts, skills and evaluator for all three paired methods. Only Gate backend differs. NoAsk skips Gate.',
        planner_profiles=dict(pack_and_cover='shared_task_contract_v3.1',place_into_selected_containers='shared_task_contract_v3.1',
            find_and_approach='navigation_search_dev_v1',category_sorting='six_tasks_dev_v1',inventory_restock='six_tasks_dev_v1',
            patrol_return='six_tasks_dev_v1',buffer_exchange='memory_dev_v6+gate_dev_v7',retrieve_restore='memory_dev_v6+gate_dev_v7',occlusion_inspection='memory_dev_v6+gate_dev_v7'),
        model_parameters=dict(temperature=0,thinking='disabled',action_tokens='160/500/650 by fixed family',gate_tokens=64,question_tokens='300/500 by fixed family'),
        expected_returned_models=dict(deepseek='deepseek-flash',jev='jev-1.14.0'),
        global_limits=dict(episodes=57,authenticated_requests=900,dev_smokes=3,test_episodes=54),
        per_episode_limits=LIMITS,retry_policy='Config retries=1, all attempts count; backend blocks on permanent or three consecutive API errors; HTTP200 schema errors are not outages; no whole-episode retries. Interrupted evidence is retained.',
        unknown_facts='Occlusion code and navigation location are world facts; action can reveal them. Missing information does not automatically imply ASK. No rule changed to increase Jev ASK.',
        navigation_contract='Existing v1 exploratory search, fixed nominal3s reply contract. Simulator answers immediately without physics steps; no real human response-time claim. Map station/furniture layouts vary; wall topology fixed.',
        selection='All 18 new Test cases, two per template, each paired across all methods. Nine-task engineering coverage pilot, NOT completion of the original128-Test or high-powered nine-task study.',
        group_analysis='36 independent declared layout groups; 18 Test groups. No rewritten preferences or aliases counted as extra independent cases. Report per-task n=2 without significance claims.',
        jobs=jobs,smoke_jobs=smoke,run_order_seed=42781120)
    write(path,plan);return plan


def checked():
    plan=json.loads((OUT/'manifest.json').read_text())
    if hashes()!=plan['source_hashes']:raise ValueError('Source changed after experimental freeze')
    if Config.load().public_config()!=plan['configuration']:raise ValueError('Configuration changed after freeze')
    for part,h in plan['dataset_hashes'].items():
        if hashlib.sha256((DATA/(part+'.jsonl')).read_bytes()).hexdigest()!=h:raise ValueError('Frozen data changed')
    return plan


def run_episode(job):
    plan=checked();s=next(s for s in load(job['partition']) if s.sample_id==job['sample_id'])
    dest=OUT/(job['partition']+'_runs')/job['episode_id'];dest.mkdir(parents=True,exist_ok=False)
    ledger=Ledger();ledger.start_episode(job['episode_id']);config=Config.load()
    api=Audit(job['episode_id'],config,path=dest/'api_attempts.jsonl',limit=LIMITS['api_attempts'])
    api.session=SchemaAwareSession(ledger,api)
    gate,planner=components(s.template_id,job['method'],DeepSeekClient(config,api),JevClient(config,api),.5)
    a=None;history=[];prior=[];turns=[];actions=[];burden=0;termination='round_limit';error=None
    start=time.monotonic();score=None;final=None;events=[]
    def models():
        for r in api.records:
            if r.get('returned_model') and r['returned_model']!=plan['expected_returned_models'][r['backend']]:
                raise RuntimeError('returned_model_drift')
    try:
        a=Adapter(s);a.world.render().save(dest/'scene.png')
        for i in range(LIMITS['rounds']):
            api.round=i;state,public=view(a,history,prior)
            turn=dict(round=i,public_payload=public,payload_sha256=digest(public));turns.append(turn)
            decision=gate.decide(state) if gate else None;models()
            turn['gate']=dict(called=gate is not None,decision=decision.decision if decision else 'CONTINUE',p_ask=decision.p_ask if decision else None)
            if hasattr(gate,'last_payload'):turn['gate_payload']=copy.deepcopy(gate.last_payload)
            if turn['gate']['decision']=='ASK':
                if burden>=LIMITS['slot_requests']:termination='slot_request_limit';break
                q=planner.generate_question(state);models()
                if isinstance(q,dict):
                    from .task6_protocol import Question
                    q=Question(q['type'],q['text'],tuple(q['requests']),('target_location',))
                resolver=PreferenceResolver(s.slots,s.theta_star);charge=len(set(resolver.resolve(q).values()))
                if burden+charge>LIMITS['slot_requests']:termination='slot_request_limit';break
                before=a.state(history);before=before.observation if a.family=='study' else before
                response,_=resolver.answer(q)
                after=a.state(history);after=after.observation if a.family=='study' else after
                if before!=after:raise RuntimeError('ASK changed physics')
                burden+=charge
                history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=response)])
                turn.update(question=q.to_dict(),user_answer=response,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
            else:
                action=planner.generate_action(state);models()
                action=action.to_dict() if hasattr(action,'to_dict') else action
                turn['action']=action
                if hasattr(planner,'last_model_plan'):turn['model_plan']=copy.deepcopy(planner.last_model_plan)
                if action['kind']=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
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
        episode=dict(experiment_id=VERSION,evidence_kind='real_api_real_pybullet',partition=s.partition,
            sample_id=s.sample_id,group_id=s.group_id,template_id=s.template_id,method=job['method'],scene_seed=s.scene_seed,
            instruction=s.u0,unknown_slots=s.unknown_slots,turns=turns,actions=actions,public_history=history,
            evaluation=score,termination_reason=termination,error=error,cost=api.summary(),wall_time_s=time.monotonic()-start,
            final_observation=final,execution_log=events,configuration=config.public_config(),manifest_sha256=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest())
        write(dest/'episode.json',config.sanitize(episode));write(dest/'evaluation.json',score)
    row=dict(episode_id=job['episode_id'],sample_id=s.sample_id,template=s.template_id,method=job['method'],
        success=score['task_success'] if score else None,burden=burden,actions=len(actions),termination=termination,
        attempts=len(api.records),error=error)
    print(json.dumps(row),flush=True);return row


def run_all(live=False,smoke=False):
    if not live:raise ValueError('Explicit --live flag required')
    plan=checked();jobs=plan['smoke_jobs'] if smoke else plan['jobs']
    if not smoke:
        previous=json.loads((OUT/'smoke_summary.json').read_text())
        if len(previous['rows'])!=3 or any(r.get('error') for r in previous['rows']):raise ValueError('Dev smoke errors require a new version before Test')
    target=OUT/('dev_runs' if smoke else 'test_runs');target.mkdir(exist_ok=False)
    rows=[]
    # Interleaved preregistered order; separate processes isolate Bullet clients/maps.
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        # map preserves the frozen launch order, while workers execute independently.
        for row in pool.map(run_episode,jobs,chunksize=1):
            rows.append(row)
            write(OUT/('smoke_progress.json' if smoke else 'test_progress.json'),dict(rows=rows,session=Ledger().snapshot()))
    result=dict(planned=len(jobs),completed=len(rows),rows=rows,session=Ledger().snapshot())
    write(OUT/('smoke_summary.json' if smoke else 'test_summary.json'),result);return result
