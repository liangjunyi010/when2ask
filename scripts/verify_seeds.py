"""Small physics regression sweep, not a research benchmark or measured policy study."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from when2ask.runner import run_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    args = parser.parse_args()
    rows = []
    for mode in ("ask", "noask"):
        for seed in args.seeds:
            out = Path(f"outputs/seed_checks/{mode}_{seed}")
            episode = run_episode(mode, seed, out, quiet=True)
            score = episode["evaluation"]
            row = dict(mode=mode, seed=seed, task_success=score["task_success"],
                       physical_execution_completed=score.get("execution_termination") == "done"
                       and score.get("successful_action_count") == 3,
                       successful_actions=score.get("successful_action_count", 0),
                       clarification_burden=score["clarification_burden"],
                       termination_reason=score["termination_reason"],
                       selected_objects=[a["object_id"] for a in episode["actions"]])
            rows.append(row)
            print(json.dumps(row), flush=True)
    report = dict(purpose="Small fixed-seed physics regression only", runs=rows,
                  physical_completions=sum(r["physical_execution_completed"] for r in rows),
                  total_runs=len(rows))
    target = Path("outputs/verification/seed_summary.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["physical_completions"] == report["total_runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
