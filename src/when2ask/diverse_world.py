"""Version 3 physical scenes. Legacy environment and its default layout survive.

All containers have real hollow compound collision geometry. No pose resets are
used at execution time. The original motor controller and guarded grasp are reused.
"""
from __future__ import annotations

import numpy as np
import pybullet as p

from .environment import Environment, SceneObject
from .skills import RobotSkills, SkillFailure, SkillResult

PHYSICS_VERSION = "panda_diverse_v3.1"


class DiverseEnvironment(Environment):
    def __init__(self, seed=0, *, scene_spec, **kwargs):
        self.spec = scene_spec
        self.geometry = {}
        super().__init__(seed, scene_spec=scene_spec, **kwargs)
        aliases = scene_spec["object_id_map"]
        self.geometry = {aliases[k]: v for k, v in self.geometry.items()}
        self.container_ids = tuple(self.geometry)
        self.home_positions = {k: self.body_pose(k)[0] for k, o in self.objects.items()
                               if o.category != "container"}

    def _build_scene(self, minimal):
        if minimal:
            raise ValueError("Diverse scenes require the complete declared geometry")
        for container in self.spec["containers"]:
            key, xy = container["id"], container["xy"]
            hx, hy = container["half_xy"]
            height, wall, floor = container["wall_height"], .012, .014
            inner = (hx - wall, hy - wall)
            halves = [(hx, hy, floor / 2), (wall / 2, hy, height / 2),
                      (wall / 2, hy, height / 2), (inner[0], wall / 2, height / 2),
                      (inner[0], wall / 2, height / 2)]
            poses = [(0, 0, floor / 2), (-hx + wall / 2, 0, floor + height / 2),
                     (hx - wall / 2, 0, floor + height / 2),
                     (0, -hy + wall / 2, floor + height / 2),
                     (0, hy - wall / 2, floor + height / 2)]
            color = container.get("rgba", [.63, .4, .2, 1])
            body = self._compound([p.GEOM_BOX] * 5, halves, poses, [(0, 0, 0, 1)] * 5,
                                  (*xy, self.TABLE_Z), color, 0)
            self.objects[key] = SceneObject(key, body, "container", container["color"],
                                           (hx, hy, (floor + height) / 2))
            self.geometry[key] = dict(xy=xy, half=(hx, hy), inner=inner,
                                      floor=self.TABLE_Z + floor, rim=self.TABLE_Z + floor + height)
        if self.spec["template_id"] == "pack_and_cover":
            g = next(iter(self.geometry.values()))
            self.BOX_XY, self.BOX_HALF, self.INNER_HALF = tuple(g["xy"]), g["half"], g["inner"]
            self.FLOOR_Z, self.RIM_Z = g["floor"], g["rim"]
        sources = self.spec["sources"]
        for key, rgba, name in (("red_cup", (.85, .08, .08, 1), "red"),
                                ("blue_cup", (.06, .25, .92, 1), "blue")):
            self._add_cup(key, sources[key], rgba, name)
        for key, rgba, name in (("green_block", (.1, .72, .27, 1), "green"),
                                ("yellow_block", (.98, .76, .06, 1), "yellow")):
            self._add_block(key, sources[key], rgba, name)
        if self.spec["template_id"] == "pack_and_cover":
            for key, rgba, name in (("black_lid", (.065, .065, .075, 1), "black"),
                                    ("white_lid", (.94, .94, .94, 1), "white")):
                xy = np.array(sources[key]) + self.rng.uniform(-.004, .004, 2)
                body = self._box((.154, .134, .006), (*xy, self.TABLE_Z + .008), rgba, .1)
                self.objects[key] = SceneObject(key, body, "lid", name, (.154, .134, .006))

    def containment(self, object_id, container_id=None):
        target = container_id or self.spec["object_id_map"][self.spec["containers"][0]["id"]]
        # During base initialization, the aliases have not yet been applied.
        g = self.geometry[target]
        lo, hi = self.bounds(object_id)
        xy, half = np.array(g["xy"]), np.array(g["inner"])
        xy_ok = bool(np.all(lo[:2] >= xy - half - .002) and np.all(hi[:2] <= xy + half + .002))
        z_ok = bool(lo[2] >= g["floor"] - .004 and hi[2] <= g["rim"] + .002)
        contacts = p.getContactPoints(self.objects[object_id].body_id, self.objects[target].body_id,
                                      physicsClientId=self.client)
        supported = any(c[7][2] > .65 and c[9] > .001 for c in contacts)
        return dict(inside=bool(xy_ok and z_ok and supported and self.stable(object_id)),
                    full_xy_inside=xy_ok, full_z_inside=z_ok, supported_by_box=supported,
                    stable=self.stable(object_id), aabb_min=lo.tolist(), aabb_max=hi.tolist())

    def outside_box(self, object_id, container_id=None):
        target = container_id or self.spec["object_id_map"][self.spec["containers"][0]["id"]]
        g = self.geometry[target]
        lo, hi = self.bounds(object_id)
        lower, upper = np.array(g["xy"]) - g["half"], np.array(g["xy"]) + g["half"]
        outside = bool(np.any(hi[:2] < lower - .001) or np.any(lo[:2] > upper + .001))
        return dict(outside=bool(outside and self.stable(object_id)),
                    footprint_disjoint=outside, stable=self.stable(object_id))

    def coverage(self, lid_id):
        # The original full-corner/rim-contact evaluator is used without relaxed
        # tolerances. Its box lookup needs the physical container's visible alias.
        box = self.spec["object_id_map"][self.spec["containers"][0]["id"]]
        if box == "box":
            return super().coverage(lid_id)
        self.objects["box"] = self.objects[box]
        try:
            return super().coverage(lid_id)
        finally:
            del self.objects["box"]


