"""Offline explanation and presentation rendering; never changes frozen policies."""
import csv
import html
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.metrics_dev_study import checked,METHODS
from when2ask.metrics_dev_data import OUT
from when2ask.nine_task_data import write


def main():
    checked();dest=OUT/'report';summary=json.loads((dest/'summary.json').read_text())
    attempts=[];failures=[];skill_rejections=[]
    for p in sorted((OUT/'episodes').glob('*/episode.json')):
        e=json.loads(p.read_text())
        ap=p.parent/'api_attempts.jsonl';rows=[json.loads(l) for l in ap.read_text().splitlines()]
        attempts+=rows
        if e['evaluation'] and not e['evaluation']['task_success']:
            failures.append(dict(episode_id=e['episode_id'],instruction=e['instruction'],
                failed_conditions=[k for k,v in e['evaluation']['conditions'].items() if not v],
                actions=[t['action'] for t in e['turns'] if 'action'in t],termination=e['termination_reason']))
        for a in e['actions']:
            if not a['success']:skill_rejections.append(dict(episode_id=e['episode_id'],result=a,final_task_success=e['evaluation']['task_success']))
    folder=OUT/'episodes';same_request=[]
    a=folder/'md1_04_1__llm_noask/api_attempts.jsonl';b=folder/'md1_04_1__llm_gate/api_attempts.jsonl'
    for x in [json.loads(l) for l in a.read_text().splitlines()]:
        for y in [json.loads(l) for l in b.read_text().splitlines()]:
            if x['request']!=y['request']:continue
            xo=x['response']['choices'][0]['message']['content'];yo=y['response']['choices'][0]['message']['content']
            if xo==yo:continue
            same_request.append(dict(noask_round=x['round'],llm_gate_round=y['round'],
                request_dicts_equal=True,request_bytes_equal=json.dumps(x['request']).encode()==json.dumps(y['request']).encode(),
                request_sha256=hashlib.sha256(json.dumps(x['request']).encode()).hexdigest(),
                noask_output=xo,llm_gate_output=yo,
                noask_fingerprint=x['response'].get('system_fingerprint'),llm_gate_fingerprint=y['response'].get('system_fingerprint'),
                noask_source=str(a.relative_to(OUT)),llm_gate_source=str(b.relative_to(OUT))))
    costs=list(csv.DictReader((dest/'attempt_costs.csv').open()));cache=[]
    for method in METHODS:
        rows=[r for r in costs if r['method']==method and r['backend']=='deepseek']
        hit=sum(int(r['cache_hit_tokens']) for r in rows);miss=sum(int(r['cache_miss_tokens']) for r in rows)
        cache.append(dict(method=method,cache_hit_tokens=hit,cache_miss_tokens=miss,hit_fraction=hit/(hit+miss)))
    result=dict(kind='post_run_read_only_diagnostics',failures=failures,skill_rejections=skill_rejections,
        schema_errors=dict(Counter(r.get('error') for r in attempts if r['status']=='schema_error')),
        matched_request_different_response=same_request,deepseek_cache=cache,
        time_range_utc=[min(r['request_started_at_utc'] for r in attempts),max(r['request_started_at_utc'] for r in attempts)],
        interpretation=[
            'All three asking methods have zero observed false alarms on 18 fully disclosed tasks. This small explicit-information negative set does not distinguish their false-alarm behavior.',
            'NoAsk has four failures in undisclosed-preference controls and two in fully disclosed inventory tasks. These cannot all be attributed to missing clarification.',
            'The quota=3 fully disclosed inventory task ends early for NoAsk, Jev-Gate and Unified. Separate LLM-Gate adds the missing block and succeeds.',
            'An identical recorded DeepSeek action request returned DONE for NoAsk and a block-placement action for LLM-Gate. Cause is unobserved; success differences are not solely evidence of better gating.',
            'The retrieval skill rejected move(lid,box) before advancing physics; the model subsequently used cover and completed. The failure is retained and final success is based on real final conditions.',
            'The frozen global random order is not block balanced over time. Cache mix and provider timing are observed confounders; costs are estimates, no universal cheapest/fastest or statistical claim.',
            'All 21 schema/affordance repair attempts are charged in latency, tokens and cost. No API outages, missing usage or censored core negatives occurred.'])
    write(dest/'diagnostics.json',result)
    # Presentation-only rendering: same four metrics and exact original data.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,4,figsize=(14,3.7));colors=['#8093a9','#3378b9','#178f95','#9656b4']
    for ax,k,title in zip(axs,['success_rate','api_seconds_mean','estimated_usd_mean','fpr'],
        ['Physical success','Mean API time (s)','Mean estimated USD','Unnecessary ASK rate']):
        vals=[]
        for i,r in enumerate(summary['methods']):
            v=r[k]
            if v is None:ax.text(i,.035,'N/A',ha='center',va='bottom',color='#667',fontsize=9);continue
            vals.append(v);ax.bar(i,v,color=colors[i])
            text=f"{r['false_positives']}/{r['fpr_denominator']}" if k=='fpr' else f'{v:.5f}' if 'usd'in k else f'{v:.2f}'
            ax.text(i,max(v,.035) if k=='fpr' else v,text,ha='center',va='bottom',fontsize=9)
        ax.set_xlim(-.6,3.6);ax.set_xticks(range(4),['NoAsk','LLM\nGate','Jev\nGate','Unified']);ax.set_title(title,fontsize=11)
        ax.set_ylim(0,1.2 if k=='success_rate' else 1.0 if k=='fpr' else max(vals+[.001])*1.3)
    fig.suptitle('Independent Dev pilot · Nine tasks · Four metrics');fig.tight_layout();fig.savefig(dest/'comparison.png',dpi=160);plt.close(fig)
    page=dest/'index.html';content=page.read_text();marker='<section id="post-run-diagnostics">'
    if marker in content:
        start=content.index(marker);end=content.index('</section>',start)+len('</section>')
        content=content[:start]+content[end:]
    block=marker+'<h2>What these runs show</h2><ul>'+''.join('<li>'+html.escape(s)+'</li>' for s in result['interpretation'])+'</ul><p><a href="diagnostics.json">Failure and request evidence</a></p></section>'
    page.write_text(content.replace('</main>',block+'</main>'))
    print(json.dumps(dict(failure_episodes=len(failures),retained_skill_rejections=len(skill_rejections),
        identical_request_output_disagreements=len(same_request),schema_errors=sum(result['schema_errors'].values())),indent=2))


if __name__=='__main__':main()
