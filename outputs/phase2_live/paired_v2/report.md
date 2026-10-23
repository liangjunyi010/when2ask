# When2Ask Engineering Pilot

Tiny controlled sample; no statistical significance or generalization claim. Token sums are observed usage, with unknown-attempt counts; backend tokens are not dollar equivalents.

| Method | Success | Burden | DeepSeek tokens | Jev tokens | API latency (ms) |
|---|---:|---:|---:|---:|---:|
| llm_noask | 1/3 | 0 | 16842 | — | 10409.31 |
| llm_gate | 3/3 | 5 | 38359 | — | 22129.22 |
| jev_gate | 3/3 | 5 | 20267 | 27455 | 17641.26 |

Raw episode paths and separated input/output usage are in episodes.csv.
Every HTTP attempt is retained in the episode api_attempts.jsonl. API smoke/model-discovery and local user-simulator costs are reported separately.
Final success is based on physics, independently of DONE or budget termination.
