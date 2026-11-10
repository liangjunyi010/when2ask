# Buffered exchange Dev repair clips

Six real API/PyBullet episodes, with original v1 known-choice control and independent grounded-planner Dev controls/comparison. All complete in three physical moves. The hidden-back NoAsk case still fails preference scoring, while the otherwise identical hidden-front case succeeds; both failures and successes are retained.

The clips are compressed from the real episode GIFs. ASK/USER frames are display holds tied to actual recorded events, not invented inference latency. Media are encoded at their original display speed; the local page plays at 3×. Six clips total about 2.4 MB. `media_manifest.json` verifies source GIF hash/frame count/duration and MP4 hash/ffprobe metadata.

This is one physical group, not six independent benchmark samples. Full analysis, negative v2/v3 probes, actual usage and limitations: [independent Dev report](../../docs/buffer_shared_planner_dev.md). The main HTML and frozen experimental configurations are unchanged.
