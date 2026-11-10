"""Offline public-grounding regressions and real physics; no paid API requests."""
import copy
import json
from dataclasses import replace

import pytest

from when2ask.config import ROOT
from when2ask.buffer_public_dev import augment,diagnose_action
from when2ask.buffer_planner_dev import Profile,Planner,components
from when2ask.buffer_study_dev import cases,sample_for
from when2ask.task6_agents import ACTION,QUESTION,GATE
from when2ask.task6_protocol import payload,action
from when2ask.task6_spec import make_sample
from when2ask.task6_world import make_world
from when2ask.task6_evaluator import evaluate


def recorded(round_index):
    return copy.deepcopy(json.loads((ROOT/'outputs/six_tasks_dev_v1/live/buffer_exchange/episode.json').read_text())['turns'][round_index]['public_payload'])


def test_first_regression_has_correct_world_state_and_complete_wire_history():
    public=recorded(2)
    calls=[json.loads(s) for s in (ROOT/'outputs/six_tasks_dev_v1/live/buffer_exchange/api_attempts.jsonl').read_text().splitlines()]
    request=next(r['request'] for r in calls if r['round']==2)
    assert json.loads(request['messages'][1]['content'])==public
    assert len(public['history'])==2
    assert public['observation']['containers']['slot_left']['contents']==['item_b']
    assert public['observation']['containers']['slot_right']['contents']==[]


def test_summary_keeps_completed_relation_and_assumption_separate_from_confirmation():
    public=recorded(2);before=copy.deepcopy(public);summary=augment(public)['public_summary']
    assert public==before
    assert summary['object_locations']=={'item_a':['buffer_front'],'item_b':['slot_left']}
    assert summary['explicit_final_relations']==[
        dict(object_id='item_a',target_id='slot_right',currently_inside=False),
        dict(object_id='item_b',target_id='slot_left',currently_inside=True)]
    assert summary['confirmed_user_choices']=={}
    assert summary['unresolved_user_roles']==['buffer_pad']
    assert summary['agent_buffer_assumption']==dict(value='buffer_front',source='own_first_successful_parking',user_confirmed=False)
    assert 'next_action' not in summary and 'task_success' not in summary


def test_latest_measured_state_overrides_stale_successful_history_after_failure():
    public=recorded(9);summary=augment(public)['public_summary']
    assert summary['object_locations']['item_b']==[]
    assert summary['chronological_action_results'][-1]['success'] is False
    assert any(r['target_id']=='slot_right' and r['success'] for r in summary['chronological_action_results'])
    assert summary['current_regions']['slot_right']==[]


def test_failed_attempt_does_not_create_confirmed_or_assumed_choice():
    public=recorded(0)
    public['history']=[dict(kind='action',result=dict(skill='move',object_id='item_a',target_id='buffer_front',success=False,reason='grasp_failed',start_step=240,end_step=240))]
    summary=augment(public)['public_summary']
    assert summary['agent_buffer_assumption'] is None
    assert summary['confirmed_user_choices']=={}


def test_disclosed_choice_takes_precedence_without_rewriting_past_used_pad():
    public=recorded(2);public['history'].append(dict(kind='user_answer',response=dict(choices=dict(buffer_pad='buffer_back'))))
    summary=augment(public)['public_summary']
    assert summary['confirmed_user_choices']==dict(buffer_pad='buffer_back')
    assert summary['agent_buffer_assumption'] is None
    assert summary['prior_successful_parking'][0]['buffer_id']=='buffer_front'


def test_summary_neither_masks_affordances_nor_rewrites_bad_model_output():
    public=recorded(2);model=augment(public)
    assert model['observation']['affordances']==public['observation']['affordances']
    proposed=dict(kind='move',object_id='item_b',target_id='slot_right')
    assert action(proposed,model)==proposed
    class FakeClient:
        def json(self,system,public,stage,validator,max_tokens):return validator(copy.deepcopy(proposed))
    assert Planner(FakeClient(),Profile(True,True)).generate_action(model)==proposed
    assert diagnose_action(public,proposed)['undoes_currently_satisfied_final_relation']


def test_occupied_target_is_diagnostic_not_a_hidden_action_filter():
    public=recorded(4);proposed=dict(kind='move',object_id='item_a',target_id='slot_right')
    assert diagnose_action(public,proposed)['targets_occupied_single_capacity_slot']
    assert action(proposed,augment(public))==proposed


