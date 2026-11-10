"""Real offline physics and public contracts. No live API calls in pytest."""
import copy
from dataclasses import replace

import pytest

from when2ask.api import SchemaError
from when2ask.config import Config
from when2ask.console_state import TaskManager
from when2ask.task6_spec import TITLES,make_sample,public_task
from when2ask.task6_protocol import payload,scripted_next,question,action,known_choices,validate_answer
from when2ask.task6_world import make_world
from when2ask.task6_evaluator import evaluate
from when2ask.task6_agents import components,Planner
from when2ask.user_simulator import PreferenceResolver


@pytest.mark.parametrize('template',TITLES)
def test_new_samples_and_console_scenes(template):
    s=make_sample(template);assert len(s.slots)==1 and not s.initial_disclosed_slots
    assert make_sample(template,0).initial_disclosed_slots
    with pytest.raises(ValueError):make_sample(template,2)
    assert public_task(s)['initial_choices']=={}
    assert 'theta_star' not in public_task(s)


@pytest.mark.parametrize('template',TITLES)
def test_real_physical_oracle_and_budget_scoring(template):
    sample=make_sample(template,0)
    with make_world(sample) as world:
        actions=[]
        for _ in range(12):
            proposed=scripted_next(payload(sample.u0,world.observation(),[]))
            if proposed['kind']=='DONE':break
            result=world.execute(proposed);actions.append(result);assert result['success'],result
        result=evaluate(world,sample,actions=actions,termination='robot_action_limit')
        assert result['task_success'],result
        assert result['termination_reason']=='robot_action_limit'


@pytest.mark.parametrize('template',TITLES)
def test_hidden_intent_cannot_change_initial_public_observation(template):
    sample=make_sample(template);slot=next(iter(sample.slots));other=next(k for k in sample.slots[slot]['candidate_ids'] if k!=sample.theta_star[slot])
    scene=sample.scene()
    if template=='occlusion_inspection':scene['label']['code']=other
    changed=replace(sample,theta_star={slot:other},physical_scene=scene).validate()
    with make_world(sample) as a,make_world(changed) as b:
        assert payload(sample.u0,a.observation(),[])==payload(changed.u0,b.observation(),[])


def test_noask_has_no_gate_and_three_methods_share_planner():
    pairs=[components(m,object(),object(),.5) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None
    assert all(isinstance(pair[1],Planner) for pair in pairs)


def test_same_new_sample_and_hashes_for_three_method_comparison(tmp_path):
    manager=TaskManager(tmp_path,config=Config(deepseek_key='unit-private',typesafe_key='unit-private'),allow_live=True)
    group=manager.create_comparison(dict(template='buffer_exchange',unknown_preferences=1),'unit-task6-comparison')
    tasks=[manager.tasks[k] for k in group['task_ids']]
    assert len(tasks)==3 and len({t.id for t in tasks})==3
    assert all(t.sample==tasks[0].sample for t in tasks)
    assert group['physics_signature']==manager.new_task_signature
    assert set(group['prompt_hashes'])=={'gate','action','question'}
    assert manager.ledger.snapshot()['attempts']==0
    assert all(t.public()['review']['ground_truth'] is None for t in tasks)


def test_question_resolver_only_returns_requested_role():
    sample=make_sample('inventory_restock')
    with make_world(sample) as world:
        public=payload(sample.u0,world.observation(),[])
        q=question(dict(type='select',text='How many blocks?',requests=[dict(role='block_quota',candidate_ids=['2','3'])]),public)
        response,burden=PreferenceResolver(sample.slots,sample.theta_star).answer(q)
        assert response=={'choices':{'block_quota':'3'}} and burden==1
        validate_answer(q,public,response)
        with pytest.raises(ValueError):validate_answer(q,public,dict(choices={'block_quota':'3','cup':'cup_1'}))
        with pytest.raises(SchemaError):question(dict(type='select',text='Choose',requests=[dict(role='block_quota',candidate_ids=['3'])]),public)


def test_support_check_has_continue_and_blocked_cases():
    for template in ('category_sorting','inventory_restock','retrieve_restore','patrol_return','occlusion_inspection'):
        s=make_sample(template)
        with make_world(s) as w:assert scripted_next(payload(s.u0,w.observation(),[]),known_only=True)
    s=make_sample('buffer_exchange')
    with make_world(s) as w:assert scripted_next(payload(s.u0,w.observation(),[]),known_only=True) is None


def test_correct_report_or_user_hint_without_physical_inspection_cannot_pass():
    sample=make_sample('occlusion_inspection')
    with make_world(sample) as world:
        public=payload(sample.u0,world.observation(),[])
        assert 'label_fixture' not in public['observation']['objects']
        assert not public['observation']['inspections']
        world.execute(dict(kind='report',code='beta'))
        assert not evaluate(world,sample)['task_success']
        world.execute(dict(kind='move',object_id='opaque_screen',target_id='screen_pad'))
        assert not evaluate(world,sample)['task_success'] # Exposed but not inspected.
        world.execute(dict(kind='inspect',target_id='label_fixture'))
        world.execute(dict(kind='report',code='alpha'))
        result=evaluate(world,sample,overrides={'inspection_code_choice':'alpha'})
        assert not result['conditions']['correct_report_after_inspection']


def test_wrong_retrieved_object_and_missing_restore_fail():
    sample=make_sample('retrieve_restore')
    with make_world(sample) as world:
        world.execute(dict(kind='move',object_id='storage_lid',target_id='lid_pad'))
        world.execute(dict(kind='move',object_id='stored_cup',target_id='delivery_pad'))
        result=evaluate(world,sample)
        assert not result['conditions']['selected_item_delivered']
        assert not result['conditions']['box_reclosed']
        assert not result['task_success']


def test_malformed_or_unobserved_action_rejected():
    sample=make_sample('retrieve_restore')
    with make_world(sample) as world:
        public=payload(sample.u0,world.observation(),[])
        for value in (dict(kind='move',object_id='stored_block',target_id='delivery_pad'),dict(kind='DONE',success=True),dict(kind='teleport',target_id='delivery_pad')):
            with pytest.raises(SchemaError):action(value,public)
