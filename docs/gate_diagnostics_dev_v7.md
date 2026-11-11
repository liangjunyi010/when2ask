# Gate Dev v7 — state / prompt / threshold diagnosis (2026-11-11)

## Finding

The buffer miss is not a reversed probability, an API parsing failure or evidence that we should simply lower the threshold. The exact raw public input and Gate prompt for the historical v5/v6 first buffer decisions are identical except for the attached summary. However, exact-request replays also vary around the boundary, so the historical0.53→0.43 change alone is insufficient to attribute causality to summary format.

A preregistered new2×2 diagnostic tests full versus compact Gate state and original versus explicit Gate contract. Strengthening wording alone does not fix the initial buffer miss. Compacting the Gate view while preserving the original contract,0.5 threshold and v6 shared Planner does fix it in these controls and in one new end-to-end episode. The selected optional version is **Gate Dev v7**, not a replacement for any default or frozen study.

## Controlled design

Before calls, `matrix/plan.json` locks eight states from actual prior Dev episode public inputs, randomized/interleaved jobs, profile hashes, interpretation labels, selection rule and budgets. Labels are never included in API requests. States cover:

- Buffer initial unknown preference: ASK before a pad-dependent first move.
- Same scene after a disclosed answer: CONTINUE, no repeated question.
- Buffer physically finished under a guess: CONTINUE to Planner DONE, no endless confirmation.
- Retrieval initially covered and choice unknown: CONTINUE with the supported opening action.
- Retrieval opened, still unknown item choice: ASK.
- Retrieval completed with occluded contents remembered: CONTINUE to DONE.
- Occlusion initially hiding a world fact: CONTINUE with required physical inspection work.
- Inspection and report complete: CONTINUE to DONE.

The compact projection has no task-specific branches, blocked-role labels, completion verdict, private truth, score or prescribed next action. It preserves the original instruction, task/DAG/candidates, public dialogue, legal affordances, measured contents, observed/remembered positions, confirmed versus own choices and actual sensor/inspection/report evidence. It removes motor geometry, joint/velocity detail and redundant prose that are unnecessary for the binary gate. The unchanged Planner still receives full v6 input. Both DeepSeek-Gate and Jev-Gate use the same projection; NoAsk still skips Gate and uses the exact same v6 Planner.

The explicit-contract factor distinguishes physically executable commands from actions justified by disclosed preferences, while retaining progress-before-asking, useful sensing, answer reuse and completion exceptions. It is a bundled wording change, not a one-sentence causal isolation. It was **not selected**, because compact state alone met the prelocked rule with fewer changes.

## Actual Gate-state outcomes at0.5

| Public state | Expected | Full/original | Full/explicit | Compact/original | Compact/explicit |
|---|---|---:|---:|---:|---:|
| Buffer initial | ASK | 0.39 | 0.40 | 0.57 | 0.54 |
| Buffer disclosed | CONTINUE | 0.04 | 0.04 | 0.04 | 0.04 |
| Buffer finished guess | CONTINUE | 0.16 | 0.05 | 0.17 | 0.07 |
| Retrieval initial | CONTINUE | 0.13 | 0.07 | 0.13 | 0.07 |
| Retrieval open | ASK | 0.76 | 0.80 | 0.84 | 0.83 |
| Retrieval finished | CONTINUE | 0.11 | 0.09 | 0.11 | 0.10 |
| Inspection initial | CONTINUE | 0.04 | 0.03 | 0.04 | 0.03 |
| Inspection finished | CONTINUE | 0.03 | 0.03 | 0.04 | 0.03 |

Original/full and explicit/full each match7/8 contract labels; compact/original and compact/explicit each match8/8. Neither compact variant produces an extra ASK in the six CONTINUE controls. These are eight correlated diagnostic states from three old physical groups, **not task success rates or eight independent scenes**.

Six exact original-body replays provide a repeatability check. Historical v5 was0.53; this session replays are0.48,0.41,0.47. Historical v6 was0.43; replays are0.45,0.45,0.46. Request-body equality is verified. The same returned model alias/version does not expose every server-side inference detail, so this study establishes observed score variation rather than a specific internal mechanism.

Four separately logged DeepSeek gate checks match their contract labels. They are limited cross-backend controls, not a full DeepSeek factorial or a new three-method benchmark.

## Threshold analysis

The decoder is correct: `ASK if p >= threshold`, with no absolute-distance transform. Runtime threshold stays0.5; neither `.env` nor frozen configuration is changed. The CSV evaluates0.3/0.4/0.5/0.6/0.7 on the **already observed gate scores only**. This is sensitivity analysis, not fresh end-to-end performance at those thresholds. A threshold that happens to classify these few states correctly is not adopted.

