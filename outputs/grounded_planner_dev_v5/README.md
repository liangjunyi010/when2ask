# Grounded Dev v5 evidence

- Main command center: http://127.0.0.1:8877/ (Default v1 remains selected; explicitly choose Grounded Dev v5).
- Live paired study: http://127.0.0.1:8894/?comparison=283a02340d73490c (use paired-run selector for the other tasks).
- [Study interpretation and limitations](../../docs/grounded_planner_dev_v5.md).
- [Automatically computed report](report.md), [summary JSON](summary.json), [episode CSV](episodes.csv), [method CSV](methods.csv).
- [Frozen r2 plan](live_plan_r2.json), [wire/turn/physics mapping audit](mapping_validation.json), [test counts](test_validation.json).
- `live/<task>__<method>/`: original episode, API attempts, physical trace, evaluation, review and actual screenshots; no invented outcomes.
- `browser/validation.json`: final Chrome scripted-policy / real-physics manual regression (zero paid API requests). This is separate from the nine real-model episodes.
- `preflight_r1/` and `live_plan.json`: three aborted r1 real launches, six requests, preserved without rewriting. The Dev schema/health amendment was then locked in r2 before nine fresh paired episodes. Total12 real launches,127/150 authenticated requests. All debug requests are included in cumulative cost.
- [Nine physical MP4s](../../presentation/grounded_dev_v5/README.md). Full GIFs remain in the ignored `outputs/local_console/task6_worker_v1/<episode_id>/` directories. Videos show simulation time rather than API/human waiting time.

R2 results: NoAsk1/3, LLM-Gate2/3, Jev-Gate2/3. Retrieval is still a planning failure: both gates ask at the right point, but the planner repeatedly reopens the restored box. No whole r2 episode was rerun or removed. The frozen benchmark and every historical result remain unchanged.

Offline report reproduction: `.venv/bin/python scripts/grounded_dev_report.py --export-media`. The online harness requires explicit `--live` and refuses to overwrite this study.
