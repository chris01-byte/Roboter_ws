"""Self-healing exploration parent: real node profile and mission loop.

The loop is exercised with fake time, map and Nav2 peers. No device, no
motion: navigation, rotation and BackUp are recorded calls.
"""
import math
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid

from explore.explore_node import ExploreNode
from test_metric_frontier import require_isolated_ros

CONFIG = Path(__file__).resolve().parents[1]/'config'


def _real_node(*extra):
    import rclpy
    rclpy.init(args=['--ros-args', '--params-file', str(CONFIG/'explore_params.yaml'),
                     '--params-file', str(CONFIG/'self_healing_params.yaml'),
                     '-p', 'behavior_tree:=/fake/self_healing.xml', *extra])
    return rclpy


def test_profile_starts_real_node_with_self_healing_owner():
    require_isolated_ros()
    rclpy = _real_node()
    node = ExploreNode()
    try:
        assert node._exploration_strategy == 'self_healing'
        assert node._self_healing_enabled and not node._metric_enabled
        assert node._self_healing_track_back_max_m == pytest.approx(.4)
        assert node._self_healing_track_back_speed == pytest.approx(.05)
        assert node._self_healing_ladder_config['help_after'] == 8
        assert node._self_healing_unknown_speed == pytest.approx(.06)
        assert node._self_healing_speed_pub.topic_name == '/speed_limit'
        node._status_phase = node._status_message = 'idle'
        published = []
        node._status_pub = SimpleNamespace(publish=lambda m: published.append(m.data))
        node._publish_status('idle')
        assert '"strategy":"self_healing"' in published[-1]
        assert '"self_healing":' in published[-1]
    finally:
        node.destroy_node(); rclpy.shutdown()


@pytest.mark.parametrize('extra', [
    ['-p', 'coverage_enabled:=true'],
    ['-p', 'self_healing_track_back_speed_mps:=0.5'],
    ['-p', 'self_healing_unknown_speed_mps:=0.12'],   # an absolute limit must never speed RPP up
    ['-p', 'self_healing_look_around_after:=9', '-p', 'self_healing_track_back_after:=2'],
])
def test_incompatible_or_unsafe_profiles_fail_closed(extra):
    require_isolated_ros()
    rclpy = _real_node(*extra)
    try:
        with pytest.raises(ValueError):
            ExploreNode()
    finally:
        rclpy.shutdown()


# ---------------------------------------------------------------------------
RES = .05


def _room(size=60):
    occupancy = np.full((size, size), -1, dtype=np.int16)
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = occupancy[:, -1] = 100
    return occupancy


def _reveal(occupancy, xy, radius):
    rows, cols = np.mgrid[0:occupancy.shape[0], 0:occupancy.shape[1]]
    near = np.hypot((cols+.5)*RES-xy[0], (rows+.5)*RES-xy[1]) <= radius
    occupancy[near & (occupancy != 100)] = 0


def _grid(occupancy, stamp):
    g = OccupancyGrid()
    g.header.frame_id = 'map'
    g.info.width, g.info.height = occupancy.shape[1], occupancy.shape[0]
    g.info.resolution = RES
    g.info.origin.orientation.w = 1.
    g.data = occupancy.ravel().tolist()
    return g


