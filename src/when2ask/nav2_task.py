"""Independent Dev v2 worlds and public cost contract; no frozen files edited."""
import json
from dataclasses import dataclass

from .config import ROOT
from .navigation_map import LOCATIONS


def settings():
    return json.loads((ROOT/'configs/navigation_dev_v2.json').read_text())


@dataclass(frozen=True)
class Sample:
    sample_id: str
    target_location: str
    speed_factor: float
    answer_delay_s: float
    scene_seed: int = 0
    group_id: str = 'three_room_map_v1'

    @property
    def u0(self):
        return ('Find the kitchen knife and approach within 1.2 metres; no pickup or delivery. '
                'The known map has exactly six possible stations and the static target is at one of them. '
                'Use a stipulated uniform planning prior over the six stations, not a kitchen-first assumption. '
                'An exhaustive negative station inspection rules out only that station. '
                'Location hints from this study user simulator are exact and reliable, but do not count as physical detection. '
                'First achieve physical success. Then minimize motion time plus reply waiting plus the declared per-question interruption cost.')

    def public_contract(self):
        cfg=settings()
        return dict(speed_factor=self.speed_factor,answer_delay_s=self.answer_delay_s,
            burden_equivalent_s=cfg['burden_equivalent_s'],failure_penalty_s=cfg['failure_penalty_s'],
            reply_reliability=1.0,reply_granularity='exact_station',target_static=True,
            prior={k:1/len(LOCATIONS) for k in LOCATIONS},exhaustive_candidate_set=list(LOCATIONS),
            limits=cfg['limits'],cost_model=cfg['nominal_cost_model'],
            objective='physical success first; operational seconds = simulated motion + actual reply waiting + burden_equivalent_s * slots',
            api_cost='Measured separately by backend; not folded into operational seconds',
            estimates='Shared nominal kinematic estimates, not hidden-target/oracle rollout costs')


def samples():
    cfg=settings()
    return [Sample(f'nav2_s{int(speed*100):03d}_d{int(delay):02d}_{target}',target,speed,delay)
            for speed in cfg['speed_factors'] for delay in cfg['answer_delays_s'] for target in LOCATIONS]
