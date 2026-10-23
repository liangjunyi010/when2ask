# Phase 3 Dev calibration report

This is an engineering pilot using real DeepSeek/Jev outputs and real Panda/PyBullet execution. There are no mock rows in the experiment results. Formal Test API episodes: **0**.

## Dataset and physical verification

| Partition | Samples | Base layout groups | Pack/cover | Two containers | Missing 0/1/2/3 |
|---|---|---|---|---|---|
| dev | 32 | 8 | 16 | 16 | 8/8/8/8 |
| test | 128 | 16 | 64 | 64 | 32/32/32/32 |

All aliases, hidden choices, wording and millimeter perturbations of one physical layout stay in its partition. Dev/Test can share preference combinations. Test uses held-out container arrangements; minimum cross-split maximum-matched container distance is 0.1011 m. Candidate-list, lexical-ID, observation-list and spatial-rank answer histograms cover both ranks; counts are in the frozen data audit. This checks deterministic shortcuts, not every possible statistical correlation.

| Template | Dev actual oracle | Test actual oracle | Combined |
|---|---|---|---|
| pack_and_cover | 16/16 | 64/64 | 80/80 |
| place_into_selected_containers | 16/16 | 64/64 | 80/80 |

All 160 samples also passed separate all-pairs initial penetration and private/public checks. The old 25-scene oracle passed 25/25 before extension and 25/25 on the final controller. All 194 previously published historical artifact hashes stayed unchanged. The new containers have a bottom and four physical walls; scoring retains full AABBs, actual support contact, velocity stability, release, unselected-object exclusion and publicly specified DAG order.

## Pre-registered Dev comparison

One sample from each of all 8 Dev groups was selected before any Phase 3 authenticated request. Each template contributes one case at each disclosure level. Five conditions independently reset physics and history; threshold runs are fresh episodes, not replayed decisions. Order is randomized/interleaved with seed 20261023. Runtime, prompt, dataset and budget hashes were registered at source commit `9cefbd3905cc9f3fcdfef23244de0eba8f08d693`. The shared planner, question/action prompts, physics, user simulator, evaluator and per-episode budgets are identical.

| Condition | Task success | Burden total (mean) | DeepSeek tokens | Jev tokens | API latency total s |
|---|---|---|---|---|---|
| llm_noask | 5/8 (62.5%) | 0 (0.000) | 42,022 | — | 24.350 |
| llm_gate | 7/8 (87.5%) | 12 (1.500) | 99,034 | — | 58.213 |
| jev_gate@0.3 | 7/8 (87.5%) | 11 (1.375) | 50,748 | 66,152 | 40.307 |
| jev_gate@0.5 | 7/8 (87.5%) | 11 (1.375) | 50,748 | 66,152 | 39.658 |
| jev_gate@0.7 | 6/8 (75.0%) | 7 (0.875) | 46,959 | 58,924 | 35.821 |

Tokens above are actual input+output, kept separate by backend and never converted into comparable dollar cost. Per-attempt/CSV input and output remain separate. Failed format repairs count as inference. Latency is cumulative agent API time; physics/rendering are in episode wall time. Discovery/revalidation cost is excluded from condition rows and included in the global session.

| Condition | DeepSeek in/out | Jev in/out | SR group Wilson 95% |
|---|---|---|---|
| llm_noask | 41,354/668 | — | [0.306, 0.863] |
| llm_gate | 97,812/1,222 | — | [0.529, 0.978] |
| jev_gate@0.3 | 49,801/947 | 65,360/792 | [0.529, 0.978] |
| jev_gate@0.5 | 49,801/947 | 65,360/792 | [0.529, 0.978] |
| jev_gate@0.7 | 46,150/809 | 58,204/720 | [0.409, 0.929] |

### Paired sample results

| Sample | Task | Missing | llm_noask | llm_gate | jev_gate@0.3 | jev_gate@0.5 | jev_gate@0.7 |
|---|---|---|---|---|---|---|---|
| v3_dev_000 | pack_and_cover | 0 | S/0 | S/0 | S/0 | S/0 | S/0 |
| v3_dev_005 | pack_and_cover | 1 | F/0 | F/0 | F/0 | F/0 | F/0 |
| v3_dev_010 | pack_and_cover | 2 | F/0 | S/2 | S/2 | S/2 | F/0 |
| v3_dev_015 | pack_and_cover | 3 | F/0 | S/3 | S/3 | S/3 | S/3 |
| v3_dev_016 | place_into_selected_containers | 0 | S/0 | S/1 | S/0 | S/0 | S/0 |
| v3_dev_021 | place_into_selected_containers | 1 | S/0 | S/1 | S/1 | S/1 | S/1 |
| v3_dev_026 | place_into_selected_containers | 2 | S/0 | S/2 | S/2 | S/2 | S/0 |
| v3_dev_031 | place_into_selected_containers | 3 | S/0 | S/3 | S/3 | S/3 | S/3 |

