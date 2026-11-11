"""Offline independent-layout benchmark validity; never calls paid APIs."""
import copy
import json
from collections import Counter
from dataclasses import replace
import pytest
from when2ask.config import ROOT
from when2ask.three_task_data import load,audit_samples,geometry,distance,MIN_GROUP_DISTANCE,Sample
from when2ask.task6_world import make_world
from when2ask.task6_protocol import payload
from when2ask.memory_dev_public import serialize
from when2ask.gate_contract_dev import compact


def test_full_new_dataset_has_distinct_groups_and_balanced_test_conditions():
    rows=load('r2');a=audit_samples(rows)
    assert a['distribution']['dev']['samples']==24 and a['distribution']['test']['samples']==12
    assert a['distribution']['dev']['groups']==6 and a['distribution']['test']['groups']==12
    assert a['distribution']['test']['candidate_rank']=={'0':6,'1':6}
    assert a['minimum_cross_split_group_distance_m']>=MIN_GROUP_DISTANCE
    test=[s for s in rows if s.partition=='test']
    for template in {s.template_id for s in rows}:
        subset=[s for s in test if s.template_id==template]
        assert len(subset)==4 and len({s.group_id for s in subset})==4
        assert Counter(len(s.initial_disclosed_slots) for s in subset)=={0:2,1:2}
        assert sorted(Counter(next(iter(s.theta_star.values())) for s in subset).values())==[2,2]


def test_changing_colour_order_code_cannot_change_group_identity():
    s=load('r2','dev')[-1];a=s.scene();b=copy.deepcopy(a)
    b['objects'].reverse();b['zones'].reverse();b['label']['code']='alpha' if a['label']['code']=='beta' else 'beta';b['objects'][0]['color']='black'
    assert geometry(a)==geometry(b) and distance(a,b)==0


def test_aliases_or_disclosure_variants_cannot_cross_split():
    rows=load('r2');dev=rows[0]
    with pytest.raises(ValueError):audit_samples([dev,replace(dev,partition='test',sample_id='cross_split_clone')])


@pytest.mark.parametrize('template',['buffer_exchange','retrieve_restore','occlusion_inspection'])
def test_hidden_choices_cannot_change_initial_public_payload(template):
    rows=[s for s in load('r2','dev') if s.template_id==template and not s.initial_disclosed_slots]
    a=rows[0];b=next(s for s in rows if s.group_id==a.group_id and s.theta_star!=a.theta_star)
    assert a.u0==b.u0 and a.scene_seed==b.scene_seed
    with make_world(a) as wa,make_world(b) as wb:
        pa=serialize(payload(a.u0,wa.observation(),[]));pb=serialize(payload(b.u0,wb.observation(),[]))
        assert pa==pb and compact(pa)==compact(pb)
        assert 'theta_star' not in json.dumps(pa) and 'task_success' not in json.dumps(pa)


def test_old_tuned_layouts_are_not_test_groups():
    old={s['template_id']:s['physical_scene'] for s in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']}
    assert all(distance(s.scene(),old[s.template_id])>=MIN_GROUP_DISTANCE for s in load('r2','test'))


def test_new_schema_roundtrips_and_stays_distinct_from_legacy():
    from dataclasses import asdict
    for sample in load('r2'):
        assert Sample(**asdict(sample)).validate()==sample
        assert sample.dataset_version=='when2ask_three_task_v8' and sample.schema_version==8
        assert sample.group_id.endswith(sample.layout_family_id)
