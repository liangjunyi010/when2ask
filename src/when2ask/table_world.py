"""Tabletop geometry, observations and motor-controlled manipulation skills."""
import copy
import math
import os
import tempfile

import numpy as np
import pybullet as p
from PIL import Image, ImageDraw

from .environment import Environment, SceneObject
from .skills import RobotSkills, SkillFailure, SkillResult
from .task_graph import placement_offsets

COLORS = dict(red=[.85,.08,.08,1],blue=[.06,.25,.92,1],green=[.1,.72,.27,1],
    yellow=[.98,.76,.06,1],purple=[.55,.25,.8,1],cyan=[.10,.75,.8,1],
    orange=[.95,.45,.12,1],brown=[.63,.4,.2,1],black=[.065,.065,.075,1],gray=[.45,.49,.55,1])


class TableWorld(Environment):
    def __init__(self, sample):
        self.sample, self.spec = sample, sample.scene()
        self.geometry, self.zones = {}, {z['id']: z for z in self.spec.get('zones', [])}
        self.phase, self.inspections, self.reports, self.checkpoints = 'idle', [], [], []
        self.inventory_checks = []
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
                self._add_cup(key,xy,COLORS[color],color)
            else:
                half=tuple(o.get('half_extents', (.154,.134,.006) if category in ('lid','screen') else (.022,.022,.022)))
                if category=='puck':
                    shape=p.createCollisionShape(p.GEOM_CYLINDER,radius=.022,height=.044,physicsClientId=self.client)
                    visual=p.createVisualShape(p.GEOM_CYLINDER,radius=.022,length=.044,rgbaColor=COLORS[color],physicsClientId=self.client)
                    body=p.createMultiBody(.06,shape,visual,[*xy,o.get('z',self.TABLE_Z+.024)],physicsClientId=self.client)
                    p.changeDynamics(body,-1,lateralFriction=.8,restitution=0,physicsClientId=self.client)
                else:body=self._box(half,(*xy,o.get('z',self.TABLE_Z+half[2]+.002)),COLORS[color],.10 if category in ('lid','screen') else .06)
                self.objects[key]=SceneObject(key,body,category,color,half)
        if self.sample.template_id=='occlusion_inspection':
            label=self.spec['label'];xy=label['xy']
            if label.get('support', False):
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

    def containment(self, object_id, container_id=None):
        target = container_id or next(iter(self.geometry))
        g = self.geometry[target]
        lo, hi = self.bounds(object_id)
        xy, half = np.array(g["xy"]), np.array(g["inner"])
        xy_ok = bool(np.all(lo[:2] >= xy - half - .002) and np.all(hi[:2] <= xy + half + .002))
        z_ok = bool(lo[2] >= g["floor"] - .004 and hi[2] <= g["rim"] + .002)
        contacts = p.getContactPoints(self.objects[object_id].body_id, self.objects[target].body_id,
                                      physicsClientId=self.client)
        supported = any(c[7][2] > .65 and c[9] > .001 for c in contacts)
        return dict(inside=bool(xy_ok and z_ok and supported and self.stable(object_id)),
                    full_xy_inside=xy_ok, full_z_inside=z_ok, supported_by_box=supported,
                    stable=self.stable(object_id), aabb_min=lo.tolist(), aabb_max=hi.tolist())

    def outside_box(self, object_id, container_id=None):
        target = container_id or next(iter(self.geometry))
        g = self.geometry[target]
        lo, hi = self.bounds(object_id)
        lower, upper = np.array(g["xy"]) - g["half"], np.array(g["xy"]) + g["half"]
        outside = bool(np.any(hi[:2] < lower - .001) or np.any(lo[:2] > upper + .001))
        return dict(outside=bool(outside and self.stable(object_id)),
                    footprint_disjoint=outside, stable=self.stable(object_id))

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
        covered = 'box' in self.geometry and any(self.coverage(k)['covered'] for k,o in self.objects.items() if o.category=='lid')
        if covered:
            hidden.extend(self.contents()['box'])
        camera=self.camera()
        if camera and not camera['visible']:hidden.append('label_fixture')
        raw['objects']={k:v for k,v in raw['objects'].items() if k not in hidden}
        raw['containers']={c:{**copy.deepcopy(self.geometry[c]),'contents':[k for k in keys if k not in hidden],
            'contents_observed':not (covered and c=='box') } for c,keys in self.contents().items()}
        raw['zones']={z:{**copy.deepcopy(spec),'contents':self.zone_contents()[z]} for z,spec in self.zones.items()}
        raw['inspections']=copy.deepcopy(self.inspections)
        raw['reports']=copy.deepcopy(self.reports)
        raw['sensor']=dict(label_visible=camera['visible'],model=camera['sensor']) if camera else None
        raw['affordances']={'move':{k:list(self.container_ids)+list(self.zones) for k in self.movable() if k in raw['objects']},
            'cover':{k:['box'] for k,o in self.objects.items() if o.category=='lid' and 'box' in self.geometry},
            'inspect':['label_fixture'] if camera else [],
            'report':self.sample.slots.get('inspection_code',{}).get('candidate_ids',[]),
            'inspect_inventory':bool(self.geometry)}
        raw['inventory_checks']=copy.deepcopy(self.inventory_checks)
        return raw

    def record_checkpoint(self, action):
        self.checkpoints.append(dict(step=self.step_count,action=copy.deepcopy(action),
            contents=self.contents(),zones=self.zone_contents(),released=self.released(),
            positions={k:list(self.body_pose(k)[0]) for k in self.movable()}))

    def execute(self, action):
        kind=action['kind'];start=self.step_count
        if kind=='move':result=self.skills.move(action['object_id'],action['target_id'])
        elif kind=='cover':result=self.skills.cover(action['object_id'],action['target_id']).to_dict()
        elif kind=='inspect_inventory':
            evidence=dict(step=self.step_count,contents=self.observation()['containers'])
            self.inventory_checks.append(evidence)
            result=dict(skill=kind,success=True,start_step=start,end_step=self.step_count)
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
                slots=placement_offsets(g['half'], .032)
                slot=next((offset for offset in slots if all(math.dist([g['xy'][0]+offset[0],g['xy'][1]+offset[1]],env.body_pose(k)[0][:2])>.055 for k in contents if k!=key)),None)
                if slot is None:raise SkillFailure('target_full')
                destination=[g['xy'][0]+slot[0],g['xy'][1]+slot[1],g['floor']+obj.half_extents[2]+.004]
            elif target in env.zones:
                z=env.zones[target]
                slots=[(0,0)] if obj.category in ('lid','screen') else placement_offsets(z['half_xy'],.032)
                contents=env.zone_contents()[target]
                slot=next((offset for offset in slots if all(math.dist([z['xy'][0]+offset[0],z['xy'][1]+offset[1]],env.body_pose(k)[0][:2])>.060 for k in contents if k!=key)),None)
                if slot is None:raise SkillFailure('target_full')
                destination=[z['xy'][0]+slot[0],z['xy'][1]+slot[1],env.TABLE_Z+obj.half_extents[2]+.004]
            else:raise SkillFailure('unknown_target')
            env.events.append(dict(kind='placement_started',object_id=key,target_id=target,step=start))
            self._transfer(key,destination)
            ok=env.containment(key,target)['inside'] if target in env.geometry else env.in_zone(key,target)
            reason='placed' if ok else 'placement_geometry_failed'
        except (SkillFailure,p.error) as exc:
            ok=False;reason=str(exc);self._cleanup_failed_grasp()
        result=SkillResult('move',key,target,bool(ok),reason,start,env.step_count).to_dict()
        env.events.append(dict(kind='skill_result',**result));return result
