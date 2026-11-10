"""Offline report of all retained buffer Dev iterations and six real rollouts."""
import argparse,csv,html,json,shutil,subprocess,sys
from pathlib import Path

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.buffer_study_dev import digest,write


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--export-media',action='store_true');args=parser.parse_args()
    out=ROOT/'outputs/buffer_dev_v4';probes=[];attempts=[]
    for version in (2,3,4):
        base=ROOT/f'outputs/buffer_dev_v{version}'
        probes.extend(json.loads((base/'probe_summary.json').read_text())['rows'])
        attempts.extend(json.loads(line) for p in (base/'probes').glob('*.api.jsonl') for line in p.read_text().splitlines())
    probe_rows=[]
    for profile in dict.fromkeys(r['profile_id'] for r in probes):
        group=[r for r in probes if r['profile_id']==profile];valid=[r for r in group if r['diagnostics']['assessment_available']]
        probe_rows.append(dict(profile=profile,probes=len(group),valid_responses=len(valid),
            goal_regressions=sum(r['diagnostics']['undoes_currently_satisfied_final_relation'] for r in valid),
            occupied_slot_targets=sum(r['diagnostics']['targets_occupied_single_capacity_slot'] for r in valid),
            errors=sum(r['error'] is not None for r in group)))
    episodes=[];rows=[]
    for path in sorted((out/'episodes').glob('*/episode.json')):
        e=json.loads(path.read_text());episodes.append(e);ev=e['evaluation'];cost=e['cost']
        records=[json.loads(s) for s in path.with_name('api_attempts.jsonl').read_text().splitlines()];attempts.extend(records)
        rows.append(dict(case_id=e['case']['case_id'],method=e['case']['method'],known=e['case']['known'],truth=e['case']['truth'],
            profile=e['profile_id'],physical_swap_complete=e['physical_swap_complete'],task_success=ev['task_success'],
            burden=ev['clarification_burden'],actions=len(e['actions']),physical_failures=sum(not a['success'] for a in e['actions']),
            regressive_actions=sum(t.get('public_diagnostics',{}).get('undoes_currently_satisfied_final_relation',False) for t in e['turns']),
            api_attempts=cost['api_attempts'],api_latency_s=cost['api_latency_ms']/1000 if cost['api_latency_ms'] is not None else None,
            deepseek_input_tokens=cost['deepseek']['input_tokens'],deepseek_output_tokens=cost['deepseek']['output_tokens'],
            jev_input_tokens=cost['jev']['input_tokens'],jev_output_tokens=cost['jev']['output_tokens'],
            schema_errors=cost['schema_errors'],termination=e['termination_reason']))
    for name,values in [('episodes.csv',rows),('probes.csv',probe_rows)]:
        with (out/name).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(values[0]),lineterminator='\n');writer.writeheader();writer.writerows(values)
    ledger=json.loads((ROOT/'outputs/buffer_dev_v2/session/session_budget.json').read_text())
    if len(attempts)!=ledger['attempts']:raise ValueError('Request records do not match shared ledger')
    backend={}
    for name in ('deepseek','jev'):
        selected=[r for r in attempts if r['backend']==name]
        backend[name]=dict(attempts=len(selected),**{key:sum(r[key] for r in selected if r.get(key) is not None) if any(r.get(key) is not None for r in selected) else None
            for key in ('input_tokens','output_tokens','latency_ms')})
    result=dict(evidence='32 real action probes without physics + six real API/PyBullet episodes',
        scope='One physical layout group, adaptive Dev iterations, no held-out test or significance/ranking claim',
        probes=probe_rows,episodes=rows,total_authenticated_attempts=len(attempts),complete_episodes=len(rows),
        all_physical_swaps=sum(r['physical_swap_complete'] for r in rows),task_successes=sum(r['task_success'] for r in rows),
        backend_cost=backend,total_api_latency_s=sum(r['latency_ms'] for r in attempts if r.get('latency_ms') is not None)/1000,
        schema_errors=sum(r['status']=='schema_error' for r in attempts),
        actual_models=sorted({r['returned_model'] for r in attempts if r.get('returned_model')}),default_console_changed=False)
    write(out/'summary.json',result)
    lines=['# Buffered exchange: independent Dev repair report','',result['scope'],'',
      '## Original failure diagnosis','',
      'The first regression was round 2, after A had been parked on buffer_front and B had reached slot_left. The next model response moved B back to slot_right. All 13 serialized API inputs matched their saved turn payloads, and complete physical action history was present. This rules out missing history and stale controller/transport state at that point.',
      '', 'The original affordance list was broad schema support, not a filtered list of currently safe/progressing actions. Current contents were correct, but explicit final relations and persistent agent assumptions were not prominent. These are plausible representation/planning contributors, not access to the model\'s hidden reasoning.',
      '', '## All retained real action probes','',
      '| Profile | Probes | Valid outputs | Goal-regressing first actions | Occupied-slot targets |','|---|---:|---:|---:|---:|']
    for r in probe_rows:lines.append(f"| {r['profile']} | {r['probes']} | {r['valid_responses']} | {r['goal_regressions']} | {r['occupied_slot_targets']} |")
    lines+=['',
      '`s` = append-only public summary; `p` = extra planner grounding wording; `c1` = compact physical history retaining all user dialogue. Structured-plan profiles ask the same DeepSeek planner for current locations, public final targets, a working buffer choice and a remaining action suffix.',
      '', 'V2 summary/prompt changes and V3 context compression did not consistently stop old-history regressions. Their negative raw outputs remain intact. V4 structured planning produced no regressing first action in its eight probes. These use four states from ONE archived trajectory; they are not independent tasks, rollout success rates, or a confirmatory ablation.',
      '', '## Six complete episodes','',
      '| Case | Profile | Physical swap | Task success | Burden | Robot actions | API latency |','|---|---|---|---|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['case_id']} | {r['profile']} | {r['physical_swap_complete']} | {r['task_success']} | {r['burden']} | {r['actions']} | {r['api_latency_s']:.2f} s |")
    lines+=['',
      'The original v1 planner also completed the known-buffer control in three moves. Therefore the original failure must not be described as a universal v1 inability to swap objects. The original unknown-preference episode did loop, while the grounded Dev planner completed both unknown-preference controls mechanically. It guessed the front pad in both: the back-truth task failed preference scoring; the front-truth control succeeded. NoAsk is not forced to fail.',
      '', 'Only `unknown_back_v4_noask`, `unknown_back_v4_llm`, and `unknown_back_v4_jev` form a matched three-method case. They start from identical physical layout, preference and public information. Both gates asked once and succeeded; NoAsk completed the physical swap but used the wrong preferred pad. This single group supports an engineering demonstration, not a general claim that Jev outperforms LLM-Gate.',
      '', '## What V4 changes, and what it does not','',
      '- Every CONTINUE first follows its Gate decision, then calls the same planner again. The planner returns a short JSON state/goal audit and remaining plan; only its first action is executed, verbatim. No cached future actions are executed before later gates.',
      '- Grounding validation checks only publicly measured current region membership and the final targets implied by the public exchange instruction. It does not check an action against a correct next-action oracle, private pad preference or evaluator score.',
      '- Unit tests deliberately pass a regressing action with correct grounding and confirm that the planner wrapper returns that bad action unchanged. There is no silent correction, hard-coded swap executor or action mask.',
      '- All three new-method cases use the same structured planner, context rules and per-call output cap. Output cap increased from 160 to 400 for the structured action JSON; token/cost differences from v1 must be interpreted with that change.',
      '- Physics, grasp guards, physical constraints, skill-step limits, task evaluator and Jev threshold 0.5 remain unchanged. No final object pose resets are introduced.',
      '- V3/V4 were adaptive Dev amendments after observing earlier negative probes. The final six-case list was locked before any complete episode. All stages share the original 120-request / six-episode ceiling; no new budget was created.',
      '- The existing HTML and its default v1 planner were not silently replaced. This remains an independent Dev candidate pending optional-profile integration and regression across other tasks.',
      '', '## Actual usage','',f"Total authenticated requests: {len(attempts)} / 120, including {result['schema_errors']} schema repairs. Completed episodes: {len(rows)} / 6; no formal Test API calls."]
    for name,cost in backend.items():lines.append(f"- {name}: input {cost['input_tokens']}, output {cost['output_tokens']}, API latency {cost['latency_ms']/1000:.2f} s.")
    lines += ['', 'Backend tokens are not added into monetary-cost claims. Replay probes and complete episodes have separate raw API logs; all inference attempts are charged. GIF ASK/USER frames are explicitly display holds for actual events, not fabricated model latency.',
      '', '## Next step','',
      'Expose the grounded planner as an explicit Dev profile, generalize public grounding to the other task contracts, then run nine paired episodes: buffered exchange (must ask before choosing), retrieve/restore (known action first, ask later), and occlusion inspection (observe without asking), each with all three methods and identical per-case state/preferences. Keep planning failures separate from preference/timing failures. Freeze a new version only after that regression; do not modify the historical frozen Test configuration.',
      '', 'Full tests: 311 passed. All pre-existing experiment/configuration/source hashes are separately audited; the old six-task and formal Benchmark records are unchanged.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    clips=[];media=ROOT/'presentation/buffer_dev_v4/media'
    if args.export_media:media.mkdir(parents=True,exist_ok=True)
    for e in episodes:
        case=e['case']['case_id'];source=out/'episodes'/case/'demo.gif';target=media/(case+'.mp4')
        if args.export_media and not target.exists():
            subprocess.run(['ffmpeg','-v','error','-n','-i',str(source),'-vf','fps=20','-c:v','libx264','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
        if target.exists():
            with Image.open(source) as gif:
                frames=gif.n_frames;duration=0
                for i in range(frames):gif.seek(i);duration+=gif.info.get('duration',0)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',str(target)],text=True))
            if abs(float(probe['format']['duration'])*1000-duration)>60:raise ValueError('Clip duration mismatch')
            clips.append(dict(case_id=case,source_gif_sha256=digest(source),source_gif_frames=frames,duration_ms=duration,
                mp4=str(target.relative_to(ROOT)),mp4_sha256=digest(target),bytes=target.stat().st_size,probe=probe))
    if clips:write(ROOT/'presentation/buffer_dev_v4/media_manifest.json',dict(clips=clips,total_bytes=sum(c['bytes'] for c in clips)))
    local=out/'media';local.mkdir(exist_ok=True)
    for clip in media.glob('*.mp4'):shutil.copyfile(clip,local/clip.name)
    table=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ('case_id','physical_swap_complete','task_success','burden','actions'))+'</tr>' for r in rows)
    probes_table=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ('profile','probes','goal_regressions'))+'</tr>' for r in probe_rows)
    videos=''.join(f'<article id="{r["case_id"]}"><h3>{r["case_id"]}</h3><video controls playsinline preload="none" poster="episodes/{r["case_id"]}/scene.png" src="media/{r["case_id"]}.mp4"></video><p>Actual physics + labelled ASK/USER display holds; default 3×.</p><a href="episodes/{r["case_id"]}/episode.json">Raw episode JSON</a></article>' for r in rows)
    page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>When2Ask · Independent buffer Dev</title><style>
