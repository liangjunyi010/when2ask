"""Frozen independent v8 Test runner: real APIs and PyBullet, no legacy edits."""
import copy
import hashlib
import json
import multiprocessing
import random
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path

from .config import ROOT,Config
from .accounting import Audit,SessionLedger
from .api import DeepSeekClient,JevClient
from .grounded_dev_health import SchemaAwareSession
from .gate_ready_dev import components,prompt_hashes,configuration
from .memory_dev_public import serialize
from .three_task_data import load,audit_samples,VERSION
from .task6_protocol import payload,action
from .user_simulator import PreferenceResolver

OUT=ROOT/'outputs/three_task_v8'
METHODS=('llm_noask','llm_gate','jev_gate')
LIMITS=dict(rounds=20,robot_actions=12,slot_requests=12,api_attempts=32)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def ledger():return SessionLedger(OUT/'session',450,36,policy='phase3_dev')


def freeze(revision='r2'):
    target=OUT/'frozen_manifest.json'
    if target.exists():raise FileExistsError('Do not replace a frozen benchmark protocol')
    samples=load(revision);audit=audit_samples(samples);oracle=json.loads((OUT/('oracle_'+revision)/'summary.json').read_text())
    if oracle['successes']!=36 or oracle['total']!=36:raise ValueError('Every declared physical sample must pass before freeze')
    test=[s for s in samples if s.partition=='test'];assert len(test)==12 and len({s.group_id for s in test})==12
    recorded={next(s.sample_id for s in test if s.template_id==template and not s.initial_disclosed_slots) for template in {s.template_id for s in test}}
    jobs=[dict(sample_id=s.sample_id,method=m,episode_id=s.sample_id+'__'+m,record=s.sample_id in recorded) for s in test for m in METHODS]
    random.Random(42781115).shuffle(jobs)
    source_paths=list((ROOT/'src/when2ask').glob('*.py'))
    result=dict(experiment_id='three_task_v8_heldout_test_r2',dataset_version=VERSION,revision=revision,status='FROZEN_BEFORE_MODEL_TEST',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        dataset_hashes={p:digest(ROOT/'data/three_task_v8'/revision/(p+'.jsonl')) for p in ['dev','test']},
        audit=audit,oracle_summary_sha256=digest(OUT/('oracle_'+revision)/'summary.json'),
        protocol=dict(gate=configuration(),planner='memory_dev_v6',prompt_hashes=prompt_hashes(),threshold=.5),
        configuration=Config.load().public_config(),expected_returned_models=dict(deepseek='deepseek-flash',jev='jev-1.14.0'),
        source_hashes={str(p.relative_to(ROOT)):digest(p) for p in source_paths},
        jobs=jobs,job_order_seed=42781115,workers=3,recorded_samples=sorted(recorded),
        global_limits=dict(full_episodes=36,all_authenticated_requests=450),per_episode_limits=LIMITS,
        model_parameters=dict(action_max_tokens=650,question_max_tokens=300,deepseek_gate_max_tokens=64,temperature=0,thinking='disabled'),
        failure_policy='One API retry; all attempts count. Same persistent ledger. Genuine backend outages/permanent failures trip breaker; HTTP200 schema errors count but are not outages. No whole-episode retries, prompt/threshold changes or post-outcome sample selection. Returned-model drift aborts episode.',
        test_policy='All12 new Test samples ×3 methods. New physical groups only; old tuned groups excluded. Test oracle was mechanical verification only; no model Test calls before freeze. Dev24 not scored as held-out.',
        known_limits='Three templates, one binary slot/fact each, unknown0/1,12 independent Test layouts; small benchmark, not broad nine-template or original128-Test completion.',
        scoring='Unchanged task6 full geometry/contact/evidence/DAG evaluator; task_success independent of termination/DONE and model ID claims.')
    write(target,result);write(ROOT/'data/three_task_v8'/revision/'freeze.json',dict(experiment_id=result['experiment_id'],dataset_hashes=result['dataset_hashes'],audit=audit,oracle_summary_sha256=result['oracle_summary_sha256'],protocol_sha256=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()))
    return result


def checked():
    plan=json.loads((OUT/'frozen_manifest.json').read_text())
    if plan['configuration']!=Config.load().public_config():raise ValueError('Model configuration changed after freeze')
    if any(digest(ROOT/p)!=d for p,d in plan['source_hashes'].items()):raise ValueError('Source changed after freeze; new experiment version required')
    for part,d in plan['dataset_hashes'].items():
        if digest(ROOT/'data/three_task_v8'/plan['revision']/(part+'.jsonl'))!=d:raise ValueError('Dataset changed after freeze')
    return plan


