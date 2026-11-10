# Buffered exchange: independent shared-Planner Dev repair

This development branch diagnoses the original six-task NoAsk exchange failure and tests a shared planning repair. It does **not** replace frozen prompts/configuration, modify any historical episode, or silently promote a new planner into the main HTML console.

## Diagnosis from the actual request and physical trace

The original episode is `outputs/six_tasks_dev_v1/live/buffer_exchange/episode.json`. At round 2, the state correctly showed:

- `item_a` on `buffer_front`;
- `item_b` inside `slot_left`;
- `slot_right` empty;
- both successful prior moves in the public action history.

The next actual DeepSeek response moved `item_b` back to `slot_right`. A subsequent attempt to put A there failed with `target_full`, followed by more reversing and occupied-pad placements. All thirteen serialized provider inputs matched the saved turn payloads. The first wrong action therefore came from the Planner; it was not caused by losing history, sending an old world state, or failing to move B physically.

The state was complete but dense, initial-position wording remained in the instruction, and the single-action planner had no explicit checkpoint separating current position, final relation and its own assumed buffer choice. These are plausible contributors; we do not claim access to the model's internal reasoning. The broad v1 `affordances` list described schema-supported destinations, including occupied targets and reverse moves, rather than guaranteed useful actions.

## Retained Dev iterations

All experiments use only public state, the existing models and the original buffer physics/evaluator. No private preference, evaluator score, prescribed next action or oracle suffix is sent to the planner.

| Candidate | What changed | Observed regressing first actions |
|---|---|---:|
| Raw v1 | Original request/prompt | 2/4 probes |
| Dev v2 summary only | Explicit measured regions, public final relations, confirmed answers versus own assumptions | 2/4 |
| Dev v2 wording only | Preserve completed relations; distinguish initial and current state | 1/4 |
| Dev v2 summary + wording | Both | 1/4 |
| Dev v3 compact context | All user dialogue retained; physical history aggregated with latest result | 2/4 |
| Dev v3 compact + wording | Both | 2/4 |
| Dev v4 grounded plan, appended context | Model emits current locations, public final targets, working choice and remaining plan | 0/4 |
| Dev v4 grounded plan, compact context | Same structured planner with compact context | 0/4 |

These **32 real API action probes** come from four states in one archived episode, with repeated physical arrangements at different history lengths. They are proposed-action diagnostics, not end-to-end task success rates or independent samples. Negative v2/v3 records and their plans/amendments remain intact. V3/v4 are adaptive Dev iterations after inspecting earlier probes, not a confirmatory pre-registered result.

V4 validates only that the model's current-location and final-target fields agree with public facts. It does **not** validate its first action against a correct-action label or hidden buffer preference. A unit test deliberately returns a goal-regressing action with correct grounding and confirms that the wrapper returns that bad action unchanged. There is no action mask, automatic correction, classical swap planner, or scripted fallback.

Every round still runs Gate first. On CONTINUE the shared DeepSeek planner produces a fresh plan; only the first model-proposed action executes. Future actions are not cached or executed before later gates. The same planner and serializer apply to NoAsk, LLM-Gate and Jev-Gate. The structured action output cap is **400 tokens**, versus v1's 160; this is an explicit inference-cost change shared across methods. Provider, non-thinking mode, temperature, original geometry/grasp controller/evaluator and Jev threshold **0.5** stay unchanged.

## Six complete real API/PyBullet cases

The full-case list was locked before any complete episode. All versions share one hard ceiling of 120 authenticated requests and six complete episodes, with the existing request retry/circuit-breaker policy. This run used **69 authenticated attempts**: 32 probe calls and 37 episode attempts, including one schema repair in the original-planner known-preference control. No episode was rerun until success.

| Condition | Planner / method | Physical exchange | Final task success | Burden | Physical moves |
|---|---|---|---|---:|---:|
| Back pad disclosed | Original v1 NoAsk | Complete | Success | 0 | 3 |
| Back pad disclosed | Dev v4 NoAsk | Complete | Success | 0 | 3 |
| Back pad hidden | Dev v4 NoAsk | Complete | Failed: guessed front | 0 | 3 |
| Back pad hidden | Dev v4 LLM-Gate | Complete | Success | 1 | 3 |
| Back pad hidden | Dev v4 Jev-Gate | Complete | Success | 1 | 3 |
| Front pad hidden | Dev v4 NoAsk | Complete | Success: same front guess | 0 | 3 |

