"""Structured oracle: returns exactly the requested preference slots."""
from .task import PrivateTaskSpec, SLOT_OPTIONS


class UserSimulator:
    def __init__(self, private_spec: PrivateTaskSpec):
        self.__private_spec = private_spec

    def answer(self, slots: tuple[str, ...] | list[str]):
        if not slots or any(slot not in SLOT_OPTIONS for slot in slots):
            raise ValueError("Ask one or more recognized preference slots")
        return {slot: getattr(self.__private_spec, slot) for slot in slots}


class PreferenceResolver:
    """Private routing from PUBLIC role/candidate descriptions to one slot.

    Constructed by the runner only. Neither registry nor theta is passed to a model.
    """
    def __init__(self, slots, theta):
        self._slots, self._theta = slots, theta

    def resolve(self, question):
        roles = question.roles()
        routing = {}
        for role in roles:
            matches = [slot for slot, registry in self._slots.items() if registry["public_role"] == role]
            if len(matches) != 1:
                raise ValueError("Public role does not resolve to exactly one task preference")
            routing[role] = matches[0]
        return routing

    def answer(self, question):
        routing = self.resolve(question)
        # Access only the requested keys. In particular no copying/iterating theta.
        if question.type in ("select", "all_preferences"):
            response = {"choices": {role: self._theta[slot] for role, slot in sorted(routing.items())}}
        else:
            response = {"confirmations": [dict(role=r["role"], candidate_id=r["candidate_id"],
                          confirmed=self._theta[routing[r["role"]]] == r["candidate_id"])
                          for r in question.requests]}
        return response, len(set(routing.values()))
