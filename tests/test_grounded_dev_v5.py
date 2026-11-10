"""Offline-only contracts for the optional shared Dev planner."""
import copy
import json
from dataclasses import replace
import pytest
from when2ask.config import Config,ROOT
from when2ask.grounded_dev_public import PROFILE,SUPPORTED,serialize,facts
from when2ask.grounded_dev_agents import Planner,components,prompt_hashes
from when2ask.console_state import TaskManager
from when2ask.task6_spec import make_sample
from when2ask.task6_world import make_world
from when2ask.task6_protocol import payload
from when2ask.api import SchemaError


def recorded(template,index=0):
    return copy.deepcopy(json.loads((ROOT/f'outputs/six_tasks_dev_v1/live/{template}/episode.json').read_text())['turns'][index]['public_payload'])


@pytest.mark.parametrize('template',SUPPORTED)
def test_public_grounding_pure_and_preserves_affordances(template):
    raw=recorded(template);before=copy.deepcopy(raw);dev=serialize(raw)
    assert raw==before and dev['observation']['affordances']==raw['observation']['affordances']
    assert 'theta_star' not in json.dumps(dev) and 'task_success' not in json.dumps(dev)
    assert 'next_action' not in json.dumps(dev)
    assert dev['public_summary']['confirmed_choices']=={}


@pytest.mark.parametrize('template',SUPPORTED)
def test_hidden_choice_does_not_change_public_payload(template):
    sample=make_sample(template)
    # For world facts alter private choice and physical printed code together;
    # while occluded neither may enter the payload.
    slot=next(iter(sample.slots));other=next(c for c in sample.slots[slot]['candidate_ids'] if c!=sample.theta_star[slot])
    scene=copy.deepcopy(sample.physical_scene)
    if sample.slots[slot].get('kind')=='world_fact':scene['label']['code']=other
    changed=replace(sample,theta_star={slot:other},physical_scene=scene)
    with make_world(sample) as a,make_world(changed) as b:
        assert serialize(payload(sample.u0,a.observation(),[]))==serialize(payload(changed.u0,b.observation(),[]))


def test_retrieval_unknown_contents_are_not_empty_or_movable():
    dev=serialize(recorded('retrieve_restore'));summary=dev['public_summary']
    assert summary['contents_observed']=={'box':False}
    assert set(summary['unobserved_public_item_ids'])=={'stored_cup','stored_block'}
    assert 'stored_cup' not in summary['current_locations']


def test_sensor_code_cannot_enter_summary_before_real_inspection():
    dev=serialize(recorded('occlusion_inspection'));assert dev['public_summary']['confirmed_choices']=={}
    assert dev['observation']['inspections']==[]
    assert 'label_fixture' not in dev['observation']['objects']


def test_history_compaction_preserves_dialogue_order_latest_action_and_failed_count():
    raw=recorded('buffer_exchange',9)
    q=dict(kind='user_answer',response={'choices':{'buffer_pad':'buffer_front'}})
    raw['history'].insert(1,q);dev=serialize(raw)
    expected=[q,raw['history'][-1]]
    assert dev['history']==expected
    assert dev['public_summary']['action_history_coverage']['total']==9
    assert dev['public_summary']['action_history_coverage']['failed']>0
    assert dev['public_summary']['confirmed_choices']=={'buffer_pad':'buffer_front'}


class Client:
    def __init__(self,value):self.value=value;self.calls=[]
    def json(self,system,public,stage,validator,max_tokens):
        self.calls.append((stage,max_tokens));return validator(copy.deepcopy(self.value))


def proposed(public,action):
    _,locations,goal=facts(public)
    return dict(current_locations=locations,goal_requirements=goal,working_choices={'buffer_pad':'buffer_front'},remaining_plan=[action])


def test_bad_progress_is_accepted_verbatim_not_masked():
    dev=serialize(recorded('buffer_exchange',2));bad=dict(kind='move',object_id='item_b',target_id='slot_right')
    client=Client(proposed(dev,bad));planner=Planner(client)
    assert planner.generate_action(dev)==bad
    assert planner.last_model_plan==client.value
    assert client.calls==[('action',650)]


@pytest.mark.parametrize('field',['current_locations','goal_requirements','working_choices'])
def test_malformed_grounding_rejected(field):
    dev=serialize(recorded('buffer_exchange',2));value=proposed(dev,{'kind':'DONE'});value[field]={}
    with pytest.raises(SchemaError):Planner(Client(value)).generate_action(dev)


def test_same_planner_configuration_noask_skips_gate():
    pairs=[components(m,object(),object(),.5) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None and all(type(p) is Planner for _,p in pairs)
    assert all(g.threshold==.5 for g,_ in pairs if g)
    assert set(prompt_hashes())=={'gate','question','action'}


def test_default_opt_in_validation_and_paired_profile_metadata(tmp_path):
    manager=TaskManager(tmp_path,config=Config(deepseek_key='unit',typesafe_key='unit'),allow_live=True,live_episode_limit=6)
    options=dict(template='buffer_exchange',unknown_preferences=1,method='scripted_ask',answer_mode='manual')
    t=manager.create(options,'default-unique-id');assert t['planner_profile']=='default_v1'
    t=manager.create(dict(options,planner_profile=PROFILE),'dev-unique-id');assert t['planner_profile']==PROFILE
    group=manager.create_comparison(dict(template='retrieve_restore',unknown_preferences=1,planner_profile=PROFILE),'paired-unique-id')
    assert group['planner_profile']==PROFILE and group['prompt_hashes']==prompt_hashes()
    assert all(manager.tasks[k].planner_profile==PROFILE for k in group['task_ids'])
    assert manager.ledger.snapshot()['attempts']==0
    for bad in ['pack_and_cover','category_sorting','find_and_approach']:
        with pytest.raises(ValueError):manager.validate_options(dict(options,template=bad,planner_profile=PROFILE))


def test_schema_repair_debits_budget_without_reporting_backend_outage(tmp_path):
    from when2ask.grounded_dev_health import SchemaAwareSession
    from when2ask.accounting import Audit,BackendBlocked
    from when2ask.console_state import ConsoleLedger
    ledger=ConsoleLedger(tmp_path/'ledger',20,9);audit=Audit('offline',Config())
    session=SchemaAwareSession(ledger,audit)
    for _ in range(3):
        audit.records.append(dict(status='schema_error',http_status=200))
        session.reserve('deepseek');session.outcome('deepseek',False)
    assert ledger.snapshot()['attempts']==3
    assert not ledger.snapshot()['backends']['deepseek']['blocked']
    assert all(r['backend_health']=='http_ok_schema_error' for r in audit.records)
    for _ in range(3):
        audit.records.append(dict(status='api_error',http_status=503))
        session.reserve('deepseek');session.outcome('deepseek',False)
    with pytest.raises(BackendBlocked):session.reserve('deepseek')
