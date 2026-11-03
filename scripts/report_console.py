"""Summarize existing console evidence. Never sends model or robot requests."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from when2ask.config import Config


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def build(session, evidence):
    config = Config.load()
    report_path = evidence / 'live_validation.json'
    report = json.loads(report_path.read_text())
    table = []
    for row in report['results']:
        task_dir = session / 'tasks' / row['id']
        episode = json.loads((task_dir / 'episode.json').read_text())
        attempts = jsonl(task_dir / 'api_attempts.jsonl')
        # Preserve original attempts in the ignored session; publish sanitized copies.
        attempts = config.sanitize(attempts)
        episode['api_attempts'] = attempts
        row['returned_models'] = sorted({a['returned_model'] for a in attempts if a.get('returned_model')})
        row['physical_skills_succeeded'] = sum(a['success'] is True for a in episode['actions'])
        row['gate_trace'] = [t['gate'] for t in episode['turns'] if t.get('gate', {}).get('called')]
        assert row['api_attempts'] == len(attempts)
        assert episode['cost'] == row['cost']
        assert episode['evaluation']['task_success'] is row['task_success']
        write_json(evidence / f"live_{row['method']}_episode.json", config.sanitize(episode))
        (evidence / f"live_{row['method']}_api_attempts.jsonl").write_text(
            ''.join(json.dumps(a, ensure_ascii=False) + '\n' for a in attempts))
        ds, jev = row['cost']['deepseek'], row['cost']['jev']
        table.append(dict(method=row['method'], task_success=row['task_success'], burden=row['burden'],
                          physical_skills=row['physical_skills_succeeded'],
                          deepseek_input_tokens=ds['input_tokens'], deepseek_output_tokens=ds['output_tokens'],
                          jev_input_tokens=jev['input_tokens'], jev_output_tokens=jev['output_tokens'],
                          api_latency_s=row['cost']['api_latency_ms'] / 1000,
                          api_attempts=len(attempts), retries=row['cost']['retries'],
                          returned_models='; '.join(row['returned_models'])))
    discovery = config.sanitize(jsonl(session / 'discovery_attempts.jsonl'))
    (evidence / 'discovery_attempts.jsonl').write_text(''.join(json.dumps(a) + '\n' for a in discovery))
    write_json(evidence / 'discovery_results.json', config.sanitize(json.loads((session / 'discovery_results.json').read_text())))
    assert sum(r['api_attempts'] for r in table) + len(discovery) == report['budget']['attempts']
    report['discovery_attempts'] = len(discovery)
    report['episode_inference_attempts'] = sum(r['api_attempts'] for r in table)
    report['budget_note'] = 'Dedicated console ledger; policy phase2 is the reused ledger primitive, not a historical experiment session.'
    write_json(report_path, config.sanitize(report))
    with (evidence / 'live_results.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(table)
    tests = ElementTree.parse(evidence / 'pytest.xml').getroot().findall('.//testcase')
    passed = sum(not any(t.find(k) is not None for k in ('failure', 'error', 'skipped')) for t in tests)
    browser = json.loads((evidence / 'browser_validation.json').read_text())
    visual = json.loads((evidence / 'browser_visual_validation.json').read_text())
    lines = [
        '# Local console validation — 2026-11-03', '',
        'Interactive engineering checks, not a Dev/Test benchmark or a new ranking of methods. '
        'Frozen datasets, prompts, controllers and historical results were preserved. No held-out Test API episodes ran.', '',
        '## Three real-model executions', '',
        'One fixed interactive pack-and-cover instance per method; automatic structured user replies. '
        'The initial instruction specifies the blue cup. The fixed simulator prefers the green block and black lid. '
        'All methods use independent resets and the unchanged shared planner/prompts. '
        'The API latency below is the sum of actual calls within that one episode, excluding physical execution.', '',
        '| Method | Task success | Burden | Physical skills | DeepSeek in/out | Jev in/out | API seconds | Attempts |',
        '|---|---|---:|---:|---:|---:|---:|---:|'
    ]
    for r in table:
        j = '—' if r['jev_input_tokens'] is None else f"{r['jev_input_tokens']}/{r['jev_output_tokens']}"
        lines.append(f"| {r['method']} | {r['task_success']} | {r['burden']} | {r['physical_skills']}/3 | "
                     f"{r['deepseek_input_tokens']}/{r['deepseek_output_tokens']} | {j} | {r['api_latency_s']:.3f} | {r['api_attempts']} |")
    lines.extend(['',
        'LLM-Gate asked early, before moving the known cup, then completed successfully. '
        'Jev returned CONTINUE at 0.27, 0.37, 0.13 and 0.05 (threshold 0.5), so it never clarified. '
        'NoAsk and Jev physically packed the guessed yellow block and white lid; the independent evaluator correctly rejected them. '
        'These current observations do not replace the earlier Phase 3 calibration results.', '',
        'Both providers authenticated successfully. DeepSeek returned `deepseek-flash` '
        '(discovery catalogue name `DeepSeek-V4.1-Flash`); Jev configured `jev-latest`, returned `jev-1.14.0`. '
        'Aliases may evolve; old frozen model records were not rewritten. No API/schema errors or retries occurred.', '',
        f"The dedicated console session used **{report['budget']['attempts']}/{report['budget']['max_attempts']} authenticated attempts** "
        f"({len(discovery)} discovery + {report['episode_inference_attempts']} inference) and "
        f"**{report['budget']['episodes']}/{report['budget']['max_episodes']} live episodes** at this validation checkpoint. "
        'These are persisted session caps, not a recommendation to start another benchmark.', '',
        '## Offline policies, real physics and browser checks', '',
        f"- Three concurrent independent Bullet processes: {browser['independent_worker_pids']}.",
        f"- Manual ASK: fresh worker snapshots were exactly equal at step {browser['ask_simulation_step']}; other tasks continued.",
        '- Browser reload retained the question; duplicate answer did not execute a second action.',
        '- Human chose yellow block and white lid. Real physics succeeded under the explicitly declared interactive intent.',
        '- Automatic two-container task succeeded. Scripted NoAsk failed its actual preference score.',
        '- Fourth task queued at capacity three and was cancelled without starting physics.',
        '- Each displayed JPEG matched the worker SHA and simulation-step metadata. No synthetic robot animation.',
        f"- Browser logic checks: {browser['passed']}; final 1920×1080 layout/focus check: {visual['passed']}; no JavaScript errors.",
        f'- Offline pytest: **{passed}/{len(tests)} passed**, including the original 102 tests and 24 console checks. No paid API in pytest.', '',
        'Detailed evidence: `browser_validation.json`, `browser_visual_validation.json`, `pytest.xml`, '
        '`live_validation.json`, `live_results.csv`, per-method episode JSON and raw sanitized API JSONL. '
        'The ignored session retains earlier failed development attempts as well; only the identified final validation runs appear here.', '',
        '## Reproduce', '', '```sh',
        'python console.py --live --output-dir outputs/local_console/<new-session> --api-limit 60 --live-episode-limit 6',
        '# Separate terminal: real browser + real physics, no model API:',
        'node scripts/console_browser_check.mjs',
        '# Explicitly paid, creates three new live episodes; do not rerun merely to build a report:',
        'node scripts/console_live_check.mjs --live --session-dir outputs/local_console/<new-session>',
        '# Offline only, after the evidence above exists:',
        'python scripts/report_console.py --session-dir outputs/local_console/<new-session>', '```', '',
        '## Limits', '',
        'The single-machine controller/worker HTTP boundary is tested. Two physical computers and VPN transport are not yet verified. '
        'Browser reconnect works. Controller/worker crash recovery from a partially completed grasp is not implemented; '
        'saved logs and the session budget survive, while in-memory task cards do not survive a controller restart. '
        'Manual preference changes define interactive intent and are not pooled with fixed-hidden-preference benchmark scores.', ''
    ])
    (evidence / 'README.md').write_text('\n'.join(lines))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence.iterdir()
              if p.is_file() and p.name != 'evidence_hashes.json'}
    write_json(evidence / 'evidence_hashes.json', hashes)
    return dict(passed_tests=passed, episodes=len(table), authenticated_attempts=report['budget']['attempts'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-dir', type=Path, required=True)
    parser.add_argument('--evidence-dir', type=Path, default=ROOT / 'outputs/console_evidence')
    args = parser.parse_args()
    print(json.dumps(build(args.session_dir, args.evidence_dir)))
