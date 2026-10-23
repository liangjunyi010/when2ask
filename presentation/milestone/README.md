# When2Ask milestone presentation

This delivery replays **preserved live-model / real PyBullet evidence**. It makes no DeepSeek/Jev requests and does not run or tune the held-out Test. The source branch was `feat/devtest-calibration` at `960c7caa4e2051eef898ae82b67da1051e682645`.

## Ready-to-present files

| File | Purpose |
|---|---|
| [When2Ask_Milestone_Presentation.pptx](When2Ask_Milestone_Presentation.pptx) | Exactly two editable 16:9 slides. Slide 1 contains the actual animated GIF **and embedded H.264 MP4**. Slide 2 has an editable results table. |
| [media/when2ask_milestone_highlight.mp4](media/when2ask_milestone_highlight.mp4) | 11.88 s, 1280×720 at 60 fps, entire synchronized HTML, under 1 MB. Preferred standalone playback fallback. |
| [media/when2ask_milestone_highlight.gif](media/when2ask_milestone_highlight.gif) | 11.86 s, 1280×720 at 30 fps, 356 animated frames, 3.27 MB. |
| [media/when2ask_full_replay.mp4](media/when2ask_full_replay.mp4) | 49.20 s, 1920×1080, complete original display timeline at 1×. |
| [speaker_notes.md](speaker_notes.md) | User's exact 243-word script, targeting 55–60 s for Slide 1 and 60–65 s for Slide 2. Also embedded in the PPT notes. |
| [speaker_script.json](speaker_script.json) | Authoritative user-provided script and titles, checked against the embedded PPT notes. |
| [slide_previews/When2Ask_Milestone_Presentation.pdf](slide_previews/When2Ask_Milestone_Presentation.pdf) | Static preview only. The PPT and independent MP4 contain the animation. |
| [web/index.html](web/index.html) | Offline replay app, served locally as described below. No CDN, fonts, cloud media or API credentials. |

Use PowerPoint Slide Show for the deck. The MP4 declares slide-entry playback with looping, matching the GIF's repeat behavior during the spoken demo. It also has a click-to-play media action. A complete animated GIF sits beneath it as a fallback, including for viewers that omit video objects. Neither embedded asset is just a first-frame screenshot. Both media streams contain robot and flow together, so presentation software cannot desynchronize the two halves.

The current script-matched revision uses **When2Ask: System & Real Demo** and **Benchmark & Preliminary Results** as its two titles. It highlights the real 0.14 CONTINUE / 0.70 ASK sequence, names both task types, and retains the exact Dev table while summarizing 39.66 s and 58.21 s as approximately 40 s and 58 s, as in the script. The previous 19.16 s highlight/deck remain recoverable in commit `b80b0be`. The full 49.2 s movie and all original experimental records remain unchanged.

**Validation boundary:** final slides were rendered by local LibreOfficeDev 26.8 to PDF and then 1920×1080 PNGs, and individually inspected. PowerPoint 16.114.1 subsequently opened a byte-identical verification copy. Native inspection exposed that a video node alone did not register as automatic playback, so the final deck adds an actual media-call event starting with the slide. PowerPoint now recognizes both play-on-entry and looping. In a real Slide Show the live player reported **2012 ms → 4023 ms → 2128 ms** at scheduled 2/4/14-second checks, confirming automatic playback and a loop across the 11.88-second clip. See [native_powerpoint_validation.json](native_powerpoint_validation.json). Native screen pixels were not captured; slide visual inspection used the rendered PNGs. The independent MP4 remains available for other viewers.

## Open the HTML

Fast script-matched preview: <http://127.0.0.1:8765/?view=highlight&autoplay=1>. The full original playback remains at <http://127.0.0.1:8765/>. From the project root the equivalent server command is:

```bash
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory presentation/milestone/web
```

The default page has Play/Pause, Restart, seek, 1×/2×/3× and an episode selector. `?presentation=1` hides controls for presentation. `?episode=llm_containers` selects the real two-container episode. `?view=highlight` uses exactly the accelerated export intervals in the interactive master clock; add `&autoplay=1` to start it. `?export=1&view=highlight` hides controls for deterministic capture. With no highlight parameter, interactive playback follows the full source timeline.

The delivered web directory is self-contained. A fresh clone can play it using only HTTP and a modern browser, without the original ignored GIFs or Python simulation. The original 640×480 renderer resolution remains visible when enlarged; no generated robot imagery or sharpening is substituted.

## Evidence and exact synchronization

Main source: `outputs/phase2_live/paired_v2/validation_002/jev_gate/`:

