"""ROS-Anbindung der Erkundungsstrategie ``self_healing``.

Der Explorer entscheidet nur WOHIN (schnelle Frontier-Auswahl). Nav2 plant
und fährt, auch durch Unbekanntes; die lokale Kostenkarte mit VL53/OAK und
der collision_monitor weichen aus bzw. stoppen. Fehlschläge laufen durch die
begrenzte Heilungsleiter aus :mod:`explore.self_healing`. Die Mission endet
nur bei echten Ausnahmen, erschöpftem Heilungsbudget (Hilfe benötigt, Karte
bleibt nutzbar) oder vollständiger Erkundung.

Unverändert gilt: Fehlende oder alte Sicherheitsquellen erlauben nie
Bewegung. Hier führen sie zu Warten im Stillstand statt zum Abbruch; erst
nach ``self_healing_source_wait_s`` wird Hilfe angefordert. Ein aktiver
Not-Aus und Aktorfehler beenden die Mission sofort (AGENTS.md §2.3).
"""
import math
import threading
import time

import numpy as np
import rclpy
from builtin_interfaces.msg import Duration
from nav2_msgs.action import BackUp
from nav2_msgs.msg import SpeedLimit
from rcl_interfaces.msg import ParameterDescriptor
from robot_interfaces.action import ExploreArea

from .action_client import SerializedActionClient as ActionClient
from .self_healing import (
    FATAL, WAIT, classify, HealingLadder, RETRY, LOOK_AROUND, TRACK_BACK,
    REQUEST_HELP, TrackRecorder, frontier_goals, frontier_cells_remaining,
    reachable_goal_mask, rotation_clear, unknown_ahead_fraction)


