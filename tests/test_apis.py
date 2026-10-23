import json
from dataclasses import replace

import pytest

from when2ask.accounting import Audit, BackendBlocked, BudgetExceeded, SessionLedger
from when2ask.agents import GateResult, JevGate, components
from when2ask.api import APIError, DeepSeekClient, JevClient, SchemaError
from when2ask.config import Config


def config(**changes):
    return replace(Config(deepseek_key="synthetic-sensitive-value", typesafe_key="synthetic-other-value"), **changes)


def completion(content='{"ok":true}', usage=True):
    value = {"model": "returned-test-model", "choices": [{"message": {"content": content}}]}
    if usage:
        value["usage"] = {"prompt_tokens": 17, "completion_tokens": 6}
    return value


def transport_sequence(values, observed):
    def send(url, headers, payload, timeout):
        observed.append((url, payload, timeout))
        item = values.pop(0)
        if isinstance(item, Exception):
            raise item
        return item[0], json.dumps(item[1])
    return send


def test_deepseek_json_model_usage_and_non_thinking_config(tmp_path):
    cfg, observed = config(), []
    audit = Audit("offline_unit", cfg, path=tmp_path / "attempts.jsonl")
    client = DeepSeekClient(cfg, audit, transport_sequence([(200, completion())], observed))
    assert client.json("Return JSON", {}, stage="action") == {"ok": True}
    record, = audit.records
    assert record["returned_model"] == "returned-test-model"
    assert record["input_tokens"] == 17 and record["output_tokens"] == 6
    assert record["latency_ms"] >= 0 and record["status"] == "ok"
    assert observed[0][1]["thinking"] == {"type": "disabled"}
    assert observed[0][1]["response_format"] == {"type": "json_object"}
    assert cfg.deepseek_key not in audit.path.read_text()


def test_timeout_retry_and_exact_attempt_budget(tmp_path):
    cfg, observed = config(), []
    ledger = SessionLedger(tmp_path / "ledger", max_attempts=2)
    audit = Audit("offline_unit", cfg, ledger)
    client = DeepSeekClient(cfg, audit, transport_sequence(
        [TimeoutError("timeout"), (200, completion())], observed), sleep=lambda _: None)
    client.json("JSON", {}, stage="gate")
    assert len(observed) == ledger.snapshot()["attempts"] == 2
    assert audit.summary()["retries"] == 1
    assert audit.records[0]["input_tokens"] is None
    assert audit.summary()["deepseek"]["unknown_input_tokens_attempts"] == 1
    with pytest.raises(BudgetExceeded):
        client.json("JSON", {}, stage="action")
    assert len(observed) == 2


@pytest.mark.parametrize("status", [429, 503])
def test_rate_limit_and_server_error_have_finite_logged_retry(status):
    cfg, observed = config(), []
    audit = Audit("offline_unit", cfg)
    client = DeepSeekClient(cfg, audit, transport_sequence(
        [(status, {"error": "temporary"}), (200, completion())], observed), sleep=lambda _: None)
    assert client.json("JSON", {}, stage="action") == {"ok": True}
    assert audit.summary()["api_errors"] == 1
    assert audit.summary()["retries"] == 1
    assert len(observed) == 2


def test_malformed_json_repair_is_logged_with_usage():
    cfg, observed = config(), []
    audit = Audit("offline_unit", cfg)
    client = DeepSeekClient(cfg, audit, transport_sequence([
        (200, completion("not JSON")), (200, completion())], observed), sleep=lambda _: None)
    assert client.json("JSON", {}, stage="question") == {"ok": True}
    assert audit.summary()["schema_errors"] == 1
    assert audit.summary()["deepseek"]["input_tokens"] == 34
    assert observed[1][1]["messages"][-1]["role"] == "user"
    assert all(r["stage"] == "question" for r in audit.records)


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {"content": "[]"}}]},
                                  {"model": "x", "usage": "invalid"}])
def test_malformed_deepseek_response_is_bounded(body):
    cfg, observed = config(max_retries=0), []
    audit = Audit("offline_unit", cfg)
    client = DeepSeekClient(cfg, audit, transport_sequence([(200, body)], observed))
    with pytest.raises(SchemaError):
        client.json("JSON", {}, stage="action")
    assert len(observed) == 1 and audit.records[0]["status"] == "schema_error"


