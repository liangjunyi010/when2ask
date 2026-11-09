"""A read-only, local presentation gallery derived from completed real traces."""
import json
import shutil
from pathlib import Path

from .config import ROOT
from .presentation_scenarios import catalogue, get_sample
from .presentation_study import OUTPUT, report
from .study_data import write_json


def build():
    result = report()
    rows = {r['sample_id']: r for r in result['rows']}
    scenes = []
    for entry in catalogue():
        if entry['sample_id'] not in rows:
            continue
        row = rows[entry['sample_id']]
        path = ROOT / row['episode_path']
        episode = json.loads(path.read_text())
        sample = get_sample(entry['sample_id'])
        names = {k: v['color'] + ' ' + v['category'] for k, v in episode['final_observation']['objects'].items()}
        turns = []
        for turn in episode['turns']:
            turns.append({k: v for k, v in turn.items() if k in
                ('round', 'gate', 'question', 'user_answer', 'action', 'physical_result')})
        scenes.append(dict(**entry, metrics=row, object_names=names, turns=turns,
            ground_truth={sample.slots[k]['public_role']: names.get(v, v) for k, v in sample.theta_star.items()},
            conditions=episode['evaluation'].get('conditions', {}),
            scene=str(path.parent.relative_to(OUTPUT) / 'scene.png'),
            final=str(path.parent.relative_to(OUTPUT) / 'final.png'),
            gif=str(path.parent.relative_to(OUTPUT) / 'demo.gif'),
            video='media/' + entry['sample_id'] + '.mp4',
            trace=str(path.relative_to(OUTPUT))))
    media = OUTPUT / 'media'
    media.mkdir(exist_ok=True)
    for clip in (ROOT / 'presentation/dag_scenarios_v1/media').glob('*.mp4'):
        shutil.copyfile(clip, media / clip.name)
    write_json(OUTPUT / 'gallery_data.json', dict(summary={k: v for k, v in result.items() if k != 'rows'}, scenarios=scenes))
    source = Path(__file__).with_name('presentation_gallery.html')
    (OUTPUT / 'index.html').write_text(source.read_text())
    return dict(url='http://127.0.0.1:8881/', path=str(OUTPUT / 'index.html'), scenarios=len(scenes))