def test_baseline_profile_is_exact_original_prompt_and_all_methods_share_dev_planner():
    assert Profile(False,False).prompts()==dict(action=ACTION,question=QUESTION,gate=GATE)
    profile=Profile(True,True)
    pairs=[components(m,object(),object(),.5,profile) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None
    assert all(type(p)==Planner and p.profile.hashes()==profile.hashes() for _,p in pairs)
    assert all(g.threshold==.5 for g,_ in pairs if g)


def test_compact_context_keeps_only_latest_execution_and_complete_public_dialogue():
    from when2ask.buffer_context_dev_v3 import compact
    public=recorded(7);before=copy.deepcopy(public)
    public['history'].append(dict(kind='ask',question=dict(text='Which buffer?')))
    public['history'].append(dict(kind='user_answer',response=dict(choices=dict(buffer_pad='buffer_back'))))
    result=compact(public)
    assert len([e for e in result['history'] if e['kind']=='action'])==1
    assert [e['kind'] for e in result['history']]==['action','ask','user_answer']
    assert result['public_summary']['confirmed_user_choices']==dict(buffer_pad='buffer_back')
    assert result['public_summary']['execution_history_coverage']['total_actions']==7
    assert 'chronological_action_results' not in result['public_summary']
    assert result['observation']['affordances']==public['observation']['affordances']
    assert public['history'][:7]==before['history']


def test_compact_and_append_profiles_use_identical_prompts_for_context_ablation():
    from when2ask.buffer_context_dev_v3 import CompactProfile
    for repaired in (False,True):
        assert CompactProfile(True,repaired).hashes()==Profile(True,repaired).hashes()


def test_structured_planner_returns_model_action_without_progress_or_preference_rewrite():
    from when2ask.buffer_plan_dev_v4 import Planner as GroundedPlanner,PlanProfile
    proposed=dict(kind='move',object_id='item_b',target_id='slot_right')
    class Client:
        def json(self,system,public,stage,validator,max_tokens):
            assert max_tokens==400
            return validator(dict(current_locations=dict(item_a=['buffer_front'],item_b=['slot_left']),
                final_targets=dict(item_a='slot_right',item_b='slot_left'),working_buffer='buffer_front',remaining_plan=[proposed]))
    profile=PlanProfile(True,True,True);planner=GroundedPlanner(Client(),profile)
    assert planner.generate_action(profile.serialize(recorded(2)))==proposed
    assert diagnose_action(recorded(2),proposed)['undoes_currently_satisfied_final_relation']


def test_structured_plan_checks_only_public_grounding():
    from when2ask.buffer_plan_dev_v4 import Planner as GroundedPlanner,PlanProfile
    class Client:
        def json(self,system,public,stage,validator,max_tokens):
            return validator(dict(current_locations=dict(item_a=['slot_left'],item_b=['slot_right']),
                final_targets=dict(item_a='slot_right',item_b='slot_left'),working_buffer='buffer_front',remaining_plan=[dict(kind='DONE')]))
    profile=PlanProfile(True,True,True)
    from when2ask.api import SchemaError
    with pytest.raises(SchemaError,match='latest measured'):
        GroundedPlanner(Client(),profile).generate_action(profile.serialize(recorded(2)))


def test_structured_planner_is_shared_by_all_three_methods():
    from when2ask.buffer_plan_dev_v4 import Planner as GroundedPlanner,PlanProfile,components as make
    profile=PlanProfile(True,True,True)
    pairs=[make(m,object(),object(),.5,profile) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None
    assert all(type(p)==GroundedPlanner and p.profile.hashes()==profile.hashes() for _,p in pairs)


def test_opposite_hidden_preferences_have_identical_initial_public_payload():
    back=sample_for(next(c for c in cases() if c['case_id']=='unknown_back_v2_noask'))
    front=sample_for(next(c for c in cases() if c['case_id']=='unknown_front_v2_noask'))
    assert back.theta_star!=front.theta_star and back.u0==front.u0
    with make_world(back) as a,make_world(front) as b:
        assert augment(payload(back.u0,a.observation(),[]))==augment(payload(front.u0,b.observation(),[]))


@pytest.mark.parametrize('pad',['buffer_front','buffer_back'])
def test_original_physics_and_evaluator_separate_swap_execution_from_preference(pad):
    sample=make_sample('buffer_exchange')
    with make_world(sample) as world:
        actions=[world.execute(dict(kind='move',object_id='item_a',target_id=pad)),
                 world.execute(dict(kind='move',object_id='item_b',target_id='slot_left')),
                 world.execute(dict(kind='move',object_id='item_a',target_id='slot_right'))]
        assert all(a['success'] for a in actions)
        result=evaluate(world,sample,actions=actions,termination='done')
        assert result['conditions']['items_exchanged'] and result['conditions']['buffers_empty_at_end']
        assert result['task_success']==(pad==sample.theta_star['buffer_pad_choice'])
