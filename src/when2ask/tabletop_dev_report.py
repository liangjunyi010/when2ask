"""Descriptive Dev tables generated from real attempts and physical episodes."""
import csv
import html
import json

from .tabletop_dev_study import OUT, METHODS
from .tabletop_dev_agents import PROFILES, SELECTED
from .nine_task_data import write


def report():
    dest=OUT/'report';dest.mkdir(parents=True,exist_ok=True)
    probes=[json.loads(p.read_text()) for p in sorted((OUT/'probes').glob('*/result.json'))]
    episodes=[json.loads(p.read_text()) for p in sorted((OUT/'episodes').glob('*/episode.json'))]
    rows=[]
    expected_ask={'td1_pack_block_first':0,'td1_pack_continue_known_cup':1,
                  'td1_containers_block_first':0,'td1_containers_all_known':None}
    for e in episodes:
        asks=[t for t in e['turns'] if 'question' in t];c=e['cost'];ev=e['evaluation']
        first_after=sum('physical_result' in t for t in e['turns'] if asks and t['round']<asks[0]['round']) if asks else None
        known=set();initial=e['turns'][0]['public_payload'] if e['turns'] else {}
        # Request reuse is derived only from public roles in instruction/answers.
        from .study_protocol import disclosed_choices
        from .task import PublicState
        if e['turns']:
            value=initial['observation'];objects=value['objects']
            state=PublicState.build({**value,'objects':{o['object_id']:o for o in objects}},[],e['instruction'])
            known=set(disclosed_choices(state))
        redundant=0;requested=[]
        for t in asks:
            q=t['question'];roles=([r['role'] for r in q['requests']] if q['type']!='all_preferences' else
                ['cup','block','lid' if e['template_id']=='pack_and_cover' else 'cup_destination'])
            redundant+=len(set(roles)&known);known.update(roles);requested.extend(roles)
        repeated=len(requested)-len(set(requested));signatures={}
        for a in e['actions']:
            key=(a['skill'],a['object_id'],a['target_id']);signatures[key]=signatures.get(key,0)+1
        rows.append(dict(sample_id=e['sample_id'],profile=e['profile'],method=e['method'],
            success=bool(ev and ev['task_success']),scored=ev is not None,burden=ev['clarification_burden'] if ev else None,
            ask_turns=len(asks),first_ask_after_actions=first_after,expected_first_ask_after_actions=expected_ask[e['sample_id']],
            expected_ask_timing_match=(first_after==expected_ask[e['sample_id']]) if e['method']!='llm_noask' else None,
            redundant_role_requests=redundant,repeated_role_requests=repeated,
            actions=len(e['actions']),physical_failures=sum(not a['success'] for a in e['actions']),
            maximum_identical_action_count=max(signatures.values(),default=0),
            termination=e['termination_reason'],error=e['error'],api_attempts=c['api_attempts'],schema_errors=c['schema_errors'],
            api_errors=c['api_errors'],retries=c['retries'],api_latency_s=c['api_latency_ms']/1000 if c['api_latency_ms'] is not None else None,
            **{b+'_'+k:c[b][k] for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')}))
    summary=[]
    for profile in ('raw_legacy',SELECTED):
        for method in METHODS:
            rr=[r for r in rows if r['profile']==profile and r['method']==method]
            def total(key):
                values=[r[key] for r in rr if r[key] is not None]
                return sum(values) if values else None
            summary.append(dict(profile=profile,method=method,episodes=len(rr),successes=sum(r['success'] for r in rr),
                burden_total=total('burden'),burden_mean=total('burden')/len(rr) if rr and total('burden') is not None else None,
                first_ask_reference_matches=sum(r['expected_ask_timing_match'] is True for r in rr),
                **{k:total(k) for k in ('api_attempts','schema_errors','api_errors','retries','api_latency_s','redundant_role_requests','repeated_role_requests',
                    'deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens')}))
    factor=[]
    for profile in PROFILES:
        for method in ('llm_gate','jev_gate','llm_noask'):
            rr=[r for r in probes if r['profile']==profile and r['method']==method]
            factor.append(dict(profile=profile,stage='action' if method=='llm_noask' else 'gate',method=method,
                states=len(rr),reference_matches=sum(r['match'] for r in rr),errors=sum(r['error'] is not None for r in rr)))
    ledger=json.loads((OUT/'session/session_budget.json').read_text())
    result=dict(study_version='tabletop_contract_dev_v1',scope='Dev-only repair/regression; NOT new held-out results.',
        episodes=len(episodes),expected_episodes=24,probe_calls=len(probes),expected_probe_calls=56,
        groups=4,case_variants=4,threshold=.5,methods=summary,factor_diagnostics=factor,
        authenticated_attempts=ledger['attempts'],registered_episodes=ledger['episodes'],
        known_limits=['Four Dev layouts selected to reproduce public-order and partial-progress failure mechanisms, not randomly sampled for generalization.',
            'Original frozen Test failures informed development; any new claim needs a fresh frozen held-out study. Historical54 episodes and metrics remain unchanged.',
            'Same structured public facts and shared Planner configuration for all three methods within each profile.',
            'Small deterministic-state ablations identify sensitivity, not the hidden internal reasoning of a model.',
            'First-ASK references describe only these explicit controlled Dev cases, not universal optimal timing. NoAsk has no Gate accuracy score.',
            'Both gates can still fail. Threshold is unchanged; no action is rewritten and no deterministic controller supplies a Gate decision.',
            'Jev/DeepSeek tokens stay separate; cumulative API latency excludes physics/user response time. Unused-backend totals are null, never fabricated zeros.'])
    write(dest/'summary.json',result)
    for name,values in [('episodes',rows),('methods',summary),('factor_diagnostics',factor),('probes',probes)]:
        with (dest/(name+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]) if values else [])
            writer.writeheader();writer.writerows(values)
    lines=['# Tabletop contract Dev repair','',result['scope'],'',
        '| Profile | Method | Success | Slots requested | First-ASK reference matches | API latency |',
        '|---|---|---:|---:|---:|---:|']
    for r in summary:
        latency='unknown' if r['api_latency_s'] is None else f"{r['api_latency_s']:.2f}s"
        timing='N/A' if r['method']=='llm_noask' else f"{r['first_ask_reference_matches']}/{r['episodes']}"
        lines.append(f"| {r['profile']} | {r['method']} | {r['successes']}/{r['episodes']} | {r['burden_total']} | {timing} | {latency} |")
    lines+=['','## Fixed-state 2×2 diagnostic','',
        '| Public representation / prompt | LLM Gate | Jev Gate | Planner next-action reference |',
        '|---|---:|---:|---:|']
    for profile in PROFILES:
        ff=[next(r for r in factor if r['profile']==profile and r['method']==m) for m in ('llm_gate','jev_gate','llm_noask')]
        lines.append('| '+profile+' | '+' | '.join(f"{r['reference_matches']}/{r['states']}" for r in ff)+' |')
    lines+=['','## Every paired episode','',
        '| Case | Profile | Method | Success | Burden | First ASK after actions | Robot actions | Termination |',
        '|---|---|---|---:|---:|---:|---:|---|']
    for r in rows:
        lines.append(f"| {r['sample_id']} | {r['profile']} | {r['method']} | {r['success']} | {r['burden']} | {r['first_ask_after_actions']} | {r['actions']} | {r['termination']} |")
    lines+=['','## Failures preserved','']
    for e in episodes:
        if not e['evaluation'] or not e['evaluation']['task_success']:
            failed=[k for k,v in (e['evaluation'] or {}).get('conditions',{}).items() if not v]
            lines.append(f"- {e['episode_id']}: {', '.join(failed) or e['error']}.")
    lines+=['','## Interpretation','']+['- '+v for v in result['known_limits']]
    lines+=['','Run `.venv/bin/python scripts/tabletop_contract_dev.py report` to recompute from raw files. '
        'Full request/response/usage JSONL and PyBullet logs are in ../probes/ and ../episodes/. '
        'The protocol, prompt/data/source hashes and randomized run list are in ../manifest.json.']
    (dest/'README.md').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,4.4));colors={'llm_noask':'#92a6ba','llm_gate':'#2456a1','jev_gate':'#1396a4'}
    for i,method in enumerate(METHODS):
        rr=[next(r for r in summary if r['profile']==p and r['method']==method) for p in ('raw_legacy',SELECTED)]
        xs=[i-.18,i+.18]
        bars=ax.bar(xs,[r['successes'] for r in rr],width=.32,color=[colors[method]]*2,alpha=.9)
        bars[0].set_hatch('//');bars[0].set_alpha(.45)
        for x,r in zip(xs,rr):ax.text(x,r['successes']+.08,f"{r['successes']}/4",ha='center')
    ax.set_xticks(range(3),['NoAsk','LLM-Gate','Jev-Gate (0.5)']);ax.set_ylim(0,4.6);ax.set_yticks(range(5))
    ax.set_title('Dev repair regression · 4 controlled cases\nHatched: original profile · Solid: public facts + clarified contract')
    ax.set_ylabel('Successful physical episodes');fig.tight_layout();fig.savefig(dest/'dev_results.png',dpi=180);plt.close(fig)
    body=['<!doctype html><html lang="en"><meta charset="utf-8"><title>When2Ask · Tabletop Dev Repair</title><style>body{font:17px system-ui;background:#f3f6fa;color:#19314c;margin:0}main{max-width:1260px;margin:auto;padding:32px}table{border-collapse:collapse;width:100%;background:white}td,th{padding:10px;border-bottom:1px solid #dbe4ed;text-align:left}th{background:#dce9f6}section{background:white;border-radius:12px;margin:20px 0;padding:20px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}img{max-width:100%}pre{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}a{color:#1e64a4}</style><main><h1>When2Ask · Tabletop Dev Repair</h1><p>Public-state and task-contract diagnostics · 4 Dev cases · Original Test records remain unchanged</p>',
        '<img src="dev_results.png" alt="Original versus repaired Dev profile success"><table><tr><th>Profile</th><th>Method</th><th>Success</th><th>Slots requested</th><th>Total API latency</th></tr>']
    for r in summary:
        body.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['profile'],r['method'],str(r['successes'])+'/'+str(r['episodes']),r['burden_total'],round(r['api_latency_s'],2) if r['api_latency_s'] is not None else 'unknown'])+'</tr>')
    body.append('</table><p>Descriptive Dev regression, not a new held-out or statistical claim. Unknown preferences may be guessed correctly; fewer questions alone do not prove better timing.</p>')
    for profile in ('raw_legacy',SELECTED):
        for sample_id in sorted({e['sample_id'] for e in episodes}):
            body.append('<section><h2>'+html.escape(sample_id+' · '+profile)+'</h2><div class="cards">')
            for method in METHODS:
                es=[e for e in episodes if e['sample_id']==sample_id and e['profile']==profile and e['method']==method]
                if not es:body.append('<div>Not run</div>');continue
                e=es[0];folder='../episodes/'+e['episode_id']+'/'
                body.append('<div><h3>'+method+' · '+('SUCCESS' if e['evaluation'] and e['evaluation']['task_success'] else 'FAILED')+'</h3><img src="'+folder+'final.png" alt="Actual final PyBullet state"><a href="'+folder+'episode.json">Full episode</a><details><summary>Questions and actions</summary>')
                for t in e['turns']:
                    text='Round '+str(t['round'])+' · '+str(t['gate'])
                    if 'question' in t:text+='\nASK: '+t['question']['text']+'\nUSER: '+json.dumps(t['user_answer'])
                    if 'action' in t:text+='\n'+json.dumps(t['action'])
                    body.append('<pre>'+html.escape(text)+'</pre>')
                body.append('</details></div>')
            body.append('</div></section>')
    body.append('</main></html>');(dest/'index.html').write_text(''.join(body))
    return result
