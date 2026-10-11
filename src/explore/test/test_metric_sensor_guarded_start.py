"""Actual parent start decisions on raw unknown maps; no robot/SLAM claim."""
import copy
import math

import numpy as np
import pytest

from explore.metric_frontier import MetricTaskPolicy
from explore.sensor_motion_guard import scan_sweep_clear
from test_metric_map_lifecycle import status
from test_metric_progress import parent_fixture, scan


def sensor_start(monkeypatch):
    node, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_unknown_space_policy = 'sensor_guarded'
    node._metric_start_strategy = 'sensor_scan_first'
    node._initial_scan_enabled = True
    node._initial_scan_angle = 2*math.pi
    node._initial_scan_timeout = 280.
    # Reproduce the bootstrap failure: unknown beside/under the turning body.
    raw = np.asarray(grid.data).reshape(100, 100).copy()
    col, row = node._world_to_grid(.05, .05, grid.info)
    raw[row-4:row+5, col-4:col+5] = -1
    grid = copy.deepcopy(grid)
    grid.data = raw.ravel().tolist()
    grid.header.stamp.nanosec = 20_000_000
    node._on_map(grid)
    node._on_metric_map_status(status(grid, accepted=3, observed=3, when=100.03))
    return node, grid, clock, parent, terminal


def test_unknown_bootstrap_scan_precedes_any_goal_search_without_changing_map(monkeypatch):
    node, grid, _, _, _ = sensor_start(monkeypatch)
    raw = list(grid.data)
    # Same raw sources: old policy rejects the sweep, sensor policy admits it.
    node._metric_unknown_space_policy = 'observed_only'
    assert not node._metric_scan_geometry_ready(node._metric_inputs())
    node._metric_unknown_space_policy = 'sensor_guarded'
    inputs = node._metric_inputs()
    assert node._metric_scan_geometry_ready(inputs)
    node._metric_select = lambda *_: pytest.fail('No frontier search before a ready start scan')
    decision, candidates = node._metric_start_decision(inputs, MetricTaskPolicy(.6, 30., 2), .3, True)
    assert decision['selected_motion'] == 'full_scan' and not candidates
    assert decision['unobserved_cells_in_scope'] > 0
    assert node._metric_public_inputs(inputs) is inputs
    assert list(grid.data) == raw


def test_actual_parent_attempts_full_turn_before_search_and_does_not_fake_completion(monkeypatch):
    node, grid, _, parent, terminal = sensor_start(monkeypatch)
    raw = list(grid.data)
    calls = []
    def rotate(*, stop_requested, **_):
        assert not calls and not stop_requested()
        calls.append('scan')
        return 'success', 2*math.pi
    def select(*_):
        assert calls == ['scan']
        calls.append('search')
        node._frontier_rank_stats = {}
        parent.is_cancel_requested = True
        return []
    node._scan_in_place = rotate  # transport peer; parent/inputs/decision are real
    node._metric_select = select
    result = node._execute_metric_frontier(parent, 10., .3)
    assert calls == ['scan', 'search'] and not result.success
    assert node._metric_status['scan_progress_rad'] == pytest.approx(2*math.pi)
    assert node._metric_status['observations'] == 0  # a turn is not a measured map gain
    assert list(grid.data) == raw
    assert terminal != ['success']


@pytest.mark.parametrize('fault', ['stale_receipt', 'stale_stamp', 'invalid_scan', 'missing_scan', 'missing_tf'])
def test_sensor_loss_rejects_unknown_motion_even_with_cached_geometry(monkeypatch, fault):
    node, _, _, _, _ = sensor_start(monkeypatch)
    node._metric_inputs()  # populate the pure geometry cache
    actual = node._door_lidar_scan_snapshot()
    if fault == 'stale_receipt':
        actual['received_at'] -= 1.
    if fault == 'stale_stamp':
        actual['key'] = (99, 0, 360)
    if fault == 'invalid_scan':
        actual['ranges'][:] = np.nan
    if fault == 'missing_tf':
        node._door_lidar_mount = lambda _: None
    node._door_lidar_scan_snapshot = lambda: None if fault == 'missing_scan' else actual
    with pytest.raises(ValueError):
        node._metric_inputs()


@pytest.mark.parametrize('angle', [0., math.pi/2, math.pi, -math.pi/2])
def test_measured_hits_around_the_turning_body_block_scan_even_when_raw_map_unknown(angle):
    actual = scan()
    actual['ranges'][round((angle+math.pi)/(math.pi/180)) % 360] = .35
    assert not scan_sweep_clear(actual, (0., 0., 0.), (-.13, .33, -.25, .25))
    assert scan_sweep_clear(scan(), (.245, 0., math.pi/2), (-.13, .33, -.25, .25))


