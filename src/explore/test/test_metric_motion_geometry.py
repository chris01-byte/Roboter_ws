"""AP-03 actual chassis/Explorer regressions with real ROS messages.

Nav2 execution lives in the separate closed-loop harness; these tests must not
claim a synthetic ActionServer is a real planner or controller.
"""
import math
from dataclasses import replace

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid, Path
from geometry_msgs.msg import PoseStamped

from explore.explore_node import ExploreNode
from explore.metric_frontier import MetricCandidate, MetricTaskPolicy, footprint_clear, rpp_trajectory
import explore.metric_frontier as motion
from test_metric_frontier import adaptive_fixture


def door_inputs(width=.68, resolution=.02):
    n,base=adaptive_fixture();n._metric_path_validation='rpp_rollout'
    g=OccupancyGrid();g.header.frame_id='map';g.info.resolution=resolution
    g.info.width=g.info.height=round(4/resolution);g.info.origin.position.x=g.info.origin.position.y=-2.;g.info.origin.orientation.w=1.
    rr,cc=np.indices((g.info.height,g.info.width));x=-2+(cc+.5)*resolution;y=-2+(rr+.5)*resolution
    values=np.zeros(x.shape,np.int8);values[(abs(x)<.1)&(abs(y)>=width/2)]=100
    values[[0,-1],:]=100;values[:,[0,-1]]=100;g.data=values.ravel().tolist()
    known=values==0
    n._metric_scope=replace(n._metric_scope,vertices=tuple(type(n._metric_scope.vertices[0])(x,y) for x,y in ((-1.9,-1.9),(1.9,-1.9),(1.9,1.9),(-1.9,1.9))))
    return n,[g,base[1],(-.9,0.,0.),known,known.copy(),g,known.copy()]


@pytest.mark.parametrize('width', [.68,.80])
@pytest.mark.parametrize('resolution', [.01,.02])
def test_straight_door_preserves_body_raster_tracking_and_goal_reserves(width,resolution):
    n,inputs=door_inputs(width,resolution)
    assert n._metric_waypoints_clear(inputs,((-.9,0.),(.9,0.)),0.)
    n._metric_path_validation='conservative'
    assert n._metric_waypoints_clear(inputs,((-.9,0.),(.9,0.)),0.) is None


@pytest.mark.parametrize('width', [.46,.50,.56])
def test_rollout_does_not_admit_too_small_passage(width):
    n,inputs=door_inputs(width)
    assert n._metric_waypoints_clear(inputs,((-.9,0.),(.9,0.)),0.) is None


def test_turn_in_narrow_passage_rejected_but_free_goal_region_beyond_passes():
    n,inputs=door_inputs();inputs[2]=(0.,0.,0.)
    assert not footprint_clear(0.,0.,math.pi/2,inputs[0],inputs[3],n._world_to_grid,n._grid_to_world)
    assert n._metric_waypoints_clear(inputs,((0.,0.),(.1,.1)),math.pi/2) is None
    inputs[2]=(-.9,0.,0.)
    assert n._metric_waypoints_clear(inputs,((-.9,0.),(.9,0.)),math.pi/2)


@pytest.mark.parametrize('source', [3,6])
def test_unknown_exterior_never_used_as_free_by_rollout_or_proposal(source):
    n,inputs=door_inputs();inputs[source][:,110:]=False
    if source==3:
        data=np.asarray(inputs[0].data).reshape(inputs[3].shape).copy();data[:,110:]=-1;inputs[0].data=data.ravel().tolist()
    assert n._metric_waypoints_clear(inputs,((-.9,0.),(.9,0.)),0.) is None
    assert n._metric_nav2_proposal(inputs,(.9,0.),0.) is None


def test_known_connected_proposal_is_not_claimed_as_footprint_proof():
    n,inputs=door_inputs(.50)
    assert n._metric_route(inputs,(.9,0.),0.) is None
    assert n._metric_nav2_proposal(inputs,(.9,0.),0.)
    # Motion still requires a real valid path. A straight rejected plan remains rejected.
    p=Path();p.header.frame_id='map'
    for x in (-.9,0.,.9):
        pose=PoseStamped();pose.pose.position.x=x;pose.pose.orientation.w=1.;p.poses.append(pose)
    c=MetricCandidate('t',.9,0.,0.,(.9,0.),(),1.,1.,'a'*64,1,True)
    assert n._metric_validate_nav_plan(inputs,p,c) is None


def test_valid_actual_detour_takes_precedence_over_unrelated_shortest_route():
    n,inputs=door_inputs()
    # Replace the door by an obstacle island. The point-mask shortest route
    # turns too close to it; the actual longer path has a wide south detour.
    g=inputs[0];rr,cc=np.indices(inputs[3].shape)
    x=-2+(cc+.5)*g.info.resolution;y=-2+(rr+.5)*g.info.resolution
    a=np.zeros(inputs[3].shape,np.int8);a[(abs(x)<.1)&(abs(y)<.5)]=100
    a[[0,-1],:]=100;a[:,[0,-1]]=100;g.data=a.ravel().tolist()
    inputs[3]=inputs[4]=inputs[6]=a==0
    c=MetricCandidate('t',.9,0.,0.,(.9,0.),(),4.,1.,'a'*64,1,True)
    assert n._metric_route(inputs,(.9,0.),0.) is None
    p=Path();p.header.frame_id='map'
    for px,py in ((-.9,0.),(-.9,-1.),(.9,-1.),(.9,0.)):
        pose=PoseStamped();pose.pose.position.x=px;pose.pose.position.y=py
        pose.pose.orientation.w=1.;p.poses.append(pose)
    n._metric_nav_path=p
    assert n._metric_navigation_geometry_ready(inputs,c)
    p.poses=[p.poses[0],p.poses[-1]]
    assert not n._metric_navigation_geometry_ready(inputs,c)


