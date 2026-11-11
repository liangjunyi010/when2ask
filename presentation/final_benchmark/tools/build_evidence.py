"""Create presentation inputs from immutable v8 results; never call a backend."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'presentation/final_benchmark'
CASE = 'outputs/three_task_v8/test_runs/t8_r2_test_1_04_1__jev_gate'

def dump(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def main():
    episode_path = ROOT / CASE / 'episode.json'
    ep = json.loads(episode_path.read_text())
    evaluation = json.loads((ROOT / CASE / 'evaluation.json').read_text())
    summary = json.loads((ROOT / 'outputs/three_task_v8/report/summary.json').read_text())
    frames = ep['recording']['frames']
    gif = Image.open(ROOT / CASE / 'demo.gif')
    assert gif.n_frames == len(frames), (gif.n_frames, len(frames))
    out = BASE / 'web/frames'
    out.mkdir(parents=True, exist_ok=True)
    timeline = []
    display_ms = 0
    for i, f in enumerate(frames):
        step, label = f['simulation_step'], f['label']
        if label.startswith('ASK '):
            turn, stage = ep['turns'][1], 'question'
        elif label.startswith('USER '):
            turn, stage = ep['turns'][1], 'answer'
        elif label.startswith('FINAL '):
            turn, stage = ep['turns'][-1], 'evaluation'
        elif label.startswith('OBSERVE '):
            turn, stage = ep['turns'][0], 'decision'
        else:
            # Matching label is essential at shared boundary steps.
            matches = [t for t in ep['turns'] if 'physical_result' in t
                       and label == f"{t['action']['kind']} {t['action']['object_id']}"
                       and t['physical_result']['start_step'] <= step <= t['physical_result']['end_step']]
            assert len(matches) == 1, (i, f, matches)
            turn = matches[0]
            stage = 'execution' if turn['physical_result']['success'] else 'rejection'
        phases = [e for e in ep['execution_log'] if e['kind'] == 'phase'
                  and turn.get('physical_result', {}).get('start_step', 10**9) <= e['step'] <= step
                  and e.get('object_id') == turn.get('action', {}).get('object_id')]
        phase = phases[-1]['phase'] if phases and stage == 'execution' else None
        duration = f['duration_ms'] / 3 if stage == 'execution' else {
            'decision': 600, 'question': 1500, 'answer': 1500, 'evaluation': 1800,
            'rejection': 900
        }[stage]
        action = turn.get('action')
        record = dict(frame_index=i, simulation_step=step, label=label,
                      original_duration_ms=f['duration_ms'], start_ms=display_ms,
                      end_ms=display_ms + duration, duration_ms=duration,
                      round=turn['round'], stage=stage, gate=turn['gate'],
                      action=action, phase=phase,
                      question=ep['turns'][1]['question'] if stage in ['question','answer'] else None,
                      answer=ep['turns'][1]['user_answer'] if i >= 50 else None,
                      evaluation=evaluation if stage == 'evaluation' else None,
                      repaired_rejection=(turn['round'] == 4),
                      evidence=f"{CASE}/episode.json#/recording/frames/{i}")
        timeline.append(record)
        gif.seek(i)
        gif.convert('RGB').save(out / f'{i:04d}.jpg', quality=94)
        display_ms += duration
    assert timeline[49]['stage'] == 'question' and timeline[50]['stage'] == 'answer'
    assert timeline[49]['simulation_step'] == timeline[50]['simulation_step']
    assert all(f['gate']['p_ask'] == ep['turns'][f['round']]['gate']['p_ask'] for f in timeline)
    # A handful of lossless frame atlases make the HTML self-contained without
    # committing hundreds of intermediate images or the ignored source GIF.
    atlas_dir = BASE / 'web/assets'
    atlas_dir.mkdir(exist_ok=True)
    for start in range(0,len(frames),32):
        sheet=Image.new('RGB',(640*8,480*4),'white')
        name=f'frames-{start//32:02d}.webp'
        for i in range(start,min(start+32,len(frames))):
            gif.seek(i)
            x,y=((i-start)%8)*640,((i-start)//8)*480
            sheet.paste(gif.convert('RGB'),(x,y))
            timeline[i]['image']={'path':'assets/'+name,'x':x,'y':y,'width':640,'height':480}
        sheet.save(atlas_dir/name,lossless=True,method=6)
    data = dict(source_episode=f'{CASE}/episode.json', source_sha256=hashlib.sha256(episode_path.read_bytes()).hexdigest(),
                original_duration_ms=sum(f['duration_ms'] for f in frames), duration_ms=display_ms,
                display_policy='3x physical motion; explicit decision/question/answer/final display holds; no inferred inference timing',
                zero_simulation_step_events=[dict(round=t['round'], action=t.get('action'), result=t.get('physical_result'))
                    for t in ep['turns'] if t.get('physical_result', {}).get('start_step') == t.get('physical_result', {}).get('end_step') and 'physical_result' in t],
                frames=timeline)
    dump(BASE / 'web/timeline.json', data)
    dump(BASE / 'evidence_manifest.json', dict(summary=summary, source_episode=data['source_episode'],
        episode_sha256=data['source_sha256'], protected_artifacts=[
            {'path':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in [ROOT/'data/three_task_v8/r2/dev.jsonl',ROOT/'data/three_task_v8/r2/test.jsonl',
                ROOT/'outputs/three_task_v8/report/summary.json',episode_path,ROOT/'outputs/three_task_v8/frozen_manifest.json']],
        authentication_requests_during_presentation_build=0))
    dump(BASE / 'mapping_validation.json',dict(source_frames=len(frames), frame_count_matches_gif=True,
        frame_order_preserved=True, same_step_question_and_answer_preserved=True,
        probability_matches_source=True, source_actions_unmodified=True,
        rejected_command_has_own_frame=any(f['stage']=='rejection' for f in timeline),
        rejection_events=data['zero_simulation_step_events'],duration_ms=display_ms,
        checkpoints=[dict(frame=i,simulation_step=timeline[i]['simulation_step'],stage=timeline[i]['stage'],
            round=timeline[i]['round'],gate=timeline[i]['gate'],action=timeline[i]['action'])
            for i in [0,20,49,50,75,130,163]]))
    print(json.dumps({'frames':len(frames),'highlight_seconds':display_ms/1000,'api_calls':0}))

if __name__ == '__main__': main()
