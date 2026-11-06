"""Independent exploratory-search Dev prompts. Frozen tabletop prompts unchanged."""
import hashlib

from .agents import GateResult
from .api import SchemaError
from .navigation_map import LOCATIONS
from .navigation_protocol import goal_observed, parse_action, parse_question

VERSION = 'navigation_search_dev_v1'
CONTEXT = """You control a wheel-driven robot finding a kitchen knife in three known rooms.
The target is static but its location is a WORLD FACT, not a user preference. The robot
starts in the living room. The kitchen is a plausible semantic prior, never an oracle.
Only local range/FOV/line-of-sight perception reveals the target. The known map lists
six open-surface inspection stations. search(location_id) actually drives, orients and
inspects ONE station. A negative station observation does not clear an entire room.
Unseen target coordinates are unavailable. Public user answers are location claims,
not detection, and may be corrected after a genuinely negative inspection. An
initially specified location or earlier answer can be reused without asking again.
Complete only when target_observation exists, distance_to_observed_target_m <= 1.2,
and robot_stopped is true. There is NO grasp, pickup, delivery or language-only success.
Continuing to search can reduce uncertainty. Unknown location does not automatically
require ASK. Compare useful exploration with asking for a hint (one slot, 3s automatic
reply delay; manual reply may take longer). Prefer a plausible, useful local/search
step while confidence is adequate; consider ASK when failed searches or expensive
remaining travel make a user hint valuable. Do not assume one failed search mandates
ASK. NoAsk must keep searching; it cannot ask. Never repeat a confirmed fact without
new contradictory observations. Use the same map and public history for all methods.
"""
GATE = CONTEXT + """Decide whether clarification is useful NOW. Return ASK or CONTINUE
only. If a hint already supports a useful next search, CONTINUE. If the target has
been seen, CONTINUE to approach/finish. A complete task must CONTINUE to allow DONE.
Balance continued autonomous search against an interruption; do not always ask at
the start solely because a target location is unknown. No action or question here.
"""
ACTION = CONTEXT + """You are the shared action planner. Return one JSON object only:
{"kind":"search","location_id":"one known station ID"} OR {"kind":"DONE"}.
Use a public location hint unless contradicted by local inspection. Otherwise search
a plausible unchecked station, then use semantic prior and route_distances_m to choose
useful unchecked stations. If the target is observed but not near, search its observed
location. Avoid repeating a cleared station without a reason. This action stage cannot
ask, even when location is uncertain. DONE requires the physical completion conditions
above. No extra keys, target coordinates, explanations or questions.
"""
QUESTION = CONTEXT + """You are the shared question planner. Ask for the current fixed
location of the knife using a short, natural question. Return exactly this JSON schema:
{"type":"select","text":"Where is the knife?","requests":[{"role":"target_location",
"candidate_ids":["kitchen_counter","kitchen_shelf","living_cabinet","living_table","study_desk","study_shelf"]}]}.
This requests one complete location fact, not six slots. Do not disclose a hidden answer.
"""


def prompt_hashes():
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in
            (('gate', GATE), ('action', ACTION), ('question', QUESTION))}


class NavigationPlanner:
    def __init__(self, client): self.client = client
    def generate_action(self, payload):
        return self.client.json(ACTION, payload, stage='action', validator=parse_action, max_tokens=128)
    def generate_question(self, payload):
        return self.client.json(QUESTION, payload, stage='question', validator=parse_question, max_tokens=300)


class NavigationGate:
    def __init__(self, client, backend, threshold=.5):
        self.client, self.backend, self.threshold = client, backend, threshold
    def decide(self, payload):
        if self.backend == 'jev':
            probability = self.client.noul(payload, GATE + '\nShould the robot ask for a location hint NOW?',
                {'true': 'ASK: the value of a location hint now outweighs another autonomous search and its interruption cost.',
                 'false': 'CONTINUE: useful autonomous exploration or a known-location action is available, or goal is complete.'})
            return GateResult('ASK' if probability >= self.threshold else 'CONTINUE', probability)
        def validate(value):
            if not isinstance(value, dict) or set(value) != {'decision'} or value['decision'] not in ('ASK', 'CONTINUE'):
                raise SchemaError('Navigation gate must return only decision ASK or CONTINUE')
            return GateResult(value['decision'])
        return self.client.json(GATE + '\nReturn JSON {"decision":"ASK"} or {"decision":"CONTINUE"}.',
            payload, stage='gate', validator=validate, max_tokens=64)


def components(method, deepseek, jev, threshold=.5):
    planner = NavigationPlanner(deepseek)
    if method == 'llm_noask': return None, planner
    if method == 'llm_gate': return NavigationGate(deepseek, 'deepseek', threshold), planner
    if method == 'jev_gate': return NavigationGate(jev, 'jev', threshold), planner
    raise ValueError('Unknown navigation method')


class ScriptedPlanner:
    """Free hardware/UI diagnostic. Never described as an LLM or Jev result."""
    def generate_action(self, payload):
        obs = payload['observation']
        if goal_observed(payload): return {'kind': 'DONE'}
        seen = obs['target_observation']
        if seen: return dict(kind='search', location_id=seen['location_id'])
        hint = payload['location_claim']
        if hint and not obs['checked_locations'].get(hint): return dict(kind='search', location_id=hint)
        unchecked = [k for k in LOCATIONS if k not in obs['checked_locations']]
        key = ('kitchen_counter' if 'kitchen_counter' in unchecked else
               min(unchecked, key=lambda k: obs['route_distances_m'][k])) if unchecked else 'kitchen_counter'
        return dict(kind='search', location_id=key)
    def generate_question(self, payload):
        return dict(type='select', text='Where is the kitchen knife now?',
            requests=[dict(role='target_location', candidate_ids=list(LOCATIONS))])


class ScriptedGate:
    def decide(self, payload):
        obs = payload['observation']
        ask = bool(obs['checked_locations']) and not payload['location_claim'] and not obs['target_observation']
        return GateResult('ASK' if ask else 'CONTINUE')