- `episode.json`, `evaluation.json`, `api_attempts.jsonl`, `scene.png`, and the original local `demo.gif`.
- 447 logical frames / 447 GIF frames, 49,200 ms.
- Three actual skills: blue cup into box, green block into box, black lid covers box. Recorded `grasp_mode=constraint` is retained in the original image HUD and event provenance.
- ASK probability 0.14 → CONTINUE, then 0.70 → ASK, then recorded 0.09/0.15 CONTINUE and 0.03 before DONE. No model inference is rerun.

Second source: `outputs/phase3_live/dev/v3_dev_016__llm_gate/`, 315 frames / 36,000 ms, real two-container execution. This example includes an actual redundant initial question even though preferences were already public. Its LLM gate has **no Noul probability**; the page displays none.

`scripts/build_replay.py` and `src/when2ask/replay.py` create [web/timeline.json](web/timeline.json). For each original recording entry:

```text
start_ms[i] = sum(duration_ms[0:i])
end_ms[i]   = start_ms[i] + duration_ms[i]
```

The mapping uses these original fields:

| Source field | Use |
|---|---|
| `recording.frames[].simulation_step / duration_ms / label` | Ordered frame display intervals; ASK and USER distinguishable at the same physical step. |
| `turns[].round / gate / question / user_answer / action` | Recorded decision, real probability, question, disclosed response, action. |
| `turns[].physical_result.start_step / end_step` and `actions[]` | Match physical action to a measured skill interval, kind and object identity. |
| `execution_log[].kind / phase / step / object_id` | Latest actual Approach/Grasp/Lift/Transport/Lower/Release/Settle event at the displayed step. |
| Public initial observation + public instruction/answers | Human-readable object names and disclosed preferences. No future answer shown early. |
| Final `evaluation` / standalone `evaluation.json` | Real independent outcome, only displayed at the recorded final frame. |

Each timeline frame retains source frame index, encoded GIF frame index, source-pixel SHA-256, interval, step, round, flow nodes/edges, current skill/phase, question/answer, outcome and JSON-pointer evidence. Source-file hashes are in the manifest. Lossless WebP atlases hold exact decoded source pixels, with 32 images per atlas (24 atlases total), so hundreds of intermediate files need not enter Git.

The browser uses **one master display clock**. It selects a timeline frame, loads its atlas tile, then commits the left canvas and right flow state together in `renderAt`. Play, seek, restart, pause and speed all use that same clock. There is no freely looping GIF or separate flow-highlighting timer. During loading it holds the previous complete frame/state rather than showing a new flow over old pixels.

Recorded decision results are overlaid on matching display intervals. The recorder did not capture separate wall-clock instants for Gate, Planner and Evaluator within one physical step. The page explicitly labels these as source display time, not inferred model latency. API latency remains in the original attempt logs. The initial OBSERVE frame shows its associated first recorded Gate/Planner result retrospectively, without claiming an instantaneous model call.

## Mapping acceptance checks

All requested six stages passed, with additional transport and cover checks:

| Checkpoint | Source frame (0-based) | Simulation step | Full display start | Active node | Actual p(ASK) |
|---|---:|---:|---:|---|---:|
| Initial decision | 0 | 240 | 0.0 s | Gate / CONTINUE | 0.14 |
| Cup grasp | 40 | 1200 | 4.6 s | PyBullet Execution | 0.14 |
| Cup transport | 62 | 1728 | 6.8 s | PyBullet Execution | 0.14 |
| ASK | 143 | 3663 | 14.9 s | Question Planner | 0.70 |
| User answer | 144 | 3663 | 16.1 s | User Simulator | 0.70 |
| Block transport | 208 | 5184 | 23.6 s | PyBullet Execution | 0.09 |
| Cover transport | 369 | 9048 | 39.7 s | PyBullet Execution | 0.15 |
| DONE / Success | 446 | 10877 | 47.4 s | Independent Evaluator | 0.03 |

Each browser check verifies displayed source pixels by SHA-256, actual frame index and step, DOM node, action/question/answer and gate. All **762 source frames** across both cases passed pixel and flow checks. Pause, seek, replay, episode switching and 1×/2×/3× were exercised, including physical transport and the ASK→USER boundary. Console errors, failed loads and external network requests: **0**.

The accelerated interactive mode additionally passed all **447** main-episode source frames, exact export-interval matching, and ASK→USER transitions at each playback speed. [revision_validation.json](revision_validation.json) verifies the shorter duration, identical source-frame order, unchanged full MP4 and exact supplied script provenance.

Screenshots are in [screenshots/](screenshots/). Machine-readable results:

- [mapping_validation.json](mapping_validation.json): browser + independent original JSON/GIF checks.
- [export_schedule.json](export_schedule.json): all exported frame timings, source indices and screenshot hashes.
- [media_validation.json](media_validation.json): codecs, dimensions, duration and 16 decoded MP4 checkpoint comparisons.
- [pptx_validation.json](pptx_validation.json): embedded media hashes, 356 GIF frames, two slides, native table, exact script/title matching and raw-data verification.
- [source_preservation.json](source_preservation.json): SHA-256 of 847 protected original files, all unchanged.
- [pytest.xml](pytest.xml): **102 passed** (preserved 96 benchmark tests + 6 new replay tests). No paid network calls.

