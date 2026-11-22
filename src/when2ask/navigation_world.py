"""Real wheel-driven Husky, known map and local range/FOV/ray observations."""
import math

import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image,ImageDraw,ImageFont

from .navigation_map import LOCATIONS, ROOMS, room_at, route, route_distance, public_map


def angle(value):
    return (value+math.pi)%(2*math.pi)-math.pi


class NavigationWorld:
    DT=1/240

    def __init__(self,sample):
        self.sample=sample
        self.distance_budget_m=sample.scene().get("distance_budget_m",180.)
        self.client=p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(),physicsClientId=self.client)
        p.setGravity(0,0,-9.81,physicsClientId=self.client)
        p.setTimeStep(self.DT,physicsClientId=self.client)
        p.setPhysicsEngineParameter(numSolverIterations=80,deterministicOverlappingPairs=1,physicsClientId=self.client)
        self.step_count=0;self.distance_m=0.;self.events=[];self.path=[];self.checked={};self.last_seen=None
        self.frame_callback=None;self.phase='initializing';self.wall_contacts=0;self.walls=[]
        plane=p.loadURDF('plane.urdf',physicsClientId=self.client)
        p.changeVisualShape(plane,-1,textureUniqueId=-1,rgbaColor=[.93,.95,.97,1],physicsClientId=self.client)
        for (name,xy),color in zip(ROOMS.items(),([.86,.90,.84,1],[.85,.89,.95,1],[.91,.86,.94,1])):
            self.box([1.98,2.95,.006],[xy[0],0,.007],color,collision=False)
        for y in (-3,3):self.walls.append(self.box([6,.06,.65],[0,y,.65],[.62,.69,.75,1]))
        for x in (-6,6):self.walls.append(self.box([.06,3,.65],[x,0,.65],[.62,.69,.75,1]))
        for x in (-2,2):
            for y in (-1.975,1.975):self.walls.append(self.box([.06,1.025,.65],[x,y,.65],[.62,.69,.75,1]))
        for key,loc in LOCATIONS.items():
            side=1 if loc['xy'][1]>0 else -1
            self.box([.85,.35,.35],[loc['xy'][0],side*2.15,.35],[.40,.45,.51,1])
            self.box([.13,.13,.008],[*loc['xy'],.01],[.15,.68,.68,1],collision=False)
        self.robot=p.loadURDF('husky/husky.urdf',[0,0,.12],p.getQuaternionFromEuler([0,0,math.pi]),physicsClientId=self.client)
        self.wheels=[2,3,4,5]
        for wheel in self.wheels:
            p.changeDynamics(self.robot,wheel,lateralFriction=.8,spinningFriction=.001,rollingFriction=.001,physicsClientId=self.client)
        self.motors(0,0)
        loc=LOCATIONS[sample.target_location];side=1 if loc['xy'][1]>0 else -1
        blade=p.createCollisionShape(p.GEOM_BOX,halfExtents=[.17,.04,.012],physicsClientId=self.client)
        visual=p.createVisualShape(p.GEOM_BOX,halfExtents=[.17,.04,.012],rgbaColor=[.85,.88,.93,1],physicsClientId=self.client)
        handle=p.createCollisionShape(p.GEOM_BOX,halfExtents=[.10,.025,.018],physicsClientId=self.client)
        hv=p.createVisualShape(p.GEOM_BOX,halfExtents=[.10,.025,.018],rgbaColor=[.12,.15,.18,1],physicsClientId=self.client)
        self.target=p.createMultiBody(baseMass=.03,baseCollisionShapeIndex=blade,baseVisualShapeIndex=visual,
            basePosition=[loc['xy'][0],side*2.15,.75],linkMasses=[.005],linkCollisionShapeIndices=[handle],
            linkVisualShapeIndices=[hv],linkPositions=[[-.26,0,0]],linkOrientations=[[0,0,0,1]],
            linkInertialFramePositions=[[0,0,0]],linkInertialFrameOrientations=[[0,0,0,1]],
            linkParentIndices=[0],linkJointTypes=[p.JOINT_FIXED],linkJointAxis=[[0,0,0]],physicsClientId=self.client)
        for _ in range(240):p.stepSimulation(physicsClientId=self.client)
        self.step_count=240;self._last_xy=self.pose()[:2];self.path=[self._last_xy]
        self.phase='idle';self.perceive()

    def box(self,half,position,color,collision=True):
        c=p.createCollisionShape(p.GEOM_BOX,halfExtents=half,physicsClientId=self.client) if collision else -1
        v=p.createVisualShape(p.GEOM_BOX,halfExtents=half,rgbaColor=color,physicsClientId=self.client)
        return p.createMultiBody(0,c,v,position,physicsClientId=self.client)

    def pose(self):
        xyz,q=p.getBasePositionAndOrientation(self.robot,physicsClientId=self.client)
        return [xyz[0],xyz[1],p.getEulerFromQuaternion(q)[2]]

    def motors(self,v,w):
        left,right=(v-w*.30)/.165,(v+w*.30)/.165
        p.setJointMotorControlArray(self.robot,self.wheels,p.VELOCITY_CONTROL,
            targetVelocities=[left,right,left,right],forces=[100]*4,physicsClientId=self.client)

    def step(self):
        p.stepSimulation(physicsClientId=self.client);self.step_count+=1
        xy=self.pose()[:2];self.distance_m+=math.dist(self._last_xy,xy);self._last_xy=xy
        if self.step_count%24==0:
            self.path.append(xy);self.perceive()
            if self.frame_callback:self.frame_callback()

    def event(self,kind,**data):
        self.events.append(dict(kind=kind,step=self.step_count,phase=self.phase,**data))

    def target_pose(self):
        return list(p.getBasePositionAndOrientation(self.target,physicsClientId=self.client)[0])

    def perceive(self):
        x,y,yaw=self.pose();target=self.target_pose();d=math.dist([x,y],target[:2])
        bearing=angle(math.atan2(target[1]-y,target[0]-x)-yaw)
        visible=False
        if d<=1.65 and abs(bearing)<=math.pi/4:
            eye=[x+.35*math.cos(yaw),y+.35*math.sin(yaw),1.05]
            hit=p.rayTest(eye,target,physicsClientId=self.client)[0][0]
            visible=hit==self.target
        if visible:
            location=min(LOCATIONS,key=lambda k:math.dist(LOCATIONS[k]['xy'],target[:2]))
            self.last_seen=dict(object_id='target_knife',category='kitchen_knife',position=[round(v,4) for v in target],
                location_id=location,observed_step=self.step_count)
            if not any(e['kind']=='target_detected' for e in self.events):self.event('target_detected',location_id=location)
        self.visible_now=visible
        # Fog-of-war rendering. Hidden geometry stays at its real physical pose.
        p.changeVisualShape(self.target,-1,rgbaColor=[.85,.88,.93,1 if self.last_seen else 0],physicsClientId=self.client)
        p.changeVisualShape(self.target,0,rgbaColor=[.12,.15,.18,1 if self.last_seen else 0],physicsClientId=self.client)

    def observation(self):
        pose=self.pose();v,w=p.getBaseVelocity(self.robot,physicsClientId=self.client)
        return dict(physics_step=self.step_count,robot_pose=[round(v,4) for v in pose],
            current_room=room_at(pose[:2]),known_map=public_map(),checked_locations=self.checked.copy(),
            target_observation=self.last_seen.copy() if self.last_seen else None,target_visible_now=self.visible_now,
            distance_to_observed_target_m=round(math.dist(pose[:2],self.last_seen['position'][:2]),4) if self.last_seen else None,
            robot_stopped=math.hypot(v[0],v[1])<.08 and abs(w[2])<.12,
            distance_travelled_m=round(self.distance_m,4),
            route_distances_m={k:round(route_distance(pose[:2],k),3) for k in LOCATIONS})

    def drive(self,waypoint,max_steps=4000,final_yaw=None):
        orienting=False
        for _ in range(max_steps):
            x,y,yaw=self.pose();distance=math.dist([x,y],waypoint)
            if distance<=.15:orienting=True
            if distance>.30:orienting=False
            desired=(final_yaw if final_yaw is not None else yaw) if orienting else math.atan2(waypoint[1]-y,waypoint[0]-x)
            error=angle(desired-yaw)
            if orienting and (final_yaw is None or abs(error)<.12):return True
            velocity=min(.85,1.5*distance)*max(0,math.cos(error)) if not orienting and abs(error)<.45 else 0
            self.motors(velocity,max(-1.8,min(1.8,2.5*error)));self.step()
            if self.distance_m>self.distance_budget_m:return False
        return False

    def search(self,location):
        if location not in LOCATIONS:raise ValueError('Unknown station')
        start,distance=self.step_count,self.distance_m
        self.phase='navigate';self.event('phase',location_id=location)
        reached=True
        for point in route(self.pose()[:2],location):
            if not self.drive(point):reached=False;break
        if reached:
            self.phase='inspect';self.event('phase',location_id=location)
            reached=self.drive(LOCATIONS[location]['xy'],max_steps=1800,final_yaw=LOCATIONS[location]['yaw'])
        self.motors(0,0)
        for _ in range(120):self.step()
        self.perceive()
        if reached:
            self.checked[location]=dict(observed_step=self.step_count,target_detected=bool(self.last_seen and self.last_seen['location_id']==location),scope='local_station_inspection')
            self.event('station_inspected',location_id=location,target_detected=self.checked[location]['target_detected'])
        self.phase='idle';self.event('phase',location_id=location)
        result=dict(skill='search',object_id='mobile_robot',target_id=location,success=reached,
            reason='inspected' if reached else 'motion_or_distance_limit',start_step=start,end_step=self.step_count,
            distance_m=round(self.distance_m-distance,4),target_detected=bool(self.last_seen))
        self.event('skill_result',**result)
        return result

    def render(self,width=960,height=540):
        view=p.computeViewMatrix([2,-6,10],[0,0,0],[0,0,1]);proj=p.computeProjectionMatrixFOV(58,width/height,.1,60)
        rgba=p.getCameraImage(width,height,view,proj,renderer=p.ER_TINY_RENDERER,shadow=0,physicsClientId=self.client)[2]
        image=Image.fromarray(np.asarray(rgba,dtype=np.uint8)[:,:,:3]);draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,width,37),fill=(10,25,42));draw.text((12,8),'When2Ask / Husky / known map + LOCAL range-FOV-LOS sensing',fill='white')
        matrix=np.asarray(proj).reshape(4,4,order='F')@np.asarray(view).reshape(4,4,order='F')
        def pixel(xy,z=.04):
            point=matrix@np.array([xy[0],xy[1],z,1]);point/=point[3]
            return ((point[0]+1)*width/2,(1-point[1])*height/2)
        if len(self.path[::3])>1:draw.line([pixel(x) for x in self.path[::3]],fill=(13,164,176),width=3)
        for room,xy in ROOMS.items():
            pos=pixel([xy[0],2.65]);draw.text(pos,room.replace('_',' ').upper(),fill=(20,43,68),anchor='mm')
        for key in self.checked:
            x,y=pixel(LOCATIONS[key]['xy']);draw.ellipse((x-4,y-4,x+4,y+4),fill=(25,160,100))
        x,y,yaw=self.pose();eye=[x+.35*math.cos(yaw),y+.35*math.sin(yaw),1.05]
        localview=p.computeViewMatrix(eye,[eye[0]+math.cos(yaw),eye[1]+math.sin(yaw),.9],[0,0,1])
        rgb=p.getCameraImage(240,150,localview,p.computeProjectionMatrixFOV(75,240/150,.05,20),renderer=p.ER_TINY_RENDERER,shadow=0,physicsClientId=self.client)[2]
        image.paste(Image.fromarray(np.asarray(rgb,dtype=np.uint8)[:,:,:3]),(width-252,48))
        draw.rectangle((width-252,48,width-12,69),fill=(10,25,42));draw.text((width-244,52),'ROBOT CAMERA',fill='white')
        draw.rectangle((0,height-28,width,height),fill=(10,25,42));draw.text((12,height-21),f'step {self.step_count} | {self.phase} | travelled {self.distance_m:.2f}m | inspected {len(self.checked)}/{len(LOCATIONS)}',fill='white')
        return image

    def close(self):
        if p.isConnected(self.client):p.disconnect(self.client)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
