# Implementation and validation status

## Phase 2 current status (2026-10-23)

| Stage | Implemented and actually verified |
|---|---|
| Stable baseline | Original 26 tests passed before branching; original Scripted entry points and evidence retained |
| Credentials | Both configured locally; ignored `.env` is 0600; exact-value/pattern scans pass |
| DeepSeek | Real model discovery and JSON completions, non-thinking; returned `deepseek-flash`; actual usage and latency |
| Jev | Real `/v1/models` and `/v1/systemone` Noul; configured `jev-latest`, returned `jev-1.14.0`; threshold remains 0.5 |
| Agent split | Gate only ASK/CONTINUE, always before shared Planner; Planner alone returns DONE; NoAsk never calls a gate |
| Public boundary | Same projection for all methods; changed hidden truth leaves payload unchanged; no private keys in recorded turns |
| Benchmark | 5 crafted validation + 20 pilot samples; all 0/1/2/3 disclosure levels; varied IDs/order/truth; 8 intent groups isolated across partitions |
| Physical oracle | Current validation 5/5 and pilot 20/20 real successes; initial red-cup collision failures retained separately |
| Questions | select/confirm/all_preferences, private unified resolver, only requested hidden keys read; distinct-slot burden/repeats verified |
| ASK freeze | Every actual ASK has unchanged complete physical state and step count |
| Recovery | Real uncover/table-return/replace/recover test passed; inside regrasp clearance fixed while retaining proximity guards |
| Evaluator | Original geometry/contact/release checks retained; latest relevant real DAG event allows corrections; success independent of DONE/termination |
| Budgets/errors | Locked persisted counters, finite retries/format repair, auth/three-error circuits; actual 12/12 episodes and 95/200 authenticated requests |
| Costs | Each attempt has model/stage/usage-or-null/latency; backend tokens separate; simulator/generation/oracle costs separate |
| CLI | doctor/live, generate, validate/oracle, run/live and report executed against real local package/providers |
| Diagnostic v1 | Three genuine episodes: physical skills succeed but task scores all fail; raw results retained, never pooled with v2 |
| Final v2 | Nine real paired episodes: NoAsk 1/3, LLM-Gate 3/3, Jev-Gate 3/3; burden totals 0/5/5; all 27 physical skills succeed |
| Fair comparison | Initial payload, Planner configuration and prompt hashes match across each paired sample; mixed-cohort reports rejected |
| Tests/evidence | **66 passed in 34.61 s**, no skips; offline pytest blocks network; evidence/GIF/attempt sequence checks pass |
| Publication | Feature branch `feat/benchmark-apis`; source/data/tests/sanitized records prepared; private push/PR checked at publication, no auto-merge |

Current details: [real experiment report](phase2/experiment_report.md),
[interfaces and commands](phase2/interfaces.md), `outputs/phase2/evidence.json`,
`outputs/phase2_live/paired_v2/` (final), `outputs/phase2_live/paired/` (diagnostic).

Not completed: a formal independent Dev/Test study, threshold calibration, broad
layout/task distributions, real hardware or friction-only grasping, MP4, training
or 1,800-episode benchmark. Final online coverage is 0/2/3 unknown preferences;
1-unknown was validated offline/oracle only after the prompt revision, to respect
the total episode cap. Current online pilot cases are dev-family cases. The
public fixed-preference contract was clarified uniformly after validation
diagnostics; no statistical significance is claimed. DeepSeek reports an alias,
not an immutable backend build. A first-discovery audit restart bug was repaired
from actual terminal evidence with an explicit recovery note and preserved
high-water count; all 95 attempt IDs are now continuous and unique.

## Phase 1 historical acceptance record

The following is the original Phase 1 record at stable commit `442efa4`; its
unimplemented-model notes describe that historical scope, superseded above.

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
