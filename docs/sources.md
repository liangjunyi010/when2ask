# Background and third-party assets

- The local `When2Ask_3min_6slides.pptx` was found under the existing CS5478 Robot
  course folder and read without modification. It motivates public/private intent
  separation, ASK/CONTINUE gating, shared robot skills, and slot-based burden.
  The original presentation is not copied into this repository.
- [Bullet / PyBullet](https://github.com/bulletphysics/bullet3), version 3.2.7
  from [PyPI](https://pypi.org/project/pybullet/3.2.7/), supplies the physics engine,
  TinyRenderer, `plane.urdf`, and Franka Panda model through `pybullet_data`.
  Bullet uses the zlib license. The installed Panda asset includes its own
  Apache-2.0 `franka_panda/LICENSE.txt`, which is authoritative for that asset.
- [Official Panda example](https://github.com/bulletphysics/bullet3/blob/master/examples/pybullet/gym/pybullet_robots/panda/panda_sim.py)
  documents the Panda joint and end-effector convention. Project controller code
  is written here; no tutorial controller or third-party meshes are vendored.
- All cups, blocks, lids and the hollow box are generated with native Bullet
  collision/visual shapes. No outside textures or mesh assets are downloaded.
- No code or assets from NUS-LinS-Lab/PyBullet-Tutorial are used.

The setup script's `fdopen` build macro works around the legacy bundled zlib
`#if defined(MACOS) || defined(TARGET_OS_MAC)` branch; it does not alter PyBullet's
physics or runtime behavior. The SDK override changes only that build process.
