from when2ask.environment import Environment
from when2ask.evaluator import Evaluator
from when2ask.skills import RobotSkills
from when2ask.task import PrivateTaskSpec


def test_wrong_early_cover_and_wrong_block_can_be_repaired_with_real_motions():
    with Environment() as env:
        skills = RobotSkills(env)
        actions = []
        for method, key, target, relation in [
            ("cover", "black_lid", "box", None),
            ("pick_place", "black_lid", "table", "on"),
            ("pick_place", "blue_cup", "box", "inside"),
            ("pick_place", "yellow_block", "box", "inside"),
            ("pick_place", "yellow_block", "table", "on"),
            ("pick_place", "green_block", "box", "inside"),
            ("cover", "black_lid", "box", None),
        ]:
            result = (skills.cover(key, target) if method == "cover" else
                      skills.pick_place(key, target, relation))
            actions.append(result.to_dict())
            assert result.success, result.reason
        outcome = Evaluator().evaluate(env, PrivateTaskSpec(), clarification_burden=0,
                                       actions=actions, termination="robot_action_limit")
        assert outcome["task_success"]
        assert outcome["termination_reason"] == "robot_action_limit"
        assert outcome["conditions"]["packing_before_cover"]
        covers = [e for e in env.events if e["kind"] == "cover_started"]
        assert covers[0]["contents_before"] == []
        assert set(covers[-1]["contents_before"]) == {"blue_cup", "green_block"}
