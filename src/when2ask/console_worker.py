"""Execution-only worker: independent process per Bullet world, JSON over HTTP.

No LLM clients or provider credentials are needed on this machine.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import multiprocessing as mp
import os
import time
import uuid
from dataclasses import replace
from pathlib import Path

from .console_samples import demo_sample
from .console_transport import request


class WorkerCancelled(RuntimeError):
    pass


def run_physics_task(server, token_file, worker_id, job, speed=3.0, fps=8):
    if job['template'] == 'find_and_approach':
        from .navigation_worker import run_physics_task as navigation_worker
        return navigation_worker(server, token_file, worker_id, job, speed=1, fps=fps)
    # Spawned process only: do not propagate any model credential environment.
    for name in ('DEEPSEEK_API_KEY', 'TYPESAFE_API_KEY'):
        os.environ.pop(name, None)
    from .diverse_world import DiverseEnvironment, DiverseSkills
    from .study_evaluator import evaluate_study
    from .study_protocol import StudyAction, observe
    token = Path(token_file).read_text().strip()
    for name, expected in job['physics_signature'].items():
        if name not in ('skills.py', 'environment.py', 'diverse_world.py', 'study_evaluator.py', 'console_samples.py'):
            raise ValueError('Unknown physics source in worker handshake')
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Controller/worker physics source versions differ')
    sample = demo_sample(job['template'], job.get('unknown_preferences'))
    actual_hash = hashlib.sha256(json.dumps(sample.scene(), sort_keys=True).encode()).hexdigest()
    if actual_hash != job['scene_sha256']:
        raise RuntimeError('Controller/worker scene versions differ')
    seq, after, frame_seq = 0, 0, 0
    env, current_action = None, None
    actions = []
    controls = dict(evaluation_overrides={}, clarification_burden=0)
    termination = 'worker_error'

    def rpc(path, body):
        last = None
        for attempt in range(3):
            try:
                return request(server, path, body, token=token, timeout=12)
            except (OSError, ValueError, RuntimeError) as exc:
                last = exc
                time.sleep(.15 * (attempt + 1))
        raise RuntimeError('Controller connection unavailable') from last

    def emit(kind, data):
        nonlocal seq
        seq += 1
        result = rpc('/api/worker/event', dict(task_id=job['task_id'], worker_id=worker_id, seq=seq, kind=kind, data=data))
        controls.update(result)
        return result

    def observation():
        return observe(env, sample.u0, []).observation

    def frame():
        nonlocal frame_seq
        frame_seq += 1
        image = env.render(640, 480)
        buffer = io.BytesIO()
        image.save(buffer, 'JPEG', quality=78)
        data = buffer.getvalue()
        events = [e for e in env.events if e['kind'] in ('phase', 'grasp', 'release')
                  and current_action and e.get('object_id') == current_action.get('object_id')]
        phase = events[-1].get('phase', events[-1]['kind']) if events else None
        names = {k: f"{v.color} {v.category}" for k, v in env.objects.items()}
        if 'box' in names:
            names['box'] = 'box'
        return dict(seq=frame_seq, simulation_step=env.step_count, phase=phase,
                    action=current_action, object_names=names, width=640, height=480,
                    source='PyBullet TinyRenderer', grasp_mode='constraint',
                    sha256=hashlib.sha256(data).hexdigest(), jpeg=base64.b64encode(data).decode())

    try:
        env = DiverseEnvironment(seed=sample.scene_seed, scene_spec=sample.scene(), gui=False)
        skills = DiverseSkills(env)
        emit('ready', dict(observation=observation(), frame=frame(), pid=os.getpid()))
        while True:
            response = rpc('/api/worker/commands', dict(task_id=job['task_id'], worker_id=worker_id, after=after))
            controls.update(response)
            if response['cancelled'] or response['shutdown']:
                termination = 'cancelled_by_user'
                break
            if not response['commands']:
                continue  # No stepSimulation here: questions freeze physics.
            command = response['commands'][0]
            after = command['id']
            if command['kind'] == 'finalize':
                controls.update(command)
                termination = command['termination']
                break
            if command['kind'] == 'inspect':
                emit('inspection', dict(command_id=command['id'], observation=observation(), frame=frame()))
                continue
            if command['kind'] != 'action':
                raise ValueError('Unsupported execution command')
            if command['expected_step'] != env.step_count:
                raise ValueError('Stale action observation; refusing to execute')
            state = observe(env, sample.u0, [])
            action = StudyAction.parse(command['action'], state)
            if action.kind == 'DONE':
                raise ValueError('Worker action endpoint does not execute DONE')
            current_action = action.to_dict()
            controls.update(command)
            start_step, start_wall, last_frame = env.step_count, time.monotonic(), 0.0

            def tick():
                nonlocal last_frame
                if env.step_count % 24:
                    return
                target = start_wall + (env.step_count - start_step) * env.DT / speed
                delay = target - time.monotonic()
                if delay > 0:
                    time.sleep(min(delay, .1))
                if time.monotonic() - last_frame >= 1 / fps:
                    last_frame = time.monotonic()
                    emit('frame', dict(frame=frame(), command_id=command['id']))
                    if controls.get('cancelled'):
                        raise WorkerCancelled()

            env.frame_callback = tick
            physical = (skills.pick_place(action.object_id, action.target_id, action.relation)
                        if action.kind == 'pick_place' else skills.cover(action.object_id, action.target_id))
            env.frame_callback = None
            result = physical.to_dict()
            actions.append(result)
            emit('action_result', dict(command_id=command['id'], result=result,
                                      observation=observation(), frame=frame(), pid=os.getpid()))
    except WorkerCancelled:
        termination = 'cancelled_by_user'
    except Exception as exc:
        termination = 'worker_error'
        try:
            emit('worker_error', dict(error=f'{type(exc).__name__}: {exc}'))
        except Exception:
            pass
    finally:
        if env is not None:
            env.frame_callback = None
            try:
                theta = {**sample.theta_star, **controls.get('evaluation_overrides', {})}
                evaluated_sample = replace(sample, theta_star=theta).validate()
                evaluation = evaluate_study(env, evaluated_sample, clarification_burden=controls.get('clarification_burden', 0),
                                            actions=actions, termination=termination)
                emit('finalized', dict(evaluation=evaluation, observation=observation(), frame=frame(),
                                       execution_log=env.events, termination=termination, pid=os.getpid()))
            finally:
                env.close()


def worker_loop(server, token_file, *, capacity=3, speed=3.0, fps=8):
    token = Path(token_file).read_text().strip()
    worker_id = 'worker-' + uuid.uuid4().hex[:12]
    context = mp.get_context('spawn')
    children = {}
    last_heartbeat = 0
    try:
        while True:
            if time.monotonic() - last_heartbeat > 2:
                request(server, '/api/worker/heartbeat', dict(worker_id=worker_id, capacity=capacity), token=token)
                last_heartbeat = time.monotonic()
            for task_id, process in list(children.items()):
                if not process.is_alive():
                    process.join()
                    request(server, '/api/worker/exited', dict(task_id=task_id, worker_id=worker_id), token=token)
                    del children[task_id]
            if len(children) < capacity:
                job = request(server, '/api/worker/claim', dict(worker_id=worker_id, capacity=capacity), token=token)['job']
                if job:
                    process = context.Process(target=run_physics_task,
                        args=(server, token_file, worker_id, job, speed, fps), name='bullet-' + job['task_id'])
                    process.start()
                    children[job['task_id']] = process
            time.sleep(.2)
    except (KeyboardInterrupt, ConnectionError, OSError):
        pass
    finally:
        for process in children.values():
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Execution worker; no model API credentials required')
    parser.add_argument('--server', default='http://127.0.0.1:8877')
    parser.add_argument('--token-file', required=True)
    parser.add_argument('--capacity', type=int, default=3)
    parser.add_argument('--speed', type=float, default=3)
    parser.add_argument('--fps', type=int, default=8)
    args = parser.parse_args(argv)
    if not 1 <= args.capacity <= 8 or not .1 <= args.speed <= 10 or not 1 <= args.fps <= 20:
        parser.error('Invalid capacity, simulation speed or image rate')
    worker_loop(args.server, args.token_file, capacity=args.capacity, speed=args.speed, fps=args.fps)
