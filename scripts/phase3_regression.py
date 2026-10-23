"""Read-only Phase 2 regression; all new evidence goes to Phase 3."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from when2ask.benchmark import load_samples
from when2ask.environment import Environment
from when2ask.evaluator import Evaluator
from when2ask.skills import RobotSkills


def historical_hashes():
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "3bc24b2"], cwd=ROOT, text=True)
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in paths.splitlines() if p.startswith(("data/", "scenes/", "outputs/", "docs/phase2/"))}


def main():
    out = ROOT / "outputs/phase3/baseline"
    out.mkdir(parents=True, exist_ok=True)
    before = historical_hashes()
    rows = []
    for split in ("validation", "pilot"):
        for s in load_samples(split):
            with Environment(s.scene_seed, scene_spec=s.scene()) as env:
                skills, actions = RobotSkills(env), []
                for kind, role in (("pick_place", "cup"), ("pick_place", "block"), ("cover", "lid")):
                    actions.append(getattr(skills, kind)(s.theta_star[role + "_choice"], "box").to_dict())
                evaluation = Evaluator().evaluate(env, s.private_spec(), clarification_burden=0,
                                                 actions=actions, termination="regression_completed")
                row = dict(sample_id=s.sample_id, actions=actions, evaluation=evaluation,
                           execution_log=env.events, final_observation=env.snapshot())
                (out / f"{s.sample_id}.json").write_text(json.dumps(row, separators=(",", ":")) + "\n")
                rows.append(dict(sample_id=s.sample_id, success=evaluation["task_success"]))
                print(rows[-1], flush=True)
    assert before == historical_hashes(), "Historical evidence changed"
    result = dict(base_commit="3bc24b2", historical_sha256=before, historical_unchanged=True,
                  successes=sum(r["success"] for r in rows), total=len(rows), runs=rows)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    assert all(r["success"] for r in rows)


if __name__ == "__main__":
    main()
