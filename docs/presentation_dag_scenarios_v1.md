# Twenty DAG presentation scenarios

This independent presentation collection reuses the existing Panda environment, physical skills, shared v3.1 prompts, DeepSeek planner, Jev gate and independent evaluator. It does not modify the frozen Dev/Test dataset, prompts, thresholds, navigation studies or historical results.

There are **20 task instances, two task templates and ten physical layout groups**. These are not twenty new robotic capabilities or twenty independent layouts. Each template uses five conservative development layout families, with two task variants per family. Hidden choices, candidate order, object aliases and category source assignments vary independently. No held-out Test sample was used for selection or model calls.

| Dimension | Distribution |
|---|---|
| Pack and cover | 10 samples |
| Place into selected containers | 10 samples |
| Unknown preferences | 0, 1, 2, 3: five samples each |
| Public order | Independent: 7; cup first: 7; block first: 6 |
| Base physical groups | 10; two variants per group |

The DAG specifies **publicly instructed action prerequisites**. For example, pack-and-cover always requires both placements before covering. A block-first variant also requires the block placement before the cup. This makes a known cup insufficient for immediate progress if the preceding block choice is missing. Conversely, an independent known block supports progress even when the cup is unknown. In the two-container template, one destination preference is reused to place the cup and the block in opposite containers.

The public console catalogue contains DAG edges, titles and teaching descriptions, but no private candidate registry or hidden answers. Its teaching descriptions are observer-facing and are not added to the model input. Models receive only the original public instruction, current physical observation and public history. Final truth is revealed only for completed episodes.

## Actual execution

All twenty samples passed the **real PyBullet physical oracle: 20/20**, with no initial penetrations. Oracle traces include motor-driven constraint grasps, releases, geometric/support/contact scoring and DAG event evidence. No physics, evaluator tolerance or final object poses were modified.

The locked online plan uses one episode per scenario, rotating NoAsk / LLM-Gate / Jev-Gate and shuffling execution order. Limits were 20 episodes and 200 authenticated requests globally; each episode allowed at most 20 rounds and 24 API attempts, including the existing one-retry policy. The actual run used **20 episodes and 138 authenticated requests**. All use the existing shared task contract and Jev threshold **0.5**, without tuning. Configured/returned DeepSeek: `deepseek-flash`; configured Jev: `jev-latest`, returned: `jev-1.14.0`.

| Method | Success | Total clarification burden | Cumulative API latency |
|---|---:|---:|---:|
| LLM-NoAsk | 2/7 | 0 | 33.82 s |
| LLM-Gate | 6/7 | 6 | 48.68 s |
| Jev-Gate | 5/6 | 9 | 32.28 s |

**Different methods ran different samples. This is an unpaired smoke demonstration, not evidence that one method outperforms another.** It is also not a held-out Test experiment. All 60 executed robot skills reported success, while seven whole tasks failed final preference/order conditions; completing a skill does not establish task success.

The machine-generated [report](../outputs/presentation_dag_v1/report.md), [CSV](../outputs/presentation_dag_v1/results.csv), [summary](../outputs/presentation_dag_v1/summary.json), raw episode JSONs and separate backend token usage remain available. A post-hoc public-only scripted support check found two ASK turns with already-supported progress. It is a conservative diagnostic, not an optimal-timing gold label and never feeds back into live decisions.

Useful contrasting cases are `dag_demo_03` (Jev misses needed block clarification and fails), `dag_demo_06` (Jev asks before a supported cup placement, then succeeds), `dag_demo_14` (LLM-Gate guesses correctly without ASK), `dag_demo_15` (one reusable destination answer, success), and `dag_demo_18` (all preferences missing, asks before acting, success). Keep these limitations visible when presenting.

## Presentation UI and recordings

- Command center: **http://127.0.0.1:8877/**. Choose a task template and then a named **DAG PRESENTATION SCENARIO**. Disclosure is fixed by that preset. Free demonstration and navigation remain available. Both individual runs and one-click comparisons use the exact selected preset.
- Read-only gallery: **http://127.0.0.1:8881/**. It has all twenty scenarios, public DAG constraints, original instructions, model decisions/questions/answers, final truth and physical score. It launches no model calls. Links back to the console only select a preset; they do not start a paid episode.
- Gallery MP4 controls default to uniform **2×** playback, with 1×/2×/3×, pause and seek. The adjacent DAG is explicitly a static dependency diagram, not a timed stage animation. The earlier synchronized milestone replay remains unchanged.
- [Twenty downloadable MP4 clips](../presentation/dag_scenarios_v1/media) are compressed directly from the original real-execution GIFs, with unchanged duration. Total size is about 11 MB. The export manifest checks each original GIF duration against ffprobe and records source/media hashes. Original GIFs stay local under `outputs/presentation_dag_v1/live/`.
- Browser screenshots and separate scripted integration evidence are in `outputs/presentation_dag_v1/browser/`. The manual-form browser test uses a labelled **scripted policy with real physics**, makes zero API requests, and is excluded from the twenty model results.

## Commands actually executed

```bash
.venv/bin/python scripts/presentation_dag.py generate
.venv/bin/python scripts/presentation_dag.py validate
.venv/bin/python scripts/presentation_dag.py oracle --workers 3
.venv/bin/python scripts/presentation_dag.py plan
.venv/bin/python scripts/presentation_dag.py run --live --workers 3
.venv/bin/python scripts/export_presentation_clips.py
.venv/bin/python scripts/presentation_dag.py gallery
.venv/bin/python -m pytest -q
node scripts/presentation_console_check.mjs
node scripts/presentation_gallery_check.mjs
```

Generation, oracle, preregistration, online episodes and media export refuse to overwrite their existing evidence. Do not delete evidence to rerun them; a new experiment needs a separate version directory. `validate`, `report` and `gallery` are safe offline operations. To reopen the gallery after a fresh checkout, `gallery` copies the committed MP4 clips to its served directory; no API calls or original GIFs are required:

```bash
.venv/bin/python scripts/presentation_dag.py gallery
.venv/bin/python -m http.server 8881 --bind 127.0.0.1 --directory outputs/presentation_dag_v1
```

Start the interactive controller separately with its existing bounded console command. New launches consume its own session budget; browsing the gallery and reading existing episodes consume none. This collection is for presentation/debugging; formal method comparisons still need a preregistered paired design and group-aware analysis.
