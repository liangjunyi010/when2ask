"""Scene-grouped, versioned Dev/Test data, separate from the immutable pilot.

Groups are physical base layouts, never preference triples. Test holds out a
different container arrangement; aliases, truth, wording and mm jitter stay in
the layout's group. Public instructions express every required precedence edge.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .benchmark import Sample as LegacySample
from .config import ROOT
from .diverse_world import PHYSICS_VERSION

DATA_VERSION = "when2ask_scene_groups_v3.1"
TEMPLATES = ("pack_and_cover", "place_into_selected_containers")
SOURCE_PAIRS = {"cup": ("red_cup", "blue_cup"), "block": ("green_block", "yellow_block"),
                "lid": ("black_lid", "white_lid")}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def base_scene(template, partition, index):
    """Declared families, not trial-selected for a particular gate's behavior."""
    if template not in TEMPLATES or partition not in ("dev", "test"):
        raise ValueError("Unknown scene family")
    if template == "pack_and_cover":
        mirror = 1 if partition == "dev" else -1
        # Distinct base positions (cm), with a complete y reflection held out.
        offsets = [(-.015, 0), (.025, 0), (0, .035), (.025, -.025),
                   (-.025, .025), (.01, -.035), (.035, .025), (-.015, -.035)]
        dx, dy = offsets[index]
        xy = [.57 + dx, mirror * (.08 + dy)]
        containers = [dict(id="box", xy=xy, half_xy=[.14, .12], wall_height=.11,
                           color="brown", rgba=[.63, .4, .2, 1])]
        sources = {"red_cup": [.375 + .008 * (index % 2), -.12 - .01 * (index % 3)],
                   "blue_cup": [.31 + .012 * (index % 3), -.24 + .012 * (index % 2)],
                   "green_block": [.29 + .006 * (index % 3), -.025 + .014 * (index % 2)],
                   "yellow_block": [.29 + .012 * (index % 2), .145 + .008 * (index % 3)],
                   "black_lid": [.30 - .012 * (index % 2), .39],
                   "white_lid": [.61 + .01 * (index % 2), -.34 - .008 * (index % 3)]}
        sources = {k: [x, mirror * y] for k, (x, y) in sources.items()}
    else:
        offsets = [(-.015, -.015), (.015, .015), (-.02, .02), (.02, -.02),
                   (0, -.03), (0, .03), (-.03, 0), (.03, 0)]
        dx, dy = offsets[index]
        centers = ([[.55 + dx, -.18 + dy], [.55 - dx, .18 + dy]] if partition == "dev"
                   else [[.44 + dx, .13 + dy], [.66 + dx, .13 - dy]])
        containers = [dict(id=key, xy=xy, half_xy=[.09, .08], wall_height=.09,
                           color=color, rgba=rgba) for key, xy, color, rgba in
                      zip(("container_a", "container_b"), centers, ("orange", "purple"),
                          ([.95, .45, .12, 1], [.55, .25, .8, 1]))]
        sources = {"red_cup": [.34 + .008 * (index % 2), -.12 - .008 * (index % 3)],
                   "blue_cup": [.29 - .01 * (index % 3), -.26 + .008 * (index % 2)],
                   "green_block": [.29 + .006 * (index % 2), .035 + .01 * (index % 3)],
                   "yellow_block": [.29 + .01 * (index % 2), .24 + .01 * (index % 3)]}
    return dict(schema_version=3, geometry_version=PHYSICS_VERSION, template_id=template,
                jitter_max_m=.004, containers=containers, sources=sources)


