# Independent three-task Benchmark v8

Selected dataset: `r2/`. Dev24 samples/6 layout groups; Test12 samples/12 held-out layout groups; each of3 templates has Dev8/Test4. One binary preference/world-fact slot, unknown0/1 balanced. All12 Test samples were paired across3 real methods. This is separate from the original `data/phase3/`32-Dev/128-Test benchmark.

Groups depend on unordered physical geometry, not preference/colour/code/list order. All variants remain in one partition. Test groups are excluded from near-duplicate Dev and historical tuned layouts. Physical oracle36/36 before model Test. Correct alternative and candidate ranks are balanced; group-fixed physical seed and source order prevent hidden preference from changing initial public state.

`r1/` is a retained generation candidate whose2/10 Test candidate-rank imbalance was detected before any oracle/API call. The counterbalanced r2 revision is recorded in `outputs/three_task_v8/generation_amendment.json`; no model result was used to select samples. `r2/freeze.json` records the selected dataset hashes and link to the frozen protocol. Full [construction/results](../../docs/three_task_benchmark_v8.md).
