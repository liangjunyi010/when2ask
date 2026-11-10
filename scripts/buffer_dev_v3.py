"""Adaptive buffer Dev v3 amendment; shares the v2 120-request/six-episode cap."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

if __name__=='__main__':
    from when2ask import buffer_study_dev_v3 as study
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('command',choices=('plan','probes','episodes'));parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if args.command!='plan' and not args.live:parser.error('Explicit --live required')
    print(json.dumps({'plan':study.amendment,'probes':study.probes,'episodes':study.episodes}[args.command](),indent=2,ensure_ascii=False))
