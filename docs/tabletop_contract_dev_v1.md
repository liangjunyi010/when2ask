# Independent tabletop contract Dev repair

This opt-in study investigates missed clarification and repeated undo/replacement
in the two original tabletop tasks. Original agents, physics, evaluators, frozen
datasets/configuration and the 54 nine-task pilot episodes remain unchanged.

## What failed and what is known

The historical pack failure required **block before cup**, with known cup/lid and
unknown block. Both gates continued; Jev returned 0.04. The shared planner guessed
the wrong block, physically placed it, placed the cup and covered. All skills
succeeded, but the independent evaluator correctly rejected the wrong selection.
The original presentation demo allowed its known cup first, then asked for the
remaining block/lid. The new precedence/disclosure combination is a harder state,
not a rerun of the same successful demo.

In the selected-container failure, both gates asked for cup_destination, received
the same correct answer and physically placed the correct block in the OTHER
container. The next public payload contains the answer, the successful action and
the measured block containment. The planner nevertheless removes the block, then
replaces it and repeats until the action budget. Thus history was not dropped and
the motor controller did not fail. The observable error is failure to preserve a
correct partial goal. Incorrect role/destination binding is a hypothesis; the model's
internal reasoning was not logged and cannot be asserted as fact.

The existing prompt already mentions precedence and the other-container relation.
Simply adding the missing sentence cannot explain the repair. The controlled Dev
study separates representation (raw versus concise public facts) and prompting
(original versus clarified contract) to test sensitivity.

Read-only source hashes and exact evidence are in
`outputs/tabletop_contract_dev_v1/forensics.json`. Examining these historical Test
failures means they cannot be reused as fresh held-out evidence for this repair.

## Repair and controlled regression

The new public-only serializer takes `PublicState` alone. It extracts the public
instruction's explicit precedence sentence, disclosed choices, candidates, actual
containment and prior actions. It makes the two absolute destinations explicit
from a disclosed cup_destination; an own guess stays marked unconfirmed. It does
not read the sample, private DAG/registry, evaluator, correct answer or an oracle.
No blocked-role label, completion verdict, prescribed action or Gate label enters
the payload. Unsupported/ambiguous instruction grammar is rejected explicitly.

The contract addendum explains that legal motor affordances do not authorize
unknown preferences, later known subgoals may be blocked by order, incomplete work
is not an incorrect placement, and satisfied absolute final relations should be
preserved. The planner still emits the exact same action schema. Its output is
validated for schema and executed verbatim; no wrapper replaces a wrong action or
forces a Gate answer. Jev threshold stays 0.5.

Four Dev cases reuse four existing **Dev** physical layout groups (new variants,
not new independent Test layouts):

| Dev case | Disclosure/order | Expected public support pattern |
|---|---|---|
| pack_block_first | Cup/lid known, block unknown; block first | Ask before choosing block |
| pack_continue_known_cup | Cup known; independent order | Pack cup first, then clarify |
| containers_block_first | Objects known, destination unknown; block first | Ask destination, place block, preserve it, place cup |
| containers_all_known | All three choices known; cup first | Continue without clarification |

All four must pass actual PyBullet oracle before online experiments. Two additional
public snapshots are captured by real execution in the third case: after the
correct block placement, and after completion. References are stored separately
and never supplied to a model. Fixed-state references are controlled-case
diagnostics, not a claimed optimal clarification policy.

Preregistered comparisons:

- Six public Dev states × four representation/prompt profiles × two Gate backends:
  48 Gate probes.
- Two of those physical states × four profiles: eight DeepSeek next-action probes.
- Four Dev cases × three methods × two profiles (original and combined repair):
  24 fresh full episodes, each with independent reset and history.
- Both factors are combined in the designated repair before seeing any diagnostic
  result. Report all factors, not only a winning cell. No threshold tuning.
- One persistent session caps all authenticated requests, including retries, at
  **450**, and full episodes at **24**. Per episode: 20 rounds, 12 actions, 12 slot
  requests, 32 requests. One API retry; real usage and latency for every attempt.
- Frozen randomized run order, model configuration, prompt/data/state/source hashes;
  no Test API runs or whole-episode replacement. Any later Dev revision needs a
  different version and retains all failed attempts.

## Reproduce

```bash
.venv/bin/python scripts/tabletop_contract_dev.py generate
.venv/bin/python scripts/tabletop_contract_dev.py forensics
.venv/bin/python scripts/tabletop_contract_dev.py oracle
.venv/bin/python -m pytest tests/test_tabletop_contract_dev.py -q
.venv/bin/python scripts/tabletop_contract_dev.py freeze
.venv/bin/python scripts/tabletop_contract_dev.py probes --live
.venv/bin/python scripts/tabletop_contract_dev.py run --live
.venv/bin/python scripts/tabletop_contract_dev.py report
```

Generation, freeze, probes and episodes refuse to overwrite existing evidence.
The original default factories are untouched. To opt into this version from new
Dev code, use `when2ask.tabletop_dev_agents.components` with `facts_contract`;
`raw_legacy` is the exact old prompt/raw-state control. Existing HTML defaults do
not silently change.

## Difficult tasks and a useful benchmark

Reasonable model failures should remain in a benchmark. Both Gates missing a
predecessor-dependent choice is a legitimate clarification-timing challenge. A
shared planner undoing correct progress is a legitimate planning failure, provided
the interface, public facts and evaluator are sound. Neither failure justifies
editing old scores or removing an unsuccessful sample after evaluation.

Potential future challenge strata can reuse existing verified skills:

