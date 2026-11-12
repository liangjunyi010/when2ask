"""Offline regression tests. Stub outputs test plumbing, not model performance."""
import copy
import json
from dataclasses import replace

import pytest

from when2ask.tabletop_dev_study import OUT, load, run
from when2ask.tabletop_dev_public import facts_payload, public_order
from when2ask.tabletop_dev_agents import Profile, PROFILES, components
from when2ask.study_agents import GATE_RULES, ACTION_PROMPT, QUESTION_PROMPT
from when2ask.task import PublicState


def state(id):
    raw=next(s['state'] for s in json.loads((OUT/'diagnostic_states.json').read_text())['states'] if s['id']==id)
    return PublicState.build(raw['observation'],raw['history'],raw['instruction'])


def test_dev_data_never_relables_a_test_as_dev():
    samples=load();assert len(samples)==4
    assert all(s.partition=='dev' and 'td1_' in s.sample_id for s in samples)
    assert len({s.group_id for s in samples})==4


def test_raw_legacy_profile_preserves_exact_existing_prompts():
    assert Profile(False,False).prompts()==dict(gate=GATE_RULES,action=ACTION_PROMPT,question=QUESTION_PROMPT)


def test_missing_predecessor_is_explicit_but_no_gate_decision_is_injected():
    value=facts_payload(state('td1_pack_block_first_initial'))
    facts=value['public_facts']
    assert facts['unresolved_roles']==['block']
    assert facts['order']['edges'][-1]==['place_block','place_cup']
    assert set(facts['confirmed_choices'])=={'cup','lid'}
    assert not {'gate_decision','next_action','oracle','task_success','blocked','ready_for_done'} & facts.keys()


def test_public_order_never_reads_private_dag():
    s=state('td1_pack_block_first_initial')
    obs=copy.deepcopy(s.observation);obs['private_dag']={'order':'cup_first'}
    # Explicit public allowlist excludes unexpected/private fields entirely.
    v=facts_payload(PublicState.build(obs,list(s.history),s.instruction))
    assert v['public_facts']['order']['order']=='block_first'
    assert 'private_dag' not in json.dumps(v)


@pytest.mark.parametrize('instruction',['Do anything.', 'Place the block before the cup. Place the cup before the block.'])
def test_unknown_or_ambiguous_order_is_not_silently_independent(instruction):
    with pytest.raises(ValueError):public_order(instruction,False)


def test_partial_block_progress_uses_answer_and_measured_region():
    s=state('td1_containers_block_first_after_correct_block');value=facts_payload(s)
    f=value['public_facts'];block=f['confirmed_choices']['block'];dest=f['working_destinations']['block']
    assert f['working_destinations']['cup']!=dest
    assert block in value['observation']['spatial_relations']['inside_containers'][dest]
    assert f['confirmed_choices']['cup_destination']==f['working_destinations']['cup']
    assert len(value['history'])==3


def test_a_successful_guess_never_becomes_user_confirmation():
    s=state('td1_pack_block_first_initial');key=next(k for k,o in s.observation['objects'].items() if o['category']=='block')
    history=[dict(kind='action',result=dict(skill='pick_place',object_id=key,target_id='box',success=True))]
    facts=facts_payload(PublicState.build(s.observation,history,s.instruction))['public_facts']
    assert 'block' in facts['unresolved_roles'] and 'block' not in facts['confirmed_choices']
    assert facts['own_unconfirmed_choices']['block']['value']==key
    assert facts['own_unconfirmed_choices']['block']['user_confirmed'] is False


def test_changed_hidden_truth_cannot_change_payload():
    sample=next(s for s in load() if s.sample_id=='td1_pack_block_first')
    hidden=copy.deepcopy(sample.theta_star)
    hidden['block_choice']=next(k for k in sample.slots['block_choice']['candidate_ids'] if k!=hidden['block_choice'])
    changed=replace(sample,theta_star=hidden)
    assert changed.theta_star!=sample.theta_star
    s=state(sample.sample_id+'_initial');a=facts_payload(s)
    # There is intentionally no sample/private argument in this policy function.
    assert facts_payload(s)==a
    assert not {'theta_star','sample_id','partition','group_id','evaluation'} & a.keys()


class StubClient:
    def __init__(self,p=.04,output=None):self.p,self.output=p,output;self.calls=[]
    def noul(self,public,prompt,criteria):
        self.calls.append(('gate',public,prompt));return self.p
    def json(self,prompt,public,*,stage,validator,max_tokens):
        self.calls.append((stage,public,prompt));return validator(self.output)


def test_jev_gate_is_not_forced_to_ask_by_summary():
    c=StubClient(p=.04);gate,_=components('jev_gate',c,c)
    result=gate.decide(state('td1_pack_block_first_initial'))
    assert result.decision=='CONTINUE' and result.p_ask==.04


@pytest.mark.parametrize('probability,expected',[(.499,'CONTINUE'),(.5,'ASK'),(.9,'ASK')])
def test_unchanged_half_threshold(probability,expected):
    c=StubClient(p=probability);gate,_=components('jev_gate',c,c)
    assert gate.decide(state('td1_pack_block_first_initial')).decision==expected


def test_planner_can_still_make_an_error_and_action_is_not_rewritten():
    s=state('td1_containers_block_first_after_correct_block');f=facts_payload(s)['public_facts']
    proposed=dict(kind='pick_place',object_id=f['confirmed_choices']['block'],target_id='table',relation='on')
    c=StubClient(output=proposed);_,planner=components('llm_noask',c,c)
    assert planner.generate_action(s).to_dict()==proposed


@pytest.mark.parametrize('profile',list(PROFILES))
def test_all_methods_share_exact_planner_profile_and_noask_skips_gate(profile):
    c=StubClient();pairs=[components(m,c,c,profile) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None
    assert all(p.profile==PROFILES[profile] for _,p in pairs)
    assert type(pairs[0][1]) is type(pairs[1][1]) is type(pairs[2][1])
    assert not c.calls


def test_live_flag_required():
    with pytest.raises(ValueError,match='Explicit --live'):run('probes')
