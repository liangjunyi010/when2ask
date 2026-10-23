"""First acceptance gate: DIRECT dynamics, state, TinyRenderer, disconnect."""
import json
from pathlib import Path

import numpy as np
import pybullet as p
from PIL import Image


def main():
    cid = p.connect(p.DIRECT)
    try:
        p.setGravity(0, 0, -9.81, physicsClientId=cid)
        shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=[.05] * 3, physicsClientId=cid)
        body = p.createMultiBody(1, shape, basePosition=[0, 0, 1], physicsClientId=cid)
        for _ in range(60):
            p.stepSimulation(physicsClientId=cid)
        position = p.getBasePositionAndOrientation(body, physicsClientId=cid)[0]
        assert position[2] < .9, position
        view = p.computeViewMatrix([1, -1, 1], [0, 0, .7], [0, 0, 1])
        projection = p.computeProjectionMatrixFOV(60, 1, .01, 10)
        pixels = p.getCameraImage(160, 160, view, projection,
                                  renderer=p.ER_TINY_RENDERER, physicsClientId=cid)[2]
        frame = np.asarray(pixels, dtype=np.uint8).reshape(160, 160, 4)
        assert np.unique(frame[:, :, :3]).size > 1
        out = Path("outputs/verification")
        out.mkdir(parents=True, exist_ok=True)
        Image.fromarray(frame[:, :, :3]).save(out / "direct_smoke.png")
    finally:
        p.disconnect(cid)
    assert not p.isConnected(cid)
    evidence = dict(mode="DIRECT", steps=60, position=position, tiny_renderer=True,
                    clean_disconnect=True)
    (out / "direct_smoke.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
