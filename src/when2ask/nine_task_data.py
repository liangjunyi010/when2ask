"""Nine-task pilot v1. New layouts and evidence; legacy datasets stay immutable."""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import random
from dataclasses import asdict, dataclass

from .config import ROOT
from .study_data import base_scene, SOURCE_PAIRS, dag_for, instruction
from .task import PrivateTaskSpec
from .task6_spec import TITLES
from .three_task_data import geometry, distance

VERSION = 'nine_task_pilot_v1'
DATA = ROOT / 'data' / VERSION
OUT = ROOT / 'result' / 'nine_task_v1'
TEMPLATES = ('pack_and_cover', 'place_into_selected_containers', 'find_and_approach', *TITLES)
STUDY = TEMPLATES[:2]
MOBILE = ('find_and_approach', 'patrol_return')
MIN_DISTANCE = .035


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def shape(scene):
    if 'stations' in scene:
        return {'station_and_fixture': sorted([*v['xy'], *v['fixture_xy']] for v in scene['stations'].values())}
    if 'sources' in scene:
        s = dict(containers=scene['containers'], objects=[])
        for category, pair in SOURCE_PAIRS.items():
            s['objects'].extend(dict(category=category, xy=scene['sources'][k]) for k in pair if k in scene['sources'])
        return geometry(s)
    return geometry(scene)


def separation(a, b):
    ga, gb = shape(a), shape(b)
    if ga.keys() != gb.keys() or any(len(ga[k]) != len(gb[k]) for k in ga):
        return float('inf')
    # Category-matched, identity/order invariant. All groups are very small.
    return max(min(max(math.dist(x, y) for x, y in zip(ga[k], perm))
                   for perm in itertools.permutations(gb[k])) for k in ga)


@dataclass(frozen=True)
class Case:
    sample_id: str
    template_id: str
    group_id: str
    layout_family_id: str
    partition: str
    scene_seed: int
    u0: str
    slots: dict
    theta_star: dict
    initial_disclosed_slots: list
    dag: dict
    physical_scene: dict
    public_goal: dict
    schema_version: int = 9
    dataset_version: str = VERSION
    version: str = 'six_tasks_dev_v1'  # Compatibility with the existing physical task contract.

    def scene(self):
        return copy.deepcopy(self.physical_scene)

    @property
    def target_location(self):
        return self.theta_star['target_location_choice']

    @property
    def unknown_slots(self):
        return len(self.slots) - len(self.initial_disclosed_slots)

    def private_spec(self):
        return PrivateTaskSpec(**self.theta_star,
            candidate_registry={s: r['candidate_ids'] for s, r in self.slots.items()})

    def validate(self):
        if self.template_id not in TEMPLATES or self.partition not in ('dev', 'test'):
            raise ValueError('Unknown template/partition')
        if self.schema_version != 9 or self.dataset_version != VERSION:
            raise ValueError('Unsupported nine-task version')
        if set(self.slots) != set(self.theta_star) or not set(self.initial_disclosed_slots) <= self.slots.keys():
            raise ValueError('Invalid preference registry/disclosure')
        for key, row in self.slots.items():
            if self.theta_star[key] not in row['candidate_ids'] or len(set(row['candidate_ids'])) != len(row['candidate_ids']):
                raise ValueError('Invalid choice/candidates')
        fp = digest(shape(self.physical_scene))[:16]
        if self.layout_family_id != 'layout_' + fp or self.group_id != self.template_id + ':' + self.layout_family_id:
            raise ValueError('Physical group identity mismatch')
        return self


def translated(scene, dx, dy):
    s = copy.deepcopy(scene)
    def xy(v): return [round(v[0]+dx, 5), round(v[1]+dy, 5)]
    for field in ('containers', 'objects', 'zones'):
        for row in s.get(field, []): row['xy'] = xy(row['xy'])
    if 'sources' in s: s['sources'] = {k: xy(v) for k, v in s['sources'].items()}
    if 'label' in s:
        s['label']['xy'] = xy(s['label']['xy'])
        s['label']['eye'][:2] = xy(s['label']['eye'])
    return s


