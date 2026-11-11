# When2Ask — 10-minute presentation

Spoken script; evidence notes are separate and are not visible on slides. Video playback is included in slide 8 timing.

## Slide 1 — When2Ask

Target: 45 seconds.

When a robot receives an incomplete instruction, it has two options: ask the user, or continue with the information already available. Asking too early interrupts useful work. Guessing can produce the wrong result. Our project, When2Ask, studies that decision through a robotic benchmark. The main contribution is a controlled way to test clarification timing: tasks have explicit dependencies, some user preferences are hidden, and every proposed action is executed in PyBullet. We compare three decision mechanisms while keeping the planner and robot skills shared. Today I will focus on how we constructed the benchmark, how we kept the comparison fair, and what happened in the held-out evaluation.

Evidence (not spoken): docs/three_task_benchmark_v8.md; outputs/three_task_v8/report/summary.json; hero image from oracle_r2/t8_r2_test_0_05_1/scene.png.

## Slide 2 — What makes one benchmark sample?

Target: 65 seconds.

Each sample combines four things: a physical layout and seed, a task instruction, a dependency graph, and a private user preference with a specified disclosure level. Here the robot must open a box, retrieve the user-selected item, and replace the lid. The arrows show necessary task order. If the item choice is missing, the robot cannot select the right item yet, but opening the box is still useful and already authorized. The agent only receives the public instruction, visible scene state, and its own public interaction history. The true preference, evaluator verdict, and physical oracle trajectory remain separate. This distinction matters because a benchmark would be misleading if the gate could read the answer or a private label saying that it should ask.

Evidence (not spoken): data/three_task_v8/r2/test.jsonl; src/when2ask/ task/public serialization; immutable source commit in frozen_manifest.json.

## Slide 3 — Three tasks, three clarification regimes

Target: 80 seconds.

We designed three task templates to create different reasons to ask or continue. First, buffer exchange: two occupied slots must swap their contents through one temporary pad. The user has to choose the permitted pad, so an undisclosed preference blocks the first useful move. Second, retrieve and restore: the robot can open the box immediately, then ask which item to deliver, and finally reclose it. This tests whether a gate can postpone a question until it actually blocks progress. Third, occlusion inspection: a hidden world fact is available through a required inspection step. The robot should uncover, inspect, and report the measured code, rather than asking the user for an observable fact. We also include fully disclosed controls. Together these cases distinguish immediate clarification, delayed clarification, and useful observation without clarification. They are different task structures, rather than just color changes.

Evidence (not spoken): data/three_task_v8/r2/{dev,test}.jsonl; public task DAGs; outputs/three_task_v8/report/disclosure_breakdown.csv. Public-support timing categories are conceptual; exact event counts on slide8 are exploratory post-Test diagnostics.

## Slide 4 — Build layouts first, then split by group

Target: 70 seconds.

We generate physical layouts first, assign each layout a group, and split those groups before adding preference and instruction variants. Variants of the same base scene never cross the development and Test boundary. Development contains twenty-four samples from six layouts. Test contains twelve samples from twelve separate layouts, four per task. Both partitions balance zero and one initially unknown slot, and the correct alternatives are balanced across candidate order. Previously debugged layouts are excluded from Test, with geometry-based checks for near duplicates. Finally, a deterministic oracle executes every sample using the actual robot skills and the independent physical evaluator. All thirty-six executions passed. Those are thirty-six feasibility checks, not thirty-six independent layouts. The oracle can use private preferences to test feasibility; its actions are never given to the models.

Evidence (not spoken): data/three_task_v8/r2/audit.json; outputs/three_task_v8/oracle_r2/summary.json; outputs/three_task_v8/frozen_manifest.json. Dev6+Test12=18 independent base layouts. Original 32Dev/128Test benchmark is a separate preserved version, not included here.

## Slide 5 — Compare gates while keeping the planner fixed

Target: 60 seconds.

The three methods differ mainly in the gate. NoAsk skips gating and always proceeds to action planning. LLM-Gate asks DeepSeek to choose ASK or CONTINUE. Jev-Gate uses the Noul clarification score with a frozen threshold of zero point five. Both gates receive the same compact public representation. After the decision, all methods share the same DeepSeek action planner and, where applicable, the same question generator. A gate cannot directly issue robot actions, and it runs before the planner. The environments, user simulator, evaluator, and episode budgets are shared. Every method starts with a fresh world and history for the same sample. The source, prompts, model settings, run list, and threshold were frozen before these Test runs; we did not rerun or exclude unsuccessful episodes.

