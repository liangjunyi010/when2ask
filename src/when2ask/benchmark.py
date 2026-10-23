"""Private benchmark records, controlled generation and offline physical oracle."""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import ROOT
from .environment import Environment
from .evaluator import Evaluator
from .skills import RobotSkills
from .task import PrivateTaskSpec

ROLES = ("cup", "block", "lid")
CANONICAL = (("red_cup", "blue_cup"), ("green_block", "yellow_block"), ("black_lid", "white_lid"))
COMBINATIONS = list(itertools.product((0, 1), repeat=3))
PILOT_INTENTS = (0, 3, 6)
VALIDATION_INTENTS = (1, 2, 4, 5, 7)
TASK_DAG = {"nodes": ["pack_cup", "pack_block", "cover"],
            "edges": [["pack_cup", "cover"], ["pack_block", "cover"]]}


@dataclass(frozen=True)
class Sample:
    sample_id: str
    group_id: str
    template_id: str
    scene_seed: int
    scene_spec_ref: str
    u0: str
    slots: dict
    dag: dict
    theta_star: dict
    initial_disclosed_slots: list[str]
    constraints: dict
    partition: str

    def validate(self):
        if self.template_id != "pack_and_cover" or self.dag != TASK_DAG:
            raise ValueError("Only the pack-and-cover DAG is implemented")
        if set(self.slots) != {f"{r}_choice" for r in ROLES} or set(self.theta_star) != set(self.slots):
            raise ValueError("Invalid private slot registry")
        for slot, registry in self.slots.items():
            if len(registry["candidate_ids"]) != 2 or self.theta_star[slot] not in registry["candidate_ids"]:
                raise ValueError("Hidden choice is not a scene candidate")
        if not set(self.initial_disclosed_slots) <= self.slots.keys():
            raise ValueError("Invalid disclosed slot")
        if self.constraints != {"unselected_outside": True, "released": True}:
            raise ValueError("Unsupported task constraints")
        return self

    def scene(self, root=ROOT):
        scene = json.loads((root / self.scene_spec_ref).read_text())
        if (scene.get("geometry_version") != "panda_pack_v2_safe_cup"
                or scene.get("jitter_max_m") != .004
                or scene.get("source_xy_overrides") != {"red_cup": [.38, -.12]}):
            raise ValueError("Scene outside the validated geometry family")
        return scene

    def private_spec(self):
        return PrivateTaskSpec(**self.theta_star,
                               candidate_registry={s: v["candidate_ids"] for s, v in self.slots.items()})


def dataset_path(split, root=ROOT):
    if split not in ("pilot", "validation"):
        raise ValueError("Split must be pilot or validation")
    return root / "data" / f"{split}.jsonl"


def load_samples(split, root=ROOT):
    return [Sample(**json.loads(line)).validate() for line in dataset_path(split, root).read_text().splitlines()
            if line.strip()]


def find_sample(sample_id, root=ROOT):
    for split in ("validation", "pilot"):
        path = dataset_path(split, root)
        if path.exists():
            for sample in load_samples(split, root):
                if sample.sample_id == sample_id:
                    return sample
    raise ValueError(f"Unknown sample: {sample_id}")


def group_partition(intent_index):
    # Group by canonical hidden preference triple, ignoring aliases, instruction
    # wording, disclosure amount and source jitter. All variants stay together.
    if intent_index in VALIDATION_INTENTS:
        return "validation"
    return "dev" if intent_index == PILOT_INTENTS[0] else "test"


