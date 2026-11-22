"""Four headline metrics; episode-level false alarms have explicit denominators."""
import os
import csv
import hashlib
import html
import json

from .config import ROOT
from .nine_task_data import TEMPLATES,write
from .metrics_dev_data import OUT,entries
from .metrics_dev_study import METHODS,checked
from .unified_dev_report import price_attempt,complete_sum,csv_write

LABELS=dict(llm_noask='LLM-NoAsk',llm_gate='LLM-Gate',jev_gate='Jev-Gate',llm_unified='DeepSeek Unified')
TASKS=dict(zip(TEMPLATES,['Pack and Cover','Selected Containers','Find and Approach','Category Sorting',
    'Inventory Restock','Retrieve and Restore','Buffered Exchange','Patrol and Return','Reveal and Inspect']))


def explicit_ask(episode,calls):
    for t in episode.get('turns',[]):
        if t.get('gate',{}).get('decision')=='ASK' or t.get('unified_decision',{}).get('kind')=='ASK':return True
    # A valid explicit decision is still a false alarm if generating/validating
    # its question later fails. Schema failures must not hide emitted ASK.
    for r in calls:
        if r.get('backend')!='deepseek' or r.get('stage') not in ('gate','unified'):continue
        try:value=json.loads(r['response']['choices'][0]['message']['content'])
        except (KeyError,TypeError,IndexError,json.JSONDecodeError):continue
        if isinstance(value,dict) and value.get('decision' if r['stage']=='gate' else 'kind')=='ASK':return True
    return False


def fpr_case(episode,calls,is_negative):
    if not is_negative or episode['method']=='llm_noask':return None
    if explicit_ask(episode,calls):return True
    # A truncated technical run with no ASK has not demonstrated a clean full
    # negative. Never credit network/schema/budget exceptions as true negatives.
    if episode.get('error') or not any(r.get('status')=='ok' and r.get('stage') in ('gate','unified') for r in calls):return None
    return False


def aggregate(rows,method):
    rr=[r for r in rows if r['method']==method]
    n=len(rr);scored=[r for r in rr if r['success'] is not None]
    negatives=[r for r in rr if r['fpr_core_negative']]
    valid=[r for r in negatives if r['false_alarm'] is not None]
    success=sum(r['success'] for r in scored);fp=sum(r['false_alarm'] is True for r in valid)
    result=dict(method=method,episodes=n,scored=len(scored),successes=success,success_rate=success/len(scored) if scored else None,
        api_seconds_total=complete_sum(r['api_seconds'] for r in rr),estimated_usd_total=complete_sum(r['estimated_usd'] for r in rr),
        negative_cases=len(negatives),false_positives=fp if method!='llm_noask' else None,
        fpr_denominator=len(valid) if method!='llm_noask' else None,fpr=fp/len(valid) if valid else None,
        negative_censored=sum(r['false_alarm'] is None for r in negatives) if method!='llm_noask' else None)
    for field in ('api_seconds','estimated_usd'):
        result[field+'_mean']=result[field+'_total']/n if n and result[field+'_total'] is not None else None
    for key in ('api_attempts','retries','schema_errors','api_errors','unknown_cost_attempts','physical_failures',
        'deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens','wall_time_s'):
        result[key+'_total']=complete_sum(r[key] for r in rr)
    return result


