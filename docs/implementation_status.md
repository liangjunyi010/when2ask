# Implementation and validation status

Validation date: 2026-10-23. This is a scripted engineering MVP, not a formal
LLM-NoAsk / LLM-Gate / Jev-Gate evaluation.

| Stage | Implementation | Actual verification |
|---|---|---|
| Background inspection | Read existing When2Ask slide text, did not modify originals | Completed; no implementation guidance Markdown found in searched locations |
| Isolated environment | Project-local Python 3.11 venv, pinned dependencies, setup script | Python 3.11.16 / macOS 26.6.2 arm64; PyBullet built against SDK 26.5 with documented zlib macro fix |
| DIRECT smoke gate | Gravity, rigid body, step, state, CPU render, disconnect | Passed; `outputs/verification/direct_smoke.json` and PNG |
| One-block gate | Panda motors + IK, proximity constraint, release, settle | Passed; `block_pick_place.json`, before/after PNG; held-body motion tested |
| Full scene | Static tabletop, fixed Panda, hollow five-part box, two hollow cups, two blocks, two lids | Collision shapes inspected; center rays pass through openings; no initial inter-object penetration deeper than 1 mm |
| Fixed physical pack/cover | Blue cup, green block, black lid | All three skills passed before introducing QA; `pack_fixed.json` |
| Private/public boundary | Policy accepts PublicState only; env receives no private spec | Changing hidden preferences leaves full initial observation, NoAsk decisions and actions unchanged |
| ASK freeze and disclosure | Structured slot oracle, burden per requested slot | Same complete state and same step count before/after ASK; unknown slots rejected and unasked slots absent |
| Scripted Ask | Cup -> ASK two slots -> block -> cover -> DONE | Seed 0: all physical and task conditions true, burden 2, 3 actions |
| Scripted NoAsk | Public closest-to-box rule with stable ID tie breaker | Seed 0: all 3 physical actions succeed; task false because yellow chosen over hidden green; burden 0 |
| Fair NoAsk scoring | Same policy/physics with alternate hidden block preference | Same observations, decisions and actions score true when hidden block is yellow |
| Alternate choices | Ask with hidden yellow block / white lid | Real full execution passed at seed 3 |
| Independent evaluator | Full AABBs, height, contacts, speed, transformed mouth corners, release, temporal evidence | Positive physical episodes pass; wrong objects, false labels, crossed wall, rotated/floating lid, missing packing evidence and retained constraint rejected |
| Failure handling | Bounded waypoints/skills, release cleanup, failed log persistence | Step-limit failure saved as failure; far grasp creates no constraint; artifact errors preserve physical evaluator results |
| DIRECT recording | Live TinyRenderer GIF + scene/action/final PNG + episode JSON | Both demos generated at seed 0; inspect `artifact_validation.json` for hashes/frame counts |
| GUI | Optional native Bullet GUI, fixed camera, explicit non-real-time physics | GUI execution and viewport checked separately; native unbundled Python window could not be targeted by the app inspection connector |
| Regression seeds | Seeds 0–4, source XY jitter ±4 mm | Ask physical 5/5, task 5/5; NoAsk physical 5/5, task 0/5 for default hidden intent; `seed_summary.json` |
| Automated tests | pytest over real Bullet + public policy contract and adverse fixtures | **26 passed**; JUnit results are in `outputs/verification/pytest.xml` and `artifact_validation.json` |
| Git packaging | Independent main branch, ignore secrets/env/caches/videos/bulk runs, source docs and evidence | Reviewed before initial commit |
| GitHub publication | New private `when2ask` repository, origin main | Remote privacy and uploaded HEAD checked after push; see completion report |

## Scope and limitations

- Grasp is explicitly `constraint`, not friction-only grasping. Only held-object
  hand contacts are suppressed between attachment and safe retreat. All runtime
  object transfers use dynamics; only initial Panda joints are reset.
- Negative evaluator tests deliberately reposition test bodies or attach a fault
  constraint. These are adverse fixtures, never represented as successful skills.
- The box is static. Cup walls and lids are simple idealized geometry. The layout
  and small jitter have been exercised, not broad distributions or arbitrary
  clutter. No general motion planner, real robot, LLM, Jev, training or database.
- The full collision AABB containment test is conservative for rotated objects.
  Support/contact thresholds are tuned to these primitive geometries.
- The public/private boundary is a typed application interface, not an OS sandbox
  for untrusted Python policy code. Final evaluator labels appear only after DONE
  or failure and must not be put into future policy payloads in that episode.
- Video is GIF at 640×480, based on actual live CPU renders. MP4 is not implemented.
  GIFs remain local and are reproducible; screenshots, JSON and compact evidence
  are committed. Bulk seed/GUI episodes remain local.
- GUI connection, positive viewport and actual complete execution are validated
  programmatically. No claim of native-window screenshot inspection is made.
- Future formal experiments require independent tasks/seeds, dev-only gate tuning,
  consistent planners/skills, model token and latency logging, and statistical
  evaluation. Current fixed scripted results cannot establish a learned gate's
  effectiveness.

## Commands used

From the project directory with `.venv` active:

```bash
bash scripts/setup_env.sh
python scripts/verify_direct.py
python scripts/verify_block.py
python scripts/verify_pack.py
python demo.py --mode ask --record
python demo.py --mode noask --record
python demo.py --mode ask --gui
python demo.py --mode ask --gui --fast --output-dir outputs/gui_checks/ask
python demo.py --mode noask --gui --output-dir outputs/gui_checks/noask
python -m pytest -q --junitxml=outputs/verification/pytest.xml
python scripts/verify_seeds.py --seeds 0 1 2 3 4
python scripts/verify_artifacts.py
```

The setup script uses uv when available and standard venv/pip otherwise. The
uv path is the path exercised on this machine. The fallback is provided but was
not separately tested in a second environment.
