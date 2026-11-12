"""Isolated Dev diagnostics/paired regressions. Never runs or edits frozen Test."""
from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import random
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace

from .accounting import Audit, SessionLedger
from .api import DeepSeekClient, JevClient
from .config import ROOT, Config
from .grounded_dev_health import SchemaAwareSession
from .nine_task_data import Case, load as load_original, digest, write
from .nine_task_world import Adapter
from .protocol import public_payload
from .study_data import instruction, dag_for
from .study_evaluator import expected_targets
from .study_protocol import StudyQuestion, disclosed_choices
from .task import PublicState
from .tabletop_dev_agents import VERSION, PROFILES, SELECTED, components
from .user_simulator import PreferenceResolver

DATA=ROOT/'data'/VERSION
OUT=ROOT/'outputs'/VERSION
METHODS=('llm_noask','llm_gate','jev_gate')


def ledger():return SessionLedger(OUT/'session',450,24,policy='phase3_dev')


def load():
    values=json.loads((DATA/'samples.json').read_text())['cases']
    samples=[Case(**r['sample']).validate() for r in values]
    if any(s.partition!='dev' for s in samples):raise ValueError('This repair study permits Dev only')
    return samples


def generate():
    if DATA.exists():raise FileExistsError('Do not overwrite an independent Dev version')
    definitions=[('pack_block_first','n9_dev_00_0','block_first',('cup','lid')),
        ('pack_continue_known_cup','n9_dev_00_1','independent',('cup',)),
        ('containers_block_first','n9_dev_01_0','block_first',('cup','block')),
        ('containers_all_known','n9_dev_01_1','cup_first',('cup','block','cup_destination'))]
    original={s.sample_id:s for s in load_original('dev')};rows=[]
    for i,(name,source,order,known) in enumerate(definitions):
        old=original[source];theta={}
        for j,(slot,record) in enumerate(old.slots.items()):
            theta[slot]=record['candidate_ids'][(i+j)%len(record['candidate_ids'])]
        disclosed=[slot for slot,r in old.slots.items() if r['public_role'] in known]
        u0=instruction(old.template_id,order,i)
        for slot in disclosed:u0+=f" For the {old.slots[slot]['public_role']}, use {theta[slot]}."
        case=replace(old,sample_id='td1_'+name,u0=u0,dag=dag_for(old.template_id,order),
                     theta_star=theta,initial_disclosed_slots=disclosed).validate()
        rows.append(dict(condition=name,source_dev_sample=source,sample=asdict(case)))
    value=dict(study_version=VERSION,partition='dev_only',cases=rows,
        policy='Reuses FOUR existing Dev physical layout groups, with fresh preference/order/disclosure variants. No Test reset, retest or new held-out claim.',
        known_scope='Earlier nine-task Test failures inform the repair motivation only; all paid diagnostics and paired runs use these Dev cases.')
    write(DATA/'samples.json',value);return value


