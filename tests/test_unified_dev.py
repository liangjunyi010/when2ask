"""Offline schema/control/accounting tests; fake outputs are never experiment data."""
import copy
import json
from pathlib import Path

import pytest

from when2ask.api import DeepSeekClient, SchemaError
from when2ask.config import Config, ROOT
from when2ask.task import PublicState
from when2ask.tabletop_dev_public import facts_payload
from when2ask.unified_dev_agent import UnifiedPolicy, parse, SYSTEM_PROMPT
from when2ask.unified_dev_study import next_output, run, TimedAudit
from when2ask.unified_dev_report import price_attempt, complete_sum


@pytest.fixture
def state():
    raw=json.loads((ROOT/'outputs/tabletop_contract_dev_v1/diagnostic_states.json').read_text())['states'][0]['state']
    return PublicState.build(raw['observation'],raw['history'],raw['instruction'])


def question(state):
    ids=facts_payload(state)['public_facts']['role_candidates']['block']
    return dict(type='select',text='Which block?',requests=[dict(role='block',candidate_ids=ids)])


class OfflineClient:
    def __init__(self, outputs, calls=None):self.outputs=list(outputs);self.calls=[] if calls is None else calls
    def json(self,prompt,public,*,stage,validator,max_tokens):
        self.calls.append(dict(stage=stage,public=public,prompt=prompt,max_tokens=max_tokens))
        return validator(self.outputs.pop(0))
    def noul(self,public,prompt,criteria):
        self.calls.append(dict(stage='gate',public=public,prompt=prompt));return self.outputs.pop(0)


@pytest.mark.parametrize('kind',['ASK','pick_place','DONE'])
def test_unified_one_call_including_question_generation(state,kind):
    obj=facts_payload(state)['public_facts']['confirmed_choices']['cup']
    wire=({'kind':'ASK','question':question(state)} if kind=='ASK' else {'kind':'DONE'} if kind=='DONE'
          else dict(kind='pick_place',object_id=obj,target_id='box',relation='inside'))
    c=OfflineClient([wire]);q,a,meta,out=next_output('llm_unified',state,c,None)
    assert out==wire and len(c.calls)==1 and c.calls[0]['stage']=='unified'
    assert meta['separate_gate_called'] is False
    assert (q is not None)==(kind=='ASK')
    assert (a is not None)==(kind!='ASK')


@pytest.mark.parametrize('wire',[None,[],{'decision':'CONTINUE'},{'kind':'ASK'},
    {'kind':'DONE','question':{}},{'kind':'ASK','question':{},'action':{'kind':'DONE'}}])
def test_unified_rejects_incomplete_or_mixed_outputs(state,wire):
    with pytest.raises(SchemaError):parse(wire,state)


def test_one_call_does_not_force_correct_completion_or_block_wrong_actions(state):
    assert parse({'kind':'DONE'},state).kind=='DONE'  # Physics evaluator decides success.
    cup=facts_payload(state)['public_facts']['confirmed_choices']['cup']
    wrong_order=dict(kind='pick_place',object_id=cup,target_id='box',relation='inside')
    assert parse(wrong_order,state).to_dict()==wrong_order  # Public block-first rule may be violated by model.


def test_methods_receive_identical_initial_public_payload(state):
    payloads=[]
    for method in ('llm_noask','llm_gate','jev_gate','llm_unified'):
        c=OfflineClient(([{'decision':'CONTINUE'}] if method=='llm_gate' else [])+[{'kind':'DONE'}])
        j=OfflineClient([.2],calls=c.calls)
        next_output(method,state,c,j)
        payloads.extend(r['public'] for r in c.calls)
        stages=[r['stage'] for r in c.calls]
        assert stages==({'llm_noask':['action'],'llm_gate':['gate','action'],
                         'jev_gate':['gate','action'],'llm_unified':['unified']}[method])
    assert all(p==facts_payload(state) for p in payloads)


