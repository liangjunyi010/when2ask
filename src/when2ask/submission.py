"""Commands for the saved evaluation and new benchmark runs."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from .config import ROOT, Config

ARCHIVE = ROOT / 'result/nine_task_metrics_dev_v1'


def verify_archive():
    manifest = json.loads((ROOT / 'result/checksums.json').read_text())
    for name, expected in manifest['files'].items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Saved evidence changed: ' + name)
    return dict(verified_files=len(manifest['files']),
                original_commit=manifest['original_commit'])


def new_output(value):
    path = Path(value).resolve()
    if path == ARCHIVE or ARCHIVE in path.parents:
        raise ValueError('Choose a new directory outside the saved evaluation')
    if path.exists():
        raise FileExistsError('Output directory already exists: ' + str(path))
    path.mkdir(parents=True)
    os.environ['WHEN2ASK_RUN_DIR'] = str(path)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify', help='Verify the saved evidence checksums')
    sub.add_parser('report', help='Recompute tables and figures without API calls')
    sub.add_parser('audit', help='Check saved execution and information boundaries')
    sub.add_parser('doctor', help='Check local dependencies without API calls')
    oracle = sub.add_parser('oracle', help='Run all 27 physical oracle cases offline')
    oracle.add_argument('--output', required=True)
    live = sub.add_parser('run', help='Run a fresh four-method evaluation')
    live.add_argument('--output', required=True)
    live.add_argument('--pricing', required=True, help='JSON prices in the saved pricing format')
    live.add_argument('--live', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'verify':
        result = verify_archive()
    elif args.command in ('report', 'audit'):
        from . import metrics_dev_report
        result = getattr(metrics_dev_report, args.command)(
            source=ARCHIVE, destination=ROOT / 'result/recomputed', archived=True)
        if args.command == 'report':
            result = dict(completed_episodes=result['completed_episodes'],
                          methods=result['methods'], output='result/recomputed')
    elif args.command == 'doctor':
        from .doctor import doctor
        doctor(False, None)
        return 0
    else:
        if args.command == 'run':
            if not args.live:
                parser.error('Live execution requires --live')
            config = Config.load()
            if not config.deepseek_key or not config.typesafe_key:
                parser.error('Set DEEPSEEK_API_KEY and TYPESAFE_API_KEY in .env')
            prices = Path(args.pricing).resolve()
            if not prices.is_file():
                parser.error('Pricing file does not exist')
            json.loads(prices.read_text())
        out = new_output(args.output)
        from . import metrics_dev_study
        result = metrics_dev_study.oracle()
        if result['successes'] != result['total']:
            raise RuntimeError('Physical oracle validation failed')
        if args.command == 'run':
            shutil.copy2(prices, out / 'pricing.json')
            metrics_dev_study.freeze()
            result = metrics_dev_study.run(live=True)
            from .metrics_dev_report import report
            report()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
