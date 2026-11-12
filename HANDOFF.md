# Team 11 development handoff

**Liang Junyi and Yang Haocheng — 12 November 2026**

Repository: [liangjunyi010/when2ask](https://github.com/liangjunyi010/when2ask), **Private**.

The complete current development snapshot is on **`codex/team11-handoff`**. It contains all previous development branches in its history, including the English console, v8 benchmark and latest Team 11 presentation. `main` retains the original stable MVP. The existing stacked pull requests remain open and unmerged.

## Get the current project

An invited GitHub collaborator can use:

```bash
gh repo clone liangjunyi010/when2ask -- --branch codex/team11-handoff
cd when2ask
git switch -c feat/your-improvement
```

Or clone with Git:

```bash
git clone --branch codex/team11-handoff git@github.com:liangjunyi010/when2ask.git
```

Reading/pushing to this private repository requires an invitation to the correct GitHub account. The teammate's username is required to grant Write access; a real name is not enough to identify an account safely.

## Install and run without paid APIs

The validated platform is macOS Apple Silicon with Python 3.11. The runtime is a small Python project with PyBullet, NumPy and Pillow; pytest is the test dependency. See the original README for the macOS SDK workaround and pinned versions. Linux/Windows and a two-computer deployment have not been validated here.

```bash
bash scripts/setup_env.sh
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m when2ask doctor
.venv/bin/python -m pytest -q
.venv/bin/python presentation_console.py --port 8902
```

Open **http://127.0.0.1:8902/**. This starts the English console with **scripted policies and real physics**, with no model API requests. Benchmark Results and Recorded Replay read the saved evidence. Single scripted tasks and Auto/Human answers remain available. The live three-method comparison requires explicit `--live`, valid local credentials and sufficient configured budget.

The original standalone robot demo also works offline:

```bash
.venv/bin/python demo.py --mode ask --record --output-dir outputs/my-offline-demo
# Optional native PyBullet GUI:
.venv/bin/python demo.py --mode ask --gui
```

Environment creation installs packages only in this project's `.venv`. The editable install makes subsequent source edits visible to the Python CLI. No virtual environment from another machine is shipped. Node/Playwright is only needed for browser automation, and the bundled Artifact Tool is only needed to rerun the presentation authoring scripts. Neither is required to run the Python console or view the committed PowerPoint.

## Live models are opt-in

`.env`, API keys and worker/controller tokens are deliberately excluded from both Git and Release assets. `.env.example` contains safe variable names/placeholders. Use a private local environment for authorized API access; never put credentials in commits, issues, PRs or browser assets.

For an explicitly authorized new Dev session:

```bash
.venv/bin/python presentation_console.py --live --port 8902 \
  --api-limit 60 --live-episode-limit 6
```

The command starts the service; only a live task launch invokes models. Use a fresh output directory/session and retain failures. Opening a saved replay or results view does not call a model. Offline pytest blocks live network requests.

## Where to work

| Area | Entry points |
|---|---|
| English presentation UI | `presentation_console.py`, `presentation/console_en/web/` |
| Original controller and worker | `console.py`, `src/when2ask/console_server.py`, `console_worker.py`, `console_state.py` |
| Shared planning and gate contracts | `src/when2ask/agents.py`, `protocol.py`, `research_runner.py` and the opt-in Dev agent modules |
| Physics and skills | `src/when2ask/environment.py`, `skills.py`, task-specific world/skill modules |
| Task samples and private/public boundary | `benchmark.py`, `task.py`, `user_simulator.py`, `three_task_data.py` |
| Independent scoring | `evaluator.py` and task-specific geometry/contact evaluators |
| Fresh three-task benchmark | `docs/three_task_benchmark_v8.md`, `data/three_task_v8/r2/`, `outputs/three_task_v8/` |
| Historical Phase 2/3 studies | `docs/phase2/`, `docs/phase3/`, corresponding `outputs/` directories |
| Latest presentation and script | `presentation/team11_final/` |
| Cost estimate derivation | `presentation/final_benchmark_cost/analysis/` |
| Automated tests | `tests/` |

The original Default v1 and all opt-in Dev variants remain selectable. Gate Dev v7 is the current presentation recommendation, not a guarantee of success on every task/layout. The English UI has nine engineering task templates; the frozen v8 comparison covers three templates only. Two-computer/VPN operation remains untested.

## Evidence and dataset versions

- **v8 r2:** 24 Dev samples from 6 layout groups; 12 Test samples from 12 independent groups. Physical oracle 36/36. Real held-out comparisons: NoAsk 10/12, LLM-Gate 12/12, Jev-Gate 12/12, over 36 model/physics episodes and 262 API attempts.
- **Earlier Phase 3:** separate 32 Dev / 128 Test dataset. Its 160 physical oracle checks and small Dev calibration were completed. Its 128-sample model Test remains unrun. Do not merge these counts with v8.
- **English-console rehearsal:** three new Dev episodes, separate from frozen Test. Its failures remain visible and do not change the Test scores.
- **Dollar costs:** explicitly estimated from actual usage and current public prices, not invoices. Rates, cache-hit accounting, raw references and limitations are preserved with the presentation cost analysis.

Use a new independent Dev directory/version for further prompt, observation, threshold or controller tuning. Preserve the original frozen data, settings, raw episodes and reports. Changing a parameter after seeing Test results requires a separately named experiment. Do not present script policies or offline doubles as model results.

## Media and local evidence beyond normal Git

Git contains code, tests, generated datasets, original JSON/JSONL/CSV evidence, screenshots, browser frame atlases, selected MP4s, GIF highlights, PowerPoints and speaker notes. An additional [Private Release](https://github.com/liangjunyi010/when2ask/releases/tag/team11-handoff-20261112) contains the raw recordings and sanitized local-console evidence that were previously ignored:

- `when2ask_raw_recordings_20261112.tar.gz`
- `when2ask_local_console_evidence_20261112.tar.gz`
- `raw_assets_manifest.json` and `SHA256SUMS`
- The latest Team 11 PowerPoint and speaker notes as direct-download assets

The archives retain original relative paths and exact file bytes. They are optional for ordinary code development: the selected display media needed by the console is already in Git. They are useful to rebuild old recordings or inspect local trial evidence.

```bash
gh release download team11-handoff-20261112 --repo liangjunyi010/when2ask \
  --pattern '*.tar.gz' --pattern SHA256SUMS
shasum -a 256 -c SHA256SUMS
# Extract from the repository root to restore the recorded relative paths:
tar -xzf when2ask_raw_recordings_20261112.tar.gz
tar -xzf when2ask_local_console_evidence_20261112.tar.gz
```

The manifest lists each included file's path, size and SHA-256. Authentication, process IDs, live session-budget controls and reproducible build/frame intermediates are excluded. Archived local trials remain historical evidence; do not treat them as resumable live worker sessions or pool them into frozen benchmark results.

The previously uncommitted local Milestone deck is also preserved byte-for-byte as `presentation/milestone/When2Ask_Milestone_LocalEdits_20261112.pptx`. Its original working file is left untouched. The current ten-minute deliverable is `presentation/team11_final/deliverables/When2Ask_Team11_Final_Presentation.pptx`.

## Suggested first contribution

Create a new feature branch from this handoff, run the offline tests and console, then inspect one saved failure alongside its public state/action history. Keep any fixes opt-in until a fresh Dev check is complete. Open a PR against `codex/team11-handoff`; do not force-push, rewrite historical results or automatically merge the existing stacked PRs.

## Fresh-clone verification

A new private GitHub clone and a new Python 3.11 virtual environment successfully installed through the documented setup script. PyBullet was actually compiled, then verified in DIRECT mode with 60 simulation steps, TinyRenderer and clean disconnect. All offline tests ran: **363 passed, 1 skipped** (the credential-locality check intentionally skips when `.env` is absent). The English console served its frontend, saved Benchmark JSON, synchronized replay and byte-range MP4 from this credential-free clone. No model API calls were made. See `handoff/checks/clone_validation.json`.
