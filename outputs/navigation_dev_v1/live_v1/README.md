# Navigation Dev v1 — actual API + PyBullet pilot

Engineering pilot on ONE shared floorplan, not three independent map groups; no significance or Test-set claim.

| Method | Success | Mean burden | Total travel (m) | API latency total (s) | DeepSeek in/out | Jev in/out |
|---|---:|---:|---:|---:|---:|---:|
| llm_noask | 3/3 | 0.00 | 46.75 | 9.51 | 20116/141 | — (not called) |
| llm_gate | 3/3 | 0.00 | 46.75 | 21.61 | 39894/232 | — (not called) |
| jev_gate | 3/3 | 0.00 | 46.75 | 13.53 | 20116/141 | 26648/312 |

Authenticated attempts: 65/120; episodes: 9/9. No paid Test calls. All metrics above are derived from episode JSON and API audit records. Backend tokens are kept separate.

The target is a fixed world fact. Search uses known map routes and real wheel motors; detection uses local geometric range/FOV/ray line of sight, not learned vision. User hints do not move the object. Success means found and approached, without pickup or delivery. Each automatic reply incurs one slot and a declared 3s delay.

**Observed limitation:** Neither learned gate asked in these episodes. Both continued autonomous search until detection. Consequently this pilot demonstrates integration and search feasibility, not a clarification-timing advantage; the gate methods incurred extra inference cost without shortening travel. Actual ASK freezing and human/automatic replies were verified separately with explicitly scripted policies and real physics; they are not live-model ASK evidence.

## Paired traces and timing

- [nav_dev_v1_case_c_unknown / jev_gate](episodes/1a50c17b021d46a9/episode.json): success=True; burden=0; distance=27.01m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_b_unknown / llm_noask](episodes/351fd147019847c8/episode.json): success=True; burden=0; distance=14.61m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_b_unknown / jev_gate](episodes/356fb9167ab041dd/episode.json): success=True; burden=0; distance=14.61m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_a_unknown / jev_gate](episodes/3a078366ecb54009/episode.json): success=True; burden=0; distance=5.14m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_a_unknown / llm_noask](episodes/4a542012267e4220/episode.json): success=True; burden=0; distance=5.14m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_a_unknown / llm_gate](episodes/c5a594d5d1c04cdc/episode.json): success=True; burden=0; distance=5.14m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_c_unknown / llm_gate](episodes/cf4efce6d33340fa/episode.json): success=True; burden=0; distance=27.01m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_b_unknown / llm_gate](episodes/e1447600c82141cf/episode.json): success=True; burden=0; distance=14.61m; first ASK round=None, after None inspections; termination=done; error=None.
- [nav_dev_v1_case_c_unknown / llm_noask](episodes/e244a505fc5d4f41/episode.json): success=True; burden=0; distance=27.01m; first ASK round=None, after None inspections; termination=done; error=None.

These placements share one layout group, so no independent-group confidence interval or significance comparison is reported. This pilot evaluates task and UI integration; it does not establish an optimal asking policy. Frozen tabletop prompts, datasets and historical experiments are unchanged.
