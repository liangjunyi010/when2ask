# When2Ask: nine-task coverage pilot

Real API paired evaluation: 54/54 episodes. Physical oracle: 36/36.

| Task | Dev | Test | Groups | Physical oracle | NoAsk | LLM-Gate | Jev-Gate |
|---|---:|---:|---:|---:|---:|---:|---:|
| pack_and_cover | 2 | 2 | 4 | 4/4 | 0/2 | 1/2 | 1/2 |
| place_into_selected_containers | 2 | 2 | 4 | 4/4 | 2/2 | 1/2 | 1/2 |
| find_and_approach | 2 | 2 | 4 | 4/4 | 2/2 | 2/2 | 2/2 |
| category_sorting | 2 | 2 | 4 | 4/4 | 1/2 | 2/2 | 2/2 |
| inventory_restock | 2 | 2 | 4 | 4/4 | 1/2 | 2/2 | 2/2 |
| retrieve_restore | 2 | 2 | 4 | 4/4 | 1/2 | 2/2 | 2/2 |
| buffer_exchange | 2 | 2 | 4 | 4/4 | 2/2 | 2/2 | 2/2 |
| patrol_return | 2 | 2 | 4 | 4/4 | 2/2 | 2/2 | 2/2 |
| occlusion_inspection | 2 | 2 | 4 | 4/4 | 2/2 | 2/2 | 2/2 |

| Method | Success | Avg slots requested | DeepSeek in / out | Jev in / out | Total API latency |
|---|---:|---:|---:|---:|---:|
| llm_noask | 13/18 | 0.000 | 235535 / 3396 | unknown / unknown | 78.39s |
| llm_gate | 16/18 | 0.556 | 446252 / 4650 | unknown / unknown | 166.35s |
| jev_gate | 16/18 | 0.389 | 245895 / 3928 | 278894 / 2184 | 112.26s |

## Per-case failures

- n9_test_00_0 / jev_gate: correct_block_inside, unselected_objects_outside, packing_before_cover, declared_dag_order; termination=done.
- n9_test_00_0 / llm_gate: correct_block_inside, unselected_objects_outside, packing_before_cover, declared_dag_order; termination=done.
- n9_test_00_0 / llm_noask: correct_block_inside, unselected_objects_outside, packing_before_cover, declared_dag_order; termination=done.
- n9_test_00_1 / llm_noask: correct_block_inside, unselected_objects_outside, packing_before_cover, declared_dag_order; termination=done.
- n9_test_01_0 / jev_gate: correct_cup_in_selected_container, correct_block_in_other_container, declared_dag_order; termination=robot_action_limit.
- n9_test_01_0 / llm_gate: correct_cup_in_selected_container, correct_block_in_other_container, declared_dag_order; termination=robot_action_limit.
- n9_test_03_1 / llm_noask: all_items_in_category_bins; termination=done.
- n9_test_04_1 / llm_noask: exact_cup_inventory; termination=done.
- n9_test_05_1 / llm_noask: selected_item_delivered, other_item_left_inside, uncover_retrieve_restore_order; termination=done.

## Interpretation and limits

- Only two independent Test cases per task; descriptive engineering pilot, no significance or broad robustness claim.
- The historical128-sample held-out experiment remains unrun and unchanged.
- Each task family retains its established prompts/contract; all three methods share exactly the same planner/serialization within a paired case.
- Mobile cases vary station/furniture placement within one wall topology; not new room topologies.
- Backend tokens stay separate. API latency is cumulative measured inference time, excluding motion and user response time.
- Task success comes from final geometry, contacts, sensing and required event order, independently of DONE or claimed action IDs.
- Historical and new geometry-validation failures are retained; infeasible first geometry was revised before any online calls.

## Reproduce

Run `.venv/bin/python scripts/nine_task_pilot.py report` to recompute all tables from raw episodes. The generate/oracle/freeze commands refuse to replace existing evidence. Online smoke/run commands require --live and refuse reused episode directories. Frozen jobs, dataset/source/prompt hashes, models and budgets are recorded in ../manifest.json. All public model payloads, questions, answers, actions, physical events and per-attempt token/latency records are stored in ../test_runs/.