Cells are success/failure and burden. Pairing is retained by physical group in paired_groups.json. Per-condition denominator is 8 independent groups, not 32 Dev variants or 40 independent scenes.

## Threshold sensitivity and freeze

Selected threshold: **0.5**. No adequately supported alternative; retain predeclared default.

Thresholds 0.3 and 0.5 produced the same paired success/burden outcomes and token counts on these eight cases, from separate actual HTTP calls and separately initialized worlds. Their observed latency difference does not satisfy the predeclared 10%/paired-interval rule. Threshold 0.7 saved requests/slots partly by failing to clarify, and lost one success. That is not an efficiency win at comparable success.

The predeclared 20,000-draw paired group bootstrap (seed 4278) uses 97.5% intervals for two alternative-vs-default comparisons. Full per-group differences and intervals are in threshold_selection.json. Eight groups are too few to establish a uniquely optimal threshold or generalization; default retention is a conservative policy, not evidence that 0.5 is optimal.

### Coverage limitation discovered in the selected subset

The complete Dev and Test partitions include all 8 normalized preference triples per template. The predeclared one-variant-per-group online subset covers only 2 triples per template: all selected blocks are green, all selected pack/cover lids black, and all selected cup destinations container_b. This results from the deterministic variant/truth schedule, not from inspecting model performance. It is an important limitation of this small calibration subset and can make NoAsk luck/defaults look favorable. We did not replace runs after observing outcomes or exceed the 40-episode cap. See truth_coverage_audit.json for exact counts. A future independent Dev replication should stratify truth combinations as well as layout/template/disclosure before any new calls. The frozen Test contains every triple within each of its 16 groups; it was not adjusted using Dev failures.

## Errors and clarification timing

- llm_noask: early ASK 0, blocked CONTINUE 19, redundant requested slots 0, repeated requested slots 0, physical skill failures 0, schema-error attempts 0.
- llm_gate: early ASK 1, blocked CONTINUE 2, redundant requested slots 1, repeated requested slots 0, physical skill failures 0, schema-error attempts 0.
- jev_gate@0.3: early ASK 0, blocked CONTINUE 2, redundant requested slots 0, repeated requested slots 0, physical skill failures 0, schema-error attempts 0.
- jev_gate@0.5: early ASK 0, blocked CONTINUE 2, redundant requested slots 0, repeated requested slots 0, physical skill failures 0, schema-error attempts 0.
- jev_gate@0.7: early ASK 0, blocked CONTINUE 8, redundant requested slots 0, repeated requested slots 0, physical skill failures 0, schema-error attempts 2.

Timing labels are public-only diagnostics, never fed to a model or used as success labels. NoAsk blocked CONTINUE is expected by design. Recovery states may be left unclassified.

- `v3_dev_005`: both object choices are known initially, so packing them first is appropriate. After packing, the lid remains unknown. LLM-Gate and every Jev threshold nevertheless continued and chose the wrong lid (Jev probabilities around 0.1). All physical skills succeeded but the independent evaluator rejected the wrong user preference. This is a late-clarification failure which a threshold sweep alone did not fix.
- `v3_dev_016 / llm_gate`: all choices were already disclosed, but an initial ASK redundantly requested cup_destination, charging one extra slot. The task eventually succeeded. Jev runs on this case completed without that request.
- `v3_dev_010 / Jev 0.7`: initial p=0.56 and next p=0.54 were below 0.7, so the planner guessed objects. At the lid step it twice emitted pick_place(lid, box, inside), violating the legal action schema. The single allowed repair retry also failed; the episode stopped with a SchemaError and was scored on its actual incomplete/wrong physical state. Both billed responses and usage remain in the logs.
- NoAsk successes on unknown choices are retained, including `v3_dev_026`. It was not forced to fail. No private preference was supplied to any planner request.

Across all 40 episodes, 99/99 executed skills passed their actual geometric placement check. Task failure remains distinct from skill failure. There were 1 retried inference and 2 schema-error attempts, 0 authentication/network/API errors, and 0 unknown inference-usage attempts. ASK invariance and paired initial payload equality passed the independent evidence audit.

