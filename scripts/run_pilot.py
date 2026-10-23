"""Run/resume the predeclared small paired pilot; never exceed the shared session cap."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from when2ask.accounting import Limits, SessionLedger
from when2ask.benchmark import find_sample
from when2ask.config import Config, ROOT
from when2ask.prompts import ACTION_PROMPT, GATE_RULES, QUESTION_PROMPT
from when2ask.reporting import report
from when2ask.research_runner import run_sample


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--plan", type=Path, default=ROOT / "docs/phase2/experiment_plan_v2.json")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "outputs/phase2_live/paired_v2")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    hashes = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in
              (("action", ACTION_PROMPT), ("question", QUESTION_PROMPT), ("gate_rules", GATE_RULES))}
    if hashes != plan["prompt_hashes"]:
        raise ValueError("Current prompts differ from the predeclared plan")
    config = Config.load()
    if config.threshold != plan["threshold"]:
        raise ValueError("Configured threshold differs from the predeclared plan")
    ledger = SessionLedger(ROOT / "outputs/phase2_live")
    for sample_id in [plan["experiment_b"], *plan["experiment_c"]]:
        sample = find_sample(sample_id)
        split = sample_id.split("_")[0]
        oracle_path = ROOT / "outputs/phase2/oracle" / split / f"{sample_id}.json"
        oracle = json.loads(oracle_path.read_text())
        if not oracle["evaluation"]["task_success"]:
            raise ValueError("Oracle did not confirm this scene")
        if oracle["evaluation"]["details"]["expected_objects"] != {
                r: sample.theta_star[r + "_choice"] for r in ("cup", "block", "lid")}:
            raise ValueError("Oracle evidence is for another dataset revision")
        sample_episodes = []
        for method in plan["methods"]:
            out = args.run_dir / sample_id / method
            if (out / "episode.json").exists():
                episode = json.loads((out / "episode.json").read_text())
                if episode["prompt_hashes"] != hashes or episode["evidence_kind"] != "live_model_and_physics":
                    raise ValueError("Existing episode has another configuration or is a test double")
                print(f"KEEP existing verified episode {sample_id}/{method}", flush=True)
            else:
                episode = run_sample(sample, method, out, live=True, session=ledger,
                                     limits=Limits(**plan["per_episode"]), record=sample_id == plan["experiment_b"])
            sample_episodes.append(episode)
        if sample_id == plan["experiment_b"] and any(
                e["error"] or e["diagnostics"]["physical_execution_failures"] for e in sample_episodes):
            print("Experiment B has execution/API errors; stopping further paid testing.", flush=True)
            report(args.run_dir)
            return 1
    report(args.run_dir)
    print("SESSION", json.dumps(ledger.snapshot()), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