def layout_fingerprint(scene):
    # Ignore aliases, colors, preferences, wording, object order and seed. Source
    # category slots are unordered: swapping two candidates is the SAME layout.
    signature = dict(template_id=scene["template_id"],
                     containers=sorted((tuple(c["xy"]), tuple(c["half_xy"]), c["wall_height"])
                                       for c in scene["containers"]),
                     sources={role: sorted(tuple(scene["sources"][k]) for k in pair)
                              for role, pair in SOURCE_PAIRS.items() if pair[0] in scene["sources"]})
    return hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class StudySample(LegacySample):
    schema_version: int = 3
    dataset_version: str = DATA_VERSION
    layout_family_id: str = ""

    def validate(self):
        if self.schema_version != 3 or self.dataset_version != DATA_VERSION or self.template_id not in TEMPLATES:
            raise ValueError("Unsupported study schema")
        if self.partition not in ("dev", "test") or not self.layout_family_id or not self.group_id:
            raise ValueError("Explicit scene group and partition required")
        roles = ("cup", "block", "lid") if self.template_id == TEMPLATES[0] else ("cup", "block", "cup_destination")
        if set(self.slots) != {r + "_choice" for r in roles} or set(self.theta_star) != set(self.slots):
            raise ValueError("Invalid preference registry")
        for role in roles:
            slot = role + "_choice"
            record = self.slots[slot]
            if (record["public_role"] != role or len(record["candidate_ids"]) != 2
                    or len(set(record["candidate_ids"])) != 2 or self.theta_star[slot] not in record["candidate_ids"]):
                raise ValueError("Invalid candidate registry")
        if not set(self.initial_disclosed_slots) <= self.slots.keys():
            raise ValueError("Invalid disclosure")
        if self.constraints != {"unselected_outside": True, "released": True}:
            raise ValueError("Unsupported constraints")
        expected = dag_for(self.template_id, self.dag["order"])
        if self.dag != expected:
            raise ValueError("Unsupported DAG")
        public_order = {"independent": "Either object may be placed first.",
                        "cup_first": "Place the cup before the block.",
                        "block_first": "Place the block before the cup."}[self.dag["order"]]
        if public_order not in self.u0:
            raise ValueError("Every precedence rule must be publicly stated")
        for slot in self.initial_disclosed_slots:
            if f"For the {self.slots[slot]['public_role']}, use {self.theta_star[slot]}." not in self.u0:
                raise ValueError("Disclosure must agree with the private record")
        return self

    def scene(self, root=ROOT):
        scene = json.loads((Path(root) / self.scene_spec_ref).read_text())
        if (scene.get("schema_version") != 3 or scene.get("geometry_version") != PHYSICS_VERSION
                or scene["template_id"] != self.template_id or scene["jitter_max_m"] != .004
                or scene["layout_fingerprint"] != layout_fingerprint(scene)
                or self.layout_family_id != "layout_" + scene["layout_fingerprint"][:16]
                or self.group_id != self.template_id + ":" + self.layout_family_id):
            raise ValueError("Scene family identity mismatch")
        return scene


def dag_for(template, order):
    if order not in ("independent", "cup_first", "block_first"):
        raise ValueError("Unknown order")
    edges = ([["place_cup", "cover"], ["place_block", "cover"]]
             if template == "pack_and_cover" else [])
    if order != "independent":
        edges.append(["place_cup", "place_block"] if order == "cup_first" else ["place_block", "place_cup"])
    return dict(nodes=["place_cup", "place_block"] + (["cover"] if template == "pack_and_cover" else []),
                edges=edges, order=order)


def instruction(template, order, style):
    if template == "pack_and_cover":
        text = ["Pack exactly one cup and one block into the box, then cover it with one lid.",
                "Put one selected cup and one selected block in the box; cover it only after both are packed."][style % 2]
    else:
        text = ["Put one selected cup in its preferred container and one selected block in the OTHER container.",
                "Place the preferred cup and block into separate containers: the cup uses its preferred destination, "
                "and the block must use the remaining container."][style % 2]
        text += " The cup_destination preference chooses the cup's container and also determines the block's other container."
    text += " " + {"independent": "Either object may be placed first.",
                    "cup_first": "Place the cup before the block.",
                    "block_first": "Place the block before the cup."}[order]
    text += (" Leave every unselected movable object outside ALL containers; release everything. "
             "Each named preference has one fixed user choice; an undisclosed preference is unknown.")
    return text


