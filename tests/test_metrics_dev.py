"""Offline-only new-policy plumbing, data labels and task-level FPR tests."""
import copy
import json
from dataclasses import replace

import pytest

from when2ask.accounting import BudgetExceeded
from when2ask.nine_task_data import TEMPLATES,STUDY
from when2ask.nine_task_world import Adapter
from when2ask.metrics_dev_data import create_rows,audit_rows,load,entries
from when2ask.metrics_dev_agents import Unified,view,build_prompt,components
from when2ask.metrics_dev_report import explicit_ask,fpr_case,aggregate
from when2ask.metrics_dev_study import Ledger,run


def test_balanced_core_negatives_and_no_fake_must_ask_labels():
    rows=create_rows();r=audit_rows(rows)
    assert r['samples']==27 and r['physical_groups']==18 and r['core_fpr_negatives']==18
    assert sum(x['condition']=='preference_clarification_required' for x in rows)==7
    assert sum(x['condition']=='observable_fact_no_ask' for x in rows)==1
    assert sum(x['condition']=='search_hint_optional' for x in rows)==1
    assert all(x['sample']['partition']=='dev' for x in rows)


def test_contrast_stays_in_same_group_as_its_layout_variant():
    rows=create_rows()
    for t in TEMPLATES:
        r=[x for x in rows if x['sample']['template_id']==t]
        assert r[1]['sample']['group_id']==r[2]['sample']['group_id']
        assert r[1]['sample']['physical_scene']==r[2]['sample']['physical_scene']
        assert r[1]['sample']['theta_star']==r[2]['sample']['theta_star']


class OfflineClient:
    def __init__(self,value):self.value=value;self.calls=[]
    def json(self,prompt,public,*,stage,validator,max_tokens):
        self.calls.append(dict(stage=stage,prompt=prompt,public=public,max_tokens=max_tokens))
        return validator(self.value)


@pytest.mark.parametrize('template',TEMPLATES)
@pytest.mark.parametrize('ask',[False,True])
def test_unified_one_real_adapter_invocation_per_task_family_offline(template,ask):
    from when2ask.nine_task_benchmark import MEMORY
    from when2ask.task6_protocol import known_choices
    from when2ask.navigation_map import LOCATIONS
    s=next(s for s in load() if s.template_id==template)
    a=Adapter(s)
    try:
        state,public=view(a,[],[])
        if ask:
            q=(dict(type='select',text='Where?',requests=[dict(role='target_location',candidate_ids=list(LOCATIONS))])
               if template=='find_and_approach' else dict(type='all_preferences',text='Which choices?',requests=[]))
            wire=dict(kind='ASK',question=q)
        elif template in MEMORY:
            known=known_choices(public)
            choices={r:known.get(r,ids[0]) for r,ids in public['public_summary']['preference_candidates'].items()}
            wire=dict(working_choices=choices,completion_assessment=dict(ready_for_done=True,reason='Offline output validation only.'),remaining_plan=[dict(kind='DONE')])
        else:wire=dict(kind='DONE')
        client=OfflineClient(wire);q,action=Unified(template,client).decide(state)
        assert len(client.calls)==1 and client.calls[0]['stage']=='unified'
        assert (q is not None)==ask and (action is not None)==(not ask)
        assert client.calls[0]['public']==public
        assert not {'condition','fpr_core_negative','annotation_basis','theta_star','sample_id','partition'}&public.keys()
    finally:a.close()


@pytest.mark.parametrize('template',TEMPLATES)
def test_existing_baselines_still_share_planner_and_noask_skips_gate(template):
    marker=object();pairs=[components(template,m,marker,marker) for m in ('llm_noask','llm_gate','jev_gate')]
    assert pairs[0][0] is None
    assert len({type(p) for _,p in pairs})==1


def test_task_fpr_counts_multiple_false_alarms_once_and_noask_not_applicable():
    e=dict(method='llm_gate',turns=[dict(gate=dict(decision='ASK'))]*3,error=None)
    assert fpr_case(e,[],True) is True
    assert fpr_case(e,[],False) is None
    assert fpr_case({**e,'method':'llm_noask'},[],True) is None


def test_question_failure_does_not_hide_gate_false_positive():
    e=dict(method='llm_gate',turns=[dict(gate=dict(decision='ASK'))],error='SchemaError')
    assert fpr_case(e,[],True) is True


def test_malformed_unified_question_still_has_explicit_ask_decision():
    e=dict(method='llm_unified',turns=[{}],error='SchemaError')
    r=dict(backend='deepseek',stage='unified',response={'choices':[{'message':{'content':'{"kind":"ASK","question":{}}'}}]})
    assert fpr_case(e,[r],True) is True


def test_technical_failure_without_decision_is_not_a_true_negative():
    e=dict(method='llm_gate',turns=[],error='APIError')
    assert fpr_case(e,[],True) is None
    good=dict(backend='deepseek',stage='gate',status='ok')
    assert fpr_case({**e,'error':None},[good],True) is False


def test_fpr_denominator_excludes_censored_without_ask():
    keys=('api_attempts','retries','schema_errors','api_errors','unknown_cost_attempts','physical_failures',
          'deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens','wall_time_s')
    base=dict(method='jev_gate',success=True,api_seconds=1.,estimated_usd=.01,fpr_core_negative=True,**dict.fromkeys(keys,0))
    rows=[dict(base,false_alarm=True),dict(base,false_alarm=False),dict(base,false_alarm=None)]
    a=aggregate(rows,'jev_gate')
    assert a['fpr']==.5 and a['fpr_denominator']==2 and a['negative_censored']==1


def test_new_budget_cannot_reset_and_old_study_limits_are_not_changed(tmp_path):
    from when2ask.accounting import SessionLedger
    led=Ledger(tmp_path/'new',max_attempts=1,max_episodes=1)
    led.reserve('deepseek');led.start_episode('one')
    with pytest.raises(BudgetExceeded):Ledger(tmp_path/'new').reserve('jev')
    with pytest.raises(BudgetExceeded):Ledger(tmp_path/'new').start_episode('two')
    old=SessionLedger(tmp_path/'old',9999,9999,policy='phase2')
    assert old.max_attempts==200 and old.max_episodes==12


def test_no_paid_calls_without_explicit_live_flag():
    with pytest.raises(ValueError,match='--live'):run()
