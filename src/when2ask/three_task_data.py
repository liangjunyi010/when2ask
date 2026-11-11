"""Independent v8 benchmark: new physical layout groups, not relabelled Dev traces."""
import copy
import hashlib
import itertools
import json
import math
import random
from dataclasses import asdict,dataclass
from pathlib import Path
from .config import ROOT
from .task6_spec import Sample as LegacySample,VERSION as PHYSICS_TASK_VERSION

VERSION='when2ask_three_task_v8'
TEMPLATES=('buffer_exchange','retrieve_restore','occlusion_inspection')
MIN_GROUP_DISTANCE=.035


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def geometry(scene):
    """Ignore candidate identity/order, colours, label code and user preference."""
    parts={}
    for key,field in [('container','containers'),('zone','zones')]:
        for row in scene.get(field,[]):
            shape=key+':'+str(row.get('half_xy'))+':'+str(row.get('wall_height'))
            parts.setdefault(shape,[]).append(list(row['xy']))
    for row in scene.get('objects',[]):parts.setdefault('body:'+row['category'],[]).append([*row['xy'],row.get('z',0)])
    if 'label' in scene:parts['label_and_camera']=[[*scene['label']['xy'],*scene['label']['eye']]]
    return {k:sorted(v) for k,v in sorted(parts.items())}


def distance(a,b):
    ga,gb=geometry(a),geometry(b)
    if ga.keys()!=gb.keys():return float('inf')
    return max(min(max(math.dist(x,y) for x,y in zip(ga[k],perm)) for perm in itertools.permutations(gb[k])) for k in ga)


@dataclass(frozen=True)
class Sample:
    template_id:str
    sample_id:str
    group_id:str
    layout_family_id:str
    partition:str
    scene_seed:int
    u0:str
    slots:dict
    theta_star:dict
    initial_disclosed_slots:list
    public_goal:dict
    physical_scene:dict
    dag:dict
    dataset_version:str=VERSION
    schema_version:int=8
    version:str=PHYSICS_TASK_VERSION
    def scene(self):return copy.deepcopy(self.physical_scene)
    def validate(self):
        LegacySample.validate(self)
        if self.template_id not in TEMPLATES or self.partition not in ('dev','test') or self.dataset_version!=VERSION or self.schema_version!=8:raise ValueError('Unsupported v8 sample')
        fp=digest(geometry(self.physical_scene))[:16]
        if self.layout_family_id!='layout_'+fp or self.group_id!=self.template_id+':'+self.layout_family_id:raise ValueError('Layout grouping mismatch')
        return self


