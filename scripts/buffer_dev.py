"""Independent buffer Dev v2; real calls require --live; no frozen file updates."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


if __name__=='__main__':
    from when2ask import buffer_study_dev as study
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=('analyze','plan','probes','episodes'));parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if args.command in ('probes','episodes') and not args.live:parser.error('Explicit --live required')
    result={'analyze':study.analyze,'plan':study.preregister,'probes':study.probes,'episodes':study.episodes}[args.command]()
    print(json.dumps(result,indent=2,ensure_ascii=False))
