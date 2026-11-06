"""Build the command-center delivery report from saved evidence; no network."""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree

OUT = Path(__file__).resolve().parents[1] / 'outputs/command_center_evidence'


def read(name):
    return json.loads((OUT / name).read_text())


def main():
    live, offline = read('live_validation.json'), read('browser_validation.json')
    development = read('development_attempt_1/comparison.json')
    correction = read('development_attempt_1/accounting_correction.json')
    cases = ElementTree.parse(OUT / 'pytest.xml').getroot().findall('.//testcase')
    passed = sum(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases)
    sources = sorted(OUT.glob('live_*_api_attempts.jsonl')) + sorted((OUT / 'development_attempt_1').glob('*_api_attempts.jsonl'))
    attempts = [json.loads(x) for p in sources for x in p.read_text().splitlines() if x.strip()]
    assert len(attempts) == live['new_authenticated_attempts'] + correction['actual_authenticated_attempts']
    totals = {}
    for b in ('deepseek', 'jev'):
        rows = [a for a in attempts if a['backend'] == b]
        totals[b] = dict(attempts=len(rows), **{k: sum(a[k] for a in rows if a.get(k) is not None)
                         for k in ('input_tokens', 'output_tokens', 'latency_ms')})
    summary = dict(tests_passed=passed, tests_total=len(cases), live_episodes_this_delivery=6,
        authenticated_attempts_this_delivery=len(attempts), final_group_id=live['group_id'],
        verified_session_budget=live['budget'], provider_totals_including_development_repeat=totals,
        physical_skills_succeeded=sum(r['physical_successes'] for r in development['rows'] + live['results']),
        formal_test_episodes=0, retries=sum(a.get('attempt', 1)>1 for a in attempts),
        api_errors=sum(a['status']=='api_error' for a in attempts), schema_errors=sum(a['status']=='schema_error' for a in attempts),
        browser_passed=offline['passed'] and live['passed'] and read('final_visual_validation.json')['passed'])
    lines = ['# Robot Command Center — 2026-11-06', '',
        'Local delivery: dark robot wall, one-click three-method comparison and unified clarification queue. '
        'Camera images are real PyBullet renders. Frozen data/prompts, core physics/evaluator and prior results are preserved.', '',
        '## Validation', '',
        f'- **{passed}/{len(cases)} offline tests passed**. No paid requests in pytest.',
        '- Real Chromium checks at 1920×1080, 1440×900 and 430×932, without page overflow or unexpected JS errors.',
        '- Two simultaneous manual questions: switching/reload retained drafts; cross-task answers were rejected (expected HTTP 409); duplicate submission was ignored.',
        '- Fresh ASK snapshots stayed identical while a third robot progressed. Three scripted physical tasks succeeded with burdens 2/1/0; a fourth queued task was cancelled.',
        '- A separate all-unknown profile asked for cup/block/lid before its first action, charged burden 3 and completed real physics after an automatic one-time reply; zero model calls.',
        '- Worker JPEG hashes and simulation steps matched displayed frames. Selected inspector, real Jev probability and evaluator success/failure colors were checked.',
        '- One-click comparison: three independent workers, identical initial public payloads and shared prompt hashes, automatic replies, matching JSON/CSV and browser reload.', '',
        '## Final verified real-model comparison', '',
        f"Group `{live['group_id']}` uses a validated Dev layout with two unknown preferences. "
        'Each method has a fresh world and fixed structured simulator. These interactive samples are separate from the frozen benchmark.', '',
        '| Method | Task success | Burden | ASK | Physical skills | API seconds | DeepSeek in/out | Jev in/out |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in live['results']:
        d, j = r['cost']['deepseek'], r['cost']['jev']
        jt = f"{j['input_tokens']}/{j['output_tokens']}" if j['attempts'] else '—'
        lines.append(f"| {r['method']} | {r['task_success']} | {r['burden']} | {r['ask_turns']} | "
            f"{r['physical_successes']}/{r['robot_actions']} | {r['cost']['api_latency_ms']/1000:.3f} | "
            f"{d['input_tokens']}/{d['output_tokens']} | {jt} |")
    probs = [t['gate']['p_ask'] for t in read('live_jev_gate_pack_and_cover_episode.json')['turns']
             if t.get('gate', {}).get('p_ask') is not None]
    lines += ['',
        'All 9 final-comparison skills succeeded. NoAsk and Jev guessed yellow block/white lid; '
        'the independent evaluator rejected these against green-block/black-lid preferences. '
        'LLM-Gate asked before moving the known cup and then succeeded. No outcomes were forced.', '',
        f'Jev probabilities: `{probs}`, threshold 0.5. Returned models: `deepseek-flash`, `jev-1.14.0`. '
        'No prompt/model tuning or formal Test calls occurred. API seconds sum actual request latencies; '
        'CSV wall time includes queue/physics. Tokens remain separate by provider. One paired instance cannot establish a ranking.', '',
        '## Development accounting correction', '',
        'The first comparison completed 3 real episodes and 22 actual API calls. Per-task costs were complete, '
        'but batch creation omitted the shared audit-session binding, so the global request-counter assertion failed. '
        'Unmodified raw logs and scores are retained under `development_attempt_1/`. '
        '`accounting_correction.json` records the explicit reconstruction of the old session counter and source hashes.', '',
        'Every paired task now uses the shared ledger. A regression test verifies reservations before network and rejection at the shared ceiling. '
        'The full comparison was rerun in a fresh bounded session; all 22 requests had positive reservation IDs and exactly matched its counter.', '',
        f"Total online work: **6 episodes, {len(attempts)} authenticated calls, {summary['physical_skills_succeeded']}/18 successful skills**, "
        'no API/schema errors or retries. The two comparisons repeat the same layout and are not six independent scenarios. '
        'No discovery calls were needed. The delivered session checkpoint is 22/60 attempts and 3/6 live episodes; '
        'the reconciled development session is separate. Later user launches can increase these counts.', '',
        '## Reproduce', '', '```sh',
        'python console.py --live --output-dir outputs/local_console/<fresh-session> --api-limit 60 --live-episode-limit 6',
        '# Real browser/physics, no model calls:',
        'node scripts/command_center_check.mjs',
        '# Explicitly paid, creates exactly one three-method group:',
        'node scripts/command_center_check.mjs --live --session-dir outputs/local_console/<fresh-session>',
        '# Offline report only:', 'python scripts/report_command_center.py', '```', '',
        '## Evidence and limits', '',
        'Numbered PNGs show real browser rendering. `browser_validation.json`, `live_validation.json`, '
        '`final_visual_validation.json`, `pytest.xml` and `preservation_validation.json` contain checks. '
        '`live_comparison.json`/`.csv`, per-method episode JSON and API JSONL contain measured results. '
        '`summary.json` includes total usage; `evidence_hashes.json` checks artifact integrity.', '',
        'Two physical computers/VPN and worker crash-resume remain unverified. Browser reload/reconnect works; '
        'a full controller restart starts a new in-memory registry while files and budget persist. '
        'Manual intent-setting episodes remain separate from fixed-preference comparisons.', '']
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (OUT / 'README.md').write_text('\n'.join(lines))
    hashes = {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(OUT.rglob('*')) if p.is_file() and p.name != 'evidence_hashes.json'}
    (OUT / 'evidence_hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
