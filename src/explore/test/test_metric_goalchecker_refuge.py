"""Recorded B68 public geometry; these are component evidence only.

Actual terminal rasters, scan and exhausted ledger are retained. One explicit
component variant contains only the two completed tasks; it does not alter or
claim the recorded terminal history or a whole-mission result.
"""
import copy
import math
import time

import pytest

from explore.explore_node import Frontier
from explore.metric_frontier import MetricCandidate, MetricTaskPolicy, footprint_clear
from explore.metric_checkpoint import restore_policy
from test_metric_robot_side_observation import fixture
from test_metric_departure import path


def geometry():
    return fixture('ap06_b68_public_refuge')


def checker_disk_turn_room(node, inputs, goal):
    return all(footprint_clear(*goal[:2],goal[2]+math.pi,g,mask,
        node._world_to_grid,node._grid_to_world,node._metric_bounds,
        heading_half_angle=math.pi,heading_samples=127,center_deviation_m=.15+.02)
        for g,mask in ((inputs[0],inputs[3]),(inputs[5],inputs[6])))


def test_b68_public_choice_has_turn_room_across_goalchecker_disk():
    node,inputs,metadata=geometry()
    original,_=restore_policy(metadata['checkpoint'],time.monotonic(),
                              metadata['checkpoint']['saved_wall_time'])
    # Completed-only COMPONENT history on explicitly terminal rasters.
    # All terminal exhausted tasks remain available in the separate test.
    policy=MetricTaskPolicy(.6,30.,2);policy.next_id=9
    for key in ('metric-task-1','metric-task-8'):
        policy.attempts[key]=copy.deepcopy(original.attempts[key])
    before={k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items()}
    frontier=Frontier(original.attempts['metric-task-2'].frontier_xy,1)
    candidate=node._metric_public_observation(inputs,[frontier],policy,
        node._metric_scope_mask(inputs),time.monotonic())
    assert candidate is not None
    assert candidate.observation_points and not candidate.requires_nav2_plan
    assert checker_disk_turn_room(node,inputs,(candidate.x,candidate.y,candidate.yaw))
    assert node._metric_waypoints_clear(inputs,candidate.route,candidate.yaw) is not None
    assert .3-1e-12 <= math.dist(inputs[2][:2],(candidate.x,candidate.y)) <= .6+1e-12
    assert before=={k:(policy.attempts[k].tries,policy.attempts[k].failures,
                       policy.attempts[k].completed) for k in before}


@pytest.mark.parametrize('index',range(5))
def test_actual_native_near_refuges_preserve_full_arrival_and_departure(index):
    node,inputs,metadata=geometry();record=metadata['plans'][index]
    target=MetricCandidate('recorded-native',*record['goal'],tuple(record['goal'][:2]),
                           (),1.,0.,inputs[1].fingerprint,1)
    route=node._metric_validate_nav_plan(inputs,path(record),target,public_only=True)
    assert route is not None
    assert checker_disk_turn_room(node,inputs,record['goal'])
    assert node._metric_departure_plan_ready(inputs,route,target,lambda:False)


def test_original_b68_exhausted_tasks_and_neighbours_remain_capped():
    node,inputs,metadata=geometry()
    policy,_=restore_policy(metadata['checkpoint'],time.monotonic(),
                           metadata['checkpoint']['saved_wall_time'])
    before={k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items()}
    assert policy.attempts['metric-task-2'].tries==3
    assert policy.attempts['metric-task-3'].tries==3
    candidates=node._metric_select(inputs,policy,.3)
    for candidate in candidates:
        assert candidate.task_id not in ('metric-task-2','metric-task-3')
        assert all(math.dist(candidate.frontier_xy,policy.attempts[k].frontier_xy)>=policy.radius
            and math.dist((candidate.x,candidate.y),policy.attempts[k].target_xy)>=policy.radius
            for k in ('metric-task-2','metric-task-3'))
    assert before=={k:(policy.attempts[k].tries,policy.attempts[k].failures,
                       policy.attempts[k].completed) for k in before}
