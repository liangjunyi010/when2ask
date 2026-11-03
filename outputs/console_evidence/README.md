# Local console validation — 2026-11-03

Interactive engineering checks, not a Dev/Test benchmark or a new ranking of methods. Frozen datasets, prompts, controllers and historical results were preserved. No held-out Test API episodes ran.

## Three real-model executions

One fixed interactive pack-and-cover instance per method; automatic structured user replies. The initial instruction specifies the blue cup. The fixed simulator prefers the green block and black lid. All methods use independent resets and the unchanged shared planner/prompts. The API latency below is the sum of actual calls within that one episode, excluding physical execution.

| Method | Task success | Burden | Physical skills | DeepSeek in/out | Jev in/out | API seconds | Attempts |
|---|---|---:|---:|---:|---:|---:|---:|
| llm_noask | False | 0 | 3/3 | 6071/89 | — | 3.279 | 4 |
| llm_gate | True | 2 | 3/3 | 15551/201 | — | 7.445 | 10 |
| jev_gate | False | 0 | 3/3 | 6071/89 | 7859/96 | 4.871 | 8 |

LLM-Gate asked early, before moving the known cup, then completed successfully. Jev returned CONTINUE at 0.27, 0.37, 0.13 and 0.05 (threshold 0.5), so it never clarified. NoAsk and Jev physically packed the guessed yellow block and white lid; the independent evaluator correctly rejected them. These current observations do not replace the earlier Phase 3 calibration results.

Both providers authenticated successfully. DeepSeek returned `deepseek-flash` (discovery catalogue name `DeepSeek-V4.1-Flash`); Jev configured `jev-latest`, returned `jev-1.14.0`. Aliases may evolve; old frozen model records were not rewritten. No API/schema errors or retries occurred.

The dedicated console session used **24/60 authenticated attempts** (2 discovery + 22 inference) and **3/6 live episodes** at this validation checkpoint. These are persisted session caps, not a recommendation to start another benchmark.

## Offline policies, real physics and browser checks

- Three concurrent independent Bullet processes: [11430, 11432, 11434].
- Manual ASK: fresh worker snapshots were exactly equal at step 3461; other tasks continued.
- Browser reload retained the question; duplicate answer did not execute a second action.
- Human chose yellow block and white lid. Real physics succeeded under the explicitly declared interactive intent.
- Automatic two-container task succeeded. Scripted NoAsk failed its actual preference score.
- Fourth task queued at capacity three and was cancelled without starting physics.
- Each displayed JPEG matched the worker SHA and simulation-step metadata. No synthetic robot animation.
- Browser logic checks: True; final 1920×1080 layout/focus check: True; no JavaScript errors.
- Offline pytest: **126/126 passed**, including the original 102 tests and 24 console checks. No paid API in pytest.

Detailed evidence: `browser_validation.json`, `browser_visual_validation.json`, `pytest.xml`, `live_validation.json`, `live_results.csv`, per-method episode JSON and raw sanitized API JSONL. The ignored session retains earlier failed development attempts as well; only the identified final validation runs appear here.

## Reproduce

```sh
python console.py --live --output-dir outputs/local_console/<new-session> --api-limit 60 --live-episode-limit 6
# Separate terminal: real browser + real physics, no model API:
node scripts/console_browser_check.mjs
# Explicitly paid, creates three new live episodes; do not rerun merely to build a report:
node scripts/console_live_check.mjs --live --session-dir outputs/local_console/<new-session>
# Offline only, after the evidence above exists:
python scripts/report_console.py --session-dir outputs/local_console/<new-session>
```

## Limits

The single-machine controller/worker HTTP boundary is tested. Two physical computers and VPN transport are not yet verified. Browser reconnect works. Controller/worker crash recovery from a partially completed grasp is not implemented; saved logs and the session budget survive, while in-memory task cards do not survive a controller restart. Manual preference changes define interactive intent and are not pooled with fixed-hidden-preference benchmark scores.
