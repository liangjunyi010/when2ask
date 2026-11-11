# When2Ask Three-task Benchmark v8 — independent held-out layouts

This independent benchmark adds **buffered exchange, retrieve/restore and occlusion inspection**. It preserves the original32-Dev/128-Test dataset, its frozen protocol and every historical record. The new Test was generated and mechanically validated before its first model request; no old tuned case was renamed as Test. This is a small three-template benchmark, not a completed nine-template evaluation.

## Dataset and construction

| Partition | Samples | Independent base groups | Per template | Unknown slot0/1 |
|---|---:|---:|---:|---:|
| Dev |24|6|8 samples /2 groups|12 /12|
| Test |12|12|4 samples /4 groups|6 /6|

Dev has all four combinations of two possible true choices × disclosed/undisclosed for each base layout. Each Test group contributes one condition chosen in the generation plan, balancing choice and disclosure across its four layouts. **All12 Test samples are evaluated under all3 methods**, not an outcome-selected subset. Each new task has one binary preference/fact, so its disclosure count is0/1; this does not claim the old0–3-slot coverage.

- **Exchange DAG:** park A on the user-selected pad → move B to left slot → move A to right slot. Capacity one, other pad never used, both pads empty and robot released at the end. Two possible pad preferences, each equally represented.
- **Retrieval DAG:** park lid/open → retrieve selected cup/block to delivery pad → restore lid. Other item must remain inside; release required. Both possible item choices equally represented.
- **Inspection DAG:** clear screen → real camera inspection → report measured alpha/beta code. Both codes equally represented. This is an immutable world fact; hints or guesses cannot replace inspection.

The primitive geometry and existing motor/IK/guarded constraint-grasp skills are reused. New bin/source/parking/delivery/label-camera arrangements stay in the conservative workspace. A group's fingerprint ignores truth, disclosure, colour, candidate/list order and printed code, and matches unordered geometry by type. All variants of the same geometry stay together. The minimum cross-split matched-geometry distance is **0.0781m**; near-duplicate groups below0.035m are rejected, including any Test layout near the historical tuned base scenes. This metric describes matched layout displacement, not object clearance.

Physical object IDs remain canonical for compatibility with the unchanged task world and skill API. Truth is balanced across both alternatives, and correct candidate rank is exactly6/6 in Test and12/12 in Dev. Source object order and scene seed are fixed within a group, independently of hidden truth. Tests instantiate two actual worlds with opposite hidden values and verify identical initial public payloads while the fact is unobserved. The small design cannot eliminate every incidental higher-order correlation, and does not claim opaque-ID or natural-language diversity beyond two controlled instruction forms.

The first generated candidate `r1` had an unbalanced candidate-rank audit (2/10 on Test) and was revised **before any oracle or model request**. Its raw files/audit remain. `r2` is the selected dataset, under `data/three_task_v8/r2/`. This was counterbalancing, not filtering on model performance.

## Actual physical oracle

Every sample instantiated its real PyBullet world, checked initial inter-object penetrations, executed the deterministic oracle using real motor skills, and was scored by the unchanged independent task6 geometry/contact/DAG evaluator:

| Partition | Actual physical success |
|---|---:|
| Dev |24/24|
| Test |12/12|
| Total |36/36|

There are18 independent layouts across these36 instances, not36 independent layouts. Private preferences are available only to the offline feasibility oracle. Its generated dialogue/trajectory is never an online agent input. The oracle establishes physical executability, not model success or clarification correctness.

## Frozen protocol and real evaluation

Experiment ID: `three_task_v8_heldout_test_r2`. Source commit `0fcd2723eea2008c094000b65eda62284f1d7874`. After all oracle checks, `outputs/three_task_v8/frozen_manifest.json` locks source/prompt/data hashes, model settings, every Test sample/method, randomized order, recording cases and budgets before model Test.

- Methods: LLM-NoAsk, LLM-Gate, Jev-Gate. All share the exact v6 DeepSeek Planner/Question generator, v7 common compact Gate view, simulator, physical skills and evaluator. NoAsk skips Gate.
- Jev threshold0.5, DeepSeek non-thinking JSON, temperature0. Action/question/gate output caps650/300/64. Actual returned models `deepseek-flash`, `jev-1.14.0`; aliases do not expose every underlying build detail.
- Per episode:20 rounds,12 attempted robot commands,12 requested slots,32 API attempts. Global36 episodes/450 requests, including repairs/retries.3 isolated processes, randomized/interleaved jobs, independent scene/history reset for every method.
- Gate precedes action planning. Only the first model-proposed action executes verbatim; no cached suffix, forced ASK/DONE, private evaluator input, progress masking or rewritten command.
- User Simulator discloses only requested information; ASK never steps physics. Task success is judged from real final state and required events, independently of DONE/termination.
- No prompt, threshold, controller, sample selection or task scoring was changed after viewing Test results. No whole episode was rerun or excluded.

## Held-out Test results

| Method | Task success | Mean burden | DeepSeek input/output | Jev input/output | API latency total |
|---|---:|---:|---:|---:|---:|
| LLM-NoAsk |10/12 (83.3%)|0.000|143,551 /4,830|—|57.91s|
| LLM-Gate |12/12 (100%)|0.333|238,767 /5,442|—|105.41s|
| Jev-Gate |12/12 (100%)|0.333|161,546 /5,219|116,101 /1,296|78.56s|

