# Console clarification and episode-review verification

Exactly three real-model episodes, one per template with the methods rotated. This is UI/transport/physics smoke verification, **not** a three-method benchmark ranking. All original frozen studies, navigation studies, model prompts, thresholds and physical controllers remain unchanged.

| Task | Method | Success | ASK turns | Burden | Timing observation |
|---|---|---:|---:|---:|---|
| Pack and cover | LLM-Gate | true | 1 | 2 | Asked at round 0 before executing the publicly specified cup: premature asking remains |
| Two selected containers | Jev-Gate | true | 1 | 1 | Continued at p=0.33, placed known cup, then asked block at p=0.54 |
| Find and approach | LLM-NoAsk | true | 0 | 0 | Autonomous search; no Gate or question by design |

Total: **22 authenticated requests**, no retries/API/schema errors. Operator input was submitted through real Chromium by browser automation, acting as the manual operator; no human-subject study or model-generated user reply is claimed. Exact input text, question IDs, normalized choices and simulation steps are retained.

The two text forms were actually used (`green block, black lid`; `green block`). ASK observations and rendered-frame hashes stayed identical while waiting. Draft text survived refresh, duplicate submission was idempotent, and complete conversations/ground truth rendered after termination. The completed views survived controller restart with **zero new model calls**. Full offline pytest: **241 passed**.

## What changed

- Human mode now clearly says it waits for a real ASK; NoAsk never asks, and automatic three-method comparison uses Auto regardless of the individual-task reply selector.
- A pending question supports typed public candidate names/IDs/colors or explicit dropdown choices. Ambiguous text gets an error, with no extra model call. This is conservative structured grounding, not general natural-language command parsing.
- Each card shows a persistent interaction explanation, a final evaluated-goal preview, and a **指令 · 完整对话 · Ground Truth** button. The modal contains the verbatim generated initial instruction, public ID/name legend, every Gate/question/answer/action/outcome and independent physical conditions. The queue handles **pending** questions; it is not the permanent conversation archive.
- Hidden reference preferences/location are withheld until the task terminates. They are observer-only review data and never added to agent public payloads. For tabletop manual mode, initial reference and human-declared effective scoring goals are both shown; navigation truth stays fixed even if a human hint is wrong.
- `review.json`, `final_view.json` and the episode review persist on disk. A restarted controller restores completed tasks as read-only views. Resuming an interrupted active physical world remains unsupported.

## Remaining policy problem

Selecting Human does not force ASK. Prior user trials with only the lid preference hidden ended without asking and failed; their missing form was a genuine missing model question, not a lost user input box. Even this successful Pack-and-cover smoke asked too early. UI visibility and input are verified; clarification timing is not universally reliable, and no threshold or rule was changed to manufacture an ASK.

## Evidence and local entry

- [Live browser validation](validation.json), [restart restoration](restore_validation.json), [integrity/privacy checks](integrity.json), [summary CSV](summary.csv), [pytest](pytest.xml).
- Per-template folders contain untouched new-run episode JSON, API JSONL, full review JSON and final actual PyBullet image.
- Interactive console: http://127.0.0.1:8877/ . Its three completed smoke runs are restored as read-only cards; a separate fresh interactive budget is available only when the operator explicitly launches a new live task. No extra model episodes were automatically run.
