"""One shared public contract and planner for all six new tasks and three methods."""
import hashlib

from .agents import GateResult
from .api import SchemaError
from .task6_protocol import action, question, scripted_next, known_choices

CONTEXT='''You control a real Panda arm or Husky in one of six tasks. Read the public instruction and observation.task for the exact goal, public DAG and finite preference slots. Never assume hidden choices are known. Observation is measured geometry, contents, counts, prior physical inspections and public history, not evaluator labels. Initial choices and prior answers are reusable. A successful move is not necessarily a successful task.
The six tasks are category sorting (cups to specified bin; blocks to preferred bin; pucks to OTHER bin), inventory deficit replenishment (do not move existing stock or surplus), open-retrieve-reclose storage (uncover first, retrieve selected item, leave other inside, close again), single-capacity exchange via the selected buffer (do not use the other pad), actual station patrol then physical return home, and reveal-inspect-report (move screen, physically inspect label, report observed code).
World facts and preferences differ: the inspection code is an immutable world fact observable by a fixed camera after clearing an opaque screen. A user reply does not count as physical inspection. A missing preference should only block actions depending on it. Useful specified work, such as sorting cups, replenishing cups, opening storage or inspecting the known station, may precede clarification. Do not invent extra requirements or actions. All methods share this contract.
'''
GATE=CONTEXT+'''Decide ASK or CONTINUE only, before any action planning. Ask when missing user information blocks useful supported progress; continue when a required specified action or information-gathering action is available. Do not ask for facts the robot can directly observe with a useful task action. Do not repeat disclosed answers. If complete, CONTINUE so the action planner can produce DONE. Return JSON {"decision":"ASK"} or {"decision":"CONTINUE"}; no actions or questions here.'''
ACTION=CONTEXT+'''Return exactly one JSON action from the public affordances:
{"kind":"move","object_id":"visible movable ID","target_id":"container or zone ID"}
{"kind":"cover","object_id":"storage_lid"}
{"kind":"inspect","target_id":"label_fixture"}
{"kind":"report","code":"alpha"} (code must be alpha or beta)
{"kind":"inspect_station","location_id":"public station ID"}
{"kind":"return_home"}
{"kind":"DONE"}
No extra keys. Containers and surfaces differ; move to a zone places on the table, move to a bin places inside. A lid can be parked on its pad; cover closes its storage box. Inventory: count contents and add only the deficit, selecting spare stock only. Exchange: item_a to chosen buffer, item_b to left slot, item_a to right slot; never place in an occupied single-capacity slot. Inspect before reporting a code; do not infer the code from object IDs or user hints. Patrol must return home after both required inspections, even if already physically near home earlier. DONE only after all physical task requirements are satisfied. This action stage cannot ask. When a choice is still unknown in NoAsk, make a reproducible reasonable guess from public candidates rather than refusing or pretending it was confirmed.'''
QUESTION=CONTEXT+'''Generate one concise natural question about unresolved public preference_slots. Return only JSON:
{"type":"select","text":"Your question","requests":[{"role":"public slot role","candidate_ids":["all candidates for this role"]}]}
You may instead use {"type":"confirm","text":"...","requests":[{"role":"role","candidate_id":"one candidate"}]} or {"type":"all_preferences","text":"...","requests":[]}.
Request only the needed information, do not disclose or invent hidden answers. Do not ask the user to repeat an already answered choice.'''


def prompt_hashes():return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in [('gate',GATE),('action',ACTION),('question',QUESTION)]}


class Planner:
    def __init__(self,client):self.client=client
    def generate_action(self,public):return self.client.json(ACTION,public,stage='action',validator=lambda v:action(v,public),max_tokens=160)
    def generate_question(self,public):return self.client.json(QUESTION,public,stage='question',validator=lambda v:question(v,public),max_tokens=300)


class Gate:
    def __init__(self,client,backend,threshold):self.client,self.backend,self.threshold=client,backend,threshold
    def decide(self,public):
        if self.backend=='jev':
            probability=self.client.noul(public,GATE+'\nDoes missing user information block useful supported task progress NOW?',
                {'true':'ASK: a necessary unresolved user choice now blocks useful task progress.',
                 'false':'CONTINUE: specified work or a useful physical observation can progress, or the task is complete.'})
            return GateResult('ASK' if probability>=self.threshold else 'CONTINUE',probability)
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'decision'}:raise SchemaError('Gate outputs decision only')
            return GateResult(value['decision'])
        return self.client.json(GATE,public,stage='gate',validator=validate,max_tokens=64)


def components(method,deepseek,jev,threshold):
    planner=Planner(deepseek)
    if method=='llm_noask':return None,planner
    return Gate(jev if method=='jev_gate' else deepseek,'jev' if method=='jev_gate' else 'deepseek',threshold),planner


class ScriptedPlanner:
    def generate_action(self,public):return action(scripted_next(public),public)
    def generate_question(self,public):
        slots=public['observation']['task']['preference_slots'];known=known_choices(public)
        return question(dict(type='select',text='Please choose the unresolved task preference.',requests=[dict(role=r,candidate_ids=v['candidate_ids']) for r,v in slots.items() if r not in known]),public)


class ScriptedGate:
    def decide(self,public):return GateResult('CONTINUE' if scripted_next(public,known_only=True) else 'ASK')
