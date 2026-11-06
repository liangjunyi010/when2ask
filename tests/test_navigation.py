"""Offline only. Real physics tests plus clearly synthetic API-contract unit tests."""
import copy
import json
from dataclasses import replace

import pybullet as p
import pytest

from when2ask.agents import GateResult
from when2ask.api import SchemaError
from when2ask.config import Config
from when2ask.console_state import TaskManager
from when2ask.navigation_agents import ScriptedPlanner, ScriptedGate, components, prompt_hashes
from when2ask.navigation_map import LOCATIONS, route
from when2ask.navigation_protocol import auto_answer, location_claim, parse_action, parse_question, public_payload, validate_answer
from when2ask.navigation_task import make_sample
from when2ask.navigation_world import NavigationWorld


@pytest.fixture(scope='module')
def initial():
    with NavigationWorld(make_sample()) as world:
        return public_payload(world.sample.u0,world.observation(),[])


def test_hidden_world_changes_do_not_change_initial_public_payload():
    rows=[]
    for case in ('case_a','case_b','case_c'):
        with NavigationWorld(make_sample(case)) as world:
            rows.append(public_payload(world.sample.u0,world.observation(),[]))
            assert not world.last_seen
    assert rows[0]==rows[1]==rows[2]
    assert not {'sample_id','case_id','theta_star','target_location'} & set(rows[0])


def test_payload_allowlist_removes_private_and_score_fields(initial):
    obs=dict(initial['observation'],theta_star='SECRET',score=1,target_location='PRIVATE',case_id='PRIVATE')
    payload=public_payload(initial['instruction'],obs,[])
    assert 'SECRET' not in json.dumps(payload) and 'PRIVATE' not in json.dumps(payload)


def test_initial_public_frame_does_not_reveal_hidden_target():
    rendered=[]
    for case in ('case_a','case_b'):
        with NavigationWorld(make_sample(case)) as world:rendered.append(world.render(480,270).tobytes())
    assert rendered[0]==rendered[1]


@pytest.mark.parametrize('value',[{'kind':'search','location_id':'secret_room'},{'kind':'teleport','location_id':'study_desk'},
    {'kind':'DONE','success':True},{'kind':'search','location_id':'study_desk','target_position':[4,2,0]}])
def test_invalid_navigation_action_rejected(value):
    with pytest.raises(SchemaError):parse_action(value)


def test_question_one_location_fact_and_no_extra_disclosure(initial):
    q=ScriptedPlanner().generate_question(initial)
    assert parse_question(q)==q
    assert auto_answer(make_sample('case_b'))=={'choices':{'target_location':'living_cabinet'}}
    assert len(q['requests'])==1 and len(q['requests'][0]['candidate_ids'])==6
    with pytest.raises(SchemaError):parse_question(dict(q,private_answer='anything'))
    with pytest.raises(ValueError):validate_answer({'choices':{'target_location':'living_cabinet','other_secret':'bad'}})


def test_known_initial_hint_and_history_reuse(initial):
    sample=make_sample('case_c',0)
    assert location_claim(sample.u0,[])=='study_shelf'
    h=[dict(kind='user_answer',response={'choices':{'target_location':'study_desk'}})]
    assert location_claim(initial['instruction'],h)=='study_desk'


def test_manual_wrong_location_never_changes_fixed_world(tmp_path):
    manager=TaskManager(tmp_path)
    row=manager.create(dict(template='find_and_approach',method='scripted_ask',answer_mode='manual',navigation_case='case_b'),'nav-manual-unit')
    task=manager.tasks[row['id']];task.status='waiting_answer';task.pending={'id':'q'};task._question={}
    manager.answer(task.id,'q',{'choices':{'target_location':'study_desk'}})
    assert task.sample.target_location=='living_cabinet' and not task.goal_overrides
    assert task.answers['q']['response']['choices']['target_location']=='study_desk'


def test_doorway_routes_use_shared_known_corridor():
    assert route([-4,1.1],'study_shelf')==[[-4.,0.],[0.,0.],[4.,0.],[4.,-1.1]]


@pytest.mark.parametrize('case',['case_a','case_b','case_c'])
def test_real_physics_known_location_oracle(case):
    with NavigationWorld(make_sample(case)) as world:
        assert not world.evaluate(0,[],'done')['task_success']
        result=world.search(world.sample.target_location)
        evaluation=world.evaluate(0,[result],'round_limit')
        assert result['success'] and result['end_step']>result['start_step']
        assert world.distance_m>.5 and evaluation['task_success']
        assert evaluation['termination_reason']=='round_limit'


