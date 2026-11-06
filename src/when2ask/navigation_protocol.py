"""Public navigation contract, shared by all methods; no private world registry."""
import copy
import re

from .api import SchemaError
from .navigation_map import LOCATIONS


def location_claim(instruction, history):
    match = re.search(r'target_location=([a-z_]+)', instruction)
    known = match[1] if match and match[1] in LOCATIONS else None
    for item in history:
        if item.get('kind') == 'user_answer':
            value = item.get('response', {}).get('choices', {}).get('target_location')
            if value in LOCATIONS:
                known = value
    return known


def public_payload(instruction, observation, history):
    """Explicit allowlist. No case/sample ID, private target, or evaluator labels."""
    fields = ('simulation_step', 'robot_pose', 'current_room', 'known_map', 'checked_locations',
              'target_observation', 'target_visible_now', 'distance_to_observed_target_m',
              'robot_stopped', 'distance_travelled_m', 'route_distances_m')
    measured = {k: copy.deepcopy(observation[k]) for k in fields}
    return dict(instruction=instruction, observation=measured, public_history=copy.deepcopy(history),
        location_claim=location_claim(instruction, history),
        interaction_contract=dict(auto_answer_delay_s=3, location_hint_requests_count_as_one_slot=True,
            user_claim_is_not_detection=True, robot_time_advances_only_during_actions=True,
            target_static=True, sensor='geometric range/FOV/ray LOS; not learned computer vision'))


def parse_action(value):
    if value == {'kind': 'DONE'}:
        return value
    if (isinstance(value, dict) and set(value) == {'kind', 'location_id'}
            and value['kind'] == 'search' and value['location_id'] in LOCATIONS):
        return value
    raise SchemaError('Action JSON must be {kind:DONE} or {kind:search,location_id:known station ID}')


def parse_question(value):
    if not isinstance(value, dict) or set(value) != {'type', 'text', 'requests'}:
        raise SchemaError('Question requires only type, text, requests')
    if not isinstance(value['text'], str) or not 1 <= len(value['text']) <= 400:
        raise SchemaError('Question needs a short nonempty text')
    expected = dict(role='target_location', candidate_ids=list(LOCATIONS))
    if value['type'] != 'select' or value['requests'] != [expected]:
        raise SchemaError('Select exactly one target_location role, listing all six station IDs in map order')
    return value


def validate_answer(response):
    if (not isinstance(response, dict) or set(response) != {'choices'}
            or not isinstance(response['choices'], dict) or set(response['choices']) != {'target_location'}
            or response['choices']['target_location'] not in LOCATIONS):
        raise ValueError('Answer must choose one known target_location station')


def auto_answer(sample):
    # Private resolver used only after an explicit location request, never by models.
    return {'choices': {'target_location': sample.target_location}}


def goal_observed(payload):
    obs = payload['observation']
    return (obs['target_observation'] is not None and obs['distance_to_observed_target_m'] <= 1.2
            and obs['robot_stopped'])
