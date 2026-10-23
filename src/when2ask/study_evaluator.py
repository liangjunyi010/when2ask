"""Version 3 scoring: final Bullet geometry, support, release and witnessed DAG."""
from __future__ import annotations

import pybullet as p

from .evaluator import Evaluator

EVALUATOR_VERSION = "full_aabb_contact_dag_v3.1"


def expected_targets(sample, env):
    if sample.template_id == "pack_and_cover":
        return {"cup": "box", "block": "box"}
    cup_target = sample.theta_star["cup_destination_choice"]
    other = next(k for k in env.container_ids if k != cup_target)
    return {"cup": cup_target, "block": other}


def order_evidence(env, sample, targets):
    events = {}
    for role in ("cup", "block"):
        key = sample.theta_star[role + "_choice"]
        relevant = [e for e in env.events if e["kind"] == "placement_started" and e["object_id"] == key
                    and e["target_id"] == targets[role]
                    and any(r["kind"] == "release" and r["object_id"] == key
                            and r["step"] >= e["step"] and
                            any(a["kind"] == "skill_result" and a["object_id"] == key
                                and a["start_step"] == e["step"] and r["step"] <= a["end_step"]
                                for a in env.events) for r in env.events)]
        events[role] = relevant[-1] if relevant else None
    checks = {}
    for parent, child in sample.dag["edges"]:
        if child == "cover":
            continue  # Original independent cover evaluator checks these edges.
        before, after = parent.removeprefix("place_"), child.removeprefix("place_")
        first, second = events[before], events[after]
        checks[parent + "->" + child] = bool(first and second and first["step"] < second["step"]
            and sample.theta_star[before + "_choice"] in second["contents_before"][targets[before]]
            and second["released_before"])
    return dict(placement_events_present=all(events.values()), precedence_checks=checks,
                satisfied=all(events.values()) and all(checks.values()))


def evaluate_study(env, sample, *, clarification_burden, actions, termination):
    targets = expected_targets(sample, env)
    order = order_evidence(env, sample, targets)
    if sample.template_id == "pack_and_cover":
        result = Evaluator().evaluate(env, sample.private_spec(), clarification_burden=clarification_burden,
                                      actions=actions, termination=termination)
        result["conditions"]["declared_dag_order"] = bool(order["satisfied"])
        result["details"]["declared_dag"] = order
        result["task_success"] = all(result["conditions"].values())
        result["evaluator_version"] = EVALUATOR_VERSION
        return result
    selected = {sample.theta_star[r + "_choice"] for r in ("cup", "block")}
    inside = {r: env.containment(sample.theta_star[r + "_choice"], targets[r]) for r in ("cup", "block")}
    outside = {key: {target: env.outside_box(key, target) for target in env.container_ids}
               for key, obj in env.objects.items() if obj.category != "container" and key not in selected}
    contacts = {key: len(p.getContactPoints(env.objects[key].body_id, env.robot,
                                          physicsClientId=env.client)) for key in selected}
    conditions = dict(correct_cup_in_selected_container=inside["cup"]["inside"],
                      correct_block_in_other_container=inside["block"]["inside"],
                      unselected_objects_outside=all(v["outside"] for row in outside.values() for v in row.values()),
                      robot_released=bool(env.released() and not any(contacts.values())),
                      declared_dag_order=bool(order["satisfied"]))
    return dict(task_success=all(conditions.values()), termination_reason=termination,
                execution_termination=termination, execution_completed=termination == "done",
                evaluator_version=EVALUATOR_VERSION, conditions=conditions,
                details=dict(expected_objects={r: sample.theta_star[r + "_choice"] for r in ("cup", "block")},
                             expected_targets=targets, containment=inside, unselected=outside,
                             robot_contact_counts=contacts, declared_dag=order),
                clarification_burden=clarification_burden, action_count=len(actions),
                successful_action_count=sum(bool(a["success"]) for a in actions), simulation_steps=env.step_count)
