"""Unpaid physical policy anchors; configured reply waits are MODELED, not slept."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.nav2_task import Sample
from when2ask.nav2_world import World
from when2ask.nav2_public import payload,evidence,motion_estimate,reference_values


if __name__=='__main__':
    root=Path('outputs/navigation_dev_v2/study_v2');plan=json.loads((root/'plan.json').read_text())
    out=Path('outputs/navigation_dev_v2/references');out.mkdir(exist_ok=False)
    rows=[]
    for batch in plan['episode_batches']:
        sample=Sample(**batch['sample'])
        for policy in ['never_ask','ask_at_start','ask_after_one','nominal_cost_gate']:
            history=[];actions=[];burden=0
            with World(sample) as world:
                for _ in range(12):
                    public=payload(sample.u0,world.observation(),history,sample.public_contract())
                    e=evidence(sample.u0,world.observation(),history,sample.public_contract())
                    if e['completion_observed']:break
                    ask=(policy=='ask_at_start' or policy=='ask_after_one' and len(actions)>=1 or
                        policy=='nominal_cost_gate' and reference_values(public)['decision']=='ASK') and not e['supported_location']
                    if ask:
                        burden+=1
                        question=dict(type='select',text='Where is the knife?',requests=[dict(role='target_location',candidate_ids=list(sample.public_contract()['prior']))])
                        before=world.observation()
                        history.extend([dict(kind='ask',question=question),dict(kind='user_answer',response={'choices':{'target_location':sample.target_location}})])
                        assert world.observation()==before
                        continue
                    options=[k for k,w in e['posterior_from_public_facts'].items() if w>0]
                    location=e['supported_location'] or max(options,key=lambda k:e['posterior_from_public_facts'][k]/motion_estimate(world.pose(),k,sample.public_contract()))
                    result=world.search(location);actions.append(result);history.append(dict(kind='action',result=result))
                evaluation=world.evaluate(burden,actions,'scripted_reference_done')
                motion=(world.step_count-240)*world.DT
                row=dict(sample=sample.sample_id,policy=policy,success=evaluation['task_success'],burden=burden,
                    distance_m=world.distance_m,motion_sim_s=motion,modeled_reply_s=sample.answer_delay_s*burden,
                    modeled_operational_s=motion+(sample.answer_delay_s+5)*burden,
                    evidence_kind='unpaid_scripted_policy_real_pybullet_with_modeled_reply_cost',
                    actual_reply_wait_performed=False,actions=actions,public_history=history,evaluation=evaluation)
                rows.append(row)
    (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('sample','policy','success','burden','motion_sim_s','modeled_operational_s')} for r in rows],indent=2))