@pytest.mark.parametrize('raster', ['raw', 'costmap'])
def test_occupied_cell_is_not_exempted_by_unknown_policy(monkeypatch, raster):
    node, grid, clock, _, _ = sensor_start(monkeypatch)
    changed = copy.deepcopy(grid if raster == 'raw' else node._global_costmap)
    col, row = node._world_to_grid(.25, .05, changed.info)
    changed.data[row*changed.info.width+col] = 100
    clock[0] = 10.04
    changed.header.stamp.nanosec = 30_000_000
    if raster == 'raw':
        node._on_map(changed)
        node._on_metric_map_status(status(changed, accepted=4, observed=4, when=100.04))
    else:
        node._on_global_costmap(changed)
    assert not node._metric_scan_geometry_ready(node._metric_inputs())


@pytest.mark.parametrize('cause', ['encoder_fault', 'vl53_sensor_frame_stale', 'user_cancel'])
def test_actual_parent_keeps_sensor_stop_and_cancel_before_any_rotation(monkeypatch, cause):
    node, _, _, parent, terminal = sensor_start(monkeypatch)
    node._scan_in_place = lambda **_: pytest.fail('Unsafe/canceled start cannot rotate')
    if cause == 'user_cancel':
        parent.is_cancel_requested = True
    else:
        node._metric_operating_snapshot = lambda **_: dict(safe=False, first_rejecting_predicate=cause)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal != ['success']


def test_scan_interruption_retains_actual_sensor_cause(monkeypatch):
    node, _, _, parent, _ = sensor_start(monkeypatch)
    def rotate(*, stop_requested, **_):
        node._metric_operating_snapshot = lambda **_: dict(safe=False, first_rejecting_predicate='encoder_fault')
        assert stop_requested()
        return 'interrupted', .1
    node._scan_in_place = rotate
    node._execute_metric_frontier(parent, 10., .3)
    assert node._metric_status['first_trigger']['reason'] == 'encoder_fault'
    assert node._metric_status['scan_progress_rad'] == pytest.approx(.1)


def test_complete_chassis_route_can_leave_unknown_start_but_keeps_scope_and_obstacles(monkeypatch):
    node, _, _, _, _ = sensor_start(monkeypatch)
    node._metric_unknown_space_policy = 'observed_only'
    assert node._metric_route(node._metric_inputs(), (.85, .05), 0.) is None
    node._metric_unknown_space_policy = 'sensor_guarded'
    inputs = node._metric_inputs()
    assert node._metric_route(inputs, (.85, .05), 0.) is not None
    assert node._metric_route(inputs, (50., .05), 0.) is None


def test_blocked_round_turn_falls_back_to_goal_search(monkeypatch):
    node, _, _, _, _ = sensor_start(monkeypatch)
    actual = node._door_lidar_scan_snapshot()
    actual['ranges'][180] = .37  # outside current front, inside full turning sweep
    node._door_lidar_scan_snapshot = lambda: actual
    calls = []
    node._metric_select = lambda *_: calls.append('search') or []
    decision, _ = node._metric_start_decision(node._metric_inputs(), MetricTaskPolicy(.6, 30., 2), .3, True)
    assert not decision['scan_admissible'] and decision['selected_motion'] != 'full_scan'
    assert calls == ['search']


def test_actual_ros_node_loads_new_policy_and_keeps_it_readonly():
    import json
    import rclpy
    from rclpy.parameter import Parameter
    from explore.explore_node import ExploreNode
    from test_metric_frontier import require_isolated_ros
    require_isolated_ros()
    values = dict(exploration_strategy='metric_frontier',
        metric_execution_mode='lab_slots',
        metric_unknown_space_policy='sensor_guarded', metric_start_strategy='sensor_scan_first',
        metric_self_body_enabled=False, metric_start_egress_enabled=False,
        wohnungserkundung_accessible_scope_verified=True, wohnungserkundung_scope_id='scope-test',
        wohnungserkundung_scope_polygon_xy=[-1., -1., 3., -1., 3., 3., -1., 3.],
        metric_session_id='metric-test', metric_scope_map_fingerprint='a'*64,
        portal_crossing_enabled=False, coverage_enabled=False, overall_timeout_s=60.,
        region_graph_shadow_enabled=False, behavior_tree='/fake/no_recovery.xml')
    rclpy.init(args=['--ros-args', *[v for key, value in values.items()
                                   for v in ('-p', key+':='+json.dumps(value))]])
    node = None
    try:
        node = ExploreNode()
        assert node._metric_sensor_guarded()
        result = node.set_parameters([Parameter('metric_unknown_space_policy', value='observed_only')])
        assert not result[0].successful and node._metric_sensor_guarded()
        result = node.set_parameters([Parameter('metric_execution_mode', value='continuous')])
        assert not result[0].successful and node._metric_execution_mode=='lab_slots'
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()
