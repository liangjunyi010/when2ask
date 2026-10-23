from dataclasses import fields

import pytest

from when2ask.scripted_agent import ScriptedAgent
from when2ask.task import INSTRUCTION, PrivateTaskSpec, PublicState
from when2ask.user_simulator import UserSimulator


def test_public_state_has_only_permitted_inputs(env):
    assert {f.name for f in fields(PublicState)} == {"instruction", "observation", "history"}
    state = PublicState.build(env.snapshot(), [])
    assert state.instruction == INSTRUCTION
    assert state.disclosed_preferences() == {"cup_choice": "blue_cup"}
    assert not any(k in state.observation for k in ("private_spec", "correct_answers", "task_success"))
    state.observation["objects"].clear()
    assert len(env.objects) == 7  # A policy receives a copy, never the live environment.


def test_unasked_preferences_do_not_change_observation_or_noask_policy(
        noask_episode, matched_noask_episode):
    assert noask_episode["initial_observation"] == matched_noask_episode["initial_observation"]
    assert noask_episode["decisions"] == matched_noask_episode["decisions"]
    assert noask_episode["actions"] == matched_noask_episode["actions"]
    assert not noask_episode["evaluation"]["task_success"]
    assert matched_noask_episode["evaluation"]["task_success"]


def test_simulator_discloses_only_requested_slots():
    user = UserSimulator(PrivateTaskSpec())
    assert user.answer(["block_choice"]) == {"block_choice": "green_block"}
    assert user.answer(["lid_choice"]) == {"lid_choice": "black_lid"}
    assert user.answer(["cup_choice"]) == {"cup_choice": "blue_cup"}
    assert user.answer(["block_choice", "lid_choice"]) == {
        "block_choice": "green_block", "lid_choice": "black_lid"}


@pytest.mark.parametrize("slots", [[], ["all_preferences"], ["block_choice", "private_spec"]])
def test_simulator_rejects_unrecognized_requests(slots):
    with pytest.raises(ValueError):
        UserSimulator(PrivateTaskSpec()).answer(slots)


def test_policy_is_public_and_deterministic(env):
    state = PublicState.build(env.snapshot(), [])
    for mode in ("scripted_ask", "scripted_noask"):
        policy = ScriptedAgent(mode)
        assert vars(policy) == {"mode": mode}
        assert policy.decide(state) == policy.decide(state)
        assert policy.decide(state).object_id == "blue_cup"
