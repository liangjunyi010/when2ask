"""One skill per action, scoped questions, and private task evaluation."""
import copy

from .graph_evaluator import GraphEvaluator
from .task_graph import resolve


class ActionLimit(RuntimeError):
    pass


def validate_action(value, observation):
    if value == {'kind':'DONE'}:
        return value
    if not isinstance(value,dict) or not isinstance(value.get('kind'),str):
        raise ValueError('An action must be a JSON object with a skill kind')
    kind, options = value['kind'], observation['affordances']
    fields = {'move':{'object_id','target_id'}, 'cover':{'object_id','target_id'},
              'search':{'location_id'}, 'approach':{'location_id'}, 'inspect_station':{'location_id'},
              'inspect':{'target_id'}, 'report':{'code'}, 'inspect_inventory':set(), 'return_home':set()}
    if kind not in fields or set(value)!={'kind'}|fields[kind] or not options.get(kind):
        raise ValueError('Choose an available skill and exactly its declared arguments')
    if any(not isinstance(value[k],str) for k in fields[kind]):
        raise ValueError('Skill arguments must be strings')
    if kind in ('move','cover'):
        valid = value['target_id'] in options[kind].get(value['object_id'],[])
    elif fields[kind]:
        valid = value[next(iter(fields[kind]))] in options[kind]
    else:
        valid = True
    if not valid:
        raise ValueError('Choose IDs from the observed affordances')
    return copy.deepcopy(value)


class GraphWorld:
    def __init__(self, sample, action_limit=60, adapter_factory=None, user=None):
        from .physical_world import Adapter
        self.sample, self.action_limit = sample, action_limit
        self.adapter_factory = adapter_factory or Adapter
        self.user = user
        self.adapter = self.adapter_factory(sample)
        self.world = self.adapter.world
        self.evaluator = GraphEvaluator(sample,self.adapter.measurements())
        self.actions, self.history = [], []
        self.terminated = False

    def public(self, history=None):
        observation = self.adapter.observation()
        observation['choices'] = copy.deepcopy(self.sample.slots)
        observation['disclosed'] = self.sample.public_task()['disclosed']
        return dict(instruction=self.sample.u0, observation=observation,
                    history=copy.deepcopy(self.history if history is None else history))

    def execute(self, action):
        if self.terminated:
            raise RuntimeError('Reset the ended episode before acting')
        action = validate_action(action,self.adapter.observation())
        if action['kind']=='DONE':
            raise ValueError('DONE is a termination decision')
        if len(self.actions)>=self.action_limit:
            raise ActionLimit('Physical action limit reached')
        result = self.adapter.execute(action)
        self.actions.append(copy.deepcopy(result))
        self.evaluator.observe(action,result,self.adapter.measurements())
        self.history.append(dict(kind='action',action=action,result=copy.deepcopy(result),
                                 observation=copy.deepcopy(self.adapter.observation())))
        return result

    def ask(self, question, user=None):
        from .dag_evaluation import question_answer
        question = question_answer(question,self.sample)
        user = user or self.user
        if user is None:
            raise ValueError('An LLM user client is required for questions')
        before = self.world.step_count
        answer = user.answer(question)
        if self.world.step_count != before:
            raise RuntimeError('Question changed the physical clock')
        self.history.append(dict(kind='user_answer',question=copy.deepcopy(question),response=copy.deepcopy(answer)))
        return answer

    def score(self, questions=None, termination='done'):
        if questions is None:
            questions = sum(h['kind']=='user_answer' for h in self.history)
        return dict(**self.evaluator.score(self.adapter.measurements()), termination=termination,
                    action_count=len(self.actions), ask_count=questions)

    def reset(self):
        self.close()
        self.__init__(self.sample,self.action_limit,self.adapter_factory,self.user)
        return self.public()

    def step(self, action):
        if self.terminated:
            raise RuntimeError('Reset the ended episode before acting')
        if action == {'kind':'DONE'}:
            self.terminated = True
            return self.public(), float(self.score()['task_success']), True, {}
        if action.get('kind')=='ASK':
            if set(action)!={'kind','text','slots'}:
                raise ValueError('ASK requires text and slots')
            answer = self.ask({k:action[k] for k in ('text','slots')})
            return self.public(), 0., False, dict(answer=answer)
        try:
            result = self.execute(action)
        except ActionLimit:
            self.terminated = True
            return self.public(), float(self.score()['task_success']), True, dict(termination='action_limit')
        return self.public(), 0., False, dict(execution=result)

    def close(self):
        self.adapter.close()


def oracle_actions(node, world):
    goal, op = node['goal'], node['operation']
    if op in ('place','cover'):
        yield dict(kind='move' if op=='place' else 'cover',object_id=goal['object_id'],target_id=goal['target_id'])
    elif op=='quota':
        for key in goal['supply']:
            if GraphEvaluator.holds(node,world.adapter.measurements()):
                break
            yield dict(kind='move',object_id=key,target_id=goal['target_id'])
    elif op=='search':
        yield dict(kind='inspect_station' if world.sample.template_id=='patrol_return' else 'search',location_id=goal['location_id'])
    elif op=='detect':
        if node['id'] not in world.evaluator.witnesses:
            yield dict(kind='search',location_id=world.sample.theta_star['target_location'])
    elif op=='approach':
        yield dict(kind='approach',location_id=goal['location_id'])
    elif op=='inspect':
        yield dict(kind='inspect',target_id=goal['target_id'])
    elif op=='report':
        yield dict(kind='report',code=goal['code'])
    else:
        yield dict(kind='inspect_inventory' if op=='inventory' else 'return_home')


def run_oracle(sample):
    world = None
    try:
        world = GraphWorld(sample)
        for node in resolve(sample.dag['nodes'],sample.theta_star):
            for action in oracle_actions(node,world):
                if not world.execute(action)['success']:
                    return dict(task_success=False,evaluation=world.score(termination='oracle'),actions=world.actions,api_attempts=0)
        score = world.score(termination='oracle')
        return dict(task_success=score['task_success'],evaluation=score,actions=world.actions,
                    graph_records=world.evaluator.records,api_attempts=0)
    except Exception as exc:
        return dict(task_success=False,error=str(exc),actions=world.actions if world else [],api_attempts=0)
    finally:
        if world:
            world.close()
