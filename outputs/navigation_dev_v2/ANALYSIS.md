# Navigation Dev v2 interpretation

Verified 12 physical model episodes and 48 gate-only calls. Total authenticated attempts including the protocol incident: 172/200.

All 48 gate-only outputs were CONTINUE. Thus this small ablation did not show a decision-level effect of exclusive wording or the derived summary. Its six states share one map and cannot support generalization or significance claims. The nominal reference is conditional on approximate kinematic costs and a stipulated prior; disagreement is a diagnostic, not proof that a real human would prefer a question.

Complete episodes contain additional measured states beyond those six snapshots. Their actual ASK events must be read from raw turns. Any ASK appearing online does not retroactively change the gate-only result.

The action planner is identical across methods (temperature 0, same prompts/model), yet generated station orders can differ. For example, normal-speed/30s-delay LLM-Gate visited the kitchen while the other two chose the study earlier, even though all three continued. This is planner route variation, not a demonstrated gate-timing effect. Matched-state ablations isolate Gate outputs better; this tiny end-to-end pilot mixes timing with realized search-order variability.

## Technical incident and amendment

The original v2 run registered 12 episode launches and made no robot actions. A DeepSeek HTTP 400 required a literal JSON marker in JSON-object-mode prompts. Its 48 successful gate calls and six launch-stage requests are retained. All source/raw records of that run remain available. The marker was added to Action/Question prompts, regression-tested, and a new hashed plan was created before valid physical execution. Gate rules, threshold, scene facts and ablation snapshots were unchanged; gate-only results were reused without payment.

This explicitly amends the launch cap: 24 combined registrations, comprising 12 execution-before-motion aborts and 12 valid physical runs. The original 200-request cap was preserved using a 54-request offset and a fresh session with at most 146 remaining requests. The amended plan allows 140 for valid episodes. This is a software repair, not a prompt/threshold selection based on performance.

## Unpaid physical policy anchors

The anchors below actually execute wheel-driven physics. Their answer-wait costs are arithmetic using the declared delay; the offline script does not sleep. They are not additional LLM/Jev episodes, and modeled time must not be reported as observed wall time. The nominal-cost Gate is an independent diagnostic policy, never an override on learned gates.

| Cost case | Policy | Success | Burden | Motion simulation s | Modeled operational s |
|---|---|---:|---:|---:|---:|
| nav2_s100_d30_study_shelf | never_ask | True | 0 | 38.31 | 38.31 |
| nav2_s100_d30_study_shelf | ask_at_start | True | 1 | 11.25 | 46.25 |
| nav2_s100_d30_study_shelf | ask_after_one | True | 1 | 20.58 | 55.58 |
| nav2_s100_d30_study_shelf | nominal_cost_gate | True | 0 | 38.31 | 38.31 |
| nav2_s050_d01_study_shelf | never_ask | True | 0 | 74.44 | 74.44 |
| nav2_s050_d01_study_shelf | ask_at_start | True | 1 | 21.80 | 27.80 |
| nav2_s050_d01_study_shelf | ask_after_one | True | 1 | 39.10 | 45.10 |
| nav2_s050_d01_study_shelf | nominal_cost_gate | True | 1 | 21.80 | 27.80 |
| nav2_s050_d30_study_shelf | never_ask | True | 0 | 74.44 | 74.44 |
| nav2_s050_d30_study_shelf | ask_at_start | True | 1 | 21.80 | 56.80 |
| nav2_s050_d30_study_shelf | ask_after_one | True | 1 | 39.10 | 74.10 |
| nav2_s050_d30_study_shelf | nominal_cost_gate | True | 1 | 21.80 | 56.80 |
| nav2_s100_d01_study_shelf | never_ask | True | 0 | 38.31 | 38.31 |
| nav2_s100_d01_study_shelf | ask_at_start | True | 1 | 11.25 | 17.25 |
| nav2_s100_d01_study_shelf | ask_after_one | True | 1 | 20.58 | 26.58 |
| nav2_s100_d01_study_shelf | nominal_cost_gate | True | 1 | 11.25 | 17.25 |

## Limits and next experiment

One original map group and one seed-selected target are used for the complete cost-factorial. The uniform prior is a planning stipulation, not a frequency estimated from the four placements. Realized cost on this target can disagree with expected cost under that prior. Therefore neither realized advantage nor nominal-reference match alone proves optimal clarification timing.

A next independent version should balance multiple target placements across independent layouts, hold declared costs fixed, quantify search-order variation, and preregister any threshold sensitivity by operational cost/burden, not ask frequency. Recompute actual trajectories for every threshold. Keep existing frozen Test and these results unchanged.

Preservation: all 1261 pre-existing protected file hashes match. No held-out Test calls; user-modified PPT preserved.
