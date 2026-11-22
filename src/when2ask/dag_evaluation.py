"""Paired model evaluation and tables computed from recorded episodes."""
from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .config import ROOT
from .dag_benchmark import load_dataset, file_digest, read_json, write_json
from .dag_world import GraphWorld, validate_action, ActionLimit
from .model_client import Client, resolve_models, public_models, estimated_cost, token_usage, RequestLimit, ModelOutputError
from .user_simulator import LlmUser, USER_PROMPT

GATE_PROMPT = """Decide whether missing user intent blocks every useful next action.
Continue when a required sensing step or a fully specified subgoal can proceed.
Observe world facts instead of asking the user to guess them. Use only the public state and history.
If complete, CONTINUE so the planner can return DONE.
Return only {"decision":"ASK"} or {"decision":"CONTINUE"}."""
JEV_PROMPT = """Does missing user intent block every useful next action?
Return a high probability only when every useful unfinished subgoal needs a missing user preference.
Return a low probability when observation can reveal the missing world fact, when a fully specified
subgoal can proceed, or when the task is complete. Use only the supplied public state and history."""
ACTION_PROMPT = """Choose one robot skill from observation.affordances using the instruction and history.
Use the exact object and location IDs. Return one JSON object with kind and the required arguments:
move or cover: object_id, target_id; search, approach or inspect_station: location_id;
inspect: target_id; report: code; inspect_inventory or return_home: no arguments.
Respect the task's required order. User answers resolve preferences; observations resolve world facts.
If a required choice remains unknown, select a candidate. This action stage cannot ask a question.
Return {"kind":"DONE"} only when the requested task is complete. Do not add explanations."""
QUESTION_PROMPT = """Ask one concise question for the missing user choices needed to proceed.
Return {"text":"your question","slots":["requested_slot"]}. Use only slot names in observation.choices.
Ask only for relevant missing choices. Do not add a robot action."""


def gate_answer(value):
    if not isinstance(value, dict) or set(value) != {"decision"} or value["decision"] not in ("ASK", "CONTINUE"):
        raise ValueError("Gate must return ASK or CONTINUE")
    return value["decision"]


def question_answer(value, sample):
    if not isinstance(value, dict) or set(value) != {"text", "slots"}:
        raise ValueError("Question requires text and slots")
    slots = value["slots"]
    if not isinstance(value["text"], str) or not 1 <= len(value["text"]) <= 600:
        raise ValueError("Invalid question text")
    if not isinstance(slots, list) or not slots or any(not isinstance(s, str) for s in slots):
        raise ValueError("Question must request named slots")
    if len(slots) != len(set(slots)) or not set(slots) <= set(sample.slots):
        raise ValueError("Question slots must be distinct public slots")
    return value


def run_episode(sample, job, config, client, world_factory=GraphWorld):
    turns = []
    asks, error, world = 0, None, None
    termination, score = "round_limit", None
    try:
        world = world_factory(sample, action_limit=config["limits"]["physical_actions"])
        user = LlmUser(client, sample)
        for turn in range(config["limits"]["rounds"]):
            public = world.public()
            probability = None
            if job["method"] == "noask":
                decision = "CONTINUE"
            elif job["method"] == "llm_gate":
                decision = client.request(job["model"], "gate", GATE_PROMPT, public, gate_answer)
            elif job["method"] == "jev_gate":
                probability = client.request("jev", "gate", JEV_PROMPT, public, lambda x: x)
                decision = "ASK" if probability >= config["threshold"] else "CONTINUE"
            else:
                raise ValueError("Unknown method")
            entry = dict(turn=turn, decision=decision, p_ask=probability, public_state=public)
            turns.append(entry)
            if decision == "ASK":
                asks += 1
                question = client.request(job["model"], "question", QUESTION_PROMPT, public,
                                          lambda x: question_answer(x, sample))
                answer = world.ask(question,user)
                entry.update(question=question, answer=answer)
            else:
                action = client.request(job["model"], "action", ACTION_PROMPT, public,
                    lambda x: validate_action(x, public["observation"]))
                entry["action"] = action
                if action["kind"] == "DONE":
                    termination = "done"
                    break
                result = world.execute(action)
                entry["result"] = result

        score = world.score(asks, termination)
    except (RequestLimit, ModelOutputError, ActionLimit) as exc:
        if getattr(exc,"actor",None)=="user_simulator":
            error, termination = str(client._clean(str(exc))), "user_error"
        else:
            termination = "invalid_model_output" if isinstance(exc,ModelOutputError) else "budget_exhausted"
            score = world.score(asks,termination) if world else None
    except Exception as exc:
        error = str(client._clean(str(exc)))
        termination = "technical_error"
    finally:
        if world:
            world.close()
    return dict(sample_id=sample.sample_id, group_id=sample.group_id, template_id=sample.template_id,
                fully_specified=sample.fully_specified, job=job["name"], model=job["model"], method=job["method"],
                status="complete" if error is None else "incomplete", termination=termination,
                task_success=bool(score and score["task_success"]) if error is None else None,
                ask_count=asks, agent=client.totals(), user_simulator=client.totals("user_simulator"),
                turns=turns, evaluation=score, error=error)


