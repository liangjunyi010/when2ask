# Single-call DeepSeek: independent Dev architecture comparison

The existing LLM-Gate makes one DeepSeek classification call, then a separate
shared question/action planning call. The new `llm_unified` policy directly
returns an ASK with its complete structured question, one physical action, or
DONE in one logical model call. JSON repairs and network retries remain extra
counted requests. It does not secretly call a second question generator.

This is opt-in CLI work. Existing HTML defaults, frozen prompts, datasets,
historical episodes and evaluators remain byte-for-byte unchanged.

## Preregistered design

- Reuse all four `tabletop_contract_dev_v1` Dev cases / four physical groups:
  unknown block with block-first order; known cup with independent order;
  two containers with unknown destination and block-first order; all-known
  two containers with cup-first order. These are developed Dev cases, not a
  fresh held-out sample. No outcome-based case selection or new Test calls.
- Four methods freshly run on each case: LLM-NoAsk, separate LLM-Gate,
  Jev-Gate at unchanged 0.5, and DeepSeek Unified. Exactly 16 planned episodes.
- Existing methods use the unchanged `facts_contract` profile. Unified
  combines the same timing/action/question contracts, changing output routing
  only. Same public state, skills, structured GT simulator and evaluator.
- Unified has a longer combined prompt. This is an architecture comparison;
  the shared-planner/gate-only control claim does not apply to the fourth arm.
- Same DeepSeek model, non-thinking, temperature 0, JSON output, maximum 500
  output tokens for planning/unified; separate Gate maximum 64. API timeout
  40s, one retry, every attempt charged. No warmup, selective rerun or discarded
  failure. Model drift or sustained backend errors stop further affected calls.
- 20 rounds, 12 robot actions, 12 requested slots, 32 API attempts per episode;
  global ceiling 320 authenticated requests and 16 full episodes.
- Randomized case blocks and rotated randomized method order (seed 42781122).
  Every method occupies each within-block position once. Episodes execute
  serially to reduce local concurrency effects. Independent resets/history.
- Before online execution: offline tests, four fresh physical oracle runs,
  source commit, data/prompt/config/pricing hashes and exact run list frozen.

## Metrics and interpretation

Task success comes from the existing physical evaluator, independently of DONE
or budget termination. Report per-case pairing, SR, distinct-slot burden, robot
actions/failures, all API attempts, backend input/output tokens, accumulated API
latency and episode wall time. USD is an estimate, not an invoice, using actual
DeepSeek cache-hit/cache-miss/output usage and Jev input usage with official
prices checked on 2026-11-12. Missing usage is unknown, not zero. API time is not
robot execution time. Unified has no separately measurable Gate latency.

Four groups and one rollout each are descriptive engineering evidence; no
statistical superiority, unseen-task generalization or universal cost ranking.
Correct guesses may succeed. Preserve every failure and timing error.

## Reproduction

```sh
.venv/bin/python scripts/unified_deepseek_dev.py prepare
.venv/bin/python scripts/unified_deepseek_dev.py oracle
.venv/bin/python scripts/unified_deepseek_dev.py freeze
.venv/bin/python scripts/unified_deepseek_dev.py run --live
.venv/bin/python scripts/unified_deepseek_dev.py report
.venv/bin/python scripts/unified_deepseek_dev.py audit
```

The preparation/freeze/run commands refuse to overwrite existing study data.
Reporting and audit are offline. The independently versioned pricing snapshot
is `outputs/unified_deepseek_dev_v1/pricing.json`. Existing credentials are read
from the ignored local `.env`; no keys appear in prompts, datasets or logs.

Actual results and limitations follow; no policy changes were made after seeing them.

## Actual paired results (2026-11-12)

All **16/16** planned episodes completed with **99/320** authenticated attempts,
zero API errors, zero schema errors, zero retries, and no missing usage. Returned
models: `deepseek-flash` and `jev-1.14.0`. Four fresh real PyBullet oracle episodes
passed (**4/4**). Full offline pytest: **428 passed** (410 original + 18 new).

