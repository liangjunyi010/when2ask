"""Prelocked 2×2 Gate-state diagnostic and exact historical replay. Explicit live."""
import argparse,copy,hashlib,json,random,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT,Config
from when2ask.console_state import ConsoleLedger
from when2ask.accounting import Audit
from when2ask.api import JevClient,DeepSeekClient
from when2ask.grounded_dev_health import SchemaAwareSession
from when2ask.gate_contract_dev import Gate,GateProfile

OUT=ROOT/'outputs/gate_diagnostics_dev_v7'
SPECS=[('buffer_initial','buffer_exchange','jev_gate',0,'ASK'),
       ('buffer_disclosed','buffer_exchange','llm_gate',1,'CONTINUE'),
       ('buffer_finished_guess','buffer_exchange','llm_noask',3,'CONTINUE'),
       ('retrieval_initial','retrieve_restore','jev_gate',0,'CONTINUE'),
       ('retrieval_open','retrieve_restore','jev_gate',1,'ASK'),
       ('retrieval_finished','retrieve_restore','jev_gate',4,'CONTINUE'),
       ('inspection_initial','occlusion_inspection','jev_gate',0,'CONTINUE'),
       ('inspection_finished','occlusion_inspection','jev_gate',3,'CONTINUE')]


def states():
    result={}
    for key,template,method,index,expected in SPECS:
        p=ROOT/f'outputs/memory_planner_dev_v6/live/{template}__{method}/episode.json';e=json.loads(p.read_text())
        result[key]=dict(source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),round=index,
            expected_contract_decision=expected,public_payload=e['turns'][index]['public_payload'])
    return result


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:parser.error('Explicit --live required')
    dest=OUT/'matrix';dest.mkdir(exist_ok=False);cases=states();profiles=[GateProfile(s,c) for s in (False,True) for c in (False,True)]
    jobs=[dict(id=key+'__'+p.name,kind='factorial',backend='jev',state_id=key,compact=p.compact_state,contract=p.explicit_contract) for key in cases for p in profiles]
    for version in ('grounded_planner_dev_v5','memory_planner_dev_v6'):
        for repeat in range(3):jobs.append(dict(id=f'replay_{version}_{repeat}',kind='historical_replay',backend='jev',version=version,repeat=repeat))
    for key,p in [('buffer_initial',profiles[0]),('buffer_initial',profiles[1]),('retrieval_initial',profiles[1]),('inspection_initial',profiles[1])]:
        jobs.append(dict(id='deepseek_'+key+'__'+p.name,kind='factorial',backend='deepseek',state_id=key,compact=p.compact_state,contract=p.explicit_contract))
    random.Random(42781112).shuffle(jobs)
    plan=dict(date='2026-11-11',purpose='Gate-state decisions, not end-to-end success. Eight old PUBLIC states, 2 required ASK and6 CONTINUE controls. Labels are never sent to a model.',
        configuration=Config.load().public_config(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=hashlib.sha256((ROOT/'src/when2ask/gate_contract_dev.py').read_bytes()).hexdigest(),
        profiles={p.name:dict(compact_state=p.compact_state,explicit_contract=p.explicit_contract,prompt_hashes=p.hashes()) for p in profiles},
        states={k:{f:v for f,v in row.items() if f!='public_payload'} for k,row in cases.items()},jobs=jobs,seed=42781112,
        limits=dict(gate_jobs=42,all_authenticated_requests=150,full_episodes=6,max_retries=1),threshold=.5,
        threshold_diagnostic=[.3,.4,.5,.6,.7],threshold_policy='Offline Gate-state sensitivity only; never changes runtime0.5 or claims end-to-end scores.',
        selection_rule='Candidate must fix the buffer miss, match both required ASK and all six CONTINUE controls at0.5; then prefer fewer changed factors, contract-only before compact-only before both. If none qualify, do not promote.',
        failure_policy='All attempts charged to one ledger; no in-place reruns. Stop backend on genuine permanent/auth/network breaker. No threshold tuning or formal Test calls.')
    (dest/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');(dest/'state_sources.json').write_text(json.dumps(cases,indent=2)+'\n')
    config=Config.load();ledger=ConsoleLedger(ROOT/'outputs/local_console/gate-diagnostics-v7-live/inference',150,6);rows=[]
    for job in jobs:
        audit=Audit(job['id'],config,path=dest/(job['id']+'.api.jsonl'),limit=2);audit.session=SchemaAwareSession(ledger,audit)
        actual=None;probability=None;error=None;wire=None
        try:
            if job['kind']=='historical_replay':
                p=ROOT/f"outputs/{job['version']}/live/buffer_exchange__jev_gate/api_attempts.jsonl"
                original=next(json.loads(s) for s in p.read_text().splitlines() if json.loads(s)['stage']=='gate')['request']
                q=original['questions']['needs_clarification'];wire=original['state']
                probability=JevClient(config,audit).noul(wire,q['instructions'],q['criteria'],stage='historical_replay')
                actual='ASK' if probability>=.5 else 'CONTINUE'
            else:
                profile=GateProfile(job['compact'],job['contract']);g=Gate(JevClient(config,audit) if job['backend']=='jev' else DeepSeekClient(config,audit),job['backend'],.5,profile)
                result=g.decide(cases[job['state_id']]['public_payload']);actual,probability=result.decision,result.p_ask;wire=g.last_payload
        except Exception as exc:error=config.sanitize(str(exc))
        expected=cases[job['state_id']]['expected_contract_decision'] if job['kind']=='factorial' else None
        row=dict(**job,decision=actual,p_ask=probability,error=error,expected=expected,correct=(actual==expected) if expected else None,
            cost=audit.summary(),public_payload_sha256=hashlib.sha256(json.dumps(wire,sort_keys=True).encode()).hexdigest())
        (dest/(job['id']+'.json')).write_text(json.dumps(config.sanitize(row),indent=2)+'\n');rows.append(row)
        print(json.dumps({k:row[k] for k in ['id','decision','p_ask','correct','error']}),flush=True)
        if error:break
    (dest/'rows.json').write_text(json.dumps(rows,indent=2)+'\n')
    qualified=[];metrics=[]
    for profile in profiles:
        selected=[r for r in rows if r['backend']=='jev' and r['kind']=='factorial' and r['compact']==profile.compact_state and r['contract']==profile.explicit_contract]
        m=dict(profile=profile.name,states=len(selected),correct=sum(r['correct'] is True for r in selected),
            missed_asks=sum(r['expected']=='ASK' and r['decision']!='ASK' for r in selected),unnecessary_asks=sum(r['expected']=='CONTINUE' and r['decision']=='ASK' for r in selected))
        metrics.append(m)
        if m['states']==8 and m['correct']==8 and profile.name!='s0c0':qualified.append(profile.name)
    chosen=next((key for key in ['s0c1','s1c0','s1c1'] if key in qualified),None)
    selection=dict(metrics=metrics,qualified=qualified,selected=chosen,threshold=.5,selection_rule=plan['selection_rule'],authenticated_requests=ledger.snapshot()['attempts'],all_jobs_complete=len(rows)==42)
    (OUT/'selection.json').write_text(json.dumps(selection,indent=2)+'\n');print(json.dumps(selection,indent=2))
    if len(rows)!=42:raise RuntimeError('Incomplete diagnostics retained; do not silently rerun.')


if __name__=='__main__':main()