def test_negative_local_inspection_does_not_clear_room_or_finish():
    with NavigationWorld(make_sample('case_c')) as world:
        result=world.search('kitchen_counter')
        assert result['success'] and not world.last_seen
        assert list(world.checked)==['kitchen_counter']
        assert not world.evaluate(0,[result],'done')['task_success']


def test_ask_answers_do_not_advance_physics_or_relocate_target():
    with NavigationWorld(make_sample('case_b')) as world:
        before=world.observation();pose=world.target_pose()
        answer=auto_answer(world.sample)
        validate_answer(answer)
        assert world.observation()==before and world.target_pose()==pose


def test_local_fov_range_and_los_required():
    with NavigationWorld(make_sample('case_a')) as world:
        assert not world.last_seen # target outside initial range/FOV
        result=world.search('kitchen_counter')
        assert world.visible_now and world.last_seen
        # A real intervening collision shape must occlude the geometric detector.
        x,y,yaw=world.pose();target=world.target_pose()
        world.box([.4,.05,.6],[(x+target[0])/2,(y+target[1])/2,.8],[.5,.5,.5,1])
        world.last_seen=None;world.perceive()
        assert not world.visible_now and world.last_seen is None


def test_scripted_noask_search_can_succeed_without_hidden_truth(initial):
    planner=ScriptedPlanner()
    assert not vars(planner)
    with NavigationWorld(make_sample('case_c')) as world:
        actions=[]
        for _ in range(8):
            payload=public_payload(world.sample.u0,world.observation(),[])
            action=planner.generate_action(payload)
            if action['kind']=='DONE':break
            actions.append(world.search(action['location_id']))
        assert world.evaluate(0,actions,'done')['task_success']
        assert all(a['success'] for a in actions) and len(actions)<=6


class SyntheticClient:
    def __init__(self):self.calls=[]
    def json(self,prompt,payload,*,stage,validator,max_tokens):
        self.calls.append((stage,payload,prompt))
        return validator({'decision':'CONTINUE'} if stage=='gate' else {'kind':'search','location_id':'kitchen_counter'})
    def noul(self,payload,instructions,criteria):
        self.calls.append(('gate',payload,instructions));return .6


@pytest.mark.parametrize('method',['llm_noask','llm_gate','jev_gate'])
def test_three_methods_share_identical_public_state_and_planner(initial,method):
    deep,jev=SyntheticClient(),SyntheticClient()
    gate,planner=components(method,deep,jev,.5)
    if gate:gate.decide(initial)
    planner.generate_action(initial)
    if method=='llm_noask':assert not jev.calls and len(deep.calls)==1 and gate is None
    if method=='llm_gate':assert [r[0] for r in deep.calls]==['gate','action']
    if method=='jev_gate':assert jev.calls[0][0]=='gate'
    assert deep.calls[-1][1] is initial
    assert len(prompt_hashes())==3


def test_jev_threshold_is_probability_not_confidence(initial):
    client=SyntheticClient()
    gate,_=components('jev_gate',client,client,.5)
    assert gate.decide(initial)==GateResult('ASK',.6)
    gate,_=components('jev_gate',client,client,.7)
    assert gate.decide(initial).decision=='CONTINUE'


def test_navigation_comparison_independent_reset_and_budget(tmp_path):
    config=Config(deepseek_key='unit-sentinel',typesafe_key='unit-sentinel2')
    manager=TaskManager(tmp_path,config=config,allow_live=True,live_episode_limit=3,api_limit=20)
    g=manager.create_comparison(dict(template='find_and_approach',unknown_preferences=1,navigation_case='case_c'),'nav-paired-unit')
    assert len(g['task_ids'])==3 and len({id(manager.tasks[i].history) for i in g['task_ids']})==3
    assert all(manager.tasks[i].audit.session is manager.ledger for i in g['task_ids'])
    assert manager.ledger.snapshot()['episodes']==3 and manager.ledger.snapshot()['attempts']==0
    assert g['prompt_hashes']==prompt_hashes() and g['evaluation_protocol']=='fixed_world_location'


def test_navigation_rejects_tabletop_options(tmp_path):
    manager=TaskManager(tmp_path)
    with pytest.raises(ValueError):manager.create(dict(template='find_and_approach',method='scripted_ask',answer_mode='auto',unknown_preferences=3),'invalid-nav-options')
