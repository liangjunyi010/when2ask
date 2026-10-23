"""Deterministic Bullet scene. This module never receives user preferences."""
from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image


@dataclass(frozen=True)
class SceneObject:
    object_id: str
    body_id: int
    category: str
    color: str
    half_extents: tuple[float, float, float]


class Environment:
    DT = 1 / 240
    TABLE_Z = 0.42
    EE_LINK = 11
    ARM_JOINTS = tuple(range(7))
    FINGERS = (9, 10)
    HOME = (0.0, -0.45, 0.0, -2.25, 0.0, 1.85, 0.785398)
    BOX_XY = (.57, .08)
    BOX_HALF = (.14, .12)
    INNER_HALF = (.128, .108)
    FLOOR_Z = TABLE_Z + .014
    RIM_Z = TABLE_Z + .124

    def __init__(self, seed: int = 0, gui: bool = False, minimal: bool = False,
                 realtime: bool = True, scene_spec: dict | None = None):
        self.client = p.connect(p.GUI if gui else p.DIRECT)
        if self.client < 0:
            raise RuntimeError("PyBullet connection failed")
        self.gui, self.realtime, self.seed = gui, realtime, seed
        self.step_count = 0
        self.events: list[dict] = []
        self.objects: dict[str, SceneObject] = {}
        self.held_object: str | None = None
        self.grasp_constraint: int | None = None
        self.frame_callback: Callable[[], None] | None = None
        self.rng = np.random.default_rng(seed)
        self.source_xy_overrides = (scene_spec or {}).get("source_xy_overrides", {})
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        p.setGravity(0, 0, -9.81, physicsClientId=self.client)
        p.setRealTimeSimulation(0, physicsClientId=self.client)
        p.setTimeStep(self.DT, physicsClientId=self.client)
        p.setPhysicsEngineParameter(numSolverIterations=150, deterministicOverlappingPairs=1,
                                    enableConeFriction=1, physicsClientId=self.client)
        p.loadURDF("plane.urdf", physicsClientId=self.client)
        self.table = self._box((0.66, 0.56, 0.025), (0.35, 0, self.TABLE_Z - .025),
                               (0.72, 0.61, 0.46, 1), mass=0)
        self.robot = p.loadURDF("franka_panda/panda.urdf", (0, 0, self.TABLE_Z),
                                useFixedBase=True, physicsClientId=self.client)
        # Joint resets are initialization only. Runtime movement always uses motors.
        for joint, angle in zip(self.ARM_JOINTS, self.HOME):
            p.resetJointState(self.robot, joint, angle, physicsClientId=self.client)
        for joint in self.FINGERS:
            p.resetJointState(self.robot, joint, .04, physicsClientId=self.client)
        self.command_joints(self.HOME)
        self.command_fingers(.04)
        self._build_scene(minimal)
        if scene_spec:
            aliases = scene_spec.get("object_id_map", {})
            if set(aliases) != set(self.objects) - {"box"} or len(set(aliases.values())) != len(aliases):
                raise ValueError("Scene must bijectively rename the six movable objects")
            renamed = {aliases.get(key, key): replace(obj, object_id=aliases.get(key, key))
                       for key, obj in self.objects.items()}
            order = scene_spec.get("object_order", list(renamed))
            if set(order) != set(renamed) or len(order) != len(renamed):
                raise ValueError("Scene object order is not a permutation")
            self.objects = {key: renamed[key] for key in order}
        if gui:
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=self.client)
            p.resetDebugVisualizerCamera(1.65, 48, -40, (.38, .02, .60),
                                         physicsClientId=self.client)
        self.step(240)
        self.initial_step = self.step_count
        self.home_positions = {key: self.body_pose(key)[0] for key in self.objects if key != "box"}

    def _box(self, half, position, color, mass=.06):
        collision = p.createCollisionShape(p.GEOM_BOX, halfExtents=half,
                                           physicsClientId=self.client)
        visual = p.createVisualShape(p.GEOM_BOX, halfExtents=half, rgbaColor=color,
                                     physicsClientId=self.client)
        body = p.createMultiBody(mass, collision, visual, position, physicsClientId=self.client)
        p.changeDynamics(body, -1, lateralFriction=.8, spinningFriction=.01,
                          rollingFriction=.001, restitution=0, linearDamping=.08,
                          angularDamping=.08, physicsClientId=self.client)
        return body

    def _build_scene(self, minimal):
        if minimal:
            self._add_block("green_block", (.35, -.16), (.1, .72, .27, 1), "green", jitter=False)
            return
        # One compound STATIC rigid body, with a bottom and four separate walls.
        # Its interior is empty collision space.
        half = [(.14, .12, .007), (.006, .12, .055), (.006, .12, .055),
                (.128, .006, .055), (.128, .006, .055)]
        positions = [(0, 0, .007), (-.134, 0, .069), (.134, 0, .069),
                     (0, -.114, .069), (0, .114, .069)]
        box = self._compound([p.GEOM_BOX] * 5, half, positions, [(0, 0, 0, 1)] * 5,
                             (.57, .08, self.TABLE_Z), (.63, .40, .20, 1), mass=0)
        self.objects["box"] = SceneObject("box", box, "container", "brown", (.14, .12, .062))
        self._add_cup("red_cup", (.48, -.10), (.85, .08, .08, 1), "red")
        self._add_cup("blue_cup", (.34, -.23), (.06, .25, .92, 1), "blue")
        self._add_block("green_block", (.28, -.03), (.10, .72, .27, 1), "green")
        self._add_block("yellow_block", (.29, .15), (.98, .76, .06, 1), "yellow")
        for key, xy, color, name in [
            ("black_lid", (.32, .39), (.065, .065, .075, 1), "black"),
            ("white_lid", (.61, -.33), (.94, .94, .94, 1), "white"),
        ]:
            xy = np.asarray(xy) + self.rng.uniform(-.004, .004, 2)
            body = self._box((.154, .134, .006), (*xy, self.TABLE_Z + .008), color, .10)
            self.objects[key] = SceneObject(key, body, "lid", name, (.154, .134, .006))

    def _compound(self, types, half, positions, orientations, location, color, mass,
                  radii=None, lengths=None):
        kwargs = dict(shapeTypes=types, halfExtents=half, physicsClientId=self.client)
        if radii is not None:
            kwargs.update(radii=radii, lengths=lengths)
        collision = p.createCollisionShapeArray(**kwargs, collisionFramePositions=positions,
                                                 collisionFrameOrientations=orientations)
        visual = p.createVisualShapeArray(**kwargs, visualFramePositions=positions,
                                           visualFrameOrientations=orientations,
                                           rgbaColors=[color] * len(types))
        body = p.createMultiBody(mass, collision, visual, location, physicsClientId=self.client)
        p.changeDynamics(body, -1, lateralFriction=.8, spinningFriction=.01,
                          restitution=0, linearDamping=.1, angularDamping=.1,
                          physicsClientId=self.client)
        return body

    def _add_block(self, key, xy, color, name, jitter=True):
        xy = np.asarray(xy) + (self.rng.uniform(-.004, .004, 2) if jitter else 0)
        body = self._box((.022, .022, .022), (*xy, self.TABLE_Z + .024), color)
        self.objects[key] = SceneObject(key, body, "block", name, (.022, .022, .022))

    def _add_cup(self, key, xy, color, name):
        # Hollow low-poly cup: cylindrical bottom + 12 thin radial wall panels.
        # It is a single dynamic compound rigid body, not a solid cylinder.
        xy = np.asarray(self.source_xy_overrides.get(key, xy)) + self.rng.uniform(-.004, .004, 2)
        n, radius = 12, .027
        positions = [(0, 0, -.027)]
        half = [(radius, radius, .003)]
        orientations = [(0, 0, 0, 1)]
        for i in range(n):
            angle = 2 * np.pi * i / n
            positions.append((.025 * np.cos(angle), .025 * np.sin(angle), .003))
            half.append((.002, .025 * np.tan(np.pi / n) + .0007, .027))
            orientations.append(p.getQuaternionFromEuler((0, 0, angle)))
        body = self._compound([p.GEOM_CYLINDER] + [p.GEOM_BOX] * n, half, positions,
                              orientations, (*xy, self.TABLE_Z + .032), color, .05,
                              radii=[radius] + [0] * n, lengths=[.006] + [0] * n)
        self.objects[key] = SceneObject(key, body, "cup", name, (.028, .028, .03))

    def command_joints(self, targets):
        p.setJointMotorControlArray(self.robot, self.ARM_JOINTS, p.POSITION_CONTROL,
                                     targetPositions=list(targets[:7]),
                                     forces=[160, 160, 120, 120, 80, 60, 40],
                                     positionGains=[.12] * 7, velocityGains=[1] * 7,
                                     physicsClientId=self.client)

    def command_fingers(self, opening):
        p.setJointMotorControlArray(self.robot, self.FINGERS, p.POSITION_CONTROL,
                                     targetPositions=[opening, opening], forces=[25, 25],
                                     physicsClientId=self.client)

    def step(self, count=1):
        for _ in range(count):
            p.stepSimulation(physicsClientId=self.client)
            self.step_count += 1
            if self.frame_callback:
                self.frame_callback()
            if self.gui and self.realtime:
                time.sleep(self.DT)

    def ee_pose(self):
        state = p.getLinkState(self.robot, self.EE_LINK, computeForwardKinematics=True,
                               physicsClientId=self.client)
        return state[4], state[5]

    def body_pose(self, object_id):
        return p.getBasePositionAndOrientation(self.objects[object_id].body_id,
                                               physicsClientId=self.client)

    def bounds(self, object_id):
        body = self.objects[object_id].body_id
        boxes = [p.getAABB(body, link, physicsClientId=self.client)
                 for link in range(-1, p.getNumJoints(body, physicsClientId=self.client))]
        return np.min([a for a, _ in boxes], axis=0), np.max([b for _, b in boxes], axis=0)

    def snapshot(self):
        """Physical state only; includes velocities so ASK invariance is checkable."""
        result = {}
        for key, obj in self.objects.items():
            position, orientation = self.body_pose(key)
            linear, angular = p.getBaseVelocity(obj.body_id, physicsClientId=self.client)
            lo, hi = self.bounds(key)
            result[key] = dict(category=obj.category, color=obj.color,
                               position=list(position), orientation=list(orientation),
                               aabb_min=lo.tolist(), aabb_max=hi.tolist(),
                               linear_velocity=list(linear), angular_velocity=list(angular))
        joints = p.getJointStates(self.robot, self.ARM_JOINTS + self.FINGERS,
                                  physicsClientId=self.client)
        return dict(simulation_step=self.step_count, objects=result,
                    end_effector=list(self.ee_pose()[0]), held_object=self.held_object,
                    robot_joints=[dict(position=s[0], velocity=s[1]) for s in joints])

    def stable(self, object_id):
        v, w = p.getBaseVelocity(self.objects[object_id].body_id, physicsClientId=self.client)
        return bool(np.linalg.norm(v) < .025 and np.linalg.norm(w) < .25)

    def containment(self, object_id):
        """Conservative FULL collision AABB containment + actual supporting contact."""
        lo, hi = self.bounds(object_id)
        xy = np.array(self.BOX_XY)
        half = np.array(self.INNER_HALF)
        xy_inside = bool(np.all(lo[:2] >= xy - half - .002)
                         and np.all(hi[:2] <= xy + half + .002))
        z_inside = bool(lo[2] >= self.FLOOR_Z - .004 and hi[2] <= self.RIM_Z + .002)
        contacts = p.getContactPoints(self.objects[object_id].body_id,
                                      self.objects["box"].body_id, physicsClientId=self.client)
        supported = any(c[7][2] > .65 and c[9] > .001 for c in contacts)
        return dict(inside=bool(xy_inside and z_inside and supported and self.stable(object_id)),
                    full_xy_inside=xy_inside, full_z_inside=z_inside,
                    supported_by_box=supported, stable=self.stable(object_id),
                    aabb_min=lo.tolist(), aabb_max=hi.tolist())

    def outside_box(self, object_id):
        lo, hi = self.bounds(object_id)
        lower = np.array(self.BOX_XY) - self.BOX_HALF
        upper = np.array(self.BOX_XY) + self.BOX_HALF
        # Entire horizontal collision envelope must be disjoint from the box.
        outside = bool(np.any(hi[:2] < lower - .001) or np.any(lo[:2] > upper + .001))
        return dict(outside=bool(outside and self.stable(object_id)),
                    footprint_disjoint=outside, stable=self.stable(object_id))

    def coverage(self, lid_id):
        obj = self.objects[lid_id]
        position, orientation = self.body_pose(lid_id)
        rotation = np.array(p.getMatrixFromQuaternion(orientation)).reshape(3, 3)
        normal_z = float(rotation[2, 2])
        # Test all four mouth corners in the ACTUAL rotated lid's local frame.
        mouth = np.array([[self.BOX_XY[0] + sx * self.INNER_HALF[0],
                           self.BOX_XY[1] + sy * self.INNER_HALF[1], self.RIM_Z]
                          for sx in (-1, 1) for sy in (-1, 1)])
        local = (mouth - np.asarray(position)) @ rotation
        corners_covered = bool(np.all(np.abs(local[:, :2]) <= np.array(obj.half_extents[:2]) + .001))
        height_ok = abs(position[2] - (self.RIM_Z + obj.half_extents[2])) < .009
        contacts = p.getContactPoints(obj.body_id, self.objects["box"].body_id,
                                      physicsClientId=self.client)
        supports = [c[6] for c in contacts if c[7][2] > .65 and c[9] > .001]
        spread = np.ptp(np.array(supports), axis=0) if len(supports) >= 2 else np.zeros(3)
        rim_supported = bool(spread[0] > .22 or spread[1] > .18)
        flat = normal_z > .985
        return dict(covered=bool(corners_covered and height_ok and flat and rim_supported
                                 and self.stable(lid_id)),
                    all_mouth_corners_covered=corners_covered, height_ok=bool(height_ok),
                    flat=bool(flat), normal_z=normal_z, rim_supported=rim_supported,
                    support_contact_count=len(supports), stable=self.stable(lid_id))

    def released(self):
        constraints = [p.getConstraintInfo(p.getConstraintUniqueId(i, physicsClientId=self.client),
                                           physicsClientId=self.client)
                       for i in range(p.getNumConstraints(physicsClientId=self.client))]
        robot_constraints = [c for c in constraints if c[0] == self.robot or c[2] == self.robot]
        return self.held_object is None and not robot_constraints

    def render(self, width=640, height=480):
        view = p.computeViewMatrixFromYawPitchRoll((.38, .01, .60), 1.65, 48, -40, 0, 2)
        projection = p.computeProjectionMatrixFOV(48, width / height, .04, 3)
        pixels = p.getCameraImage(width, height, view, projection,
                                  renderer=p.ER_TINY_RENDERER, physicsClientId=self.client)[2]
        rgba = np.asarray(pixels, dtype=np.uint8).reshape(height, width, 4)
        return Image.fromarray(rgba[:, :, :3])

    def save_scene(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.render(960, 720).save(path)

    def close(self):
        if p.isConnected(self.client):
            p.disconnect(self.client)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
