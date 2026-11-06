"""No paid calls. Real dynamics and synthetic client contracts are kept distinct."""
import json
from dataclasses import replace

import pytest

from when2ask.accounting import BudgetExceeded
from when2ask.nav2_agents import components,CRITERIA,hashes
from when2ask.nav2_public import payload,evidence,motion_estimate,reference_values
from when2ask.nav2_runner import run_episode
from when2ask.nav2_study import Ledger
from when2ask.nav2_task import Sample,samples
from when2ask.nav2_world import World
from when2ask.navigation_protocol import goal_observed


@pytest.fixture(scope='module')
def initial():
    s=Sample('private','study_shelf',1,1)
    with World(s) as w:return s,w.observation()


@pytest.mark.parametrize('style',['raw','summary'])
def test_hidden_target_and_ids_never_enter_public_payload(initial,style):
    s,obs=initial;p=payload(s.u0,obs,[],s.public_contract(),style)
    other=replace(s,sample_id='different-private-id',target_location='living_cabinet')
    assert p==payload(other.u0,obs,[],other.public_contract(),style)
    assert not {'sample_id','nominal_reference','theta_star','reference_decision'} & set(p)


def test_actual_initial_physics_and_images_do_not_disclose_target():
    observations=[];frames=[]
    for target in ['kitchen_counter','study_shelf']:
        with World(Sample('private',target,.5,30)) as w:
            observations.append(w.observation());frames.append(w.render(320,180).tobytes())
    assert observations[0]==observations[1] and frames[0]==frames[1]


def test_raw_and_summary_hold_same_underlying_facts(initial):
    s,obs=initial;a=payload(s.u0,obs,[],s.public_contract(),'raw');b=payload(s.u0,obs,[],s.public_contract(),'summary')
    assert a=={k:v for k,v in b.items() if k!='public_cost_summary'}
    assert set(b['public_cost_summary']['alternatives'])==set(s.public_contract()['prior'])


@pytest.mark.parametrize('delay',[1,30])
def test_actual_reply_delay_is_explicit_not_v1_constant(initial,delay):
    s,obs=initial;s=replace(s,answer_delay_s=delay)
    for style in ['raw','summary']:
        assert payload(s.u0,obs,[],s.public_contract(),style)['cost_contract']['answer_delay_s']==delay


def test_belief_conditions_only_on_public_negative_evidence(initial):
    s,obs=initial;obs=dict(obs,checked_locations={'kitchen_counter':{'target_detected':False}})
    e=evidence(s.u0,obs,[],s.public_contract())
    assert e['posterior_from_public_facts']['kitchen_counter']==0
    assert all(abs(v-.2)<1e-9 for k,v in e['posterior_from_public_facts'].items() if k!='kitchen_counter')


def test_public_hint_is_reused_but_does_not_count_as_detection(initial):
    s,obs=initial;h=[dict(kind='user_answer',response={'choices':{'target_location':'living_cabinet'}})]
    p=payload(s.u0,obs,h,s.public_contract());e=p['public_cost_summary']
    assert e['supported_location']=='living_cabinet' and not e['completion_observed']
    assert reference_values(p)['decision']=='CONTINUE'


def test_nominal_reference_changes_with_cost_not_hidden_truth(initial):
    s,obs=initial
    cheap=reference_values(payload(s.u0,obs,[],s.public_contract()))
    expensive=replace(s,answer_delay_s=30)
    costly=reference_values(payload(expensive.u0,obs,[],expensive.public_contract()))
    assert cheap['decision']=='ASK' and costly['decision']=='CONTINUE'
    assert cheap==reference_values(payload(replace(s,target_location='living_table').u0,obs,[],s.public_contract()))


def test_one_remaining_candidate_has_no_question_value(initial):
    s,obs=initial;obs=dict(obs,checked_locations={k:{'target_detected':False} for k in s.public_contract()['prior'] if k!='study_shelf'})
    assert reference_values(payload(s.u0,obs,[],s.public_contract()))['decision']=='CONTINUE'


