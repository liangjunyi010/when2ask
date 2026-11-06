# Independent Dev version: findings and limits

This version adds files only. Frozen Test configuration, all prior data/reports, existing agents/physics/evaluator and the user-modified PPT are unchanged. Integrity audit checked 1056 existing tracked files. Inference sources were sealed at commit `6d873d1298eca7a1c0cf1e81eb97bf90233b820c` before model calls.

## Observed outcome

Task completion improved from 2/4 to 4/4 for both compact variants on these four deliberately scoped Dev cases. The joint variant reduced public-information blocked CONTINUE decisions from 5 to 0, but both new variants added one premature ASK. Neither satisfies the predeclared no-new-early-ASK rule. Neither is adopted as the frozen/default configuration.

The old/new task-success difference is not exclusively a Jev gate effect: compact_state also changes the public representation read by the unchanged DeepSeek planner. The all-known two-container original run repeatedly removed/replaced a correctly placed block, exhausting its action budget. The compact-state run also reached its action budget, but its final geometric/contact/DAG state passed; it remains scored successful despite no DONE. The joint run finished that task with six physical actions. All skill calls succeeded; the extra actions were planning/repair choices.

## Target regression: identical initial public state

| Profile | Initial Jev p(ASK) | Actual decision | Interpretation |
|---|---:|---|---|
| v3_original | 0.40 | CONTINUE | Correctly continues with the known cup |
| compact_state | 0.75 | ASK | Premature: the specified blue cup is still executable |
| compact_question | 0.54 | ASK | Premature: the specified blue cup is still executable |

The new variants obtain the missing block/lid answers early and then finish correctly. They do not yet produce the desired CONTINUE → pack cup → ASK sequence. After this early answer, their later states include more public information; their round-1 probabilities must not be compared to the original round-1 as if the states were identical.

The one-unknown late-lid case is also informative: the original and compact-state runs guessed the correct lid and passed the physical task without asking. They still missed the information gap at the selection stage. The joint version asked after both known objects had been packed. Thus physical task success and clarification timing are reported separately; lucky guesses are not marked as task failures.

Actual duplicate action-request groups with differing model outputs: 1. Details are in audit.json. The shared planner prompts and temperature were unchanged; identical returned model aliases and temperature=0 do not establish identical repeated outputs. Consequently completion differences, particularly repair loops, must not all be attributed to gate wording.

## Evidence and reproducibility

Oracle 4/4; 12 real model episodes, 140/140 authenticated requests, 54/54 physical skills succeeded. No HTTP/schema errors or retries. 181 offline tests passed; synthetic unit transports are kept outside the experiment reports. No Test API calls ran.

- [Generated metrics and pairing](report/README.md)
- [Read-only visual report](report/index.html)
- [Raw episode table](report/episodes.csv)
- [Every gate decision](report/gate_turns.csv)
- [Matched public states](report/matched_public_states.json)
- [Integrity and request audit](audit.json)
- Real GIFs remain local under episodes/regression_console_m2__{v3_original,compact_question}/demo.gif; PNGs and JSON are committed.

```sh
python scripts/run_summary_dev.py prepare
python scripts/run_summary_dev.py seal
python scripts/run_summary_dev.py run --live
python scripts/run_summary_dev.py report
python scripts/audit_summary_dev.py
```

The sealed v1 is complete and its budget is exhausted. Re-running the command skips saved episodes and does not create new requests. Any new prompt/summary replication needs an explicitly separate experiment version. The next useful Dev question is how to preserve known-subgoal-first behavior while retaining the reduced late misses, using public facts without injecting a computed ready-action or ASK oracle.
