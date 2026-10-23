"""Inspect actual episode/GIF files and persist concise local acceptance evidence."""
import hashlib
import importlib.metadata
import json
import platform
import xml.etree.ElementTree as ET
from pathlib import Path

import pybullet as p
from PIL import Image, ImageChops


def main():
    root = Path(__file__).resolve().parents[1]
    reports = {}
    for mode in ("ask", "noask"):
        out = root / "outputs" / f"{mode}_demo"
        episode = json.loads((out / "episode.json").read_text())
        assert episode["error"] is None
        score, recording = episode["evaluation"], episode["recording"]
        assert score["execution_termination"] == "done"
        assert score["successful_action_count"] == 3
        assert score["task_success"] == all(score["conditions"].values())
        assert episode["physics"]["connection_mode"] == "DIRECT"
        assert all(c["state_unchanged"] and c["before_step"] == c["after_step"]
                   for c in episode["ask_checks"])
        assert any(t["held_object"] is not None for t in episode["trajectory"])
        assert len(recording["frames"]) == recording["frame_count"]
        steps = [f["simulation_step"] for f in recording["frames"]]
        assert steps == sorted(steps)
        grasps = [e for e in episode["execution_log"] if e["kind"] == "grasp"]
        assert len(grasps) == 3
        assert all(g["grip_error_m"] <= .025 and g["closest_hand_distance_m"] <= .04
                   for g in grasps)
        with Image.open(out / "scene.png") as im:
            assert im.width >= 640 and im.height >= 480
            screenshot_size = list(im.size)
        gif_path = out / "demo.gif"
        with Image.open(gif_path) as gif:
            assert gif.n_frames > 100
            assert gif.n_frames == recording["encoded_frame_count"]
            initial = gif.convert("RGB").crop((0, 36, gif.width, gif.height))
            gif.seek(gif.n_frames // 2)
            middle = gif.convert("RGB").crop((0, 36, gif.width, gif.height))
            assert ImageChops.difference(initial, middle).getbbox() is not None
            duration_ms = 0
            for index in range(gif.n_frames):
                gif.seek(index)
                duration_ms += gif.info.get("duration", 0)
            encoded_frames = gif.n_frames
        reports[mode] = dict(task_success=score["task_success"],
                             successful_actions=score["successful_action_count"],
                             clarification_burden=score["clarification_burden"],
                             steps=score["simulation_steps"], screenshot_size=screenshot_size,
                             gif_frames=encoded_frames, gif_duration_ms=duration_ms,
                             gif_bytes=gif_path.stat().st_size,
                             gif_sha256=hashlib.sha256(gif_path.read_bytes()).hexdigest())
    gui_reports = {}
    for mode in ("ask", "noask"):
        path = root / "outputs" / "gui_checks" / mode / "episode.json"
        if path.exists():
            episode = json.loads(path.read_text())
            assert episode["physics"]["connection_mode"] == "GUI"
            assert episode["evaluation"]["execution_termination"] == "done"
            assert episode["evaluation"]["successful_action_count"] == 3
            viewport = episode["physics"]["gui_viewport"]
            assert viewport["width"] > 0 and viewport["height"] > 0
            gui_reports[mode] = dict(task_success=episode["evaluation"]["task_success"],
                                     viewport=viewport, physical_actions=3)
    pytest_file = root / "outputs/verification/pytest.xml"
    suites = list(ET.parse(pytest_file).getroot().iter("testsuite"))
    test_counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites)
                   for k in ("tests", "errors", "failures", "skipped")}
    assert test_counts["errors"] == test_counts["failures"] == test_counts["skipped"] == 0
    environment = dict(python=platform.python_version(), machine=platform.machine(),
                        macos=platform.mac_ver()[0], bullet_api_version=p.getAPIVersion(),
                        packages={name: importlib.metadata.version(name)
                                  for name in ("pybullet", "numpy", "pillow", "pytest")})
    verification = root / "outputs/verification"
    (verification / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
    report = dict(artifacts_valid=True, demos=reports, gui=gui_reports, pytest=test_counts)
    (verification / "artifact_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
