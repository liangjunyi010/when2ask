"""Four paired Dev cases x four policies, isolated from all historical studies."""
import copy
import hashlib
import json
import random
import subprocess
import time
from datetime import datetime, timezone
from dataclasses import asdict

from .accounting import Audit, SessionLedger
from .api import DeepSeekClient, JevClient
from .config import ROOT, Config
from .grounded_dev_health import SchemaAwareSession
from .nine_task_data import Case, write, digest
from .nine_task_world import Adapter
from .study_evaluator import expected_targets
from .tabletop_dev_agents import components, PROFILES, SELECTED
from .tabletop_dev_public import facts_payload
from .user_simulator import PreferenceResolver
from .unified_dev_agent import VERSION, SYSTEM_PROMPT, UnifiedPolicy, prompt_hash

OUT = ROOT / 'result' / VERSION
DATA = ROOT / 'data' / VERSION
METHODS = ('llm_noask', 'llm_gate', 'jev_gate', 'llm_unified')
MAX_REQUESTS, MAX_EPISODES = 320, 16
LIMITS = dict(rounds=20, actions=12, slots=12, api_attempts=32)


def ledger():
    return SessionLedger(OUT/'session', MAX_REQUESTS, MAX_EPISODES, policy='phase3_dev')


class TimedAudit(Audit):
    def reserve(self, backend):
        row = super().reserve(backend)
        row['request_started_at_utc'] = datetime.now(timezone.utc).isoformat()
        self.flush()
        return row


def load():
    value = json.loads((DATA/'samples.json').read_text())
    cases = [Case(**c['sample']).validate() for c in value['cases']]
    if len(cases) != 4 or len({c.group_id for c in cases}) != 4 or any(c.partition != 'dev' for c in cases):
        raise ValueError('Exactly four independent existing Dev groups required')
    return cases


def prepare():
    DATA.mkdir(parents=True, exist_ok=False)
    source = ROOT/'data/tabletop_contract_dev_v1/samples.json'
    data = json.loads(source.read_text())
    data.update(study_version=VERSION, source_data=str(source.relative_to(ROOT)),
                source_data_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                policy='Same four previously developed Dev cases, not new held-out data. No historical episode contributes to current outcome tables.')
    write(DATA/'samples.json', data)
    return {'samples':len(load()), 'groups':4, 'partition':'dev'}


def oracle():
    dest = OUT/'oracle'
    dest.mkdir(parents=True, exist_ok=False)
    rows = []
    for s in load():
        a = Adapter(s)
        actions = []
        try:
            a.world.render().save(dest/(s.sample_id+'_initial.png'))
            targets = expected_targets(s, a.world)
            for role in (['block','cup'] if s.dag['order']=='block_first' else ['cup','block']):
                actions.append(a.execute(dict(kind='pick_place', object_id=s.theta_star[role+'_choice'],
                                              target_id=targets[role], relation='inside')))
            if s.template_id == 'pack_and_cover':
                actions.append(a.execute(dict(kind='cover', object_id=s.theta_star['lid_choice'], target_id='box')))
            score = a.score(0, actions, 'offline_oracle')
            a.world.render().save(dest/(s.sample_id+'_final.png'))
            write(dest/(s.sample_id+'.json'), dict(sample_id=s.sample_id, group_id=s.group_id,
                  partition='dev', evidence_kind='real_pybullet_oracle', api_attempts=0,
                  actions=actions, evaluation=score, execution_log=a.world.events))
            rows.append(dict(sample_id=s.sample_id, success=score['task_success']))
        finally:
            a.close()
    result = dict(successes=sum(r['success'] for r in rows), total=len(rows), rows=rows)
    write(dest/'summary.json', result)
    return result