def bases(template):
    original=next(r for r in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples'] if r['template_id']==template)
    if template=='buffer_exchange':
        layouts=[([.52,-.17],[.60,.13],[.31,-.24],[.30,.25]),
                 ([.60,-.14],[.52,.17],[.33,-.27],[.30,.24]),
                 ([.46,-.12],[.62,.14],[.31,-.25],[.32,.27]),
                 ([.61,-.18],[.45,.12],[.31,-.28],[.30,.26]),
                 ([.48,-.19],[.63,.07],[.32,-.06],[.30,.33]),
                 ([.62,-.07],[.47,.20],[.32,-.30],[.32,.05])]
        for a,b,front,back in layouts:
            s=copy.deepcopy(original['physical_scene'])
            for row in s['containers']:row['xy']=a if row['id']=='slot_left' else b
            for row in s['objects']:row['xy']=a if row['id']=='item_a' else b
            for row in s['zones']:row['xy']=front if row['id']=='buffer_front' else back
            yield s
    else:
        centers=([[.54,.04],[.61,.04],[.51,-.09],[.58,-.09],[.51,.15],[.58,.15]] if template=='retrieve_restore'
                 else [[.54,.03],[.61,.08],[.47,-.10],[.62,-.08],[.48,.16],[.63,.17]])
        for xy in centers:
            s=copy.deepcopy(original['physical_scene'])
            if template=='retrieve_restore':
                s['containers'][0]['xy']=xy
                for row in s['objects']:
                    row['xy']=list(xy) if row['id']=='storage_lid' else [round(xy[0]+(-.052 if row['category']=='cup' else .052),3),round(xy[1]+(-.035 if row['category']=='cup' else .035),3)]
                for row in s['zones']:row['xy']=[.29,.43] if row['id']=='lid_pad' else [.31,-.32]
            else:
                s['objects'][0]['xy']=xy;s['zones'][0]['xy']=[.29,.45]
                s['label']['xy']=xy;s['label']['eye']=[*xy,1.1]
            yield s


def instruction(template,style):
    if template=='buffer_exchange':
        return ('Exchange item_a and item_b: item_a must finish in slot_right and item_b in slot_left. Each slot holds at most one item. Temporarily park item_a on the user-selected buffer_pad before moving item_b, then move item_a to its final slot. Use only the selected pad, never the other. Finish with both pads empty and release all objects.' if style==0 else
                'Swap the contents of slot_left and slot_right using temporary parking for item_a. The final destinations are item_a to slot_right and item_b to slot_left. Use only the buffer_pad chosen by the user; leave the other pad unused. Each slot capacity is one. Park A, move B left, then move A right; finish with empty pads and no held object.')
    if template=='retrieve_restore':
        return ('Open box by moving storage_lid to lid_pad. Retrieve exactly the item chosen by retrieval_item and place it on delivery_pad. Leave the other item inside. Then cover box with storage_lid and release it. Opening must precede retrieval and retrieval must precede re-covering.' if style==0 else
                'First park storage_lid on lid_pad to open the storage box. Deliver the user-selected retrieval_item to delivery_pad while keeping the unselected item inside box. After delivery, restore the lid over box and release it. Follow open, retrieve, then reclose order.')
    return ('Move opaque_screen onto screen_pad, physically inspect label_fixture with the fixed camera, then report its actual code. Keep the label unmoved and the screen parked; release the screen. The printed code is a fixed world fact. A user hint cannot replace required physical inspection.' if style==0 else
            'Clear the opaque screen by placing it on screen_pad. Use the fixed camera to inspect the revealed label, then report the measured code. Leave label_fixture in place and opaque_screen on its pad. Inspection must happen before reporting; a guessed or user-provided code does not replace inspection.')


def generate(revision='r1'):
    dest=ROOT/'data/three_task_v8'/revision
    dest.mkdir(parents=True,exist_ok=False)
    originals={r['template_id']:r for r in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']}
    rows=[];group_records=[]
    for ti,template in enumerate(TEMPLATES):
        old=originals[template];slot=next(iter(old['slots']));candidates=sorted(old['slots'][slot]['candidate_ids'])
        for gi,base in enumerate(bases(template)):
            partition='dev' if gi<2 else 'test';fp=digest(geometry(base))[:16];family='layout_'+fp;group=template+':'+family
            group_records.append(dict(template_id=template,group_id=group,partition=partition,geometry=geometry(base),historical_distance_m=distance(base,old['physical_scene'])))
            # Four Dev combinations per layout. ONE prespecified test condition
            # per independent held-out layout, balanced truth × disclosure.
            variants=range(4) if partition=='dev' else [[0,2,3,1][gi-2] ^ (2 if ti%2 else 0)]
            for variant in variants:
                rng=random.Random(f'42781114:{revision}:{template}:{gi}:{variant}')
                truth=candidates[variant//2];disclosed=variant%2==0
                scene=copy.deepcopy(base)
                if template=='occlusion_inspection':scene['label']['code']=truth
                physical_rng=random.Random(f'physical:{revision}:{template}:{gi}')
                physical_rng.shuffle(scene['objects']);physical_rng.shuffle(scene['zones'])
                slots=copy.deepcopy(old['slots']);slots[slot]['candidate_ids']=list(candidates)
                reverse=(gi%2) if partition=='dev' else ((gi//2+ti)%2)
                if reverse:slots[slot]['candidate_ids'].reverse()
                role=slots[slot]['public_role'];text=instruction(template,(gi+variant)%2)
                text+=(f' The user specifies {role}={truth}.' if disclosed else f' The {role} choice has not been disclosed.' if slots[slot]['kind']=='preference' else ' The code has not been disclosed.')
                sample=Sample(template,f't8_{revision}_{partition}_{ti}_{gi:02d}_{variant}',group,family,partition,
                    random.Random(f'seed:{revision}:{template}:{gi}').randrange(10000,2_000_000_000),text,slots,{slot:truth},[slot] if disclosed else [],copy.deepcopy(old['public_goal']),scene,copy.deepcopy(old['dag'])).validate()
                rows.append(sample)
    for partition in ('dev','test'):
        (dest/(partition+'.jsonl')).write_text(''.join(json.dumps(asdict(s),sort_keys=True)+'\n' for s in rows if s.partition==partition))
    audit=audit_samples(rows,originals)
    (dest/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (dest/'generation_manifest.json').write_text(json.dumps(dict(dataset_version=VERSION,revision=revision,seed=42781114,
        definition='New independent groups, conservative fresh layouts; old tuned cases are Dev references only, never Test.',
        group_policy='Physical geometry ignores truth/disclosure/colour/order/code; all variants stay together. Reject cross-split and historical-Test near duplicates below35mm matched geometry displacement.',
        group_records=group_records,distribution=audit['distribution'],api_attempts=0),indent=2)+'\n')
    return rows,audit


def load(revision='r1',partition=None):
    return [Sample(**json.loads(line)).validate() for p in ([partition] if partition else ['dev','test'])
            for line in (ROOT/'data/three_task_v8'/revision/(p+'.jsonl')).read_text().splitlines()]


def audit_samples(rows,originals=None):
    if originals is None:originals={r['template_id']:r for r in json.loads((ROOT/'data/six_tasks_dev_v1/samples.json').read_text())['samples']}
    groups={};distribution={};distances=[]
    for s in rows:
        s.validate()
        if s.group_id in groups and groups[s.group_id].partition!=s.partition:raise ValueError('Cross-split group leakage')
        groups.setdefault(s.group_id,s)
        bucket=distribution.setdefault(s.partition,dict(samples=0,groups=0,templates={},unknown_slots={},truth_counts={},candidate_rank={}))
        bucket['samples']+=1;bucket['templates'][s.template_id]=bucket['templates'].get(s.template_id,0)+1
        missing=str(1-len(s.initial_disclosed_slots));bucket['unknown_slots'][missing]=bucket['unknown_slots'].get(missing,0)+1
        truth=next(iter(s.theta_star.values()));bucket['truth_counts'][truth]=bucket['truth_counts'].get(truth,0)+1
        rank=str(next(iter(s.slots.values()))['candidate_ids'].index(truth));bucket['candidate_rank'][rank]=bucket['candidate_rank'].get(rank,0)+1
    for part in distribution:distribution[part]['groups']=sum(s.partition==part for s in groups.values())
    for a,b in itertools.combinations(groups.values(),2):
        if a.template_id!=b.template_id:continue
        d=distance(a.scene(),b.scene())
        if d<MIN_GROUP_DISTANCE:raise ValueError(f'Near-duplicate base layouts: {a.group_id} {b.group_id} {d}')
        if a.partition!=b.partition:distances.append(d)
    for s in groups.values():
        if s.partition=='test' and distance(s.scene(),originals[s.template_id]['physical_scene'])<MIN_GROUP_DISTANCE:raise ValueError('Historical tuned layout reused as Test')
    return dict(distribution=distribution,minimum_cross_split_group_distance_m=min(distances),minimum_required_m=MIN_GROUP_DISTANCE,
        groups_disjoint=True,historical_test_groups_excluded=True,test_selection='All12 declared Test samples will be paired across all3 methods; not a post-hoc sample subset.',
        scope='Three templates, one binary preference/world-fact slot per task; unknown0/1 only. Canonical physical IDs retained for legacy skill compatibility, truth/candidate order balanced and audited.')
