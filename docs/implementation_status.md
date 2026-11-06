# Implementation and validation status

## Phase 3 current status (2026-10-23)

| Stage | Implemented and actually verified |
|---|---|
| Preservation | Started from `3bc24b2`; old 66 tests passed; 194 historical artifact hashes unchanged; PR #1 remains OPEN |
| Branch | `feat/devtest-calibration`, based on `feat/benchmark-apis` |
| Versioned grouping | Schema 3 explicit template/layout/group/seed/sample/partition; physical base groups replace truth grouping for new data; legacy reader retained |
| Dataset | Dev 32 samples/8 groups; Test 128/16; each half per template and balanced 0/1/2/3 unknown counts |
| Split checks | Alias/truth/style/jitter variants grouped together; held-out physical container arrangements; minimum cross-split matched-container distance 101.1 mm |
| New task | Two real five-piece containers, cup target preference reused to infer other block target, public order variants |
| Physical oracle | Dev 32/32, Test 128/128; pack/cover 80/80, two-container 80/80; separate all-pairs initial geometry checks passed |
| Controller regression | Final code passed old 25/25 oracle again; original motor/IK, proximity guards, release and full-geometry evaluators retained |
| Models | Live revalidation successful; configured/returned DeepSeek `deepseek-flash`; Jev `jev-latest` / `jev-1.14.0`; real usage/latency |
| Pre-registration | Source commit `9cefbd3`, 20 runtime/analysis source hashes, prompts, data, 40 randomized jobs, retry policy and selection rules committed before authenticated calls |
| Real Dev | 40 independent fresh episodes, 8 scene groups ×5 conditions; 293/600 authenticated requests including discovery/revalidation/retry; 40/40 episode cap exhausted |
| Dev scores | NoAsk 5/8 B0; LLM-Gate 7/8 B12; Jev .3 7/8 B11, .5 7/8 B11, .7 6/8 B7 |
| Physics vs task | 99/99 executed physical skills succeeded; wrong preferences and malformed model actions still fail task; all failures retained |
| API failures | 2 schema-error attempts in one episode, 1 retry, no network/auth/API errors; inference usage present for every attempt |
| Threshold | Default 0.5 retained by predeclared paired-group rule; no supported advantage for alternative; uncertainty preserved |
| Public boundary | Paired initial payloads identical; no private metadata in any model state; ASK freezes full Bullet state; Gate before Planner; NoAsk no Gate |
| Analysis | Raw-backed CSV/JSON/Markdown, 8-group pairing/intervals, error/timing cases, token costs separate; frozen report byte identity preserved on equivalent regeneration |
| Test freeze | `configs/frozen_test.yaml` plus manifest; hashes, models, threshold, parameters, code and budgets; **0 Test API episodes**, live Test blocked in Phase 3 |
| Recording | New live two-container episode, 315 real TinyRenderer GIF frames; per-episode initial/final PNG and trajectory; GIF ignored |
| Tests | **96 passed**, including original 66; offline network guard; final JUnit and evidence saved under outputs/phase3 |
| Publication | Private repository verified; `feat/devtest-calibration` pushed; [PR #2](https://github.com/liangjunyi010/when2ask/pull/2) OPEN against `feat/benchmark-apis`; original PR #1 head/state unchanged; receipt in outputs/phase3/publication.json |

Current report: [Dev calibration](phase3/dev_report.md),
[design and pre-registration](phase3/design_and_preregistration.md),
`outputs/phase3/report/`, `outputs/phase3_live/`, `configs/frozen_test.yaml`.

Unresolved: the 8-group online selection covers only two preference triples per
template (all selected blocks green, pack lids black, cup destinations container_b).
Full Dev/Test each cover all eight triples per template. The limitation was found
in the coverage audit, disclosed, and not repaired by post-hoc replacement runs.
Future independent Dev replication should stratify truth jointly with layout and
disclosure before calls. This small exploratory study does not prove Jev superiority
or a uniquely optimal threshold. Formal Test remains unrun; 384 paired fresh episodes
are planned under a separately authorized cap. Model alias drift, conservative
primitive scenes, constraint-assisted grasp and lack of hardware remain limitations.

The historical Phase 2 and Phase 1 records below retain their original scope.

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
| Publication | `feat/benchmark-apis` pushed; repository `isPrivate=true`; [PR #1](https://github.com/liangjunyi010/when2ask/pull/1) is OPEN against main, not merged; remote commit checked |

Current details: [real experiment report](phase2/experiment_report.md),
[interfaces and commands](phase2/interfaces.md), `outputs/phase2/evidence.json`,
`outputs/phase2_live/paired_v2/` (final), `outputs/phase2_live/paired/` (diagnostic).

Not completed: a formal independent Dev/Test study, threshold calibration, broad
layout/task distributions, real hardware or friction-only grasping, MP4, training
or 1,800-episode benchmark. Final online coverage is 0/2/3 unknown preferences;
1-unknown was validated offline/oracle only after the prompt revision, to respect
the total episode cap. Online pilot cases include one dev-family and one
test-family instance, too few for a formal Dev/Test conclusion. The
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

## Local task console — 2026-11-03

- Added an independent browser controller and authenticated HTTP execution worker. One process per real Bullet world; three concurrent tasks by default. Original skill/evaluator sources, frozen data/prompts and historical results are unchanged.
- Supports both templates, all three real API methods, explicitly labelled offline scripted policies, automatic structured replies and human candidate selections. Unknown human choices define interactive intent and are logged separately from fixed-hidden-preference evaluation.
- Real browser/physics verification passed: independent processes, queue/cancel, ASK snapshot equality, progress in other worlds, refresh/reconnect, duplicate answer handling, frame SHA/step equality, full-view camera and no JavaScript errors.
- Three real-model pack-and-cover executions completed with 9/9 physical skill successes. Final task scores were NoAsk false, LLM-Gate true, Jev-Gate false; genuine preference errors are retained. This single-instance smoke is not a benchmark ranking.
- Dedicated live session used 24 authenticated requests (2 discovery, 22 inference), 3 live episodes, no API/schema errors or retries. No held-out Test API episodes ran.
- Full offline pytest: **126 passed** (original 102 plus 24 console tests). Actual artifacts and model versions: [console evidence](../outputs/console_evidence/README.md). Usage: [local console guide](local_console.md).
- Not yet verified: two physical computers over VPN. Not implemented: resuming an active physical world after controller/worker crash. Browser reconnect is verified; saved logs and budget persist across restart, task cards do not.

## Robot Command Center — 2026-11-06

- Implemented and locally rendered the dark robot wall, selectable 0–3 unknown preferences, one-click three-method comparison, unified clarification queue and real event/phase trace. Camera frames and metadata remain atomic.
- Paired comparisons enforce identical initial public payload, shared planner/prompts, independent physical resets and automatic fixed-preference replies. Atomic episode reservation and idempotent batch IDs prevent partial or repeated launches. Actual scores, per-backend costs and JSON/CSV exports are available in the UI.
- Browser/physics checks passed for simultaneous pending questions, draft persistence on switch/reload, exact question routing, duplicate answer handling, queued cancellation, ASK freeze, other-task progress and responsive layouts.
- Final live comparison: 3 episodes, 22 pre-reserved API attempts, 9/9 physical skills succeeded; task scores NoAsk false, LLM-Gate true, Jev-Gate false. All genuine preference failures remain visible.
- Development discovered a missing shared-ledger binding in the first paired run. Raw logs were retained, its 22 real requests explicitly reconciled, binding fixed, regression tested and the full comparison rerun. Total work: 6 real-model episodes and 44 authenticated calls, not six independent scenarios.
- Full offline suite: **152 passed**. No provider network in pytest. [New evidence](../outputs/command_center_evidence/README.md) is separate from frozen data and earlier reports. No held-out Test API experiments and no dual-computer tests were run.
## Navigation Dev v1 — 2026-11-06

- Added an independent three-room Husky task. Actual wheel motors, shared known-map
  routes, local geometric range/FOV/ray detection and true distance/stopped-state
  evaluation; no target/robot teleportation or pickup/delivery claims.
- Reuses controller/worker processes, live robot wall, automatic/manual clarification
  queue and one-click three-method comparison. World location facts remain fixed
  even if a manual hint is wrong. Each location question costs one slot.
- Real physical regression: **9/9** (three placements × known-location oracle,
  scripted NoAsk, scripted ASK); all skill actions succeeded. One floorplan group.
- Real Chromium regression passed manual navigation + autonomous navigation + original
  Panda task concurrently, ASK freeze, other-world progress, draft reload and exact
  frame hash/step consistency. No model calls in these checks.
- Offline full suite: **205 passed**. The 181 pre-existing tests remain unchanged.
- Separate preregistered real-model pilot is capped at 9 episodes / 120 requests;
  its result is reported separately when actually run. Frozen files are hash-checked.
- Guide: [navigation_dev_v1.md](navigation_dev_v1.md). Dual computers, new independent
  layouts, dynamic obstacles, learned vision and physical hardware remain unverified.


### Navigation Dev v1 actual live outcome

- Dedicated navigation pilot: **9/9 real-model physical successes** on three placement
  cases in one fixed map group; **65/120 authenticated API attempts**, no retries,
  API errors or schema errors. Returned models: `deepseek-flash`, `jev-1.14.0`.
- NoAsk / LLM-Gate / Jev-Gate each succeeded 3/3 with burden 0 and the same total
  travel (46.754m per method). API latency totals: 9.506s / 21.607s / 13.531s.
- Neither learned gate asked. This is not evidence of a clarification-timing benefit.
  Manual and automatic ASK paths were separately run with labelled scripted policies
  and real physics, including the actual 3s automatic reply delay and ASK freeze.
- All 1,148 protected existing tracked files (including the user's already-modified
  PPT) matched their pre-task hashes. No held-out Test API run or frozen-setting change.
- [Raw logs, automatic CSV/JSON report and preregistration](../outputs/navigation_dev_v1/live_v1/README.md).

## Navigation Dev v2 — independent cost study (2026-11-06)

- Added independent nav2 modules and CLI, preserving all 1,261 protected existing files. Reuses original Husky geometry, local detector and physical evaluator; true wheel motor factors 1/0.5, reply delays 1s/30s, fixed interruption equivalent 5s and Jev threshold 0.5.
- Physical oracle: 26/26; full offline suite: 226 passed. Public/raw-derived payload isolation, no oracle input, ASK freeze, gate order and shared budget limits verified.
- 48 real gate-only cases all returned CONTINUE; no decision-level effect observed in the small 2x2 contract/summary ablation.
- Corrected study: 12/12 valid physical model episodes succeeded, four per method. Mean burden: NoAsk 0, LLM-Gate 0.5, Jev-Gate 0.5. Mean operational cost: 56.37s / 60.63s / 94.48s. Gates asked in half-speed cases; Jev asked after four inspections. Planner path variation prevents attributing all cost differences to timing. One map and one seeded target only.
- Technical incident preserved separately: the initial JSON-mode Action prompt lacked the required JSON marker. One HTTP 400 led to 12 pre-motion aborted launches. A format-only amendment retained 48 gate results and six launch-stage requests, then allowed 12 valid navigation launches. Combined launch registrations 24, completed physical model episodes 12, total model requests 172/200. No frozen-setting/threshold tuning or Test API run.
- [Actual report, raw data and full incident accounting](../outputs/navigation_dev_v2/README.md). [Implementation/reproduction](navigation_dev_v2.md). The original HTML controller remains v1; v2 has a separate read-only experiment report.
