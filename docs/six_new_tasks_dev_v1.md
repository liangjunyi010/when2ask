# Six new robotic task templates (independent Dev v1)

Implemented six new task templates, rather than changing colors or ordering within the two old tasks. The original three templates and twenty presentation variants remain available. The console now offers **nine task types**. This is a fixed-case engineering prototype, separate from all frozen Benchmark datasets, prompts and historical experiments.

| New task | Physical goal and independent checks | New capability reused across tasks |
|---|---|---|
| Category sorting | Six objects, three categories, three hollow bins; correct category allocation, no mixing, support/stability/release | Multi-item placement slots; one block-bin answer also determines the puck bin |
| Inventory restock | Count existing stock, add only the deficit to two shelves; exact quantities, original stock and surplus untouched | Observation-derived counts and non-overlapping stock placement |
| Retrieve and restore | Open a closed box, park lid, retrieve one item, leave the other inside, close again | Surface parking and retrieval from a container; existing full-corner/rim-contact cover check |
| Buffered exchange | Exchange two single-capacity slots through the selected temporary pad; other pad unused, final pads empty, physical sequence evidence | Intermediate parking zones and capacity rejection |
| Patrol and return | Physically inspect known and selected stations, then drive back to the start and stop | Existing Husky wheel controller/map; actual inspection fixtures, pose/orientation/ray evidence and return action |
| Occlusion inspection | Move an opaque supported screen, inspect the exposed label, report its actual code; preserve the label | Physical screen movement; fixed-camera Bullet ray/range-gated structured observation |

All Panda movements use the existing IK/motor path, guarded proximity constraint grasp and physical release. Hollow bins, objects, lids, screen supports and equipment fixtures have real collision bodies. No action resets final object poses. Surface placement checks full AABB, table contact and stability. The label reader is a **structured simulation sensor**, not learned image recognition; it reveals a fixed world fact only after physical line-of-sight and range checks and an inspection action.

## Public/private separation and shared methods

`data/six_tasks_dev_v1/samples.json` stores each complete task, including its private preference or world fact. Public state is explicitly constructed from the instruction, measured observation and public history. Public task fields include the goal, stated DAG, candidate roles and initially disclosed choices; they contain no evaluator score, private answer registry or oracle action sequence. Altering the undisclosed truth leaves initial public payload unchanged, including for an occluded label with different actual text.

The three methods use the same `task6_agents.py` action/question planner and public serialization. NoAsk skips the gate; LLM-Gate runs DeepSeek first; Jev-Gate runs Noul first and asks iff `p >= threshold`. Default threshold is 0.5. Gate outputs only ASK/CONTINUE, and DONE is produced by the action planner. New prompts have their own version/hashes and do not replace frozen tabletop/navigation contracts.

Automatic answers reveal only requested roles through the existing resolver. Human select/confirm/text responses use the same queue. Previously disclosed preferences remain fixed. An initial human answer can define a missing preference for that interactive run; it cannot alter a fixed label or substitute for a physical observation. Burden is the number of distinct requested slots per question, charged again for repeats. No physics steps occur while waiting for model calls or user replies.

## Actual validation

- Original baseline: **270 passed** before edits.
- Updated full pytest: **295 passed**, including six real physical task executions, hidden/public isolation, malformed questions/actions, shared planner/NoAsk contracts, paired comparison reset/configuration, negative physical scoring and budget-termination success.
- Physical oracle attempt 1: **4/6**. A short category object caused hand/rim interference; patrol initially lacked a physical fixture for its sight ray. Those raw failed traces remain in `oracle_01`.
- Corrected geometry: graspable cylindrical category objects and real equipment collision fixtures. Oracle attempt 2: **6/6**, with the original motor controller and scoring thresholds. Source hashes are retained.
- Actual Chrome UI with six scripted policies and real physics: **6/6**, five manual question forms and frozen-world checks, no ASK for the observable label, mobile layout and zero console errors. These zero-API cases are labelled separately and excluded from model metrics.
- One real-model episode per new template: **six episodes, 60 authenticated attempts, 4/6 task successes**, including two schema-repair retries. No transport/authentication API errors. No whole-episode reruns and no formal Test calls.

| Task | Method | Task success | Burden | Physical actions | Cumulative API latency |
|---|---|---:|---:|---:|---:|
| Category sorting | LLM-NoAsk | Failed | 0 | 6 | 6.95 s |
| Inventory restock | LLM-Gate | Success | 1 | 3 | 9.94 s |
| Retrieve and restore | Jev-Gate | Success | 1 | 3 | 5.59 s |
| Buffered exchange | LLM-NoAsk | Failed | 0 | 12 | 11.11 s |
| Patrol and return | LLM-Gate | Success | 1 | 3 | 9.27 s |
| Occlusion inspection | Jev-Gate | Success | 0 | 3 | 5.32 s |

