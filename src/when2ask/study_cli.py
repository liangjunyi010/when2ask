import argparse
import json

from .calibration import create_plan, freeze_data, revalidate_live, run_dev
from .study_data import generate_study
from .study_oracle import run_oracle
from .study_reporting import dev_report, freeze_test
from .study_validation import validate_study


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m when2ask study")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate")
    p.add_argument("--seed", type=int, default=4278)
    p = sub.add_parser("oracle")
    p.add_argument("--partition", choices=("dev", "test"), required=True)
    sub.add_parser("check-data")
    sub.add_parser("freeze-data")
    sub.add_parser("plan")
    p = sub.add_parser("smoke")
    p.add_argument("--live", action="store_true", required=True)
    p = sub.add_parser("dev")
    p.add_argument("--live", action="store_true", required=True)
    p.add_argument("--record-first", action="store_true")
    sub.add_parser("report")
    sub.add_parser("freeze-test")
    args = parser.parse_args(argv)
    if args.command == "generate":
        result = generate_study(seed=args.seed)
    elif args.command == "oracle":
        result = run_oracle(args.partition)
    elif args.command == "check-data":
        result = validate_study()
    elif args.command == "freeze-data":
        result = freeze_data()
    elif args.command == "plan":
        result = create_plan()
    elif args.command == "smoke":
        result = revalidate_live()
    elif args.command == "dev":
        result = run_dev(record_first=args.record_first)
    elif args.command == "report":
        result = dev_report()
    else:
        result = freeze_test()
    # Do not emit entire large manifests or raw HTTP content to the console.
    concise = {k:result[k] for k in ("distribution", "total", "successes", "oracle", "all_passed", "episodes",
                                    "session", "threshold_selection", "status", "gate_threshold") if k in result}
    if args.command == "smoke":
        concise["results"] = {k:{n:v for n,v in r.items() if n != "catalog"} for k,r in result["results"].items()}
    if args.command == "plan":
        concise.update(study_id=result["study_id"], jobs=len(result["jobs"]), global_limits=result["global_limits"])
    print(json.dumps(concise, ensure_ascii=False, indent=2))
    return 0
