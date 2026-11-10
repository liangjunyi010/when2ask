"""Freeze the nine paired Dev jobs before any real request. No API calls."""
import hashlib,json,random,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import ROOT,Config
from when2ask.grounded_dev_public import SUPPORTED,PROFILE
from when2ask.grounded_dev_agents import prompt_hashes

out=ROOT/'outputs/grounded_planner_dev_v5';dest=out/'live_plan.json'
if dest.exists():raise FileExistsError('Locked plan already exists; do not overwrite')
ui=json.loads((out/'browser/validation.json').read_text())
if ui['successes']!=3 or ui['authenticated_requests']!=0:raise ValueError('Offline UI / physics must pass')
templates=list(SUPPORTED);random.Random(42781110).shuffle(templates)
paths=list((ROOT/'src/when2ask').glob('*.py'))+list((ROOT/'src/when2ask/console_web').glob('*'))
hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
samples=ROOT/'data/six_tasks_dev_v1/samples.json'
plan=dict(version=PROFILE,created_date='2026-11-10',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 purpose='Three fixed Dev task instances × three real methods, paired by physical scene/hidden truth; not formal Test, no ranking inference.',
 configuration=Config.load().public_config(),planner_profile=PROFILE,prompt_hashes=prompt_hashes(),source_hashes=hashes,
 dataset_sha256=hashlib.sha256(samples.read_bytes()).hexdigest(),
 groups=[dict(template=t,unknown_preferences=1,planner_profile=PROFILE) for t in templates],
 methods=['llm_noask','llm_gate','jev_gate'],run_order_seed=42781110,
 limits=dict(episodes=9,authenticated_attempts=150,rounds=20,robot_actions=12,slot_requests=12,api_attempts_per_episode=32),
 planner_parameters=dict(action_max_tokens=650,question_max_tokens=300,deepseek_gate_max_tokens=64,temperature=0,thinking='disabled',json_output=True),
 answer_mode='auto',gate_threshold=.5,
 failure_policy='Existing one retry per API call, all attempts charged; permanent or three consecutive errors block backend. No whole-episode reruns; retain failures.',
 physics_policy='Existing real skills and independent task6 evaluator unchanged. No action cache, action rewriting, logical action mask or scripted fallback. Gate precedes each planner call. Only first model-proposed action executes.')
dest.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({k:v for k,v in plan.items() if k not in ['source_hashes']},indent=2))
