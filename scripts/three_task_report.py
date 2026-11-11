"""Offline v8 aggregation, paired group analysis and presentation-ready figures."""
import argparse,csv,hashlib,json,math,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from when2ask.config import ROOT
from when2ask.three_task_benchmark import OUT,checked,METHODS
from when2ask.three_task_data import load
from when2ask.memory_dev_public import serialize
from when2ask.gate_contract_dev import compact
from when2ask.task6_protocol import scripted_next,known_choices


def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
def records(path):return [json.loads(s) for s in path.read_text().splitlines()]
def wilson(k,n):
    if not n:return [None,None]
    z=1.96;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,c-r),min(1,c+r)]
def total(values):
    selected=[v for v in values if v is not None];return sum(selected) if selected else None


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--export-media',action='store_true');a=parser.parse_args()
    plan=checked();report=OUT/'report';report.mkdir(exist_ok=True);sample_map={s.sample_id:s for s in load(plan['revision'],'test')};episodes=[];rows=[];all_api=[];audits=[]
    for job in plan['jobs']:
        path=OUT/'test_runs'/job['episode_id']/'episode.json'
        if not path.exists():continue
        e=json.loads(path.read_text());episodes.append(e);api=records(path.with_name('api_attempts.jsonl'));all_api+=api;prior=[];early=miss=redundant=0;gate_rows=[]
        for t in e['turns']:
            assert t['public_payload']==serialize(t['raw_public_payload'],prior);prior.append(t['raw_public_payload']['observation'])
            calls=[r for r in api if r['round']==t['round']]
            if e['method']=='llm_noask':assert not any(r['stage']=='gate' for r in calls)
            elif calls:assert calls[0]['stage']=='gate'
            if t['gate']['called']:
                assert t['gate_payload']==compact(t['public_payload'])
                reference='ASK' if scripted_next(t['public_payload'],known_only=True) is None else 'CONTINUE'
                actual=t['gate']['decision'];early+=actual=='ASK' and reference=='CONTINUE';miss+=actual=='CONTINUE' and reference=='ASK'
                gate_rows.append(dict(round=t['round'],step=t['public_payload']['observation']['simulation_step'],actual=actual,public_reference=reference,p_ask=t['gate']['p_ask']))
            for r in calls:
                wire=json.loads(r['request']['messages'][1]['content']) if r['backend']=='deepseek' else r['request']['state']
                assert wire==(t['gate_payload'] if r['stage']=='gate' else t['public_payload'])
            if 'model_plan' in t:assert t['action']==t['model_plan']['remaining_plan'][0]
            if 'ask_check' in t:
                assert t['ask_check']['state_unchanged'] and t['ask_check']['before_step']==t['ask_check']['after_step']
                q=t['question'];roles=set(t['public_payload']['observation']['task']['preference_slots']) if q['type']=='all_preferences' else {r['role'] for r in q['requests']}
                redundant+=len(roles & set(known_choices(t['public_payload'])))
        ev=e['evaluation'];cost=e['cost'];s=sample_map[e['sample_id']]
        row=dict(sample_id=e['sample_id'],group_id=e['group_id'],template=e['task_template'],method=e['method'],unknown_slots=e['unknown_slots'],
            task_success=ev['task_success'] if ev else None,burden=ev['clarification_burden'] if ev else None,ask_turns=sum('question' in t for t in e['turns']),
            actions=len(e['actions']),physical_failures=sum(not r['success'] for r in e['actions']),
            early_asks_exploratory=early,missed_asks_exploratory=miss,repeated_slot_requests=redundant,
            api_attempts=len(api),schema_errors=cost['schema_errors'],api_errors=cost['api_errors'],retries=cost['retries'],
            api_latency_s=cost['api_latency_ms']/1000 if cost['api_latency_ms'] is not None else None,wall_s=e['wall_time_s'],
            deepseek_input_tokens=cost['deepseek']['input_tokens'],deepseek_output_tokens=cost['deepseek']['output_tokens'],
            jev_input_tokens=cost['jev']['input_tokens'],jev_output_tokens=cost['jev']['output_tokens'],
            termination=e['termination_reason'],error=e['error'],failed_conditions=[k for k,v in ev['conditions'].items() if not v] if ev else None)
        rows.append(row);audits.append(dict(episode_id=job['episode_id'],wire_payloads_valid=True,public_memory_recomputes=True,gate_before_planner=True,
            first_action_verbatim=True,ask_freeze_checks=sum('ask_check' in t for t in e['turns']),gate_decisions=gate_rows))
    for sid in sample_map:
        paired=[e for e in episodes if e['sample_id']==sid]
        if len(paired)==3:assert len({e['turns'][0]['payload_sha256'] for e in paired})==1
    session=json.loads((OUT/'session/session_budget.json').read_text());assert len(all_api)==session['attempts']<=450
    protected=json.loads((OUT/'preserved_file_hashes.json').read_text());assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==d for p,d in protected.items())
    method_rows=[];breakdown=[]
    for method in METHODS:
        rr=[r for r in rows if r['method']==method];scored=[r for r in rr if r['task_success'] is not None];n=len(scored);wins=sum(r['task_success'] for r in scored)
        v=dict(method=method,scored=n,planned=12,successes=wins,success_rate=wins/n if n else None,group_wilson95=wilson(wins,n),
            burden_total=total(r['burden'] for r in scored),burden_mean=float(np.mean([r['burden'] for r in scored])) if n else None,
            actions=sum(r['actions'] for r in rr),physical_failures=sum(r['physical_failures'] for r in rr),api_attempts=sum(r['api_attempts'] for r in rr),
            api_latency_s=total(r['api_latency_s'] for r in rr),early_asks_exploratory=sum(r['early_asks_exploratory'] for r in rr),
            missed_asks_exploratory=sum(r['missed_asks_exploratory'] for r in rr),schema_errors=sum(r['schema_errors'] for r in rr),retries=sum(r['retries'] for r in rr))
        for key in ['deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens']:v[key]=total(r[key] for r in rr)
        method_rows.append(v)
        for template in sorted({s.template_id for s in sample_map.values()}):
            for unknown in [0,1]:
                selected=[r for r in scored if r['template']==template and r['unknown_slots']==unknown]
                breakdown.append(dict(method=method,template=template,unknown=unknown,n=len(selected),successes=sum(r['task_success'] for r in selected),burden=sum(r['burden'] for r in selected)))
    paired=[];rng=np.random.default_rng(42781116)
    if len(rows)==36:
        for first,second in [('llm_gate','llm_noask'),('jev_gate','llm_noask'),('jev_gate','llm_gate')]:
            strata=[]
            for template in sorted({s.template_id for s in sample_map.values()}):
                ids=[s.sample_id for s in sample_map.values() if s.template_id==template]
                deltas=[]
                for sid in ids:
                    x=next(r for r in rows if r['sample_id']==sid and r['method']==first);y=next(r for r in rows if r['sample_id']==sid and r['method']==second)
                    deltas.append(float(x['task_success'])-float(y['task_success']))
                strata.append(np.asarray(deltas))
            boot=np.mean(np.concatenate([v[rng.integers(0,len(v),(5000,len(v)))] for v in strata],axis=1),axis=1)
            paired.append(dict(first=first,second=second,group_paired_sr_difference=float(np.mean(np.concatenate(strata))),
                bootstrap95=[float(x) for x in np.quantile(boot,[.025,.975])],independent_groups=12,
                policy='Exploratory stratified paired group bootstrap; each template contributes4 groups. No significance claim, no variants counted independently.',
                warning='No observed discordant outcomes; a degenerate empirical interval is not evidence of population equivalence.' if np.all(np.concatenate(strata)==0) else None))
    summary=dict(experiment_id=plan['experiment_id'],dataset_version=plan['dataset_version'],revision=plan['revision'],
        completed=len(rows),planned=36,independent_test_groups=12,test_samples=12,dev_samples=24,
        oracle=dict(successes=36,total=36),methods=method_rows,template_disclosure_breakdown=breakdown,paired_group_analysis=paired,
        total_authenticated_requests=len(all_api),budget=450,api_errors=sum(r['status']=='api_error' for r in all_api),schema_errors=sum(r['status']=='schema_error' for r in all_api),
        retries=sum(r.get('attempt',1)>1 for r in all_api),returned_models={b:sorted({r['returned_model'] for r in all_api if r['backend']==b and r.get('returned_model')}) for b in ['deepseek','jev']},
        protected_files=len(protected),notes=['Small genuinely held-out layout Test for the three new templates, independent of original128-Test.',
            'Source/prompts/models/threshold frozen before Test, all Test samples paired across methods; no whole-episode retries or sample exclusions.',
            'Early/missed ASK counts are EXPLORATORY post-Test public-DAG/scripted support diagnostics, not preregistered optimal-timing labels. No private preference is used for this reference.',
            'Physical oracle knows private preference only for feasibility; its trajectories are never agent inputs.'])
    write(report/'summary.json',summary);write(report/'episodes.json',rows);write(report/'mapping_validation.json',dict(episodes=audits,paired_initial_public_inputs_match=True,protected_files=len(protected)))
    for name,data in [('episodes.csv',rows),('methods.csv',method_rows),('disclosure_breakdown.csv',breakdown)]:
        with (report/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    # Standard plotting library; numeric values and uncertainty derive from raw logs.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    labels=['NoAsk','LLM-Gate','Jev-Gate'];colors=['#8593a6','#2469b3','#e49038'];fig,axes=plt.subplots(1,3,figsize=(13.4,4.4))
    vals=[r['success_rate'] for r in method_rows];intervals=[r['group_wilson95'] for r in method_rows]
    axes[0].bar(labels,vals,color=colors,width=.65);axes[0].errorbar(range(3),vals,yerr=[[v-c[0] for v,c in zip(vals,intervals)],[c[1]-v for v,c in zip(vals,intervals)]],fmt='none',color='#273b55',capsize=4)
    axes[0].set_ylim(0,1.16);axes[0].set_title('Task success (12 held-out groups)');axes[0].set_ylabel('Success rate (group Wilson 95% CI)')
    for i,r in enumerate(method_rows):axes[0].text(i,r['success_rate']+.035,f"{r['successes']}/12",ha='center')
    axes[1].bar(labels,[r['burden_mean'] for r in method_rows],color=colors,width=.65);axes[1].set_title('Clarification burden');axes[1].set_ylabel('Requested distinct slots / episode')
    axes[2].bar(labels,[r['api_latency_s']/12 for r in method_rows],color=colors,width=.65);axes[2].set_title('Agent API latency');axes[2].set_ylabel('Mean cumulative API seconds / episode')
    fig.suptitle('When2Ask v8 · Small held-out three-task Benchmark',fontsize=14,fontweight='bold');fig.text(.5,.015,'12 independent layouts · All 3 methods paired · Fixed 0.5 threshold · Separate from original 128-Test',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(report/'benchmark_summary.png',dpi=180);fig.savefig(report/'benchmark_summary.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.4,6.5));ids=sorted(sample_map);matrix=np.array([[next(r['task_success'] for r in rows if r['sample_id']==sid and r['method']==m) for m in METHODS] for sid in ids],dtype=int)
    from matplotlib.colors import ListedColormap
    ax.imshow(matrix,aspect='auto',cmap=ListedColormap(['#eec6c2','#b9ddce']),vmin=0,vmax=1)
    ax.set_xticks(range(3),labels);ax.set_yticks(range(12),[sample_map[sid].template_id.replace('_',' ')+' · '+sid.split('_')[-2]+' · '+('unknown' if not sample_map[sid].initial_disclosed_slots else 'known') for sid in ids],fontsize=9)
    for i in range(12):
        for j in range(3):ax.text(j,i,'PASS' if matrix[i,j] else 'FAIL',ha='center',va='center',fontsize=9)
    ax.set_title('All held-out samples · paired physical evaluation');fig.tight_layout();fig.savefig(report/'paired_outcomes.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.1));unknown_retrieval=[sid for sid,s in sample_map.items() if s.template_id=='retrieve_restore' and not s.initial_disclosed_slots]
    for y,sid in enumerate(sorted(unknown_retrieval)):
        for method,color,label,dy in [('llm_gate','#2469b3','LLM-Gate',-.10),('jev_gate','#e49038','Jev-Gate',.10)]:
            episode=next(e for e in episodes if e['sample_id']==sid and e['method']==method)
            first=next((t for t in episode['turns'] if 'question' in t),None)
            if first:
                x=sum(h['kind']=='action' for h in first['raw_public_payload']['history'])
                ax.scatter(x,y+dy,color=color,s=120,label=label if y==0 else None,zorder=3)
                ax.text(x+.03,y+dy,'ASK',va='center',fontsize=10)
    ax.set_xticks([0,1],['0 · before opening','1 · after opening']);ax.set_xlim(-.22,1.30)
    ax.set_yticks(range(len(unknown_retrieval)),['Held-out layout '+sid.split('_')[-2] for sid in sorted(unknown_retrieval)])
    ax.set_xlabel('Completed physical actions when first clarification occurs');ax.set_title('Exploratory timing: two unknown-item retrieval cases')
    ax.legend(loc='upper center',ncol=2,bbox_to_anchor=(.5,1.0));ax.grid(axis='x',alpha=.2)
    fig.text(.5,.02,'Post-Test diagnostic; public DAG supports opening before the missing item choice. Not a preregistered timing metric.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(report/'clarification_timing.png',dpi=180);plt.close(fig)
    lines=['# Three-task Benchmark v8 — held-out paired Test','',*summary['notes'],'',
        '| Method | Success | Mean burden | DeepSeek in/out | Jev in/out | Total API latency | Physical failures |','|---|---:|---:|---|---|---:|---:|']
    for r in method_rows:lines.append(f"| {r['method']} | {r['successes']}/12 | {r['burden_mean']:.3f} | {r['deepseek_input_tokens']}/{r['deepseek_output_tokens']} | {r['jev_input_tokens']}/{r['jev_output_tokens']} | {r['api_latency_s']:.2f}s | {r['physical_failures']} |")
    lines+=['',f"All {len(rows)}/36 planned episodes retained; {len(all_api)}/450 authenticated requests. Oracle36/36, actual offline Test source/prompt/config hashes verified. Group Wilson intervals and paired bootstrap are descriptive; only12 independent groups.",'',
        '## Physical/model failures','']
    for e in episodes:
        failed=[a for a in e['actions'] if not a['success']]
        if failed or not e['evaluation']['task_success']:lines.append(f"- {e['sample_id']} / {e['method']}: task_success={e['evaluation']['task_success']}; failed conditions={[k for k,v in e['evaluation']['conditions'].items() if not v]}; rejected skill attempts={failed}")
    lines+=['','## Exploratory ASK timing','',
        'Reference uses only the public DAG/observations and the unchanged scripted support policy after Test. It is an explanatory diagnostic, not an optimal oracle or a tuning signal. NoAsk does not call Gate and is not scored as a Gate classifier.']
    for r in method_rows:
        if r['method']=='llm_noask':lines.append('- NoAsk: Gate skipped; classifier timing metric is not applicable.')
        else:lines.append(f"- {r['method']}: early/unnecessary asks={r['early_asks_exploratory']}, missed blocking asks={r['missed_asks_exploratory']}.")
    lines+=['','## Paired group uncertainty','',json.dumps(paired),'',
        'Rows, attempted skill failures, full costs, source hashes and all API attempts are retained. No prompt/threshold/controller repair was made after Test outcomes. Original frozen128-Test and all its historical records were left untouched.']
    (report/'report.md').write_text('\n'.join(lines)+'\n')
    if a.export_media:
        media=ROOT/'presentation/three_task_v8/media';media.mkdir(parents=True,exist_ok=True);manifest=[]
        for e in episodes:
            src=OUT/'test_runs'/(e['sample_id']+'__'+e['method'])/'demo.gif'
            if not src.exists():continue
            dest=media/(src.parent.name+'.mp4')
            subprocess.run(['/opt/homebrew/bin/ffmpeg','-y','-loglevel','error','-i',str(src),'-vf','scale=960:-2','-c:v','libx264','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
            probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','quiet','-show_format','-of','json',str(dest)]))
            manifest.append(dict(sample_id=e['sample_id'],template=e['task_template'],method=e['method'],file=dest.name,success=e['evaluation']['task_success'],
                bytes=dest.stat().st_size,duration_s=float(probe['format']['duration']),sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
        write(media.parent/'media_manifest.json',manifest)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
