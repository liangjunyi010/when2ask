"""Interactive demo instances on validated Dev layouts; never edits frozen data."""
import copy
import re
from dataclasses import replace

from .study_data import load_study

TEMPLATES = {
    'pack_and_cover': ('Pack and Cover', 'v3_dev_010'),
    'place_into_selected_containers': ('Two Selected Containers', 'v3_dev_026'),
}


def demo_sample(template):
    if template not in TEMPLATES:
        raise ValueError('Unknown task template')
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
    instruction = re.sub(r'For the (?:cup|block|lid|cup_destination), use [A-Za-z0-9_]+\.\s*', '', original.u0).strip()
    for slot in disclosed:
        instruction += f" For the {original.slots[slot]['public_role']}, use {theta[slot]}."
    return replace(original, theta_star=copy.deepcopy(theta), initial_disclosed_slots=disclosed, u0=instruction).validate()


def catalogue():
    return [dict(id=key, name=value[0], source_sample_id=value[1]) for key, value in TEMPLATES.items()]
