"""Public-only protocol for both version 3 tasks; never imports dataset truth."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from .api import SchemaError
from .protocol import Action, Question, public_payload
from .task import PublicState


def public_roles(state):
    containers = [k for k, v in state.observation["objects"].items() if v["category"] == "container"]
    return ("cup", "block", "cup_destination") if len(containers) == 2 else ("cup", "block", "lid")


def role_candidates(state, role):
    category = "container" if role == "cup_destination" else role
    return [k for k, v in state.observation["objects"].items() if v["category"] == category]


def observe(env, instruction, history):
    raw = env.snapshot()
    raw["spatial_relations"] = {
        "inside_containers": {target: [key for key, obj in env.objects.items()
            if obj.category in ("cup", "block") and env.containment(key, target)["inside"]]
            for target in env.container_ids},
        "covering_containers": {target: [key for key, obj in env.objects.items()
            if obj.category == "lid" and env.coverage(key)["covered"]]
            for target in env.container_ids} if len(env.container_ids) == 1 else {},
        "outside_all_containers": [key for key, obj in env.objects.items() if obj.category != "container"
            and all(env.outside_box(key, target)["outside"] for target in env.container_ids)],
    }
    return PublicState.build(raw, history, instruction)


def disclosed_choices(state):
    roles = public_roles(state)
    choices = {r: key for r, key in re.findall(
        r"For the (cup|block|lid|cup_destination), use ([A-Za-z0-9_]+)", state.instruction)}
    excluded = {r: set() for r in roles}
    for event in state.history:
        if event["kind"] != "user_answer":
            continue
        response = event.get("response", {})
        choices.update(response.get("choices", {}))
        for item in response.get("confirmations", []):
            if item["confirmed"]:
                choices[item["role"]] = item["candidate_id"]
            else:
                excluded[item["role"]].add(item["candidate_id"])
    for role in roles:
        remaining = set(role_candidates(state, role)) - excluded[role]
        if len(remaining) == 1:
            choices[role] = remaining.pop()
    return choices


@dataclass(frozen=True)
class StudyQuestion(Question):
    active_roles: tuple[str, ...] = ("cup", "block", "lid")

    def roles(self):
        return set(self.active_roles) if self.type == "all_preferences" else {r["role"] for r in self.requests}

    @classmethod
    def parse(cls, value, state):
        if not isinstance(value, dict) or set(value) != {"type", "text", "requests"}:
            raise SchemaError("Question requires only type, text, requests")
        kind, text, requests = value["type"], value["text"], value["requests"]
        if kind not in ("select", "confirm", "all_preferences") or not isinstance(text, str) or not 1 <= len(text) <= 600:
            raise SchemaError("Invalid question type/text")
        if not isinstance(requests, list) or len(requests) > 6:
            raise SchemaError("Invalid requests array")
        if (kind == "all_preferences" and requests) or (kind != "all_preferences" and not requests):
            raise SchemaError("all_preferences has no requests; select/confirm needs requests")
        for request in requests:
            if not isinstance(request, dict) or request.get("role") not in public_roles(state):
                raise SchemaError("Use the public roles of this task")
            candidates = role_candidates(state, request["role"])
            if kind == "select":
                if (set(request) != {"role", "candidate_ids"} or not isinstance(request["candidate_ids"], list)
                        or len(request["candidate_ids"]) != len(candidates)
                        or set(request["candidate_ids"]) != set(candidates)):
                    raise SchemaError("select must list all visible role candidates exactly once")
            elif set(request) != {"role", "candidate_id"} or request["candidate_id"] not in candidates:
                raise SchemaError("confirm requires one visible role candidate")
        return cls(kind, text, tuple(copy.deepcopy(requests)), public_roles(state))


class StudyAction(Action):
    @classmethod
    def parse(cls, value, state):
        if not isinstance(value, dict):
            raise SchemaError("Action must be an object")
        kind = value.get("kind")
        if kind == "DONE":
            if set(value) != {"kind"}:
                raise SchemaError("DONE only has kind")
            return cls("DONE")
        if kind not in ("pick_place", "cover") or set(value) - {"kind", "object_id", "target_id", "relation"}:
            raise SchemaError("Invalid action schema")
        key, target = value.get("object_id"), value.get("target_id")
        objects = state.observation["objects"]
        obj = objects.get(key)
        if obj is None:
            raise SchemaError("object_id must be visible")
        containers = [k for k, v in objects.items() if v["category"] == "container"]
        if kind == "cover":
            if obj["category"] != "lid" or target not in containers or len(containers) != 1:
                raise SchemaError("Only the single-box task can be covered with a visible lid")
            return cls(kind, key, target, "covers")
        relation = value.get("relation", "inside")
        if obj["category"] not in ("cup", "block", "lid"):
            raise SchemaError("Only movable objects can be transferred")
        if not ((target in containers and relation == "inside" and obj["category"] in ("cup", "block"))
                or (target == "table" and relation == "on")):
            raise SchemaError("Use visible container/inside or table/on")
        return cls(kind, key, target, relation)
