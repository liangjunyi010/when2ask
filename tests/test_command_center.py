"""Offline comparison/queue contracts; synthetic unit states, never live evidence."""
import csv
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from when2ask.accounting import BudgetExceeded
from when2ask.config import Config
from when2ask.console_samples import demo_sample
from when2ask.console_state import Conflict, LIVE_METHODS, TaskManager
from when2ask.console_server import ConsoleHTTPServer
from when2ask.console_transport import WireError, request


def manager(tmp_path, **kwargs):
    return TaskManager(tmp_path, config=Config(deepseek_key='unit-deepseek-sentinel',
        typesafe_key='unit-jev-sentinel'), allow_live=True, **kwargs)


def options(unknown=2):
    return dict(template='pack_and_cover', unknown_preferences=unknown)


@pytest.mark.parametrize('template', ['pack_and_cover', 'place_into_selected_containers'])
@pytest.mark.parametrize('unknown', range(4))
def test_disclosure_profiles_preserve_physics_and_control_unknown_count(template, unknown):
    sample = demo_sample(template, unknown)
    original = demo_sample(template)
    assert len(sample.slots) - len(sample.initial_disclosed_slots) == unknown
    assert sample.scene() == original.scene() and sample.theta_star == original.theta_star
    for slot, value in sample.theta_star.items():
        assert (f'use {value}.' in sample.u0) == (slot in sample.initial_disclosed_slots)


@pytest.mark.parametrize('unknown', [-1, 4, True, '2', 2.1])
def test_invalid_disclosure_rejected(tmp_path, unknown):
    m = manager(tmp_path)
    with pytest.raises(ValueError):
        m.create_comparison(options(unknown), 'unit-comparison-0001')
    assert not m.tasks and m.ledger.snapshot()['episodes'] == 0


def test_one_click_creates_three_independent_paired_worlds(tmp_path):
    m = manager(tmp_path)
    g = m.create_comparison(options(), 'unit-comparison-0001')
    tasks = [m.tasks[tid] for tid in g['task_ids']]
    assert [t.method for t in tasks] == list(LIVE_METHODS)
    assert len({id(t.history) for t in tasks}) == len({t.id for t in tasks}) == 3
    assert all(t.answer_mode == 'auto' and t.comparison_id == g['id'] for t in tasks)
    assert all(t.audit.session is m.ledger for t in tasks)
    assert all(t.sample == tasks[0].sample for t in tasks)
    assert m.ledger.snapshot()['episodes'] == 3 and m.ledger.snapshot()['attempts'] == 0
    assert g['planner_configuration'] == m.config.public_config()
    for secret in ('unit-deepseek-sentinel', 'unit-jev-sentinel', 'theta_star', 'slots'):
        assert secret not in json.dumps(g)


def test_each_paired_model_attempt_is_charged_before_network(tmp_path):
    m = manager(tmp_path, api_limit=2)
    g = m.create_comparison(options(), 'unit-comparison-0001')
    one, two, three = [m.tasks[tid] for tid in g['task_ids']]
    assert one.audit.reserve('deepseek')['session_attempt'] == 1
    assert two.audit.reserve('jev')['session_attempt'] == 2
    with pytest.raises(BudgetExceeded):
        three.audit.reserve('deepseek')
    assert m.ledger.snapshot()['attempts'] == 2 and not three.audit.records


def test_batch_idempotency_survives_exhausted_episode_budget(tmp_path):
    m = manager(tmp_path, live_episode_limit=3)
    first = m.create_comparison(options(), 'unit-comparison-0001')
    second = m.create_comparison(options(), 'unit-comparison-0001')
    assert first['task_ids'] == second['task_ids']
    assert len(m.tasks) == 3 and m.ledger.snapshot()['episodes'] == 3
    with pytest.raises(Conflict):
        m.create_comparison(options(1), 'unit-comparison-0001')


@pytest.mark.parametrize('budget', [dict(live_episode_limit=2), dict(api_limit=0)])
def test_insufficient_budget_rejects_whole_batch(tmp_path, budget):
    m = manager(tmp_path, **budget)
    with pytest.raises(BudgetExceeded):
        m.create_comparison(options(), 'unit-comparison-0001')
    assert not m.tasks and not m.comparisons and m.ledger.snapshot()['episodes'] == 0
    assert not list((tmp_path / 'tasks').glob('*'))


