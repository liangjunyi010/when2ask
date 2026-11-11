"""Independent Dev v6 shared planner; unchanged Gate criterion/threshold."""
import copy
import hashlib
from .api import SchemaError
from .buffer_planner_dev import Gate
from .grounded_dev_agents import NOTE
from .task6_agents import CONTEXT,GATE,QUESTION
from .task6_protocol import action,question,known_choices
from .memory_dev_public import PROFILE

PLAN=CONTEXT+'''You are the SHARED Dev v6 action planner, called only AFTER CONTINUE. Act from the CURRENT public observation and observation memory. Never restart an already achieved task from its initial instruction. Think through final requirements BEFORE selecting another physical action.
Visibility is not location: observed_locations includes current region-sensor membership even when grasp affordances omit that body. object_memory explicitly separates observed_now, remembered_occluded and unknown. An object omitted under a closed lid has not disappeared. Remembered facts have observation steps and are uncertain, not new vision. New measured facts and failed-action invalidations override memories. Never open the box merely to make an already-delivered object reappear in the movable-object list.
Retrieval: deliver the chosen item to delivery_pad, keep the other inside, then restore the lid. Read the delivery-zone measurement, the other item's last observed box membership, the observed visit chronology, latest cover outcome and CURRENT lid AABB geometry. If delivery is still observed, the other item was observed inside before a successful cover, no later disturbance invalidated that memory, the lid currently spans the opening at the rim and the robot has released it, the public evidence supports finishing. Do not reopen solely to verify a deliberately occluded item. A parked lid means restoration is pending. A prior cover success alone cannot override a currently displaced lid or missing delivery. Return DONE when the public requirements are met under the working selection; do not claim the unknown private preference was correct.
Exchange: required_final_relations fixes the absolute final destinations: item_a to task.right and item_b to task.left. The initial positions in the instruction are not goals. Check BOTH current relation measurements, empty buffer pads, the observed parking/placement history and release. Once those relations are satisfied, exchange is finished; performing another exchange would undo the goal. Preserve each already satisfied final relation unless another explicit unmet public requirement requires moving it. Do not move an already-correct object just to create a new action.
Occlusion: move screen to its pad, actually inspect with the physical sensor, report the measured code, then finish. Read observations.inspections, reports and sensor; a user hint is not a physical inspection. Do not re-inspect/re-report a satisfied requirement without contradictory new evidence.
Use disclosed preferences when present; otherwise keep an existing own working choice, or guess reasonably from public preference_candidates. A guess is not a user-confirmed choice. An unknown private preference is not something further physical actions can verify. World-fact roles NEVER go into working_choices; for occlusion_inspection that field is {}.
Return exactly one JSON object:
{"working_choices":{"public preference role":"candidate ID"},"completion_assessment":{"ready_for_done":false,"reason":"Brief explanation grounded in current measurements/memory, and remaining public requirement"},"remaining_plan":[{"kind":"DONE"}]}
working_choices includes every and only public preference_candidates role. completion_assessment is YOUR judgment, not an evaluator label. reason is 1–400 characters. If ready_for_done, choose DONE; otherwise choose the useful next action yourself.
remaining_plan has 1–6 actions, using only CURRENT public affordances and exact schemas: {"kind":"move","object_id":"visible movable ID","target_id":"container or zone ID"}, {"kind":"cover","object_id":"storage_lid"}, {"kind":"inspect","target_id":"label_fixture"}, {"kind":"report","code":"alpha or beta"}, {"kind":"DONE"}. Stop a suffix before actions depending on a future observation. Only the FIRST model-proposed action executes verbatim; the next turn gates and plans again. No hidden data, action cache or automatic completion controller exists. No explanations outside JSON.'''


class Profile:
    name=PROFILE
    def prompts(self):return dict(gate=GATE+NOTE,question=QUESTION+NOTE,action=PLAN)
    def hashes(self):return {k:hashlib.sha256(v.encode()).hexdigest() for k,v in self.prompts().items()}


def prompt_hashes():return Profile().hashes()


class Planner:
    def __init__(self,client):self.client=client;self.last_model_plan=None
    def generate_action(self,public):
        def validate(value):
            if not isinstance(value,dict) or set(value)!={'working_choices','completion_assessment','remaining_plan'}:raise SchemaError('Use exactly working_choices, completion_assessment, remaining_plan')
            choices=value['working_choices'];candidates=public['public_summary']['preference_candidates'];known=known_choices(public)
            if not isinstance(choices,dict) or set(choices)!=set(candidates):raise SchemaError('working_choices includes only and all preference roles; occlusion uses {}')
            if any(choices[r] not in candidates[r] or (r in known and choices[r]!=known[r]) for r in choices):raise SchemaError('Use public candidates and preserve disclosed preferences')
            assessment=value['completion_assessment']
            if not isinstance(assessment,dict) or set(assessment)!={'ready_for_done','reason'} or type(assessment['ready_for_done']) is not bool or not isinstance(assessment['reason'],str) or not 1<=len(assessment['reason'])<=400:
                raise SchemaError('completion_assessment requires boolean ready_for_done and 1–400 character reason')
            plan=value['remaining_plan']
            if not isinstance(plan,list) or not 1<=len(plan)<=6:raise SchemaError('remaining_plan needs 1–6 exact actions')
            for proposed in plan:action(proposed,public)
            # Deliberately do NOT test progress, completion truth, first-action
            # consistency with assessment, or any hidden preference/evaluator.
            self.last_model_plan=copy.deepcopy(value)
            return plan[0]
        return self.client.json(PLAN,public,stage='action',validator=validate,max_tokens=650)
    def generate_question(self,public):
        return self.client.json(QUESTION+NOTE,public,stage='question',validator=lambda v:question(v,public),max_tokens=300)


def components(method,deepseek,jev,threshold):
    if method not in ('llm_noask','llm_gate','jev_gate'):raise ValueError('Unknown method')
    return (None if method=='llm_noask' else Gate(jev if method=='jev_gate' else deepseek,
        'jev' if method=='jev_gate' else 'deepseek',threshold,Profile())),Planner(deepseek)