[Official TypeSafe Noul documentation](https://docs.typesafe.ai/primitives/noul) describes Noul as the probability of a yes answer, treats near-boundary values as ambiguous and cautions against closely fitting thresholds to a few cases. The request/response shape and positive score direction were checked against that source; no SDK/API adapter change was needed.

## Six fresh full API/PyBullet episodes

After selecting compact/original by the locked minimum-change rule, the new source, shared Planner, prompt hashes, threshold, budgets and randomized execution list were separately frozen in `live_plan.json` at commit `a0f9868e58aa7d54b9cd009929201aaaac9fa398`. All jobs use unchanged conservative scenes, seed4278, Auto answers and independent resets. Four buffer episodes compare method×profile on the same initial public input; two new Jev cases check progress-before-ASK and observation-without-ASK. No full episode was rerun, omitted or modified mid-study.

| Actual task | Method/profile | Success | Burden | Actions | First p | API latency |
|---|---|---:|---:|---:|---:|---:|
| Buffer | Jev/v6 original | False | 0 | 3 | 0.39 | 5.96s |
| Buffer | Jev/v7 compact | True | 1 | 3 | 0.56 | 7.85s |
| Buffer | LLM/v6 original | True | 1 | 3 | — | 10.35s |
| Buffer | LLM/v7 compact | True | 1 | 3 | — | 8.55s |
| Retrieval | Jev/v7 compact | True | 1 | 3 | 0.13 | 7.53s |
| Occlusion | Jev/v7 compact | True | 0 | 3 | 0.04 | 5.84s |

Candidate cases succeed4/4 over three physical scenes; the preserved original Jev control still fails preference compliance. Candidate retrieval continues at0.13, opens, then asks at0.83. Candidate occlusion continues throughout. Every job uses3 real physical actions and model-generated DONE, without repeated opening or exchange regressions. Current v7 changes no shared action/question prompts or physical scoring. NoAsk was not rerun in this follow-up; its component still uses the unchanged v6 shared Planner and skips Gate.

A higher-latency successful buffer run is not a speed win: it includes a question and additional inference. Backend tokens and per-stage costs are reported separately in the raw-derived summary; do not combine them as dollar savings.

## Cost and verification

- 42 diagnostic requests:32 Jev factorial,6 exact Jev replays,4 DeepSeek controls.
- 56 full-episode requests. Total98/150 authenticated requests, six full episodes, no whole-episode retries or aborts.
- Zero schema/API errors or inference retries. Actual returned models: `deepseek-flash`, `jev-1.14.0`.
- DeepSeek total115,785 input/2,709 output tokens,43.26s cumulative API time. Jev total151,329 input/1,344 output tokens,17.32s. These include all diagnostics and six episodes.
- Baseline343 and final350 offline tests passed. Three scripted-policy/real-physics browser cases, two manual replies, ASK freeze/frame equality, terminal-only truth and mobile layout verified with zero model requests.
- All stage wire inputs recompute exactly. Gate receives the selected projection; Question/Action receive unchanged v6 full public input. Four initial buffer inputs and all Planner/Gate semantic prompt hashes match. Gate precedes Planner; first model action executes verbatim; no automatic ASK/DONE, action masking, hidden truth or oracle.
- All2,515 protected files match previous hashes, including defaults/v5/v6, frozen formal source/data/configuration, historical experiments and the user's already-modified PPT. The complete original formal Test source hash list also still matches.

## Scope and remaining uncertainty

This establishes a usable small Dev fix, not general Gate calibration or a statistical Jev advantage. The state factor removes several kinds of detail together; it cannot isolate which field caused the effect. Candidate scores near0.5 can still vary. Three old layouts do not establish robustness across all9 demo task templates, and v7 is deliberately offered only for these three supported tasks. No formal held-out Test API experiment was run and no frozen configuration was updated.

The next research step is a separately versioned broader Dev evaluation of Gate-state framing, then a newly frozen protocol if adopting v7 formally. The old frozen384-episode Test plan must remain attached to its original protocol; it cannot silently become a v7 test.

## Local delivery

Main HTML http://127.0.0.1:8877/ now offers **Gate Dev v7 · 精简 Gate 输入**; Original Default v1, v5 and v6 remain selectable. Auto/Human and the one-click three-method interface are preserved. Completed six-case evidence is visible at http://127.0.0.1:8898/. [Full report/CSV/raw JSON](../outputs/gate_diagnostics_dev_v7/README.md), [six real MP4s](../presentation/gate_dev_v7/README.md), [tonight's delivery readiness audit](delivery_readiness_2026-11-11.md).

Recompute without API calls: `.venv/bin/python scripts/gate_dev_report.py --export-media` and `.venv/bin/python scripts/delivery_readiness.py`. Paid harnesses require explicit `--live` and refuse to overwrite evidence. All diagnostic and full-episode attempts share one persistent session ledger.
