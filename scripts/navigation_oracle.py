"""No paid API calls. Real physics regression, including autonomous exhaustive search."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.navigation_agents import ScriptedGate, ScriptedPlanner
from when2ask.navigation_protocol import auto_answer, public_payload
from when2ask.navigation_task import SCENARIOS, make_sample
from when2ask.navigation_world import NavigationWorld


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'summary.json').exists():raise ValueError('Use a new output directory; oracle evidence is append-only')
    rows=[]
    for case in SCENARIOS:
        for method in ('known_location_oracle','scripted_noask','scripted_ask'):
            sample=make_sample(case,0 if method=='known_location_oracle' else 1)
            history=[];actions=[];turns=[];burden=0;termination='round_limit'
            with NavigationWorld(sample) as world:
                path=output/f'{case}__{method}';path.mkdir()
                world.render().save(path/'scene.png')
                for round_index in range(20):
                    payload=public_payload(sample.u0,world.observation(),history)
                    gate=ScriptedGate().decide(payload) if method=='scripted_ask' else None
                    turn=dict(round=round_index,public_payload=payload,decision=gate.decision if gate else 'CONTINUE')
                    turns.append(turn)
                    if gate and gate.decision=='ASK':
                        before=world.observation();question=ScriptedPlanner().generate_question(payload);answer=auto_answer(sample)
                        history.extend([dict(kind='ask',question=question),dict(kind='user_answer',response=answer)])
                        burden+=1;turn.update(question=question,answer=answer,physics_unchanged=before==world.observation())
                        continue
                    action=ScriptedPlanner().generate_action(payload);turn['action']=action
                    if action['kind']=='DONE':termination='done';break
                    if len(actions)>=8:termination='robot_action_limit';break
                    result=world.search(action['location_id']);actions.append(result);history.append(dict(kind='action',result=result))
                evaluation=world.evaluate(burden,actions,termination)
                world.render().save(path/'final.png')
                record=dict(case=case,method=method,group_id=sample.group_id,scene_seed=sample.scene_seed,
                    evidence_kind='scripted_policy_real_pybullet',evaluation=evaluation,turns=turns,actions=actions,execution_log=world.events)
                (path/'episode.json').write_text(json.dumps(record,indent=2)+'\n')
                rows.append(dict(case=case,method=method,success=evaluation['task_success'],burden=burden,
                    distance_m=world.distance_m,actions=len(actions),physical_actions_successful=all(a['success'] for a in actions)))
                print(json.dumps(rows[-1]),flush=True)
    summary=dict(layout_groups=1,placement_cases=3,rows=rows,successes=sum(r['success'] for r in rows),episodes=len(rows))
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',default='outputs/navigation_dev_v1/oracle')
    run(parser.parse_args().output_dir)
