"""Retiming whole-browser footage; every panel and cursor stays in one video clock."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'presentation/command_center_demo_v1'
OUT=ROOT/'outputs/command_center_demo_v1'
BUILD=BASE/'.build'
MEDIA=BASE/'media'
SOURCE=BUILD/'full_live_capture.webm'

def run(args):
    subprocess.run(args,check=True)

def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
        'format=duration,size:stream=codec_name,width,height,avg_frame_rate,nb_frames,pix_fmt',
        '-of','json',str(p)]))

def main():
    global SOURCE
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--source',type=Path,help='Whole-browser capture; defaults to local WebM or the archived full MP4')
    supplied=parser.parse_args().source
    SOURCE=supplied or (SOURCE if SOURCE.exists() else MEDIA/'When2Ask_Command_Center_Full.mp4')
    events=json.loads((OUT/'capture_events.json').read_text())['events']
    duration=float(probe(SOURCE)['format']['duration'])
    def first(kind):return next(e['capture_ms']/1000 for e in events if e['kind']==kind)
    focuses=[e for e in events if e['kind']=='answer_focus']
    assert len(focuses)==3
    segments=[]
    def add(label,start,end,target):
        assert end>start and target>0
        segments.append(dict(label=label,source_start_s=start,source_end_s=end,target_frames=round(target*30)))
    add('Empty command center',first('empty_ready'),first('configure_start'),2)
    add('Select and dispatch four missions',first('configure_start'),first('all_dispatched'),12)
    end=first('all_dispatched')
    for i,focus in enumerate(focuses):
        at=focus['capture_ms']/1000
        submitted=next(e['capture_ms']/1000 for e in events if e['kind']=='answer_submitted' and e['question_id']==focus['question_id'])
        add('Queue selection',end,at,.6)
        end=submitted+1.5
        add('Read, type and submit answer '+str(i+1),at,end,6 if i==0 else 5.5)
    # Remaining time belongs to observed physical completion; no events are cut/reordered.
    allocated=sum(s['target_frames'] for s in segments)
    add('Robots finish their tasks',end,first('all_terminal'),(1500-allocated-120)/30)
    add('Four independently evaluated successes',first('all_terminal'),duration,4)
    assert sum(s['target_frames'] for s in segments)==1500
    video_t=0
    for i,s in enumerate(segments):
        length=s['source_end_s']-s['source_start_s'];target=s['target_frames']/30
        s.update(display_start_s=video_t,display_end_s=video_t+target,speed=length/target)
        video_t+=target
        # Source is a single Chromium viewport capture, never independent camera/UI tracks.
        filters=(f"setpts=(PTS-STARTPTS)*{target/length:.12f},fps=30,"
                 f"tpad=stop_mode=clone:stop_duration=1,"
                 "drawbox=x=1120:y=1042:w=800:h=38:color=0x081422:t=fill,"
                 "drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:"
                 f"text='Recorded live  |  {s['speed']:.1f}x playback':"
                 "fontcolor=0x9eb7ce:fontsize=21:x=w-tw-28:y=h-29")
        dest=BUILD/f'segment_{i:02d}.mp4'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(s['source_start_s']),
             '-i',str(SOURCE),'-t',str(length),'-an','-vf',filters,
             '-frames:v',str(s['target_frames']),'-c:v','libx264','-preset','fast','-crf','20',
             '-pix_fmt','yuv420p','-movflags','+faststart',str(dest)])
        s['encoded_frames']=int(probe(dest)['streams'][0]['nb_frames'])
        assert s['encoded_frames']==s['target_frames'],s
    listing=BUILD/'segments.txt'
    listing.write_text(''.join(f"file 'segment_{i:02d}.mp4'\n" for i in range(len(segments))))
    final=MEDIA/'When2Ask_Command_Center_50s.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
         '-i',str(listing),'-c','copy','-movflags','+faststart',str(final)])
    full=MEDIA/'When2Ask_Command_Center_Full.mp4'
    if SOURCE.resolve()!=full.resolve():
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(SOURCE),'-an',
             '-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p',
             '-movflags','+faststart',str(full)])
    # Decode the delivered file and inspect the exact PPT frames, rather than source screenshots only.
    for name,at in [('empty',1),('dispatch',10),('question',16),('typing',19),('resume',36),('success',48)]:
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(at),'-i',str(final),
             '-frames:v','1',str(BASE/'screenshots'/f'video_{name}.png')])
    record=dict(source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                retiming='Whole viewport retimed together, chronological and continuous; three operator answers are real. Only pre-load frames are trimmed.',
                capture='Playwright Chromium 1920x1080 at 25 fps',segments=segments,
                highlight=probe(final),full=probe(full),audio='Silent for live presenter narration',
                highlight_sha256=hashlib.sha256(final.read_bytes()).hexdigest())
    (OUT/'edit_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    assert abs(float(record['highlight']['format']['duration'])-50)<.05
    assert record['highlight']['streams'][0]['nb_frames']=='1500'
    print(json.dumps({k:record[k] for k in ['highlight','full']},indent=2))

if __name__=='__main__':main()
