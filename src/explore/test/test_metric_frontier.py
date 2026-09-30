"""Metric policy/geometric regressions; no robot/device processes."""
import math
import os
import threading
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid

from explore.metric_frontier import (
    MetricCandidate, MetricTaskPolicy, route_cells, footprint_clear,
    footprint_route_clear, known_safe_mask)
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import Point2D, PortalMapContext
from explore.portal_source_adapter import PortalSourceCorrelation
from explore.explore_node import ExploreNode


def require_isolated_ros():
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID','-1')) <= 230
    assert not os.environ.get('CYCLONEDDS_URI')


def grid():
    g=OccupancyGrid();g.info.width=80;g.info.height=40;g.info.resolution=.1
    g.info.origin.position.x=-1.;g.info.origin.position.y=-2.;g.info.origin.orientation.w=1.
    g.header.frame_id='map';g.header.stamp.sec=100
    g.data=[0]*3200
    return g


def candidate(key='metric-task-1',xy=(1.,0.)):
    return MetricCandidate(key,*xy,0.,(1.5,0.),((0.,0.),xy),1.,2.,'a'*64,1)


def test_history_survives_new_revision_and_uuid_and_needs_changed_evidence():
    p=MetricTaskPolicy(.6,30.,2)
    key=p.identify((1.5,0.));c=candidate(key)
    p.record(c,'task_unreached_cause_unproven',10,'a'*64)
    assert p.identify((1.6,.1))==key
    assert not p.eligible(key,(1.,0.),39,'b'*64)
    assert not p.eligible(key,(1.,0.),41,'a'*64)
    assert p.eligible(key,(1.,0.),41,'b'*64)
    p.record(replace(c,revision=25),'route_blocked',42,'b'*64)
    assert not p.eligible(key,(1.,0.),100,'c'*64)


def test_successful_neighbourhood_cannot_be_recreated_as_new_task():
    p=MetricTaskPolicy(.6,30.,2)
    key=p.identify((1.5,0.));p.record(candidate(key),'observed',1,'a'*64)
    other=p.identify((2.4,0.))
    assert other!=key
    assert not p.eligible(other,(1.2,.1),100,'b'*64)
    assert p.eligible(other,(2.,0.),100,'b'*64)


def test_route_never_seeds_over_unknown_or_cuts_diagonal():
    mask=np.ones((7,7),dtype=bool);mask[:,3]=False
    assert route_cells(mask,(3,1),(3,5)) is None
    assert route_cells(mask,(3,3),(3,5)) is None
    mask=np.array([[True,False],[False,True]])
    assert route_cells(mask,(0,0),(1,1)) is None


def test_open_connection_without_semantic_label_is_geometrically_reachable():
    g=grid();known=np.ones((40,80),bool)
    known[:,30:32]=False;known[12:28,30:32]=True
    mask=known.copy()
    route=route_cells(mask,(20,20),(20,45))
    assert route
    xy=tuple(ExploreNode._grid_to_world(c,r,g.info) for r,c in route)
    check=lambda x,y,yaw,g,a:footprint_clear(x,y,yaw,g,a,ExploreNode._world_to_grid,ExploreNode._grid_to_world)
    assert footprint_route_clear(xy,0.,((g,known),),check)
    # Narrowing the raster connection rejects the same physical chassis.
    known[:,30:32]=False;known[18:22,30:32]=True
    assert not footprint_route_clear(xy,0.,((g,known),),check)


def test_full_front_and_rear_footprint_and_unknown_are_checked():
    g=grid();known=np.ones((40,80),bool)
    check=lambda yaw:footprint_clear(.05,.05,yaw,g,known,ExploreNode._world_to_grid,ExploreNode._grid_to_world)
    assert check(0.)
    known[20,13]=False
    assert not check(0.)  # front at +0.33 m
    assert check(math.pi) # asymmetry changes which side is front
    known[:]=True;known[20,8]=False
    assert not check(math.pi)


def test_scope_and_unknown_reduce_route_space_before_utility():
    g=grid();context=PortalMapContext('metric','map-test','map')
    scope=AuthorizedExplorationScope('scope',context,tuple(Point2D(x,y) for x,y in ((-.8,-1.8),(3.,-1.8),(3.,1.8),(-.8,1.8))))
    c=PortalSourceCorrelation(context,1,'a'*64,1)
    occupancy=np.zeros((40,80),dtype=int);occupancy[:,25:]=-1
    known,safe=known_safe_mask(occupancy,scope,c,(-1.,-2.),0.,.1,.28)
    assert not np.any(safe[:,25:])
    assert not safe[0,10]
    assert safe[20,10]
    assert np.count_nonzero(safe)<np.count_nonzero(known)


