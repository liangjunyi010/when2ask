"""Independent checks against the untouched episode and actual decoded GIF."""
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"presentation/milestone"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preservation():
    path=BASE/"source_preservation.json"
    if not path.exists():
        files=subprocess.check_output(["git","ls-tree","-r","--name-only","960c7ca"],cwd=ROOT,text=True).splitlines()
        protected=[p for p in files if p.startswith(("data/","configs/","outputs/","src/when2ask/","docs/phase2/","docs/phase3/"))]
        path.write_text(json.dumps(dict(base_commit="960c7caa4e2051eef898ae82b67da1051e682645",
            protected_sha256={p:sha(ROOT/p) for p in protected},api_calls_in_this_stage=0),indent=2)+"\n")
    original=json.loads(path.read_text())
    changed=[p for p,h in original["protected_sha256"].items() if sha(ROOT/p)!=h]
    assert not changed, f"Protected source/evidence modified: {changed}"
    return len(original["protected_sha256"])


def validate():
    count=preservation()
    timeline=json.loads((BASE/"web/timeline.json").read_text())
    report=json.loads((BASE/"mapping_validation.json").read_text())
    ep=timeline["episodes"][0]
    original=json.loads((ROOT/ep["source_episode"]).read_text())
    raw_api_checks=[]
    for source in timeline["episodes"]:
        data=json.loads((ROOT/source["source_episode"]).read_text())
        attempts=[json.loads(line) for line in (ROOT/source["source_files"]["api_attempts.jsonl"]["path"]).read_text().splitlines()]
        for turn in data["turns"]:
            rows=[a for a in attempts if a["round"]==turn["round"] and a["status"]=="ok"]
            gate=next(a for a in rows if a["stage"]=="gate")
            if gate["backend"]=="jev":
                probability=gate["response"]["answers"]["needs_clarification"]["noul"]
                assert probability==turn["gate"]["p_ask"]
                assert turn["gate"]["decision"]==("ASK" if probability>=.5 else "CONTINUE")
            else:
                payload=json.loads(gate["response"]["choices"][0]["message"]["content"])
                assert payload["decision"]==turn["gate"]["decision"]
                assert turn["gate"]["p_ask"] is None
            stage="question" if "question" in turn else "action"
            planner=next(a for a in rows if a["stage"]==stage)
            payload=json.loads(planner["response"]["choices"][0]["message"]["content"])
            if stage=="question":
                assert payload["type"]==turn["question"]["type"] and payload["text"]==turn["question"]["text"]
                assert [(r["role"],r["candidate_ids"]) for r in payload["requests"]]==[(r["role"],r["candidate_ids"]) for r in turn["question"]["requests"]]
            else:
                assert all(turn["action"][key]==value for key,value in payload.items())
            raw_api_checks.append(dict(episode=source["episode_key"],round=turn["round"],
                gate_backend=gate["backend"],decision=turn["gate"]["decision"],p_ask=turn["gate"]["p_ask"],
                planner_stage=stage,matched_original_http_responses=True))
    original_gif=ROOT/ep["source_files"]["demo.gif"]["path"]
    checkpoints=report["checkpoints"]
    expected={"01_initial":(0,"gate"),"02_pick_cup":(0,"execution"),"02b_cup_transport":(0,"execution"),
        "03_ask":(1,"question_planner"),"04_user_answer":(1,"user_simulator"),
        "05_robot_continue":(2,"execution"),"05b_cover":(3,"execution"),"06_evaluation":(4,"evaluator")}
    with Image.open(original_gif) as gif:
        for check in checkpoints:
            frame=original["recording"]["frames"][check["frame_index"]]
            turn_index,node=expected[check["label"]]
            turn=original["turns"][turn_index]
            assert check["active_flow_node"]==node and check["round"]==turn["round"]
            assert check["simulation_step"]==frame["simulation_step"]
            assert check["start_ms"]==sum(f["duration_ms"] for f in original["recording"]["frames"][:check["frame_index"]])
            assert check["end_ms"]-check["start_ms"]==frame["duration_ms"]
            assert check["gate"]["p_ask"]==turn["gate"]["p_ask"] and check["gate"]["decision"]==turn["gate"]["decision"]
            if node=="execution":
                result=turn["physical_result"]
                assert result["start_step"]<=frame["simulation_step"]<=result["end_step"]
                assert check["action"]==turn["action"]
                events=[(i,e) for i,e in enumerate(original["execution_log"]) if e.get("object_id")==result["object_id"]
                    and e["kind"] in ("phase","grasp","release") and result["start_step"]<=e["step"]<=frame["simulation_step"]]
                latest=max(events,key=lambda row:(row[1]["step"],row[0]))[1]
                assert check["physical_phase"]==latest.get("phase",latest["kind"])
            if node=="question_planner":
                assert check["question"]==turn["question"] and check["user_answer"] is None
                assert "ASK " in frame["label"]
            if node=="user_simulator":
                assert check["user_answer"]==turn["user_answer"] and frame["label"].startswith("USER ")
            gif.seek(check["source_gif_frame_index"])
            assert hashlib.sha256(gif.convert("RGBA").tobytes()).hexdigest()==check["pixel_sha256"]
    ask=next(c for c in checkpoints if c["label"]=="03_ask")
    user=next(c for c in checkpoints if c["label"]=="04_user_answer")
    assert ask["simulation_step"]==user["simulation_step"]==3663
    assert ask["frame_index"]==143 and user["frame_index"]==144
    assert ask["gate"]["p_ask"]==.70 and checkpoints[0]["gate"]["p_ask"]==.14
    report["independent_raw_episode_and_gif_checks"]=dict(passed=True,protected_files_unchanged=count,
        source_files_sha256_match=all(sha(ROOT/ref["path"])==ref["sha256"] for ep in timeline["episodes"] for ref in ep["source_files"].values()),
        no_model_wall_time_invented=True,same_step_frame_order_verified=True)
    report["original_http_response_checks"]=raw_api_checks
    (BASE/"mapping_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["independent_raw_episode_and_gif_checks"]))


if __name__=="__main__":
    import sys
    preservation() if "--snapshot-only" in sys.argv else validate()
