"""Offline public projection/agent tests. Synthetic responses are not experiments."""
import copy
import json
from dataclasses import replace

import pytest

from when2ask.console_samples import demo_sample
from when2ask.dev_public_summary import PROFILES, encode
from when2ask.dev_summary_agents import components, prompt_hashes, question_spec, SHORT_INSTRUCTIONS
from when2ask.diverse_world import DiverseEnvironment
from when2ask.protocol import public_payload
from when2ask.study_agents import prompt_hashes as frozen_prompt_hashes
from when2ask.study_protocol import observe, role_candidates
from when2ask.task import PublicState


@pytest.fixture(scope='module')
def state():
    s = demo_sample('pack_and_cover', 2)
    with DiverseEnvironment(seed=s.scene_seed, scene_spec=s.scene()) as env:
        return observe(env, s.u0, [])


def test_original_projection_is_exactly_frozen_public_payload(state):
    assert encode(state, 'v3_original') == public_payload(state)


def test_compact_projection_is_factual_and_never_an_action_or_timing_verdict(state):
    value = encode(state, 'compact_state')
    preferences = value['public_summary']['preference_disclosures']
    assert preferences['cup']['disclosure'] == 'known'
    assert preferences['block']['disclosure'] == preferences['lid']['disclosure'] == 'not_disclosed'
    assert 'disclosed_object_id' not in preferences['block']
    assert 'position' not in json.dumps(value) and 'aabb' not in json.dumps(value)
    for field in ('theta_star', 'slots', 'dag', 'task_success', 'needs_clarification', 'next_action', 'recommended_decision'):
        assert field not in json.dumps(value)
    assert value['observation']['spatial_relations'] == state.observation['spatial_relations']


def test_changing_hidden_preferences_cannot_change_compact_payload(state):
    sample = demo_sample('pack_and_cover', 2)
    changed = replace(sample, theta_star={**sample.theta_star,
        'block_choice': next(k for k in sample.slots['block_choice']['candidate_ids'] if k != sample.theta_star['block_choice'])})
    same_public = PublicState.build(state.observation, list(state.history), changed.u0)
    assert encode(state, 'compact_state') == encode(same_public, 'compact_state')


def test_physical_success_is_never_inferred_as_a_disclosed_preference(state):
    block = role_candidates(state, 'block')[0]
    history = [dict(kind='action', result=dict(skill='pick_place', object_id=block, target_id='box', success=True))]
    altered = PublicState.build(state.observation, history, state.instruction)
    value = encode(altered, 'compact_question')
    assert value['public_summary']['preference_disclosures']['block']['disclosure'] == 'not_disclosed'
    assert value['history'][0]['physical_execution_succeeded'] is True


def test_answers_are_reused_but_unasked_choices_remain_unknown(state):
    block = role_candidates(state, 'block')[0]
    altered = PublicState.build(state.observation, [dict(kind='user_answer', response={'choices':{'block':block}})], state.instruction)
    preferences = encode(altered, 'compact_question')['public_summary']['preference_disclosures']
    assert preferences['block']['disclosed_object_id'] == block
    assert preferences['lid']['disclosure'] == 'not_disclosed'


def test_binary_confirmation_is_public_deduction_and_does_not_mutate_input(state):
    candidates = role_candidates(state, 'block')
    altered = PublicState.build(state.observation, [dict(kind='user_answer', response={'confirmations':[
        dict(role='block', candidate_id=candidates[0], confirmed=False)]})], state.instruction)
    before = copy.deepcopy(altered)
    value = encode(altered, 'compact_state')
    assert value['public_summary']['preference_disclosures']['block']['disclosed_object_id'] == candidates[1]
    value['observation']['spatial_relations']['inside_containers']['box'].append('unit-only')
    assert altered == before


class Client:
    def __init__(self, probability=.8):
        self.calls = []
        self.probability = probability

    def noul(self, payload, instructions, criteria):
        self.calls.append(('gate', payload, instructions, criteria))
        return self.probability

    def json(self, instructions, payload, stage, validator, **kwargs):
        self.calls.append((stage, payload, instructions))
        if stage == 'gate':
            return validator({'decision':'CONTINUE'})
        if stage == 'action':
            return validator({'kind':'DONE'})
        candidates = [o['object_id'] for o in payload['observation']['objects'] if o['category']=='block']
        return validator(dict(type='select', text='Which block?', requests=[dict(role='block', candidate_ids=candidates)]))


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('method', ['llm_noask', 'llm_gate', 'jev_gate'])
def test_every_method_gate_question_and_action_share_identical_projection(state, profile, method):
    deepseek, jev = Client(), Client()
    gate, planner = components(method, deepseek, jev, .5, profile)
    if method == 'llm_noask':
        assert gate is None
    else:
        gate.decide(state)
    planner.generate_question(state)
    planner.generate_action(state)
    assert all(call[1] == encode(state, profile) for call in deepseek.calls + jev.calls)


