"""LAB observation/plan/drive slots inside the existing ExploreArea owner.

No new ROS node, action client or velocity publisher. Motion uses the existing
measured scan driver and NavigateToPose/cancel/confirmed-stop chain. Planning
rasters are used at standstill; live sensor, epoch, pose and scope checks never
reuse a cached movement authorization. Recovery discards plans, never faults.
"""
import math
import time
import hashlib

import rclpy
from shapely.geometry import Polygon
from robot_interfaces.action import ExploreArea

from .metric_checkpoint import restore_policy
from .metric_frontier import MetricTaskPolicy, rpp_trajectory
from .metric_progress import (CompletionWindow, local_evidence, local_small_remainder, measured_gain,
                              observation_complete, reachable_remainder)


WAIT_REASONS = frozenset((
    'map_scope_not_joined', 'map_status_join_pending', 'raw_map_stamp_stale',
    'map_manager_status_stale', 'costmap_missing_or_stale', 'costmap_stamp_stale',
    'pose_missing_stale_or_invalid', 'pose_stale_after_processing',
    'self_body_scan_stale_after_processing', 'localization_missing_or_stale',
    'lidar_missing_stale_or_invalid', 'vl53_status_missing_stale_or_invalid',
    'vl53_cloud_missing_stale_or_invalid', 'vl53_triplet_unmatched',
    'candidate_lidar_missing_stale_or_tf_missing', 'candidate_lidar_stamp_stale',
    'candidate_lidar_no_valid_rays', 'stable_standstill_not_confirmed',
    'actuator_or_encoder_state_invalid', 'lab_scope_not_bound',
    'resume_localization_unconfirmed', 'nav2_planner_unavailable',
    'nav2_controller_parameters_unavailable', 'nav2_controller_parameters_timeout',
    'map_pose_missing',
    'frontier_candidate_processing_budget_exhausted',
    'start_motion_wheel_missing_stale_or_invalid',
    'start_motion_wheel_stale_after_processing', 'start_motion_wheel_tf_disagreement',
))
REPLAN_REASONS = frozenset((
    'route_invalidated', 'task_budget_exhausted', 'nav2_plan_aborted',
    'nav2_plan_timeout_or_stop', 'nav2_plan_rejected', 'nav2_plan_failed',
    'planning_failed', 'alignment_failed', 'timeout', 'aborted',
    'interrupted', 'no_progress', 'too_slow', 'odom_stale', 'accessible_work_blocked',
    'footprint_sweep_invalid', 'goal_orientation_invalid', 'goal_stop_rotation_invalid',
    'start_egress_in_place_turn', 'controller_lookahead_sweep_invalid', 'no_known_free_route',
    'nav2_plan_pose_disconnected', 'nav2_plan_controller_carrot_unbounded',
    'public_alignment_geometry_invalid', 'map_no_improvement', 'map_alignment_failed',
    'lab_route_outside_scope', 'lab_turn_outside_scope',
))


class LabTaskPolicy(MetricTaskPolicy):
    """Keep history/caps; a failed approach does not blacklist every approach.

    Two 15-cm arrival disks plus two 2-cm tracking margins must be disjoint.
    Completed/partial observations retain the original neighbourhood rules.
    """
    def _limit_neighbours(self, task_id, target_xy):
        ordinary=('task_unreached_cause_unproven','route_invalidated','proposal_rejected',
                  'arrival_without_observation')
        return [a for a in super()._limit_neighbours(task_id,target_xy)
            if not (not a.completed and not a.partial_observation and a.reason in ordinary
                    and a.tries<self.retry_limit+1 and a.failures<self.retry_limit
                    and math.dist(a.target_xy,target_xy)>.34+1e-12)]


def recovery_kind(reason, snapshot=None):
    """An explicit allowlist: unknown/contract/latched faults stay terminal."""
    if reason == 'actuator_or_encoder_state_invalid':
        wheel = (snapshot or {}).get('encoder_state') or {}
        if wheel.get('encoder_config_fault_latched') is True:
            return 'fatal'
    if reason in WAIT_REASONS or reason.startswith('odometry_missing_stale_or_invalid '):
        return 'wait'
    return 'replan' if reason in REPLAN_REASONS else 'fatal'


def _scope_shape(node):
    scope = node._metric_scope
    if scope is None:
        raise ValueError('lab_scope_not_bound')
    key = scope.fingerprint
    cached = getattr(node, '_lab_scope_shape', None)
    if cached is None or cached[0] != key:
        cached = node._lab_scope_shape = (key, Polygon([(p.x, p.y) for p in scope.vertices]))
    return cached[1]


