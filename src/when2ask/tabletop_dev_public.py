"""Opt-in Dev public facts for the two tabletop tasks; no private data inputs."""
import copy
import re

from .protocol import public_payload
from .study_protocol import disclosed_choices, public_roles, role_candidates

VERSION = 'tabletop_contract_dev_v1'


def public_order(instruction, two_containers):
    """Parse only the existing controlled PUBLIC instruction grammar.

    No sample/DAG registry, preference truth, evaluator or oracle is imported.
    Unsupported/ambiguous order is an error, never silently treated as independent.
    """
    text=instruction.lower()
    markers={
        'block_first':'place the block before the cup.',
        'cup_first':'place the cup before the block.',
        'independent':'either object may be placed first.'}
    found=[key for key,phrase in markers.items() if phrase in text]
    if len(found)!=1:raise ValueError('Dev public-order parser needs one explicit controlled precedence sentence')
    edges=[] if two_containers else [['place_cup','cover'],['place_block','cover']]
    if found[0]!='independent':edges.append(['place_block','place_cup'] if found[0]=='block_first' else ['place_cup','place_block'])
    return dict(order=found[0],nodes=['place_cup','place_block']+([] if two_containers else ['cover']),edges=edges,
        provenance='Explicit user instruction and public task contract, not a private DAG annotation')


def facts_payload(state):
    base=public_payload(state);roles=public_roles(state);two='cup_destination' in roles
    known=disclosed_choices(state)
    objects=state.observation['objects']
    containers=[k for k,v in objects.items() if v['category']=='container']
    working={};sources={}
    # Successful observed actions can stabilize the planner's OWN earlier guesses.
    # They never become user-confirmed preferences or resolve an unknown role.
    for event in state.history:
        if event.get('kind')!='action':continue
        r=event.get('result',{});key=r.get('object_id');target=r.get('target_id')
        if not r.get('success') or key not in objects:continue
        role=objects[key]['category']
        if role in ('cup','block','lid') and role in roles and target in containers:
            working.setdefault(role,key)
        if two and target in containers:
            if role=='cup':working.setdefault('cup_destination',target)
            elif role=='block':working.setdefault('cup_destination',next(c for c in containers if c!=target))
    initial=dict(re.findall(r'For the (cup|block|lid|cup_destination), use ([A-Za-z0-9_]+)',state.instruction))
    for role in roles:
        if role in known:sources[role]='initial_instruction' if initial.get(role)==known[role] else 'public_answer_or_binary_deduction'
    choices={r:known.get(r,working.get(r)) for r in roles}
    destinations={}
    if two:
        dest=choices['cup_destination']
        if dest in containers:
            destinations={'cup':dest,'block':next(c for c in containers if c!=dest)}
    else:destinations={'cup':containers[0],'block':containers[0],'lid':containers[0]}
    value=copy.deepcopy(base)
    value['observation']['objects']=[{k:v for k,v in o.items() if k in ('object_id','category','color')}
                                      for o in base['observation']['objects']]
    value['public_facts']=dict(version=VERSION,task_type='two_containers' if two else 'pack_and_cover',
        order=public_order(state.instruction,two),
        role_candidates={r:role_candidates(state,r) for r in roles},
        confirmed_choices=known,confirmed_choice_sources=sources,
        unresolved_roles=[r for r in roles if r not in known],
        own_unconfirmed_choices={r:dict(value=v,source='own_successful_action',user_confirmed=False)
                                 for r,v in working.items() if r not in known},
        working_selection=choices,working_destinations=destinations,
        destination_provenance='Known cup_destination implies the block uses the OTHER container; otherwise an own working guess. Never hidden truth.',
        public_labels={k:v['color']+' '+v['category'] for k,v in objects.items()},
        observation_scope='Current measured containment/coverage and full public history. Actions and guesses are not preference disclosures.',
        constraints=dict(unselected_outside_all_containers=True,release_everything=True),
        limitation='Facts and stated final relations only: no Gate decision, next action, task score, completion verdict, private registry or oracle trajectory.')
    return value
