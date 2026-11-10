"""Real Bullet worlds for the six new tasks, reusing the validated motor skills."""
import copy
import math
import os
import tempfile
from types import SimpleNamespace

import numpy as np
import pybullet as p
from PIL import Image, ImageDraw

from .environment import Environment, SceneObject
from .diverse_world import DiverseEnvironment
from .skills import RobotSkills, SkillFailure, SkillResult
from .task6_spec import public_task

COLORS = dict(red=[.85,.08,.08,1],blue=[.06,.25,.92,1],green=[.1,.72,.27,1],
    yellow=[.98,.76,.06,1],purple=[.55,.25,.8,1],cyan=[.10,.75,.8,1],
    orange=[.95,.45,.12,1],brown=[.63,.4,.2,1],black=[.065,.065,.075,1],gray=[.45,.49,.55,1])


class TableWorld(Environment):
    def __init__(self, sample):
        self.sample, self.spec = sample, sample.scene()
        self.geometry, self.zones = {}, {z['id']: z for z in self.spec.get('zones', [])}
        self.phase, self.inspections, self.reports, self.checkpoints = 'idle', [], [], []
        super().__init__(sample.scene_seed)
        self.container_ids = tuple(self.geometry)
        self.initial_positions = {k: list(self.body_pose(k)[0]) for k in self.objects}
        self.skills = TaskSkills(self)
        self.record_checkpoint('initial')

    def _build_scene(self, minimal):
        for c in self.spec.get('containers', []):
            hx,hy = c['half_xy']; h,w,f = c['wall_height'],.012,.014
            halves=[(hx,hy,f/2),(w/2,hy,h/2),(w/2,hy,h/2),(hx-w,w/2,h/2),(hx-w,w/2,h/2)]
            positions=[(0,0,f/2),(-hx+w/2,0,f+h/2),(hx-w/2,0,f+h/2),(0,-hy+w/2,f+h/2),(0,hy-w/2,f+h/2)]
            body=self._compound([p.GEOM_BOX]*5,halves,positions,[(0,0,0,1)]*5,
                (*c['xy'],self.TABLE_Z),COLORS[c['color']],0)
            self.objects[c['id']]=SceneObject(c['id'],body,'container',c['color'],(hx,hy,(f+h)/2))
            self.geometry[c['id']]=dict(xy=c['xy'],half=(hx,hy),inner=(hx-w,hy-w),floor=self.TABLE_Z+f,rim=self.TABLE_Z+f+h)
        if 'box' in self.geometry:
            g=self.geometry['box'];self.BOX_XY=tuple(g['xy']);self.BOX_HALF=g['half'];self.INNER_HALF=g['inner'];self.FLOOR_Z=g['floor'];self.RIM_Z=g['rim']
        for z in self.zones.values():
            v=p.createVisualShape(p.GEOM_BOX,halfExtents=[*z['half_xy'],.001],rgbaColor=[.2,.72,.73,.45],physicsClientId=self.client)
            p.createMultiBody(0,-1,v,[*z['xy'],self.TABLE_Z+.001],physicsClientId=self.client)
        for o in self.spec.get('objects', []):
            key,xy,category,color=o['id'],o['xy'],o['category'],o['color']
            if category=='cup':
                # Same hollow geometry as the stable Panda demo; zero jitter here.
                self._add_cup(key,xy,COLORS[color],color)
                # Initial height for stocked/covered items is created correctly,
                # rather than moving them during an episode. See _compound override.
            else:
                half=(.154,.134,.006) if category in ('lid','screen') else (.022,.022,.022)
                if category=='puck':
                    shape=p.createCollisionShape(p.GEOM_CYLINDER,radius=.022,height=.044,physicsClientId=self.client)
                    visual=p.createVisualShape(p.GEOM_CYLINDER,radius=.022,length=.044,rgbaColor=COLORS[color],physicsClientId=self.client)
                    body=p.createMultiBody(.06,shape,visual,[*xy,self.TABLE_Z+.024],physicsClientId=self.client)
                    p.changeDynamics(body,-1,lateralFriction=.8,restitution=0,physicsClientId=self.client)
                else:body=self._box(half,(*xy,o.get('z',self.TABLE_Z+half[2]+.002)),COLORS[color],.10 if category in ('lid','screen') else .06)
                self.objects[key]=SceneObject(key,body,category,color,half)
        if self.sample.template_id=='occlusion_inspection':
            label=self.spec['label'];xy=label['xy']
            for dx in (-.13,.13):
                for dy in (-.11,.11):self._box((.009,.009,.062),(xy[0]+dx,xy[1]+dy,.482),[.55,.58,.61,1],0)
            body=self._box((.04,.025,.002),(*xy,self.TABLE_Z+.003),[1,1,1,1],0)
            self.objects['label_fixture']=SceneObject('label_fixture',body,'label','white',(.04,.025,.002))
            image=Image.new('RGB',(160,100),'white');ImageDraw.Draw(image).text((20,35),label['code'].upper(),fill='black',font_size=24)
            fd,path=tempfile.mkstemp(suffix='.png');os.close(fd);image.save(path)
            texture=p.loadTexture(path,physicsClientId=self.client);os.unlink(path)
            p.changeVisualShape(body,-1,textureUniqueId=texture,physicsClientId=self.client)

    def _compound(self, types, half, positions, orientations, location, color, mass, **kwargs):
        if mass>0 and len(types)>5:
            for o in self.spec.get('objects', []):
                if o['category']=='cup' and math.dist(location[:2],o['xy'])<.008 and 'z' in o:
                    location=(*location[:2],o['z'])
        return super()._compound(types,half,positions,orientations,location,color,mass,**kwargs)

    def containment(self,key,target=None):
        return DiverseEnvironment.containment(self,key,target or next(iter(self.geometry)))

    def outside_box(self,key,target=None):
        return DiverseEnvironment.outside_box(self,key,target or next(iter(self.geometry)))

    def in_zone(self, key, zone):
        lo,hi=self.bounds(key);z=self.zones[zone];xy=np.array(z['xy']);half=np.array(z['half_xy'])
        contacts=p.getContactPoints(self.objects[key].body_id,self.table,physicsClientId=self.client)
        supported=any(c[7][2]>.65 and c[9]>.001 for c in contacts)
        return bool(np.all(lo[:2]>=xy-half-.002) and np.all(hi[:2]<=xy+half+.002)
                    and abs(lo[2]-self.TABLE_Z)<.005 and supported and self.stable(key))

    def movable(self):return [k for k,o in self.objects.items() if o.category not in ('container','label')]

    def contents(self):
        return {c:[k for k in self.movable() if self.objects[k].category not in ('lid','screen') and self.containment(k,c)['inside']] for c in self.container_ids}

    def zone_contents(self):return {z:[k for k in self.movable() if self.in_zone(k,z)] for z in self.zones}

    def camera(self):
        if self.sample.template_id!='occlusion_inspection':return None
        label=self.spec['label'];target=self.body_pose('label_fixture')[0];eye=label['eye']
        hit=p.rayTest(eye,target,physicsClientId=self.client)[0][0]
        visible=hit==self.objects['label_fixture'].body_id and math.dist(eye,target)<=.8
        return dict(visible=visible,range_m=math.dist(eye,target),ray_hit_body=hit,
                    eye=eye,target=list(target),sensor='fixed_camera_range_and_bullet_ray_los')

    def observation(self):
        raw=self.snapshot();hidden=[]
        if self.sample.template_id=='retrieve_restore' and self.coverage('storage_lid')['covered']:
            hidden=['stored_cup','stored_block']
        camera=self.camera()
        if camera and not camera['visible']:hidden.append('label_fixture')
        raw['objects']={k:v for k,v in raw['objects'].items() if k not in hidden}
        raw['task']=public_task(self.sample)
        raw['containers']={c:{**copy.deepcopy(self.geometry[c]),'contents':[k for k in keys if k not in hidden],
            'contents_observed':not bool(hidden) } for c,keys in self.contents().items()}
        raw['zones']={z:{**copy.deepcopy(spec),'contents':self.zone_contents()[z]} for z,spec in self.zones.items()}
        raw['inspections']=copy.deepcopy(self.inspections)
        raw['reports']=copy.deepcopy(self.reports)
        raw['sensor']=dict(label_visible=camera['visible'],model=camera['sensor']) if camera else None
        raw['affordances']={'move':{k:list(self.container_ids)+list(self.zones) for k in self.movable() if k in raw['objects']},
            'cover':['storage_lid'] if self.sample.template_id=='retrieve_restore' else [],
            'inspect':['label_fixture'] if camera else []}
        return raw

    def record_checkpoint(self, action):
        self.checkpoints.append(dict(step=self.step_count,action=copy.deepcopy(action),
            contents=self.contents(),zones=self.zone_contents(),released=self.released(),
            positions={k:list(self.body_pose(k)[0]) for k in self.movable()}))

    def execute(self, action):
        kind=action['kind'];start=self.step_count
        if kind=='move':result=self.skills.move(action['object_id'],action['target_id'])
        elif kind=='cover':result=self.skills.cover(action['object_id'],'box').to_dict()
        elif kind=='inspect':
            self.phase='inspect';self.step(120);camera=self.camera();ok=bool(camera and camera['visible'])
            evidence=dict(step=self.step_count,camera=camera,code=self.spec['label']['code'] if ok else None)
            self.inspections.append(evidence);self.events.append(dict(kind='physical_inspection',**evidence))
            result=dict(skill='inspect',object_id='label_fixture',target_id='inspection_camera',success=ok,
                reason='physically_observed' if ok else 'occluded',start_step=start,end_step=self.step_count)
        elif kind=='report':
            report=dict(step=self.step_count,code=action['code']);self.reports.append(report);self.events.append(dict(kind='report',**report))
            result=dict(skill='report',object_id=action['code'],target_id='operator',success=True,reason='report_submitted',start_step=start,end_step=self.step_count)
        else:raise ValueError('Unsupported physical action')
        self.record_checkpoint(action);self.phase='idle'
        return result


