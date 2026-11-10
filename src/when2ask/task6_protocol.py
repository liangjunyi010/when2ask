"""Finite public action/question protocol; does not import samples or hidden truth."""
import copy
from dataclasses import dataclass

from .api import SchemaError


def payload(instruction,observation,history):
    return copy.deepcopy(dict(instruction=instruction,observation=observation,history=history))


def known_choices(public):
    known=copy.deepcopy(public['observation']['task']['initial_choices'])
    for event in public['history']:
        if event.get('kind')!='user_answer':continue
        response=event['response'];known.update(response.get('choices',{}))
        for r in response.get('confirmations',[]):
            if r['confirmed']:known[r['role']]=r['candidate_id']
            else:
                values=public['observation']['task']['preference_slots'][r['role']]['candidate_ids']
                if len(values)==2:known[r['role']]=next(k for k in values if k!=r['candidate_id'])
    for inspection in public['observation'].get('inspections',[]):
        if inspection.get('code'):known['inspection_code']=inspection['code']
    return known


def action(value,public):
    if not isinstance(value,dict):raise SchemaError('Action must be a JSON object')
    kind=value.get('kind');obs=public['observation'];aff=obs['affordances']
    if kind=='DONE' and set(value)=={'kind'}:return value
    if kind=='move' and set(value)=={'kind','object_id','target_id'}:
        if value['target_id'] in aff.get('move',{}).get(value['object_id'],[]):return value
    elif kind=='cover' and set(value)=={'kind','object_id'}:
        if value['object_id'] in aff.get('cover',[]):return value
    elif kind=='inspect' and set(value)=={'kind','target_id'}:
        if value['target_id'] in aff.get('inspect',[]):return value
    elif kind=='report' and set(value)=={'kind','code'}:
        if value['code'] in obs['task']['preference_slots'].get('inspection_code',{}).get('candidate_ids',[]):return value
    elif kind=='inspect_station' and set(value)=={'kind','location_id'}:
        if value['location_id'] in aff.get('inspect_station',[]):return value
    elif kind=='return_home' and set(value)=={'kind'} and aff.get('return_home'):return value
    raise SchemaError('Use one public affordance with its exact action schema; no extra keys or hidden IDs')


@dataclass(frozen=True)
class Question:
    type:str
    text:str
    requests:list
    active_roles:tuple

    def roles(self):return set(self.active_roles) if self.type=='all_preferences' else {r['role'] for r in self.requests}
    def to_dict(self):return dict(type=self.type,text=self.text,requests=copy.deepcopy(self.requests))


def question(value,public):
    registry=public['observation']['task']['preference_slots']
    if not isinstance(value,dict) or set(value)!={'type','text','requests'}:raise SchemaError('Question needs only type, text, requests')
    kind,text,requests=value['type'],value['text'],value['requests']
    if kind not in ('select','confirm','all_preferences') or not isinstance(text,str) or not 1<=len(text)<=600 or not isinstance(requests,list):raise SchemaError('Invalid question')
    if (kind=='all_preferences' and requests) or (kind!='all_preferences' and not requests):raise SchemaError('Invalid requested roles')
    seen=set()
    for request in requests:
        if not isinstance(request,dict) or request.get('role') not in registry or request['role'] in seen:raise SchemaError('Use distinct public roles')
        role=request['role'];seen.add(role);candidates=registry[role]['candidate_ids']
        expected={'role','candidate_id'} if kind=='confirm' else {'role','candidate_ids'}
        if set(request)!=expected:raise SchemaError('Invalid request fields')
        if kind=='confirm':
            if request['candidate_id'] not in candidates:raise SchemaError('Unknown candidate')
        elif not isinstance(request['candidate_ids'],list) or set(request['candidate_ids'])!=set(candidates) or len(request['candidate_ids'])!=len(candidates):raise SchemaError('Select must list all public candidates')
    return Question(kind,text,copy.deepcopy(requests),tuple(registry))


