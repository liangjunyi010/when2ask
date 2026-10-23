from when2ask.accounting import Limits
from when2ask.agents import GateResult
from when2ask.benchmark import find_sample
from when2ask.protocol import Action, Question, disclosed_choices, role_candidates
from when2ask.research_runner import run_sample


class PublicPlannerDouble:
    """Offline contract fixture: reads only public instruction/answers and sensors."""
    def __init__(self, calls):
        self.calls = calls

    def generate_action(self, state):
        self.calls.append("action")
        known = disclosed_choices(state)
        relations = state.observation["spatial_relations"]
        for role in ("cup", "block"):
            if known[role] not in relations["inside_box"]:
                return Action("pick_place", known[role], "box")
        if known["lid"] not in relations["covering_box"]:
            return Action("cover", known["lid"], "box", "covers")
        return Action("DONE")

    def generate_question(self, state):
        self.calls.append("question")
        known = disclosed_choices(state)
        requests = [dict(role=role, candidate_ids=role_candidates(state, role))
                    for role in ("cup", "block", "lid") if role not in known]
        return (Question("select", "Which objects do you prefer?", tuple(requests)) if requests else
                Question("all_preferences", "Please repeat all preferences.", ()))


class GateDouble:
    def __init__(self, calls, decisions):
        self.calls, self.decisions = calls, iter(decisions)

    def decide(self, state):
        self.calls.append("gate")
        return GateResult(next(self.decisions, "CONTINUE"))


def test_noask_never_calls_gate_and_budget_can_end_in_true_success(tmp_path):
    calls = []
    result = run_sample(find_sample("pilot_000"), "llm_noask", tmp_path, quiet=True,
                        limits=Limits(max_robot_actions=3),
                        test_components=(None, PublicPlannerDouble(calls)))
    assert calls == ["action"] * 3
    assert result["termination_reason"] == "robot_action_limit"
    assert result["evaluation"]["task_success"]
    assert not result["evaluation"]["execution_completed"]
    assert result["cost"]["api_attempts"] == 0
    assert result["evidence_kind"] == "offline_test_double_with_real_physics"
    assert all(not t["gate"]["called"] for t in result["turns"])


def test_gate_always_precedes_planner_including_done(tmp_path):
    calls = []
    result = run_sample(find_sample("pilot_000"), "llm_gate", tmp_path, quiet=True,
                        test_components=(GateDouble(calls, []), PublicPlannerDouble(calls)))
    assert result["evaluation"]["task_success"]
    assert calls == ["gate", "action"] * 4
    assert result["turns"][-1]["action"]["kind"] == "DONE"


def test_ask_freeze_and_repeated_distinct_slot_burden(tmp_path):
    calls = []
    result = run_sample(find_sample("pilot_003"), "jev_gate", tmp_path, quiet=True,
                        limits=Limits(max_rounds=2),
                        test_components=(GateDouble(calls, ["ASK", "ASK"]), PublicPlannerDouble(calls)))
    assert calls == ["gate", "question", "gate", "question"]
    assert result["diagnostics"]["clarification_burden"] == 6
    assert result["diagnostics"]["repeated_slot_requests"] == 3
    assert result["diagnostics"]["redundant_slot_requests"] == 3
    assert all(c["before_step"] == c["after_step"] and c["state_unchanged"] for c in result["ask_checks"])
    assert result["initial_observation"] == result["final_observation"]


def test_slot_budget_is_checked_before_user_answer(tmp_path):
    calls = []
    result = run_sample(find_sample("pilot_003"), "jev_gate", tmp_path, quiet=True,
                        limits=Limits(max_slot_requests=1),
                        test_components=(GateDouble(calls, ["ASK"]), PublicPlannerDouble(calls)))
    assert result["termination_reason"] == "slot_request_limit"
    assert result["public_history"] == []
    assert result["diagnostics"]["clarification_burden"] == 0


def test_live_flag_is_required_and_cannot_be_mixed_with_test_double(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="explicit --live"):
        run_sample(find_sample("pilot_000"), "llm_noask", tmp_path)
    with pytest.raises(ValueError, match="may not use test doubles"):
        run_sample(find_sample("pilot_000"), "llm_noask", tmp_path, live=True,
                   test_components=(None, PublicPlannerDouble([])))