def test_comparison_has_no_scripted_fallback_when_offline(tmp_path):
    m = TaskManager(tmp_path)
    with pytest.raises(Conflict, match='disabled'):
        m.create_comparison(options(), 'unit-comparison-0001')
    assert not m.tasks


def test_missing_jev_key_rejects_entire_comparison(tmp_path):
    m = TaskManager(tmp_path, allow_live=True, config=Config(deepseek_key='unit-sentinel'))
    with pytest.raises(Conflict, match='configured'):
        m.create_comparison(options(), 'unit-comparison-0001')
    assert not m.tasks and m.ledger.snapshot()['episodes'] == 0


def test_concurrent_batches_cannot_overdraw_episode_reservation(tmp_path):
    m = manager(tmp_path, live_episode_limit=3)
    def launch(i):
        try:
            return m.create_comparison(options(), f'unit-comparison-{i}')['id']
        except BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(launch, [1, 2]))
    assert sum(r is not None for r in results) == 1
    assert len(m.tasks) == 3 and m.ledger.snapshot()['episodes'] == 3


def test_comparison_queue_capacity_is_atomic(tmp_path):
    m = manager(tmp_path)
    for i in range(18):
        m.create(dict(template='pack_and_cover', method='scripted_ask', answer_mode='manual'), f'queued-task-{i:04}')
    with pytest.raises(Conflict, match='queue capacity'):
        m.create_comparison(options(), 'unit-comparison-0001')
    assert len(m.tasks) == 18 and m.ledger.snapshot()['episodes'] == 0


def test_paired_run_cannot_override_automatic_reply_protocol(tmp_path):
    m = manager(tmp_path)
    with pytest.raises(ValueError):
        m.create_comparison(dict(options(), answer_mode='manual'), 'unit-comparison-0001')
    assert not m.tasks


def test_live_comparison_http_routes_and_pending_export(tmp_path):
    m = manager(tmp_path)
    server = ConsoleHTTPServer(('127.0.0.1', 0), m, 'unit-worker-token')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        g = request(base, '/api/comparisons', dict(options=options(), request_id='unit-comparison-0001'))
        assert request(base, '/api/comparisons')['comparisons'][0]['id'] == g['id']
        assert request(base, '/api/comparisons/' + g['id'])['task_ids'] == g['task_ids']
        assert request(base, '/api/clarifications') == dict(clarifications=[])
        with pytest.raises(WireError):
            request(base, '/api/comparisons/' + g['id'] + '/csv')
        assert m.ledger.snapshot()['attempts'] == 0
    finally:
        m.closed = True
        server.shutdown()
        server.server_close()


def test_global_queue_routes_and_orders_only_pending_questions(tmp_path):
    m = manager(tmp_path)
    for i in range(3):
        t = m.tasks[m.create(dict(template='pack_and_cover', method='scripted_ask', answer_mode='manual'), f'pending-task-{i:04}')['id']]
        t.status = 'waiting_answer' if i < 2 else 'done'
        t.pending = dict(id=f'question-{i}', created=20-i, text='Public question', requests=[])
    queue = m.clarifications()
    assert [q['question']['id'] for q in queue] == ['question-1', 'question-0']
    assert len({q['task_id'] for q in queue}) == 2
    assert all('theta_star' not in json.dumps(q) for q in queue)


def test_completed_csv_preserves_failed_and_unscored_outcomes(tmp_path):
    m = manager(tmp_path)
    group = m.create_comparison(options(), 'unit-comparison-0001')
    with m.changed:
        for tid, score in zip(group['task_ids'], [False, True, None]):
            t = m.tasks[tid]
            t.status = 'done'
            if score is not None:
                t.finalization = dict(evaluation=dict(task_success=score))
            m.publish(t)
    result = m.comparison(group['id'])
    assert result['status'] == 'complete'
    assert [r['task_success'] for r in result['rows']] == [False, True, None]
    rows = list(csv.DictReader((tmp_path / 'comparisons' / f"{group['id']}.csv").open()))
    assert [r['task_success'] for r in rows] == ['False', 'True', '']
    assert all(r['api_latency_ms'] == '' and r['jev_input_tokens'] == '' for r in rows)
