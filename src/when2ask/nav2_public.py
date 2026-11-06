"""Derived public costs and belief; never reads target_location or evaluator state."""
import copy
import math

from .navigation_map import LOCATIONS,route
from .navigation_protocol import location_claim
from .navigation_world import angle


def motion_estimate(pose,location,contract):
    points=route(pose[:2],location);xy=list(pose[:2]);yaw=pose[2];distance=turn=0.
    for point in points:
        d=math.dist(xy,point)
        if d>.15:
            heading=math.atan2(point[1]-xy[1],point[0]-xy[0]);turn+=abs(angle(heading-yaw));yaw=heading
        distance+=d;xy=point
    turn+=abs(angle(LOCATIONS[location]['yaw']-yaw))
    m=contract['cost_model'];factor=contract['speed_factor']
    return distance/(m['linear_speed_m_s']*factor)+turn/(m['angular_speed_rad_s']*factor)+len(points)*m['waypoint_overhead_s']+m['settle_s']


def evidence(instruction,obs,history,contract):
    seen=obs['target_observation'];hint=location_claim(instruction,history)
    negative=[k for k,v in obs['checked_locations'].items() if not v['target_detected']]
    remaining=[k for k in LOCATIONS if k not in negative]
    supported=(seen['location_id'] if seen else hint if hint in remaining else None)
    weights={k:(1. if k==supported else 0.) if supported else contract['prior'][k] if k in remaining else 0. for k in LOCATIONS}
    total=sum(weights.values());posterior={k:v/total if total else 0. for k,v in weights.items()}
    return dict(negative_stations=negative,remaining_locations=remaining,location_claim=hint,supported_location=supported,
        posterior_from_public_facts=posterior,target_observation=copy.deepcopy(seen),
        completion_observed=bool(seen and obs['distance_to_observed_target_m']<=1.2 and obs['robot_stopped']))


def payload(instruction,obs,history,contract,style='summary'):
    if style not in ('raw','summary'):raise ValueError('Unknown public payload style')
    # Explicit allowlist: no sample ID, hidden location, evaluator result or reference policy.
    keys=('simulation_step','robot_pose','current_room','known_map','checked_locations','target_observation',
          'target_visible_now','distance_to_observed_target_m','robot_stopped','distance_travelled_m','route_distances_m')
    measured={k:copy.deepcopy(obs[k]) for k in keys}
    result=dict(instruction=instruction,observation=measured,public_history=copy.deepcopy(history),
        cost_contract=copy.deepcopy(contract))
    if style=='summary':
        result['public_cost_summary']=dict(**evidence(instruction,obs,history,contract),
            alternatives={k:dict(route_distance_m=obs['route_distances_m'][k],
                estimated_motion_s=round(motion_estimate(obs['robot_pose'],k,contract),3)) for k in LOCATIONS},
            remaining_distance_m=round(max(0,contract['limits']['distance_m']-obs['distance_travelled_m']),3),
            remaining_robot_actions=max(0,contract['limits']['robot_actions']-sum(h['kind']=='action' for h in history)),
            previous_location_requests=sum(h['kind']=='ask' for h in history))
    return result


def reference_values(public):
    """Offline nominal-cost DP diagnostic, NOT included in agent payloads or gates.

    Exact for this stated finite candidate/cost model, not a physical optimum.
    It marginalizes public beliefs, never accesses the episode's hidden target.
    """
    from functools import lru_cache
    obs=public['observation'];contract=public['cost_contract']
    e=evidence(public['instruction'],obs,public['public_history'],contract)
    if e['completion_observed']:return dict(decision='CONTINUE',ask_s=None,continue_s=0.,margin_s=None)
    weights=e['posterior_from_public_facts'];remaining=tuple(k for k,w in weights.items() if w>0)
    if not remaining:return dict(decision=None,ask_s=None,continue_s=None,margin_s=None)
    question=contract['answer_delay_s']+contract['burden_equivalent_s']

    @lru_cache(None)
    def values(current,candidates):
        pose=obs['robot_pose'] if current=='initial' else [*LOCATIONS[current]['xy'],LOCATIONS[current]['yaw']]
        mass=sum(weights[k] for k in candidates);prob={k:weights[k]/mass for k in candidates}
        costs={k:motion_estimate(pose,k,contract) for k in candidates}
        ask=question+sum(prob[k]*costs[k] for k in candidates)
        cont=min(costs[k]+(1-prob[k])*min(values(k,tuple(j for j in candidates if j!=k)))
                 if len(candidates)>1 else costs[k] for k in candidates)
        return ask,cont
    ask,cont=values('initial',remaining)
    return dict(decision='ASK' if ask<cont else 'CONTINUE',ask_s=ask,continue_s=cont,margin_s=cont-ask,
        interpretation='Expected cost under shared nominal estimates and public prior, not realized hindsight truth')
