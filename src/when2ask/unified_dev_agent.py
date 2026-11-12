"""Independent one-call policy. No defaults, frozen prompts or controllers change."""
import hashlib
from dataclasses import dataclass

from .api import SchemaError
from .study_agents import CONTEXT, GATE_RULES, ACTION_PROMPT, QUESTION_PROMPT
from .study_protocol import StudyAction, StudyQuestion
from .tabletop_dev_agents import GATE_ADDENDUM, ACTION_ADDENDUM, QUESTION_ADDENDUM
from .tabletop_dev_public import facts_payload

VERSION = 'unified_deepseek_dev_v1'


def build_prompt():
    # Reuse the repaired contract verbatim except for the output routing that
    # necessarily changes when classification and generation share one call.
    timing = (GATE_RULES.removeprefix(CONTEXT) + GATE_ADDENDUM)
    replacements = {
        'You decide clarification TIMING, returning ASK or CONTINUE only.':
            'Decide clarification timing internally before selecting your output.',
        'When complete CONTINUE\nso the action planner can emit DONE. Do not output an action or a question.':
            'When complete, output DONE.',
        'Return only ASK or CONTINUE; the action planner chooses actions and DONE.':
            'In this unified policy, directly output the question, action, or DONE yourself.',
    }
    for old, new in replacements.items():
        if old not in timing:
            raise RuntimeError('Upstream contract changed; version this Dev prompt explicitly')
        timing = timing.replace(old, new)
    action = ACTION_PROMPT.removeprefix(CONTEXT) + ACTION_ADDENDUM
    question = QUESTION_PROMPT.removeprefix(CONTEXT) + QUESTION_ADDENDUM
    return (CONTEXT + '''You are a UNIFIED robot policy. Make exactly ONE model response per task round.
Choose between asking the user, executing one physical action, and finishing. There is no separate Gate call and no second question/action generation call. Use only the provided public state and history. Do not output a standalone CONTINUE decision.
The following timing policy governs whether to ask. The ACTION rules apply only if you choose a physical action or DONE. The QUESTION rules apply only to the nested question if you choose ASK. References to an action stage cannot prohibit ASK at this top-level choice.
\nTIMING POLICY\n''' + timing + '\nCONDITIONAL ACTION RULES\n' + action
        + '\nCONDITIONAL QUESTION RULES\n' + question + '''
FINAL WIRE FORMAT (one JSON object, no explanation or additional keys):
For ASK, return {"kind":"ASK","question":{"type":"select","text":"Your question","requests":[{"role":"public role","candidate_ids":["all public candidates"]}]}}. The nested question may also use the exact confirm or all_preferences formats above.
For a physical action, return the exact pick_place or cover object above directly, without a wrapper.
For completion, return {"kind":"DONE"} directly. Completion is your judgment; no private score or automatic success signal is provided. Do not emit ASK without a complete question. Do not emit both a question and a physical action.
''')


SYSTEM_PROMPT = build_prompt()


@dataclass(frozen=True)
class UnifiedResult:
    kind: str
    question: StudyQuestion | None = None
    action: StudyAction | None = None

    def to_dict(self):
        return ({'kind': 'ASK', 'question': self.question.to_dict()}
                if self.kind == 'ASK' else
                {'kind': 'DONE'} if self.kind == 'DONE' else self.action.to_dict())


def parse(value, state):
    if not isinstance(value, dict):
        raise SchemaError('Unified response must be one JSON object')
    if value.get('kind') == 'ASK':
        if set(value) != {'kind', 'question'}:
            raise SchemaError('ASK contains exactly kind and question')
        return UnifiedResult('ASK', question=StudyQuestion.parse(value['question'], state))
    action = StudyAction.parse(value, state)
    return UnifiedResult(action.kind, action=action)


class UnifiedPolicy:
    def __init__(self, client):
        self.client = client

    def decide(self, state):
        return self.client.json(SYSTEM_PROMPT, facts_payload(state), stage='unified',
                                validator=lambda value: parse(value, state), max_tokens=500)


def prompt_hash():
    return hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()
