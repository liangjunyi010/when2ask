"""Offline aggregation/audit of the nine new Dev episodes. No API requests."""
import argparse,csv,hashlib,html,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.grounded_dev_public import PROFILE,serialize
from when2ask.buffer_public_dev import diagnose_action
from when2ask.task6_agents import prompt_hashes as default_hashes

OUT=ROOT/'outputs/grounded_planner_dev_v5'
def read(p):return json.loads(p.read_text())
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--export-media',action='store_true');args=parser.parse_args()
    plan=read(OUT/'live_plan_r2.json');validation=read(OUT/'live_validation.json')
    assert validation['episodes']==9
    all_records=[];rows=[];audits=[];episodes=[]
    for path in sorted((OUT/'live').glob('*/episode.json')):
        e=read(path);episodes.append(e);records=[json.loads(s) for s in path.with_name('api_attempts.jsonl').read_text().splitlines()]
        all_records+=records;cost=e['cost'];ev=e['evaluation'];template=e['task_template']
        comparisons=[]
        for turn in e['turns']:
            assert turn['public_payload']==serialize(turn['raw_public_payload'])
            calls=[r for r in records if r['round']==turn['round']]
            for r in calls:
                request=r['request'];wire=(json.loads(request['messages'][1]['content']) if r['backend']=='deepseek' else request['state'])
                assert wire==turn['public_payload'],'Wire public state mismatch'
                assert e['planner_profile']==PROFILE
            if e['method']=='llm_noask':assert not any(r['stage']=='gate' for r in calls)
            elif calls:
                assert calls[0]['stage']=='gate','Planner called before Gate'
            if 'model_plan' in turn:assert turn['action']==turn['model_plan']['remaining_plan'][0]
            if 'ask_check' in turn:assert turn['ask_check']['state_unchanged'] and turn['ask_check']['before_step']==turn['ask_check']['after_step']
            if template=='buffer_exchange' and 'action' in turn:comparisons.append(diagnose_action(turn['raw_public_payload'],turn['action']))
        gate_sequence=[dict(round=t['round'],decision=t['gate']['decision'],p_ask=t['gate']['p_ask'],
                            step=t['raw_public_payload']['observation']['simulation_step'],
                            action=t.get('action'),question=t.get('question'),answer=t.get('user_answer')) for t in e['turns']]
        row=dict(template=template,method=e['method'],episode_id=e['episode_id'],task_success=ev['task_success'],
            burden=ev['clarification_burden'],ask_turns=sum('question' in t for t in e['turns']),actions=len(e['actions']),
            physical_failures=sum(not a['success'] for a in e['actions']),
            regressions=sum(d.get('undoes_currently_satisfied_final_relation',False) for d in comparisons),
            attempts=len(records),latency_s=cost['api_latency_ms']/1000 if cost['api_latency_ms'] is not None else None,
            deepseek_input_tokens=cost['deepseek']['input_tokens'],deepseek_output_tokens=cost['deepseek']['output_tokens'],
            jev_input_tokens=cost['jev']['input_tokens'],jev_output_tokens=cost['jev']['output_tokens'],schema_errors=cost['schema_errors'],
            termination=e['termination_reason'],error=e['error'],failed_conditions=[k for k,v in ev['conditions'].items() if not v])
        rows.append(row);audits.append(dict(episode_id=e['episode_id'],template=template,method=e['method'],wire_payload_valid=True,
            gate_before_planner=True,first_model_action_executed_verbatim=True,ask_state_unchanged=True,gate_sequence=gate_sequence))
    assert len(rows)==9
    for template in {e['task_template'] for e in episodes}:
        es=[e for e in episodes if e['task_template']==template]
        assert len(es)==3 and len({e['comparison_id'] for e in es})==1
        assert len({e['turns'][0]['payload_sha256'] for e in es})==1
        assert all(e['prompt_hashes']==plan['prompt_hashes'] for e in es)
    assert len(all_records)==validation['authenticated_requests'] and len(all_records)+6<=150
    unchanged=read(OUT/'preserved_file_hashes.json');changed=[p for p,d in unchanged.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=d]
    assert not changed,changed
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==d for p,d in plan['source_hashes'].items())
    groups=[]
    for method in plan['methods']:
        selected=[r for r in rows if r['method']==method]
        g=dict(method=method,episodes=len(selected),successes=sum(r['task_success'] for r in selected),burden=sum(r['burden'] for r in selected),
            actions=sum(r['actions'] for r in selected),latency_s=sum(r['latency_s'] or 0 for r in selected),attempts=sum(r['attempts'] for r in selected))
        for key in ['deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens']:
            values=[r[key] for r in selected if r[key] is not None];g[key]=sum(values) if values else None
        groups.append(g)
    preflight=[json.loads(line) for p in (OUT/'preflight_r1').glob('*/api_attempts.jsonl') for line in p.read_text().splitlines()]
    assert len(preflight)==6
    def totals(records):
        result={}
        for backend in ('deepseek','jev'):
            rs=[r for r in records if r['backend']==backend]
            result[backend]=dict(attempts=len(rs),**{k:sum(r[k] for r in rs if r.get(k) is not None) if any(r.get(k) is not None for r in rs) else None for k in ('input_tokens','output_tokens','latency_ms')})
        return result
    summary=dict(version=PROFILE,evidence_kind='real_apis_real_pybullet_nine_paired_episodes',rows=rows,methods=groups,
        episodes=9,successes=sum(r['task_success'] for r in rows),authenticated_requests=len(all_records),preflight_authenticated_requests=6,preflight_aborted_episodes=3,preflight_cost=totals(preflight),cumulative_cost=totals(preflight+all_records),cumulative_authenticated_requests=len(all_records)+6,
        schema_errors=sum(r['status']=='schema_error' for r in all_records),retries=sum(r['attempt']>1 for r in all_records),
        configured_models=plan['configuration'],returned_models={b:sorted({r['returned_model'] for r in all_records if r['backend']==b and r.get('returned_model')}) for b in ['deepseek','jev']},
        preserved_files_verified=len(unchanged),default_prompt_hashes=default_hashes(),source_commit=plan['code_commit'],
        note='One fixed scene per task (3 paired groups), not a powered benchmark or formal Test. Three r1 aborted preflight episodes are separate and fully retained; nine r2 paired episodes use identical corrected configuration. No r2 whole-episode reruns; schema repairs and all failures retained. Manual UI checks use explicitly scripted policies and real physics, zero API.')
    write(OUT/'summary.json',summary);write(OUT/'mapping_validation.json',dict(paired_initial_payloads_equal=True,source_hashes_unchanged=True,preserved_files=len(unchanged),episodes=audits))
    for name,data in [('episodes.csv',rows),('methods.csv',groups)]:
        with (OUT/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    lines=['# Grounded Dev v5 — nine paired real episodes','',summary['note'],'',
        '| Task | Method | Success | Burden | Actions | API latency | Failed conditions |','|---|---|---:|---:|---:|---:|---|']
    lines += [f"| {r['template']} | {r['method']} | {r['task_success']} | {r['burden']} | {r['actions']} | {r['latency_s']:.2f}s | {', '.join(r['failed_conditions']) or '—'} |" for r in rows]
    lines+=['','## Cost by method (cumulative over 3 episodes)','',
        '| Method | Success | Burden | DeepSeek in/out | Jev in/out | API latency |','|---|---:|---:|---|---|---:|']
    lines += [f"| {g['method']} | {g['successes']}/3 | {g['burden']} | {g['deepseek_input_tokens']}/{g['deepseek_output_tokens']} | {g['jev_input_tokens']}/{g['jev_output_tokens']} | {g['latency_s']:.2f}s |" for g in groups]
    lines+=['','## Retained preflight cost (separate from r2 table)','',json.dumps(totals(preflight)),f'All work: {len(preflight)+len(all_records)}/150 authenticated attempts; three aborted r1 plus nine r2 episodes.','','## Actual decision sequences','']
    for a in audits:
        lines += [f"### {a['template']} / {a['method']}",'']
        for t in a['gate_sequence']:
            lines.append(f"- Round {t['round']}, step {t['step']}: {t['decision']} p={t['p_ask']}; action={t['action']}; question={t['question']}; answer={t['answer']}")
    lines+=['','## Audit','',f"Authenticated requests: {len(all_records)}/150. Preserved historical/physics files: {len(unchanged)}. All wire inputs match saved public payloads; all three initial payloads match within each paired task. First model action is executed verbatim, without a cached suffix. Gate precedes planning. ASK holds the same physical state.",
        '',f"Source implementation commit: `{plan['code_commit']}`. Prompt/source hashes, budgets and randomized group order were locked before the first paid request in `live_plan_r2.json`. Default v1 and frozen/history files remain unchanged."]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    if args.export_media:
        media=ROOT/'presentation/grounded_dev_v5/media';media.mkdir(parents=True,exist_ok=True);manifest=[]
        for e in episodes:
            key=e['task_template']+'__'+e['method'];src=ROOT/e['artifacts']['directory']/'demo.gif';dest=media/(key+'.mp4')
            subprocess.run(['/opt/homebrew/bin/ffmpeg','-y','-loglevel','error','-i',str(src),'-vf','scale=960:-2','-c:v','libx264','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
            probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','quiet','-show_format','-of','json',str(dest)]))
            manifest.append(dict(case=key,source_episode=str((OUT/'live'/key/'episode.json').relative_to(ROOT)),source_gif=str(src),file=dest.name,
                sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,duration_s=float(probe['format']['duration'])))
        write(media.parent/'media_manifest.json',manifest)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
