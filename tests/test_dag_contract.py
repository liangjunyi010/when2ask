import copy
import json
from types import SimpleNamespace

import pytest

from when2ask.config import ROOT
from when2ask.dag_benchmark import candidate, generate, load_dataset, read_json, statistics
from when2ask.dag_evaluation import run_episode, summarize
from when2ask.dag_world import GraphWorld, validate_action
from when2ask.graph_evaluator import GraphEvaluator
from when2ask.model_client import Client, RequestLimit, ModelOutputError, estimated_cost, token_usage
from when2ask.task_graph import placement_offsets, resolve
from when2ask.user_simulator import LlmUser
from when2ask.submission import main


@pytest.fixture
def config():
    return read_json(ROOT/'config/benchmark.json')


def test_design_counts_graphs_and_disclosure(config):
    samples = [candidate(config,t,i) for t,f in config['families'].items() for i in range(f['count'])]
    actual = statistics(samples)
    assert actual['environments']==900 and actual['fully_specified']==266
    assert len({s.sample_id for s in samples})==900
    assert len(config['jobs'])*len(samples)==4500
    for row in actual['families']:
        expected = config['families'][row['template']]
        assert row['nodes']==expected['nodes'] and row['uncertain']==expected['uncertain']
        assert row['fully_specified']==expected['fully_specified']
    supported = {'place','cover','quota','inventory','search','detect','approach','inspect','report','return_home'}
    for s in samples:
        s.validate()
        assert all(n['operation'] in supported for n in s.dag['nodes'])
        assert s.slots and all(v['kind'] in ('preference','world_fact') for v in s.slots.values())
        fixtures = {r['id']:r for r in s.physical_scene.get('containers',[])}
        for target,fixture in fixtures.items():
            stored = [r for r in s.physical_scene['objects'] if s.dag['resources'][r['id']].get('initial_target')==target and r['category']!='lid']
            assert len(stored)<=len(placement_offsets(fixture['half_xy'],.032))
    packing = next(s for s in samples if s.template_id=='pack_and_cover')
    assert sum(b=='cover' for a,b in packing.dag['edges'])>1


def test_hidden_intent_not_in_public_task(config):
    sample = next(candidate(config,'pack_and_cover',i) for i in range(105)
                  if not candidate(config,'pack_and_cover',i).fully_specified)
    other = copy.deepcopy(sample)
    for slot in set(sample.slots)-set(sample.initial_disclosed_slots):
        other.theta_star[slot] = next(v for v in other.slots[slot]['candidate_ids'] if v!=sample.theta_star[slot])
    assert sample.public_task()==other.public_task()
    assert sample.theta_star!=other.theta_star


def response(value, model='test-model', usage=True):
    body = dict(model=model,choices=[dict(message=dict(content=json.dumps(value)))])
    if usage:
        body['usage'] = dict(prompt_tokens=20,completion_tokens=5)
    return 200,json.dumps(body)


def fake_client(transport, **kwargs):
    profiles = {name:dict(model='test-model',key='private-test-token',url='https://example.invalid',protocol='chat',options={})
                for name in ('deepseek','user')}
    prices = {name:dict(input_per_million=1.,cached_input_per_million=.1,output_per_million=2.) for name in profiles}
    return Client(profiles,prices,transport=transport,**kwargs)


class MeasuredBackend:
    def __init__(self,sample):
        self.sample = sample
        self.world = SimpleNamespace(step_count=17)
        self.calls = []
        self.state = dict(containers={'box':[]},zones={},coverage={},positions={},categories={},safe=True)

    def observation(self):
        objects = [k for k,r in self.sample.dag['resources'].items() if r['category'] in ('cup','block')]
        lids = [k for k,r in self.sample.dag['resources'].items() if r['category']=='lid']
        return dict(affordances=dict(move={k:['box'] for k in objects},cover={k:['box'] for k in lids},inspect_inventory=True))

    def measurements(self):
        return copy.deepcopy(self.state)

    def execute(self,action):
        self.calls.append(action)
        self.world.step_count += 1
        if action['kind']=='move':
            self.state['containers']['box'].append(action['object_id'])
        if action['kind']=='cover':
            self.state['coverage'][action['object_id']] = True
        return dict(success=True,skill=action['kind'])

    def close(self):
        pass


def test_one_skill_per_action_and_no_graph_or_private_progress(config):
    sample = candidate(config,'pack_and_cover',0)
    world = GraphWorld(sample,adapter_factory=MeasuredBackend)
    public = world.public()
    assert set(public)=={'instruction','observation','history'}
    assert all(k not in json.dumps(public) for k in ('theta_star','sample_id','completed_nodes','prerequisites','"dag"'))
    node = resolve(sample.dag['nodes'],sample.theta_star)[0]
    action = dict(kind='move',object_id=node['goal']['object_id'],target_id='box')
    world.execute(action)
    assert world.adapter.calls==[action]
    assert world.history[0]['action']==action
    assert not world.score()['task_success']
    reset = world.reset()
    assert reset['history']==[] and world.adapter.calls==[]


