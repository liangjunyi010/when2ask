"""The private intent and the ONLY policy input are separate data types."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass

INSTRUCTION = (
    "Put one cup and one block in the box, then cover it. Use the blue cup. "
    "Leave all unselected objects outside the box."
)
SLOT_OPTIONS = {
    "cup_choice": ("red_cup", "blue_cup"),
    "block_choice": ("green_block", "yellow_block"),
    "lid_choice": ("black_lid", "white_lid"),
}


@dataclass(frozen=True)
class PrivateTaskSpec:
    cup_choice: str = "blue_cup"
    block_choice: str = "green_block"
    lid_choice: str = "black_lid"

    def __post_init__(self):
        for slot, options in SLOT_OPTIONS.items():
            if getattr(self, slot) not in options:
                raise ValueError(f"Invalid {slot}")
        if self.cup_choice != "blue_cup":
            raise ValueError("This fixed task publicly specifies the blue cup")


@dataclass(frozen=True)
class PublicState:
    instruction: str
    observation: dict
    history: tuple[dict, ...]

    @classmethod
    def build(cls, observation: dict, history: list[dict]):
        # No PrivateTaskSpec argument, evaluator labels, or simulator reference.
        return cls(INSTRUCTION, copy.deepcopy(observation), tuple(copy.deepcopy(history)))

    def disclosed_preferences(self):
        result = {}
        match = re.search(r"Use the (blue|red) cup", self.instruction)
        if match:
            result["cup_choice"] = f"{match.group(1)}_cup"
        for event in self.history:
            if event["kind"] == "user_answer":
                result.update(event["answers"])
        return result
