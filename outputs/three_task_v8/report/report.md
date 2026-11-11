# Three-task Benchmark v8 — held-out paired Test

Small genuinely held-out layout Test for the three new templates, independent of original128-Test.
Source/prompts/models/threshold frozen before Test, all Test samples paired across methods; no whole-episode retries or sample exclusions.
Early/missed ASK counts are EXPLORATORY post-Test public-DAG/scripted support diagnostics, not preregistered optimal-timing labels. No private preference is used for this reference.
Physical oracle knows private preference only for feasibility; its trajectories are never agent inputs.

| Method | Success | Mean burden | DeepSeek in/out | Jev in/out | Total API latency | Physical failures |
|---|---:|---:|---|---|---:|---:|
| llm_noask | 10/12 | 0.000 | 143551/4830 | None/None | 57.91s | 0 |
| llm_gate | 12/12 | 0.333 | 238767/5442 | None/None | 105.41s | 1 |
| jev_gate | 12/12 | 0.333 | 161546/5219 | 116101/1296 | 78.56s | 2 |

All 36/36 planned episodes retained; 262/450 authenticated requests. Oracle36/36, actual offline Test source/prompt/config hashes verified. Group Wilson intervals and paired bootstrap are descriptive; only12 independent groups.

## Physical/model failures

- t8_r2_test_1_04_1 / llm_noask: task_success=False; failed conditions=['selected_item_delivered', 'other_item_left_inside', 'uncover_retrieve_restore_order']; rejected skill attempts=[]
- t8_r2_test_1_04_1 / jev_gate: task_success=True; failed conditions=[]; rejected skill attempts=[{'skill': 'move', 'object_id': 'storage_lid', 'target_id': 'box', 'success': False, 'reason': 'use_surface_for_large_panel', 'start_step': 7514, 'end_step': 7514, 'grasp_mode': 'constraint'}]
- t8_r2_test_1_04_1 / llm_gate: task_success=True; failed conditions=[]; rejected skill attempts=[{'skill': 'move', 'object_id': 'storage_lid', 'target_id': 'box', 'success': False, 'reason': 'use_surface_for_large_panel', 'start_step': 7514, 'end_step': 7514, 'grasp_mode': 'constraint'}]
- t8_r2_test_0_04_3 / llm_noask: task_success=False; failed conditions=['selected_buffer_physically_used', 'other_buffer_unused', 'buffer_exchange_order']; rejected skill attempts=[]
- t8_r2_test_1_03_0 / jev_gate: task_success=True; failed conditions=[]; rejected skill attempts=[{'skill': 'move', 'object_id': 'storage_lid', 'target_id': 'box', 'success': False, 'reason': 'use_surface_for_large_panel', 'start_step': 7900, 'end_step': 7900, 'grasp_mode': 'constraint'}]

## Exploratory ASK timing

Reference uses only the public DAG/observations and the unchanged scripted support policy after Test. It is an explanatory diagnostic, not an optimal oracle or a tuning signal. NoAsk does not call Gate and is not scored as a Gate classifier.
- NoAsk: Gate skipped; classifier timing metric is not applicable.
- llm_gate: early/unnecessary asks=2, missed blocking asks=0.
- jev_gate: early/unnecessary asks=0, missed blocking asks=0.

## Paired group uncertainty

[{"first": "llm_gate", "second": "llm_noask", "group_paired_sr_difference": 0.16666666666666666, "bootstrap95": [0.0, 0.4166666666666667], "independent_groups": 12, "policy": "Exploratory stratified paired group bootstrap; each template contributes4 groups. No significance claim, no variants counted independently.", "warning": null}, {"first": "jev_gate", "second": "llm_noask", "group_paired_sr_difference": 0.16666666666666666, "bootstrap95": [0.0, 0.4166666666666667], "independent_groups": 12, "policy": "Exploratory stratified paired group bootstrap; each template contributes4 groups. No significance claim, no variants counted independently.", "warning": null}, {"first": "jev_gate", "second": "llm_gate", "group_paired_sr_difference": 0.0, "bootstrap95": [0.0, 0.0], "independent_groups": 12, "policy": "Exploratory stratified paired group bootstrap; each template contributes4 groups. No significance claim, no variants counted independently.", "warning": "No observed discordant outcomes; a degenerate empirical interval is not evidence of population equivalence."}]

Rows, attempted skill failures, full costs, source hashes and all API attempts are retained. No prompt/threshold/controller repair was made after Test outcomes. Original frozen128-Test and all its historical records were left untouched.
