# Buffered exchange: independent Dev repair report

One physical layout group, adaptive Dev iterations, no held-out test or significance/ranking claim

## Original failure diagnosis

The first regression was round 2, after A had been parked on buffer_front and B had reached slot_left. The next model response moved B back to slot_right. All 13 serialized API inputs matched their saved turn payloads, and complete physical action history was present. This rules out missing history and stale controller/transport state at that point.

The original affordance list was broad schema support, not a filtered list of currently safe/progressing actions. Current contents were correct, but explicit final relations and persistent agent assumptions were not prominent. These are plausible representation/planning contributors, not access to the model's hidden reasoning.

## All retained real action probes

| Profile | Probes | Valid outputs | Goal-regressing first actions | Occupied-slot targets |
|---|---:|---:|---:|---:|
| s0p0 | 4 | 4 | 2 | 0 |
| s0p1 | 4 | 4 | 1 | 0 |
| s1p0 | 4 | 4 | 2 | 0 |
| s1p1 | 4 | 4 | 1 | 0 |
| s1p0c1 | 4 | 4 | 2 | 0 |
| s1p1c1 | 4 | 4 | 2 | 0 |
| grounded_plan_compact | 4 | 4 | 0 | 0 |
| grounded_plan_append | 4 | 4 | 0 | 0 |

`s` = append-only public summary; `p` = extra planner grounding wording; `c1` = compact physical history retaining all user dialogue. Structured-plan profiles ask the same DeepSeek planner for current locations, public final targets, a working buffer choice and a remaining action suffix.

V2 summary/prompt changes and V3 context compression did not consistently stop old-history regressions. Their negative raw outputs remain intact. V4 structured planning produced no regressing first action in its eight probes. These use four states from ONE archived trajectory; they are not independent tasks, rollout success rates, or a confirmatory ablation.

## Six complete episodes

| Case | Profile | Physical swap | Task success | Burden | Robot actions | API latency |
|---|---|---|---|---:|---:|---:|
| known_back_v1_noask | s0p0 | True | True | 0 | 3 | 3.97 s |
| known_back_v4_noask | grounded_plan_compact | True | True | 0 | 3 | 4.73 s |
| unknown_back_v4_jev | grounded_plan_compact | True | True | 1 | 3 | 7.19 s |
| unknown_back_v4_llm | grounded_plan_compact | True | True | 1 | 3 | 10.25 s |
| unknown_back_v4_noask | grounded_plan_compact | True | False | 0 | 3 | 5.09 s |
| unknown_front_v4_noask | grounded_plan_compact | True | True | 0 | 3 | 4.70 s |

The original v1 planner also completed the known-buffer control in three moves. Therefore the original failure must not be described as a universal v1 inability to swap objects. The original unknown-preference episode did loop, while the grounded Dev planner completed both unknown-preference controls mechanically. It guessed the front pad in both: the back-truth task failed preference scoring; the front-truth control succeeded. NoAsk is not forced to fail.

Only `unknown_back_v4_noask`, `unknown_back_v4_llm`, and `unknown_back_v4_jev` form a matched three-method case. They start from identical physical layout, preference and public information. Both gates asked once and succeeded; NoAsk completed the physical swap but used the wrong preferred pad. This single group supports an engineering demonstration, not a general claim that Jev outperforms LLM-Gate.

## What V4 changes, and what it does not

- Every CONTINUE first follows its Gate decision, then calls the same planner again. The planner returns a short JSON state/goal audit and remaining plan; only its first action is executed, verbatim. No cached future actions are executed before later gates.
- Grounding validation checks only publicly measured current region membership and the final targets implied by the public exchange instruction. It does not check an action against a correct next-action oracle, private pad preference or evaluator score.
- Unit tests deliberately pass a regressing action with correct grounding and confirm that the planner wrapper returns that bad action unchanged. There is no silent correction, hard-coded swap executor or action mask.
- All three new-method cases use the same structured planner, context rules and per-call output cap. Output cap increased from 160 to 400 for the structured action JSON; token/cost differences from v1 must be interpreted with that change.
- Physics, grasp guards, physical constraints, skill-step limits, task evaluator and Jev threshold 0.5 remain unchanged. No final object pose resets are introduced.
- V3/V4 were adaptive Dev amendments after observing earlier negative probes. The final six-case list was locked before any complete episode. All stages share the original 120-request / six-episode ceiling; no new budget was created.
- The existing HTML and its default v1 planner were not silently replaced. This remains an independent Dev candidate pending optional-profile integration and regression across other tasks.

## Actual usage

Total authenticated requests: 69 / 120, including 1 schema repairs. Completed episodes: 6 / 6; no formal Test API calls.
- deepseek: input 163196, output 2904, API latency 64.82 s.
- jev: input 16638, output 120, API latency 1.55 s.

Backend tokens are not added into monetary-cost claims. Replay probes and complete episodes have separate raw API logs; all inference attempts are charged. GIF ASK/USER frames are explicitly display holds for actual events, not fabricated model latency.

## Next step

Expose the grounded planner as an explicit Dev profile, generalize public grounding to the other task contracts, then run nine paired episodes: buffered exchange (must ask before choosing), retrieve/restore (known action first, ask later), and occlusion inspection (observe without asking), each with all three methods and identical per-case state/preferences. Keep planning failures separate from preference/timing failures. Freeze a new version only after that regression; do not modify the historical frozen Test configuration.

Full tests: 311 passed. All pre-existing experiment/configuration/source hashes are separately audited; the old six-task and formal Benchmark records are unchanged.
