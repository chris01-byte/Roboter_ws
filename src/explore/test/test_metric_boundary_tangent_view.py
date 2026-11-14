"""Actual B73 local view: use the measured boundary's tangent directions."""
import copy
import json
import math
from pathlib import Path
import time
import pytest

from explore.metric_frontier import MetricCandidate
from explore.metric_frontier import MetricTaskPolicy
from test_metric_public_cooldown import frozen
from test_metric_departure import path

NAME='ap06_b73_before_last_view'


def test_optional_view_lookup_cannot_allocate_a_new_task_budget():
    policy=MetricTaskPolicy(.6,30.,2)
    assert policy.identify((1.,0.),create=False) is None
    assert policy.next_id==0 and policy.attempts=={}
    key=policy.identify((1.,0.))
    policy.attempts[key].tries=3
    before=copy.deepcopy(policy.attempts)
    assert policy.identify((1.1,0.),(.5,0.),create=False)==key
    assert policy.identify((3.,0.),create=False) is None
    assert before==policy.attempts and policy.next_id==1


def test_actual_boundary_tangent_improves_last_view_without_renewing_history():
    n,i,p=frozen(NAME)
    before=copy.deepcopy(p.attempts)
    next_id=p.next_id
    candidates=n._metric_select(i,p,.3)
    assert candidates and not candidates[0].requires_nav2_plan
    candidate=candidates[0]
    assert candidate.task_id=='metric-task-9'
    assert len(candidate.observation_points)>=7  # old first-safe view has one
    assert math.dist(i[2][:2],(candidate.x,candidate.y))<=.6+1e-12
    assert n._metric_waypoints_clear(i,candidate.route,candidate.yaw) is not None
    assert before==p.attempts
    assert next_id==p.next_id
    assert p.attempts['metric-task-2'].tries==3


def test_recorded_native_tangent_arrival_keeps_real_stop_and_turning_refuge():
    n,i,_,=frozen(NAME)
    meta=json.loads((Path(__file__).parent/'data'/(NAME+'.json')).read_text())
    record=meta['native_plans'][0]
    target=MetricCandidate('recorded-native',*record['goal'],(2.9249999346211553,-.04499999899417162),
        (),1.,0.,i[1].fingerprint,1)
    route=n._metric_validate_nav_plan(i,path(record),target,public_only=True)
    assert route is not None
    stop=n._metric_rollout_stop_pose(i,route,target.yaw,native_plan=True)
    assert math.dist(stop[:2],record['goal'][:2])<=.15
    assert n._metric_scan_geometry_ready((i[0],i[1],stop,*i[3:]))


def test_tangent_search_does_not_reopen_an_exhausted_original_task():
    n,i,p=frozen(NAME)
    p.identify((2.9249999346211553,-.04499999899417162))
    p.attempts['metric-task-9'].tries=3
    before=copy.deepcopy(p.attempts)
    candidates=n._metric_select(i,p,.3)
    assert not any(c.task_id=='metric-task-9' for c in candidates)
    assert all(p.attempts[key]==attempt for key,attempt in before.items())


def test_current_heading_cost_orders_b76_tangent_inside_original_helper_window():
    from dataclasses import replace
    from explore.explore_node import Frontier
    name='ap06_b76_before_third_view'
    n,i,p=frozen(name,elapsed_s=31.)
    meta=json.loads((Path(__file__).parent/'data'/(name+'.json')).read_text())
    selected=MetricCandidate(**meta['original_third_target'])
    selected=replace(selected,fingerprint=i[1].fingerprint)
    frontier=Frontier(selected.frontier_xy,1.)
    frontier.approach_direction=(-1.,0.)
    before=copy.deepcopy(p.attempts);next_id=p.next_id
    started=time.monotonic()
    refined=n._metric_refine_observation(i,frontier,p,n._metric_scope_mask(i),
        selected,selected.task_id,started+.5)
    assert len(refined.observation_points)>len(selected.observation_points)
    assert refined.cost<selected.cost
    assert refined.x==pytest.approx(i[2][0])
    assert refined.y==pytest.approx(i[2][1]-.45)
    assert n._metric_waypoints_clear(i,refined.route,refined.yaw) is not None
    assert before==p.attempts and next_id==p.next_id


def test_b76_native_tangent_keeps_stop_and_departure_reserve():
    name='ap06_b76_before_third_view'
    n,i,p=frozen(name)
    meta=json.loads((Path(__file__).parent/'data'/(name+'.json')).read_text())
    rec=meta['native_plans'][0]
    target=MetricCandidate('component',*rec['goal'],(2.8949999352917075,-.07499999832361937),
        (),1.,0.,i[1].fingerprint,1)
    route=n._metric_validate_nav_plan(i,path(rec),target,public_only=True)
    assert route is not None
    stop=n._metric_rollout_stop_pose(i,route,target.yaw,native_plan=True)
    assert math.dist(stop[:2],(target.x,target.y))<=.15
    assert n._metric_scan_geometry_ready((i[0],i[1],stop,*i[3:]))
    assert n._metric_departure_plan_ready(i,route,target,lambda:False)
