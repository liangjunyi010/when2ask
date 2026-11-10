"""Bounded independent buffer Dev v2 diagnosis, probes and real physics runs."""
import copy
import hashlib
import json
import random
import subprocess
import time
from collections import Counter
from dataclasses import asdict,replace
from pathlib import Path

from .config import Config,ROOT
from .task6_spec import make_sample,SOURCES
from .task6_protocol import payload,action
from .buffer_planner_dev import Profile,Planner,components,VERSION
from .buffer_public_dev import diagnose_action

OUT=ROOT/'outputs/buffer_dev_v2'
ORIGINAL=ROOT/'outputs/six_tasks_dev_v1/live/buffer_exchange'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze():
    episode=json.loads((ORIGINAL/'episode.json').read_text())
    calls=[json.loads(s) for s in (ORIGINAL/'api_attempts.jsonl').read_text().splitlines()]
    rows=[]
    for turn in episode['turns']:
        request=next(r for r in calls if r['round']==turn['round'])['request']
        serialized=json.loads(request['messages'][1]['content']);public=turn['public_payload']
        obs=public['observation']
        rows.append(dict(round=turn['round'],simulation_step=obs['simulation_step'],
            left=obs['containers']['slot_left']['contents'],right=obs['containers']['slot_right']['contents'],
            front=obs['zones']['buffer_front']['contents'],back=obs['zones']['buffer_back']['contents'],
            history_length=len(public['history']),wire_equals_logged_state=serialized==public,
            planner_output=turn['action'],physical_result=turn.get('physical_result'),
            public_diagnostics=diagnose_action(public,turn['action'])))
    result=dict(original_episode_sha256=digest(ORIGINAL/'episode.json'),
        original_api_log_sha256=digest(ORIGINAL/'api_attempts.jsonl'),
        all_sent_states_match_logged_states=all(r['wire_equals_logged_state'] for r in rows),
        first_regression_round=next(r['round'] for r in rows if r['public_diagnostics']['undoes_currently_satisfied_final_relation']),
        history_was_present=True,rows=rows,
        conclusions=['Round 2 correctly showed B in left slot, A on front buffer and right slot empty, with both successful actions in history.',
          'The actual DeepSeek response moved B back to the right slot; this is a planner decision, not lost history or stale transport state.',
          'V1 affordances enumerate schema-supported destinations, including occupied slots and backward moves; they are not a verified set of currently executable or task-progressing actions.',
          'Initial-location wording, dense raw state and unstated persistence of an agent guess are plausible contributors, not proven internal model reasoning.'],
        unresolved='Factorial action probes and end-to-end controls are needed to assess public summaries versus planner wording.')
    write(OUT/'analysis.json',result);return result


def cases():
    return [dict(case_id='known_back_v1_noask',known=True,truth='buffer_back',method='llm_noask',summary=False,planner_repair=False),
            dict(case_id='known_back_v2_noask',known=True,truth='buffer_back',method='llm_noask',summary=True,planner_repair=True),
            dict(case_id='unknown_back_v2_noask',known=False,truth='buffer_back',method='llm_noask',summary=True,planner_repair=True),
            dict(case_id='unknown_back_v2_llm',known=False,truth='buffer_back',method='llm_gate',summary=True,planner_repair=True),
            dict(case_id='unknown_back_v2_jev',known=False,truth='buffer_back',method='jev_gate',summary=True,planner_repair=True),
            dict(case_id='unknown_front_v2_noask',known=False,truth='buffer_front',method='llm_noask',summary=True,planner_repair=True)]


def sample_for(case):
    sample=make_sample('buffer_exchange',1);theta={'buffer_pad_choice':case['truth']}
    return replace(sample,sample_id='buffer_dev_v2_'+case['case_id'],theta_star=theta,
        initial_disclosed_slots=['buffer_pad_choice'] if case['known'] else [],
        u0=sample.u0+(f" User specifies buffer_pad={case['truth']}." if case['known'] else '')).validate()


def source_hashes():
    package=ROOT/'src/when2ask'
    files=(*SOURCES,'task6_agents.py','buffer_public_dev.py','buffer_planner_dev.py','buffer_study_dev.py','api.py','accounting.py')
    return {f:digest(package/f) for f in files}