def freeze():
    if (OUT/'manifest.json').exists():
        raise FileExistsError('Never overwrite an online Dev protocol')
    if json.loads((OUT/'oracle/summary.json').read_text())['successes'] != 4:
        raise ValueError('All four cases must pass physical oracle before online calls')
    # Rotate a shuffled method order across independently shuffled case blocks.
    # Every method occupies each execution position once. Serial episodes avoid
    # local concurrent physics/HTTP contention; no prewarming or selective reruns.
    rng = random.Random(42781122)
    cases = load(); rng.shuffle(cases)
    order = list(METHODS); rng.shuffle(order)
    jobs = [dict(sample_id=s.sample_id, method=order[(j+i)%4],
                 episode_id=s.sample_id+'__'+order[(j+i)%4])
            for i,s in enumerate(cases) for j in range(4)]
    sources = list((ROOT/'src/when2ask').glob('*.py')) + [ROOT/'script/unified_deepseek_dev.py']
    value = dict(study_version=VERSION, status='LOCKED_BEFORE_NEW_AUTHENTICATED_CALLS',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        data_sha256=hashlib.sha256((DATA/'samples.json').read_bytes()).hexdigest(),
        pricing_sha256=hashlib.sha256((OUT/'pricing.json').read_bytes()).hexdigest(),
        configuration=Config.load().public_config(), expected_returned_models=dict(deepseek='deepseek-flash',jev='jev-1.14.0'),
        profile=SELECTED, separate_prompt_hashes=PROFILES[SELECTED].hashes(), unified_prompt_sha256=prompt_hash(),
        global_limits=dict(authenticated_requests=MAX_REQUESTS, full_episodes=MAX_EPISODES),
        per_episode_limits=LIMITS, run_order_seed=42781122, jobs=jobs,
        method_order_policy='Randomized case blocks; rotated randomized four-method order, each position once; serial independent resets.',
        retry_policy='At most one retry per failed HTTP/schema call; attempts charged including format repair. Permanent/three consecutive API errors block backend. No whole-episode reruns.',
        planner_parameters=dict(max_tokens=500, temperature=0, thinking='disabled', response_format='json_object'),
        threshold=.5, gate_max_tokens=64, simulator='unchanged deterministic requested-slot GT resolver',
        scientific_scope='Architecture comparison on four developed Dev groups. Unified combines decision and generation; not a gate-only substitution or fresh held-out claim.',
        success_policy='Unchanged physical evaluator. Task success independent of termination reason, all scored failures retained.',
        cost_policy='Report all real attempts including retries/DONE; backend tokens separate. USD from actual cache/usage and published rates; missing usage stays unknown, not zero.',
        metrics=['physical_task_success','clarification_burden','agent_api_latency_s','episode_wall_time_s','per_backend_tokens','estimated_usd','api_attempts','schema_errors','physical_failures'])
    write(OUT/'manifest.json', value)
    (OUT/'unified_system_prompt.txt').write_text(SYSTEM_PROMPT)
    return value


