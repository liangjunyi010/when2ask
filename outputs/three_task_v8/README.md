# Three-task Benchmark v8 — held-out evaluation evidence

[Construction/results/limitations](../../docs/three_task_benchmark_v8.md). Read-only gallery: http://127.0.0.1:8900/.

- `oracle_r2/`: all36 real feasibility executions and unchanged independent scores;36/36 passed, zero model calls.
- `frozen_manifest.json`: sources, data, prompts, models, threshold, every Test job, recording selection and budgets fixed before model Test.
- `test_runs/`: all12 held-out samples ×3 methods =36 actual API/PyBullet episodes. Complete public inputs, gate projection, model outputs, questions/answers, physical actions/events/checkpoints, final evaluation and PNGs. No episode reruns/exclusions; original NoAsk failures and skill rejections retained.
- [Raw-derived summary](report/summary.json), [readable report](report/report.md), [all episode CSV rows](report/episodes.csv), [disclosure breakdown](report/disclosure_breakdown.csv), [mapping audit](report/mapping_validation.json).
- [Benchmark figure](report/benchmark_summary.png), [paired outcomes](report/paired_outcomes.png), [exploratory timing](report/clarification_timing.png). Timing is a post-Test public-DAG diagnostic, not a preregistered optimal label or statistical claim.
- [Nine real recordings](../../presentation/three_task_v8/README.md), selected before Test by first undisclosed layout per template and all methods. Full GIFs remain ignored locally; MP4s are committed under `presentation/three_task_v8/media/`. Videos use actual simulation/display time, not inference wall time. Other cases have traces and PNGs without a recording claim.
- `browser/validation.json`: actual Chrome desktop/mobile rendering, all9 MP4s decoded, zero console errors/overflow or added model requests.
- `test_validation.json` and `runtime_versions.json`: actual baseline350/final358 offline tests and dependency versions.

Results: NoAsk10/12, LLM-Gate12/12, Jev-Gate12/12. Mean burden0/0.333/0.333.262/450 authenticated requests; no API/schema errors or inference retries. Three invalid panel-placement commands were rejected and followed by real cover repairs. NoAsk's two preference errors remain scored false.

There are12 independent Test groups, not36 independent cases. All2,709 protected historical/frozen/source files are unchanged. Original frozen128-Test is still unrun; do not combine studies or claim nine-template Test coverage. Offline reproduction: `.venv/bin/python scripts/three_task_report.py --export-media`; gallery `.venv/bin/python scripts/three_task_gallery.py --serve --port8900`. New paid runs require a new version namespace and a new freeze; in-place reruns are refused.
