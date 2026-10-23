import copy
import json
from dataclasses import asdict

import pytest

from when2ask.benchmark import Sample, check_groups, find_sample, generate, load_samples
from when2ask.environment import Environment
from when2ask.protocol import Question, observe, payload_hash, public_payload
from when2ask.user_simulator import PreferenceResolver


def test_generation_reproducibility_disclosure_coverage_and_group_isolation(tmp_path):
    validation = generate("validation", 5, 42, tmp_path)
    pilot = generate("pilot", 20, 42, tmp_path)
    assert [asdict(s) for s in pilot] == [asdict(s) for s in generate("pilot", 20, 42, tmp_path)]
    manifest = json.loads((tmp_path / "data/generation_manifest.json").read_text())
    assert manifest["pilot"]["api_attempts"] == 0
    assert manifest["pilot"]["input_tokens"] is None
    assert manifest["pilot"]["wall_time_ms"] >= 0
    assert {3 - len(s.initial_disclosed_slots) for s in pilot} == {0, 1, 2, 3}
    assert check_groups(validation + pilot, tmp_path)["groups"] == 8
    groups = {p: {s.group_id for s in validation + pilot if s.partition == p}
              for p in ("validation", "dev", "test")}
    assert not groups["dev"] & groups["test"]
    assert not groups["validation"] & (groups["dev"] | groups["test"])
    assert not {s.scene_seed for s in validation} & {s.scene_seed for s in pilot}
    for role in ("cup", "block", "lid"):
        slot = role + "_choice"
        ranks = {s.slots[slot]["candidate_ids"].index(s.theta_star[slot]) for s in pilot}
        assert ranks == {0, 1}


def test_changing_private_truth_preserves_public_payload():
    sample = find_sample("pilot_003")
    different = copy.deepcopy(asdict(sample))
    for slot, registry in sample.slots.items():
        different["theta_star"][slot] = next(v for v in registry["candidate_ids"] if v != sample.theta_star[slot])
    changed = Sample(**different).validate()
    with Environment(sample.scene_seed, scene_spec=sample.scene()) as a, \
         Environment(changed.scene_seed, scene_spec=changed.scene()) as b:
        first = public_payload(observe(a, sample.u0, []))
        second = public_payload(observe(b, changed.u0, []))
        assert first == second and payload_hash(first) == payload_hash(second)
        text = json.dumps(first)
        for key in ("theta_star", "slots", "dag", "private_spec", "task_success", "oracle"):
            assert '"' + key + '"' not in text
        assert '"cup_choice"' not in text


class OnlyRequested(dict):
    def __getitem__(self, key):
        assert key == "block_choice", "Simulator accessed an unasked hidden preference"
        return super().__getitem__(key)


def test_resolver_accesses_only_questioned_preference_and_freezes_world():
    sample = find_sample("pilot_003")
    with Environment(sample.scene_seed, scene_spec=sample.scene()) as env:
        state = observe(env, sample.u0, [])
        candidates = sample.slots["block_choice"]["candidate_ids"]
        question = Question.parse(dict(type="select", text="Which block?", requests=[
            dict(role="block", candidate_ids=candidates), dict(role="block", candidate_ids=candidates)]), state)
        resolver = PreferenceResolver(sample.slots, OnlyRequested(sample.theta_star))
        before = env.snapshot()
        answer, burden = resolver.answer(question)
        assert answer == {"choices": {"block": sample.theta_star["block_choice"]}}
        assert burden == 1
        assert resolver.answer(question)[1] == 1  # A repeated question is charged again.
        assert env.snapshot() == before
        confirm = Question.parse(dict(type="confirm", text="This block?", requests=[
            dict(role="block", candidate_id=candidates[0])]), state)
        response, count = resolver.answer(confirm)
        assert count == 1 and set(response) == {"confirmations"}
        assert "choices" not in response


def test_all_preferences_explicitly_requests_three_slots():
    sample = find_sample("pilot_003")
    question = Question("all_preferences", "Which cup, block and lid?", ())
    response, burden = PreferenceResolver(sample.slots, sample.theta_star).answer(question)
    assert burden == 3 and set(response["choices"]) == {"cup", "block", "lid"}


def test_question_cannot_smuggle_private_slots_or_unknown_candidates(env):
    from when2ask.api import SchemaError
    state = observe(env, "Pack one cup and one block then cover.", [])
    for request in ([{"role": "block_choice", "candidate_ids": []}],
                    [{"role": "lid", "candidate_ids": ["not-visible", "black_lid"]}]):
        with pytest.raises(SchemaError):
            Question.parse(dict(type="select", text="Question", requests=request), state)
