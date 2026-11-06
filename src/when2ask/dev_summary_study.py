"""Predeclared independent Dev selection, physical oracle, sealing and execution."""
import json
import random
import subprocess
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from .accounting import SessionLedger
from .config import Config, ROOT
from .console_samples import demo_sample
from .dev_public_summary import PROFILES, digest
from .dev_summary_agents import prompt_hashes, question_spec
from .dev_summary_runner import run_episode
from .diverse_world import DiverseEnvironment, DiverseSkills
from .study_data import StudySample, load_study, sha256, write_json
from .study_evaluator import evaluate_study, expected_targets
from .study_oracle import initial_penetrations

VERSION = 'dev_public_summary_v1'
PLAN = ROOT / 'configs' / (VERSION + '.json')
CASES = ROOT / 'data' / VERSION / 'cases.json'
OUTPUT = ROOT / 'outputs' / VERSION
SEED = 427806
SOURCES = ['src/when2ask/' + p for p in (
    'dev_public_summary.py', 'dev_summary_agents.py', 'dev_summary_runner.py', 'dev_summary_study.py', 'dev_summary_report.py',
    'study_agents.py', 'study_protocol.py', 'protocol.py', 'api.py', 'accounting.py', 'user_simulator.py',
    'environment.py', 'skills.py', 'diverse_world.py', 'study_evaluator.py', 'evaluator.py',
    'study_reporting.py', 'config.py', 'task.py', 'recording.py')]


def selected_cases():
    rng = random.Random(SEED)
    samples = load_study('dev')
    regression = demo_sample('pack_and_cover', 2)
    rows = [dict(case_id='regression_console_m2', selection='targeted observed console failure; not a representative random sample',
                 source_sample_id=regression.sample_id, sample=asdict(regression))]
    groups = {regression.group_id}
    # Coverage uses PUBLIC disclosure/order features, never recorded model scores.
    for missing, template in ((0, 'place_into_selected_containers'), (1, 'pack_and_cover'), (3, 'place_into_selected_containers')):
        candidates = [s for s in samples if s.template_id == template and s.group_id not in groups
                      and 3-len(s.initial_disclosed_slots) == missing
                      and (missing != 1 or set(s.initial_disclosed_slots) == {'cup_choice', 'block_choice'})]
        chosen = rng.choice(sorted(candidates, key=lambda s:s.sample_id))
        rows.append(dict(case_id=f'dev_m{missing}_{chosen.sample_id}',
            selection='fixed-seed draw among public coverage strata; m1 has known cup/block and unknown lid',
            source_sample_id=chosen.sample_id, sample=asdict(chosen)))
        groups.add(chosen.group_id)
    assert len(groups) == 4
    return rows


def oracle(case, sample):
    out = OUTPUT / 'oracle' / case
    signature = dict(sample=digest(asdict(sample)), scene=sha256(ROOT / sample.scene_spec_ref))
    if (out / 'episode.json').exists():
        result = json.loads((out / 'episode.json').read_text())
        if result['signature'] != signature:
            raise ValueError('Oracle data changed; do not overwrite prior evidence')
        return result
    out.mkdir(parents=True)
    with DiverseEnvironment(seed=sample.scene_seed, scene_spec=sample.scene()) as env:
        penetrations = initial_penetrations(env)
        env.save_scene(out / 'scene.png')
        skills, actions = DiverseSkills(env), []
        targets = expected_targets(sample, env)
        order = ['block', 'cup'] if sample.dag['order'] == 'block_first' else ['cup', 'block']
        for role in order:
            actions.append(skills.pick_place(sample.theta_star[role+'_choice'], targets[role]).to_dict())
        if sample.template_id == 'pack_and_cover':
            actions.append(skills.cover(sample.theta_star['lid_choice'], 'box').to_dict())
        result = dict(signature=signature, evidence_kind='offline_oracle_real_pybullet', api_attempts=0,
            initial_penetrations=penetrations, actions=actions, execution_log=env.events,
            evaluation=evaluate_study(env, sample, clarification_burden=0, actions=actions, termination='oracle_done'))
        env.save_scene(out / 'final.png')
    write_json(out / 'episode.json', result)
    return result


