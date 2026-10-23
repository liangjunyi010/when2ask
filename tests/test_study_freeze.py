import hashlib
import json
from dataclasses import replace

import pytest

from when2ask.calibration import FROZEN_DATA, PLAN, SELECTED, source_hashes, verify_data_freeze
from when2ask.config import ROOT
from when2ask.study_agents import prompt_hashes
from when2ask.study_data import load_study, sha256


def test_frozen_study_data_and_all_scene_hashes_match():
    frozen = verify_data_freeze()
    assert frozen["oracle"]["dev"]["successes"] == 32
    assert frozen["oracle"]["test"]["successes"] == 128
    assert frozen["test_api_episodes"] == 0
    assert frozen["dataset_hashes"]["dev"] != frozen["dataset_hashes"]["test"]


def test_preregistered_plan_pairs_every_condition_and_balances_disclosure():
    plan = json.loads(PLAN.read_text())
    assert len(plan["jobs"]) == 40
    assert plan["prompt_hashes"] == prompt_hashes()
    assert plan["source_sha256"] == source_hashes()
    assert plan["dataset_freeze_sha256"] == sha256(FROZEN_DATA)
    assert plan["global_limits"] == {"episodes":40, "authenticated_requests":600}
    assert {j["sample_id"] for j in plan["jobs"]} == set(SELECTED)
    assert len({j["group_id"] for j in plan["jobs"]}) == 8
    for condition in {j["condition"] for j in plan["jobs"]}:
        jobs = [j for j in plan["jobs"] if j["condition"] == condition]
        assert len(jobs) == 8 and sorted(j["missing_preferences"] for j in jobs) == [0,0,1,1,2,2,3,3]


def test_frozen_oracle_records_are_actual_physics_and_not_fake_agent_outputs():
    for partition in ("dev", "test"):
        for sample in load_study(partition):
            path = ROOT / f"outputs/phase3/oracle/{partition}/{sample.sample_id}.json"
            trace = json.loads(path.read_text())
            assert trace["kind"] == "offline_deterministic_physical_oracle"
            assert trace["evaluation"]["task_success"]
            assert trace["signature"]["scene_sha256"] == sha256(ROOT/sample.scene_spec_ref)
            assert all(a["grasp_mode"] == "constraint" for a in trace["actions"])
            assert trace["final_observation"]["simulation_step"] > trace["initial_observation"]["simulation_step"]
            assert all(e["grip_error_m"] <= .025 and e["closest_hand_distance_m"] <= .04
                       for e in trace["execution_log"] if e["kind"] == "grasp")


def test_private_record_rejects_a_claimed_disclosure_inconsistent_with_instruction():
    sample = load_study("dev")[0]
    theta = dict(sample.theta_star)
    theta["cup_choice"] = next(v for v in sample.slots["cup_choice"]["candidate_ids"] if v != theta["cup_choice"])
    with pytest.raises(ValueError, match="Disclosure must agree"):
        replace(sample,theta_star=theta).validate()
