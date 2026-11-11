"""Freeze Dev v6 nine-episode paired study after paid probes and offline QA."""
import hashlib,json,random,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT,Config
from when2ask.memory_dev_agents import prompt_hashes
from when2ask.memory_dev_public import PROFILE,SUPPORTED
from when2ask.console_state import ConsoleLedger

out=ROOT/'outputs/memory_planner_dev_v6';dest=out/'live_plan.json'
if dest.exists():raise FileExistsError('Never replace a frozen plan')
ui=json.loads((out/'browser/validation.json').read_text());probes=json.loads((out/'probes_r2/summary.json').read_text())
assert ui['successes']==3 and ui['authenticated_requests']==0
assert probes['probes']==6 and probes['matches']==6
ledger=ConsoleLedger(ROOT/'outputs/local_console/memory-dev-v6-live/inference',150,9).snapshot()
assert ledger['episodes']==0
probe_attempts=sum(len(p.read_text().splitlines()) for p in out.glob('probes*/*.api.jsonl'))
assert probe_attempts==ledger['attempts']
templates=list(SUPPORTED);random.Random(42781111).shuffle(templates)
paths=list((ROOT/'src/when2ask').glob('*.py'))+list((ROOT/'src/when2ask/console_web').glob('*'))
plan=dict(version=PROFILE,created_date='2026-11-11',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 purpose='Nine real paired Dev episodes: one existing fixed scene per task, independent resets across methods. Not formal Test.',
 configuration=Config.load().public_config(),planner_profile=PROFILE,prompt_hashes=prompt_hashes(),
 source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},
 dataset_sha256=hashlib.sha256((ROOT/'data/six_tasks_dev_v1/samples.json').read_bytes()).hexdigest(),
 groups=[dict(template=t,unknown_preferences=1,planner_profile=PROFILE) for t in templates],
 methods=['llm_noask','llm_gate','jev_gate'],run_order_seed=42781111,answer_mode='auto',gate_threshold=.5,
 prior_action_only_probe_attempts=probe_attempts,
 limits=dict(full_episodes=9,cumulative_authenticated_attempts=150,rounds=20,robot_actions=12,slot_requests=12,api_attempts_per_episode=32),
 planner_parameters=dict(action_max_tokens=650,question_max_tokens=300,deepseek_gate_max_tokens=64,temperature=0,thinking='disabled',json_output=True),
 failure_policy='One API retry, all attempts including retained r1/r2 probes charged to SAME persistent ledger. HTTP-200 schema failures are separate from backend outages; auth/network/permanent errors retain breaker. No full episode reruns or mid-study prompt/source changes.',
 isolation='Only current and earlier actual public observations/history enter memory. No private theta, hidden contents, evaluator conditions or prescribed next action. Gate then shared planner, first action verbatim, no action rewriting or automatic DONE. Original worker/skills/evaluator unchanged.')
dest.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({k:plan[k] for k in ['code_commit','groups','prior_action_only_probe_attempts','limits','prompt_hashes']},indent=2))
