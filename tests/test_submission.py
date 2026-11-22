import json

import pytest

from when2ask import submission
from when2ask.metrics_dev_report import audit, report


def test_saved_report_and_audit_leave_evidence_unchanged(tmp_path):
    before = submission.verify_archive()
    summary = report(source=submission.ARCHIVE, destination=tmp_path, archived=True)
    checks = audit(source=submission.ARCHIVE, destination=tmp_path, archived=True)
    assert checks['all_108_paired'] and checks['authenticated_attempts'] == 724
    assert {r['method']: r['successes'] for r in summary['methods']} == {
        'llm_noask': 21, 'llm_gate': 27, 'jev_gate': 26, 'llm_unified': 26}
    assert submission.verify_archive() == before
    assert (tmp_path / 'evidence_validation.json').is_file()


def test_new_run_cannot_write_into_saved_evidence():
    with pytest.raises(ValueError, match='outside the saved evaluation'):
        submission.new_output(submission.ARCHIVE / 'new')


def test_live_run_requires_flag_before_creating_output(tmp_path):
    out = tmp_path / 'run'
    with pytest.raises(SystemExit):
        submission.main(['run', '--output', str(out), '--pricing', 'missing.json'])
    assert not out.exists()


def test_checksum_verification_detects_changed_evidence(tmp_path, monkeypatch):
    (tmp_path / 'result').mkdir()
    (tmp_path / 'result/checksums.json').write_text(json.dumps({
        'files': {'record.json': 'invalid'}, 'original_commit': 'test'}))
    (tmp_path / 'record.json').write_text('{}')
    monkeypatch.setattr(submission, 'ROOT', tmp_path)
    with pytest.raises(ValueError, match='Saved evidence changed'):
        submission.verify_archive()
