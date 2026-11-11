# Gate Dev v7: state / contract / threshold diagnosis

Eight replayed public states are not independent physical groups or end-to-end episodes. Contract labels remain outside API payloads. Threshold0.5 is unchanged. Six full episodes are separately scored by the unchanged physical evaluator. No reruns, Test calls or historical rewrites.

| Public state | Expected | Full/original | Full/explicit | Compact/original | Compact/explicit |
|---|---|---:|---:|---:|---:|
| buffer_initial | ASK | 0.39 | 0.40 | 0.57 | 0.54 |
| buffer_disclosed | CONTINUE | 0.04 | 0.04 | 0.04 | 0.04 |
| buffer_finished_guess | CONTINUE | 0.16 | 0.05 | 0.17 | 0.07 |
| retrieval_initial | CONTINUE | 0.13 | 0.07 | 0.13 | 0.07 |
| retrieval_open | ASK | 0.76 | 0.80 | 0.84 | 0.83 |
| retrieval_finished | CONTINUE | 0.11 | 0.09 | 0.11 | 0.10 |
| inspection_initial | CONTINUE | 0.04 | 0.03 | 0.04 | 0.03 |
| inspection_finished | CONTINUE | 0.03 | 0.03 | 0.04 | 0.03 |

Selected by the prelocked minimum-change rule: s1c0. The original contract, shared v6 planner and threshold are unchanged; only the Gate view is compact.

| Actual task | Method | Profile | Success | Burden | Actions | First p | API latency |
|---|---|---|---:|---:|---:|---:|---:|
| buffer_exchange | jev_gate | gate_dev_v7 | True | 1 | 3 | 0.56 | 7.85s |
| buffer_exchange | jev_gate | memory_dev_v6 | False | 0 | 3 | 0.39 | 5.96s |
| buffer_exchange | llm_gate | gate_dev_v7 | True | 1 | 3 | None | 8.55s |
| buffer_exchange | llm_gate | memory_dev_v6 | True | 1 | 3 | None | 10.35s |
| occlusion_inspection | jev_gate | gate_dev_v7 | True | 0 | 3 | 0.04 | 5.84s |
| retrieve_restore | jev_gate | gate_dev_v7 | True | 1 | 3 | 0.13 | 7.53s |

## Replayed exact original requests

- grounded_planner_dev_v5: historical 0.53, this session [0.48, 0.41, 0.47].
- memory_planner_dev_v6: historical 0.43, this session [0.45, 0.45, 0.46].

The historical0.53→0.43 crossing cannot be attributed solely to formatting: identical requests vary. Within this new factorial, compact input improves the buffer decision; stronger wording alone does not. These are local diagnostic observations, not a universal causal/model calibration claim.

## Costs / audit

Gate-only requests 42, full-episode requests 56, total 98/150. Retries/schema/API errors: 0/0/0. Protected files 2515. Stage wire inputs, initial matched physics inputs, unchanged prompts, gate ordering and first-action/ASK-freeze evidence verified.

{"deepseek": {"attempts": 42, "input_tokens": 115785, "unknown_input_tokens_attempts": 0, "output_tokens": 2709, "unknown_output_tokens_attempts": 0, "latency_ms": 43255.466214963235, "unknown_latency_ms_attempts": 0}, "jev": {"attempts": 56, "input_tokens": 151329, "unknown_input_tokens_attempts": 0, "output_tokens": 1344, "unknown_output_tokens_attempts": 0, "latency_ms": 17322.068874069373, "unknown_latency_ms_attempts": 0}}

Threshold sensitivity CSV/JSON is OFFLINE Gate-state reclassification only. It does not represent fresh physical trajectories or task success under another threshold. No runtime threshold was selected from these eight states.

Official Noul semantics and cautions about near-boundary probabilities and small-case threshold fitting were checked against [TypeSafe documentation](https://docs.typesafe.ai/primitives/noul).

Source commit for full episodes: a0f9868e58aa7d54b9cd009929201aaaac9fa398. See live_plan.json and matrix/plan.json for preregistered order, factors, source hashes, selection rule and budget.