def parent(monkeypatch, *, reveal_radius=1.2, navigate=None):
    import explore.self_healing_runtime as module
    clock = [100.]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(module.time, 'sleep', lambda d: clock.__setitem__(0, clock[0]+max(.05, d)))
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    n = ExploreNode.__new__(ExploreNode)
    occupancy = _room()
    pose = [1.5, 1.5, 0.]
    _reveal(occupancy, pose, 1.0)
    state = SimpleNamespace(occupancy=occupancy, pose=pose, clock=clock, calls=[],
                            safety=[None], navigate=navigate)
    def refresh_map():
        n._map = _grid(state.occupancy, clock[0])
        n._map_received_at = clock[0]
    refresh_map()
    state.refresh_map = refresh_map
    state.limits = None
    for name, value in dict(
            _self_healing_heal_wait_s=2., _self_healing_source_wait_s=30.,
            _self_healing_map_timeout_s=5., _self_healing_pose_timeout_s=1.5,
            _self_healing_min_gain_m2=.05, _self_healing_blacklist_radius_m=.5,
            _self_healing_min_goal_distance_m=.3, _self_healing_gain_scale=.5,
            _self_healing_completion_checks=3, _self_healing_look_around_rad=math.pi/2,
            _self_healing_rotation_radius_m=.45, _self_healing_track_back_max_m=.4,
            _self_healing_track_back_min_m=.1, _self_healing_track_back_speed=.05,
            _self_healing_track_lateral_m=.03, _goal_timeout_s=150., _replan_period_s=.25,
            _cancel_timeout_s=3., _initial_scan_speed=.08, _initial_scan_timeout=60.,
            _frontiers_remaining=0, _frontiers_visited_status=0, _status_phase='idle',
            _status_message='', _status_state='idle', _global_costmap=None,
            _wohnungserkundung_estop=False, _wohnungserkundung_last_safety_failure=None,
            _nav_child_uncertain=False, _self_healing_enabled=True,
            _self_healing_unknown_speed=.06, _self_healing_unknown_lookahead_m=1.,
            _self_healing_unknown_half_width_m=.25, _self_healing_unknown_fraction=.02,
            _self_healing_speed_state=None, _global_frame='map').items():
        setattr(n, name, value)
    n._self_healing_ladder_config = dict(goal_retries=1, look_around_after=3, track_back_after=5,
                                         help_after=8, max_heals=30, no_progress_timeout_s=600.)
    n._wohnungserkundung_runtime_lock = threading.Lock()
    n._wohnungserkundung_hwt_hold = lambda *_: False
    state_limits = []
    n._self_healing_speed_pub = SimpleNamespace(publish=lambda m: state_limits.append(
        (round(m.speed_limit, 3), m.percentage)))
    state.limits = state_limits
    def safety():
        reason = state.safety[0]
        n._wohnungserkundung_last_safety_failure = reason
        return reason is not None
    n._wohnungserkundung_active_safety_failure = safety
    n._robot_pose_sample = lambda: (tuple(state.pose), 0.)
    n._motion_odom_snapshot = lambda: ((state.pose[0], state.pose[1]), state.pose[2], 0., 0., clock[0])
    def navigate(x, y, timeout, stop_requested=lambda: False, progress_observer=None, **_):
        state.calls.append(('navigate', round(x, 2), round(y, 2)))
        clock[0] += 5.
        if state.navigate is not None:
            return state.navigate(x, y, stop_requested, progress_observer)
        # Drive straight there, recording the own track, then observe.
        start = list(state.pose)
        heading = math.atan2(y-start[1], x-start[0])
        steps = max(1, int(math.dist(start[:2], (x, y))/.02))
        for i in range(1, steps+1):
            state.pose[:] = [start[0]+(x-start[0])*i/steps, start[1]+(y-start[1])*i/steps, heading]
            progress_observer()
        _reveal(state.occupancy, (x, y), reveal_radius)
        refresh_map()
        return 'success'
    n._navigate_to = navigate
    n._rotate_in_place = lambda angle, speed, timeout, stop_requested=None: (
        state.calls.append(('look_around', round(angle, 3))) or ('success', angle))
    n._publish_scan_stop = lambda: None
    n._self_healing_track_back = lambda distance, stop: (
        state.calls.append(('track_back', round(distance, 3))) or 'success')
    n._finish_result = lambda result, count: (setattr(result, 'frontiers_visited', count) or result)
    terminal = []
    goal = SimpleNamespace(is_cancel_requested=False, abort=lambda: terminal.append('abort'),
                           canceled=lambda: terminal.append('cancel'),
                           succeed=lambda: terminal.append('success'))
    return n, state, goal, terminal


