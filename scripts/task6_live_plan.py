"""Lock six new-task live cases before any authenticated request. No API calls."""
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from when2ask.config import Config,ROOT
from when2ask.task6_agents import prompt_hashes
from when2ask.task6_spec import TITLES,SOURCES


def main():
    out=ROOT/'outputs/six_tasks_dev_v1';path=out/'live_plan.json'
    if path.exists():raise FileExistsError('Do not replace a locked online plan')
    oracle=json.loads((out/'oracle_02/summary.json').read_text());ui=json.loads((out/'browser/validation.json').read_text())
    if oracle['successes']!=6 or ui['successes']!=6:raise ValueError('Physical and UI verification must pass first')
    methods=('llm_noask','llm_gate','jev_gate')
    jobs=[dict(template=t,method=methods[i%3],unknown_preferences=1,answer_mode='auto') for i,t in enumerate(TITLES)]
    random.Random(427811).shuffle(jobs)
    hashes={name:hashlib.sha256((ROOT/'src/when2ask'/name).read_bytes()).hexdigest() for name in SOURCES}
    result=dict(version='six_tasks_dev_v1',purpose='one real episode per new task, rotating methods; unpaired engineering smoke, not a ranking',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        dataset_sha256=hashlib.sha256((ROOT/'data/six_tasks_dev_v1/samples.json').read_bytes()).hexdigest(),
        prompt_hashes=prompt_hashes(),source_hashes=hashes,configuration=Config.load().public_config(),
        limits=dict(episodes=6,authenticated_attempts=120,rounds_per_episode=20,robot_actions_per_episode=12,
                    slot_requests_per_episode=12,api_attempts_per_episode=32),
        failure_policy='Existing one API retry, all attempts charged; permanent or three consecutive errors block backend. No whole-episode reruns.',
        jobs=jobs,run_order_seed=427811)
    path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
