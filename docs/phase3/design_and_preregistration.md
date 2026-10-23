# Phase 3: scene-grouped benchmark and Dev-only calibration

This phase builds on `feat/benchmark-apis` at `3bc24b2`. PR #1 remains open.
All historical Phase 2 data, scenes, API responses, reports and metrics remain
byte-for-byte unchanged. New evidence lives under `outputs/phase3/` and
`outputs/phase3_live/`. No formal Test API experiment is run in this phase.

## Physical tasks and conservative scope

`pack_and_cover` retains the five-piece hollow box, real cup/block placement and
full-corner/rim-contact lid checks. `place_into_selected_containers` adds two
five-piece open rigid containers. The user's cup_destination choice determines
the cup container and, by the public instruction, the block's other container.
One answer can therefore be reused by both actions. Cup/block identity plus this
destination yield three binary preferences, with 0/1/2/3 initially unknown.

Both tasks support independent, cup-first and block-first public orders. All
precedence edges are stated in the instruction. Independent evaluators inspect
full Bullet AABBs, actual upward support contacts, stable velocity, full-footprint
exclusion of unselected objects, release and witnessed placement/cover events.
Returning a wrong object to the table and replacing it can repair an episode;
termination and final physical success remain independent.

The original motor/IK path, bounded waypoints, 25 mm tracking/40 mm hand proximity
guards and explicitly logged constraint grasp are reused. No execution-time body
pose reset, relaxed geometric success tolerance or learned grasp model is added.
An initial geometry probe put a block too close to the robot base (x≈0.25 m) and
failed IK convergence. Its source was moved to x≥0.29 m before dataset generation.
The final scene distribution then passed 160/160 complete real physical oracles.

## Groups and split isolation

Schema 3 has explicit template_id, layout_family_id, group_id, scene_seed,
sample_id, partition and dataset_version. The compatibility reader still accepts
the old Phase 2 schema without rewriting historical files.

A group is a base physical layout. Its fingerprint contains template, container
geometry/centers and unordered source slots by object category. It ignores truth,
colors, aliases, candidate order, instruction style, disclosure and mm jitter.
Every variant of that layout stays in the same partition. Source color assignment
is randomized independently of truth; opaque IDs, candidate lists and observation
lists are shuffled. Rank histograms are preserved in `data/phase3/freeze.json`.

Dev has 8 layout groups ×4 variants =32 samples. Test has 16 held-out layout
groups ×8 variants =128 samples. Each task receives half of each partition. Each
partition has equal counts at 0/1/2/3 unknown preferences. Correct preference
combinations may occur in both splits; they do not define split membership.

For pack/cover, Test holds out the reflected container/source arrangement. For
two containers, Dev separates bins along the table's y axis, while Test separates
them across x. The all-pairs cross-split check rejects matching container layouts
within 25 mm; the actual minimum max-matched-container distance is 101.1 mm.
Variants use ±4 mm source jitter. These are conservative primitive geometries,
not a claim of broad robotic scene diversity or IID natural tasks.

All 160 scenes are instantiated for schema, full pairwise inter-object penetration
and public/private checks; every sample also executes the complete offline oracle
with an independent physical evaluator. Test oracle access only verifies mechanics,
not prompts, model selection or clarification quality. Dataset/scene hashes freeze
before the first Phase 3 authenticated API request.

## Pre-registered online Dev study

Before any authenticated call, `configs/dev_calibration_manifest.json` locks the
runtime source hashes/code commit, dataset hashes, prompt hashes, model settings,
sample list, shuffled run order, budgets, retry rules and threshold selection rule.
There is exactly one selected sample per Dev group:

| Task | Missing 0 | Missing 1 | Missing 2 | Missing 3 |
|---|---|---|---|---|
| pack_and_cover | v3_dev_000 | v3_dev_005 | v3_dev_010 | v3_dev_015 |
| place_into_selected_containers | v3_dev_016 | v3_dev_021 | v3_dev_026 | v3_dev_031 |

These were chosen by group index and disclosure variant before model responses.
All five conditions run on each sample: NoAsk, LLM-Gate, Jev thresholds 0.3, 0.5,
0.7. Every condition starts a fresh environment and public history. No threshold
is evaluated by replaying another episode. Shuffle seed is 20261023.

Two model discoveries and one gate inference per backend revalidate connectivity
and the uniform public contract before complete episodes. These are not additional
episodes but do count as authenticated requests. The entire session is limited to
40 complete/started episodes and 600 HTTP attempts, including retries, malformed
response repairs, discovery, diagnostics and smoke. Per episode: 20 rounds,
12 robot actions, 12 slot requests, 64 attempts; inference output caps 64 gate /500
planner tokens. Temperature 0, non-thinking JSON output, timeout 40 s, one retry.
Permanent HTTP errors block the backend; three consecutive unsuccessful responses
also block it. Unknown usage stays null. All original 200/12 Phase 2 limits remain
the default for legacy sessions and cannot be silently expanded by this study.

All methods see the identical public serialization and shared planner. Version 3
prompts preserve Phase 2's fixed-user-preference contract while explaining both
public task types and order rules. Gate precedes planner, has no action, and cannot
return DONE. Only the shared action planner returns DONE. ASK freezes all physics.
NoAsk instantiates no Gate. Target roles are resolved privately by the same user
simulator; it reads only requested preference keys. Burden charges distinct slots
within a question and charges repeated requests again.

## Threshold choice and uncertainty

Default is 0.5. Compare 0.3 and 0.7 against 0.5 using paired resampling of the eight
independent layout groups (20,000 bootstrap draws, seed 4278, 97.5% intervals;
Bonferroni for two alternatives). Prefer higher success. An alternative needs a
strictly positive lower bound on the paired success improvement. When all paired
success outcomes are identical, a strictly positive lower bound on burden saving
can select it. Only when success and burden vectors are identical can ≥10% latency
saving with a positive lower bound select it. Eligible alternatives rank by SR,
burden, latency and distance to default. Missing pairing or insufficient evidence
keeps 0.5. Exact machine-readable rules are in the manifest.

SR intervals use independent-group Wilson intervals; paired differences retain
the same group identities. Paraphrases and hidden variants do not inflate sample
size. Eight groups provide limited evidence: identical observed SR is not proof
of equivalence, and this remains exploratory engineering calibration. DeepSeek
and Jev tokens are reported separately, not treated as interchangeable dollars.

## Formal Test freeze

After Dev, `configs/frozen_test.yaml` records configured/returned models, selected
threshold, prompt hashes, planner parameters, skill/evaluator and source hashes,
dataset hashes, code commit and budgets/retries. The file uses JSON syntax, which
is a YAML 1.2 subset, so no YAML dependency is needed. A companion manifest hashes
the configuration. Existing frozen parameters cannot be silently overwritten.

Formal Test has 128 samples ×3 methods =384 fresh episodes, clustered into 16
layout groups for statistical inference. Its worst-case per-episode ceiling sums
to 24,576 HTTP attempts plus bounded discovery; an initial proposed separate study
cap is 5,000 attempts, subject to next-phase authorization and actual Dev costs.
Interleave paired jobs, stop on budget/circuit limits and never tune on Test
outcomes. Changing prompts, threshold, model, controller or data starts a distinct
experiment version. DeepSeek's returned alias cannot guarantee an immutable
underlying backend build; model drift must be reported and unexpected versions
must stop the run. Phase 3's runner rejects live Test requests.
