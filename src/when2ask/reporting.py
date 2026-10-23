"""Auditable pilot tables. Backend tokens stay separate; unknown usage stays null."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .research_runner import METHODS


def known_sum(values):
    known = [value for value in values if value is not None]
    return sum(known) if known else None


def report(run_dir):
    base = Path(run_dir)
    episodes = []
    for path in sorted(base.rglob("episode.json")):
        episode = json.loads(path.read_text())
        if episode.get("evidence_kind") == "live_model_and_physics":
            episodes.append((path, episode))
    if not episodes:
        raise ValueError("No real-model episodes in this directory; offline test doubles are excluded")
    configurations = {(json.dumps(e["planner_configuration"], sort_keys=True),
                       json.dumps(e["prompt_hashes"], sort_keys=True)) for _, e in episodes}
    if len(configurations) != 1:
        raise ValueError("Different prompts/model configurations must be reported separately; choose one cohort directory")
    rows = []
    for path, episode in episodes:
        cost = episode["cost"]
        row = dict(sample_id=episode["sample_id"], group_id=episode["group_id"],
                   partition=episode["partition"], method=episode["method"],
                   scored="final_observation" in episode, task_success=episode["evaluation"]["task_success"],
                   clarification_burden=episode["diagnostics"]["clarification_burden"],
                   ask_turns=episode["diagnostics"]["ask_turns"],
                   api_attempts=cost["api_attempts"], api_latency_ms=cost["api_latency_ms"],
                   episode_wall_time_s=episode["wall_time_s"], retries=cost["retries"],
                   schema_errors=cost["schema_errors"], api_errors=cost["api_errors"],
                   physical_execution_failures=episode["diagnostics"]["physical_execution_failures"],
                   repeated_slot_requests=episode["diagnostics"]["repeated_slot_requests"],
                   redundant_slot_requests=episode["diagnostics"]["redundant_slot_requests"],
                   termination_reason=episode["termination_reason"], path=str(path.relative_to(base)))
        for backend in ("deepseek", "jev"):
            data = cost[backend]
            for kind in ("input_tokens", "output_tokens"):
                row[f"{backend}_{kind}"] = data[kind]
            row[f"{backend}_tokens"] = known_sum([data["input_tokens"], data["output_tokens"]])
            row[f"{backend}_unknown_usage_attempts"] = max(data["unknown_input_tokens_attempts"],
                                                           data["unknown_output_tokens_attempts"])
        rows.append(row)
    aggregates = []
    for method in METHODS:
        selected = [row for row in rows if row["method"] == method]
        scored = [row for row in selected if row["scored"]]
        value = dict(method=method, episodes=len(selected), scored_episodes=len(scored),
                     successful_episodes=sum(row["task_success"] for row in scored),
                     success_rate=sum(row["task_success"] for row in scored) / len(scored) if scored else None,
                     clarification_burden=sum(row["clarification_burden"] for row in selected))
        for key in ("deepseek_input_tokens", "deepseek_output_tokens", "deepseek_tokens",
                    "jev_input_tokens", "jev_output_tokens", "jev_tokens", "api_latency_ms"):
            value[key] = known_sum([row[key] for row in selected])
        for key in ("api_attempts", "retries", "schema_errors", "api_errors",
                    "deepseek_unknown_usage_attempts", "jev_unknown_usage_attempts"):
            value[key] = sum(row[key] for row in selected)
        aggregates.append(value)
    paired = []
    for sample_id in sorted({e["sample_id"] for _, e in episodes}):
        group = [e for _, e in episodes if e["sample_id"] == sample_id]
        hashes = {e["turns"][0]["payload_sha256"] for e in group if e["turns"]}
        planner_configs = {json.dumps(e["planner_configuration"], sort_keys=True) for e in group}
        prompt_hashes = {json.dumps(e["prompt_hashes"], sort_keys=True) for e in group}
        paired.append(dict(sample_id=sample_id, methods=sorted(e["method"] for e in group),
                           all_three_methods=len(group) == 3 and {e["method"] for e in group} == set(METHODS),
                           same_initial_public_payload=len(hashes) == 1,
                           same_planner_configuration=len(planner_configs) == 1,
                           same_prompts=len(prompt_hashes) == 1))
    summary = dict(kind="Engineering Pilot", episodes=len(rows), methods=aggregates, paired_checks=paired,
                   caveat="Tiny controlled sample; no statistical significance or generalization claim. "
                   "Token sums are observed usage, with unknown-attempt counts; backend tokens are not dollar equivalents.")
    base.mkdir(parents=True, exist_ok=True)
    for filename, values in (("episodes.csv", rows), ("summary.csv", aggregates)):
        with (base / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    (base / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# When2Ask Engineering Pilot", "", summary["caveat"], "",
             "| Method | Success | Burden | DeepSeek tokens | Jev tokens | API latency (ms) |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in aggregates:
        def display(value):
            return "—" if value is None else str(round(value, 2))
        lines.append(f"| {row['method']} | {row['successful_episodes']}/{row['scored_episodes']} | "
                     f"{row['clarification_burden']} | {display(row['deepseek_tokens'])} | "
                     f"{display(row['jev_tokens'])} | {display(row['api_latency_ms'])} |")
    lines += ["", "Raw episode paths and separated input/output usage are in episodes.csv.",
              "Every HTTP attempt is retained in the episode api_attempts.jsonl. "
              "API smoke/model-discovery and local user-simulator costs are reported separately.",
              "Final success is based on physics, independently of DONE or budget termination.", ""]
    (base / "report.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))
    return summary
