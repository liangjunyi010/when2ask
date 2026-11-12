"""Two-factor Dev repair: public representation × contract, fixed threshold0.5."""
import hashlib
from dataclasses import dataclass

from .agents import GateResult
from .api import SchemaError
from .protocol import public_payload
from .study_agents import GATE_RULES, ACTION_PROMPT, QUESTION_PROMPT
from .study_protocol import StudyAction, StudyQuestion
from .tabletop_dev_public import facts_payload

VERSION='tabletop_contract_dev_v1'
GATE_ADDENDUM='''
Separate information from physical ability. An available motor command is not necessarily a useful action authorized by the instruction. A guessed preference is still unknown, even after a successful move.
Read the task's CURRENT precedence constraints before judging whether a known later subgoal is available. An order edge means the prerequisite must be satisfied under supported choices before executing the later subgoal. A known cup cannot progress before an unknown block when the instruction says block before cup. Conversely, when order is independent or cup first, execute the supported known cup before asking about a future block or lid. Knowing a lid does not allow covering an unpacked box.
For two containers, a single disclosed cup_destination fixes BOTH destinations. A block already placed in the other container is useful achieved progress; the cup's container may still be empty. A partial task is not a placement mistake. Continue towards remaining supported requirements instead of undoing achieved ones. Reuse all initial choices and answers.
Use the same rule for every state and both Gate backends. Do not ask simply because some future preference is unresolved. Return only ASK or CONTINUE; the action planner chooses actions and DONE.
'''
ACTION_ADDENDUM='''
Preserve achieved progress. Interpret cup_destination as an ABSOLUTE final cup destination; the block's absolute final destination is the other container. These final destinations do not swap as the robot moves. A selected block already inside its correct other container is a satisfied partial goal, even while the cup's container is empty. Do not remove it as a repair merely because the cup is not placed yet. Finish the remaining cup placement. Do not restart a completed exchange or repeat an achieved placement.
Before repairing, identify a concrete contradiction between a CURRENT measured relation and a disclosed/working final relation. Incomplete work alone is not a contradiction. Keep a consistent own working selection when a preference remains unknown; own actions are not user confirmation. If all final measured relations, release, exclusion and public order requirements are satisfied under that working selection, return DONE. If the user later discloses a different choice, real corrective actions may be required.
Respect the publicly stated order, not a habitual cup-first routine. In a block-first task the chosen block must be placed first, then the chosen cup. Cover only after both. This planner stage cannot ask; if an undisclosed choice is still required, guess from public candidates and keep the guess consistent. No hidden score, forced completion test or action replacement is supplied.
'''
QUESTION_ADDENDUM='''
Read both the initial instruction and public answers. Ask only roles still unknown. One cup_destination reply also resolves where the block goes; do not separately ask a block destination. Keep the natural question and structured public roles/candidate IDs consistent.
'''
CRITERIA={'true':'ASK: unknown preferences block all useful required actions under the stated order.',
          'false':'CONTINUE: a supported required action or correction is available, or the task is complete.'}
QUERY='Does missing user preference information block ALL further useful supported task progress NOW?'


@dataclass(frozen=True)
class Profile:
    facts:bool
    contract:bool

    @property
    def name(self):return ('facts' if self.facts else 'raw')+'_'+('contract' if self.contract else 'legacy')

    def serialize(self,state):return facts_payload(state) if self.facts else public_payload(state)

    def prompts(self):
        return dict(gate=GATE_RULES+(GATE_ADDENDUM if self.contract else ''),
            action=ACTION_PROMPT+(ACTION_ADDENDUM if self.contract else ''),
            question=QUESTION_PROMPT+(QUESTION_ADDENDUM if self.contract else ''))

    def hashes(self):return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts().items()}


PROFILES={p.name:p for p in [Profile(False,False),Profile(True,False),Profile(False,True),Profile(True,True)]}
SELECTED='facts_contract'  # Declared before all diagnostic/full Dev calls; no outcome selection.


class Gate:
    def __init__(self,client,backend,profile,threshold=.5):
        if not 0<=threshold<=1:raise ValueError('Invalid threshold')
        self.client,self.backend,self.profile,self.threshold=client,backend,profile,threshold
        self.last_payload=None

    def decide(self,state):
        self.last_payload=self.profile.serialize(state);prompt=self.profile.prompts()['gate']
        if self.backend=='jev':
            p=self.client.noul(self.last_payload,prompt+'\n'+QUERY,CRITERIA)
            return GateResult('ASK' if p>=self.threshold else 'CONTINUE',p)
        def parse(value):
            if not isinstance(value,dict) or set(value)!={'decision'} or value['decision'] not in ('ASK','CONTINUE'):
                raise SchemaError('Gate returns only decision ASK or CONTINUE')
            return GateResult(value['decision'])
        return self.client.json(prompt+'\nReturn JSON: {"decision":"ASK"} or {"decision":"CONTINUE"}.',
            self.last_payload,stage='gate',validator=parse,max_tokens=64)


class Planner:
    def __init__(self,client,profile):self.client,self.profile=client,profile
    def generate_question(self,state):
        return self.client.json(self.profile.prompts()['question'],self.profile.serialize(state),stage='question',
            validator=lambda v:StudyQuestion.parse(v,state),max_tokens=500)
    def generate_action(self,state):
        return self.client.json(self.profile.prompts()['action'],self.profile.serialize(state),stage='action',
            validator=lambda v:StudyAction.parse(v,state),max_tokens=500)


def components(method,deepseek,jev,profile=SELECTED,threshold=.5):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    p=PROFILES[profile];planner=Planner(deepseek,p)
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',p,threshold)),planner
