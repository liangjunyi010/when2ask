"""Versioned, shared structured Planner. Optional; default agents stay unchanged."""
import copy
import hashlib
from .api import SchemaError
from .buffer_planner_dev import Gate
from .task6_agents import CONTEXT,GATE,QUESTION
from .task6_protocol import action,question,known_choices
from .grounded_dev_public import PROFILE,facts

NOTE='''\nThe public_summary restates measured state and public goal requirements, not an evaluator or next action. Own working choices are not user-confirmed. Unobserved contents are unknown, not empty. Apply the original missing-information criterion. Useful physical observation can precede asking; a user hint never substitutes for required inspection.'''
PLAN=CONTEXT+'''You are the SHARED Dev action planner, called only AFTER CONTINUE. Generate a short remaining plan FROM THE CURRENT OBSERVED STATE, not from the initial arrangement. Preserve already satisfied final relations unless a move is needed for another requirement. Current observations override earlier successes; failed actions may move objects. A working guess is not a user-confirmed preference. Use known choices when available; otherwise choose reasonably from public candidates. Keep an earlier working choice unless new evidence contradicts it. Do not ask at the action stage.
Exchange: original slot locations describe the START, not the final goal. Use public_summary.goal_requirements.final_targets. Keep the other pad unused, respect capacity one, and empty temporary parking by the end.
Retrieval: park the lid before accessing contents. Covered/unobserved contents are UNKNOWN, not absent. Re-observe after opening. Deliver the chosen item, leave the other inside, then cover the box again. A parked lid is not a restored lid. Read the latest lid AABB/opening geometry.
Occlusion: clear the screen, physically inspect, then report the actual measured code. A user reply or guessed code is not physical inspection. Inspection results are authoritative world evidence; do not ask for information obtainable by a useful required inspection.
Return exactly JSON with these four fields:
{"current_locations":{"visible movable ID":["measured region IDs or empty list"]},"goal_requirements":{},"working_choices":{"public preference role":"candidate ID"},"remaining_plan":[{"kind":"DONE"}]}
Copy current_locations and goal_requirements exactly from public_summary; they restate public facts. working_choices contains preference roles only, with candidate IDs, and includes every preference role. Use disclosed values when known. World-fact roles are not preferences and must not be guessed here.
remaining_plan contains 1–6 actions from these exact schemas: {"kind":"move","object_id":"visible movable ID","target_id":"container or zone ID"}, {"kind":"cover","object_id":"storage_lid"}, {"kind":"inspect","target_id":"label_fixture"}, {"kind":"report","code":"alpha or beta"}, {"kind":"DONE"}.
Use only CURRENT public affordances. Stop the plan before an action that needs an as-yet-unobserved object or inspection code; replan after new observation. A plan need not end in DONE. If all observable requirements are complete, return [{"kind":"DONE"}]. Only the FIRST action executes verbatim. Every later turn gates and plans again; no cached actions execute. Do not write explanations or success claims.'''


class Profile:
    name=PROFILE
    def prompts(self):return dict(gate=GATE+NOTE,question=QUESTION+NOTE,action=PLAN)
    def hashes(self):return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts().items()}


def prompt_hashes():return Profile().hashes()


class Planner:
    def __init__(self,client):self.client=client;self.last_model_plan=None
    def generate_action(self,public):
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'current_locations','goal_requirements','working_choices','remaining_plan'}:
                raise SchemaError('Return exactly current_locations, goal_requirements, working_choices, remaining_plan')
            _,locations,goal=facts(public)
            if value['current_locations']!=locations:raise SchemaError('Copy current_locations exactly from latest public_summary')
            if value['goal_requirements']!=goal:raise SchemaError('Copy goal_requirements exactly from public_summary')
            slots=public['observation']['task']['preference_slots'];known=known_choices(public);choices=value['working_choices']
            roles={k for k,v in slots.items() if v['kind']=='preference'}
            if not isinstance(choices,dict) or set(choices)!=roles:raise SchemaError('working_choices contains all and only preference roles, not world facts')
            if any(choices[r] not in slots[r]['candidate_ids'] or (r in known and choices[r]!=known[r]) for r in roles):raise SchemaError('Use a public candidate and preserve disclosed choices')
            plan=value['remaining_plan']
            if not isinstance(plan,list) or not 1<=len(plan)<=6:raise SchemaError('remaining_plan needs 1–6 actions')
            for proposed in plan:action(proposed,public)
            # No progress/optimality/private-truth check; regressive actions are
            # not rejected or rewritten. Existing physical controller evaluates.
            self.last_model_plan=copy.deepcopy(value)
            return plan[0]
        return self.client.json(PLAN,public,stage='action',validator=validate,max_tokens=650)
    def generate_question(self,public):
        return self.client.json(QUESTION+NOTE,public,stage='question',validator=lambda v:question(v,public),max_tokens=300)


def components(method,deepseek,jev,threshold):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',threshold,Profile())),Planner(deepseek)
