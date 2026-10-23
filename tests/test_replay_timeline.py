import copy
import json

from when2ask.config import ROOT
from when2ask.replay import make_frames

SOURCE=ROOT/"outputs/phase2_live/paired_v2/validation_002/jev_gate/episode.json"


def episode():
    return json.loads(SOURCE.read_text())


def test_master_timeline_preserves_all_original_frames_and_durations():
    original=episode();frames=make_frames(original)
    assert len(frames)==447 and frames[-1]["end_ms"]==49200
    assert frames[0]["start_ms"]==0
    for i,f in enumerate(frames):
        assert f["simulation_step"]==original["recording"]["frames"][i]["simulation_step"]
        assert f["duration_ms"]==original["recording"]["frames"][i]["duration_ms"]
        assert f["end_ms"]==f["start_ms"]+f["duration_ms"]
        if i:assert f["start_ms"]==frames[i-1]["end_ms"]


def test_frozen_ask_and_user_have_distinct_ordered_display_intervals():
    frames=make_frames(episode());ask,user=frames[143:145]
    assert ask["simulation_step"]==user["simulation_step"]==3663
    assert ask["active_flow_node"]=="question_planner" and user["active_flow_node"]=="user_simulator"
    assert ask["user_answer"] is None and user["user_answer"]["choices"]
    assert ask["end_ms"]==user["start_ms"]
    assert "block" not in ask["public_preferences"] and user["public_preferences"]["block"]=="green block"


def test_execution_is_bound_to_real_skill_interval_and_logged_phase():
    original=episode();frames=make_frames(original)
    for f in frames:
        if f["stage"]!="execution":continue
        assert f["active_flow_node"]=="execution" and f["gate"]["decision"]=="CONTINUE"
        assert f["physical_interval"]["start_step"]<=f["simulation_step"]<=f["physical_interval"]["end_step"]
        assert f["physical_phase"] in ("approach","grasp","lift","transport","lower","release","settle")
        assert f["action_outcome"] is None  # Every recorded motor frame precedes skill completion.
    block=next(f for f in frames if f["round"]==2)
    assert block["gate"]["p_ask"]==.09 and block["question"] is None


def test_future_answer_and_evaluator_truth_do_not_appear_early():
    frames=make_frames(episode())
    assert all(f["user_answer"] is None for f in frames[:144])
    assert all(f["evaluation"] is None for f in frames[:-1])
    assert frames[-1]["active_flow_node"]=="evaluator" and frames[-1]["evaluation"]["task_success"]
    assert frames[-1]["gate"]["p_ask"]==.03


def test_llm_gate_retains_null_probability_and_real_redundant_question():
    source=ROOT/"outputs/phase3_live/dev/v3_dev_016__llm_gate/episode.json"
    frames=make_frames(json.loads(source.read_text()))
    assert len(frames)==315 and all(f["gate"]["p_ask"] is None for f in frames)
    assert frames[1]["question"]["requests"][0]["role"]=="cup_destination"


def test_unknown_recorder_label_fails_instead_of_fabricating_a_stage():
    import pytest
    broken=episode();broken["recording"]["frames"][1]["label"]="imaginary movement"
    with pytest.raises(ValueError,match="Unknown recorder label"):
        make_frames(broken)
