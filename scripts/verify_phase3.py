"""Offline evidence audit. Never calls APIs or rewrites historical Phase 2 files."""
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from PIL import Image
from when2ask.calibration import FROZEN_DATA, LIVE, PLAN, verify_plan
from when2ask.config import Config
from when2ask.study_agents import ACTION_PROMPT, QUESTION_PROMPT
from when2ask.study_data import sha256
from when2ask.study_cli import stable_dev_report


def verify():
    plan = verify_plan()
    old = json.loads((ROOT / "outputs/phase3/baseline/summary.json").read_text())
    assert all(sha256(ROOT / p) == h for p,h in old["historical_sha256"].items())
    report = stable_dev_report()
    assert report["episodes"] == 40 and report["independent_groups"] == 8
    assert report["session"]["episodes"] == 40 and report["session"]["attempts"] <= 600
    initial, rows, gifs = {}, [], []
    config = Config.load()
    for job in plan["jobs"]:
        out = LIVE / "dev" / job["run_id"]
        ep = json.loads((out / "episode.json").read_text())
        assert ep["method"] == job["method"] and ep["group_id"] == job["group_id"]
        assert ep["scene_seed"] == job["scene_seed"] and ep["partition"] == "dev"
        digest = ep["turns"][0]["payload_sha256"]
        assert initial.setdefault(job["sample_id"], digest) == digest
        for check in ep["ask_checks"]:
            assert check["before_step"] == check["after_step"] and check["state_unchanged"]
        assert ep["diagnostics"]["clarification_burden"] == sum(c["charged_slots"] for c in ep["ask_checks"])
        if ep["method"] == "llm_noask":
            assert not ep["ask_checks"]
            assert all(r["stage"] == "action" and r["backend"] == "deepseek" for r in ep["api_attempts"])
            assert all(not turn["gate"]["called"] for turn in ep["turns"])
        by_round = {}
        for call in ep["api_attempts"]:
            by_round.setdefault(call["round"], []).append(call)
            if call["stage"] in ("question", "action"):
                expected = QUESTION_PROMPT if call["stage"] == "question" else ACTION_PROMPT
                assert call["backend"] == "deepseek"
                assert call["request"]["messages"][0]["content"] == expected
                assert call["request"]["temperature"] == 0
                assert call["request"]["max_tokens"] == 500
            request = call["request"]
            state = request["state"] if call["backend"] == "jev" else json.loads(request["messages"][1]["content"])
            assert state == ep["turns"][call["round"]]["public_payload"]
            raw = json.dumps(state)
            for key in ("theta_star", "slots", "dag", "group_id", "sample_id", "partition", "task_success"):
                assert '"' + key + '"' not in raw
        if ep["method"] != "llm_noask":
            assert all(calls[0]["stage"] == "gate" for calls in by_round.values())
        for name in ("scene.png", "final.png"):
            with Image.open(out / name) as image:
                assert image.size == (960,720)
                image.verify()
        if "recording" in ep:
            metadata = ep["recording"]
            assert metadata["renderer"] == "PyBullet ER_TINY_RENDERER"
            assert len({f["simulation_step"] for f in metadata["frames"]}) > 20
            with Image.open(out / "demo.gif") as image:
                assert image.n_frames == metadata["encoded_frame_count"]
                gifs.append(dict(path=str((out / "demo.gif").relative_to(ROOT)), frames=image.n_frames,
                                 sha256=sha256(out / "demo.gif")))
        rows.append(dict(run_id=job["run_id"], initial_payload_sha256=digest,
                         episode_sha256=sha256(out / "episode.json"), success=ep["evaluation"]["task_success"]))
    frozen = json.loads((ROOT / "configs/frozen_test.yaml").read_text())
    manifest = json.loads((ROOT / "configs/frozen_test_manifest.json").read_text())
    assert frozen["status"] == "FROZEN_NOT_RUN" and frozen["partition"] == "test"
    assert manifest["config_sha256"] == sha256(ROOT / "configs/frozen_test.yaml")
    assert frozen["gate_threshold"] == report["threshold_selection"]["selected_threshold"]
    assert frozen["source_sha256"] == plan["source_sha256"]
    assert frozen["dev_report_sha256"] == sha256(ROOT / "outputs/phase3/report/summary.json")
    for path, digest in plan["source_sha256"].items():
        historical_source = subprocess.check_output(["git", "show", f"{plan['code_commit']}:{path}"], cwd=ROOT)
        assert hashlib.sha256(historical_source).hexdigest() == digest
    for split in ("dev", "test"):
        oracle = json.loads((ROOT / f"outputs/phase3/oracle/{split}/summary.json").read_text())
        assert oracle["successes"] == oracle["total"]
    xml = ROOT / "outputs/phase3/pytest_final.xml"
    suite = ET.parse(xml).getroot()
    tests = sum(int(s.attrib["tests"]) for s in suite.iter("testsuite"))
    failures = sum(int(s.attrib.get("failures",0))+int(s.attrib.get("errors",0)) for s in suite.iter("testsuite"))
    assert tests >= 90 and failures == 0
    result = dict(historical_phase2_artifacts_unchanged=len(old["historical_sha256"]),
                  registered_code_commit=plan["code_commit"], episodes=40,
                  paired_initial_payloads_identical=True, all_live_asks_freeze_physics=True,
                  planner_prompts_and_parameters_identical=True, private_fields_absent_from_inference=True,
                  gate_precedes_planner=True, noask_gate_calls=0, test_api_episodes=0,
                  authenticated_requests=report["session"]["attempts"], pytest_tests=tests,
                  frozen_test_config_sha256=manifest["config_sha256"], gifs=gifs, episodes_evidence=rows)
    (ROOT / "outputs/phase3/evidence.json").write_text(json.dumps(config.sanitize(result),indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "episodes_evidence"}, indent=2))


if __name__ == "__main__":
    verify()