def source_hashes():
    paths = [*(ROOT / "src/when2ask").glob("*.py"), *(ROOT / "config").glob("*.json")]
    return {str(p.relative_to(ROOT)): file_digest(p) for p in sorted(paths)}


def run(dataset, output, config_path, pricing_path, models_path, *, live=False):
    if not live:
        raise ValueError("Model evaluation requires --live")
    data_manifest, samples = load_dataset(dataset, require_oracle=True)
    config, model_settings = read_json(config_path), read_json(models_path)
    if config != data_manifest["config"]:
        raise ValueError("Evaluation configuration differs from the dataset configuration")
    needed = {j["model"] for j in config["jobs"]} | {"user"}
    if any(j["method"] == "jev_gate" for j in config["jobs"]):
        needed.add("jev")
    profiles = resolve_models(model_settings, sorted(needed))
    pricing = read_json(pricing_path)
    for name in needed:
        price = pricing["models"].get(name, {})
        if price.get("model_id") != profiles[name]["model"] or estimated_cost(
                dict(input_tokens=1, cached_input_tokens=0, output_tokens=1), price) is None:
            raise ValueError("Set matching model IDs and finite pricing rates for " + name)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    jobs = [(sample, job) for sample in samples for job in config["jobs"]]
    random.Random(config["seed"]).shuffle(jobs)
    manifest = dict(config=config, dataset_manifest=data_manifest, models=public_models(profiles),
                    pricing=pricing, source_sha256=source_hashes(), status="running",
                    expected_episodes=len(jobs), completed_episodes=0,
                    prompts=dict(gate=GATE_PROMPT, jev=JEV_PROMPT, action=ACTION_PROMPT,
                                 question=QUESTION_PROMPT, user=USER_PROMPT),
                    accounting="Agent calls and LLM user-simulator calls are reported separately.")
    write_json(output / "manifest.json", manifest)
    for sample, job in jobs:
        if source_hashes() != manifest["source_sha256"]:
            raise RuntimeError("Code or configuration changed during evaluation")
        destination = output / "episodes" / (sample.sample_id + "__" + job["name"])
        destination.mkdir(parents=True, exist_ok=False)
        client = Client(profiles, pricing["models"], destination / "requests.jsonl", config["limits"]["api_attempts"],
                        user_limit=config["limits"]["user_api_attempts"], **config["request"])
        result = run_episode(sample, job, config, client)
        result["requests_sha256"] = file_digest(destination / "requests.jsonl") if (destination / "requests.jsonl").exists() else None
        write_json(destination / "episode.json", result)
        manifest["completed_episodes"] += result["status"] == "complete"
        if result["status"] != "complete":
            manifest["status"] = "interrupted"
            write_json(output / "manifest.json", manifest)
            raise RuntimeError("Evaluation stopped after a technical error; all attempts were saved")
        write_json(output / "manifest.json", manifest)
    manifest["status"] = "complete"
    write_json(output / "manifest.json", manifest)
    return aggregate(output, dataset)


def summarize(rows, expected_ids, cost_scope="agent"):
    if cost_scope not in ("agent","all"):
        raise ValueError("Unknown cost scope")
    ids = [r["sample_id"] for r in rows]
    if not rows or len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise ValueError("Missing, duplicated or unexpected episode")
    if any(r["status"] != "complete" or type(r["task_success"]) is not bool for r in rows):
        raise ValueError("Incomplete episodes cannot be used for a complete benchmark table")
    full = [r for r in rows if r["fully_specified"]]
    costs = [r["agent"]["estimated_usd"] for r in rows]
    user_costs = [r["user_simulator"]["estimated_usd"] for r in rows]
    combined = [a+b if a is not None and b is not None else None for a,b in zip(costs,user_costs)]
    reported_costs = costs if cost_scope=="agent" else combined
    noask = all(r["method"] == "noask" for r in rows)
    if noask and any(r["ask_count"] for r in rows):
        raise ValueError("NoAsk episode contains an ASK")
    return dict(episodes=len(rows), successes=sum(r["task_success"] for r in rows),
                success_pct=100 * sum(r["task_success"] for r in rows) / len(rows),
                api_time_s=sum(r["agent"]["api_time_s"] for r in rows) / len(rows),
                estimated_usd=sum(reported_costs) / len(rows) if all(c is not None for c in reported_costs) else None,
                cost_scope=cost_scope,
                agent_estimated_usd=sum(costs)/len(rows) if all(c is not None for c in costs) else None,
                total_estimated_usd=sum(combined)/len(rows) if all(c is not None for c in combined) else None,
                fully_specified=len(full), unnecessary_ask_cases=None if noask else sum(r["ask_count"] > 0 for r in full),
                unnecessary_ask_pct=None if noask or not full else 100 * sum(r["ask_count"] > 0 for r in full) / len(full),
                user_api_time_s=sum(r["user_simulator"]["api_time_s"] for r in rows) / len(rows),
                user_estimated_usd=sum(user_costs) / len(rows) if all(c is not None for c in user_costs) else None)


