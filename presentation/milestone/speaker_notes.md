# When2Ask milestone speaker notes

Approximately 2 minutes at 140–155 words per minute (294 spoken words). Sources below are not spoken.

## Slide 1 (about 60 seconds)

When2Ask asks a simple question: when should a robot ask for clarification, and when can it already make useful progress?

This replay comes from a real recorded PyBullet episode with a Panda arm. The user has specified the blue cup, but has not yet chosen a block or a lid. Jev first returns an ASK probability of 0.14, so the shared DeepSeek planner packs the cup. Only then does Jev return 0.70, and the robot asks which block and lid to use. The simulated user answers, and the robot packs the block and covers the box.

The robot frames and highlighted flow share one recorded timeline. These are actual simulated physics actions with a documented constraint grasp, not hardware execution. An independent physical evaluator checks the final result.

The key idea is to clarify only when missing information blocks useful progress.

Source notes: Source: outputs/phase2_live/paired_v2/validation_002/jev_gate/{episode.json,evaluation.json,api_attempts.jsonl,demo.gif}. Frame-indexed HTML replay: presentation/milestone/web/timeline.json. Inference instants within recorded frames were not captured and are not reconstructed. The 19.16 s highlight compresses only display time, preserving source order and synchronized left/right states.

## Slide 2 (about 60 seconds)

The milestone system now supports two task templates: pack and cover, and placing objects into selected containers. We generated 32 Dev samples and 128 held-out Test samples, separated by base physical layout groups. All 160 passed actual physical oracle execution. The Phase 3 system also passed 96 automated tests and integrates real DeepSeek and Jev APIs.

This table shows a small Dev comparison across eight independent groups. NoAsk succeeded in five of eight cases. Both clarification gates succeeded in seven. Jev at threshold 0.5 used slightly less clarification and showed 39.66 seconds of cumulative API latency, compared with 58.21 seconds for the LLM gate. These are totals across eight episodes, not averages.

This is preliminary evidence, with limited preference coverage in the online subset. It does not establish a statistical advantage. Our next step is the frozen evaluation: 128 held-out samples, each run with all three methods. That Test has not run yet.

Source notes: Sources: docs/phase3/dev_report.md; outputs/phase3/pytest_final.xml; outputs/phase3_live/dev/*/{episode.json,evaluation.json,api_attempts.jsonl}; frozen configs/frozen_test.yaml. All table values are rounded from original episode totals. LLM-NoAsk: 5/8, burden 0/8, latency 24.350076 s. LLM-Gate: 7/8, burden 12/8, latency 58.213124 s. Jev-Gate 0.5: 7/8, burden 11/8, latency 39.658448 s. Only two preference triples per template occur in the selected online subset; all selected blocks are green and all pack/cover lids black. Formal Test model calls remain zero. The 96-test figure describes the preserved Phase 3 milestone snapshot; separate replay tests are additional.