def prepare():
    if PLAN.exists():
        return json.loads(PLAN.read_text())
    cases = selected_cases()
    if CASES.exists() and json.loads(CASES.read_text()) != cases:
        raise ValueError('Existing independent case materialization differs')
    write_json(CASES, cases)
    results = []
    for case in cases:
        sample = StudySample(**case['sample']).validate()
        evidence = oracle(case['case_id'], sample)
        results.append(dict(case_id=case['case_id'], group_id=sample.group_id, template=sample.template_id,
            missing_preferences=3-len(sample.initial_disclosed_slots), success=evidence['evaluation']['task_success'],
            initial_penetrations=len(evidence['initial_penetrations'])))
    write_json(OUTPUT / 'oracle' / 'summary.json', results)
    if not all(r['success'] and not r['initial_penetrations'] for r in results):
        raise RuntimeError('Physical oracle failed. No model run authorized by this plan')
    jobs = [dict(case_id=c['case_id'], profile=p, run_id=c['case_id']+'__'+p,
                 record=c['case_id']=='regression_console_m2' and p in ('v3_original', 'compact_question'))
            for c in cases for p in PROFILES]
    random.Random(SEED+1).shuffle(jobs)
    plan = dict(experiment_id=VERSION, partition='dev', seed=SEED, threshold=0.5,
        purpose='Representation/question ablation, not replacement Test calibration or a general success estimate',
        case_materialization_sha256=sha256(CASES),
        profiles={p:dict(prompt_hashes=prompt_hashes(p), gate_question=question_spec(p)[0],
                        gate_criteria=question_spec(p)[1]) for p in PROFILES},
        method='jev_gate', oracle_summary=results, jobs=jobs,
        configured_models=dict(deepseek='deepseek-flash', jev='jev-latest'),
        expected_returned_models=dict(deepseek='deepseek-flash', jev='jev-1.14.0'),
        budgets=dict(max_episodes=12, max_authenticated_attempts=140, max_rounds=20,
                     max_robot_actions=12, max_slot_requests=12, max_episode_api_attempts=64),
        retry_policy=dict(max_retries=1, timeout_s=40, max_output_tokens=500, consecutive_errors_stop=3),
        decision_rule='ASK iff p_ask >= 0.5; no threshold sweep or mid-run prompt edits',
        primary_metrics=['early_asks', 'blocked_continues', 'complete_asks'],
        secondary_metrics=['task_success', 'clarification_burden', 'tokens_by_backend', 'api_latency'],
        interpretation='compact_state changes gate AND shared planner representation; compact_question vs compact_state isolates gate wording. No timing verdict/next action/private registry is supplied.',
        eligibility='A candidate is only promising if it adds no early/complete asks and reduces blocked continues without reducing per-case success; otherwise report mixed/no improvement. Four groups do not establish significance.',
        docs=['https://docs.typesafe.ai/primitives/noul'])
    write_json(PLAN, plan)
    return plan


def seal():
    plan = json.loads(PLAN.read_text())
    if sha256(CASES) != plan['case_materialization_sha256']:
        raise ValueError('Prepared cases changed')
    signature = dict(plan_sha256=sha256(PLAN), cases_sha256=sha256(CASES),
        source_sha256={p:sha256(ROOT / p) for p in SOURCES},
        scene_sha256={c['sample']['scene_spec_ref']:sha256(ROOT / c['sample']['scene_spec_ref']) for c in json.loads(CASES.read_text())})
    path = OUTPUT / 'execution_manifest.json'
    if path.exists():
        saved = json.loads(path.read_text())
        if saved['signature'] != signature:
            raise ValueError('Sealed sources/data differ; create a new experiment version')
        return saved
    manifest = dict(signature=signature, code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        sealed_at=datetime.now(timezone.utc).isoformat(), experiment_id=VERSION,
        model_configuration=replace(Config.load(),threshold=.5).public_config())
    write_json(path, manifest)
    return manifest


def run(live=False):
    if not live:
        raise ValueError('Paid diagnostics require explicit --live')
    manifest = seal()
    plan = json.loads(PLAN.read_text())
    config = replace(Config.load(), threshold=.5)
    if config.public_config() != manifest['model_configuration']:
        raise ValueError('Sealed API configuration changed')
    if not config.deepseek_key or not config.typesafe_key:
        raise ValueError('Both local provider credentials are required')
    if (config.deepseek_model != plan['configured_models']['deepseek'] or config.jev_model != plan['configured_models']['jev']
            or config.max_retries != 1 or config.timeout_s != 40 or config.max_tokens != 500):
        raise ValueError('Unexpected planner configuration')
    cases = {c['case_id']:StudySample(**c['sample']).validate() for c in json.loads(CASES.read_text())}
    session = SessionLedger(OUTPUT / 'inference', 140, 12, policy='phase3_dev')
    for job in plan['jobs']:
        path = OUTPUT / 'episodes' / job['run_id']
        if (path / 'episode.json').exists():
            continue
        if path.exists():
            raise ValueError('Partial episode must not be overwritten; report interrupted evidence')
        budget = session.snapshot()
        if budget['attempts'] >= budget['max_attempts'] or any(v.get('blocked') for v in budget['backends'].values()):
            print('STOP session budget/circuit', flush=True)
            break
        seal()  # Assert immutable inference sources before every new job.
        result = run_episode(cases[job['case_id']], job['case_id'], job['profile'], path,
            config=config, session=session, live=True, record=job['record'], expected_models=plan['expected_returned_models'])
        print(json.dumps(dict(run_id=job['run_id'], success=result['evaluation']['task_success'],
                             attempts=result['cost']['api_attempts'], termination=result['termination_reason'])), flush=True)
        write_json(OUTPUT / 'run_status.json', dict(budget=session.snapshot(), last_completed=job['run_id']))
    return session.snapshot()
