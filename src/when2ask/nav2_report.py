"""Automatic descriptive reports only: raw model decisions are never filled in."""
import csv
import html
import json
from collections import defaultdict
from pathlib import Path

from .nav2_runner import write_json


def table(rows,columns):
    def cell(v):return '—' if v is None else f'{v:.3f}' if isinstance(v,float) else str(v)
    return '<table><thead><tr>'+''.join(f'<th>{html.escape(k)}</th>' for k in columns)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(cell(r.get(k)))+'</td>' for k in columns)+'</tr>' for r in rows)+'</tbody></table>'


def report(output):
    from .nav2_study import check,Ledger
    output=Path(output);plan=check(output)
    ablations=json.loads((output/'ablation/results.json').read_text()) if (output/'ablation/results.json').exists() else []
    grouped=defaultdict(list)
    for r in ablations:grouped[(r['backend'],r['contract'],r['style'])].append(r)
    ablation_rows=[]
    for (backend,contract,style),rs in sorted(grouped.items()):
        valid=[r for r in rs if r['decision'] is not None]
        regrets=[]
        for r in valid:
            ref=r['nominal_reference'];chosen=ref['ask_s'] if r['decision']=='ASK' else ref['continue_s']
            regrets.append(chosen-min(ref['ask_s'],ref['continue_s']))
        ablation_rows.append(dict(backend=backend,contract=contract,payload=style,states=len(rs),valid=len(valid),
            asks=sum(r['decision']=='ASK' for r in valid),reference_matches=sum(r['decision']==r['nominal_reference']['decision'] for r in valid),
            mean_nominal_regret_s=sum(regrets)/len(regrets) if regrets else None,
            attempts=sum(r['cost']['api_attempts'] for r in rs),api_latency_s=sum(r['cost']['api_latency_ms'] or 0 for r in rs)/1000))
    rows=[];attempts=[];paired=defaultdict(list)
    for p in sorted((output/'episodes').glob('*/episode.json')):
        e=json.loads(p.read_text());ev=e['evaluation'];cost=e['api_cost'];op=e['operational_cost']
        api_path=p.with_name('api_attempts.jsonl')
        if api_path.exists():attempts.extend(json.loads(s) for s in api_path.read_text().splitlines() if s)
        asks=[t for t in e['turns'] if 'question' in t]
        row=dict(sample=e['sample_id'],method=e['method'],success=ev['task_success'] if ev else None,
            speed=e['public_contract']['speed_factor'],reply_delay_s=e['public_contract']['answer_delay_s'],burden=e['clarification_burden'],
            distance_m=ev['details']['distance_travelled_m'] if ev else None,motion_sim_s=op['motion_sim_s'],reply_wait_wall_s=op['reply_wait_wall_s'],
            operational_s=op['operational_seconds'],penalized_s=op['penalized_seconds'],wall_s=e['wall_time_s'],
            api_latency_s=cost['api_latency_ms']/1000 if cost['api_latency_ms'] is not None else None,
            **{f'{b}_{k}':cost[b][k] for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')},
            attempts=cost['api_attempts'],first_ask_round=asks[0]['round'] if asks else None,
            first_ask_after_checks=len(asks[0]['public_payload']['observation']['checked_locations']) if asks else None,
            ask_freeze=all(t['ask_check']['state_unchanged'] for t in asks) if asks else None,
            termination=e['termination_reason'],error=e['error'],episode=str(p.relative_to(output)))
        rows.append(row);paired[e['sample_id']].append(e)
    fairness=[]
    for sample,es in paired.items():
        initial=[e['turns'][0]['payload_sha256'] for e in es if e['turns']]
        fairness.append(dict(sample=sample,methods=len(es),initial_public_identical=len(set(initial))==1,
            same_planner=len({json.dumps(e['prompt_hashes'],sort_keys=True) for e in es})==1))
    for p in (output/'ablation').glob('gate_*.jsonl'):
        attempts.extend(json.loads(s) for s in p.read_text().splitlines() if s)
    incident=output/'incident_api_attempts.jsonl'
    if incident.exists():attempts.extend(json.loads(s) for s in incident.read_text().splitlines() if s)
    methods=[]
    for method in ('llm_noask','llm_gate','jev_gate'):
        rs=[r for r in rows if r['method']==method]
        if not rs:continue
        def total(key):
            vals=[r[key] for r in rs];return sum(vals) if all(v is not None for v in vals) else None
        methods.append(dict(method=method,episodes=len(rs),successes=sum(r['success'] is True for r in rs),
            mean_burden=total('burden')/len(rs),mean_motion_sim_s=total('motion_sim_s')/len(rs),
            mean_operational_s=total('operational_s')/len(rs),total_distance_m=total('distance_m'),
            total_api_latency_s=total('api_latency_s'),
            **{f'{b}_{k}':total(f'{b}_{k}') for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')}))
    budget=Ledger(output/'inference','episodes').snapshot()
    numbers=[a['session_attempt'] for a in attempts]
    prior=plan['settings'].get('prior_authenticated_requests',0)
    assert len(numbers)==len(set(numbers)) and len(numbers)==budget['attempts']+prior,'Missing or duplicate paid attempts'
    assert sorted(numbers)==list(range(1,len(numbers)+1))
    assert all(r['initial_public_identical'] and r['same_planner'] for r in fairness)
    summary=dict(version=plan['version'],ablations=ablation_rows,methods=methods,episodes=rows,fairness=fairness,budget=budget,
        requests=len(attempts),returned_models=sorted({a['returned_model'] for a in attempts if a.get('returned_model')}),
        schema_errors=sum(a['status']=='schema_error' for a in attempts),api_errors=sum(a['status']=='api_error' for a in attempts),
        unknown_usage_attempts=sum(a.get('input_tokens') is None or a.get('output_tokens') is None for a in attempts),
        interpretation=plan['independence'],gate_threshold=plan['settings']['gate_threshold'],
        reference_warning='Reference matches/regret are conditional on approximate nominal public costs, not physical optimality or independent test labels')
    summary['protocol_incident']=dict(prior_requests=prior,aborted_launches=12 if prior else 0,prior_physical_actions=0,
        correction='Add required literal JSON to action/question format declarations; gate rules/threshold unchanged',
        ablation_reused_without_new_calls=True,combined_registered_launches=budget['episodes']+(12 if prior else 0))
    write_json(output/'summary.json',summary)
    for filename,data in (('ablation.csv',ablation_rows),('episodes.csv',rows),('methods.csv',methods)):
        if data:
            with (output/filename).open('w',newline='') as handle:
                writer=csv.DictWriter(handle,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)
    text='# Navigation Dev v2 — actual API and physical pilot\n\n'+plan['independence']+'.\n\n'
    text+=f"{len(ablations)} gate-only ablation cases; {len(rows)} end-to-end model episodes; {len(attempts)}/200 authenticated requests. Threshold fixed at 0.5. Gate-only calls are not complete robot episodes.\n\n"
    text+='Technical incident: the first run registered 12 launches, all aborted before any robot action after a DeepSeek JSON-mode HTTP 400. Its 54 requests (48 successful ablations plus six launch-stage attempts) remain counted and its raw files unchanged. Only the JSON format marker was fixed; gates/cost rules were not tuned. The 48 gate cases are reused. This amended run allows 12 valid navigation launches, so combined registrations can reach 24 while completed physical episodes remain capped at 12. Total requests remain capped at 200.\n\n'
    text+='Operational seconds = simulated physical motion + actual answer waiting + 5s × requested slots. API latency and backend tokens stay separate. Actual physics is paced at 1× for online episodes.\n\n'
    text+='## Three methods\n\n'+table(methods,['method','successes','episodes','mean_burden','mean_operational_s','total_api_latency_s','deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens'])
    text+='\n\n## Gate-only 2×2 ablation\n\nThe overlap control uses v1-style decision logic with the same new factual context; it is not a rerun of frozen v1 prompts. Raw and summary use the same underlying public facts; summary adds deterministic derived costs/beliefs. No reference decision/cost-to-go is given to any agent.\n\n'
    text+=table(ablation_rows,['backend','contract','payload','states','valid','asks','reference_matches','mean_nominal_regret_s'])
    text+='\n\nReference match and regret use an offline finite-state calculation over the stipulated public prior and nominal kinematic costs. They are diagnostics, not proof of optimal real-physics timing. No threshold/prompt selection follows these results.\n\n## Paired episodes\n\n'
    text+=table(rows,['sample','method','success','burden','distance_m','motion_sim_s','reply_wait_wall_s','operational_s','first_ask_after_checks','termination'])
    text+='\n\n## Scope and reproducibility\n\nThe full cost-factorial reuses a single target selected by seed before API calls, isolating cost effects. There is one map group, so no independent-group confidence interval, significance, held-out Test, or general navigation claim. All frozen/v1 records are unchanged. Raw requests/responses, failures, models and usage are under ablation/ and episodes/. Plan and source/data hashes are in plan.json.\n'
    (output/'README.md').write_text(text)
    body='<h1>When2Ask · Navigation Dev v2</h1><p>Real API × wheel-driven PyBullet · controlled search and reply costs</p>'
    body+=f'<div class="banner">{len(rows)} physical model episodes · {len(ablations)} gate-only cases · {len(attempts)}/200 requests · threshold 0.5 fixed</div>'
    body+='<h2>Three methods — end-to-end</h2>'+table(methods,['method','successes','episodes','mean_burden','mean_operational_s','total_api_latency_s'])
    body+='<p>Operational seconds: simulated motion + actual reply waiting + 5 s per slot. API latency is summed separately. One map group and one seeded target; engineering pilot only.</p>'
    body+='<h2>Gate contract × public summary</h2>'+table(ablation_rows,['backend','contract','payload','states','asks','reference_matches','mean_nominal_regret_s'])
    body+='<p>Reference values use approximate public costs. They are withheld from models. These gate-only results are not task success rates.</p><h2>Paired physical runs</h2>'+table(rows,['sample','method','success','burden','distance_m','motion_sim_s','reply_wait_wall_s','operational_s','first_ask_after_checks'])
    body+='<h2>Actual final PyBullet frames</h2><div class="frames">'
    for r in rows:
        img=str(Path(r['episode']).with_name('final.png'));body+=f'<figure><img src="{img}" alt="Actual PyBullet final frame"><figcaption>{html.escape(r["sample"]+" / "+r["method"])}</figcaption></figure>'
    body+='</div><p><a href="summary.json">Raw summary JSON</a> · <a href="episodes.csv">Episode CSV</a> · <a href="ablation.csv">Ablation CSV</a> · <a href="plan.json">Preregistered plan</a></p>'
    css='body{font:15px system-ui,sans-serif;background:#f4f7fb;color:#18324b;margin:32px auto;max-width:1600px;padding:0 24px}h1{font-size:34px}h2{margin-top:35px}p{line-height:1.65}.banner{background:#dbeaf7;border-left:5px solid #2676b8;padding:18px}table{width:100%;border-collapse:collapse;background:white;font-size:12px;display:block;overflow:auto}th,td{text-align:left;padding:12px;border-bottom:1px solid #dce4ed;white-space:nowrap}th{background:#e6edf5}.frames{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}figure{margin:0;background:white;padding:8px}img{width:100%}figcaption{font-size:11px;overflow-wrap:anywhere}@media(max-width:800px){.frames{grid-template-columns:1fr}}'
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>When2Ask Navigation Dev v2</title><style>'+css+'</style><body>'+body+'</body></html>')
    print(json.dumps({k:summary[k] for k in ('requests','returned_models','methods','ablations')},indent=2))
    return summary
