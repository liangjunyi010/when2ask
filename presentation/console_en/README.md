# When2Ask — English presentation console

Open **http://127.0.0.1:8902/**. The service is running locally with real physics workers. The original console remains at8877 with its original display, defaults and records.

## Presentation controls

- **Live Demo** launches a fresh Dev task, selects the method and Auto/Human response mode, and supports the existing three-method paired comparison. The independent UI initially recommends Retrieve & Restore with Gate Dev v7; the original Default v1 remains selectable and the original application default is unchanged.
- **Presentation View** hides launch/history clutter, enlarges the current mission or paired methods, and keeps the clarification queue visible. **Mission Controls** reopens the launcher; **Exit Presentation** restores the full console. Click a camera for its expanded panoramic view.
- **Benchmark Results** reads the unchanged v8 held-out results:10/12,12/12,12/12 across12 independent groups. It keeps those results separate from session outcomes and the new one-scene rehearsal.
- **Recorded Replay** embeds the actual frame-indexed robot/Gate replay and all9 paired MP4s with their original conversations. No model call is made by opening these views. Videos support HTTP byte-range seeking.
- **Human** displays its answer form only when an actual ASK occurs. Type an English candidate name or select the requested slots. **Let Simulator Answer** is available for a pending manual question. NoAsk never asks. ASK freezes only its own world; other workers continue.
- **Instruction · Conversation · Ground Truth** opens the original instruction, full decisions/dialogue, DAG and independent physical scoring. Hidden truth appears only after termination. Interactive human preferences and fixed world facts retain the original evaluation semantics.

All interface copy is English. Original model/user utterances and raw evidence are retained verbatim. Backend messages are adapted only for display; no model input, question, action, gate probability or score is rewritten. UI flow nodes follow the same decoded worker frame/task packets as the preserved console, and replay nodes follow its original master timeline.

## Run from a fresh session

```bash
.venv/bin/python presentation_console.py --live --port 8902 \
  --api-limit 96 --live-episode-limit 6
```

Omit `--live` for explicitly scripted policies with real physics and no backend calls. The live three-method button requires live APIs and three remaining episode slots; comparisons use automatic responses. Budgets do not reset themselves. Credentials are loaded from the existing ignored `.env`, and never enter frontend files or Git. A fresh session is distinct from the frozen Test protocol.

The independent handler reuses the original task controller and worker APIs, serves only allowlisted presentation/evidence assets, and leaves `console.py`, `src/when2ask/`, frozen configurations and all previous results untouched. It binds to loopback by default. This delivery validates one-machine operation; two-computer VPN deployment remains future work.

## Actual rehearsal and checks

[Measured report and raw evidence](../../outputs/presentation_console_en/20261112/README.md): three offline real-physics UI cases passed; a real-model paired retrieval run scored NoAsk unsuccessful, LLM-Gate successful, Jev-Gate successful, with burden0/1/1. The model comparison used3 new Dev episodes and24 API requests, with no retry or inference error. These are rehearsal outcomes, not a new Benchmark ranking. The original frozen Test metrics are unchanged.

Project pytest:364 passed. Actual Chrome checks cover English text, view navigation, manual input/validation/routing, frozen physics during ASK, final truth, nine decoded MP4s, synchronized replay controls, and1920/1280/390px layouts. The old3121 tracked files were hash-checked unchanged. Initial UI QA failures and their final passing checks are retained in separate directories.

The current session has used3/6 live episode slots and24/96 API attempts, leaving room for one more three-method comparison. Remaining quota is always shown live by the controller; it is not automatically extended.

## Rebuild / verify without model calls

```bash
.venv/bin/python presentation/console_en/tools/build_frontend.py
.venv/bin/python -m pytest -q
node presentation/console_en/tools/check_views.mjs
```

Use the existing Codex-bundled Node/Playwright runtime for the browser checks. `check_views.mjs` reads the saved rehearsal comparison ID and never dispatches a task. `rehearse.mjs --attempt=NEW_NAME` explicitly starts scripted real-physics UI tasks; adding `--live` launches exactly one new three-method comparison and refuses to run after live episode slots have already been consumed in that session. Each attempt gets a separate evidence directory.

`tools/build_report.py` computes the rehearsal table from raw episode JSON and checks the preserved-source hashes. Its concrete session paths refer to this delivered rehearsal; use a separate namespace for a future study.