def oracle_and_states():
    dest=OUT/'oracle';dest.mkdir(parents=True,exist_ok=False)
    states=[];rows=[]
    expected_gate={'td1_pack_block_first':'ASK','td1_pack_continue_known_cup':'CONTINUE',
        'td1_containers_block_first':'ASK','td1_containers_all_known':'CONTINUE'}
    for s in load():
        a=Adapter(s);history=[];actions=[];initial=a.state(history)
        a.world.render().save(dest/(s.sample_id+'_initial.png'))
        states.append(dict(id=s.sample_id+'_initial',sample_id=s.sample_id,kind='initial',
            state=asdict(initial),expected_gate=expected_gate[s.sample_id],expected_action=None,
            annotation='Public instruction, disclosed roles and prerequisite order; reference is NOT supplied to any model.'))
        missing=[r['public_role'] for k,r in s.slots.items() if k not in s.initial_disclosed_slots]
        if missing:
            q=StudyQuestion.parse(dict(type='select',text='Which task choices should be used?',
                requests=[dict(role=r,candidate_ids=next(v['candidate_ids'] for v in s.slots.values() if v['public_role']==r)) for r in missing]),initial)
            before=a.world.snapshot();answer,_=PreferenceResolver(s.slots,s.theta_star).answer(q)
            assert a.world.snapshot()==before
            history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=answer)])
        targets=expected_targets(s,a.world)
        roles=['block','cup'] if s.dag['order']=='block_first' else ['cup','block']
        for role in roles:
            proposed=dict(kind='pick_place',object_id=s.theta_star[role+'_choice'],target_id=targets[role],relation='inside')
            result=a.execute(proposed);actions.append(result);history.append(dict(kind='action',result=result))
            if s.sample_id=='td1_containers_block_first' and len(actions)==1:
                state=a.state(history)
                states.append(dict(id=s.sample_id+'_after_correct_block',sample_id=s.sample_id,kind='preserve_progress',state=asdict(state),
                    expected_gate='CONTINUE',expected_action=dict(kind='pick_place',object_id=s.theta_star['cup_choice'],target_id=targets['cup'],relation='inside'),
                    annotation='Chosen block is measured in the OTHER container; remaining known cup placement. Reference withheld from models.'))
                a.world.render().save(dest/(s.sample_id+'_after_correct_block.png'))
        if s.template_id=='pack_and_cover':
            result=a.execute(dict(kind='cover',object_id=s.theta_star['lid_choice'],target_id='box'))
            actions.append(result);history.append(dict(kind='action',result=result))
        score=a.score(0,actions,'offline_dev_oracle')
        if s.sample_id=='td1_containers_block_first':
            states.append(dict(id=s.sample_id+'_complete',sample_id=s.sample_id,kind='complete',state=asdict(a.state(history)),
                expected_gate='CONTINUE',expected_action=dict(kind='DONE'),
                annotation='All requested physical relations observed; DONE reference withheld from models.'))
        write(dest/(s.sample_id+'.json'),dict(sample_id=s.sample_id,group_id=s.group_id,partition='dev',
            evidence='real_pybullet_deterministic_oracle',actions=actions,evaluation=score,execution_log=a.world.events,api_attempts=0))
        a.world.render().save(dest/(s.sample_id+'_final.png'));a.close()
        rows.append(dict(sample_id=s.sample_id,success=score['task_success']))
    write(OUT/'diagnostic_states.json',dict(states=states,api_attempts=0,
        caution='References are public-rule diagnostic annotations, not a universal optimal timing score. Stored separately and stripped from all API inputs.'))
    result=dict(successes=sum(r['success'] for r in rows),total=len(rows),rows=rows)
    write(dest/'summary.json',result);return result


def forensic():
    out=[]
    for sid in ('n9_test_00_0','n9_test_01_0'):
        for method in ('llm_gate','jev_gate'):
            source=ROOT/'outputs/nine_task_v1/test_runs'/(sid+'__'+method)/'episode.json'
            e=json.loads(source.read_text());turns=e['turns'];first=turns[0]
            row=dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                sample_id=sid,method=method,instruction=e['instruction'],initial_gate=first['gate'],
                physical_action_failures=sum(not a['success'] for a in e['actions']),termination=e['termination_reason'])
            if sid=='n9_test_00_0':
                state=PublicState.build({**first['public_payload']['observation'],
                    'objects':{o['object_id']:o for o in first['public_payload']['observation']['objects']}},[],e['instruction'])
                row.update(confirmed_initial_choices=disclosed_choices(state),public_order='block_before_cup',
                    unknown_required_role='block',observed_problem='Both gates continued before an unresolved required predecessor; the planner guessed a wrong block. No motion failure.',
                    interpretation='Model decision error under the explicit original contract. Lack of a concise known/unknown/order view is a repair hypothesis, not proof of internal model reasoning.')
            else:
                t=turns[2];pub=t['public_payload'];previous=turns[1]['physical_result']
                row.update(correct_answer_present=pub['history'][1],previous_successful_placement=previous,
                    measured_containment_before_removal=pub['observation']['spatial_relations']['inside_containers'],
                    undo_action=t['action'],
                    observed_problem='Answer, successful block action and measured partial goal are present; planner removes the already-correct block and cycles.',
                    interpretation='No evidence of missing public history or physical failure; candidate causes are role/destination binding and failure to preserve a partial goal. Internal reasoning is unobserved.')
            out.append(row)
    value=dict(evidence='Read-only analysis of historical Test; NOT a new held-out test or any API replay.',cases=out,
        prior_demo_difference='Phase2 pack demo has a known cup with no block-before-cup edge. The current packing failure adds a blocked known later subgoal. Phase3 selected-container video places cup first in an independent-order task; current failure is block-first and destination-dependent.',
        confounds='Previous success on a layout/goal ordering never proves robust performance for new aliases, disclosures and DAG constraints.')
    write(OUT/'forensics.json',value);return value