def historical_scenes(template):
    result = []
    original = json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']
    result += [s['physical_scene'] for s in original if s['template_id'] == template]
    for p in (ROOT/'data').glob('three_task_v8/*/*.jsonl'):
        result += [v['physical_scene'] for line in p.read_text().splitlines()
                   if (v := json.loads(line))['template_id'] == template]
    if template in STUDY:
        for p in (ROOT/'data/phase3/scenes').glob('*.json'):
            s = json.loads(p.read_text())
            if s.get('template_id') == template: result.append(s)
    return result


def mobile_layout(index, template='find_and_approach'):
    from .navigation_map import LOCATIONS
    # New furniture/station arrangements, SAME three-room topology/controller.
    shifts = ([(-.32,.04),(.30,-.04),(-.28,-.04),(.34,.04)] if template=='find_and_approach'
              else [(-.16,-.02),(.16,.02),(-.44,.02),(.44,-.02)])[index]
    stations = copy.deepcopy(LOCATIONS)
    for i, row in enumerate(stations.values()):
        dx = shifts[0] * (1 if i % 2 == 0 else -1)
        side = 1 if row['xy'][1] > 0 else -1
        row['xy'] = [row['xy'][0]+dx, side*(1.25+shifts[1])]
        row['fixture_xy'] = [row['xy'][0], side*2.15]
    return dict(kind='three_room_station_layout_v9', stations=stations,
                room_topology='unchanged_three_room_corridor', walls='unchanged_v1')


def layouts(template, original):
    if template in MOBILE: return [mobile_layout(i,template) for i in range(4)]
    # Deterministic geometry selection ONLY: no model outputs or preferences.
    old = historical_scenes(template)
    candidates = [translated(original, dx, dy)
                  for dx, dy in itertools.product((0, .04, -.015), (-.06, 0, .06))]
    selected = []
    for s in candidates:
        if all(separation(s, other) >= MIN_DISTANCE for other in old + selected): selected.append(s)
        if len(selected) == 4: return selected
    raise ValueError('Insufficient new separated conservative layouts: '+template)


