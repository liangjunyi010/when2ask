# Observation Memory & Completion Dev v6 — 2026-11-11

The original default and v5 remain available. The new opt-in **PLANNER PROFILE → Memory Dev v6** supports buffered exchange, retrieve/restore and occlusion inspection. Auto/Human answering and the three-method comparison button are preserved. Main console: http://127.0.0.1:8877/. New recorded paired results: http://127.0.0.1:8896/?comparison=2a887ccd10544e07.

## What caused the loops

**Retrieval:** v5's `current_locations` was built from `affordances.move`. After covering, the legacy observation hides both stored-item geometry entries, even the delivered item outside the box. The public delivery-zone contents still report that item, but v5 drops it from the location summary. Compacting older physical history further weakens the evidence that delivery has happened. On the actual v5 LLM-Gate round4, the block is still listed in `delivery_pad`, the lid spans the opening, and the latest cover succeeded; nevertheless the model reopens the box. All three methods then used12 actions, including five reopens, ending with the lid parked.

**Buffered exchange:** this is a different failure. In v5 Jev round4 both objects are already measured at their absolute final destinations and the pads are empty. The model copies the correct target map but generates another relative "exchange", moving the completed object out again. Copying state/goal fields was not sufficient to make the model assess completion. It eventually repairs the state but takes7 actions, with2 regressions. The gate had already asked correctly; this extra motion was an action-planning failure.

Actual old/new fields, model outputs and source pointers are exported automatically in [root_cause_evidence.json](../outputs/memory_planner_dev_v6/root_cause_evidence.json). Old episodes are read, never rewritten.

## Independent repair

`memory_dev_public.py` consumes only the current public input and earlier actual public observation snapshots from the same episode:

- Current region membership is independent of individual-body geometry and grasp availability. A measured delivery-zone member remains located there even if the body is omitted from the current grasp list. Affordances themselves are unchanged.
- Each object's memory records status (`observed_now`, `remembered_occluded`, `unknown`, `unknown_after_action`), region, source and observation step. Never-seen hidden contents remain unknown. Past contents are not presented as fresh vision through a lid.
- Current positive/negative region observations override old memory. Later failed actions invalidate unseen remembered locations; a moved unseen object's old placement is also invalidated. A successful action is not automatically promoted to a new measured placement.
- User-confirmed choices remain separate from guesses inferred from the agent's own prior successful actions. All user dialogue, observed region visits, latest action per object and aggregate action coverage remain available.
- Buffered exchange has explicit absolute final relations and current measurement booleans. Retrieval retains current delivery evidence, earlier observed box contents, lid AABB geometry and actual action/visit chronology. These are public facts, not private task scores or prescribed next actions.

`memory_dev_agents.py` makes the **shared model** assess whether it can finish before planning another action. Its JSON contains working choices, `completion_assessment` and a remaining suffix. It explicitly distinguishes `cover(lid)` from ordinary `move(lid, box)`, which places inside a container and does not mean covering.

The controller never forces DONE, rewrites an action, rejects it for regression, executes a cached suffix or consults private truth. Even a schema-valid regressive action paired with a model assessment saying "complete" is accepted unchanged by the wrapper; an offline test verifies this. Every turn still gates first, then plans; only the first model action executes. The independent unchanged evaluator checks actual geometry/contact/order and may reject a model's DONE.

Original `task6_world`, worker, IK/skills, evaluator, scripted policies, default agents/controller and every v5 file are byte-identical. v6 reuses the already isolated schema-aware API health wrapper. Gate/Question **prompt hashes are identical to v5**, threshold stays0.5, and all three methods share the same v6 serializer/planner. Public input changes, so gate decisions can still change. No formal Test settings were altered.

## Checks before the nine full episodes

- Baseline327 offline tests passed. Full updated suite343 passed; final16 targeted tests passed again after clarifying cover semantics. Pytest makes no paid calls.
- Three real physical controls use existing skills and the independent evaluator;3/3 succeed. These are explicitly scripted diagnostic controls, not model results.
- Chrome1920×1080 and mobile390px regression: three scripted-policy/real-PyBullet tasks, two browser-operated manual replies, unchanged frame/state during ASK, terminal-only truth, no console errors or horizontal overflow. Main controller compatibility restores all10 historical cards, preserves Default v1 and the v5 option, and exposes v6 without a paid launch.
- Two rounds of six **real API action-only probes** use old recorded public states. Round1 matches5/6: the pending-lid case used ordinary `move(lid, box)`. That mismatch and its raw response remain in `probes/`. After the cover-semantic clarification, round2 matches6/6, including both disclosed and guessed completed retrieval states, completed exchange, unfinished exchange, pending cover and completed inspection. Probes are not physics episodes or success-rate samples. All12 requests debit the same persistent150-request ledger used below.

## Nine new real paired episodes

The final code/prompts/source hashes/model configuration/budgets and group order were locked before full episodes in [live_plan.json](../outputs/memory_planner_dev_v6/live_plan.json), implementation commit `1a69c3ca841654da3031a361d5dc00653461193b`. Three unchanged fixed Dev samples (seed4278), one unknown preference/fact each, independent resets, same truth per paired task, Auto replies. Each group was launched using the actual HTML three-method button. No full episode was rerun, removed or patched midway.