Evidence (not spoken): outputs/three_task_v8/frozen_manifest.json; outputs/three_task_v8/report/mapping_validation.json; deepseek-flash; jev-1.14.0; shared v7 compact gate view and v6 planner.

## Slide 6 — Score the world, not the model’s claim

Target: 60 seconds.

We measure success, clarification burden, and inference cost. Success comes from the independent physical evaluator, not from the planner saying DONE. It checks the full object footprint, physical support and stability, lid coverage where required, release from the robot, and task order. Burden counts distinct preference slots in each question; asking again costs again. Backend inference is recorded as separate token totals and cumulative API latency, including errors and retries. We do not add Jev and DeepSeek tokens together as if they had the same dollar value. The robot uses inverse kinematics and an explicitly documented near-range constraint grasp. It really approaches and transports the object, and after release PyBullet controls the object. This is a reproducible manipulation test, while remaining simpler than an unrestricted real-robot setting.

Evidence (not spoken): outputs/three_task_v8/report/summary.json; task6_geometry_contact_evidence_v1 evaluator; episode execution logs grasp_mode=constraint. No final-pose resets used as successful skills.

## Slide 7 — Both gates completed all 12 held-out tasks

Target: 80 seconds.

Here are the actual held-out outcomes: twelve independent layouts, paired across three methods, for thirty-six online episodes. NoAsk completed ten out of twelve. Both clarification gates completed all twelve. NoAsk made two wrong guesses: a buffer choice and a retrieval item. It was scored from the same physical criteria, not marked wrong simply for skipping questions. Both gates requested four preference slots in total, averaging one third of a slot per episode. Cumulative API latency was about fifty-eight seconds for NoAsk, one hundred and five seconds for LLM-Gate, and seventy-nine seconds for Jev-Gate, over twelve episodes each. These are inference totals, not average task duration or robot wall time. Jev had lower observed latency than LLM-Gate in this run, but we do not claim statistical superiority from twelve groups. Three rejected skill commands were repaired by later real actions; no failures were removed from the evaluation.

Evidence (not spoken): outputs/three_task_v8/report/summary.json; methods.csv; episodes.json. Wilson group intervals: NoAsk55.2–95.3%; gates75.7–100%. Exploratory paired bootstrap gate-minus-NoAsk interval includes0. Requests262; API/schema errors0; retries0. Rejected commands: LLM1,Jev2.

## Slide 8 — Clarification timing changes the execution order

Target: 75 seconds.

Task success alone does not tell us when a question was asked. On the two retrieval cases with an undisclosed item, LLM-Gate asked before opening. Jev first opened the box, then asked. The user burden and final success were the same, but useful physical progress happened earlier. This is an exploratory analysis of the saved traces, not a pre-registered optimal-timing score. The video shows one of those actual Jev episodes. The initial score is zero point eleven, so the robot opens the lid. Then the score is zero point sixty-two, and it asks which item to retrieve. The user simulator selects the block. The robot delivers it and restores the lid. One generic lid move is rejected before a proper cover action repairs it; the replay keeps that event visible. Motion is accelerated three times, with readable question holds, all driven by the recorded frame order.

Evidence (not spoken): outputs/three_task_v8/test_runs/t8_r2_test_1_04_1__jev_gate/episode.json and demo.gif. Original probabilities0.11/0.62; no new API calls. Source recordings are simulation/display time, not inference wall time. Exploratory first-ASK analysis from paired unknown retrieval groups; no private theta used in public-DAG support diagnostic.

## Slide 9 — A benchmark for asking at the right time

Target: 50 seconds.

The main outcome is a benchmark that distinguishes three situations: ask before acting, make supported progress before asking, and observe instead of asking. It combines layout-group separation, physical feasibility checks, shared planning, and auditable model interactions. The current evidence is encouraging, but limited: only twelve independent Test layouts, binary preference alternatives, simple geometry, and assisted grasping. We also observed three rejected commands that required physical repair. The next step is to scale independently generated layouts and the number of unknown preferences, pre-register timing labels, and test robustness to wording and observation changes. Any new tuning should use a new development version, leaving this Test result intact. Our goal is not to make the robot ask more. It is to clarify when missing information blocks useful progress. Thank you.

Evidence (not spoken): docs/three_task_benchmark_v8.md; outputs/three_task_v8/report/test_validation.json reports358 passed final project tests. Test12groups; binaryslot alternatives; 3rejectedcommands repaired. Other legacy templates and original128Test not part of this evaluation.
