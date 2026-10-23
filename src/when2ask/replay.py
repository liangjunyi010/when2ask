"""Offline, evidence-linked replay conversion. No physics or model calls.

The recorder's display-frame order is authoritative. Simulation steps locate
motor phases, but cannot order ASK/USER frames at a frozen physical step.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_names(episode):
    names = {k: f"{v['color']} {v['category']}" for k,v in episode["initial_observation"]["objects"].items()}
    if "box" in names:
        names["box"] = "box"
    names["table"] = "table"
    return names


def humanize(value, names):
    if not isinstance(value, str):
        return value
    for key in sorted(names, key=len, reverse=True):
        if key != "table":
            value = value.replace(key, names[key])
    return value


def public_choices(episode, turn, include_current_answer=False):
    import re
    choices = {role:key for role,key in re.findall(
        r"For the (cup|block|lid|cup_destination), use ([A-Za-z0-9_]+)",episode["instruction"])}
    history = turn["public_payload"]["history"]
    answers = [e["response"] for e in history if e["kind"] == "user_answer"]
    if include_current_answer:
        answers.append(turn["user_answer"])
    for answer in answers:
        choices.update(answer.get("choices",{}))
        for confirmation in answer.get("confirmations",[]):
            if confirmation["confirmed"]:
                choices[confirmation["role"]] = confirmation["candidate_id"]
    return choices


def phase_at(episode, physical, step):
    candidates = []
    for index,event in enumerate(episode["execution_log"]):
        if (event.get("object_id") == physical["object_id"]
                and physical["start_step"] <= event.get("step",-1) <= min(step,physical["end_step"])
                and event["kind"] in ("phase","grasp","release")):
            candidates.append((event["step"],index,event))
    if not candidates:
        return None,None
    _, index,event = max(candidates,key=lambda e:(e[0],e[1]))
    return event.get("phase",event["kind"]),index


def action_description(action,names):
    if not action:
        return None
    if action["kind"] == "DONE":
        return "DONE"
    obj, target = names[action["object_id"]], names[action["target_id"]]
    return (f"cover({obj}, {target})" if action["kind"] == "cover" else f"pick_place({obj}, {target})")


def make_frames(episode):
    """Associate every logical recording frame with its exact public round."""
    records,turns = episode["recording"]["frames"],episode["turns"]
    names = object_names(episode)
    actions = [(i,t) for i,t in enumerate(turns) if "physical_result" in t]
    asks = [(i,t) for i,t in enumerate(turns) if "question" in t]
    ask_cursor,current_ask = 0,None
    frames,start = [],0
    visited = set()
    for index,raw in enumerate(records):
        label,step = raw["label"],raw["simulation_step"]
        phase,phase_index,physical = None,None,None
        question,answer,evaluation = None,None,None
        source_refs = [f"episode.json#/recording/frames/{index}"]
        if label.startswith("OBSERVE"):
            ti,turn = 0,turns[0]
            stage,node = "gate_result","gate"
            nodes = ["instruction","observation","gate",turn["gate"]["decision"].lower()]
            edges = ["instruction-observation","observation-gate","gate-"+turn["gate"]["decision"].lower()]
        elif label.startswith("ASK "):
            if ask_cursor >= len(asks):
                raise ValueError("Recorded ASK has no corresponding public question")
            ti,turn = asks[ask_cursor]
            if turn["ask_check"]["before_step"] != step:
                raise ValueError("ASK frame and question step disagree")
            current_ask = (ti,turn)
            ask_cursor += 1
            stage,node = "question","question_planner"
            question = turn["question"]
            nodes = ["gate","ask","question_planner"]
            edges = ["gate-ask","ask-question_planner"]
            source_refs.append(f"episode.json#/turns/{ti}/question")
        elif label.startswith("USER "):
            if current_ask is None:
                raise ValueError("USER frame before any ASK frame")
            ti,turn = current_ask
            if turn["ask_check"]["after_step"] != step:
                raise ValueError("User response and recorded frame step disagree")
            stage,node = "user_answer","user_simulator"
            question,answer = turn["question"],turn["user_answer"]
            nodes = ["gate","ask","question_planner","user_simulator","history"]
            edges = ["gate-ask","ask-question_planner","question_planner-user_simulator","user_simulator-history"]
            source_refs += [f"episode.json#/turns/{ti}/question",f"episode.json#/turns/{ti}/user_answer",
                            f"episode.json#/turns/{ti}/ask_check"]
        elif label.startswith(("pick_place ","cover ")):
            kind,key = label.split(" ",1)
            matches = [(i,t) for i,t in actions if t["action"]["kind"]==kind and t["action"]["object_id"]==key
                       and t["physical_result"]["start_step"] <= step <= t["physical_result"]["end_step"]]
            if len(matches) != 1:
                raise ValueError(f"Frame {index} is not located in exactly one real skill interval")
            ti,turn = matches[0]
            physical = turn["physical_result"]
            phase,phase_index = phase_at(episode,physical,step)
            stage,node = "execution","execution"
            nodes = ["continue","action_planner","execution"]
            edges = ["gate-continue","continue-action_planner","action_planner-execution"]
            source_refs += [f"episode.json#/turns/{ti}/physical_result",
                            f"episode.json#/execution_log/{phase_index}"] if phase_index is not None else []
        elif label.startswith(("done ","DONE")):
            done = [(i,t) for i,t in enumerate(turns) if t.get("action",{}).get("kind")=="DONE"]
            if len(done)!=1 or index!=len(records)-1:
                raise ValueError("Final display frame lacks unique logged DONE")
            ti,turn = done[0]
            stage,node = "evaluation","evaluator"
            nodes = ["continue","action_planner","done","evaluator"]
            edges = ["gate-continue","continue-action_planner","action_planner-done","done-evaluator"]
            evaluation = dict(task_success=episode["evaluation"]["task_success"],
                              conditions=episode["evaluation"]["conditions"],
                              clarification_burden=episode["evaluation"]["clarification_burden"],
                              action_count=episode["evaluation"]["action_count"])
            source_refs += [f"episode.json#/turns/{ti}/action","evaluation.json#/task_success",
                            "evaluation.json#/conditions"]
        else:
            raise ValueError(f"Unknown recorder label: {label}")
        gate = turn["gate"]
        action = turn.get("action")
        if stage in ("question","user_answer"):
            action = None
        completed_actions = [dict(a,object_name=names[a["object_id"]],target_name=names[a["target_id"]])
                             for a in episode["actions"] if a["end_step"] <= step]
        # Never expose a later action result, later answer, or evaluator truth.
        outcome = (physical if physical and physical["end_step"] <= step else None)
        disclosed = public_choices(episode,turn,stage=="user_answer")
        row = dict(frame_index=index,recording_frame_index=index,simulation_step=step,
            duration_ms=raw["duration_ms"],start_ms=start,end_ms=start+raw["duration_ms"],
            source_label=label,round=turn["round"],stage=stage,active_flow_node=node,
            active_nodes=nodes,active_edges=edges,completed_nodes=sorted(visited-set(nodes)),
            gate=dict(backend="jev" if episode["method"]=="jev_gate" else "deepseek",
                      decision=gate["decision"],p_ask=gate["p_ask"]),
            action=action,action_text=action_description(action,names),
            action_name=(names.get(action.get("object_id")) if action else None),
            target_name=(names.get(action.get("target_id")) if action else None),
            physical_interval=({k:physical[k] for k in ("start_step","end_step")} if physical else None),
            physical_phase=phase,question=question,user_answer=answer,action_outcome=outcome,
            completed_actions=completed_actions,evaluation=evaluation,
            public_preferences={role:names[key] for role,key in disclosed.items()},
            evidence=source_refs+[f"episode.json#/turns/{ti}/gate"],
            timing_basis="Recorded display interval, not model inference wall time")
        frames.append(row)
        start = row["end_ms"]
        visited.update(nodes)
    if ask_cursor != len(asks):
        raise ValueError("An actual question has no recorded display frame")
    return frames


def convert_episode(source, destination, episode_key, *, repository_root):
    source,destination = Path(source),Path(destination)
    episode = json.loads((source/"episode.json").read_text())
    evaluation = json.loads((source/"evaluation.json").read_text())
    if evaluation != episode["evaluation"]:
        raise ValueError("Independent evaluation file and episode disagree")
    if episode["evidence_kind"] != "live_model_and_physics":
        raise ValueError("Presentation replay requires actual live-model/physics evidence")
    frames = make_frames(episode)
    assets = destination/"assets"/episode_key
    assets.mkdir(parents=True,exist_ok=True)
    encoded,encoded_durations = [],[]
    with Image.open(source/"demo.gif") as gif:
        size = gif.size
        for i in range(gif.n_frames):
            gif.seek(i)
            encoded.append(gif.convert("RGB").copy())
            encoded_durations.append(gif.info["duration"])
    if sum(encoded_durations) != sum(f["duration_ms"] for f in frames):
        raise ValueError("GIF and recorder total duration disagree")
    # Supports Pillow merging identical adjacent frames without deleting the
    # logical metadata entries (including equal-step ASK and USER frames).
    encoded_index,encoded_start = 0,0
    for f in frames:
        while f["start_ms"] >= encoded_start+encoded_durations[encoded_index]:
            encoded_start += encoded_durations[encoded_index]
            encoded_index += 1
        if f["end_ms"] > encoded_start+encoded_durations[encoded_index]:
            raise ValueError("Logical frame spans incompatible encoded GIF frames")
        f.update(source_gif_frame_index=encoded_index,
                 source_gif_frame_interval=[encoded_index,encoded_index+1],
                 source_pixel_sha256=hashlib.sha256(encoded[encoded_index].convert("RGBA").tobytes()).hexdigest())
    columns,rows,tile_count = 8,4,32
    for sheet in range((len(encoded)+tile_count-1)//tile_count):
        batch=encoded[sheet*tile_count:(sheet+1)*tile_count]
        atlas=Image.new("RGB",(size[0]*columns,size[1]*rows),"white")
        for j,frame in enumerate(batch):
            atlas.paste(frame,((j%columns)*size[0],(j//columns)*size[1]))
        atlas.save(assets/f"atlas_{sheet:02d}.webp",lossless=True,method=4)
    for f in frames:
        i=f["source_gif_frame_index"]
        tile=i%tile_count
        f["asset"] = dict(url=f"assets/{episode_key}/atlas_{i//tile_count:02d}.webp",
                          rect=[(tile%columns)*size[0],(tile//columns)*size[1],*size])
    result = dict(schema_version=1,episode_key=episode_key,episode_id=episode["episode_id"],
        sample_id=episode["sample_id"],method=episode["method"],
        source_episode=str((source/"episode.json").relative_to(repository_root)),
        source_files={name:dict(path=str((source/name).relative_to(repository_root)),sha256=digest(source/name))
                      for name in ("episode.json","demo.gif","evaluation.json","api_attempts.jsonl","scene.png")},
        source_dimensions=list(size),recorded_frame_count=len(frames),encoded_gif_frame_count=len(encoded),
        duration_ms=frames[-1]["end_ms"],object_names=object_names(episode),
        instruction=humanize(episode["instruction"],object_names(episode)),
        public_task_summary=("Pack one cup and one block, then cover the box. Keep unselected objects outside."
            if any(a["skill"]=="cover" for a in episode["actions"]) else
            "Put the selected cup in its preferred container and the block in the other. Keep unselected objects outside."),
        frames=frames,notes=["All times are source display times, not inferred API start/end times.",
            "Same-step frames retain their original order and separate durations.",
            "Object names come from the public initial observation; answers appear only on USER frames.",
            "Original TinyRenderer frame pixels are preserved losslessly in atlas resources."])
    return result
