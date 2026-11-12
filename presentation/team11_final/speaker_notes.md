# Team 11 — When2Ask speaker notes

Liang Junyi and Yang Haocheng

English script: 1038 words. Slide schedule: 9:30, including a separate 22.2-second recorded demo. The remaining 30 seconds are a buffer.

Evidence paragraphs are not spoken. Start the video on slide 9 and let it finish; its duration is already included.

## Slide 1 — When2Ask

0:00–0:15 (15 seconds)

Hi everyone. We are Team Eleven, Liang Junyi and Yang Haocheng. Our project, When2Ask, benchmarks when a robot should ask for clarification and when it can continue.

<details><summary>Evidence and cautions (not spoken)</summary>

Team number and names supplied directly by the team.

</details>

## Slide 2 — Problem & Motivation

0:15–1:20 (65 seconds)

As we learned in class, conversational large language models have strong zero-shot capabilities, making it easy to build agents for new tasks. However, response speed and inference cost are important factors when we call these models repeatedly. Our project brings that trade-off into robotic clarification. Consider this instruction: open the box, bring my chosen item, and replace the lid. If the user never specified the item, even a strong model cannot know the preference. Guessing risks a wrong choice. Asking immediately can interrupt useful work, because opening the box is already allowed. We therefore benchmark whether a specialized judgment model can decide when to ask, while keeping task reliability and reducing decision overhead.

<details><summary>Evidence and cautions (not spoken)</summary>

outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json. Motivation distinguishes prompting without task-specific training from unseen-template generalization. No BERT baseline. Vendor describes parallel probability outputs: https://typesafe.ai/blog/introducing-system-one-models-and-jev . Vendor speed multipliers are not our results. Classroom connection paraphrases the user-supplied lecture description; no invented quotation or slide attribution.

</details>

## Slide 3 — Approach & Implementation

1:20–2:20 (60 seconds)

This diagram shows the implemented execution loop. The public state contains the instruction, current observation and public history. A gate chooses ASK or CONTINUE before the planner runs. On the orange branch, DeepSeek generates a question. The simulator, or a human in the HTML console, answers it, and the answer updates public history. The physical world stays paused. On the blue branch, the shared DeepSeek planner selects a robot skill. Panda executes it using inverse kinematics and our documented near-range constraint grasp, then observes the result. Only the action planner can return DONE. The independent evaluator checks the actual world and task order. Hidden preferences stay outside the gate and planner.

<details><summary>Evidence and cautions (not spoken)</summary>

outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json. Planner v6; compact public gate view v7; deepseek-flash non-thinking JSON; returned Jev jev-1.14.0. Parallel outputs are the provider's architecture description: https://typesafe.ai/blog/introducing-system-one-models-and-jev . No task-specific weight training or BERT comparison. Same-source implementation: research_runner, public protocol, user simulator, skills and physical evaluator. The frozen benchmark uses simulator answers; HTML supports human answers separately.

</details>

## Slide 4 — Benchmark Task Design

2:20–3:25 (65 seconds)

The benchmark creates three different clarification situations. Buffer exchange requires swapping two occupied slots through a temporary pad. If the permitted pad is unknown, the first move needs a user preference. Retrieve and restore allows useful progress first: open the box, ask which item to deliver, retrieve it, and reclose the box. Occlusion inspection tests a different kind of uncertainty. The robot must move the screen, inspect a label and report the measured code. That is an observable world fact, so asking the user should not replace the required inspection. Public task dependencies define the order in every case. Fully disclosed controls test whether gates avoid unnecessary questions. These structures test when to ask, rather than simply whether a robot can ask.

<details><summary>Evidence and cautions (not spoken)</summary>

data/three_task_v8/r2/{dev,test}.jsonl; public task DAGs. Inspection DAG: clear_screen, inspect_label, report_code; screen remains parked. Conceptual regimes are not a preregistered numerical timing metric.

</details>

## Slide 5 — Dataset Construction & Physical Validation

3:25–4:35 (70 seconds)

Each generated sample combines a layout, instruction, public dependency graph and private preference. We split by base physical layout, so preference changes and wording variants cannot cross Development and Test. This version has twenty-four Development samples from six groups, and twelve Test samples from twelve independent groups, four per task. Both partitions balance zero and one initially unknown slot. We also balance correct-choice candidate order and exclude previously debugged layouts from Test. Before online evaluation, a deterministic oracle executes every sample using the real robot skills. An independent evaluator checks footprints, support, stability, release and required task order. All thirty-six feasibility executions passed. The oracle can access private preferences to check feasibility, but the models never receive its actions or evaluation labels.

<details><summary>Evidence and cautions (not spoken)</summary>

data/three_task_v8/r2/audit.json; outputs/three_task_v8/oracle_r2/summary.json. Separate from older 32 Dev / 128 Test benchmark. outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json.

</details>

## Slide 6 — Three Methods, One Shared Planner

4:35–5:25 (50 seconds)

We compare three methods under the same task and execution conditions. LLM-NoAsk skips the gate and never asks. DeepSeek must act from public information and may guess. LLM-Gate uses DeepSeek to generate an ASK-or-CONTINUE decision. Jev-Gate uses a Noul probability with a frozen threshold of zero point five. Jev returns typed probabilities instead of autoregressive answer text, motivating faster decisions. Both gates receive the same compact public state. All methods share the DeepSeek action planner, skills, evaluator and budgets. Both asking methods share the question planner and simulator. We froze models, prompts and threshold before Test, and reset the environment independently for every method.