class TaskSkills(RobotSkills):
    def move(self,key,target):
        env=self.env;start=env.step_count;self._deadline=start+self.MAX_SKILL_STEPS
        try:
            if key not in env.movable():raise SkillFailure('not_movable')
            obj=env.objects[key]
            if target in env.geometry:
                if obj.category in ('lid','screen'):raise SkillFailure('use_surface_for_large_panel')
                g=env.geometry[target];contents=env.contents()[target]
                slots=[(0,0)] if min(g['inner'])<.045 else [(-.035,0),(.035,0)] if min(g['inner'])<.08 else [(-.045,0),(.045,0),(0,.05)]
                slot=next((offset for offset in slots if all(math.dist([g['xy'][0]+offset[0],g['xy'][1]+offset[1]],env.body_pose(k)[0][:2])>.055 for k in contents if k!=key)),None)
                if slot is None:raise SkillFailure('target_full')
                destination=[g['xy'][0]+slot[0],g['xy'][1]+slot[1],g['floor']+obj.half_extents[2]+.004]
            elif target in env.zones:
                z=env.zones[target];destination=[*z['xy'],env.TABLE_Z+obj.half_extents[2]+.004]
            else:raise SkillFailure('unknown_target')
            env.events.append(dict(kind='placement_started',object_id=key,target_id=target,step=start))
            self._transfer(key,destination)
            ok=env.containment(key,target)['inside'] if target in env.geometry else env.in_zone(key,target)
            reason='placed' if ok else 'placement_geometry_failed'
        except (SkillFailure,p.error) as exc:
            ok=False;reason=str(exc);self._cleanup_failed_grasp()
        result=SkillResult('move',key,target,bool(ok),reason,start,env.step_count).to_dict()
        env.events.append(dict(kind='skill_result',**result));return result