All six completed in three real physical moves and DONE. The five cases using the repaired planner had no failed skill or goal-regressing executed move. The known-preference original-planner control also succeeded, so the historical loop must not be described as a universal v1 inability to swap objects.

The two unknown-preference NoAsk controls have identical initial model payloads, but opposite hidden preferences. They produced the same front-pad choice and physical action sequence. The unchanged evaluator correctly fails one and passes the other. This separates a wrong preference guess from mechanical/planning failure and prevents artificially making NoAsk fail.

Only the three **back-pad-hidden Dev v4 methods** form a matched comparison. Both gates asked at the beginning, when no specified buffer choice was available; Jev returned p(ASK)=**0.59**. After disclosure both completed the same physical goal. The case-level API latencies were NoAsk **5.09 s**, LLM-Gate **10.25 s**, Jev-Gate **7.19 s**. This one physical group is an engineering demonstration, not evidence of a general Jev advantage or statistical significance.

Across all probes and episodes, measured backend usage was DeepSeek **163,196 input / 2,904 output tokens**, Jev **16,638 input / 120 output tokens**. Cumulative API latency was **66.37 s**. Backend tokens are not combined into monetary-cost claims. Returned models were `deepseek-flash` and `jev-1.14.0` (configured `jev-latest`). The complete raw usage, including the repaired baseline response, remains in JSONL.

## Evidence and local presentation page

- Original-case diagnosis: `outputs/buffer_dev_v2/analysis.json`.
- Negative early probes: `outputs/buffer_dev_v2/` and `outputs/buffer_dev_v3/`.
- Grounded-plan probes, all six complete episodes, original/model payloads, provider attempts, physical events, evaluator results and automatically generated CSV/Markdown: `outputs/buffer_dev_v4/`.
- Offline tests: **311 passed**, retaining all original 295 tests. Tests cover public isolation, truth reversal, latest-state precedence, assumption versus disclosure, no action rewriting/masking, exact original-prompt baseline, shared planner and actual physical scoring for both buffers.
- Read-only result/video page: **http://127.0.0.1:8893/**. Six actual MP4s support play/pause/seek and default 3×. They total about **2.4 MB**. ASK/USER frames are explicitly presentation holds for actual events, not model-inference wall time.
- Media and ffprobe/hash evidence: `presentation/buffer_dev_v4/`.

The main HTML's v1 default is intentionally unchanged; it can still exhibit the old behavior. This candidate is independent Dev evidence, not an unannounced replacement of the previous six-task experiment or formal Benchmark configuration.

Actual commands:

```bash
.venv/bin/python scripts/buffer_dev.py analyze
.venv/bin/python scripts/buffer_dev.py plan
.venv/bin/python scripts/buffer_dev.py probes --live
.venv/bin/python scripts/buffer_dev_v3.py plan
.venv/bin/python scripts/buffer_dev_v3.py probes --live
.venv/bin/python scripts/buffer_dev_v4.py plan
.venv/bin/python scripts/buffer_dev_v4.py probes --live
.venv/bin/python scripts/buffer_dev_v4.py episodes --live
.venv/bin/python -m pytest -q
.venv/bin/python scripts/buffer_dev_report.py --export-media
node scripts/buffer_dev_browser_check.mjs
```

Paid probe/episode commands refuse to overwrite their outputs. The v2/v3 complete-episode commands were superseded before running, and were not used. Do not start a new ledger to bypass the shared ceiling. To reopen the offline report on a matching checkout, use `scripts/buffer_dev_report.py` without `--export-media` and serve `outputs/buffer_dev_v4` on port 8893; the report copies committed MP4s without API calls.

## Next research step

The observed open-box-then-ask, inspect-known-station-then-ask and observe-label-without-asking behaviors fit the intended qualitative clarification timing. The historical NoAsk planning loop is a confound, not evidence for gate superiority. The repair makes the comparison more meaningful by allowing NoAsk to execute well and still be scored honestly when a preference guess is wrong or right.

Next, generalize public grounding beyond this buffer-only Dev implementation and expose an explicit optional Dev profile in HTML. Then lock and run **nine paired cases**: three methods on each of buffered exchange (ask before the first choice), retrieve/restore (do known work before asking) and occlusion inspection (obtain observable information without asking). Use identical per-case layout, truth, budget, serializer and planner; keep planner failures, preference failures, early/repeated asks, burden and separate backend cost visible. This is still a small engineering comparison. A new frozen version and independently grouped layouts are needed before any new-task held-out evaluation; the old 128-sample Test remains untouched.
