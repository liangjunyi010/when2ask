"""Encode whole-HTML screenshots using the saved source-driven display schedule."""
import json
import subprocess
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
BUILD=BASE/".build"
MEDIA=BASE/"media"


def run(args):
    subprocess.run(args,check=True)


def main():
    MEDIA.mkdir(exist_ok=True)
    schedule=json.loads((BASE/"export_schedule.json").read_text())
    results=[]
    highlight_only='--highlight-only' in sys.argv
    if highlight_only:
        prior=json.loads((BASE/'media_validation.json').read_text())
        results.extend(e for e in prior['media'] if e['file']=='when2ask_full_replay.mp4')
    for entry in schedule["exports"]:
        view=entry["view"]
        if highlight_only and view=='full':
            continue
        name="when2ask_full_replay.mp4" if view=="full" else "when2ask_milestone_highlight.mp4"
        target=MEDIA/name
        run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-f","concat","-safe","0",
             "-i",str(BUILD/f"{view}.concat.txt"),"-t",str(entry["duration_ms"]/1000),
             "-vf","fps=60" if view=='highlight' else "fps=30","-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
             "-movflags","+faststart",str(target)])
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(target)]))
        video=next(s for s in probe["streams"] if s["codec_type"]=="video")
        assert abs(float(probe["format"]["duration"])-entry["duration_ms"]/1000)<.07
        assert video["width"]==entry["viewport"]["width"] and video["height"]==entry["viewport"]["height"]
        results.append(dict(file=name,bytes=target.stat().st_size,duration_s=float(probe["format"]["duration"]),
                            width=video["width"],height=video["height"],codec=video["codec_name"],
                            source="Deterministic whole-HTML Chromium screenshots",frame_rate=video["r_frame_rate"]))
    gif=MEDIA/"when2ask_milestone_highlight.gif"
    duration=next(e["duration_ms"] for e in schedule["exports"] if e["view"]=="highlight")/1000
    run(["ffmpeg","-hide_banner","-loglevel","warning","-y","-f","concat","-safe","0",
         "-i",str(BUILD/"highlight.concat.txt"),"-t",str(duration),"-filter_complex",
         "[0:v]fps=30,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
         "-loop","0",str(gif)])
    from PIL import Image
    with Image.open(gif) as image:
        gif_duration=0
        for index in range(image.n_frames):
            image.seek(index);gif_duration+=image.info.get("duration",0)
        assert image.n_frames>100 and abs(gif_duration/1000-duration)<.15
        results.append(dict(file=gif.name,bytes=gif.stat().st_size,duration_s=gif_duration/1000,
                            width=image.width,height=image.height,frames=image.n_frames,
                            source="Same deterministic whole-HTML screenshots, palette encoded"))
    (BASE/"media_validation.json").write_text(json.dumps(dict(media=results,all_durations_match_schedule=True),indent=2)+"\n")
    print(json.dumps(results,indent=2))


if __name__=="__main__":
    main()
