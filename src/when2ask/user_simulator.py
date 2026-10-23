"""Structured oracle: returns exactly the requested preference slots."""
from .task import PrivateTaskSpec, SLOT_OPTIONS


class UserSimulator:
    def __init__(self, private_spec: PrivateTaskSpec):
        self.__private_spec = private_spec

    def answer(self, slots: tuple[str, ...] | list[str]):
        if not slots or any(slot not in SLOT_OPTIONS for slot in slots):
            raise ValueError("Ask one or more recognized preference slots")
        return {slot: getattr(self.__private_spec, slot) for slot in slots}
