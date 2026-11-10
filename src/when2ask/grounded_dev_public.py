"""Optional Dev v5 grounding; only public input is accepted, never a Sample."""
import copy
from collections import Counter
from .task6_protocol import known_choices

PROFILE='grounded_dev_v5'
DEFAULT='default_v1'
SUPPORTED=('buffer_exchange','retrieve_restore','occlusion_inspection')
LABEL='Grounded Dev v5'


def facts(public):
    obs=public['observation'];task=obs['task'];kind=task['template_id']
    if kind not in SUPPORTED:raise ValueError('Grounded Dev v5 supports exchange, retrieval and occlusion only')
    regions={k:list(v['contents']) for k,v in {**obs['containers'],**obs['zones']}.items()}
    objects=obs['affordances'].get('move',{})
    locations={key:[r for r,items in regions.items() if key in items] for key in objects}
    if kind=='buffer_exchange':
        goal=dict(final_targets={task['item_a']:task['right'],task['item_b']:task['left']},
                  buffer_candidates=list(task['buffers']),buffers_empty_at_end=True)
    elif kind=='retrieve_restore':
        goal={k:copy.deepcopy(task[k]) for k in ('box','lid','lid_pad','delivery_pad','items')}
        goal.update(other_item_remains_inside=True,restore_lid_after_delivery=True)
    else:
        goal={k:copy.deepcopy(task[k]) for k in ('screen','screen_pad','inspection_target')}
        goal.update(physical_inspection_before_report=True,report_measured_code=True)
    return regions,locations,goal


def serialize(public):
    regions,locations,goal=facts(public);value=copy.deepcopy(public);obs=value['observation'];task=obs['task']
    history=public['history'];last=max((i for i,e in enumerate(history) if e.get('kind')=='action'),default=-1)
    results=[e['result'] for e in history if e.get('kind')=='action']
    value['history']=[copy.deepcopy(e) for i,e in enumerate(history) if e.get('kind')!='action' or i==last]
    # Geometry stays public. All user dialogue and the latest result keep their
    # original chronological order. The controller saves the full raw payload.
    obs['objects']={key:{k:v for k,v in obj.items() if k in ('category','color','position','aabb_min','aabb_max')}
                    for key,obj in obs['objects'].items()}
    counts=Counter((r.get('object_id'),r.get('target_id'),r.get('skill')) for r in results)
    known=known_choices(public)
    parking=[r['target_id'] for r in results if r.get('success') and r.get('object_id')==task.get('item_a') and r.get('target_id') in task.get('buffers',[])]
    lid=obs['objects'].get(task.get('lid'));box=obs['containers'].get(task.get('box'))
    lid_geometry=None
    if lid and box:
        lo,hi=lid['aabb_min'],lid['aabb_max'];x,y=box['xy'];a,b=box['inner']
        lid_geometry=dict(aabb_spans_opening=lo[0]<=x-a and hi[0]>=x+a and lo[1]<=y-b and hi[1]>=y+b,
                          bottom_minus_rim_m=round(lo[2]-box['rim'],5),
                          note='AABB geometry only; no evaluator/contact success claim.')
    value['public_summary']=dict(version=PROFILE,current_regions=regions,current_locations=locations,goal_requirements=goal,
        contents_observed={k:v.get('contents_observed',True) for k,v in obs['containers'].items()},
        unobserved_public_item_ids=[k for k in task.get('items',[]) if k not in obs['objects']],
        preference_candidates={r:v['candidate_ids'] for r,v in task['preference_slots'].items() if v['kind']=='preference'},
        world_fact_roles=[r for r,v in task['preference_slots'].items() if v['kind']=='world_fact'],
        confirmed_choices=known,unresolved_roles=sorted(set(task['preference_slots'])-set(known)),
        own_working_buffer=(dict(value=parking[0],user_confirmed=False) if parking and 'buffer_pad' not in known else None),
        lid_geometry=lid_geometry,
        action_history_coverage=dict(total=len(results),failed=sum(not r.get('success') for r in results),latest=results[-1] if results else None),
        repeated_commands=[dict(object_id=k[0],target_id=k[1],skill=k[2],attempts=n) for k,n in counts.items() if n>1],
        caution='Unknown or occluded is not absent. Region membership is measured, not an oracle. Failed actions can change geometry. Own choices are not user answers; current observation overrides old action outcomes.')
    return value
