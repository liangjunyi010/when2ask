import argparse
import json
from pathlib import Path

from .accounting import Limits, SessionLedger
from .benchmark import find_sample, generate, oracle_validate
from .config import ROOT
from .doctor import doctor
from .reporting import report
from .research_runner import METHODS, run_sample


def main():
    parser = argparse.ArgumentParser(prog="python -m when2ask")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("doctor")
    p.add_argument("--live", action="store_true")
    p.add_argument("--session-dir")
    p = sub.add_parser("generate")
    p.add_argument("--split", choices=("pilot", "validation"), default="pilot")
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)
    p = sub.add_parser("validate")
    p.add_argument("--split", choices=("pilot", "validation"), default="pilot")
    p.add_argument("--oracle", action="store_true", required=True)
    p = sub.add_parser("run")
    p.add_argument("--sample", required=True)
    p.add_argument("--method", choices=METHODS, required=True)
    p.add_argument("--live", action="store_true", required=True)
    p.add_argument("--output-dir")
    p.add_argument("--session-dir", default=str(ROOT / "outputs/phase2_live"))
    p.add_argument("--record", action="store_true")
    p.add_argument("--gui", action="store_true")
    for name, default in vars(Limits()).items():
        p.add_argument("--" + name.replace("_", "-"), type=int, default=default)
    p = sub.add_parser("report")
    p.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    if args.command == "doctor":
        doctor(args.live, args.session_dir)
    elif args.command == "generate":
        samples = generate(args.split, args.count, args.seed)
        print(json.dumps(dict(split=args.split, samples=len(samples), seed=args.seed)))
    elif args.command == "validate":
        result = oracle_validate(args.split)
        return 0 if result["successes"] == result["total"] else 1
    elif args.command == "run":
        limits = Limits(**{name: getattr(args, name) for name in vars(Limits())})
        run_sample(find_sample(args.sample), args.method, args.output_dir, live=args.live,
                   session=SessionLedger(Path(args.session_dir)), limits=limits, record=args.record, gui=args.gui)
    elif args.command == "report":
        report(args.run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
