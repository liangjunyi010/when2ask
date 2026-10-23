# When2Ask milestone speaker notes

User-provided script, preserved verbatim without Markdown emphasis. 243 spoken words. Target total: 115–125 seconds. Source notes below are not spoken.

## Slide 1 — When2Ask: System & Real Demo

Target: 55–60 seconds (120 words).

Hi everyone. Our project is When2Ask, and we're studying a simple question: when should a robot ask for clarification, and when should it continue acting?

Imagine being told to pack a cup, a block, and a lid, but only the cup choice is specified. Asking everything immediately may interrupt the user, while guessing could lead to mistakes.

Here is our working PyBullet Panda demo.

Jev first gives a clarification score of 0.14, so the robot continues and packs the known cup.

After that, the score rises to 0.70, so the robot asks which block and lid to use before finishing the task.

The flowchart on the right follows the robot's actual execution, showing how decisions and physical actions are connected.

Source notes: Source: outputs/phase2_live/paired_v2/validation_002/jev_gate/{episode.json,evaluation.json,api_attempts.jsonl,demo.gif}. Frame-indexed HTML replay: presentation/milestone/web/timeline.json. Inference instants within recorded frames were not captured and are not reconstructed. The 11.88 s highlight compresses only display time, preserving source order and synchronized left/right states. Actual PyBullet Panda execution uses a documented constraint grasp.

## Slide 2 — Benchmark & Preliminary Results

Target: 60–65 seconds (123 words).

Beyond the demo, we've built a procedurally generated benchmark with two robotic task types: packing and covering, and placing objects into selected containers.

We currently have 32 development samples and 128 held-out test samples. All 160 passed physical feasibility checks, and 96 automated tests passed.

We've also integrated DeepSeek and Jev, and compared three methods: NoAsk, LLM-Gate, and Jev-Gate.

In our preliminary evaluation on eight development scenarios, NoAsk succeeded in five, while both gate methods succeeded in seven.

Jev achieved similar clarification burden, with lower total API latency: about 40 seconds, compared with 58 seconds for LLM-Gate.

These are still preliminary results. Our next step is to evaluate all three methods on the held-out test set and analyze their clarification timing.

Thank you!

Source notes: Sources: docs/phase3/dev_report.md; outputs/phase3/pytest_final.xml; outputs/phase3_live/dev/*/{episode.json,evaluation.json,api_attempts.jsonl}; frozen configs/frozen_test.yaml. All table values are rounded from original episode totals. LLM-NoAsk: 5/8, burden 0/8, latency 24.350076 s. LLM-Gate: 7/8, burden 12/8, latency 58.213124 s. Jev-Gate 0.5: 7/8, burden 11/8, latency 39.658448 s. Only two preference triples per template occur in the selected online subset; all selected blocks are green and all pack/cover lids black. Formal Test model calls remain zero. The 96-test figure describes the preserved Phase 3 milestone snapshot; separate replay tests are additional.
