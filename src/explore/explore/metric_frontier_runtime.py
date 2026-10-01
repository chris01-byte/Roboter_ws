"""Explicit strategy adapter inside the existing Explorer/Action owner.

Only ExploreNode's existing Nav2 client and gated scan path execute motion.
Map/status identity is shared product code; semantic feeds never enter this
adapter. The measured footprint is checked on both actual input rasters.
"""
import json
import math
import threading
import time

import numpy as np
import rclpy
from .exploration_scope import rasterize_scope
from rcl_interfaces.msg import ParameterDescriptor
from std_msgs.msg import String
from robot_interfaces.action import ExploreArea

from .map_status_adapter import (
    MapManagerStatusCorrelator, decode_map_manager_status_json,
    MapStatusUnavailableError)
from .portal_source_adapter import raw_map_portal_source_from_values, PortalSourceCorrelation
from .frontier_task_evidence import _validated_snapshot
from .exploration_scope import AuthorizedExplorationScope
from .metric_frontier import (
    MetricCandidate, MetricTaskPolicy, route_cells, known_safe_mask,
    footprint_clear, footprint_route_clear, self_body_unknown_mask)


class MetricFrontierRuntime:
    def _declare_metric_strategy(self):
        self._exploration_strategy = self.declare_parameter(
            'exploration_strategy', 'existing',
            ParameterDescriptor(read_only=True,
                description='Select at process start while no mission is active.')).value
        if self._exploration_strategy not in ('existing', 'metric_frontier'):
            raise ValueError('Unknown exploration_strategy')
        self._metric_enabled = self._exploration_strategy == 'metric_frontier'

    def _initialize_metric_strategy(self):
        if not self._metric_enabled:
            return
        if self._wohnungserkundung_navigation_enabled or self._wohnungserkundung_policy_enabled:
            raise ValueError('metric_frontier excludes the semantic task owner')
        if (not self._wohnungserkundung_accessible_scope_verified
                or not self._wohnungserkundung_scope_id or not self._wohnungserkundung_scope_vertices):
            raise ValueError('metric_frontier needs an explicitly verified polygon scope')
        if self._portal_enabled or self._door_distance > 0 or self._coverage_enabled or self._return_to_start_p:
            raise ValueError('metric_frontier excludes direct bridges, coverage and return execution')
        self._metric_lock = threading.RLock()
        self._metric_hold_lock = threading.RLock()
        self._metric_correlator = MapManagerStatusCorrelator(
            self.declare_parameter('metric_session_id', '').value, self._global_frame)
        self._metric_scope_binding = self.declare_parameter('metric_scope_map_fingerprint', '').value
        if (len(self._metric_scope_binding) != 64
                or any(c not in '0123456789abcdef' for c in self._metric_scope_binding)):
            raise ValueError('metric scope needs the observed initial map fingerprint')
        self._metric_retry_s = float(self.declare_parameter('metric_retry_cooldown_s', 30.).value)
        self._metric_retry_limit = int(self.declare_parameter('metric_task_retry_limit', 2).value)
        # The existing per-child budget is absolute, across HOLD and alignment.
        if (not all(math.isfinite(v) and v > 0 for v in (self._goal_timeout_s,
                self._overall_timeout_s,self._metric_retry_s)) or self._metric_retry_limit < 1):
            raise ValueError('metric_frontier needs finite positive budgets')
        footprint = self.declare_parameter(
            'metric_footprint_xy', [-.13,-.25,.33,-.25,.33,.25,-.13,.25]).value
        if (len(footprint) < 6 or len(footprint) % 2
                or not all(math.isfinite(v) for v in footprint)):
            raise ValueError('metric footprint invalid')
        self._metric_self_body_enabled = self.declare_parameter(
            'metric_self_body_enabled', False).value
        self._metric_body_anchor = None
        self._metric_bounds = (min(footprint[::2]), max(footprint[::2]),
                               min(footprint[1::2]), max(footprint[1::2]))
        if any((self._metric_bounds[0] > -.13, self._metric_bounds[1] < .33,
                self._metric_bounds[2] > -.25, self._metric_bounds[3] < .25)):
            raise ValueError('metric footprint cannot shrink the measured padded chassis')
        self._metric_raw = None
        self._metric_correlation = None
        self._metric_status_at = None
        self._metric_pending_since = None
        self._metric_fault = None
        self._metric_scope = None
        self._metric_wheel = None
        self._metric_wheel_at = None
        self._metric_active = None
        self._metric_status = {'state': 'idle', 'full_apartment_complete': False,
                               'semantic_complete': False, 'floor_coverage_verified': False}
        # Shared source observers and single-child/HOLD lock, without policy.
        self._wohnungserkundung_runtime_lock = threading.Lock()
        self._wohnungserkundung_active_child = None
        self._wohnungserkundung_estop = None
        self._wohnungserkundung_estop_received_at = None
        self._wohnungserkundung_vl53_received_at = dict(left=None, right=None)
        self._wohnungserkundung_vl53_observed_at = dict(left=None, right=None)
        self._wohnungserkundung_vl53_measurement_valid = dict(left=None, right=None)
        self._wohnungserkundung_vl53_point_count = dict(left=0, right=0)
        self._wohnungserkundung_vl53_cloud_stamp_ns = dict(left=None, right=None)
        self._wohnungserkundung_vl53_status = None
        self._wohnungserkundung_vl53_status_at = None
        self._wohnungserkundung_vl53_status_observed_at = None
        self.create_subscription(String, '/robot_map_manager/status_json',
                                 self._on_metric_map_status, 10, callback_group=self._cb)
        self.create_subscription(String, '/base_hardware/state_json',
                                 self._on_metric_wheel_status, 10, callback_group=self._cb)

    @staticmethod
    def _metric_grid_values(grid):
        o = grid.info.origin
        return dict(width=grid.info.width, height=grid.info.height,
                    resolution=grid.info.resolution, frame_id=grid.header.frame_id,
                    origin=(o.position.x,o.position.y,o.position.z,
                            o.orientation.x,o.orientation.y,o.orientation.z,o.orientation.w),
                    cells=grid.data, source_stamp_ns=grid.header.stamp.sec*1000000000+grid.header.stamp.nanosec)

    def _on_metric_map(self, grid):
        try:
            if grid.info.width*grid.info.height > self._wohnungserkundung_evidence_max_cells:
                raise ValueError('map_capacity')
            values = self._metric_grid_values(grid)
            source = raw_map_portal_source_from_values(**values)
            if source.frame_id != self._global_frame:
                raise ValueError('map_frame_changed')
            with self._metric_lock:
                previous = self._metric_raw
                if previous is not None and source.source_stamp_ns < previous[1].source_stamp_ns:
                    return  # delayed old callback cannot replace the current raw raster
                self._metric_raw = (grid, source, time.monotonic())
                if not self._metric_matches_status(source) and self._metric_pending_since is None:
                    self._metric_pending_since = time.monotonic()
                elif self._metric_matches_status(source):
                    self._metric_pending_since = None
        except Exception as error:
            with self._metric_lock:
                self._metric_fault = f'raw_map_{type(error).__name__}:{error}'

    def _metric_matches_status(self, source):
        c = self._metric_correlation
        return (c is not None and c.fingerprint == source.fingerprint
                and c.source_stamp_ns == source.source_stamp_ns
                and c.context.frame_id == source.frame_id)

    def _on_metric_map_status(self, msg):
        try:
            sample = decode_map_manager_status_json(msg.data)
            with self._metric_lock:
                old = self._metric_correlator._last_sample
                if old is not None and sample.status_time_seconds < old.status_time_seconds:
                    return
                status = self._metric_correlator.accept(sample)
                if self._metric_scope is None:
                    if sample.fingerprint != self._metric_scope_binding:
                        raise ValueError('scope_initial_map_binding_mismatch')
                    self._metric_scope = AuthorizedExplorationScope(
                        self._wohnungserkundung_scope_id, status.context,
                        self._wohnungserkundung_scope_vertices)
                self._metric_correlation = status
                self._metric_status_at = time.monotonic() - sample.received_age_seconds
                if self._metric_raw and self._metric_matches_status(self._metric_raw[1]):
                    self._metric_pending_since = None
        except MapStatusUnavailableError:
            pass  # before first map only; no invented map/session
        except Exception as error:
            with self._metric_lock:
                self._metric_fault = f'map_status_{type(error).__name__}:{error}'

    def _on_metric_wheel_status(self, msg):
        try:
            status = json.loads(msg.data) if len(msg.data) <= 65536 else None
            if not isinstance(status, dict):
                status = None
        except (ValueError, TypeError):
            status = None
        with self._metric_lock:
            self._metric_wheel = status
            self._metric_wheel_at = time.monotonic()

    def _metric_inputs(self, active=False):
        with self._metric_lock:
            fault = self._metric_fault
            raw, c, scope = self._metric_raw, self._metric_correlation, self._metric_scope
            at, pending = self._metric_status_at, self._metric_pending_since
        now = time.monotonic()
        if fault:
            raise ValueError(fault)
        if raw is None or c is None or scope is None:
            raise ValueError('map_scope_not_joined')
        grid, source, received = raw
        if not 0 <= now-received <= self._map_timeout_s or at is None or not 0 <= now-at <= self._map_timeout_s:
            raise ValueError('map_or_status_stale')
        age = (self.get_clock().now().nanoseconds-source.source_stamp_ns)/1e9
        if not 0 <= age <= self._map_timeout_s:
            raise ValueError('raw_map_stamp_stale')
        if not self._metric_matches_status(source):
            if not active or pending is None or now-pending > 1.25:
                raise ValueError('map_status_join_pending')
        correlation = PortalSourceCorrelation(c.context, c.map_revision, source.fingerprint, source.source_stamp_ns)
        occupancy, res, origin, yaw = _validated_snapshot(
            correlation, **self._metric_grid_values(grid), max_cells=self._wohnungserkundung_evidence_max_cells)
        pose, age = self._robot_pose_sample()
        if pose is None or age is None or not 0 <= age <= self._door_pose_timeout:
            raise ValueError('pose_missing_stale_or_invalid')
        costmap, at = self._global_costmap, self._global_costmap_received_at
        if costmap is None or at is None or not 0 <= time.monotonic()-at <= self._map_timeout_s:
            raise ValueError('costmap_missing_or_stale')
        values = self._metric_grid_values(costmap)
        identity = raw_map_portal_source_from_values(**values)
        cost_c = PortalSourceCorrelation(c.context, c.map_revision, identity.fingerprint, identity.source_stamp_ns)
        costs, _, _, _ = _validated_snapshot(cost_c, **values, max_cells=self._wohnungserkundung_evidence_max_cells)
        cost_age = (self.get_clock().now().nanoseconds-identity.source_stamp_ns)/1e9
        if not 0 <= cost_age <= self._map_timeout_s:
            raise ValueError('costmap_stamp_stale')
        body = None
        if self._metric_self_body_enabled:
            scan = self._door_lidar_scan_snapshot()
            # A scan callback can arrive during the map calculations above.
            # Evaluate after selecting its immutable snapshot, not against
            # the older map-evaluation start time (which makes it 'future').
            scan_now = time.monotonic()
            if (scan is None or not 0 <= scan_now-scan['received_at'] <= self._door_lidar_scan_timeout):
                raise ValueError('self_body_scan_stale')
            mount = self._door_lidar_mount(scan['frame_id'])
            if mount is None:
                raise ValueError('self_body_lidar_tf_missing')
            # Validate TF even after this bounded first-map exemption expires.
            body = self_body_unknown_mask(grid, occupancy, pose, mount)
            if self._metric_body_anchor is None:
                self._metric_body_anchor = (source.fingerprint, pose)
            fingerprint, anchor = self._metric_body_anchor
            # Freeze the exemption at the first joined pose/map. It never
            # follows the vehicle into newly swept unknown space or a new map.
            body = (self_body_unknown_mask(grid, occupancy, anchor, mount)
                    if fingerprint == source.fingerprint else None)
        known, safe = known_safe_mask(occupancy, scope, correlation, origin, yaw, res,
                                     self._goal_clearance_m, body)
        # Costmap values already include Nav2 inflation; also check full chassis
        # against actual occupied/unknown cells rather than treating unknown free.
        cost_known = (costs >= 0) & (costs < 100)
        rr, cc = np.nonzero(safe)
        lx, ly = (cc+.5)*res, (rr+.5)*res
        wx = origin[0]+math.cos(yaw)*lx-math.sin(yaw)*ly
        wy = origin[1]+math.sin(yaw)*lx+math.cos(yaw)*ly
        o=costmap.info.origin; q=o.orientation
        cyaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        dx,dy=wx-o.position.x,wy-o.position.y
        cx=np.floor((math.cos(cyaw)*dx+math.sin(cyaw)*dy)/costmap.info.resolution).astype(int)
        cy=np.floor((-math.sin(cyaw)*dx+math.cos(cyaw)*dy)/costmap.info.resolution).astype(int)
        valid=(cy>=0)&(cy<costs.shape[0])&(cx>=0)&(cx<costs.shape[1])
        allowed=np.zeros(valid.shape,dtype=bool)
        allowed[valid]=(costs[cy[valid],cx[valid]]>=0)&(costs[cy[valid],cx[valid]]<=self._frontier_goal_max_cost)
        safe[rr[~allowed],cc[~allowed]]=False
        return grid, correlation, pose, known, safe, costmap, cost_known

    @staticmethod
    def _metric_grid_line_clear(mask,start,end):
        # Import at call time to avoid a module cycle with the owning Node.
        from .explore_node import grid_line_is_clear
        return grid_line_is_clear(mask,start,end)

    def _metric_route(self, inputs, target, target_yaw=None):
        grid, _, pose, known, safe, costmap, cost_known = inputs
        sc, sr = self._world_to_grid(*pose[:2], grid.info)
        tc, tr = self._world_to_grid(*target, grid.info)
        cells = route_cells(safe, (sr, sc), (tr, tc))
        if cells is None:
            self._metric_last_route_rejection='no_known_free_route'
            return None
        route = (pose[:2],) + tuple(self._grid_to_world(c, r, grid.info) for r, c in cells) + (target,)
        # Remove coincident points so atan2(0, 0) does not invent a turn.
        route = tuple(p for i, p in enumerate(route) if i == 0 or math.dist(p, route[i-1]) > 1e-6)
        # A raster staircase is a reachability proof, not a command to rotate
        # at every cell. Reuse the existing clear-line helper, then check the
        # full continuous chassis sweep of each resulting segment below.
        simplified = [route[0]]
        index = 0
        while index < len(route)-1:
            sc,sr = self._world_to_grid(*route[index],grid.info)
            end = index+1
            for j in range(len(route)-1,index,-1):
                tc,tr = self._world_to_grid(*route[j],grid.info)
                if self._metric_grid_line_clear(safe,(sr,sc),(tr,tc)):
                    end=j
                    break
            simplified.append(route[end])
            index=end
        route=tuple(simplified)
        def check(x, y, yaw, g, allowed):
            return footprint_clear(x,y,yaw,g,allowed,self._world_to_grid,
                                   self._grid_to_world,self._metric_bounds)
        if not footprint_route_clear(route, pose[2], ((grid,known),(costmap,cost_known)),check):
            self._metric_last_route_rejection='footprint_sweep_invalid'
            return None
        if target_yaw is not None:
            arrival_yaw = pose[2] if len(route)==1 else math.atan2(
                route[-1][1]-route[-2][1],route[-1][0]-route[-2][0])
            delta = math.atan2(math.sin(target_yaw-arrival_yaw),math.cos(target_yaw-arrival_yaw))
            steps = max(1,math.ceil(abs(delta)/.05))
            if not all(check(*target,arrival_yaw+delta*k/steps,g,allowed)
                       for k in range(steps+1)
                       for g,allowed in ((grid,known),(costmap,cost_known))):
                self._metric_last_route_rejection='goal_orientation_invalid'
                return None
        self._metric_last_route_rejection=None
        return route

    def _metric_select(self, inputs, policy, min_frontier):
        grid, correlation, pose, *_ = inputs
        frontiers = self._detect_frontiers(grid, min_frontier)
        candidates = []
        stats = dict(raw=len(frontiers), unsafe=0, deferred_or_served=0, accepted=0,route_rejections={})
        for f in frontiers:
            goal = self._frontier_approach_goal(f, pose[:2], grid)
            route = None if goal is None else self._metric_route(inputs, goal)
            if goal is not None and route is None:
                # The historic circular clearance may admit the base centre
                # while the rotated asymmetric front touches unknown. Search
                # back from that real approach, within the existing local
                # search radius; each alternative needs the entire route proof.
                dx,dy = goal[0]-f.cx,goal[1]-f.cy
                length = math.hypot(dx,dy)
                if length > 1e-9:
                    steps = int(math.floor(self._goal_search_m/grid.info.resolution))
                    for step in range(1,steps+1):
                        distance = step*grid.info.resolution
                        alternative = (goal[0]+distance*dx/length,goal[1]+distance*dy/length)
                        alternative_route = self._metric_route(inputs,alternative)
                        if alternative_route is not None:
                            goal,route = alternative,alternative_route
                            break
            if route is None or math.dist(goal, pose[:2]) < self._min_goal_dist_m:
                stats['unsafe'] += 1
                reason=('approach_unavailable' if goal is None else
                        self._metric_last_route_rejection if route is None else 'goal_too_near')
                counts=stats['route_rejections'];counts[reason]=counts.get(reason,0)+1
                continue
            heading = math.atan2(goal[1]-pose[1], goal[0]-pose[0])
            error = abs(math.atan2(math.sin(heading-pose[2]), math.cos(heading-pose[2])))
            if self._frontier_forward_cone_half_angle > 0 and error > self._frontier_forward_cone_half_angle:
                stats['unsafe'] += 1
                continue
            key = policy.identify((f.cx,f.cy))
            if not policy.eligible(key, goal, time.monotonic(), correlation.fingerprint):
                stats['deferred_or_served'] += 1
                continue
            length = sum(math.dist(a,b) for a,b in zip(route,route[1:]))
            cost = self._potential_scale*length-self._gain_scale*f.size*grid.info.resolution+self._heading_scale*error
            target_yaw = math.atan2(route[-1][1]-route[-2][1],route[-1][0]-route[-2][0])
            candidates.append(MetricCandidate(key,*goal,target_yaw,(f.cx,f.cy),route,length,cost,
                                              correlation.fingerprint,correlation.map_revision))
        candidates.sort(key=lambda candidate:(candidate.cost,candidate.task_id))
        stats['accepted'] = len(candidates)
        self._frontier_rank_stats = stats
        self._frontiers_remaining = len(frontiers)
        if self._visualize:
            self._publish_markers(frontiers, grid.header.frame_id)
        return candidates

    def _metric_operating_snapshot(self, require_stop=False):
        reason = None
        if self._wohnungserkundung_active_safety_failure():
            reason = self._wohnungserkundung_last_safety_failure
        with self._metric_lock:
            wheel, at = self._metric_wheel, self._metric_wheel_at
        if reason is None and (at is None or not 0 <= time.monotonic()-at <= .8
                or wheel is None or wheel.get('dry_run') is not False
                or wheel.get('allow_rs485') is not True or wheel.get('rs485_ready') is not True
                or wheel.get('odometry_source') != 'encoder_position'
                or wheel.get('encoder_feedback_ok') is not True
                or wheel.get('encoder_stale') is not False
                or wheel.get('encoder_config_fault_latched') is not False
                or type(wheel.get('encoder_feedback_age_s')) not in (int,float)
                or not 0 <= wheel['encoder_feedback_age_s'] <= .8):
            reason = 'actuator_or_encoder_state_invalid'
        with self._wohnungserkundung_runtime_lock:
            status = self._wohnungserkundung_vl53_status
            stamps = dict(self._wohnungserkundung_vl53_cloud_stamp_ns)
        if reason is None:
            stamp = status.header.stamp.sec*1000000000+status.header.stamp.nanosec
            if any(v != stamp for v in stamps.values()):
                reason = 'vl53_triplet_unmatched'
        stopped = self._wohnungserkundung_hwt_standstill_confirmed() if require_stop else None
        if reason is None and require_stop and not stopped:
            reason = 'stable_standstill_not_confirmed'
        return dict(time_monotonic=time.monotonic(), safe=reason is None,
                    first_rejecting_predicate=reason, standstill=stopped,
                    encoder_state=wheel, hwt_state=self._hwt601_decision()[1])

    def _metric_confirm_stop(self, goal_handle, expired):
        deadline = time.monotonic()+self._scan_stop_timeout
        self._hwt_stop_stable_since = None
        self._hwt_stop_first_odom_at = None
        while time.monotonic() < deadline:
            if goal_handle.is_cancel_requested or expired():
                return False
            snapshot = self._metric_operating_snapshot(True)
            self._metric_status['decision_snapshot'] = snapshot
            if snapshot['safe']:
                return True
            if snapshot['first_rejecting_predicate'] not in (
                    'stable_standstill_not_confirmed', 'vl53_triplet_unmatched'):
                return False
            time.sleep(.05)
        return False

    def _metric_health_tick(self):
        # Evaluate short source gaps independently of expensive route work.
        # The existing HOLD announcement remains latched until validated ACK.
        if getattr(self, '_active_goal', False) and self._hwt_guard is not None:
            decision = self._hwt601_decision()
            if decision[1] in ('HOLD','RECOVERY_VALIDATION'):
                self._wohnungserkundung_hwt_hold(decision)

    def _metric_resume_path_ready(self):
        if self._metric_active is None:
            return False
        try:
            return self._metric_route(self._metric_inputs(active=True),
                                      (self._metric_active.x,self._metric_active.y),self._metric_active.yaw) is not None
        except Exception:
            return False

    def _execute_metric_frontier(self, goal_handle, overall_timeout, min_frontier):
        result = ExploreArea.Result()
        overall_timeout = min(overall_timeout,self._overall_timeout_s)
        self._coverage_complete = False
        self._coverage_ratio = 0.
        self._frontiers_visited_status = 0
        policy = MetricTaskPolicy(self._frontier_revisit_radius,self._metric_retry_s,self._metric_retry_limit)
        started = time.monotonic()
        attempts = failures = 0
        pending = None
        task_started = None
        scan_pending = self._initial_scan_enabled
        chain = []
        stable_empty = set()
        def expired():
            return time.monotonic()-started >= overall_timeout
        def finish(state, reason):
            self._metric_status.update(state=state,reason=reason,chain=chain[-40:],
                                       attempts=attempts,failures=failures)
            self._status_message = reason
            self._status_phase = state
            result.success = False  # no semantic/full-coverage result is proven here
            result.message = f'metric_frontier:{state}:{reason}'
            if state == 'canceled':
                goal_handle.canceled()
            else:
                goal_handle.abort()
            self._metric_active = None
            return self._finish_result(result,self._frontiers_visited_status)
        self._metric_status = dict(state='running', full_apartment_complete=False,
                                  semantic_complete=False,floor_coverage_verified=False,chain=chain)
        self._blacklist.clear()
        self._visited_frontier_goals.clear()
        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                return finish('canceled','user_canceled')
            if expired() or attempts >= self._max_frontier_goals or failures >= self._max_failed_goals:
                return finish('partial','budget_exhausted')
            if self._wohnungserkundung_hwt_hold():
                resume = self._wohnungserkundung_wait_for_hwt_resume(goal_handle,expired,require_target=pending is not None)
                if resume != 'resumed':
                    return finish('canceled' if resume=='user_canceled' else 'failed',f'hwt_{resume}')
                continue
            snapshot = self._metric_operating_snapshot()
            self._metric_status['decision_snapshot'] = snapshot
            if not snapshot['safe']:
                if snapshot['first_rejecting_predicate'] == 'vl53_triplet_unmatched':
                    time.sleep(.02)
                    continue
                return finish('failed',snapshot['first_rejecting_predicate'])
            try:
                inputs = self._metric_inputs(active=pending is not None)
            except Exception as error:
                reason = str(error)
                if pending is None and reason in ('map_scope_not_joined','map_status_join_pending'):
                    self._status_phase='metric_waiting_sources'
                    self._status_message=reason
                    time.sleep(.05)
                    continue
                return finish('failed',reason)
            if scan_pending:
                grid, _, pose, known, _, costmap, cost_known = inputs
                if not all(footprint_clear(*pose[:2], pose[2]+angle,g,allowed,
                           self._world_to_grid,self._grid_to_world,self._metric_bounds)
                           for angle in np.linspace(0.,2*math.pi,127)
                           for g,allowed in ((grid,known),(costmap,cost_known))):
                    return finish('failed','initial_scan_footprint_invalid')
                self._status_phase='we_initial_scan'
                last_scan_check = [0.]
                def scan_stop():
                    if goal_handle.is_cancel_requested or expired() or self._wohnungserkundung_hwt_hold():
                        return True
                    snapshot = self._metric_operating_snapshot()
                    self._metric_status['decision_snapshot'] = snapshot
                    if (not snapshot['safe'] and
                            snapshot['first_rejecting_predicate'] != 'vl53_triplet_unmatched'):
                        return True  # unmatched publication window remains blocked by the gate
                    if time.monotonic()-last_scan_check[0] < .2:
                        return False
                    last_scan_check[0] = time.monotonic()
                    try:
                        live = self._metric_inputs(active=True)
                        g, _, p, allowed, _, cg, ca = live
                        clear = all(footprint_clear(*p[:2],p[2]+angle,grid,mask,
                                    self._world_to_grid,self._grid_to_world,self._metric_bounds)
                                    for angle in np.linspace(0.,2*math.pi,127)
                                    for grid,mask in ((g,allowed),(cg,ca)))
                        if not clear:
                            self._metric_status['first_rejecting_predicate'] = 'scan_footprint_invalid'
                        return not clear
                    except Exception as error:
                        self._metric_status['first_rejecting_predicate'] = str(error)
                        return True
                status, _ = self._scan_in_place(stop_requested=scan_stop)
                if self._hwt_hold_announced:
                    continue
                if status != 'success':
                    return finish('failed',f'initial_scan_{status}')
                scan_pending=False
                continue
            if pending is None:
                candidates = self._metric_select(inputs,policy,min_frontier)
                self._metric_status.update(candidates=len(candidates),ranking=self._frontier_rank_stats)
                if not candidates:
                    grid,c,_,known,*_=inputs
                    occupancy=np.asarray(grid.data).reshape(known.shape)
                    origin=self._metric_grid_values(grid)['origin']
                    inside=rasterize_scope(self._metric_scope,context=c.context,
                        width=grid.info.width,height=grid.info.height,resolution_m=grid.info.resolution,
                        origin_x_m=origin[0],origin_y_m=origin[1],origin_yaw_rad=math.atan2(
                            2*origin[6]*origin[5],1-2*origin[5]**2),maximum_cells=self._wohnungserkundung_evidence_max_cells)
                    unknown=int(np.count_nonzero((occupancy<0)&inside))
                    scope_inside=all(0<=self._world_to_grid(v.x,v.y,grid.info)[0]<grid.info.width
                        and 0<=self._world_to_grid(v.x,v.y,grid.info)[1]<grid.info.height
                        for v in self._metric_scope.vertices)
                    unresolved=any(a.failures and not a.completed for a in policy.attempts.values())
                    self._metric_status.update(unknown_cells_in_scope=unknown,
                        deferred_tasks=sum(a.failures>0 and not a.completed for a in policy.attempts.values()))
                    if (not self._frontiers_remaining and not unknown and scope_inside and not unresolved):
                        stable_empty.add((c.fingerprint,c.source_stamp_ns))
                        if len(stable_empty)>=3:
                            self._metric_status['metric_completion_candidate']=True
                            return finish('partial','metric_exhausted_candidate_requires_review')
                    else:
                        stable_empty.clear()
                    self._status_phase='metric_waiting_tasks'
                    self._status_message='No eligible task; remaining unknown/deferred work is not completion.'
                    self._metric_status['state']='waiting'
                    time.sleep(min(.25,self._replan_period_s))
                    continue
                pending = candidates[0]
                task_started = time.monotonic()
                attempts += 1
            self._metric_active = pending
            self._metric_status.update(state='running',active_goal=dict(
                task_id=pending.task_id,x=pending.x,y=pending.y,route_length_m=pending.route_length_m,
                cost=pending.cost,revision=pending.revision),attempt=attempts)
            stop_reason = [None]
            last_pose = [inputs[2],time.monotonic()]
            def stop():
                if goal_handle.is_cancel_requested:
                    stop_reason[0]='user_canceled'
                elif expired():
                    stop_reason[0]='budget_exhausted'
                elif self._wohnungserkundung_hwt_hold():
                    stop_reason[0]='hwt_hold'
                else:
                    s = self._metric_operating_snapshot()
                    # Triplet publication window is movement-gated by the real gate.
                    if not s['safe'] and s['first_rejecting_predicate'] != 'vl53_triplet_unmatched':
                        stop_reason[0]=s['first_rejecting_predicate']
                    elif time.monotonic()-task_started >= self._goal_timeout_s:
                        stop_reason[0]='task_budget_exhausted'
                    else:
                        try:
                            current = self._metric_inputs(active=True)
                            now = time.monotonic()
                            if math.dist(current[2][:2],last_pose[0][:2]) > .35+.2*(now-last_pose[1]):
                                stop_reason[0]='pose_discontinuity'
                            last_pose[:] = [current[2],now]
                            if self._metric_route(current,(pending.x,pending.y),pending.yaw) is None:
                                stop_reason[0]='route_invalidated'
                        except Exception as error:
                            stop_reason[0]=str(error)
                return stop_reason[0] is not None
            self._status_phase='metric_prealign'
            if stop():
                status='canceled'
            else:
                # Align to first route leg, never through an unvalidated chord.
                leg=pending.route[min(2,len(pending.route)-1)]
                align,*_=self._prealign_to_goal(*leg,inputs[2],stop_requested=stop)
                status = None if align in ('success','skipped') else 'alignment_failed'
            if status is None and not stop():
                self._status_phase='metric_navigation'
                feedback=ExploreArea.Feedback()
                feedback.frontiers_remaining=self._frontiers_remaining
                feedback.current_goal.header.frame_id=self._global_frame
                feedback.current_goal.pose.position.x=pending.x
                feedback.current_goal.pose.position.y=pending.y
                feedback.current_goal.pose.orientation.w=1.
                goal_handle.publish_feedback(feedback)
                with self._wohnungserkundung_runtime_lock:
                    if self._wohnungserkundung_active_child is not None:
                        return finish('failed','second_child_forbidden')
                    self._wohnungserkundung_active_child=pending
                try:
                    status=self._navigate_to(pending.x,pending.y,
                        max(.001,self._goal_timeout_s-(time.monotonic()-task_started)),
                        stop_requested=stop,goal_yaw=pending.yaw)
                finally:
                    with self._wohnungserkundung_runtime_lock:
                        self._wohnungserkundung_active_child=None
            status = status or 'canceled'
            if status in ('cancel_failed','error'):
                return finish('failed',f'child_{status}')
            if goal_handle.is_cancel_requested or stop_reason[0]=='user_canceled':
                return finish('canceled','user_canceled')
            if self._hwt_hold_announced or stop_reason[0]=='hwt_hold':
                chain.append(dict(task=pending.task_id,result='hwt_hold',terminal_child=True))
                continue  # task_started, attempts and overall budget are retained
            if expired():
                return finish('partial','budget_exhausted')
            if not self._metric_confirm_stop(goal_handle,expired):
                return finish('failed','post_child_state_or_standstill_unconfirmed')
            try:
                after=self._metric_inputs(active=True)
            except Exception as error:
                return finish('failed',str(error))
            hard = stop_reason[0]
            if hard and hard not in ('route_invalidated','task_budget_exhausted'):
                return finish('failed',hard)
            # Nav2 SUCCESS alone is not a measured arrival/observation.
            yaw_error=math.atan2(math.sin(after[2][2]-pending.yaw),math.cos(after[2][2]-pending.yaw))
            reached = (status=='success' and math.dist(after[2][:2],(pending.x,pending.y)) <= .15
                       and abs(yaw_error) <= .4)
            outcome='observed' if reached else ('route_invalidated' if hard=='route_invalidated' else 'task_unreached_cause_unproven')
            policy.record(pending,outcome,time.monotonic(),after[1].fingerprint)
            chain.append(dict(task=pending.task_id,target=[pending.x,pending.y],result=status,
                              decision=outcome,terminal_child=True,stop_reason=hard,
                              snapshot=self._metric_status['decision_snapshot']))
            if reached:
                self._frontiers_visited_status += 1
            else:
                failures += 1
            pending=None
            self._metric_active=None
            self._metric_status['state']='waiting_new_observation'
            self._status_phase='metric_replanning'
            time.sleep(min(.25,self._replan_period_s))
        return finish('failed','ros_shutdown')
