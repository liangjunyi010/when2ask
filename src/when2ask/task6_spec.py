"""Six new task definitions. Private intent/world facts never enter agent payloads."""
import copy
import json
from dataclasses import dataclass, replace

from .config import ROOT

VERSION = 'six_tasks_dev_v1'
TITLES = {
    'category_sorting': 'Category Sorting · 分类整理',
    'inventory_restock': 'Inventory Restock · 库存补货',
    'retrieve_restore': 'Retrieve & Restore · 开盒取物复原',
    'buffer_exchange': 'Buffered Exchange · 缓冲区交换',
    'patrol_return': 'Patrol & Return · 多点巡检返航',
    'occlusion_inspection': 'Reveal & Inspect · 移开遮挡检查',
}
SOURCES = ('task6_spec.py', 'task6_world.py', 'task6_protocol.py', 'task6_evaluator.py',
           'task6_worker.py', 'environment.py', 'skills.py', 'diverse_world.py', 'navigation_world.py', 'navigation_map.py')


@dataclass(frozen=True)
class Sample:
    template_id: str
    sample_id: str
    scene_seed: int
    u0: str
    slots: dict
    theta_star: dict
    initial_disclosed_slots: list
    public_goal: dict
    physical_scene: dict
    dag: dict
    version: str = VERSION
    partition: str = 'independent_task6_dev'

    @property
    def group_id(self): return self.template_id + ':conservative_layout_v1'

    def scene(self): return copy.deepcopy(self.physical_scene)

    def validate(self):
        if self.version != VERSION or self.template_id not in TITLES:
            raise ValueError('Unsupported six-task sample')
        if set(self.slots) != set(self.theta_star) or len(self.slots) != 1:
            raise ValueError('One finite preference/fact per demo instance')
        for key, record in self.slots.items():
            if self.theta_star[key] not in record['candidate_ids']:
                raise ValueError('Choice outside declared candidates')
            if record.get('kind')=='world_fact' and self.theta_star[key]!=self.physical_scene['label']['code']:
                raise ValueError('Printed label and fixed world fact must agree')
        if not set(self.initial_disclosed_slots) <= self.slots.keys():
            raise ValueError('Invalid disclosure')
        return self


def make_sample(template, unknown_preferences=None):
    if template not in TITLES: raise ValueError('Unknown new task')
    if unknown_preferences is not None and (type(unknown_preferences) is not int or unknown_preferences not in (0, 1)):
        raise ValueError('New demos support 0/1 unknown preference or fact')
    path = ROOT / 'data/six_tasks_dev_v1/samples.json'
    value = next(s for s in json.loads(path.read_text())['samples'] if s['template_id'] == template)
    sample = Sample(**value).validate()
    if unknown_preferences == 0:
        slot = next(iter(sample.slots)); role = sample.slots[slot]['public_role']
        return replace(sample, initial_disclosed_slots=[slot],
            u0=sample.u0 + f' User specifies {role}={sample.theta_star[slot]}.').validate()
    return sample


def public_task(sample):
    result = copy.deepcopy(sample.public_goal)
    result.update(template_id=sample.template_id, version=VERSION, dag=copy.deepcopy(sample.dag),
        preference_slots={r['public_role']: dict(candidate_ids=r['candidate_ids'],
            kind=r.get('kind', 'preference'), description=r['description']) for r in sample.slots.values()},
        initial_choices={sample.slots[k]['public_role']: sample.theta_star[k] for k in sample.initial_disclosed_slots})
    return result
