# Three-room search — independent Navigation Dev v1

This extends the local command center with `find_and_approach`. It does not change
the frozen tabletop study, prompts, data, model settings or historical results.

## Run locally

```bash
.venv/bin/python console.py --live --port 8877 --api-limit 160 --live-episode-limit 12
```

Open `http://127.0.0.1:8877/`, select **Find & Approach**, choose case A/B/C,
0/1 unknown location facts, method and Auto/Human reply. Scripted methods use no API.
**One-click comparison** creates three independent real-model episodes with automatic
replies on the same fixed world. It shares the existing bounded API ledger and queue.
Never start a second controller on the same port or reuse a completed study directory.

The live frame is a real PyBullet TinyRenderer panorama with a real robot-camera inset.
The turquoise trail comes from measured base positions. Frames carry simulation step,
sequence and JPEG hash in the same packet as phase/action/navigation statistics.
The HTML exposes actual distance, inspected stations, ASK burden, backend token usage,
API latency and final physical evaluation. Click a viewport to enlarge it.

## Task and information boundary

- Three known rooms, two doorways, six declared open-surface inspection stations.
- A Husky differential-drive base moves by wheel velocity control. The shared route
  graph uses room centers and inspection points. No post-initialization pose resets,
  teleportation, grasping or delivery are used.
- Local detection requires range ≤1.65m, horizontal FOV ≤90° and a collision-ray hit
  on the actual target. This is geometric simulated perception, **not learned vision**.
- Target geometry is hidden in the public panorama until locally detected; this changes
  visual alpha only, never physical pose/collision. Unseen coordinates and case IDs are
  omitted from the model payload. All unknown-location cases have identical initial
  public observations **and rendered frames**.
- A negative inspection covers one station, never the whole room. NoAsk can keep
  exploring and succeed. Six stations can be searched within the 36m travel budget.
- Success requires a real detection event, physical distance ≤1.2m, a stopped robot,
  no wall penetration and the distance budget. Saying DONE or providing a hint is
  insufficient. A valid final state can succeed on another termination reason.

Unlike tabletop choices, a location is a **fixed world fact**. Automatic replies reveal
only the requested `target_location` fact. A manual answer is logged as an operator
claim; a wrong claim never moves the target or changes the evaluator. A later corrected
claim is allowed. The query requests one complete room/landmark location: burden=1,
including repetitions. Both model and user waiting leave Bullet frozen. Automatic
navigation replies have a declared actual 3s delay, identical for all gated methods.

## Agents and fairness

All three real methods use the same navigation public serialization and DeepSeek
question/action planner. NoAsk skips the gate; LLM-Gate calls DeepSeek; Jev-Gate uses
the actual Noul probability at threshold 0.5. Gate runs before planner. DONE comes
only from the action planner. The new prompts recognize useful exploration and
semantic priors; they do not impose "one failed search must ASK" on learned gates.

Scripted ASK does use that simple rule for free UI diagnostics, clearly labelled
`scripted_policy_real_pybullet`. Scripted NoAsk exhaustively searches unchecked
stations. Their successes are never presented as model results.

## Verification and bounded live pilot

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/navigation_oracle.py --output-dir outputs/navigation_dev_v1/oracle_NEW
node scripts/navigation_browser_check.mjs
.venv/bin/python scripts/navigation_pilot.py prepare
# Dedicated controller, not the interactive session:
.venv/bin/python console.py --live --port 8878 \
  --output-dir outputs/local_console/navigation-pilot-v1 --api-limit 120 --live-episode-limit 9
node scripts/navigation_live_pilot.mjs --live
.venv/bin/python scripts/navigation_pilot.py report
```

Use the bundled Node binary if `node` is absent from PATH. Browser scripts use the
existing Playwright runtime helper and installed Chrome; no CDN/font service is used.
The browser regression runs actual manual navigation, autonomous navigation and the
original Panda task concurrently, checks ASK frame/observation equality and verifies
JPEG hash/step consistency, answer draft reload and zero model calls.

The live pilot is **3 placements × 3 methods = at most 9 episodes, 120 authenticated
attempts**, including retries. Plan, prompt/source hashes, model settings, order,
token limits and failures are recorded before calls. All three placements share
**one layout group**; they are not independent maps and have no significance claim.
No formal Test calls are made. Actual raw logs and automatic report live under
`outputs/navigation_dev_v1/live_v1/` when run. Do not overwrite a prior plan/results.

## Assets and limitations

Husky is loaded directly from installed `pybullet_data/husky/husky.urdf`. Its embedded
license is BSD 3-Clause, Copyright 2015 Clearpath Robotics, author Paul Bovbel.
See the upstream [Bullet Husky asset](https://github.com/bulletphysics/bullet3/blob/master/data/husky/husky.urdf).
The room/cabinet/knife collision and visual shapes are constructed in this project;
no knife motion/grasp capability or external perception model is claimed.

Current scope is one small static floorplan, six supported surfaces, no dynamic
obstacles, localization error, physical hardware or retrieval. Two-computer/VPN
execution remains untested; the existing controller/worker RPC interface is reused.
Future evaluation should add independent map groups, location priors and reply-cost
conditions, preregister policies/budgets, then compare travel/latency/burden jointly.
