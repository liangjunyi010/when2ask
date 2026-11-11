import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.three_task_benchmark import freeze,run_all

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run']);p.add_argument('--revision',default='r2');p.add_argument('--live',action='store_true');a=p.parse_args()
 if a.command=='freeze':
  result=freeze(a.revision);print(json.dumps({k:result[k] for k in ['experiment_id','code_commit','global_limits','per_episode_limits','audit']},indent=2))
 else:run_all(a.live)
if __name__=='__main__':main()
