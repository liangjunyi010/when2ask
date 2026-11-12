# Nine-task Dev: success, speed, estimated cost and false alarms

This independent Dev version adds two fully specified cases per task and one
information-condition contrast, then freshly pairs four methods on all 27 cases:
LLM-NoAsk, LLM-Gate, Jev-Gate and single-call DeepSeek Unified. There are 108
planned real episodes. No previous episodes are pooled or replaced.

The **main table contains only four metrics** (besides method names):

1. Physical success rate: successful / scored episodes, independent of DONE.
2. Speed: mean accumulated API HTTP seconds per episode, including repairs,
   retries and DONE. This is not robot motion speed or total wall time.
3. Estimated USD per episode: actual input/output/cache usage and separately
   priced backends. Unknown cost stays unknown. Public-rate estimates are not
   invoices; caches can change the ranking.
4. Task-level unnecessary ASK rate: any explicit ASK on a core negative counts
   one false positive, regardless of how many questions follow. The denominator
   is 18 balanced fully specified cases (two per task), with censoring reported.
   NoAsk is N/A because it is forbidden to ask. A technical interruption before
   any ASK is not a true negative; an explicit ASK remains FP even if question
   generation fails afterwards.

Clarification burden is retained in raw legacy-compatible logs only, not the
headline report or main presentation table.

## Data and labels fixed before model calls

Nine templates: pack-and-cover, selected containers, find-and-approach, category
sorting, inventory restock, retrieve-and-restore, buffered exchange,
patrol-and-return, and reveal-and-inspect.

Each has two fully disclosed cases, with real required robot execution. Seven
templates also have a contrast with a fixed undisclosed **user preference**.
Navigation's unknown location can be discovered by search, so it is an optional
hint control, not a mandatory-ASK positive. An obscured printed label is a world
fact obtainable by required physical inspection, so its unknown version is a
supplemental hard negative, not a fake preference. Neither supplemental control
enters the balanced 18-case core FPR denominator.

The 27 samples reuse **18 existing Dev physical layout groups**. A contrast
shares its task's second negative layout and GT but changes disclosure. Variants
stay in their original Dev group; no Test group is reused or renamed Dev. These
are new Dev sample variants, not 27 new independent physical layouts. No
confidence interval treats layout variants as independent. No new held-out claim.
Labels, sample/group IDs and private answers never enter model inputs. All cases
must pass the unchanged real PyBullet oracle before online evaluation.

## Locked experiment

- Existing methods keep their selected family profiles: tabletop facts_contract,
  memory v6 planner / v7 Gate for retrieval, exchange and inspection, existing
  navigation/six-task contracts for others. Jev threshold remains 0.5.
- Unified uses one logical call to generate ASK plus complete question, or a
  native action/DONE. Memory tasks retain the same native working-choice and
  completion-assessment schema; only the first selected action executes.
  The existing validators are reused without a second inference request.
- Same initial public facts, simulator, physics, skills, evaluator and budgets.
  Memory Gate compaction retains its existing design; Unified uses the native
  Planner view. This is an architecture comparison, not only Gate substitution.
- DeepSeek non-thinking JSON, temperature0. Existing action/question limits;
  Unified uses their maximum: tabletop500, memory650, other tasks300 tokens.
- Global hard ceiling **108 episodes / 1,600 authenticated attempts**. Per
  episode: 20 rounds, 12 actions, 12 requested slots, 32 attempts. One retry per
  request, permanent/three consecutive API errors block backend. No episode
  reruns, no threshold/prompt adjustment after seeing outcomes.
- Fixed three-process execution, globally shuffled launch order seed42781123.
  All methods interleave; API latency is observed under this scheduling, while
  wall time also includes physics/rendering/contention. No isolated-service
  latency claim. No warmup or selective discard.
- Models, prices, exact samples, prompts, code commit, hashes, budgets and run
  order recorded before paid execution in the independent manifest.

## Commands and evidence

```sh
.venv/bin/python scripts/nine_task_metrics_dev.py prepare
.venv/bin/python scripts/nine_task_metrics_dev.py oracle
.venv/bin/python scripts/nine_task_metrics_dev.py freeze
.venv/bin/python scripts/nine_task_metrics_dev.py run --live
.venv/bin/python scripts/nine_task_metrics_dev.py report
.venv/bin/python scripts/nine_task_metrics_dev.py audit
```

Preparation/oracle/freeze/run refuse to overwrite existing artifacts. Reporting
and audit are offline. Data: `data/nine_task_metrics_dev_v1/samples.json`. Raw
evidence, protocol, standalone English report and figures:
`outputs/nine_task_metrics_dev_v1/`. Existing defaults, frozen configurations,
datasets and experiment outputs stay byte-for-byte unchanged.

