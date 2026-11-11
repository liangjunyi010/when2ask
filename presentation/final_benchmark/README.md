# When2Ask — 10-minute benchmark presentation

The nine-slide English deck focuses on the independently held-out three-task v8 Benchmark. It does not combine that evaluation with the older two-template benchmark or its unrun 128-sample Test set.

- [PowerPoint with embedded video](deliverables/When2Ask_Benchmark_Presentation.pptx)
- [English speaker notes](speaker_notes.md): 1,169 spoken words; 585-second slide schedule, including demo.
- [22.2-second synchronized highlight](media/when2ask_highlight.mp4), [GIF fallback](media/when2ask_highlight.gif), and [51.5-second full replay](media/when2ask_full.mp4).
- [Slide previews](slide_previews/) and [presentation validation](presentation_validation.json).
- [HTML replay](web/index.html), [frame mapping](mapping_validation.json), and [browser checks](browser_validation.json).

Use PowerPoint Slide Show for embedded MP4 playback on slide 8. An animated GIF is embedded underneath as a fallback. PDF/PNG previews are static. The independent MP4 is available if another viewer does not support presentation video. No network or model key is needed to present.

**Actual checks:** project pytest **358 passed in97.43seconds**. All nine exported slides were individually inspected after LibreOffice PDF/PNG rendering. A byte-identical copy was opened in native **Microsoft PowerPoint16.115** and Slide Show started at slide8: `play_on_entry=true`, with real player positions **1992ms →3997ms** after two2-second waits. The show exited cleanly. Native screen pixels were not captured; the visual inspection used the exported PNGs. See `native_powerpoint_validation.json` and `checks/`.

## Story and timing

| Slide | Main point | Seconds |
|---|---|---:|
| 1 | Research question and contributions | 45 |
| 2 | Sample = layout, public instruction, DAG, private preference | 65 |
| 3 | Ask first / progress then ask / inspect instead of ask | 80 |
| 4 | Layout groups, independent Dev/Test, physical oracle | 70 |
| 5 | Three gates, one shared planner and execution stack | 60 |
| 6 | Independent physical success, burden, backend inference | 60 |
| 7 | Actual held-out success, burden and latency | 80 |
| 8 | Exploratory timing analysis and real synchronized video | 75 |
| 9 | Findings, limits and next experiment | 50 |

No source captions, file paths, generated-by text, or production notes appear on slides. Provenance is preserved in nonspoken speaker notes and `evidence_manifest.json`.

## Evidence boundaries

The v8 r2 dataset contains **24 Dev samples / 6 independent layouts** and **12 Test samples / 12 independent layouts**. All **36 physical oracle executions** passed. In 36 model-and-physics Test episodes: NoAsk **10/12**, LLM-Gate **12/12**, Jev-Gate **12/12**. Cumulative API latency is **57.91 / 105.41 / 78.56 seconds**, respectively, over 12 episodes per method. Mean burden is **0 / 0.333 / 0.333**. These are a small held-out study; they do not establish statistical superiority. Three rejected commands were repaired through later actual actions. Exact tokens remain separately reported by backend in the preserved benchmark summary and evidence manifest.

The first-ASK comparison on the two undisclosed retrieval tasks is an **exploratory post-Test trace analysis**. It was not a preregistered optimal-timing label. The correct task completion result remains independent of the planner's DONE and can include genuine repair.

The video comes from `outputs/three_task_v8/test_runs/t8_r2_test_1_04_1__jev_gate/episode.json` and its original GIF. It shows **0.11 CONTINUE → open → 0.62 ASK → answer → retrieve → rejected lid move → actual cover → success**. It is not the old 0.14/0.70 pack-and-cover demo. No episode, frozen setting or original record is edited. No new model API request is made during presentation production.

## Synchronization

Each logical frame retains its source GIF index, simulation step, duration, label, round, gate decision and probability. Positive-duration actions match their actual `start_step`/`end_step` and action label. The rejected command has its own recorded frame at step7514. ASK and USER remain separate ordered frames at the same step3620. Physical subphases come only from `execution_log`. Gate inference wall times are never reconstructed from simulation time.

One browser clock drives the frame, flow highlight and text together. Frames load before the whole state commits. Play/pause, seek/restart and1×/2×/3× controls share that clock. Six lossless WebP atlases package all164 source frames; no hundreds of frame intermediates are tracked. The exported MP4/GIF encode actual deterministic Chromium screenshots of the entire replay, not separate clocks or invented robot animation.

## Reproduce without paid APIs

From the repository root, after installing the normal project environment:

```bash
python presentation/final_benchmark/tools/write_script.py
python presentation/final_benchmark/tools/build_evidence.py
python -m http.server 8901 --bind 127.0.0.1
# http://127.0.0.1:8901/presentation/final_benchmark/web/
```

The committed HTML and atlases are self-contained: fresh clones can play without regenerating frames or having the ignored original GIF. Rebuilding atlases specifically needs the preserved original GIF. Authoring/export uses the bundled Artifact Tool runtime and local Chrome/Playwright, FFmpeg, Pillow, and XML tools:

```bash
node presentation/final_benchmark/tools/capture.mjs
python presentation/final_benchmark/tools/encode.py
node presentation/final_benchmark/tools/build_local.mjs
python presentation/final_benchmark/tools/embed_media.py
node presentation/final_benchmark/tools/finalize.mjs
python presentation/final_benchmark/tools/validate.py
```

Use the runtime returned by Codex `load_workspace_dependencies` for Node and its packages; normal shell `node` is shown for readability. The finalizer never overwrites an existing output: move an earlier locally generated deck to a versioned archive before rerunning. The editable native chart uses a15-significant-digit ratio for Excel portability; displayed exact counts10/12,12/12,12/12 and raw scores are retained. All source images are actual TinyRenderer scenes. No generated robotics artwork is used.

The saved Spaces deck uses the same authoring callbacks. Its connected API currently supports previews but not PPTX export or native movie insertion, so the local validated PowerPoint is the presentation-ready deliverable with media. The earlier Milestone PPT is preserved, including the user's existing uncommitted edits.
