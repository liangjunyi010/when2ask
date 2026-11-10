# Six genuinely new robotic tasks — engineering smoke

Unpaired: one different task per case, methods rotate. No ranking, significance, or held-out Test conclusion.

| Task | Method | Success | Burden | Actions | Skill failures | API latency |
|---|---|---|---:|---:|---:|---:|
| Category Sorting · 分类整理 | llm_noask | False | 0 | 6 | 0 | 6.95 s |
| Inventory Restock · 库存补货 | llm_gate | True | 1 | 3 | 0 | 9.94 s |
| Retrieve & Restore · 开盒取物复原 | jev_gate | True | 1 | 3 | 0 | 5.59 s |
| Buffered Exchange · 缓冲区交换 | llm_noask | False | 0 | 12 | 3 | 11.11 s |
| Patrol & Return · 多点巡检返航 | llm_gate | True | 1 | 3 | 0 | 9.27 s |
| Reveal & Inspect · 移开遮挡检查 | jev_gate | True | 0 | 3 | 0 | 5.32 s |

## What the actual turns show

### Category Sorting · 分类整理

- Round 0: CONTINUE; {"kind": "move", "object_id": "cup_1", "target_id": "bin_a"}
- Round 1: CONTINUE; {"kind": "move", "object_id": "cup_2", "target_id": "bin_a"}
- Round 2: CONTINUE; {"kind": "move", "object_id": "block_1", "target_id": "bin_b"}
- Round 3: CONTINUE; {"kind": "move", "object_id": "block_2", "target_id": "bin_b"}
- Round 4: CONTINUE; {"kind": "move", "object_id": "puck_1", "target_id": "bin_c"}
- Round 5: CONTINUE; {"kind": "move", "object_id": "puck_2", "target_id": "bin_c"}
- Round 6: CONTINUE; {"kind": "DONE"}

### Inventory Restock · 库存补货

- Round 0: CONTINUE; {"kind": "move", "object_id": "spare_cup_1", "target_id": "cup_shelf"}
- Round 1: ASK; How many blocks should the block shelf hold in total: 2 or 3?
  User simulator: {"choices": {"block_quota": "3"}}
- Round 2: CONTINUE; {"kind": "move", "object_id": "spare_block_1", "target_id": "block_shelf"}
- Round 3: CONTINUE; {"kind": "move", "object_id": "spare_block_2", "target_id": "block_shelf"}
- Round 4: CONTINUE; {"kind": "DONE"}

### Retrieve & Restore · 开盒取物复原

- Round 0: CONTINUE p=0.26; {"kind": "move", "object_id": "storage_lid", "target_id": "lid_pad"}
- Round 1: ASK p=0.79; Which item should I retrieve from the storage box: the blue cup or the green block?
  User simulator: {"choices": {"retrieval_item": "stored_block"}}
- Round 2: CONTINUE p=0.04; {"kind": "move", "object_id": "stored_block", "target_id": "delivery_pad"}
- Round 3: CONTINUE p=0.08; {"kind": "cover", "object_id": "storage_lid"}
- Round 4: CONTINUE p=0.09; {"kind": "DONE"}

### Buffered Exchange · 缓冲区交换

- Round 0: CONTINUE; {"kind": "move", "object_id": "item_a", "target_id": "buffer_front"}
- Round 1: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_left"}
- Round 2: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_right"}
- Round 3: CONTINUE; {"kind": "move", "object_id": "item_a", "target_id": "slot_right"}
- Round 4: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_left"}
- Round 5: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_right"}
- Round 6: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_left"}
- Round 7: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_right"}
- Round 8: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "buffer_front"}
- Round 9: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_left"}
- Round 10: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "buffer_front"}
- Round 11: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_right"}
- Round 12: CONTINUE; {"kind": "move", "object_id": "item_b", "target_id": "slot_left"} (planned but not executed: budget termination)

### Patrol & Return · 多点巡检返航

- Round 0: CONTINUE; {"kind": "inspect_station", "location_id": "living_cabinet"}
- Round 1: ASK; Which study-room station should I inspect as the extra station: the study desk or the study shelf?
  User simulator: {"choices": {"extra_station": "study_shelf"}}
- Round 2: CONTINUE; {"kind": "inspect_station", "location_id": "study_shelf"}
- Round 3: CONTINUE; {"kind": "return_home"}
- Round 4: CONTINUE; {"kind": "DONE"}

### Reveal & Inspect · 移开遮挡检查

- Round 0: CONTINUE p=0.04; {"kind": "move", "object_id": "opaque_screen", "target_id": "screen_pad"}
- Round 1: CONTINUE p=0.06; {"kind": "inspect", "target_id": "label_fixture"}
- Round 2: CONTINUE p=0.07; {"kind": "report", "code": "beta"}
- Round 3: CONTINUE p=0.05; {"kind": "DONE"}

## Interpretation and limitations

- Real physical oracle attempt 1: 4/6. The short category item interfered with the bin rim; patrol had no physical fixture to hit with its ray. Both failures are retained.
- Corrected geometry uses graspable cylinders and actual equipment fixtures. Attempt 2: 6/6; independent real-physics pytest also passes all six. No old controller, evaluator threshold or frozen study was changed.
- Sorting NoAsk placed all six objects successfully but guessed the wrong category-bin assignment. Final task score remains false.
- Buffered exchange NoAsk guessed a buffer, repeatedly reversed progress, attempted full/occupied targets and stopped at 12 physical actions. This combines preference uncertainty and planner failure; it cannot be attributed solely to the absence of clarification.
- Inventory and patrol LLM-Gate each performed known work, then asked one preference, reused the answer and completed.
- Retrieve/restore Jev-Gate continued to open the box at p=0.26, asked at p=0.79, retrieved the selected item and closed the box.
- Occlusion Jev-Gate continued throughout: move screen, perform a real ray/range-qualified inspection, report the measured code. It did not ask for an observable world fact.
- 60 real authenticated requests, including 2 retries and 2 schema errors. Actual usage and latency remain in every API attempt. No API errors were reported.
- These are six different tasks with two cases per method, not paired method comparisons. The HTML comparison launcher is integrated; additional paid three-method batches were not run in this six-episode study.
- Tabletop inspection is a structured sensor gated by actual Bullet ray visibility and range, not learned image recognition. Patrol reuses the existing known three-room map and requires actual orientation, fixture sight and return.
- Worker GIF/MP4 records actual physical frames with display holds; model/ASK wall time is excluded. The full original instruction, gate/question/answer/action sequence and final truth are in the console review. The dependency diagrams are static task DAGs, not independent timed animations.
- Manual browser verification used six explicitly scripted policies with real physics (six successes, five question/answer freeze checks, zero API calls). It is excluded from live-model metrics.

## Tokens (backends separate)

DeepSeek input/output: 137341 / 813. Jev input/output: 26666 / 216.
Cumulative authenticated API latency: 48.18 s, not average episode latency.

All original frozen datasets, prompts, configurations, physics files and historical records remain unchanged. New task prompts/data and the locked six-case manifest are separate.