All36 planned episodes completed, using **262/450 authenticated requests**, no API/schema errors or inference retries. These latency values are cumulative over12 episodes per method; means are4.83s/8.78s/6.55s. Backend tokens are separate and do not establish dollar savings. Different actual action histories also contribute to latency; it is not a pure isolated gate-speed measurement.

| Task | NoAsk | LLM-Gate | Jev-Gate |
|---|---:|---:|---:|
| Buffered exchange |3/4|4/4|4/4|
| Retrieve & restore |3/4|4/4|4/4|
| Reveal & inspect |4/4|4/4|4/4|

There are two unknown-preference cases per task, plus two disclosed controls. All methods succeed on the six disclosed cases. Across the six undisclosed cases, NoAsk4/6, LLM6/6, Jev6/6; the unknown code cases remain physically observable and need no user question. NoAsk guesses wrong once for the pad and once for the retrieval item, and correctly scores false despite physically completing under those guesses. It is not artificially labelled unsuccessful.

### Failures and repairs remain visible

There are111 attempted skill commands:108 succeed and3 are rejected. In three gate episodes, the model proposes `move(storage_lid, box)` instead of the dedicated cover skill. The unchanged skill guard returns `use_surface_for_large_panel`, without teleporting or silently translating it. The next actual model turn calls `cover`, physically closes the box and passes the independent final evaluator. These3 rejected commands and their inference cost are retained;100% final task success is not zero intermediate failure.

### Timing diagnostic — explicitly exploratory

After Test, we computed a diagnostic using only public DAG/state and the existing public-only scripted support policy. It never reads hidden preferences. NoAsk is not a gate classifier. The diagnostic finds2 early/unnecessary LLM questions and0 for Jev, with no missed blocking questions for either. Both cases are the two undisclosed retrieval layouts: LLM asks before the useful opening action, Jev opens first then asks.

This diagnostic was added after observing Test; it is **not a preregistered optimal-timing metric** and is not used for threshold/prompt selection. Its plot is useful for explaining the difference between identical success/burden and different interruption timing. It should become a predefined metric in a future experiment, not retroactively a confirmatory claim here.

## Uncertainty and scope

There are12 independent Test groups, one Test sample per group. Wilson95% intervals are approximately NoAsk[0.552,0.953], gates[0.757,1.000]. A stratified paired group bootstrap estimates the gate−NoAsk difference as+0.167 with interval[0.000,0.417]; no statistical superiority claim is made. With no discordant success outcomes between the two gates, a degenerate empirical bootstrap difference does not establish population equivalence. Dev variants are never counted as independent Test cases.

The benchmark covers new layouts for the same three task templates, not zero-shot unseen task types. It uses primitive geometry, one binary slot/fact and a small controlled distribution. The old frozen two-template128-Test is still unrun and unchanged; the new numbers cannot be merged with old Dev tables as one experiment. The other four HTML templates remain outside this new Test. General timing robustness, harder disclosure regimes and broader task/layout distributions remain future work.

## Evidence and reproduction

- [Automatic report](../outputs/three_task_v8/report/report.md), [summary JSON](../outputs/three_task_v8/report/summary.json), [all36 CSV rows](../outputs/three_task_v8/report/episodes.csv), [template/disclosure breakdown](../outputs/three_task_v8/report/disclosure_breakdown.csv).
- [Paired raw-input/action/ASK audit](../outputs/three_task_v8/report/mapping_validation.json), [frozen protocol](../outputs/three_task_v8/frozen_manifest.json), [dataset audit](../data/three_task_v8/r2/audit.json).
- `outputs/three_task_v8/test_runs/<sample>__<method>/` retains actual public states, every API attempt, model plan, physical result/events/checkpoints, final physical observation, evaluator and scene/final PNGs. All initial paired public inputs match; Gate/Planner stage payloads recompute exactly and ASK freezes physics.
- Nine actual recordings were selected before Test: first undisclosed layout per template, all three methods. [MP4 downloads](../presentation/three_task_v8/README.md). Other episodes have actual traces/PNGs, not invented videos.
- [Ready-to-use summary plot](../outputs/three_task_v8/report/benchmark_summary.png), [paired outcomes](../outputs/three_task_v8/report/paired_outcomes.png), [exploratory timing plot](../outputs/three_task_v8/report/clarification_timing.png).
- Local read-only results gallery http://127.0.0.1:8900/. Real Chrome desktop/mobile checks decoded all9 MP4s, found no JS errors/overflow and added no model requests.
- Baseline350/final358 offline tests passed. All2,709 protected existing files including defaults, frozen data/source/configs, old results and the user-modified PPT remain hash-identical.

Actual commands used: `python scripts/three_task_data.py --revision r2`; `python scripts/three_task_oracle.py --revision r2`; `python -m pytest -q`; `python scripts/three_task_benchmark.py freeze --revision r2`; `python scripts/three_task_benchmark.py run --live`; `python scripts/three_task_report.py --export-media`; `python scripts/three_task_gallery.py --serve --port8900`; `node scripts/three_task_browser_check.mjs`. Python commands use `.venv/bin/python`; Node uses the existing bundled runtime. `requirements-three-task-v8.txt` pins the additional plotting dependency; core dependencies remain unchanged. Paid commands refuse to overwrite a study, and frozen source/dataset/config hashes are checked before each episode.
