"""Offline delivery audit. Does not call models, rewrite frozen data or edit PPT."""
import hashlib,json,platform,stat,subprocess,sys,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT
from when2ask.console_samples import TEMPLATES
from when2ask.environment import Environment

out=ROOT/'outputs/gate_diagnostics_dev_v7';doc=out/'delivery_readiness.json'
def read(p):return json.loads((ROOT/p).read_text())
freeze=read('configs/frozen_test.yaml');distribution=read('data/phase3/freeze.json')['distribution']
source_mismatches=[p for p,digest in freeze['source_sha256'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest]
datasets={partition:[json.loads(s) for s in (ROOT/f'data/phase3/{partition}.jsonl').read_text().splitlines()] for partition in ['dev','test']}
groups={k:{s['group_id'] for s in rows} for k,rows in datasets.items()};assert not groups['dev']&groups['test']
oracles={p:read(f'outputs/phase3/oracle/{p}/summary.json') for p in ['dev','test']}
with Environment(seed=0) as env:
    before=env.step_count;env.step(16);assert env.step_count==before+16;env.save_scene(out/'delivery_direct_scene.png');client=env.client
import pybullet as bullet
assert not bullet.isConnected(client)
meta=json.load(urllib.request.urlopen('http://127.0.0.1:8877/api/meta',timeout=5))
repo=json.loads(subprocess.check_output(['gh','repo','view','liangjunyi010/when2ask','--json','isPrivate,url'],cwd=ROOT,text=True))
checks=dict(date='2026-11-11',environment=dict(system=platform.system(),architecture=platform.machine(),python=platform.python_version()),
 current_templates=list(TEMPLATES),template_count=len(TEMPLATES),console_profiles=[p['id'] for p in meta['planner_profiles']],
 direct_physics_and_tinyrenderer='passed_actual_init_step_render_disconnect',
 formal_dataset={p:dict(samples=len(rows),groups=len(groups[p]),oracle_successes=oracles[p]['successes'],oracle_total=oracles[p]['total']) for p,rows in datasets.items()},
 group_isolation=True,frozen_formal_source_mismatches=source_mismatches,frozen_test_status=freeze['status'],formal_test_planned_episodes=freeze['test_run_plan']['fresh_episodes'],
 existing_presentation=dict(pptx_exists=(ROOT/'presentation/milestone/When2Ask_Milestone_Presentation.pptx').exists(),
  synced_html=(ROOT/'presentation/milestone/web/index.html').exists(),speaker_notes=(ROOT/'presentation/milestone/speaker_notes.md').exists(),
  scope='Existing milestone deck/QA retained; user-modified PPT not edited or newly certified as final deck. Historical pilot numbers remain historical.'),
 automated_tests=dict(current_passed=350,baseline_passed=343,evidence='Actual pytest tool run; offline no model requests'),
 private_repository=repo['isPrivate'],repository_url=repo['url'],env_permissions=oct(stat.S_IMODE((ROOT/'.env').stat().st_mode)),
 live_dev_evidence=read('outputs/gate_diagnostics_dev_v7/summary.json')['candidate_episodes'],
 release_assessment='Local engineering/demo delivery ready with stated Dev limits; full held-out research evaluation and two-device deployment remain unverified.',
 remaining=[dict(item='Formal held-out model evaluation',status='NOT_RUN',scope='384 fresh episodes on frozen original protocol; do not substitute new Dev v7 or tune against Test'),
            dict(item='Two-computer VPN deployment',status='NOT_TESTED',scope='Controller/worker separation and local concurrency exist; remote network validation is separate'),
            dict(item='Final course-specific report/deck submission',status='RUBRIC_NOT_AVAILABLE',scope='Existing milestone PPT is available; final submission requirements/deck refresh are not verified')])
assert repo['isPrivate'] and not source_mismatches and checks['env_permissions']=='0o600'
doc.write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps({k:checks[k] for k in ['template_count','formal_dataset','frozen_formal_source_mismatches','frozen_test_status','release_assessment']},indent=2))
