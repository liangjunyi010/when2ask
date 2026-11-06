"""Prepare/check a bounded navigation Dev pilot, then derive reports from raw logs."""
import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from when2ask.config import Config
from when2ask.navigation_agents import VERSION,prompt_hashes


def sources():
    files=list((ROOT/'src/when2ask').glob('navigation_*.py'))
    files += [ROOT/f'src/when2ask/{s}' for s in ('console_agent.py','console_worker.py','console_state.py','console_samples.py')]
    files += [ROOT/'data/navigation_dev_v1/scenarios.json']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def prepare(out):
    out.mkdir(parents=True,exist_ok=True)
    if (out/'plan.json').exists():raise ValueError('Plan already exists; no overwriting preregistration')
    cases=['case_a','case_b','case_c'];random.Random(20261106).shuffle(cases)
    plan=dict(version=VERSION,created_utc=datetime.now(timezone.utc).isoformat(),partition='navigation_dev_only',
        layout_groups=1,placement_cases=3,scenario_order=cases,unknown_location_facts=1,
        methods=['llm_noask','llm_gate','jev_gate'],method_scheduling='Three independent workers launched together for each case; fixed method order, cases seeded shuffle',
        max_new_episodes=9,max_authenticated_requests=120,comparison_answer_mode='auto',auto_answer_delay_s=3,
        models=Config.load().public_config(),prompt_hashes=prompt_hashes(),source_sha256=sources(),
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        planner_token_limits=dict(action=128,question=300,gate=64),
        episode_limits=dict(rounds=20,robot_actions=8,slot_requests=12,api_attempts=64,distance_m=36),
        retry_policy='One retry; all attempts charged; backend stops after three consecutive errors or a permanent API error',
        timing='Wheel-driven physics paced at 1x for every method; model and user waiting never step physics',
        metrics=['physical_success','slot_burden','distance_travelled_m','inspected_stations','API_latency_ms','backend_input_output_tokens','ask_timing'],
        selection='All three declared placements, one per room. No selection after observing model outputs.',
        interpretation='Engineering pilot on ONE shared floorplan, not three independent map groups; no significance or Test-set claim',
        no_prompt_tuning_during_run=True,no_model_discovery_calls=True)
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return plan


def check(out):
    plan=json.loads((out/'plan.json').read_text())
    assert plan['source_sha256']==sources(),'Source changed after pilot plan'
    assert plan['prompt_hashes']==prompt_hashes(),'Prompt changed after pilot plan'
    assert plan['models']==Config.load().public_config(),'Model configuration changed'
    assert plan['max_new_episodes']==9 and plan['max_authenticated_requests']==120
    return plan