def validate_answer(q,public,response):
    registry=public['observation']['task']['preference_slots'];known=known_choices(public)
    if not isinstance(response,dict):raise ValueError('Answer must be structured')
    if q.type=='confirm':
        rows=response.get('confirmations')
        if set(response)!={'confirmations'} or not isinstance(rows,list) or len(rows)!=len(q.requests):raise ValueError('Confirm each requested role')
        expected={(r['role'],r['candidate_id']) for r in q.requests}
        if any(not isinstance(r,dict) or set(r)!={'role','candidate_id','confirmed'} or type(r['confirmed']) is not bool for r in rows):raise ValueError('Invalid confirmation')
        if {(r['role'],r['candidate_id']) for r in rows}!=expected:raise ValueError('Answer only requested candidates')
        if any(r['role'] in known and r['confirmed']!=(known[r['role']]==r['candidate_id']) for r in rows):raise ValueError('Already disclosed choices are fixed')
    else:
        choices=response.get('choices')
        if set(response)!={'choices'} or not isinstance(choices,dict) or set(choices)!=q.roles():raise ValueError('Answer only the requested roles')
        if any(v not in registry[r]['candidate_ids'] for r,v in choices.items()):raise ValueError('Invalid candidate')
        if any(r in known and v!=known[r] for r,v in choices.items()):raise ValueError('Already disclosed choices are fixed')


def names(observation):
    values={k:(v['color']+' '+v['category']+' / '+k) for k,v in observation.get('objects',{}).items()}
    values.update({k:k.replace('_',' ') for k in observation.get('zones',{})})
    from .navigation_map import LOCATIONS
    if observation.get('task',{}).get('template_id')=='patrol_return':values.update({k:v['name'] for k,v in LOCATIONS.items()})
    labels={'2':'2 blocks','3':'3 blocks','alpha':'Label ALPHA','beta':'Label BETA','stored_cup':'Stored cup','stored_block':'Stored block'}
    for slot in observation.get('task',{}).get('preference_slots',{}).values():
        for key in slot['candidate_ids']:
            if key not in values:values[key]=labels.get(key,key.replace('_',' '))
    return values


def scripted_next(public,known_only=False):
    obs=public['observation'];g=obs['task'];kind=g['template_id'];known=known_choices(public)
    def choice(role):return known.get(role) or (None if known_only else sorted(g['preference_slots'][role]['candidate_ids'])[0])
    def move(key,target):return dict(kind='move',object_id=key,target_id=target)
    if kind=='category_sorting':
        targets={'cup':g['cup_bin']};c=choice('block_bin')
        if c:targets.update(block=c,puck=next(k for k in g['other_bins'] if k!=c))
        for key,o in obs['objects'].items():
            if o['category'] in targets and key not in obs['containers'][targets[o['category']]]['contents']:return move(key,targets[o['category']])
        return dict(kind='DONE') if c else None
    if kind=='inventory_restock':
        for role,target,quota in [('cup',g['cup_bin'],g['cup_quota']),('block',g['block_bin'],int(choice('block_quota')) if choice('block_quota') else None)]:
            if quota is None:return None
            if len(obs['containers'][target]['contents'])<quota:
                key=next((k for k,o in obs['objects'].items() if k.startswith('spare_') and o['category']==role and all(k not in c['contents'] for c in obs['containers'].values())),None)
                if key:return move(key,target)
        return dict(kind='DONE')
    if kind=='retrieve_restore':
        c=choice('retrieval_item');inside=obs['containers']['box']['contents'];parked=g['lid'] in obs['zones'][g['lid_pad']]['contents']
        delivered=c and c in obs['zones'][g['delivery_pad']]['contents']
        if delivered:return dict(kind='cover',object_id=g['lid']) if parked else dict(kind='DONE')
        if not parked:return move(g['lid'],g['lid_pad'])
        if not c:return None
        return move(c,g['delivery_pad'])
    if kind=='buffer_exchange':
        a,b=g['item_a'],g['item_b'];left=obs['containers'][g['left']]['contents'];right=obs['containers'][g['right']]['contents']
        if a in right and b in left:return dict(kind='DONE')
        c=choice('buffer_pad')
        if not c:return None
        if a in left:return move(a,c)
        if b in right:return move(b,g['left'])
        return move(a,g['right'])
    if kind=='patrol_return':
        checked=obs['checked_locations'];station=g['required_station']
        if station not in checked:return dict(kind='inspect_station',location_id=station)
        c=choice('extra_station')
        if not c:return None
        if c not in checked:return dict(kind='inspect_station',location_id=c)
        return dict(kind='DONE') if obs['return_events'] and obs['robot_stopped'] else dict(kind='return_home')
    if kind=='occlusion_inspection':
        if g['screen'] not in obs['zones'][g['screen_pad']]['contents']:return move(g['screen'],g['screen_pad'])
        if not obs['inspections'] or not obs['inspections'][-1]['code']:return dict(kind='inspect',target_id=g['inspection_target'])
        code=obs['inspections'][-1]['code']
        return dict(kind='DONE') if obs['reports'] and obs['reports'][-1]['code']==code else dict(kind='report',code=code)
    raise ValueError('Unknown public task')
