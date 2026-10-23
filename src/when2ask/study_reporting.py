"""Auditable paired Dev metrics and selection, calculated from raw episode files."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from .accounting import Audit
from .calibration import FROZEN_DATA, LIVE, PLAN, SELECTION_RULE, utc_now, verify_data_freeze
from .config import Config, ROOT
from .diverse_world import PHYSICS_VERSION
from .protocol import public_payload
from .study_agents import PROMPT_VERSION, prompt_hashes
from .study_data import load_study, sha256, write_json
from .study_evaluator import EVALUATOR_VERSION
from .study_protocol import disclosed_choices, public_roles
from .task import PublicState


def known_sum(values):
    known = [x for x in values if x is not None]
    return sum(known) if known else None


def wilson(successes, groups):
    if not groups:
        return [None, None]
    z, n, p = 1.959963984540054, groups, successes / groups
    center = (p + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0, center-half), min(1, center+half)]


def paired_interval(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(SELECTION_RULE["bootstrap_seed"])
    sampled = values[rng.integers(0, len(values), size=(SELECTION_RULE["bootstrap_draws"], len(values)))].mean(axis=1)
    return np.quantile(sampled, SELECTION_RULE["paired_interval"]).tolist()


def select_threshold(rows):
    by_condition = {}
    for row in rows:
        by_condition.setdefault(row["condition"], {})[row["group_id"]] = row
    baseline = by_condition.get("jev_gate@0.5", {})
    result = dict(selected_threshold=.5, default_threshold=.5, rule=SELECTION_RULE,
                  reason="No adequately supported alternative; retain predeclared default.", comparisons={})
    groups = sorted(baseline)
    if len(groups) != 8:
        result["reason"] = "Incomplete independent-group pairing; retain default."
        return result
    eligible = []
    for threshold in (.3, .7):
        alternative = by_condition.get(f"jev_gate@{threshold:.1f}", {})
        if set(alternative) != set(groups):
            result["comparisons"][str(threshold)] = dict(eligible=False, reason="incomplete pairing")
            continue
        sr_diff = [int(alternative[g]["task_success"]) - int(baseline[g]["task_success"]) for g in groups]
        burden_gain = [baseline[g]["burden"] - alternative[g]["burden"] for g in groups]
        latency_gain = [baseline[g]["api_latency_ms"] - alternative[g]["api_latency_ms"] for g in groups]
        sr_ci, burden_ci, latency_ci = paired_interval(sr_diff), paired_interval(burden_gain), paired_interval(latency_gain)
        identical_success = all(d == 0 for d in sr_diff)
        identical_burden = all(d == 0 for d in burden_gain)
        baseline_latency = sum(baseline[g]["api_latency_ms"] for g in groups)
        relative_latency_gain = sum(latency_gain) / baseline_latency if baseline_latency else 0
        reason = ("success" if sr_ci[0] > 0 else "burden" if identical_success and burden_ci[0] > 0 else
                  "latency" if identical_success and identical_burden and relative_latency_gain >= .1 and latency_ci[0] > 0 else None)
        result["comparisons"][str(threshold)] = dict(groups=groups, success_diff=sr_diff,
            success_diff_interval=sr_ci, burden_saving=burden_gain, burden_saving_interval=burden_ci,
            latency_saving_ms=latency_gain, latency_saving_interval_ms=latency_ci,
            relative_latency_saving=relative_latency_gain, eligible=reason is not None, reason=reason)
        if reason:
            eligible.append((threshold, alternative, reason))
    if eligible:
        threshold, _, reason = min(eligible, key=lambda item: (
            -sum(v["task_success"] for v in item[1].values()), sum(v["burden"] for v in item[1].values()),
            sum(v["api_latency_ms"] for v in item[1].values()), abs(item[0] - .5)))
        result.update(selected_threshold=threshold, reason=f"Predeclared paired rule selected {threshold} on {reason}; exploratory only.")
    return result


def public_progress(payload):
    """Diagnostic of timing using ONLY the same public projection as the models.

    This is never fed back to a gate/planner and never changes task scoring.
    Recovery turns are left unclassified rather than treated as a timing oracle.
    """
    obs = dict(payload["observation"])
    obs["objects"] = {o["object_id"]: {k:v for k,v in o.items() if k != "object_id"} for o in obs["objects"]}
    state = PublicState.build(obs, payload["history"], payload["instruction"])
    choices, roles = disclosed_choices(state), public_roles(state)
    spatial = obs["spatial_relations"]
    inside = spatial.get("inside_containers", {})
    containers = list(inside)
    if not containers:
        return "unclassified"
    if len(containers) == 1:
        targets = {"cup": containers[0], "block": containers[0]}
    elif "cup_destination" in choices:
        targets = {"cup": choices["cup_destination"], "block": next(c for c in containers if c != choices["cup_destination"])}
    else:
        targets = {}
    complete = {r: r in choices and r in targets and choices[r] in inside[targets[r]] for r in ("cup", "block")}
    order = "cup" if "Place the cup before the block." in state.instruction else (
        "block" if "Place the block before the cup." in state.instruction else None)
    for role in ("cup", "block"):
        if role in choices and role in targets and not complete[role] and (not order or role == order or complete[order]):
            return "supported_progress"
    if all(complete.values()):
        if len(containers) == 2:
            return "complete"
        if "lid" in choices:
            if choices["lid"] in spatial.get("covering_containers", {}).get(containers[0], []):
                return "complete"
            return "supported_progress"
    if any(role not in choices for role in roles):
        return "preference_blocked"
    return "unclassified_recovery"


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def dev_report(run_dir=LIVE / "dev", *, output_dir=None):
    run_dir = Path(run_dir)
    out = Path(output_dir or ROOT / "outputs/phase3/report")
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    samples = {s.sample_id:s for s in load_study("dev")}
    rows, cases, attempts, models = [], [], [], {"deepseek":set(), "jev":set()}
    for job in plan["jobs"]:
        path = run_dir / job["run_id"] / "episode.json"
        if not path.exists():
            continue
        ep = json.loads(path.read_text())
        if ep.get("evidence_kind") != "live_model_and_physics":
            raise ValueError("Only real-model/real-physics evidence may enter Dev metrics")
        if ep["partition"] != "dev" or ep["prompt_hashes"] != plan["prompt_hashes"]:
            raise ValueError("Test/mixed-prompt episodes cannot enter calibration")
        expected = dict(plan["model_configuration"], jev_threshold=job["threshold"])
        if ep["planner_configuration"] != expected or ep["sample_id"] != job["sample_id"]:
            raise ValueError("Episode differs from pre-registered pairing/configuration")
        audit = Audit(ep["episode_id"], Config(), path=path.parent / "api_attempts.jsonl")
        cost = audit.summary()
        if cost != ep["cost"]:
            raise ValueError("Episode cost does not match raw per-attempt JSONL")
        attempts.extend(audit.records)
        for r in audit.records:
            if r.get("returned_model"):
                models[r["backend"]].add(r["returned_model"])
        timing = {"early_asks":0, "blocked_continues":0, "complete_asks":0}
        turn_timings = []
        for turn in ep["turns"]:
            category = public_progress(turn["public_payload"])
            decision = turn.get("gate", {}).get("decision")
            timing["early_asks"] += category == "supported_progress" and decision == "ASK"
            timing["blocked_continues"] += category == "preference_blocked" and decision == "CONTINUE"
            timing["complete_asks"] += category == "complete" and decision == "ASK"
            turn_timings.append(dict(round=turn["round"], category=category, decision=decision,
                                     p_ask=turn.get("gate", {}).get("p_ask")))
        ds, jev = cost["deepseek"], cost["jev"]
        row = dict(run_id=job["run_id"], sample_id=job["sample_id"], group_id=job["group_id"],
            template_id=job["template_id"], missing_preferences=job["missing_preferences"], condition=job["condition"],
            task_success=ep["evaluation"]["task_success"], burden=ep["diagnostics"]["clarification_burden"],
            ask_turns=ep["diagnostics"]["ask_turns"], actions=len(ep["actions"]),
            deepseek_input_tokens=ds["input_tokens"], deepseek_output_tokens=ds["output_tokens"],
            jev_input_tokens=jev["input_tokens"], jev_output_tokens=jev["output_tokens"],
            api_latency_ms=cost["api_latency_ms"], wall_time_s=ep["wall_time_s"],
            api_attempts=cost["api_attempts"], retries=cost["retries"], schema_errors=cost["schema_errors"],
            api_errors=cost["api_errors"], termination_reason=ep["termination_reason"],
            repeated_requests=ep["diagnostics"]["repeated_slot_requests"],
            redundant_requests=ep["diagnostics"]["redundant_slot_requests"],
            physical_failures=ep["diagnostics"]["physical_execution_failures"], **timing,
            episode_path=str(path.relative_to(ROOT)), episode_sha256=sha256(path))
        rows.append(row)
        cases.append(dict(run_id=job["run_id"], task_success=row["task_success"],
            failed_conditions=[k for k,v in ep["evaluation"].get("conditions",{}).items() if not v],
            timing=turn_timings, asks=[dict(round=t["round"], question=t["question"], answer=t["user_answer"])
                                      for t in ep["turns"] if "question" in t],
            failed_actions=[a for a in ep["actions"] if not a["success"]], error=ep["error"]))
    if not rows:
        raise ValueError("No real Dev episodes available")
    summary_rows = []
    for condition in dict.fromkeys(j["condition"] for j in plan["jobs"]):
        subset = [r for r in rows if r["condition"] == condition]
        if not subset:
            continue
        if len({r["group_id"] for r in subset}) != len(subset):
            raise ValueError("This pilot expects exactly one sample per independent group")
        row = dict(condition=condition, successes=sum(r["task_success"] for r in subset), episodes=len(subset),
                   independent_groups=len(subset), success_rate=sum(r["task_success"] for r in subset)/len(subset))
        row["success_interval_group_wilson95"] = wilson(row["successes"], len(subset))
        for name in ("burden", "ask_turns", "deepseek_input_tokens", "deepseek_output_tokens", "jev_input_tokens",
                     "jev_output_tokens", "api_latency_ms", "wall_time_s", "api_attempts", "retries", "schema_errors",
                     "api_errors", "physical_failures", "repeated_requests", "redundant_requests",
                     "early_asks", "blocked_continues", "complete_asks"):
            row[name] = known_sum([r[name] for r in subset])
        row["mean_burden"] = row["burden"] / len(subset)
        summary_rows.append(row)
    selection = select_threshold(rows)
    smoke_path = LIVE / "revalidation_attempts.jsonl"
    smoke_attempts = [json.loads(line) for line in smoke_path.read_text().splitlines()] if smoke_path.exists() else []
    all_attempts = smoke_attempts + attempts
    ledger = json.loads((LIVE / "session_budget.json").read_text())
    ids = [r["session_attempt"] for r in all_attempts]
    if sorted(ids) != list(range(1, ledger["attempts"] + 1)):
        raise ValueError("Global authenticated request audit is incomplete or duplicated")
    result = dict(study_id=plan["study_id"], evidence="real API + real PyBullet; no mock rows",
        plan_sha256=sha256(PLAN), episodes=len(rows), independent_groups=len({r["group_id"] for r in rows}),
        aggregate=summary_rows, threshold_selection=selection,
        returned_models={k:sorted(v) for k,v in models.items()}, session=ledger,
        global_audit=dict(attempts=len(all_attempts), session_ids_contiguous_unique=True,
                          statuses={s:sum(r["status"]==s for r in all_attempts) for s in {r["status"] for r in all_attempts}},
                          unknown_inference_usage=sum(r.get("stage")!="models" and
                              (r.get("input_tokens") is None or r.get("output_tokens") is None) for r in all_attempts)),
        dataset=verify_data_freeze()["distribution"], test_api_episodes=0)
    write_csv(out / "episodes.csv", rows)
    write_csv(out / "summary.csv", summary_rows)
    write_json(out / "summary.json", result)
    write_json(out / "error_and_timing_cases.json", cases)
    write_json(out / "threshold_selection.json", selection)
    write_json(out / "paired_groups.json", {g:{r["condition"]:r["run_id"] for r in rows if r["group_id"]==g}
                                           for g in sorted({r["group_id"] for r in rows})})
    lines = ["# Phase 3 Dev calibration — engineering pilot", "",
             "All figures below are calculated from raw real-model episodes and per-attempt JSONL. "
             "Each method/threshold ran a fresh physical episode. No formal Test inference was run.", "",
             "| Condition | Success | Burden total (mean) | DeepSeek in/out | Jev in/out | API latency s |",
             "|---|---:|---:|---:|---:|---:|"]
    for r in summary_rows:
        lines.append(f"| {r['condition']} | {r['successes']}/{r['episodes']} | {r['burden']} ({r['mean_burden']:.2f}) | "
            f"{r['deepseek_input_tokens']}/{r['deepseek_output_tokens']} | "
            f"{r['jev_input_tokens']}/{r['jev_output_tokens']} | {r['api_latency_ms']/1000:.3f} |")
    lines += ["", f"Selected threshold: **{selection['selected_threshold']}**. {selection['reason']}", "",
              "Intervals use independent scene groups (8 per condition), not paraphrases or truth variants. "
              "SR intervals are group-level Wilson 95%; alternative-vs-default differences use the predeclared "
              "paired group bootstrap 97.5% intervals. This small pilot does not establish equivalence or generalization.",
              "", "Backend tokens remain separate and do not imply equal monetary cost. None denotes unknown/unused usage, "
              "not a manufactured zero. API latency is cumulative agent inference time; wall time also includes physics.",
              "", "## Dataset", "", "| Partition | Samples | Independent groups | Missing 0/1/2/3 |",
              "|---|---:|---:|---|"]
    for partition, d in result["dataset"].items():
        lines.append(f"| {partition} | {d['samples']} | {d['groups']} | " + "/".join(str(d["missing"][str(i)]) for i in range(4)) + " |")
    lines += ["", "## Timing and errors", "",
              "Timing labels in error_and_timing_cases.json use only public information, are diagnostics, "
              "and never feed back into any model or success score. Recovery states may be unclassified.", ""]
    for r in summary_rows:
        lines.append(f"- {r['condition']}: early ASK={r['early_asks']}, blocked CONTINUE={r['blocked_continues']}, "
            f"complete ASK={r['complete_asks']}, redundant slots={r['redundant_requests']}, "
            f"physical failures={r['physical_failures']}, API/schema errors={r['api_errors']}/{r['schema_errors']}.")
    lines += ["", "## Traceability", "", "See episodes.csv for sample/group pairing, episode path/hash, "
              "input/output usage, latency, termination and diagnostics; paired_groups.json retains paired units. "
              "threshold_selection.json preserves every paired difference and interval. "
              "Each episode directory includes API request/responses, public states, actions, Bullet events, "
              "dense physical trajectory, ASK invariance checks, evaluator details and real rendered PNGs.", "",
              f"Global authenticated requests: {ledger['attempts']}/600; episodes: {ledger['episodes']}/40. "
              "Discovery and smoke requests are counted separately from the method table, but included in this global ceiling.", ""]
    (out / "dev_report.md").write_text("\n".join(lines))
    return result


def freeze_test():
    frozen = verify_data_freeze()
    report_path = ROOT / "outputs/phase3/report/summary.json"
    result = json.loads(report_path.read_text())
    if result["episodes"] != 40 or result["independent_groups"] != 8:
        raise ValueError("Incomplete Dev study; do not freeze a claimed completed calibration")
    models = result["returned_models"]
    if any(len(models[b]) != 1 for b in ("deepseek", "jev")):
        raise ValueError("Returned model changed within study; version/resolve before freezing Test")
    plan = json.loads(PLAN.read_text())
    source_commit = plan["code_commit"]
    config = dict(experiment_id="phase4_formal_test_v1", status="FROZEN_NOT_RUN", frozen_at=utc_now(),
        partition="test", no_test_api_experiments_in_phase3=True,
        models={"deepseek":dict(configured=plan["model_configuration"]["deepseek_model"], returned=models["deepseek"][0]),
                "jev":dict(configured=plan["model_configuration"]["jev_model"], returned=models["jev"][0])},
        gate_threshold=result["threshold_selection"]["selected_threshold"],
        threshold_selection_sha256=sha256(ROOT / "outputs/phase3/report/threshold_selection.json"),
        prompt_version=PROMPT_VERSION, prompt_hashes=prompt_hashes(),
        planner_parameters={k:v for k,v in plan["model_configuration"].items() if k not in ("jev_threshold",)},
        planner_temperature=0, gate_max_output_tokens=64, planner_max_output_tokens=500,
        skill_version=PHYSICS_VERSION, evaluator_version=EVALUATOR_VERSION,
        physics_code_sha256=frozen["physics_code_sha256"], dataset_version=frozen["dataset_version"],
        dataset_hashes=frozen["dataset_hashes"], dataset_freeze_sha256=sha256(FROZEN_DATA),
        scene_manifest_sha256=sha256(ROOT / "data/phase3/manifest.json"),
        code_commit=source_commit, source_sha256=plan["source_sha256"],
        dev_manifest_sha256=sha256(PLAN), dev_report_sha256=sha256(report_path),
        per_episode_budgets=plan["limits"], retry_policy=plan["retry_policy"],
        methods=["llm_noask", "llm_gate", "jev_gate"],
        model_drift_policy="Abort on unexpected returned model; deepseek-flash is an alias, exact underlying build unavailable.",
        amendment_policy="Any changed prompt/model/threshold/dataset/controller requires a new experiment ID and manifest.",
        test_run_plan=dict(samples=128, independent_groups=16, methods=3, fresh_episodes=384,
            interleave_seed=427804, run_unit="sample paired across methods; cluster inference/statistics by physical group",
            maximum_authenticated_episode_attempts=384*64,
            suggested_separate_approved_study_request_cap=5000,
            suggested_execution="First an approved bounded canary, then interleaved jobs; stop at cap or backend circuit. "
                                "Do not tune on canary/Test outcomes. Any repair starts a separately versioned experiment.",
            authentication_discovery_and_smoke_count_toward_cap=True,
            note="No Test API budget was spent or authorized by the Phase 3 runner."))
    target = ROOT / "configs/frozen_test.yaml"
    if target.exists():
        prior = json.loads(target.read_text())
        # Time is not an experimental parameter. Existing frozen parameters cannot
        # be silently replaced by a regenerated artifact.
        compare = dict(config, frozen_at=prior["frozen_at"])
        if prior != compare:
            raise ValueError("Frozen Test configuration differs; create an explicit new experiment version")
        return prior
    write_json(target, config)  # JSON is a YAML 1.2 subset, no extra runtime dependency.
    write_json(ROOT / "configs/frozen_test_manifest.json", dict(config_path="configs/frozen_test.yaml",
        config_sha256=sha256(target), frozen_data_sha256=sha256(FROZEN_DATA), code_commit=source_commit,
        test_dataset_sha256=frozen["dataset_hashes"]["test"], status="NOT_RUN"))
    return config
