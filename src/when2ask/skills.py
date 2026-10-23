"""Bounded Panda motor/IK skills with explicitly logged proximity constraint grasp."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pybullet as p

from .environment import Environment


@dataclass
class SkillResult:
    skill: str
    object_id: str
    target_id: str
    success: bool
    reason: str
    start_step: int
    end_step: int
    grasp_mode: str = "constraint"

    def to_dict(self):
        return asdict(self)


class SkillFailure(RuntimeError):
    pass


class RobotSkills:
    TRANSIT_Z = .83
    MAX_SKILL_STEPS = 15000
    ORIENTATION = p.getQuaternionFromEuler((np.pi, 0, 0))

    def __init__(self, env: Environment):
        self.env = env
        self._deadline = 0
        self._collision_suppressed: set[str] = set()

    def _tick(self, count=1):
        if self.env.step_count + count > self._deadline:
            raise SkillFailure("skill_step_limit")
        self.env.step(count)

    def move_to(self, position, speed=.22):
        env = self.env
        start = np.array(env.ee_pose()[0])
        target = np.asarray(position)
        ticks = max(100, int(np.linalg.norm(target - start) / speed / env.DT))
        if ticks > 1400:
            raise SkillFailure("unreachable_waypoint")
        for tick in range(ticks + 180):
            alpha = min((tick + 1) / ticks, 1)
            waypoint = start + alpha * (target - start)
            joints = p.calculateInverseKinematics(env.robot, env.EE_LINK, waypoint,
                                                  self.ORIENTATION, maxNumIterations=60,
                                                  residualThreshold=1e-5,
                                                  physicsClientId=env.client)
            env.command_joints(joints)
            self._tick()
            if tick >= ticks and np.linalg.norm(np.array(env.ee_pose()[0]) - target) < .006:
                return
        error = float(np.linalg.norm(np.array(env.ee_pose()[0]) - target))
        raise SkillFailure(f"ik_not_converged:{error:.4f}m")

    def _grasp(self, object_id, grip_point):
        env = self.env
        if env.held_object:
            raise SkillFailure("already_holding_object")
        actual, orientation = env.ee_pose()
        distance = float(np.linalg.norm(np.array(actual) - grip_point))
        body = env.objects[object_id].body_id
        nearby = p.getClosestPoints(env.robot, body, .05, physicsClientId=env.client)
        hand_distances = [c[8] for c in nearby if c[3] in (8, 9, 10, 11)]
        if distance > .025 or not hand_distances or min(hand_distances) > .04:
            raise SkillFailure(f"grasp_out_of_range:{distance:.4f}m")
        env.command_fingers(.018)
        # Disable only held-object/hand collision: the constraint is grasp assistance.
        # All world collisions and the remaining arm links remain active.
        for link in (8, 9, 10, 11):
            p.setCollisionFilterPair(env.robot, body, link, -1, 0, physicsClientId=env.client)
        self._collision_suppressed.add(object_id)
        obj_pos, obj_rot = env.body_pose(object_id)
        inv_pos, inv_rot = p.invertTransform(actual, orientation)
        rel_pos, rel_rot = p.multiplyTransforms(inv_pos, inv_rot, obj_pos, obj_rot)
        cid = p.createConstraint(env.robot, env.EE_LINK, body, -1, p.JOINT_FIXED, (0, 0, 0),
                                  rel_pos, (0, 0, 0), parentFrameOrientation=rel_rot,
                                  childFrameOrientation=(0, 0, 0, 1),
                                  physicsClientId=env.client)
        p.changeConstraint(cid, maxForce=150, erp=.8, physicsClientId=env.client)
        env.grasp_constraint, env.held_object = cid, object_id
        env.events.append(dict(kind="grasp", object_id=object_id, step=env.step_count,
                               grasp_mode="constraint", grip_error_m=distance,
                               closest_hand_distance_m=min(hand_distances)))
        self._tick(60)

    def _release(self):
        env = self.env
        key = env.held_object
        if env.grasp_constraint is not None:
            p.removeConstraint(env.grasp_constraint, physicsClientId=env.client)
        env.grasp_constraint = None
        env.held_object = None
        env.command_fingers(.04)
        env.events.append(dict(kind="release", object_id=key, step=env.step_count))
        return key

    def _restore_collisions(self, object_id):
        body = self.env.objects[object_id].body_id
        for link in (8, 9, 10, 11):
            p.setCollisionFilterPair(self.env.robot, body, link, -1, 1,
                                     physicsClientId=self.env.client)
        self._collision_suppressed.discard(object_id)

    def _cleanup_failed_grasp(self):
        if self.env.held_object:
            self._release()
        for key in list(self._collision_suppressed):
            self._restore_collisions(key)

    def _transfer(self, object_id, desired_center):
        env = self.env
        def phase(name):
            env.events.append(dict(kind="phase", phase=name, object_id=object_id,
                                   step=env.step_count, end_effector=list(env.ee_pose()[0])))

        lo, hi = env.bounds(object_id)
        center = np.array(env.body_pose(object_id)[0])
        # Regrasping a short packed object needs the wider hand above the rim.
        # Its fingertips remain within the same 40 mm proximity requirement.
        inside = (any(env.containment(object_id, key)["inside"] for key in env.container_ids)
                  if hasattr(env, "container_ids") and env.objects[object_id].category in ("cup", "block")
                  else ("box" in env.objects and env.objects[object_id].category in ("cup", "block")
                        and env.containment(object_id)["inside"]))
        grip = np.array([center[0], center[1], hi[2] + (.035 if inside else .018)])
        env.command_fingers(.04)
        phase("approach")
        current = np.array(env.ee_pose()[0])
        self.move_to([current[0], current[1], self.TRANSIT_Z])
        self.move_to([grip[0], grip[1], self.TRANSIT_Z])
        self.move_to(grip, speed=.14)
        self._grasp(object_id, grip)
        offset = np.array(env.ee_pose()[0]) - np.array(env.body_pose(object_id)[0])
        phase("lift")
        self.move_to([grip[0], grip[1], self.TRANSIT_Z], speed=.17)
        destination = np.asarray(desired_center) + offset
        phase("transport")
        self.move_to([destination[0], destination[1], self.TRANSIT_Z], speed=.17)
        phase("lower")
        self.move_to(destination, speed=.12)
        released = self._release()
        self._tick(90)
        self.move_to([destination[0], destination[1], self.TRANSIT_Z], speed=.14)
        self._restore_collisions(released)
        phase("settle")
        self._tick(240)

    def pick_place(self, object_id, target_id, relation="inside"):
        env = self.env
        start = env.step_count
        self._deadline = start + self.MAX_SKILL_STEPS
        try:
            if object_id not in env.objects:
                raise SkillFailure("unknown_object")
            category = env.objects[object_id].category
            if category not in ("cup", "block") and not (category == "lid" and target_id == "table"):
                raise SkillFailure("object_is_not_packable")
            if target_id == "box" and relation == "inside" and "box" in env.objects:
                is_cup = env.objects[object_id].category == "cup"
                dx, dy = (-.052, -.035) if is_cup else (.052, .035)
                half_height = env.objects[object_id].half_extents[2]
                destination = (env.BOX_XY[0] + dx, env.BOX_XY[1] + dy,
                               env.FLOOR_Z + half_height + .004)
            elif target_id == "table" and relation == "on":
                half_height = env.objects[object_id].half_extents[2]
                xy = env.home_positions[object_id][:2] if "box" in env.objects else (.57, .10)
                destination = (*xy, env.TABLE_Z + half_height + .004)
            else:
                raise SkillFailure("unsupported_target")
            self._transfer(object_id, destination)
            lo, hi = env.bounds(object_id)
            ok = (env.containment(object_id)["inside"] if target_id == "box" else
                  (bool(env.outside_box(object_id)["outside"] and abs(lo[2] - env.TABLE_Z) < .005)
                   if "box" in env.objects else
                   bool(.53 < lo[0] and hi[0] < .61 and .06 < lo[1] and hi[1] < .14
                        and abs(lo[2] - env.TABLE_Z) < .005)))
            reason = "placed" if ok else "placement_geometry_failed"
        except (SkillFailure, p.error) as exc:
            ok, reason = False, str(exc)
            self._cleanup_failed_grasp()
        result = SkillResult("pick_place", object_id, target_id, ok, reason, start, env.step_count)
        env.events.append(dict(kind="skill_result", **result.to_dict()))
        return result

    def cover(self, lid_id, box_id):
        env = self.env
        start = env.step_count
        self._deadline = start + self.MAX_SKILL_STEPS
        try:
            if lid_id not in env.objects or env.objects[lid_id].category != "lid":
                raise SkillFailure("unknown_lid")
            if box_id != "box" or box_id not in env.objects:
                raise SkillFailure("unknown_box")
            contents = [key for key, obj in env.objects.items() if obj.category in ("cup", "block")
                        and env.containment(key)["inside"]]
            env.events.append(dict(kind="cover_started", step=start,
                                   contents_before=contents, released_before=env.released(),
                                   lid_id=lid_id))
            self._transfer(lid_id, (*env.BOX_XY, env.RIM_Z + .006 + .004))
            ok = env.coverage(lid_id)["covered"]
            reason = "covered" if ok else "lid_geometry_failed"
        except (SkillFailure, p.error) as exc:
            ok, reason = False, str(exc)
            self._cleanup_failed_grasp()
        result = SkillResult("cover", lid_id, box_id, ok, reason, start, env.step_count)
        env.events.append(dict(kind="skill_result", **result.to_dict()))
        return result
