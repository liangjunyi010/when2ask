"""Six explicit live action-only regression probes; never scores episodes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT,Config
from when2ask.accounting import Audit
from when2ask.console_state import ConsoleLedger
from when2ask.api import DeepSeekClient
from when2ask.memory_dev_agents import Planner,prompt_hashes
from when2ask.memory_dev_public import serialize
from when2ask.grounded_dev_health import SchemaAwareSession


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--live',action='store_true');p.add_argument('--revision',choices=['r1','r2'],default='r1');a=p.parse_args()
    if not a.live:p.error('Explicit --live required')
    out=ROOT/'outputs/memory_planner_dev_v6';dest=out/('probes' if a.revision=='r1' else 'probes_r2');dest.mkdir(exist_ok=False)
    cases=[('retrieval_closed_known','retrieve_restore','llm_gate',4,{'kind':'DONE'}),
           ('retrieval_closed_guess','retrieve_restore','llm_noask',3,{'kind':'DONE'}),
           ('retrieval_needs_cover','retrieve_restore','llm_gate',3,{'kind':'cover','object_id':'storage_lid'}),
           ('exchange_complete','buffer_exchange','jev_gate',4,{'kind':'DONE'}),
           ('exchange_needs_final_move','buffer_exchange','jev_gate',3,{'kind':'move','object_id':'item_a','target_id':'slot_right'}),
           ('inspection_complete','occlusion_inspection','llm_gate',3,{'kind':'DONE'})]
    frozen=dict(revision=a.revision,created_date='2026-11-11',purpose='Action-only regression probes from six actual previously observed public states; no oracle/private inputs, no end-to-end success claims',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),prompt_hashes=prompt_hashes(),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'src/when2ask').glob('memory_dev*.py')},
        cases=[dict(id=k,template=t,method=m,round=i,expected_public_action=c) for k,t,m,i,c in cases],
        request_limit_including_episodes=150,full_episode_limit=9,per_probe_attempt_limit=2)
    (dest/'plan.json').write_text(json.dumps(frozen,indent=2)+'\n')
    config=Config.load();ledger=ConsoleLedger(ROOT/'outputs/local_console/memory-dev-v6-live/inference',150,9);rows=[]
    for key,template,method,index,expected in cases:
        source=ROOT/f'outputs/grounded_planner_dev_v5/live/{template}__{method}/episode.json';e=json.loads(source.read_text());ts=e['turns']
        raw=ts[index]['raw_public_payload'];prior=[t['raw_public_payload']['observation'] for t in ts[:index]];public=serialize(raw,prior)
        assert ts[index]['gate']['decision']=='CONTINUE'
        audit=Audit('probe_'+key,config,path=dest/(key+'.api.jsonl'),limit=2);audit.session=SchemaAwareSession(ledger,audit)
        planner=Planner(DeepSeekClient(config,audit));result=None;error=None
        try:result=planner.generate_action(public)
        except Exception as exc:error=config.sanitize(str(exc))
        record=dict(id=key,evidence_kind='real_api_action_only_replay_probe_not_episode',source_episode=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            source_round=index,public_payload=public,expected_public_action=expected,actual_action=result,model_plan=planner.last_model_plan,error=error,
            matches_expected=result==expected,cost=audit.summary())
        (dest/(key+'.json')).write_text(json.dumps(config.sanitize(record),indent=2)+'\n');rows.append(record)
        print(json.dumps(dict(id=key,action=result,expected=expected,match=result==expected,error=error)),flush=True)
        if error:break
    summary=dict(probes=len(rows),matches=sum(r['matches_expected'] for r in rows),authenticated_requests=ledger.snapshot()['attempts'],
                 evidence_kind='action_only_replay_probes_not_physical_episodes',rows=[{k:v for k,v in r.items() if k not in ['public_payload','model_plan']} for r in rows])
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if len(rows)!=6 or summary['matches']!=6:raise RuntimeError('Probe failures retained. Diagnose before freezing full episodes; never rerun in-place.')


if __name__=='__main__':main()
