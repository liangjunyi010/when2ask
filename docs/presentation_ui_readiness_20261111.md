# Presentation UI readiness — 2026-11-11

This read-only audit used actual Chromium rendering against the running local services. It launched no task, made no model request, and did not modify the frozen research protocol or raw results.

## Current verified state

| Surface | Actual observation |
|---|---|
| Main console, port8877 | Renders without JavaScript errors; desktop1920×1080 and mobile390×844 have no page overflow. Nine task templates are available. UI is still mixed Chinese/English and declares `lang=zh-CN`. |
| Episode review | Initial instruction, model decisions, questions, user answers, physical results, task DAG where supported, and terminal-only Ground Truth are present. No new live/manual interaction was executed in this audit. |
| Live defaults | Original/Default v1 and Scripted ASK selected on page load. v5/v6/v7 are selectable for the three supported newer tasks; the default is deliberately preserved. |
| Dashboard state | Ten archived tasks are restored, with8/10 scored successes and no active task. Those mixed historical/session outcomes are not the v8 paired benchmark result. Current live budget starts at0/60requests and0/6episodes. |
| v8 result gallery, port8900 | English, three result rows, three recorded cases, all nine actual MP4s decoded in Chrome; no JavaScript errors. Read-only: no model request. |
| New presentation replay | Independent English frame-synchronized replay at port8901 under `presentation/final_benchmark/web/`, with existing mapping, playback-control and native PowerPoint evidence. |

The v8 held-out layouts are not selectable as live tasks in the main console. Re-running a lookalike free-demo layout does not reproduce a frozen Test sample. Use the results gallery to show those already evaluated Test cases and a clearly marked fresh Dev run for interaction.

## Highest-priority presentation changes

1. **English throughout.** Translate the static HTML, dynamically generated JavaScript labels, template catalogue names, server-generated interaction messages and Ground Truth descriptions. Merely changing the HTML language attribute does not translate the interface. User/model original utterances should remain verbatim.
2. **One clear presentation entry.** Provide `Live Demo`, `Benchmark Results` and `Recorded Replay` navigation. Keep the three v8 task names consistent with the deck. A recommended Dev profile must be explicit, without silently replacing the original research default.
3. **Separate session outcomes from research results.** Label the restored8/10 as historical/session results, with policy/method provenance. Show v8 10/12,12/12,12/12 only under its actual paired benchmark manifest. Do not combine scripted and model runs into a method ranking.
4. **Rehearse one manual ASK flow and one no-ASK control.** The queue form should appear only after an actual ASK. Choosing Human does not force a question; NoAsk never asks. A pending task must show its question, request slots and routing; the form must resume the correct world while ASK leaves physics unchanged. This needs a fresh isolated rehearsal, not a fabricated probability or a forced ASK.
5. **Projector-readable presentation view.** Current operational status, task metadata, dialogue and flow labels often use8–12px fonts. Keep the normal console available, but provide a view that hides the launcher and old archived cards, enlarges critical text, and keeps the selected robot/methods, question/answer and final evaluation above the fold. Readability needs an actual1920×1080 screenshot check after English wording is applied.

All new interface copy should be English, e.g. `Start Mission`, `Compare Three Methods`, `Clarification Queue`, `Initial Instruction`, `Conversation`, `Ground Truth`, `Physical Evaluation`, and `Session Outcomes`.

## Research scope remaining

- The new three-task Test is complete:12 independent groups×3methods=36 actual model/physics episodes. This is a small, single-binary-slot held-out study.
- Exact first-ASK timing analysis remains exploratory; a future experiment should pre-register its timing criteria and extend independent layouts, slots and robustness conditions.
- Six other catalogue templates are outside this new paired Test. Original two-template128-Test is separately frozen and unrun. Neither has to be expanded tonight merely to show the working course prototype.
- Two-computer VPN deployment is not actually validated. Local controller/worker separation is implemented and tested; remote deployment must be described accordingly.

## Presentation consistency correction

The actual inspection DAG is **move screen → inspect label → report measured code**, leaving the screen parked. It does not restore the screen. Slide3 and its spoken narration were corrected to match the immutable dataset and execution trace. No task or evaluator was changed.
