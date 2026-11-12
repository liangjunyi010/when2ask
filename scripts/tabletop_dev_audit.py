"""Reproducible evidence/immutability checks; zero network and model requests."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.tabletop_dev_study import OUT, ROOT, checked


def main():
    checked();files=list((OUT/'episodes').glob('*/episode.json'));assert len(files)==24
    pairs={};attempts=[];asks=0
    for p in files:
        e=json.loads(p.read_text());rows=[json.loads(line) for line in (p.parent/'api_attempts.jsonl').read_text().splitlines()]
        attempts+=rows;pairs.setdefault((e['sample_id'],e['profile']),set()).add(e['method'])
        assert e['partition']=='dev';assert len(rows)<=32 and len(e['actions'])<=12 and len(e['turns'])<=20
        assert e['evaluation']['task_success']==all(e['evaluation']['conditions'].values())
        if e['method']=='llm_noask':
            assert not any(t['gate']['called'] or 'question' in t for t in e['turns'])
            assert not any(r['stage'] in ('gate','question') for r in rows)
        else:
            for t in e['turns']:
                rr=[r for r in rows if r['round']==t['round']]
                assert t['gate']['called'] and (not rr or rr[0]['stage']=='gate')
        for t in e['turns']:
            if 'question' in t:
                asks+=1;assert t['ask_check']['state_unchanged']
                assert t['ask_check']['before_step']==t['ask_check']['after_step']
        assert e['evaluation']['clarification_burden']==sum(t['ask_check']['charged_slots'] for t in e['turns'] if 'ask_check'in t)
    assert len(pairs)==8 and all(len(v)==3 for v in pairs.values())
    probe_files=list((OUT/'probes').glob('*/result.json'));assert len(probe_files)==56
    for p in probe_files:attempts += [json.loads(line) for line in (p.parent/'api_attempts.jsonl').read_text().splitlines()]
    forbidden={'theta_star','private_spec','expected_action','expected_gate','reference','task_success','sample_id','group_id','partition'}
    def keys(value):
        if isinstance(value,dict):
            return set(value).union(*(keys(v) for v in value.values()))
        if isinstance(value,list):return set().union(*(keys(v) for v in value))
        return set()
    for r in attempts:
        request=r['request'];public=request['state'] if r['backend']=='jev' else json.loads(request['messages'][1]['content'])
        assert not keys(public)&forbidden
    ledger=json.loads((OUT/'session/session_budget.json').read_text())
    assert len(attempts)==ledger['attempts']<=450 and ledger['episodes']==24
    before=json.loads((OUT/'protected_before.json').read_text())
    changed=[f for f,h in before.items() if not (ROOT/f).exists() or hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h]
    # README may receive a new, explicit Dev entry; frozen code/data/results may not.
    assert set(changed)<= {'README.md'}
    id='td1_pack_continue_known_cup'
    probe=OUT/'probes'/(id+'_initial__facts_contract__llm_gate')/'api_attempts.jsonl'
    episode=OUT/'episodes'/(id+'__facts_contract__llm_gate')/'api_attempts.jsonl'
    a=json.loads(probe.read_text().splitlines()[0]);b=json.loads(episode.read_text().splitlines()[0])
    requests_equal=a['request']==b['request']
    variation=dict(probe_path=str(probe.relative_to(ROOT)),episode_path=str(episode.relative_to(ROOT)),
        actual_request_bytes_equal=json.dumps(a['request']).encode()==json.dumps(b['request']).encode(),
        request_dicts_equal=requests_equal,request_sha256=hashlib.sha256(json.dumps(a['request']).encode()).hexdigest(),
        probe_response=a['response']['choices'][0]['message']['content'],
        episode_response=b['response']['choices'][0]['message']['content'],
        probe_fingerprint=a['response'].get('system_fingerprint'),episode_fingerprint=b['response'].get('system_fingerprint'),
        interpretation='Observed response inconsistency on identical requests. Cause is not identified; no extra reruns were made to select a response.')
    write=lambda name,v:(OUT/name).write_text(json.dumps(v,indent=2)+'\n')
    write('observed_response_variation.json',variation)
    result=dict(full_dev_episodes=24,probe_calls=56,paired_case_profiles=8,all_methods_per_pair=True,
        authenticated_attempts=len(attempts),ask_turns_verified=asks,ask_physics_frozen=True,gate_before_planner=True,
        noask_skips_gate_question=True,burden_and_scores_match_evidence=True,private_references_absent_from_requests=True,
        budgets_respected=True,api_errors=sum(r['status']=='api_error' for r in attempts),
        schema_errors=sum(r['status']=='schema_error' for r in attempts),
        unknown_usage_attempts=sum(r['input_tokens'] is None or r['output_tokens'] is None for r in attempts),
        protected_files=len(before),changed_preexisting_files=changed,
        actual_models={b:sorted({r['returned_model'] for r in attempts if r['backend']==b}) for b in ('deepseek','jev')},
        backend_usage={b:{k:sum(r[k] for r in attempts if r['backend']==b and r[k] is not None)
                          for k in ('input_tokens','output_tokens','latency_ms')} for b in ('deepseek','jev')})
    write('evidence_validation.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
