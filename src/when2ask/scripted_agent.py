"""A policy over PublicState only. No model, simulator or evaluator access."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

from .task import PublicState


@dataclass(frozen=True)
class Decision:
    kind: Literal["ASK", "CONTINUE", "DONE"]
    skill: str | None = None
    object_id: str | None = None
    target_id: str | None = None
    slots: tuple[str, ...] = ()
    explanation: str = ""

    def to_dict(self):
        return asdict(self)


class ScriptedAgent:
    def __init__(self, mode: str):
        if mode not in ("scripted_ask", "scripted_noask"):
            raise ValueError("Unknown scripted mode")
        self.mode = mode

    @staticmethod
    def _default(category: str, state: PublicState):
        """Closest initial/current XY center to the box; stable ID breaks ties."""
        objects = state.observation["objects"]
        box_xy = objects["box"]["position"][:2]
        candidates = [key for key, value in objects.items() if value["category"] == category]
        return min(candidates, key=lambda key: (
            math.dist(objects[key]["position"][:2], box_xy), key))

    def decide(self, state: PublicState) -> Decision:
        disclosed = state.disclosed_preferences()
        completed = [h["result"] for h in state.history
                     if h["kind"] == "action" and h["result"]["success"]]
        cup = disclosed["cup_choice"]
        if not any(r["skill"] == "pick_place" and r["object_id"] == cup for r in completed):
            return Decision("CONTINUE", "pick_place", cup, "box",
                            explanation="Cup preference is explicit in the instruction")
        missing = tuple(s for s in ("block_choice", "lid_choice") if s not in disclosed)
        if self.mode == "scripted_ask" and missing:
            return Decision("ASK", slots=missing,
                            explanation="Which block and which lid should I use?")
        block = disclosed.get("block_choice") or self._default("block", state)
        lid = disclosed.get("lid_choice") or self._default("lid", state)
        if not any(r["skill"] == "pick_place" and r["object_id"] == block for r in completed):
            return Decision("CONTINUE", "pick_place", block, "box",
                            explanation="Use disclosed choice or closest-to-box default")
        if not any(r["skill"] == "cover" for r in completed):
            return Decision("CONTINUE", "cover", lid, "box",
                            explanation="Pack actions finished; use disclosed/default lid")
        return Decision("DONE", explanation="Execution complete; independent evaluator scores now")