| Method | Physical success | Mean burden | API attempts | Total API latency | Estimated USD total |
|---|---:|---:|---:|---:|---:|
| llm_noask | 3/4 | 0.00 | 14 | 12.38s | $0.000664 |
| llm_gate | 4/4 | 1.00 | 34 | 28.84s | $0.002374 |
| jev_gate | 4/4 | 1.00 | 34 | 18.53s | $0.002479 |
| llm_unified | 4/4 | 1.00 | 17 | 16.24s | $0.003258 |

All latency and USD totals above cover **four episodes per method**.
API timing excludes physics and rendering; the report also retains complete
episode wall time. All actual requests occurred outside the published DeepSeek
peak windows (2026-11-12 10:07:54–10:09:51 UTC), so off-peak rates apply to this
estimate. Prices checked against [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/)
and [TypeSafe](https://docs.typesafe.ai/models). These are usage-based estimates,
not invoices; all cache hits/misses and per-attempt calculations are preserved.

### What this small pilot actually shows

- Unified used 17 calls versus 34 for each separated gate architecture. Its
  accumulated API time was 43.7% lower than LLM-Gate and 12.4% lower than
  Jev-Gate in this run. NoAsk remained faster, but failed one preference choice.
- Unified was **not cheapest**: its estimated USD was 37.3% above LLM-Gate and
  31.4% above Jev-Gate. It used a longer combined prompt and 19,164 uncached
  DeepSeek input tokens. LLM-Gate used 12,517 uncached input tokens despite
  having more total tokens; observed cache-hit fractions were 59.8% (Unified)
  and 78.8% (LLM-Gate). Cache conditions were observed, not experimentally fixed.
- Jev-Gate was faster than LLM-Gate, but slightly more expensive under this
  actual cache mix. Gate-stage estimates were $0.001622 for Jev and $0.001102
  for DeepSeek. Do not claim Jev is always cheaper from provider list prices.
- In the known-cup independent-order case, Unified and LLM-Gate asked for the
  block/lid **before placing the supported cup**. Jev placed the cup first.
  All completed successfully with burden two. Across the four explicit public
  timing references, LLM-Gate / Jev / Unified matched 3/4, 4/4, 3/4; this is a
  controlled-case diagnostic, not a universal optimal-timing label.
- NoAsk guessed the wrong destinations in the block-first two-container case.
  Physical skills succeeded, but correct-container and corresponding DAG
  checks failed. Other guesses happened to be correct and counted as successes.
- All four methods performed ten physical actions across their four episodes.
  No repeated relocation loops or skill failures occurred in this pilot.
- A separately labeled, offline all-input-uncached repricing is included in
  `report/interpretation.json` to illustrate cache sensitivity. It is not a
  new run, observed charge, or replacement for the primary table.

### Evidence and delivery

- Source commit before paid calls: `834e22afe5f3ec239e70d1d339dc5e4ed3f53e78`.
- `outputs/unified_deepseek_dev_v1/manifest.json`: exact run order, model/config,
  source/data/prompt/pricing hashes, budgets and retry policy.
- `outputs/unified_deepseek_dev_v1/episodes/`: 16 original request/response JSONL,
  episode JSON, evaluations, and real initial/final PNGs.
- `outputs/unified_deepseek_dev_v1/report/index.html`: English read-only result
  gallery with all four methods, physical screenshots, questions and actions.
- `report/summary.json`, `methods.csv`, `episodes.csv`, `attempt_costs.csv`,
  `stages.csv`, `paired_differences.csv`: generated from new raw files only.
- `.venv/bin/python scripts/unified_dev_interpretation.py`: reproducible offline
  timing/cache interpretation; no inference or changes to locked policies.
- `evidence_validation.json`: all 16 paired, all nine ASK turns frozen,
  exactly one logical Unified call per round, budgets/privacy/score checks,
  and all **4,142** pre-existing protected file bytes unchanged.
- `report/browser_validation.json`: Chromium rendering at 1920x1080 and
  1366x768, 17 images loaded, expandable traces work, no JS errors or overflow.

The current task is complete. This version remains an independent Dev CLI;
it has not replaced the default HTML policy or any frozen Benchmark configuration.
Next rigorous comparison should freeze all four architectures together, control
or explicitly stratify cache conditions, use more independent layout groups,
and report task success separately from clarification timing.