<details><summary>Evidence and cautions (not spoken)</summary>

outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json. Planner v6; compact public gate view v7; deepseek-flash non-thinking JSON; returned Jev jev-1.14.0. Parallel outputs are the provider's architecture description: https://typesafe.ai/blog/introducing-system-one-models-and-jev . No task-specific weight training or BERT comparison.

</details>

## Slide 7 — Results: Success & Clarification Burden

5:25–6:25 (60 seconds)

We evaluated twelve held-out layout groups across three methods: thirty-six real API and PyBullet episodes. NoAsk succeeded in ten out of twelve, while both gates succeeded in all twelve. Its two failures came from guessing the wrong buffer or requested item. The evaluator used the same physical criteria for every method; skipping questions did not automatically count as failure. Burden counts distinct requested preference slots, charging repeated questions again. Both gates requested four slots in total, or one third per episode. Success and burden alone cannot tell us whether a question came too early, which is why we also inspect the saved execution order. These are observed results from a small study, not proof of general superiority.

<details><summary>Evidence and cautions (not spoken)</summary>

outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json. Genuine private preference subset excludes observable inspection codes: buffer + retrieval undisclosed cases, n=4. Whole API totals 57.9066 / 105.4084 / 78.5606 seconds; 25.4703% observed reduction Jev vs LLM-Gate. Small samples, no significance claim.

</details>

## Slide 8 — Results: Speed & Estimated API Cost

6:25–7:30 (65 seconds)

Speed has two scopes here. Mean gate API response was eight hundred and fifteen milliseconds for DeepSeek and two hundred and ninety-five for Jev, about two point eight times faster. These calls follow different trajectories, not identical test inputs. Across twelve episodes per method, cumulative API latency was fifty-eight seconds for NoAsk, one hundred and five for LLM-Gate, and seventy-nine for Jev-Gate. That excludes robot execution time. Estimated total API cost was about one point one cents, one point eight five cents, and one point seven eight cents, respectively. We apply current public rates to actual usage, including cache hits. These are estimates, not invoices. Jev's estimated total saving over LLM-Gate is only three point seven percent. NoAsk remains fastest and cheapest, with lower observed reliability.

<details><summary>Evidence and cautions (not spoken)</summary>

Read-only derivation: presentation/final_benchmark_cost/analysis/cost_report.json. Current rates verified 2026-11-12: https://api-docs.deepseek.com/quick_start/pricing/ and https://docs.typesafe.ai/models. These are current-price estimates, not invoices. Gate means 815.114 ms / 53 calls and 294.803 ms / 54 calls. Total USD 0.010921350 / 0.018457914 / 0.017770626. Estimated saving 3.7235%. DeepSeek off-peak USD/M input cache hit .003, miss .15, output .6; Jev input .042, output free. Request timestamps 2026-11-11 13:53:34–13:55:36 UTC. Cache and trajectory mix limit generalization.

</details>

## Slide 9 — Results & Demonstration: Real Execution

7:30–8:45 (75 seconds)

Timing can differ even when success and burden match. On two retrieval tasks with an undisclosed item, LLM-Gate asked before opening, while Jev opened first and then asked. This is exploratory trace analysis. Here is one actual Jev episode. A score of zero point eleven leads to CONTINUE and the robot opens the box. The score then becomes zero point sixty-two. It asks which item to retrieve, and the simulator selects the block. The robot delivers it and replaces the lid. The replay retains a rejected lid move before the correct cover action repairs it. Both motion and flow highlights follow the same recorded frames.

**Demo cue:** allow the full 22.2-second clip. A separate playback hold fits inside this slide’s 75 seconds.

<details><summary>Evidence and cautions (not spoken)</summary>

Play the 22.2-second embedded replay during the final two spoken sentences, or pause narration to watch. The 75-second allocation permits a separate playback hold. outputs/three_task_v8/test_runs/t8_r2_test_1_04_1__jev_gate/episode.json; existing 164-frame replay and mapping. No new model request or invented inference timing. First-ASK comparison is exploratory post-Test analysis, not a preregistered optimal policy.

</details>

## Slide 10 — Discussion & Conclusions

8:45–9:30 (45 seconds)

Our benchmark separates asking first, progressing before asking, and inspecting instead of asking. We combine layout isolation, physical validation and shared planning. In this small study, both gates improved observed reliability over guessing. Jev reduced gate response time, while its estimated total cost advantage was modest. Limitations include twelve Test groups, binary choices, assisted grasping and sensitivity to prompts, thresholds and API conditions. Next, we will expand independent layouts, pre-register timing metrics and repeat the comparisons. The takeaway is that clarification should depend on what information blocks useful progress. Thank you.

<details><summary>Evidence and cautions (not spoken)</summary>

outputs/three_task_v8/report/summary.json; outputs/three_task_v8/frozen_manifest.json. Limits: 12 independent Test groups, binary choices, assisted grasping, three rejected commands repaired; no significance, same-state speed, BERT or unseen-template generalization claim. Read-only derivation: presentation/final_benchmark_cost/analysis/cost_report.json. Current rates verified 2026-11-12: https://api-docs.deepseek.com/quick_start/pricing/ and https://docs.typesafe.ai/models. These are current-price estimates, not invoices.

</details>