def aggregate(directory, dataset):
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    if manifest["status"] != "complete":
        raise ValueError("A complete run is required before publishing benchmark tables")
    data_manifest, samples = load_dataset(dataset, require_oracle=True)
    if data_manifest != manifest["dataset_manifest"]:
        raise ValueError("Run and dataset manifests differ")
    expected = {s.sample_id: s for s in samples}
    jobs = {j["name"]: j for j in manifest["config"]["jobs"]}
    groups, stages = defaultdict(list), defaultdict(lambda: dict(requests=0, api_time_s=0., estimated_usd=0.))
    for path in sorted((directory / "episodes").glob("*/episode.json")):
        row = read_json(path)
        if row["job"] not in jobs or row["sample_id"] not in expected:
            raise ValueError("Unexpected episode identity")
        sample, job = expected[row["sample_id"]], jobs[row["job"]]
        if (row["fully_specified"] != sample.fully_specified or row["method"] != job["method"]
                or row["model"] != job["model"] or row["template_id"] != sample.template_id):
            raise ValueError("Episode metadata differs from the locked design")
        if row["requests_sha256"] != file_digest(path.parent / "requests.jsonl"):
            raise ValueError("Request evidence checksum mismatch")
        records = [json.loads(line) for line in (path.parent / "requests.jsonl").read_text().splitlines() if line]
        for request in records:
            if request["actor"] not in ("agent", "user_simulator"):
                raise ValueError("Unknown request actor")
            if request["actor"] == "user_simulator" and (request["stage"] != "user_answer" or request["backend"] != "user"):
                raise ValueError("Incorrect user-simulator accounting")
            if request["actor"] == "agent" and request["stage"] not in ("gate", "question", "action"):
                raise ValueError("Incorrect agent accounting")
            if not math.isfinite(request["api_time_s"]) or request["api_time_s"] < 0:
                raise ValueError("Invalid request time")
            body = request.get("response", {})
            usage = token_usage(body) if isinstance(body, dict) else None
            if request["usage"] != usage:
                raise ValueError("Token counts differ from the model response")
            expected_cost = estimated_cost(usage, manifest["pricing"]["models"].get(request["backend"]))
            if request["estimated_usd"] != expected_cost:
                raise ValueError("Request cost differs from usage and locked pricing")
        for actor, field in (("agent", "agent"), ("user_simulator", "user_simulator")):
            client = Client({}, {})
            client.records = [r for r in records if r["actor"] == actor]
            if client.totals(actor) != row[field]:
                raise ValueError("Episode totals differ from recorded requests")
        for request in records:
            key = (row["job"], request["actor"], request["stage"])
            stage = stages[key]
            stage["requests"] += 1
            stage["api_time_s"] += request["api_time_s"]
            cost = request["estimated_usd"]
            stage["estimated_usd"] = stage["estimated_usd"] + cost if stage["estimated_usd"] is not None and cost is not None else None
        groups[row["job"]].append(row)
    if set(groups) != set(jobs):
        raise ValueError("Missing model or method configuration")
    scope = manifest["config"]["accounting"]["cost_scope"]
    summary = {name: summarize(groups[name], expected, scope) for name in jobs}
    baseline = summary["deepseek_llm_gate"]
    for name in ("deepseek_noask", "deepseek_jev_gate"):
        row = summary[name]
        row["time_reduction_pct"] = 100 * (1 - row["api_time_s"] / baseline["api_time_s"]) if baseline["api_time_s"] else None
        row["cost_reduction_pct"] = 100 * (1 - row["estimated_usd"] / baseline["estimated_usd"]) if baseline["estimated_usd"] and row["estimated_usd"] is not None else None
    per_family = {name: {t: summarize([r for r in rows if r["template_id"] == t],
                  [s.sample_id for s in samples if s.template_id == t], scope) for t in sorted({s.template_id for s in samples})}
                  for name, rows in groups.items()}
    result = dict(benchmark=data_manifest["statistics"], methods=summary, per_family=per_family,
                  stages=[dict(job=k[0], actor=k[1], stage=k[2], **v) for k, v in sorted(stages.items())])
    write_json(directory / "tables.json", result)
    fields = sorted({k for row in summary.values() for k in row})
    with (directory / "methods.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["job", *fields])
        writer.writeheader()
        writer.writerows(dict(job=name, **row) for name, row in summary.items())
    return result