## Completed real experiment (2026-11-12)

All **108/108** planned real API + PyBullet episodes completed, with **724/1,600**
authenticated requests. No backend/API errors and no missing usage. There were
**21 schema/affordance errors and 21 repair retries**, all included in the metrics.
Fresh physical oracle **27/27**; offline pytest **464 passed** (428 existing +36 new).
Returned models: `deepseek-flash`, `jev-1.14.0`. No post-outcome policy changes.

| Method | Success rate | Mean API time | Mean estimated USD | Task-level FPR |
|---|---:|---:|---:|---:|
| llm_noask | 21/27 (77.8%) | 4.05s | $0.000718 | N/A (cannot ask) |
| llm_gate | 27/27 (100.0%) | 8.24s | $0.001977 | 0.0% (0/18) |
| jev_gate | 26/27 (96.3%) | 5.73s | $0.001062 | 0.0% (0/18) |
| llm_unified | 26/27 (96.3%) | 4.35s | $0.001394 | 0.0% (0/18) |

Times and costs above are **per-episode averages over 27 cases**, not totals.
The 18-case FPR denominator is identical for each asking method; there were no
censored core negatives. NoAsk is deliberately not credited with a zero Gate FPR.
Public rates were checked on [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/)
and [TypeSafe](https://docs.typesafe.ai/models). Every request occurred outside
DeepSeek peak hours; actual cache hit/miss counts drive each request estimate.
This is not an invoice or an assertion that one backend is universally cheaper.

### Interpretation and failure evidence

- All three asking methods have zero observed false alarms on 18 fully disclosed tasks. This small explicit-information negative set does not distinguish their false-alarm behavior.
- NoAsk has four failures in undisclosed-preference controls and two in fully disclosed inventory tasks. These cannot all be attributed to missing clarification.
- The quota=3 fully disclosed inventory task ends early for NoAsk, Jev-Gate and Unified. Separate LLM-Gate adds the missing block and succeeds.
- An identical recorded DeepSeek action request returned DONE for NoAsk and a block-placement action for LLM-Gate. Cause is unobserved; success differences are not solely evidence of better gating.
- The retrieval skill rejected move(lid,box) before advancing physics; the model subsequently used cover and completed. The failure is retained and final success is based on real final conditions.
- The frozen global random order is not block balanced over time. Cache mix and provider timing are observed confounders; costs are estimates, no universal cheapest/fastest or statistical claim.
- All 21 schema/affordance repair attempts are charged in latency, tokens and cost. No API outages, missing usage or censored core negatives occurred.

The quota=3 example is `md1_04_1`. Three methods placed one extra block and
stopped at two; LLM-Gate placed the remaining block. The identical action-request
comparison is preserved with both responses, timestamps, source paths and hash
in `report/diagnostics.json`. This illustrates why one small run cannot isolate
all success differences to the Gate, even though pairing and public inputs are
controlled. No extra calls were made to select a preferred result.

### Reproducible artifacts and verification

- Source commit before paid calls: `137271ec79199fbc4f26a8efe684685c6509843a`.
- `manifest.json`: locked model/prompt/source/data hashes, launch order and budgets.
- `episodes/`: all108 raw episodes, API request/response JSONL, evaluator JSON,
  actual initial/final PNGs and physics execution logs.
- `report/index.html`: standalone English results, exactly four main metrics,
  all nine per-task tables and expandable 27-case four-method evidence.
- `report/summary.json`, `methods.csv`, `episodes.csv`, `per_template.csv`,
  `attempt_costs.csv`, `paired_differences.csv`: computed from new raw logs only.
- `scripts/nine_task_metrics_diagnostics.py`: read-only failure/cache/request
  analysis and presentation-only chart rendering. Run after `report` to
  reproduce the final annotated page; it does not change metrics or policies.
- Chromium validated at1920×1080 and1366×768: all109 images loaded, no JS errors,
  no horizontal overflow, main table has exactly method + four metric columns.
- `evidence_validation.json`: all108 pairs complete, all20 ASK turns kept physics
  frozen,118 Unified rounds each used one logical model invocation, labels absent
  from requests, final scores match independent conditions. All **4,267**
  pre-existing protected file bytes remain unchanged.

Next work should predeclare more varied fully specified instructions and answer
reuse cases if false-alarm discrimination is needed. Zero observed FPR here is
a result to retain, not a reason to alter the frozen threshold or manufacture
false alarms. A larger study should balance method launch positions within time
blocks and keep repetitions grouped by independent base layout.
