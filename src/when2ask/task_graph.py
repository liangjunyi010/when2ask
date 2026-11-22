"""Task-family composition with explicit physical goals and prerequisites."""
from __future__ import annotations

import math

TITLES = {
    'pack_and_cover': 'Pack & Cover', 'place_into_selected_containers': 'Two Containers',
    'category_sorting': 'Category Sorting', 'inventory_restock': 'Inventory Restock',
    'retrieve_restore': 'Retrieve & Restore', 'buffer_exchange': 'Buffered Exchange',
    'find_and_approach': 'Find & Approach', 'patrol_return': 'Patrol & Return',
    'occlusion_inspection': 'Reveal & Inspect',
}


def reference(slot):
    return {'choice': slot}


def resolve(value, intent):
    if isinstance(value, dict):
        if set(value) == {'choice'}:
            return intent[value['choice']]
        if set(value) == {'other_than', 'values'}:
            return next(v for v in value['values'] if v != intent[value['other_than']])
        return {k: resolve(v, intent) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, intent) for v in value]
    return value


class GraphBuilder:
    def __init__(self, family):
        self.family = family
        self.nodes, self.edges, self.resources, self.slots = [], [], {}, {}

    def resource(self, name, category, **values):
        self.resources.setdefault(name, dict(id=name, category=category, **values))
        return name

    def choice(self, name, candidates, description, kind='preference'):
        self.slots[name] = dict(candidate_ids=list(candidates), public_role=name,
                                description=description, kind=kind)
        return reference(name)

    def add(self, name, operation, description, *, slot=None, after=(), final=True, **goal):
        self.nodes.append(dict(id=name, operation=operation, description=description,
                               choice_slot=slot, goal=goal, final=final))
        self.edges.extend([parent, name] for parent in after)
        return name

    def graph(self):
        return dict(nodes=self.nodes, edges=self.edges, resources=self.resources)