def test_wrong_choice_is_executable_and_order_is_private(config):
    sample = candidate(config,'pack_and_cover',0)
    world = GraphWorld(sample,adapter_factory=MeasuredBackend)
    wrong = next(k for k in sample.slots['lid_choice']['candidate_ids'] if k!=sample.theta_star['lid_choice'])
    action = dict(kind='cover',object_id=wrong,target_id='box')
    assert validate_action(action,world.adapter.observation())==action
    assert world.execute(action)['success']
    assert world.evaluator.witnesses=={}
    assert not world.score()['task_success']


def test_evaluator_requires_physical_goal_and_correct_order(config):
    sample = candidate(config,'pack_and_cover',0)
    nodes = resolve(sample.dag['nodes'],sample.theta_star)
    state = dict(containers={'box':[]},coverage={},safe=True)
    evaluator = GraphEvaluator(sample,state)
    lid = nodes[-1]['goal']['object_id']
    state['coverage'][lid] = True
    evaluator.observe(dict(kind='cover',object_id=lid,target_id='box'),dict(success=True),state)
    assert 'cover' not in evaluator.witnesses
    for node in nodes[:-1]:
        key = node['goal']['object_id']
        action = dict(kind='move',object_id=key,target_id='box')
        evaluator.observe(action,dict(success=True),state)
        assert node['id'] not in evaluator.witnesses
        state['containers']['box'].append(key)
        evaluator.observe(action,dict(success=True),state)
    assert not evaluator.score(state)['task_success']
    evaluator.observe(dict(kind='cover',object_id=lid,target_id='box'),dict(success=True),state)
    assert evaluator.score(state)['task_success']
    state['containers']['box'].pop()
    assert not evaluator.score(state)['task_success']


def test_user_is_llm_call_and_scoped(config):
    sample = candidate(config,'pack_and_cover',0)
    slot = next(iter(sample.slots))
    seen = []
    def transport(url,headers,payload,timeout):
        seen.append(json.loads(payload['messages'][1]['content']))
        return response({'choices':{slot:sample.theta_star[slot]}})
    client = fake_client(transport)
    answer = LlmUser(client,sample).answer(dict(text='Which item?',slots=[slot]))
    assert answer=={'choices':{slot:sample.theta_star[slot]}}
    assert seen[0]['complete_intent']==sample.theta_star
    assert client.totals()['requests']==0
    assert client.totals('user_simulator')['requests']==1


def test_user_does_not_fall_back_to_scripted_reply(config):
    sample = candidate(config,'pack_and_cover',0)
    client = fake_client(lambda *args:response({'choices':sample.theta_star}))
    with pytest.raises(ModelOutputError,match='requested slots'):
        LlmUser(client,sample).answer(dict(text='Which item?',slots=[next(iter(sample.slots))]))
    assert len(client.records)==2 and all(r['status']=='error' for r in client.records)


def test_rl_questions_preserve_physics_and_include_history(config):
    sample = candidate(config,'pack_and_cover',0)
    slot = next(iter(sample.slots))
    client = fake_client(lambda *args:response({'choices':{slot:sample.theta_star[slot]}}))
    world = GraphWorld(sample,adapter_factory=MeasuredBackend,user=LlmUser(client,sample))
    before = world.adapter.measurements()
    obs,reward,done,info = world.step(dict(kind='ASK',text='Which item?',slots=[slot]))
    assert world.world.step_count==17 and before==world.adapter.measurements()
    assert reward==0 and not done and info['answer']['choices']=={slot:sample.theta_star[slot]}
    assert len(obs['history'])==1 and 'complete_intent' not in json.dumps(obs)
    assert world.step({'kind':'DONE'})[2]
    with pytest.raises(RuntimeError,match='Reset'):
        world.step({'kind':'DONE'})


def test_episode_call_sequence_and_accounting(config):
    sample = candidate(config,'pack_and_cover',0)
    slot = next(iter(sample.slots))
    replies = iter([{'decision':'ASK'},{'text':'Which item?','slots':[slot]},
                    {'choices':{slot:sample.theta_star[slot]}},{'decision':'CONTINUE'},{'kind':'DONE'}])
    client = fake_client(lambda *args:response(next(replies)))
    factory = lambda sample,action_limit:GraphWorld(sample,action_limit,MeasuredBackend)
    row = run_episode(sample,dict(name='test',model='deepseek',method='llm_gate'),config,client,factory)
    assert row['status']=='complete' and row['ask_count']==1
    assert row['agent']['requests']==4 and row['user_simulator']['requests']==1
    assert [r['stage'] for r in client.records]==['gate','question','user_answer','gate','action']
    assert 'complete_intent' not in json.dumps(row['turns'])
    assert row['turns'][-1]['public_state']['history'][0]['response']['choices']=={slot:sample.theta_star[slot]}


