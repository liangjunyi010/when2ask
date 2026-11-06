"""Independent Dev experiment; explicit --live is mandatory for model requests."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from when2ask.dev_summary_study import prepare, run, seal

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('command', choices=['prepare', 'seal', 'run', 'report'])
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
if args.command == 'report':
    from when2ask.dev_summary_report import report
    value = report()
else:
    value = prepare() if args.command == 'prepare' else seal() if args.command == 'seal' else run(args.live)
print(json.dumps(value, ensure_ascii=False, indent=2))