def compose(family, size, uncertain, rng):
    b = GraphBuilder(family)
    if family == 'pack_and_cover':
        b.resource('box', 'container', capacity=size-1)
        placements = []
        for i in range(size-1):
            category = 'cup' if i % 2 == 0 else 'block'
            key = f'pack_{i}'
            item = b.resource(key, category)
            slot = None
            if i < uncertain-1:
                other = b.resource(key+'_alternative', category)
                slot = key+'_choice'
                item = b.choice(slot, [key, other], f'Which {category} should be packed for item {i+1}?')
            placements.append(b.add(key, 'place', f'Pack item {i+1} ({category}) into the box.',
                                    slot=slot, object_id=item, target_id='box'))
        lids = [b.resource('lid_'+c, 'lid') for c in ('black', 'gray')]
        lid = b.choice('lid_choice', lids, 'Which lid should cover the box?')
        b.add('cover', 'cover', 'Cover the box after packing all required items.', slot='lid_choice',
              after=placements, object_id=lid, target_id='box')
    elif family == 'place_into_selected_containers':
        for k in ('container_a', 'container_b'):
            b.resource(k, 'container', capacity=size)
        for i in range(size):
            key = b.resource(f'item_{i}', 'cup' if i % 2 == 0 else 'block')
            item, target, slot = key, ('container_a' if i % 2 == 0 else 'container_b'), None
            if i < uncertain:
                slot = f'item_{i}_choice'
                if i % 2:
                    other = b.resource(key+'_alternative', b.resources[key]['category'])
                    item = b.choice(slot, [key, other], f'Which object is item {i+1}?')
                else:
                    target = b.choice(slot, ['container_a', 'container_b'], f'Which container should receive {key}?')
            b.add(f'place_{i}', 'place', f'Place item {i+1} in its assigned container.', slot=slot,
                  object_id=item, target_id=target)
    elif family == 'category_sorting':
        for k in ('cup_bin', 'puck_bin', 'block_bin_a', 'block_bin_b'):
            b.resource(k, 'container', capacity=size)
        rule = b.choice('block_bin_choice', ['block_bin_a', 'block_bin_b'], 'Which bin should hold the blocks?')
        for i in range(size):
            category = 'block' if i < uncertain else 'cup' if i % 2 else 'puck'
            key = b.resource(f'{category}_{i}', category)
            target = rule if category == 'block' else category+'_bin'
            b.add('sort_'+key, 'place', f'Sort {key} into the {category} bin.',
                  slot='block_bin_choice' if category == 'block' else None, object_id=key, target_id=target)
    elif family == 'inventory_restock':
        for kind in ('cup', 'block'):
            b.resource(kind+'_shelf', 'container', capacity=size+1)
            b.resource('stocked_'+kind, kind, initial_target=kind+'_shelf', protected=True)
        count = b.add('count_inventory', 'inventory', 'Count the existing inventory before adding stock.', final=False)
        fixed_count = size-1-uncertain
        cup_nodes = []
        for i in range(fixed_count):
            key = b.resource(f'spare_cup_{i}', 'cup')
            cup_nodes.append(b.add('add_'+key, 'place', f'Add {key} to the cup shelf.', after=[count],
                                    object_id=key, target_id='cup_shelf'))
        if uncertain == 2:
            quota = b.choice('cup_quota', [str(fixed_count+2), str(fixed_count+3)], 'What total cup count is required?')
            supply = [b.resource(f'extra_cup_{i}', 'cup') for i in range(2)]
            b.add('cup_quantity', 'quota', 'Bring the cup shelf to the requested total.', slot='cup_quota',
                  after=cup_nodes, category='cup', target_id='cup_shelf', count=quota, supply=supply)
        quota = b.choice('block_quota', ['2', '3'], 'What total block count is required?')
        supply = [b.resource(f'spare_block_{i}', 'block') for i in range(2)]
        b.add('block_quantity', 'quota', 'Bring the block shelf to the requested total.', slot='block_quota',
              after=[count], category='block', target_id='block_shelf', count=quota, supply=supply)
    elif family == 'retrieve_restore':
        b.resource('box', 'container', capacity=size+uncertain)
        b.resource('storage_lid', 'lid', initial_target='box', covering=True)
        b.resource('lid_pad', 'zone', panel=True)
        b.resource('delivery_pad', 'zone', capacity=size-2)
        opening = b.add('uncover', 'place', 'Open the box by moving its lid onto the lid pad.',
                        final=False, object_id='storage_lid', target_id='lid_pad')
        deliveries = []
        for i in range(size-2):
            key = b.resource(f'stored_{i}', 'cup' if i % 2 == 0 else 'block', initial_target='box')
            item, slot = key, None
            if i < uncertain:
                other = b.resource(key+'_alternative', b.resources[key]['category'], initial_target='box')
                slot = key+'_choice'
                item = b.choice(slot, [key, other], f'Which stored object should be retrieved for item {i+1}?')
            deliveries.append(b.add('retrieve_'+str(i), 'place', f'Deliver selected item {i+1} onto the delivery pad.',
                                    slot=slot, after=[opening], object_id=item, target_id='delivery_pad'))
        b.add('restore_lid', 'cover', 'Close the box again after all deliveries.', after=deliveries,
              object_id='storage_lid', target_id='box')
    elif family == 'buffer_exchange':
        lengths = {6: [3,3], 7: [3,4], 8: [4,4], 9: [3,3,3]}[size]
        previous = []
        for i, length in enumerate(lengths):
            left = b.resource(f'left_{i}', 'container', capacity=1)
            right = b.resource(f'right_{i}', 'container', capacity=1)
            a = b.resource(f'item_a_{i}', 'block', initial_target=left)
            c = b.resource(f'item_b_{i}', 'block', initial_target=right)
            pads = [b.resource('buffer_'+str(j), 'zone', capacity=1) for j in range(2)]
            slot = f'buffer_choice_{i}' if i < uncertain else None
            pad = b.choice(slot, pads, f'Which buffer should be used first for pair {i+1}?') if slot else pads[0]
            first = b.add(f'park_a_{i}', 'place', f'Park item A of pair {i+1} on its buffer.', slot=slot,
                          after=previous, final=False, object_id=a, target_id=pad)
            if length == 4:
                other = {'other_than':slot, 'values':pads} if slot else pads[1]
                second = b.add(f'park_b_{i}', 'place', f'Park item B of pair {i+1} on the other buffer.',
                               after=[first], final=False, object_id=c, target_id=other)
                third = b.add(f'finish_a_{i}', 'place', f'Put item A of pair {i+1} in the right slot.',
                              after=[second], object_id=a, target_id=right)
                last = b.add(f'finish_b_{i}', 'place', f'Put item B of pair {i+1} in the left slot.',
                             after=[third], object_id=c, target_id=left)
            else:
                second = b.add(f'finish_b_{i}', 'place', f'Put item B of pair {i+1} in the left slot.',
                               after=[first], object_id=c, target_id=left)
                last = b.add(f'finish_a_{i}', 'place', f'Put item A of pair {i+1} in the right slot.',
                             after=[second], object_id=a, target_id=right)
            previous = [last]
    elif family in ('find_and_approach', 'patrol_return'):
        stations = [f'{room}_{side}_{offset}' for room in ('kitchen','living_room','study')
                    for side in ('north','south') for offset in ('left','right')]
        rng.shuffle(stations)
        if family == 'find_and_approach':
            selected = stations[:size-2]
            for name in selected:
                b.resource(name, 'station')
            location = b.choice('target_location', selected, 'Where is the target located?', 'world_fact')
            visits = [b.add('search_'+str(i), 'search', f'Search station {k}.', location_id=k) for i,k in enumerate(selected)]
            found = b.add('find', 'detect', 'Locate the target through direct observation.',
                          slot='target_location' if uncertain == 2 else None,
                          **({'location_id':location} if uncertain == 2 else {}))
            b.add('approach', 'approach', 'Approach the observed target and stop within 1.2 metres.',
                  slot='target_location', after=visits+[found], location_id=location)
        else:
            visits, index = [], 0
            for i in range(size-1):
                slot = None
                if i < uncertain:
                    candidates = [b.resource(k, 'station') for k in stations[index:index+2]]
                    index += 2
                    slot = f'checkpoint_{i}_choice'
                    location = b.choice(slot, candidates, f'Which station is checkpoint {i+1}?')
                else:
                    location = b.resource(stations[index], 'station'); index += 1
                visits.append(b.add('visit_'+str(i), 'search', f'Inspect checkpoint {i+1}.', slot=slot, location_id=location))
            b.add('return_home', 'return_home', 'Return to the start after inspecting all checkpoints.', after=visits)
    elif family == 'occlusion_inspection':
        b.resource('label_fixture', 'label')
        code = b.choice('inspection_code', ['alpha', 'beta'], 'What code is printed on the hidden label?', 'world_fact')
        previous = []
        for i in reversed(range(size-2)):
            panel = b.resource(f'panel_{i}', 'screen', stack_level=i)
            pad = b.resource(f'panel_pad_{i}', 'zone', panel=True, small=True)
            key = b.add(f'clear_{i}', 'place', f'Move panel {i+1} onto its parking pad.',
                        after=previous, object_id=panel, target_id=pad)
            previous = [key]
        inspection = b.add('inspect_label', 'inspect', 'Read the exposed label using the camera.',
                           slot='inspection_code' if uncertain == 2 else None, after=previous,
                           target_id='label_fixture', **({'code':code} if uncertain == 2 else {}))
        b.add('report_code', 'report', 'Report the observed code.', slot='inspection_code',
              after=[inspection], code=code)
    else:
        raise ValueError('Unknown task family: '+family)
    graph = b.graph()
    if len(graph['nodes']) != size or sum(n['choice_slot'] is not None for n in graph['nodes']) != uncertain:
        raise ValueError('Task composition does not meet its declared graph dimensions')
    return graph, b.slots


