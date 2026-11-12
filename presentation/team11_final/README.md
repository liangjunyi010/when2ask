# Team 11 — When2Ask final presentation

**Liang Junyi and Yang Haocheng**

- [Presentation with embedded synchronized replay](deliverables/When2Ask_Team11_Final_Presentation.pptx)
- [English speaker notes](speaker_notes.md), also embedded in the PowerPoint
- [PDF preview](slide_previews/When2Ask_Team11_Final_Presentation.pdf)
- [Full-size slide previews](slide_previews/)
- [Rubric mapping](rubric_coverage.json) and [validation](presentation_validation.json)

The ten-slide presentation is scheduled for **9 minutes 30 seconds**, including a separate **22.2-second** recorded-demo hold. The **1,038-word** script leaves 30 seconds within the ten-minute limit. Private evidence paragraphs are not spoken. The title slide contains the full team number and both names.

| Slides | Required section | Content |
|---|---|---|
| 2 | Problem and motivation | Strong zero-shot LLM capability, response latency and inference cost, plus missing user preferences |
| 3–6 | Approach and implementation | Runtime loop, three task DAGs, layout grouping, physical oracle and shared-planner methods |
| 7–9 | Results and demonstration | Physical success and burden, measured API time, estimated USD and real synchronized replay |
| 10 | Discussion and conclusions | Benchmark achievements, limits, takeaways and next experiment |

The Problem script starts with the requested classroom connection: “As we learned in class…” It paraphrases the team's supplied description of the lecture. It does not invent a quotation from the instructor or attribute unmeasured model superiority to the class.

## Editable execution diagram

Slide 3 has nine native nodes and 17 editable connector segments. Orange is the ASK branch, blue is CONTINUE, and green is evaluation. Both history and observation return to Public State. Only Action Planner connects DONE to the evaluator; Gate never issues an action or DONE. The figure shows the normal execution loop. The runner also scores episodes that terminate through errors or budgets.

`flow_spec.json` records the intended graph and coordinates. Validation checks actual PPTX connectors, endpoint positions, arrow directions and routing around unrelated nodes. Visual review separately checks text and arrows. The benchmark uses structured simulator answers; the existing HTML also supports manual answers. Neither feature changes the frozen evaluation.

## Evidence boundaries

The preserved three-task v8 Test contains 12 independent layout groups, paired across three methods: 36 real model/PyBullet episodes. NoAsk succeeded in 10/12 and both gates in 12/12. Average burden is 0 / 0.333 / 0.333. Cumulative API latency totals 57.91 / 105.41 / 78.56 seconds for 12 episodes per method. Mean Gate API response is 815.114 ms over 53 DeepSeek calls versus 294.803 ms over 54 Jev calls, from different trajectories rather than identical-input latency trials.

USD values remain the prior **current-price estimates, not invoices**: $0.010921350 / $0.018457914 / $0.017770626. Prices were checked on 12 November 2026. The derivation uses actual DeepSeek cache hits, misses and outputs at published off-peak rates, plus Jev's separately priced input usage. Jev-Gate's estimated whole-workflow saving over LLM-Gate is modest, 3.72%. NoAsk remains fastest and cheapest overall. All assumptions, raw-attempt references and backend token totals remain in [the preserved cost analysis](../final_benchmark_cost/analysis/cost_report.json).

The replay comes from the existing held-out retrieval episode: **0.11 CONTINUE, open, 0.62 ASK, answer, retrieve, rejected generic lid move, actual cover repair, success**. Its enlarged video is byte-identical to the previous synchronized recording. The 164-frame GIF is also embedded as a fallback. Use PowerPoint Slide Show; PDF previews are static. [Independent MP4](../final_benchmark/media/when2ask_highlight.mp4).

No new model API requests or experimental reruns occur. Frozen data, prompts, settings, raw records, prior decks and the user's modified Milestone PPT remain unchanged. The saved Spaces presentation is edited in place with preserved slide IDs. Its connected interface supports previews but not PowerPoint export/native video, so the verified local media-enabled PPTX is the presentation-ready fallback.

## Reproduction

Run from the repository root with the bundled Artifact Tool Node runtime. No `.env` or model client is read.

```bash
.venv/bin/python presentation/team11_final/tools/write_script.py
node presentation/team11_final/tools/build_local.mjs
.venv/bin/python presentation/team11_final/tools/embed_media.py
node presentation/team11_final/tools/finalize.mjs
.venv/bin/python presentation/team11_final/tools/run_native.py
.venv/bin/python presentation/team11_final/tools/validate.py
```

The builder applies focused callbacks to the preceding deck. Finalization preserves native tables and charts and includes embedded chart workbooks. As with the previous version, the finalizer refuses to overwrite outputs/receipts: archive your own previous generated build and select a unique receipt before rebuilding. Keep the immutable benchmark inputs intact.
