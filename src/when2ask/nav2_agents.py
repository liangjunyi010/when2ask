"""Same planner/public state for every method; preregistered gate-contract ablation."""
import hashlib

from .agents import GateResult
from .api import SchemaError
from .navigation_protocol import parse_action,parse_question

CONTEXT='''Known-map local-perception find-and-approach task. Use only the supplied public state.
Six stations form the EXHAUSTIVE search space for one static target. A station search
physically drives, turns and inspects that station. A negative inspection eliminates
that station only. Use the supplied uniform planning prior, conditioning on observed
negatives; do not invent a kitchen-first prior. Simulator location answers are exact
and reliable; one complete station hint costs one slot. A hint is not physical detection.
Complete requires target_observation, measured distance <=1.2m and robot_stopped.
The cost_contract specifies actual response delay, robot speed, interruption cost and
budgets. Nominal motion estimates are approximations, not oracle success labels.
Physical success is required. Among feasible policies minimize expected remaining
operational seconds: robot motion + response waiting + interruption seconds per slot.
API tokens/latency are measured separately. Never use hidden target/evaluator data.
'''
EXCLUSIVE='''Decide ASK or CONTINUE only, before any action/question is generated.
ASK means a location question NOW has LOWER expected remaining operational cost than
continuing autonomous search, including future searches/possible later questions.
CONTINUE means continuing has equal or lower expected remaining cost, or task complete.
These alternatives are mutually exclusive. The existence of a useful search alone
does not settle the comparison. Neither missing information nor one failed search
automatically mandates ASK. Prefer CONTINUE on a tie. Reuse a valid location answer;
do not pay again for information already known/inferred. If observed/complete continue.
'''
OVERLAP='''Decide ASK or CONTINUE only, before any action/question is generated.
ASK when a location hint's value outweighs another autonomous search and interruption.
CONTINUE when useful autonomous exploration or a known-location action is available,
or task complete. Prefer a plausible useful search while confidence is adequate.
Do not assume one failed search mandates ASK. Reuse earlier location answers.
'''
ACTION=CONTEXT+'''Shared ACTION planner: return one JSON object, exactly {"kind":"search","location_id":"known station ID"}
or {"kind":"DONE"}. This action stage cannot ask. Use an observed or reliably disclosed
location first; otherwise search unchecked stations according to public probability
and travel/time cost. Avoid unnecessary repeats. DONE requires measured completion.
No question, explanation or extra keys.
'''
QUESTION=CONTEXT+'''Shared QUESTION planner: ask one short natural question for the
knife's location. Return one JSON object only: {"type":"select","text":"Where is the knife?","requests":[
{"role":"target_location","candidate_ids":["kitchen_counter","kitchen_shelf","living_cabinet","living_table","study_desk","study_shelf"]}]}.
'''
CRITERIA={
    'cost_exclusive':dict(true='ASK now has strictly lower expected remaining operational cost, including waiting and interruption, than continuing.',
        false='CONTINUE has equal or lower expected remaining operational cost than ASK now, or the task is complete.'),
    'overlap_control':dict(true='The value of a location hint now outweighs another autonomous search and interruption.',
        false='Useful autonomous exploration or a known-location action is available, or task complete.')}


def hashes():
    import json
    return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in dict(action=ACTION,question=QUESTION,
        cost_exclusive=CONTEXT+EXCLUSIVE,overlap_control=CONTEXT+OVERLAP,criteria=json.dumps(CRITERIA,sort_keys=True)).items()}


class Gate:
    def __init__(self,client,backend,contract='cost_exclusive',threshold=.5):
        self.client,self.backend,self.contract,self.threshold=client,backend,contract,threshold
    def decide(self,public):
        prompt=CONTEXT+(EXCLUSIVE if self.contract=='cost_exclusive' else OVERLAP)
        if self.backend=='jev':
            p=self.client.noul(public,prompt+'\nShould the robot ask for a location hint NOW?',CRITERIA[self.contract])
            return GateResult('ASK' if p>=self.threshold else 'CONTINUE',p)
        def parse(v):
            if not isinstance(v,dict) or set(v)!={'decision'} or v['decision'] not in ('ASK','CONTINUE'):
                raise SchemaError('Gate returns only decision ASK/CONTINUE')
            return GateResult(v['decision'])
        return self.client.json(prompt+'\nReturn JSON {"decision":"ASK"} or {"decision":"CONTINUE"}.',public,
            stage='gate',validator=parse,max_tokens=64)


class Planner:
    def __init__(self,client):self.client=client
    def generate_action(self,public):return self.client.json(ACTION,public,stage='action',validator=parse_action,max_tokens=128)
    def generate_question(self,public):return self.client.json(QUESTION,public,stage='question',validator=parse_question,max_tokens=300)


def components(method,deepseek,jev,contract='cost_exclusive',threshold=.5):
    planner=Planner(deepseek)
    if method=='llm_noask':return None,planner
    if method=='llm_gate':return Gate(deepseek,'deepseek',contract,threshold),planner
    if method=='jev_gate':return Gate(jev,'jev',contract,threshold),planner
    raise ValueError('Unknown method')
