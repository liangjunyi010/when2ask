"""Offline only: compact state changes no task facts, authority or Planner."""
import copy
import json
import pytest
from when2ask.config import ROOT,Config
from when2ask.gate_contract_dev import compact,Gate,GateProfile
from when2ask.gate_ready_dev import components,prompt_hashes,SELECTED,PROFILE
from when2ask.memory_dev_agents import Planner,prompt_hashes as v6_hashes
from when2ask.console_state import TaskManager


def state(template='buffer_exchange',method='jev_gate',index=0):
    return json.loads((ROOT/f'outputs/memory_planner_dev_v6/live/{template}__{method}/episode.json').read_text())['turns'][index]['public_payload']


@pytest.mark.parametrize('template', ['buffer_exchange','retrieve_restore','occlusion_inspection'])
def test_compact_is_pure_and_retains_public_information_that_defines_gate_contract(template):
    raw=state(template);before=copy.deepcopy(raw);small=compact(raw)
    assert raw==before and len(json.dumps(small))<len(json.dumps(raw))
    for key in ['instruction','history']:assert small[key]==raw[key]
    for key in ['task','affordances','held_object','sensor','inspections','reports']:
        assert small['observation'][key]==raw['observation'][key]
    for key in ['confirmed_choices','own_working_choices','unresolved_roles','object_memory','goal_requirements']:
        assert small['public_summary'][key]==raw['public_summary'][key]
    assert 'expected' not in json.dumps(small) and 'task_success' not in json.dumps(small) and 'theta_star' not in json.dumps(small)


def test_prior_occluded_object_memory_and_finished_guess_are_not_lost():
    full=state('retrieve_restore','jev_gate',4);small=compact(full)
    assert small['public_summary']['object_memory']['stored_cup']['status']=='remembered_occluded'
    assert small['public_summary']['observed_locations']['stored_block']==['delivery_pad']
    small=compact(state('buffer_exchange','llm_noask',3))
    assert small['public_summary']['confirmed_choices']=={}
    assert small['public_summary']['own_working_choices']['buffer_pad']['value']=='buffer_front'
    assert all(r['currently_observed_at_target'] for r in small['public_summary']['required_final_relations'])


class Jev:
    def __init__(self,p):self.p=p;self.calls=[]
    def noul(self,public,instructions,criteria):self.calls.append((public,instructions,criteria));return self.p


def test_fixed_threshold_score_direction_and_identical_shared_contract():
    public=state();client=Jev(.49);gate=Gate(client,'jev',.5,SELECTED)
    assert gate.decide(public).decision=='CONTINUE'
    assert client.calls[0][0]==compact(public)
    client.p=.5;assert gate.decide(public).decision=='ASK'
    assert SELECTED.explicit_contract is False
    assert prompt_hashes()==v6_hashes()
    assert not any(token in SELECTED.prompts()['gate'] for token in ['expected_decision','correct_buffer'])


def test_all_methods_share_exact_v6_planner_noask_never_calls_gate():
    pairs=[components(m,object(),object(),.5) for m in ['llm_noask','llm_gate','jev_gate']]
    assert pairs[0][0] is None and all(type(p) is Planner for _,p in pairs)
    assert all(g.profile==SELECTED and g.threshold==.5 for g,_ in pairs if g)


def test_profile_is_optional_existing_profiles_unchanged_and_comparison_paired(tmp_path):
    manager=TaskManager(tmp_path,config=Config(deepseek_key='unit',typesafe_key='unit'),allow_live=True)
    base=dict(template='buffer_exchange',method='scripted_ask',answer_mode='manual',unknown_preferences=1)
    assert manager.create(base,'unit-v7-default')['planner_profile']=='default_v1'
    for name in ['grounded_dev_v5','memory_dev_v6',PROFILE]:assert manager.create(dict(base,planner_profile=name),'unit-v7-'+name)['planner_profile']==name
    group=manager.create_comparison(dict(template='buffer_exchange',unknown_preferences=1,planner_profile=PROFILE),'unit-v7-comparison')
    assert group['prompt_hashes']==v6_hashes() and group['gate_configuration']['selected_factor_profile']=='s1c0'
    assert len({manager.tasks[k].sample.sample_id for k in group['task_ids']})==1
    with pytest.raises(ValueError):manager.validate_options(dict(base,template='pack_and_cover',planner_profile=PROFILE))
    assert manager.ledger.snapshot()['attempts']==0