class DiverseSkills(RobotSkills):
    def pick_place(self, object_id, target_id, relation="inside"):
        env, start = self.env, self.env.step_count
        self._deadline = start + self.MAX_SKILL_STEPS
        try:
            if object_id not in env.objects or env.objects[object_id].category not in ("cup", "block", "lid"):
                raise SkillFailure("object_is_not_packable")
            obj = env.objects[object_id]
            if target_id in env.geometry and relation == "inside" and obj.category != "lid":
                g = env.geometry[target_id]
                # Leave clearance for both roles even when an uninformed planner
                # chooses the same container. Full geometry still decides success.
                offset = ((-.052, -.035) if obj.category == "cup" else (.052, .035))
                if env.spec["template_id"] != "pack_and_cover":
                    offset = ((-.025, -.02) if obj.category == "cup" else (.025, .02))
                destination = (g["xy"][0] + offset[0], g["xy"][1] + offset[1],
                               g["floor"] + obj.half_extents[2] + .004)
            elif target_id == "table" and relation == "on":
                destination = (*env.home_positions[object_id][:2], env.TABLE_Z + obj.half_extents[2] + .004)
            else:
                raise SkillFailure("unsupported_target")
            env.events.append(dict(kind="placement_started", object_id=object_id, target_id=target_id,
                                   step=start, contents_before={k: [o for o, v in env.objects.items()
                                       if v.category in ("cup", "block") and env.containment(o, k)["inside"]]
                                       for k in env.container_ids}, released_before=env.released()))
            self._transfer(object_id, destination)
            lo, _ = env.bounds(object_id)
            ok = (env.containment(object_id, target_id)["inside"] if target_id in env.geometry else
                  all(env.outside_box(object_id, k)["outside"] for k in env.container_ids)
                  and abs(lo[2] - env.TABLE_Z) < .005)
            reason = "placed" if ok else "placement_geometry_failed"
        except (SkillFailure, p.error) as exc:
            ok, reason = False, str(exc)
            self._cleanup_failed_grasp()
        result = SkillResult("pick_place", object_id, target_id, bool(ok), reason, start, env.step_count)
        env.events.append(dict(kind="skill_result", **result.to_dict()))
        return result

    def cover(self, lid_id, box_id):
        env = self.env
        if box_id not in env.geometry or env.spec["template_id"] != "pack_and_cover":
            return SkillResult("cover", lid_id, box_id, False, "unknown_box", env.step_count, env.step_count)
        # Reuse the original cover path, collision guards and event semantics.
        original = env.objects.get("box")
        env.objects["box"] = env.objects[box_id]
        try:
            result = super().cover(lid_id, "box")
            result.target_id = box_id
            env.events[-1]["target_id"] = box_id
            return result
        finally:
            if original is None:
                del env.objects["box"]
            else:
                env.objects["box"] = original
