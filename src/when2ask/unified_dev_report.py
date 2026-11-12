"""Read-only, raw-attempt-derived metrics and estimated USD; never invent usage."""
import csv
import hashlib
import html
import json
from datetime import datetime

from .config import ROOT
from .nine_task_data import write
from .unified_dev_study import OUT, DATA, METHODS, checked, LIMITS

LABELS = dict(llm_noask='LLM-NoAsk', llm_gate='LLM-Gate', jev_gate='Jev-Gate (0.5)', llm_unified='DeepSeek Unified')


def complete_sum(values):
    """Missing observations must not masquerade as a complete lower cost."""
    values=list(values)
    return sum(values) if values and all(v is not None for v in values) else None


def price_attempt(row, prices):
    b=row['backend'];usage=(row.get('response') or {}).get('usage') or {}
    inp,out=row.get('input_tokens'),row.get('output_tokens')
    result=dict(estimated_usd=None,cache_hit_tokens=None,cache_miss_tokens=None,
                tariff=None,reason=None)
    if b=='jev':
        result.update(tariff='jev_input_only',estimated_usd=inp*prices['jev']['input_per_million']/1e6 if inp is not None else None)
        if inp is None:result['reason']='missing_input_usage'
        return result
    timestamp=row.get('request_started_at_utc')
    if timestamp is None:
        result['reason']='missing_request_timestamp';return result
    dt=datetime.fromisoformat(timestamp)
    if dt.utcoffset() is None or dt.utcoffset().total_seconds()!=0:
        raise ValueError('Pricing requires a UTC request timestamp')
    peak=dt.weekday()<5 and (1<=dt.hour<4 or 6<=dt.hour<10)
    tariff='peak' if peak else 'off_peak';rates=prices['deepseek'][tariff]
    hit=usage.get('prompt_cache_hit_tokens', (usage.get('prompt_tokens_details') or {}).get('cached_tokens'))
    miss=usage.get('prompt_cache_miss_tokens')
    if miss is None and hit is not None and inp is not None:miss=inp-hit
    result.update(tariff=tariff,cache_hit_tokens=hit,cache_miss_tokens=miss)
    if any(type(v) is not int or v<0 for v in (inp,out,hit,miss)) or hit+miss!=inp:
        result['reason']='missing_or_inconsistent_cache_usage';return result
    result['estimated_usd']=(hit*rates['cache_hit_per_million']+miss*rates['cache_miss_per_million']+out*rates['output_per_million'])/1e6
    return result


def csv_write(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else [])
        w.writeheader();w.writerows(rows)


