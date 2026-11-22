# Saved evidence

`nine_task_metrics_dev_v1/` contains the original 108 episodes, API requests and responses, physical evaluations, before/after images, oracle validation, pricing, prompt snapshots and result tables.

The files were copied byte for byte from `outputs/nine_task_metrics_dev_v1/` at commit `300ec95b85b7ab7e3be6733c8f59e7d1af8f626b`. The data files are also unchanged. Run `python script/benchmark.py verify` to check all 866 files against `checksums.json`.

The original study manifest records the source hashes used during that experiment. The public source has since been reorganized and uses English task labels. Those historical source hashes are preserved as provenance; they are not presented as hashes of the reorganized code. New live runs create their own source manifest and a separate output directory.

The final report selects NoAsk, LLM-Gate and Jev-Gate for its main table. The saved study also contains the Unified baseline, so the archive has 108 episodes rather than 81. The separate cross-model values in the report come from the final presentation. This archive contains the shared-planner experiment, not raw GPT or GLM runs.

`report` recomputes aggregate metrics from the original requests and evaluations. `audit` checks pairing, physical scores, ASK state preservation and private-data boundaries. Both commands write to `result/recomputed/`. The older `protected_before.json` is a historical record of checks on earlier project files; those old development artifacts are available in Git history rather than the main tree.