def _body_polygon(pose, bounds, margin=.02):
    x, y, yaw = pose
    xmin, xmax, ymin, ymax = bounds
    co, si = math.cos(yaw), math.sin(yaw)
    return Polygon([(x+co*a-si*b, y+si*a+co*b)
        for a, b in ((xmin-margin, ymin-margin), (xmax+margin, ymin-margin),
                     (xmax+margin, ymax+margin), (xmin-margin, ymax+margin))])


def live_guard(node, *, context=None, rotation=False):
    """Small current-source guard, independent of raster joins/frontier search.

    Nav2's live costmaps/controller and the independent LiDAR/VL53 monitor own
    obstacle response. Changed native paths are checked against the LAB boundary
    once per actual path object; this cache contains geometry, not health.
    """
    snapshot = node._metric_operating_snapshot()
    node._metric_status['decision_snapshot'] = snapshot
    if not snapshot['safe'] and snapshot['first_rejecting_predicate']!='vl53_triplet_unmatched':
        return snapshot['first_rejecting_predicate']
    # The three VL53 messages are published separately. Their short delivery
    # window remains zero-gated by the actual mission gate, without canceling
    # the child on every normal publication. Source validity/ages still apply.
    if getattr(node,'_metric_fault',None):
        return node._metric_fault
    correlation=getattr(node,'_metric_correlation',None)
    if node._metric_scope is not None and correlation is not None and correlation.context!=node._metric_scope.context:
        return 'map_work_context_changed'
    if context is not None and not node._metric_work_is_current(context):
        return 'map_work_context_changed'
    try:
        node._metric_sensor_scan()
        pose, age = node._robot_pose_sample()
        if (pose is None or age is None or not 0 <= age <= node._door_pose_timeout
                or not all(math.isfinite(v) for v in pose)):
            return 'pose_missing_stale_or_invalid'
        shape = _scope_shape(node)
        if not shape.covers(_body_polygon(pose, node._metric_bounds)):
            return 'lab_body_outside_scope'
        if not rotation and context is not None:
            raw=node._metric_raw
            costmap=node._global_costmap
            now=time.monotonic()
            stamp_now=node.get_clock().now().nanoseconds
            if raw is None or not 0<=now-raw[2]<=node._map_timeout_s or not 0<=(stamp_now-raw[1].source_stamp_ns)/1e9<=node._map_timeout_s:
                return 'raw_map_stamp_stale'
            if costmap is None or not 0<=now-node._global_costmap_received_at<=node._map_timeout_s:
                return 'costmap_missing_or_stale'
            cost_stamp=costmap.header.stamp.sec*10**9+costmap.header.stamp.nanosec
            if not 0<=(stamp_now-cost_stamp)/1e9<=node._map_timeout_s:
                return 'costmap_stamp_stale'
        # LAB turning permission is not a speculative full-circle map/scope
        # clearance test. The padded ACTUAL body boundary above is still
        # checked on every current pose; the live collision gate can stop it.
        path = getattr(node, '_metric_nav_path', None)
        if not rotation and path is not None:
            cached = getattr(node, '_lab_scoped_path', None)
            if cached is None or cached[0] is not path or cached[1] != node._metric_scope.fingerprint:
                if not path.poses or path.header.frame_id != node._global_frame:
                    return 'nav2_plan_missing_or_wrong_frame'
                points = [(p.pose.position.x, p.pose.position.y) for p in path.poses]
                if not all(math.isfinite(v) for p in points for v in p):
                    return 'nav2_plan_goal_or_values_invalid'
                # Current changed native route: only its controller/body sweep
                # against the authorized polygon. An enclosing robot circle
                # would wrongly reject a valid oriented passage near a border.
                poses=rpp_trajectory(points,pose,
                    min(node._metric_raw[0].info.resolution,node._global_costmap.info.resolution),
                    getattr(node,'_prealign_handoff_tolerance',.17),node._metric_bounds,
                    prealign_to_first_leg=True)
                if not all(shape.covers(_body_polygon((x,y,yaw+delta),node._metric_bounds,.03))
                           for x,y,yaw in poses for delta in (-.05,0.,.05)):
                    return 'lab_route_outside_scope'
                node._lab_scoped_path = (path, node._metric_scope.fingerprint)
    except Exception as error:
        return str(error)
    return None


