# Memory Dev v6 evidence (2026-11-11)

[Implementation, root causes and limitations](../../docs/memory_planner_dev_v6.md). Main console http://127.0.0.1:8877/ offers **Memory Dev v6** explicitly; Original Default v1 and Dev v5 stay unchanged. [Recorded three-method retrieval comparison](http://127.0.0.1:8896/?comparison=2a887ccd10544e07); select other paired runs in that HTML.

- [Automatic report](report.md), [summary/costs](summary.json), [episode CSV](episodes.csv), [method CSV](methods.csv).
- [Frozen full-study plan](live_plan.json), [wire/memory/action mapping audit](mapping_validation.json), [root-cause evidence](root_cause_evidence.json), [historical comparison without modifying old records](historical_comparison.json).
- `live/<task>__<method>/`: original model-driven episode, every API attempt, actual physical trace, evaluator, review and real screenshots. All9 episodes have3 physical actions and model-generated DONE. Goal scoring is independent: NoAsk1/3, LLM-Gate3/3, Jev-Gate2/3. Zero reopens or exchange regressions; Jev buffer failure is an actual missed clarification/incorrect pad guess.
- `probes/` and `probes_r2/`: twelve paid action-only probes from actual prior public states, not physics episodes or success samples. One r1 move-versus-cover mismatch retained; final6/6 match. No raw record overwritten.
- `browser/`: final scripted-policy/real-physics manual UI regression, zero paid requests; two manual replies freeze physical frames/state. `main_console_validation.json` verifies Default v1/v5/v6 compatibility and restores10 historical cards without launching paid tasks.
- [Test evidence](test_validation.json): full343 offline passed, final16 targeted passed, three real physical diagnostic controls succeed. Offline checks are separate from live model results.
- [Nine downloadable physical MP4s](../../presentation/memory_dev_v6/README.md). Videos show actual simulation time; API/ASK wall time and dialogue are in the episode logs. Original full GIFs remain in ignored `outputs/local_console/task6_worker_v1/<episode_id>/` folders.

Exactly9 full episodes/66 requests plus12 action-only probe requests =78/150 cumulative authenticated requests, no full episode retries or aborted launches. Same persistent ledger and immutable final source/prompt plan across all9. No Test APIs, default/frozen changes or historical rewrites. All2,346 protected files verified identical.

Recompute without API calls: `.venv/bin/python scripts/memory_dev_report.py --export-media`. Online harnesses require `--live` and refuse to overwrite this namespace. This small engineering regression is not a statistical or held-out Test conclusion.
