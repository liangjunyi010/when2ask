"""Private fixed world facts. Only controller simulator/worker/evaluator use them."""
import json
from dataclasses import dataclass

from .config import ROOT
from .navigation_map import LOCATIONS, TEMPLATE, public_map

SCENARIOS = ('case_a','case_b','case_c')


@dataclass(frozen=True)
class NavigationSample:
    case_id: str
    target_location: str
    disclosed: bool = False
    scene_seed: int = 0
    template_id: str = TEMPLATE
    partition: str = 'dev'
    group_id: str = 'three_room_map_v1'

    @property
    def sample_id(self):
        return 'nav_dev_v1_'+self.case_id+('_known' if self.disclosed else '_unknown')

    @property
    def slots(self):
        return {'target_location_choice':dict(public_role='target_location',candidate_ids=list(LOCATIONS))}

    @property
    def theta_star(self):
        return {'target_location_choice':self.target_location}

    @property
    def initial_disclosed_slots(self):
        return ['target_location_choice'] if self.disclosed else []

    @property
    def u0(self):
        text = ('Find the kitchen knife and approach it within 1.2 metres. Do not pick it up or deliver it. '
                'You know the room map and six inspection stations, but unseen object locations are not observations. '
                'A kitchen counter or shelf is a plausible semantic prior for a kitchen knife, not a guaranteed location. '
                'You may search stations and ask the user for a location hint. A search can make useful progress by revealing absence. '
                'A user location claim does not itself count as detecting the object.')
        if self.disclosed:
            text += f' The user has specified target_location={self.target_location}.'
        return text

    def scene(self):
        return public_map()  # NEVER includes hidden target facts.


def make_sample(case_id='case_b',unknown_preferences=1):
    if case_id not in SCENARIOS or type(unknown_preferences) is not int or unknown_preferences not in (0,1):
        raise ValueError('Navigation needs case_a/b/c and 0 or 1 unknown location fact')
    data = json.loads((ROOT/'data/navigation_dev_v1/scenarios.json').read_text())['scenarios'][case_id]
    return NavigationSample(case_id,data['target_location'],unknown_preferences==0,data['scene_seed'])
