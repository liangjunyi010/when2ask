# Phase 2 interfaces and reproducibility

The robot/controller and generated collision geometry from Phase 1 remain the
execution backend. Formal methods are `llm_noask`, `llm_gate`, `jev_gate`.

## Public boundary

`Sample` owns private `theta_star`, slot registry and DAG. `observe()` receives
only the environment, `u0` and public history. `public_payload()` projects visible
IDs/categories/colors, measured AABBs/positions, measured spatial relations and
the public history. The three methods use that exact projection. Neither sample
metadata nor evaluator labels are injected into inference requests.

The shared public task contract states that one fixed user preference exists for
each role. It provides no correct choices. Question resolution privately maps a
public role and its visible candidates onto a task slot. Select/confirm questions
access only requested theta keys. `all_preferences` explicitly requests all three.
Burden counts distinct slots within one question, and charges repeats again.

`Gate.decide(PublicState)` can return ASK/CONTINUE only. NoAsk instantiates no gate.
The runner calls the gate before either shared planner method. Only the action
planner produces DONE. Action and question prompts/configuration are identical
across methods; their hashes and every actual inference request are retained.

## Official REST contracts

- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/):
  `POST /chat/completions`, JSON-object output, explicit JSON instructions and
  bounded output tokens. We use `thinking={"type":"disabled"}`, temperature 0,
  500 tokens for planner output and 64 for gate output. Live requests confirmed
  this parameter combination and the `deepseek-flash` alias.
- [TypeSafe Noul](https://docs.typesafe.ai/primitives/noul) and
  [OpenAPI](https://api.typesafe.ai/openapi.json): discover models with
  `GET /v1/models`, then send state/model/questions to `POST /v1/systemone`.
  The gate uses exactly `answers.needs_clarification.noul >= threshold`, with a
  finite numeric range check. The default threshold stays 0.5.
- The API returned `deepseek-flash` as DeepSeek's model string and `jev-1.14.0`
  for configured `jev-latest`. DeepSeek reports an alias, not a fully versioned
  backend build. Model catalogs and raw returned-model fields are preserved.

No third-party API SDK was added. The standard-library HTTPS transport has a
40-second request timeout. Each logical request gets at most one retry, including
format repair. No hidden SDK retries can exceed the attempt budget.

## Budgets, costs and errors

Per-episode defaults: 20 rounds, 12 physical actions, 12 requested slots, 64 HTTP
attempts. Counters are checked before the corresponding call/action/disclosure.
A file-locked session ledger reserves each authenticated request before network
I/O. This study is capped at 12 episodes / 200 requests, including discovery,
smokes, probes, repairs and retries. Completed episodes are not overwritten.

Authentication/payment/invalid-endpoint errors block that backend immediately.
Three consecutive unsuccessful responses also block further paid calls to it.
Transport errors, schema errors, actual usage, local monotonic latency, retries,
and incomplete reservations are logged. Unknown usage is null. Each backend's
input/output tokens stay separate; these counts are not interchangeable dollars.

User-simulator calls have measured local wall time and zero API attempts, with
token fields null. Generation is offline and has its own timing/hash manifest.
Oracle physics time is retained per trace. These are excluded from agent cost.

## Data and physics scope

There are five hand-designed validation conditions and twenty controlled pilot
instances. All support only the validated pack-and-cover DAG. Source jitter is
bounded to ±4 mm. IDs, candidate order, preferences, disclosure and wording vary.
Intent-equivalent instances, ignoring aliases/disclosure/wording/jitter, share a
group. Five intent families are validation-only; three are pilot dev/test groups.
This is a narrow primitive-scene pilot, not a broad independent task distribution.

The original red-cup position allowed hand/box-rim interference. Benchmark scene
v2 moves that source to (0.38, -0.12), while default Phase 1 geometry is unchanged.
Initial failed oracle records are retained separately. All current 25 scenes then
passed actual deterministic oracle execution.

`pick_place(..., "table", "on")` returns an object/lid to its original safe source
by real motion, enabling recovery. Regrasping a short object inside the box uses
35 mm clearance above its top so the wider hand stays above the rim. The original
25 mm tracking / 40 mm hand-to-object proximity guards still apply. No runtime
object pose reset is used.

Evaluator checks final geometry/contacts/release plus the latest relevant real
cover event and preceding physical packing events. A corrected historical mistake
does not invalidate the final task. Success and termination reason are independent;
a genuinely complete state can pass at a budget boundary without DONE.

## Offline and live commands

```bash
source .venv/bin/activate
python -m when2ask doctor
python -m when2ask doctor --live
python -m when2ask generate --split validation --count 5 --seed 42
python -m when2ask generate --split pilot --count 20 --seed 42
python -m when2ask validate --split validation --oracle
python -m when2ask validate --split pilot --oracle
python -m when2ask run --sample validation_002 --method llm_noask --live
python -m when2ask run --sample validation_002 --method llm_gate --live
python -m when2ask run --sample validation_002 --method jev_gate --live
python -m when2ask report --run-dir outputs/phase2_live/paired_v2
python -m pytest -q --junitxml=outputs/phase2/pytest.xml
python scripts/verify_phase2.py
python scripts/secret_scan.py
```

`scripts/run_pilot.py --live` resumes the predeclared v2 paired plan. Already
completed matching episodes are retained without extra API calls. A fresh run
needs its own explicitly bounded session; the current session has reached its
12-episode ceiling. Do not pool prompt versions: report rejects mixed configurations.

Local credentials are merged into ignored `.env` with permission 0600; safe names
and placeholders are in `.env.example`. Headers and credentials are never written
to source/audit records. Offline pytest blocks urllib network access globally and
uses explicitly labeled test doubles for adapter/runner contracts. Success tests
and negative/recovery tests still use actual Bullet dynamics.
