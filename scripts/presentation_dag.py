"""Independent presentation scenario CLI; online calls require --live."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main():
    from when2ask import presentation_scenarios as data, presentation_study as study
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("command", choices=("generate", "validate", "oracle", "plan", "run", "report"))
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workers", type=int, default=3, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.command == "run" and not args.live:
        parser.error("Real model execution requires explicit --live")
    actions = {"generate": data.generate, "validate": data.validate, "oracle": lambda: study.oracle(args.workers),
               "plan": study.preregister, "run": lambda: study.run_live(args.workers), "report": study.report}
    print(json.dumps(actions[args.command](), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