def report():
    plan=checked();prices=json.loads((OUT/'pricing.json').read_text())
    dest=OUT/'report';dest.mkdir(exist_ok=True)
    episodes=[];attempts=[];rows=[]
    for job in plan['jobs']:
        path=OUT/'episodes'/job['episode_id']/'episode.json'
        if not path.exists():continue
        e=json.loads(path.read_text());episodes.append(e)
        ap=path.parent/'api_attempts.jsonl'
        calls=[json.loads(l) for l in ap.read_text().splitlines()] if ap.exists() else []
        costs=[price_attempt(r,prices) for r in calls]
        for i,(r,c) in enumerate(zip(calls,costs)):
            attempts.append(dict(episode_id=e['episode_id'],sample_id=e['sample_id'],method=e['method'],
                attempt_index=i,round=r['round'],stage=r['stage'],backend=r['backend'],attempt=r['attempt'],
                status=r['status'],request_started_at_utc=r.get('request_started_at_utc'),
                configured_model=r['configured_model'],returned_model=r.get('returned_model'),
                input_tokens=r.get('input_tokens'),output_tokens=r.get('output_tokens'),latency_ms=r.get('latency_ms'),**c))
        ev=e['evaluation'];asks=[t for t in e['turns'] if 'question' in t]
        first_ask=sum('physical_result'in t for t in e['turns'] if asks and t['round']<asks[0]['round']) if asks else None
        row=dict(episode_id=e['episode_id'],sample_id=e['sample_id'],group_id=e['group_id'],method=e['method'],
            scored=ev is not None,success=ev['task_success'] if ev else None,burden=ev['clarification_burden'] if ev else None,
            ask_turns=len(asks),first_ask_after_actions=first_ask,actions=len(e['actions']),
            physical_failures=sum(not a['success'] for a in e['actions']),termination=e['termination_reason'],error=e['error'],
            api_attempts=len(calls),api_latency_s=complete_sum(r.get('latency_ms') for r in calls),
            wall_time_s=e['wall_time_s'],estimated_usd=complete_sum(c['estimated_usd'] for c in costs),
            unknown_cost_attempts=sum(c['estimated_usd'] is None for c in costs),
            retries=sum(r.get('attempt',1)>1 for r in calls),schema_errors=sum(r['status']=='schema_error' for r in calls),api_errors=sum(r['status']=='api_error' for r in calls))
        if row['api_latency_s'] is not None:row['api_latency_s']/=1000
        for b in ('deepseek','jev'):
            bb=[r for r in calls if r['backend']==b]
            for k in ('input_tokens','output_tokens'):row[b+'_'+k]=complete_sum(r.get(k) for r in bb)
            row[b+'_estimated_usd']=complete_sum(c['estimated_usd'] for r,c in zip(calls,costs) if r['backend']==b)
        rows.append(row)
    methods=[]
    for m in METHODS:
        rr=[r for r in rows if r['method']==m];scored=sum(r['scored'] for r in rr)
        row=dict(method=m,episodes=len(rr),planned_episodes=4,scored_episodes=scored,
                 successes=sum(r['success'] is True for r in rr),success_rate=sum(r['success'] is True for r in rr)/scored if scored else None)
        for k in ('burden','ask_turns','actions','physical_failures','api_attempts','api_latency_s','wall_time_s','estimated_usd',
                  'unknown_cost_attempts','retries','schema_errors','api_errors','deepseek_input_tokens','deepseek_output_tokens',
                  'jev_input_tokens','jev_output_tokens','deepseek_estimated_usd','jev_estimated_usd'):
            row[k+'_total']=complete_sum(r[k] for r in rr)
        for k in ('burden','api_latency_s','wall_time_s','estimated_usd'):
            row[k+'_mean']=row[k+'_total']/len(rr) if rr and row[k+'_total'] is not None else None
        methods.append(row)
    stages=[]
    for method in METHODS:
        for stage in sorted({r['stage'] for r in attempts if r['method']==method}):
            rr=[r for r in attempts if r['method']==method and r['stage']==stage]
            stages.append(dict(method=method,stage=stage,attempts=len(rr),latency_ms=complete_sum(r['latency_ms'] for r in rr),
                               estimated_usd=complete_sum(r['estimated_usd'] for r in rr)))
    paired=[]
    for r in rows:
        ref=next((q for q in rows if q['sample_id']==r['sample_id'] and q['method']=='llm_gate'),None)
        if ref and r['method']!='llm_gate':
            paired.append(dict(sample_id=r['sample_id'],group_id=r['group_id'],method=r['method'],reference='llm_gate',
                **{k+'_difference':(float(r[k])-float(ref[k]) if r[k] is not None and ref[k] is not None else None)
                   for k in ('success','burden','api_latency_s','wall_time_s','estimated_usd')}))
    notes=[
        'Four previously developed Dev groups, two task templates, one run per method/case. No held-out or statistical superiority claim.',
        'All four methods freshly executed; no historical episode is pooled into this report.',
        'Unified generates the question or action/DONE in one logical call. Repairs/retries are extra charged attempts; no separate Gate latency exists for it.',
        'Same public facts, simulator, physics, evaluator, budgets and model parameters. Unified combines role prompts, so this is an architecture comparison, not a gate-only controlled substitution.',
        'API latency sums authenticated HTTP attempts; wall time additionally includes physics/rendering. Serial execution; real provider caching is recorded, not controlled.',
        'USD is an estimate from public prices and actual cache/token usage, not an invoice. Backend tokens are separately reported. Unknown usage/cost remains null.',
        'DeepSeek weekday peak-window classification assumes no Chinese public holiday; outside the peak windows holiday status cannot affect the rate.',
        'All success/failure outcomes retained; guessed preferences can be correct by chance. Lower burden alone does not prove better timing.']
    result=dict(study_version=plan['study_version'],scope='Independent Dev architecture pilot',groups=4,
        planned_episodes=16,completed_episodes=len(rows),all_pairs_complete=len(rows)==16,
        methods=methods,stages=stages,notes=notes,session=json.loads((OUT/'session/session_budget.json').read_text()),
        returned_models={b:sorted({r['returned_model'] for r in attempts if r['backend']==b and r['returned_model']}) for b in ('deepseek','jev')},
        tariffs=sorted({r['tariff'] for r in attempts if r['tariff']}),pricing_sources=prices['sources'])
    write(dest/'summary.json',result)
    for name,data in [('episodes',rows),('methods',methods),('attempt_costs',attempts),('paired_differences',paired),('stages',stages)]:csv_write(dest/(name+'.csv'),data)
    def n(v,d=2):return 'unknown' if v is None else f'{v:.{d}f}'
    header=['Method','Success','Mean burden','Total API s','Mean wall s','Estimated USD total','Requests']
    table=[[LABELS[r['method']],f"{r['successes']}/{r['scored_episodes']}",n(r['burden_mean']),n(r['api_latency_s_total']),
            n(r['wall_time_s_mean']),n(r['estimated_usd_total'],6),str(r['api_attempts_total'])] for r in methods]
    lines=['# Single-call DeepSeek Dev comparison','','Four paired Dev groups; all four methods rerun.','',
           '| '+' | '.join(header)+' |','|'+'---|'*len(header)]+['| '+' | '.join(r)+' |' for r in table]
    lines+=['','## Interpretation limits','']+['- '+note for note in notes]
    lines+=['','## Every episode','', '| Case | Method | Success | Burden | Actions | First ASK after actions | Termination |','|---|---|---|---|---|---|---|']
    for r in rows:lines.append('| '+' | '.join(str(r[k]) for k in ('sample_id','method','success','burden','actions','first_ask_after_actions','termination'))+' |')
    lines+=['','Recompute: `.venv/bin/python scripts/unified_deepseek_dev.py report`. Full raw JSON/JSONL is under `../episodes/`.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,4,figsize=(14,3.8));colors=['#8093a9','#3679bb','#138f96','#9658b2']
    for ax,key,title in zip(axs,['success_rate','burden_mean','api_latency_s_total','estimated_usd_total'],
        ['Task success','Mean preference burden','Total API latency (s)','Estimated USD total']):
        values=[r[key] for r in methods]
        for i,v in enumerate(values):
            if v is not None:ax.bar(i,v,color=colors[i]);ax.text(i,v,n(v,4 if 'usd'in key else 2),ha='center',va='bottom',fontsize=9)
        ax.set_xticks(range(4),['NoAsk','LLM\nGate','Jev\nGate','Unified']);ax.set_title(title,fontsize=11)
        if key=='success_rate':ax.set_ylim(0,1.2)
        else:ax.set_ylim(0,max([v for v in values if v is not None]+[.001])*1.25)
    fig.suptitle('Independent Dev pilot · 4 paired groups · 16 real episodes');fig.tight_layout();fig.savefig(dest/'comparison.png',dpi=160);plt.close(fig)
    body=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>When2Ask · Single-call Dev</title><style>body{margin:0;background:#f2f6fb;color:#19334c;font:16px system-ui}main{max-width:1400px;margin:auto;padding:28px}section{background:white;padding:20px;border-radius:12px;margin:24px 0}img{max-width:100%}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid #ddd}th{background:#e0ebf6}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}a{color:#2864a5}h3{font-size:17px}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}.scroll{overflow:auto}</style><main><h1>When2Ask · Single-call DeepSeek</h1><p>Independent Dev architecture comparison · 4 paired cases · No frozen Test changes</p><img src="comparison.png" alt="Four-method real Dev comparison"><div class="scroll"><table><tr>',
          ''.join('<th>'+x+'</th>' for x in header),'</tr>']
    body+=['<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in r)+'</tr>' for r in table]
    body+=['</table></div><p>API seconds are totals across four episodes. USD is estimated, not an invoice. Unified makes one decision-and-generation call per round; retries count separately.</p>']
    for sid in sorted({e['sample_id'] for e in episodes}):
        body.append('<section><h2>'+html.escape(sid)+'</h2><div class="cards">')
        for m in METHODS:
            e=next((e for e in episodes if e['sample_id']==sid and e['method']==m),None)
            if not e:body.append('<div>'+LABELS[m]+' · Not run</div>');continue
            path='../episodes/'+e['episode_id']+'/'
            status='SUCCESS' if e['evaluation'] and e['evaluation']['task_success'] else 'FAILED'
            body.append('<div><h3>'+LABELS[m]+' · '+status+'</h3><img src="'+path+'final.png" alt="Actual PyBullet final state"><a href="'+path+'episode.json">Episode JSON</a> · <a href="'+path+'api_attempts.jsonl">API log</a><details><summary>Questions and actions</summary>')
            for t in e['turns']:
                value={k:t[k] for k in ('round','gate','unified_decision','question','user_answer','action','physical_result') if k in t}
                body.append('<pre>'+html.escape(json.dumps(value,indent=2))+'</pre>')
            body.append('</details></div>')
        body.append('</div></section>')
    body+=['<section><h2>Scope and limitations</h2><ul>']+['<li>'+html.escape(v)+'</li>' for v in notes]+['</ul></section></main></html>']
    (dest/'index.html').write_text(''.join(body))
    return result


def audit():
    plan=checked();paths=list((OUT/'episodes').glob('*/episode.json'))
    seen=set();all_calls=[];asks=0;unified_rounds=0
    def keys(v):
        if isinstance(v,dict):return set(v).union(*(keys(x) for x in v.values()))
        if isinstance(v,list):return set().union(*(keys(x) for x in v))
        return set()
    forbidden={'theta_star','private_spec','task_success','expected_action','expected_gate','sample_id','partition','group_id'}
    for p in paths:
        e=json.loads(p.read_text());seen.add((e['sample_id'],e['method']))
        calls=[json.loads(l) for l in (p.parent/'api_attempts.jsonl').read_text().splitlines()]
        all_calls+=calls
        assert e['partition']=='dev' and len(calls)<=32 and len(e['turns'])<=20 and len(e['actions'])<=12
        if e['evaluation']:
            assert e['evaluation']['task_success']==all(e['evaluation']['conditions'].values())
            assert e['evaluation']['clarification_burden']==sum(t['ask_check']['charged_slots'] for t in e['turns'] if 'ask_check'in t)
        for t in e['turns']:
            rr=[r for r in calls if r['round']==t['round']]
            if e['method']=='llm_unified':
                assert all(r['stage']=='unified' and r['backend']=='deepseek' for r in rr)
                assert sum(r['attempt']==1 for r in rr)<=1
                assert 'gate' not in t;unified_rounds+=1
            elif e['method']=='llm_noask':
                assert all(r['stage']=='action' and r['backend']=='deepseek' for r in rr)
                assert 'question' not in t
            else:assert not rr or rr[0]['stage']=='gate'
            if 'ask_check'in t:
                c=t['ask_check'];assert c['state_unchanged'] and c['before_step']==c['after_step'];asks+=1
        for r in calls:
            req=r['request'];pub=req['state'] if r['backend']=='jev' else json.loads(req['messages'][1]['content'])
            assert not keys(pub)&forbidden
    budget=json.loads((OUT/'session/session_budget.json').read_text())
    assert len(all_calls)==budget['attempts']<=320 and len(paths)==budget['episodes']<=16
    protected=json.loads((OUT/'protected_before.json').read_text())
    changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not changed,changed
    expected={(j['sample_id'],j['method']) for j in plan['jobs']}
    result=dict(completed_episodes=len(paths),all_16_paired=seen==expected,authenticated_attempts=len(all_calls),
        ask_turns_physics_frozen=asks,unified_rounds=unified_rounds,unified_one_logical_call_per_round=True,
        noask_skips_gate=True,other_gates_before_planner=True,private_keys_absent_from_requests=True,
        evaluator_conditions_match_success=True,budget_respected=True,protected_files=len(protected),changed_protected_files=changed,
        schema_errors=sum(r['status']=='schema_error' for r in all_calls),api_errors=sum(r['status']=='api_error' for r in all_calls),
        retries=sum(r.get('attempt',1)>1 for r in all_calls),unknown_usage_attempts=sum(r.get('input_tokens') is None or r.get('output_tokens') is None for r in all_calls))
    write(OUT/'evidence_validation.json',result)
    return result