def report(*, source=None, destination=None, archived=False):
    out = source or OUT
    if archived:
        from .submission import ARCHIVE, verify_archive
        if out != ARCHIVE: raise ValueError('Unknown evidence directory')
        verify_archive()
    plan=json.loads((out/'manifest.json').read_text()) if archived else checked();prices=json.loads((out/'pricing.json').read_text());meta={r['sample']['sample_id']:r for r in entries()}
    dest=destination or out/'report';dest.mkdir(parents=True,exist_ok=True)
    episodes=[];rows=[];attempts=[]
    for job in plan['jobs']:
        path=out/'episodes'/job['episode_id']/'episode.json'
        if not path.exists():continue
        e=json.loads(path.read_text());episodes.append(e);m=meta[e['sample_id']]
        ap=path.parent/'api_attempts.jsonl'
        calls=[json.loads(l) for l in ap.read_text().splitlines()] if ap.exists() else []
        costs=[price_attempt(r,prices) for r in calls]
        for i,(r,c) in enumerate(zip(calls,costs)):
            attempts.append(dict(episode_id=e['episode_id'],method=e['method'],template_id=e['template_id'],index=i,
                round=r['round'],stage=r.get('stage'),backend=r['backend'],status=r['status'],attempt=r.get('attempt'),
                input_tokens=r.get('input_tokens'),output_tokens=r.get('output_tokens'),latency_ms=r.get('latency_ms'),
                returned_model=r.get('returned_model'),request_started_at_utc=r.get('request_started_at_utc'),**c))
        ev=e['evaluation'];latency=complete_sum(r.get('latency_ms') for r in calls)
        row=dict(episode_id=e['episode_id'],sample_id=e['sample_id'],template_id=e['template_id'],group_id=e['group_id'],
            method=e['method'],condition=m['condition'],fpr_core_negative=m['fpr_core_negative'],
            success=ev['task_success'] if ev else None,api_seconds=latency/1000 if latency is not None else None,
            estimated_usd=complete_sum(c['estimated_usd'] for c in costs),
            false_alarm=fpr_case(e,calls,m['fpr_core_negative']),explicit_ask=explicit_ask(e,calls),
            api_attempts=len(calls),retries=sum(r.get('attempt',1)>1 for r in calls),
            schema_errors=sum(r['status']=='schema_error' for r in calls),api_errors=sum(r['status']=='api_error' for r in calls),
            unknown_cost_attempts=sum(c['estimated_usd'] is None for c in costs),
            physical_failures=sum(not r['success'] for r in e['actions']),wall_time_s=e['wall_time_s'],
            termination=e['termination_reason'],error=e['error'])
        for b in ('deepseek','jev'):
            for k in ('input_tokens','output_tokens'):row[b+'_'+k]=complete_sum(r.get(k) for r in calls if r['backend']==b)
        rows.append(row)
    methods=[aggregate(rows,m) for m in METHODS]
    per_task=[dict(template_id=t,**aggregate([r for r in rows if r['template_id']==t],m)) for t in TEMPLATES for m in METHODS]
    pairs=[]
    for sid in meta:
        rr={r['method']:r for r in rows if r['sample_id']==sid};ref=rr.get('llm_gate')
        if ref:
            for m,r in rr.items():
                if m=='llm_gate':continue
                pairs.append(dict(sample_id=sid,group_id=r['group_id'],template_id=r['template_id'],method=m,reference='llm_gate',
                    **{k+'_delta':float(r[k])-float(ref[k]) if r[k] is not None and ref[k] is not None else None
                       for k in ('success','api_seconds','estimated_usd','false_alarm')}))
    notes=[
        'Nine templates, 27 Dev variants from 18 existing Dev physical groups. Each template has two fully disclosed core negatives and one information-condition contrast.',
        'Seven contrasts hide real user preferences. Unknown navigation permits autonomous search; the hidden inspection label is a physically observable fact. Neither is mislabeled as a mandatory-ASK positive.',
        'Primary FPR is task-level: at least one explicit ASK on a prelabelled core negative. Multiple asks count once. NoAsk is N/A because asking is disabled.',
        'Explicit ASK remains a false positive if question generation fails. Technically interrupted runs without ASK are censored rather than credited as true negatives; denominators are shown.',
        'Success comes from independent actual physics and event checks, even after a guessed choice or budget termination. It is separate from task-level FPR.',
        'Speed is mean cumulative API HTTP seconds per episode, including all retries and DONE. It excludes physical motion and user response time. Three fixed worker processes run a frozen interleaved order.',
        'USD is estimated per episode from real backend/cache usage and official public prices, not invoices. Missing usage remains unknown. Tokens of different backends are never directly added as money.',
        'All four methods were freshly executed. Unified fuses decision and native question/action generation; this is an architecture comparison, not only a Gate substitution.',
        'Contrast variants share groups with negatives. No statistical interval treats all 27 cases as independent; no fresh held-out Test or universal ranking claim.',
        'Clarification burden remains only in original episode diagnostics; headline tables contain success, API time, estimated cost and unnecessary ASK rate.']
    result=dict(study_version=plan['study_version'],main_metrics=['success_rate','api_seconds_mean','estimated_usd_mean','fpr'],
        planned_episodes=108,completed_episodes=len(rows),complete_pairing=len(rows)==108,
        physical_groups=18,dev_samples=27,core_negative_samples=18,methods=methods,per_template=per_task,
        notes=notes,session=json.loads((out/'session/session_budget.json').read_text()),
        actual_models={b:sorted({r['returned_model'] for r in attempts if r['backend']==b and r['returned_model']}) for b in ('deepseek','jev')},
        pricing_sources=prices['sources'])
    write(dest/'summary.json',result)
    for name,data in [('episodes',rows),('methods',methods),('per_template',per_task),('attempt_costs',attempts),('paired_differences',pairs)]:csv_write(dest/(name+'.csv'),data)
    def n(v,d=2):return 'unknown' if v is None else f'{v:.{d}f}'
    def cells(r):
        fpr='— (disabled)' if r['method']=='llm_noask' else 'unknown' if r['fpr'] is None else f"{100*r['fpr']:.1f}% ({r['false_positives']}/{r['fpr_denominator']})"
        return [LABELS[r['method']],f"{r['successes']}/{r['scored']} ({100*r['success_rate']:.1f}%)" if r['success_rate'] is not None else 'unknown',
                n(r['api_seconds_mean'])+' s','$'+n(r['estimated_usd_mean'],6),fpr]
    headers=['Method','Success rate ↑','Mean API time ↓','Mean estimated USD ↓','Unnecessary ASK rate ↓']
    lines=['# Nine-task Dev: four headline metrics','','| '+' | '.join(headers)+' |','|'+'---|'*5]
    lines+=['| '+' | '.join(cells(r))+' |' for r in methods]
    lines+=['','Time and cost are **per episode means**, not totals. FPR uses only the 18 prelabelled core negatives.','',
        '## Coverage and interpretation','']+['- '+s for s in notes]
    lines+=['','## Per-task paired results','']
    for t in TEMPLATES:
        lines+=['### '+TASKS[t],'','| '+' | '.join(headers)+' |','|'+'---|'*5]
        lines+=['| '+' | '.join(cells(r))+' |' for r in per_task if r['template_id']==t]
        lines.append('')
    lines+=['Recompute: `.venv/bin/python script/benchmark.py report`. Raw records are in `../episodes/`; exact policy/data/model/budget hashes are in `../manifest.json`.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,4,figsize=(14,3.7));colors=['#8093a9','#3378b9','#178f95','#9656b4']
    for ax,k,title in zip(axs,['success_rate','api_seconds_mean','estimated_usd_mean','fpr'],
                          ['Physical success','Mean API time (s)','Mean estimated USD','Unnecessary ASK rate']):
        vals=[]
        for i,r in enumerate(methods):
            v=r[k]
            if v is None:ax.text(i,0,'N/A',ha='center',va='bottom',color='#667');continue
            vals.append(v);ax.bar(i,v,color=colors[i]);ax.text(i,v,n(v,5 if 'usd'in k else 2),ha='center',va='bottom',fontsize=9)
        ax.set_xticks(range(4),['NoAsk','LLM\nGate','Jev\nGate','Unified']);ax.set_title(title,fontsize=11)
        ax.set_ylim(0,1.2 if k=='success_rate' else 1.0 if k=='fpr' else max(vals+[.001])*1.3)
    fig.suptitle('Independent Dev pilot · Nine tasks · Four metrics');fig.tight_layout();fig.savefig(dest/'comparison.png',dpi=160);plt.close(fig)
    def table(rs):return '<div class="scroll"><table><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in cells(r))+'</tr>' for r in rs)+'</table></div>'
    body=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>When2Ask · Nine-task Dev</title><style>body{margin:0;background:#f3f6fa;color:#19334c;font:16px system-ui}main{max-width:1420px;margin:auto;padding:28px}section{background:white;border-radius:12px;padding:20px;margin:22px 0}img{max-width:100%}table{width:100%;border-collapse:collapse}th,td{padding:11px;text-align:left;border-bottom:1px solid #dbe4ed}th{background:#dce9f6}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}a{color:#2964a5}.scroll{overflow:auto}h3{font-size:17px}.tag{color:#8a6423}summary{cursor:pointer;padding:10px 0}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}</style><main><h1>When2Ask · Nine Tasks, Four Metrics</h1><p>Independent Dev pilot · 27 cases / 18 layout groups · Four methods · 18 fully specified cases test false alarms</p><img src="comparison.png" alt="Four primary metrics">',table(methods),
        '<p>Time and cost are per-task means. FPR counts tasks with any unnecessary ASK, not individual decision rounds. NoAsk cannot ask, so its FPR is not a Gate score.</p><p><a href="summary.json">Summary JSON</a> · <a href="episodes.csv">Episode metrics CSV</a> · <a href="attempt_costs.csv">Per-request usage and estimated cost</a></p>']
    for t in TEMPLATES:
        body+=['<section><h2>'+TASKS[t]+'</h2>',table([r for r in per_task if r['template_id']==t])]
        for sid,m in meta.items():
            if m['sample']['template_id']!=t:continue
            label='Fully specified · FPR negative' if m['fpr_core_negative'] else m['condition'].replace('_',' ')
            body+=['<details class="case"><summary>'+sid+' · '+html.escape(label)+'</summary><p>'+html.escape(m['sample']['u0'])+'</p><div class="cards">']
            for method in METHODS:
                e=next((e for e in episodes if e['sample_id']==sid and e['method']==method),None)
                if not e:body.append('<div>'+LABELS[method]+' · Not run</div>');continue
                row=next(r for r in rows if r['episode_id']==e['episode_id']);folder=os.path.relpath(out/'episodes'/e['episode_id'],dest)+'/'
                status='SUCCESS' if row['success'] else 'FAILED'
                body+=['<div><h3>'+LABELS[method]+' · '+status+'</h3><p class="tag">'+('False alarm: ASK on a fully specified task' if row['false_alarm'] else 'No false alarm observed' if row['false_alarm'] is False else 'FPR not applicable / censored')+'</p><img loading="lazy" src="'+folder+'final.png" alt="Real final PyBullet state"><a href="'+folder+'episode.json">Episode JSON</a> · <a href="'+folder+'api_attempts.jsonl">API log</a><details><summary>Question / action trace</summary>']
                for turn in e['turns']:
                    record={k:turn[k] for k in ('round','gate','unified_decision','question','user_answer','action','physical_result') if k in turn}
                    body.append('<pre>'+html.escape(json.dumps(record,indent=2))+'</pre>')
                body.append('</details></div>')
            body.append('</div></details>')
        body.append('</section>')
    body+=['<section><h2>Scope and limitations</h2><ul>']+['<li>'+html.escape(s)+'</li>' for s in notes]+['</ul></section></main></html>']
    (dest/'index.html').write_text(''.join(body))
    return result


def audit(*, source=None, destination=None, archived=False):
    out = source or OUT
    if archived:
        from .submission import ARCHIVE, verify_archive
        if out != ARCHIVE: raise ValueError('Unknown evidence directory')
        verify_archive()
    plan=json.loads((out/'manifest.json').read_text()) if archived else checked();paths=list((out/'episodes').glob('*/episode.json'));calls=[];seen=set();asks=0;unified_rounds=0
    public_forbidden={'theta_star','sample_id','group_id','partition','condition','fpr_core_negative','annotation_basis','source_dev_sample_id','task_success','expected_action','expected_gate'}
    def keys(v):
        if isinstance(v,dict):return set(v).union(*(keys(x) for x in v.values()))
        if isinstance(v,list):return set().union(*(keys(x) for x in v))
        return set()
    for p in paths:
        e=json.loads(p.read_text());seen.add((e['sample_id'],e['method']))
        ap=p.parent/'api_attempts.jsonl';rr=[json.loads(l) for l in ap.read_text().splitlines()] if ap.exists() else []
        calls+=rr
        assert e['partition']=='dev' and len(rr)<=32 and len(e['turns'])<=20 and len(e['actions'])<=12
        if e['evaluation']:
            assert e['evaluation']['task_success']==all(e['evaluation']['conditions'].values())
            assert e['evaluation']['clarification_burden']==sum(t['ask_check']['charged_slots'] for t in e['turns'] if 'ask_check'in t)
        for t in e['turns']:
            tr=[r for r in rr if r['round']==t['round']]
            if e['method']=='llm_unified':
                assert all(r['stage']=='unified' and r['backend']=='deepseek' for r in tr)
                assert sum(r['attempt']==1 for r in tr)<=1;unified_rounds+=1
                assert 'gate' not in t
            elif e['method']=='llm_noask':
                assert all(r['stage']=='action' for r in tr) and 'question' not in t
            else:assert not tr or tr[0]['stage']=='gate'
            if 'ask_check'in t:
                c=t['ask_check'];assert c['state_unchanged'] and c['before_step']==c['after_step'];asks+=1
        for r in rr:
            req=r.get('request')
            if not req:continue
            public=req['state'] if r['backend']=='jev' else json.loads(req['messages'][1]['content'])
            assert not keys(public)&public_forbidden
    ledger=json.loads((out/'session/session_budget.json').read_text())
    assert len(calls)==ledger['attempts']<=1600 and len(paths)==ledger['episodes']<=108
    result=dict(completed_episodes=len(paths),all_108_paired=seen=={(j['sample_id'],j['method']) for j in plan['jobs']},
        authenticated_attempts=len(calls),ask_turns_physics_frozen=asks,unified_rounds=unified_rounds,
        one_unified_call_per_round=True,private_labels_absent_from_payloads=True,physical_scores_match_conditions=True,
        saved_evidence_checksums_verified=archived,
        api_errors=sum(r['status']=='api_error' for r in calls),schema_errors=sum(r['status']=='schema_error' for r in calls),
        retries=sum(r.get('attempt',1)>1 for r in calls),unknown_usage_attempts=sum(r.get('input_tokens') is None or r.get('output_tokens') is None for r in calls))
    dest=destination or out
    dest.mkdir(parents=True,exist_ok=True)
    write(dest/'evidence_validation.json',result);return result