def layout(graph, family, rng):
    resources = graph['resources']
    scene = dict(containers=[], zones=[], objects=[])
    if family in ('find_and_approach','patrol_return'):
        stations = {}
        centers = {'kitchen':-4.,'living_room':0.,'study':4.}
        for name, r in resources.items():
            if r['category'] != 'station':
                continue
            room, side, offset = name.rsplit('_',2)
            x = centers[room] + (-.9 if offset == 'left' else .9) + rng.uniform(-.04,.04)
            sign = 1 if side == 'north' else -1
            stations[name] = dict(room=room,name=name.replace('_',' '),xy=[x,sign*1.25],
                                  yaw=sign*math.pi/2,fixture_xy=[x,sign*2.15])
        return dict(stations=stations, distance_budget_m=180.)
    container_ids = [k for k,r in resources.items() if r['category']=='container']
    if len(container_ids) == 1:
        centers = [[.64,.04]]
    elif len(container_ids) == 2:
        centers = [[.64,-.22],[.64,.22]]
    elif len(container_ids) == 4:
        centers = [[.48,-.23],[.73,-.23],[.48,.20],[.73,.20]]
    else:
        centers = [[x,y] for y in (-.26,0,.26) for x in (.51,.73)]
    for key, xy in zip(container_ids, centers):
        cap = resources[key].get('capacity',3)
        half = [.045,.045] if cap == 1 else [.11,.12] if len(container_ids)==4 else [.18,.12] if family=='inventory_restock' else [.14,.12]
        xy = [xy[0]+rng.uniform(-.008,.008),xy[1]+rng.uniform(-.008,.008)]
        scene['containers'].append(dict(id=key,xy=xy,half_xy=half,wall_height=.10,color='orange' if key!='box' else 'brown'))
    zones = [k for k,r in resources.items() if r['category']=='zone']
    for i,key in enumerate(zones):
        spec = resources[key]
        if spec.get('panel') and not spec.get('small'):
            xy, half = [.27,.38], [.16,.14]
        elif key == 'delivery_pad':
            xy, half = [.29,-.22], [.14,.12]
        else:
            xy, half = [.29,-.28+i*.14], [.065,.065]
        scene['zones'].append(dict(id=key,xy=xy,half_xy=half))
    pool = [[x,y] for y in (-.36,-.27,-.18,-.09,0,.09,.18,.27,.36) for x in (.21,.30,.39)]
    panels = [k for k,r in resources.items() if r['category']=='lid' and not r.get('covering')]
    for i,key in enumerate(panels):
        xy = [.28,.34] if i == 0 else [.63,-.35]
        scene['objects'].append(dict(id=key,category='lid',color='black' if i == 0 else 'gray',xy=xy))
    fixtures = {r['id']:r for r in scene['containers']+scene['zones']}
    occupied = []
    for obj in scene['objects']:
        occupied.append((obj['xy'],[.154,.134]))
    occupied += [(r['xy'],r['half_xy']) for r in scene['containers']+scene['zones']]
    rng.shuffle(pool)
    inside_counts = {}
    colors = ['red','blue','green','yellow','purple','cyan']
    for key, resource in resources.items():
        category = resource['category']
        if category in ('container','zone','station','label') or key in panels:
            continue
        obj = dict(id=key,category=category,color=colors[len(scene['objects'])%len(colors)])
        if category == 'screen':
            level=resource['stack_level']; obj.update(xy=[.64,.04],half_extents=[.055,.045,.006],z=.43+level*.012,color='gray')
        elif resource.get('covering'):
            fixture=fixtures[resource['initial_target']]
            obj.update(xy=fixture['xy'],z=.42+.014+fixture['wall_height']+.008,color='black')
        elif 'initial_target' in resource:
            target=resource['initial_target']; fixture=fixtures[target]
            index=inside_counts.get(target,0);inside_counts[target]=index+1
            offsets = placement_offsets(fixture['half_xy'], .032)
            if index >= len(offsets):raise ValueError('Initial inventory exceeds fixture capacity')
            off=offsets[index];obj.update(xy=[fixture['xy'][0]+off[0],fixture['xy'][1]+off[1]],
                                        z=.42+.014+(.032 if category=='cup' else .024))
        else:
            xy=next((xy for xy in pool if all(abs(xy[0]-center[0])>half[0]+.04 or abs(xy[1]-center[1])>half[1]+.04
                                            for center,half in occupied)),None)
            if xy is None:raise ValueError('Scene layout cannot accommodate its graph resources')
            pool.remove(xy);occupied.append((xy,[.032,.032]));obj['xy']=xy
        scene['objects'].append(obj)
    if family=='occlusion_inspection':
        scene['label']=dict(xy=[.64,.04],eye=[.64,.04,1.1],support=False)
    return scene