def report(out):
    plan=check(out);rows=[];attempts=[]
    for path in sorted((out/'episodes').glob('*/episode.json')):
        ep=json.loads(path.read_text());evaluation=ep['evaluation'];cost=ep['cost']
        api=[json.loads(s) for s in (path.parent/'api_attempts.jsonl').read_text().splitlines() if s]
        attempts.extend(api)
        asks=[t for t in ep['turns'] if 'question' in t]
        rows.append(dict(sample=ep['source_sample_id'],episode_id=ep['episode_id'],method=ep['method'],
            success=evaluation['task_success'] if evaluation else None,burden=evaluation['clarification_burden'] if evaluation else None,
            distance_m=evaluation['details']['distance_travelled_m'] if evaluation else None,
            inspected=len(evaluation['details']['checked_locations']) if evaluation else None,
            actions=len(ep['actions']),ask_turns=len(asks),first_ask_round=asks[0]['round'] if asks else None,
            first_ask_after_inspections=len(asks[0]['public_payload']['observation']['checked_locations']) if asks else None,
            api_attempts=cost['api_attempts'],api_latency_ms=cost['api_latency_ms'],
            deepseek_attempts=cost['deepseek']['attempts'],jev_attempts=cost['jev']['attempts'],
            **{f'{b}_{k}':cost[b][k] for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')},
            returned_models=' | '.join(sorted({a['returned_model'] for a in api if a.get('returned_model')})),
            ask_physics_unchanged=all(t['ask_check']['state_unchanged'] for t in asks) if asks else None,
            termination=ep['termination_reason'],error=ep['error']))
    aggregate=[]
    for method in plan['methods']:
        selected=[r for r in rows if r['method']==method]
        if not selected:continue
        def total(key):
            values=[r[key] for r in selected];return sum(values) if all(v is not None for v in values) else None
        aggregate.append(dict(method=method,episodes=len(selected),successes=sum(r['success'] is True for r in selected),
            burden_total=total('burden'),mean_burden=total('burden')/len(selected) if total('burden') is not None else None,
            distance_m_total=total('distance_m'),api_latency_ms_total=total('api_latency_ms'),
            **{f'{b}_{k}':total(f'{b}_{k}') for b in ('deepseek','jev') for k in ('input_tokens','output_tokens')},
            jev_attempts=total('jev_attempts'),deepseek_attempts=total('deepseek_attempts'),
            api_attempts=total('api_attempts')))
    summary=dict(plan_sha256=hashlib.sha256((out/'plan.json').read_bytes()).hexdigest(),layout_groups=1,
        placement_cases=3,episodes=len(rows),authenticated_requests=len(attempts),
        returned_models=sorted({a['returned_model'] for a in attempts if a.get('returned_model')}),
        schema_errors=sum(a['status']=='schema_error' for a in attempts),api_errors=sum(a['status']=='api_error' for a in attempts),
        live_ask_turns=sum(r['ask_turns'] for r in rows),
        aggregate=aggregate,rows=rows,note=plan['interpretation'])
    assert len(rows)<=9 and len(attempts)<=120
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for filename,table in [('episodes.csv',rows),('summary.csv',aggregate)]:
        if table:
            with (out/filename).open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    def f(value):return 'unknown' if value is None else f'{value:.2f}' if isinstance(value,float) else str(value)
    header='| Method | Success | Mean burden | Total travel (m) | API latency total (s) | DeepSeek in/out | Jev in/out |\n|---|---:|---:|---:|---:|---:|---:|\n'
    lines=[]
    for r in aggregate:
        jev_usage=f"{r['jev_input_tokens']}/{r['jev_output_tokens']}" if r['jev_attempts'] else '— (not called)'
        lines.append(f"| {r['method']} | {r['successes']}/{r['episodes']} | {f(r['mean_burden'])} | {f(r['distance_m_total'])} | {f(r['api_latency_ms_total']/1000) if r['api_latency_ms_total'] is not None else 'unknown'} | {r['deepseek_input_tokens']}/{r['deepseek_output_tokens']} | {jev_usage} |")
    text='# Navigation Dev v1 — actual API + PyBullet pilot\n\n'+plan['interpretation']+'.\n\n'+header+'\n'.join(lines)+'\n\n'
    text+=f"Authenticated attempts: {len(attempts)}/120; episodes: {len(rows)}/9. No paid Test calls. All metrics above are derived from episode JSON and API audit records. Backend tokens are kept separate.\n\n"
    text+='The target is a fixed world fact. Search uses known map routes and real wheel motors; detection uses local geometric range/FOV/ray line of sight, not learned vision. User hints do not move the object. Success means found and approached, without pickup or delivery. Each automatic reply incurs one slot and a declared 3s delay.\n\n'
    if rows and not summary['live_ask_turns']:
        text+='**Observed limitation:** Neither learned gate asked in these episodes. Both continued autonomous search until detection. Consequently this pilot demonstrates integration and search feasibility, not a clarification-timing advantage; the gate methods incurred extra inference cost without shortening travel. Actual ASK freezing and human/automatic replies were verified separately with explicitly scripted policies and real physics; they are not live-model ASK evidence.\n\n'
    text+='## Paired traces and timing\n\n'
    for r in rows:
        text+=f"- [{r['sample']} / {r['method']}](episodes/{r['episode_id']}/episode.json): success={r['success']}; burden={r['burden']}; distance={f(r['distance_m'])}m; first ASK round={r['first_ask_round']}, after {r['first_ask_after_inspections']} inspections; termination={r['termination']}; error={r['error']}.\n"
    text+='\nThese placements share one layout group, so no independent-group confidence interval or significance comparison is reported. This pilot evaluates task and UI integration; it does not establish an optimal asking policy. Frozen tabletop prompts, datasets and historical experiments are unchanged.\n'
    (out/'README.md').write_text(text)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=['prepare','check','report']);p.add_argument('--output-dir',default='outputs/navigation_dev_v1/live_v1')
    args=p.parse_args();value=globals()[args.operation](Path(args.output_dir));print(json.dumps(value if args.operation=='report' else {'status':'ok','operation':args.operation},indent=2))