def freeze():
    target=OUT/'manifest.json'
    if target.exists():raise FileExistsError('Never overwrite this Dev protocol')
    oracle=json.loads((OUT/'oracle/summary.json').read_text())
    if oracle['successes']!=4:raise ValueError('All four Dev cases must pass physical oracle')
    states=json.loads((OUT/'diagnostic_states.json').read_text())['states']
    probes=[]
    for state in states:
        for profile in PROFILES:
            for method in ('llm_gate','jev_gate'):
                probes.append(dict(id=state['id']+'__'+profile+'__'+method,stage='gate',state_id=state['id'],profile=profile,method=method))
            if state['expected_action']:
                probes.append(dict(id=state['id']+'__'+profile+'__planner',stage='action',state_id=state['id'],profile=profile,method='llm_noask'))
    jobs=[dict(sample_id=s.sample_id,profile=profile,method=method,episode_id=s.sample_id+'__'+profile+'__'+method)
        for s in load() for profile in ('raw_legacy',SELECTED) for method in METHODS]
    rng=random.Random(42781121);rng.shuffle(probes);rng.shuffle(jobs)
    source_paths=list((ROOT/'src/when2ask').glob('*.py'))
    value=dict(study_version=VERSION,status='DEV_PROTOCOL_LOCKED_BEFORE_PAID_CALLS',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        data_sha256=hashlib.sha256((DATA/'samples.json').read_bytes()).hexdigest(),
        states_sha256=hashlib.sha256((OUT/'diagnostic_states.json').read_bytes()).hexdigest(),
        config=Config.load().public_config(),profile_hashes={k:p.hashes() for k,p in PROFILES.items()},
        selected_profile=SELECTED,selection_policy='Both public facts and contract addendum fixed before diagnostics; no data-driven threshold change or winner selection. All four diagnostic factors reported.',
        threshold=.5,expected_returned_models=dict(deepseek='deepseek-flash',jev='jev-1.14.0'),
        design='2x2 representation(raw/facts) x prompt(legacy/clarified). Six Dev states x two gates x four factors =48 Gate probes; two states x four factors =8 Planner probes. No private references sent to APIs.',
        global_limits=dict(authenticated_requests=450,full_episodes=24),per_episode_limits=dict(rounds=20,actions=12,slots=12,api_attempts=32),
        planner_parameters=dict(temperature=0,thinking='disabled',max_tokens=500),gate_max_tokens=64,
        retry_policy='One attempt retry including schema repair. Every request charged to one persistent ledger. Permanent errors or three consecutive API errors block backend; no episode reruns. Unknown usage remains null.',
        partition='DEV_ONLY; previously examined Test failures are not claimed as a new held-out evaluation',
        probes=probes,jobs=jobs,run_order_seed=42781121)
    write(target,value);return value


def checked():
    plan=json.loads((OUT/'manifest.json').read_text())
    if Config.load().public_config()!=plan['config']:raise ValueError('Dev model config changed')
    for file,h in plan['source_hashes'].items():
        if hashlib.sha256((ROOT/file).read_bytes()).hexdigest()!=h:raise ValueError('Dev source changed: '+file)
    for path,key in [(DATA/'samples.json','data_sha256'),(OUT/'diagnostic_states.json','states_sha256')]:
        if hashlib.sha256(path.read_bytes()).hexdigest()!=plan[key]:raise ValueError('Dev data/state changed')
    return plan


def model_check(api,plan):
    for r in api.records:
        if r.get('returned_model') and r['returned_model']!=plan['expected_returned_models'][r['backend']]:raise RuntimeError('returned_model_drift')


def clients(id,path,limit):
    config=Config.load();api=Audit(id,config,path=path,limit=limit)
    api.session=SchemaAwareSession(ledger(),api)
    return config,api,DeepSeekClient(config,api),JevClient(config,api)


def probe(job):
    plan=checked();s=next(s for s in json.loads((OUT/'diagnostic_states.json').read_text())['states'] if s['id']==job['state_id'])
    raw=s['state'];state=PublicState.build(raw['observation'],raw['history'],raw['instruction'])
    dest=OUT/'probes'/job['id'];dest.mkdir(parents=True,exist_ok=False)
    config,api,deepseek,jev=clients(job['id'],dest/'api_attempts.jsonl',4)
    gate,planner=components(job['method'],deepseek,jev,job['profile'],.5)
    result=None;error=None
    try:
        proposed=gate.decide(state) if job['stage']=='gate' else planner.generate_action(state)
        model_check(api,plan)
        result=dict(decision=proposed.decision,p_ask=proposed.p_ask) if job['stage']=='gate' else proposed.to_dict()
    except Exception as exc:error=config.sanitize(str(exc))
    expected=s['expected_gate'] if job['stage']=='gate' else s['expected_action']
    match=(result is not None and (result['decision']==expected if job['stage']=='gate' else
        all(result.get(k)==v for k,v in expected.items())))
    row=dict(**job,reference=expected,output=result,match=match,error=error,cost=api.summary(),
        public_payload=PROFILES[job['profile']].serialize(state),evidence_kind='real_api_fixed_dev_state_probe')
    write(dest/'result.json',config.sanitize(row));print(json.dumps(dict(id=job['id'],match=match,error=error)),flush=True);return row


