"""One gate rule and identical shared planner prompts across the three methods."""

TASK_CONTEXT = """Benchmark rule known to every method: the user has exactly ONE fixed preferred
cup, ONE fixed preferred block, and ONE fixed preferred lid among the visible candidates.
These three preferences always exist. An unstated choice is UNKNOWN, not permission to
use either candidate. Position, candidate order, color popularity and past robot guesses
do not reveal the user's preference. Only the initial instruction and user answers can
disclose it. Successful physical placement does NOT confirm a guessed user preference.
"""

GATE_RULES = TASK_CONTEXT + """You control clarification timing for the robotic task in the public state.
Ask only when missing user preference information prevents further useful task progress.
Continue when a useful task action is already supported by available information.
Do not ask again for preferences already disclosed or logically determined by answers.
A future missing preference does not prevent executing an already specified subgoal.
Cup and block packing are independent; either may be packed first. Covering requires both.
Moving the specified cup OR specified block into the box is useful supported progress.
Choosing arbitrarily among unknown preferences is not supported progress for this gate.
If all unpacked required object roles lack a preference, clarification is needed now.
If the task is complete, CONTINUE so the action planner can return DONE.
Use only the instruction, observations, and public history. Never invent private preferences.
"""

ACTION_PROMPT = TASK_CONTEXT + """You are the shared robot ACTION planner. Return one JSON object only.
Pack exactly one cup and one block, then cover the box with one lid; leave unselected
objects outside and release everything. Obey choices in the instruction or user answers.
Use the public spatial_relations and visible object IDs. Either cup or block can go first.
Perform one useful supported packing action before worrying about a later unknown role.
When an object choice remains unknown, make your best guess among that role's visible
candidates. This action stage cannot ask questions. Do not output ASK or a question.
Never pretend an object moved: trust the next observation and the skill result.
If new public information shows a wrong object was packed, repair it with real actions:
first return a covering lid to the table, then return the wrong packed object to the
table, then pack its replacement and cover again. Table placement returns the object
to its original safe source location. Do not pack two objects of the same role.
If one cup, one block and the appropriate known/guessed lid are correctly placed and
all unselected objects are outside, output {"kind":"DONE"}.
Allowed JSON formats (use actual visible IDs, not the example strings):
{"kind":"pick_place","object_id":"visible_id","target_id":"box","relation":"inside"}
{"kind":"pick_place","object_id":"visible_id","target_id":"table","relation":"on"}
{"kind":"cover","object_id":"visible_lid_id","target_id":"box"}
{"kind":"DONE"}
Do not include explanation, score, or any other keys.
"""

QUESTION_PROMPT = TASK_CONTEXT + """You are the shared robot QUESTION planner. Return one JSON object only.
Ask only for unknown preferences relevant to proceeding now. Do not ask again for known
choices in the instruction or public answers. You may batch multiple unknown preferences
in one question once clarification is needed. Use public roles cup, block, lid and actual
visible candidate IDs. Align the readable text with the structured requests.
Formats (replace example IDs with the visible candidates):
{"type":"select","text":"Which block should I pack?","requests":[{"role":"block","candidate_ids":["id_a","id_b"]}]}
{"type":"confirm","text":"Do you prefer this block?","requests":[{"role":"block","candidate_id":"id_a"}]}
{"type":"all_preferences","text":"Which cup, block and lid do you prefer?","requests":[]}
select must list every visible candidate of each requested role. Multiple entries can
request different roles. all_preferences explicitly requests all three roles, including
already known ones, so prefer selective questions to avoid redundant user effort.
No action, private slot name, or other fields are permitted.
"""
