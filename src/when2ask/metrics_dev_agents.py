"""Extend single-call inference to existing nine-task contracts without hidden labels."""
import copy
import hashlib
from dataclasses import dataclass

from .api import SchemaError
from .nine_task_data import STUDY
from .nine_task_benchmark import MEMORY, components as old_components, view as old_view
from .tabletop_dev_agents import components as tabletop_components
from .tabletop_dev_public import facts_payload
from .unified_dev_agent import UnifiedPolicy as TabletopUnified, SYSTEM_PROMPT as TABLETOP_PROMPT


def view(adapter,history,prior):
    if adapter.family=='study':
        state=adapter.state(history)
        return state,facts_payload(state)
    return old_view(adapter,history,prior)


def components(template,method,deepseek,jev):
    if template in STUDY:return tabletop_components(method,deepseek,jev,'facts_contract',.5)
    return old_components(template,method,deepseek,jev,.5)


@dataclass
class RequestSpec:
    prompt:str
    public:dict
    validator:object
    max_tokens:int


class SpecificationClient:
    """Extract existing public schema validators/prompts. Never performs inference."""
    def json(self,prompt,public,*,stage,validator,max_tokens):
        return RequestSpec(prompt,public,validator,max_tokens)


def build_prompt(template):
    if template in STUDY:return TABLETOP_PROMPT
    if template=='find_and_approach':
        from .navigation_agents import CONTEXT,GATE,ACTION,QUESTION
        gate=GATE.removeprefix(CONTEXT)
        for old,new in [
            ('Return ASK or CONTINUE\nonly.','Choose the question/action branch internally.'),
            ('A complete task must CONTINUE to allow DONE.','A complete task should output DONE.'),
            ('No action or question here.','')]:
            if old not in gate:raise ValueError('Navigation gate contract drift')
            gate=gate.replace(old,new)
    else:
        from .task6_agents import CONTEXT,GATE,ACTION,QUESTION
        if template in MEMORY:
            from .memory_dev_agents import Profile
            prompts=Profile().prompts();GATE,ACTION,QUESTION=prompts['gate'],prompts['action'],prompts['question']
        gate=GATE.removeprefix(CONTEXT)
        for old,new in [
            ('Decide ASK or CONTINUE only, before any action planning.','Decide whether to ask internally before selecting the output.'),
            ('If complete, CONTINUE so the action planner can produce DONE.','If complete, choose DONE in the action format.'),
            ('Return JSON {"decision":"ASK"} or {"decision":"CONTINUE"}; no actions or questions here.','')]:
            if old not in gate:raise ValueError('Six-task gate contract drift')
            gate=gate.replace(old,new)
    memory=template in MEMORY
    ending=('For an action or DONE, return the exact working_choices, completion_assessment, remaining_plan object defined above. Only its FIRST model-selected action executes; the next round observes and decides again. Do not wrap this action-plan object in kind/action/plan fields.' if memory else
            'For an action or DONE, return the exact action JSON defined above directly, with no wrapper.')
    return CONTEXT+'''You are a UNIFIED robot policy. Use ONE model response to choose a complete ASK question, a physical action, or DONE. There is no separate Gate or second question/action model call. Use only the supplied public information and history.
The timing policy governs the top-level choice. The ACTION rules below apply only when you choose not to ask; their references to AFTER CONTINUE or an action stage that cannot ask do not prohibit top-level ASK. The QUESTION rules apply only inside an ASK question. No standalone CONTINUE output.
TIMING POLICY
'''+gate+'\nCONDITIONAL ACTION RULES\n'+ACTION.removeprefix(CONTEXT)+'\nCONDITIONAL QUESTION RULES\n'+QUESTION.removeprefix(CONTEXT)+'''
FINAL WIRE FORMAT: exactly one JSON object. For ASK return {"kind":"ASK","question":{the complete question object in the QUESTION schema above}}. No physical action in an ASK response, and no separate question-generation call.
'''+ending+'\nNo private score, prescribed next action or forced completion is provided.\n'


class Unified:
    def __init__(self,template,client):
        self.template,self.client=template,client;self.last_model_plan=None;self.last_output=None

    def decide(self,state):
        if self.template in STUDY:
            result=TabletopUnified(self.client).decide(state)
            self.last_output=result.to_dict()
            return result.question,result.action
        # Bind the SAME existing validators and native action schema, including
        # the v6 memory planner's public completion reasoning. No extra model,
        # private semantic validator, cached action or action rewrite is added.
        _,planner=components(self.template,'llm_noask',SpecificationClient(),None)
        action_spec=planner.generate_action(state)
        question_spec=planner.generate_question(state)
        def parse(value):
            if not isinstance(value,dict):raise SchemaError('Unified output must be one JSON object')
            if value.get('kind')=='ASK':
                if set(value)!={'kind','question'}:raise SchemaError('ASK contains exactly kind and question')
                result=(question_spec.validator(value['question']),None)
            else:
                result=(None,action_spec.validator(value))
                self.last_model_plan=copy.deepcopy(getattr(planner,'last_model_plan',None))
            self.last_output=copy.deepcopy(value)
            return result
        return self.client.json(build_prompt(self.template),action_spec.public,stage='unified',validator=parse,
            max_tokens=max(action_spec.max_tokens,question_spec.max_tokens))


def prompt_hashes():
    from .nine_task_data import TEMPLATES
    return {t:hashlib.sha256(build_prompt(t).encode()).hexdigest() for t in TEMPLATES}
