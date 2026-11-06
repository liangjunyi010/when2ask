"""Execution-only navigation worker. Motor commands, never target pose resets."""
import base64
import hashlib
import io
import json
import os
import time
from pathlib import Path

from .console_transport import request
from .navigation_map import LOCATIONS
from .navigation_protocol import parse_action
from .navigation_task import make_sample
from .navigation_world import NavigationWorld

SOURCES=('navigation_world.py','navigation_map.py','navigation_task.py','navigation_protocol.py')


def run_physics_task(server,token_file,worker_id,job,speed=1,fps=6):
    for name in ('DEEPSEEK_API_KEY','TYPESAFE_API_KEY'):os.environ.pop(name,None)
    token=Path(token_file).read_text().strip()
    for name,expected in job['physics_signature'].items():
        if name not in SOURCES or hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Navigation controller/worker source mismatch')
    sample=make_sample(job['navigation_case'],job['unknown_preferences'])
    digest=hashlib.sha256(json.dumps(sample.scene(),sort_keys=True).encode()).hexdigest()
    if digest!=job['scene_sha256']:raise RuntimeError('Navigation map mismatch')
    seq=after=frame_seq=0;world=None;current_action=None;actions=[];controls={};termination='worker_error'

    def rpc(path,body):
        for attempt in range(3):
            try:return request(server,path,body,token=token,timeout=12)
            except (OSError,ValueError,RuntimeError):
                if attempt==2:raise
                time.sleep(.15*(attempt+1))

    def emit(kind,data):
        nonlocal seq
        seq+=1;result=rpc('/api/worker/event',dict(task_id=job['task_id'],worker_id=worker_id,seq=seq,kind=kind,data=data))
        controls.update(result);return result

    def frame():
        nonlocal frame_seq
        frame_seq+=1;buffer=io.BytesIO();world.render().save(buffer,'JPEG',quality=80);data=buffer.getvalue()
        obs=world.observation()
        return dict(seq=frame_seq,simulation_step=world.step_count,phase=world.phase,action=current_action,
            object_names={k:v['name'] for k,v in LOCATIONS.items()},width=960,height=540,
            source='PyBullet TinyRenderer',grasp_mode=None,sha256=hashlib.sha256(data).hexdigest(),
            jpeg=base64.b64encode(data).decode(),navigation=dict(distance_m=obs['distance_travelled_m'],
                checked=len(obs['checked_locations']),current_room=obs['current_room'],
                locally_detected=obs['target_observation'] is not None))

    try:
        world=NavigationWorld(sample);emit('ready',dict(observation=world.observation(),frame=frame(),pid=os.getpid()))
        while True:
            response=rpc('/api/worker/commands',dict(task_id=job['task_id'],worker_id=worker_id,after=after));controls.update(response)
            if response['cancelled'] or response['shutdown']:termination='cancelled_by_user';break
            if not response['commands']:continue # Absolutely no stepping during ASK or model inference.
            command=response['commands'][0];after=command['id']
            if command['kind']=='finalize':controls.update(command);termination=command['termination'];break
            if command['kind']=='inspect':
                emit('inspection',dict(command_id=after,observation=world.observation(),frame=frame()));continue
            if command['kind']!='action' or command['expected_step']!=world.step_count:raise ValueError('Invalid/stale navigation command')
            action=parse_action(command['action'])
            if action['kind']!='search':raise ValueError('Worker only executes search, not DONE')
            if len(actions)>=8 or world.distance_m>=36:raise ValueError('Navigation physical action budget exhausted')
            current_action=action;start_step=world.step_count;start=time.monotonic();last_frame=0

            def tick():
                nonlocal last_frame
                # Navigation uses real-time physics for every policy; tabletop speed is independent.
                delay=start+(world.step_count-start_step)*world.DT-time.monotonic()
                if delay>0:time.sleep(min(delay,.1))
                if time.monotonic()-last_frame>=1/min(fps,6):
                    last_frame=time.monotonic();emit('frame',dict(frame=frame(),command_id=after))
                    if controls.get('cancelled'):raise InterruptedError('cancelled_by_user')

            world.frame_callback=tick;result=world.search(action['location_id']);world.frame_callback=None;actions.append(result)
            emit('action_result',dict(command_id=after,result=result,observation=world.observation(),frame=frame(),pid=os.getpid()))
    except InterruptedError:termination='cancelled_by_user'
    except Exception as exc:
        try:emit('worker_error',dict(error=f'{type(exc).__name__}: {exc}'))
        except Exception:pass
    finally:
        if world:
            world.frame_callback=None
            try:emit('finalized',dict(evaluation=world.evaluate(controls.get('clarification_burden',0),actions,termination),
                observation=world.observation(),frame=frame(),execution_log=world.events,termination=termination,pid=os.getpid()))
            finally:world.close()