def episode(job):
    plan=checked();s=next(s for s in load() if s.sample_id==job['sample_id'])
    dest=OUT/'episodes'/job['episode_id'];dest.mkdir(parents=True,exist_ok=False)
    ledger().start_episode(job['episode_id']);config,api,deepseek,jev=clients(job['episode_id'],dest/'api_attempts.jsonl',32)
    gate,planner=components(job['method'],deepseek,jev,job['profile'],.5)
    a=None;history=[];turns=[];actions=[];burden=0;termination='round_limit';error=None;score=None;final=None;events=[]
    start=time.monotonic()
    try:
        a=Adapter(s);a.world.render().save(dest/'scene.png')
        for i in range(20):
            api.round=i;state=a.state(history);public=PROFILES[job['profile']].serialize(state)
            turn=dict(round=i,public_payload=public,payload_sha256=digest(public));turns.append(turn)
            result=gate.decide(state) if gate else None;model_check(api,plan)
            turn['gate']=dict(called=gate is not None,decision=result.decision if result else 'CONTINUE',p_ask=result.p_ask if result else None)
            if turn['gate']['decision']=='ASK':
                if burden>=12:termination='slot_request_limit';break
                q=planner.generate_question(state);model_check(api,plan)
                resolver=PreferenceResolver(s.slots,s.theta_star);charge=len(set(resolver.resolve(q).values()))
                if burden+charge>12:termination='slot_request_limit';break
                before=a.world.snapshot();answer,_=resolver.answer(q);after=a.world.snapshot()
                if before!=after:raise RuntimeError('ASK changed physics')
                burden+=charge;history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=answer)])
                turn.update(question=q.to_dict(),user_answer=answer,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
            else:
                proposed=planner.generate_action(state);model_check(api,plan);turn['action']=proposed.to_dict()
                if proposed.kind=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
                if len(actions)>=12:termination='robot_action_limit';break
                result=a.execute(proposed.to_dict());actions.append(result);history.append(dict(kind='action',result=result));turn['physical_result']=copy.deepcopy(result)
    except Exception as exc:termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        if a:
            try:
                score=a.score(burden,actions,termination);a.world.render().save(dest/'final.png')
                final=a.state(history).observation;events=copy.deepcopy(a.world.events)
            finally:a.close()
        row=dict(**job,study_version=VERSION,evidence_kind='real_api_real_pybullet_dev_regression',partition='dev',
            group_id=s.group_id,template_id=s.template_id,instruction=s.u0,turns=turns,actions=actions,public_history=history,
            evaluation=score,termination_reason=termination,error=error,cost=api.summary(),wall_time_s=time.monotonic()-start,
            final_observation=final,execution_log=events,configuration=config.public_config())
        write(dest/'episode.json',config.sanitize(row));write(dest/'evaluation.json',score)
    print(json.dumps(dict(episode_id=job['episode_id'],success=score['task_success'] if score else None,burden=burden,actions=len(actions),termination=termination,error=error)),flush=True)
    return dict(episode_id=job['episode_id'],success=score['task_success'] if score else None,error=error)


def run(kind,live=False):
    if not live:raise ValueError('Explicit --live required; offline tests never call a paid API')
    plan=checked();target=OUT/('probes' if kind=='probes' else 'episodes');target.mkdir(exist_ok=False)
    jobs=plan['probes' if kind=='probes' else 'jobs'];function=probe if kind=='probes' else episode
    rows=[]
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        for row in pool.map(function,jobs,chunksize=1):
            rows.append(row);write(OUT/(kind+'_progress.json'),dict(completed=len(rows),planned=len(jobs),session=ledger().snapshot()))
    result=dict(completed=len(rows),planned=len(jobs),session=ledger().snapshot())
    write(OUT/(kind+'_summary.json'),result);return result
