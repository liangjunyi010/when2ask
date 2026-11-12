# Nine-task benchmark coverage pilot

This independent extension tests every implemented task type. It does not modify
earlier data, frozen prompts/configuration, default agents, experiment records, or
the original 128-case held-out Test set.

## Scope locked before online evaluation

| Task | Actual physical goal | Information relevant to asking |
|---|---|---|
| Pack and cover | Select cup/block, pack a hollow box, cover | Object/lid choices; known subgoals may proceed |
| Selected containers | Put selected cup/block into their two assigned bins | Choices plus reusable cup-destination preference |
| Find and approach | Drive Husky, detect a knife locally, stop within 1.2 m | Unknown location is observable; exploration is permitted |
| Category sorting | Sort six physical objects into three category bins | One bin mapping also determines the remaining category |
| Inventory restock | Count stock and fill only the deficit | Block quota; existing stock and surplus must stay untouched |
| Retrieve and restore | Park lid, retrieve selected item, reclose | Selection need not block opening; retain occluded position memory |
| Buffer exchange | Swap occupied single-capacity slots via a temporary pad | User-selected pad is required before parking |
| Patrol and return | Inspect known/selected station, physically return home | Known inspection may precede asking; reuse station reply |
| Reveal and inspect | Move screen, physically inspect label, report code | Observable world fact; user answer cannot replace inspection |

Each task has **two Dev cases and two new Test cases**, each with a different base
layout group: 36 cases/groups, including 18 Test cases. Every Test case runs all
three methods independently: 54 planned model episodes. Three additional Dev smoke
episodes check the API/runner path. A persistent file-locked budget caps the whole
new study at 57 registered episodes and 900 authenticated attempts, including
retries. Per episode: 20 rounds, 12 robot actions, 12 slot requests, 32 attempts.

This is a small **coverage pilot**, not sufficient to rank methods robustly within
each task. No significance claim or large-benchmark claim is warranted at n=2 per
task. In particular, these 18 new Test cases do not imply completion of the old
128-case experiment.

## Separation and fairness

- Group identity uses actual physical geometry, ignoring answer, label code,
  candidate order, aliases and colour. Category-matched near-duplicate layouts
  below 35 mm separation are rejected, including historical tabletop layouts.
- Mobile layouts vary station/furniture positions, while retaining the existing
  three-room corridor/wall topology. Find/approach and patrol use distinct layouts.
  No claim of held-out floor-plan/topology generalization is made.
- The two original tabletop tasks cover 0/1/2/3 unknown preferences across their
  four cases. Other tasks retain their established one-slot contract, covering
  known and unknown conditions. Not every task intrinsically has three slots.
- Truth and candidate order are counterbalanced for binary single-slot tasks.
  Study aliases and scene object ordering are randomized independently of truth.
  Canonical IDs remain for existing six-task skills, so ID invariance is limited.
- The three methods share the exact same planner, state serializer, question/action
  prompts, budgets, physical controller and evaluator **within each task family**.
  Different families retain their already implemented task contracts. NoAsk skips
  Gate; Gate runs before Planner; DONE belongs to Planner only.
- Threshold remains 0.5. The existing exploratory navigation contract allows
  searching without asking. Neither Gate is forced to ask on an unknown fact.
- Navigation's existing v1 contract mentions a nominal 3-second reply cost; the
  structured simulator replies immediately and never advances physics. Reported
  API latency is actual inference latency, not hypothetical human waiting time.
- Task success is independent of DONE and comes from existing full geometry,
  contact, stability, sensing and event-order evaluators. Patrol uses the same
  numerical v1 criteria against the current map's station coordinates.

## Execution and evidence

```bash
.venv/bin/python scripts/nine_task_pilot.py generate
.venv/bin/python scripts/nine_task_pilot.py oracle
.venv/bin/python -m pytest tests/test_nine_task_pilot.py -q
.venv/bin/python scripts/nine_task_pilot.py freeze
.venv/bin/python scripts/nine_task_pilot.py smoke --live
.venv/bin/python scripts/nine_task_pilot.py run --live
.venv/bin/python scripts/nine_task_pilot.py report
```

Generation/freeze/oracle/episode directories refuse overwrite. Model tests require
`--live`. The freeze pins every source/data/prompt hash, model configuration, job
order and budget. Each paired episode resets physics and history. All attempts,
including failures/repairs, are logged with backend-specific tokens and measured
latency. Unknown usage stays null. Backend authentication/network failures trip
the existing circuit breaker. There are no whole-episode retries or Test-dependent
prompt/threshold adjustments.

Data: `data/nine_task_pilot_v1/`. New physical/model evidence and generated report:
`outputs/nine_task_v1/`. The report's CSV, JSON, per-task plot and read-only HTML
are computed from raw episode files, including failures. API smoke episodes are
kept separate from scored Test results.

