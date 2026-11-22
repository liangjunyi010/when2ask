"""Private evaluation of physical predicates and witnessed prerequisite order."""
import math
from .task_graph import resolve


class GraphEvaluator:
    def __init__(self, sample, initial):
        self.sample, self.initial = sample, initial
        self.nodes = resolve(sample.dag['nodes'], sample.theta_star)
        self.witnesses = {}
        self.records = []

    @staticmethod
    def holds(node, state):
        goal, op = node['goal'], node['operation']
        if op == 'place':
            contents = {**state.get('containers', {}), **state.get('zones', {})}
            return goal['object_id'] in contents.get(goal['target_id'], [])
        if op == 'cover':
            return state.get('coverage', {}).get(goal['object_id'], False)
        if op == 'quota':
            contents = state.get('containers', {}).get(goal['target_id'], [])
            return len(contents)==int(goal['count']) and all(state['categories'][k]==goal['category'] for k in contents)
        if op == 'search':
            return goal['location_id'] in state.get('visited', [])
        if op == 'detect':
            return bool(state.get('detected')) and ('location_id' not in goal or state['detected']['location_id']==goal['location_id'])
        if op == 'approach':
            return ((state.get('detected') or {}).get('location_id') == goal['location_id']
                    and state.get('distance_to_target', float('inf')) <= 1.2 and state.get('stopped',False))
        if op == 'inspect':
            return any(r['code'] is not None and r['camera']['visible'] and ('code' not in goal or r['code']==goal['code'])
                       for r in state.get('inspections', []))
        if op == 'report':
            return bool(state.get('reports')) and state['reports'][-1]['code']==goal['code']
        if op == 'return_home':
            return state.get('at_home',False) and state.get('stopped',False)
        return op == 'inventory'

    @staticmethod
    def matches(node, action):
        goal, op, kind = node['goal'], node['operation'], action['kind']
        if op in ('place','cover'):
            return (kind==('move' if op=='place' else 'cover') and action.get('object_id')==goal['object_id']
                    and action.get('target_id')==goal['target_id'])
        if op=='quota':
            return kind=='move' and action.get('target_id')==goal['target_id']
        if op=='search':
            return kind in ('search','inspect_station') and action.get('location_id')==goal['location_id']
        if op=='detect':
            return kind in ('search','approach')
        if op=='approach':
            return kind=='approach' and action.get('location_id')==goal['location_id']
        return kind=={'inventory':'inspect_inventory','return_home':'return_home','inspect':'inspect','report':'report'}[op]

    def observe(self, action, result, state):
        before = set(self.witnesses)
        attained = []
        if result['success']:
            for node in self.nodes:
                predecessors = {a for a,b in self.sample.dag['edges'] if b==node['id']}
                if (predecessors<=before and self.matches(node,action) and self.holds(node,state)):
                    self.witnesses.setdefault(node['id'],len(self.records))
                    attained.append(node['id'])
        self.records.append(dict(action=action, attained=attained))

    def score(self, state):
        complete = all(n['id'] in self.witnesses for n in self.nodes)
        final = all(self.holds(n,state) for n in self.nodes if n['final'])
        order = all(a in self.witnesses and b in self.witnesses and self.witnesses[a]<self.witnesses[b]
                    for a,b in self.sample.dag['edges'])
        selected = {n['goal'].get('object_id') for n in self.nodes}
        supplies = {k for n in self.nodes for k in n['goal'].get('supply',[])}
        resources = self.sample.dag['resources']
        stationary = {k for k in state.get('positions',{}) if k not in selected|supplies or resources[k].get('protected')}
        preserved = all(math.dist(state['positions'][k], self.initial['positions'][k])<=.015 for k in stationary)
        conditions = dict(subgoals_completed=complete, final_physical_goals=final, prerequisite_order=order,
                          unselected_items_preserved=preserved, released=state.get('released',True),
                          stable=state.get('stable',True), physical_constraints=state['safe'])
        return dict(task_success=all(conditions.values()), conditions=conditions, witnesses=dict(self.witnesses))