def test_optional_semantics_do_not_enter_strategy_dependencies():
    from pathlib import Path
    text=(Path(__file__).parents[1]/'explore/metric_frontier_runtime.py').read_text()
    assert 'graph.current_region' not in text
    assert 'portal_snapshots' not in text
    assert 'create_subscription(String, \'/robot_map_manager/status_json\'' in text


def test_late_goal_acceptance_is_canceled_after_parent_timeout(monkeypatch):
    """Delayed real-client contract, no ActionServer or active hardware."""
    import explore.explore_node as module
    from builtin_interfaces.msg import Time
    from action_msgs.msg import GoalStatus
    class Future:
        def __init__(self,value=None):self.value=value;self.callbacks=[]
        def result(self):return self.value
        def add_done_callback(self,cb):self.callbacks.append(cb);return self
        def complete(self,value):
            self.value=value
            for callback in self.callbacks:callback(self)
    accept,result=Future(),Future()
    cancels=[]
    handle=SimpleNamespace(accepted=True,get_result_async=lambda:result,
                           cancel_goal_async=lambda:cancels.append(True) or Future())
    n=ExploreNode.__new__(ExploreNode)
    n._nav_client=SimpleNamespace(wait_for_server=lambda **_:True,send_goal_async=lambda _:accept)
    n._global_frame='map';n._behavior_tree='no-recovery';n._cancel_timeout_s=.05
    n._robot_xy=lambda:(0.,0.);n._record_coverage_pose=lambda _:None
    n.get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(to_msg=lambda:Time(sec=1)))
    monkeypatch.setattr(module.rclpy,'ok',lambda:True)
    assert n._navigate_to(1.,0.,.01)=='cancel_failed'
    assert n._nav_child_uncertain
    accept.complete(handle)
    assert cancels==[True]
    result.complete(SimpleNamespace(status=GoalStatus.STATUS_CANCELED))
    assert not n._nav_child_uncertain


@pytest.mark.parametrize('change,reason',[
    ('scope_verified','verified polygon'),('scope_fingerprint','initial map'),
    ('footprint','cannot shrink'),('semantic_owner','excludes the semantic'),
    ('portal','excludes direct'),('coverage','excludes direct'),('budget','positive budgets')])
def test_real_node_configuration_fails_closed(change,reason):
    require_isolated_ros()
    import rclpy
    values=dict(exploration_strategy='metric_frontier',
        wohnungserkundung_accessible_scope_verified=True,
        wohnungserkundung_scope_id='scope-test',
        wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],
        metric_session_id='metric-test',metric_scope_map_fingerprint='a'*64,
        portal_crossing_enabled=False,coverage_enabled=False,overall_timeout_s=60.,
        region_graph_shadow_enabled=False,behavior_tree='/fake/no_recovery.xml')
    if change=='scope_verified':values['wohnungserkundung_accessible_scope_verified']=False
    if change=='scope_fingerprint':values['metric_scope_map_fingerprint']=''
    if change=='footprint':values['metric_footprint_xy']=[-.1,-.2,.3,-.2,.3,.2,-.1,.2]
    if change=='semantic_owner':
        # The old policy's existing initialization contracts remain in force.
        values.update(region_graph_shadow_enabled=True,region_graph_shadow_raw_map_enabled=True,
            region_graph_shadow_session_id='test',region_graph_shadow_start_observation_id='start',
            region_graph_shadow_raw_map_capacity=100000,
            wohnungserkundung_policy_enabled=True)
    if change=='portal':values['portal_crossing_enabled']=True
    if change=='coverage':values['coverage_enabled']=True
    if change=='budget':values['overall_timeout_s']=0.
    import json
    rclpy.init(args=['--ros-args',*[x for k,v in values.items() for x in ('-p',k+':='+json.dumps(v))]])
    try:
        with pytest.raises(ValueError,match=reason):ExploreNode()
    finally:rclpy.shutdown()


def test_strategy_is_immutable_and_existing_is_default():
    require_isolated_ros()
    import rclpy
    from rclpy.parameter import Parameter
    rclpy.init(args=['--ros-args','-p','behavior_tree:=/fake/no_recovery.xml'])
    n=ExploreNode()
    try:
        assert n._exploration_strategy=='existing'
        assert not n._metric_enabled
        result=n.set_parameters([Parameter('exploration_strategy',value='metric_frontier')])[0]
        assert not result.successful
        assert n._exploration_strategy=='existing'
    finally:n.destroy_node();rclpy.shutdown()


def test_old_costmap_cannot_overwrite_new_obstacle_rejection():
    n=ExploreNode.__new__(ExploreNode);n._metric_enabled=True
    blocked=grid();blocked.header.stamp.sec=101;blocked.data=[100]*3200
    n._global_costmap=None
    n._on_global_costmap(blocked)
    n._on_global_costmap(grid())
    assert n._global_costmap is blocked


