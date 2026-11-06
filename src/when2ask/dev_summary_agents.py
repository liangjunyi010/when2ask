"""Independent Dev-only agents; frozen v3.1 prompts/files are never edited."""
import hashlib

from .agents import GateResult
from .api import SchemaError
from .dev_public_summary import PROFILES, encode
from .study_agents import ACTION_PROMPT, QUESTION_PROMPT, GATE_RULES
from .study_agents import components as original_components
from .study_protocol import StudyAction, StudyQuestion

OLD_INSTRUCTIONS = GATE_RULES + '\nDoes missing user preference information block ALL further useful supported task progress NOW?'
OLD_CRITERIA = {
    'true': 'ASK: unknown preferences block all useful required actions under the stated order.',
    'false': 'CONTINUE: a supported required action or correction is available, or the task is complete.'}

SHORT_INSTRUCTIONS = 'Does the robot need a user preference answer before it can make further progress on this task?'
SHORT_CRITERIA = {
    'true': 'The next unfinished step needs a preference that is not disclosed, and no other required step can proceed using disclosed choices under the stated order. An available arbitrary object is not a user choice.',
    'false': 'A required step can proceed using disclosed object and destination choices under the stated order, or the placements and covering are already complete. Do not ask for future choices while a specified step can proceed.'}


def prompt_hashes(profile):
    instructions, criteria = question_spec(profile)
    import json
    return {k: hashlib.sha256(v.encode()).hexdigest() for k,v in dict(
        action=ACTION_PROMPT, question=QUESTION_PROMPT, gate_instructions=instructions,
        gate_criteria=json.dumps(criteria, sort_keys=True)).items()}


def question_spec(profile):
    if profile not in PROFILES:
        raise ValueError('Unknown independent Dev profile')
    return (SHORT_INSTRUCTIONS, SHORT_CRITERIA) if profile == 'compact_question' else (OLD_INSTRUCTIONS, OLD_CRITERIA)


class DevPlanner:
    def __init__(self, client, profile):
        self.client, self.profile = client, profile

    def generate_question(self, state):
        return self.client.json(QUESTION_PROMPT, encode(state, self.profile), stage='question',
            validator=lambda v: StudyQuestion.parse(v, state))

    def generate_action(self, state):
        return self.client.json(ACTION_PROMPT, encode(state, self.profile), stage='action',
            validator=lambda v: StudyAction.parse(v, state))


class DevJevGate:
    def __init__(self, client, profile, threshold):
        if not 0 <= threshold <= 1:
            raise ValueError('Threshold outside [0,1]')
        self.client, self.profile, self.threshold = client, profile, threshold

    def decide(self, state):
        instructions, criteria = question_spec(self.profile)
        probability = self.client.noul(encode(state, self.profile), instructions, criteria)
        return GateResult('ASK' if probability >= self.threshold else 'CONTINUE', probability)


class DevLLMGate:
    def __init__(self, client, profile):
        self.client, self.profile = client, profile

    def decide(self, state):
        def validate(value):
            if set(value) != {'decision'} or value['decision'] not in ('ASK', 'CONTINUE'):
                raise SchemaError('Gate returns only ASK/CONTINUE')
            return GateResult(value['decision'])
        if self.profile == 'compact_state':
            instructions = GATE_RULES
        else:
            instructions = SHORT_INSTRUCTIONS + '\nASK when: ' + SHORT_CRITERIA['true'] + '\nCONTINUE when: ' + SHORT_CRITERIA['false']
        return self.client.json(instructions + '\nReturn JSON: {"decision":"ASK"} or {"decision":"CONTINUE"}.',
            encode(state, self.profile), stage='gate', validator=validate, max_tokens=64)


def components(method, deepseek, jev, threshold, profile):
    if profile not in PROFILES:
        raise ValueError('Unknown independent Dev profile')
    if profile == 'v3_original':
        return original_components(method, deepseek, jev, threshold)
    planner = DevPlanner(deepseek, profile)
    if method == 'llm_noask':
        return None, planner
    if method == 'llm_gate':
        return DevLLMGate(deepseek, profile), planner
    if method == 'jev_gate':
        return DevJevGate(jev, profile, threshold), planner
    raise ValueError('Unknown method')
