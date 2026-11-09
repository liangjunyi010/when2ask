"""Interactive demo instances on validated Dev layouts; never edits frozen data."""
import copy
import re
from dataclasses import replace

from .study_data import load_study

TEMPLATES = {
    'pack_and_cover': ('Pack and Cover', 'v3_dev_010'),
    'place_into_selected_containers': ('Two Selected Containers', 'v3_dev_026'),
    'find_and_approach': ('Three-room Find & Approach', 'navigation_dev_v1'),
}


def demo_sample(template, unknown_preferences=None, navigation_case=None, scenario_id=None):
    if template not in TEMPLATES:
        raise ValueError('Unknown task template')
    if scenario_id is not None:
        from .presentation_scenarios import get_sample
        sample = get_sample(scenario_id)
        if sample is None or sample.template_id != template:
            raise ValueError('Unknown presentation scenario or template mismatch')
        if navigation_case is not None or (unknown_preferences is not None and
                unknown_preferences != 3 - len(sample.initial_disclosed_slots)):
            raise ValueError('A presentation preset has fixed disclosure and no navigation case')
        return sample
    if template == 'find_and_approach':
        from .navigation_task import make_sample
        return make_sample(navigation_case or 'case_b', 1 if unknown_preferences is None else unknown_preferences)
    original = next(s for s in load_study('dev') if s.sample_id == TEMPLATES[template][1])
    scene = original.scene()
    aliases = scene['object_id_map']
    theta = dict(cup_choice=aliases['blue_cup'], block_choice=aliases['green_block'])
    disclosed = ['cup_choice']
    if template == 'pack_and_cover':
        theta['lid_choice'] = aliases['black_lid']
    else:
        theta['cup_destination_choice'] = aliases[scene['containers'][0]['id']]
        disclosed.append('cup_destination_choice')
    if unknown_preferences is not None:
        if type(unknown_preferences) is not int or not 0 <= unknown_preferences <= 3:
            raise ValueError('Unknown preferences must be an integer from 0 to 3')
        order = [s for s in ('cup_choice', 'cup_destination_choice', 'block_choice', 'lid_choice') if s in theta]
        disclosed = order[:len(order) - unknown_preferences]
    instruction = re.sub(r'For the (?:cup|block|lid|cup_destination), use [A-Za-z0-9_]+\.\s*', '', original.u0).strip()
    for slot in disclosed:
        instruction += f" For the {original.slots[slot]['public_role']}, use {theta[slot]}."
    return replace(original, theta_star=copy.deepcopy(theta), initial_disclosed_slots=disclosed, u0=instruction).validate()


def catalogue():
    return [dict(id=key, name=value[0], source_sample_id=value[1]) for key, value in TEMPLATES.items()]
