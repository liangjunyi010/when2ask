"""Real physical feasibility check. Explicit deterministic oracle, zero API calls."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.task6_spec import TITLES,make_sample
from when2ask.task6_world import make_world
from when2ask.task6_protocol import payload,scripted_next
from when2ask.task6_evaluator import evaluate


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--attempt',required=True);parser.add_argument('--task',choices=TITLES)
    args=parser.parse_args();out=ROOT/'outputs/six_tasks_dev_v1'/('oracle_'+args.attempt)
    out.mkdir(parents=True,exist_ok=False);rows=[]
    for template in ([args.task] if args.task else TITLES):
        sample=make_sample(template,0);dest=out/template;dest.mkdir();world=None;actions=[];error=None
        try:
            world=make_world(sample);initial=world.observation();world.render().save(dest/'scene.png')
            for _ in range(12):
                obs=world.observation();proposed=scripted_next(payload(sample.u0,obs,[]))
                if proposed['kind']=='DONE':break
                result=world.execute(proposed);actions.append(result)
                print(json.dumps(dict(template=template,action=proposed,result=result)),flush=True)
                if not result['success']:break
            result=evaluate(world,sample,actions=actions,termination='offline_physical_oracle')
            world.render().save(dest/'final.png')
            trace=dict(evidence_kind='deterministic_oracle_real_physics',sample_id=sample.sample_id,
                initial_observation=initial,final_observation=world.observation(),actions=actions,
                execution_log=world.events,checkpoints=getattr(world,'checkpoints',None),evaluation=result,api_attempts=0)
            (dest/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
        except Exception as exc:
            error=repr(exc);result=dict(task_success=False,conditions={});print(error,flush=True)
            (dest/'error.json').write_text(json.dumps(dict(error=error,actions=actions))+'\n')
        finally:
            if world:world.close()
        rows.append(dict(template=template,success=result['task_success'],conditions=result['conditions'],error=error))
    summary=dict(successes=sum(r['success'] for r in rows),total=len(rows),rows=rows,api_attempts=0)
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
