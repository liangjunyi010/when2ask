# When2Ask — revised 10-minute English presentation

This revision explains the problem, the three-method comparison, observed Gate response time and **estimated API dollars**. It preserves the original nine-slide deck and all frozen benchmark artifacts. It makes no new model API requests.

- [Presentation with embedded replay](deliverables/When2Ask_Benchmark_Presentation_v2.pptx)
- [English speaker notes](speaker_notes.md), also embedded in PowerPoint
- [PDF preview](slide_previews/When2Ask_Benchmark_Presentation_v2.pdf)
- [Per-slide previews](slide_previews/)
- [Reproducible cost derivation](analysis/cost_report.json), [method CSV](analysis/methods.csv), [stage CSV](analysis/stages.csv), [all 262 attempts](analysis/attempt_costs.csv)
- [Pricing assumptions](analysis/pricing_assumptions.json)

The ten-slide schedule totals **9 minutes 40 seconds**, including a separate 22.2-second video hold. The script has **1,091 spoken words**. Speaking at approximately 115–125 words per minute leaves a small margin within ten minutes. Evidence paragraphs in notes are not spoken.

| Slide | Topic | Seconds |
|---|---|---:|
| 1 | Strong LLM agents, missing preferences and repeated decision overhead | 55 |
| 2 | Public instruction, private preference and task DAG | 50 |
| 3 | Three task structures and clarification regimes | 60 |
| 4 | Base-layout groups, Dev/Test isolation and physical oracle | 55 |
| 5 | NoAsk / LLM-Gate / Jev-Gate with a shared DeepSeek Planner | 60 |
| 6 | Physical success, clarification burden and inference overhead | 55 |
| 7 | Reliability and cumulative workflow API latency | 60 |
| 8 | Mean Gate API response and estimated API dollars | 70 |
| 9 | Exploratory clarification timing and real synchronized replay | 75 |
| 10 | Conclusions, limits and next experiment | 40 |

## Evidence and estimates

All measured results below come from the **existing frozen v8 Test**: 12 independent layout groups, paired across three methods, 36 episodes and 262 agent API attempts. The separate English-console rehearsal and older benchmark versions are not pooled into these results.

| Method | Success | Mean burden | Cumulative API latency | Estimated DeepSeek USD | Estimated Jev USD | Estimated total USD |
|---|---:|---:|---:|---:|---:|---:|
| LLM-NoAsk | 10/12 | 0.000 | 57.91 s | $0.010921350 | N/A | $0.010921350 |
| LLM-Gate | 12/12 | 0.333 | 105.41 s | $0.018457914 | N/A | $0.018457914 |
| Jev-Gate | 12/12 | 0.333 | 78.56 s | $0.012894384 | $0.004876242 | $0.017770626 |

Each latency/cost total covers **12 episodes per method**, including Gate, Question, Action and DONE. API latency excludes robot motion and other episode wall time. Gate-only mean API responses are **815.114 ms over 53 DeepSeek calls** and **294.803 ms over 54 Jev calls**. They come from different trajectories, not an identical-state latency benchmark. Observed total API latency is 25.47% lower for Jev-Gate than LLM-Gate. Neither gate is faster or cheaper than NoAsk in this study.

Dollar values are **retrospective estimates using current public rates, not invoices or verified deductions**. Rates were checked on **12 November 2026** at [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/) and [TypeSafe models](https://docs.typesafe.ai/models). The raw DeepSeek timestamps span 11 November 2026, 13:53:34–13:55:36 UTC, outside the published peak clock hours. The estimate applies current off-peak rates to recorded cache hits, cache misses and output tokens:

```text
DeepSeek USD = (cache_hit_input × 0.003 + cache_miss_input × 0.15 + output × 0.6) / 1,000,000
Jev USD      = (input × 0.042 + output × 0) / 1,000,000
Total USD    = estimated DeepSeek USD + estimated Jev USD
```

Different backend tokens are priced separately before adding dollars. All source usage is present; unknown usage is never replaced by zero. Jev output is free under the documented rate, rather than unrecorded. The estimate excludes taxes, credits, discounts, robot/computer runtime and human effort. The report also includes a clearly hypothetical all-peak DeepSeek sensitivity calculation, separate from the timing-matched estimate.

The whole-workflow estimated saving of Jev-Gate versus LLM-Gate is **3.72%**, a modest difference. Shared planning, different trajectories and low cache-hit prices limit the advantage. We claim neither statistical superiority from 12 groups nor better zero-shot performance than BERT. There is no BERT baseline or unseen-template experiment. The provider's parallel probability-output description motivates the hypothesis; its marketing speed/cost multipliers are not used as project results.

## Playback and validation

Slide 9 contains the existing 22.2-second synchronized MP4 and a 164-frame animated GIF fallback. Use PowerPoint Slide Show. PDF previews are static. The [independent MP4](../final_benchmark/media/when2ask_highlight.mp4) remains available if another viewer cannot play embedded media. Original episode, frame mapping and motion are unchanged.

The saved editable Spaces deck was revised in place, preserving all original slide IDs. Its current API supports previews but not PPTX export/native video insertion, so the presentation-ready deliverable is the local validated PowerPoint fallback. Both use the same focused revision callback, theme, fonts, native charts and tables.

`presentation_validation.json` checks the slide text, notes, three native tables, two native charts/workbooks, cost/latency data and byte-identical replay. `native_powerpoint_validation.json` records native PowerPoint playback on a byte-identical disposable copy. Every final slide is also rendered through LibreOffice to PDF/PNG for visual inspection. The original user-modified Milestone PPT is preserved.

## Reproduce without paid APIs

Run from the repository root. Normal project Python dependencies and the bundled Artifact Tool runtime are required. No `.env` or API key is read by these tools.

```bash
.venv/bin/python presentation/final_benchmark_cost/tools/derive_cost.py
.venv/bin/python presentation/final_benchmark_cost/tools/write_script.py
node presentation/final_benchmark_cost/tools/build_local.mjs
.venv/bin/python presentation/final_benchmark_cost/tools/embed_media.py
node presentation/final_benchmark_cost/tools/finalize.mjs
.venv/bin/python presentation/final_benchmark_cost/tools/run_native.py
.venv/bin/python presentation/final_benchmark_cost/tools/validate.py
```

Use the Node executable and package directory supplied by Codex `load_workspace_dependencies`; `node` above is shorthand. The finalizer intentionally refuses to overwrite an existing output or receipt. Before a rebuild, archive only your previous locally generated output under ignored `.build/` and give the new receipt a unique filename. Keep the original frozen artifacts intact.