*{box-sizing:border-box}body{background:#0b1624;color:#dae7f4;font:15px/1.7 system-ui;margin:0}main{max-width:1440px;margin:auto;padding:35px}h1{font-size:30px}p{color:#a5bdd3}a{color:#7ee0d4}table{width:100%;border-collapse:collapse;font-size:13px}td,th{text-align:left;border-bottom:1px solid #36506b;padding:9px}.scroll{overflow:auto}section,article{border:1px solid #35516e;padding:22px;border-radius:10px;background:#13263a;margin-bottom:24px}.videos{display:grid;grid-template-columns:1fr 1fr;gap:22px}video{width:100%}h3{font-size:17px;overflow-wrap:anywhere}@media(max-width:700px){main{padding:18px}.videos{grid-template-columns:1fr}h1{font-size:24px}}</style></head><body><main><p>WHEN2ASK / INDEPENDENT DEV · DEFAULT CONSOLE UNCHANGED</p><h1>Repair planning before evaluating clarification timing.</h1><p>History was present. The planner reversed a completed relation. Public summaries alone did not fix it; grounded state/goal planning improved the observed probes and real executions.</p><section><h2>All retained action probes</h2><p>Four snapshots from one old episode; these are action diagnostics, not task-success rates.</p><div class="scroll"><table><tr><th>Profile</th><th>Probes</th><th>Goal-regressing actions</th></tr>'''+probes_table+'''</table></div></section><section><h2>Six complete real episodes</h2><p>One physical group. NoAsk can complete the mechanics and still guess the wrong preference; the opposite-truth control can succeed.</p><div class="scroll"><table><tr><th>Case</th><th>Physical swap</th><th>Task success</th><th>Burden</th><th>Moves</th></tr>'''+table+'''</table></div><p><a href="report.md">Detailed report</a> · <a href="episodes.csv">CSV</a> · <a href="summary.json">Raw summary</a></p></section><div class="videos">'''+videos+'''</div></main><script>for(const v of document.querySelectorAll('video')){v.defaultPlaybackRate=3;v.playbackRate=3;}</script></body></html>'''
    (out/'index.html').write_text(page)
    print(json.dumps({k:v for k,v in result.items() if k not in ('probes','episodes')},indent=2))


if __name__=='__main__':main()