def generate():
    if DATA.exists(): raise FileExistsError('Never overwrite an existing dataset version')
    DATA.mkdir(parents=True)
    original = {s['template_id']: s for s in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']}
    rows = []
    for ti, template in enumerate(TEMPLATES):
        base = base_scene(template, 'dev', 0) if template in STUDY else original.get(template, {}).get('physical_scene', {})
        for i, scene in enumerate(layouts(template, base)):
            partition = 'dev' if i < 2 else 'test'
            rng = random.Random(f'42781119:{template}:{i}')
            if template in STUDY:
                aliases = {k: ('box' if k == 'box' else 'item_'+f'{rng.getrandbits(40):010x}')
                           for k in [*[c['id'] for c in scene['containers']], *scene['sources']]}
                order = list(aliases.values()); rng.shuffle(order)
                scene.update(object_id_map=aliases, object_order=order)
                roles = ('cup', 'block', 'lid' if template == STUDY[0] else 'cup_destination')
                pairs = [SOURCE_PAIRS['cup'], SOURCE_PAIRS['block'], SOURCE_PAIRS['lid'] if template == STUDY[0] else ('container_a','container_b')]
                slots, theta = {}, {}
                for ri, (role, pair) in enumerate(zip(roles, pairs)):
                    candidates = [aliases[k] for k in pair]
                    # Counterbalance truth independently of shuffled candidate order.
                    truth = candidates[(i+ri+ti) % 2]; rng.shuffle(candidates)
                    slots[role+'_choice'] = dict(public_role=role, candidate_ids=candidates)
                    theta[role+'_choice'] = truth
                missing = (0,3,1,2)[i]
                disclosed = list(slots); rng.shuffle(disclosed); disclosed = disclosed[:3-missing]
                dag = dag_for(template, ('independent','cup_first','block_first','independent')[i])
                text = instruction(template, dag['order'], i)
                for slot in disclosed: text += f" For the {slots[slot]['public_role']}, use {theta[slot]}."
                goal = {}
            elif template == 'find_and_approach':
                from .navigation_task import NavigationSample
                loc = ('kitchen_counter','study_shelf','living_table','study_desk')[i]
                native = NavigationSample('new_layout',loc,disclosed=i%2 == 0)
                slots, theta, text = native.slots, native.theta_star, native.u0
                disclosed = native.initial_disclosed_slots
                dag = dict(nodes=['find','approach'], edges=[['find','approach']]); goal = {}
            else:
                src = original[template]; slots = copy.deepcopy(src['slots']); slot = next(iter(slots))
                candidates = slots[slot]['candidate_ids']; truth = candidates[(i+ti)%2]
                if (i//2)%2: candidates.reverse()
                theta = {slot:truth}; disclosed = [slot] if i%2 == 0 else []
                text = src['u0']
                # Initial source text describes an unspecified role. Explicit appended
                # user choice overrides it exactly as in existing demo contracts.
                if disclosed: text += f" The user specifies {slots[slot]['public_role']}={truth}."
                if template == 'occlusion_inspection': scene['label']['code'] = truth
                goal = copy.deepcopy(src['public_goal']); dag = copy.deepcopy(src['dag'])
                for field in ('objects','containers','zones'): rng.shuffle(scene.get(field, []))
            fp = digest(shape(scene))[:16]; family = 'layout_'+fp
            sample = Case(f'n9_{partition}_{ti:02d}_{i%2}',template,template+':'+family,family,
                partition,rng.randrange(10000,2_000_000_000),text,slots,theta,disclosed,dag,scene,goal).validate()
            rows.append(sample)
    for part in ('dev','test'):
        (DATA/(part+'.jsonl')).write_text(''.join(json.dumps(asdict(s),sort_keys=True)+'\n' for s in rows if s.partition==part))
    result = audit(rows)
    write(DATA/'audit.json', result)
    write(DATA/'generation_manifest.json',dict(dataset_version=VERSION,seed=42781119,
        policy='Four new physical layouts/task; two Dev and two Test. No model outcomes used in generation. Every Test case paired across all three methods.',
        grouping='Category/shape-matched physical geometry; ignore IDs, colours, answers, list order and printed code. Never split variants of one base layout.',
        limitations='Small coverage pilot: two Test groups per task. Mobile layouts vary stations/furniture but share the three-room wall topology. Legacy canonical IDs retained in six skill families.',
        dataset_hashes={p:hashlib.sha256((DATA/(p+'.jsonl')).read_bytes()).hexdigest() for p in ('dev','test')},audit=result))
    return result


def load(partition=None):
    return [Case(**json.loads(line)).validate() for part in ([partition] if partition else ('dev','test'))
            for line in (DATA/(part+'.jsonl')).read_text().splitlines()]


def audit(samples):
    if len({s.sample_id for s in samples}) != len(samples): raise ValueError('Duplicate sample IDs')
    groups = {}; distribution = {}; distances = []
    for s in samples:
        s.validate()
        if s.group_id in groups and groups[s.group_id] != s.partition: raise ValueError('Group split leakage')
        groups[s.group_id] = s.partition
        row = distribution.setdefault(s.template_id,dict(dev=0,test=0,unknown_counts={},truth_rank_counts={}))
        row[s.partition] += 1
        row['unknown_counts'][str(s.unknown_slots)] = row['unknown_counts'].get(str(s.unknown_slots),0)+1
        for k, v in s.theta_star.items():
            rank = str(s.slots[k]['candidate_ids'].index(v))
            row['truth_rank_counts'][rank] = row['truth_rank_counts'].get(rank,0)+1
    for a,b in itertools.combinations(samples,2):
        if a.template_id != b.template_id: continue
        d = separation(a.scene(),b.scene())
        if a.group_id != b.group_id and d < MIN_DISTANCE: raise ValueError('Near-duplicate groups')
        if a.partition != b.partition: distances.append(d)
    for s in samples:
        if s.partition == 'test' and s.template_id not in MOBILE:
            if any(separation(s.scene(),old)<MIN_DISTANCE for old in historical_scenes(s.template_id)):
                raise ValueError('Historical group reused as new Test')
    return dict(samples=len(samples),groups=len(groups),distribution=distribution,
                minimum_cross_partition_separation_m=min(distances),minimum_required_m=MIN_DISTANCE,
                group_isolation=True,historical_groups_excluded=True)
