import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.three_task_data import generate
p=argparse.ArgumentParser();p.add_argument('--revision',default='r1');args=p.parse_args()
rows,audit=generate(args.revision);print(json.dumps(audit,indent=2))
