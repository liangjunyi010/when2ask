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

Results will be appended after completing the locked run list.
