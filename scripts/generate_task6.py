"""Write a new independent six-task design; refuses to overwrite existing data."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from when2ask.config import ROOT


def main():
    out = ROOT / 'data/six_tasks_dev_v1'
    if out.exists(): raise FileExistsError('Use a new version; preserve previous designs/evidence')
    samples = []
    def add(template, instruction, role, candidates, choice, goal, scene, nodes, edges, kind='preference'):
        samples.append(dict(template_id=template, sample_id='task6_'+template+'_001', scene_seed=4278,
            u0=instruction, slots={role+'_choice':dict(public_role=role,candidate_ids=candidates,
                description=goal.pop('slot_description'),kind=kind)}, theta_star={role+'_choice':choice},
            initial_disclosed_slots=[],public_goal=goal,physical_scene=scene,dag=dict(nodes=nodes,edges=edges)))
    def container(key, xy, half=(.085,.085), height=.10, color='orange'):
        return dict(id=key,xy=xy,half_xy=list(half),wall_height=height,color=color)
    def obj(key,category,xy,color,z=None):
        return dict(id=key,category=category,xy=xy,color=color,**({'z':z} if z is not None else {}))
    add('category_sorting',
        'Sort all six objects into three category bins. Cups go in bin_a. Ask for the user\'s block_bin choice if needed; '
        'pucks use the OTHER bin among bin_b and bin_c. Do not mix categories. Release every object. '
        'You can sort the known cups before needing the missing rule.',
        'block_bin',['bin_b','bin_c'],'bin_c',
        dict(cup_bin='bin_a',other_bins=['bin_b','bin_c'],categories=['cup','block','puck'],
             slot_description='Which bin should contain the blocks? Pucks use the remaining bin.'),
        dict(containers=[container('bin_a',[.55,-.29]),container('bin_b',[.57,0]),container('bin_c',[.55,.29])],
            objects=[obj('cup_1','cup',[.28,-.30],'red'),obj('cup_2','cup',[.37,-.18],'blue'),
                obj('block_1','block',[.28,-.06],'green'),obj('block_2','block',[.36,.06],'yellow'),
                obj('puck_1','puck',[.28,.21],'purple'),obj('puck_2','puck',[.36,.34],'cyan')]),
        ['sort_cups','sort_blocks','sort_pucks'],[])
    add('inventory_restock',
        'Restock the cup shelf to exactly 2 cups. Restock the block shelf to the user\'s block_quota, either 2 or 3 blocks. '
        'Count current physical contents first and add only the deficit. Do not move already stocked items or surplus spare stock. '
        'Cup replenishment is fully specified even before the block quota is known.',
        'block_quota',['2','3'],'3',
        dict(cup_bin='cup_shelf',block_bin='block_shelf',cup_quota=2,
             slot_description='How many blocks should the block shelf hold in total: 2 or 3?'),
        dict(containers=[container('cup_shelf',[.56,-.19],(.12,.095)),container('block_shelf',[.56,.19],(.12,.095))],
            objects=[obj('stocked_cup','cup',[.515,-.19],'red',.465),obj('stocked_block','block',[.515,.19],'green',.457),
                obj('spare_cup_1','cup',[.29,-.29],'blue'),obj('spare_cup_2','cup',[.29,-.15],'cyan'),
                obj('spare_block_1','block',[.29,.045],'yellow'),obj('spare_block_2','block',[.29,.25],'purple')]),
        ['count_inventory','replenish_cups','replenish_blocks'],[['count_inventory','replenish_cups'],['count_inventory','replenish_blocks']])
    add('retrieve_restore',
        'Open the storage box by parking its lid on lid_pad. Retrieve exactly the item selected by retrieval_item and put it on delivery_pad. '
        'Then replace the lid to close the box. Leave the unselected item inside. The selected item is initially unspecified. '
        'Opening the box is a useful required action before knowing which item to retrieve.',
        'retrieval_item',['stored_cup','stored_block'],'stored_block',
        dict(box='box',lid='storage_lid',lid_pad='lid_pad',delivery_pad='delivery_pad',items=['stored_cup','stored_block'],
             slot_description='Which item should be retrieved from the box?'),
        dict(containers=[container('box',[.57,.06],(.14,.12),.11,'brown')],
            zones=[dict(id='lid_pad',xy=[.30,.39],half_xy=[.16,.14]),dict(id='delivery_pad',xy=[.33,-.22],half_xy=[.075,.075])],
            objects=[obj('stored_cup','cup',[.518,.025],'blue',.465),obj('stored_block','block',[.622,.095],'green',.457),
                     obj('storage_lid','lid',[.57,.06],'black',.55)]),
        ['uncover','retrieve','restore_lid'],[['uncover','retrieve'],['retrieve','restore_lid']])
    add('buffer_exchange',
        'Exchange item_a in slot_left and item_b in slot_right. Each slot holds at most one item. '
        'Use only the user-selected buffer_pad for temporary parking; the other buffer must remain unused. '
        'Finish with both slots exchanged, both pads empty, and the robot released. The required buffer_pad is unspecified.',
        'buffer_pad',['buffer_front','buffer_back'],'buffer_back',
        dict(left='slot_left',right='slot_right',item_a='item_a',item_b='item_b',buffers=['buffer_front','buffer_back'],
             slot_description='Which temporary pad should be used for the exchange?'),
        dict(containers=[container('slot_left',[.55,-.16],(.045,.045),.075),container('slot_right',[.55,.16],(.045,.045),.075,'purple')],
            zones=[dict(id='buffer_front',xy=[.31,-.22],half_xy=[.065,.065]),dict(id='buffer_back',xy=[.31,.22],half_xy=[.065,.065])],
            objects=[obj('item_a','block',[.55,-.16],'green',.457),obj('item_b','block',[.55,.16],'yellow',.457)]),
        ['park_a','move_b_left','move_a_right'],[['park_a','move_b_left'],['move_b_left','move_a_right']])
    add('patrol_return',
        'Physically inspect living_cabinet and the user-selected extra_station (study_desk or study_shelf), '
        'then return to the starting pose area at [0,0] and stop. Inspection requires reaching the station and facing its equipment. '
        'Do not count a user answer as an inspection. You can inspect the known living_cabinet before clarifying extra_station.',
        'extra_station',['study_desk','study_shelf'],'study_shelf',
        dict(required_station='living_cabinet',home_xy=[0,0],home_radius_m=.22,
             slot_description='Which additional study-room inspection station should be visited?'),
        dict(kind='patrol',map_version='three_room_map_v1'),
        ['inspect_known','inspect_selected','return_home'],[['inspect_known','return_home'],['inspect_selected','return_home']])
    add('occlusion_inspection',
        'Move the opaque screen onto screen_pad, use the fixed inspection camera to inspect the label underneath, '
        'and report its actual code. Leave the label in place and the screen on its pad. '
        'The code is a fixed world fact, not a preference. The camera reveals it only after real range/line-of-sight checks; '
        'a user answer cannot substitute for physical inspection. No need to ask for a code that can be observed after clearing the screen.',
        'inspection_code',['alpha','beta'],'beta',
        dict(screen='opaque_screen',screen_pad='screen_pad',inspection_target='label_fixture',
             slot_description='What is the printed inspection code? Fixed world fact; physical verification still required.'),
        dict(containers=[],zones=[dict(id='screen_pad',xy=[.30,.39],half_xy=[.16,.14])],
            objects=[obj('opaque_screen','screen',[.57,.06],'gray',.55)],
            label=dict(xy=[.57,.06],code='beta',eye=[.57,.06,1.10])),
        ['clear_screen','inspect_label','report_code'],[['clear_screen','inspect_label'],['inspect_label','report_code']],kind='world_fact')
    out.mkdir(parents=True)
    (out/'samples.json').write_text(json.dumps(dict(version='six_tasks_dev_v1',purpose='six new task templates, not frozen benchmark',samples=samples),indent=2)+'\n')
    print({'samples':len(samples),'path':str(out)})


if __name__=='__main__':main()
