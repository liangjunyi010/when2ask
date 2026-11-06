# Robot Command Center — 2026-11-06

Local delivery: dark robot wall, one-click three-method comparison and unified clarification queue. Camera images are real PyBullet renders. Frozen data/prompts, core physics/evaluator and prior results are preserved.

## Validation

- **152/152 offline tests passed**. No paid requests in pytest.
- Real Chromium checks at 1920×1080, 1440×900 and 430×932, without page overflow or unexpected JS errors.
- Two simultaneous manual questions: switching/reload retained drafts; cross-task answers were rejected (expected HTTP 409); duplicate submission was ignored.
- Fresh ASK snapshots stayed identical while a third robot progressed. Three scripted physical tasks succeeded with burdens 2/1/0; a fourth queued task was cancelled.
- A separate all-unknown profile asked for cup/block/lid before its first action, charged burden 3 and completed real physics after an automatic one-time reply; zero model calls.
- Worker JPEG hashes and simulation steps matched displayed frames. Selected inspector, real Jev probability and evaluator success/failure colors were checked.
- One-click comparison: three independent workers, identical initial public payloads and shared prompt hashes, automatic replies, matching JSON/CSV and browser reload.

## Final verified real-model comparison

Group `4f3f8a60d186453e` uses a validated Dev layout with two unknown preferences. Each method has a fresh world and fixed structured simulator. These interactive samples are separate from the frozen benchmark.

| Method | Task success | Burden | ASK | Physical skills | API seconds | DeepSeek in/out | Jev in/out |
|---|---|---:|---:|---:|---:|---:|---:|
| llm_noask | False | 0 | 0 | 3/3 | 2.819 | 6071/89 | — |
| llm_gate | True | 2 | 1 | 3/3 | 8.572 | 15551/201 | — |
| jev_gate | False | 0 | 0 | 3/3 | 4.627 | 6071/89 | 7859/96 |

All 9 final-comparison skills succeeded. NoAsk and Jev guessed yellow block/white lid; the independent evaluator rejected these against green-block/black-lid preferences. LLM-Gate asked before moving the known cup and then succeeded. No outcomes were forced.

Jev probabilities: `[0.48, 0.2, 0.12, 0.06]`, threshold 0.5. Returned models: `deepseek-flash`, `jev-1.14.0`. No prompt/model tuning or formal Test calls occurred. API seconds sum actual request latencies; CSV wall time includes queue/physics. Tokens remain separate by provider. One paired instance cannot establish a ranking.

## Development accounting correction

The first comparison completed 3 real episodes and 22 actual API calls. Per-task costs were complete, but batch creation omitted the shared audit-session binding, so the global request-counter assertion failed. Unmodified raw logs and scores are retained under `development_attempt_1/`. `accounting_correction.json` records the explicit reconstruction of the old session counter and source hashes.

Every paired task now uses the shared ledger. A regression test verifies reservations before network and rejection at the shared ceiling. The full comparison was rerun in a fresh bounded session; all 22 requests had positive reservation IDs and exactly matched its counter.

Total online work: **6 episodes, 44 authenticated calls, 18/18 successful skills**, no API/schema errors or retries. The two comparisons repeat the same layout and are not six independent scenarios. No discovery calls were needed. The delivered session checkpoint is 22/60 attempts and 3/6 live episodes; the reconciled development session is separate. Later user launches can increase these counts.

## Reproduce

```sh
python console.py --live --output-dir outputs/local_console/<fresh-session> --api-limit 60 --live-episode-limit 6
# Real browser/physics, no model calls:
node scripts/command_center_check.mjs
# Explicitly paid, creates exactly one three-method group:
node scripts/command_center_check.mjs --live --session-dir outputs/local_console/<fresh-session>
# Offline report only:
python scripts/report_command_center.py
```

## Evidence and limits

Numbered PNGs show real browser rendering. `browser_validation.json`, `live_validation.json`, `final_visual_validation.json`, `pytest.xml` and `preservation_validation.json` contain checks. `live_comparison.json`/`.csv`, per-method episode JSON and API JSONL contain measured results. `summary.json` includes total usage; `evidence_hashes.json` checks artifact integrity.

Two physical computers/VPN and worker crash-resume remain unverified. Browser reload/reconnect works; a full controller restart starts a new in-memory registry while files and budget persist. Manual intent-setting episodes remain separate from fixed-preference comparisons.