def run_episode(job):
    from .task6_world import make_world
    from .task6_evaluator import evaluate
    from .recording import Recorder
    plan=checked();sample=next(s for s in load(plan['revision'],'test') if s.sample_id==job['sample_id'])
    dest=OUT/'test_runs'/job['episode_id'];dest.mkdir(parents=True,exist_ok=False)
    session=ledger();session.start_episode(job['episode_id']);config=Config.load();api=Audit(job['episode_id'],config,path=dest/'api_attempts.jsonl',limit=32);api.session=SchemaAwareSession(session,api)
    gate,planner=components(job['method'],DeepSeekClient(config,api),JevClient(config,api),.5)
    history=[];observations=[];turns=[];actions=[];burden=0;world=None;recorder=None;start=time.monotonic();termination='round_limit';error=None;score=None;final=None;events=[];checkpoints=[]
    def models():
        for r in api.records:
            if r.get('returned_model') and r['returned_model']!=plan['expected_returned_models'][r['backend']]:raise RuntimeError('returned_model_drift')
    try:
        world=make_world(sample);world.render().save(dest/'scene.png')
        if job['record']:
            recorder=Recorder(world,stride=72);recorder.capture();world.frame_callback=recorder.on_step
        for index in range(20):
            api.round=index;raw=payload(sample.u0,world.observation(),history);public=serialize(raw,observations);observations.append(copy.deepcopy(raw['observation']))
            turn=dict(round=index,raw_public_payload=raw,public_payload=public,payload_sha256=hashlib.sha256(json.dumps(public,sort_keys=True).encode()).hexdigest());turns.append(turn)
            decision=gate.decide(public) if gate else None;models()
            turn['gate']=dict(called=gate is not None,decision=decision.decision if decision else 'CONTINUE',p_ask=decision.p_ask if decision else None)
            if gate:turn['gate_payload']=copy.deepcopy(gate.last_payload)
            if turn['gate']['decision']=='ASK':
                if burden>=12:termination='slot_request_limit';break
                q=planner.generate_question(public);models();resolver=PreferenceResolver(sample.slots,sample.theta_star);charge=len(set(resolver.resolve(q).values()))
                if burden+charge>12:termination='slot_request_limit';break
                before=world.observation();response,_=resolver.answer(q);after=world.observation()
                if before!=after:raise RuntimeError('ASK changed physics')
                burden+=charge;history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=response)])
                turn.update(question=q.to_dict(),user_answer=response,ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
                if recorder:
                    recorder.label='ASK '+q.text[:65];recorder.capture(1000);recorder.label='USER '+str(response);recorder.capture(1000)
            else:
                proposed=action(planner.generate_action(public),public);models();turn['action']=proposed;turn['model_plan']=copy.deepcopy(planner.last_model_plan)
                if proposed['kind']=='DONE':
                    if api.records:api.records[-1]['completion_kind']='DONE';api.flush()
                    termination='done';break
                if len(actions)>=12:termination='robot_action_limit';break
                if recorder:recorder.label=proposed['kind']+' '+str(proposed.get('object_id',proposed.get('code','')))
                physical=world.execute(proposed);actions.append(physical);history.append(dict(kind='action',result=physical));turn['physical_result']=copy.deepcopy(physical)
                if recorder:recorder.capture()
    except Exception as exc:termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        recording=None
        if world:
            world.frame_callback=None;score=evaluate(world,sample,burden=burden,actions=actions,termination=termination)
            world.render().save(dest/'final.png');final=world.observation();events=copy.deepcopy(world.events);checkpoints=copy.deepcopy(world.checkpoints)
            if recorder:
                recorder.label='FINAL success='+str(score['task_success']);recorder.capture(1200);recording=recorder.save(dest/'demo.gif')
            world.close()
        episode=dict(experiment_id=plan['experiment_id'],evidence_kind='real_api_real_pybullet_heldout_test',dataset_version=VERSION,
            sample_id=sample.sample_id,group_id=sample.group_id,partition=sample.partition,task_template=sample.template_id,method=job['method'],
            scene_seed=sample.scene_seed,instruction=sample.u0,unknown_slots=1-len(sample.initial_disclosed_slots),
            protocol=plan['protocol'],configuration=config.public_config(),source_commit=plan['code_commit'],
            turns=turns,actions=actions,public_history=history,evaluation=score,termination_reason=termination,error=error,
            cost=api.summary(),wall_time_s=time.monotonic()-start,final_observation=final,execution_log=events,checkpoints=checkpoints,recording=recording)
        write(dest/'episode.json',config.sanitize(episode));write(dest/'evaluation.json',score)
    row=dict(episode_id=job['episode_id'],sample_id=sample.sample_id,group_id=sample.group_id,template=sample.template_id,method=job['method'],
        success=score['task_success'] if score else None,burden=burden,actions=len(actions),termination=termination,error=error,attempts=api.summary()['api_attempts'])
    print(json.dumps(row),flush=True);return row


def run_all(live=False):
    if not live:raise ValueError('Explicit live flag required')
    plan=checked();(OUT/'test_runs').mkdir(exist_ok=False);jobs=iter(plan['jobs']);rows=[];pending={};state=ledger().snapshot()
    if state['episodes'] or state['attempts']:raise ValueError('Fresh session required; never repeat Test in-place')
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('spawn')) as pool:
        def launch():
            try:job=next(jobs)
            except StopIteration:return False
            pending[pool.submit(run_episode,job)]=job;return True
        for _ in range(3):launch()
        while pending:
            done,_=wait(pending,return_when=FIRST_COMPLETED)
            for future in done:
                job=pending.pop(future)
                try:rows.append(future.result())
                except Exception as exc:rows.append(dict(episode_id=job['episode_id'],error=type(exc).__name__+': '+str(exc),success=None))
                state=ledger().snapshot()
                blocked=any(c.get('blocked') for c in state['backends'].values())
                if not blocked and state['attempts']<450:launch()
                write(OUT/'run_progress.json',dict(completed=len(rows),planned=36,rows=rows,session=state))
    write(OUT/'run_summary.json',dict(completed=len(rows),planned=36,rows=rows,session=ledger().snapshot(),all_jobs_attempted=len(rows)==36))
    return rows
