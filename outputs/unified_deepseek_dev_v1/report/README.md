# Single-call DeepSeek Dev comparison

Four paired Dev groups; all four methods rerun.

| Method | Success | Mean burden | Total API s | Mean wall s | Estimated USD total | Requests |
|---|---|---|---|---|---|---|
| LLM-NoAsk | 3/4 | 0.00 | 12.38 | 5.65 | 0.000664 | 14 |
| LLM-Gate | 4/4 | 1.00 | 28.84 | 9.82 | 0.002374 | 34 |
| Jev-Gate (0.5) | 4/4 | 1.00 | 18.53 | 7.22 | 0.002479 | 34 |
| DeepSeek Unified | 4/4 | 1.00 | 16.24 | 6.61 | 0.003258 | 17 |

## Interpretation limits

- Four previously developed Dev groups, two task templates, one run per method/case. No held-out or statistical superiority claim.
- All four methods freshly executed; no historical episode is pooled into this report.
- Unified generates the question or action/DONE in one logical call. Repairs/retries are extra charged attempts; no separate Gate latency exists for it.
- Same public facts, simulator, physics, evaluator, budgets and model parameters. Unified combines role prompts, so this is an architecture comparison, not a gate-only controlled substitution.
- API latency sums authenticated HTTP attempts; wall time additionally includes physics/rendering. Serial execution; real provider caching is recorded, not controlled.
- USD is an estimate from public prices and actual cache/token usage, not an invoice. Backend tokens are separately reported. Unknown usage/cost remains null.
- DeepSeek weekday peak-window classification assumes no Chinese public holiday; outside the peak windows holiday status cannot affect the rate.
- All success/failure outcomes retained; guessed preferences can be correct by chance. Lower burden alone does not prove better timing.

## Every episode

| Case | Method | Success | Burden | Actions | First ASK after actions | Termination |
|---|---|---|---|---|---|---|
| td1_pack_block_first | llm_gate | True | 1 | 3 | 0 | done |
| td1_pack_block_first | jev_gate | True | 1 | 3 | 0 | done |
| td1_pack_block_first | llm_noask | True | 0 | 3 | None | done |
| td1_pack_block_first | llm_unified | True | 1 | 3 | 0 | done |
| td1_pack_continue_known_cup | jev_gate | True | 2 | 3 | 1 | done |
| td1_pack_continue_known_cup | llm_noask | True | 0 | 3 | None | done |
| td1_pack_continue_known_cup | llm_unified | True | 2 | 3 | 0 | done |
| td1_pack_continue_known_cup | llm_gate | True | 2 | 3 | 0 | done |
| td1_containers_block_first | llm_noask | False | 0 | 2 | None | done |
| td1_containers_block_first | llm_unified | True | 1 | 2 | 0 | done |
| td1_containers_block_first | llm_gate | True | 1 | 2 | 0 | done |
| td1_containers_block_first | jev_gate | True | 1 | 2 | 0 | done |
| td1_containers_all_known | llm_unified | True | 0 | 2 | None | done |
| td1_containers_all_known | llm_gate | True | 0 | 2 | None | done |
| td1_containers_all_known | jev_gate | True | 0 | 2 | None | done |
| td1_containers_all_known | llm_noask | True | 0 | 2 | None | done |

Recompute: `.venv/bin/python scripts/unified_deepseek_dev.py report`. Full raw JSON/JSONL is under `../episodes/`.
