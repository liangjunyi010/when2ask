# Nine-task Dev: four headline metrics

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 21/27 (77.8%) | 4.05 s | $0.000718 | — (disabled) |
| LLM-Gate | 27/27 (100.0%) | 8.24 s | $0.001977 | 0.0% (0/18) |
| Jev-Gate | 26/27 (96.3%) | 5.73 s | $0.001062 | 0.0% (0/18) |
| DeepSeek Unified | 26/27 (96.3%) | 4.35 s | $0.001394 | 0.0% (0/18) |

Time and cost are **per episode means**, not totals. FPR uses only the 18 prelabelled core negatives.

## Coverage and interpretation

- Nine templates, 27 Dev variants from 18 existing Dev physical groups. Each template has two fully disclosed core negatives and one information-condition contrast.
- Seven contrasts hide real user preferences. Unknown navigation permits autonomous search; the hidden inspection label is a physically observable fact. Neither is mislabeled as a mandatory-ASK positive.
- Primary FPR is task-level: at least one explicit ASK on a prelabelled core negative. Multiple asks count once. NoAsk is N/A because asking is disabled.
- Explicit ASK remains a false positive if question generation fails. Technically interrupted runs without ASK are censored rather than credited as true negatives; denominators are shown.
- Success comes from independent actual physics and event checks, even after a guessed choice or budget termination. It is separate from task-level FPR.
- Speed is mean cumulative API HTTP seconds per episode, including all retries and DONE. It excludes physical motion and user response time. Three fixed worker processes run a frozen interleaved order.
- USD is estimated per episode from real backend/cache usage and official public prices, not invoices. Missing usage remains unknown. Tokens of different backends are never directly added as money.
- All four methods were freshly executed. Unified fuses decision and native question/action generation; this is an architecture comparison, not only a Gate substitution.
- Contrast variants share groups with negatives. No statistical interval treats all 27 cases as independent; no fresh held-out Test or universal ranking claim.
- Clarification burden remains only in original episode diagnostics; headline tables contain success, API time, estimated cost and unnecessary ASK rate.

## Per-task paired results

### Pack and Cover

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 2/3 (66.7%) | 3.32 s | $0.000482 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 7.14 s | $0.001056 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 5.36 s | $0.000852 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 3.73 s | $0.000785 | 0.0% (0/2) |

### Selected Containers

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 2/3 (66.7%) | 2.40 s | $0.000356 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 5.52 s | $0.000834 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 3.52 s | $0.000582 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 3.05 s | $0.000550 | 0.0% (0/2) |

### Find and Approach

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 3/3 (100.0%) | 2.89 s | $0.000150 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 5.36 s | $0.001018 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 4.28 s | $0.000483 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 3.07 s | $0.000761 | 0.0% (0/2) |

### Category Sorting

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 3/3 (100.0%) | 7.19 s | $0.001459 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 14.43 s | $0.006194 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 9.26 s | $0.002392 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 5.96 s | $0.003494 | 0.0% (0/2) |

### Inventory Restock

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 0/3 (0.0%) | 3.48 s | $0.000733 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 8.24 s | $0.002830 | 0.0% (0/2) |
| Jev-Gate | 2/3 (66.7%) | 5.34 s | $0.001318 | 0.0% (0/2) |
| DeepSeek Unified | 2/3 (66.7%) | 3.22 s | $0.001515 | 0.0% (0/2) |

### Retrieve and Restore

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 3/3 (100.0%) | 4.79 s | $0.000915 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 9.71 s | $0.001886 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 6.58 s | $0.001215 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 6.13 s | $0.001734 | 0.0% (0/2) |

### Buffered Exchange

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 2/3 (66.7%) | 4.69 s | $0.001150 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 9.02 s | $0.001385 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 6.64 s | $0.001246 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 5.45 s | $0.001701 | 0.0% (0/2) |

### Patrol and Return

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 3/3 (100.0%) | 3.21 s | $0.000640 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 6.61 s | $0.001242 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 4.52 s | $0.000812 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 3.97 s | $0.000976 | 0.0% (0/2) |

### Reveal and Inspect

| Method | Success rate ↑ | Mean API time ↓ | Mean estimated USD ↓ | Unnecessary ASK rate ↓ |
|---|---|---|---|---|
| LLM-NoAsk | 3/3 (100.0%) | 4.50 s | $0.000581 | — (disabled) |
| LLM-Gate | 3/3 (100.0%) | 8.11 s | $0.001345 | 0.0% (0/2) |
| Jev-Gate | 3/3 (100.0%) | 6.02 s | $0.000655 | 0.0% (0/2) |
| DeepSeek Unified | 3/3 (100.0%) | 4.60 s | $0.001033 | 0.0% (0/2) |

Recompute: `.venv/bin/python scripts/nine_task_metrics_dev.py report`. Raw records are in `../episodes/`; exact policy/data/model/budget hashes are in `../manifest.json`.
