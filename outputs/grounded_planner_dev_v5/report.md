# Grounded Dev v5 — nine paired real episodes

One fixed scene per task (3 paired groups), not a powered benchmark or formal Test. Three r1 aborted preflight episodes are separate and fully retained; nine r2 paired episodes use identical corrected configuration. No r2 whole-episode reruns; schema repairs and all failures retained. Manual UI checks use explicitly scripted policies and real physics, zero API.

| Task | Method | Success | Burden | Actions | API latency | Failed conditions |
|---|---|---:|---:|---:|---:|---|
| buffer_exchange | jev_gate | True | 1 | 7 | 14.23s | — |
| buffer_exchange | llm_gate | True | 1 | 3 | 8.49s | — |
| buffer_exchange | llm_noask | False | 0 | 3 | 4.45s | selected_buffer_physically_used, other_buffer_unused, buffer_exchange_order |
| occlusion_inspection | jev_gate | True | 0 | 3 | 6.15s | — |
| occlusion_inspection | llm_gate | True | 0 | 3 | 8.00s | — |
| occlusion_inspection | llm_noask | True | 0 | 3 | 4.16s | — |
| retrieve_restore | jev_gate | False | 1 | 12 | 22.05s | box_reclosed |
| retrieve_restore | llm_gate | False | 1 | 12 | 29.18s | box_reclosed |
| retrieve_restore | llm_noask | False | 0 | 12 | 16.04s | selected_item_delivered, other_item_left_inside, box_reclosed, uncover_retrieve_restore_order |

## Cost by method (cumulative over 3 episodes)

| Method | Success | Burden | DeepSeek in/out | Jev in/out | API latency |
|---|---:|---:|---|---|---:|
| llm_noask | 1/3 | 0 | 52049/2540 | None/None | 24.65s |
| llm_gate | 2/3 | 2 | 108202/2796 | None/None | 45.68s |
| jev_gate | 2/3 | 2 | 69581/3127 | 87463/648 | 42.44s |

## Retained preflight cost (separate from r2 table)

{"deepseek": {"attempts": 5, "input_tokens": 9017, "output_tokens": 424, "latency_ms": 4588.360415000352}, "jev": {"attempts": 1, "input_tokens": 2246, "output_tokens": 24, "latency_ms": 288.2045000005746}}
All work: 127/150 authenticated attempts; three aborted r1 plus nine r2 episodes.

## Actual decision sequences

### buffer_exchange / jev_gate

- Round 0, step 240: ASK p=0.53; action=None; question={'type': 'select', 'text': 'Which temporary buffer pad should I use for the exchange?', 'requests': [{'role': 'buffer_pad', 'candidate_ids': ['buffer_front', 'buffer_back']}]}; answer={'choices': {'buffer_pad': 'buffer_back'}}
- Round 1, step 240: CONTINUE p=0.04; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'buffer_back'}; question=None; answer=None
- Round 2, step 3791: CONTINUE p=0.05; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_left'}; question=None; answer=None
- Round 3, step 7160: CONTINUE p=0.07; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'slot_right'}; question=None; answer=None
- Round 4, step 10796: CONTINUE p=0.15; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'buffer_back'}; question=None; answer=None
- Round 5, step 13942: CONTINUE p=0.08; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_right'}; question=None; answer=None
- Round 6, step 17532: CONTINUE p=0.08; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_left'}; question=None; answer=None
- Round 7, step 20731: CONTINUE p=0.06; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'slot_right'}; question=None; answer=None
- Round 8, step 24366: CONTINUE p=0.1; action={'kind': 'DONE'}; question=None; answer=None
### buffer_exchange / llm_gate

- Round 0, step 240: ASK p=None; action=None; question={'type': 'select', 'text': 'Which temporary buffer pad should I use for the exchange?', 'requests': [{'role': 'buffer_pad', 'candidate_ids': ['buffer_front', 'buffer_back']}]}; answer={'choices': {'buffer_pad': 'buffer_back'}}
- Round 1, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'buffer_back'}; question=None; answer=None
- Round 2, step 3791: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_left'}; question=None; answer=None
- Round 3, step 7160: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'slot_right'}; question=None; answer=None
- Round 4, step 10796: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None
### buffer_exchange / llm_noask

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'buffer_front'}; question=None; answer=None
- Round 1, step 3507: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_left'}; question=None; answer=None
- Round 2, step 7097: CONTINUE p=None; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'slot_right'}; question=None; answer=None
- Round 3, step 10803: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None
### occlusion_inspection / jev_gate

