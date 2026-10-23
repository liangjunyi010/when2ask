# When2Ask Engineering Pilot

Tiny controlled sample; no statistical significance or generalization claim. Token sums are observed usage, with unknown-attempt counts; backend tokens are not dollar equivalents.

| Method | Success | Burden | DeepSeek tokens | Jev tokens | API latency (ms) |
|---|---:|---:|---:|---:|---:|
| llm_noask | 0/1 | 0 | 5166 | — | 2938.1 |
| llm_gate | 0/1 | 0 | 9676 | — | 6881.86 |
| jev_gate | 0/1 | 0 | 5166 | 7113 | 4738.29 |

Raw episode paths and separated input/output usage are in episodes.csv.
Every HTTP attempt is retained in the episode api_attempts.jsonl. API smoke/model-discovery and local user-simulator costs are reported separately.
Final success is based on physics, independently of DONE or budget termination.