## API budget, models and tests

Authenticated requests: **293/600**; new online episodes: **40/40**. The request IDs are unique and contiguous. 4 requests are model discovery/revalidation, the remaining 289 are full-episode inference including format repair. Configured/returned DeepSeek is deepseek-flash/deepseek-flash; Jev is jev-latest/jev-1.14.0. DeepSeek returns an alias, so an immutable underlying build is unavailable. Both providers returned real usage and measured latency during revalidation. Credentials stayed in ignored 0600 .env, outside source/logs/commits.

Original tests: 66/66 before changes. Final tests: 96 passed. JUnit and evidence audit are in outputs/phase3/pytest_final.xml and evidence.json. Offline pytest blocks urllib network I/O; synthetic adapter/threshold unit tests are labeled tests and never included in these tables. No friction-only grasp, hardware test, general motion planner or confirmatory model-quality experiment is claimed.

## Frozen Test and next execution plan

| Artifact | SHA-256 |
|---|---|
| Dev dataset | 0b1a197217a1896604bdf10be6d7572322255ede7607d87639e81678b11b1fb4 |
| Test dataset | e44b6dfc1980014ddf8628fafdde099cbc968d18e62e6618d62d0385cd7bcccb |
| Frozen Test YAML | 897968817e70f47f16c0d75a2911c635a44722535a7093f8e4f9be608d90bcc0 |
| Dev manifest | 12db2fdcee3c4baf5cd88532caa3c26539705fd78dd304ed92000d027da1daff |

The frozen YAML (JSON syntax, valid YAML 1.2) and companion manifest record configured/returned models, threshold, prompt hashes, planner parameters, skill/evaluator/source versions, data hashes, code commit and retry/budget policy. No Test model call has occurred. Changed parameters or model versions require a distinct experiment ID; unexpected returned models must stop the run.

Next formal Test plan: 128 samples ×3 methods =384 fresh paired episodes, 16 cluster/group units. Interleave all methods with seed 427804. Based on Dev means (3.5 NoAsk, 8.5 LLM-Gate, 8.25 Jev-0.5 calls per episode), nominal request planning is about 2,592 episode calls plus discovery and retries; this is a forecast, not a guarantee. A separate initially proposed 5,000-request study cap gives headroom and must stop rather than silently expand. Absolute 64-attempt per-episode limits sum to 24,576, so a global 5,000 ceiling can terminate before all jobs in a bad run. Run a bounded predeclared canary, retain failures, then continue the same frozen configuration; never tune on Test outcomes. Additional Dev replication, if desired, is separately versioned and must precede any replacement Test configuration.

## Reproduction and evidence paths

```bash
cd ~/Desktop/CS4278/when2ask
source .venv/bin/activate
python -m when2ask study oracle --partition dev
python -m when2ask study oracle --partition test
python -m when2ask study check-data
python -m when2ask study freeze-data
python -m when2ask study plan
python -m when2ask study smoke --live
python -m when2ask study dev --live --record-first
python -m when2ask study report
python -m when2ask study freeze-test
python scripts/build_phase3_report.py
python -m pytest -q --junitxml=outputs/phase3/pytest_final.xml
python scripts/verify_phase3.py
python scripts/secret_scan.py
```

Generation was run once with seed 4278; `study generate --seed 4278` now refuses to overwrite the frozen files. Oracle commands validate matching cached evidence and reject changed inputs. The completed smoke/Dev commands resume matching records without new model calls; the 40-episode ceiling is exhausted. Use a separately versioned/approved session for future inference.

- Dataset/scenes: data/phase3/; physics oracles: outputs/phase3/oracle/{dev,test}/.
- Raw live public states, requests/responses, dense physics, evaluation and PNGs: outputs/phase3_live/dev/.
- CSV/JSON metrics and paired differences: outputs/phase3/report/.
- Actual two-container GIF: outputs/phase3_live/dev/v3_dev_016__llm_gate/demo.gif (315 encoded TinyRenderer frames, local/ignored).
- Existing `python demo.py --mode ask --gui` and `--mode noask --gui` remain available.

## GitHub publication

[Phase 3 PR #2](https://github.com/liangjunyi010/when2ask/pull/2) is OPEN against `feat/benchmark-apis`. Repository privacy was verified as isPrivate=true. The verified uploaded experiment payload is `10ce0c8a5d77da65f61cf801e18b09a1dd78bae0`; later publication-only documentation commits are checked again after push. Original PR #1 remains OPEN with its original head. No PR was merged or force-pushed.