def test_speed_changes_estimated_and_actual_motion(initial):
    s,obs=initial;times=[]
    for speed in [1,.5]:
        sample=replace(s,speed_factor=speed)
        with World(sample) as w:
            r=w.search('study_shelf');times.append((r['end_step']-r['start_step'])*w.DT)
            assert w.evaluate(0,[r],'round_limit')['task_success'] and r['success']
    assert times[1]>times[0]*1.6
    assert motion_estimate(obs['robot_pose'],'study_shelf',replace(s,speed_factor=.5).public_contract())>motion_estimate(obs['robot_pose'],'study_shelf',s.public_contract())


def test_dataset_factorial_and_group_isolation():
    rows=samples();assert len(rows)==24
    assert len({s.sample_id for s in rows})==24 and len({s.group_id for s in rows})==1
    assert {(s.speed_factor,s.answer_delay_s) for s in rows}=={(1,1),(1,30),(.5,1),(.5,30)}


class SyntheticClient:
    def __init__(self):self.calls=[]
    def json(self,prompt,public,*,stage,validator,max_tokens):
        self.calls.append((stage,prompt,public))
        return validator({'decision':'CONTINUE'} if stage=='gate' else {'kind':'search','location_id':'living_cabinet'})
    def noul(self,public,instructions,criteria):
        self.calls.append(('gate',instructions,public));assert criteria==CRITERIA['cost_exclusive'];return .7


@pytest.mark.parametrize('method',['llm_noask','llm_gate','jev_gate'])
def test_noask_skips_gate_others_gate_before_identical_planner(initial,method):
    s,obs=initial;public=payload(s.u0,obs,[],s.public_contract());deep,jev=SyntheticClient(),SyntheticClient()
    gate,planner=components(method,deep,jev)
    if gate:gate.decide(public)
    planner.generate_action(public)
    assert deep.calls[-1][0]=='action' and deep.calls[-1][2] is public
    if method=='llm_noask':assert gate is None and len(deep.calls)==1 and not jev.calls
    if method=='llm_gate':assert deep.calls[0][0]=='gate'
    if method=='jev_gate':assert jev.calls[0][0]=='gate'
    assert len(hashes())==5


def test_exclusive_criteria_are_cost_comparison_not_search_existence():
    assert 'equal or lower' in CRITERIA['cost_exclusive']['false']
    assert 'useful autonomous' not in CRITERIA['cost_exclusive']['false'].lower()


def test_stage_and_global_request_budgets(tmp_path):
    a=Ledger(tmp_path,'ablation');b=Ledger(tmp_path,'episodes')
    for _ in range(60):a.reserve('deepseek')
    with pytest.raises(BudgetExceeded):a.reserve('deepseek')
    for _ in range(140):b.reserve('jev')
    with pytest.raises(BudgetExceeded):b.reserve('jev')
    assert b.snapshot()['attempts']==200


def test_episode_budget_never_exceeds_twelve(tmp_path):
    l=Ledger(tmp_path,'episodes')
    for i in range(12):l.start_episode(str(i))
    with pytest.raises(BudgetExceeded):l.start_episode('extra')


def test_ask_freeze_and_truth_independent_success_in_actual_runner(tmp_path):
    from when2ask.agents import GateResult
    from when2ask.navigation_agents import ScriptedPlanner
    class TestGate:
        def decide(self,p):return GateResult('ASK' if not p['public_history'] else 'CONTINUE')
    class TestPlanner(ScriptedPlanner):
        def generate_action(self,p):
            if goal_observed({'observation':p['observation']}):return {'kind':'DONE'}
            return dict(kind='search',location_id=p['public_cost_summary']['supported_location'])
    factory=lambda *args:(TestGate(),TestPlanner())
    e=run_episode(Sample('unit','living_cabinet',1,1),'unit',tmp_path/'episode',Ledger(tmp_path/'ledger','episodes'),realtime=False,component_factory=factory)
    assert e['evaluation']['task_success'] and e['clarification_burden']==1
    assert e['turns'][0]['ask_check']['state_unchanged'] and e['turns'][0]['answer_wait_s']>=1
    assert e['api_cost']['api_attempts']==0
    assert e['evidence_kind']=='injected_offline_test_policy_real_pybullet'
    op=e['operational_cost'];assert abs(op['operational_seconds']-(op['motion_sim_s']+op['reply_wait_wall_s']+5))<1e-6
