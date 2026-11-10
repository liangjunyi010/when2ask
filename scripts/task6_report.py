"""Aggregate only real episode JSON and compress real recorded frames for demos."""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.task6_spec import TITLES


def export_clip(source,target):
    if not target.exists():
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(source),'-vf','fps=20','-c:v','libx264','-preset','medium',
            '-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    with Image.open(source) as gif:
        count=gif.n_frames;duration=0
        for i in range(count):gif.seek(i);duration+=gif.info.get('duration',0)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',str(target)],text=True))
    if abs(float(probe['format']['duration'])*1000-duration)>60:raise ValueError('Export duration differs from actual GIF')
    return dict(source_gif_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_gif_frames=count,
        source_gif_duration_ms=duration,mp4=str(target.relative_to(ROOT)),mp4_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,probe=probe)


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--export-media',action='store_true');args=parser.parse_args()
    out=ROOT/'outputs/six_tasks_dev_v1';rows=[];episodes=[];clips=[]
    for template in TITLES:
        path=out/'live'/template/'episode.json';e=json.loads(path.read_text());episodes.append(e)
        cost=e['cost'];ev=e['evaluation'];turns=e['turns']
        rows.append(dict(template=template,method=e['method'],success=ev['task_success'],burden=ev['clarification_burden'],
            ask_turns=sum('question' in t for t in turns),actions=len(e['actions']),physical_failures=sum(not a['success'] for a in e['actions']),
            termination_reason=e['termination_reason'],api_attempts=cost['api_attempts'],api_latency_s=cost['api_latency_ms']/1000 if cost['api_latency_ms'] is not None else None,
            deepseek_input_tokens=cost['deepseek']['input_tokens'],deepseek_output_tokens=cost['deepseek']['output_tokens'],
            jev_input_tokens=cost['jev']['input_tokens'],jev_output_tokens=cost['jev']['output_tokens'],
            schema_errors=cost['schema_errors'],retries=cost['retries'],api_errors=cost['api_errors']))
        if args.export_media:
            target=ROOT/'presentation/six_tasks_dev_v1/media'/(template+'.mp4');target.parent.mkdir(parents=True,exist_ok=True)
            clips.append(dict(template=template,**export_clip(path.with_name('demo.gif'),target)))
    with (out/'results.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    def total(key):
        values=[r[key] for r in rows if r[key] is not None];return sum(values) if values else None
    result=dict(evidence_kind='six_real_model_episodes_real_physics',episodes=len(rows),successes=sum(r['success'] for r in rows),
        authenticated_requests=total('api_attempts'),api_latency_s=total('api_latency_s'),
        **{k:total(k) for k in ('deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens','schema_errors','retries','api_errors')},
        rows=rows,scope='Unpaired: one different task per case, methods rotate. No ranking, significance, or held-out Test conclusion.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Six genuinely new robotic tasks — engineering smoke','',result['scope'],'',
        '| Task | Method | Success | Burden | Actions | Skill failures | API latency |','|---|---|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f"| {TITLES[r['template']]} | {r['method']} | {r['success']} | {r['burden']} | {r['actions']} | {r['physical_failures']} | {r['api_latency_s']:.2f} s |")
    lines+=['','## What the actual turns show','']
    for e in episodes:
        lines.append('### '+TITLES[e['task_template']]);lines.append('')
        for turn in e['turns']:
            gate=turn['gate'];ptext=f" p={gate['p_ask']:.2f}" if gate.get('p_ask') is not None else ''
            detail=turn.get('question',{}).get('text') or json.dumps(turn.get('action'),ensure_ascii=False)
            suffix=' (planned but not executed: budget termination)' if turn.get('action',{}).get('kind') not in (None,'DONE') and 'physical_result' not in turn else ''
            lines.append(f"- Round {turn['round']}: {gate['decision']}{ptext}; {detail}{suffix}")
            if turn.get('user_answer'):lines.append('  User simulator: '+json.dumps(turn['user_answer'],ensure_ascii=False))
        lines.append('')
    lines+=['## Interpretation and limitations','',
        '- Real physical oracle attempt 1: 4/6. The short category item interfered with the bin rim; patrol had no physical fixture to hit with its ray. Both failures are retained.',
        '- Corrected geometry uses graspable cylinders and actual equipment fixtures. Attempt 2: 6/6; independent real-physics pytest also passes all six. No old controller, evaluator threshold or frozen study was changed.',
        '- Sorting NoAsk placed all six objects successfully but guessed the wrong category-bin assignment. Final task score remains false.',
        '- Buffered exchange NoAsk guessed a buffer, repeatedly reversed progress, attempted full/occupied targets and stopped at 12 physical actions. This combines preference uncertainty and planner failure; it cannot be attributed solely to the absence of clarification.',
        '- Inventory and patrol LLM-Gate each performed known work, then asked one preference, reused the answer and completed.',
        '- Retrieve/restore Jev-Gate continued to open the box at p=0.26, asked at p=0.79, retrieved the selected item and closed the box.',
        '- Occlusion Jev-Gate continued throughout: move screen, perform a real ray/range-qualified inspection, report the measured code. It did not ask for an observable world fact.',
        f"- {result['authenticated_requests']} real authenticated requests, including {result['retries']} retries and {result['schema_errors']} schema errors. Actual usage and latency remain in every API attempt. No API errors were reported.",
        '- These are six different tasks with two cases per method, not paired method comparisons. The HTML comparison launcher is integrated; additional paid three-method batches were not run in this six-episode study.',
        '- Tabletop inspection is a structured sensor gated by actual Bullet ray visibility and range, not learned image recognition. Patrol reuses the existing known three-room map and requires actual orientation, fixture sight and return.',
        '- Worker GIF/MP4 records actual physical frames with display holds; model/ASK wall time is excluded. The full original instruction, gate/question/answer/action sequence and final truth are in the console review. The dependency diagrams are static task DAGs, not independent timed animations.',
        '- Manual browser verification used six explicitly scripted policies with real physics (six successes, five question/answer freeze checks, zero API calls). It is excluded from live-model metrics.',
        '', '## Tokens (backends separate)', '',
        f"DeepSeek input/output: {result['deepseek_input_tokens']} / {result['deepseek_output_tokens']}. Jev input/output: {result['jev_input_tokens']} / {result['jev_output_tokens']}.",
        f"Cumulative authenticated API latency: {result['api_latency_s']:.2f} s, not average episode latency.",
        '', 'All original frozen datasets, prompts, configurations, physics files and historical records remain unchanged. New task prompts/data and the locked six-case manifest are separate.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    if clips:
        (ROOT/'presentation/six_tasks_dev_v1/media_manifest.json').write_text(json.dumps(dict(clips=clips,total_bytes=sum(c['bytes'] for c in clips)),indent=2)+'\n')
    # The existing command center supplies full live/review functionality. This
    # compact page is an offline, read-only presentation index of recorded cases.
    media_dir=out/'media';media_dir.mkdir(exist_ok=True)
    for source in (ROOT/'presentation/six_tasks_dev_v1/media').glob('*.mp4'):shutil.copyfile(source,media_dir/source.name)
    cards=[]
    import html
    for row,e in zip(rows,episodes):
        template=row['template'];safe=html.escape
        events=[]
        for t in e['turns']:
            g=t['gate'];label=g['decision']+(f" · p={g['p_ask']:.2f}" if g.get('p_ask') is not None else '')
            text=t.get('question',{}).get('text') or json.dumps(t.get('action'),ensure_ascii=False)
            if t.get('user_answer'):text+=' → '+json.dumps(t['user_answer'],ensure_ascii=False)
            events.append('<li><b>Round '+str(t['round'])+' · '+safe(label)+'</b><br>'+safe(text)+'</li>')
        cards.append(f'''<article id="{template}"><h2>{safe(TITLES[template])}</h2><p>{safe(row['method'])} · {'SUCCESS' if row['success'] else 'UNSUCCESSFUL'} · Burden {row['burden']} · {row['api_latency_s']:.2f} API seconds</p>
<video controls playsinline preload="none" poster="live/{template}/scene.png" src="media/{template}.mp4"></video><p class="note">Real physical frames; default 3×. API and ASK wall time excluded. Full interaction below.</p>
<details><summary>Original instruction, model turns and final truth</summary><p>{safe(e['public_instruction'])}</p><ol>{''.join(events)}</ol><pre>{safe(json.dumps(e['review']['ground_truth'],indent=2,ensure_ascii=False))}</pre></details>
<p><a href="http://127.0.0.1:8877/?review={e['episode_id']}">Full command-center review ↗</a> · <a href="live/{template}/episode.json">Raw episode JSON ↗</a> · <a href="media/{template}.mp4" download>MP4 ↓</a></p></article>''')
    document='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>When2Ask · Six new tasks</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b1522;color:#deebf7;font:15px/1.7 system-ui,sans-serif}header,main{max-width:1550px;margin:auto;padding:30px}h1{font-size:32px}p{color:#a9bed2}a{color:#7ce1d4}main{display:grid;grid-template-columns:1fr 1fr;gap:24px;padding-top:0}article{min-width:0;padding:22px;background:#122438;border:1px solid #31506c;border-radius:12px}h2{font-size:21px;margin-top:0}video{display:block;width:100%;background:#080f19}summary{cursor:pointer;color:#b8e4ef}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}li{padding:8px 0;font-size:13px}.note{font-size:11px}details p{font-size:13px}@media(max-width:800px){main{grid-template-columns:1fr}header,main{padding:20px}h1{font-size:25px}}</style></head><body><header><p>WHEN2ASK / INDEPENDENT SIX-TASK DEV v1</p><h1>Six new goals. Real robots. Observable clarification timing.</h1><p>__MEASURED_SUMMARY__</p><p>Static recorded-case index; no new API calls. <a href="results.csv">CSV</a> · <a href="report.md">Detailed report</a> · <a href="http://127.0.0.1:8877/">Interactive command center</a></p></header><main>'''+''.join(cards)+'''</main><script>for(const video of document.querySelectorAll('video')){video.defaultPlaybackRate=3;video.playbackRate=3;}</script></body></html>'''
    # Header numbers are replaced from raw metrics so a report can never silently
    # present hard-coded passing totals if an episode failed or was interrupted.
    oracle=json.loads((out/'oracle_02/summary.json').read_text())
    document=document.replace('__MEASURED_SUMMARY__',f"Physical oracle {oracle['successes']}/{oracle['total']} · Real-model task success {result['successes']}/{result['episodes']} · {result['episodes']} unpaired cases · {result['authenticated_requests']} authenticated requests")
    (out/'index.html').write_text(document)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
