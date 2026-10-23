import copy
import json
from dataclasses import asdict, replace

import pytest

from when2ask.benchmark import Sample, find_sample
from when2ask.config import ROOT
from when2ask.diverse_world import DiverseEnvironment
from when2ask.protocol import public_payload
from when2ask.study_data import StudySample, check_study, generate_study, load_study, read_sample, sha256
from when2ask.study_protocol import StudyQuestion, disclosed_choices, observe, role_candidates
from when2ask.user_simulator import PreferenceResolver


def test_v3_scene_groups_cover_both_templates_and_all_disclosures():
    dev, test = load_study("dev"), load_study("test")
    result = check_study(dev + test)
    assert (len(dev), len(test)) == (32, 128)
    assert result["distribution"]["dev"]["groups"] == 8
    assert result["distribution"]["test"]["groups"] == 16
    assert result["minimum_cross_split_container_distance_m"] > .025
    for samples in (dev, test):
        assert {3 - len(s.initial_disclosed_slots) for s in samples} == {0, 1, 2, 3}
        for template in {s.template_id for s in samples}:
            group = [s for s in samples if s.template_id == template]
            assert len({tuple(s.theta_star.values()) for s in group}) > 1
    assert not {s.group_id for s in dev} & {s.group_id for s in test}


def test_v3_generation_reproduces_frozen_data_without_overwriting(tmp_path):
    regenerated = generate_study(tmp_path, seed=4278)
    frozen = json.loads((ROOT / "data/phase3/manifest.json").read_text())
    assert regenerated["dataset_hashes"] == frozen["dataset_hashes"]
    assert regenerated["scene_hashes"] == frozen["scene_hashes"]
    with pytest.raises(FileExistsError, match="Frozen data"):
        generate_study(tmp_path, seed=4278)


def test_v3_groups_are_independent_of_truth_aliases_and_wording():
    samples = load_study("dev")
    assert len({s.group_id for s in samples[:4]}) == 1
    assert len({s.theta_star["cup_choice"] for s in samples[:4]}) == 4
    bad = replace(samples[1], partition="test")
    with pytest.raises(ValueError, match="crosses partitions"):
        check_study([samples[0], bad])


def test_legacy_schema_reader_does_not_rewrite_historical_records():
    original = find_sample("pilot_003")
    assert isinstance(read_sample(asdict(original)), Sample)
    new = load_study("dev")[0]
    assert isinstance(read_sample(asdict(new)), StudySample)


@pytest.mark.parametrize("index", [3, 19])
def test_v3_hidden_changes_leave_public_payload_identical(index):
    sample = load_study("dev")[index]
    hidden = copy.deepcopy(sample.theta_star)
    for slot, entry in sample.slots.items():
        hidden[slot] = next(k for k in entry["candidate_ids"] if k != hidden[slot])
    changed = replace(sample, theta_star=hidden).validate()
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as a, \
         DiverseEnvironment(changed.scene_seed, scene_spec=changed.scene()) as b:
        pa, pb = public_payload(observe(a, sample.u0, [])), public_payload(observe(b, changed.u0, []))
        assert pa == pb
        for forbidden in ("theta_star", "slots", "dag", "group_id", "sample_id", "partition", "task_success"):
            assert '"' + forbidden + '"' not in json.dumps(pa)


def test_container_question_discloses_only_requested_slot_and_reuses_it():
    sample = load_study("dev")[19]
    class Guard(dict):
        def __getitem__(self, key):
            assert key == "cup_destination_choice"
            return super().__getitem__(key)
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        state = observe(env, sample.u0, [])
        q = StudyQuestion.parse(dict(type="select", text="Which destination?", requests=[
            dict(role="cup_destination", candidate_ids=role_candidates(state, "cup_destination"))]), state)
        before = env.snapshot()
        answer, burden = PreferenceResolver(sample.slots, Guard(sample.theta_star)).answer(q)
        assert burden == 1 and set(answer["choices"]) == {"cup_destination"}
        assert env.snapshot() == before
        after = observe(env, sample.u0, [dict(kind="user_answer", response=answer)])
        choices = disclosed_choices(after)
        assert choices == answer["choices"]
        assert len(set(role_candidates(after, "cup_destination")) - {choices["cup_destination"]}) == 1
        assert PreferenceResolver(sample.slots, Guard(sample.theta_star)).answer(q)[1] == 1


@pytest.mark.parametrize("index,roles", [(3, {"cup", "block", "lid"}), (19, {"cup", "block", "cup_destination"})])
def test_all_preferences_is_task_specific(index, roles):
    sample = load_study("dev")[index]
    with DiverseEnvironment(sample.scene_seed, scene_spec=sample.scene()) as env:
        q = StudyQuestion.parse(dict(type="all_preferences", text="All choices?", requests=[]), observe(env, sample.u0, []))
        answer, burden = PreferenceResolver(sample.slots, sample.theta_star).answer(q)
        assert burden == 3 and set(answer["choices"]) == roles


def test_alias_list_position_and_spatial_order_are_not_fixed_answers():
    for partition in ("dev", "test"):
        samples = load_study(partition)
        for template in {s.template_id for s in samples}:
            subset = [s for s in samples if s.template_id == template]
            for slot in subset[0].slots:
                assert {s.slots[slot]["candidate_ids"].index(s.theta_star[slot]) for s in subset} == {0, 1}
                lex = {sorted(s.slots[slot]["candidate_ids"]).index(s.theta_star[slot]) for s in subset}
                assert lex == {0, 1}
