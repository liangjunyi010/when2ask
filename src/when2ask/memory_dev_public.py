"""Dev v6: public observation memory, separate from visibility/affordances.

No Sample, evaluator or oracle imports. Earlier observations must be the actual
public snapshots from this episode, never reconstructed from private world state.
"""
import copy
from .grounded_dev_public import facts as legacy_facts
from .task6_protocol import known_choices

PROFILE='memory_dev_v6'
SUPPORTED=('buffer_exchange','retrieve_restore','occlusion_inspection')
LABEL='Memory Dev v6'


def regions(observation):
    return {key:dict(contents=list(value['contents']),observed=value.get('contents_observed',True))
            for key,value in {**observation['containers'],**observation['zones']}.items()}


def serialize(public,prior_observations=()):
    obs=public['observation'];task=obs['task'];kind=task['template_id']
    if kind not in SUPPORTED:raise ValueError('Memory Dev v6 supports three tabletop Dev tasks only')
    snapshots=[*prior_observations,obs]
    if any(o['task']!=task for o in snapshots):raise ValueError('Observation memory must belong to the same public task')
    if any(a['simulation_step']>b['simulation_step'] for a,b in zip(snapshots,snapshots[1:])):
        raise ValueError('Observation memory must be chronological')
    ids=set(task.get('items',[]))|set(obs['affordances'].get('move',{}))
    for old in snapshots:ids.update(old['affordances'].get('move',{}))
    # Membership published by the region sensor is usable even when the object's
    # individual geometry/grasp affordance is currently suppressed by occlusion.
    memory={};visits={}
    for old in snapshots:
        step=old['simulation_step'];rr=regions(old)
        for key in sorted(ids):
            membership=[r for r,v in rr.items() if key in v['contents']]
            visible=key in old['objects']
            if visible or membership:
                memory[key]=dict(regions=membership,observed_step=step,source='public_region_contents' if membership else 'visible_geometry_unassigned')
                for r in membership:
                    event=visits.setdefault((key,r),dict(object_id=key,region_id=r,first_observed_step=step,last_observed_step=step))
                    event['last_observed_step']=step
            elif key in memory and any(rr[r]['observed'] and key not in rr[r]['contents'] for r in memory[key]['regions'] if r in rr):
                memory.pop(key)  # Direct negative observation overrides old memory.
    current=regions(obs);observed_locations={key:[r for r,v in current.items() if key in v['contents']]
        for key in sorted(ids) if key in obs['objects'] or any(key in v['contents'] for v in current.values())}
    results=[e['result'] for e in public['history'] if e.get('kind')=='action']
    object_memory={}
    for key in sorted(ids):
        last=copy.deepcopy(memory.get(key));status='observed_now' if key in observed_locations else 'remembered_occluded' if last else 'unknown'
        invalidators=[r for r in results if last and r.get('end_step',-1)>last['observed_step'] and
            (r.get('success') is False or (r.get('object_id')==key and r.get('skill') in ('move','cover')))]
        if status=='remembered_occluded' and invalidators:status='unknown_after_action'
        object_memory[key]=dict(status=status,regions=last['regions'] if last and status in ('observed_now','remembered_occluded') else None,
            observed_step=last['observed_step'] if last else None,source=last['source'] if last else None,
            geometry_visible=key in obs['objects'],currently_graspable=key in obs['affordances'].get('move',{}),
            invalidated_after_step=invalidators[-1].get('end_step') if invalidators else None)
    known=known_choices(public);own={}
    for r in results:
        if not r.get('success'):continue
        if kind=='buffer_exchange' and r.get('object_id')==task['item_a'] and r.get('target_id') in task['buffers']:
            own.setdefault('buffer_pad',r['target_id'])
        if kind=='retrieve_restore' and r.get('object_id') in task['items'] and r.get('target_id')==task['delivery_pad']:
            own.setdefault('retrieval_item',r['object_id'])
    # Keep user information distinct from actions under a guess. No truth check.
    working={r:dict(value=v,source='own_successful_action',user_confirmed=False) for r,v in own.items() if r not in known}
    latest={}
    for r in results:
        latest[r.get('object_id')]=dict((k,copy.deepcopy(r.get(k))) for k in ('skill','object_id','target_id','success','reason','start_step','end_step'))
    goal=legacy_facts(public)[2];relations=[]
    if kind=='buffer_exchange':
        for key,target in goal['final_targets'].items():
            relations.append(dict(object_id=key,required_final_region=target,
                currently_observed_at_target=(key in current[target]['contents']) if current[target]['observed'] else None,
                region_contents=copy.deepcopy(current[target]['contents'])))
    lid_geometry=None
    if kind=='retrieve_restore':
        lid=obs['objects'].get(task['lid']);box=obs['containers'][task['box']]
        if lid:
            lo,hi=lid['aabb_min'],lid['aabb_max'];x,y=box['xy'];a,b=box['inner']
            lid_geometry=dict(aabb_spans_opening=lo[0]<=x-a and hi[0]>=x+a and lo[1]<=y-b and hi[1]>=y+b,
                bottom_minus_rim_m=round(lo[2]-box['rim'],5),note='Public AABB measurement only; not evaluator/contact success.')
    value=copy.deepcopy(public)
    last_action=max((i for i,e in enumerate(public['history']) if e.get('kind')=='action'),default=-1)
    value['history']=[copy.deepcopy(e) for i,e in enumerate(public['history']) if e.get('kind')!='action' or i==last_action]
    value['observation']['objects']={key:{k:v for k,v in obj.items() if k in ('category','color','position','aabb_min','aabb_max')}
                                    for key,obj in value['observation']['objects'].items()}
    value['public_summary']=dict(version=PROFILE,current_regions=current,observed_locations=observed_locations,object_memory=object_memory,
        goal_requirements=goal,required_final_relations=relations,lid_geometry=lid_geometry,
        confirmed_choices=known,own_working_choices=working,
        preference_candidates={r:v['candidate_ids'] for r,v in task['preference_slots'].items() if v['kind']=='preference'},
        unresolved_roles=sorted(set(task['preference_slots'])-set(known)),
        observed_region_visits=list(visits.values()),latest_action_by_object=latest,
        action_history_coverage=dict(total=len(results),failed=sum(not r.get('success') for r in results)),
        memory_scope=dict(prior_public_snapshots=len(prior_observations),current_step=obs['simulation_step'],
            note='Memory records past public observations, never fresh sight through a lid. Region sensor membership and current grasp visibility are different. Unknown is not absent. New measured state overrides memory; unseen memories after failed/disturbing actions are invalidated.'),
        limitation='These are public facts, not task scores, an oracle, prescribed actions or a completion verdict. The model must assess the goal; the independent evaluator uses actual final geometry/contact.')
    return value