def test_noask_skips_gate_and_invalid_action_counts_as_failure(config):
    sample = candidate(config,'pack_and_cover',0)
    client = fake_client(lambda *args:response({'kind':'EXECUTE','node_id':'cover'}))
    factory = lambda sample,action_limit:GraphWorld(sample,action_limit,MeasuredBackend)
    row = run_episode(sample,dict(name='test',model='deepseek',method='noask'),config,client,factory)
    assert row['status']=='complete' and row['task_success'] is False
    assert row['termination']=='invalid_model_output' and row['ask_count']==0
    assert all(r['stage']=='action' for r in client.records)


def test_unknown_usage_and_cached_token_cost():
    assert token_usage({}) is None and estimated_cost(None,{}) is None
    usage = token_usage({'usage':{'prompt_tokens':100,'completion_tokens':10,'prompt_cache_hit_tokens':40}})
    assert estimated_cost(usage,dict(input_per_million=2,cached_input_per_million=.5,output_per_million=4))==pytest.approx(.00018)


def test_metrics_denominators_cost_scope_and_incomplete_runs():
    rows = [dict(sample_id=str(i),status='complete',task_success=i==0,method='llm_gate',fully_specified=i<2,
                 ask_count=5 if i==1 else 0,agent=dict(api_time_s=i+1,estimated_usd=.01),
                 user_simulator=dict(api_time_s=20,estimated_usd=.02)) for i in range(3)]
    summary = summarize(rows,['0','1','2'])
    assert summary['success_pct']==pytest.approx(100/3)
    assert summary['api_time_s']==2 and summary['unnecessary_ask_pct']==50
    assert summary['estimated_usd']==.01 and summary['total_estimated_usd']==pytest.approx(.03)
    assert summarize(rows,['0','1','2'],'all')['estimated_usd']==pytest.approx(.03)
    rows[0]['status']='incomplete'
    with pytest.raises(ValueError,match='Incomplete'):
        summarize(rows,['0','1','2'])


def test_live_flag_required_before_output(tmp_path):
    out = tmp_path/'run'
    with pytest.raises(SystemExit):
        main(['run','--dataset','missing','--output',str(out),'--pricing','missing'])
    assert not out.exists()


def test_request_retry_time_and_credential_redaction():
    sequence = iter([(429,json.dumps({'error':'rate limited'})),response({'decision':'CONTINUE'})])
    client = fake_client(lambda *args:next(sequence))
    assert client.request('deepseek','gate','Decide.',{},lambda x:x)=={'decision':'CONTINUE'}
    assert len(client.records)==2 and client.totals()['estimated_usd'] is None
    client = fake_client(lambda *args:(401,json.dumps({'error':'private-test-token'})))
    with pytest.raises(RuntimeError,match='401'):
        client.request('deepseek','gate','Decide.',{},lambda x:x)
    assert len(client.records)==1 and 'private-test-token' not in json.dumps(client.records)


def test_separate_request_limits_and_configurable_payload():
    seen = []
    def transport(url,headers,payload,timeout):
        seen.append((payload,timeout))
        return response({})
    client = fake_client(transport,limit=1,user_limit=2,max_output_tokens=123,timeout_s=17,retries=0)
    client.request('deepseek','action','Act.',{},lambda x:x)
    client.request('user','user_answer','Answer.',{},lambda x:x,actor='user_simulator')
    client.request('user','user_answer','Answer.',{},lambda x:x,actor='user_simulator')
    with pytest.raises(RequestLimit):
        client.request('deepseek','action','Act.',{},lambda x:x)
    assert client.totals()['requests']==1 and client.totals('user_simulator')['requests']==2
    assert all(payload['max_tokens']==123 and timeout==17 for payload,timeout in seen)


def test_typed_noul_probability_is_not_text():
    client = fake_client(lambda *args:(200,json.dumps(dict(model='test-model',answers={'needs_clarification':{'type':'noul','noul':.5}}))))
    client.profiles['jev'] = dict(client.profiles['deepseek'],protocol='noul')
    assert client.request('jev','gate','Decide.',{},lambda x:x)==.5
    assert client.records[0]['request']['questions']['needs_clarification']['type']=='noul'
    client.transport = lambda *args:(200,json.dumps(dict(model='test-model',answers={'needs_clarification':{'type':'noul','noul':True}})))
    with pytest.raises(ModelOutputError):
        client.request('jev','gate','Decide.',{},lambda x:x)