| Task | LLM-NoAsk | LLM-Gate | Jev-Gate |
|---|---|---|---|
| Buffered exchange | Fail; burden0;3 actions | Success; burden1;3 actions | Fail; burden0;3 actions |
| Retrieve & restore | Fail; burden0;3 actions | Success; burden1;3 actions | Success; burden1;3 actions |
| Occlusion inspection | Success; burden0;3 actions | Success; burden0;3 actions | Success; burden0;3 actions |

**All27 real skills succeeded. All9 episodes reached model-generated DONE in3 physical actions. Reopens after cover:0. Moves undoing completed exchange relations:0.** Actual task success is6/9, because correct execution under a wrong preference guess is still independently unsuccessful.

- Retrieval: both gates open first, then ask which item. Jev p0.13 CONTINUE → p0.76 ASK. Both deliver the selected block, cover and finish. NoAsk instead selects the cup and physically completes under that guess; it scores false, with the lid correctly restored.
- Exchange: LLM-Gate asks before choosing the pad and succeeds. Jev's first p0.43 is below0.5, so it does not ask and uses the wrong pad, as does NoAsk. Both still exchange the objects cleanly in3 actions and stop. **The motion loop is repaired in this sample; Jev's clarification timing remains a real failure.** No threshold adjustment, forced ASK or rerun was used to hide it.
- Occlusion: all methods continue, clear the screen, physically inspect and report the measured code, then finish without asking. A user hint never substitutes for inspection.

### Actual episode inference cost (cumulative across3 episodes per method)

| Method | Success | Total burden | DeepSeek input/output | Jev input/output | API latency |
|---|---:|---:|---:|---:|---:|
| LLM-NoAsk | 1/3 | 0 | 35,980 / 1,177 | — | 13.52s |
| LLM-Gate | 3/3 | 2 | 75,530 / 1,397 | — | 29.00s |
| Jev-Gate | 2/3 | 1 | 38,988 / 1,221 | 45,001 / 312 | 18.85s |

The nine episodes used66 requests, zero schema/API errors/retries. The12 probes separately used38,820 DeepSeek input and1,027 output tokens,14.11s API latency. **Total78/150 authenticated requests, exactly9 full episodes, zero aborted/repeated full episodes.** Total backend usage: DeepSeek189,318 input/4,822 output; Jev45,001 input/312 output. Actual returned models: `deepseek-flash` and `jev-1.14.0`. Backend tokens are not interchangeable dollar costs; all latencies are observed, not guarantees.

## Interpretation and remaining limits

This is a three-group engineering regression, not proof of general planner reliability or a statistical comparison of gates. v6 changes memory, the completion contract/output schema and cover semantics together; the experiment does not isolate each change's causal effect. The same fixed scenes as v5 enable a useful regression comparison, but are not additional independent groups. [Automatically linked historical comparison](../outputs/memory_planner_dev_v6/historical_comparison.json) preserves every old result, including the old successful Jev buffer task that becomes a preference failure here.

The old world's visibility mask is still coarse; v6 repairs public-state interpretation, not that legacy geometry/affordance policy. Remembered occluded positions may be stale after unobserved interactions; failed-action invalidation is conservative and the independent physical evaluator remains necessary. Neither model completion reasoning nor these few successful physical runs establish a general safety/completeness guarantee. Gate probabilities can depend on public-state framing; the buffer p0.43 miss needs broader independent Dev diagnosis, not a post-hoc threshold change for this case. Frozen formal Test data/configuration and all historical experiments are untouched.

## Evidence and reproducible checks

- [Automatic raw-derived report](../outputs/memory_planner_dev_v6/report.md), [summary/cost JSON](../outputs/memory_planner_dev_v6/summary.json), [episode CSV](../outputs/memory_planner_dev_v6/episodes.csv), [wire/memory mapping audit](../outputs/memory_planner_dev_v6/mapping_validation.json).
- Every `live/<task>__<method>/` contains episode/API attempts/physical trace/evaluation/review and real scene/final screenshots. All wire inputs match their saved public payload; all three initial payloads match within a paired task; memory recomputes from actual preceding public observations; first model action executes verbatim; ASK leaves the physical state unchanged.
- [Nine actual physical MP4 recordings](../presentation/memory_dev_v6/README.md). Videos use simulation time, not API/ASK wall time; dialogue is in episode logs.
- 2,346 protected existing files hash-identical, including v5 and older studies, frozen datasets/prompts/configs, stable physics/evaluator and the user's already-modified PPT. Secrets remain ignored/private; no Test API calls.

Actual commands: `.venv/bin/python -m pytest -q`; `.venv/bin/python -m pytest tests/test_memory_dev_v6.py -q`; `node scripts/memory_dev_browser_check.mjs`; `.venv/bin/python scripts/memory_dev_probes.py --live` and `--revision r2`; `.venv/bin/python scripts/memory_dev_plan.py`; `node scripts/memory_dev_live_check.mjs --live`; `.venv/bin/python scripts/memory_dev_report.py --export-media`; `node scripts/memory_dev_main_check.mjs`. Node is the bundled runtime; online harnesses refuse to overwrite existing results. A new online series needs a new namespace and locked plan. Offline aggregation is rerunnable and does not call APIs.
