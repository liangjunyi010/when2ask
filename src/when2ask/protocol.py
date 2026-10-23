"""Public sensor projection and strictly validated question/action wire formats."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass

from .api import SchemaError
from .task import PublicState

ROLES = ("cup", "block", "lid")


def observe(env, instruction, history):
    raw = env.snapshot()
    raw["spatial_relations"] = {
        "inside_box": [key for key, obj in env.objects.items() if obj.category in ("cup", "block")
                       and env.containment(key)["inside"]],
        "covering_box": [key for key, obj in env.objects.items() if obj.category == "lid"
                         and env.coverage(key)["covered"]],
        "outside_box": [key for key in env.objects if key != "box" and env.outside_box(key)["outside"]],
    }
    return PublicState.build(raw, history, instruction)


def public_payload(state: PublicState):
    raw = state.observation
    objects = [dict(object_id=key, **{name: value[name] for name in
                    ("category", "color", "position", "aabb_min", "aabb_max")})
               for key, value in raw["objects"].items()]
    value = dict(instruction=state.instruction,
                 observation=dict(objects=objects, simulation_step=raw["simulation_step"],
                                  held_object=raw["held_object"],
                                  spatial_relations=raw.get("spatial_relations", {})),
                 history=list(state.history))
    def compact(obj):
        if isinstance(obj, float):
            return round(obj, 5)
        if isinstance(obj, list):
            return [compact(v) for v in obj]
        if isinstance(obj, dict):
            return {k: compact(v) for k, v in obj.items()}
        return obj
    return compact(copy.deepcopy(value))


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def role_candidates(state, role):
    return [key for key, obj in state.observation["objects"].items() if obj["category"] == role]


def disclosed_choices(state):
    choices = {role: key for role, key in re.findall(
        r"For the (cup|block|lid), use ([A-Za-z0-9_]+)", state.instruction)}
    excluded = {r: set() for r in ROLES}
    for event in state.history:
        if event["kind"] == "user_answer":
            response = event.get("response", {})
            choices.update(response.get("choices", {}))
            for item in response.get("confirmations", []):
                if item["confirmed"]:
                    choices[item["role"]] = item["candidate_id"]
                else:
                    excluded[item["role"]].add(item["candidate_id"])
    for role in ROLES:
        remaining = set(role_candidates(state, role)) - excluded[role]
        if len(remaining) == 1:
            choices[role] = remaining.pop()
    return choices


@dataclass(frozen=True)
class Question:
    type: str
    text: str
    requests: tuple[dict, ...] = ()

    def roles(self):
        return set(ROLES) if self.type == "all_preferences" else {r["role"] for r in self.requests}

    def to_dict(self):
        return dict(type=self.type, text=self.text, requests=list(copy.deepcopy(self.requests)))

    @classmethod
    def parse(cls, value, state):
        if set(value) != {"type", "text", "requests"}:
            raise SchemaError("Question keys must be type, text, requests")
        kind, text, requests = value["type"], value["text"], value["requests"]
        if kind not in ("select", "confirm", "all_preferences") or not isinstance(text, str) or not 1 <= len(text) <= 600:
            raise SchemaError("Invalid question type/text")
        if not isinstance(requests, list) or len(requests) > 6:
            raise SchemaError("requests must be an array with at most six entries")
        if kind == "all_preferences":
            if requests:
                raise SchemaError("all_preferences requires an empty requests array and asks all three roles")
        elif not requests:
            raise SchemaError("select/confirm requires requests")
        for request in requests:
            if not isinstance(request, dict) or request.get("role") not in ROLES:
                raise SchemaError("Question role must be cup, block or lid")
            candidates = role_candidates(state, request["role"])
            if kind == "select":
                if (set(request) != {"role", "candidate_ids"} or not isinstance(request["candidate_ids"], list)
                        or len(request["candidate_ids"]) != len(candidates)
                        or set(request["candidate_ids"]) != set(candidates)):
                    raise SchemaError("select must list exactly the publicly visible candidates for its role")
            elif set(request) != {"role", "candidate_id"} or request["candidate_id"] not in candidates:
                raise SchemaError("confirm requires one visible candidate_id")
        return cls(kind, text, tuple(copy.deepcopy(requests)))


@dataclass(frozen=True)
class Action:
    kind: str
    object_id: str | None = None
    target_id: str | None = None
    relation: str = "inside"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def parse(cls, value, state):
        kind = value.get("kind")
        if kind == "DONE":
            if set(value) != {"kind"}:
                raise SchemaError("DONE has only the kind key")
            return cls("DONE")
        if kind not in ("pick_place", "cover") or set(value) - {"kind", "object_id", "target_id", "relation"}:
            raise SchemaError("Action must be pick_place, cover or DONE with only action fields")
        key, target = value.get("object_id"), value.get("target_id")
        obj = state.observation["objects"].get(key)
        if obj is None:
            raise SchemaError("object_id must be a currently visible object ID")
        relation = value.get("relation", "inside")
        if kind == "cover":
            if target != "box" or obj["category"] != "lid":
                raise SchemaError("cover requires a visible lid and target_id=box")
            return cls(kind, key, target, "covers")
        if (target, relation) not in (("box", "inside"), ("table", "on")):
            raise SchemaError("pick_place target/relation must be box/inside or table/on")
        if obj["category"] not in ("cup", "block", "lid") or (target == "box" and obj["category"] == "lid"):
            raise SchemaError("Only cups/blocks go inside; lids may be returned to the table")
        return cls(kind, key, target, relation)
