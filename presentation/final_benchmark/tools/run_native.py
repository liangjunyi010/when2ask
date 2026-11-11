"""Verify actual PowerPoint playback on a byte-identical disposable copy."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
BASE=Path(__file__).resolve().parents[1]
deck=BASE/'deliverables/When2Ask_Benchmark_Presentation.pptx'
copy=BASE/'.build/Native_Validation_Copy.pptx'
shutil.copyfile(deck,copy)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(deck)==sha(copy)
r=subprocess.run(['osascript',str(BASE/'tools/native_check.applescript'),str(copy)],capture_output=True,text=True,timeout=90,check=True)
data=json.loads(r.stdout)
assert data['slides']==9 and data['play_on_entry']
assert data['player_positions_ms'][1]>data['player_positions_ms'][0]>500
data.update(pptx_sha256=sha(deck),byte_identical_copy=True,autoplay_verified=True,
    method='Native PowerPoint Slide Show; real Player object positions after two 2-second waits.',
    visual_review='All slide visuals separately checked through LibreOffice PDF and PNG; native screen pixels not captured.')
(BASE/'native_powerpoint_validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
