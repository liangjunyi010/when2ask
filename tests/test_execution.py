import json

import numpy as np
import pybullet as p
import pytest

from when2ask.environment import Environment
from when2ask.runner import run_episode
from when2ask.skills import RobotSkills, SkillFailure
from when2ask.task import PrivateTaskSpec


def test_one_block_really_follows_motor_driven_arm_and_is_released():
    with Environment(minimal=True) as env:
        skills = RobotSkills(env)
        samples = []

        def sample():
            if env.held_object and env.step_count % 40 == 0:
                samples.append((np.array(env.ee_pose()[0]), np.array(env.body_pose("green_block")[0])))

        env.frame_callback = sample
        before = np.array(env.body_pose("green_block")[0])
        result = skills.pick_place("green_block", "table", "on")
        assert result.success, result.reason
        assert np.linalg.norm(np.array(env.body_pose("green_block")[0]) - before) > .2
        assert len(samples) > 20
        held_path = np.array([obj for _, obj in samples])
        offsets = np.array([obj - ee for ee, obj in samples])
        assert np.ptp(held_path[:, 2]) > .2
        assert np.max(np.ptp(offsets, axis=0)) < .01
        assert env.released() and p.getNumConstraints(physicsClientId=env.client) == 0
        grasp = next(e for e in env.events if e["kind"] == "grasp")
        assert grasp["grip_error_m"] < .025
        assert grasp["closest_hand_distance_m"] < .04


def test_full_ask_episode_and_freeze(ask_episode):
    score = ask_episode["evaluation"]
    assert score["task_success"]
    assert all(score["conditions"].values())
    assert score["clarification_burden"] == 2
    assert score["action_count"] == score["successful_action_count"] == 3
    assert [d["kind"] for d in ask_episode["decisions"]] == [
        "CONTINUE", "ASK", "CONTINUE", "CONTINUE", "DONE"]
    check, = ask_episode["ask_checks"]
    assert check["before_step"] == check["after_step"]
    assert check["state_unchanged"] and check["burden"] == 2
    assert len(ask_episode["trajectory"]) > 50
    assert ask_episode["error"] is None


def test_noask_executes_real_choices_and_gets_physical_score(noask_episode):
    score = noask_episode["evaluation"]
    assert score["execution_termination"] == "done"
    assert score["successful_action_count"] == 3
    assert score["clarification_burden"] == 0
    assert not any(d["kind"] == "ASK" for d in noask_episode["decisions"])
    assert [r["object_id"] for r in noask_episode["actions"]] == [
        "blue_cup", "yellow_block", "black_lid"]
    assert score["conditions"]["correct_cup_inside"]
    assert score["conditions"]["correct_lid_covers"]
    assert not score["conditions"]["correct_block_inside"]
    assert not score["task_success"]


def test_noask_can_succeed_when_defaults_match_hidden_intent(matched_noask_episode):
    assert matched_noask_episode["evaluation"]["task_success"]
    assert matched_noask_episode["evaluation"]["clarification_burden"] == 0


def test_ask_follows_alternate_unpublished_block_and_lid(tmp_path):
    episode = run_episode("ask", seed=3, output_dir=tmp_path, quiet=True,
                           private_spec=PrivateTaskSpec(block_choice="yellow_block", lid_choice="white_lid"))
    assert episode["evaluation"]["task_success"], episode["evaluation"]
    assert [a["object_id"] for a in episode["actions"]] == ["blue_cup", "yellow_block", "white_lid"]


def test_far_grasp_cannot_create_constraint(env):
    skills = RobotSkills(env)
    with pytest.raises(SkillFailure, match="grasp_out_of_range"):
        skills._grasp("green_block", np.array(env.body_pose("green_block")[0]))
    assert env.held_object is None
    assert p.getNumConstraints(physicsClientId=env.client) == 0


def test_invalid_object_and_bounded_failure(env):
    skills = RobotSkills(env)
    result = skills.pick_place("missing_object", "box")
    assert not result.success and result.reason == "unknown_object"
    assert result.start_step == result.end_step
    skills.MAX_SKILL_STEPS = 5
    result = skills.pick_place("green_block", "box")
    assert not result.success and result.reason == "skill_step_limit"
    assert result.end_step - result.start_step <= 5
    assert env.released()


def test_failed_episode_still_saves_score_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(RobotSkills, "MAX_SKILL_STEPS", 5)
    episode = run_episode("ask", output_dir=tmp_path, quiet=True)
    assert not episode["evaluation"]["task_success"]
    assert episode["evaluation"]["termination_reason"] == "skill_failed:skill_step_limit"
    saved = json.loads((tmp_path / "episode.json").read_text())
    assert len(saved["actions"]) == 1 and not saved["actions"][0]["success"]
    assert (tmp_path / "evaluation.json").exists()
    assert (tmp_path / "final.png").exists()


def test_artifact_failure_preserves_true_physical_score(tmp_path, monkeypatch):
    original = Environment.save_scene

    def fail_final_image(self, path):
        if path.name == "final.png":
            raise OSError("injected artifact write failure")
        return original(self, path)

    monkeypatch.setattr(Environment, "save_scene", fail_final_image)
    episode = run_episode("ask", output_dir=tmp_path, quiet=True)
    assert episode["evaluation"]["task_success"]
    assert "injected artifact write failure" in episode["artifact_error"]
    assert episode["error"] is not None
    assert json.loads((tmp_path / "evaluation.json").read_text())["task_success"]
