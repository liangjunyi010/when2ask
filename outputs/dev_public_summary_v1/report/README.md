# Independent Dev public-summary diagnostic

Four independent Dev scene groups, one case each, three paired Jev conditions. Threshold fixed at 0.5. The console regression was intentionally selected after an observed failure; the remaining cases were seeded public-coverage draws. These are targeted engineering diagnostics, not held-out or statistically confirmatory results.

| Profile | Task success | Burden | Early ASK | Blocked CONTINUE | Complete ASK | API seconds (sum) | DeepSeek in/out | Jev in/out |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v3_original | 2/4 | 3 | 0 | 5 | 0 | 30.464 | 39332/688 | 51176/576 |
| compact_state | 4/4 | 5 | 1 | 2 | 0 | 28.909 | 36211/781 | 47603/600 |
| compact_question | 4/4 | 6 | 1 | 0 | 0 | 26.464 | 28955/628 | 32096/504 |

## Per-case pairing

| Case | Missing | Profile | Success | Burden | Early / blocked |
|---|---:|---|---|---:|---|
| regression_console_m2 | 2 | v3_original | False | 0 | 0 / 3 |
| regression_console_m2 | 2 | compact_state | True | 2 | 1 / 0 |
| regression_console_m2 | 2 | compact_question | True | 2 | 1 / 0 |
| dev_m0_v3_dev_024 | 0 | v3_original | False | 0 | 0 / 0 |
| dev_m0_v3_dev_024 | 0 | compact_state | True | 0 | 0 / 0 |
| dev_m0_v3_dev_024 | 0 | compact_question | True | 0 | 0 / 0 |
| dev_m1_v3_dev_013 | 1 | v3_original | True | 0 | 0 / 2 |
| dev_m1_v3_dev_013 | 1 | compact_state | True | 0 | 0 / 2 |
| dev_m1_v3_dev_013 | 1 | compact_question | True | 1 | 0 / 0 |
| dev_m3_v3_dev_023 | 3 | v3_original | True | 3 | 0 / 0 |
| dev_m3_v3_dev_023 | 3 | compact_state | True | 3 | 0 / 0 |
| dev_m3_v3_dev_023 | 3 | compact_question | True | 3 | 0 / 0 |

## Predeclared interpretation

```json
{
  "compact_state": {
    "promising": false,
    "no_per_case_success_or_early_ask_regression": false,
    "blocked_continue_reduction": 3,
    "reason": "Predeclared exploratory rule only; no automatic Test promotion"
  },
  "compact_question": {
    "promising": false,
    "no_per_case_success_or_early_ask_regression": false,
    "blocked_continue_reduction": 5,
    "reason": "Predeclared exploratory rule only; no automatic Test promotion"
  }
}
```

No candidate is promoted to the frozen Test configuration. Four groups, including a targeted regression, are insufficient for generalization claims. compact_state changes the public representation supplied to BOTH gate and planner; its success difference is not a pure gate-only effect. compact_question vs compact_state keeps that representation and the action/question planner prompts identical, changing only the gate wording.

Timing labels are computed offline with the unchanged public_progress diagnostic, never sent to a model. Raw gate scores are only compared at identical public-state hashes in matched_public_states.json; equal round indices on divergent trajectories are not treated as matched states.

Actual authenticated requests: 140/140; episodes: 12/12. All retries/repairs count. Unknown usage stays null in raw records, and provider token counts are not combined as dollar cost.

All metrics above derive from episode JSON and raw API JSONL. Scene/final PNGs, real execution logs, independent geometric/contact/DAG scores and ASK freeze checks are saved per episode. The regression baseline and joint variant also have locally generated real PyBullet GIFs; GIF files remain ignored by Git.

Noul wording follows the positive yes/no proposition interface documented at https://docs.typesafe.ai/primitives/noul. Original source/data/configuration and historical experiment preservation are audited separately. No held-out Test inference was run.
