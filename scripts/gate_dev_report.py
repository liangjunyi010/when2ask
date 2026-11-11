"""Recompute v7 Gate-state ablation, threshold diagnostics and real task evidence."""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.gate_contract_dev import compact
from when2ask.memory_dev_public import serialize

OUT=ROOT/'outputs/gate_diagnostics_dev_v7'
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def records(path):return [json.loads(s) for s in path.read_text().splitlines()]
def totals(rows):
    result={}
    for backend in ('deepseek','jev'):
        rr=[r for r in rows if r['backend']==backend];result[backend]=dict(attempts=len(rr))
        for key in ('input_tokens','output_tokens','latency_ms'):
            values=[r[key] for r in rr if r.get(key) is not None];result[backend][key]=sum(values) if values else None
            result[backend]['unknown_'+key+'_attempts']=sum(r.get(key) is None for r in rr)
    return result


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--export-media',action='store_true');args=parser.parse_args()
    plan=read(OUT/'matrix/plan.json');rows=read(OUT/'matrix/rows.json');selection=read(OUT/'selection.json');live=read(OUT/'live_validation.json');liveplan=read(OUT/'live_plan.json')
    assert len(rows)==42 and live['episodes']==6
    assert hashlib.sha256((ROOT/'src/when2ask/gate_contract_dev.py').read_bytes()).hexdigest()==plan['source_sha256']
    sensitivity=[];probability_table=[]
    for key in plan['states']:
        values={}
        for profile in plan['profiles']:
            r=next(r for r in rows if r['kind']=='factorial' and r['backend']=='jev' and r['state_id']==key and f"s{int(r['compact'])}c{int(r['contract'])}"==profile)
            values[profile]=r['p_ask']
        probability_table.append(dict(state=key,expected=plan['states'][key]['expected_contract_decision'],**values))
    for profile in plan['profiles']:
        for threshold in plan['threshold_diagnostic']:
            pp=[(r['expected'],'ASK' if r[profile]>=threshold else 'CONTINUE') for r in probability_table]
            sensitivity.append(dict(profile=profile,threshold=threshold,correct=sum(a==b for a,b in pp),states=8,
                missed_asks=sum(a=='ASK' and b=='CONTINUE' for a,b in pp),unnecessary_asks=sum(a=='CONTINUE' and b=='ASK' for a,b in pp),scope='offline gate-state classification, NOT end-to-end success'))
    matrix_records=[r for p in (OUT/'matrix').glob('*.api.jsonl') for r in records(p)]
    assert len(matrix_records)==42
    sources=read(OUT/'matrix/state_sources.json')
    for row in rows:
        rr=records(OUT/'matrix'/(row['id']+'.api.jsonl'))
        for r in rr:
            request=r['request']
            if row['kind']=='historical_replay':
                path=ROOT/f"outputs/{row['version']}/live/buffer_exchange__jev_gate/api_attempts.jsonl"
                original=next(x['request'] for x in records(path) if x['stage']=='gate')
                assert request==original,'Historical replay request changed'
            else:
                original=sources[row['state_id']]['public_payload']
                expected=compact(original) if row['compact'] else original
                wire=json.loads(request['messages'][1]['content']) if row['backend']=='deepseek' else request['state']
                assert wire==expected,'Diagnostic label or unexpected field entered API payload'

    episodes=[];episode_rows=[];audits=[];api=[]
    for path in sorted((OUT/'live').glob('*/episode.json')):
        e=read(path);episodes.append(e);rr=records(path.with_name('api_attempts.jsonl'));api+=rr;prior=[]
        for turn in e['turns']:
            assert turn['public_payload']==serialize(turn['raw_public_payload'],prior);prior.append(turn['raw_public_payload']['observation'])
            is_new=e['planner_profile']=='gate_dev_v7'
            expected_gate=compact(turn['public_payload']) if is_new else turn['public_payload']
            if is_new:assert turn['gate_payload']==expected_gate
            calls=[r for r in rr if r['round']==turn['round']]
            if calls:assert calls[0]['stage']=='gate'
            for r in calls:
                wire=json.loads(r['request']['messages'][1]['content']) if r['backend']=='deepseek' else r['request']['state']
                assert wire==(expected_gate if r['stage']=='gate' else turn['public_payload'])
            if 'model_plan' in turn:assert turn['action']==turn['model_plan']['remaining_plan'][0]
            if 'ask_check' in turn:assert turn['ask_check']['state_unchanged'] and turn['ask_check']['before_step']==turn['ask_check']['after_step']
        v=e['evaluation'];c=e['cost'];row=dict(template=e['task_template'],method=e['method'],profile=e['planner_profile'],episode_id=e['episode_id'],
            success=v['task_success'],burden=v['clarification_burden'],actions=len(e['actions']),physical_failures=sum(not a['success'] for a in e['actions']),
            attempts=len(rr),api_latency_s=c['api_latency_ms']/1000 if c['api_latency_ms'] is not None else None,
            deepseek_input_tokens=c['deepseek']['input_tokens'],deepseek_output_tokens=c['deepseek']['output_tokens'],jev_input_tokens=c['jev']['input_tokens'],jev_output_tokens=c['jev']['output_tokens'],
            first_p_ask=e['turns'][0]['gate']['p_ask'],gate_sequence=[t['gate'] for t in e['turns']],termination=e['termination_reason'],failed_conditions=[k for k,v in v['conditions'].items() if not v])
        episode_rows.append(row);audits.append(dict(id=e['episode_id'],gate_before_planner=True,wire_stage_payloads_match=True,first_action_verbatim=True,memory_recomputes=True,
            ask_checks=sum('ask_check' in t for t in e['turns'])))
    assert len(episodes)==6
    buffers=[e for e in episodes if e['task_template']=='buffer_exchange']
    assert len(buffers)==4 and len({e['turns'][0]['payload_sha256'] for e in buffers})==1
    assert len({json.dumps(e['prompt_hashes'],sort_keys=True) for e in episodes})==1
    assert len(api)==live['authenticated_episode_requests'] and len(api)+len(matrix_records)==live['total_authenticated_requests']<=150
    unchanged=read(OUT/'preserved_file_hashes.json');assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==d for p,d in unchanged.items())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==d for p,d in liveplan['source_hashes'].items())
    replays=[]
    for version in ['grounded_planner_dev_v5','memory_planner_dev_v6']:
        values=[r['p_ask'] for r in rows if r.get('version')==version]
        old=read(ROOT/f'outputs/{version}/live/buffer_exchange__jev_gate/episode.json')['turns'][0]['gate']['p_ask']
        replays.append(dict(version=version,historical_p=old,repeated_p=values,range=[min(values),max(values)]))
    summary=dict(evidence_scope='Dev gate-state ablation and six real physics episodes, not formal Test',selection=selection,
        gate_state_probabilities=probability_table,historical_replay=replays,episodes=episode_rows,
        candidate_successes=sum(r['success'] for r in episode_rows if r['profile']=='gate_dev_v7'),candidate_episodes=sum(r['profile']=='gate_dev_v7' for r in episode_rows),
        state_calls=len(matrix_records),episode_calls=len(api),total_authenticated_requests=len(api)+len(matrix_records),matrix_cost=totals(matrix_records),episode_cost=totals(api),total_cost=totals(matrix_records+api),
        models={backend:sorted({r['returned_model'] for r in matrix_records+api if r['backend']==backend and r.get('returned_model')}) for backend in ['deepseek','jev']},
        schema_errors=sum(r['status']=='schema_error' for r in matrix_records+api),api_errors=sum(r['status']=='api_error' for r in matrix_records+api),retries=sum(r['attempt']>1 for r in matrix_records+api),
        protected_files=len(unchanged),threshold=.5,formal_test_api_episodes=0)
    write(OUT/'summary.json',summary);write(OUT/'threshold_sensitivity.json',sensitivity);write(OUT/'mapping_validation.json',dict(episodes=audits,buffer_initial_full_inputs_identical=True,all_prompts_identical=True,historical_files_preserved=len(unchanged)))
    for name,data in [('gate_states.csv',probability_table),('threshold_sensitivity.csv',sensitivity),('episodes.csv',episode_rows)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    lines=['# Gate Dev v7: state / contract / threshold diagnosis','',
        'Eight replayed public states are not independent physical groups or end-to-end episodes. Contract labels remain outside API payloads. Threshold0.5 is unchanged. Six full episodes are separately scored by the unchanged physical evaluator. No reruns, Test calls or historical rewrites.','',
        '| Public state | Expected | Full/original | Full/explicit | Compact/original | Compact/explicit |','|---|---|---:|---:|---:|---:|']
    lines += [f"| {r['state']} | {r['expected']} | {r['s0c0']:.2f} | {r['s0c1']:.2f} | {r['s1c0']:.2f} | {r['s1c1']:.2f} |" for r in probability_table]
    lines+=['','Selected by the prelocked minimum-change rule: '+str(selection['selected'])+'. The original contract, shared v6 planner and threshold are unchanged; only the Gate view is compact.','',
        '| Actual task | Method | Profile | Success | Burden | Actions | First p | API latency |','|---|---|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['template']} | {r['method']} | {r['profile']} | {r['success']} | {r['burden']} | {r['actions']} | {r['first_p_ask']} | {r['api_latency_s']:.2f}s |" for r in episode_rows]
    lines+=['','## Replayed exact original requests','']+[f"- {r['version']}: historical {r['historical_p']}, this session {r['repeated_p']}." for r in replays]
    lines+=['','The historical0.53→0.43 crossing cannot be attributed solely to formatting: identical requests vary. Within this new factorial, compact input improves the buffer decision; stronger wording alone does not. These are local diagnostic observations, not a universal causal/model calibration claim.','',
        '## Costs / audit','',f"Gate-only requests {len(matrix_records)}, full-episode requests {len(api)}, total {len(matrix_records)+len(api)}/150. Retries/schema/API errors: {summary['retries']}/{summary['schema_errors']}/{summary['api_errors']}. Protected files {len(unchanged)}. Stage wire inputs, initial matched physics inputs, unchanged prompts, gate ordering and first-action/ASK-freeze evidence verified.",
        '',json.dumps(summary['total_cost']),'',
        'Threshold sensitivity CSV/JSON is OFFLINE Gate-state reclassification only. It does not represent fresh physical trajectories or task success under another threshold. No runtime threshold was selected from these eight states.','',
        'Official Noul semantics and cautions about near-boundary probabilities and small-case threshold fitting were checked against [TypeSafe documentation](https://docs.typesafe.ai/primitives/noul).',
        '',f"Source commit for full episodes: {liveplan['code_commit']}. See live_plan.json and matrix/plan.json for preregistered order, factors, source hashes, selection rule and budget."]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    if args.export_media:
        media=ROOT/'presentation/gate_dev_v7/media';media.mkdir(parents=True,exist_ok=True);manifest=[]
        for e in episodes:
            key='__'.join([e['task_template'],e['method'],e['planner_profile']]);src=Path(e['artifacts']['directory'])/'demo.gif';dest=media/(key+'.mp4')
            subprocess.run(['/opt/homebrew/bin/ffmpeg','-y','-loglevel','error','-i',str(src),'-vf','scale=960:-2','-c:v','libx264','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
            probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','quiet','-show_format','-of','json',str(dest)]))
            manifest.append(dict(file=dest.name,episode_id=e['episode_id'],source_gif=str(src),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),bytes=dest.stat().st_size,duration_s=float(probe['format']['duration'])))
        write(media.parent/'media_manifest.json',manifest)
    print(json.dumps({k:summary[k] for k in ['state_calls','episode_calls','total_authenticated_requests','candidate_successes','candidate_episodes','total_cost','protected_files']},indent=2))


if __name__=='__main__':main()
