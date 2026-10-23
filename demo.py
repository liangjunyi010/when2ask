#!/usr/bin/env python3
"""Run a real Panda episode. Activate .venv or use .venv/bin/python directly."""
import argparse
import sys
from pathlib import Path

# Source checkout entry point, independent of editable-install .pth behavior.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from when2ask.runner import run_episode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("ask", "noask"), default="ask")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gui", action="store_true", help="Open the actual PyBullet GUI")
    parser.add_argument("--record", action="store_true", help="Save TinyRenderer frames as demo.gif")
    parser.add_argument("--output-dir", help="Defaults to outputs/{mode}_demo")
    parser.add_argument("--fast", action="store_true", help="Do not pace GUI simulation to wall time")
    parser.add_argument("--require-success", action="store_true", help="Exit 2 if the evaluator returns false")
    args = parser.parse_args()
    episode = run_episode(args.mode, args.seed, args.output_dir, gui=args.gui, record=args.record,
                          realtime=not args.fast)
    evaluation = episode["evaluation"]
    if episode["error"] or evaluation.get("execution_termination") != "done":
        return 1
    return 2 if args.require_success and not evaluation["task_success"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
