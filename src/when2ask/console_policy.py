"""Explicitly scripted public-only policy for offline console/transport testing."""
from .agents import GateResult
from .study_protocol import StudyAction, StudyQuestion, disclosed_choices, public_roles, role_candidates


class ConsoleScriptedPlanner:
    def selection(self, state, known_only=False):
        known = disclosed_choices(state)
        return {role: known.get(role) or (None if known_only else sorted(role_candidates(state, role))[0])
                for role in public_roles(state)}

    def next_action(self, state, known_only=False):
        objects = state.observation['objects']
        containers = sorted(k for k, v in objects.items() if v['category'] == 'container')
        choices = self.selection(state, known_only)
        relations = state.observation['spatial_relations']
        inside = relations['inside_containers']
        if len(containers) == 1:
            targets = dict(cup=containers[0], block=containers[0])
        else:
            destination = choices['cup_destination']
            targets = dict(cup=destination, block=next((k for k in containers if k != destination), None) if destination else None)
        order = ['block', 'cup'] if 'Place the block before the cup.' in state.instruction else ['cup', 'block']
        strict = 'before the' in state.instruction
        for role in order:
            key, target = choices[role], targets[role]
            if key and target and key in inside[target]:
                continue
            if key and target:
                return StudyAction('pick_place', key, target, 'inside')
            if strict:
                return None
        if not all(choices[r] and targets[r] and choices[r] in inside[targets[r]] for r in ['cup', 'block']):
            return None
        if len(containers) == 1:
            lid = choices['lid']
            if not lid:
                return None
            if lid not in relations['covering_containers'][containers[0]]:
                return StudyAction('cover', lid, containers[0], 'covers')
        return StudyAction('DONE')

    def generate_action(self, state):
        action = self.next_action(state)
        if action is None:
            raise ValueError('Scripted planner has no supported action')
        wire = {'kind': 'DONE'} if action.kind == 'DONE' else action.to_dict()
        return StudyAction.parse(wire, state)

    def generate_question(self, state):
        known = disclosed_choices(state)
        roles = [r for r in public_roles(state) if r not in known]
        return StudyQuestion.parse(dict(type='select', text='Which ' + ' and '.join(r.replace('_', ' ') for r in roles) + ' should I use?',
            requests=[dict(role=r, candidate_ids=role_candidates(state, r)) for r in roles]), state)


class ConsoleScriptedGate:
    def __init__(self, planner):
        self.planner = planner

    def decide(self, state):
        return GateResult('CONTINUE' if self.planner.next_action(state, known_only=True) else 'ASK')
