"""Generate, validate and evaluate the report benchmark."""
import argparse
import json

from .config import ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    generate = sub.add_parser('generate', help='Synthesize a dataset; optionally validate physics')
    generate.add_argument('--config', default=str(ROOT / 'config/benchmark.json'))
    generate.add_argument('--output', required=True)
    generate.add_argument('--validate-physics', action='store_true')
    inspect = sub.add_parser('inspect', help='Check saved dataset hashes and actual statistics')
    inspect.add_argument('--dataset', required=True)
    run = sub.add_parser('run', help='Evaluate all model/method pairs with an LLM user simulator')
    run.add_argument('--dataset', required=True)
    run.add_argument('--output', required=True)
    run.add_argument('--config', default=str(ROOT / 'config/benchmark.json'))
    run.add_argument('--models', default=str(ROOT / 'config/models.json'))
    run.add_argument('--pricing', required=True)
    run.add_argument('--live', action='store_true')
    report = sub.add_parser('report', help='Recompute tables from complete recorded episodes')
    report.add_argument('--run', required=True)
    report.add_argument('--dataset', required=True)
    sub.add_parser('doctor', help='Check imports without model calls or physics execution')
    args = parser.parse_args(argv)
    if args.command == 'generate':
        from .dag_benchmark import generate
        result = generate(args.config, args.output, validate_physics=args.validate_physics)
    elif args.command == 'inspect':
        from .dag_benchmark import load_dataset
        manifest, _ = load_dataset(args.dataset)
        result = dict(statistics=manifest['statistics'], validation_status=manifest['validation_status'])
    elif args.command == 'run':
        if not args.live:
            parser.error('Live execution requires --live')
        from .dag_evaluation import run
        result = run(args.dataset, args.output, args.config, args.pricing, args.models, live=True)
    elif args.command == 'report':
        from .dag_evaluation import aggregate
        result = aggregate(args.run, args.dataset)
    else:
        import importlib
        import platform
        for module in ('pybullet', 'numpy', 'PIL', 'when2ask.dag_world', 'when2ask.dag_evaluation'):
            importlib.import_module(module)
        result = dict(python=platform.python_version(), dependencies='available', physics_run=False, api_requests=0)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
