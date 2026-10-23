"""Negative geometry fixtures deliberately alter poses only inside tests.

No test fixture is presented as a successful robot action. Positive success
fixtures execute all skills with actual Bullet dynamics and Panda motors.
"""
import numpy as np
import pybullet as p
import pytest

from when2ask.environment import Environment
from when2ask.evaluator import Evaluator
from when2ask.skills import RobotSkills
from when2ask.task import PrivateTaskSpec


def score(env, termination="done", actions=None):
    return Evaluator().evaluate(env, PrivateTaskSpec(), clarification_burden=0,
                                actions=actions or [{"success": True}] * 3, termination=termination)


@pytest.fixture(scope="module")
def packed_world():
    with Environment() as env:
        skills = RobotSkills(env)
        actions = [skills.pick_place("blue_cup", "box").to_dict(),
                   skills.pick_place("green_block", "box").to_dict(),
                   skills.cover("black_lid", "box").to_dict()]
        assert all(a["success"] for a in actions)
        yield env, actions


def test_claimed_success_ids_cannot_override_physics(env):
    result = score(env)
    assert not result["task_success"]
    assert not result["conditions"]["correct_cup_inside"]
    assert not result["conditions"]["correct_lid_covers"]


def test_center_inside_but_body_crossing_wall_is_rejected(env):
    key = "green_block"
    position = [env.BOX_XY[0] + env.INNER_HALF[0] - .005, env.BOX_XY[1], env.FLOOR_Z + .022]
    assert position[0] < env.BOX_XY[0] + env.INNER_HALF[0]
    p.resetBasePositionAndOrientation(env.objects[key].body_id, position, [0, 0, 0, 1],
                                      physicsClientId=env.client)
    assert not env.containment(key)["full_xy_inside"]
    assert not score(env)["task_success"]


def test_centered_rotated_lid_does_not_cover_all_corners(env):
    p.resetBasePositionAndOrientation(env.objects["black_lid"].body_id,
                                      [*env.BOX_XY, env.RIM_Z + .006],
                                      p.getQuaternionFromEuler([0, 0, np.pi / 4]),
                                      physicsClientId=env.client)
    details = env.coverage("black_lid")
    assert not details["all_mouth_corners_covered"]
    assert not details["covered"]
    assert not score(env)["conditions"]["correct_lid_covers"]


def test_lid_above_opening_without_support_is_rejected(env):
    p.resetBasePositionAndOrientation(env.objects["black_lid"].body_id,
                                      [*env.BOX_XY, env.RIM_Z + .04], [0, 0, 0, 1],
                                      physicsClientId=env.client)
    details = env.coverage("black_lid")
    assert details["all_mouth_corners_covered"]
    assert not details["height_ok"] and not details["rim_supported"]
    assert not details["covered"]


def test_real_success_requires_release_order_but_is_independent_of_termination(packed_world):
    env, actions = packed_world
    assert score(env, actions=actions)["task_success"]
    outcome = score(env, "skill_failed:grasp_out_of_range", actions)
    assert outcome["task_success"]
    assert outcome["termination_reason"] == "skill_failed:grasp_out_of_range"
    original = env.events
    try:
        # Keep final physics unchanged; remove the sensor evidence of prior packing.
        env.events = [e for e in original if e["kind"] != "cover_started"]
        result = score(env, actions=actions)
        assert result["conditions"]["correct_cup_inside"]
        assert not result["conditions"]["packing_before_cover"]
        assert not result["task_success"]
        env.events = [dict(e, contents_before=[]) if e["kind"] == "cover_started" else e
                      for e in original]
        assert not score(env, actions=actions)["task_success"]
    finally:
        env.events = original
    # A fault fixture adds a real Bullet attachment without changing bookkeeping.
    cid = p.createConstraint(env.robot, env.EE_LINK, env.objects["black_lid"].body_id, -1,
                              p.JOINT_FIXED, [0, 0, 0], [0, 0, 0], [0, 0, 0],
                              physicsClientId=env.client)
    try:
        assert env.held_object is None
        assert not score(env, actions=actions)["conditions"]["robot_released"]
    finally:
        p.removeConstraint(cid, physicsClientId=env.client)