These are **different tasks per method**, not a paired method comparison or evidence of superiority. The comparison launcher supports all six tasks with independent worlds and the same configuration; additional paid three-method batches were not run in this six-case study.

Sorting NoAsk successfully moved all six objects but guessed the wrong bin rule. Exchange NoAsk chose a buffer, repeatedly undid progress, tried occupied/full targets and exhausted its twelve-action limit. The exchange failure combines missing preference information and planner errors, so it cannot be attributed solely to clarification timing. Both failures retain their physical scores, recording and full logs.

The successful timing cases are directly visible in the actual turns:

- **Retrieve/restore Jev:** CONTINUE at **0.26**, physically open the box; ASK at **0.79**; user selects the stored block; retrieve, reclose, DONE and success.
- **Inventory LLM-Gate:** replenish the known cup deficit first; ask the required block count; add two blocks, then finish.
- **Patrol LLM-Gate:** inspect the known station first; ask for the additional station; inspect it and actually return to start.
- **Occlusion Jev:** CONTINUE for screen movement, camera inspection, report and DONE; no unnecessary code question. Reporting a correct code without inspection fails the evaluator.

Actual configured/returned models: DeepSeek `deepseek-flash`; Jev configured `jev-latest`, returned `jev-1.14.0`. Total DeepSeek input/output tokens: **137,341 / 813**. Total Jev input/output: **26,666 / 216**. Cumulative API latency: **48.18 s**, excluding robot execution and recording; token counts are not combined into monetary cost.

The locked plan in `outputs/six_tasks_dev_v1/live_plan.json` records code commit, source/data/prompt hashes, model parameters, shuffled run order and limits: six episodes, 120 total authenticated requests, 20 rounds/12 physical actions/12 slot requests/32 API attempts per episode, one request retry and the existing backend circuit breakers. All actual attempts, including malformed responses and repairs, count toward the ceiling.

## Local UI and evidence

- Main command center: **http://127.0.0.1:8877/**. Select a new task under **NEW TASKS · 六个新任务**, choose 0/1 missing preference/fact, method and Auto/Human. Existing three-method comparison remains available and uses independent resets of the same instance.
- The six actual model cases are archived in the main console. Each card opens the original instruction, complete gate/question/answer/action history, final ground truth and independent physical conditions. Archived runs do not launch new requests.
- Read-only recordings/results: **http://127.0.0.1:8892/**. Six MP4s support play/pause/seek, default to uniform **3×** and total about **3.4 MB**. Original GIFs stay local. Model and ASK wall time are excluded from these physical-frame recordings; the interaction is in the accompanying transcript. No independent timed flow animation is claimed.
- Committed media: `presentation/six_tasks_dev_v1/media/`. Each source GIF hash/duration and MP4 hash/ffprobe result is in `media_manifest.json`.
- Raw model runs: `outputs/six_tasks_dev_v1/live/<template>/episode.json`, `evaluation.json`, `api_attempts.jsonl`, PNGs and physical traces. Machine-generated CSV, summary and detailed report are at the collection root. Failed cases are retained.
- Browser screenshots and labelled offline validation are in `outputs/six_tasks_dev_v1/browser/`.

Commands actually used:

```bash
.venv/bin/python scripts/generate_task6.py
.venv/bin/python scripts/task6_oracle.py --attempt 01
.venv/bin/python scripts/task6_oracle.py --attempt 02
.venv/bin/python -m pytest -q
node scripts/task6_browser_check.mjs
.venv/bin/python scripts/task6_live_plan.py
node scripts/task6_live_check.mjs --live
.venv/bin/python scripts/task6_report.py --export-media
node scripts/task6_readonly_check.mjs
```

Generation, oracle attempt directories, the locked live plan and live run collection refuse overwrites. To reopen the UI on a matching checkout:

```bash
.venv/bin/python console.py --live --port 8877 --api-limit 60 --live-episode-limit 6
.venv/bin/python scripts/task6_report.py
.venv/bin/python -m http.server 8892 --bind 127.0.0.1 --directory outputs/six_tasks_dev_v1
```

The report command copies committed MP4 clips into the served output directory without making model calls. On a fresh clone the original local GIFs are absent, so `--export-media` is unnecessary. Reviewing records is free; starting new live tasks uses that controller's explicitly bounded session. Two-computer/VPN operation was not tested in this round; the worker must have matching source/data and dependencies, with provider keys staying on the controller.

Known limits: one conservative instance per new template; only 0/1 unknown slot per prototype; fixed grasp orientation and constraint assistance; no generic collision-aware motion planning; one existing three-room map for patrol; structured label sensing; real NoAsk planning failures remain. This is not a randomized multi-seed benchmark, and these cases do not enter the frozen Dev/Test study.