def preregister():
    if (OUT/'preregistration.json').exists():raise FileExistsError('Do not replace a locked Dev plan')
    analyze();jobs=[]
    for round_index in (2,4,7,9):
        for summary,repair in ((False,False),(True,False),(False,True),(True,True)):
            jobs.append(dict(round=round_index,summary=summary,planner_repair=repair))
    random.Random(427812).shuffle(jobs);episodes=cases();random.Random(427813).shuffle(episodes)
    plan=dict(version=VERSION,scope='Dev only: one physical group, action probes are not episodes or success-rate evidence',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        original_episode_sha256=digest(ORIGINAL/'episode.json'),original_api_log_sha256=digest(ORIGINAL/'api_attempts.jsonl'),
        configuration=Config.load().public_config(),source_hashes=source_hashes(),
        profile_prompt_hashes={Profile(s,p).name:Profile(s,p).hashes() for s,p in ((False,False),(True,False),(False,True),(True,True))},
        budgets=dict(authenticated_attempts=120,complete_episodes=6,action_probes=16,rounds_per_episode=20,robot_actions=12,slot_requests=12,api_attempts_per_episode=32),
        retry_policy='Existing one request retry, all attempts count; permanent/three-consecutive-error circuit breaker. No episode reruns.',
        probe_interpretation='Same historical states, four crossed summary/prompt profiles. Only proposed-action diagnostics; no claimed counterfactual physical success.',
        probe_jobs=jobs,episode_jobs=episodes,default_console_unchanged=True)
    write(OUT/'preregistration.json',plan)
    write(ROOT/'data/buffer_dev_v2/cases.json',dict(version=VERSION,base_scene_ref='data/six_tasks_dev_v1/samples.json',
        note='All cases share the existing buffer scene; these are controls and matched preferences, not independent scene groups.',cases=cases()))
    return plan


def checked_plan():
    plan=json.loads((OUT/'preregistration.json').read_text())
    if plan['source_hashes']!=source_hashes() or plan['configuration']!=Config.load().public_config():raise ValueError('Code/model configuration changed after preregistration')
    if plan['original_episode_sha256']!=digest(ORIGINAL/'episode.json'):raise ValueError('Original record changed')
    return plan


def session():
    from .accounting import SessionLedger
    return SessionLedger(OUT/'session',120,6)


def probes():
    from .accounting import Audit,BackendBlocked,BudgetExceeded
    from .api import DeepSeekClient
    plan=checked_plan();destination=OUT/'probes'
    if destination.exists():raise FileExistsError('Probe output exists; never silently pay to repeat')
    destination.mkdir();source=json.loads((ORIGINAL/'episode.json').read_text());rows=[];config=Config.load()
    for job in plan['probe_jobs']:
        profile=Profile(job['summary'],job['planner_repair']);key=f"round{job['round']:02d}_{profile.name}"
        audit=Audit('buffer_probe_'+key,config,session(),destination/(key+'.api.jsonl'),limit=2);audit.round=job['round']
        public=copy.deepcopy(source['turns'][job['round']]['public_payload']);model=profile.serialize(public)
        proposed=None;error=None
        try:proposed=Planner(DeepSeekClient(config,audit),profile).generate_action(model,stage='action_probe')
        except Exception as exc:error=config.sanitize(str(exc))
        result=dict(evidence_kind='real_api_action_probe_no_physics',round=job['round'],profile=asdict(profile),profile_id=profile.name,
            public_payload=public,model_payload=model,action=proposed,error=error,
            diagnostics=diagnose_action(public,proposed),cost=audit.summary())
        write(destination/(key+'.json'),result);rows.append({k:v for k,v in result.items() if k not in ('public_payload','model_payload')})
        print(json.dumps(rows[-1]),flush=True)
        if session().snapshot()['backends'].get('deepseek',{}).get('blocked'):break
    result=dict(scope=plan['probe_interpretation'],rows=rows);write(OUT/'probe_summary.json',result);return result


