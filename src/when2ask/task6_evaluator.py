"""Independent geometric/evidence scoring. Never scores a proposed action ID."""
import math

import pybullet as p

VERSION='task6_geometry_contact_evidence_v1'


def evaluate(world,sample,*,burden=0,actions=(),termination='done',overrides=None):
    theta={**sample.theta_star,**(overrides or {})};choice=next(iter(theta.values()))
    goal=sample.public_goal;kind=sample.template_id;details={}
    if kind=='patrol_return':
        from .navigation_map import LOCATIONS
        required={goal['required_station'],choice}
        evidence=[]
        for e in world.inspection_evidence:
            station=LOCATIONS[e['location_id']]
            # Pose and actual ray result, not a planner's "visited" claim.
            ok=(e['success'] and math.dist(e['robot_pose'][:2],station['xy'])<=.22
                and e['yaw_error']<.20 and e['fixture_distance_m']<1.65 and e['ray_hit_body']==world.beacons[e['location_id']]
                and math.dist(e['ray_hit_point'],e['ray_endpoint'])<.4)
            if ok:evidence.append(e)
        visited={e['location_id'] for e in evidence};pose=world.pose();v,w=p.getBaseVelocity(world.robot,physicsClientId=world.client)
        final_return=world.return_events[-1] if world.return_events else None
        checks=dict(required_stations_physically_inspected=required<=visited,
            returned_to_start=math.dist(pose[:2],goal['home_xy'])<=goal['home_radius_m'],
            inspections_before_return=bool(required<=visited and final_return and all(any(e['location_id']==k and e['step']<final_return['step'] for e in evidence) for k in required)),
            robot_stopped=math.hypot(v[0],v[1])<.08 and abs(w[2])<.12,
            no_wall_penetration=not any(c[8]<-.02 for wall in world.walls for c in p.getContactPoints(world.robot,wall,physicsClientId=world.client)),
            distance_budget_respected=world.distance_m<=36)
        details=dict(required_stations=sorted(required),inspection_evidence=evidence,final_pose=pose,distance_m=world.distance_m)
    else:
        contents=world.contents();zones=world.zone_contents();checks={}
        if kind=='category_sorting':
            other=next(c for c in goal['other_bins'] if c!=choice)
            targets={'cup':goal['cup_bin'],'block':choice,'puck':other}
            placements={k:world.containment(k,targets[o.category]) for k,o in world.objects.items() if o.category in targets}
            checks=dict(all_items_in_category_bins=all(v['inside'] for v in placements.values()),
                categories_not_mixed=all(len({world.objects[k].category for k in keys})<=1 for keys in contents.values()))
            details=dict(expected_category_bins=targets,containment=placements)
        elif kind=='inventory_restock':
            cups=contents[goal['cup_bin']];blocks=contents[goal['block_bin']]
            protected=['stocked_cup','stocked_block'];grasped={e['object_id'] for e in world.events if e['kind']=='grasp'}
            spares=[k for k in world.movable() if k.startswith('spare_') and k not in cups+blocks]
            checks=dict(exact_cup_inventory=len(cups)==goal['cup_quota'] and all(world.objects[k].category=='cup' for k in cups),
                exact_block_inventory=len(blocks)==int(choice) and all(world.objects[k].category=='block' for k in blocks),
                original_stock_untouched=all(k not in grasped and math.dist(world.body_pose(k)[0],world.initial_positions[k])<.01 for k in protected),
                surplus_stock_untouched=all(k not in grasped and math.dist(world.body_pose(k)[0],world.initial_positions[k])<.01 for k in spares))
            details=dict(actual_inventory={goal['cup_bin']:cups,goal['block_bin']:blocks},target_block_count=int(choice))
        elif kind=='retrieve_restore':
            other=next(k for k in goal['items'] if k!=choice)
            opened=[c for c in world.checkpoints if goal['lid'] in c['zones'][goal['lid_pad']]]
            delivered=[c for c in world.checkpoints if choice in c['zones'][goal['delivery_pad']]]
            covers=[e for e in world.events if e['kind']=='cover_started']
            coverage=world.coverage(goal['lid'])
            checks=dict(selected_item_delivered=world.in_zone(choice,goal['delivery_pad']),
                other_item_left_inside=world.containment(other,'box')['inside'],box_reclosed=coverage['covered'],
                uncover_retrieve_restore_order=bool(opened and delivered and covers and any(a['step']<b['step']<=c['step'] for a in opened for b in delivered for c in covers)))
            details=dict(selected_item=choice,coverage=coverage)
        elif kind=='buffer_exchange':
            a,b=goal['item_a'],goal['item_b'];other=next(z for z in goal['buffers'] if z!=choice)
            parked=[c for c in world.checkpoints if a in c['zones'][choice]]
            b_left=[c for c in world.checkpoints if b in c['contents'][goal['left']]]
            a_right=[c for c in world.checkpoints if a in c['contents'][goal['right']]]
            checks=dict(items_exchanged=world.containment(a,goal['right'])['inside'] and world.containment(b,goal['left'])['inside'],
                selected_buffer_physically_used=bool(parked),other_buffer_unused=not any(c['zones'][other] for c in world.checkpoints),
                buffers_empty_at_end=not any(zones[z] for z in goal['buffers']),
                capacity_respected=all(len(c['contents'][z])<=1 for c in world.checkpoints for z in (goal['left'],goal['right'])),
                buffer_exchange_order=any(x['step']<y['step']<z['step'] for x in parked for y in b_left for z in a_right))
            details=dict(selected_buffer=choice,checkpoints=world.checkpoints)
        elif kind=='occlusion_inspection':
            # World fact cannot be changed by a manual answer or evaluator override.
            truth=sample.physical_scene['label']['code'];camera=world.camera()
            observations=[e for e in world.inspections if e['camera']['visible'] and e['camera']['range_m']<=.8 and e['code']==truth]
            reports=[e for e in world.reports if e['code']==truth]
            checks=dict(screen_parked=world.in_zone(goal['screen'],goal['screen_pad']),
                label_physically_observed=bool(observations),line_of_sight_clear_now=camera['visible'],
                correct_report_after_inspection=any(a['step']<=b['step'] for a in observations for b in reports),
                label_not_moved=math.dist(world.body_pose('label_fixture')[0],world.initial_positions['label_fixture'])<.001)
            details=dict(actual_code=truth,camera=camera,inspections=world.inspections,reports=world.reports)
        else:raise ValueError('Unknown task evaluator')
        contacts={k:len(p.getContactPoints(world.objects[k].body_id,world.robot,physicsClientId=world.client)) for k in world.movable()}
        checks.update(robot_released=world.released() and not any(contacts.values()),all_movable_objects_stable=all(world.stable(k) for k in world.movable()))
        details['robot_contact_counts']=contacts
    return dict(task_success=all(checks.values()),termination_reason=termination,conditions=checks,details=details,
        clarification_burden=burden,action_count=len(actions),successful_action_count=sum(a['success'] for a in actions),
        simulation_steps=world.step_count,evaluator_version=VERSION)
