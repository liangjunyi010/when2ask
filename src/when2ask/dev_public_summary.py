"""Experimental public projections. No samples, private registry or evaluator input."""
import copy
import hashlib
import json

from .protocol import public_payload
from .study_protocol import disclosed_choices, public_roles, role_candidates

SUMMARY_VERSION = 'public_facts_v1'
PROFILES = ('v3_original', 'compact_state', 'compact_question')


def encode(state, profile):
    if profile not in PROFILES:
        raise ValueError('Unknown independent Dev profile')
    original = public_payload(state)
    if profile == 'v3_original':
        return original
    known = disclosed_choices(state)
    objects = state.observation['objects']
    preferences = {}
    for role in public_roles(state):
        entry = dict(disclosure='known' if role in known else 'not_disclosed',
            candidates=[dict(object_id=k, category=objects[k]['category'], color=objects[k]['color'])
                        for k in role_candidates(state, role)])
        if role in known:
            entry['disclosed_object_id'] = known[role]
        preferences[role] = entry
    quotes = [s for s in ('Place the cup before the block.', 'Place the block before the cup.',
                         'Either object may be placed first.') if s in state.instruction]
    # These are observed contents, not correctness/completion labels. In
    # particular a physically placed guess does NOT become a disclosed choice.
    history = []
    for event in state.history:
        if event['kind'] == 'action':
            result = event['result']
            history.append(dict(kind='physical_skill_result', skill=result['skill'],
                object_id=result['object_id'], target_id=result['target_id'],
                physical_execution_succeeded=result['success']))
        elif event['kind'] in ('ask', 'user_answer'):
            history.append(copy.deepcopy(event))
    return dict(instruction=state.instruction,
        public_summary=dict(version=SUMMARY_VERSION, preference_disclosures=preferences, public_order_quotes=quotes),
        observation=dict(objects=[dict(object_id=k, category=v['category'], color=v['color']) for k,v in objects.items()],
            held_object=state.observation['held_object'],
            spatial_relations=copy.deepcopy(state.observation['spatial_relations'])),
        history=history,
        interpretation='Physical execution success describes motion only; it does not disclose a user preference.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
