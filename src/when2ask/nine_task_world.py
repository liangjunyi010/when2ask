"""Isolated scene adapters. Existing skills and geometric tolerances are retained."""
import copy
import importlib.util
import math
import types

import pybullet as p

from .config import ROOT
from .diverse_world import DiverseEnvironment, DiverseSkills
from .study_protocol import observe
from .study_evaluator import evaluate_study
from .task6_world import TableWorld
from .task6_spec import public_task
from .task6_evaluator import evaluate
from .navigation_world import angle
from .nine_task_data import STUDY


def isolated_module(filename, suffix):
    """Fresh module globals per world: map variants never modify legacy imports."""
    spec = importlib.util.spec_from_file_location('when2ask._nine_'+suffix,
                                                ROOT/'src/when2ask'/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def navigation_class(scene):
    map_module = isolated_module('navigation_map.py','map')
    map_module.LOCATIONS = copy.deepcopy(scene['stations'])
    original_public_map = map_module.public_map
    def public_map():
        value = original_public_map()
        value['version'] = 'three_room_station_layout_v9'
        return value
    world_module = isolated_module('navigation_world.py','world')
    for key in ('LOCATIONS','ROOMS','room_at','route','route_distance'):
        setattr(world_module,key,getattr(map_module,key))
    world_module.public_map = public_map
    return world_module.NavigationWorld, map_module


def mobile_world(sample):
    Base, map_module = navigation_class(sample.scene())
    if sample.template_id == 'find_and_approach': return Base(sample)

    class Patrol(Base):
        def __init__(self):
            super().__init__(types.SimpleNamespace(target_location='study_shelf'))
            p.removeBody(self.target,physicsClientId=self.client)
            self.sample=sample;self.inspection_evidence=[];self.return_events=[]
            self.stations=map_module.LOCATIONS
            self.beacons={k:self.box([.05,.05,.04],[*v['fixture_xy'],.74],[.18,.7,.4,1])
                          for k,v in self.stations.items()}

        def perceive(self): self.visible_now=False

        def observation(self):
            raw=super().observation()
            for key in ('target_observation','target_visible_now','distance_to_observed_target_m'):raw.pop(key,None)
            raw['task']=public_task(sample);raw['known_map']['goal']=dict(inspect_then_return=True)
            raw['known_map']['limits']=dict(distance_m=36,robot_actions=12)
            raw['inspection_evidence']=copy.deepcopy(self.inspection_evidence)
            raw['return_events']=copy.deepcopy(self.return_events)
            raw['affordances']=dict(inspect_station=list(self.stations),return_home=True)
            return raw

        def execute(self,action):
            start=self.step_count
            if action['kind']=='inspect_station':
                key=action['location_id'];result=self.search(key);pose=self.pose();station=self.stations[key]
                target=[*station['fixture_xy'],.74]
                eye=[pose[0]+.35*math.cos(pose[2]),pose[1]+.35*math.sin(pose[2]),1.05]
                ray=p.rayTest(eye,target,physicsClientId=self.client)[0]
                evidence=dict(step=self.step_count,location_id=key,robot_pose=pose,
                    distance_m=math.dist(pose[:2],station['xy']),yaw_error=abs(angle(pose[2]-station['yaw'])),
                    fixture_distance_m=math.dist(eye,target),ray_hit_body=ray[0],ray_hit_point=list(ray[3]),
                    ray_endpoint=target,success=result['success'])
                self.inspection_evidence.append(evidence)
                self.event('patrol_inspection',**{k:v for k,v in evidence.items() if k!='step'})
                result['skill']='inspect_station';return result
            if action['kind']!='return_home':raise ValueError('Invalid patrol action')
            self.phase='return_home';here=map_module.room_at(self.pose()[:2]);names=list(map_module.ROOMS)
            index=names.index(here)
            sequence=list(range(index,0,-1)) if index>1 else list(range(index,2)) if index<1 else [1]
            ok=all(self.drive(list(map_module.ROOMS[names[i]])) for i in sequence)
            self.motors(0,0)
            for _ in range(120):self.step()
            pose=self.pose();self.return_events.append(dict(step=self.step_count,robot_pose=pose))
            result=dict(skill='return_home',object_id='mobile_robot',target_id='home',
                success=ok and math.dist(pose[:2],[0,0])<=.22,reason='returned' if ok else 'motion_limit',
                start_step=start,end_step=self.step_count)
            self.event('skill_result',**result);self.phase='idle';return result

    return Patrol()


def patrol_score(world,sample,burden,actions,termination):
    """Same v1 pose/ray/contact/DAG criteria, evaluated against this world's map."""
    required={sample.public_goal['required_station'],next(iter(sample.theta_star.values()))}
    evidence=[]
    for e in world.inspection_evidence:
        station=world.stations[e['location_id']]
        if (e['success'] and math.dist(e['robot_pose'][:2],station['xy'])<=.22
            and e['yaw_error']<.20 and e['fixture_distance_m']<1.65
            and e['ray_hit_body']==world.beacons[e['location_id']]
            and math.dist(e['ray_hit_point'],e['ray_endpoint'])<.4):evidence.append(e)
    visited={e['location_id'] for e in evidence};pose=world.pose()
    v,w=p.getBaseVelocity(world.robot,physicsClientId=world.client)
    last=world.return_events[-1] if world.return_events else None
    checks=dict(required_stations_physically_inspected=required<=visited,
        returned_to_start=math.dist(pose[:2],sample.public_goal['home_xy'])<=sample.public_goal['home_radius_m'],
        inspections_before_return=bool(required<=visited and last and
            all(any(e['location_id']==k and e['step']<last['step'] for e in evidence) for k in required)),
        robot_stopped=math.hypot(v[0],v[1])<.08 and abs(w[2])<.12,
        no_wall_penetration=not any(c[8]<-.02 for wall in world.walls for c in p.getContactPoints(world.robot,wall,physicsClientId=world.client)),
        distance_budget_respected=world.distance_m<=36)
    return dict(task_success=all(checks.values()),termination_reason=termination,conditions=checks,
        clarification_burden=burden,action_count=len(actions),simulation_steps=world.step_count,
        details=dict(required_stations=sorted(required),inspection_evidence=evidence,final_pose=pose,distance_m=world.distance_m),
        evaluator_version='task6_patrol_v1_criteria_map_adapter_v9')


class Adapter:
    def __init__(self,sample):
        self.sample=sample;self.family=('study' if sample.template_id in STUDY else
            'navigation' if sample.template_id=='find_and_approach' else 'task6')
        self.world=(DiverseEnvironment(sample.scene_seed,scene_spec=sample.scene()) if self.family=='study'
            else mobile_world(sample) if sample.template_id in ('find_and_approach','patrol_return') else TableWorld(sample))
        self.skills=DiverseSkills(self.world) if self.family=='study' else None

    def state(self,history):
        if self.family=='study':return observe(self.world,self.sample.u0,history)
        return self.world.observation()

    def execute(self,action):
        if self.family=='study':
            return (self.skills.cover(action['object_id'],action['target_id']) if action['kind']=='cover' else
                self.skills.pick_place(action['object_id'],action['target_id'],action.get('relation','inside'))).to_dict()
        if self.family=='navigation':return self.world.search(action['location_id'])
        return self.world.execute(action)

    def score(self,burden,actions,termination):
        s,w=self.sample,self.world
        if self.family=='study':return evaluate_study(w,s,clarification_burden=burden,actions=actions,termination=termination)
        if self.family=='navigation':return w.evaluate(burden,actions,termination)
        if s.template_id=='patrol_return':return patrol_score(w,s,burden,actions,termination)
        return evaluate(w,s,burden=burden,actions=actions,termination=termination)

    def close(self):self.world.close()
