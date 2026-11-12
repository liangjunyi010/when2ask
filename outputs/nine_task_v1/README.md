# Nine-task coverage pilot: evidence index

**All nine implemented task types were tested.** There are four new cases per task
(two Dev, two Test), with 36/36 actual PyBullet oracle successes. All 18 new Test
cases ran each of LLM-NoAsk, LLM-Gate and Jev-Gate, giving 54 real paired episodes.
NoAsk succeeded in 13/18; both Gate methods in 16/18. This remains a small pilot.

- [Per-task results, costs and failures](report/README.md)
- [Machine-readable summary](report/summary.json)
- [Per-episode CSV](report/episodes.csv) and [per-task CSV](report/per_task.csv)
- [Paired success figure](report/task_success.png)
- [English evidence gallery](report/index.html), served locally at port 8904
- [Protocol/model/source/data freeze](manifest.json), source commit `da4db9e`
- [Physical oracle summary](oracle/summary.json), with all 36 execution traces
- `test_runs/`: all 54 model episodes, final/initial PNGs, evaluations, actual API attempts
- `dev_runs/`: three separate API/physics smoke episodes, excluded from Test metrics
- [Request accounting and invariant audit](evidence_validation.json)
- [Post-hoc Gate costs and ask positions](report/diagnostics.json)
- [Complete pytest output](pytest_console.txt) and [JUnit](pytest.xml): 391 passed
- [Actual browser validation](report/browser_validation.json)

The global session reached **57 episodes / 491 authenticated requests**, below the
fixed ceiling of 57 / 900. The 18 schema errors and their retries are included in
actual inference costs; there were no API errors and no missing usage. No whole
episode was rerun or selected after observing a model outcome.

`oracle_geometry_r1/` retains the earlier 30/36 physical layout attempt, before
conservative geometry revision and before any online calls. `generation_geometry_r1/`
and `initial_generation_before_rank_audit/` are pre-freeze diagnostics, not additional
Test cases or model results. They are excluded from every reported success rate.

See [the full scope and limitations](../../docs/nine_task_pilot_v1.md). Old frozen
experiments and the original 128-case Test are unchanged. The dated Team 11 slides
have not been rewritten to claim these new results automatically.
