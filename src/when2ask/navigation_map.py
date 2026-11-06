"""Public known map. No target location or private scenario registry."""
import copy
import math

TEMPLATE = 'find_and_approach'
ROOMS = {'kitchen':(-4.,0.), 'living_room':(0.,0.), 'study':(4.,0.)}
LOCATIONS = {
    'kitchen_counter':dict(room='kitchen',name='Kitchen counter',xy=[-4.,1.1],yaw=math.pi/2),
    'kitchen_shelf':dict(room='kitchen',name='Kitchen shelf',xy=[-4.,-1.1],yaw=-math.pi/2),
    'living_cabinet':dict(room='living_room',name='Living room cabinet',xy=[0.,1.1],yaw=math.pi/2),
    'living_table':dict(room='living_room',name='Living room table',xy=[0.,-1.1],yaw=-math.pi/2),
    'study_desk':dict(room='study',name='Study desk',xy=[4.,1.1],yaw=math.pi/2),
    'study_shelf':dict(room='study',name='Study shelf',xy=[4.,-1.1],yaw=-math.pi/2),
}


def room_at(xy):
    return 'kitchen' if xy[0]<-2 else 'study' if xy[0]>2 else 'living_room'


def route(xy, location):
    """Shortest path on the shared corridor/inspection graph, plus current pose."""
    if location not in LOCATIONS:
        raise ValueError('Unknown inspection location')
    here, there = room_at(xy), LOCATIONS[location]['room']
    goal = LOCATIONS[location]['xy']
    if here==there:
        return [list(goal)]
    rooms = list(ROOMS)
    i,j = rooms.index(here),rooms.index(there)
    step = 1 if j>i else -1
    return [list(ROOMS[rooms[k]]) for k in range(i,j+step,step)] + [list(goal)]


def route_distance(xy, location):
    points = [list(xy)] + route(xy, location)
    return sum(math.dist(a,b) for a,b in zip(points,points[1:]))


def public_map():
    return dict(version='three_room_map_v1',rooms={k:list(v) for k,v in ROOMS.items()},
        doorways=[[-2,0],[2,0]],locations=copy.deepcopy(LOCATIONS),
        sensing=dict(range_m=1.65,horizontal_fov_degrees=90,requires_line_of_sight=True),
        goal=dict(detect_target=True,approach_distance_m=1.2,no_pickup_or_delivery=True),
        limits=dict(distance_m=36,search_actions=8),
        search_scope='Six declared open-surface inspection stations; a negative observation covers the inspected station, not an entire room.')
