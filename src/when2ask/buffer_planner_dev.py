"""Isolated shared Planner repair and factorial ablation profiles. V1 untouched."""
import hashlib
from dataclasses import dataclass

from . import task6_agents as v1
from .agents import GateResult
from .api import SchemaError
from .task6_protocol import action,question
from .buffer_public_dev import augment

VERSION='buffer_shared_planner_dev_v2'
REPAIR='''\nDev state-grounding rules, shared by every method:
Keep object IDs and explicit final destination relations fixed throughout execution. An initial instruction saying an object starts in a slot is not a requirement to put it back there. The latest physical observation is authoritative. Read measured current contents and previous action outcomes before choosing an action; a history entry saying placed describes that time, not all future times.
Preserve a final relation that is currently satisfied unless moving it is necessary to satisfy another explicit requirement. Avoid undoing useful progress or alternating an object between its initial and final locations. Check whether a single-capacity target is occupied. A failed placement may still change the physical state; reassess the new observation, rather than blindly repeating it.
An agent's earlier choice is a working assumption, not a confirmed user preference. If clarification is unavailable, keep the same reasonable working assumption across steps unless a new observation or disclosed answer contradicts it. Do not reinterpret every round as a fresh task. Never describe an assumed choice as user-confirmed. Physical completion under a guess does not establish preference correctness; the independent evaluator will check that.
The public_summary, when present, only restates observed regions, public final relations and chronological history. It contains no hidden preference, task score, prescribed next action or oracle. Continue to select the action yourself. Return DONE when the observable final relations and remaining public physical requirements are complete; do not keep moving a correctly placed object merely because an undisclosed preference was guessed.
'''
GATE_NOTE='''\nPublic summaries distinguish user-confirmed choices from your own prior assumptions. A working assumption is not a disclosed preference. Measured progress is public evidence, not a hidden success label. Apply the same ASK/CONTINUE criterion and threshold as v1; do not ask merely to verify a completed action.'''


@dataclass(frozen=True)
class Profile:
    summary:bool
    planner_repair:bool

    @property
    def name(self):return f's{int(self.summary)}p{int(self.planner_repair)}'

    def serialize(self,public):return augment(public) if self.summary else public

    def prompts(self):
        return dict(action=v1.ACTION+(REPAIR if self.planner_repair else ''),
            question=v1.QUESTION+(GATE_NOTE if self.planner_repair else ''),
            gate=v1.GATE+(GATE_NOTE if self.planner_repair else ''))

    def hashes(self):return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts().items()}


class Planner:
    def __init__(self,client,profile):self.client,self.profile=client,profile
    def generate_action(self,public,stage='action'):
        return self.client.json(self.profile.prompts()['action'],public,stage=stage,
            validator=lambda value:action(value,public),max_tokens=160)
    def generate_question(self,public):
        return self.client.json(self.profile.prompts()['question'],public,stage='question',
            validator=lambda value:question(value,public),max_tokens=300)


class Gate:
    def __init__(self,client,backend,threshold,profile):self.client,self.backend,self.threshold,self.profile=client,backend,threshold,profile
    def decide(self,public):
        instructions=self.profile.prompts()['gate']
        if self.backend=='jev':
            probability=self.client.noul(public,instructions+'\nDoes missing user information block useful supported task progress NOW?',
                {'true':'ASK: a necessary unresolved user choice now blocks useful task progress.',
                 'false':'CONTINUE: specified work or a useful physical observation can progress, or the task is complete.'})
            return GateResult('ASK' if probability>=self.threshold else 'CONTINUE',probability)
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'decision'}:raise SchemaError('Gate outputs decision only')
            return GateResult(value['decision'])
        return self.client.json(instructions,public,stage='gate',validator=validate,max_tokens=64)


def components(method,deepseek,jev,threshold,profile):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    planner=Planner(deepseek,profile)
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',threshold,profile)),planner