@pytest.mark.parametrize('probability,decision', [(0,'CONTINUE'),(.49,'CONTINUE'),(.5,'ASK'),(1,'ASK')])
def test_short_question_keeps_original_probability_direction(state, probability, decision):
    gate, _ = components('jev_gate', Client(), Client(probability), .5, 'compact_question')
    assert gate.decide(state).decision == decision


def test_ablation_changes_only_gate_wording_between_compact_conditions(state):
    assert encode(state, 'compact_state') == encode(state, 'compact_question')
    first, second = prompt_hashes('compact_state'), prompt_hashes('compact_question')
    assert first['action'] == second['action'] == frozen_prompt_hashes()['action']
    assert first['question'] == second['question'] == frozen_prompt_hashes()['question']
    assert first['gate_instructions'] != second['gate_instructions']
    assert question_spec('compact_question')[0] == SHORT_INSTRUCTIONS


@pytest.mark.parametrize('profile', PROFILES)
@pytest.mark.parametrize('template,unknown', [('pack_and_cover', 2), ('place_into_selected_containers', 0)])
def test_runner_real_physics_with_explicitly_synthetic_transport(tmp_path, monkeypatch, profile, template, unknown):
    # Unit transport only; files stay under pytest tmp and never enter Dev reports.
    from when2ask import dev_summary_runner
    from when2ask.accounting import SessionLedger
    from when2ask.api import DeepSeekClient, JevClient
    from when2ask.config import Config
    from when2ask.console_policy import ConsoleScriptedGate, ConsoleScriptedPlanner
    sample = demo_sample(template, unknown)
    session = SessionLedger(tmp_path / 'ledger', 40, 1, policy='phase3_dev')
    policy = ConsoleScriptedPlanner()
    def reconstruct(payload):
        obs = copy.deepcopy(payload['observation'])
        obs['objects'] = {o['object_id']:{k:v for k,v in o.items() if k!='object_id'} for o in obs['objects']}
        return PublicState.build(obs, payload['history'], payload['instruction'])
    def transport(url, headers, payload, timeout):
        assert session.snapshot()['attempts'] > 0
        if url.endswith('/v1/systemone'):
            decision = ConsoleScriptedGate(policy).decide(reconstruct(payload['state'])).decision
            return 200, json.dumps(dict(model='unit-jev-model', answers=dict(needs_clarification=dict(type='noul', noul=.9 if decision=='ASK' else .01)), usage=dict(input_tokens=5,output_tokens=1)))
        public = json.loads(payload['messages'][1]['content'])
        state = reconstruct(public)
        if 'QUESTION planner' in payload['messages'][0]['content']:
            value = policy.generate_question(state).to_dict()
        else:
            action = policy.generate_action(state)
            value = {'kind':'DONE'} if action.kind=='DONE' else action.to_dict()
        return 200, json.dumps(dict(model='unit-deepseek-model', choices=[dict(message=dict(content=json.dumps(value)))], usage=dict(prompt_tokens=5,completion_tokens=1)))
    monkeypatch.setattr(dev_summary_runner, 'DeepSeekClient', lambda config,audit:DeepSeekClient(config,audit,transport=transport))
    monkeypatch.setattr(dev_summary_runner, 'JevClient', lambda config,audit:JevClient(config,audit,transport=transport))
    e = dev_summary_runner.run_episode(sample, 'unit-case', profile, tmp_path / 'episode',
        config=Config(deepseek_key='unit-sentinel',typesafe_key='unit-sentinel'), session=session, live=True)
    assert e['evaluation']['task_success'] and e['error'] is None
    assert session.snapshot()['attempts'] == e['cost']['api_attempts'] == len(e['api_attempts'])
    assert all(a['session_attempt'] is not None for a in e['api_attempts'])
    assert all(c['state_unchanged'] for c in e['ask_checks'])
    assert e['evaluation']['clarification_burden'] == unknown


def test_live_runner_rejects_nonlive_or_test_without_request(tmp_path):
    from when2ask.dev_summary_runner import run_episode
    from when2ask.config import Config
    sample = demo_sample('pack_and_cover')
    with pytest.raises(ValueError):
        run_episode(sample, 'unit', 'compact_state', tmp_path, config=Config(), session=None)
    with pytest.raises(ValueError):
        run_episode(replace(sample, partition='test'), 'unit', 'compact_state', tmp_path,
                    config=Config(), session=None, live=True)


def test_exploratory_rule_does_not_trade_early_asks_or_success_for_lower_miss_count():
    from when2ask.dev_summary_report import eligibility
    baseline = {str(i):dict(task_success=True, early_asks=0, complete_asks=0, blocked_continues=2) for i in range(4)}
    candidate = {k:dict(v, blocked_continues=0) for k,v in baseline.items()}
    assert eligibility(baseline, candidate)['promising']
    candidate['0']['early_asks'] = 1
    assert not eligibility(baseline, candidate)['promising']
    candidate['0'].update(early_asks=0, task_success=False)
    assert not eligibility(baseline, candidate)['promising']


def test_incomplete_pairing_never_declares_a_promising_candidate():
    from when2ask.dev_summary_report import eligibility
    assert not eligibility({}, {})['promising']