def placement_offsets(half_xy, radius):
    step=max(.065,2*radius+.008)
    axes=[]
    for half in half_xy:
        usable=half-.012-radius-.004
        count=max(1,int(2*usable/step+1e-8)+1)
        axes.append([(i-(count-1)/2)*step for i in range(count)])
    return [(x,y) for y in axes[1] for x in axes[0]]


def instruction(family, graph, slots, intent, disclosed):
    parts=[TITLES[family]+'.']
    for n in graph['nodes']:
        goal=n['goal']
        if n['operation']=='place':
            parts.append('Move '+describe(goal['object_id'])+' to '+describe(goal['target_id'])+'.')
        elif n['operation']=='cover':
            parts.append('Cover '+goal['target_id']+' with '+describe(goal['object_id'])+'.')
        elif n['operation']=='search':
            parts.append('Inspect '+describe(goal['location_id'])+'.')
        elif n['operation']=='quota':
            parts.append('Bring '+goal['target_id']+' to '+describe(goal['count'])+' '+goal['category']+' objects in total.')
        else:
            parts.append(n['description'])
    if graph['edges']:
        labels={n['id']:n['description'].rstrip('.') for n in graph['nodes']}
        parts.append('Required order: '+'; '.join(labels[a]+' before '+labels[c] for a,c in graph['edges'])+'.')
    parts.append('Operations without a stated dependency may be completed in either order. Leave unselected items in place.')
    for key in disclosed:
        parts.append(slots[key]['description']+' The specified choice is '+str(intent[key])+'.')
    return ' '.join(parts)


def describe(value):
    if isinstance(value,str):return value
    if 'choice' in value:return 'the selection for '+value['choice']
    return 'the other option relative to '+value['other_than']
