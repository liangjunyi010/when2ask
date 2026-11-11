"""Offline public-memory, non-oracle completion and real physical regressions."""
import copy
import json
from dataclasses import replace
import pytest
from when2ask.api import SchemaError
from when2ask.config import ROOT,Config
from when2ask.memory_dev_public import PROFILE,SUPPORTED,serialize
from when2ask.memory_dev_agents import Planner,components,prompt_hashes
from when2ask.console_state import TaskManager
from when2ask.task6_spec import make_sample
from when2ask.task6_world import make_world
from when2ask.task6_protocol import payload,scripted_next
from when2ask.task6_evaluator import evaluate


def turns(template='retrieve_restore',method='llm_gate'):
    return json.loads((ROOT/f'outputs/grounded_planner_dev_v5/live/{template}__{method}/episode.json').read_text())['turns']


def old_state(index,template='retrieve_restore',method='llm_gate'):
    ts=turns(template,method)
    return ts[index]['raw_public_payload'],[t['raw_public_payload']['observation'] for t in ts[:index]]


def test_delivered_object_is_observed_in_region_even_when_grasp_geometry_hidden():
    raw,prior=old_state(4);before=copy.deepcopy(raw);s=serialize(raw,prior)['public_summary']
    assert raw==before
    assert 'stored_block' not in raw['observation']['objects']
    assert 'stored_block' not in raw['observation']['affordances']['move']
    assert s['observed_locations']['stored_block']==['delivery_pad']
    assert s['object_memory']['stored_block']['status']=='observed_now'
    assert not s['object_memory']['stored_block']['currently_graspable']


def test_other_item_stays_typed_remembered_not_new_vision():
    raw,prior=old_state(4);s=serialize(raw,prior)['public_summary'];m=s['object_memory']['stored_cup']
    assert m['status']=='remembered_occluded' and m['regions']==['box']
    assert m['observed_step']<raw['observation']['simulation_step']
    assert 'stored_cup' not in s['observed_locations']
    assert s['current_regions']['box']==dict(contents=[],observed=False)
    assert s['lid_geometry']['aabb_spans_opening']


def test_never_seen_hidden_contents_start_unknown():
    raw,prior=old_state(0);s=serialize(raw,prior)['public_summary']
    for key in ['stored_cup','stored_block']:
        assert s['object_memory'][key]['status']=='unknown'
        assert s['object_memory'][key]['regions'] is None
        assert s['object_memory'][key]['observed_step'] is None


def test_region_negative_observation_overrides_old_delivery():
    raw,prior=old_state(4);raw=copy.deepcopy(raw);raw['observation']['zones']['delivery_pad']['contents']=[]
    m=serialize(raw,prior)['public_summary']['object_memory']['stored_block']
    assert m['status']=='unknown' and m['regions'] is None


def test_failed_unseen_disturbance_invalidates_remembered_contents():
    raw,prior=old_state(4);raw=copy.deepcopy(raw)
    raw['history'][-1]['result']['success']=False
    s=serialize(raw,prior)['public_summary']
    assert s['object_memory']['stored_cup']['status']=='unknown_after_action'
    assert s['object_memory']['stored_cup']['regions'] is None
    assert s['object_memory']['stored_block']['status']=='observed_now'


def test_new_observation_overrides_stale_placement_and_preserves_affordances():
    raw,prior=old_state(5);s=serialize(raw,prior)
    assert s['public_summary']['observed_locations']['storage_lid']==['lid_pad']
    assert not s['public_summary']['lid_geometry']['aabb_spans_opening']
    assert s['observation']['affordances']==raw['observation']['affordances']


def test_buffer_final_targets_remain_absolute_after_swap():
    raw,prior=old_state(4,'buffer_exchange','jev_gate');s=serialize(raw,prior)['public_summary']
    assert [(r['object_id'],r['required_final_region'],r['currently_observed_at_target']) for r in s['required_final_relations']]==[('item_a','slot_right',True),('item_b','slot_left',True)]
    assert all(s['current_regions'][r]['contents']==[] for r in ['buffer_front','buffer_back'])
    assert s['confirmed_choices']=={'buffer_pad':'buffer_back'}


