# Phase 3 Dev calibration — engineering pilot

All figures below are calculated from raw real-model episodes and per-attempt JSONL. Each method/threshold ran a fresh physical episode. No formal Test inference was run.

| Condition | Success | Burden total (mean) | DeepSeek in/out | Jev in/out | API latency s |
|---|---:|---:|---:|---:|---:|
| llm_gate | 7/8 | 12 (1.50) | 97812/1222 | None/None | 58.213 |
| llm_noask | 5/8 | 0 (0.00) | 41354/668 | None/None | 24.350 |
| jev_gate@0.7 | 6/8 | 7 (0.88) | 46150/809 | 58204/720 | 35.821 |
| jev_gate@0.5 | 7/8 | 11 (1.38) | 49801/947 | 65360/792 | 39.658 |
| jev_gate@0.3 | 7/8 | 11 (1.38) | 49801/947 | 65360/792 | 40.307 |

Selected threshold: **0.5**. No adequately supported alternative; retain predeclared default.

Intervals use independent scene groups (8 per condition), not paraphrases or truth variants. SR intervals are group-level Wilson 95%; alternative-vs-default differences use the predeclared paired group bootstrap 97.5% intervals. This small pilot does not establish equivalence or generalization.

Backend tokens remain separate and do not imply equal monetary cost. None denotes unknown/unused usage, not a manufactured zero. API latency is cumulative agent inference time; wall time also includes physics.

## Dataset

| Partition | Samples | Independent groups | Missing 0/1/2/3 |
|---|---:|---:|---|
| dev | 32 | 8 | 8/8/8/8 |
| test | 128 | 16 | 32/32/32/32 |

## Timing and errors

Timing labels in error_and_timing_cases.json use only public information, are diagnostics, and never feed back into any model or success score. Recovery states may be unclassified.

- llm_gate: early ASK=1, blocked CONTINUE=2, complete ASK=0, redundant slots=1, physical failures=0, API/schema errors=0/0.
- llm_noask: early ASK=0, blocked CONTINUE=19, complete ASK=0, redundant slots=0, physical failures=0, API/schema errors=0/0.
- jev_gate@0.7: early ASK=0, blocked CONTINUE=8, complete ASK=0, redundant slots=0, physical failures=0, API/schema errors=0/2.
- jev_gate@0.5: early ASK=0, blocked CONTINUE=2, complete ASK=0, redundant slots=0, physical failures=0, API/schema errors=0/0.
- jev_gate@0.3: early ASK=0, blocked CONTINUE=2, complete ASK=0, redundant slots=0, physical failures=0, API/schema errors=0/0.

## Traceability

See episodes.csv for sample/group pairing, episode path/hash, input/output usage, latency, termination and diagnostics; paired_groups.json retains paired units. threshold_selection.json preserves every paired difference and interval. Each episode directory includes API request/responses, public states, actions, Bullet events, dense physical trajectory, ASK invariance checks, evaluator details and real rendered PNGs.

Global authenticated requests: 293/600; episodes: 40/40. Discovery and smoke requests are counted separately from the method table, but included in this global ceiling.
