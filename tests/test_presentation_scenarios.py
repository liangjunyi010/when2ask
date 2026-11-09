"""Offline presentation dataset/console contracts; no network or paid calls."""
import copy
import json
from collections import Counter
from dataclasses import replace

import pytest

from when2ask.config import Config
from when2ask.console_policy import ConsoleScriptedPlanner
from when2ask.console_samples import demo_sample
from when2ask.console_state import TaskManager
from when2ask.presentation_scenarios import catalogue, generate, get_sample, load_samples, validate
from when2ask.protocol import public_payload
from when2ask.task import PublicState


def test_distribution_and_frozen_manifest():
    assert validate()['sample_count'] == 20
    samples, entries = load_samples(), catalogue()
    assert len({s.group_id for s in samples}) == 10
    assert set(Counter(s.group_id for s in samples).values()) == {2}
    assert Counter(s.template_id for s in samples) == {'pack_and_cover': 10, 'place_into_selected_containers': 10}
    assert Counter(e['unknown_preferences'] for e in entries) == {0: 5, 1: 5, 2: 5, 3: 5}


def test_generation_is_deterministic_and_refuses_overwrite(tmp_path):
    result = generate(tmp_path)
    assert result['samples_sha256'] == json.loads(__import__('pathlib').Path('data/presentation_dag_v1/manifest.json').read_text())['samples_sha256']
    with pytest.raises(FileExistsError):
        generate(tmp_path)
    assert validate(tmp_path)['hashes_valid']


@pytest.mark.parametrize('sample', load_samples(), ids=lambda s: s.sample_id)
def test_public_payload_independent_of_undisclosed_truth(sample):
    scene = sample.scene()
    objects = {v: dict(category=('container' if k in [c['id'] for c in scene['containers']] else k.split('_')[-1]))
               for k, v in scene['object_id_map'].items()}
    for obj in objects.values():
        obj.update(color='unit-test', position=[0, 0, 0], aabb_min=[0, 0, 0], aabb_max=[1, 1, 1])
    raw = dict(objects=objects, simulation_step=0, held_object=None)
    # Synthetic observation is only an isolation unit test, never a physical result.
    state = PublicState.build(raw, [], sample.u0)
    changed = copy.deepcopy(sample.theta_star)
    for slot in sample.slots:
        if slot not in sample.initial_disclosed_slots:
            changed[slot] = next(k for k in sample.slots[slot]['candidate_ids'] if k != changed[slot])
    altered = replace(sample, theta_star=changed).validate()
    assert public_payload(state) == public_payload(PublicState.build(raw, [], altered.u0))
    assert set(public_payload(state)) == {'instruction', 'observation', 'history'}


def test_console_preset_reuses_exact_choices_and_seed(tmp_path):
    sample = get_sample('dag_demo_06')
    manager = TaskManager(tmp_path, config=Config())
    row = manager.create(dict(template=sample.template_id, method='scripted_ask', answer_mode='manual',
        unknown_preferences=2, scenario_id=sample.sample_id), 'presentation-unit-request')
    task = manager.tasks[row['id']]
    assert task.sample == sample
    assert demo_sample(sample.template_id, 2, scenario_id=sample.sample_id).scene() == sample.scene()
    assert row['review']['scenario']['sample_id'] == sample.sample_id
    assert row['review']['ground_truth'] is None
    assert row['review']['public_dag'] == sample.dag
    assert 'theta_star' not in json.dumps(manager.metadata())


@pytest.mark.parametrize('options', [
    dict(template='pack_and_cover', scenario_id='dag_demo_11'),
    dict(template='pack_and_cover', scenario_id='dag_demo_06', unknown_preferences=0),
    dict(template='find_and_approach', scenario_id='dag_demo_06'),
    dict(template='pack_and_cover', scenario_id='missing'),
    dict(template='pack_and_cover', scenario_id=None),
])
def test_invalid_preset_rejected(options):
    with pytest.raises(ValueError):
        TaskManager.validate_options(dict(options, method='scripted_ask', answer_mode='auto'))


def initial_state(sample):
    scene = sample.scene()
    containers = {scene['object_id_map'][c['id']]: dict(category='container') for c in scene['containers']}
    objects = {scene['object_id_map'][k]: dict(category=k.split('_')[-1]) for k in scene['sources']}
    objects.update(containers)
    relations = dict(inside_containers={k: [] for k in containers}, covering_containers={k: [] for k in containers})
    return PublicState.build(dict(objects=objects, spatial_relations=relations), [], sample.u0)


def test_dag_changes_current_supported_progress_without_gate_oracle():
    planner = ConsoleScriptedPlanner()
    # Known cup, but block-first prerequisite means no currently supported action.
    assert planner.next_action(initial_state(get_sample('dag_demo_03')), known_only=True) is None
    # A known lid cannot be used before packing both unknown objects.
    assert planner.next_action(initial_state(get_sample('dag_demo_08')), known_only=True) is None
    # Known independent block supports progress despite missing cup selection.
    sample = get_sample('dag_demo_05')
    action = planner.next_action(initial_state(sample), known_only=True)
    assert action.object_id == sample.theta_star['block_choice']
    # Both container placements depend on the one reusable destination answer.
    assert planner.next_action(initial_state(get_sample('dag_demo_15')), known_only=True) is None
