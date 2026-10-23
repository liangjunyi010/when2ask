import json
import subprocess
from pathlib import Path

import pytest

from when2ask.config import Config, ROOT
from when2ask.doctor import doctor
from when2ask.reporting import known_sum, report


def test_offline_doctor_does_not_call_live_http_and_never_prints_key(capsys):
    result = doctor(live=False)
    output = capsys.readouterr().out
    cfg = Config.load()
    assert result["live"] is False
    for secret in (cfg.deepseek_key, cfg.typesafe_key):
        if secret:
            assert secret not in output


def test_unknown_usage_and_offline_results_are_not_fake_live_measurements(tmp_path):
    assert known_sum([None, None]) is None
    assert known_sum([None, 7, 2]) == 9
    (tmp_path / "episode.json").write_text(json.dumps({"evidence_kind": "offline_test_double_with_real_physics"}))
    with pytest.raises(ValueError, match="No real-model"):
        report(tmp_path)


def test_report_refuses_to_pool_different_prompt_versions(tmp_path):
    for index in (1, 2):
        directory = tmp_path / str(index)
        directory.mkdir()
        (directory / "episode.json").write_text(json.dumps({
            "evidence_kind": "live_model_and_physics", "planner_configuration": {},
            "prompt_hashes": {"action": str(index)}}))
    with pytest.raises(ValueError, match="reported separately"):
        report(tmp_path)


def test_local_credentials_are_private_and_absent_from_tracked_files():
    env = ROOT / ".env"
    if not env.exists():
        pytest.skip("Clone has no local credentials; no secrets are provisioned by tests")
    assert env.stat().st_mode & 0o777 == 0o600
    assert subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0
    cfg = Config.load()
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, names):
        raw = (ROOT / name).read_bytes()
        for secret in (cfg.deepseek_key, cfg.typesafe_key):
            assert not secret or secret.encode() not in raw, f"Secret in tracked file: {name}"