def test_delayed_old_raw_map_cannot_reopen_new_blockage():
    n=ExploreNode.__new__(ExploreNode);n._metric_lock=threading.RLock()
    n._metric_raw=None;n._metric_correlation=None;n._metric_pending_since=None
    n._metric_fault=None;n._global_frame='map';n._wohnungserkundung_evidence_max_cells=262144
    blocked=grid();blocked.header.stamp.sec=101;blocked.data=[100]*3200
    n._on_metric_map(blocked)
    n._on_metric_map(grid())
    assert n._metric_raw[0] is blocked
    assert n._metric_fault is None


def test_new_foreign_map_latches_fault_and_later_valid_map_does_not_clear_it():
    n=ExploreNode.__new__(ExploreNode);n._metric_lock=threading.RLock()
    n._metric_raw=None;n._metric_correlation=None;n._metric_pending_since=None
    n._metric_fault=None;n._global_frame='map';n._wohnungserkundung_evidence_max_cells=262144
    wrong=grid();wrong.header.frame_id='foreign'
    n._on_metric_map(wrong)
    assert 'map_frame_changed' in n._metric_fault
    n._on_metric_map(grid())
    assert 'map_frame_changed' in n._metric_fault


def test_rotated_approach_refinement_stays_bounded_and_checks_full_route():
    """A real input frontier's rotated front touches unknown at the old point."""
    import time
    from explore.metric_frontier_runtime import MetricFrontierRuntime
    from explore.portal_source_adapter import raw_map_portal_source_from_values
    n=ExploreNode.__new__(ExploreNode)
    n._global_frame='map';n._map_timeout_s=5.;n._global_costmap_received_at=time.monotonic()
    n._frontier_goal_max_cost=90;n._goal_clearance_m=.28;n._goal_search_m=.30;n._approach_dist_m=.45
    n._min_goal_dist_m=.30;n._frontier_forward_cone_half_angle=0.
    n._potential_scale=3.;n._gain_scale=1.;n._heading_scale=.75
    n._metric_bounds=(-.13,.33,-.25,.25);n._visualize=False
    g=grid();a=np.zeros((40,80),int);a[:,25:]=-1
    a[(0,39),:]=100;a[:,(0,79)]=100;a[19:21,18:]=100
    g.data=a.ravel().tolist()
    cm=grid();cm.data=np.maximum(a,0).ravel().tolist();n._global_costmap=cm
    source=raw_map_portal_source_from_values(**MetricFrontierRuntime._metric_grid_values(g))
    context=PortalMapContext('metric','test-map','map')
    correlation=PortalSourceCorrelation(context,1,source.fingerprint,source.source_stamp_ns)
    scope=AuthorizedExplorationScope('scope',context,tuple(Point2D(x,y) for x,y in
        ((-.8,-1.8),(6.8,-1.8),(6.8,1.8),(-.8,1.8))))
    known,safe=known_safe_mask(a,scope,correlation,(-1.,-2.),0.,g.info.resolution,.28)
    inputs=(g,correlation,(.05,.05,0.),known,safe,cm,np.asarray(cm.data).reshape(40,80)<100)
    frontiers=n._detect_frontiers(g,.3)
    initial=[n._frontier_approach_goal(f,(.05,.05),g) for f in frontiers]
    assert len(initial)==2 and all(n._metric_route(inputs,goal) is None for goal in initial)
    candidates=n._metric_select(inputs,MetricTaskPolicy(.6,30.,2),.3)
    assert len(candidates)==2
    for c in candidates:
        assert min(math.dist((c.x,c.y),goal) for goal in initial)<=n._goal_search_m
        assert n._metric_route(inputs,(c.x,c.y)) is not None
    # Nothing about this refinement permits a genuinely blocked route.
    inputs=(g,correlation,(.05,.05,0.),np.zeros_like(known),np.zeros_like(safe),cm,np.zeros_like(known))
    assert n._metric_select(inputs,MetricTaskPolicy(.6,30.,2),.3)==[]


def test_active_route_also_revalidates_the_original_nav2_goal_orientation():
    n=ExploreNode.__new__(ExploreNode);n._metric_bounds=(-.13,.33,-.25,.25)
    g=grid();known=np.ones((40,80),bool);known[20,14]=False
    safe=np.ones_like(known)
    inputs=(g,None,(.05,.05,math.pi),known,safe,g,known)
    assert n._metric_route(inputs,(.05,.05)) is not None
    assert n._metric_route(inputs,(.05,.05),math.pi) is not None
    assert n._metric_route(inputs,(.05,.05),0.) is None
    assert n._metric_last_route_rejection=='goal_orientation_invalid'
