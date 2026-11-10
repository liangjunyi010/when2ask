# Optional Grounded Dev Planner v5 (2026-11-10)

The command center offers **PLANNER PROFILE → Grounded Dev v5** for buffered exchange, retrieve/restore and occlusion inspection. **Original / Default v1 remains selected on page load.** Unsupported task changes reset to Default v1; the server rejects incompatible requests. Single-task Auto/Human and automatic three-method comparison retain their existing routing. Human forms appear only after an actual ASK; NoAsk never forces one.

This is an independent development candidate, not the frozen benchmark configuration. The three methods share one serializer, action/question planner, physical worker and evaluator. NoAsk skips the gate. Jev threshold remains 0.5. Every CONTINUE makes a new planner call after the gate and executes only the first proposed action. The suffix is recorded, never cached. There is no scripted fallback, action rewriting, progress rejection or private answer access.

## Public grounding

`grounded_dev_public.py` accepts only instruction, observation and public history. It retains measured geometry/affordances, all user dialogue, the latest physical result, aggregate action counts and public goal requirements. It distinguishes confirmed choices from working guesses, public candidate identities from visible movable bodies, unobserved contents from empty containers, and world facts from preferences. Lid AABB/opening measurements are explicitly geometry, not evaluator labels.

The shared action model returns current measured locations, public goal requirements, working preference choices and a 1–6-action remaining plan. Grounding checks public facts and schema; a schema-valid regressive action is accepted unchanged. Action output cap650, question300, DeepSeek gate64, temperature0, non-thinking JSON. These are Dev-only parameters, equal across methods.

`grounded_dev_console.py` preserves the original controller's budgets, finite waits, answer routing, ASK freeze and independent physical scoring. Original task6 agents/controller/world/skills/evaluator and buffer Dev v2/v3/v4 files are unchanged. Raw public input, model input, structured output and first executed action are saved for every turn.

## Real nine-episode paired study (revision r2)

Each task uses one fixed existing Dev sample, seed4278, one unknown slot/fact, identical truth and reset across methods. Auto answers only. Groups were shuffled before launch; each group was launched with the actual HTML three-method button. Configuration, source/prompt/dataset hashes and limits were frozen before requests in [live_plan_r2.json](../outputs/grounded_planner_dev_v5/live_plan_r2.json), implementation commit `216e2cfc2b60847b7e202efa34d7e7dbdbc3f49d`.

| Task | LLM-NoAsk | LLM-Gate | Jev-Gate |
|---|---|---|---|
| Buffered exchange | Fail; burden0; 3 actions | Success; burden1; 3 actions | Success; burden1; 7 actions |
| Retrieve & restore | Fail; burden0; 12 actions | Fail; burden1; 12 actions | Fail; burden1; 12 actions |
| Occlusion inspection | Success; burden0; 3 actions | Success; burden0; 3 actions | Success; burden0; 3 actions |

| Method | Success | Total burden | DeepSeek input/output | Jev input/output | Cumulative API latency |
|---|---:|---:|---:|---:|---:|
| LLM-NoAsk | 1/3 | 0 | 52,049 / 2,540 | — | 24.65s |
| LLM-Gate | 2/3 | 2 | 108,202 / 2,796 | — | 45.68s |
| Jev-Gate | 2/3 | 2 | 69,581 / 3,127 | 87,463 / 648 | 42.44s |

Nine r2 episodes used121 authenticated attempts, zero schema/API errors or retries. Actual returned models: `deepseek-flash`, `jev-1.14.0`. Backend tokens remain separate; latency includes all inference stages and is not dollar cost. No formal Test calls were made. Three fixed paired groups are engineering evidence, not a general ranking.

### Timing versus planning