def test_explores_closed_room_to_completion(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    result = n._execute_self_healing(goal, 1200., .3)
    assert result.success and terminal == ['success'], n._self_healing_status
    assert n._self_healing_status['reason'] == 'exploration_complete'
    assert n._self_healing_status['goals_reached'] >= 1
    assert not any(c[0] in ('look_around', 'track_back') for c in state.calls)
    assert not np.any(state.occupancy[1:-1, 1:-1] < 0)


def test_persistent_blockage_climbs_the_full_ladder_then_requests_help(monkeypatch):
    def blocked(x, y, stop, record):
        # Drive 0.3 m straight ahead first so an own track exists.
        if not state.calls or len(state.calls) == 1:
            for i in range(16):
                state.pose[:] = [1.5+.02*i, 1.5, 0.]
                record()
        state.refresh_map()  # SLAM keeps publishing while the goal fails
        return 'aborted'
    n, state, goal, terminal = parent(monkeypatch, navigate=blocked)
    # A fresh global costmap without measured obstacles (unknown is allowed).
    n._global_costmap = _grid(np.full(state.occupancy.shape, -1, dtype=np.int16), 0.)
    check = n._self_healing_look_around_possible
    def fresh_check(pose):
        n._global_costmap_received_at = state.clock[0]
        return check(pose)
    n._self_healing_look_around_possible = fresh_check
    result = n._execute_self_healing(goal, 1200., .3)
    assert not result.success and terminal == ['abort']
    assert n._self_healing_status['outcome'] == 'blocked_help_required'
    assert n._self_healing_status['reason'] == 'help_required:nav_aborted'
    kinds = [c[0] for c in state.calls]
    assert 'look_around' in kinds and 'track_back' in kinds
    assert kinds.index('look_around') < kinds.index('track_back')
    track = [c for c in state.calls if c[0] == 'track_back'][0]
    assert .1 <= track[1] <= .4
    actions = [h['action'] for h in n._self_healing_status['ladder']['history']]
    assert actions[0] == 'retry' and actions[-1] == 'help'


def test_active_estop_is_fatal_without_motion(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    state.safety[0] = 'estop_missing_stale_or_active'
    n._wohnungserkundung_estop = True
    result = n._execute_self_healing(goal, 1200., .3)
    assert not result.success and terminal == ['abort']
    assert n._self_healing_status['reason'] == 'estop_active'
    assert state.calls == []


def test_short_source_gap_waits_then_continues_long_gap_requests_help(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    state.safety[0] = 'lidar_missing_stale_or_invalid'
    original = n._wohnungserkundung_active_safety_failure
    def heals_after_two_seconds():
        if state.clock[0] >= 102.:
            state.safety[0] = None
        return original()
    n._wohnungserkundung_active_safety_failure = heals_after_two_seconds
    result = n._execute_self_healing(goal, 1200., .3)
    assert result.success and terminal == ['success']

    n, state, goal, terminal = parent(monkeypatch)
    state.safety[0] = 'vl53_status_missing_stale_or_invalid'
    result = n._execute_self_healing(goal, 1200., .3)
    assert not result.success and terminal == ['abort']
    assert n._self_healing_status['reason'] == 'help_required:vl53_status_missing_stale_or_invalid'
    assert state.calls == []  # never moved while a safety source was missing


def test_uncertain_nav2_child_stops_everything(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch, navigate=lambda *_: 'cancel_failed')
    result = n._execute_self_healing(goal, 1200., .3)
    assert not result.success and n._self_healing_status['reason'] == 'child_cancel_failed'
    assert [c[0] for c in state.calls] == ['navigate']


def test_user_cancel_and_overall_budget(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    goal.is_cancel_requested = True
    n._execute_self_healing(goal, 1200., .3)
    assert terminal == ['cancel'] and state.calls == []
    n, state, goal, terminal = parent(monkeypatch, navigate=lambda *_: 'aborted')
    result = n._execute_self_healing(goal, 6., .3)
    assert not result.success and n._self_healing_status['outcome'] in ('usable_partial',)


def test_look_around_needs_a_fresh_costmap_without_measured_obstacles(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    pose = tuple(state.pose)
    assert not n._self_healing_look_around_possible(pose)            # no costmap
    costs = np.full(state.occupancy.shape, -1, dtype=np.int16)
    n._global_costmap = _grid(costs, 0.)
    n._global_costmap_received_at = state.clock[0]
    assert n._self_healing_look_around_possible(pose)                # unknown only
    state.clock[0] += 10.
    assert not n._self_healing_look_around_possible(pose)            # stale
    n._global_costmap_received_at = state.clock[0]
    costs[30, 36] = 100                                              # 0.3 m beside
    n._global_costmap = _grid(costs, 0.)
    assert not n._self_healing_look_around_possible(pose)


class _Future:
    def __init__(self, value):
        self._value = value
    def result(self):
        return self._value
    def add_done_callback(self, callback):
        callback(self)


def _backup_node(monkeypatch, *, accept=True, status=4, finish=True):
    import explore.self_healing_runtime as module
    clock = [0.]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    n = ExploreNode.__new__(ExploreNode)
    n._self_healing_track_back_speed = .05
    n._cancel_timeout_s = 3.
    sent, canceled = [], []
    class Handle:
        accepted = accept
        def get_result_async(self):
            future = SimpleNamespace(add_done_callback=lambda cb: (
                cb(SimpleNamespace(result=lambda: SimpleNamespace(status=status))) if finish else None))
            return future
        def cancel_goal_async(self):
            canceled.append(1)
    class Client:
        def wait_for_server(self, timeout_sec):
            return True
        def send_goal_async(self, goal):
            sent.append(goal)
            return _Future(Handle())
    n._self_healing_backup_client = Client()
    import threading as real_threading
    class FastEvent(real_threading.Event):
        def wait(self, timeout=None):
            clock[0] += timeout or 0.
            return super().wait(0)
    monkeypatch.setattr(module.threading, 'Event', FastEvent)
    return n, sent, canceled, clock


def test_track_back_sends_bounded_backup_goal(monkeypatch):
    n, sent, canceled, _ = _backup_node(monkeypatch)
    assert n._self_healing_track_back(.3, lambda: False) == 'success'
    goal = sent[0]
    assert goal.target.x == pytest.approx(.3) and goal.speed == pytest.approx(.05)
    assert goal.time_allowance.sec == int(.3/.05+10.)
    assert canceled == []


def test_track_back_rejected_or_stopped(monkeypatch):
    n, sent, canceled, _ = _backup_node(monkeypatch, accept=False)
    assert n._self_healing_track_back(.3, lambda: False) == 'rejected'
    n, sent, canceled, _ = _backup_node(monkeypatch, finish=False)
    assert n._self_healing_track_back(.3, lambda: True) == 'cancel_failed'
    assert canceled == [1]
    assert n._self_healing_track_back(0., lambda: False) == 'unavailable'


def test_speed_limited_to_006_while_corridor_ahead_is_unmapped(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    # Start inside the known disc but facing the unknown part of the room.
    state.pose[:] = [1.5, 1.5, 0.]
    state.occupancy[:, 40:] = -1
    state.refresh_map()
    assert n._self_healing_govern_speed(force=True) == pytest.approx(.06)
    assert state.limits[-1] == (.06, False)          # absolute, not percentage
    # Facing the mapped area: limit released (0.0 = Nav2 NO_SPEED_LIMIT).
    state.pose[:] = [1.5, 1.5, math.pi]
    assert n._self_healing_govern_speed(force=True) == 0.
    assert state.limits[-1] == (0., False)
    # Stale map: fail-safe slow.
    state.clock[0] += 10.
    assert n._self_healing_govern_speed(force=True) == pytest.approx(.06)
    # Governor fault never becomes speed.
    n._robot_pose_sample = lambda: 1/0
    assert n._self_healing_govern_speed(force=True) == pytest.approx(.06)


def test_mission_limits_speed_in_unknown_and_releases_it_at_the_end(monkeypatch):
    n, state, goal, terminal = parent(monkeypatch)
    result = n._execute_self_healing(goal, 1200., .3)
    assert result.success
    assert (.06, False) in state.limits          # approached unmapped frontiers slowly
    assert state.limits[-1] == (0., False)       # released for later users
