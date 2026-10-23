from dataclasses import replace

import pytest

from when2ask.accounting import BudgetExceeded, SessionLedger
from when2ask.agents import GateResult
from when2ask.api import SchemaError
from when2ask.config import Config
from when2ask.diverse_world import DiverseEnvironment, DiverseSkills
from when2ask.research_runner import run_sample
from when2ask.study_agents import ACTION_PROMPT, QUESTION_PROMPT, StudyJevGate, StudyPlanner, components
from when2ask.study_data import load_study
from when2ask.study_evaluator import evaluate_study, expected_targets
from when2ask.study_protocol import StudyAction, StudyQuestion, observe


def test_phase3_session_has_hard_global_limits_and_keeps_old_policy(tmp_path):
    session = SessionLedger(tmp_path / "new", 999, 999, policy="phase3_dev")
    for i in range(600):
        assert session.reserve("deepseek") == i + 1
    with pytest.raises(BudgetExceeded):
        session.reserve("jev")
    for i in range(40):
        session.start_episode(str(i))
    with pytest.raises(BudgetExceeded):
        session.start_episode("41")
    assert SessionLedger(tmp_path / "old", 999, 999).snapshot()["max_attempts"] == 200
    assert session.snapshot()["max_episodes"] == 40
    with pytest.raises(ValueError):
        SessionLedger(tmp_path / "new").snapshot()


def test_study_methods_share_exact_planner_and_prompts():
    client = object()
    for method in ("llm_noask", "llm_gate", "jev_gate"):
        gate, planner = components(method, client, object(), .5)
        assert type(planner) is StudyPlanner and planner.client is client
        if method == "llm_noask":
            assert gate is None


@pytest.mark.parametrize("threshold,decision", [(.3, "ASK"), (.5, "ASK"), (.7, "CONTINUE")])
def test_study_jev_uses_direct_probability_threshold(threshold, decision):
    class Client:
        def noul(self, *args):
            return .5
    sample = load_study("dev")[0]
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        assert StudyJevGate(Client(), threshold).decide(observe(env, sample.u0, [])).decision == decision


def test_study_runner_gate_precedes_planner_and_ask_freezes_world(tmp_path):
    sample = load_study("dev")[19]
    calls = []
    class Gate:
        def decide(self, state):
            calls.append("gate")
            return GateResult("ASK" if not state.history else "CONTINUE")
    class Planner:
        def generate_question(self, state):
            calls.append("question")
            return StudyQuestion.parse(dict(type="all_preferences", text="All choices?", requests=[]), state)
        def generate_action(self, state):
            calls.append("action")
            return StudyAction("DONE")
    ep = run_sample(sample, "llm_gate", tmp_path, test_components=(Gate(), Planner()), quiet=True)
    assert calls == ["gate", "question", "gate", "action"]
    assert ep["diagnostics"]["clarification_burden"] == 3
    assert ep["ask_checks"][0]["state_unchanged"]
    assert ep["evaluation"]["task_success"] is False
    assert ep["evidence_kind"].startswith("offline_test_double")


def test_study_test_partition_rejects_live_before_any_request(tmp_path):
    with pytest.raises(ValueError, match="live Dev"):
        run_sample(load_study("test")[0], "jev_gate", tmp_path, live=True)
    assert not list(tmp_path.iterdir())


def test_multi_container_scoring_detects_wrong_target_then_real_repair():
    sample = load_study("dev")[16]  # independent, all choices public
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        skills = DiverseSkills(env)
        cup, block = sample.theta_star["cup_choice"], sample.theta_star["block_choice"]
        targets = expected_targets(sample, env)
        actions = [skills.pick_place(cup, targets["block"]).to_dict(),
                   skills.pick_place(block, targets["block"]).to_dict()]
        wrong = evaluate_study(env, sample, clarification_burden=0, actions=actions, termination="done")
        assert not wrong["task_success"] and not wrong["conditions"]["correct_cup_in_selected_container"]
        actions += [skills.pick_place(cup, "table", "on").to_dict(), skills.pick_place(cup, targets["cup"]).to_dict()]
        repaired = evaluate_study(env, sample, clarification_burden=0, actions=actions, termination="robot_action_limit")
        assert repaired["task_success"] and repaired["termination_reason"] == "robot_action_limit"


def test_multi_container_dag_rejects_early_block_and_accepts_real_repair():
    sample = load_study("dev")[17]  # cup_first
    assert sample.dag["order"] == "cup_first"
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        skills, targets = DiverseSkills(env), expected_targets(sample, env)
        cup, block = sample.theta_star["cup_choice"], sample.theta_star["block_choice"]
        actions = [skills.pick_place(block, targets["block"]).to_dict(), skills.pick_place(cup, targets["cup"]).to_dict()]
        wrong = evaluate_study(env, sample, clarification_burden=0, actions=actions, termination="done")
        assert wrong["conditions"]["correct_block_in_other_container"]
        assert not wrong["conditions"]["declared_dag_order"]
        actions += [skills.pick_place(block, "table", "on").to_dict(), skills.pick_place(block, targets["block"]).to_dict()]
        assert evaluate_study(env, sample, clarification_burden=0, actions=actions, termination="done")["task_success"]


def test_multi_action_schema_cannot_pack_containers_or_cover_without_lids():
    sample = load_study("dev")[16]
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        state = observe(env, sample.u0, [])
        target = env.container_ids[0]
        with pytest.raises(SchemaError):
            StudyAction.parse(dict(kind="pick_place", object_id=target, target_id=target), state)
        with pytest.raises(SchemaError):
            StudyAction.parse(dict(kind="cover", object_id=sample.theta_star["cup_choice"], target_id=target), state)
