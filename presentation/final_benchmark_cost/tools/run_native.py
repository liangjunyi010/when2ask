"""Verify actual PowerPoint playback on a byte-identical disposable copy."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
BASE=Path(__file__).resolve().parents[1]
deck=BASE/'deliverables/When2Ask_Benchmark_Presentation_v2.pptx'
copy=BASE/'.build/Native_Validation_Copy.pptx'
# Launch Services avoids the first-launch Apple-event open delay. Touch only
# this disposable validation document, never the user's existing presentations.
subprocess.run(['osascript','-e','tell application "Microsoft PowerPoint"\ntry\nclose presentation "Native_Validation_Copy.pptx" saving no\nend try\nend tell'],capture_output=True,text=True,timeout=10,check=True)
shutil.copyfile(deck,copy)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(deck)==sha(copy)
subprocess.run(['open','-a','Microsoft PowerPoint',str(copy)],capture_output=True,text=True,timeout=10,check=True)
ready=False
for _ in range(30):
    state=subprocess.run(['osascript','-e','tell application "Microsoft PowerPoint" to get name of every presentation'],capture_output=True,text=True,timeout=5,check=True)
    if 'Native_Validation_Copy.pptx' in state.stdout:
        ready=True
        break
    time.sleep(.5)
assert ready,'PowerPoint did not open the disposable copy'
r=subprocess.run(['osascript',str(BASE/'tools/native_check.applescript'),str(copy)],capture_output=True,text=True,timeout=90,check=True)
data=json.loads(r.stdout)
assert data['slides']==10 and data['play_on_entry']
assert data['player_positions_ms'][1]>data['player_positions_ms'][0]>500
data.update(pptx_sha256=sha(deck),byte_identical_copy=True,autoplay_verified=True,
    opening_method='Launch Services, then explicit disposable presentation selection. Initial cold-start Apple-event open timed out; no benchmark/API rerun.',
    method='Native PowerPoint Slide Show; real Player object positions after two 2-second waits.',
    visual_review='All slide visuals separately checked through LibreOffice PDF and PNG; native screen pixels not captured.')
(BASE/'native_powerpoint_validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
