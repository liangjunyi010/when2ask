"""Third gate: fixed physical pack/cover, before introducing agent/QA code."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from when2ask.environment import Environment
from when2ask.skills import RobotSkills


def main():
    out = Path("outputs/verification")
    with Environment(seed=0) as env:
        env.save_scene(out / "pack_before.png")
        skills = RobotSkills(env)
        results = []
        for skill, key in [("pick_place", "blue_cup"), ("pick_place", "green_block"),
                           ("cover", "black_lid")]:
            result = getattr(skills, skill)(key, "box")
            print(result.to_dict(), flush=True)
            results.append(result.to_dict())
            env.save_scene(out / f"after_{key}.png")
            if not result.success:
                break
        details = dict(cup=env.containment("blue_cup"), block=env.containment("green_block"),
                       lid=env.coverage("black_lid"))
        print(details, flush=True)
        (out / "pack_fixed.json").write_text(json.dumps(dict(results=results, details=details,
                events=env.events, final_state=env.snapshot()), indent=2) + "\n")
        assert len(results) == 3 and all(r["success"] for r in results)


if __name__ == "__main__":
    main()