class SelfHealingRuntime:
    """Mixin für ExploreNode; aktiv nur mit exploration_strategy=self_healing."""

    def _initialize_self_healing_strategy(self):
        self._self_healing_enabled = getattr(self, '_exploration_strategy', 'existing') == 'self_healing'
        if not self._self_healing_enabled:
            return
        if (getattr(self, '_wohnungserkundung_navigation_enabled', False)
                or getattr(self, '_wohnungserkundung_policy_enabled', False)):
            raise ValueError('self_healing excludes the semantic task owner')
        if (self._portal_enabled or self._door_distance > 0
                or self._coverage_enabled or self._return_to_start_p):
            raise ValueError('self_healing excludes direct bridges, coverage and return execution')
        read_only = ParameterDescriptor(read_only=True)
        def number(name, default, low, high):
            value = float(self.declare_parameter(name, default, read_only).value)
            if not (math.isfinite(value) and low <= value <= high):
                raise ValueError(f'{name} must be within {low}..{high}')
            return value
        self._self_healing_heal_wait_s = number('self_healing_heal_wait_s', 2., 0., 30.)
        self._self_healing_source_wait_s = number('self_healing_source_wait_s', 30., 1., 300.)
        self._self_healing_map_timeout_s = number('self_healing_map_timeout_s', 5., .5, 60.)
        self._self_healing_pose_timeout_s = number('self_healing_pose_timeout_s', 1.5, .1, 10.)
        self._self_healing_min_gain_m2 = number('self_healing_min_gain_m2', .05, 0., 10.)
        self._self_healing_blacklist_radius_m = number('self_healing_blacklist_radius_m', .5, .05, 3.)
        self._self_healing_min_goal_distance_m = number('self_healing_min_goal_distance_m', .3, 0., 3.)
        self._self_healing_gain_scale = number('self_healing_gain_scale', .5, 0., 10.)
        self._self_healing_completion_checks = int(number('self_healing_completion_checks', 3, 1, 20))
        # Vorab nur eindeutig Abgeschnittenes ausschließen (z. B. hinter einer
        # geschlossenen Tür). 0 schaltet die Prüfung ab.
        self._self_healing_reach_clearance_m = number('self_healing_reachability_clearance_m', .2, 0., .5)
        self._self_healing_reach_escape_m = number('self_healing_reachability_escape_m', .35, 0., 1.)
        self._self_healing_reach_tolerance_m = number('self_healing_reachability_goal_tolerance_m', .3, 0., 1.)
        self._self_healing_look_around_rad = number('self_healing_look_around_rad', math.pi/2, .1, 2*math.pi)
        self._self_healing_rotation_radius_m = number('self_healing_rotation_radius_m', .45, .2, 1.)
        self._self_healing_track_back_max_m = number('self_healing_track_back_max_m', .4, 0., 1.)
        self._self_healing_track_back_min_m = number('self_healing_track_back_min_m', .1, .02, 1.)
        self._self_healing_track_back_speed = number('self_healing_track_back_speed_mps', .05, .01, .1)
        self._self_healing_track_lateral_m = number('self_healing_track_lateral_tolerance_m', .03, .005, .1)
        # Entscheidung Projektinhaber 15.10.2026: solange vor dem Roboter noch
        # nicht kartiert ist, absolut 0,06 m/s (Nav2 speed_limit an RPP).
        # Obergrenze 0,08 m/s: ein absolutes Limit darf RPP nie beschleunigen.
        self._self_healing_unknown_speed = number('self_healing_unknown_speed_mps', .06, .02, .08)
        self._self_healing_unknown_lookahead_m = number('self_healing_unknown_lookahead_m', 1., .3, 3.)
        self._self_healing_unknown_half_width_m = number('self_healing_unknown_half_width_m', .25, .1, 1.)
        self._self_healing_unknown_fraction = number('self_healing_unknown_fraction', .02, 0., 1.)
        speed_topic = str(self.declare_parameter(
            'self_healing_speed_limit_topic', '/speed_limit', read_only).value).strip()
        if not speed_topic:
            raise ValueError('self_healing_speed_limit_topic must not be empty')
        self._self_healing_ladder_config = dict(
            goal_retries=int(number('self_healing_goal_retries', 1, 0, 5)),
            look_around_after=int(number('self_healing_look_around_after', 3, 1, 20)),
            track_back_after=int(number('self_healing_track_back_after', 5, 1, 20)),
            help_after=int(number('self_healing_help_after', 8, 1, 50)),
            max_heals=int(number('self_healing_max_heals', 30, 1, 500)),
            no_progress_timeout_s=number('self_healing_no_progress_timeout_s', 600., 10., 7200.))
        HealingLadder(**self._self_healing_ladder_config)  # validate once at start
        backup_action = str(self.declare_parameter(
            'self_healing_backup_action', 'backup', read_only).value).strip()
        if not backup_action:
            raise ValueError('self_healing_backup_action must not be empty')
        if self._self_healing_track_back_min_m > self._self_healing_track_back_max_m > 0:
            raise ValueError('self_healing_track_back_min_m exceeds the maximum')
        # Shared source observers and single-child lock (same contract as the
        # metric path); subscriptions are created by the node constructor.
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
        self._self_healing_backup_client = ActionClient(
            self, BackUp, backup_action, callback_group=self._cb)
        self._self_healing_speed_pub = self.create_publisher(SpeedLimit, speed_topic, 10)
        self._self_healing_speed_state = None   # (limit, published_at)
        self._self_healing_status = dict(schema_version=1, state='idle', outcome='in_progress')

    # ------------------------------------------------------------------
    def _self_healing_safety_reason(self):
        """None if movement may continue; otherwise the first hard reason."""
        with self._wohnungserkundung_runtime_lock:
            estop = self._wohnungserkundung_estop
        if estop is True:
            return 'estop_active'
        if self._wohnungserkundung_active_safety_failure():
            return self._wohnungserkundung_last_safety_failure or 'safety_source_invalid'
        return None

    def _self_healing_odom_pose(self):
        xy, yaw, _, _, received_at = self._motion_odom_snapshot()
        if xy is None or yaw is None or received_at is None:
            return None
        if not 0. <= time.monotonic()-received_at <= .8:
            return None
        return (xy[0], xy[1], yaw)

    def _self_healing_look_around_possible(self, pose):
        costmap = getattr(self, '_global_costmap', None)
        received = getattr(self, '_global_costmap_received_at', None)
        if (costmap is None or pose is None or received is None
                or not 0. <= time.monotonic()-received <= self._self_healing_map_timeout_s):
            return False  # no current proof that the turning circle is unobstructed
        info = costmap.info
        costs = np.asarray(costmap.data, dtype=np.int16).reshape(info.height, info.width)
        return rotation_clear(costs, lambda x, y: self._world_to_grid(x, y, info),
                              info.resolution, pose[:2], self._self_healing_rotation_radius_m)

    def _self_healing_look_around(self, stop_requested):
        """H3: slow in-place turn to gain view; collision monitor stays active."""
        try:
            status, achieved = self._rotate_in_place(
                self._self_healing_look_around_rad, self._initial_scan_speed,
                self._initial_scan_timeout, stop_requested=stop_requested)
        finally:
            self._publish_scan_stop()
        return status, achieved

    def _self_healing_track_back(self, distance_m, stop_requested):
        """H4: Nav2 BackUp, only along the straight recent own track."""
        client = self._self_healing_backup_client
        if distance_m <= 0 or not client.wait_for_server(timeout_sec=2.0):
            return 'unavailable'
        goal = BackUp.Goal()
        goal.target.x = float(distance_m)
        goal.speed = float(self._self_healing_track_back_speed)
        allowance = distance_m/self._self_healing_track_back_speed + 10.
        goal.time_allowance = Duration(sec=int(allowance), nanosec=0)
        done = threading.Event()
        holder = {'handle': None, 'status': None}
        def on_result(future):
            try:
                holder['status'] = future.result().status
            except Exception:
                holder['status'] = 'error'
            done.set()
        def on_goal(future):
            try:
                handle = future.result()
            except Exception:
                holder['status'] = 'error'
                done.set()
                return
            if not handle.accepted:
                holder['status'] = 'rejected'
                done.set()
                return
            holder['handle'] = handle
            handle.get_result_async().add_done_callback(on_result)
        client.send_goal_async(goal).add_done_callback(on_goal)
        deadline = time.monotonic()+allowance+self._cancel_timeout_s
        canceled = False
        while rclpy.ok() and not done.wait(timeout=.05):
            if not canceled and (stop_requested() or time.monotonic() > deadline):
                canceled = True
                if holder['handle'] is not None:
                    holder['handle'].cancel_goal_async()
            if canceled and time.monotonic() > deadline+self._cancel_timeout_s:
                return 'cancel_failed'
        if holder['status'] == 4:   # GoalStatus.STATUS_SUCCEEDED
            return 'success'
        return 'canceled' if canceled else str(holder['status'])

    def _self_healing_speed_limit(self):
        """Absolute limit if the corridor ahead is not yet mapped, else 0 (none)."""
        grid = getattr(self, '_map', None)
        received = getattr(self, '_map_received_at', None)
        pose, age = self._robot_pose_sample()
        if (grid is None or received is None or pose is None or age is None
                or not 0. <= time.monotonic()-received <= self._self_healing_map_timeout_s
                or not 0. <= age <= self._self_healing_pose_timeout_s):
            return self._self_healing_unknown_speed, 1.   # fail-safe slow
        info = grid.info
        occupancy = np.asarray(grid.data, dtype=np.int16).reshape(info.height, info.width)
        q = info.origin.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        c, s = math.cos(yaw), math.sin(yaw)
        def to_cells(x, y):
            dx, dy = x-info.origin.position.x, y-info.origin.position.y
            return (np.floor((c*dx+s*dy)/info.resolution).astype(int),
                    np.floor((-s*dx+c*dy)/info.resolution).astype(int))
        fraction = unknown_ahead_fraction(occupancy, to_cells, info.resolution, pose,
            lookahead_m=self._self_healing_unknown_lookahead_m,
            half_width_m=self._self_healing_unknown_half_width_m)
        limited = fraction > self._self_healing_unknown_fraction
        return (self._self_healing_unknown_speed if limited else 0.), fraction

    def _self_healing_govern_speed(self, *, release=False, force=False):
        """Publish Nav2 SpeedLimit on change and refresh it once per second."""
        now = time.monotonic()
        state = self._self_healing_speed_state
        if not release and not force and state is not None and now-state[2] < .2:
            return state[0]
        if release:
            limit, fraction = 0., None
        else:
            try:
                limit, fraction = self._self_healing_speed_limit()
            except Exception:   # never turn a governor fault into speed
                limit, fraction = self._self_healing_unknown_speed, 1.
        if force or release or state is None or limit != state[0] or now-state[1] >= 1.:
            message = SpeedLimit()
            message.header.frame_id = self._global_frame
            message.percentage = False
            message.speed_limit = float(limit)   # 0.0 = nav2 NO_SPEED_LIMIT
            self._self_healing_speed_pub.publish(message)
            state = (limit, now, now)
        else:
            state = (state[0], state[1], now)
        self._self_healing_speed_state = state
        if hasattr(self, '_self_healing_status'):
            self._self_healing_status['speed_limit_mps'] = limit or None
            self._self_healing_status['unknown_ahead_fraction'] = fraction
        return limit

    # ------------------------------------------------------------------
    def _execute_self_healing(self, goal_handle, overall_timeout, min_frontier_m):
        result = ExploreArea.Result()
        started = time.monotonic()
        limit = overall_timeout if overall_timeout and overall_timeout > 0 else math.inf
        ladder = HealingLadder(**self._self_healing_ladder_config)
        ladder.start(started)
        track = TrackRecorder()
        blacklist, attempts = [], {}
        reached = 0
        empty_checks = 0
        known_cells = None
        source_wait_since = None
        second_chance_used = False
        status = self._self_healing_status = dict(
            schema_version=1, state='running', outcome='in_progress', reason=None,
            goals_reached=0, heals=0, deferred_goals=0, track_backs=0, look_arounds=0,
            waiting_for=None, active_goal=None, ladder=ladder.snapshot())
        self._status_state = 'running'

        def expired():
            return time.monotonic()-started >= limit

        def finish(state, reason):
            if goal_handle.is_cancel_requested and not getattr(self, '_nav_child_uncertain', False):
                state, reason = 'canceled', 'user_canceled'
            outcome = dict(success='exploration_complete', partial='usable_partial',
                           blocked='blocked_help_required', failed='error',
                           canceled='user_canceled')[state]
            status.update(state=state, reason=reason, outcome=outcome, active_goal=None,
                          ladder=ladder.snapshot(), goals_reached=reached)
            self._status_message = reason
            self._status_phase = state
            self._status_state = 'partial' if state == 'blocked' else state
            self._self_healing_govern_speed(release=True)
            result.success = state == 'success'
            result.message = f'self_healing:{state}:{reason}'
            if state == 'canceled':
                goal_handle.canceled()
            elif state == 'success':
                goal_handle.succeed()
            else:
                goal_handle.abort()
            return self._finish_result(result, reached)

        def stop_requested():
            return (goal_handle.is_cancel_requested or expired()
                    or self._wohnungserkundung_hwt_hold()
                    or self._self_healing_safety_reason() is not None)

        def record_track():
            track.add(self._self_healing_odom_pose())
            self._self_healing_govern_speed()
            return True

        def wait_for(reason):
            """H0: stay stopped; True while still within the source window."""
            nonlocal source_wait_since
            now = time.monotonic()
            if source_wait_since is None:
                source_wait_since = now
            status.update(state='waiting', waiting_for=reason)
            self._status_phase = 'self_healing_waiting'
            self._status_message = reason
            if now-source_wait_since > self._self_healing_source_wait_s:
                return False
            time.sleep(.2)
            return True

        while rclpy.ok():
            if goal_handle.is_cancel_requested:
                return finish('canceled', 'user_canceled')
            if expired():
                return finish('partial', 'overall_budget_exhausted')
            if self._wohnungserkundung_hwt_hold():
                resume = self._wohnungserkundung_wait_for_hwt_resume(
                    goal_handle, expired, require_target=False)
                if resume == 'resumed':
                    continue
                if resume == 'user_canceled':
                    return finish('canceled', 'user_canceled')
                if resume == 'budget_exhausted':
                    return finish('partial', 'overall_budget_exhausted')
                return finish('blocked', f'help_required:hwt_{resume}')
            reason = self._self_healing_safety_reason()
            if reason is not None:
                if classify(reason) == FATAL:
                    return finish('failed', reason)
                if not wait_for(reason):
                    return finish('blocked', f'help_required:{reason}')
                continue
            grid = getattr(self, '_map', None)
            received = getattr(self, '_map_received_at', None)
            pose, pose_age = self._robot_pose_sample()
            if (grid is None or received is None
                    or time.monotonic()-received > self._self_healing_map_timeout_s):
                if not wait_for('map_missing_or_stale'):
                    return finish('blocked', 'help_required:map_missing_or_stale')
                continue
            if pose is None or pose_age is None or not 0. <= pose_age <= self._self_healing_pose_timeout_s:
                if not wait_for('pose_missing_or_stale'):
                    return finish('blocked', 'help_required:pose_missing_or_stale')
                continue
            source_wait_since = None
            status['waiting_for'] = None
            info = grid.info
            occupancy = np.asarray(grid.data, dtype=np.int16).reshape(info.height, info.width)
            known = int(np.count_nonzero(occupancy >= 0))
            gain_cells = max(1, int(self._self_healing_min_gain_m2/info.resolution**2))
            now = time.monotonic()
            if known_cells is None or known < known_cells:
                known_cells = known            # first map or a SLAM re-render
            elif known-known_cells >= gain_cells:
                ladder.progress(now)
                known_cells = known
            min_cells = max(1, int(round(min_frontier_m/info.resolution)))
            def cell_to_world(rows, cols, info=info):
                q = info.origin.orientation
                yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                lx, ly = (cols+.5)*info.resolution, (rows+.5)*info.resolution
                c, s = math.cos(yaw), math.sin(yaw)
                return (info.origin.position.x+c*lx-s*ly, info.origin.position.y+s*lx+c*ly)
            allowed = None
            if self._self_healing_reach_clearance_m > 0:
                q = info.origin.orientation
                yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                dx, dy = pose[0]-info.origin.position.x, pose[1]-info.origin.position.y
                lx = math.cos(yaw)*dx + math.sin(yaw)*dy
                ly = -math.sin(yaw)*dx + math.cos(yaw)*dy
                allowed = reachable_goal_mask(
                    occupancy, info.resolution,
                    (math.floor(ly/info.resolution), math.floor(lx/info.resolution)),
                    clearance_m=self._self_healing_reach_clearance_m,
                    escape_m=self._self_healing_reach_escape_m,
                    goal_tolerance_m=self._self_healing_reach_tolerance_m)
            selection = dict(min_size_cells=min_cells, blacklist=blacklist,
                blacklist_radius_m=self._self_healing_blacklist_radius_m,
                min_distance_m=self._self_healing_min_goal_distance_m,
                gain_scale=self._self_healing_gain_scale)
            goals = frontier_goals(occupancy, info.resolution, cell_to_world, pose[:2],
                                   allowed=allowed, **selection)
            if allowed is not None:
                status['unreachable_frontiers'] = len(frontier_goals(
                    occupancy, info.resolution, cell_to_world, pose[:2], **selection)) - len(goals)
            self._frontiers_remaining = len(goals)
            if not goals:
                empty_checks += 1
                status.update(state='checking_completion', active_goal=None)
                if empty_checks < self._self_healing_completion_checks:
                    time.sleep(min(.5, self._replan_period_s))
                    continue
                remaining = frontier_cells_remaining(occupancy, min_cells)
                if remaining == 0:
                    return finish('success', 'exploration_complete')
                if not second_chance_used and blacklist:
                    # Deferred goals get one more chance with the grown map.
                    second_chance_used = True
                    blacklist.clear()
                    attempts.clear()
                    empty_checks = 0
                    continue
                return finish('partial', 'remaining_frontiers_unreachable')
            empty_checks = 0
            goal = goals[0]
            key = (round(goal.x/.25), round(goal.y/.25))
            attempts[key] = attempts.get(key, 0)+1
            status.update(state='running', active_goal=dict(x=goal.x, y=goal.y,
                distance_m=goal.distance_m, size_cells=goal.size_cells, attempt=attempts[key]))
            self._status_phase = 'self_healing_navigation'
            self._status_message = 'Navigating to frontier.'
            self._self_healing_govern_speed(force=True)   # limit before the child exists
            record_track()
            with self._wohnungserkundung_runtime_lock:
                self._wohnungserkundung_active_child = goal
            try:
                nav = self._navigate_to(goal.x, goal.y, self._goal_timeout_s,
                                        stop_requested=stop_requested,
                                        progress_observer=record_track)
            finally:
                with self._wohnungserkundung_runtime_lock:
                    self._wohnungserkundung_active_child = None
            if nav in ('error', 'cancel_failed'):
                # Nav2 child state is uncertain: never command anything else.
                return finish('failed', f'child_{nav}')
            if nav == 'success':
                reached += 1
                self._frontiers_visited_status = reached
                attempts.pop(key, None)
                ladder.progress(time.monotonic())
                status.update(goals_reached=reached, ladder=ladder.snapshot())
                continue
            if nav == 'canceled':
                continue   # safety/HOLD/cancel/budget: the loop head decides
            failure = f'nav_{nav}'
            odom = self._self_healing_odom_pose()
            track_len = track.straight_back_distance(
                odom, self._self_healing_track_back_max_m,
                lateral_tolerance_m=self._self_healing_track_lateral_m) if odom else 0.
            action = ladder.failure(time.monotonic(), failure, attempts[key],
                track_back_available=track_len >= self._self_healing_track_back_min_m,
                look_around_available=self._self_healing_look_around_possible(pose))
            status.update(heals=ladder.heals, ladder=ladder.snapshot())
            if action == REQUEST_HELP:
                return finish('blocked', f'help_required:{failure}')
            if action == RETRY:
                time.sleep(self._self_healing_heal_wait_s)
                continue
            blacklist.append((goal.x, goal.y))
            status['deferred_goals'] = len(blacklist)
            if action == LOOK_AROUND:
                self._status_phase = 'self_healing_look_around'
                self._self_healing_look_around(stop_requested)
                status['look_arounds'] += 1
            elif action == TRACK_BACK:
                self._status_phase = 'self_healing_track_back'
                outcome = self._self_healing_track_back(track_len, stop_requested)
                if outcome == 'cancel_failed':
                    return finish('failed', 'track_back_cancel_failed')
                if outcome == 'success':
                    track.consume(track_len)
                status['track_backs'] += 1
                status['last_track_back'] = dict(distance_m=track_len, result=outcome)
            time.sleep(self._self_healing_heal_wait_s)
        return finish('failed', 'ros_shutdown')
