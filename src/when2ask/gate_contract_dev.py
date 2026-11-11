"""Independent Gate Dev v7 factors. Public-only; no score/oracle/next-action input."""
import copy
import hashlib
from dataclasses import dataclass
from .buffer_planner_dev import Gate as ExistingGate
from .memory_dev_agents import Profile as V6Profile

CONTRACT='''Decide whether missing USER INFORMATION prevents useful, supported task progress NOW. Use only the public instruction, measurements and dialogue. Return a gate decision, never an action or a question.
A physically executable action is not necessarily supported by the user's instructions. Affordances list legal motor commands; they do not authorize guessing an unresolved user preference. An agent's own working guess is not a disclosed preference. Do not treat the ability to move either candidate as evidence that either choice is justified.
CONTINUE when at least one useful required action is supported independently of unresolved preferences, including a known subgoal or a required physical observation. A future missing choice does not block earlier specified work. A direct observation can reveal a world fact but cannot reveal a personal preference. Do not ask for a fact that a useful required sensing action can obtain.
ASK when useful unfinished work now requires choosing among unresolved user-controlled alternatives and no independent supported subgoal or useful observation is available. Ask only for missing information; reuse disclosed answers.
When the public physical requirements have already been carried out under the current working selection, CONTINUE so the shared action planner can return DONE. Unknown preference correctness after a guessed completion does not authorize endless confirmation or restarting. Do not ask merely because an unresolved role exists.
Use the same criterion for every task and backend. No private preferences, evaluator labels, prescribed next action or model-generated action proposal are available here.'''
QUERY='Does missing user information block useful supported task progress NOW?'
CRITERIA={'true':'ASK: a necessary unresolved user choice now blocks useful task progress.',
          'false':'CONTINUE: specified work or a useful physical observation can progress, or the task is complete.'}


def compact(public):
    """Remove motor geometry and redundant prose; preserve public task facts.

    No task-specific branching, preference-dependent action selection, blocked-role
    label, completion verdict, expected decision or hidden data is introduced.
    """
    value=copy.deepcopy(public);obs=value['observation'];summary=value['public_summary']
    obs['objects']={k:{f:v for f,v in obj.items() if f in ('category','color')} for k,obj in obs['objects'].items()}
    for key in ('containers','zones'):
        obs[key]={r:{f:v for f,v in data.items() if f in ('contents','contents_observed')} for r,data in obs[key].items()}
    keep={'simulation_step','task','objects','containers','zones','held_object','affordances','sensor','inspections','reports'}
    value['observation']={k:v for k,v in obs.items() if k in keep}
    summary_keep={'current_regions','observed_locations','object_memory','goal_requirements','required_final_relations',
        'lid_geometry','confirmed_choices','own_working_choices','preference_candidates','unresolved_roles',
        'observed_region_visits','latest_action_by_object','action_history_coverage'}
    value['public_summary']={k:v for k,v in summary.items() if k in summary_keep}
    return value


@dataclass(frozen=True)
class GateProfile:
    compact_state:bool=False
    explicit_contract:bool=False
    @property
    def name(self):return f's{int(self.compact_state)}c{int(self.explicit_contract)}'
    def serialize(self,public):return compact(public) if self.compact_state else copy.deepcopy(public)
    def prompts(self):return dict(gate=CONTRACT if self.explicit_contract else V6Profile().prompts()['gate'])
    def hashes(self):return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts().items()}


class Gate:
    def __init__(self,client,backend,threshold,profile):
        self.client,self.backend,self.threshold,self.profile=client,backend,threshold,profile;self.last_payload=None
    def decide(self,public):
        self.last_payload=self.profile.serialize(public)
        if self.profile.explicit_contract and self.backend=='deepseek':
            from .agents import GateResult
            from .api import SchemaError
            def validate(value):
                if not isinstance(value,dict) or set(value)!={'decision'}:raise SchemaError('Gate outputs decision only')
                return GateResult(value['decision'])
            return self.client.json(CONTRACT+'\nReturn only JSON {"decision":"ASK"} or {"decision":"CONTINUE"}.',
                self.last_payload,stage='gate',validator=validate,max_tokens=64)
        return ExistingGate(self.client,self.backend,self.threshold,self.profile).decide(self.last_payload)
