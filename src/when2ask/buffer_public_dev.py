"""Independent Dev v2: transparent summaries from PUBLIC observations/history.

No sample, hidden choice, evaluator, oracle or next-action generator is imported.
The raw public state is retained. This is redundant grounding, not action masking.
"""
import copy
from collections import Counter

VERSION='buffer_public_summary_dev_v2'


def augment(public):
    value=copy.deepcopy(public)
    observation=value['observation'];task=observation['task']
    if task['template_id']!='buffer_exchange':raise ValueError('This Dev study targets buffered exchange only')
    regions={**{k:list(v['contents']) for k,v in observation['containers'].items()},
             **{k:list(v['contents']) for k,v in observation['zones'].items()}}
    locations={key:[region for region,items in regions.items() if key in items]
               for key in (task['item_a'],task['item_b'])}
    # These destinations are implied by the PUBLIC exchange instruction. They
    # do not depend on the user's unknown buffer-pad preference.
    targets={task['item_a']:task['right'],task['item_b']:task['left']}
    relations=[dict(object_id=key,target_id=target,currently_inside=key in regions[target])
               for key,target in targets.items()]
    confirmed=copy.deepcopy(task['initial_choices']);history=[];parking=[]
    for event in value['history']:
        if event.get('kind')=='user_answer':
            response=event['response'];confirmed.update(response.get('choices',{}))
            for row in response.get('confirmations',[]):
                if row['confirmed']:confirmed[row['role']]=row['candidate_id']
                else:
                    candidates=task['preference_slots'][row['role']]['candidate_ids']
                    if len(candidates)==2:confirmed[row['role']]=next(k for k in candidates if k!=row['candidate_id'])
        elif event.get('kind')=='action':
            result=event['result']
            row={key:result.get(key) for key in ('skill','object_id','target_id','success','reason','start_step','end_step')}
            history.append(row)
            if (result.get('success') is True and result.get('object_id')==task['item_a']
                    and result.get('target_id') in task['buffers']):
                parking.append(dict(buffer_id=result['target_id'],observed_result_step=result.get('end_step')))
    counts=Counter((r['object_id'],r['target_id']) for r in history)
    # Keep an assumption visibly separate from a user answer. Successful past
    # parking is historical evidence; current measured location remains authoritative.
    assumption=(dict(value=parking[0]['buffer_id'],source='own_first_successful_parking',user_confirmed=False)
                if parking and 'buffer_pad' not in confirmed else None)
    value['public_summary']=dict(version=VERSION,
        interpretation='Instruction states INITIAL object locations; current observation states where objects are NOW. IDs do not change when objects move.',
        current_regions=regions,object_locations=locations,
        explicit_final_relations=relations,holding=observation['held_object'],
        single_capacity_slots=[task['left'],task['right']],
        confirmed_user_choices=confirmed,
        unresolved_user_roles=sorted(set(task['preference_slots'])-set(confirmed)),
        prior_successful_parking=parking,agent_buffer_assumption=assumption,
        chronological_action_results=history,
        repeated_commands=[dict(object_id=k[0],target_id=k[1],attempts=n) for k,n in counts.items() if n>1],
        caution='A failed action can still move objects. Use the latest measured regions, not historical successes, as the current state.')
    return value


def diagnose_action(public,proposed):
    """Post-hoc public checks, never used to rewrite or reject an action."""
    task=public['observation']['task'];obs=public['observation']
    regions={**{k:v['contents'] for k,v in obs['containers'].items()},**{k:v['contents'] for k,v in obs['zones'].items()}}
    targets={task['item_a']:task['right'],task['item_b']:task['left']}
    if proposed is None:return dict(assessment_available=False)
    move=proposed.get('kind')=='move';key=proposed.get('object_id');target=proposed.get('target_id')
    completed=key in targets and key in regions[targets[key]]
    occupied=target in (task['left'],task['right']) and any(k!=key for k in regions.get(target,[]))
    return dict(assessment_available=True,
        undoes_currently_satisfied_final_relation=bool(move and completed and target!=targets[key]),
        targets_occupied_single_capacity_slot=bool(move and occupied),
        repeats_current_placement=bool(move and key in regions.get(target,[])),
        done_before_visible_swap_complete=bool(proposed.get('kind')=='DONE' and not all(k in regions[v] for k,v in targets.items())))
