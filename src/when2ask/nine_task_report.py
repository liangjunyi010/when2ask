"""Recompute every nine-task pilot table from immutable raw episode evidence."""
import csv
import html
import json
from .nine_task_data import ROOT, DATA, OUT, TEMPLATES, load, write
from .nine_task_benchmark import METHODS


def summarize(episodes):
    rows=[]
    for e in episodes:
        c=e['cost'];ev=e['evaluation'];turns=e['turns']
        asks=[t for t in turns if 'question' in t]
        rows.append(dict(sample_id=e['sample_id'],group_id=e['group_id'],template=e['template_id'],method=e['method'],
            success=bool(ev and ev['task_success']),scored=ev is not None,unknown_slots=e['unknown_slots'],
            burden=ev['clarification_burden'] if ev else None,ask_turns=len(asks),
            first_ask_round=asks[0]['round'] if asks else None,
            first_ask_after_actions=sum('physical_result' in t for t in turns if asks and t['round']<asks[0]['round']),
            actions=len(e['actions']),physical_failures=sum(not a['success'] for a in e['actions']),
            gate_calls=sum(t['gate']['called'] for t in turns),termination=e['termination_reason'],error=e['error'],
            api_attempts=c['api_attempts'],retries=c['retries'],schema_errors=c['schema_errors'],api_errors=c['api_errors'],
            api_latency_s=c['api_latency_ms']/1000 if c['api_latency_ms'] is not None else None,
            wall_time_s=e['wall_time_s'],
            **{b+'_'+k:c[b][k] for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')},
            **{b+'_unknown_'+k:c[b]['unknown_'+k+'_attempts'] for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')}))
    def total(rs,key):
        values=[r[key] for r in rs if r[key] is not None]
        return sum(values) if values else None
    def group(rs,**meta):
        scored=[r for r in rs if r['scored']]
        burden=total(rs,'burden')
        return dict(**meta,episodes=len(rs),scored_episodes=len(scored),successes=sum(r['success'] for r in scored),
            success_rate=sum(r['success'] for r in scored)/len(scored) if scored else None,
            burden_total=burden,burden_mean=burden/len(rs) if burden is not None and rs else None,
            **{k:total(rs,k) for k in ('api_latency_s','api_attempts','retries','schema_errors','api_errors','physical_failures',
              'deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens',
              'deepseek_unknown_input_tokens','deepseek_unknown_output_tokens','jev_unknown_input_tokens','jev_unknown_output_tokens')})
    overall=[group([r for r in rows if r['method']==m],method=m) for m in METHODS]
    by_task=[group([r for r in rows if r['method']==m and r['template']==t],template=t,method=m) for t in TEMPLATES for m in METHODS]
    return rows,overall,by_task


def report():
    dest=OUT/'report';dest.mkdir(parents=True,exist_ok=True)
    episodes=[json.loads(p.read_text()) for p in sorted((OUT/'test_runs').glob('*/episode.json'))]
    rows,overall,by_task=summarize(episodes)
    oracle=json.loads((OUT/'oracle/summary.json').read_text())
    samples=load();coverage=[]
    for t in TEMPLATES:
        cases=[s for s in samples if s.template_id==t];orows=[r for r in oracle['rows'] if r['template']==t]
        coverage.append(dict(template=t,dev=sum(s.partition=='dev' for s in cases),test=sum(s.partition=='test' for s in cases),
            groups=len({s.group_id for s in cases}),oracle_successes=sum(r['success'] for r in orows),oracle_total=len(orows)))
    paired=[]
    for sample_id in sorted({r['sample_id'] for r in rows}):
        rs={r['method']:r for r in rows if r['sample_id']==sample_id}
        paired.append(dict(sample_id=sample_id,template=next(iter(rs.values()))['template'],
            **{m:rs[m]['success'] if m in rs else None for m in METHODS}))
    attempts=[json.loads(line) for folder in ('dev_runs','test_runs')
              for p in (OUT/folder).glob('*/api_attempts.jsonl') for line in p.read_text().splitlines()]
    models={b:sorted({r['returned_model'] for r in attempts if r['backend']==b and r.get('returned_model')}) for b in ('deepseek','jev')}
    result=dict(experiment='nine_task_pilot_v1',evidence='Real model outputs, real PyBullet execution; offline oracle separate from model results.',
        coverage=coverage,methods=overall,by_task=by_task,paired_groups=paired,
        expected_test_episodes=54,recorded_test_episodes=len(rows),scored_test_episodes=sum(r['scored'] for r in rows),
        total_authenticated_requests=len(attempts),returned_models=models,
        oracle=dict(successes=oracle['successes'],total=oracle['total']),
        caveats=['Only two independent Test cases per task; descriptive engineering pilot, no significance or broad robustness claim.',
            'The historical128-sample held-out experiment remains unrun and unchanged.',
            'Each task family retains its established prompts/contract; all three methods share exactly the same planner/serialization within a paired case.',
            'Mobile cases vary station/furniture placement within one wall topology; not new room topologies.',
            'Backend tokens stay separate. API latency is cumulative measured inference time, excluding motion and user response time.',
            'Task success comes from final geometry, contacts, sensing and required event order, independently of DONE or claimed action IDs.',
            'Historical and new geometry-validation failures are retained; infeasible first geometry was revised before any online calls.'])
    write(dest/'summary.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    values=np.array([[next(r for r in by_task if r['template']==t and r['method']==m)['successes']
                      for m in METHODS] for t in TEMPLATES])
    fig,ax=plt.subplots(figsize=(9,6.5));ax.imshow(values,vmin=0,vmax=2,cmap='Blues',aspect='auto')
    ax.set_xticks(range(3),['NoAsk','LLM-Gate','Jev-Gate (0.5)'])
    ax.set_yticks(range(9),[t.replace('_',' ').title() for t in TEMPLATES])
    for i in range(9):
        for j in range(3):ax.text(j,i,f'{values[i,j]}/2',ha='center',va='center',color='white' if values[i,j]>1 else '#17314e',fontsize=12,fontweight='bold')
    ax.set_title('Nine-task pilot · paired real-physics success\nTwo new Test layouts per task; descriptive results',pad=15)
    fig.tight_layout();fig.savefig(dest/'task_success.png',dpi=180);plt.close(fig)
    for name,values in [('episodes',rows),('methods',overall),('per_task',by_task),('coverage',coverage),('paired',paired)]:
        with (dest/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]) if values else [])
            writer.writeheader();writer.writerows(values)
    lines=['# When2Ask: nine-task coverage pilot','',
        f"Real API paired evaluation: {len(rows)}/54 episodes. Physical oracle: {oracle['successes']}/{oracle['total']}.",'',
        '| Task | Dev | Test | Groups | Physical oracle | NoAsk | LLM-Gate | Jev-Gate |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for c in coverage:
        scores=[]
        for m in METHODS:
            r=next(r for r in by_task if r['template']==c['template'] and r['method']==m)
            scores.append(f"{r['successes']}/{r['scored_episodes']}")
        lines.append(f"| {c['template']} | {c['dev']} | {c['test']} | {c['groups']} | {c['oracle_successes']}/{c['oracle_total']} | "+' | '.join(scores)+' |')
    lines+=['','| Method | Success | Avg slots requested | DeepSeek in / out | Jev in / out | Total API latency |',
            '|---|---:|---:|---:|---:|---:|']
    def number(v):return 'unknown' if v is None else str(v)
    for r in overall:
        b='unknown' if r['burden_mean'] is None else f"{r['burden_mean']:.3f}"
        lat='unknown' if r['api_latency_s'] is None else f"{r['api_latency_s']:.2f}s"
        lines.append(f"| {r['method']} | {r['successes']}/{r['scored_episodes']} | {b} | {number(r['deepseek_input_tokens'])} / {number(r['deepseek_output_tokens'])} | {number(r['jev_input_tokens'])} / {number(r['jev_output_tokens'])} | {lat} |")
    lines+=['','## Per-case failures','']
    for r in rows:
        if not r['success']:
            e=next(e for e in episodes if e['sample_id']==r['sample_id'] and e['method']==r['method'])
            failed=[k for k,v in (e['evaluation'] or {}).get('conditions',{}).items() if not v]
            lines.append(f"- {r['sample_id']} / {r['method']}: {', '.join(failed) or r['error']}; termination={r['termination']}.")
    lines+=['','## Interpretation and limits','']+['- '+v for v in result['caveats']]
    lines+=['','## Reproduce','',
        'Run `.venv/bin/python scripts/nine_task_pilot.py report` to recompute all tables from raw episodes. '
        'The generate/oracle/freeze commands refuse to replace existing evidence. Online smoke/run commands require --live and refuse reused episode directories. '
        'Frozen jobs, dataset/source/prompt hashes, models and budgets are recorded in ../manifest.json. '
        'All public model payloads, questions, answers, actions, physical events and per-attempt token/latency records are stored in ../test_runs/.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n')
    # A portable English, read-only gallery; evidence can be served from repo root.
    header='''<!doctype html><html lang="en"><meta charset="utf-8"><title>When2Ask · Nine-task Benchmark</title>
<style>body{margin:0;background:#f3f6fa;color:#17314e;font:17px system-ui}main{max-width:1350px;margin:auto;padding:35px}h1{font-size:35px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:12px;text-align:left;border-bottom:1px solid #dce5ef}th{background:#dce9f6}section{background:white;padding:22px;margin:22px 0;border-radius:12px}.pair{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}img{width:100%}a{color:#1767b2}.ok{color:#138553}.fail{color:#b44337}details{margin:12px 0}summary{cursor:pointer}pre{font-size:13px;white-space:pre-wrap}p{line-height:1.5}</style><main><h1>When2Ask · Nine-task Benchmark</h1>'''
    body=[header,f"<p>18 new held-out pilot cases · 9 task types · 3 methods · {len(rows)}/54 real model episodes. Physical feasibility: {oracle['successes']}/{oracle['total']}. Two cases per task is preliminary coverage, not a conclusive ranking.</p>",
          '<table><tr><th>Task</th><th>Oracle</th><th>NoAsk</th><th>LLM-Gate</th><th>Jev-Gate</th></tr>']
    for c in coverage:
        scores=[next(r for r in by_task if r['template']==c['template'] and r['method']==m) for m in METHODS]
        body.append('<tr><td>'+html.escape(c['template'].replace('_',' ').title())+'</td><td>'+f"{c['oracle_successes']}/{c['oracle_total']}"+'</td>'+''.join(f"<td>{r['successes']}/{r['scored_episodes']}</td>" for r in scores)+'</tr>')
    body.append('</table>')
    for s in [s for s in samples if s.partition=='test']:
        body.append('<section><h2>'+html.escape(s.template_id.replace('_',' ').title())+f' · {s.unknown_slots} initially undisclosed</h2><p>'+html.escape(s.u0)+'</p><div class="pair">')
        for m in METHODS:
            found=[e for e in episodes if e['sample_id']==s.sample_id and e['method']==m]
            if not found:body.append('<div>Not run</div>');continue
            e=found[0];ok=e['evaluation'] and e['evaluation']['task_success'];folder='../test_runs/'+s.sample_id+'__'+m+'/'
            body.append(f'<div><h3>{m}</h3><b class="'+('ok' if ok else 'fail')+'">'+('SUCCESS' if ok else 'FAILED')+'</b><img src="'+folder+'final.png" alt="Actual final PyBullet state"><p>Requests: '+str((e['evaluation'] or {}).get('clarification_burden','unknown'))+'</p><a href="'+folder+'episode.json">Full execution evidence</a>')
            body.append('<details><summary>Questions & actions</summary>')
            for t in e['turns']:
                g=t['gate'];text=f"Round {t['round']}: {g['decision']}"+(f" · p={g['p_ask']:.2f}" if g['p_ask'] is not None else '')
                if 'question' in t:text+='\nASK: '+t['question']['text']+'\nUSER: '+json.dumps(t['user_answer'])
                if 'action' in t:text+='\n'+json.dumps(t['action'])
                body.append('<pre>'+html.escape(text)+'</pre>')
            body.append('</details></div>')
        body.append('</div></section>')
    body.append('</main></html>');(dest/'index.html').write_text(''.join(body))
    return result
