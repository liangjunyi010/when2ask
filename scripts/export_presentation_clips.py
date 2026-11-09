"""Compress original recorded PyBullet GIFs into seekable presentation MP4s."""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from when2ask.config import ROOT
from when2ask.study_data import sha256, write_json


def convert(path):
    episode = json.loads(path.read_text())
    source = path.with_name('demo.gif')
    destination = ROOT / 'presentation/dag_scenarios_v1/media' / (episode['sample_id'] + '.mp4')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError('Do not replace an exported clip without a new version')
    subprocess.run(['ffmpeg', '-v', 'error', '-n', '-i', str(source), '-vf', 'fps=20', '-c:v', 'libx264',
        '-preset', 'medium', '-crf', '25', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)], check=True)
    with Image.open(source) as gif:
        duration = 0
        for index in range(gif.n_frames):
            gif.seek(index); duration += gif.info.get('duration', 0)
        frames = gif.n_frames
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,width,height', '-of', 'json', str(destination)], text=True))
    if abs(float(probe['format']['duration']) * 1000 - duration) > 60:
        raise ValueError('Export duration differs from original GIF')
    return dict(sample_id=episode['sample_id'], method=episode['method'], source=str(source.relative_to(ROOT)),
        source_sha256=sha256(source), source_gif_frames=frames, source_duration_ms=duration,
        mp4=str(destination.relative_to(ROOT)), mp4_sha256=sha256(destination),
        bytes=destination.stat().st_size, probe=probe, time_compression='none in media; browser defaults to uniform 2x playback')


if __name__ == '__main__':
    paths = sorted((ROOT / 'outputs/presentation_dag_v1/live').glob('*/episode.json'))
    if len(paths) != 20:
        raise ValueError('Expected all twenty completed real episodes')
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(convert, paths))
    write_json(ROOT / 'presentation/dag_scenarios_v1/media_manifest.json', dict(
        kind='ffmpeg compression of real recorded PyBullet frames; no invented events', clips=rows,
        total_bytes=sum(r['bytes'] for r in rows)))
    print(json.dumps(dict(clips=len(rows), total_bytes=sum(r['bytes'] for r in rows))))
