"""Versioned task graphs, disclosure and scene synthesis."""
from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import ROOT

VERSION = "when2ask_dag_v3"


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def implementation_hashes():
    return {p.name:file_digest(p) for p in sorted((ROOT/'src/when2ask').glob('*.py'))}


@dataclass
class Sample:
    sample_id: str
    template_id: str
    scene_seed: int
    u0: str
    slots: dict
    theta_star: dict
    initial_disclosed_slots: list
    physical_scene: dict
    dag: dict
    group_id: str
    dataset_version: str = VERSION
    partition: str = "evaluation"

    @property
    def target_location(self):
        return self.theta_star.get("target_location", next(iter(self.physical_scene.get("stations", {})), None))

    @property
    def fully_specified(self):
        return set(self.slots) == set(self.initial_disclosed_slots)

    def scene(self):
        return copy.deepcopy(self.physical_scene)

    def validate(self):
        if self.dataset_version != VERSION or set(self.theta_star) != set(self.slots):
            raise ValueError("Invalid dataset version or intent")
        if not set(self.initial_disclosed_slots) <= set(self.slots):
            raise ValueError("Invalid disclosure")
        for key, record in self.slots.items():
            values = record["candidate_ids"]
            if len(values) < 2 or len(values) != len(set(values)) or self.theta_star[key] not in values:
                raise ValueError("Invalid finite choice")
        ids = [n["id"] for n in self.dag["nodes"]]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Duplicate or empty task graph")
        for node in self.dag["nodes"]:
            if node["choice_slot"] is not None and node["choice_slot"] not in self.slots:
                raise ValueError("Unknown graph choice")
        for parent, child in self.dag["edges"]:
            if parent not in ids or child not in ids or ids.index(parent) >= ids.index(child):
                raise ValueError("Task graph must be acyclic and topologically ordered")
        return self

    def public_task(self):
        return dict(instruction=self.u0, choices=copy.deepcopy(self.slots),
                    disclosed={s: self.theta_star[s] for s in self.initial_disclosed_slots})


def candidate(config, template, index, attempt=0):
    from .task_graph import compose, layout, instruction
    family = config["families"][template]
    rng = random.Random(f"{config['seed']}:{template}:{index}:{attempt}")
    graph, slots = compose(template, rng.randint(*family["nodes"]), rng.randint(*family["uncertain"]), rng)
    scene = layout(graph, template, rng)
    scene["distance_budget_m"] = config.get("execution", {}).get("distance_budget_m", 180.)
    theta = {s: rng.choice(row["candidate_ids"]) for s, row in slots.items()}
    if "label" in scene:
        scene["label"]["code"] = theta["inspection_code"]
    order = list(range(family["count"]))
    random.Random(f"{config['seed']}:{template}:disclosure").shuffle(order)
    full = index in order[:family["fully_specified"]]
    withheld = set()
    if not full:
        ordered = sorted(slots)
        rng.shuffle(ordered)
        withheld = set(ordered[:rng.randint(1, len(ordered))])
    disclosed = sorted(set(slots) - withheld)
    text = instruction(template, graph, slots, theta, disclosed)
    geometry = copy.deepcopy(scene)
    if "label" in geometry:
        geometry["label"].pop("code", None)
    return Sample(f"{template}_{index:04d}", template, rng.randrange(2**31), text, slots, theta,
                  disclosed, scene, graph, template+":"+digest(geometry)[:16]).validate()


def statistics(samples):
    rows = []
    for template in sorted({s.template_id for s in samples}):
        group = [s for s in samples if s.template_id == template]
        nodes = [len(s.dag["nodes"]) for s in group]
        uncertain = [sum(n["choice_slot"] is not None for n in s.dag["nodes"]) for s in group]
        rows.append(dict(template=template, environments=len(group),
                         fully_specified=sum(s.fully_specified for s in group),
                         nodes=[min(nodes), max(nodes)], uncertain=[min(uncertain), max(uncertain)]))
    return dict(environments=len(samples), fully_specified=sum(s.fully_specified for s in samples),
                groups=len({s.group_id for s in samples}), families=rows)


def generate(config_path, output, *, validate_physics=False, oracle=None):
    config = read_json(config_path)
    if config["version"] != VERSION:
        raise ValueError("Unsupported benchmark configuration")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    samples, validation = [], []
    implementation = implementation_hashes()
    if validate_physics and oracle is None:
        from .dag_world import run_oracle
        oracle = run_oracle
    for template, family in config["families"].items():
        if not 0 <= family["fully_specified"] <= family["count"]:
            raise ValueError("Invalid family quotas")
        for index in range(family["count"]):
            for attempt in range(config["max_oracle_attempts_per_case"] if validate_physics else 1):
                try:
                    sample = candidate(config, template, index, attempt)
                except ValueError as exc:
                    if not validate_physics:
                        raise
                    validation.append(dict(sample_id=f"{template}_{index:04d}", attempt=attempt, task_success=False, error=str(exc), sample_sha256=None))
                    write_json(output / "oracle_attempts.json", validation)
                    continue
                if validate_physics:
                    trace = oracle(sample)
                    validation.append(dict(sample_id=sample.sample_id, attempt=attempt,
                                           sample_sha256=digest(asdict(sample)), **trace))
                    write_json(output / "oracle_attempts.json", validation)
                    if not trace["task_success"]:
                        continue
                samples.append(sample)
                break
            else:
                raise RuntimeError(f"Oracle rejected all candidates for {template}:{index}")
    if implementation_hashes() != implementation:
        raise RuntimeError("Implementation changed during dataset generation")
    path = output / "samples.jsonl"
    path.write_text("".join(json.dumps(asdict(s), sort_keys=True) + "\n" for s in samples))
    manifest = dict(version=VERSION, config=config, statistics=statistics(samples),
                    implementation_sha256=implementation,
                    samples_sha256=file_digest(path),
                    definitions_sha256=file_digest(ROOT / "src/when2ask/task_graph.py"),
                    validation_status="oracle_passed" if validate_physics else "not_run",
                    oracle_sha256=file_digest(output / "oracle_attempts.json") if validate_physics else None,
                    model_evaluation_status="not_run")
    write_json(output / "manifest.json", manifest)
    return manifest


def load_dataset(directory, *, require_oracle=False):
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    if manifest["samples_sha256"] != file_digest(directory / "samples.jsonl"):
        raise ValueError("Dataset checksum mismatch")
    rows = [Sample(**json.loads(line)).validate() for line in (directory / "samples.jsonl").read_text().splitlines() if line]
    if len({s.sample_id for s in rows}) != len(rows) or statistics(rows) != manifest["statistics"]:
        raise ValueError("Dataset statistics or IDs do not match")
    if require_oracle:
        if manifest.get("implementation_sha256") != implementation_hashes():
            raise ValueError("Oracle evidence belongs to a different implementation")
        if manifest["validation_status"] != "oracle_passed":
            raise ValueError("Run physical oracle validation before model evaluation")
        if file_digest(directory / "oracle_attempts.json") != manifest["oracle_sha256"]:
            raise ValueError("Oracle evidence checksum mismatch")
        passed = {(r["sample_id"], r["sample_sha256"]) for r in read_json(directory / "oracle_attempts.json") if r["task_success"]}
        if any((s.sample_id, digest(asdict(s))) not in passed for s in rows):
            raise ValueError("Missing oracle evidence for retained sample")
    return manifest, rows
