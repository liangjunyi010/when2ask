"""Gate runs first; only the shared DeepSeek planner produces actions and DONE."""
from dataclasses import asdict, dataclass

from .api import SchemaError
from .prompts import ACTION_PROMPT, GATE_RULES, QUESTION_PROMPT
from .protocol import Action, Question, public_payload


@dataclass(frozen=True)
class GateResult:
    decision: str
    p_ask: float | None = None

    def __post_init__(self):
        if self.decision not in ("ASK", "CONTINUE"):
            raise SchemaError("Gate can only ASK or CONTINUE; it cannot act or terminate")

    def to_dict(self):
        return asdict(self)


class Gate:
    def decide(self, public_state) -> GateResult:
        raise NotImplementedError


class LLMGate(Gate):
    def __init__(self, client):
        self.client = client

    def decide(self, public_state):
        def validate(value):
            if set(value) != {"decision"}:
                raise SchemaError("Gate JSON has only the decision key")
            return GateResult(value["decision"])
        return self.client.json(GATE_RULES + '\nReturn only JSON {"decision":"ASK"} or {"decision":"CONTINUE"}.',
                                public_payload(public_state), stage="gate", validator=validate, max_tokens=64)


class JevGate(Gate):
    def __init__(self, client, threshold=.5):
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be in [0, 1]")
        self.client, self.threshold = client, threshold

    def decide(self, public_state):
        probability = self.client.noul(public_payload(public_state),
            GATE_RULES + "\nDoes missing user preference information prevent ALL further useful supported task progress now?",
            {"true": "ASK: no useful required task action can progress without an unknown preference.",
             "false": "CONTINUE: a supported task action can progress, or the task is already complete."})
        return GateResult("ASK" if probability >= self.threshold else "CONTINUE", probability)


class SharedPlanner:
    def __init__(self, client):
        self.client = client

    def generate_question(self, public_state) -> Question:
        return self.client.json(QUESTION_PROMPT, public_payload(public_state), stage="question",
                                validator=lambda value: Question.parse(value, public_state))

    def generate_action(self, public_state) -> Action:
        return self.client.json(ACTION_PROMPT, public_payload(public_state), stage="action",
                                validator=lambda value: Action.parse(value, public_state))


def components(method, deepseek, jev, threshold):
    planner = SharedPlanner(deepseek)
    if method == "llm_noask":
        return None, planner
    if method == "llm_gate":
        return LLMGate(deepseek), planner
    if method == "jev_gate":
        return JevGate(jev, threshold), planner
    raise ValueError("Method must be llm_noask, llm_gate or jev_gate")
