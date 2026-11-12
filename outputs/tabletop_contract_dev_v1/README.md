# Tabletop contract Dev repair: evidence index

This is a **Dev-only** investigation of two historical failure mechanisms. Four
controlled variants reuse four existing Dev layout groups. The original Test
episodes, frozen configuration and nine-task benchmark tables remain unchanged.

- [Analysis, methods, actual results and limitations](../../docs/tabletop_contract_dev_v1.md)
- [Generated results](report/README.md), [summary JSON](report/summary.json),
  [paired-episode CSV](report/episodes.csv), [factor CSV](report/factor_diagnostics.csv)
- [English read-only gallery](report/index.html), local port 8905
- [Read-only forensic analysis](forensics.json)
- [Four actual physical oracle runs](oracle/summary.json)
- [Frozen Dev protocol, source/prompt/state/data hashes](manifest.json)
- `probes/`: 56 real fixed-state calls, every request/response and usage record
- `episodes/`: all 24 baseline/repaired three-method physical episodes
- [Evidence/privacy/budget audit](evidence_validation.json)
- [Identical-request response variation](observed_response_variation.json)
- [Offline pytest output](pytest_console.txt), [JUnit](pytest.xml): 410 passed

Both Gate methods improved from 3/4 to 4/4 task success on these Dev regressions;
NoAsk stayed at 3/4. The repeated container undo/replacement disappeared in both
repaired Gate episodes (two placements versus 12 original actions). The repaired
LLM-Gate still asked early in one known-cup case. No failed or mistimed outcome
was replaced by a rerun.

All 258 authenticated attempts (56 fixed-state + 202 full-episode attempts) are
included in the persistent ledger. Budget: 450 attempts and 24 full episodes.
No API/schema errors or retries; actual usage present for every attempt. Model
versions: deepseek-flash and jev-1.14.0. All reported costs use measured backend
tokens/latency; no dollar claim or statistically significant advantage is asserted.

Recompute reports with `scripts/tabletop_contract_dev.py report` and validate
evidence with `scripts/tabletop_dev_audit.py`; both are offline. Diagnostic probes
have public-rule references only for these controlled cases, withheld from models.
They are not a universal timing oracle. Any fresh Test claim needs new frozen data
and protocol after Dev; these examined cases are not fresh held-out evidence.
