"""Independent tabletop Dev CLI; defaults and frozen Test are untouched."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('command',choices=['generate','forensics','oracle','freeze','probes','run','report'])
    p.add_argument('--live',action='store_true');args=p.parse_args()
    from when2ask import tabletop_dev_study as study
    if args.command=='generate':result=study.generate()
    elif args.command=='forensics':result=study.forensic()
    elif args.command=='oracle':result=study.oracle_and_states()
    elif args.command=='freeze':result=study.freeze()
    elif args.command in ('probes','run'):result=study.run('probes' if args.command=='probes' else 'episodes',args.live)
    else:
        from when2ask.tabletop_dev_report import report
        result=report()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
