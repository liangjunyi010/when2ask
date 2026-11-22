# When2Ask

Clarification timing for robotic tasks. CS5478 Team 11: Liang Junyi and Yang Haocheng.

[Report](report/When2Ask_Final_Report.pdf) · [Presentation](ppt/When2Ask_Team11_Final.pptx)

When2Ask constructs task graphs and PyBullet scenes, then compares NoAsk, LLM-Gate and Jev-Gate with a shared action and question planner. A separate LLM user holds the complete intent and answers only the requested choices.

## Project layout

| Folder | Contents |
|---|---|
| `src/when2ask/` | Task generation, physical skills, interaction and evaluation |
| `config/` | Benchmark quotas, model settings and pricing schema |
| `script/` | Setup, command-line entry point and plotting |
| `tests/` | Offline tests that block network access and physics connections |
| `report/` | Final report PDF |
| `ppt/` | Presentation |
| `graph/` | Figure instructions |

Generated datasets, environments, request logs, results, videos and virtual environments stay local and are excluded from Git. `scripts` links to `script` so the setup command in the report works.

## Method and benchmark

The generator creates a directed acyclic task graph, designates uncertain subgoals, instantiates the scene and samples fixed private choices. It then produces the initial instruction with the selected disclosures. User preferences require an answer; world facts can be obtained through observation.

Graph nodes represent task operations. They include individual placements, packing before covering, counting and restocking, opening and restoring a container, exchanges through temporary pads, station visits, and uncovering and reading a label. Independent operations can branch. The number of items, checkpoints and obstructions determines each graph's size. Nodes are separate from motor steps and API calls.

The configuration follows Table 1:

| Task family | Environments | Fully specified | Nodes | Uncertain nodes |
|---|---:|---:|---:|---:|
| Pack & Cover | 105 | 31 | 6–10 | 2–3 |
| Two Containers | 97 | 27 | 5–9 | 1–3 |
| Category Sorting | 108 | 34 | 7–10 | 1–2 |
| Inventory Restock | 102 | 29 | 6–10 | 1–2 |
| Retrieve & Restore | 94 | 23 | 5–7 | 1–2 |
| Buffered Exchange | 99 | 28 | 6–9 | 1–2 |
| Find & Approach | 104 | 36 | 5–8 | 1–2 |
| Patrol & Return | 91 | 26 | 6–10 | 1–2 |
| Reveal & Inspect | 100 | 32 | 5–7 | 1–2 |
| Total | 900 | 266 | | |

A physical oracle executes the required skills and checks the final geometry and prerequisite order. Candidates that fail are discarded and regenerated. Model evaluation accepts only datasets with matching oracle evidence and checksums.

| Report component | Implementation |
|---|---|
| Graph, scene and instruction synthesis | `task_graph.py`, `dag_benchmark.py` |
| Robot observations and motor skills | `physical_world.py`, `table_world.py`, `navigation_world.py`, `skills.py` |
| Public state, actions and questions | `dag_world.py` |
| Fixed-intent LLM user | `user_simulator.py` |
| Gates and shared planner | `dag_evaluation.py` |
| Physical goals and task order | `graph_evaluator.py` |
| Request time, usage and cost | `model_client.py` |

The agent receives the initial instruction, current observations and interaction history. Private choices, the internal graph, evaluator results and sample identifiers are excluded. Each action invokes one robot skill. A question invokes the LLM user without advancing the physical world. The evaluator checks success independently of `DONE`.

`GraphWorld` exposes `reset()`, `step(action)` and `score()`. Actions use the IDs in the observation's affordances. `ASK` takes `text` and `slots`; the user client is supplied when constructing the environment. Terminal reward is the evaluator's success indicator.

## Setup

Use Python 3.11 on macOS or Linux.

```bash
git clone https://github.com/liangjunyi010/when2ask.git
cd when2ask
bash script/setup_env.sh
.venv/bin/python -m when2ask doctor
.venv/bin/python -m pytest -q
```

`doctor` checks imports. Tests use temporary fixtures and do not call model services or start PyBullet worlds.

## Generate and validate

```bash
.venv/bin/python script/benchmark.py generate \
  --config config/benchmark.json \
  --output data/evaluation_v3 \
  --validate-physics
.venv/bin/python script/benchmark.py inspect --dataset data/evaluation_v3
```

Generation never overwrites an existing directory. Its manifest records the configuration, actual statistics, checksums and oracle validation status. Omitting `--validate-physics` creates task definitions for inspection; those definitions cannot be used for model evaluation until physically validated through a new generation run.

Scene dimensions and task composition are defined in `task_graph.py`. Runtime budgets and request settings are explicit configuration values: 60 rounds, 60 physical actions, separate agent and user request limits, and one retry. These are adjustable implementation defaults. The report specifies the benchmark quotas and Jev threshold; it does not prescribe these runtime settings.

## Models and interaction

```bash
cp .env.example .env
cp config/pricing.example.json result-pricing.json
```

Set actual API model IDs, base URLs and credentials in `.env`. Set the model IDs, price date and per-million-token rates in the pricing file. Model display names and API identifiers are separate. Chat endpoint options and the output-token field are configurable in `config/models.json`.

The LLM user receives the complete fixed intent and current question. Its structured reply contains exactly the requested choices. Extra disclosures, invalid values and changed intent are rejected. There is no static-answer fallback. The same user profile and prompt apply across methods.

```bash
.venv/bin/python script/benchmark.py run \
  --dataset data/evaluation_v3 \
  --pricing result-pricing.json \
  --output result/evaluation_v3 \
  --live
```

| Model | Method |
|---|---|
| DeepSeek Flash | NoAsk |
| DeepSeek Flash | LLM-Gate |
| DeepSeek Flash | Jev-Gate |
| GPT-5.6 | LLM-Gate |
| GLM 5.2 | LLM-Gate |

These five configurations produce 4,500 episodes over 900 environments. DeepSeek LLM-Gate provides the common baseline for both comparisons. NoAsk skips the gate. LLM-Gate makes a separate decision request to the planner model. Jev-Gate requests one Noul probability and asks when it is at least 0.5. The planner then generates one question or one skill action.

Requests record the model, payload, response, token usage and elapsed API time, including failed attempts. Credentials are redacted. Run manifests preserve code hashes, prompts, model settings, dataset identity and pricing. Invalid planner outputs and budget exhaustion end an episode and are scored. Transport and user-response failures interrupt the run with their records preserved.

## Metrics and figures

```bash
.venv/bin/python script/benchmark.py report \
  --dataset data/evaluation_v3 \
  --run result/evaluation_v3
.venv/bin/python script/build_figures.py \
  --tables result/evaluation_v3/tables.json \
  --output graph/generated
```

Success is the fraction of evaluated episodes satisfying the physical goal and required order. Unnecessary ASK counts fully specified environments with at least one question, divided by all fully specified environments; NoAsk is not applicable. API time sums gate, question and action requests, excluding robot motion and user response time.

Costs use recorded token usage and the configured backend prices. Agent cost, user cost and their total are retained separately. `accounting.cost_scope` selects `agent` or `all` for the comparison table; the default is `agent`. The report explicitly excludes user response time but does not separately specify the user-call cost convention. Missing token usage remains unknown rather than being treated as zero.

Tables require complete paired episode records and matching request checksums. Plotting reads those tables. Reported success rates, time and cost are not hard-coded into the evaluation.
