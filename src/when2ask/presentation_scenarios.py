"""Twenty presentation task instances, separate from the frozen study dataset.

The DAG describes publicly instructed precedence, not an oracle gate label.
Private choices remain in StudySample; catalogue entries contain no answers.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import random
from collections import Counter
from dataclasses import asdict

from .config import ROOT
from .study_data import (SOURCE_PAIRS, TEMPLATES, StudySample, base_scene, dag_for,
                         instruction, layout_fingerprint, sha256, write_json)

VERSION = "presentation_dag_v1"
DIRECTORY = "data/presentation_dag_v1"
# order, unknown public roles, title, teaching focus (observer only)
PROFILES = (
    ("independent", (), "All choices known", "No preference clarification needed"),
    ("cup_first", (), "Known cup first", "Follow a public precedence edge"),
    ("block_first", ("block",), "Block unlocks the task", "A known cup cannot bypass the block-first instruction"),
    ("cup_first", ("lid",), "Ask about the lid later", "Two supported placements are available before covering"),
    ("independent", ("cup",), "Known block can go first", "An unknown cup does not block the independent block"),
    ("cup_first", ("block", "lid"), "Pack the known cup", "One supported action precedes two missing choices"),
    ("block_first", ("cup", "lid"), "Pack the known block", "One supported action precedes two missing choices"),
    ("independent", ("cup", "block"), "Lid known, contents unknown", "Cover requires both placements"),
    ("cup_first", ("cup", "block", "lid"), "All choices missing, cup first", "Clarify the current dependency; later choices can be batched"),
    ("block_first", ("cup", "block", "lid"), "All choices missing, block first", "The public order is still binding when choices are unknown"),
    ("independent", (), "Two known destinations", "The block uses the other container"),
    ("cup_first", (), "Known split, cup first", "Follow the cup-to-block dependency"),
    ("block_first", (), "Known split, block first", "Follow the block-to-cup dependency"),
    ("cup_first", ("block",), "Cup ready, block missing", "Perform the specified cup placement before clarifying the block"),
    ("independent", ("cup_destination",), "One answer, two destinations", "A destination answer is reusable for both objects"),
    ("block_first", ("block", "cup_destination"), "Known cup behind a dependency", "A known object alone does not imply an executable action"),
    ("independent", ("cup", "block"), "Destinations known, objects missing", "Shared destination knowledge cannot select the objects"),
    ("cup_first", ("cup", "block", "cup_destination"), "Unknown split, cup first", "Combine or sequence requests without repeating disclosed choices"),
    ("block_first", ("cup", "block", "cup_destination"), "Unknown split, block first", "Resolve the current block and reusable destination preference"),
    ("independent", ("cup", "block", "cup_destination"), "Unknown split, either first", "Both object choices and the shared destination are unknown"),
)


def load_samples(root=ROOT):
    return [StudySample(**json.loads(line)).validate() for line in
            (root / DIRECTORY / "samples.jsonl").read_text().splitlines() if line.strip()]


def catalogue(root=ROOT):
    path = root / DIRECTORY / "catalogue.json"
    return json.loads(path.read_text()) if path.exists() else []


def get_sample(sample_id, root=ROOT):
    return next((s for s in load_samples(root) if s.sample_id == sample_id), None)


def public_dag(sample):
    # Every edge is explicitly stated in u0; no expected action IDs or truth.
    return copy.deepcopy(sample.dag)


def generate(root=ROOT, seed=427820):
    destination = root / DIRECTORY
    if destination.exists():
        raise FileExistsError("Use a new version directory; presentation data is immutable")
    destination.mkdir(parents=True)
    samples, entries = [], []
    for index, (order, unknown, title, focus) in enumerate(PROFILES):
        ti = index // 10
        template = TEMPLATES[ti]
        family_index = index % 5
        rng = random.Random(f"{VERSION}:{seed}:{index}")
        scene = base_scene(template, "dev", family_index)
        fingerprint = layout_fingerprint(scene)
        family = "layout_" + fingerprint[:16]
        for pair in SOURCE_PAIRS.values():
            if pair[0] in scene["sources"] and rng.getrandbits(1):
                scene["sources"][pair[0]], scene["sources"][pair[1]] = scene["sources"][pair[1]], scene["sources"][pair[0]]
        names = [c["id"] for c in scene["containers"]] + list(scene["sources"])
        aliases = {k: "box" if k == "box" else f"obj_{rng.getrandbits(40):010x}" for k in names}
        ids = list(aliases.values()); rng.shuffle(ids)
        scene.update(object_id_map=aliases, object_order=ids, layout_fingerprint=fingerprint)
        sample_id = f"dag_demo_{index + 1:02d}"
        ref = f"{DIRECTORY}/scenes/{sample_id}.json"
        write_json(root / ref, scene)
        roles = ("cup", "block", "lid" if ti == 0 else "cup_destination")
        pairs = (SOURCE_PAIRS["cup"], SOURCE_PAIRS["block"],
                 SOURCE_PAIRS["lid"] if ti == 0 else ("container_a", "container_b"))
        # Balanced truth independent of aliases, candidate order and positions.
        truth = list(itertools.product((0, 1), repeat=3))[(index * 3 + ti) % 8]
        slots, theta = {}, {}
        for role, pair, bit in zip(roles, pairs, truth):
            candidates = [aliases[k] for k in pair]; rng.shuffle(candidates)
            slots[role + "_choice"] = dict(public_role=role, candidate_ids=candidates)
            theta[role + "_choice"] = aliases[pair[bit]]
        disclosed = [r + "_choice" for r in roles if r not in unknown]
        u0 = instruction(template, order, index)
        for slot in disclosed:
            u0 += f" For the {slots[slot]['public_role']}, use {theta[slot]}."
        sample = StudySample(sample_id, template + ":" + family, template,
            rng.randrange(10_000, 2_000_000_000), ref, u0, slots, dag_for(template, order),
            theta, disclosed, {"unselected_outside": True, "released": True},
            "dev", layout_family_id=family).validate()
        samples.append(sample)
        entries.append(dict(sample_id=sample_id, title=title, template_id=template,
            group_id=sample.group_id, layout_family_id=family, unknown_preferences=len(unknown),
            order=order, dag=public_dag(sample), focus=focus, instruction=u0))
    path = destination / "samples.jsonl"
    path.write_text("".join(json.dumps(asdict(s), sort_keys=True) + "\n" for s in samples))
    write_json(destination / "catalogue.json", entries)
    result = dict(version=VERSION, schema_compatibility="StudySample v3.1",
        purpose="presentation smoke scenarios; not formal Dev/Test or 20 new task types",
        seed=seed, samples=len(samples), independent_physical_groups=len({s.group_id for s in samples}),
        templates=dict(Counter(s.template_id for s in samples)),
        missing_preferences=dict(Counter(e["unknown_preferences"] for e in entries)),
        public_order=dict(Counter(e["order"] for e in entries)),
        samples_sha256=sha256(path), catalogue_sha256=sha256(destination / "catalogue.json"),
        scene_hashes={s.scene_spec_ref: sha256(root / s.scene_spec_ref) for s in samples},
        note="Five conservative base layouts per template; two task variants per group. Existing Dev layouts reused; no Test selection.")
    write_json(destination / "manifest.json", result)
    return result


def validate(root=ROOT):
    samples = load_samples(root)
    entries = catalogue(root)
    manifest = json.loads((root / DIRECTORY / "manifest.json").read_text())
    assert len(samples) == len(entries) == 20
    assert manifest["samples_sha256"] == sha256(root / DIRECTORY / "samples.jsonl")
    assert manifest["catalogue_sha256"] == sha256(root / DIRECTORY / "catalogue.json")
    for s, entry in zip(samples, entries):
        scene = s.scene(root)
        assert s.sample_id == entry["sample_id"] and s.dag == entry["dag"]
        assert sha256(root / s.scene_spec_ref) == manifest["scene_hashes"][s.scene_spec_ref]
        assert len(set(scene["object_id_map"].values())) == len(scene["object_id_map"])
        assert set(scene["object_order"]) == set(scene["object_id_map"].values())
        assert entry["unknown_preferences"] == 3 - len(s.initial_disclosed_slots)
        assert not {"theta_star", "slots", "correct_action_ids"} & entry.keys()
    assert Counter(e["unknown_preferences"] for e in entries) == {0: 5, 1: 5, 2: 5, 3: 5}
    return dict(schema_valid=True, hashes_valid=True, sample_count=len(samples),
                groups=len({s.group_id for s in samples}), public_catalogue_has_no_hidden_registry=True)