def generate_study(root=ROOT, seed=4278):
    root = Path(root)
    destination = root / "data/phase3"
    if (destination / "manifest.json").exists():
        raise FileExistsError("Frozen data already exists; use a new version directory for regeneration")
    all_samples = []
    for partition, family_count, variants in (("dev", 4, 4), ("test", 8, 8)):
        samples = []
        for ti, template in enumerate(TEMPLATES):
            for fi in range(family_count):
                base = base_scene(template, partition, fi)
                fp = layout_fingerprint(base)
                family = "layout_" + fp[:16]
                for variant in range(variants):
                    index = (ti * family_count + fi) * variants + variant
                    rng = random.Random(f"{seed}:{partition}:{index}")
                    sample_id = f"v3_{partition}_{index:03d}"
                    scene = json.loads(json.dumps(base))
                    # Color/source assignment is independent of private choices.
                    for pair in SOURCE_PAIRS.values():
                        if pair[0] in scene["sources"] and rng.getrandbits(1):
                            scene["sources"][pair[0]], scene["sources"][pair[1]] = scene["sources"][pair[1]], scene["sources"][pair[0]]
                    names = [c["id"] for c in scene["containers"]] + list(scene["sources"])
                    aliases = {name: ("box" if name == "box" else "item_" + f"{rng.getrandbits(48):012x}") for name in names}
                    order_ids = list(aliases.values())
                    rng.shuffle(order_ids)
                    scene.update(object_id_map=aliases, object_order=order_ids, layout_fingerprint=fp)
                    ref = f"data/phase3/scenes/{sample_id}.json"
                    write_json(root / ref, scene)
                    roles = ("cup", "block", "lid") if ti == 0 else ("cup", "block", "cup_destination")
                    pairs = [SOURCE_PAIRS["cup"], SOURCE_PAIRS["block"],
                             SOURCE_PAIRS["lid"] if ti == 0 else ("container_a", "container_b")]
                    slots = {}
                    truth = list(itertools.product((0, 1), repeat=3))[(variant + fi * 3 + ti) % 8]
                    theta = {}
                    for role, pair, bit in zip(roles, pairs, truth):
                        ids = [aliases[k] for k in pair]
                        rng.shuffle(ids)
                        slots[role + "_choice"] = dict(public_role=role, candidate_ids=ids)
                        theta[role + "_choice"] = aliases[pair[bit]]
                    missing = variant % 4
                    disclosed = list(roles)
                    rng.shuffle(disclosed)
                    disclosed = disclosed[:3 - missing]
                    order = ("independent", "cup_first", "block_first")[(fi + variant) % 3]
                    u0 = instruction(template, order, variant)
                    for role in disclosed:
                        u0 += f" For the {role}, use {theta[role + '_choice']}."
                    sample = StudySample(sample_id, template + ":" + family, template,
                        rng.randrange(10_000, 2_000_000_000), ref, u0, slots, dag_for(template, order), theta,
                        [r + "_choice" for r in disclosed], {"unselected_outside": True, "released": True},
                        partition, layout_family_id=family).validate()
                    samples.append(sample)
        path = destination / f"{partition}.jsonl"
        path.write_text("".join(json.dumps(asdict(s), sort_keys=True) + "\n" for s in samples))
        all_samples.extend(samples)
    result = check_study(all_samples, root)
    result.update(dataset_version=DATA_VERSION, seed=seed, api_attempts=0,
                  dataset_hashes={p: sha256(destination / f"{p}.jsonl") for p in ("dev", "test")},
                  scene_hashes={s.scene_spec_ref: sha256(root / s.scene_spec_ref) for s in all_samples})
    write_json(destination / "manifest.json", result)
    return result


def load_study(partition, root=ROOT):
    if partition not in ("dev", "test"):
        raise ValueError("Explicit dev or test partition required")
    return [StudySample(**json.loads(line)).validate() for line in
            (Path(root) / f"data/phase3/{partition}.jsonl").read_text().splitlines() if line]


def read_sample(value):
    """Compatibility reader: old records remain valid without rewriting them."""
    return (StudySample(**value) if value.get("schema_version") == 3 else LegacySample(**value)).validate()


def layout_distance(a, b):
    # A lower bound based on container centers alone; source-slot geometry adds
    # detail to identity. Same geometry within 8 mm is treated as microjitter.
    import numpy as np
    aa, bb = [c["xy"] for c in a["containers"]], [c["xy"] for c in b["containers"]]
    if len(aa) != len(bb):
        return float("inf")
    return min(max(float(np.linalg.norm(np.array(x) - y)) for x, y in zip(aa, perm))
               for perm in itertools.permutations(bb))


def check_study(samples, root=ROOT):
    groups, fingerprints, scenes = {}, {}, {}
    distribution = {}
    for s in samples:
        s.validate()
        scene = s.scene(root)
        if groups.setdefault(s.group_id, s.partition) != s.partition:
            raise ValueError("Physical group crosses partitions")
        fp = layout_fingerprint(scene)
        if fingerprints.setdefault(fp, s.partition) != s.partition:
            raise ValueError("Alias/truth/wording version of a base scene crosses partitions")
        scenes.setdefault(s.group_id, scene)
        bucket = distribution.setdefault(s.partition, dict(samples=0, groups=0, templates={}, missing={}, orders={}))
        bucket["samples"] += 1
        for field, key in (("templates", s.template_id), ("missing", str(3 - len(s.initial_disclosed_slots))),
                           ("orders", s.dag["order"])):
            bucket[field][key] = bucket[field].get(key, 0) + 1
    cross_distances = []
    for a, b in itertools.combinations(scenes, 2):
        if groups[a] != groups[b]:
            distance = layout_distance(scenes[a], scenes[b])
            cross_distances.append(distance)
            if distance <= .025:
                raise ValueError("Near-duplicate base container layout crosses partitions")
    for partition, bucket in distribution.items():
        bucket["groups"] = sum(p == partition for p in groups.values())
    return dict(distribution=distribution, independent_groups=len(groups),
                minimum_cross_split_container_distance_m=min(cross_distances),
                split_rule="base geometry including unordered category slots; no truth-dependent grouping")
