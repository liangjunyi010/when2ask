"""Metrics from raw independent Dev episodes; classifications never feed models."""
import csv
import json
from collections import defaultdict

from .accounting import Audit, SessionLedger
from .config import Config
from .dev_public_summary import PROFILES, digest
from .dev_summary_agents import prompt_hashes, question_spec
from .dev_summary_study import PLAN, CASES, OUTPUT
from .study_reporting import public_progress
from .study_data import write_json


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def eligibility(baseline, candidate):
    if set(baseline) != set(candidate) or len(baseline) != 4:
        return dict(promising=False, reason='Incomplete four-group pairing')
    no_regression = all((not old['task_success'] or candidate[k]['task_success'])
        and candidate[k]['early_asks'] <= old['early_asks']
        and candidate[k]['complete_asks'] <= old['complete_asks'] for k,old in baseline.items())
    reduction = sum(r['blocked_continues'] for r in baseline.values()) - sum(r['blocked_continues'] for r in candidate.values())
    return dict(promising=bool(no_regression and reduction>0), no_per_case_success_or_early_ask_regression=no_regression,
                blocked_continue_reduction=reduction, reason='Predeclared exploratory rule only; no automatic Test promotion')


def report():
    plan, cases = json.loads(PLAN.read_text()), json.loads(CASES.read_text())
    case_map = {c['case_id']:c for c in cases}
    rows, turns, attempts, matched = [], [], [], defaultdict(list)
    for job in plan['jobs']:
        path = OUTPUT / 'episodes' / job['run_id'] / 'episode.json'
        if not path.exists():
            continue
        ep = json.loads(path.read_text())
        if (ep['partition']!='dev' or ep['experiment_version']!='dev_public_summary_v1'
                or ep['evidence_kind']!='live_model_and_physics' or ep['profile']!=job['profile']
                or ep['prompt_hashes']!=prompt_hashes(job['profile'])):
            raise ValueError('Mixed or non-live evidence cannot enter the report')
        audit = Audit(ep['episode_id'], Config(), path=path.with_name('api_attempts.jsonl'))
        if audit.summary()!=ep['cost']:
            raise ValueError('Episode costs differ from raw JSONL')
        attempts.extend(audit.records)
        for attempt in audit.records:
            turn = ep['turns'][attempt['round']]
            payload = attempt.get('request')
            if not payload:
                continue  # Interrupted reservation: counted, no known sent body.
            actual = payload['state'] if attempt['backend']=='jev' else json.loads(payload['messages'][1]['content'])
            if actual != turn['model_payload']:
                raise ValueError('Actual API payload differs from the logged public projection')
            if attempt['backend']=='jev':
                question = payload['questions']['needs_clarification']
                instructions, criteria = question_spec(job['profile'])
                if question['instructions']!=instructions or question['criteria']!=criteria:
                    raise ValueError('Actual gate wording differs from the sealed profile')
                if attempt['status']=='ok' and attempt['response']['answers']['needs_clarification']['noul']!=turn['gate']['p_ask']:
                    raise ValueError('Gate probability differs from raw Noul response')
        timing = dict(early_asks=0, blocked_continues=0, complete_asks=0)
        for turn in ep['turns']:
            category = public_progress(turn['public_payload'])
            gate = turn.get('gate', {})
            decision = gate.get('decision')
            timing['early_asks'] += category=='supported_progress' and decision=='ASK'
            timing['blocked_continues'] += category=='preference_blocked' and decision=='CONTINUE'
            timing['complete_asks'] += category=='complete' and decision=='ASK'
            record = dict(case_id=job['case_id'], profile=job['profile'], round=turn['round'],
                step=turn['public_payload']['observation']['simulation_step'], timing_state=category,
                decision=decision, p_ask=gate.get('p_ask'), action=turn.get('action',{}).get('kind'),
                requested_roles=','.join(sorted({r['role'] for r in turn.get('question',{}).get('requests',[])})),
                public_state_sha256=digest(turn['public_payload']))
            turns.append(record)
            matched[(job['case_id'],record['public_state_sha256'])].append(record)
        cost, sample = ep['cost'], case_map[job['case_id']]['sample']
        row = dict(case_id=job['case_id'], profile=job['profile'], group_id=ep['group_id'],
            template=ep['template_id'], missing=3-len(sample['initial_disclosed_slots']),
            task_success=ep['evaluation']['task_success'], burden=ep['evaluation'].get('clarification_burden'),
            ask_turns=ep['diagnostics']['ask_turns'], actions=len(ep['actions']),
            physical_failures=ep['diagnostics']['physical_execution_failures'],
            repeated=ep['diagnostics']['repeated_slot_requests'], redundant=ep['diagnostics']['redundant_slot_requests'],
            **timing, api_attempts=cost['api_attempts'], api_latency_ms=cost['api_latency_ms'],
            deepseek_input_tokens=cost['deepseek']['input_tokens'], deepseek_output_tokens=cost['deepseek']['output_tokens'],
            jev_input_tokens=cost['jev']['input_tokens'], jev_output_tokens=cost['jev']['output_tokens'],
            retries=cost['retries'], schema_errors=cost['schema_errors'], api_errors=cost['api_errors'],
            termination_reason=ep['termination_reason'], initial_state_sha256=ep['turns'][0]['payload_sha256'],
            episode=str(path.relative_to(OUTPUT)))
        rows.append(row)
    if not rows:
        raise ValueError('No real Dev episodes yet')
    for case in case_map:
        initial = {r['initial_state_sha256'] for r in rows if r['case_id']==case}
        if len(initial)>1:
            raise ValueError('Paired initial public states differ')
    summary = []
    columns = ['burden','ask_turns','early_asks','blocked_continues','complete_asks','physical_failures',
        'deepseek_input_tokens','deepseek_output_tokens','jev_input_tokens','jev_output_tokens',
        'api_latency_ms','api_attempts','retries','schema_errors','api_errors']
    for profile in PROFILES:
        subset = [r for r in rows if r['profile']==profile]
        s = dict(profile=profile, completed=len(subset), task_successes=sum(r['task_success'] for r in subset))
        for key in columns:
            values = [r[key] for r in subset if r[key] is not None]
            s[key] = sum(values) if values else None
        summary.append(s)
    baseline = {r['case_id']:r for r in rows if r['profile']=='v3_original'}
    decisions = {p:eligibility(baseline,{r['case_id']:r for r in rows if r['profile']==p}) for p in PROFILES[1:]}
    ledger = SessionLedger(OUTPUT / 'inference',140,12,policy='phase3_dev').snapshot()
    if ledger['attempts']!=len(attempts):
        raise ValueError('Global request ledger differs from raw attempt records')
    out = OUTPUT / 'report';out.mkdir(exist_ok=True)
    write_csv(out / 'episodes.csv', rows);write_csv(out / 'gate_turns.csv',turns);write_csv(out / 'summary.csv',summary)
    write_json(out / 'analysis.json', dict(summary=summary, eligibility=decisions, budget=ledger,
        returned_models=sorted({a['returned_model'] for a in attempts if a.get('returned_model')}),
        paired_cases=len(case_map), independent_groups=len({c['sample']['group_id'] for c in cases}),
        test_api_episodes=0, completed_episodes=len(rows), planned_episodes=len(plan['jobs'])))
    write_json(out / 'matched_public_states.json', [dict(case_id=k[0],public_state_sha256=k[1],observations=v)
        for k,v in matched.items() if len({r['profile'] for r in v})>1])
    lines = ['# Independent Dev public-summary diagnostic', '',
        'Four independent Dev scene groups, one case each, three paired Jev conditions. Threshold fixed at 0.5. '
        'The console regression was intentionally selected after an observed failure; the remaining cases were seeded public-coverage draws. '
        'These are targeted engineering diagnostics, not held-out or statistically confirmatory results.', '',
        '| Profile | Task success | Burden | Early ASK | Blocked CONTINUE | Complete ASK | API seconds (sum) | DeepSeek in/out | Jev in/out |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in summary:
        latency='unknown' if s['api_latency_ms'] is None else f"{s['api_latency_ms']/1000:.3f}"
        lines.append(f"| {s['profile']} | {s['task_successes']}/{s['completed']} | {s['burden']} | {s['early_asks']} | "
            f"{s['blocked_continues']} | {s['complete_asks']} | {latency} | {s['deepseek_input_tokens']}/{s['deepseek_output_tokens']} | "
            f"{s['jev_input_tokens']}/{s['jev_output_tokens']} |")
    lines += ['', '## Per-case pairing', '', '| Case | Missing | Profile | Success | Burden | Early / blocked |', '|---|---:|---|---|---:|---|']
    for case in case_map:
        for r in sorted([r for r in rows if r['case_id']==case],key=lambda r:PROFILES.index(r['profile'])):
            lines.append(f"| {case} | {r['missing']} | {r['profile']} | {r['task_success']} | {r['burden']} | {r['early_asks']} / {r['blocked_continues']} |")
    lines += ['', '## Predeclared interpretation', '', '```json',json.dumps(decisions,indent=2),'```','',
        'No candidate is promoted to the frozen Test configuration. Four groups, including a targeted regression, are insufficient for generalization claims. '
        'compact_state changes the public representation supplied to BOTH gate and planner; its success difference is not a pure gate-only effect. '
        'compact_question vs compact_state keeps that representation and the action/question planner prompts identical, changing only the gate wording.', '',
        'Timing labels are computed offline with the unchanged public_progress diagnostic, never sent to a model. '
        'Raw gate scores are only compared at identical public-state hashes in matched_public_states.json; equal round indices on divergent trajectories are not treated as matched states.', '',
        f"Actual authenticated requests: {ledger['attempts']}/{ledger['max_attempts']}; episodes: {ledger['episodes']}/{ledger['max_episodes']}. "
        'All retries/repairs count. Unknown usage stays null in raw records, and provider token counts are not combined as dollar cost.', '',
        'All metrics above derive from episode JSON and raw API JSONL. Scene/final PNGs, real execution logs, independent geometric/contact/DAG scores and ASK freeze checks are saved per episode. '
        'The regression baseline and joint variant also have locally generated real PyBullet GIFs; GIF files remain ignored by Git.', '',
        'Noul wording follows the positive yes/no proposition interface documented at https://docs.typesafe.ai/primitives/noul. '
        'Original source/data/configuration and historical experiment preservation are audited separately. No held-out Test inference was run.', '']
    (out / 'README.md').write_text('\n'.join(lines))
    return dict(summary=summary,eligibility=decisions,budget=ledger)
