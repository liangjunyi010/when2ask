"""Independent deterministic scoring from Bullet geometry, contacts and trusted events."""
from __future__ import annotations

import pybullet as p

from .environment import Environment
from .task import PrivateTaskSpec


class Evaluator:
    def evaluate(self, env: Environment, private_spec: PrivateTaskSpec, *,
                 clarification_burden: int, actions: list[dict], termination: str):
        cup, block, lid = (private_spec.cup_choice, private_spec.block_choice,
                           private_spec.lid_choice)
        selected = {cup, block, lid}
        cup_details, block_details = env.containment(cup), env.containment(block)
        lid_details = env.coverage(lid)
        outside = {key: env.outside_box(key) for key in env.objects
                   if key not in selected and key != "box"}
        contacts = {key: len(p.getContactPoints(env.objects[key].body_id, env.robot,
                                               physicsClientId=env.client)) for key in selected}
        released = bool(env.released() and not any(contacts.values()))
        covers = [e for e in env.events if e["kind"] == "cover_started"]
        packing_before_cover = []
        for event in covers:
            completed_before = {e["object_id"] for e in env.events
                                if e["kind"] == "skill_result" and e["skill"] == "pick_place"
                                and e["success"] and e["end_step"] <= event["step"]}
            packing_before_cover.append(
                {cup, block}.issubset(event["contents_before"])
                and {cup, block}.issubset(completed_before) and event["released_before"])
        order_ok = bool(covers and all(packing_before_cover))
        conditions = dict(correct_cup_inside=cup_details["inside"],
                          correct_block_inside=block_details["inside"],
                          correct_lid_covers=lid_details["covered"],
                          unselected_objects_outside=all(d["outside"] for d in outside.values()),
                          robot_released=released, packing_before_cover=order_ok,
                          execution_completed=termination == "done" and len(actions) >= 3)
        success = all(conditions.values())
        reason = ("success" if success else
                  "conditions_not_satisfied" if termination == "done" else termination)
        return dict(task_success=success, termination_reason=reason,
                    execution_termination=termination, conditions=conditions,
                    details=dict(expected_objects=dict(cup=cup, block=block, lid=lid),
                                 cup=cup_details, block=block_details, lid=lid_details,
                                 unselected=outside, robot_contact_counts=contacts,
                                 cover_order_checks=packing_before_cover),
                    clarification_burden=clarification_burden, action_count=len(actions),
                    successful_action_count=sum(bool(a["success"]) for a in actions),
                    simulation_steps=env.step_count)
