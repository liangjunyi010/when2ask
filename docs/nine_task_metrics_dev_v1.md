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
