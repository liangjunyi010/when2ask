# Six new tasks — real execution clips

`media/` contains six H.264 MP4s compressed directly from the actual worker-rendered GIFs. They include both failed NoAsk cases; no robot motion or evaluator outcome is invented. The six clips total about 3.4 MB. They are encoded at original recorded display speed; the local result page plays them at 3×.

For the clearest positive demonstration, use `retrieve_restore.mp4` alongside its actual console transcript: Jev continued at p=0.26 to open the box, asked at p=0.79, retrieved the selected item and reclosed the box. The clip itself records physical frames; model/ASK waiting time is excluded. `patrol_return.mp4` shows actual Husky inspections and return; `occlusion_inspection.mp4` shows clearing, physical observation and reporting without ASK.

Source GIF hashes/durations and MP4 hashes/ffprobe results are in `media_manifest.json`. Full results and limitations: [six-task documentation](../../docs/six_new_tasks_dev_v1.md). These are unpaired engineering demonstrations, not a comparative benchmark result.
