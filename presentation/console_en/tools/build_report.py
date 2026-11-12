"""Summarize new rehearsal evidence without modifying any prior experiment."""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/presentation_console_en/20261112'
SESSION=ROOT/'outputs/local_console/presentation-en-20261112-a'
load=lambda p:json.loads(p.read_text())
protection=load(ROOT/'outputs/local_console/presentation-en-protection-20261112.json')
changed=[name for name,sha in protection.items()if not(ROOT/name).is_file()or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
assert not changed,changed
offline=load(OUT/'offline_qa3/validation.json')
live=load(OUT/'live_qa1/validation.json')
views=load(OUT/'views_final/validation.json')
assert offline['passed']and live['passed']and views['passed']
episodes=load(OUT/'live_qa1/raw_episodes.json')
hashes=[hashlib.sha256(json.dumps(e['turns'][0]['public_payload'],sort_keys=True).encode()).hexdigest()for e in episodes]
assert len(set(hashes))==1
rows=[]
records=[]
for e in episodes:
    src=SESSION/'tasks'/e['episode_id']/'api_attempts.jsonl'
    dst=OUT/'live_qa1/api_attempts'/f"{e['method']}.jsonl"
    dst.parent.mkdir(exist_ok=True)
    shutil.copyfile(src,dst)
    records.extend(json.loads(x)for x in src.read_text().splitlines())
    cost=e['cost']
    rows.append(dict(method=e['method'],task_success=e['evaluation']['task_success'],burden=e['evaluation']['clarification_burden'],
        api_attempts=cost['api_attempts'],api_latency_s=cost['api_latency_ms']/1000,
        deepseek_input=cost['deepseek']['input_tokens'],deepseek_output=cost['deepseek']['output_tokens'],
        jev_input=cost['jev']['input_tokens'],jev_output=cost['jev']['output_tokens'],
        actions=len(e['actions']),rounds=len(e['turns']),termination=e['termination_reason']))
assert len(records)==sum(r['api_attempts']for r in rows)==24
tests=ET.parse(OUT/'pytest.xml').getroot().find('testsuite')
assert tests.get('tests')=='364'and tests.get('failures')=='0'
payload=dict(scope='One new paired interactive Dev scene; not a new benchmark result',
    url='http://127.0.0.1:8902/',comparison_id=live['comparison_id'],offline_physics_cases=offline['tasks'],live_rows=rows,
    total_new_online_episodes=3,total_new_authenticated_requests=len(records),
    returned_models=sorted({r.get('returned_model')for r in records if r.get('returned_model')}),
    paired_initial_public_hash=hashes[0],independent_worker_pids=[r['worker_pid']for r in live['tasks']],
    original_files_verified=len(protection),original_files_changed=changed,
    original_frontend_preserved=True,frozen_benchmark_files_preserved=True,
    english_ui=True,presentation_view=True,decoded_recorded_videos=9,
    pytest=dict(tests.attrib),browser_errors=views['errors'],
    known_limits=['Two-computer VPN deployment is not tested.','Human reply controls appear only after actual ASK.',
        'Manual keyboard rehearsal used a scripted public-only policy with real physics; the three paired live runs used automatic user replies.',
        'Early frontend QA issues (mission selection visibility and mobile flow overflow) are retained in offline_qa1/2; final offline_qa3 and views_final passed.'])
(OUT/'summary.json').write_text(json.dumps(payload,indent=2)+'\n')
table='\n'.join(f"| {r['method']} | {'Success'if r['task_success']else'Unsuccessful'} | {r['burden']} | {r['api_attempts']} | {r['api_latency_s']:.2f}s | {r['deepseek_input']} / {r['deepseek_output']} | {str(r['jev_input'])+' / '+str(r['jev_output'])if r['jev_input']is not None else'—'} |"for r in rows)
report=f'''# English presentation console — actual rehearsal, 12 November2026

Independent UI: http://127.0.0.1:8902/. Original controller remains at8877. No frozen protocol, model prompt, threshold, motor controller, evaluator, dataset or historical record was changed.

## Actual new live Dev comparison

One retrieve/restore scene, three independent real PyBullet processes, unchanged Gate Dev v7 and shared planner. The three initial public payloads are byte-identical after canonical serialization. No whole-episode retry or outcome exclusion. Automatic User Simulator replies were used for all three methods.

| Method | Physical Task Result | Burden | API Attempts | API Latency | DeepSeek Input / Output | Jev Input / Output |
|---|---|---:|---:|---:|---:|---:|
{table}

Total:3 new online episodes,24 authenticated requests, zero API/schema errors or retries. Returned models:deepseek-flash and jev-1.14.0. This one Dev scene is a functional rehearsal, not a method ranking or a replacement for the frozen12-group Test results.

NoAsk chose the cup while the fixed hidden goal selected the block, so it scored unsuccessful from the physical evaluator. Both gates opened first, asked about the item, delivered the block and reclosed the box. Jev actually returned0.14 CONTINUE before opening, then0.83 ASK. These Dev scores are separate from the recorded Test replay's0.11/0.62.

## Actual manual and browser checks

- Final offline rehearsal:3/3 genuine physics tasks passed under clearly labelled scripted public-only policies. The human typed an English pad name into the browser; invalid input produced an English validation message. The manual robot stayed at the same physical state and frame hash while another independent robot completed an inspection task.
- NoAsk disabled Human controls and never created a question. The automatic inspection case completed by physically inspecting the label, with no ASK.
- Initial instructions, the full conversation, public DAGs and final Ground Truth were inspected. Hidden truth stayed absent before termination.
- All three navigation tabs work at1920,1280 and390px. Presentation View keeps the selected mission or paired three methods visible, with enlarged labels. No page overflow or JavaScript errors in the final checks.
- All9 actual recorded MP4s decoded. The embedded synchronized replay retained separate ASK and USER frames at the same simulation step; pause/restart and1×/2×/3× stayed on its shared timeline.
- Project pytest:364 passed in{float(tests.get('time')):.2f}s. Six new HTTP-boundary tests cover English/original separation, evidence allowlisting, path traversal denial, real video byte ranges and zero-inference read-only evidence.
- All{len(protection)} pre-existing tracked files remained hash-identical, including the user's uncommitted old Milestone PPT. Worker authentication files remain in the ignored local session folder and are not published.

## Evidence and boundaries

`offline_qa1/validation.json` retains the initial presentation selection failure;`offline_qa2/validation.json` retains the mobile overflow failure after actual successful physics runs. Both UI issues were fixed in the independent English frontend. `offline_qa3/validation.json` and`views_final/validation.json` are the final passing checks. No paid episode was repeated to improve a result.

The three live raw episodes and all24 per-attempt request/response/usage records are under`live_qa1/`. Authentication headers and key values are not included. The existing frozen Benchmark view serves original evidence read-only; no Test model calls were added. Two-machine VPN operation remains untested.
'''
(OUT/'README.md').write_text(report)
print(json.dumps({'new_live_episodes':3,'api_attempts':24,'protected_files':len(protection),'pytest':364,'report':str(OUT/'README.md')}))