def test_selection_retains_reachable_target_for_real_nav2_instead_of_banning_shortest(monkeypatch):
    n,inputs=adaptive_fixture();n._metric_path_validation='rpp_rollout'
    # The only double is the rejected own prefilter; real frontier/approach,
    # goal-contour proof and policy still run against the actual input map.
    monkeypatch.setattr(n,'_metric_route',lambda *args:None)
    n._metric_last_route_rejection='footprint_sweep_invalid'
    policy=MetricTaskPolicy(.6,30.,2)
    candidates=n._metric_select(inputs,policy,.3)
    assert candidates and all(c.requires_nav2_plan for c in candidates)
    assert policy.attempts and not any(a.failures for a in policy.attempts.values())


def test_controller_rollout_prealigns_to_first_actual_leg_not_chord_through_obstacle():
    route=((0.,0.),(0.,1.),(1.,1.))
    poses=rpp_trajectory(route,(0.,0.,0.),.02,prealign_to_first_leg=True)
    # Initial stationary turn must point north, even though goal bearing is 45deg.
    first_translation=next(p for p in poses if math.hypot(p[0],p[1])>1e-6)
    assert abs(first_translation[2]-math.pi/2)<.01


def test_subcell_goal_join_does_not_invent_quarter_turn():
    route=((-1.,0.),(-.01,0.),(-.010002,-.00033))
    assert abs(motion.route_arrival_yaw(route,0.,.02))<.001
    assert motion.route_arrival_yaw(((0.,0.),(0.,1.)),0.,.02)==math.pi/2


def test_adaptive_start_reports_missing_exterior_without_repeated_scan():
    n,inputs=door_inputs();inputs[2]=(0.,0.,0.)
    decision,candidates=n._metric_start_decision(inputs,MetricTaskPolicy(.6,30.,2),.3,True)
    assert not decision['scan_admissible']
    assert decision['selected_motion']=='wait' and not candidates
    assert decision['first_rejecting_predicate']=='no_eligible_observation_route'


@pytest.mark.parametrize('enabled,tolerance', [(False,.02),(True,.17)])
def test_rollout_real_node_rejects_unqualified_prealignment(enabled,tolerance):
    import json
    import rclpy
    from test_metric_frontier import require_isolated_ros
    require_isolated_ros()
    values=dict(exploration_strategy='metric_frontier',metric_path_validation='rpp_rollout',
        prealign_enabled=enabled,prealign_handoff_tolerance_rad=tolerance,
        prealign_stop_margin_rad=.01,prealign_min_improvement_rad=.005,
        wohnungserkundung_accessible_scope_verified=True,wohnungserkundung_scope_id='scope-test',
        wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],
        metric_session_id='metric-test',metric_scope_map_fingerprint='a'*64,
        portal_crossing_enabled=False,coverage_enabled=False,overall_timeout_s=60.,
        region_graph_shadow_enabled=False,behavior_tree='/fake/no_recovery.xml')
    rclpy.init(args=['--ros-args',*[x for k,v in values.items() for x in ('-p',k+':='+json.dumps(v))]])
    try:
        with pytest.raises(ValueError,match='enabled prealignment within 0.02 rad'):ExploreNode()
    finally:rclpy.shutdown()


@pytest.mark.parametrize('name,value', [
    ('controller_frequency',10.),('FollowPath.desired_linear_vel',.2),
    ('FollowPath.rotate_to_heading_angular_vel',.4),('FollowPath.max_angular_accel',4.)])
def test_simulation_tracking_contract_rejects_different_actual_response_limits(name,value):
    """Parameter transport double with real typed values, not a Nav2 proof."""
    from pathlib import Path as FilePath
    from types import SimpleNamespace
    import yaml
    from rclpy.parameter import Parameter
    data=yaml.safe_load((FilePath(__file__).parents[2]/'robot_navigation/config/nav2_params_real.yaml').read_text())['controller_server']['ros__parameters']
    def response(request):
        values=[]
        for key in request.names:
            parts=key.split('.');current=data
            for part in parts:current=current[part]
            values.append(Parameter(key,value=current).get_parameter_value())
        return SimpleNamespace(done=lambda:True,result=lambda:SimpleNamespace(values=values))
    n=ExploreNode.__new__(ExploreNode);n._metric_path_validation='rpp_rollout';n._metric_status={}
    n._metric_controller_params=SimpleNamespace(wait_for_service=lambda **_:True,call_async=response)
    assert n._metric_controller_contract(lambda:False)
    if '.' in name:
        plugin,key=name.split('.');data[plugin][key]=value
    else:data[name]=value
    assert not n._metric_controller_contract(lambda:False)


@pytest.mark.parametrize('width',[.68,.8])
def test_rpp_stop_inside_connection_keeps_tracking_and_rejects_actual_final_turn(width):
    node,inputs=door_inputs(width)
    route=((-0.9,0.),(0.,0.))
    assert node._metric_waypoints_clear(inputs,route,0.) is not None
    assert node._metric_waypoints_clear(inputs,route,math.pi/2) is None
    node._metric_path_validation='conservative'
    assert node._metric_waypoints_clear(inputs,route,0.) is None


def test_reachable_rpp_stopping_pose_must_be_free_before_ideal_target():
    node,inputs=door_inputs()
    # Ideal endpoint is in a wide free room; the actual early stopping pose
    # remains in the narrow passage and cannot perform the requested turn.
    route=((-0.9,0.),(.45,0.))
    assert node._metric_waypoints_clear(inputs,route,0.) is not None
    assert node._metric_waypoints_clear(inputs,route,math.pi/2) is None
    assert node._metric_last_route_rejection == 'goal_stop_rotation_invalid'
