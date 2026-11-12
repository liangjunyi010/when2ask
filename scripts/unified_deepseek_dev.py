"""Opt-in paired unified DeepSeek Dev study; zero implicit paid requests."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('command',choices=['prepare','oracle','freeze','run','report','audit'])
    p.add_argument('--live',action='store_true')
    args=p.parse_args()
    from when2ask import unified_dev_study as study
    if args.command=='run':result=study.run(args.live)
    elif args.command in ('report','audit'):
        from when2ask import unified_dev_report
        result=getattr(unified_dev_report,args.command)()
    else:result=getattr(study,args.command)()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
