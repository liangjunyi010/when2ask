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
