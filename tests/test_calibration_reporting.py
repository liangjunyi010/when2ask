from when2ask.calibration import SELECTION_RULE
from when2ask.study_reporting import paired_interval, public_progress, select_threshold, wilson


def rows_for_test():
    # Explicit synthetic rows for offline selection-rule unit tests ONLY.
    return [dict(condition=f"jev_gate@{threshold:.1f}", group_id=f"synthetic_{i}", task_success=True,
                 burden=i % 4, api_latency_ms=1000) for threshold in (.3, .5, .7) for i in range(8)]


def test_threshold_rule_retains_predeclared_default_when_indistinguishable():
    result = select_threshold(rows_for_test())
    assert result["selected_threshold"] == .5
    assert result["rule"]["default_threshold"] == .5
    assert paired_interval([0]*8) == [0,0]


def test_threshold_selection_needs_complete_group_pairing():
    result = select_threshold(rows_for_test()[1:])
    assert result["selected_threshold"] == .5
    assert result["comparisons"]["0.3"]["eligible"] is False


def test_threshold_rule_can_detect_a_clear_paired_success_advantage():
    rows = rows_for_test()
    for row in rows:
        if row["condition"] in ("jev_gate@0.5", "jev_gate@0.7") and int(row["group_id"].split("_")[-1]) < 5:
            row["task_success"] = False
    assert select_threshold(rows)["selected_threshold"] == .3


def test_group_success_interval_keeps_small_sample_uncertainty():
    low, high = wilson(8,8)
    assert low < .7 and high == 1
    assert wilson(0,0) == [None,None]


def test_public_timing_diagnostic_does_not_require_private_truth():
    def state(instruction):
        return dict(instruction=instruction, history=[], observation=dict(
            objects=[dict(object_id="cup_a",category="cup"),dict(object_id="cup_b",category="cup"),
                     dict(object_id="block_a",category="block"),dict(object_id="block_b",category="block"),
                     dict(object_id="lid_a",category="lid"),dict(object_id="lid_b",category="lid"),
                     dict(object_id="box",category="container")],
            spatial_relations=dict(inside_containers={"box":[]},covering_containers={"box":[]})))
    assert public_progress(state("Either object may be placed first. For the cup, use cup_a.")) == "supported_progress"
    assert public_progress(state("Place the block before the cup. For the cup, use cup_a.")) == "preference_blocked"
