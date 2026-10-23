import itertools

import numpy as np
import pybullet as p

from when2ask.environment import Environment


def test_direct_dynamics_render_and_disconnect():
    with Environment(minimal=True) as env:
        cid = env.client
        initial = env.step_count
        env.step(12)
        assert env.step_count == initial + 12
        frame = np.asarray(env.render(160, 120))
        assert frame.shape == (120, 160, 3)
        assert np.unique(frame.reshape(-1, 3), axis=0).shape[0] > 10
        assert env.body_pose("green_block")[0][2] > env.TABLE_Z
    assert not p.isConnected(cid)


def test_stable_ids_and_real_hollow_geometry(env):
    assert set(env.objects) == {"box", "red_cup", "blue_cup", "green_block", "yellow_block",
                                 "black_lid", "white_lid"}
    box = env.objects["box"].body_id
    assert len(p.getCollisionShapeData(box, -1, physicsClientId=env.client)) == 5
    hit = p.rayTest([*env.BOX_XY, env.RIM_Z + .02],
                    [*env.BOX_XY, env.TABLE_Z - .01], physicsClientId=env.client)[0]
    assert hit[0] == box
    assert abs(hit[3][2] - env.FLOOR_Z) < .002  # Ray passes through the empty opening.
    for cup in ("red_cup", "blue_cup"):
        assert len(p.getCollisionShapeData(env.objects[cup].body_id, -1,
                                           physicsClientId=env.client)) == 13
        x, y, z = env.body_pose(cup)[0]
        hit = p.rayTest([x, y, z + .1], [x, y, env.TABLE_Z], physicsClientId=env.client)[0]
        assert hit[0] == env.objects[cup].body_id
        assert hit[3][2] < z - .02  # Open cup, not a filled cylinder.


def test_no_initial_inter_object_penetrations(env):
    for a, b in itertools.combinations(env.objects.values(), 2):
        contacts = p.getClosestPoints(a.body_id, b.body_id, 0, physicsClientId=env.client)
        assert all(c[8] >= -.001 for c in contacts), (a.object_id, b.object_id)


def test_seed_reproduces_physics():
    with Environment(seed=7) as a, Environment(seed=7) as b:
        snapshot = a.snapshot()
        assert snapshot == b.snapshot()
    with Environment(seed=8) as c:
        assert c.snapshot()["objects"]["blue_cup"]["position"] != snapshot["objects"]["blue_cup"]["position"]
        # Seed affects only the source layout, not object identities or private intent.
        assert set(c.objects) == set(a.objects)
