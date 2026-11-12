# Tabletop contract Dev repair

Dev-only repair/regression; NOT new held-out results.

| Profile | Method | Success | Slots requested | First-ASK reference matches | API latency |
|---|---|---:|---:|---:|---:|
| raw_legacy | llm_noask | 3/4 | 0 | N/A | 12.13s |
| raw_legacy | llm_gate | 3/4 | 6 | 1/4 | 44.52s |
| raw_legacy | jev_gate | 3/4 | 3 | 2/4 | 29.12s |
| facts_contract | llm_noask | 3/4 | 0 | N/A | 12.10s |
| facts_contract | llm_gate | 4/4 | 4 | 3/4 | 28.00s |
| facts_contract | jev_gate | 4/4 | 4 | 4/4 | 19.42s |

## Fixed-state 2×2 diagnostic

| Public representation / prompt | LLM Gate | Jev Gate | Planner next-action reference |
|---|---:|---:|---:|
| raw_legacy | 3/6 | 4/6 | 1/2 |
| facts_legacy | 5/6 | 5/6 | 1/2 |
| raw_contract | 3/6 | 4/6 | 2/2 |
| facts_contract | 6/6 | 6/6 | 2/2 |

## Every paired episode

| Case | Profile | Method | Success | Burden | First ASK after actions | Robot actions | Termination |
|---|---|---|---:|---:|---:|---:|---|
| td1_containers_all_known | facts_contract | jev_gate | True | 0 | None | 2 | done |
| td1_containers_all_known | facts_contract | llm_gate | True | 0 | None | 2 | done |
| td1_containers_all_known | facts_contract | llm_noask | True | 0 | None | 2 | done |
| td1_containers_all_known | raw_legacy | jev_gate | True | 0 | None | 2 | done |
| td1_containers_all_known | raw_legacy | llm_gate | True | 3 | 0 | 2 | done |
| td1_containers_all_known | raw_legacy | llm_noask | True | 0 | None | 2 | done |
| td1_containers_block_first | facts_contract | jev_gate | True | 1 | 0 | 2 | done |
| td1_containers_block_first | facts_contract | llm_gate | True | 1 | 0 | 2 | done |
| td1_containers_block_first | facts_contract | llm_noask | False | 0 | None | 2 | done |
| td1_containers_block_first | raw_legacy | jev_gate | False | 1 | 0 | 12 | robot_action_limit |
| td1_containers_block_first | raw_legacy | llm_gate | False | 1 | 0 | 12 | robot_action_limit |
| td1_containers_block_first | raw_legacy | llm_noask | False | 0 | None | 2 | done |
| td1_pack_block_first | facts_contract | jev_gate | True | 1 | 0 | 3 | done |
| td1_pack_block_first | facts_contract | llm_gate | True | 1 | 0 | 3 | done |
| td1_pack_block_first | facts_contract | llm_noask | True | 0 | None | 3 | done |
| td1_pack_block_first | raw_legacy | jev_gate | True | 0 | None | 3 | done |
| td1_pack_block_first | raw_legacy | llm_gate | True | 0 | None | 3 | done |
| td1_pack_block_first | raw_legacy | llm_noask | True | 0 | None | 3 | done |
| td1_pack_continue_known_cup | facts_contract | jev_gate | True | 2 | 1 | 3 | done |
| td1_pack_continue_known_cup | facts_contract | llm_gate | True | 2 | 0 | 3 | done |
| td1_pack_continue_known_cup | facts_contract | llm_noask | True | 0 | None | 3 | done |
| td1_pack_continue_known_cup | raw_legacy | jev_gate | True | 2 | 0 | 3 | done |
| td1_pack_continue_known_cup | raw_legacy | llm_gate | True | 2 | 0 | 3 | done |
| td1_pack_continue_known_cup | raw_legacy | llm_noask | True | 0 | None | 3 | done |

## Failures preserved

- td1_containers_block_first__facts_contract__llm_noask: correct_cup_in_selected_container, correct_block_in_other_container, declared_dag_order.
- td1_containers_block_first__raw_legacy__jev_gate: correct_cup_in_selected_container, correct_block_in_other_container, declared_dag_order.
- td1_containers_block_first__raw_legacy__llm_gate: declared_dag_order.
- td1_containers_block_first__raw_legacy__llm_noask: correct_cup_in_selected_container, correct_block_in_other_container, declared_dag_order.

## Interpretation

- Four Dev layouts selected to reproduce public-order and partial-progress failure mechanisms, not randomly sampled for generalization.
- Original frozen Test failures informed development; any new claim needs a fresh frozen held-out study. Historical54 episodes and metrics remain unchanged.
- Same structured public facts and shared Planner configuration for all three methods within each profile.
- Small deterministic-state ablations identify sensitivity, not the hidden internal reasoning of a model.
- First-ASK references describe only these explicit controlled Dev cases, not universal optimal timing. NoAsk has no Gate accuracy score.
- Both gates can still fail. Threshold is unchanged; no action is rewritten and no deterministic controller supplies a Gate decision.
- Jev/DeepSeek tokens stay separate; cumulative API latency excludes physics/user response time. Unused-backend totals are null, never fabricated zeros.

Run `.venv/bin/python scripts/tabletop_contract_dev.py report` to recompute from raw files. Full request/response/usage JSONL and PyBullet logs are in ../probes/ and ../episodes/. The protocol, prompt/data/source hashes and randomized run list are in ../manifest.json.
