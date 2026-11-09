"""Bounded real-physics validation and one real-model smoke episode per scenario."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

from .config import ROOT, Config
from .presentation_scenarios import DIRECTORY, VERSION, catalogue, get_sample, load_samples, validate
from .study_data import sha256, write_json

OUTPUT = ROOT / "outputs/presentation_dag_v1"
METHODS = ("llm_noask", "llm_gate", "jev_gate")


def oracle_one(sample_id):
    from .diverse_world import DiverseEnvironment, DiverseSkills
    from .study_evaluator import evaluate_study, expected_targets
    from .study_oracle import initial_penetrations, code_hash
    sample = get_sample(sample_id)
    out = OUTPUT / "oracle" / sample_id
    out.mkdir(parents=True, exist_ok=True)
    if (out / "trace.json").exists():
        raise FileExistsError("Oracle trace already exists; do not replace evidence")
    started = time.perf_counter()
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        env.save_scene(out / "scene.png")
        initial, penetration = env.snapshot(), initial_penetrations(env)
        skills, actions = DiverseSkills(env), []
        targets = expected_targets(sample, env)
        roles = ("block", "cup") if sample.dag["order"] == "block_first" else ("cup", "block")
        for role in roles:
            actions.append(skills.pick_place(sample.theta_star[role + "_choice"], targets[role]).to_dict())
        if sample.template_id == "pack_and_cover":
            actions.append(skills.cover(sample.theta_star["lid_choice"], "box").to_dict())
        evaluation = evaluate_study(env, sample, clarification_burden=0, actions=actions,
                                    termination="presentation_physical_oracle")
        env.save_scene(out / "final.png")
        trace = dict(sample_id=sample_id, evidence_kind="real_pybullet_deterministic_oracle",
            scene_sha256=sha256(ROOT / sample.scene_spec_ref), physics_code_sha256=code_hash(),
            initial_observation=initial, initial_penetrations=penetration, actions=actions,
            execution_log=env.events, final_observation=env.snapshot(), evaluation=evaluation,
            api_attempts=0, wall_time_s=time.perf_counter() - started)
        write_json(out / "trace.json", trace)
    row = dict(sample_id=sample_id, template_id=sample.template_id, group_id=sample.group_id,
        success=bool(evaluation["task_success"]) and not penetration,
        initial_penetrations=len(penetration), actions=len(actions),
        succeeded_actions=sum(a["success"] for a in actions))
    print(json.dumps(row), flush=True)
    return row


def oracle(workers=3):
    validate()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(oracle_one, [s.sample_id for s in load_samples()]))
    result = dict(evidence_kind="real_pybullet_deterministic_oracle", total=len(rows),
        successes=sum(r["success"] for r in rows), api_attempts=0, runs=rows)
    write_json(OUTPUT / "oracle" / "summary.json", result)
    return result


def preregister():
    from .accounting import Limits
    from .study_agents import ACTION_PROMPT, GATE_RULES, QUESTION_PROMPT
    from .study_oracle import code_hash
    validate()
    summary = json.loads((OUTPUT / "oracle/summary.json").read_text())
    if summary["total"] != 20 or summary["successes"] != 20:
        raise ValueError("All presentation scenarios must first pass the real physical oracle")
    path = OUTPUT / "live_manifest.json"
    if path.exists():
        raise FileExistsError("Online run manifest already locked")
    jobs = [dict(sample_id=s.sample_id, method=METHODS[i % 3], record=True)
            for i, s in enumerate(load_samples())]
    random.Random(427820).shuffle(jobs)
    result = dict(version=VERSION, purpose="20 unpaired presentation smoke episodes, one per scenario; not a method ranking",
        dataset_sha256=sha256(ROOT / DIRECTORY / "samples.jsonl"),
        code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        configuration=replace(Config.load(), threshold=.5).public_config(),
        limits=asdict(Limits(max_api_attempts=24)), session_max_attempts=200, session_max_episodes=20,
        prompt_hashes={k: hashlib.sha256(v.encode()).hexdigest() for k, v in
                       (("action", ACTION_PROMPT), ("question", QUESTION_PROMPT), ("gate", GATE_RULES))},
        physics_code_sha256=code_hash(), retry_policy="one retry, shared 200-attempt cap; permanent/three-consecutive-error backend circuit breaker",
        run_order_seed=427820, jobs=jobs)
    write_json(path, result)
    return result


def live_one(job):
    from .accounting import Limits, SessionLedger
    from .research_runner import run_sample
    manifest = json.loads((OUTPUT / "live_manifest.json").read_text())
    config = replace(Config.load(), threshold=.5)
    if manifest["configuration"] != config.public_config():
        raise ValueError("Live configuration differs from locked manifest")
    if manifest["dataset_sha256"] != sha256(ROOT / DIRECTORY / "samples.jsonl"):
        raise ValueError("Dataset changed after preregistration")
    out = OUTPUT / "live" / f"{job['sample_id']}__{job['method']}"
    session = SessionLedger(OUTPUT / "session", 200, 20, policy="phase3_dev")
    episode = run_sample(get_sample(job["sample_id"]), job["method"], out, live=True,
        config=config, limits=Limits(**manifest["limits"]), session=session, record=job["record"], quiet=True)
    row = episode_row(episode, out)
    print(json.dumps(row), flush=True)
    return row


def run_live(workers=3):
    manifest = json.loads((OUTPUT / "live_manifest.json").read_text())
    if (OUTPUT / "live").exists():
        raise FileExistsError("This run directory already exists; resume must never silently rerun episodes")
    # A shared file-locked ledger counts every authenticated attempt, including retries.
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(live_one, manifest["jobs"]))
    write_json(OUTPUT / "live_completion.json", dict(episodes=len(rows), rows=rows))
    return report()


def episode_row(e, out):
    evaluation, cost = e["evaluation"], e["cost"]
    return dict(sample_id=e["sample_id"], method=e["method"],
        task_success=evaluation["task_success"], termination=evaluation["termination_reason"],
        burden=evaluation.get("clarification_burden", e["diagnostics"]["clarification_burden"]), ask_turns=sum("question" in t for t in e["turns"]),
        actions=len(e["actions"]), api_attempts=cost["api_attempts"],
        api_latency_s=(cost["api_latency_ms"] / 1000 if cost["api_latency_ms"] is not None else None),
        deepseek_input_tokens=cost["deepseek"]["input_tokens"], deepseek_output_tokens=cost["deepseek"]["output_tokens"],
        jev_input_tokens=cost["jev"]["input_tokens"], jev_output_tokens=cost["jev"]["output_tokens"],
        schema_errors=cost["schema_errors"], api_errors=cost["api_errors"],
        episode_path=str(Path(out).relative_to(ROOT) / "episode.json"))


def timing_diagnostics(episode):
    """Post-hoc public-only diagnostic, never fed to models or used as a score.

    This conservative scripted support check is a teaching aid, not a gold
    optimal-timing label or a counterfactual success experiment.
    """
    from .console_policy import ConsoleScriptedPlanner
    from .task import PublicState
    planner, rows = ConsoleScriptedPlanner(), []
    for turn in episode['turns']:
        payload = turn['public_payload']
        raw = dict(payload['observation'])
        raw['objects'] = {o['object_id']: {k: v for k, v in o.items() if k != 'object_id'}
                          for o in raw['objects']}
        state = PublicState.build(raw, payload['history'], payload['instruction'])
        supported = planner.next_action(state, known_only=True)
        decision = turn['gate']['decision']
        flag = ('ask_with_supported_progress' if decision == 'ASK' and supported and supported.kind != 'DONE'
                else 'ask_after_supported_done' if decision == 'ASK' and supported and supported.kind == 'DONE'
                else 'continue_without_disclosed_next_action' if decision == 'CONTINUE' and supported is None
                else None)
        rows.append(dict(round=turn['round'], gate_decision=decision,
            p_ask=turn['gate'].get('p_ask'),
            supported_action_from_public_state=supported.to_dict() if supported else None, flag=flag))
    return rows


def report():
    entries = {e["sample_id"]: e for e in catalogue()}
    rows, diagnostics = [], []
    for path in sorted((OUTPUT / "live").glob("*/episode.json")):
        episode = json.loads(path.read_text())
        diagnostics.append(dict(sample_id=episode['sample_id'], method=episode['method'],
            turns=timing_diagnostics(episode),
            physical_skill_failures=sum(not a['success'] for a in episode['actions']),
            failed_conditions=[k for k, v in episode['evaluation'].get('conditions', {}).items() if not v],
            ask_physics_frozen=all(c['before_step'] == c['after_step'] and c['state_unchanged']
                                   for c in episode['ask_checks'])))
        rows.append({**episode_row(episode, path.parent),
            "unknown_preferences": entries[episode["sample_id"]]["unknown_preferences"],
            "order": entries[episode["sample_id"]]["order"],
            "template_id": entries[episode["sample_id"]]["template_id"],
            "group_id": entries[episode["sample_id"]]["group_id"]})
    if not rows:
        raise ValueError("No real episode records; refusing to create an experiment result table")
    with (OUTPUT / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    methods = {}
    for method in METHODS:
        subset = [r for r in rows if r["method"] == method]
        def total(key):
            values = [r[key] for r in subset if r[key] is not None]
            return sum(values) if values else None
        methods[method] = dict(episodes=len(subset), successes=total("task_success"), burden=total("burden"),
            api_latency_s=total("api_latency_s"), api_attempts=total("api_attempts"),
            **{key: total(key) for key in ("deepseek_input_tokens", "deepseek_output_tokens", "jev_input_tokens", "jev_output_tokens")})
    result = dict(evidence_kind="real_model_and_real_pybullet", episodes=len(rows),
        successes=sum(r["task_success"] for r in rows), methods=methods, rows=rows,
        caution="Unpaired smoke demonstration: different scenarios per method, 10 physical groups. Not an unbiased method comparison or held-out Test result.")
    write_json(OUTPUT / "summary.json", result)
    write_json(OUTPUT / "timing_diagnostics.json", dict(
        scope='Post-hoc public-only scripted support check, not optimal-timing ground truth; no private preferences used',
        rows=diagnostics))
    lines = ["# Twenty DAG Presentation Scenarios", "", result["caution"], "",
        "| Scenario | Method | Unknown | Order | Success | Burden | API seconds |", "|---|---|---:|---|---|---:|---:|"]
    for r in rows:
        latency = f"{r['api_latency_s']:.2f}" if r["api_latency_s"] is not None else "unknown"
        lines.append(f"| {r['sample_id']} | {r['method']} | {r['unknown_preferences']} | {r['order']} | {r['task_success']} | {r['burden']} | {latency} |")
    lines += ["", "| Method (unpaired cases) | Success | Total burden | Cumulative API seconds | DeepSeek in / out | Jev in / out |",
              "|---|---:|---:|---:|---:|---:|"]
    for method, m in methods.items():
        jev = f"{m['jev_input_tokens']} / {m['jev_output_tokens']}" if m['jev_input_tokens'] is not None else '—'
        latency = f"{m['api_latency_s']:.2f}" if m['api_latency_s'] is not None else 'unknown'
        lines.append(f"| {method} | {m['successes']}/{m['episodes']} | {m['burden']} | {latency} | {m['deepseek_input_tokens']} / {m['deepseek_output_tokens']} | {jev} |")
    flags = Counter(t['flag'] for d in diagnostics if d['method'] != 'llm_noask' for t in d['turns'] if t['flag'])
    lines += ["", "## Timing observations", "",
        "The support check below reads only the logged public instruction, observation and history; it does not label optimal timing or modify any run.", ""]
    for flag, count in flags.items():
        lines.append(f"- `{flag}`: {count} turns.")
    failed_skills = sum(d['physical_skill_failures'] for d in diagnostics)
    lines += ["", f"{sum(r['actions'] for r in rows)} robot skills executed; {failed_skills} skill failures, but {len(rows)-result['successes']} episodes failed the independent final preference/geometry/order conditions. Physical skill completion is not task success.",
        "", "Useful presentation cases:", "",
        "- `dag_demo_03` (Jev): block-first, block unknown. Scores 0.05/0.06/0.05/0.05 never cross 0.5; guessed object/order fails. A genuine missed-clarification example.",
        "- `dag_demo_05` (LLM-Gate) and `dag_demo_06` (Jev): ask at round 0 despite a supported placement. These show premature clarification, even though final tasks succeed.",
        "- `dag_demo_14` (LLM-Gate): no ASK about the unknown block; its guess happens to be correct. Success does not prove appropriate timing.",
        "- `dag_demo_15` (Jev): one missing destination; one answer is reused for the cup and the block's OTHER destination. Success, burden 1.",
        "- `dag_demo_18` (Jev): all three choices unknown; ASK at round 0 (p=0.97), then two placements and success.",
        "", "## Provenance and scope", "",
        "20 instances from 10 physical groups, 10 per template; missing counts 0/1/2/3 each occur 5 times. They reuse conservative development geometry, not held-out Test data.",
        "Each JSON trace, physical score, PNG and GIF is retained in `live/`. All requests use the unchanged shared v3.1 contract and Jev threshold 0.5.",
        "Returned models: DeepSeek `deepseek-flash`; Jev `jev-1.14.0` (configured `jev-latest`). No prompt or threshold tuning was performed on these runs.",
        "Metrics are derived from the raw episode JSONs, and the full job order/configuration is in `live_manifest.json`. Timing findings remain engineering diagnostics, not a formal comparative result."]
    (OUTPUT / "report.md").write_text("\n".join(lines) + "\n")
    return result
