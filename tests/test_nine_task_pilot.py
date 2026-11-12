"""Offline only: these tests never instantiate an authenticated HTTP request."""
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from when2ask.accounting import BudgetExceeded
from when2ask.nine_task_data import TEMPLATES, STUDY, load, audit, shape, digest
from when2ask.nine_task_benchmark import Ledger, components, view, run_all
from when2ask.nine_task_world import Adapter, navigation_class
from when2ask.task6_protocol import Question
from when2ask.user_simulator import PreferenceResolver


def test_all_nine_tasks_have_multiple_independent_cases():
    samples=load();assert len(samples)==36
    assert len({s.group_id for s in samples})==36
    for template in TEMPLATES:
        assert [sum(s.template_id==template and s.partition==p for s in samples) for p in ('dev','test')]==[2,2]
    assert audit(samples)['group_isolation']


def test_same_scene_alias_or_truth_cannot_cross_split():
    s=load('dev')[0]
    with pytest.raises(ValueError,match='Group split leakage'):
        audit([s,replace(s,sample_id='another_alias',partition='test')])


def test_group_fingerprint_ignores_hidden_label_and_candidate_order():
    s=next(s for s in load() if s.template_id=='occlusion_inspection')
    scene=s.scene();before=digest(shape(scene));scene['label']['code']='another code'
    assert digest(shape(scene))==before


@pytest.mark.parametrize('template',TEMPLATES)
def test_noask_skips_gate_and_all_methods_share_planner_class(template):
    # Factories may bind an inert object but must never make a request.
    sentinel=object()
    agents=[components(template,m,sentinel,sentinel) for m in ('llm_noask','llm_gate','jev_gate')]
    assert agents[0][0] is None
    assert type(agents[0][1]) is type(agents[1][1]) is type(agents[2][1])
    assert all(planner.client is sentinel for _,planner in agents)


@pytest.mark.parametrize('template',TEMPLATES)
def test_public_payload_does_not_read_undisclosed_truth(template):
    s=next(s for s in load('dev') if s.template_id==template and s.unknown_slots>0)
    a=Adapter(s)
    try:
        _,before=view(a,[],[])
        theta=copy.deepcopy(s.theta_star)
        for slot in theta:
            if slot not in s.initial_disclosed_slots:
                theta[slot]=next(c for c in s.slots[slot]['candidate_ids'] if c!=theta[slot])
        # Swap the private evaluator/simulator data while holding actual physics,
        # observations and initial public instruction fixed.
        changed=replace(s,theta_star=theta)
        a.sample=changed;a.world.sample=changed
        _,after=view(a,[],[])
        assert before==after
        assert not {'theta_star','group_id','sample_id','partition'} & before.keys()
    finally:a.close()


def test_ask_freezes_actual_physics_and_discloses_only_requested_slot():
    s=next(s for s in load('dev') if s.template_id=='pack_and_cover' and s.unknown_slots==3)
    a=Adapter(s)
    try:
        q=Question('select','Which cup?',(dict(role='cup',candidate_ids=s.slots['cup_choice']['candidate_ids']),),('cup','block','lid'))
        before=a.world.snapshot();answer,burden=PreferenceResolver(s.slots,s.theta_star).answer(q)
        after=a.world.snapshot()
        assert before==after
        assert answer=={'choices':{'cup':s.theta_star['cup_choice']}}
        assert burden==1
    finally:a.close()


def test_new_mobile_map_does_not_mutate_legacy_map():
    from when2ask.navigation_map import LOCATIONS
    old=copy.deepcopy(LOCATIONS)
    s=next(s for s in load() if s.template_id=='find_and_approach')
    _,map_module=navigation_class(s.scene())
    assert map_module.LOCATIONS!=old
    assert LOCATIONS==old
    assert 'target_location' not in map_module.public_map()


def test_persistent_global_budget_cannot_be_reset_or_exceeded(tmp_path):
    ledger=Ledger(tmp_path,max_attempts=2,max_episodes=1)
    ledger.start_episode('first');ledger.reserve('deepseek');ledger.reserve('jev')
    with pytest.raises(BudgetExceeded):Ledger(tmp_path).reserve('deepseek')
    with pytest.raises(BudgetExceeded):Ledger(tmp_path).start_episode('second')
    assert ledger.snapshot()['attempts']==2


def test_online_operations_require_explicit_live():
    with pytest.raises(ValueError,match='Explicit --live'):run_all()


def test_wrong_patrol_sequence_cannot_score_success():
    s=next(s for s in load() if s.template_id=='patrol_return')
    a=Adapter(s)
    try:
        a.world.execute(dict(kind='return_home'))
        score=a.score(0,[],'done')
        assert not score['task_success']
        assert not score['conditions']['required_stations_physically_inspected']
    finally:a.close()


def test_every_task_evaluator_rejects_initial_done():
    for template in TEMPLATES:
        s=next(s for s in load('dev') if s.template_id==template)
        a=Adapter(s)
        try:assert not a.score(0,[],'done')['task_success']
        finally:a.close()
