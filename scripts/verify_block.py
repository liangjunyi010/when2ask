"""Second acceptance gate: a real motor-driven Panda transfers one block."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from when2ask.environment import Environment
from when2ask.skills import RobotSkills


def main():
    out = Path("outputs/verification")
    out.mkdir(parents=True, exist_ok=True)
    with Environment(minimal=True) as env:
        before = env.snapshot()
        env.save_scene(out / "block_before.png")
        result = RobotSkills(env).pick_place("green_block", "table", relation="on")
        env.save_scene(out / "block_after.png")
        evidence = dict(result=result.to_dict(), before=before, after=env.snapshot(), events=env.events)
        (out / "block_pick_place.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
        assert result.success, result.reason


if __name__ == "__main__":
    main()