def checked():
    plan = json.loads((OUT/'manifest.json').read_text())
    if Config.load().public_config() != plan['configuration']:
        raise ValueError('Online configuration drift')
    for p,h in plan['source_hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:
            raise ValueError('Source drift: '+p)
    for p,k in [(DATA/'samples.json','data_sha256'),(OUT/'pricing.json','pricing_sha256')]:
        if hashlib.sha256(p.read_bytes()).hexdigest()!=plan[k]:
            raise ValueError('Data/pricing drift')
    return plan


def next_output(method, state, deepseek, jev):
    """Exactly one logical invocation for unified; retries remain API attempts."""
    if method == 'llm_unified':
        result = UnifiedPolicy(deepseek).decide(state)
        return result.question, result.action, dict(kind=result.kind, separate_gate_called=False), result.to_dict()
    gate, planner = components(method, deepseek, jev, SELECTED, .5)
    decision = gate.decide(state) if gate else None
    meta = dict(decision=decision.decision if decision else 'CONTINUE',
                p_ask=decision.p_ask if decision else None, called=gate is not None)
    if meta['decision']=='ASK':
        return planner.generate_question(state), None, meta, None
    return None, planner.generate_action(state), meta, None


def episode(job, plan):
    s = next(s for s in load() if s.sample_id==job['sample_id'])
    dest = OUT/'episodes'/job['episode_id']; dest.mkdir(parents=True, exist_ok=False)
    ledger().start_episode(job['episode_id'])
    config = Config.load()
    audit = TimedAudit(job['episode_id'], config, path=dest/'api_attempts.jsonl', limit=LIMITS['api_attempts'])
    audit.session = SchemaAwareSession(ledger(), audit)
    deepseek, jev = DeepSeekClient(config,audit), JevClient(config,audit)
    start=time.monotonic();a=None;history=[];turns=[];actions=[];burden=0
    score=None;error=None;final=None;events=[];termination='round_limit'
    try:
        a=Adapter(s);a.world.render().save(dest/'scene.png')
        for i in range(LIMITS['rounds']):
            audit.round=i;state=a.state(history);public=facts_payload(state)
            turn=dict(round=i,public_payload=public,payload_sha256=digest(public));turns.append(turn)
            q,action,meta,wire=next_output(job['method'],state,deepseek,jev)
            turn['unified_decision' if wire is not None else 'gate']=meta
            if wire is not None:turn['model_output']=wire
            for r in audit.records:
                if r.get('returned_model') and r['returned_model']!=plan['expected_returned_models'][r['backend']]:
                    ledger().outcome(r['backend'],False,'returned_model_drift')
                    raise RuntimeError('returned_model_drift')
            if q is not None:
                resolver=PreferenceResolver(s.slots,s.theta_star)
                charge=len(set(resolver.resolve(q).values()))
                turn['proposed_question']=q.to_dict()
                if burden+charge>LIMITS['slots']:
                    termination='slot_request_limit';break
                before=a.world.snapshot();answer,_=resolver.answer(q);after=a.world.snapshot()
                if before!=after:raise RuntimeError('Physics changed during ASK')
                burden+=charge
                history.extend([dict(kind='ask',question=q.to_dict()),dict(kind='user_answer',response=answer)])
                turn.update(question=q.to_dict(),user_answer=answer,
                    ask_check=dict(before_step=before['simulation_step'],after_step=after['simulation_step'],state_unchanged=True,charged_slots=charge))
            else:
                turn['action']=action.to_dict()
                if action.kind=='DONE':
                    audit.records[-1]['completion_kind']='DONE';audit.flush();termination='done';break
                if len(actions)>=LIMITS['actions']:
                    termination='robot_action_limit';break
                result=a.execute(action.to_dict());actions.append(result)
                history.append(dict(kind='action',result=result));turn['physical_result']=copy.deepcopy(result)
    except Exception as exc:
        termination=type(exc).__name__;error=config.sanitize(str(exc))
    finally:
        if a:
            try:
                score=a.score(burden,actions,termination)
                a.world.render().save(dest/'final.png')
                final=a.state(history).observation;events=copy.deepcopy(a.world.events)
            finally:a.close()
        e=dict(**job,study_version=VERSION,partition='dev',group_id=s.group_id,template_id=s.template_id,
            evidence_kind='real_api_real_pybullet_dev_architecture_comparison',instruction=s.u0,
            turns=turns,actions=actions,public_history=history,evaluation=score,termination_reason=termination,error=error,
            cost=audit.summary(),wall_time_s=time.monotonic()-start,final_observation=final,
            execution_log=events,configuration=config.public_config())
        write(dest/'episode.json',config.sanitize(e));write(dest/'evaluation.json',score)
    result=dict(episode_id=job['episode_id'],success=score['task_success'] if score else None,
                burden=burden,actions=len(actions),termination=termination,error=error)
    print(json.dumps(result),flush=True)
    return result


def run(live=False):
    if not live:raise ValueError('Explicit --live required')
    plan=checked();(OUT/'episodes').mkdir(exist_ok=False)
    rows=[];skipped=[]
    for job in plan['jobs']:
        budget=ledger().snapshot();backends=budget.get('backends',{})
        if budget['attempts']>=MAX_REQUESTS or backends.get('deepseek',{}).get('blocked'):
            skipped.append(dict(**job,reason='session_budget_or_deepseek_blocked'));continue
        if job['method']=='jev_gate' and backends.get('jev',{}).get('blocked'):
            skipped.append(dict(**job,reason='jev_backend_blocked'));continue
        rows.append(episode(job,plan))
        write(OUT/'progress.json',dict(completed=rows,skipped=skipped,session=ledger().snapshot()))
    result=dict(completed=rows,skipped=skipped,session=ledger().snapshot())
    write(OUT/'run_summary.json',result)
    return result
