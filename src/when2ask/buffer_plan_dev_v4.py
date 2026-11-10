"""Shared Dev v4 planner: grounded JSON state/goal and a model-generated suffix.

Only the first model-proposed action is returned; every subsequent CONTINUE
calls the planner again AFTER its gate. No action cache, action masking, logical
progress rejection or prescribed next step is used. Grounding checks public facts.
"""
import copy
import hashlib
import json
from dataclasses import dataclass

from .api import SchemaError
from .task6_protocol import action
from .buffer_planner_dev import Profile,Gate,Planner as PreviousPlanner
from .buffer_context_dev_v3 import compact
from .buffer_public_dev import augment

VERSION='buffer_grounded_plan_dev_v4'
PLAN_PROMPT='''You are the SHARED action planner for a robot exchanging two objects using a temporary buffer. This action stage occurs only AFTER the gate has chosen CONTINUE; you cannot ask here. Use only the public instruction, measured observation and public history. No hidden preference or evaluator is available.
Object IDs are permanent. The instruction describes where the objects STARTED; it does not say to restore their initial positions. The PUBLIC final destination of task.item_a is task.right, and the final destination of task.item_b is task.left. A relation currently satisfied should remain satisfied unless a move is necessary for another public goal. A successful old action does not override a later physical observation. A failed action can still change the world.
Generate a short remaining plan FROM THE CURRENT OBSERVED STATE. Never restart the whole exchange from the initial state. Read current region contents. Each slot has capacity one; a buffer is temporary parking. Use a disclosed buffer choice when present. Otherwise keep any already-used buffer as your working choice unless a user answer or actual observation requires reconsideration. A working choice is a guess until the user disclosed it. If a choice is unknown and this action stage must continue, choose a reasonable candidate; the independent evaluator will judge preference correctness. Do not invent a confirmed preference.
Return one JSON object with exactly these fields:
{"current_locations":{"object ID":["region IDs or empty list"]},
 "final_targets":{"object ID":"required final slot ID"},
 "working_buffer":"one public candidate ID",
 "remaining_plan":[{"kind":"move","object_id":"ID","target_id":"region ID"},{"kind":"DONE"}]}
current_locations and final_targets must include BOTH task.item_a and task.item_b using their real IDs. Derive them from observation and the public task, not the example placeholders. current_locations uses measured container/zone contents; an object may have no confirmed region. The plan contains 1–6 actions, and can be [{"kind":"DONE"}] if the physical work is complete. Use only move or DONE action schemas shown, with no extra keys. All model-proposed actions remain subject to real physics. Do not write explanations, confidence or task-success claims. Only the FIRST action will execute; the next turn observes physics and plans again.'''


@dataclass(frozen=True)
class PlanProfile(Profile):
    compact_context:bool=True

    @property
    def name(self):return 'grounded_plan_'+('compact' if self.compact_context else 'append')
    def serialize(self,public):return compact(public) if self.compact_context else augment(public)
    def prompts(self):return {**super().prompts(),'action':PLAN_PROMPT}


class Planner(PreviousPlanner):
    def __init__(self,client,profile):super().__init__(client,profile);self.last_model_plan=None
    def generate_action(self,public,stage='action'):
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'current_locations','final_targets','working_buffer','remaining_plan'}:
                raise SchemaError('Return exactly current_locations, final_targets, working_buffer, remaining_plan')
            obs=public['observation'];task=obs['task']
            regions={**{k:v['contents'] for k,v in obs['containers'].items()},**{k:v['contents'] for k,v in obs['zones'].items()}}
            current={key:[r for r,items in regions.items() if key in items] for key in (task['item_a'],task['item_b'])}
            if value['current_locations']!=current:raise SchemaError('current_locations must match the latest measured container/zone membership for both objects')
            targets={task['item_a']:task['right'],task['item_b']:task['left']}
            if value['final_targets']!=targets:raise SchemaError('final_targets must reflect the public exchange goal, not the initial positions')
            if value['working_buffer'] not in task['buffers']:raise SchemaError('working_buffer must be a public candidate')
            plan=value['remaining_plan']
            if not isinstance(plan,list) or not 1<=len(plan)<=6:raise SchemaError('remaining_plan must contain 1–6 actions')
            for proposed in plan:action(proposed,public)
            # No test here of whether the first action is optimal, advances a
            # goal, or matches any evaluator/private preference. No rewrite.
            self.last_model_plan=copy.deepcopy(value)
            return plan[0]
        return self.client.json(PLAN_PROMPT,public,stage=stage,validator=validate,max_tokens=400)

    def generate_question(self,public):return super().generate_question(public)


def components(method,deepseek,jev,threshold,profile):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    planner=Planner(deepseek,profile)
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',threshold,profile)),planner
