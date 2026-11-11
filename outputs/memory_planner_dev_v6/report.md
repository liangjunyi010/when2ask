# Memory Dev v6 — nine paired real episodes

One fixed scene per task (3 paired groups), not a powered benchmark or formal Test. Twelve action-only replay probes (including one retained mismatch) are separately costed, not episodes. All nine full episodes use the final frozen version; no whole-episode reruns. Manual UI checks are scripted policies with actual physics, zero API.

| Task | Method | Success | Burden | Actions | API latency | Reopens | Regressions | Failed conditions |
|---|---|---:|---:|---:|---:|---:|---:|---|
| buffer_exchange | jev_gate | False | 0 | 3 | 6.02s | 0 | 0 | selected_buffer_physically_used, other_buffer_unused, buffer_exchange_order |
| buffer_exchange | llm_gate | True | 1 | 3 | 10.39s | 0 | 0 | — |
| buffer_exchange | llm_noask | False | 0 | 3 | 4.68s | 0 | 0 | selected_buffer_physically_used, other_buffer_unused, buffer_exchange_order |
| occlusion_inspection | jev_gate | True | 0 | 3 | 6.02s | 0 | 0 | — |
| occlusion_inspection | llm_gate | True | 0 | 3 | 9.23s | 0 | 0 | — |
| occlusion_inspection | llm_noask | True | 0 | 3 | 4.70s | 0 | 0 | — |
| retrieve_restore | jev_gate | True | 1 | 3 | 6.81s | 0 | 0 | — |
| retrieve_restore | llm_gate | True | 1 | 3 | 9.39s | 0 | 0 | — |
| retrieve_restore | llm_noask | False | 0 | 3 | 4.13s | 0 | 0 | selected_item_delivered, other_item_left_inside, uncover_retrieve_restore_order |

## Cost by method (cumulative over 3 episodes)

| Method | Success | Burden | DeepSeek in/out | Jev in/out | API latency |
|---|---:|---:|---|---|---:|
| llm_noask | 1/3 | 0 | 35980/1177 | None/None | 13.52s |
| llm_gate | 3/3 | 2 | 75530/1397 | None/None | 29.00s |
| jev_gate | 2/3 | 1 | 38988/1221 | 45001/312 | 18.85s |

## Action-only probe cost (separate from episode table)

{"deepseek": {"attempts": 12, "input_tokens": 38820, "output_tokens": 1027, "latency_ms": 14106.60287301289}, "jev": {"attempts": 0, "input_tokens": null, "output_tokens": null, "latency_ms": null}}
All work: 78/150 authenticated attempts; twelve action-only probes plus nine complete episodes.

## Actual decision sequences

### buffer_exchange / jev_gate

- Round 0, step 240: CONTINUE p=0.43; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'buffer_front'}; question=None; answer=None
- Round 1, step 3507: CONTINUE p=0.16; action={'kind': 'move', 'object_id': 'item_b', 'target_id': 'slot_left'}; question=None; answer=None
- Round 2, step 7097: CONTINUE p=0.21; action={'kind': 'move', 'object_id': 'item_a', 'target_id': 'slot_right'}; question=None; answer=None
- Round 3, step 10803: CONTINUE p=0.2; action={'kind': 'DONE'}; question=None; answer=None
### buffer_exchange / llm_gate

- Round 0, step 240: ASK p=None; action=None; question={'type': 'select', 'text': 'Which temporary buffer pad should I use for the exchange: buffer_front or buffer_back?', 'requests': [{'role': 'buffer_pad', 'candidate_ids': ['buffer_front', 'buffer_back']}]}; answer={'choices': {'buffer_pad': 'buffer_back'}}
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
- Round 1, step 3702: CONTINUE p=0.05; action={'kind': 'inspect', 'target_id': 'label_fixture'}; question=None; answer=None
- Round 2, step 3822: CONTINUE p=0.06; action={'kind': 'report', 'code': 'beta'}; question=None; answer=None
- Round 3, step 3822: CONTINUE p=0.03; action={'kind': 'DONE'}; question=None; answer=None
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

- Round 0, step 240: CONTINUE p=0.13; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: ASK p=0.76; action=None; question={'type': 'select', 'text': 'Which item should I retrieve from the box: the blue cup or the green block?', 'requests': [{'role': 'retrieval_item', 'candidate_ids': ['stored_cup', 'stored_block']}]}; answer={'choices': {'retrieval_item': 'stored_block'}}
- Round 2, step 3702: CONTINUE p=0.04; action={'kind': 'move', 'object_id': 'stored_block', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 3, step 7484: CONTINUE p=0.06; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 4, step 11371: CONTINUE p=0.1; action={'kind': 'DONE'}; question=None; answer=None
### retrieve_restore / llm_gate

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: ASK p=None; action=None; question={'type': 'select', 'text': 'Which item should I retrieve from the box: the blue cup or the green block?', 'requests': [{'role': 'retrieval_item', 'candidate_ids': ['stored_cup', 'stored_block']}]}; answer={'choices': {'retrieval_item': 'stored_block'}}
- Round 2, step 3702: CONTINUE p=None; action={'kind': 'move', 'object_id': 'stored_block', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 3, step 7484: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 4, step 11371: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None
### retrieve_restore / llm_noask

- Round 0, step 240: CONTINUE p=None; action={'kind': 'move', 'object_id': 'storage_lid', 'target_id': 'lid_pad'}; question=None; answer=None
- Round 1, step 3702: CONTINUE p=None; action={'kind': 'move', 'object_id': 'stored_cup', 'target_id': 'delivery_pad'}; question=None; answer=None
- Round 2, step 7194: CONTINUE p=None; action={'kind': 'cover', 'object_id': 'storage_lid'}; question=None; answer=None
- Round 3, step 11081: CONTINUE p=None; action={'kind': 'DONE'}; question=None; answer=None

## Audit

Authenticated requests: 66/150. Preserved historical/physics files: 2346. All wire inputs match saved public payloads; all three initial payloads match within each paired task. First model action is executed verbatim, without a cached suffix. Gate precedes planning. ASK holds the same physical state.

Source implementation commit: `1a69c3ca841654da3031a361d5dc00653461193b`. Prompt/source hashes, budgets and randomized group order were locked before the first full-episode request in `live_plan.json` (the separately retained probes preceded that freeze). Default v1 and frozen/history files remain unchanged.
