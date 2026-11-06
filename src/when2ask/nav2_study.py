"""Preregistered 2x2 gate ablation, then 12 paired episodes, one shared request cap."""
import hashlib
import itertools
import json
import random
import subprocess
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path

from .accounting import Audit,SessionLedger,BudgetExceeded,BackendBlocked
from .api import DeepSeekClient,JevClient
from .config import Config,ROOT
from .navigation_map import LOCATIONS
from .nav2_agents import Gate,hashes
from .nav2_public import payload,reference_values
from .nav2_runner import run_episode,write_json
from .nav2_task import Sample,samples,settings
from .nav2_world import World


class Ledger(SessionLedger):
    def __init__(self,directory,stage):
        cfg=settings()['study_limits'];self.stage=stage
        self.prior_attempts=settings().get('prior_authenticated_requests',0)
        self.stage_limit=cfg['ablation_requests' if stage=='ablation' else 'episode_requests']
        super().__init__(directory,cfg['authenticated_requests']-self.prior_attempts,cfg['online_episodes'])
    def reserve(self,backend):
        with self._state() as state:
            used=state.setdefault('stage_attempts',{}).get(self.stage,0)
            if state['attempts']>=state['max_attempts'] or used>=self.stage_limit:raise BudgetExceeded('nav2_request_limit')
            circuit=state['backends'].get(backend,{})
            if circuit.get('blocked'):raise BackendBlocked(f'{backend}: blocked by circuit breaker')
            state['attempts']+=1;state['stage_attempts'][self.stage]=used+1
            return state['attempts']+self.prior_attempts


def source_hashes():
    files=list((ROOT/'src/when2ask').glob('nav2_*.py'))+[ROOT/'configs/navigation_dev_v2.json']
    files+=[ROOT/'src/when2ask'/name for name in ('navigation_world.py','navigation_map.py','navigation_protocol.py','api.py','accounting.py')]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def prepare(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'plan.json').exists():raise ValueError('Plan exists; refusing to overwrite')
    cfg=settings();rows=samples();write_json(output/'dataset.json',[asdict(s) for s in rows])
    # Target chosen ONCE by declared seed, identical across cost cells: isolates cost factors.
    target=random.Random(cfg['seed']).choice(list(LOCATIONS))
    selected=[s for s in rows if s.target_location==target]
    rng=random.Random(cfg['seed']);rng.shuffle(selected)
    states=[]
    for s in selected:
        for moment in ('initial','after_one_negative'):
            if moment=='after_one_negative' and s.speed_factor!=1:continue
            # Same measured negative public state for all variants; truth never reaches Gate.
            fixture=Sample(s.sample_id,'living_cabinet',s.speed_factor,s.answer_delay_s)
            with World(fixture) as world:
                history=[]
                if moment=='after_one_negative':
                    result=world.search('kitchen_counter');history=[dict(kind='action',result=result)]
                state_id=f's{s.speed_factor:g}_d{s.answer_delay_s:g}_{moment}'
                base=dict(id=state_id,instruction=s.u0,observation=world.observation(),history=history,cost_contract=s.public_contract())
                base['nominal_reference']=reference_values(payload(s.u0,base['observation'],history,s.public_contract()))
                states.append(base)
    write_json(output/'snapshots.json',states)
    jobs=[dict(state_id=s['id'],backend=b,contract=c,style=f) for s,b,c,f in itertools.product(states,('deepseek','jev'),('overlap_control','cost_exclusive'),('raw','summary'))]
    rng.shuffle(jobs)
    batches=[]
    for s in selected:
        methods=['llm_noask','llm_gate','jev_gate'];rng.shuffle(methods)
        batches.append(dict(sample=asdict(s),methods=methods))
    plan=dict(version=cfg['version'],created_utc=datetime.now(timezone.utc).isoformat(),settings=cfg,
        models=Config.load().public_config(),prompt_hashes=hashes(),source_sha256=source_hashes(),
        dataset_sha256=hashlib.sha256((output/'dataset.json').read_bytes()).hexdigest(),
        snapshots_sha256=hashlib.sha256((output/'snapshots.json').read_bytes()).hexdigest(),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        ablation_jobs=jobs,episode_batches=batches,planning_prior='Stipulated uniform across six exhaustive stations; placement fixtures are coverage cases, not prevalence estimates',
        independence='ONE physical map group, ONE seeded target for full 2x2 cost factorial; not independent layouts',
        control='overlap_control preserves v1-style ambiguous gate logic but uses v2 factual/cost context; it is not exact frozen v1 prompt replay',
        selection='Complete episodes always use cost_exclusive + summary, predetermined irrespective of ablation outcomes',
        threshold='Fixed 0.5, not calibrated to increase asks',
        reference='Offline DP over public prior and nominal costs only; never serialized to Gate/Planner; not physical optimality labels',
        no_test_calls=True,retry_policy='One retry; permanent API errors or three consecutive errors block backend; all attempts debit shared cap',
        amendment='Technical JSON-mode marker fix only; 48 gate-only cases retained unchanged. Prior run: 54 requests, 12 aborted launches, zero robot actions. New valid run capped at 12 launches; combined registered launches may reach 24, completed navigation episodes at most 12. Global request limit stays 200.',
        schedule='48 seeded-shuffled state/contract/summary/backend jobs (four initial regimes and two normal-speed post-negative states), then four cost-cell batches with three concurrently run independent methods')
    write_json(output/'plan.json',plan);return plan


