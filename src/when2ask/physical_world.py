"""Physical backends with public observations and private measurement snapshots."""
import copy
import importlib.util
import math

import pybullet as p

from .config import ROOT
from .navigation_world import angle
from .table_world import TableWorld


def isolated_module(filename, suffix):
    spec = importlib.util.spec_from_file_location('when2ask._world_'+suffix, ROOT/'src/when2ask'/filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mobile_world(sample):
    mapping = isolated_module('navigation_map.py', 'map')
    mapping.LOCATIONS = copy.deepcopy(sample.scene()['stations'])
    module = isolated_module('navigation_world.py', 'mobile')
    for key in ('LOCATIONS', 'ROOMS', 'room_at', 'route', 'route_distance'):
        setattr(module, key, getattr(mapping, key))
    def public_map():
        value = mapping.public_map()
        value['limits'] = dict(distance_m=sample.scene()['distance_budget_m'])
        value['search_scope'] = 'A negative observation covers the inspected station only.'
        return value
    module.public_map = public_map
    if sample.template_id == 'find_and_approach':
        return module.NavigationWorld(sample)

    class Patrol(module.NavigationWorld):
        def __init__(self):
            super().__init__(sample)
            p.removeBody(self.target, physicsClientId=self.client)
            self.inspection_evidence = []
            self.beacons = {k:self.box([.05,.05,.04],[*v['fixture_xy'],.74],[.18,.7,.4,1])
                            for k,v in mapping.LOCATIONS.items()}

        def perceive(self):
            self.visible_now = False

        def observation(self):
            raw = super().observation()
            for key in ('target_observation','target_visible_now','distance_to_observed_target_m'):
                raw.pop(key, None)
            raw['known_map']['goal'] = dict(inspect_then_return=True)
            raw['inspection_evidence'] = copy.deepcopy(self.inspection_evidence)
            return raw

        def inspect_station(self, key):
            result = self.search(key)
            pose, station = self.pose(), mapping.LOCATIONS[key]
            target = [*station['fixture_xy'],.74]
            eye = [pose[0]+.35*math.cos(pose[2]),pose[1]+.35*math.sin(pose[2]),1.05]
            ray = p.rayTest(eye,target,physicsClientId=self.client)[0]
            valid = (result['success'] and math.dist(pose[:2],station['xy']) <= .22
                     and abs(angle(pose[2]-station['yaw'])) < .20 and math.dist(eye,target) < 1.65
                     and ray[0] == self.beacons[key] and math.dist(ray[3],target) < .4)
            self.inspection_evidence.append(dict(location_id=key, step=self.step_count,
                                                valid=valid, pose=pose, ray_hit=ray[0]))
            result.update(skill='inspect_station', success=valid)
            return result

        def return_home(self):
            start = self.step_count
            names = list(mapping.ROOMS)
            index = names.index(mapping.room_at(self.pose()[:2]))
            sequence = list(range(index,0,-1)) if index>1 else list(range(index,2)) if index<1 else [1]
            ok = all(self.drive(list(mapping.ROOMS[names[i]])) for i in sequence)
            self.motors(0,0)
            for _ in range(120):
                self.step()
            return dict(skill='return_home', success=ok and math.dist(self.pose()[:2],[0,0])<=.22,
                        start_step=start, end_step=self.step_count)
    return Patrol()


class Adapter:
    def __init__(self, sample):
        self.sample = sample
        self.mobile = sample.template_id in ('find_and_approach','patrol_return')
        self.world = mobile_world(sample) if self.mobile else TableWorld(sample)

    def observation(self):
        raw = self.world.observation()
        if self.mobile:
            stations = list(self.sample.physical_scene['stations'])
            raw['affordances'] = (dict(search=stations, approach=stations)
                                  if self.sample.template_id=='find_and_approach'
                                  else dict(inspect_station=stations, return_home=True))
        return raw

    def execute(self, action):
        w, kind = self.world, action['kind']
        if not self.mobile:
            return w.execute(action)
        if kind in ('search','approach'):
            result = w.search(action['location_id'])
            result['skill'] = kind
            return result
        if kind == 'inspect_station':
            return w.inspect_station(action['location_id'])
        return w.return_home()

    def measurements(self):
        w = self.world
        if not self.mobile:
            return dict(containers=w.contents(), zones=w.zone_contents(),
                        categories={k:v.category for k,v in w.objects.items()},
                        positions={k:list(w.body_pose(k)[0]) for k in w.movable()},
                        coverage={k:w.coverage(k)['covered'] for k,v in w.objects.items()
                                  if v.category=='lid' and 'box' in w.geometry},
                        inspections=copy.deepcopy(w.inspections), reports=copy.deepcopy(w.reports),
                        released=w.released(), stable=all(w.stable(k) for k in w.movable()),
                        safe=True)
        observation = self.observation()
        penetrations = [c for wall in w.walls for c in p.getContactPoints(w.robot,wall,physicsClientId=w.client)
                        if c[8]<-.02]
        visited = (list(w.checked) if self.sample.template_id=='find_and_approach'
                   else [r['location_id'] for r in w.inspection_evidence if r['valid']])
        return dict(visited=visited, detected=copy.deepcopy(w.last_seen),
                    distance_to_target=math.dist(w.pose()[:2],w.target_pose()[:2])
                    if self.sample.template_id=='find_and_approach' else None,
                    at_home=math.dist(w.pose()[:2],[0,0])<=.22, stopped=observation['robot_stopped'],
                    safe=not penetrations and w.distance_m<=w.distance_budget_m)

    def close(self):
        self.world.close()