@pytest.mark.parametrize("value", [-.1, 1.1, True, "0.5", None, float("nan")])
def test_jev_rejects_invalid_noul(value):
    with pytest.raises(SchemaError):
        JevClient.parse_noul({"model": "unit", "answers": {"needs_clarification": {"type": "noul", "noul": value}}})


@pytest.mark.parametrize("probability,expected", [(0, "CONTINUE"), (.49, "CONTINUE"), (.5, "ASK"), (.9, "ASK")])
def test_noul_probability_threshold_is_not_distance_from_half(probability, expected, env):
    from when2ask.protocol import observe
    cfg, observed = config(), []
    body = {"model": "jev-unit", "answers": {"needs_clarification": {"type": "noul", "noul": probability}},
            "usage": {"input_tokens": 12, "output_tokens": 3}}
    audit = Audit("offline_unit", cfg)
    client = JevClient(cfg, audit, transport_sequence([(200, body)], observed))
    result = JevGate(client, .5).decide(observe(env, "Pack one cup and block, then cover.", []))
    assert result.decision == expected and result.p_ask == probability
    assert audit.summary()["jev"]["input_tokens"] == 12


def test_missing_usage_stays_null_and_cannot_create_false_zero_cost():
    cfg, observed = config(), []
    audit = Audit("offline_unit", cfg)
    client = DeepSeekClient(cfg, audit, transport_sequence([(200, completion(usage=False))], observed))
    client.json("JSON", {}, stage="action")
    assert audit.summary()["deepseek"]["input_tokens"] is None
    assert audit.summary()["deepseek"]["unknown_input_tokens_attempts"] == 1
    assert audit.summary()["jev"]["input_tokens"] is None


def test_auth_error_blocks_backend_without_retry_and_redacts_echo(tmp_path):
    cfg, observed = config(), []
    ledger = SessionLedger(tmp_path / "session")
    audit = Audit("offline_unit", cfg, ledger, tmp_path / "attempts.jsonl")
    client = DeepSeekClient(cfg, audit, transport_sequence([(401, {"error": cfg.deepseek_key})], observed))
    with pytest.raises(APIError):
        client.json("JSON", {}, stage="action")
    with pytest.raises(BackendBlocked):
        client.json("JSON", {}, stage="action")
    assert len(observed) == 1
    assert cfg.deepseek_key not in audit.path.read_text()
    assert cfg.deepseek_key not in repr(cfg)


def test_three_consecutive_errors_stop_paid_backend(tmp_path):
    cfg, observed = config(max_retries=0), []
    ledger = SessionLedger(tmp_path)
    audit = Audit("offline_unit", cfg, ledger)
    client = JevClient(cfg, audit, transport_sequence([(503, {})] * 3, observed))
    for _ in range(3):
        with pytest.raises(APIError):
            client.noul({}, "Question?")
    with pytest.raises(BackendBlocked):
        client.noul({}, "Question?")
    assert len(observed) == 3


def test_ledger_is_single_json_and_persists_across_instances(tmp_path):
    ledger = SessionLedger(tmp_path, max_episodes=1)
    ledger.reserve("deepseek")
    ledger.outcome("deepseek", True)
    ledger.reserve("jev")
    ledger.start_episode("one")
    assert SessionLedger(tmp_path).snapshot()["attempts"] == 2
    assert json.loads(ledger.path.read_text())["episodes"] == 1
    with pytest.raises(BudgetExceeded):
        ledger.start_episode("two")


def test_audit_restart_keeps_old_attempt_and_unknown_reservation(tmp_path):
    path, cfg = tmp_path / "audit.jsonl", config()
    first = Audit("offline_unit", cfg, path=path, limit=1)
    first.reserve("deepseek")
    second = Audit("offline_unit", cfg, path=path, limit=1)
    assert second.records[0]["status"] == "reserved"
    with pytest.raises(BudgetExceeded):
        second.reserve("deepseek")


def test_gate_has_no_done_or_action_and_planner_config_is_shared():
    with pytest.raises(SchemaError):
        GateResult("DONE")
    sentinel = object()
    planners = [components(m, sentinel, sentinel, .5)[1] for m in ("llm_noask", "llm_gate", "jev_gate")]
    assert all(p.client is sentinel for p in planners)