1. Longer public precedence chains with known work blocked behind an unknown choice.
2. A reusable destination/mapping answer needed across several later placements.
3. A wrong early guess requiring physical recovery and restoration of order.
4. Occluded state requiring memory plus an explicit sensing action before a report.

These are **design suggestions, not implemented or evaluated new tasks in this
study**. Difficulty should come from task dependencies, information and memory,
not missing API fields, contradictory instructions, unreachable physics or a
secretly impossible goal. Retain easy/intermediate/challenge tiers. A challenge
tier where all methods fail may be informative, but an entire suite with zero
success has a floor effect and cannot distinguish Gate quality through success
alone. Report task success, ask timing diagnostics, burden, planning/physical
failure classes and backend costs separately.

## Actual results

All four Dev variants passed real physical oracle. The fixed-state diagnostic
completed 56 real calls, followed by all 24 paired physical episodes. The session
used **258/450 authenticated attempts**, with zero API errors, schema errors,
retries or missing usage. Actual returned models were `deepseek-flash` and
`jev-1.14.0`. The complete offline suite passed **410 tests** (19 new).

### Representation versus prompt

| Public view / prompt | LLM Gate reference matches | Jev Gate reference matches | Planner next-action reference |
|---|---:|---:|---:|
| Raw / original | 3/6 | 4/6 | 1/2 |
| Public facts / original | 5/6 | 5/6 | 1/2 |
| Raw / clarified contract | 3/6 | 4/6 | 2/2 |
| Public facts / clarified contract | 6/6 | 6/6 | 2/2 |

The blocked unknown-block state gives a concrete distinction: original Jev p=0.05,
raw+contract p=0.18 (both CONTINUE); facts+original p=0.69 and combined p=0.72 (ASK).
Both LLM Gate variants with facts asked in this fixed-state check. The evidence
supports sensitivity to public representation, not a claim that the old prompt
omitted the order rule or that the threshold needed lowering.

For the post-block container state, original and facts-only Planner calls both
selected removal to the table. Both clarified-contract calls selected the remaining
cup placement. The added progress-preservation contract addressed this diagnostic
without choosing an action in Python.

### Full physical Dev regressions

| Profile | Method | Task success | Slots requested | First-ASK reference matches | Total API latency |
|---|---|---:|---:|---:|---:|
| Original | NoAsk | 3/4 | 0 | N/A | 12.13 s |
| Original | LLM-Gate | 3/4 | 6 | 1/4 | 44.52 s |
| Original | Jev-Gate | 3/4 | 3 | 2/4 | 29.12 s |
| Combined Dev repair | NoAsk | 3/4 | 0 | N/A | 12.10 s |
| Combined Dev repair | LLM-Gate | 4/4 | 4 | 3/4 | 28.00 s |
| Combined Dev repair | Jev-Gate | 4/4 | 4 | 4/4 | 19.42 s |

Both original Gates reproduced the block-placement/removal cycle: 12 successful
physical moves, then budget termination and final task failure. Both repaired Gate
episodes completed the same container Dev case using exactly two placements. All
Gate profiles share the same Planner within a profile; the improvement is not a
Jev-only planner advantage.

The original packing Dev case happened to guess the correct unknown block and
therefore passed the final task evaluator despite missing the required clarification.
This is an important reason to keep task success and timing diagnostics separate.
NoAsk still guesses the wrong destination in one container case and scores 3/4 under
both profiles; no failure was imposed by method name.

### Residual model behavior

The repaired LLM-Gate asked too early in the independent-order known-cup full run.
Its fixed-state call returned CONTINUE, while the full run returned ASK on the
**same request bytes**, model and reported system fingerprint. Exact request hash,
responses and source references are in `observed_response_variation.json`. These
two observed outputs were inconsistent; their internal/backend cause is unknown.
There was no rerun to select a preferred response. Hence task success 4/4 does not
mean every clarification decision is correct or perfectly repeatable.

The nine-task runner also deliberately used different established task-family
factories: the two original tabletop tasks used `study_agents` v3.1, while the
three recently repaired manipulation tasks used memory Dev v6 / Gate Dev v7.
Those earlier buffer/retrieval fixes were not automatically active in the two
original task families. This new module is opt-in and leaves both factories intact.

## Verification and artifacts

- `outputs/tabletop_contract_dev_v1/report/`: generated JSON/CSV, English HTML,
  figure and detailed per-case outcomes. The report never replaces old benchmark
  results. Tokens stay separated by backend and include probes/repairs where stated.
- `evidence_validation.json`: all eight case/profile pairs have all three methods;
  NoAsk never calls Gate/Question; Gate precedes Planner; all 11 ASK turns freeze
  physics; burden and physical conditions match raw records. No private reference,
  sample ID or evaluator label entered an API payload.
- `protected_before.json`: all 3,840 previously tracked files matched starting
  bytes before README documentation was updated, including frozen source/config,
  old experiment records and the user's edited PPT. Only a new README entry is
  intentionally added; the PPT remains unstaged.
- All old and new tests passed: 410 in 98.12 seconds. This includes explicit tests
  that a low Jev score still yields CONTINUE and an incorrect but schema-valid
  Planner action is executed verbatim, so no rule wrapper can fake a model repair.

Open the read-only results without paid calls:

```bash
.venv/bin/python -m http.server 8905 --bind 127.0.0.1 --directory outputs/tabletop_contract_dev_v1
# http://127.0.0.1:8905/report/
```

The repair is available through the independent CLI/factory; default live-console
behavior is intentionally not switched. A later optional console profile or a
fresh held-out evaluation must identify this Dev version explicitly.
