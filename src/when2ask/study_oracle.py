"""Offline oracle executes every sample through real Panda motors and scoring."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict

import pybullet as p

from .config import ROOT
from .diverse_world import DiverseEnvironment, DiverseSkills
from .study_data import load_study, sha256, write_json
from .study_evaluator import evaluate_study, expected_targets


def code_hash(root=ROOT):
    files = ("environment.py", "skills.py", "diverse_world.py", "study_evaluator.py", "evaluator.py", "study_oracle.py")
    return hashlib.sha256("".join(sha256(root / "src/when2ask" / f) for f in files).encode()).hexdigest()


def initial_penetrations(env):
    pairs = []
    objects = list(env.objects)
    for i, a in enumerate(objects):
        if env.objects[a].category == "container":
            continue
        for b in objects[i + 1:]:
            contacts = p.getClosestPoints(env.objects[a].body_id, env.objects[b].body_id, 0,
                                          physicsClientId=env.client)
            depth = min((c[8] for c in contacts), default=0)
            if depth < -.002:
                pairs.append(dict(a=a, b=b, depth_m=depth))
    return pairs


def run_oracle(partition, *, root=ROOT, selected=None, output_dir=None):
    samples = load_study(partition, root)
    if selected is not None:
        samples = [s for s in samples if s.sample_id in set(selected)]
    out = output_dir or root / "outputs/phase3/oracle" / partition
    out.mkdir(parents=True, exist_ok=True)
    controller = code_hash(root)
    rows = []
    for sample in samples:
        signature = dict(sample_sha256=hashlib.sha256(json.dumps(asdict(sample), sort_keys=True).encode()).hexdigest(),
                         scene_sha256=sha256(root / sample.scene_spec_ref), physics_code_sha256=controller)
        path = out / f"{sample.sample_id}.json"
        if path.exists():
            trace = json.loads(path.read_text())
            if trace["signature"] != signature:
                raise ValueError("Oracle evidence belongs to different physics/data; use a new output directory")
        else:
            start = time.perf_counter()
            with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene(root)) as env:
                initial = env.snapshot()
                penetrations = initial_penetrations(env)
                skills, actions, states = DiverseSkills(env), [], []
                targets = expected_targets(sample, env)
                roles = ["block", "cup"] if sample.dag["order"] == "block_first" else ["cup", "block"]
                for role in roles:
                    actions.append(skills.pick_place(sample.theta_star[role + "_choice"], targets[role]).to_dict())
                    states.append(env.snapshot())
                if sample.template_id == "pack_and_cover":
                    actions.append(skills.cover(sample.theta_star["lid_choice"], "box").to_dict())
                    states.append(env.snapshot())
                evaluation = evaluate_study(env, sample, clarification_burden=0, actions=actions,
                                            termination="offline_oracle_completed")
                trace = dict(kind="offline_deterministic_physical_oracle", sample_id=sample.sample_id,
                    group_id=sample.group_id, template_id=sample.template_id, partition=sample.partition,
                    signature=signature, initial_observation=initial, initial_penetrations=penetrations,
                    actions=actions, states=states, final_observation=env.snapshot(), execution_log=env.events,
                    evaluation=evaluation, wall_time_s=time.perf_counter() - start, api_attempts=0)
                if not rows:
                    env.save_scene(out / "final_scene.png")
                path.write_text(json.dumps(trace, separators=(",", ":")) + "\n")
        row = dict(sample_id=sample.sample_id, group_id=sample.group_id, template_id=sample.template_id,
                   success=trace["evaluation"]["task_success"], initial_penetrations=len(trace["initial_penetrations"]),
                   actions_succeeded=sum(a["success"] for a in trace["actions"]),
                   actions=len(trace["actions"]), missing=3 - len(sample.initial_disclosed_slots))
        rows.append(row)
        print(json.dumps(row), flush=True)
    templates = {t: dict(successes=sum(r["success"] for r in rows if r["template_id"] == t),
                        total=sum(r["template_id"] == t for r in rows)) for t in sorted({r["template_id"] for r in rows})}
    result = dict(partition=partition, successes=sum(r["success"] for r in rows), total=len(rows),
                  templates=templates, api_attempts=0, physics_code_sha256=controller, runs=rows)
    write_json(out / "summary.json", result)
    return result
