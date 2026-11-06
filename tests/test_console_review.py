"""Observer privacy, public-only answer grounding and completed-task persistence."""
import json
from dataclasses import replace

import pytest

from when2ask.config import Config
from when2ask.console_answers import text_answer
from when2ask.console_state import TaskManager
from when2ask.console_review import review


def task(tmp_path,template='pack_and_cover'):
    m=TaskManager(tmp_path,config=Config())
    row=m.create(dict(template=template,method='scripted_ask',answer_mode='manual'),'review-unit-0001')
    return m,m.tasks[row['id']]


def test_truth_hidden_until_terminal_and_not_disclosed_by_private_change(tmp_path):
    m,t=task(tmp_path);before=review(t)
    other=next(x for x in t.sample.slots['block_choice']['candidate_ids'] if x!=t.sample.theta_star['block_choice'])
    t.sample=replace(t.sample,theta_star={**t.sample.theta_star,'block_choice':other})
    assert review(t)==before and before['ground_truth'] is None
    for status in ('queued','executing','waiting_answer','finalizing'):
        t.status=status;assert review(t)['ground_truth'] is None
    t.status='done';assert review(t)['ground_truth']['evaluated']


def test_manual_reference_and_effective_goal_are_both_visible_after_end(tmp_path):
    m,t=task(tmp_path)
    other=next(x for x in t.sample.slots['block_choice']['candidate_ids'] if x!=t.sample.theta_star['block_choice'])
    t.goal_overrides['block_choice']=other;t.status='done'
    r=review(t)['ground_truth'];assert r['initial']!=r['evaluated'] and r['manual_changes'][0]['role']=='block'


def test_navigation_manual_claim_cannot_change_revealed_world_truth(tmp_path):
    m,t=task(tmp_path,'find_and_approach');t.history=[dict(kind='user_answer',response={'choices':{'target_location':'study_desk'}})]
    t.status='done';r=review(t)['ground_truth']
    assert r['initial']==r['evaluated'] and r['evaluated'][0]['object_id']=='living_cabinet'


def test_full_dialogue_is_not_truncated_with_short_visible_history(tmp_path):
    m,t=task(tmp_path)
    t.turns=[dict(round=i,question={'text':f'Question {i}'},question_id=str(i),user_answer={'choices':{'block':'x'}},answer_source='human') for i in range(12)]
    t.answers['0']={'input_text':'绿块'}
    events=review(t)['conversation']
    assert len(events)==24 and events[0]['value']['text']=='Question 0' and events[1]['input_text']=='绿块'


def pending():
    return dict(type='select',requests=[dict(role='block',candidate_ids=['g','y']),dict(role='lid',candidate_ids=['b','w'])],
        candidates={'g':'green block','y':'yellow block','b':'black lid','w':'white lid'})


@pytest.mark.parametrize('text',['绿块、黑盖','green block and black lid','green and black','g b'])
def test_text_resolves_visible_candidates_only(text):
    assert text_answer(pending(),text)=={'choices':{'block':'g','lid':'b'}}


@pytest.mark.parametrize('text',['绿色或者黄色方块，黑盖','用你觉得好的','',None])
def test_ambiguous_answer_never_silently_selects_default(text):
    with pytest.raises(ValueError):text_answer(pending(),text)


def test_navigation_text_needs_exact_landmark():
    q=dict(type='select',requests=[dict(role='target_location',candidate_ids=['living_cabinet','living_table'])],
        candidates={'living_cabinet':'Living room cabinet','living_table':'Living room table'})
    assert text_answer(q,'菜刀在客厅的柜子上')=={'choices':{'target_location':'living_cabinet'}}
    with pytest.raises(ValueError):text_answer(q,'在客厅')


def test_completed_snapshot_can_be_restored_without_model_call(tmp_path):
    m,t=task(tmp_path);t.status='done'
    with m.changed:m.publish(t)
    restored=TaskManager(tmp_path,config=Config())
    rows=restored.public_tasks();assert len(rows)==1 and rows[0]['archived_readonly']
    assert rows[0]['review']['truth_revealed'] and rows[0]['review']['ground_truth']
    assert restored.ledger.snapshot()['attempts']==0 and not restored.tasks


def test_noask_message_explains_absent_form(tmp_path):
    m,t=task(tmp_path);t.method='llm_noask'
    assert 'NoAsk' in review(t)['interaction']['message'] and not review(t)['interaction']['manual_form_available']