The first geometry attempt passed 30/36. Six failures (IK convergence and a
navigation stopping distance) are preserved in `oracle_geometry_r1/`. Before any
online calls, source positions were kept farther from the Panda base, navigation
inspection poses were moved closer to fixtures, and find/patrol station layouts
were separated. The revised complete physical oracle passed 36/36 without relaxing
any geometric/contact/sensing threshold or resetting object final poses.

## Completed real evaluation

All 54 paired Test episodes and all three separate Dev smoke episodes completed.
Total authenticated requests: **491/900**, including **464 Test + 27 smoke**.
Both APIs returned the expected versions: `deepseek-flash`, `jev-1.14.0`.
All usage fields were present. There were **18 schema-error attempts**, repaired
within the bounded retry policy and included in tokens/latency; **zero API errors**.
No episode was replaced or rerun. All executed skills returned success, but nine
episodes failed the independent final-task evaluation. Skill success therefore
does not imply correct object choice, correct final contents, or task completion.

| Method | Success | Total slots requested | Mean slots | Cumulative API latency |
|---|---:|---:|---:|---:|
| LLM-NoAsk | 13/18 | 0 | 0.000 | 78.39 s |
| LLM-Gate | 16/18 | 10 | 0.556 | 166.35 s |
| Jev-Gate, threshold 0.5 | 16/18 | 7 | 0.389 | 112.26 s |

Backend tokens are reported separately in the generated CSV/JSON. For methods
which never call Jev, null Jev token totals mean **not used**, not missing usage;
their unknown-usage attempt counts are zero. No dollar-cost claim is made.

Post-hoc Gate-only diagnostics: DeepSeek Gate had 93 attempts / 74.01 s cumulative,
795.80 ms per attempt; Jev Gate had 91 attempts / 27.89 s cumulative, 306.53 ms per
attempt. These are different realized state trajectories, not a controlled
same-payload latency benchmark. Full-agent times include the shared planner,
questions, DONE and repairs. They are not robot-motion duration or mean episode
latency. The raw data can be recomputed with
`.venv/bin/python scripts/nine_task_diagnostics.py`.

### What broader coverage exposed

- **Timing failure, packing:** on `n9_test_00_0`, the instruction requires the block
  before the known cup, but the block preference is unknown. Both gates continued,
  the planner guessed the wrong block, then finished. This is not physical control
  failure and is not evidence that every gate decision is correct.
- **Planner cycle, selected containers:** on `n9_test_01_0`, both gates asked for the
  missing destination and obtained the same correct reply. The shared planner
  alternated placing/removing the selected block until the 12-action limit.
  The same cycle occurred with both Gate backends.
- **Useful work before asking:** both gates sorted the two known cups before
  clarifying the category mapping, replenished the cup deficit before requesting
  block quota, and opened storage before requesting the retrieval selection.
- **Observable facts:** both gates completed reveal/inspect without asking for the
  hidden printed code. All navigation methods completed the two search tasks
  without asking. These cases do not demonstrate a navigation clarification benefit.
- **Guessing can succeed:** NoAsk succeeded in both buffer cases, including the
  undisclosed pad case. Jev also completed an unknown patrol choice and a two-unknown
  container task without asking. Lower observed burden therefore includes successful
  guesses; it cannot alone prove better clarification timing.
- **NoAsk failures have different causes:** category sorting used a wrong category
  mapping; retrieval selected the wrong item; restocking overfilled the cup shelf
  despite physically successful moves. They should not all be labelled the same
  preference-selection error.

These are descriptive, post-hoc explanations from the full traces, not a newly
defined timing score, a threshold selection, or additional model experiments.
Any repairs should be developed on a separately versioned Dev set, followed by a
new frozen evaluation. This Test batch stays unchanged.

## Verification and delivery

- Existing baseline: 364 passed. Added 27 offline tests; complete suite:
  **391 passed** in 100.46 seconds.
- Evidence audit verified all 18 samples have all three methods, NoAsk never calls
  Gate/Question, Gate attempts precede planning, all 14 ASK turns freeze simulation,
  burden matches distinct requested slots, and each success matches all physical
  conditions. Unknown API usage: zero attempts.
- Before README documentation was updated, all **3,285** previously tracked files
  matched their starting SHA-256 bytes, including frozen data, configs, defaults,
  historical results and the user's pre-existing edited PPT. The PPT is unstaged.
- Real Chromium rendering: nine task rows, 18 case sections, all 54 actual final
  scene images loaded; no JavaScript errors, no failed requests and no horizontal
  overflow at 1366px. Screenshots and validation JSON are in the new report folder.

To open the evidence gallery without any API calls:

```bash
.venv/bin/python -m http.server 8904 --bind 127.0.0.1 --directory outputs/nine_task_v1
# http://127.0.0.1:8904/report/
```
