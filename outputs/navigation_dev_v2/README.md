# Navigation Dev v2 — actual engineering pilot

[Read-only HTML report](study_v2/index.html) · [Interpretation and caveats](ANALYSIS.md) · [Protocol/preservation/cost audit](audit.json) · [Reproduction guide](../../docs/navigation_dev_v2.md)

Local report server: http://127.0.0.1:8880/study_v2/index.html

- 24 physical sample/cost conditions plus two exhaustive searches: **26/26 passed**.
- 48 real gate-only calls: two contracts × two payload forms × two backends × six measured public states.
- 12 valid real-model physical episodes: four cost cells × three methods.
- **226 offline tests passed**. Pytest never contacts paid APIs.
- One original map group, one seed-selected target for the full cost factorial. No statistical or held-out Test claim.
- Same planner/controller/evaluator for all methods. Fixed Jev threshold 0.5. No outcome-based prompt/threshold selection.

| Method | Physical success | Mean burden | Mean operational seconds | Total API latency seconds |
|---|---:|---:|---:|---:|
| llm_noask | 4/4 | 0.00 | 56.37 | 16.34 |
| llm_gate | 4/4 | 0.50 | 60.63 | 35.43 |
| jev_gate | 4/4 | 0.50 | 94.48 | 32.04 |

Operational seconds = physical simulation motion + actual reply waiting + 5s interruption equivalent per requested slot. This predeclared setting is not measured human utility. API cost and end-to-end wall time are separate; backend tokens are never combined into money.

All 48 static ablation decisions were CONTINUE, so the small matched-state ablation did not establish a decision-level contract/summary improvement. During complete episodes, both gates asked in the two half-speed cases. Jev asked after four inspections in each, with higher realized operational cost here. Shared planner route variability also affects results. These are observations on one controlled target, not a general ranking.

## Technical incident, fully retained

The first run (`study_v1`) made 48 successful Gate calls but an Action request failed HTTP 400 because the new prompt omitted the literal JSON marker required for JSON-object output. Its backend breaker aborted 12 registered launches before motion. Six launch-stage requests and every failed trajectory remain in that directory.

The corrected plan (`study_v2`, code b1d1c62) changed only Action/Question JSON format declarations, preserved Gate/criteria and dataset/snapshot hashes, reused the 48 gate results without extra calls, and allowed 12 valid navigation launches. Combined registrations are 24, including 12 pre-motion aborts. The total-request cap remains 200 via a 54-request offset.

Actual cumulative authenticated requests: **172/200** = 48 gate-only + 6 protocol-incident + 118 valid-episode attempts. There is one HTTP 400 with unknown token usage, explicitly retained; valid episodes have actual usage. Returned models: deepseek-flash, jev-1.14.0.

## Evidence

- [Physical oracle runs](oracle/results.json).
- [Full valid raw episodes and JSONL requests/responses](study_v2/episodes/).
- [Gate-only raw results](study_v2/ablation/results.json).
- [Locked plan and hashes](study_v2/plan.json).
- [Automatic episode CSV](study_v2/episodes.csv), [method CSV](study_v2/methods.csv), [ablation CSV](study_v2/ablation.csv).
- [Unpaid physical policy anchors](references/results.json): actual wheel-driven physics, with explicitly modeled reply costs, not slept user delays or model outcomes.
- [Final pytest XML](pytest-final.xml) and [actual Chromium rendering checks](browser_validation.json).

All 1,261 protected pre-existing tracked file hashes match, including frozen experiments, Navigation Dev v1, stable robot skills and the user's already-modified PPT. No held-out Test API calls; existing local console remains v1. No real hardware, learned-vision, new independent maps or dual-computer claim.
