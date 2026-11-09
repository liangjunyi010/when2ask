# Twenty DAG Presentation Scenarios

Unpaired smoke demonstration: different scenarios per method, 10 physical groups. Not an unbiased method comparison or held-out Test result.

| Scenario | Method | Unknown | Order | Success | Burden | API seconds |
|---|---|---:|---|---|---:|---:|
| dag_demo_01 | llm_noask | 0 | independent | True | 0 | 3.58 |
| dag_demo_02 | llm_gate | 0 | cup_first | True | 0 | 5.96 |
| dag_demo_03 | jev_gate | 1 | block_first | False | 0 | 5.50 |
| dag_demo_04 | llm_noask | 1 | cup_first | False | 0 | 4.15 |
| dag_demo_05 | llm_gate | 1 | independent | True | 1 | 8.54 |
| dag_demo_06 | jev_gate | 2 | cup_first | True | 2 | 5.83 |
| dag_demo_07 | llm_noask | 2 | block_first | False | 0 | 3.77 |
| dag_demo_08 | llm_gate | 2 | independent | True | 2 | 9.69 |
| dag_demo_09 | jev_gate | 3 | cup_first | True | 3 | 6.31 |
| dag_demo_10 | llm_noask | 3 | block_first | False | 0 | 4.19 |
| dag_demo_11 | llm_gate | 0 | independent | True | 0 | 5.67 |
| dag_demo_12 | jev_gate | 0 | cup_first | True | 0 | 3.71 |
| dag_demo_13 | llm_noask | 0 | block_first | True | 0 | 2.77 |
| dag_demo_14 | llm_gate | 1 | cup_first | True | 0 | 5.65 |
| dag_demo_15 | jev_gate | 1 | independent | True | 1 | 5.73 |
| dag_demo_16 | llm_noask | 2 | block_first | False | 0 | 3.54 |
| dag_demo_17 | llm_gate | 2 | independent | False | 0 | 5.87 |
| dag_demo_18 | jev_gate | 3 | cup_first | True | 3 | 5.21 |
| dag_demo_19 | llm_noask | 3 | block_first | False | 0 | 11.83 |
| dag_demo_20 | llm_gate | 3 | independent | True | 3 | 7.30 |

| Method (unpaired cases) | Success | Total burden | Cumulative API seconds | DeepSeek in / out | Jev in / out |
|---|---:|---:|---:|---:|---:|
| llm_noask | 2/7 | 0 | 33.82 | 53255 / 866 | — |
| llm_gate | 6/7 | 6 | 48.68 | 75853 / 889 | — |
| jev_gate | 5/6 | 9 | 32.28 | 37087 / 653 | 48555 / 600 |

## Timing observations

The support check below reads only the logged public instruction, observation and history; it does not label optimal timing or modify any run.

- `continue_without_disclosed_next_action`: 9 turns.
- `ask_with_supported_progress`: 2 turns.

60 robot skills executed; 0 skill failures, but 7 episodes failed the independent final preference/geometry/order conditions. Physical skill completion is not task success.

Useful presentation cases:

- `dag_demo_03` (Jev): block-first, block unknown. Scores 0.05/0.06/0.05/0.05 never cross 0.5; guessed object/order fails. A genuine missed-clarification example.
- `dag_demo_05` (LLM-Gate) and `dag_demo_06` (Jev): ask at round 0 despite a supported placement. These show premature clarification, even though final tasks succeed.
- `dag_demo_14` (LLM-Gate): no ASK about the unknown block; its guess happens to be correct. Success does not prove appropriate timing.
- `dag_demo_15` (Jev): one missing destination; one answer is reused for the cup and the block's OTHER destination. Success, burden 1.
- `dag_demo_18` (Jev): all three choices unknown; ASK at round 0 (p=0.97), then two placements and success.

## Provenance and scope

20 instances from 10 physical groups, 10 per template; missing counts 0/1/2/3 each occur 5 times. They reuse conservative development geometry, not held-out Test data.
Each JSON trace, physical score, PNG and GIF is retained in `live/`. All requests use the unchanged shared v3.1 contract and Jev threshold 0.5.
Returned models: DeepSeek `deepseek-flash`; Jev `jev-1.14.0` (configured `jev-latest`). No prompt or threshold tuning was performed on these runs.
Metrics are derived from the raw episode JSONs, and the full job order/configuration is in `live_manifest.json`. Timing findings remain engineering diagnostics, not a formal comparative result.
