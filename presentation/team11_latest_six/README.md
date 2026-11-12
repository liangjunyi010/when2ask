# Team 11 — final six slides

Open [When2Ask_Team11_Updated_Final.pptx](deliverables/When2Ask_Team11_Updated_Final.pptx). This copy preserves slides 1–5 of the supplied presentation and replaces slides 6–11. The original attachment is unchanged.

| Slide | Content |
| --- | --- |
| 6 | Nine implemented task types with real initial-scene images |
| 7 | Three gate-method flowcharts; single-call baseline explained separately |
| 8 | Editable cross-model table: measured DeepSeek row, blank GPT-5.6 and GLM 5.2 rows |
| 9 | Editable charts: task success, relative API time, relative estimated API cost |
| 10 | Embedded 50-second command-center recording, autoplay on slide entry |
| 11 | Achievements, limits and next steps |

## Table and chart interpretation

The cross-model table uses the LLM-Gate workflow: the selected conversational model serves as gate and planner. DeepSeek's measured success is 100.0%; unnecessary-ASK rate is 0.0%. API time and estimated cost are normalized to DeepSeek = 100.0%, so smaller values will mean lower time or cost. Other model cells are deliberately empty. The requested model labels are placeholders for future experiments, not verified availability or performance claims.

Slide 9 compares the four methods using the existing nine-task Dev pilot: 27 cases per method, 18 independent base-layout groups. API time and estimated USD are each normalized to LLM-Gate = 100%. This is a development pilot, not a held-out Test conclusion. No new model calls were made for this presentation update.

Values are derived from `outputs/nine_task_metrics_dev_v1/report/summary.json` and recorded in `assets/metrics.json`. Cost is estimated using the experiment's pricing assumptions; API latency excludes physical execution and human response time. The FPR denominator is the designated fully specified control set; NoAsk has no gate and is shown as not applicable.

## Presentation and checks

- [English speaker notes](speaker_notes.md): approximately 4 minutes 50 seconds for slides 6–11, including the 50-second demo.
- [Native PowerPoint PDF preview](previews/PowerPoint_render.pdf): all 11 slides rendered by Microsoft PowerPoint 16.115 on macOS.
- `previews/powerpoint-01.png` through `powerpoint-11.png`: native rendered pages, visually checked.
- `checks/validation.json`: preservation, table blanks, chart values, video identity and package checks.
- `checks/native_playback.json`: real PowerPoint Slide Show autoplay check; media position advanced from 1.893 to 3.897 seconds.
- `checks/finalization.json`: package, layout, fonts and portable editable chart/workbook validation.

The movie is self-contained inside the PPTX. The independent copy is `presentation/command_center_demo_v1/media/When2Ask_Command_Center_50s.mp4`. Press the slide-show advance control after the 50-second clip to continue to Conclusions.

## Reproduction

`tools/revise.mjs` authors slides 6–11 with ArtifactSession. `tools/assemble.py` grafts those slides into the original package and embeds the movie. `tools/finalize.mjs` validates and exports the final presentation. Intermediate source copies and generated packaging files are ignored. `tools/validate.py` rechecks the delivered package against the original attachment when that attachment is available locally.

From the repository root:

```sh
.venv/bin/python presentation/team11_latest_six/tools/validate.py
```

No frozen configuration, experiment output, application default, or existing presentation was modified. The first five slide parts and all their dependencies were verified byte-for-byte against the source.
