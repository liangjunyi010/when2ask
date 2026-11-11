"""Encode deterministic screenshots of the real browser rendering."""
import json
import subprocess
from pathlib import Path
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
t=json.loads((BASE/'web/timeline.json').read_text())
media=BASE/'media';media.mkdir(exist_ok=True)
outputs=[]
for mode in ['highlight','full']:
    frames=[];lines=[]
    for f in t['frames']:
        p=BASE/f".build/capture/{f['frame_index']:04d}.png"
        ms=f['duration_ms'] if mode=='highlight' else f['original_duration_ms']
        lines.extend([f"file '{p}'",f'duration {ms/1000:.6f}'])
        if mode=='highlight':
            im=Image.open(p).convert('RGB');im.thumbnail((960,540));frames.append(im)
    # concat's last entry is duplicated as its timestamp delimiter, trimmed explicitly.
    lines.append(f"file '{p}'")
    listing=BASE/f'.build/{mode}.concat';listing.write_text('\n'.join(lines)+'\n')
    dur=sum(f['duration_ms'] if mode=='highlight' else f['original_duration_ms'] for f in t['frames'])/1000
    out=media/f'when2ask_{mode}.mp4'
    subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),'-t',str(dur),'-vf','fps=30','-c:v','libx264','-preset','slow','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    outputs.append({'file':out.name,'duration_s':dur,'bytes':out.stat().st_size})
    if frames:
        durations=[round(f['duration_ms']/10)*10 for f in t['frames']]
        frames[0].save(media/'when2ask_highlight.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
(BASE/'media_validation.json').write_text(json.dumps({'origin':'Deterministic Chromium screenshots of frame-indexed HTML replay','outputs':outputs},indent=2)+'\n')
print(json.dumps(outputs))
