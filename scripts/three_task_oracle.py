"""Actual PyBullet oracle, every sample, before any model Test request."""
import argparse,copy,itertools,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pybullet as p
from when2ask.config import ROOT
from when2ask.three_task_data import load
from when2ask.task6_world import make_world
from when2ask.task6_protocol import payload,scripted_next
from when2ask.task6_evaluator import evaluate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='r2');args=parser.parse_args()
    out=ROOT/'outputs/three_task_v8'/('oracle_'+args.revision);out.mkdir(parents=True,exist_ok=False);rows=[]
    for sample in load(args.revision):
        dest=out/sample.sample_id;dest.mkdir();world=None;actions=[];error=None;score=None;start=time.monotonic()
        try:
            world=make_world(sample);initial=world.observation();world.render().save(dest/'scene.png')
            penetration=[dict(a=a,b=b,distance=c[8]) for a,b in itertools.combinations(world.objects,2)
                for c in p.getContactPoints(world.objects[a].body_id,world.objects[b].body_id,physicsClientId=world.client) if c[8]<-.003]
            # The oracle alone is allowed the fixed private preference. It is
            # passed as a public dialogue only to the deterministic oracle policy,
            # never reused as an agent input or online trajectory.
            role=next(iter(sample.slots.values()))['public_role'];truth=next(iter(sample.theta_star.values()))
            history=[dict(kind='user_answer',response=dict(choices={role:truth}))]
            for _ in range(12):
                command=scripted_next(payload(sample.u0,world.observation(),history))
                if command['kind']=='DONE':break
                result=world.execute(command);actions.append(result)
                if not result['success']:break
            score=evaluate(world,sample,actions=actions,termination='independent_offline_oracle')
            if penetration:score['task_success']=False;score['initial_penetrations']=penetration
            world.render().save(dest/'final.png')
            trace=dict(evidence_kind='deterministic_oracle_actual_pybullet_no_model',sample_id=sample.sample_id,group_id=sample.group_id,
                partition=sample.partition,initial_observation=initial,final_observation=world.observation(),initial_penetrations=penetration,
                actions=actions,execution_log=world.events,checkpoints=world.checkpoints,evaluation=score,api_attempts=0)
            (dest/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
        except Exception as exc:
            error=repr(exc);score=dict(task_success=False,conditions={});(dest/'error.json').write_text(json.dumps(dict(error=error,actions=actions))+'\n')
        finally:
            if world:world.close()
        row=dict(sample_id=sample.sample_id,template=sample.template_id,partition=sample.partition,group_id=sample.group_id,
            success=score['task_success'],conditions=score['conditions'],actions=len(actions),error=error,wall_s=time.monotonic()-start)
        rows.append(row);print(json.dumps(row),flush=True)
        (out/'summary.json').write_text(json.dumps(dict(successes=sum(r['success'] for r in rows),total=len(rows),expected_total=36,rows=rows,api_attempts=0),indent=2)+'\n')


if __name__=='__main__':main()
