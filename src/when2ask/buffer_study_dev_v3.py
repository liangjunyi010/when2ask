"""Recorded Dev amendment after v2 probes, before any end-to-end episode."""
import copy
import json
import random
import time
from dataclasses import asdict,replace

from .buffer_study_dev import OUT as V2OUT,ORIGINAL,write,digest,session,cases,sample_for,source_hashes
from .buffer_planner_dev import Profile,Planner,components
from .buffer_context_dev_v3 import CompactProfile,VERSION
from .buffer_public_dev import diagnose_action
from .config import ROOT,Config

OUT=ROOT/'outputs/buffer_dev_v3'


def hashes():
    return {**source_hashes(),**{name:digest(ROOT/'src/when2ask'/name) for name in ('buffer_context_dev_v3.py','buffer_study_dev_v3.py')}}


def amendment():
    if (OUT/'amendment.json').exists():raise FileExistsError('Amendment already locked')
    state=session().snapshot()
    if state['episodes']!=0:raise ValueError('Cannot amend end-to-end candidates after observing episode results')
    evidence=json.loads((V2OUT/'probe_summary.json').read_text())
    jobs=cases()
    for job in jobs:
        job['original_control_id']=job['case_id']
        job['case_id']=job['case_id'].replace('_v2_','_v3_')
        job['compact_context']=job['summary']
    random.Random(427813).shuffle(jobs)
    probes=[dict(round=r,planner_repair=p) for r in (2,4,7,9) for p in (False,True)]
    random.Random(427814).shuffle(probes)
    result=dict(version=VERSION,reason='V2 append-only summaries did not fix long-history regression; planner wording fixed round 2 but not round 7. Test context compression as a separate adaptive Dev candidate.',
        v2_plan_sha256=digest(V2OUT/'preregistration.json'),v2_probe_summary_sha256=digest(V2OUT/'probe_summary.json'),
        amendment_before_any_complete_episode=True,session_state_before_amendment=state,
        adaptation_notice='V3 is informed by V2 Dev probes; it is not a blinded pre-registered confirmatory ablation.',
        source_hashes=hashes(),configuration=Config.load().public_config(),
        budgets=dict(shared_total_authenticated_attempts=120,complete_episodes=6,additional_action_probes=8),
        probe_jobs=probes,episode_jobs=jobs,default_console_unchanged=True)
    write(OUT/'amendment.json',result);return result


def checked():
    plan=json.loads((OUT/'amendment.json').read_text())
    if plan['source_hashes']!=hashes() or plan['configuration']!=Config.load().public_config():raise ValueError('Changed source/configuration after Dev v3 lock')
    return plan


def probes():
    from .accounting import Audit
    from .api import DeepSeekClient
    plan=checked();dest=OUT/'probes'
    if dest.exists():raise FileExistsError('Do not rerun paid probes')
    dest.mkdir(parents=True);source=json.loads((ORIGINAL/'episode.json').read_text());rows=[];config=Config.load()
    for job in plan['probe_jobs']:
        profile=CompactProfile(True,job['planner_repair']);key=f"round{job['round']:02d}_{profile.name}"
        audit=Audit('buffer_v3_probe_'+key,config,session(),dest/(key+'.api.jsonl'),2);audit.round=job['round']
        public=copy.deepcopy(source['turns'][job['round']]['public_payload']);model=profile.serialize(public);proposed=None;error=None
        try:proposed=Planner(DeepSeekClient(config,audit),profile).generate_action(model,stage='action_probe')
        except Exception as exc:error=config.sanitize(str(exc))
        row=dict(evidence_kind='real_api_action_probe_no_physics',round=job['round'],profile_id=profile.name,action=proposed,error=error,
            public_payload=public,model_payload=model,diagnostics=diagnose_action(public,proposed),cost=audit.summary())
        write(dest/(key+'.json'),row);rows.append({k:v for k,v in row.items() if k not in ('public_payload','model_payload')});print(json.dumps(rows[-1]),flush=True)
        if session().snapshot()['backends'].get('deepseek',{}).get('blocked'):break
    write(OUT/'probe_summary.json',dict(scope='Adaptive Dev context-compression probes; no physics and no episode success claim',rows=rows));return rows


