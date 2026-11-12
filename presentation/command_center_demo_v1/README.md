# When2Ask command center demonstration

Use **`media/When2Ask_Command_Center_50s.mp4`** in the presentation. It is a silent
1920×1080, 30 fps, H.264/yuv420p MP4, exactly 50 seconds, approximately 4.2 MB.
The sound track is intentionally absent so the presenter can speak over it.
`speaker_notes.md` supplies approximately 50 seconds of English narration.
The 86.24-second full browser recording is also provided in `media/`.

## What happens

| Video time | On-screen action |
|---|---|
| 0–2 s | Empty command center |
| 2–14 s | Select task/method/reply mode and start four missions |
| 14–21 s | Answer the Jev robot's buffer-pad question |
| 21–27 s | Answer which item the LLM-Gate robot should retrieve |
| 27–33 s | Answer the Jev robot's sorting destination question |
| 33–46 s | Robots continue their physical tasks |
| 46–50 s | Four actual independent physical success results |

This is the **existing English HTML console**, operated through real Chromium
controls with a recording-only CSS layout. The local default web assets, model
prompts, skills, benchmarks and earlier experiment records were not changed.
The operator is browser automation playing the human role: it types visible
candidate names into the actual textarea and clicks Submit Answer. The three
questions are actual model outputs, not prewritten triggers. No private answer
is supplied to a model or read by the operator automation. In interactive human
mode the declared preference defines the goal, as in the existing console.

| Task | Actual method | Response mode | ASK turns | Physical result |
|---|---|---|---:|---|
| Retrieve & Restore | LLM-Gate / DeepSeek | Human | 1 | Success, 6/6 conditions |
| Buffered Exchange | Jev-Gate + DeepSeek | Human | 1 | Success, 8/8 conditions |
| Category Sorting | Jev-Gate + DeepSeek | Human | 1 | Success, 4/4 conditions |
| Find & Approach | LLM-NoAsk | Fully specified | 0 | Success, 5/5 conditions |

Exactly four live episodes and **38 authenticated requests**, all successful,
were used. Returned models: `deepseek-flash`, `jev-1.14.0`. The real buffer gate
asked at p=0.57. No additional episodes were run to obtain a preferred outcome.
Navigation was fully disclosed and successfully completed without asking.
This demonstration is **not a paired performance experiment or held-out Test**.
It was run on one computer; it does not claim two-computer validation.

## Synchronization and validation

Playwright recorded the whole browser viewport, including the camera frames,
questions, cursor, typing, status and final evaluation. Editing retimes that
single video track. It never animates semantic panels separately or reorders
events. All footage from the empty ready page through completion is retained;
only initial page loading is trimmed. Playback speed appears in the footer.

Three sampled answer intervals verified an unchanged simulation step and frame
SHA for the waiting robot while at least one other physical world progressed.
Steps were 240, 3702 and 6861. All four final scores come from the existing
independent evaluator. Actual episode/API records are preserved under
`outputs/command_center_demo_v1/episodes/`.

`outputs/command_center_demo_v1/` contains the capture plan, browser timestamps,
visible state samples, interaction validation, per-segment edit manifest, video
metadata and full playback validation. Screenshots include both the live
browser and six decoded frames from the delivered MP4. The main video has 1,500
frames. Chromium checked seeking and a complete 1× playback with no media or
JavaScript errors. Original private credentials and the worker token are excluded.

## Preview and regeneration

An offline player is available at `index.html`; it launches no model requests.
The delivered local preview is served at `http://127.0.0.1:8909/`.

```sh
# Offline preview from the repository root
.venv/bin/python -m http.server 8909 --bind 127.0.0.1 \
  --directory presentation/command_center_demo_v1

# Offline video export; uses .build/full_live_capture.webm if available,
# otherwise the archived full MP4. No model calls.
.venv/bin/python presentation/command_center_demo_v1/tools/export.py
```

`tools/capture.mjs --live` is the actual operator script. It requires a **fresh**
live console on port 8908 and refuses an existing capture plan or a used session.
The original controller was started with capacity 4, a 4-episode ceiling and a
160-request ceiling. Do not rerun paid capture merely to watch the finished video.
The exact original session stays under the ignored local console directory.

Source clips and intermediate encodes are ignored in `.build/`; the MP4s,
screenshots, source scripts, narration and sanitized evidence are delivered.
The existing PowerPoint files have not been edited or overwritten.