- Round 0, step 240: CONTINUE p=0.04; action={'kind': 'move', 'object_id': 'opaque_screen', 'target_id': 'screen_pad'}; question=None; answer=None
- Round 1, step 3702: CONTINUE p=0.04; action={'kind': 'inspect', 'target_id': 'label_fixture'}; question=None; answer=None
- Round 2, step 3822: CONTINUE p=0.06; action={'kind': 'report', 'code': 'beta'}; question=None; answer=None
- Round 3, step 3822: CONTINUE p=0.04; action={'kind': 'DONE'}; question=None; answer=None
### occlusion_inspection / llm_gate

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'opaque_screen', 'target_id': 'screen_pad'}; question=None; answer=None
- Round 1, step 3702: CONTINUE p=None; action={'kind': 'inspect', 'target_id': 'label_fixture'}; question=None; answer=None
- Round 2, step 3822: CONTINUE p=None; action={'kind': 'report', 'code': 'beta'}; question=None; answer=None
- Round 3, step 3822: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None
### occlusion_inspection / llm_noask

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'opaque_screen', 'target_id': 'screen_pad'}; question=None; answer=None
- Round 1, step 3702: CONTINUE p=None; action={'kind': 'inspect', 'target_id': 'label_fixture'}; question=None; answer=None
- Round 2, step 3822: CONTINUE p=None; action={'kind': 'report', 'code': 'beta'}; question=None; answer=None
- Round 3, step 3822: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None
### retrieve_restore / jev_gate

- Round 0, step 240: CONTINUE p=0.12; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: ASK p=0.81; action=None; question={'type': 'select', 'text': 'Which item should I retrieve from the box: the blue cup or the green block?', 'requests': [{'role': 'retrieval_item', 'candidate_ids': ['stored_cup', 'stored_block']}]}; answer={'choices': {'retrieval_item': 'stored_block'}}
- Round 2, step 3702: CONTINUE p=0.04; action={'kind': 'move', 'object_id': 'stored_block', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 3, step 7484: CONTINUE p=0.06; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 4, step 11371: CONTINUE p=0.06; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 5, step 14763: CONTINUE p=0.1; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 6, step 18082: CONTINUE p=0.08; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 7, step 21474: CONTINUE p=0.11; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 8, step 24793: CONTINUE p=0.07; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 9, step 28185: CONTINUE p=0.09; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 10, step 31504: CONTINUE p=0.09; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 11, step 34896: CONTINUE p=0.12; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 12, step 38215: CONTINUE p=0.09; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 13, step 41607: CONTINUE p=0.1; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
### retrieve_restore / llm_gate

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: ASK p=None; action=None; question={'type': 'select', 'text': 'Which item should I retrieve from the box: the blue cup or the green block?', 'requests': [{'role': 'retrieval_item', 'candidate_ids': ['stored_cup', 'stored_block']}]}; answer={'choices': {'retrieval_item': 'stored_block'}}
- Round 2, step 3702: CONTINUE p=None; action={'kind': 'move', 'object_id': 'stored_block', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 3, step 7484: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 4, step 11371: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 5, step 14763: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 6, step 18082: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 7, step 21474: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 8, step 24793: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 9, step 28185: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 10, step 31504: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 11, step 34896: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 12, step 38215: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 13, step 41607: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
### retrieve_restore / llm_noask

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: CONTINUE p=None; action={'kind': 'move', 'object_id': 'stored_cup', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 2, step 7194: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 3, step 11081: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 4, step 14473: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 5, step 17792: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 6, step 21184: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 7, step 24503: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 8, step 27895: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 9, step 31214: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 10, step 34606: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 11, step 37925: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 12, step 41317: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None

## Audit

Authenticated requests: 121/150. Preserved historical/physics files: 2181. All wire inputs match saved public payloads; all three initial payloads match within each paired task. First model action is executed verbatim, without a cached suffix. Gate precedes planning. ASK holds the same physical state.

Source implementation commit: `216e2cfc2b60847b7e202efa34d7e7dbdbc3f49d`. Prompt/source hashes, budgets and randomized group order were locked before the first paid request in `live_plan_r2.json`. Default v1 and frozen/history files remain unchanged.
