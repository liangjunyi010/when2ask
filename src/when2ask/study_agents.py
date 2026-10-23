"""Versioned public task contract; every method uses the identical planner."""
import hashlib

from .agents import Gate, GateResult, SharedPlanner
from .api import SchemaError
from .protocol import public_payload
from .study_protocol import StudyAction, StudyQuestion

PROMPT_VERSION = "shared_task_contract_v3.1"
CONTEXT = """Public benchmark contract: each named role has exactly ONE fixed user preference.
For a single box with lids the preference roles are cup, block, lid.
For two containers without lids the roles are cup, block, cup_destination. The chosen
cup goes in its preferred container; the chosen block goes in the OTHER container.
Thus one cup_destination answer determines BOTH target containers and is reusable.
An unstated preference is UNKNOWN, never permission to choose either candidate.
Only the instruction and user answers disclose choices. Candidate order, object ID,
color, position and successful robot guesses do not reveal a hidden preference.
Use only instruction, measured physical observations and public history.
Every precedence constraint is stated in the instruction; obey it. If it says either
object may go first, cup/block placement is independent. Covering requires both packed.
"""

GATE_RULES = CONTEXT + """You decide clarification TIMING, returning ASK or CONTINUE only.
Ask only when missing user preferences prevent ALL further useful supported task progress.
Continue when any required action is supported by known choices AND its prerequisites
are satisfied. Execute an available specified subgoal before asking about a future one.
For two containers, a supported cup/block action needs its object choice AND the
cup_destination choice; the latter also gives the block's other destination.
If a public cup-first/block-first rule blocks a known later action, do not execute it early.
Choosing arbitrarily among unknown preferences is not supported progress for the gate.
Do not re-ask choices already disclosed or deduced from a binary confirmation.
Corrective actions supported by public answers may proceed. When complete CONTINUE
so the action planner can emit DONE. Do not output an action or a question.
"""

ACTION_PROMPT = CONTEXT + """You are the shared robot ACTION planner. Return one JSON object only.
Perform the next useful action in the user's task. Use measured spatial_relations:
inside_containers maps each visible container ID to fully contained supported objects;
covering_containers lists physically covering lids; outside_all_containers lists movable
objects whose full footprints are outside all containers. Trust these, not an intended action.
Obey publicly known choices and task order. Prefer a supported known subgoal now.
When a still-required preference is UNKNOWN, make your best guess among its visible
candidates. This action stage cannot ask. Reuse the same guessed/known cup destination
to send the block to the other container. Do not place two objects of the same role.
Repair public mistakes by first returning a covering lid to the table, returning the
wrong object to the table, then placing replacements and covering again if needed.
Table placement physically returns an object to its original source; it is not deletion.
Use DONE only after one cup and one block are in the required container(s), the correct
known/guessed lid covers the single box when required, unselected objects are outside,
and the robot has released everything. A two-container task has NO lid/cover action.
Allowed JSON formats, using actual visible IDs:
{"kind":"pick_place","object_id":"id","target_id":"visible_container_id","relation":"inside"}
{"kind":"pick_place","object_id":"id","target_id":"table","relation":"on"}
{"kind":"cover","object_id":"visible_lid_id","target_id":"visible_container_id"}
{"kind":"DONE"}
Do not include explanation, question, private slot name, score or any other keys.
"""

QUESTION_PROMPT = CONTEXT + """You are the shared robot QUESTION planner. Return one JSON object only.
Ask unknown preferences needed to proceed; avoid already disclosed/deduced choices.
You may batch unknown roles once clarification is necessary. Use cup, block, lid for
the single-box task; use cup, block, cup_destination for the two-container task.
cup_destination candidates are ALL visible container IDs; other roles use all visible
objects of that category. Align text with structured requests. Formats:
{"type":"select","text":"Which block?","requests":[{"role":"block","candidate_ids":["id_a","id_b"]}]}
{"type":"confirm","text":"This cup destination?","requests":[{"role":"cup_destination","candidate_id":"id_a"}]}
{"type":"all_preferences","text":"Which choices for this task?","requests":[]}
select lists every visible candidate of each requested role exactly once. Different
requests may ask different roles. all_preferences asks all three roles, including any
already known ones, and charges three slots; selective questions avoid redundant effort.
No action, private registry, score or extra fields.
"""


def prompt_hashes():
    return {name: hashlib.sha256(text.encode()).hexdigest() for name, text in
            (("action", ACTION_PROMPT), ("question", QUESTION_PROMPT), ("gate_rules", GATE_RULES))}


class StudyLLMGate(Gate):
    def __init__(self, client):
        self.client = client

    def decide(self, public_state):
        def validate(value):
            if set(value) != {"decision"} or value["decision"] not in ("ASK", "CONTINUE"):
                raise SchemaError("Gate returns only decision=ASK or CONTINUE")
            return GateResult(value["decision"])
        return self.client.json(GATE_RULES + '\nReturn JSON: {"decision":"ASK"} or {"decision":"CONTINUE"}.',
            public_payload(public_state), stage="gate", validator=validate, max_tokens=64)


class StudyJevGate(Gate):
    def __init__(self, client, threshold):
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold outside [0,1]")
        self.client, self.threshold = client, threshold

    def decide(self, public_state):
        probability = self.client.noul(public_payload(public_state), GATE_RULES +
            "\nDoes missing user preference information block ALL further useful supported task progress NOW?",
            {"true": "ASK: unknown preferences block all useful required actions under the stated order.",
             "false": "CONTINUE: a supported required action or correction is available, or the task is complete."})
        return GateResult("ASK" if probability >= self.threshold else "CONTINUE", probability)


class StudyPlanner(SharedPlanner):
    def generate_question(self, public_state):
        return self.client.json(QUESTION_PROMPT, public_payload(public_state), stage="question",
                                validator=lambda v: StudyQuestion.parse(v, public_state))

    def generate_action(self, public_state):
        return self.client.json(ACTION_PROMPT, public_payload(public_state), stage="action",
                                validator=lambda v: StudyAction.parse(v, public_state))


def components(method, deepseek, jev, threshold):
    planner = StudyPlanner(deepseek)
    if method == "llm_noask":
        return None, planner
    if method == "llm_gate":
        return StudyLLMGate(deepseek), planner
    if method == "jev_gate":
        return StudyJevGate(jev, threshold), planner
    raise ValueError("Unknown study method")