from .navigation_world import NavigationWorld, angle
from .navigation_map import LOCATIONS, ROOMS, room_at


class PatrolWorld(NavigationWorld):
    def __init__(self,sample):
        super().__init__(SimpleNamespace(target_location='study_shelf'))
        p.removeBody(self.target,physicsClientId=self.client)
        self.sample=sample;self.inspection_evidence=[];self.return_events=[]
        self.beacons={key:self.box([.05,.05,.04],[station['xy'][0],math.copysign(2.15,station['xy'][1]),.74],[.18,.7,.4,1]) for key,station in LOCATIONS.items()}

    def perceive(self):self.visible_now=False

    def observation(self):
        raw=super().observation()
        for key in ('target_observation','target_visible_now','distance_to_observed_target_m'):raw.pop(key,None)
        raw['task']=public_task(self.sample);raw['known_map']['goal']=dict(inspect_then_return=True)
        raw['known_map']['limits']=dict(distance_m=36,robot_actions=12)
        raw['inspection_evidence']=copy.deepcopy(self.inspection_evidence);raw['return_events']=copy.deepcopy(self.return_events)
        raw['affordances']=dict(inspect_station=list(LOCATIONS),return_home=True)
        return raw

    def execute(self,action):
        start=self.step_count
        if action['kind']=='inspect_station':
            location=action['location_id'];result=self.search(location);pose=self.pose();station=LOCATIONS[location]
            target=[station['xy'][0],math.copysign(2.15,station['xy'][1]),.74]
            eye=[pose[0]+.35*math.cos(pose[2]),pose[1]+.35*math.sin(pose[2]),1.05]
            ray=p.rayTest(eye,target,physicsClientId=self.client)[0]
            evidence=dict(step=self.step_count,location_id=location,robot_pose=pose,
                distance_m=math.dist(pose[:2],station['xy']),yaw_error=abs(angle(pose[2]-station['yaw'])),
                fixture_distance_m=math.dist(eye,target),ray_hit_body=ray[0],ray_hit_point=list(ray[3]),
                ray_endpoint=target,success=result['success'])
            self.inspection_evidence.append(evidence);self.event('patrol_inspection',**{k:v for k,v in evidence.items() if k!='step'})
            result['skill']='inspect_station';return result
        if action['kind']!='return_home':raise ValueError('Unknown patrol action')
        self.phase='return_home';here=room_at(self.pose()[:2]);names=list(ROOMS);index=names.index(here)
        sequence=list(range(index,0,-1)) if index>1 else list(range(index,2)) if index<1 else [1]
        points=[list(ROOMS[names[i]]) for i in sequence]
        ok=all(self.drive(point) for point in points)
        self.motors(0,0)
        for _ in range(120):self.step()
        pose=self.pose();self.return_events.append(dict(step=self.step_count,robot_pose=pose))
        result=dict(skill='return_home',object_id='mobile_robot',target_id='home',success=ok and math.dist(pose[:2],[0,0])<=.22,
            reason='returned' if ok else 'motion_limit',start_step=start,end_step=self.step_count)
        self.event('skill_result',**result);self.phase='idle';return result


def make_world(sample):return PatrolWorld(sample) if sample.template_id=='patrol_return' else TableWorld(sample)