def test_unified_sees_no_hidden_or_unexpected_observation_fields(state):
    obs=copy.deepcopy(state.observation);obs['theta_star']={'block_choice':'private_answer'}
    changed=PublicState.build(obs,state.history,state.instruction)
    c=OfflineClient([{'kind':'DONE'}]);UnifiedPolicy(c).decide(changed)
    assert c.calls[0]['public']==facts_payload(state)
    assert 'private_answer' not in json.dumps(c.calls)


def test_prompt_scopes_conditional_rules_and_uses_same_timing_contract():
    assert 'CONDITIONAL ACTION RULES' in SYSTEM_PROMPT and 'CONDITIONAL QUESTION RULES' in SYSTEM_PROMPT
    assert 'Return only ASK or CONTINUE; the action planner' not in SYSTEM_PROMPT
    assert 'Ask only when missing user preferences prevent ALL further useful supported task progress.' in SYSTEM_PROMPT
    assert 'Preserve achieved progress.' in SYSTEM_PROMPT


def test_no_implicit_live_run():
    with pytest.raises(ValueError,match='--live'):run()


@pytest.fixture
def prices():
    return {'deepseek':{'off_peak':{'cache_hit_per_million':.003,'cache_miss_per_million':.15,'output_per_million':.6},
                        'peak':{'cache_hit_per_million':.006,'cache_miss_per_million':.3,'output_per_million':1.2}},
            'jev':{'input_per_million':.042}}


def test_cache_aware_cost_and_separate_backend_pricing(prices):
    r=dict(backend='deepseek',input_tokens=1000,output_tokens=100,request_started_at_utc='2026-11-12T10:30:00+00:00',
        response={'usage':{'prompt_cache_hit_tokens':800,'prompt_cache_miss_tokens':200}})
    p=price_attempt(r,prices)
    assert p['estimated_usd']==pytest.approx((800*.003+200*.15+100*.6)/1e6)
    assert p['tariff']=='off_peak'
    assert price_attempt({**r,'request_started_at_utc':'2026-11-12T08:30:00+00:00'},prices)['estimated_usd']==pytest.approx(p['estimated_usd']*2)
    assert price_attempt(dict(backend='jev',input_tokens=1000,output_tokens=None),prices)['estimated_usd']==pytest.approx(.000042)


def test_unknown_cost_is_not_free_and_missing_rows_do_not_sum_to_zero(prices):
    assert price_attempt(dict(backend='deepseek',input_tokens=1000,output_tokens=100,
        request_started_at_utc='2026-11-12T10:30:00+00:00'),prices)['estimated_usd'] is None
    assert price_attempt(dict(backend='jev',input_tokens=None),prices)['estimated_usd'] is None
    assert complete_sum([1,None]) is None and complete_sum([]) is None


def response(content):
    return json.dumps(dict(model='deepseek-flash',choices=[{'message':{'content':content}}],
        usage=dict(prompt_tokens=200,completion_tokens=10,prompt_cache_hit_tokens=100,prompt_cache_miss_tokens=100)))


@pytest.mark.parametrize('failure',['malformed','timeout'])
def test_real_adapter_repairs_once_and_charges_both_attempts_offline(state,tmp_path,failure):
    # Fake transport only: no authenticated network calls.
    requests=[]
    def transport(url,headers,payload,timeout):
        requests.append(payload)
        if len(requests)==1:
            if failure=='timeout':raise TimeoutError('offline timeout')
            return 200,response('{not JSON')
        return 200,response('{"kind":"DONE"}')
    cfg=Config(deepseek_key='offline-unit-test')
    audit=TimedAudit('offline',cfg,path=tmp_path/'attempts.jsonl',limit=2)
    client=DeepSeekClient(cfg,audit,transport=transport,sleep=lambda _:None)
    assert UnifiedPolicy(client).decide(state).kind=='DONE'
    assert len(audit.records)==2 and audit.summary()['retries']==1
    assert all(r['stage']=='unified' and r['request_started_at_utc'] for r in audit.records)
    assert audit.records[0]['status']==('schema_error' if failure=='malformed' else 'api_error')
    assert audit.records[0]['input_tokens']==(200 if failure=='malformed' else None)