def generate(split="pilot", count=20, seed=42, root=ROOT):
    generation_start = time.perf_counter()
    if split == "validation" and count != 5:
        raise ValueError("There are exactly five handcrafted validation cases")
    if not 1 <= count <= 200:
        raise ValueError("Generation count must be 1..200")
    rng, samples = random.Random(f"{seed}:{split}"), []
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "scenes").mkdir(parents=True, exist_ok=True)
    for index in range(count):
        sample_id = f"{split}_{index:03d}"
        intent_index = (VALIDATION_INTENTS[index] if split == "validation"
                        else PILOT_INTENTS[(index // 4) % len(PILOT_INTENTS)])
        truth = COMBINATIONS[intent_index]
        missing = ([0, 1, 2, 3, 1][index] if split == "validation" else index % 4)
        aliases = {name: "obj_" + f"{rng.getrandbits(48):012x}" for pair in CANONICAL for name in pair}
        order = ["box", *aliases.values()]
        rng.shuffle(order)
        scene_seed = rng.randrange(10_000, 1_000_000)
        scene = dict(geometry_version="panda_pack_v2_safe_cup", jitter_max_m=.004,
                     source_xy_overrides={"red_cup": [.38, -.12]},
                     object_id_map=aliases, object_order=order)
        slots = {}
        for role, pair in zip(ROLES, CANONICAL):
            candidates = [aliases[name] for name in pair]
            rng.shuffle(candidates)
            slots[f"{role}_choice"] = dict(public_role=role, candidate_ids=candidates)
        theta = {f"{role}_choice": aliases[pair[choice]]
                 for role, pair, choice in zip(ROLES, CANONICAL, truth)}
        # Controlled cases include known block before unknown cup and known lid
        # with both pack choices unknown, to exercise timing rather than ASK-all.
        disclosed_roles = list(ROLES)
        rng.shuffle(disclosed_roles)
        disclosed_roles = disclosed_roles[:3 - missing]
        if split == "validation":
            disclosed_roles = [list(ROLES), ["block", "lid"], ["cup"], [], ["cup", "block"]][index]
        bases = [
            "Put exactly one cup and one block in the box, then cover it with one lid. "
            "Leave all unselected objects outside the box and release everything.",
            "Pack one cup and one block into the box. After both are packed, cover the box with a lid. "
            "Keep every unselected object outside the box; finish with the robot holding nothing.",
            "Use the box to pack one cup and one block, and only then put a lid over its opening. "
            "All objects not selected must stay outside; release the selected objects."
        ]
        u0 = bases[index % len(bases)]
        for role in disclosed_roles:
            u0 += f" For the {role}, use {theta[role + '_choice']}."
        sample = Sample(sample_id, f"pack_and_cover:intent_{''.join(map(str, truth))}",
                        "pack_and_cover", scene_seed, f"scenes/{sample_id}.json", u0,
                        slots, TASK_DAG, theta, [r + "_choice" for r in disclosed_roles],
                        {"unselected_outside": True, "released": True}, group_partition(intent_index)).validate()
        (root / sample.scene_spec_ref).write_text(json.dumps(scene, indent=2) + "\n")
        samples.append(sample)
    dataset_path(split, root).write_text("".join(json.dumps(asdict(s)) + "\n" for s in samples))
    manifest_path = root / "data/generation_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest[split] = dict(kind="offline_controlled_generation", count=count, seed=seed,
                          wall_time_ms=(time.perf_counter() - generation_start) * 1000,
                          api_attempts=0, input_tokens=None, output_tokens=None,
                          dataset_sha256=hashlib.sha256(dataset_path(split, root).read_bytes()).hexdigest())
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return samples


def check_groups(samples, root=ROOT):
    partitions, families = {}, {}
    for sample in samples:
        previous = partitions.setdefault(sample.group_id, sample.partition)
        if previous != sample.partition:
            raise ValueError("A group crosses dataset partitions")
        scene = sample.scene(root)
        inverse = {v: k for k, v in scene["object_id_map"].items()}
        family = tuple(inverse[sample.theta_star[r + "_choice"]] for r in ROLES)
        previous = families.setdefault(family, sample.group_id)
        if previous != sample.group_id:
            raise ValueError("An alias/disclosure near-duplicate crosses groups")
    return dict(groups=len(partitions), partitions={p: sum(v == p for v in partitions.values())
                                                   for p in sorted(set(partitions.values()))})


def oracle_validate(split, root=ROOT):
    samples = load_samples(split, root)
    all_samples = [s for name in ("validation", "pilot") if dataset_path(name, root).exists()
                   for s in load_samples(name, root)]
    group_info = check_groups(all_samples, root)
    base = root / "outputs/phase2/oracle" / split
    base.mkdir(parents=True, exist_ok=True)
    rows = []
    for sample in samples:
        start = time.perf_counter()
        with Environment(seed=sample.scene_seed, scene_spec=sample.scene(root)) as env:
            initial = env.snapshot()
            skills = RobotSkills(env)
            choices = sample.theta_star
            actions = []
            states = []
            for skill, slot in (("pick_place", "cup_choice"), ("pick_place", "block_choice"),
                                ("cover", "lid_choice")):
                action = getattr(skills, skill)(choices[slot], "box").to_dict()
                actions.append(action)
                states.append(env.snapshot())
                if not action["success"]:
                    break
            evaluation = Evaluator().evaluate(env, sample.private_spec(), clarification_burden=0,
                                               actions=actions, termination="oracle_completed")
            trace = dict(sample_id=sample.sample_id, kind="offline_deterministic_physical_oracle",
                         source="Private truth used only by this offline validator; never a policy payload",
                         initial_observation=initial, actions=actions, states=states,
                         execution_log=env.events, evaluation=evaluation,
                         wall_time_s=time.perf_counter() - start, api_cost=None)
            (base / f"{sample.sample_id}.json").write_text(json.dumps(trace, separators=(",", ":")) + "\n")
            row = dict(sample_id=sample.sample_id, scene_seed=sample.scene_seed,
                       task_success=evaluation["task_success"],
                       physical_actions_succeeded=sum(a["success"] for a in actions),
                       missing_preferences=3 - len(sample.initial_disclosed_slots))
            rows.append(row)
            print(json.dumps(row), flush=True)
    report = dict(split=split, total=len(rows), successes=sum(r["task_success"] for r in rows),
                  groups=group_info, runs=rows, generation_api_cost=None,
                  note="Offline physical feasibility; no model quality or inference-cost claim")
    (base / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
