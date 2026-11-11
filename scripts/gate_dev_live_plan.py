"""Freeze a six-episode original/candidate check after the prelocked gate matrix."""
import hashlib,json,random,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT,Config
from when2ask.gate_ready_dev import configuration,prompt_hashes
from when2ask.console_state import ConsoleLedger

out=ROOT/'outputs/gate_diagnostics_dev_v7';dest=out/'live_plan.json'
if dest.exists():raise FileExistsError('Do not overwrite frozen study')
selection=json.loads((out/'selection.json').read_text());ui=json.loads((out/'browser/validation.json').read_text())
assert selection['selected']=='s1c0' and selection['all_jobs_complete'] and ui['successes']==3
jobs=[dict(template='buffer_exchange',method=m,planner_profile=p,unknown_preferences=1,answer_mode='auto') for m in ['llm_gate','jev_gate'] for p in ['memory_dev_v6','gate_dev_v7']]
jobs += [dict(template=t,method='jev_gate',planner_profile='gate_dev_v7',unknown_preferences=1,answer_mode='auto') for t in ['retrieve_restore','occlusion_inspection']]
random.Random(42781113).shuffle(jobs)
ledger=ConsoleLedger(ROOT/'outputs/local_console/gate-diagnostics-v7-live/inference',150,6).snapshot();assert ledger['episodes']==0
paths=list((ROOT/'src/when2ask').glob('*.py'))+list((ROOT/'src/when2ask/console_web').glob('*'))
plan=dict(date='2026-11-11',purpose='Four matched buffer method×profile episodes and two candidate Jev task controls. One scene per task, not independent statistical trials.',
 code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),jobs=jobs,order_seed=42781113,configuration=Config.load().public_config(),
 candidate=configuration(),prompt_hashes=prompt_hashes(),prior_gate_attempts=ledger['attempts'],
 source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},
 dataset_sha256=hashlib.sha256((ROOT/'data/six_tasks_dev_v1/samples.json').read_bytes()).hexdigest(),
 budgets=dict(full_episodes=6,total_requests_including_diagnostics=150,rounds=20,actions=12,slot_requests=12,attempts_per_episode=32),
 failure_policy='One API retry; every attempt charged to same persistent ledger. No whole-episode reruns or threshold/source changes. Retain any failure. Actual API-health breaker remains.',
 not_formal_test=True,threshold=.5)
dest.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({k:plan[k] for k in ['code_commit','jobs','prior_gate_attempts','budgets']},indent=2))
