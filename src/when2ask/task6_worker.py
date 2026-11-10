"""Isolated physical worker for new tasks; reuses controller RPC and real rendering."""
import base64
import hashlib
import io
import json
import os
import time
from pathlib import Path

from .config import ROOT
from .console_transport import request
from .task6_spec import SOURCES,make_sample


def run_physics_task(server,token_file,worker_id,job,speed=3,fps=8):
    for key in ('DEEPSEEK_API_KEY','TYPESAFE_API_KEY'):os.environ.pop(key,None)
    from .task6_world import make_world
    from .task6_protocol import action,payload,names
    from .task6_evaluator import evaluate
    from .recording import Recorder
    for name,digest in job['physics_signature'].items():
        if name not in SOURCES or hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()!=digest:raise RuntimeError('New task controller/worker version mismatch')
    sample=make_sample(job['template'],job.get('unknown_preferences'))
    if hashlib.sha256(json.dumps(sample.scene(),sort_keys=True).encode()).hexdigest()!=job['scene_sha256']:raise RuntimeError('New task scene mismatch')
    token=Path(token_file).read_text().strip();seq=after=frame_seq=0;world=None;recorder=None;current=None;actions=[];controls={};termination='worker_error'
    output=ROOT/'outputs/local_console/task6_worker_v1'/job['task_id'];output.mkdir(parents=True,exist_ok=False)
    def rpc(path,data):
        for i in range(3):
            try:return request(server,path,data,token=token,timeout=12)
            except (OSError,ValueError,RuntimeError):
                if i==2:raise
                time.sleep(.15*(i+1))
    def emit(kind,data):
        nonlocal seq
        seq+=1;result=rpc('/api/worker/event',dict(task_id=job['task_id'],worker_id=worker_id,seq=seq,kind=kind,data=data));controls.update(result);return result
    def frame():
        nonlocal frame_seq
        frame_seq+=1;image=world.render();buffer=io.BytesIO();image.save(buffer,'JPEG',quality=80);data=buffer.getvalue();obs=world.observation()
        phases=[e for e in world.events if e['kind'] in ('phase','grasp','release')]
        phase=world.phase if sample.template_id=='patrol_return' else phases[-1].get('phase',phases[-1]['kind']) if phases else 'idle'
        packet=dict(seq=frame_seq,simulation_step=world.step_count,phase=phase,action=current,object_names=names(obs),
            width=image.width,height=image.height,source='PyBullet TinyRenderer',grasp_mode=None if sample.template_id=='patrol_return' else 'constraint',
            sha256=hashlib.sha256(data).hexdigest(),jpeg=base64.b64encode(data).decode())
        if sample.template_id=='patrol_return':packet['navigation']=dict(distance_m=obs['distance_travelled_m'],checked=len(obs['checked_locations']),current_room=obs['current_room'],locally_detected=False)
        return packet
    try:
        world=make_world(sample);recorder=Recorder(world,stride=48);recorder.label=sample.template_id;recorder.capture()
        world.render().save(output/'scene.png');emit('ready',dict(observation=world.observation(),frame=frame(),pid=os.getpid()))
        while True:
            response=rpc('/api/worker/commands',dict(task_id=job['task_id'],worker_id=worker_id,after=after));controls.update(response)
            if response['cancelled'] or response['shutdown']:termination='cancelled_by_user';break
            if not response['commands']:continue # No physics during model inference or ASK.
            command=response['commands'][0];after=command['id']
            if command['kind']=='finalize':controls.update(command);termination=command['termination'];break
            if command['kind']=='inspect':emit('inspection',dict(command_id=after,observation=world.observation(),frame=frame()));continue
            if command['kind']!='action' or command['expected_step']!=world.step_count:raise ValueError('Invalid/stale new task action')
            current=action(command['action'],payload(sample.u0,world.observation(),[]));controls.update(command)
            start_step,start_wall,last=world.step_count,time.monotonic(),0.;recorder.label=current['kind']+' '+str(current.get('object_id',current.get('location_id',current.get('code',''))))
            def tick():
                nonlocal last
                if world.step_count%48:return
                recorder.on_step()
                target=start_wall+(world.step_count-start_step)*world.DT/speed
                delay=target-time.monotonic()
                if delay>0:time.sleep(min(delay,.1))
                if time.monotonic()-last>=1/fps:
                    last=time.monotonic();emit('frame',dict(frame=frame(),command_id=after))
                    if controls.get('cancelled'):raise RuntimeError('cancelled_by_user')
            world.frame_callback=tick
            physical=world.execute(current);world.frame_callback=None;actions.append(physical);recorder.capture()
            emit('action_result',dict(command_id=after,result=physical,observation=world.observation(),frame=frame(),pid=os.getpid()))
    except Exception as exc:
        termination='worker_error'
        try:emit('worker_error',dict(error=f'{type(exc).__name__}: {exc}'))
        except Exception:pass
    finally:
        if world:
            world.frame_callback=None
            try:
                result=evaluate(world,sample,burden=controls.get('clarification_burden',0),actions=actions,termination=termination,overrides=controls.get('evaluation_overrides'))
                world.render().save(output/'final.png');recorder.label='FINAL success='+str(result['task_success']);recorder.capture(1200)
                recording=recorder.save(output/'demo.gif')
                artifacts=dict(directory=str(output),recording=recording,scope='Real physics frames; API/ASK wall time is not represented. Full interaction is in episode turns.')
                (output/'physical_trace.json').write_text(json.dumps(dict(actions=actions,execution_log=world.events,
                    checkpoints=getattr(world,'checkpoints',None),evaluation=result,recording=recording),indent=2)+'\n')
                emit('finalized',dict(evaluation=result,observation=world.observation(),frame=frame(),execution_log=world.events,artifacts=artifacts,termination=termination,pid=os.getpid()))
            finally:world.close()
