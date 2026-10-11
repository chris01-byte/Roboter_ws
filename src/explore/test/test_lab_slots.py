"""Real LAB parent/selection/geometry with replaced action motion transport.

These are software counterexamples, not physical rotation/door qualification.
"""
import copy
import math
from dataclasses import replace

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from test_metric_map_lifecycle import status
from test_metric_progress import parent_fixture


def lab(monkeypatch, scene='open'):
    node,grid,clock,parent,terminal=parent_fixture(monkeypatch,scene)
    node._metric_execution_mode='lab_slots'
    node._metric_unknown_space_policy='sensor_guarded'
    node._initial_scan_enabled=True
    node._initial_scan_angle=2*math.pi
    node._initial_scan_timeout=280.
    node._initial_scan_speed=.08
    node._metric_completion_window_s=3.
    node._metric_observation_wait_s=2.
    node._metric_slot_recovery_timeout_s=5.
    node._metric_status={}
    node._scan_in_place=lambda **kw:('success',kw.get('angle_rad',2*math.pi))
    node._metric_align_nav_departure=lambda *_args,**_kwargs:('skipped',0.,0.,0.)
    def query(target, stopped):
        assert not stopped()
        path=Path()
        path.header.frame_id='map'
        for x,y in target.route:
            pose=PoseStamped()
            pose.pose.position.x,pose.pose.position.y=x,y
            pose.pose.orientation.z=math.sin(target.yaw/2)
            pose.pose.orientation.w=math.cos(target.yaw/2)
            path.poses.append(pose)
        return path,None
    node._metric_request_nav_plan=query
    return node,grid,clock,parent,terminal