def run_episode(job):
    """Same physical loop/budgets/evaluator as v2, explicit profile injection."""
    from .accounting import Audit
    from .api import DeepSeekClient,JevClient
    from .task6_protocol import payload,action
    from .task6_world import make_world
    from .task6_evaluator import evaluate
    from .user_simulator import PreferenceResolver
    from .recording import Recorder
    profile=CompactProfile(job['summary'],job['planner_repair']) if job['compact_context'] else Profile(False,False)
    sample=sample_for(job);sample=replace(sample,sample_id=sample.sample_id.replace('buffer_dev_v2','buffer_dev_v3'))
    dest=OUT/'episodes'/job['case_id'];dest.mkdir(parents=True,exist_ok=False);config=Config.load()
    session().start_episode(job['case_id']);audit=Audit(job['case_id'],config,session(),dest/'api_attempts.jsonl',32)
    gate,planner=components(job['method'],DeepSeekClient(config,audit),JevClient(config,audit),config.threshold,profile)
    history=[];turns=[];actions=[];burden=0;termination='round_limit';error=None;world=None;recorder=None;start=time.perf_counter();evaluation=None
    try:
        world=make_world(sample);world.render().save(dest/'scene.png');recorder=Recorder(world,stride=48);recorder.capture();world.frame_callback=recorder.on_step
        for index in range(20):
            audit.round=index;public=payload(sample.u0,world.observation(),history);model=profile.serialize(public)
            turn=dict(round=index,public_payload=public,model_payload=model);turns.append(turn)
            result=gate.decide(model) if gate else None
            turn['gate']=dict(decision=result.decision if result else 'CONTINUE',p_ask=result.p_ask if result else None,called=gate is not None)
            if turn['gate']['decision']=='ASK':
                if burden>=12:termination='slot_request_limit';break
                q=planner.generate_question(model);resolver=PreferenceResolver(sample.slots,sample.theta_star)
                charge=len(set(resolver.resolve(q).values()))
                if burden+charge>12:termination='slot_request_limit';break
                before=world.observation();answer,_=resolver.answer(q);after=world.observation()
                if before!=after:raise RuntimeError('ASK advanced physics')
                burden+=charge;history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=answer)])
                turn.update(question=q.to_dict(),user_answer=answer,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
                recorder.label='ASK '+q.text[:65];recorder.capture(1000);recorder.label='USER '+str(answer);recorder.capture(1000)
            else:
                proposed=action(planner.generate_action(model),public);turn['action']=proposed;turn['public_diagnostics']=diagnose_action(public,proposed)
                if proposed['kind']=='DONE':termination='done';break
                if len(actions)>=12:termination='robot_action_limit';break
                recorder.label=proposed['kind']+' '+str(proposed.get('object_id',''))+' '+str(proposed.get('target_id',''))
                physical=world.execute(proposed);actions.append(physical);turn['physical_result']=physical;history.append(dict(kind='action',result=physical))
    except Exception as exc:termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        if world:
            world.frame_callback=None;evaluation=evaluate(world,sample,burden=burden,actions=actions,termination=termination)
            world.render().save(dest/'final.png');recorder.label='FINAL success='+str(evaluation['task_success']);recorder.capture(1200);recording=recorder.save(dest/'demo.gif')
            final=world.observation();events=world.events;checkpoints=world.checkpoints;world.close()
        else:recording=None;final=None;events=[];checkpoints=[]
        episode=dict(version=VERSION,evidence_kind='real_api_and_real_physics',case=job,profile_id=profile.name,
            prompt_hashes=profile.hashes(),configuration=config.public_config(),sample_id=sample.sample_id,group_id=sample.group_id,instruction=sample.u0,
            turns=turns,actions=actions,public_history=history,evaluation=evaluation,termination_reason=termination,error=error,cost=audit.summary(),
            final_observation=final,execution_log=events,checkpoints=checkpoints,recording=recording,wall_time_s=time.perf_counter()-start,
            physical_swap_complete=bool(evaluation and all(evaluation['conditions'][k] for k in ('items_exchanged','buffers_empty_at_end','robot_released','capacity_respected'))))
        write(dest/'episode.json',config.sanitize(episode));write(dest/'evaluation.json',evaluation)
    row=dict(case_id=job['case_id'],method=job['method'],profile=profile.name,physical_swap_complete=episode['physical_swap_complete'],
        task_success=evaluation['task_success'] if evaluation else None,burden=burden,actions=len(actions),termination_reason=termination,cost=audit.summary(),error=error)
    print(json.dumps(row),flush=True);return row


def episodes():
    plan=checked()
    if (OUT/'episodes').exists():raise FileExistsError('Do not repeat paid episodes')
    rows=[]
    for job in plan['episode_jobs']:
        if session().snapshot()['backends'].get('deepseek',{}).get('blocked'):break
        rows.append(run_episode(job))
    write(OUT/'episode_summary.json',dict(scope='Six end-to-end cases, one shared physical group; only unknown-back methods are matched',rows=rows));return rows
