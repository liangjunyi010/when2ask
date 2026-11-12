"""Independent nine-task pilot CLI. Online operations always require --live."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))

def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('command',choices=['generate','oracle','freeze','smoke','run','report'])
    p.add_argument('--live',action='store_true');a=p.parse_args()
    from when2ask import nine_task_data as data,nine_task_benchmark as bench
    if a.command=='generate':result=data.generate()
    elif a.command=='oracle':result=bench.run_oracle()
    elif a.command=='freeze':result=bench.freeze()
    elif a.command=='smoke':result=bench.run_all(a.live,smoke=True)
    elif a.command=='run':result=bench.run_all(a.live)
    else:
        from when2ask.nine_task_report import report
        result=report()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
