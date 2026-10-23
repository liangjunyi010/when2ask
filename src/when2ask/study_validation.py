"""All-pairs initial geometry and hidden-input isolation checks on real worlds."""
import itertools
import json
from dataclasses import replace

import pybullet as p

from .config import ROOT
from .diverse_world import DiverseEnvironment
from .protocol import public_payload
from .study_data import check_study, load_study, sha256, write_json
from .study_protocol import observe


def validate_study():
    samples = load_study("dev") + load_study("test")
    grouping = check_study(samples)
    rows = []
    for s in samples:
        with DiverseEnvironment(s.scene_seed, scene_spec=s.scene()) as env:
            penetration = []
            for a, b in itertools.combinations(env.objects, 2):
                if all(env.objects[x].category == "container" for x in (a,b)):
                    continue
                contacts = p.getClosestPoints(env.objects[a].body_id, env.objects[b].body_id, 0,
                                              physicsClientId=env.client)
                depth = min((c[8] for c in contacts), default=0)
                if depth < -.002:
                    penetration.append(dict(a=a, b=b, depth_m=depth))
            original = public_payload(observe(env, s.u0, []))
            truth = dict(s.theta_star)
            for slot in set(s.slots) - set(s.initial_disclosed_slots):
                truth[slot] = next(k for k in s.slots[slot]["candidate_ids"] if k != truth[slot])
            changed = replace(s, theta_star=truth).validate()
            # Neither theta nor its registry is an argument to observe/project.
            altered = public_payload(observe(env, changed.u0, []))
            assert original == altered
            assert not penetration, f"Initial penetration: {s.sample_id}"
            rows.append(dict(sample_id=s.sample_id, full_pair_penetrations=penetration,
                             undisclosed_truth_change_preserves_payload=True,
                             scene_sha256=sha256(ROOT / s.scene_spec_ref)))
    result = dict(total=len(rows), all_passed=True, real_bullet_initial_worlds=len(rows),
                  api_attempts=0, grouping=grouping, checks=rows)
    write_json(ROOT / "outputs/phase3/data_validation.json", result)
    return result
