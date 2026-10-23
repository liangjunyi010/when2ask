"""Compare decoded export pixels against deterministic HTML screenshots."""
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    schedule = json.loads((BASE / "export_schedule.json").read_text())
    checkpoints = json.loads((BASE / "mapping_validation.json").read_text())["checkpoints"]
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    checks = []
    for export in schedule["exports"]:
        filename = "when2ask_full_replay.mp4" if export["view"] == "full" else "when2ask_milestone_highlight.mp4"
        for checkpoint in checkpoints:
            f = export["frames"][checkpoint["frame_index"]]
            moment = (f["start_ms"] + f["end_ms"]) / 2000
            # Constant-fps encoding rounds sub-frame intervals. Compare the
            # nearest rendered state among the at-most-one-neighbour frames.
            encoded = subprocess.check_output([
                ffmpeg, "-v", "error", "-ss", str(moment), "-i", str(BASE / "media" / filename),
                "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-threads", "1", "-"
            ])
            actual = np.asarray(Image.open(io.BytesIO(encoded)).convert("RGB"), dtype=float)
            candidates = []
            for index in range(max(0, f["frame_index"] - 1), min(len(export["frames"]), f["frame_index"] + 2)):
                candidate = export["frames"][index]
                expected = np.asarray(Image.open(BASE / candidate["intermediate_screenshot"]).convert("RGB"), dtype=float)
                candidates.append((float(np.abs(actual - expected).mean()), index))
            mae, matched = min(candidates)
            assert mae < 2, (filename, checkpoint["label"], mae)
            # All non-physical holds have to match exactly the same source index.
            if f["stage"] != "execution":
                assert matched == f["frame_index"]
            checks.append({"media": filename, "checkpoint": checkpoint["label"], "export_time_s": moment,
                           "requested_source_frame": f["frame_index"], "matched_source_frame": matched,
                           "mean_absolute_rgb_error": round(mae, 4), "passed": True})
    report = json.loads((BASE / "media_validation.json").read_text())
    report["decoded_video_checkpoint_checks"] = checks
    report["encoding_note"] = "Whole HTML encoded atomically. Full MP4 30 fps, accelerated highlight MP4 60 fps and GIF 30 fps. No independent left/right resampling."
    (BASE / "media_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "decoded_video_checks": len(checks), "maximum_rgb_error": max(x["mean_absolute_rgb_error"] for x in checks)}))


if __name__ == "__main__":
    main()
