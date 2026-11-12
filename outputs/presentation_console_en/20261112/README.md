# English presentation console — actual rehearsal, 12 November2026

Independent UI: http://127.0.0.1:8902/. Original controller remains at8877. No frozen protocol, model prompt, threshold, motor controller, evaluator, dataset or historical record was changed.

## Actual new live Dev comparison

One retrieve/restore scene, three independent real PyBullet processes, unchanged Gate Dev v7 and shared planner. The three initial public payloads are byte-identical after canonical serialization. No whole-episode retry or outcome exclusion. Automatic User Simulator replies were used for all three methods.

| Method | Physical Task Result | Burden | API Attempts | API Latency | DeepSeek Input / Output | Jev Input / Output |
|---|---|---:|---:|---:|---:|---:|
| llm_noask | Unsuccessful | 0 | 4 | 5.90s | 12567 / 408 | — |
| llm_gate | Success | 1 | 10 | 11.04s | 24205 / 481 | — |
| jev_gate | Success | 1 | 10 | 7.65s | 15587 / 474 | 11749 / 120 |

Total:3 new online episodes,24 authenticated requests, zero API/schema errors or retries. Returned models:deepseek-flash and jev-1.14.0. This one Dev scene is a functional rehearsal, not a method ranking or a replacement for the frozen12-group Test results.

NoAsk chose the cup while the fixed hidden goal selected the block, so it scored unsuccessful from the physical evaluator. Both gates opened first, asked about the item, delivered the block and reclosed the box. Jev actually returned0.14 CONTINUE before opening, then0.83 ASK. These Dev scores are separate from the recorded Test replay's0.11/0.62.

## Actual manual and browser checks

- Final offline rehearsal:3/3 genuine physics tasks passed under clearly labelled scripted public-only policies. The human typed an English pad name into the browser; invalid input produced an English validation message. The manual robot stayed at the same physical state and frame hash while another independent robot completed an inspection task.
- NoAsk disabled Human controls and never created a question. The automatic inspection case completed by physically inspecting the label, with no ASK.
- Initial instructions, the full conversation, public DAGs and final Ground Truth were inspected. Hidden truth stayed absent before termination.
- All three navigation tabs work at1920,1280 and390px. Presentation View keeps the selected mission or paired three methods visible, with enlarged labels. No page overflow or JavaScript errors in the final checks.
- All9 actual recorded MP4s decoded. The embedded synchronized replay retained separate ASK and USER frames at the same simulation step; pause/restart and1×/2×/3× stayed on its shared timeline.
- Project pytest:364 passed in111.18s. Six new HTTP-boundary tests cover English/original separation, evidence allowlisting, path traversal denial, real video byte ranges and zero-inference read-only evidence.
- All3121 pre-existing tracked files remained hash-identical, including the user's uncommitted old Milestone PPT. Worker authentication files remain in the ignored local session folder and are not published.

## Evidence and boundaries

`offline_qa1/validation.json` retains the initial presentation selection failure;`offline_qa2/validation.json` retains the mobile overflow failure after actual successful physics runs. Both UI issues were fixed in the independent English frontend. `offline_qa3/validation.json` and`views_final/validation.json` are the final passing checks. No paid episode was repeated to improve a result.

The three live raw episodes and all24 per-attempt request/response/usage records are under`live_qa1/`. Authentication headers and key values are not included. The existing frozen Benchmark view serves original evidence read-only; no Test model calls were added. Two-machine VPN operation remains untested.