def run_episode(job):
    from .accounting import Audit
    from .api import DeepSeekClient,JevClient
    from .task6_world import make_world
    from .task6_evaluator import evaluate
    from .recording import Recorder
    from .user_simulator import PreferenceResolver
    profile=Profile(job['summary'],job['planner_repair']);sample=sample_for(job);config=Config.load();ledger=session()
    dest=OUT/'episodes'/job['case_id'];dest.mkdir(parents=True,exist_ok=False)
    ledger.start_episode(job['case_id']);audit=Audit(job['case_id'],config,ledger,dest/'api_attempts.jsonl',32)
    gate,planner=components(job['method'],DeepSeekClient(config,audit),JevClient(config,audit),config.threshold,profile)
    history=[];turns=[];actions=[];burden=0;termination='round_limit';error=None;start=time.perf_counter();world=None;recorder=None
    evaluation=None
    try:
        world=make_world(sample);world.render().save(dest/'scene.png');recorder=Recorder(world,stride=48);recorder.capture();world.frame_callback=recorder.on_step
        for index in range(20):
            audit.round=index;public=payload(sample.u0,world.observation(),history);model=profile.serialize(public)
            turn=dict(round=index,public_payload=public,model_payload=model);turns.append(turn)
            decision=gate.decide(model) if gate else None
            turn['gate']=dict(decision=decision.decision if decision else 'CONTINUE',p_ask=decision.p_ask if decision else None,called=gate is not None)
            if turn['gate']['decision']=='ASK':
                if burden>=12:termination='slot_request_limit';break
                q=planner.generate_question(model);resolver=PreferenceResolver(sample.slots,sample.theta_star)
                charge=len(set(resolver.resolve(q).values()))
                if burden+charge>12:termination='slot_request_limit';break
                before=world.observation();response,_=resolver.answer(q);after=world.observation()
                if before!=after:raise RuntimeError('ASK advanced physical state')
                burden+=charge;history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=response)])
                turn.update(question=q.to_dict(),user_answer=response,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
                recorder.label='ASK '+q.text[:65];recorder.capture(1000);recorder.label='USER '+str(response['choices'] if 'choices' in response else response);recorder.capture(1000)
            else:
                proposed=action(planner.generate_action(model),public);turn['action']=proposed;turn['public_diagnostics']=diagnose_action(public,proposed)
                if proposed['kind']=='DONE':termination='done';break
                if len(actions)>=12:termination='robot_action_limit';break
                recorder.label=proposed['kind']+' '+str(proposed.get('object_id',''))+' → '+str(proposed.get('target_id',''))
                physical=world.execute(proposed);actions.append(physical);turn['physical_result']=physical;history.append(dict(kind='action',result=physical))
    except Exception as exc:termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        if world:
            world.frame_callback=None
            evaluation=evaluate(world,sample,burden=burden,actions=actions,termination=termination)
            world.render().save(dest/'final.png');recorder.label='FINAL success='+str(evaluation['task_success']);recorder.capture(1200)
            recording=recorder.save(dest/'demo.gif')
            final=world.observation();events=world.events;checkpoints=world.checkpoints;world.close()
        else:recording=None;final=None;events=[];checkpoints=[]
        episode=dict(version=VERSION,evidence_kind='real_api_and_real_physics',case=job,profile=asdict(profile),
            prompt_hashes=profile.hashes(),configuration=config.public_config(),sample_id=sample.sample_id,group_id=sample.group_id,
            instruction=sample.u0,turns=turns,actions=actions,public_history=history,evaluation=evaluation,
            termination_reason=termination,error=error,cost=audit.summary(),final_observation=final,execution_log=events,checkpoints=checkpoints,
            wall_time_s=time.perf_counter()-start,recording=recording,
            physical_swap_complete=bool(evaluation and all(evaluation['conditions'][key] for key in ('items_exchanged','buffers_empty_at_end','robot_released','capacity_respected'))))
        write(dest/'episode.json',config.sanitize(episode));write(dest/'evaluation.json',evaluation)
    row=dict(case_id=job['case_id'],method=job['method'],profile=profile.name,physical_swap_complete=episode['physical_swap_complete'],
        task_success=evaluation['task_success'] if evaluation else None,burden=burden,actions=len(actions),termination_reason=termination,cost=audit.summary(),error=error)
    print(json.dumps(row),flush=True);return row


def episodes():
    plan=checked_plan()
    if (OUT/'episodes').exists():raise FileExistsError('Episode outputs exist; no silent reruns')
    rows=[]
    for job in plan['episode_jobs']:
        if session().snapshot()['backends'].get('deepseek',{}).get('blocked'):break
        rows.append(run_episode(job))
    result=dict(scope='Six controls/cases in one physical group; only the three unknown-back methods form a matched comparison.',rows=rows)
    write(OUT/'episode_summary.json',result);return result