## Video timing and compression

The browser exports every logical frame as a whole-page screenshot using `window.replay.renderFrame(index)`. These ignored `.build/` images are then encoded by FFmpeg. No screen-recording delay estimates are involved.

Full MP4 uses every original display duration at 1× and remains unchanged. Highlight physical intervals now use 6× compression, while initial / ASK / answer / evaluation holds use 500 / 1400 / 1600 / 1000 ms. Both left and right come from the **same captured image** for each interval. Total planned highlight duration is 11.883 s, about 38% shorter than the previous 19.157 s. Highlight H.264 is sampled at 60 fps and GIF at 30 fps (full movie remains 30 fps). Output lengths differ by under 30 ms and some short compressed source frames are resampled. Source order, decisions, questions, object identities and outcome remain unchanged. The page visibly labels compression.

## Reproduce offline

Existing tested environment: Python 3.11.16, Pillow 13.0.0, NumPy 2.4.6, pytest 9.1.1; local Chrome 156.0.8078.47, FFmpeg 7.1.1, Codex-bundled Node 24.19.0, Playwright, Artifact Tool 2.8.99 and LibreOfficeDev 26.8. Arial is installed. Playback itself only needs a browser.

```bash
# Rebuild atlases and manifest from the existing ORIGINAL local recordings.
# Those source GIFs remain in their original ignored outputs directories.
.venv/bin/python scripts/build_replay.py

# In a second process, serve the page (no model APIs).
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory presentation/milestone/web

# Local Node executable on the delivery machine:
REPLAY_NODE="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
"$REPLAY_NODE" presentation/milestone/tools/browser_validation.mjs
.venv/bin/python presentation/milestone/tools/validate_sources.py
"$REPLAY_NODE" presentation/milestone/tools/capture_export.mjs
.venv/bin/python presentation/milestone/tools/encode_media.py
# Add --highlight-only to these two commands to preserve the existing full export.
.venv/bin/python presentation/milestone/tools/validate_encoded_media.py

# Author fresh drafts with editable text/table, then add actual media.
"$REPLAY_NODE" presentation/milestone/tools/build_slides.mjs
.venv/bin/python presentation/milestone/tools/embed_media.py
# finalize_slides.mjs deliberately refuses to overwrite an existing deck.
# Use a new delivery location/revision when intentionally rebuilding it.
"$REPLAY_NODE" presentation/milestone/tools/finalize_slides.mjs
soffice --headless --convert-to pdf --outdir presentation/milestone/slide_previews presentation/milestone/When2Ask_Milestone_Presentation.pptx
pdftoppm -png -scale-to-x 1920 -scale-to-y 1080 presentation/milestone/slide_previews/When2Ask_Milestone_Presentation.pdf presentation/milestone/slide_previews/slide-rendered
.venv/bin/python -m pytest -q --junitxml=presentation/milestone/pytest.xml
.venv/bin/python presentation/milestone/tools/validate_pptx.py
.venv/bin/python scripts/secret_scan.py
```

`tools/runtime.mjs` locates the delivery machine's bundled Node modules. Set `WHEN2ASK_RUNTIME_MODULES` for another installed module directory, `WHEN2ASK_CHROME` for another local Chrome executable, and `WHEN2ASK_PRESENTATIONS_SKILL` for another Artifact Tool finalizer location. These are build tooling paths, not runtime page dependencies. The source GIFs are unnecessary for playing the committed web assets or independent videos.

## Milestone numbers

The deck's numbers are checked from the **original** 24 raw Dev episode JSONs and from existing physical oracle/JUnit records by `tools/validate_pptx.py`:

| Method | Success | Average burden | Cumulative API latency (8 episodes) |
|---|---:|---:|---:|
| LLM-NoAsk | 5/8 | 0.000 | 24.35 s |
| LLM-Gate | 7/8 | 1.500 | 58.21 s |
| Jev-Gate (0.5) | 7/8 | 1.375 | 39.66 s |

These are preliminary Dev observations from 8 independent physical groups, with limited preference-truth coverage. They do not establish statistical significance, Test generalization or a universally better gate. The 160/160 figure describes prior physical oracle validation, **not** 160 online model successes. Formal held-out Test remains unrun. New API calls in this visualization task: **0**.

OOXML media implementation references: [Microsoft Open XML Video](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.video?view=openxml-3.0.1) and [Microsoft PlayOnEntry](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.playsettings.playonentry). All robot pixels and recorded decisions come from this repository's real experiments. No generated illustrative animation is used.
