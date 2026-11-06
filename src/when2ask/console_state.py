"""Authoritative task registry, idempotent answers and worker command/event IDs."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import queue
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from pathlib import Path

from .accounting import Audit, BudgetExceeded, SessionLedger
from .config import Config
from .console_samples import TEMPLATES, catalogue, demo_sample
from .study_protocol import disclosed_choices, public_roles, role_candidates
from .user_simulator import PreferenceResolver

LIVE_METHODS = ('llm_noask', 'llm_gate', 'jev_gate')
SCRIPTED_METHODS = ('scripted_ask', 'scripted_noask')
METHODS = LIVE_METHODS + SCRIPTED_METHODS
TERMINAL = ('done', 'error', 'cancelled')


class Cancelled(RuntimeError):
    pass


class Conflict(ValueError):
    pass


class ConsoleLedger(SessionLedger):
    def __init__(self, *args, **kwargs):
        self.thread_lock = threading.RLock()
        super().__init__(*args, **kwargs)

    @contextmanager
    def _state(self):
        with self.thread_lock:
            with super()._state() as state:
                yield state

    def start_batch(self, episode_ids):
        """Reserve all paired episodes atomically before publishing any tasks."""
        with self._state() as state:
            if state['episodes'] + len(episode_ids) > state['max_episodes']:
                raise BudgetExceeded('Comparison needs three remaining live episode slots')
            if state['attempts'] >= state['max_attempts']:
                raise BudgetExceeded('session_api_attempt_limit')
            if any(v.get('blocked') for v in state['backends'].values()):
                raise Conflict('A model backend is blocked in this session')
            state['episodes'] += len(episode_ids)
            state.setdefault('episode_ids', []).extend(episode_ids)


class Task:
    def __init__(self, options, output, config):
        self.id = uuid.uuid4().hex[:16]
        self.template = options['template']
        self.method = options['method']
        self.answer_mode = options['answer_mode']
        self.sample = demo_sample(self.template, options.get('unknown_preferences'), options.get('navigation_case'))
        self.unknown_preferences = len(self.sample.slots) - len(self.sample.initial_disclosed_slots)
        self.comparison_id = None
        self.created = time.time()
        self.clock_start = time.monotonic()
        self.started = None
        self.finished = None
        self.answer_wait_s = 0
        self.trace = []
        self._last_phase = None
        self.status = 'queued'
        self.error = None
        self.worker_id = None
        self.worker_pid = None
        self.worker_seq = 0
        self.observation = None
        self.frame = None
        self.pending = None
        self.answers = {}
        self.history = []
        self.turns = []
        self.actions = []
        self.events = []
        self.burden = 0
        self.gate = None
        self.round = 0
        self.cancel = False
        self.commands = []
        self.results = {}
        self.inspections = {}
        self.finalization = None
        self.goal_overrides = {}
        self.output = Path(output) / 'tasks' / self.id
        self.output.mkdir(parents=True, exist_ok=False)
        self.audit = Audit(self.id, config, path=self.output / 'api_attempts.jsonl')
        self.version = 0
        self.last_seen = time.monotonic()

    def public(self):
        from .console_review import review
        return copy.deepcopy(dict(id=self.id, template=self.template, template_name=TEMPLATES[self.template][0],
            method=self.method, answer_mode=self.answer_mode, status=self.status, created=self.created,
            evidence_kind='live_models_real_pybullet' if self.method in LIVE_METHODS else 'scripted_policy_real_pybullet',
            round=self.round, gate=self.gate, frame=self.frame, question=self.pending,review=self.audit.config.sanitize(review(self)),
            instruction=self.sample.u0, unknown_preferences=self.unknown_preferences,
            comparison_id=self.comparison_id, trace=self.trace[-60:],
            timing=dict(created=self.created, started=self.started, finished=self.finished,
                wall_time_s=(self.finished or time.time()) - self.created,
                answer_wait_s=self.answer_wait_s,
                queue_time_s=(self.started or self.finished or time.time()) - self.created),
            ask_turns=sum('question' in t for t in self.turns),
            returned_models=sorted({r['returned_model'] for r in self.audit.records if r.get('returned_model')}),
            history=self.history[-8:], actions=self.actions, burden=self.burden, cost=self.audit.summary(),
            evaluation=self.finalization.get('evaluation') if self.finalization else None,
            error=self.error, worker_id=self.worker_id, worker_pid=self.worker_pid, version=self.version,
            evaluation_protocol=('fixed_world_location' if self.template == 'find_and_approach' else
                'interactive_declared_preferences' if self.answer_mode == 'manual' else 'fixed_demo_preferences')))


class TaskManager:
    def __init__(self, output, *, config=None, allow_live=False, capacity=3, api_limit=60, live_episode_limit=6):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.config = config or Config.load()
        self.allow_live, self.capacity = allow_live, capacity
        self.ledger = ConsoleLedger(self.output / 'inference', api_limit, live_episode_limit)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.tasks = {}
        self.workers = {}
        self.create_keys = {}
        self.comparisons = {}
        self.comparison_keys = {}
        self.sequence = 0
        self.stream = deque(maxlen=100)
        self.closed = False
        self.completed = {}
        for file in self.output.glob('tasks/*/final_view.json'):
            row=json.loads(file.read_text())
            if row.get('status') in TERMINAL:
                row.update(archived_readonly=True,comparison_id=None)
                self.completed[row['id']]=row
        package = Path(__file__).parent
        self.physics_signature = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in
            ('skills.py', 'environment.py', 'diverse_world.py', 'study_evaluator.py', 'console_samples.py')}
        from .navigation_worker import SOURCES
        self.navigation_signature = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in SOURCES}

    def metadata(self):
        return dict(templates=catalogue(), methods=list(METHODS), live_enabled=self.allow_live,
                    concurrency=self.capacity, budget=self.ledger.snapshot(),
                    models=self.config.public_config(), protocol_version=2)

    def log(self, task, kind, **data):
        task.trace.append(dict(seq=len(task.trace) + 1, kind=kind,
            elapsed_ms=round((time.monotonic() - task.clock_start) * 1000),
            round=task.round, simulation_step=(task.frame or {}).get('simulation_step'), **data))

    def public_tasks(self):
        return list({**self.completed,**{k:t.public() for k,t in self.tasks.items()}}.values())

    def publish(self, task):
        # Call with the condition lock held. Frame and its physical metadata
        # are stored in one object, never pieced together by browser timers.
        if task.status in TERMINAL and task.finished is None:
            task.finished = time.time()
        task.version += 1
        if task.status in TERMINAL:
            row=self.config.sanitize(task.public())
            (task.output/'final_view.json').write_text(json.dumps(row,ensure_ascii=False)+'\n')
            (task.output/'review.json').write_text(json.dumps(row['review'],indent=2,ensure_ascii=False)+'\n')
        self.sequence += 1
        self.stream.append(dict(id=self.sequence, type='task', task=task.public()))
        self.changed.notify_all()
        if task.comparison_id and task.status in TERMINAL:
            self.persist_comparison(task.comparison_id)

    @staticmethod
    def validate_options(options):
        if not isinstance(options, dict) or not {'template', 'method', 'answer_mode'} <= set(options) or set(options) - {'template', 'method', 'answer_mode', 'unknown_preferences', 'navigation_case'}:
            raise ValueError('Choose a template, method and answer mode')
        if options['template'] not in TEMPLATES or options['method'] not in METHODS or options['answer_mode'] not in ('auto', 'manual'):
            raise ValueError('Invalid task options')
        if 'unknown_preferences' in options and (type(options['unknown_preferences']) is not int or not 0 <= options['unknown_preferences'] <= 3):
            raise ValueError('Unknown preferences must be an integer from 0 to 3')
        if options['template'] == 'find_and_approach':
            if options.get('unknown_preferences',1) not in (0,1) or options.get('navigation_case','case_b') not in ('case_a','case_b','case_c'):
                raise ValueError('Navigation has 0/1 unknown location fact and case_a/b/c')
        elif 'navigation_case' in options:
            raise ValueError('navigation_case only applies to navigation')

    def check_live(self, methods):
        if not self.allow_live:
            raise Conflict('Live API execution is disabled on this server')
        if not self.config.deepseek_key or ('jev_gate' in methods and not self.config.typesafe_key):
            raise Conflict('Required backend is not configured')

    def create(self, options, key):
        self.validate_options(options)
        if not isinstance(key, str) or not 8 <= len(key) <= 100:
            raise ValueError('A request ID is required')
        signature = json.dumps(options, sort_keys=True)
        with self.changed:
            if key in self.create_keys:
                old, task_id = self.create_keys[key]
                if signature != old:
                    raise Conflict('Request ID already used for different options')
                return self.tasks[task_id].public()
            if len(self.tasks) >= 100 or sum(t.status == 'queued' for t in self.tasks.values()) >= 20:
                raise Conflict('Task queue is full')
            if options['method'] in LIVE_METHODS:
                self.check_live([options['method']])
            task = Task(options, self.output, self.config)
            if task.method in LIVE_METHODS:
                self.ledger.start_episode(task.id)
                task.audit.session = self.ledger
            self.tasks[task.id] = task
            self.create_keys[key] = (signature, task.id)
            self.publish(task)
            return task.public()

    def create_comparison(self, options, key):
        if not isinstance(options, dict) or not {'template', 'unknown_preferences'} <= set(options) or set(options)-{'template','unknown_preferences','navigation_case'}:
            raise ValueError('Comparison requires template and unknown_preferences')
        self.validate_options(dict(options, method='llm_noask', answer_mode='auto'))
        if not isinstance(key, str) or not 8 <= len(key) <= 100:
            raise ValueError('A request ID is required')
        signature = json.dumps(options, sort_keys=True)
        with self.changed:
            if key in self.comparison_keys:
                previous, cid = self.comparison_keys[key]
                if previous != signature:
                    raise Conflict('Request ID already used for a different comparison')
                return self.comparison(cid)
            self.check_live(LIVE_METHODS)
            if len(self.tasks) + 3 > 100 or sum(t.status == 'queued' for t in self.tasks.values()) + 3 > 20:
                raise Conflict('Not enough queue capacity for all three methods')
            tasks = [Task(dict(options, method=method, answer_mode='auto'), self.output, self.config) for method in LIVE_METHODS]
            try:
                self.ledger.start_batch([t.id for t in tasks])
            except Exception:
                for t in tasks:
                    t.output.rmdir()  # No tasks were published and no calls were made.
                raise
            cid = uuid.uuid4().hex[:16]
            from .study_agents import prompt_hashes
            if options['template'] == 'find_and_approach':
                from .navigation_agents import prompt_hashes
            sample = tasks[0].sample
            group = dict(id=cid, created=time.time(), options=copy.deepcopy(options),
                task_ids=[t.id for t in tasks], partition='interactive_demo_on_dev_layout',
                source_sample_id=sample.sample_id, scene_seed=sample.scene_seed,
                public_scene_sha256=hashlib.sha256(json.dumps(dict(scene=sample.scene(), instruction=sample.u0), sort_keys=True).encode()).hexdigest(),
                planner_configuration=self.config.public_config(), prompt_hashes=prompt_hashes(),
                physics_signature=self.navigation_signature if options['template']=='find_and_approach' else self.physics_signature, answer_mode='auto',
                evaluation_protocol='fixed_world_location' if options['template']=='find_and_approach' else 'fixed_demo_preferences',
                note='One paired interactive instance; not a benchmark ranking.')
            self.comparisons[cid] = group
            self.comparison_keys[key] = (signature, cid)
            for task in tasks:
                task.comparison_id = cid
                task.audit.session = self.ledger
                self.tasks[task.id] = task
                self.log(task, 'queued', comparison_id=cid)
            path = self.output / 'comparisons'
            path.mkdir(exist_ok=True)
            (path / f'{cid}.manifest.json').write_text(json.dumps(group, indent=2) + '\n')
            for task in tasks:
                self.publish(task)
            self.sequence += 1
            self.stream.append(dict(id=self.sequence, type='comparison', comparison=self.comparison(cid)))
            self.changed.notify_all()
            return self.comparison(cid)

    def comparison(self, cid):
        with self.lock:
            group = self.comparisons[cid]
            rows = []
            for tid in group['task_ids']:
                task = self.tasks[tid]
                evaluation = (task.finalization or {}).get('evaluation')
                rows.append(dict(task_id=tid, method=task.method, status=task.status,
                    task_success=evaluation['task_success'] if evaluation else None,
                    burden=task.burden, ask_turns=sum('question' in t for t in task.turns),
                    robot_actions=len(task.actions), physical_successes=sum(a['success'] for a in task.actions),
                    distance_m=(task.observation or {}).get('distance_travelled_m'),
                    checked_locations=len((task.observation or {}).get('checked_locations',{})) if task.template=='find_and_approach' else None,
                    cost=task.audit.summary(), wall_time_s=(task.finished or time.time()) - task.created,
                    queue_time_s=(task.started or task.finished or time.time()) - task.created,
                    returned_models=sorted({a['returned_model'] for a in task.audit.records if a.get('returned_model')}),
                    termination_reason=task.termination_reason if hasattr(task, 'termination_reason') else None,
                    error=task.error))
            return dict(group, rows=rows, status='complete' if all(r['status'] in TERMINAL for r in rows) else 'running')

    def persist_comparison(self, cid):
        result = self.comparison(cid)
        if result['status'] != 'complete':
            return
        path = self.output / 'comparisons'
        (path / f'{cid}.json').write_text(json.dumps(self.config.sanitize(result), indent=2) + '\n')
        with (path / f'{cid}.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['method', 'status', 'task_success', 'burden', 'ask_turns', 'robot_actions',
                'distance_m','checked_locations','api_latency_ms', 'wall_time_s', 'deepseek_input_tokens', 'deepseek_output_tokens', 'jev_input_tokens', 'jev_output_tokens', 'api_attempts'], lineterminator='\n')
            writer.writeheader()
            for row in result['rows']:
                cost = row['cost']
                writer.writerow({**{k: row[k] for k in ('method', 'status', 'task_success', 'burden', 'ask_turns', 'robot_actions', 'wall_time_s','distance_m','checked_locations')},
                    'api_latency_ms': cost['api_latency_ms'], 'api_attempts': cost['api_attempts'],
                    **{f'{b}_{k}': cost[b][k] for b in ('deepseek', 'jev') for k in ('input_tokens', 'output_tokens')}})
        self.sequence += 1
        self.stream.append(dict(id=self.sequence, type='comparison', comparison=result))

    def clarifications(self):
        with self.lock:
            return sorted([dict(task_id=t.id, method=t.method, template=t.template,
                question=copy.deepcopy(t.pending), answer_mode=t.answer_mode) for t in self.tasks.values()
                if t.status == 'waiting_answer' and t.pending], key=lambda q: q['question'].get('created', 0))

    def claim(self, worker_id, capacity):
        if not isinstance(worker_id, str) or not 1 <= len(worker_id) <= 100:
            raise ValueError('Invalid worker ID')
        if not 1 <= capacity <= 8:
            raise ValueError('Invalid worker capacity')
        with self.changed:
            self.workers[worker_id] = dict(id=worker_id, capacity=capacity, last_seen=time.time())
            active = [t for t in self.tasks.values() if t.worker_id and t.status not in TERMINAL]
            if len(active) >= self.capacity or sum(t.worker_id == worker_id for t in active) >= capacity:
                return None
            task = next((t for t in self.tasks.values() if t.status == 'queued'), None)
            if task is None:
                return None
            task.worker_id, task.status = worker_id, 'initializing'
            task.started = time.time()
            self.log(task, 'initializing', worker_id=worker_id)
            self.publish(task)
            from .console_agent import run_agent
            threading.Thread(target=run_agent, args=(self, task), name='agent-' + task.id, daemon=True).start()
            scene = task.sample.scene()
            return dict(task_id=task.id, template=task.template, unknown_preferences=task.unknown_preferences, source_sample_id=task.sample.sample_id,
                        navigation_case=getattr(task.sample,'case_id',None),
                        physics_signature=self.navigation_signature if task.template=='find_and_approach' else self.physics_signature,
                        scene_sha256=hashlib.sha256(json.dumps(scene, sort_keys=True).encode()).hexdigest())

    def owned(self, task_id, worker_id):
        task = self.tasks[task_id]
        if task.worker_id != worker_id:
            raise Conflict('Task belongs to a different execution worker')
        return task

    def worker_event(self, value):
        with self.changed:
            task = self.owned(value['task_id'], value['worker_id'])
            if value.get('kind') not in ('ready', 'frame', 'inspection', 'action_result', 'finalized', 'worker_error') or not isinstance(value.get('data'), dict):
                raise ValueError('Invalid worker event kind/data')
            seq = value['seq']
            if not isinstance(seq, int) or seq < 1:
                raise ValueError('Invalid worker event sequence')
            if seq <= task.worker_seq:
                return dict(accepted=False, **self.controls(task))
            if seq != task.worker_seq + 1:
                raise Conflict('Worker event gap; resend the missing event')
            task.worker_seq, task.last_seen = seq, time.monotonic()
            kind, data = value['kind'], value['data']
            if kind in ('ready', 'frame', 'inspection', 'action_result', 'finalized'):
                if data.get('frame'):
                    task.frame = data['frame']
                if data.get('observation'):
                    task.observation = data['observation']
                if data.get('pid'):
                    task.worker_pid = data['pid']
                if kind == 'action_result':
                    task.results[data['command_id']] = data
                    task.actions.append(data['result'])
                    self.log(task, 'action_result', result=data['result'])
                if kind == 'finalized':
                    task.finalization = data
                if kind == 'inspection':
                    task.inspections[data['command_id']] = data
                if kind == 'frame' and task.status not in TERMINAL and not task.cancel:
                    task.status = 'executing'
                    phase = task.frame.get('phase')
                    signature = (phase, json.dumps(task.frame.get('action'), sort_keys=True))
                    if signature != task._last_phase:
                        self.log(task, 'physical_phase', phase=phase, action=task.frame.get('action'))
                        task._last_phase = signature
            elif kind == 'worker_error':
                task.error = self.config.sanitize(data.get('error', 'Execution worker failed'))
            else:
                raise ValueError('Unknown worker event')
            task.events.append(dict(kind=kind, seq=seq, step=(task.frame or {}).get('simulation_step'), command_id=data.get('command_id')))
            self.publish(task)
            return dict(accepted=True, **self.controls(task))

    @staticmethod
    def controls(task):
        return dict(cancelled=task.cancel, clarification_burden=task.burden,
                    evaluation_overrides=copy.deepcopy(task.goal_overrides))

    def command(self, task, kind, **data):
        with self.changed:
            item = dict(id=len(task.commands) + 1, kind=kind, **data)
            task.commands.append(item)
            self.changed.notify_all()
            return item['id']

    def poll_commands(self, task_id, worker_id, after):
        if type(after) is not int or after < 0:
            raise ValueError('Invalid command cursor')
        with self.changed:
            task = self.owned(task_id, worker_id)
            self.changed.wait_for(lambda: len(task.commands) > after or task.cancel or self.closed, timeout=8)
            task.last_seen = time.monotonic()
            return dict(commands=task.commands[after:after + 1], shutdown=self.closed, **self.controls(task))

    def wait(self, task, predicate, *, timeout=120, allow_cancel=False):
        deadline = time.monotonic() + timeout
        with self.changed:
            while not predicate():
                if task.cancel and not allow_cancel:
                    raise Cancelled('cancelled_by_user')
                if task.error and not allow_cancel:
                    raise RuntimeError(task.error)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Worker or answer deadline exceeded')
                self.changed.wait(min(remaining, 1))

    def answer(self, task_id, question_id, response=None, *, source='human'):
        with self.changed:
            task = self.tasks[task_id]
            if question_id in task.answers:
                previous = task.answers[question_id]
                if source == previous['source'] and (source == 'auto' or response == previous['response'] or
                        previous.get('input_text') is not None and response=={'text':previous['input_text']}):
                    return dict(accepted=True, duplicate=True)
                raise Conflict('Question has already been answered')
            if task.cancel or task.status != 'waiting_answer' or not task.pending or task.pending['id'] != question_id:
                raise Conflict('This question is no longer pending')
            question = task._question
            input_text=None
            if source not in ('auto', 'human'):
                raise ValueError('Unknown answer source')
            if source=='human' and isinstance(response,dict) and set(response)=={'text'}:
                from .console_answers import text_answer
                input_text=response['text'];response=text_answer(task.pending,input_text)
            if task.template == 'find_and_approach':
                from .navigation_protocol import auto_answer, validate_answer
                if source == 'auto':
                    response = auto_answer(task.sample)
                else:
                    if task.answer_mode != 'manual':
                        raise Conflict('This task uses automatic responses')
                    validate_answer(response)
                # World facts stay fixed even if an operator supplies a wrong hint.
            elif source == 'auto':
                response, _ = PreferenceResolver(task.sample.slots, {**task.sample.theta_star, **task.goal_overrides}).answer(question)
            else:
                if task.answer_mode != 'manual':
                    raise Conflict('This task uses automatic responses')
                self.validate_answer(task, response)
            task.answers[question_id] = dict(response=copy.deepcopy(response), source=source,input_text=input_text)
            task.answer_wait_s += max(0, time.time() - task.pending.get('created', time.time()))
            self.log(task, 'answer_received', question_id=question_id, source=source)
            task.pending = None
            task.status = 'answer_received'
            self.publish(task)
            return dict(accepted=True, duplicate=False)

    @staticmethod
    def validate_answer(task, response):
        question = task._question
        roles = question.roles()
        if not isinstance(response, dict):
            raise ValueError('Answer must be structured JSON')
        if question.type == 'confirm':
            values = response.get('confirmations')
            if set(response) != {'confirmations'} or not isinstance(values, list) or len(values) != len(question.requests):
                raise ValueError('Confirm each requested role exactly once')
            expected = {(r['role'], r['candidate_id']) for r in question.requests}
            if any(not isinstance(r, dict) or set(r) != {'role', 'candidate_id', 'confirmed'} for r in values):
                raise ValueError('Confirmations may contain only the requested role, candidate and boolean')
            if {(r.get('role'), r.get('candidate_id')) for r in values} != expected or any(type(r.get('confirmed')) is not bool for r in values):
                raise ValueError('Invalid confirmation answer')
        else:
            choices = response.get('choices')
            if set(response) != {'choices'} or not isinstance(choices, dict) or set(choices) != roles:
                raise ValueError('Answer only the roles requested by this question')
            if any(value not in role_candidates(task._question_state, role) for role, value in choices.items()):
                raise ValueError('Choose a visible candidate')
        known = disclosed_choices(task._question_state)
        if question.type == 'confirm':
            if any(r['role'] in known and r['confirmed'] != (known[r['role']] == r['candidate_id']) for r in response['confirmations']):
                raise ValueError('A previously disclosed choice is fixed for this task')
        elif any(role in known and value != known[role] for role, value in response['choices'].items()):
            raise ValueError('A previously disclosed choice is fixed for this task')

    def cancel_task(self, task_id):
        with self.changed:
            task = self.tasks[task_id]
            if task.status not in TERMINAL:
                task.cancel = True
                task.pending = None
                task.status = 'cancelled' if task.worker_id is None else 'cancelling'
                if task.worker_id is None:
                    (task.output / 'episode.json').write_text(json.dumps(dict(episode_id=task.id,
                        partition='interactive_demo', method=task.method, termination_reason='cancelled_before_start',
                        evaluation=None, cost=task.audit.summary(),review=task.public()['review'])) + '\n')
                self.publish(task)
            return task.public()
