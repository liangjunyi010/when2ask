# Navigation Dev v2: cost-aware clarification timing

Independent of the frozen tabletop experiment and Navigation Dev v1. Original
prompts, source modules, configurations, datasets and historical logs are not edited.
All v2 modules use the `nav2_` prefix, including an independent CLI/study runner.

## What controls the robot

DeepSeek chooses a station via `search(location_id)` or outputs DONE. Jev/DeepSeek
gate chooses ASK/CONTINUE before any planner call. A shared deterministic known-map
route traverses room centers and doorways, then a wheel-speed controller drives the
actual Husky rigid body. Local detection uses geometric range/FOV/collision-ray LOS,
not image recognition. The task ends at found-and-approached, without pickup.

The same validated v1 geometry, detector and physical evaluator are reused through a
subclass. A speed factor multiplies the actual left/right wheel motor targets;
physics timestep stays 1/240s. Online physical motion is paced at 1x, not accelerated
playback. Slower control has proportionately larger finite controller-step limits.
No body pose is reset after scene initialization.

## Public objective and costs

The candidate set is exactly six stations with a **stipulated uniform planning
prior**. Negative inspection rules out that station only. This replaces implicit
kitchen-first reasoning for the controlled study. It is not a population-frequency
claim. Exact reliable location answers are world facts; the target never relocates.

First require physical success. The prespecified operational score is:

`simulated motion seconds + actual reply-wait seconds + 5 seconds × requested slots`

The 5s interruption equivalent is a declared experimental setting, not a measured
human utility. Failure also incurs a reported 300s penalty; success, raw score and
penalized score are all retained. Actual end-to-end wall time and API costs are
reported separately. Each backend's tokens remain separate. The physics is paced
at 1x online, but the simulation-time and wall-time columns are still distinct.

Four public cost cells: motor speed factors **1 / 0.5**, crossed with automatic
reply delays **1s / 30s**. Reply delay is an experimental cost variable, not a
required navigation feature or an empirical human-response estimate. The existing
interactive console is unchanged; its quick/manual replies still work as before.
No simulation step is executed during model inference or user waiting.

Both gates ask the same cost question:

- ASK: asking now has strictly lower expected **remaining** operational cost.
- CONTINUE: autonomous progress has equal/lower expected remaining cost, or complete.

Useful exploration can coexist with valuable clarification; its existence does not
by itself determine the gate. Ties continue. No fixed failed-search count, oracle
override, pre-generated action or Jev-only reasoning is introduced.

## Public summary and diagnostic reference

Raw serialization contains the instruction, measured observation, full public
history, cost model parameters, uniform prior, response contract and limits.
Summary serialization adds deterministic public derivations: negative/remaining
stations, posterior conditioned on observations/answers, per-station estimated motion
cost, remaining budgets and prior requests. Both methods receive the same facts.
The cost estimates use public geometry/robot pose and nominal linear/angular rates;
they are approximate and not hidden-target physical rollout costs.

An **offline diagnostic** dynamic program compares asking with continued search
under the stated finite public prior/cost model. It never reads target truth and
its values/decision are never supplied to Gate or Planner. Reference match/regret
indicate agreement with that approximate model, not physical optimality or human
ground truth. Real end-to-end physical metrics remain the main execution evidence.

## Prespecified experiment, without result-based selection

- 24 physical sample conditions: six target placements × four cost cells. All share
  the original **one** map group. Two extra full autonomous sweeps verify that NoAsk
  can find the last station at both speeds within the same 36m budget.
- Gate-only ablation: six measured public states (four initial cost cells and two
  normal-speed post-negative states), crossed with two contracts, two payload forms
  and two backends: **48 logical calls**. Jobs are shuffled with seed 20261106.
- The `overlap_control` retains v1-style ambiguous gate logic but shares the new
  factual/cost context. It is **not** an exact frozen-v1 prompt replay. The comparison
  isolates contract logic and public derivation, rather than silently mixing a 3s
  hardcoded old instruction with a 30s new scene.
- End-to-end comparison: four cost cells × three methods = **12 episodes**. A single
  target (`study_shelf`) is chosen by the declared seed before calls and reused across
  all four cells, isolating cost effects. This is one map/target controlled case,
  not twelve independent navigation scenarios.
- Full episodes always use **cost_exclusive + summary**; no picking a variant based
  on which produces more Jev questions. Threshold **0.5 stays fixed**.
- Hard cap: **200 authenticated requests total**, including retries: at most 60 for
  ablation and 140 for episodes. At most 12 full model episodes; 32 attempts/episode,
  20 rounds, 8 actions, 4 slot requests, 36m. One retry, 40s request timeout, backend
  circuit breaker after permanent/three consecutive errors. No discovery calls.
- Three methods reset independent Bullet worlds and run concurrently per cost cell;
  method/cell order is seeded-shuffled. Planner, question schema, costs and evaluator
  are identical. No formal Test API episodes run.

## Commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/navigation_dev_v2.py oracle --output-dir outputs/navigation_dev_v2/oracle_NEW
.venv/bin/python scripts/navigation_dev_v2.py prepare
.venv/bin/python scripts/navigation_dev_v2.py check
.venv/bin/python scripts/navigation_dev_v2.py ablation --live
.venv/bin/python scripts/navigation_dev_v2.py episodes --live
.venv/bin/python scripts/navigation_dev_v2.py report
```

Prepare refuses to overwrite a plan. Live stages refuse implicit reruns. Check pins
source, prompt, configuration, dataset and measured-snapshot hashes before calls.
Actual requests/responses, model names, usage, failures and latency are retained.
Outputs are under `outputs/navigation_dev_v2/`; read-only HTML/CSV/JSON reports can be
served locally. This version does not replace the v1 command center.

## Interpretation

Ask count is a diagnostic, never the optimization target. A gate can correctly ask
less, more or never, depending on the declared costs and evidence. Report success,
travel, motion time, waiting, burden, API time and per-backend tokens together.
One layout/target does not support independent-group statistical significance.
Future work needs independent maps/target placements, delay and prior sensitivity,
and separate Dev/Test grouping. No simulated number represents a real hardware or
learned-vision result. Husky/Bullet asset attribution is unchanged from
[Navigation Dev v1](navigation_dev_v1.md).

## JSON-mode technical correction

The initial run (`study_v1`, code 317ecd9) completed 48 Gate-only calls, but its
first Action request returned HTTP 400 because the prompt omitted the literal JSON
marker required by JSON-object mode. The backend circuit breaker stopped further
DeepSeek requests; all 12 registered launches ended before any physical action.
All six launch-stage requests and all aborted traces remain preserved.

Code b1d1c62 adds only the required JSON format marker to Action/Question prompts,
adds regression tests, and registers a separate amended run (`study_v2`). Gate and
criteria hashes, snapshot/dataset hashes, scene/cost factors, seed and threshold are
identical. The 48 successful gate cases are copied unchanged and not called again.

The amendment explicitly allows 12 valid physical launches after the 12 pre-motion
aborts (24 combined registrations). Total authenticated requests across both runs
remain capped at 200: a 54-request offset leaves at most 146 new attempts, including
at most 140 for valid episodes. The old ledger and raw logs are never reset or edited.
The failed launches are reported as a protocol incident separately from valid physical
method comparisons. This is not a gate/policy tuning round.

Use `--output-dir outputs/navigation_dev_v2/study_v2` when inspecting the corrected
study; the CLI defaults there. Existing plans/stages intentionally refuse overwrites.
The read-only report and `ANALYSIS.md` distinguish real model runs, gate-only calls,
modeled-wait unpaid policy anchors, and the technical incident.
