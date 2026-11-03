"""Offline console contracts. No provider HTTP calls; synthetic transport inputs
are unit tests and never included in console/demo experiment reports.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from when2ask.accounting import BudgetExceeded
from when2ask.config import Config
from when2ask.console_policy import ConsoleScriptedGate, ConsoleScriptedPlanner
from when2ask.console_samples import demo_sample
from when2ask.console_server import ConsoleHTTPServer
from when2ask.console_state import Conflict, ConsoleLedger, TaskManager
from when2ask.console_transport import WireError, request
from when2ask.diverse_world import DiverseEnvironment
from when2ask.protocol import public_payload
from when2ask.study_protocol import StudyQuestion, observe, role_candidates


@pytest.fixture
def manager(tmp_path):
    return TaskManager(tmp_path, config=Config(deepseek_key='unit-test-private-sentinel'), capacity=2)


@pytest.fixture(scope='module')
def public_state():
    sample = demo_sample('pack_and_cover')
    with DiverseEnvironment(seed=sample.scene_seed, scene_spec=sample.scene()) as env:
        return observe(env, sample.u0, [])


def create(manager, mode='manual', key='unit-request-0001'):
    row = manager.create(dict(template='pack_and_cover', method='scripted_ask', answer_mode=mode), key)
    return manager.tasks[row['id']]


def pending(manager, state, key='unit-request-0001'):
    task = create(manager, key=key)
    question = StudyQuestion.parse(dict(type='select', text='Which block?', requests=[
        dict(role='block', candidate_ids=role_candidates(state, 'block'))]), state)
    task._question, task._question_state = question, state
    task.status, task.pending = 'waiting_answer', dict(id='unit-question-' + task.id)
    return task


def test_demo_instance_keeps_initial_private_choices_off_the_wire(manager):
    task = create(manager)
    wire = json.dumps(task.public())
    for key in ('theta_star', 'goal_overrides', 'slots', 'unit-test-private-sentinel'):
        assert key not in wire
    assert task.sample.partition == 'dev'
    assert task.sample.initial_disclosed_slots == ['cup_choice']


def test_changing_unrevealed_truth_does_not_change_model_state(public_state):
    sample = demo_sample('pack_and_cover')
    altered = replace(sample, theta_star={**sample.theta_star,
        'block_choice': next(k for k in sample.slots['block_choice']['candidate_ids'] if k != sample.theta_star['block_choice'])})
    assert sample.u0 == altered.u0
    assert public_payload(public_state)['instruction'] == altered.u0
    assert set(public_payload(public_state)) == {'instruction', 'observation', 'history'}


def test_launch_retry_is_idempotent(manager):
    first = create(manager)
    second = create(manager)
    assert first is second and len(manager.tasks) == 1
    with pytest.raises(Conflict):
        manager.create(dict(template='pack_and_cover', method='scripted_noask', answer_mode='auto'), 'unit-request-0001')


def test_live_never_silently_falls_back_to_scripted(manager):
    with pytest.raises(Conflict, match='disabled'):
        manager.create(dict(template='pack_and_cover', method='jev_gate', answer_mode='auto'), 'unit-live-request')
    assert manager.ledger.snapshot()['attempts'] == 0


def test_simulator_reveals_only_requested_role(manager, public_state):
    task = pending(manager, public_state)
    manager.answer(task.id, task.pending['id'], source='auto')
    response = next(iter(task.answers.values()))['response']
    assert set(response['choices']) == {'block'}


def test_answer_retry_does_not_create_another_answer(manager, public_state):
    task = pending(manager, public_state)
    qid = task.pending['id']
    answer = {'choices': {'block': role_candidates(public_state, 'block')[0]}}
    assert manager.answer(task.id, qid, answer)['duplicate'] is False
    assert manager.answer(task.id, qid, answer)['duplicate'] is True
    assert len(task.answers) == 1
    changed = {'choices': {'block': role_candidates(public_state, 'block')[1]}}
    with pytest.raises(Conflict):
        manager.answer(task.id, qid, changed)


def test_auto_once_respects_previously_declared_manual_preference(manager, public_state):
    task = pending(manager, public_state)
    other = next(k for k in role_candidates(public_state, 'block') if k != task.sample.theta_star['block_choice'])
    task.goal_overrides['block_choice'] = other
    manager.answer(task.id, task.pending['id'], source='auto')
    assert next(iter(task.answers.values()))['response'] == {'choices': {'block': other}}


def test_already_disclosed_choice_cannot_be_changed_by_a_redundant_question(manager, public_state):
    task = pending(manager, public_state)
    task._question = StudyQuestion.parse(dict(type='select', text='Which cup?', requests=[
        dict(role='cup', candidate_ids=role_candidates(public_state, 'cup'))]), public_state)
    wrong = next(k for k in role_candidates(public_state, 'cup') if public_state.observation['objects'][k]['color']=='red')
    with pytest.raises(ValueError, match='fixed'):
        manager.answer(task.id, task.pending['id'], {'choices': {'cup':wrong}})


def test_confirmation_does_not_accept_extra_information(manager, public_state):
    task = pending(manager, public_state)
    candidate = role_candidates(public_state, 'block')[0]
    task._question = StudyQuestion.parse(dict(type='confirm', text='This block?', requests=[
        dict(role='block', candidate_id=candidate)]), public_state)
    with pytest.raises(ValueError):
        manager.answer(task.id, task.pending['id'], {'confirmations':[
            dict(role='block', candidate_id=candidate, confirmed=True, other_preference='not-requested')]})


def test_question_id_is_scoped_to_task(manager, public_state):
    first = pending(manager, public_state)
    second = pending(manager, public_state, key='unit-request-0002')
    with pytest.raises(Conflict):
        manager.answer(second.id, first.pending['id'], source='auto')
    assert second.pending and not second.answers


@pytest.mark.parametrize('response', [
    {'choices': {'block': 'invisible-object'}},
    {'choices': {'block': 'anything', 'lid': 'anything'}},
    {'theta_star': {}},
    None,
])
def test_invalid_or_extra_preference_answers_rejected(manager, public_state, response):
    task = pending(manager, public_state)
    with pytest.raises(ValueError):
        manager.answer(task.id, task.pending['id'], response)
    assert task.pending and not task.answers


def test_scripted_gate_makes_known_progress_before_asking(public_state):
    planner = ConsoleScriptedPlanner()
    assert ConsoleScriptedGate(planner).decide(public_state).decision == 'CONTINUE'
    action = planner.generate_action(public_state)
    assert public_state.observation['objects'][action.object_id]['color'] == 'blue'


def test_scripted_policy_has_no_private_spec_reference(public_state):
    planner = ConsoleScriptedPlanner()
    assert not vars(planner)
    assert planner.generate_action(public_state).kind == 'pick_place'


def test_worker_event_retry_and_ownership(manager):
    task = create(manager)
    task.worker_id = 'worker-test'
    packet = dict(task_id=task.id, worker_id='worker-test', seq=1, kind='ready', data={'pid':123})
    assert manager.worker_event(packet)['accepted']
    assert not manager.worker_event(packet)['accepted']
    assert len(task.events) == 1
    with pytest.raises(Conflict):
        manager.worker_event({**packet, 'worker_id':'wrong-worker', 'seq':2})
    with pytest.raises(Conflict):
        manager.worker_event({**packet, 'seq':3})


def test_invalid_worker_message_does_not_consume_sequence(manager):
    task = create(manager)
    task.worker_id = 'worker-test'
    with pytest.raises(ValueError):
        manager.worker_event(dict(task_id=task.id, worker_id='worker-test', seq=1, kind='teleport', data={}))
    assert task.worker_seq == 0


def test_global_api_budget_is_atomic_between_threads(tmp_path):
    ledger = ConsoleLedger(tmp_path, max_attempts=7, max_episodes=2)
    def reserve(_):
        try:
            return ledger.reserve('deepseek')
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        numbers = list(pool.map(reserve, range(30)))
    assert sorted(n for n in numbers if n is not None) == list(range(1, 8))
    assert ledger.snapshot()['attempts'] == 7
    assert ConsoleLedger(tmp_path, max_attempts=20).snapshot()['max_attempts'] == 7


def test_negative_command_cursor_rejected(manager):
    task = create(manager)
    task.worker_id = 'test'
    with pytest.raises(ValueError):
        manager.poll_commands(task.id, 'test', -1)


@pytest.fixture
def http_console(manager):
    server = ConsoleHTTPServer(('127.0.0.1', 0), manager, 'unit-worker-token')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}', server
    manager.closed = True
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_http_worker_requires_its_token(http_console):
    base, _ = http_console
    with pytest.raises(WireError, match='token required'):
        request(base, '/api/worker/claim', dict(worker_id='unit', capacity=1))
    assert request(base, '/api/meta')['live_enabled'] is False


def test_http_launch_duplicate_and_cancel(http_console):
    base, _ = http_console
    body = dict(options=dict(template='pack_and_cover',method='scripted_ask',answer_mode='manual'),request_id='unit-http-request')
    first = request(base, '/api/tasks', body)
    assert request(base, '/api/tasks', body)['id'] == first['id']
    assert request(base, f"/api/tasks/{first['id']}/cancel", {})['status'] == 'cancelled'


def test_dns_rebinding_host_rejected(http_console):
    import http.client
    base, server = http_console
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
    connection.request('GET', '/api/meta', headers={'Host':'untrusted.example'})
    response = connection.getresponse()
    assert response.status == 403
    response.read(); connection.close()


def test_foreign_origin_cannot_launch_billable_tasks(http_console):
    import http.client
    _, server = http_console
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port)
    connection.request('POST', '/api/tasks', '{}', {'Origin':'https://untrusted.example','Content-Type':'application/json'})
    response = connection.getresponse()
    assert response.status == 403
    response.read(); connection.close()
