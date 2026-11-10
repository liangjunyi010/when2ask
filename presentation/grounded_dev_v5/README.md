# Grounded Dev v5 — real physical recordings

Nine r2 real-model episodes, captured by PyBullet TinyRenderer during actual skills. Videos represent physical simulation time, not API/ASK wall time. Raw dialogue, model outputs and scoring are in `outputs/grounded_planner_dev_v5/live/`. No animation or fabricated motion.

| Task / method | Recording | Duration |
|---|---|---:|
| buffer_exchange__jev_gate | [MP4](media/buffer_exchange__jev_gate.mp4) | 102.2s |
| buffer_exchange__llm_gate | [MP4](media/buffer_exchange__llm_gate.mp4) | 44.8s |
| buffer_exchange__llm_noask | [MP4](media/buffer_exchange__llm_noask.mp4) | 45.0s |
| occlusion_inspection__jev_gate | [MP4](media/occlusion_inspection__jev_gate.mp4) | 15.8s |
| occlusion_inspection__llm_gate | [MP4](media/occlusion_inspection__llm_gate.mp4) | 15.8s |
| occlusion_inspection__llm_noask | [MP4](media/occlusion_inspection__llm_noask.mp4) | 15.8s |
| retrieve_restore__jev_gate | [MP4](media/retrieve_restore__jev_gate.mp4) | 175.0s |
| retrieve_restore__llm_gate | [MP4](media/retrieve_restore__llm_gate.mp4) | 175.0s |
| retrieve_restore__llm_noask | [MP4](media/retrieve_restore__llm_noask.mp4) | 173.8s |

Total media size: 7.2 MB. Preserve failures: retrieval repeatedly opens/closes the lid and ends at the action limit. Read the full [study report](../../docs/grounded_planner_dev_v5.md).