def small_config(config,tmp_path):
    small = copy.deepcopy(config)
    small['families'] = {'pack_and_cover':dict(count=1,fully_specified=1,nodes=[6,6],uncertain=[2,2])}
    path = tmp_path/'config.json'
    path.write_text(json.dumps(small))
    return path


def test_unvalidated_data_is_ineligible_and_hashes_are_checked(config,tmp_path):
    out = tmp_path/'dataset'
    generate(small_config(config,tmp_path),out)
    manifest,rows = load_dataset(out)
    assert manifest['validation_status']=='not_run' and len(rows)==1
    with pytest.raises(ValueError,match='oracle'):
        load_dataset(out,require_oracle=True)
    with (out/'samples.jsonl').open('a') as stream:
        stream.write('\n')
    with pytest.raises(ValueError,match='checksum'):
        load_dataset(out)


def test_oracle_filter_retains_only_passed_candidate(config,tmp_path):
    seen = []
    def fixture(sample):
        seen.append(sample)
        return dict(task_success=len(seen)==2,evidence_kind='unit_test_fixture')
    out = tmp_path/'dataset'
    generate(small_config(config,tmp_path),out,validate_physics=True,oracle=fixture)
    manifest,rows = load_dataset(out,require_oracle=True)
    assert len(seen)==2 and rows[0].scene_seed==seen[1].scene_seed
    assert manifest['statistics']['environments']==1 and rows[0].fully_specified


@pytest.mark.parametrize('family', ['inventory_restock','buffer_exchange','retrieve_restore','occlusion_inspection','find_and_approach','patrol_return','category_sorting','place_into_selected_containers'])
def test_all_family_predicates_reject_wrong_final_state(config,family):
    sample = candidate(config,family,0)
    evaluator = GraphEvaluator(sample,dict(positions={}))
    nodes = evaluator.nodes
    state = dict(containers={},zones={},coverage={},categories={},positions={},safe=True,visited=[],
                 detected=None,inspections=[],reports=[],stopped=True,at_home=False,distance_to_target=10.)
    for node in nodes:
        g,op = node['goal'],node['operation']
        if op=='place':
            state['zones'].setdefault(g['target_id'],[]).append(g['object_id'])
            action = dict(kind='move',object_id=g['object_id'],target_id=g['target_id'])
        elif op=='cover':
            state['coverage'][g['object_id']]=True
            action = dict(kind='cover',object_id=g['object_id'],target_id=g['target_id'])
        elif op=='quota':
            keys = ['unit_'+g['target_id']+str(i) for i in range(int(g['count']))]
            state['containers'][g['target_id']]=keys
            state['categories'].update({k:g['category'] for k in keys})
            action = dict(kind='move',object_id=keys[-1],target_id=g['target_id'])
        elif op=='search':
            state['visited'].append(g['location_id'])
            action = dict(kind='inspect_station' if family=='patrol_return' else 'search',location_id=g['location_id'])
        elif op=='detect':
            state['detected'] = dict(location_id=sample.theta_star['target_location'])
            action = dict(kind='search',location_id=sample.theta_star['target_location'])
        elif op=='approach':
            state['distance_to_target']=1.
            action = dict(kind='approach',location_id=g['location_id'])
        elif op=='inspect':
            state['inspections'].append(dict(code=sample.theta_star['inspection_code'],camera={'visible':True}))
            action = dict(kind='inspect',target_id='label_fixture')
        elif op=='report':
            state['reports'].append(dict(code=g['code']))
            action = dict(kind='report',code=g['code'])
        else:
            action = dict(kind='inspect_inventory' if op=='inventory' else 'return_home')
            if op=='return_home':
                state['at_home']=True
        evaluator.observe(action,dict(success=True),state)
    assert evaluator.score(state)['task_success']
    state['safe']=False
    assert not evaluator.score(state)['task_success']


def test_gate_uses_exactly_one_noul_question():
    client = fake_client(lambda *args:(200,json.dumps(dict(model='test-model',answers={'needs_clarification':{'type':'noul','noul':.2}}))))
    client.profiles['jev'] = dict(client.profiles['deepseek'],protocol='noul')
    client.request('jev','gate','Decide.',dict(instruction='Task',observation={},history=[]),lambda x:x)
    payload = client.records[0]['request']
    assert set(payload)=={'model','state','questions'}
    assert len(payload['questions'])==1


def test_noask_metric_is_not_zero_percent():
    rows=[dict(sample_id='a',status='complete',task_success=False,method='noask',fully_specified=True,
               ask_count=0,agent=dict(api_time_s=1.,estimated_usd=.01),user_simulator=dict(api_time_s=0.,estimated_usd=0.))]
    result=summarize(rows,['a'])
    assert result['unnecessary_ask_pct'] is None and result['unnecessary_ask_cases'] is None
