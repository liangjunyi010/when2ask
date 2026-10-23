"""Read-only acceptance checks for recorded real API/physics evidence; no network."""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from when2ask.benchmark import check_groups, load_samples
from when2ask.config import Config, ROOT


def main():
    base = ROOT / "outputs/phase2_live"
    session = json.loads((base / "session_budget.json").read_text())
    assert session["attempts"] <= 200 and session["episodes"] <= 12
    attempts = []
    for path in base.rglob("*.jsonl"):
        for line in path.read_text().splitlines():
            value = json.loads(line)
            if "session_attempt" in value:
                attempts.append(value)
    numbers = [a["session_attempt"] for a in attempts]
    assert len(numbers) == len(set(numbers)) == session["attempts"]
    assert sorted(numbers) == list(range(1, session["attempts"] + 1))
    episodes = []
    recordings = []
    forbidden = {"theta_star", "slots", "dag", "private_spec", "task_success", "expected_objects"}

    def check_public(value):
        if isinstance(value, dict):
            assert not set(value) & forbidden
            for child in value.values():
                check_public(child)
        elif isinstance(value, list):
            for child in value:
                check_public(child)

    for path in base.rglob("episode.json"):
        episode = json.loads(path.read_text())
        assert episode["evidence_kind"] == "live_model_and_physics"
        assert episode["cost"]["api_attempts"] <= 64 and len(episode["turns"]) <= 20
        assert episode["evaluation"]["task_success"] == all(episode["evaluation"]["conditions"].values())
        assert len(episode["actions"]) <= 12
        assert episode["diagnostics"]["clarification_burden"] <= 12
        for turn in episode["turns"]:
            check_public(turn["public_payload"])
        for check in episode["ask_checks"]:
            assert check["state_unchanged"] and check["before_step"] == check["after_step"]
        if episode["method"] == "llm_noask":
            assert all(a["stage"] == "action" and a["backend"] == "deepseek" for a in episode["api_attempts"])
            assert not episode["ask_checks"]
        if "recording" in episode:
            gif_path = path.with_name("demo.gif")
            with Image.open(gif_path) as gif:
                assert gif.n_frames == episode["recording"]["encoded_frame_count"] > 100
                recordings.append(dict(path=str(gif_path.relative_to(ROOT)), frames=gif.n_frames,
                                       bytes=gif_path.stat().st_size,
                                       sha256=hashlib.sha256(gif_path.read_bytes()).hexdigest()))
        episodes.append(episode)
    assert len(episodes) == session["episodes"] == 12
    summary = json.loads((base / "paired_v2/summary.json").read_text())
    assert summary["episodes"] == 9
    assert all(all(v for k, v in check.items() if k.startswith("same_") or k == "all_three_methods")
               for check in summary["paired_checks"])
    oracle = {}
    for split in ("validation", "pilot"):
        report = json.loads((ROOT / "outputs/phase2/oracle" / split / "summary.json").read_text())
        assert report["successes"] == report["total"]
        oracle[split] = {k: report[k] for k in ("successes", "total")}
    groups = check_groups(load_samples("validation") + load_samples("pilot"))
    suites = ET.parse(ROOT / "outputs/phase2/pytest.xml").getroot().iter("testsuite")
    counts = {"tests": 0, "errors": 0, "failures": 0, "skipped": 0}
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.attrib.get(key, 0))
    assert counts["errors"] == counts["failures"] == counts["skipped"] == 0
    report = dict(verified=True, online_api_attempts=len(attempts), online_episodes=len(episodes),
                  diagnostic_v1_episodes=3, final_v2_episodes=9, oracle=oracle, groups=groups,
                  pytest=counts, models={backend: sorted({a["returned_model"] for a in attempts
                      if a["backend"] == backend and a.get("returned_model")}) for backend in ("deepseek", "jev")},
                  non_ok_attempts=sum(a["status"] != "ok" for a in attempts),
                  unknown_inference_usage_attempts=sum(
                      a["stage"] != "models" and (a["input_tokens"] is None or a["output_tokens"] is None)
                      for a in attempts), recordings=recordings,
                  note="No paid requests made by this verifier. v1 and v2 are reported separately.")
    report = Config.load().sanitize(report)
    (ROOT / "outputs/phase2/evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