def check(output):
    output=Path(output);plan=json.loads((output/'plan.json').read_text())
    if plan['source_sha256']!=source_hashes() or plan['prompt_hashes']!=hashes():raise ValueError('Preregistered code/prompt hashes changed')
    for name in ('dataset','snapshots'):
        if plan[f'{name}_sha256']!=hashlib.sha256((output/f'{name}.json').read_bytes()).hexdigest():raise ValueError('Preregistered data changed')
    if plan['models']!=Config.load().public_config():raise ValueError('Model configuration changed')
    prior=plan['settings'].get('prior_authenticated_requests',0)
    if prior:
        old=ROOT/plan['settings']['protocol_incident_run']
        records=[json.loads(s) for p in list((old/'ablation').glob('gate_*.jsonl'))+list((old/'episodes').glob('*/api_attempts.jsonl')) for s in p.read_text().splitlines() if s]
        if len(records)!=prior:raise ValueError('Prior incident request accounting changed')
    return plan


def ablation(output):
    output=Path(output);plan=check(output);directory=output/'ablation';directory.mkdir(exist_ok=False)
    config=Config.load();ledger=Ledger(output/'inference','ablation')
    states={s['id']:s for s in json.loads((output/'snapshots.json').read_text())};results=[]
    for i,job in enumerate(plan['ablation_jobs']):
        identifier=f'gate_{i:03d}';audit=Audit(identifier,config,ledger,directory/(identifier+'.jsonl'),limit=2)
        state=states[job['state_id']];public=payload(state['instruction'],state['observation'],state['history'],state['cost_contract'],job['style'])
        row=dict(job,id=identifier,nominal_reference=state['nominal_reference'],decision=None,p_ask=None,error=None)
        try:
            client=DeepSeekClient(config,audit) if job['backend']=='deepseek' else JevClient(config,audit)
            result=Gate(client,job['backend'],job['contract'],plan['settings']['gate_threshold']).decide(public)
            row.update(decision=result.decision,p_ask=result.p_ask)
        except Exception as exc:row['error']=config.sanitize(f'{type(exc).__name__}: {exc}')
        row['cost']=audit.summary();results.append(row)
        write_json(directory/(identifier+'.json'),row)
        print(json.dumps(dict(event='ablation',i=i+1,**job,decision=row['decision'],p_ask=row['p_ask'],error=row['error'])),flush=True)
        if ledger.snapshot().get('stage_attempts',{}).get('ablation',0)>=plan['settings']['study_limits']['ablation_requests']:break
    write_json(directory/'results.json',results);return results


def episode_job(sample,method,output):
    root=Path(output);s=Sample(**sample)
    return run_episode(s,method,root/'episodes'/f'{s.sample_id}__{method}',Ledger(root/'inference','episodes'))


def episodes(output):
    output=Path(output);plan=check(output);(output/'episodes').mkdir(exist_ok=False)
    with ProcessPoolExecutor(max_workers=3) as pool:
        for batch in plan['episode_batches']:
            futures=[pool.submit(episode_job,batch['sample'],method,str(output)) for method in batch['methods']]
            for f in as_completed(futures):
                e=f.result();print(json.dumps(dict(event='episode',sample=e['sample_id'],method=e['method'],success=(e['evaluation'] or {}).get('task_success'),burden=e['clarification_burden'],
                    operational_s=e['operational_cost']['operational_seconds'],termination=e['termination_reason'],error=e['error'])),flush=True)


def oracle(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);rows=[]
    # All 24 scene/cost cells physically executed, plus autonomous sweep per speed.
    for s in samples():
        with World(s) as world:
            before=payload(s.u0,world.observation(),[],s.public_contract());result=world.search(s.target_location)
            ev=world.evaluate(0,[result],'oracle_done')
            rows.append(dict(sample_id=s.sample_id,mode='known_location',success=ev['task_success'],action_success=result['success'],motion_sim_s=(result['end_step']-result['start_step'])*world.DT,
                actual_m=world.distance_m,estimate_s=motion_estimate_for(before,s.target_location),evaluation=ev))
            if s.answer_delay_s==1:world.render().save(output/(s.sample_id+'.png'))
    for factor in settings()['speed_factors']:
        s=Sample(f'autonomous_{factor}','study_shelf',factor,1)
        with World(s) as world:
            actions=[world.search(k) for k in LOCATIONS]
            ev=world.evaluate(0,actions,'sweep_done');rows.append(dict(sample_id=s.sample_id,mode='exhaustive_search',success=ev['task_success'],action_success=all(a['success'] for a in actions),evaluation=ev))
    write_json(output/'results.json',dict(rows=rows,successes=sum(r['success'] for r in rows),episodes=len(rows),layout_groups=1))
    print(json.dumps(dict(event='oracle',successes=sum(r['success'] for r in rows),episodes=len(rows))),flush=True)
    return rows


def motion_estimate_for(public,location):
    from .nav2_public import motion_estimate
    return motion_estimate(public['observation']['robot_pose'],location,public['cost_contract'])
