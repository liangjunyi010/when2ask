import json

from when2ask.config import ROOT
from when2ask.study_cli import stable_dev_report
from when2ask.study_data import sha256


def test_offline_report_regeneration_preserves_frozen_hash():
    path = ROOT / "outputs/phase3/report/summary.json"
    previous = path.read_bytes()
    result = stable_dev_report()
    assert result == json.loads(previous)
    assert path.read_bytes() == previous
    frozen = json.loads((ROOT / "configs/frozen_test.yaml").read_text())
    assert frozen["dev_report_sha256"] == sha256(path)