def execute_lab_slots(node, goal_handle, overall_timeout, min_frontier):
    """Run one LAB mission; only a terminal child may enter the next slot."""
    result = ExploreArea.Result()
    overall_timeout = min(overall_timeout, node._overall_timeout_s)
    started = time.monotonic()
    attempts = failures = arrivals = observations = 0
    area = 0.
    last_inputs = None
    chain = []
    completion = CompletionWindow(node._metric_completion_window_s)
    scan_progress = 0.
    scan_done = not node._initial_scan_enabled
    scan_started = None
    mission_context = node._metric_work_context()
    view_keys = set()
    source_wait_at = None
    resume_target = None
    idle_key = None
    idle_until = 0.
    policy = LabTaskPolicy(node._frontier_revisit_radius, node._metric_retry_s, node._metric_retry_limit)
    resume_checked = not getattr(node, '_metric_resume_saved', False)
    node._metric_resume_validated = False
    node._coverage_complete = False
    node._coverage_ratio = 0.
    node._frontiers_visited_status = 0
    node._blacklist.clear()
    node._visited_frontier_goals.clear()
    node._metric_active = node._metric_active_context = None
    node._metric_status = dict(schema_version=1,state='running',outcome='in_progress',
        execution_mode='lab_slots',unknown_space_policy='sensor_guarded',
        started_wall_time=time.time(),arrivals=0,observations=0,observed_area_m2=0.,
        full_apartment_complete=False,semantic_complete=False,floor_coverage_verified=False,
        chain=chain,first_trigger=None,reactions=[],terminal_reason=None,
        slot=dict(index=0,phase='observe'),recoveries=0,scan_progress_rad=0.)
    node._status_state = 'running'

    def expired():
        return time.monotonic()-started >= overall_timeout

    def phase(name):
        previous = node._metric_status['slot']
        node._metric_status['slot'] = dict(index=previous['index']+(previous['phase']!=name),
            phase=name,entered_at=time.monotonic())
        node._status_phase = dict(observe='metric_observation',plan='metric_planning',
            drive='metric_navigation',scan='we_initial_scan',recover='metric_waiting_sources')[name]

    def checkpoint(outcome='in_progress'):
        if last_inputs is not None:
            node._metric_update_checkpoint(last_inputs,policy,
                remaining=overall_timeout-(time.monotonic()-started),attempts=attempts,
                failures=failures,arrivals=arrivals,observations=observations,
                observed_area=area,outcome=outcome)

    def forget_plan():
        node._metric_active = node._metric_active_context = None
        node._metric_nav_path = node._metric_plan_after_ns = None
        node._lab_scoped_path = None
        node._metric_status['active_goal'] = None

    def record_child(entry):
        chain.append(entry)
        del chain[:-40]

    def finish(state, reason):
        if goal_handle.is_cancel_requested and not getattr(node,'_nav_child_uncertain',False):
            state,reason='canceled','user_canceled'
        outcome=dict(success='metric_complete',partial='usable_partial',blocked='blocked_help_required',
                     failed='error',canceled='user_canceled')[state]
        checkpoint(outcome)
        node._metric_status.update(state=state,outcome=outcome,reason=reason,terminal_reason=reason,
            attempts=attempts,failures=failures,arrivals=arrivals,observations=observations,
            observed_area_m2=area,chain=chain[-40:])
        node._metric_record_transition('terminal',reason,state=state)
        node._status_state = 'partial' if state=='blocked' else state
        node._status_phase=state
        node._status_message=reason
        result.success=state=='success'
        result.message=f'metric_frontier:{state}:{reason}'
        getattr(goal_handle,dict(success='succeed',canceled='canceled').get(state,'abort'))()
        forget_plan()
        return node._finish_result(result,node._frontiers_visited_status)

    def wait_source(reason):
        nonlocal source_wait_at
        phase('recover')
        node._metric_status.update(state='waiting',recovery_reason=reason)
        node._status_message=reason
        if source_wait_at is None:
            source_wait_at=time.monotonic()
            node._metric_record_transition('slot_revalidation',reason)
            node._metric_status['recoveries']+=1
        # One continuous outage has one absolute window; a changed error name
        # or every arriving sample cannot renew it. No command is sent here.
        if time.monotonic()-source_wait_at >= node._metric_slot_recovery_timeout_s:
            return False
        time.sleep(.05)
        return True

    def stop_cause(*, context=None, deadline=None, rotation=False):
        if goal_handle.is_cancel_requested:
            return 'user_canceled'
        if expired():
            return 'budget_exhausted'
        if node._wohnungserkundung_hwt_hold():
            return 'hwt_hold'
        if deadline is not None and time.monotonic()>=deadline:
            return 'task_budget_exhausted'
        return live_guard(node,context=context,rotation=rotation)

    def observation_key():
        # A repeated costmap PUBLICATION is not new geometry. A buffer digest
        # is cheap; no raster masks, frontier search or route proof run here.
        raw=node._metric_raw
        correlation=node._metric_correlation
        pose,_=node._robot_pose_sample()
        costmap=node._global_costmap
        cost_key=None
        if costmap is not None:
            origin=costmap.info.origin
            cost_key=(costmap.header.frame_id,costmap.info.width,costmap.info.height,
                costmap.info.resolution,origin.position.x,origin.position.y,origin.position.z,
                origin.orientation.x,origin.orientation.y,origin.orientation.z,origin.orientation.w,
                hashlib.blake2b(costmap.data,digest_size=16).digest())
        return (None if raw is None else raw[1].fingerprint,
            None if correlation is None else correlation.context,cost_key,
            None if pose is None else tuple(round(v,2) for v in pose))

    while rclpy.ok():
        if goal_handle.is_cancel_requested:
            return finish('canceled','user_canceled')
        if expired() or (attempts>=node._max_frontier_goals and resume_target is None):
            return finish('partial','budget_exhausted')
        if node._wohnungserkundung_hwt_hold():
            node._metric_record_transition('slot_hwt_hold','hwt_hold')
            resumed=node._wohnungserkundung_wait_for_hwt_resume(goal_handle,expired,require_target=resume_target is not None)
            if resumed!='resumed':
                return finish('canceled' if resumed=='user_canceled' else 'failed',f'hwt_{resumed}')
            if resume_target is None:
                forget_plan()
            else:
                node._metric_nav_path=node._metric_plan_after_ns=None
            continue
        reason=live_guard(node,context=mission_context,rotation=not scan_done)
        if reason:
            kind=recovery_kind(reason,node._metric_status.get('decision_snapshot'))
            if kind=='fatal':
                return finish('failed',reason)
            if kind=='replan':
                node._metric_record_transition('slot_maneuver_rejected',reason)
                if resume_target is not None:
                    policy.record(resume_target[0],'route_invalidated',time.monotonic(),
                                  resume_target[0].fingerprint,count_try=False)
                    failures+=1
                    resume_target=None
                scan_done=True
                forget_plan()
                continue
            if not wait_source(reason):
                return finish('blocked','source_revalidation_timeout:'+reason)
            continue
        if (source_wait_at is None and idle_key is not None
                and time.monotonic()<idle_until and observation_key()==idle_key):
            phase('observe')
            node._metric_status['state']='waiting'
            time.sleep(.05)
            continue
        idle_key=None
        if not node._metric_confirm_stop(goal_handle,expired):
            if node._wohnungserkundung_hwt_hold():
                continue
            snapshot=node._metric_operating_snapshot(require_stop=True)
            reason=snapshot['first_rejecting_predicate'] or 'stable_standstill_not_confirmed'
            if recovery_kind(reason,snapshot)=='fatal':
                return finish('failed',reason)
            if not wait_source(reason):
                return finish('blocked','standstill_revalidation_timeout')
            continue

        # Cold LAB start is independent of every map raster/join/free-cell test.
        # Saved missions must first restore their original counts and budgets.
        if not scan_done and resume_checked:
            phase('scan')
            node._metric_status['state']='running'
            if scan_started is None:
                scan_started=time.monotonic()
                attempts+=1
            scan_context=node._metric_work_context()
            first=[None]
            def scan_stop():
                reason=stop_cause(context=scan_context,deadline=scan_started+node._initial_scan_timeout,rotation=True)
                if reason and first[0] is None:
                    first[0]=reason
                return reason is not None
            remaining_angle=node._initial_scan_angle-scan_progress
            if remaining_angle>1e-9:
                status, achieved=node._scan_in_place(stop_requested=scan_stop,angle_rad=remaining_angle)
            else:
                status, achieved='success',0.  # previous actual angle + newly confirmed stop
            scan_progress+=achieved
            node._metric_status.update(scan_progress_rad=scan_progress,
                scan_attempt=dict(started_at=scan_started,elapsed_s=time.monotonic()-scan_started,
                    target_angle_rad=node._initial_scan_angle,achieved_angle_rad=scan_progress,
                    commanded_rate_radps=node._initial_scan_speed,result=status))
            if goal_handle.is_cancel_requested:
                return finish('canceled','user_canceled')
            if expired():
                return finish('partial','budget_exhausted')
            if node._hwt_hold_announced or first[0]=='hwt_hold':
                node._metric_record_transition('scan_interrupted',first[0] or 'hwt_hold',
                    scan_result=status,achieved_angle_rad=scan_progress)
                continue
            reason=first[0] or status
            if status!='success':
                node._metric_record_transition('scan_interrupted',reason)
                if recovery_kind(reason,node._metric_status.get('decision_snapshot'))=='fatal':
                    return finish('failed',reason)
                if recovery_kind(reason)=='wait' and time.monotonic()<scan_started+node._initial_scan_timeout:
                    if not wait_source(reason):
                        return finish('blocked','scan_source_revalidation_timeout')
                    continue
                # A real obstacle/limited turn is an observation attempt, not
                # a whole-mission failure. Resume exploration from actual pose.
                node._metric_status['deferred_initial_scan']=dict(completed=False,result=status,reason=reason)
            else:
                node._metric_status['initial_scan_complete']=True
            scan_done=True
            source_wait_at=None
            continue

        phase('observe')
        try:
            inputs=node._metric_inputs()
        except Exception as error:
            reason=str(error)
            if recovery_kind(reason)=='fatal':
                return finish('failed',reason)
            if not wait_source(reason):
                return finish('blocked','planning_sources_unavailable:'+reason)
            continue
        last_inputs=inputs
        if mission_context is None:
            mission_context=node._metric_work_context()
        if not resume_checked:
            saved=getattr(node,'_metric_restored',None)
            expected=dict(scope_id=node._metric_scope.scope_id,
                vertices=[[v.x,v.y] for v in node._metric_scope.vertices])
            if (saved is None or saved['fingerprint']!=inputs[1].fingerprint or saved['scope']!=expected
                    or saved['context']['session_id']!=inputs[1].context.session_id
                    or saved['context']['frame_id']!=inputs[1].context.frame_id
                    or saved['context']['map_id']!=node._metric_resume_origin_map_id
                    or saved['policy']['radius']!=policy.radius
                    or saved['policy']['cooldown_s']!=policy.cooldown_s
                    or saved['policy']['retry_limit']!=policy.retry_limit):
                return finish('failed','metric_resume_binding_mismatch')
            try:
                policy,remaining=restore_policy(saved,time.monotonic(),time.time())
            except ValueError as error:
                return finish('failed',str(error))
            overall_timeout=min(overall_timeout,remaining)
            policy=LabTaskPolicy(policy.radius,policy.cooldown_s,policy.retry_limit,policy.attempts,policy.next_id)
            started=time.monotonic()
            attempts,failures=saved['attempts'],saved['failures']
            arrivals,observations=saved['arrivals'],saved['observations']
            area=saved['observed_area_m2']
            node._max_frontier_goals=min(node._max_frontier_goals,saved['budget_limits']['max_frontier_goals'])
            node._goal_timeout_s=min(node._goal_timeout_s,saved['budget_limits']['goal_timeout_s'])
            completion.duration_s=max(completion.duration_s,saved['budget_limits']['completion_window_s'])
            node._metric_resume_validated=True
            resume_checked=True
            for old in policy.attempts.values():
                if old.reason=='pending':
                    old.reason='interrupted_unresolved'
            continue
        phase('plan')
        node._metric_status['state']='running'
        try:
            candidates=[resume_target[0]] if resume_target is not None else node._metric_select(inputs,policy,min_frontier)
        except Exception as error:
            reason=str(error)
            if recovery_kind(reason)=='fatal':
                return finish('failed',reason)
            if not wait_source(reason):
                return finish('blocked','planning_revalidation_timeout:'+reason)
            continue
        if resume_target is None:
            source_wait_at=None
        if goal_handle.is_cancel_requested:
            return finish('canceled','user_canceled')
        if expired():
            return finish('partial','budget_exhausted')
        if node._wohnungserkundung_hwt_hold():
            continue
        node._metric_status.update(candidates=len(candidates),ranking=node._frontier_rank_stats)
        if not candidates:
            try:
                inside=node._metric_scope_mask(inputs)
                remainder=reachable_remainder(inputs[0],inside,inputs[2],node._world_to_grid)
                scan=node._metric_sensor_scan()[1]
                unresolved=any(a.tries and not a.completed and not a.partial_observation
                               and a.reason!='proposal_rejected' for a in policy.attempts.values())
                clear=not remainder and node._metric_scope_is_covered(inputs[0]) and not unresolved
            except Exception as error:
                reason=str(error)
                if recovery_kind(reason)=='fatal':
                    return finish('failed',reason)
                if not wait_source(reason):
                    return finish('blocked','completion_sources_unavailable:'+reason)
                continue
            node._metric_status.update(reachable_boundary_cells=remainder,
                completion_blocker=None if clear else 'accessible_or_unresolved_work')
            completion_context=(inputs[1].context,getattr(node,'_metric_context_generation',0),
                inputs[0].info.resolution,node._metric_grid_values(inputs[0])['origin'][3:])
            if completion.observe(now=time.monotonic(),scan_stamp=scan['key'][0]*10**9+scan['key'][1],
                    context=completion_context,clear=clear):
                # Same fresh final-completion contract as continuous mode.
                try:
                    final=node._metric_inputs()
                    node._metric_sensor_scan()
                    final_clear=(final[1].context==inputs[1].context and node._metric_scope_is_covered(final[0])
                        and final[0].info.resolution==inputs[0].info.resolution
                        and node._metric_grid_values(final[0])['origin'][3:]==completion_context[3]
                        and not reachable_remainder(final[0],node._metric_scope_mask(final),final[2],node._world_to_grid)
                        and not stop_cause(context=mission_context)
                        and node._metric_operating_snapshot(require_stop=True)['safe'])
                except Exception as caught:
                    reason=str(caught)
                    if recovery_kind(reason)=='fatal':
                        return finish('failed',reason)
                    if not wait_source(reason):
                        return finish('blocked','completion_sources_unavailable:'+reason)
                    final_clear=False
                if final_clear:
                    with node._metric_lock:
                        current=node._metric_correlation
                        if (not node._metric_fault and current is not None and node._metric_raw is not None
                                and node._metric_matches_status(node._metric_raw[1])
                                and current.fingerprint==final[1].fingerprint
                                and current.source_stamp_ns==final[1].source_stamp_ns):
                            for old in policy.attempts.values():
                                if old.partial_observation:
                                    old.completed=True
                                    old.partial_observation=False
                                    old.reason='observed_scope_resolved'
                            last_inputs=final
                            return finish('success','reachable_metric_scope_observed')
                completion.observe(now=time.monotonic(),scan_stamp=0,context=inputs[1].context,clear=False)
            key=(inputs[1].fingerprint,round(inputs[2][0],1),round(inputs[2][1],1))
            if not clear and key not in view_keys:
                # One measured short observation turn per unchanged place/map.
                # It never invents a transit target or bypasses sensor braking.
                view_keys.add(key)
                attempts+=1
                phase('scan')
                first=[None]
                def view_stop():
                    reason=stop_cause(rotation=True)
                    if reason and first[0] is None:
                        first[0]=reason
                    return reason is not None
                status,angle=node._scan_in_place(stop_requested=view_stop,
                    angle_rad=min(math.pi/4,node._initial_scan_angle))
                node._metric_status['recoveries']+=1
                node._metric_record_transition('recovery_observation',first[0] or status,angle_rad=angle)
                view_reason=first[0] or status
                if (status!='success' and view_reason not in ('hwt_hold','user_canceled','budget_exhausted')
                        and recovery_kind(view_reason,node._metric_status.get('decision_snapshot'))=='fatal'):
                    return finish('failed',view_reason)
            phase('observe')
            node._metric_status['state']='waiting'
            if not clear:
                idle_key=observation_key()
                wake=[a.retry_after for a in policy.attempts.values() if a.retry_after>time.monotonic()]
                idle_until=min(wake,default=time.monotonic()+node._metric_retry_s)
            checkpoint()
            time.sleep(min(.25,node._replan_period_s))
            continue

        target=candidates[0]
        completion.observe(now=time.monotonic(),scan_stamp=0,context=inputs[1].context,clear=False)
        baseline=resume_target[1] if resume_target is not None else node._metric_observation_baseline(inputs,target)
        context=(getattr(node,'_metric_context_generation',0),inputs[1].context,
            inputs[0].header.frame_id,inputs[0].info.resolution,inputs[5].header.frame_id,inputs[5].info.resolution)
        if resume_target is not None and context!=resume_target[3]:
            return finish('failed','map_work_context_changed')
        node._metric_active=target
        node._metric_active_context=context
        node._metric_nav_path=None
        node._metric_plan_after_ns=None
        if resume_target is None:
            attempts+=1
            policy.record(target,'pending',time.monotonic(),target.fingerprint)
        checkpoint()
        deadline=resume_target[2] if resume_target is not None else time.monotonic()+node._goal_timeout_s
        task_motion_dispatched=resume_target[4] if resume_target is not None else False
        original_trigger=resume_target[5] if resume_target is not None else None
        resume_target=None
        first=[None]
        def child_stop():
            reason=stop_cause(context=context,deadline=deadline)
            if reason and first[0] is None:
                first[0]=reason
            return reason is not None
        node._metric_status['active_goal']=dict(task_id=target.task_id,x=target.x,y=target.y)
        status='planning_failed'
        dispatched=False
        try:
            path,error=node._metric_request_nav_plan(target,child_stop)
        except Exception as caught:
            path,error=None,str(caught)
        if path is not None and not child_stop():
            try:
                inputs=node._metric_inputs()
                route=node._metric_validate_nav_plan(inputs,path,target)
                if route is None:
                    error=str(node._metric_last_route_rejection)
                else:
                    source_wait_at=None
                    node._metric_nav_path=path
                    node._lab_scoped_path=(path,node._metric_scope.fingerprint)
                    # No next-goal/full-turn forecast before this useful leg.
                    # The actual native path and alignment remain fully proved.
                    alignment=node._metric_align_nav_departure(route,inputs[2],child_stop,inputs=inputs)
                    node._metric_status['departure_alignment']=dict(status=alignment[0],result=list(alignment))
                    if alignment[0] not in ('success','skipped','controller_owned'):
                        error=str(alignment[0])
                    elif not child_stop():
                        current=node._metric_inputs()
                        if node._metric_validate_nav_plan(current,path,target) is None:
                            error='route_invalidated'
                        else:
                            with node._wohnungserkundung_runtime_lock:
                                if node._wohnungserkundung_active_child is not None:
                                    return finish('failed','second_child_forbidden')
                                node._metric_plan_after_ns=node.get_clock().now().nanoseconds
                                node._wohnungserkundung_active_child=target
                            phase('drive')
                            try:
                                dispatched=True
                                task_motion_dispatched=True
                                status=node._navigate_to(target.x,target.y,max(.001,deadline-time.monotonic()),
                                    stop_requested=child_stop,goal_yaw=target.yaw)
                            finally:
                                with node._wohnungserkundung_runtime_lock:
                                    node._wohnungserkundung_active_child=None
            except Exception as caught:
                error=str(caught)
                if dispatched:
                    status='error'
                    node._metric_record_transition('child_exception',error)
        reason=first[0] or (error if not dispatched else None)
        if status in ('cancel_failed','error'):
            return finish('failed','child_'+status)
        if getattr(node,'_nav_child_uncertain',False):
            node._metric_record_transition('child_state_unconfirmed',status)
            return finish('failed','child_state_uncertain')
        if goal_handle.is_cancel_requested or reason=='user_canceled':
            return finish('canceled','user_canceled')
        if node._hwt_hold_announced or reason=='hwt_hold':
            original_trigger=original_trigger or reason or 'hwt_hold'
            node._metric_record_transition('slot_motion_interrupted',reason or 'hwt_hold',
                task=target.task_id,child_result=status)
            record_child(dict(task=target.task_id,result=status,stop_reason='hwt_hold',
                original_trigger=original_trigger,first_stop_reason=first[0],
                terminal_child=True,child_dispatched=dispatched,arrived=False,observed_cells=0))
            resume_target=(target,baseline,deadline,context,task_motion_dispatched,original_trigger)
            continue
        if reason and recovery_kind(reason,node._metric_status.get('decision_snapshot'))=='fatal':
            return finish('failed',reason)
        if reason:
            original_trigger=original_trigger or reason
            node._metric_record_transition('slot_motion_interrupted',reason,task=target.task_id)
            node._metric_status['recoveries']+=1
        if expired():
            return finish('partial','budget_exhausted')
        if reason and recovery_kind(reason)=='wait' and time.monotonic()<deadline:
            # Same interrupted job, original absolute deadline and counters.
            # Top of the next slot confirms healthy sources and actual stop.
            record_child(dict(task=target.task_id,result=status,stop_reason=reason,
                original_trigger=original_trigger,first_stop_reason=first[0],
                terminal_child=True,child_dispatched=dispatched,arrived=False,observed_cells=0))
            resume_target=(target,baseline,deadline,context,task_motion_dispatched,original_trigger)
            node._metric_nav_path=node._metric_plan_after_ns=None
            if not wait_source(reason):
                return finish('blocked','motion_source_revalidation_timeout:'+reason)
            continue
        phase('observe')
        # Terminal child first; actual fresh stable stop before any new work.
        if not node._metric_confirm_stop(goal_handle,expired):
            record_child(dict(task=target.task_id,result=status,stop_reason=reason,
                original_trigger=original_trigger,first_stop_reason=first[0],
                decision='await_stop_revalidation',terminal_child=True,arrived=False,observed_cells=0))
            resume_target=(target,baseline,deadline,context,task_motion_dispatched,original_trigger)
            node._metric_nav_path=node._metric_plan_after_ns=None
            if not wait_source('stable_standstill_not_confirmed'):
                return finish('blocked','standstill_revalidation_timeout')
            continue
        reached=False
        gained=frozenset()
        until=min(deadline,time.monotonic()+node._metric_observation_wait_s)
        after=None
        while time.monotonic()<until:
            reason_now=stop_cause(context=context)
            if reason_now:
                if reason_now in ('user_canceled','budget_exhausted','hwt_hold'):
                    break
                if recovery_kind(reason_now,node._metric_status.get('decision_snapshot'))=='fatal':
                    return finish('failed',reason_now)
                time.sleep(.05)
                continue
            try:
                after=node._metric_inputs()
                yaw=math.atan2(math.sin(after[2][2]-target.yaw),math.cos(after[2][2]-target.yaw))
                reached=status=='success' and math.dist(after[2][:2],(target.x,target.y))<=.15 and abs(yaw)<=.4
                if not reached:
                    break
                view,scan=node._metric_sensor_scan()
                gained=measured_gain(baseline,after[0],after[1],after[2],scan,view.mount,
                    node._world_to_grid,node._grid_to_world,node._door_lidar_max_range,batch_projection=True)
                if gained:
                    final=node._metric_inputs()
                    scan_stamp=scan['key'][0]*10**9+scan['key'][1]
                    if (final[1].fingerprint==after[1].fingerprint
                            and final[1].context==after[1].context and not expired()
                            and time.monotonic()<until and not stop_cause(context=context)
                            and 0<=time.monotonic()-scan['received_at']<=node._door_lidar_scan_timeout
                            and 0<=(node.get_clock().now().nanoseconds-scan_stamp)/1e9<=node._door_lidar_scan_timeout
                            and node._metric_operating_snapshot(require_stop=True)['safe']):
                        after=final
                        break
                gained=frozenset()
            except Exception as caught:
                if recovery_kind(str(caught))=='fatal':
                    return finish('failed',str(caught))
            time.sleep(.05)
        outcome=('observed' if gained else 'arrival_without_observation') if reached else 'task_unreached_cause_unproven'
        if not task_motion_dispatched:
            outcome='proposal_rejected'
        if gained:
            omitted=local_small_remainder(after[0],node._metric_scope_mask(after),after[2],
                policy.attempts[target.task_id].frontier_xy,node._world_to_grid,node._grid_to_world,min_frontier)
            node._metric_status['local_omitted_boundary_cells']=omitted
            if (omitted or not observation_complete(baseline,after[0],after[1],
                    node._world_to_grid,node._grid_to_world)):
                outcome='partially_observed'
        evidence=(local_evidence(after[0],policy.attempts[target.task_id].frontier_xy,node._grid_to_world,batch_projection=True)
                  if after is not None else None)
        counted_failure=task_motion_dispatched and outcome not in ('observed','partially_observed')
        policy.record(target,outcome,time.monotonic(),after[1].fingerprint if after else target.fingerprint,
            evidence,count_try=False,count_failure=counted_failure,
            arrival_xy=after[2][:2] if reached else None)
        if reached:
            arrivals+=1
            node._frontiers_visited_status=arrivals
        if gained:
            observations+=1
            area+=len(gained)*after[0].info.resolution**2
        elif counted_failure:
            failures+=1  # telemetry; ordinary task failures do not kill LAB mission
        if after is not None:
            last_inputs=after
        record_child(dict(task=target.task_id,target=[target.x,target.y],result=status,decision=outcome,
            terminal_child=True,child_dispatched=dispatched,stop_reason=reason,first_stop_reason=first[0],
            task_motion_dispatched=task_motion_dispatched,original_trigger=original_trigger,
            arrived=reached,observed_cells=len(gained)))
        forget_plan()
        checkpoint()
        node._metric_status.update(arrivals=arrivals,observations=observations,observed_area_m2=area,
                                  attempts=attempts,failures=failures,state='waiting_new_observation')
        time.sleep(min(.25,node._replan_period_s))
    return finish('failed','ros_shutdown')
