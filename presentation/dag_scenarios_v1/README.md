# Real Panda clips for twenty DAG task instances

The [gallery](../../docs/presentation_dag_scenarios_v1.md) uses these twenty seekable H.264 MP4 recordings. Each is a direct compression of a completed real PyBullet recording from `outputs/presentation_dag_v1/live/`, including the original ASK/User Simulator display frames. No synthetic robot animation, event reordering or invented model response is used.

Media are encoded at the original display speed; the gallery defaults to 2× playback. The static DAG alongside a clip states the task's public dependencies. It does not claim to be synchronized stage highlighting.

- `media/dag_demo_03.mp4`: Jev missed clarification, task failed.
- `media/dag_demo_06.mp4`: Jev asked early, then completed the pack-and-cover task.
- `media/dag_demo_15.mp4`: one destination answer reused for two placements.
- `media/dag_demo_18.mp4`: all choices unknown, Jev asked, then succeeded.

All clips, including failures, are retained. `media_manifest.json` records the source GIF SHA-256, frame count, duration, resulting MP4 hash and ffprobe metadata. The twenty clips total about 11 MB and are suitable for downloading from this private repository or inserting into a presentation.