def test_lab_start_turn_precedes_map_join_and_every_raster_search(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    changed=copy.deepcopy(grid)
    changed.header.stamp.nanosec=30_000_000
    changed.data[-1]=100
    node._on_map(changed)  # actual newer raw map; manager has not caught up
    assert not node._metric_matches_status(node._metric_raw[1])
    calls=[]
    inputs=node._metric_inputs
    def read(*args,**kwargs):
        assert calls==['scan'], 'LAB turn must not wait for a raster join'
        return inputs(*args,**kwargs)
    node._metric_inputs=read
    node._metric_scan_geometry_ready=lambda *_:pytest.fail('LAB turn cannot require map free cells')
    def turn(*,stop_requested,angle_rad=None):
        assert not stop_requested()
        calls.append('scan')
        node._on_metric_map_status(status(changed,accepted=3,observed=3,when=100.04))
        parent.is_cancel_requested=True
        return 'success',angle_rad or 2*math.pi
    node._scan_in_place=turn
    node._execute_metric_frontier(parent,10.,.3)
    assert calls==['scan'] and terminal==['cancel']
    assert node._metric_status['scan_progress_rad']==pytest.approx(2*math.pi)


def test_drive_guard_keeps_goal_during_join_and_does_no_raster_processing(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    inputs=node._metric_inputs
    reads=[]
    driving=[False]
    def read(*args,**kwargs):
        reads.append('drive' if driving[0] else 'standstill')
        return inputs(*args,**kwargs)
    node._metric_inputs=read
    def drive(*_args,stop_requested,**_kwargs):
        driving[0]=True
        before=len(reads)
        changed=copy.deepcopy(grid)
        changed.header.stamp.nanosec=30_000_000
        changed.data[-1]=100
        clock[0]=10.04
        node._on_map(changed)
        assert not node._metric_matches_status(node._metric_raw[1])
        for _ in range(30):
            assert not stop_requested(), 'ordinary map join cannot cancel live drive'
        assert len(reads)==before
        parent.is_cancel_requested=True
        return 'canceled'
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['cancel'], (node._metric_status['terminal_reason'],node._metric_status['chain'])


def test_normal_failed_leg_selects_an_alternative_beyond_old_global_failure_limit(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    node._max_failed_goals=1
    node._max_frontier_goals=3
    driven=[]
    def drive(x,y,*_args,stop_requested,**_kwargs):
        assert not stop_requested()
        driven.append((x,y))
        if len(driven)==2:
            parent.is_cancel_requested=True
        return 'aborted'
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert len(driven)==2 and math.dist(*driven)>.1, (node._metric_status['terminal_reason'],node._metric_status['chain'])
    assert terminal==['cancel']
    assert node._metric_status['failures']==1
    assert node._metric_status['chain'][0]['terminal_child']


def test_short_sensor_gap_revalidates_then_attempts_lab_turn(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    calls=[]
    node._metric_operating_snapshot=lambda **_:dict(safe=clock[0]>=10.5,
        first_rejecting_predicate=None if clock[0]>=10.5 else 'vl53_cloud_missing_stale_or_invalid')
    def turn(*,stop_requested,angle_rad=None):
        assert not stop_requested()
        calls.append('scan')
        parent.is_cancel_requested=True
        return 'success',angle_rad
    node._scan_in_place=turn
    node._execute_metric_frontier(parent,10.,.3)
    assert calls==['scan'] and terminal==['cancel']
    assert node._metric_status['recoveries']==1 and clock[0]>=10.5


def test_changing_source_error_names_does_not_renew_recovery_window(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    reasons=('vl53_cloud_missing_stale_or_invalid','lidar_missing_stale_or_invalid')
    node._metric_operating_snapshot=lambda **_:dict(safe=False,
        first_rejecting_predicate=reasons[int(clock[0]*20)%2])
    node._scan_in_place=lambda **_:pytest.fail('Source outage cannot rotate')
    node._execute_metric_frontier(parent,20.,.3)
    assert terminal==['abort'] and node._metric_status['outcome']=='blocked_help_required'
    assert clock[0]<16. and node._metric_status['recoveries']==1


@pytest.mark.parametrize('fault',['estop_missing_stale_or_active','encoder_latched','hwt601_terminal_fault',
                                 'unexpected_contract_failure'])
def test_real_faults_never_reset_or_move(monkeypatch,fault):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    snapshot=dict(safe=False,first_rejecting_predicate=fault)
    if fault=='encoder_latched':
        snapshot.update(first_rejecting_predicate='actuator_or_encoder_state_invalid',
                        encoder_state=dict(encoder_config_fault_latched=True))
    node._metric_operating_snapshot=lambda **_:snapshot
    node._scan_in_place=lambda **_:pytest.fail('Fault cannot rotate')
    node._metric_select=lambda *_:pytest.fail('Fault cannot start planning')
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and node._metric_status['outcome']=='error'
    assert node._metric_status['recoveries']==0


def test_cached_scope_path_never_caches_sensor_health_or_epoch(monkeypatch):
    from explore.lab_slots_runtime import live_guard
    node,grid,clock,parent,terminal=lab(monkeypatch)
    context=node._metric_work_context()
    assert live_guard(node,context=context) is None
    actual=node._door_lidar_scan_snapshot()
    actual['received_at']-=1.
    node._door_lidar_scan_snapshot=lambda:actual
    assert live_guard(node,context=context)=='candidate_lidar_missing_stale_or_tf_missing'
    node._metric_correlation=replace(node._metric_correlation,
        context=replace(node._metric_correlation.context,session_id='other-session'))
    assert live_guard(node,context=context)=='map_work_context_changed'


def test_missing_frontier_does_not_claim_completion_or_loop_observation_turn(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    calls=[]
    node._metric_select=lambda *_:[]
    node._frontier_rank_stats={}
    node._scan_in_place=lambda **kw:(calls.append(kw['angle_rad']) or ('success',kw['angle_rad']))
    result=node._execute_metric_frontier(parent,4.,.3)
    assert not result.success and node._metric_status['outcome']=='usable_partial'
    assert calls==[math.pi/4]
    assert node._metric_status['observations']==0


def test_customer_fallback_keeps_original_explicit_mode(monkeypatch):
    node,grid,clock,parent,terminal=parent_fixture(monkeypatch,'known')
    node._metric_execution_mode='continuous'
    result=node._execute_metric_frontier(parent,10.,.3)
    assert result.success and terminal==['success']


def test_failed_approach_allows_distinct_pose_without_erasing_history():
    from explore.lab_slots_runtime import LabTaskPolicy
    from explore.metric_frontier import MetricTaskPolicy
    from test_metric_frontier import candidate
    original=MetricTaskPolicy(.6,30.,2)
    actual=LabTaskPolicy(.6,30.,2)
    for policy in (original,actual):
        key=policy.identify((1.5,0.))
        policy.record(candidate(key),'task_unreached_cause_unproven',10.,'a'*64,evidence_key='b'*64)
    key='metric-task-1'
    assert not original.eligible(key,(1.4,0.),10.1,'a'*64,'b'*64)
    assert actual.eligible(key,(1.4,0.),10.1,'a'*64,'b'*64)
    assert not actual.eligible(key,(1.33,0.),10.1,'a'*64,'b'*64)
    assert not actual.eligible(key,(1.,0.),50.,'a'*64,'b'*64)
    actual.record(replace(candidate(key),x=1.4),'task_unreached_cause_unproven',10.1,'a'*64,evidence_key='b'*64)
    assert actual.attempts[key].tries==2 and actual.attempts[key].failures==2
    assert not actual.eligible(key,(1.8,0.),100.,'c'*64,'d'*64)


@pytest.mark.parametrize('interrupt',['source_gap','hwt_hold'])
def test_interrupted_child_resumes_same_job_with_original_deadline_and_counts(monkeypatch,interrupt):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    node._max_frontier_goals=1
    drives=[]
    waits=[]
    until=[0.]
    held=[False]
    node._wohnungserkundung_hwt_hold=lambda:held[0]
    node._metric_operating_snapshot=lambda **_:dict(safe=clock[0]>=until[0],
        first_rejecting_predicate=None if clock[0]>=until[0] else 'vl53_cloud_missing_stale_or_invalid')
    def resume(_parent,_expired,*,require_target):
        assert require_target and node._metric_active is not None
        waits.append(node._metric_active.task_id)
        clock[0]+=.4
        held[0]=node._hwt_hold_announced=False
        return 'resumed'
    node._wohnungserkundung_wait_for_hwt_resume=resume
    def drive(x,y,timeout,*,stop_requested,**_kwargs):
        assert node._wohnungserkundung_active_child is not None
        assert not stop_requested()
        drives.append((x,y,timeout,node._metric_active.task_id))
        if len(drives)==1:
            clock[0]+=.1
            if interrupt=='source_gap':
                until[0]=clock[0]+.4
            else:
                held[0]=node._hwt_hold_announced=True
            assert stop_requested()
        else:
            assert drives[0][:2]==drives[1][:2] and drives[0][3]==drives[1][3]
            assert drives[1][2]<=drives[0][2]-.4
            parent.is_cancel_requested=True
        return 'canceled'
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert len(drives)==2 and terminal==['cancel'], node._metric_status
    assert node._metric_status['attempts']==1 and node._metric_status['failures']==0
    saved=node._metric_checkpoint['policy']['tasks'][drives[0][3]]
    assert saved['tries']==1 and saved['failures']==0
    assert bool(waits) is (interrupt=='hwt_hold')


@pytest.mark.parametrize('fault',['wrong_direction','stop_unconfirmed','nav2_controller_geometry_contract_invalid'])
def test_alignment_faults_preserve_actual_cause_and_cannot_dispatch(monkeypatch,fault):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    node._metric_align_nav_departure=lambda *_args,**_kwargs:(fault,0.,0.,0.)
    node._navigate_to=lambda *_args,**_kwargs:pytest.fail('Unqualified alignment cannot drive')
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and node._metric_status['terminal_reason']==fault


def test_lab_known_scope_completion_still_requires_distinct_fresh_scan_window(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch,'known')
    node._initial_scan_enabled=False
    started=clock[0]
    result=node._execute_metric_frontier(parent,10.,.3)
    assert result.success and terminal==['success'] and clock[0]-started>=3.
    assert not node._metric_status['semantic_complete'] and not node._metric_status['floor_coverage_verified']


def test_source_interruption_does_not_erase_dispatched_work_or_original_cause(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    until=[0.]
    queries=[]
    planner=node._metric_request_nav_plan
    select=node._metric_select
    selections=[]
    def choose(*args):
        selections.append(True)
        if len(selections)>1:
            parent.is_cancel_requested=True
        return select(*args)
    node._metric_select=choose
    node._metric_operating_snapshot=lambda **_:dict(safe=clock[0]>=until[0],
        first_rejecting_predicate=None if clock[0]>=until[0] else 'vl53_cloud_missing_stale_or_invalid')
    def query(*args):
        queries.append(True)
        return planner(*args) if len(queries)==1 else (None,'nav2_plan_aborted')
    node._metric_request_nav_plan=query
    def drive(*_args,stop_requested,**_kwargs):
        until[0]=clock[0]+.2
        assert stop_requested()
        return 'canceled'
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert len(queries)==2 and terminal==['cancel']
    last=node._metric_status['chain'][-1]
    assert last['decision']=='task_unreached_cause_unproven' and last['task_motion_dispatched']
    assert not last['child_dispatched'] and node._metric_status['failures']==1
    assert last['original_trigger']=='vl53_cloud_missing_stale_or_invalid'


def test_unconfirmed_child_cannot_be_reset_even_when_user_cancel_arrives(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    def drive(*_args,**_kwargs):
        node._nav_child_uncertain=True
        parent.is_cancel_requested=True
        return 'aborted'
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and node._metric_status['terminal_reason']=='child_state_uncertain'
    assert node._nav_child_uncertain


@pytest.mark.parametrize('invalid',['frame','goal_yaw','goal_values'])
def test_invalid_native_plan_contract_cannot_be_softened_into_motion(monkeypatch,invalid):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    query=node._metric_request_nav_plan
    def plan(*args):
        path,error=query(*args)
        if invalid=='frame':
            path.header.frame_id='odom'
        elif invalid=='goal_yaw':
            yaw=args[0].yaw+.2
            path.poses[-1].pose.orientation.z=math.sin(yaw/2)
            path.poses[-1].pose.orientation.w=math.cos(yaw/2)
        else:
            path.poses[-1].pose.position.x=float('nan')
        return path,error
    node._metric_request_nav_plan=plan
    node._navigate_to=lambda *_args,**_kwargs:pytest.fail('Invalid native plan cannot drive')
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and node._metric_status['outcome']=='error'
    assert node._metric_status['terminal_reason'].startswith('nav2_plan_')


def test_lab_turn_checks_actual_body_without_a_future_full_circle_permission(monkeypatch):
    from explore.lab_slots_runtime import live_guard
    from explore.portal_memory import Point2D
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._metric_scope=replace(node._metric_scope,
        vertices=tuple(Point2D(x,y) for x,y in ((-.3,-.3),(.45,-.3),(.45,.4),(-.3,.4))))
    # Current padded body fits. An enclosing future 360-degree square does not.
    assert live_guard(node,rotation=True) is None
    node._robot_pose_sample=lambda:((.4,.05,0.),0.)
    assert live_guard(node,rotation=True)=='lab_body_outside_scope'


@pytest.mark.parametrize('change,reason',[
    ({'metric_unknown_space_policy':'observed_only'},'lab_slots requires sensor_guarded'),
    ({'initial_scan_enabled':False},'enabled full 360'),
    ({'initial_scan_angle_rad':math.pi},'enabled full 360'),
    ({'metric_slot_recovery_timeout_s':61.},'bounded 0..60'),
])
def test_actual_ros_node_rejects_inconsistent_lab_start_configuration(change,reason):
    import json
    import rclpy
    from explore.explore_node import ExploreNode
    from test_metric_frontier import require_isolated_ros
    require_isolated_ros()
    values=dict(exploration_strategy='metric_frontier',metric_execution_mode='lab_slots',
        metric_unknown_space_policy='sensor_guarded',metric_self_body_enabled=False,
        metric_start_egress_enabled=False,wohnungserkundung_accessible_scope_verified=True,
        wohnungserkundung_scope_id='scope-test',metric_session_id='metric-test',
        metric_scope_map_fingerprint='a'*64,wohnungserkundung_scope_polygon_xy=[-1.,-1.,3.,-1.,3.,3.,-1.,3.],
        portal_crossing_enabled=False,coverage_enabled=False,overall_timeout_s=60.,
        region_graph_shadow_enabled=False,behavior_tree='/fake/no_recovery.xml')
    values.update(change)
    rclpy.init(args=['--ros-args',*[arg for key,value in values.items()
                                 for arg in ('-p',key+':='+json.dumps(value))]])
    try:
        with pytest.raises(ValueError,match=reason):ExploreNode()
    finally:
        rclpy.shutdown()


def test_identical_costmap_publications_do_not_repeat_frontier_work(monkeypatch):
    import explore.lab_slots_runtime as module
    node,grid,clock,parent,terminal=lab(monkeypatch,'tiny')
    node._initial_scan_enabled=False
    select=node._metric_select
    calls=[]
    def choose(*args):
        calls.append(clock[0])
        return select(*args)
    node._metric_select=choose
    sleep=module.time.sleep
    def publish(delay):
        sleep(delay)
        node._global_costmap=copy.deepcopy(node._global_costmap)
        node._global_costmap_received_at=clock[0]
    monkeypatch.setattr(module.time,'sleep',publish)
    node._execute_metric_frontier(parent,2.,1.)
    assert len(calls)==1 and node._metric_status['terminal_reason']=='budget_exhausted'


def test_separate_short_source_gaps_each_get_a_fresh_bounded_validation_window(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch,'tiny')
    node._initial_scan_enabled=False
    node._metric_slot_recovery_timeout_s=.4
    def snapshot(**_kwargs):
        gap=(10.7<=clock[0]<11.) or (11.8<=clock[0]<12.1)
        return dict(safe=not gap,first_rejecting_predicate='vl53_cloud_missing_stale_or_invalid' if gap else None)
    node._metric_operating_snapshot=snapshot
    node._execute_metric_frontier(parent,3.,1.)
    assert node._metric_status['terminal_reason']=='budget_exhausted'
    assert node._metric_status['recoveries']==3  # one view, two separate data gaps


def test_exception_after_child_dispatch_is_terminal_and_preserves_cause(monkeypatch):
    node,grid,clock,parent,terminal=lab(monkeypatch)
    node._initial_scan_enabled=False
    def drive(*_args,**_kwargs):
        node._nav_child_uncertain=True
        raise RuntimeError('peer_result_transport_lost')
    node._navigate_to=drive
    node._execute_metric_frontier(parent,10.,.3)
    assert terminal==['abort'] and node._metric_status['terminal_reason']=='child_error'
    assert node._metric_status['first_trigger']['reason']=='peer_result_transport_lost'
    assert node._nav_child_uncertain