def test_noask_assumption_is_not_confirmed_user_choice():
    raw,prior=old_state(3,'buffer_exchange','llm_noask');s=serialize(raw,prior)['public_summary']
    assert s['confirmed_choices']=={}
    assert s['own_working_choices']['buffer_pad']==dict(value='buffer_front',source='own_successful_action',user_confirmed=False)


@pytest.mark.parametrize('template',SUPPORTED)
def test_hidden_truth_isolation_in_real_world(template):
    sample=make_sample(template);slot=next(iter(sample.slots));other=next(c for c in sample.slots[slot]['candidate_ids'] if c!=sample.theta_star[slot])
    scene=copy.deepcopy(sample.physical_scene)
    if sample.slots[slot].get('kind')=='world_fact':scene['label']['code']=other
    changed=replace(sample,theta_star={slot:other},physical_scene=scene)
    with make_world(sample) as a,make_world(changed) as b:
        pa=serialize(payload(sample.u0,a.observation(),[]));pb=serialize(payload(changed.u0,b.observation(),[]))
        assert pa==pb and 'theta_star' not in json.dumps(pa) and 'task_success' not in json.dumps(pa)


class Client:
    def __init__(self,value):self.value=value
    def json(self,system,public,stage,validator,max_tokens):return validator(copy.deepcopy(self.value))


def test_model_controls_done_and_even_regressive_first_action_verbatim():
    raw,prior=old_state(4,'buffer_exchange','jev_gate');public=serialize(raw,prior)
    bad=dict(kind='move',object_id='item_a',target_id='buffer_back')
    value=dict(working_choices={'buffer_pad':'buffer_back'},completion_assessment=dict(ready_for_done=True,reason='Already exchanged'),remaining_plan=[bad])
    assert Planner(Client(value)).generate_action(public)==bad
    value['remaining_plan']=[dict(kind='DONE')]
    assert Planner(Client(value)).generate_action(public)==dict(kind='DONE')
    value['completion_assessment']['ready_for_done']='yes'
    with pytest.raises(SchemaError):Planner(Client(value)).generate_action(public)


def test_same_planner_gate_order_and_profile_opt_in(tmp_path):
    pairs=[components(m,object(),object(),.5) for m in ['llm_noask','llm_gate','jev_gate']]
    assert pairs[0][0] is None and all(type(p) is Planner for _,p in pairs)
    manager=TaskManager(tmp_path,config=Config(deepseek_key='unit',typesafe_key='unit'),allow_live=True)
    base=dict(template='retrieve_restore',method='scripted_ask',answer_mode='manual',unknown_preferences=1)
    assert manager.create(base,'unit-default-v6')['planner_profile']=='default_v1'
    assert manager.create(dict(base,planner_profile='grounded_dev_v5'),'unit-old-dev-v6')['planner_profile']=='grounded_dev_v5'
    g=manager.create_comparison(dict(template='retrieve_restore',unknown_preferences=1,planner_profile=PROFILE),'unit-paired-v6')
    assert g['planner_profile']==PROFILE and g['prompt_hashes']==prompt_hashes()
    with pytest.raises(ValueError):manager.validate_options(dict(base,template='pack_and_cover',planner_profile=PROFILE))


@pytest.mark.parametrize('template',SUPPORTED)
def test_real_skills_with_public_memory_leave_independent_evaluator_unchanged(template):
    sample=make_sample(template,0);history=[];prior=[];actions=[]
    with make_world(sample) as world:
        for _ in range(8):
            raw=payload(sample.u0,world.observation(),history);dev=serialize(raw,prior);prior.append(copy.deepcopy(raw['observation']))
            command=scripted_next(dev)
            if command['kind']=='DONE':break
            result=world.execute(command);history.append(dict(kind='action',result=result));actions.append(result)
        score=evaluate(world,sample,actions=actions)
        assert score['task_success'],score
        if template=='retrieve_restore':
            assert dev['public_summary']['object_memory']['stored_block']['regions']==['delivery_pad']
            assert dev['public_summary']['object_memory']['stored_cup']['status']=='remembered_occluded'
        if template=='occlusion_inspection':assert dev['public_summary']['confirmed_choices']['inspection_code']=='beta'