- **Exchange:** both gates ask before selecting the temporary pad; Jev p0.53. NoAsk physically exchanges the objects in three actions but guesses the unselected pad, so independent preference/order conditions fail. Jev asks correctly but later undoes completed placements, then physically repairs them in seven actions. The structured planner reduces neither all regressions nor all costs reliably.
- **Retrieval:** both gates first open the box, then ask which item; Jev p0.12 CONTINUE → p0.81 ASK. Each correctly delivers the selected block and covers the box, then reopens it. The final action budget expires with the lid parked. The two gate failures are `box_reclosed`, not missing preference information. NoAsk additionally guesses the wrong item.
- **Occlusion:** all methods move the screen, physically inspect the label with the existing range/raycast sensor, report its measured code, then DONE. Both gates continue throughout. No clarification is needed because a useful required sensing action resolves the fact.

### Remaining generalization defect

After re-covering, the legacy observation hides both stored-item object entries. The public delivery-zone contents still contain the delivered item, but v5's `current_locations` includes only currently movable/visible IDs. This asymmetric summary, together with compacted physical history, can make the planner restart retrieval. Current observations and complete raw history are retained in the evidence; the study did not patch inputs/prompts midway. A next independent revision should preserve publicly measured region membership and explicitly typed last-observed object memory across occlusion, with timestamp/source and uncertainty. It must still permit real failures and verify DONE without evaluator/private data. The current Dev option is **not a generally reliable planner**; use Default v1 or inspect this documented limitation before choosing retrieval for a live demonstration.

## Preserved initial failure and amendment

The first r1 group had three aborted real episodes, six paid attempts. The model incorrectly included a world fact in `working_choices`. Concurrent HTTP-200 schema failures tripped the legacy global backend-outage breaker before all format repairs could run. All raw failures and their original locked plan remain in [preflight_r1](../outputs/grounded_planner_dev_v5/preflight_r1) and [live_plan.json](../outputs/grounded_planner_dev_v5/live_plan.json).

The r2 amendment adds explicit public preference/world-fact role lists and an empty-choice rule for world facts. A Dev-only session proxy classifies HTTP-200 schema errors separately from backend outages; every attempt still debits the ledger, and real authentication/network failures retain the original breaker. The default implementation is untouched. The nine r2 episodes are a separate fixed series; no r2 episode was rerun. **Total work:12 real launches (3 aborted r1 + 9 r2),127 paid requests**, within the cumulative150-request ceiling. The additional three debug launches exceed the initially intended nine total launches and are explicitly retained rather than excluded from cost accounting.

## Validation and evidence

- Original311 tests passed before edits; final327 offline tests passed. No paid requests in pytest.
- Final Chrome desktop/mobile regression: three scripted policies with actual PyBullet, two manual answers, state/frame equality during ASK, terminal-only ground truth, no JS errors or horizontal overflow. These are explicitly **scripted UI diagnostics**, not model results.
- Live Chrome study: nine real API/PyBullet episodes; all wire inputs match saved public payloads. Initial model inputs match across methods within each task. Gate order, exact first-action execution and ASK freeze audited.
- 2,181 protected existing files hash-identical, including frozen data/configs, historical experiments, stable physics and the user's already-modified PowerPoint.
- [Automatic results and per-turn audit](../outputs/grounded_planner_dev_v5/report.md), [machine-readable summary](../outputs/grounded_planner_dev_v5/summary.json), [paired CSV](../outputs/grounded_planner_dev_v5/episodes.csv), [mapping audit](../outputs/grounded_planner_dev_v5/mapping_validation.json).
- [Nine actual physical MP4 recordings](../presentation/grounded_dev_v5/README.md). These show physical simulation time, not API/human waiting time; full dialogue and gates are in episode logs.

Reproduce offline checks with `.venv/bin/python -m pytest -q` and `.venv/bin/python scripts/grounded_dev_report.py --export-media`. Start an interactive session with `.venv/bin/python console.py --live`, open http://127.0.0.1:8877/, choose one supported task, then explicitly select the Dev profile. Recorded online runs used `node scripts/grounded_dev_live_check.mjs --live`; the harness refuses to overwrite evidence or repeat the study in place. A new study needs a new output namespace and a new locked manifest.
