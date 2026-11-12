"""Post-hoc descriptive timing diagnostics; reads evidence, never calls a model."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.nine_task_data import OUT
from when2ask.nine_task_benchmark import METHODS


def main():
    episodes=[json.loads(p.read_text()) for p in sorted((OUT/'test_runs').glob('*/episode.json'))]
    result={'scope':'Post-hoc explanatory diagnostics, not preregistered timing accuracy or an optimal policy.',
            'gate_cost':[],'ask_events':[],'physical_execution_failures':0,'repeated_actions':[]}
    for method in METHODS:
        records=[json.loads(line) for p in (OUT/'test_runs').glob('*__'+method+'/api_attempts.jsonl')
                 for line in p.read_text().splitlines()]
        gate=[r for r in records if r.get('stage')=='gate']
        result['gate_cost'].append(dict(method=method,attempts=len(gate),
            cumulative_latency_s=sum(r['latency_ms'] for r in gate if r['latency_ms'] is not None)/1000 if gate else None,
            mean_attempt_latency_ms=sum(r['latency_ms'] for r in gate if r['latency_ms'] is not None)/len(gate) if gate else None,
            input_tokens=sum(r['input_tokens'] for r in gate if r['input_tokens'] is not None) if gate else None,
            output_tokens=sum(r['output_tokens'] for r in gate if r['output_tokens'] is not None) if gate else None,
            backend='jev' if method=='jev_gate' else 'deepseek' if method=='llm_gate' else None))
    for e in episodes:
        result['physical_execution_failures']+=sum(not r['success'] for r in e['actions'])
        for t in e['turns']:
            if 'question' in t:
                result['ask_events'].append(dict(sample_id=e['sample_id'],template=e['template_id'],method=e['method'],
                    round=t['round'],after_robot_actions=sum('physical_result' in q for q in e['turns'] if q['round']<t['round']),
                    p_ask=t['gate']['p_ask'],question=t['question'],answer=t['user_answer'],charged_slots=t['ask_check']['charged_slots']))
        seen={}
        for a in e['actions']:
            key=(a['skill'],a['object_id'],a['target_id']);seen[key]=seen.get(key,0)+1
        repeated=[dict(skill=k[0],object_id=k[1],target_id=k[2],count=v) for k,v in seen.items() if v>=3]
        if repeated:result['repeated_actions'].append(dict(sample_id=e['sample_id'],method=e['method'],repeated=repeated,
            caution='Repeated action alone is not a failure label; consult actual geometry and task evaluator.'))
    (OUT/'report/diagnostics.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['gate_cost'],indent=2))


if __name__=='__main__':main()
