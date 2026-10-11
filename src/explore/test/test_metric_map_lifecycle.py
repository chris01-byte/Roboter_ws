"""AP-02: real Explorer callbacks, rasters and planner bindings, no devices."""
import copy
import json
import threading
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String

from explore.explore_node import ExploreNode
from explore.map_status_adapter import MapManagerStatusCorrelator
from explore.portal_source_adapter import raw_map_portal_source_from_values
from test_metric_frontier import body_input_fixture, grid, egress_fixture, candidate


def source(g):
    return raw_map_portal_source_from_values(**ExploreNode._metric_grid_values(g))


def status(g, *, accepted=1, observed=1, when=100., age=0.):
    identity = source(g)
    return String(data=json.dumps(dict(schema_version=1, time=when,
        map=dict(available=True, snapshot_available=True, age_seconds=age,
                 summary=dict(frame_id=g.header.frame_id,
                              fingerprint=identity.fingerprint,
                              source_stamp_ns=identity.source_stamp_ns)),
        counters=dict(accepted_maps=accepted, observed_maps=observed))))


def runtime(monkeypatch, *, placement_shadow=False, body_reference=None):
    n = body_input_fixture(monkeypatch, 10.)
    del n._metric_matches_status  # exercise the product matcher, not the old fixture override
    n._metric_enabled = True
    n._global_costmap = None
    n.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=100_100_000_000))
    n._metric_raw = n._metric_joined = n._metric_correlation = None
    n._metric_status_at = n._metric_pending_since = None
    n._metric_correlator = MapManagerStatusCorrelator('metric', 'map')
    n._wohnungserkundung_scope_id = n._metric_scope.scope_id
    n._wohnungserkundung_scope_vertices = n._metric_scope.vertices
    n._metric_scope = None
    n._metric_start_egress_enabled = True
    n._metric_egress = n._metric_egress_identity = None
    n._metric_egress_expired = n._metric_body_anchor_expired = False
    if body_reference is not None:
        n._metric_body_reference = lambda: body_reference
    n._metric_bounds = (-.13, .33, -.25, .25)
    n._metric_active = n._metric_active_context = None
    n._metric_nav_path = n._metric_nav_path_at = n._metric_plan_after_ns = None
    g = grid()
    g.info.width = g.info.height = 100
    a = np.zeros((100, 100), dtype=int)
    a[18:23, 8] = -1
    if placement_shadow:
        from explore.metric_frontier import self_body_unknown_mask
        a[:] = 0
        shadow = self_body_unknown_mask(g, np.full(a.shape,-1), (.05,.05,0.),
                                        (.245,0.,np.pi/2))
        a[shadow] = -1
    g.data = a.ravel().tolist()
    n._metric_scope_binding = source(g).fingerprint
    n._on_map(g)
    cost = copy.deepcopy(g)
    cost.data = [0] * 10000
    n._on_global_costmap(cost)
    n._on_metric_map_status(status(g))
    assert n._metric_fault is None
    n._metric_inputs()
    return n, g


@pytest.mark.parametrize('raster', ['raw', 'costmap', 'both'])
@pytest.mark.parametrize('change', ['height', 'width', 'origin', 'growth_origin', 'resolution', 'yaw'])
def test_raster_transition_expires_inventory_before_array_operation(monkeypatch, raster, change):
    n, g = runtime(monkeypatch)
    previous = n._metric_egress
    masks = [e.unknown.copy() for e in previous]
    def changed(old):
        new = copy.deepcopy(old)
        new.header.stamp.nanosec = 10_000_000
        a = np.asarray(new.data).reshape(old.info.height, old.info.width)
        if change in ('height', 'growth_origin'):
            new.info.height += 1
            a = np.pad(a, ((0, 1), (0, 0)), constant_values=-1)
        if change == 'width':
            new.info.width += 1
            a = np.pad(a, ((0, 0), (0, 1)), constant_values=-1)
        if change in ('origin', 'growth_origin'):
            new.info.origin.position.y -= .1
        if change == 'resolution':
            new.info.resolution = .11
        if change == 'yaw':
            new.info.origin.orientation.z = .1
            new.info.origin.orientation.w = np.sqrt(.99)
        new.data = a.ravel().tolist()
        return new
    if raster in ('raw', 'both'):
        g = changed(g)
        n._on_map(g)
        n._on_metric_map_status(status(g, accepted=2, observed=2, when=100.02))
    if raster in ('costmap', 'both'):
        n._on_global_costmap(changed(n._global_costmap))
    inputs = n._metric_inputs()
    assert n._metric_egress is previous
    assert n._metric_egress_expired
    assert all(not e.valid for e in previous)
    for mask, evidence in zip(masks, previous):
        assert np.array_equal(mask, evidence.unknown)
    assert np.array_equal(n._metric_seed_mask(inputs), inputs[4])
    # A later valid update cannot re-anchor the original exemption.
    g2 = copy.deepcopy(g)
    g2.header.stamp.nanosec += 10_000_000
    n._on_map(g2)
    n._on_metric_map_status(status(g2, accepted=2 if raster != 'costmap' else 1,
                                  observed=3 if raster != 'costmap' else 2, when=100.03))
    n._metric_inputs()
    assert n._metric_egress is previous and n._metric_egress_expired


@pytest.mark.parametrize('change', ['session', 'map_id', 'frame'])
def test_context_transition_never_reanchors_egress(change):
    n, inputs = egress_fixture()
    context = inputs[1].context
    updated = replace(context, **{dict(session='session_id', map_id='map_id', frame='frame_id')[change]: 'new'})
    inputs[1] = replace(inputs[1], context=updated)
    inventory = n._metric_egress[0].unknown.copy()
    n._metric_prepare_egress(inputs)
    assert n._metric_egress_expired and not n._metric_egress[0].valid
    assert np.array_equal(inventory, n._metric_egress[0].unknown)


def test_direct_egress_check_rejects_incompatible_arrays():
    n, _ = egress_fixture()
    valid, reason = n._metric_egress[0].check_trajectory(
        [(0., 0., 0.)], np.zeros((41, 80)), np.ones((41, 80), bool), n._world_to_grid)
    assert not valid and reason == 'start_egress_raster_mismatch'


def test_delayed_callback_cannot_replace_generic_map_or_refresh_age(monkeypatch):
    n, g = runtime(monkeypatch)
    later = copy.deepcopy(g)
    later.header.stamp.nanosec = 10_000_000
    later.data[9999] = 100
    n._on_map(later)
    received = n._map_received_at
    n._on_map(g)
    assert n._map is later and n._metric_raw[0] is later
    assert n._map_received_at == received


def test_same_stamp_different_content_latches_fault(monkeypatch):
    n, g = runtime(monkeypatch)
    conflict = copy.deepcopy(g)
    conflict.data[9999] = 100
    n._on_map(conflict)
    assert n._map is g
    assert 'map_conflicting_same_stamp' in n._metric_fault
    n._on_map(g)
    with pytest.raises(ValueError, match='map_conflicting_same_stamp'):
        n._metric_inputs(active=True)


@pytest.mark.parametrize('raster', ['raw', 'costmap'])
def test_transient_resolution_change_cannot_restore_old_work_or_mask(monkeypatch, raster):
    n, g = runtime(monkeypatch)
    context = n._metric_work_context()
    original = g if raster == 'raw' else n._global_costmap
    changed = copy.deepcopy(original)
    changed.info.resolution = .11
    changed.header.stamp.nanosec = 10_000_000
    callback = n._on_map if raster == 'raw' else n._on_global_costmap
    callback(changed)
    assert n._metric_egress_expired and not n._metric_egress[0].valid
    returned = copy.deepcopy(original)
    returned.header.stamp.nanosec = 20_000_000
    callback(returned)
    assert not n._metric_work_is_current(context)
    assert n._metric_egress_expired


def test_costmap_conflicting_same_stamp_cannot_reopen_obstacle(monkeypatch):
    n, _ = runtime(monkeypatch)
    old = n._global_costmap
    conflict = copy.deepcopy(old)
    conflict.data[9999] = 100
    n._on_global_costmap(conflict)
    assert n._global_costmap is old
    with pytest.raises(ValueError, match='costmap_conflicting_same_stamp'):
        n._metric_inputs(active=True)


@pytest.mark.parametrize('order', ['raw_first', 'status_first'])
def test_new_content_requires_exact_status_join_then_valid_update_is_processed(monkeypatch, order):
    n, g = runtime(monkeypatch)
    new = copy.deepcopy(g)
    new.header.stamp.nanosec = 10_000_000
    new.data[9999] = 100
    callbacks = [lambda: n._on_map(new), lambda: n._on_metric_map_status(
        status(new, accepted=2, observed=2, when=100.02))]
    if order == 'status_first':
        callbacks.reverse()
    callbacks[0]()
    for active in (False, True):
        with pytest.raises(ValueError, match='map_status_join_pending'):
            n._metric_inputs(active=active)
    callbacks[1]()
    inputs = n._metric_inputs(active=True)
    assert inputs[0] is new and inputs[1].map_revision == 2
    assert not inputs[3][99, 99] and not inputs[4][99, 99]
    assert n._metric_fault is None


def test_identical_content_pending_keeps_original_exact_join_and_deadline(monkeypatch):
    n, g = runtime(monkeypatch)
    new = copy.deepcopy(g)
    new.header.stamp.nanosec = 10_000_000
    n._on_map(new)
    inputs = n._metric_inputs(active=True)
    assert inputs[0] is g and inputs[1].source_stamp_ns == 100_000_000_000
    with pytest.raises(ValueError, match='map_status_join_pending'):
        n._metric_inputs()
    import explore.metric_frontier_runtime as module
    monkeypatch.setattr(module.time, 'monotonic', lambda: 11.28)
    with pytest.raises(ValueError, match='map_status_join_pending'):
        n._metric_inputs(active=True)


def test_delayed_status_cannot_replace_current_join(monkeypatch):
    n, g = runtime(monkeypatch)
    first = status(g)
    new = copy.deepcopy(g)
    new.header.stamp.nanosec = 10_000_000
    n._on_map(new)
    n._on_metric_map_status(status(new, observed=2, when=100.02))
    correlation, received = n._metric_correlation, n._metric_status_at
    n._on_metric_map_status(first)
    assert n._metric_correlation is correlation and n._metric_status_at == received
    assert n._metric_inputs()[0] is new


@pytest.mark.parametrize('reset', ['unavailable', 'counter', 'frame'])
def test_actual_status_epoch_change_stays_terminal_until_explicit_new_session(monkeypatch, reset):
    n, g = runtime(monkeypatch)
    msg = json.loads(status(g, when=101.).data)
    if reset == 'unavailable':
        msg['map'] = dict(available=False, snapshot_available=False, summary=None, age_seconds=None)
        msg['counters'] = dict(accepted_maps=0, observed_maps=0)
    if reset == 'counter':
        newer = copy.deepcopy(g)
        newer.data[9999] = 100
        newer.header.stamp.nanosec = 10_000_000
        n._on_map(newer)
        n._on_metric_map_status(status(newer, accepted=2, observed=2, when=100.02))
    if reset == 'frame':
        msg['map']['summary']['frame_id'] = 'foreign'
    context = n._metric_work_context()
    n._on_metric_map_status(String(data=json.dumps(msg)))
    assert n._metric_fault and not n._metric_work_is_current(context)
    n._on_metric_map_status(status(g, when=102.))
    with pytest.raises(ValueError, match='map_status_'):
        n._metric_inputs(active=True)


@pytest.mark.parametrize('lost', ['raw', 'status', 'costmap', 'pose', 'scan'])
def test_required_source_loss_rejects_and_fresh_followup_is_usable(monkeypatch, lost):
    n, _ = runtime(monkeypatch)
    if lost == 'raw':
        original = n._metric_raw
        n._metric_raw = (*original[:2], 4.)
        restore = lambda: setattr(n, '_metric_raw', original)
    elif lost == 'status':
        original = n._metric_status_at
        n._metric_status_at = 4.
        restore = lambda: setattr(n, '_metric_status_at', original)
    elif lost == 'costmap':
        original = n._global_costmap_received_at
        n._global_costmap_received_at = 4.
        restore = lambda: setattr(n, '_global_costmap_received_at', original)
    elif lost == 'pose':
        original = n._robot_pose_sample
        n._robot_pose_sample = lambda: (None, None)
        restore = lambda: setattr(n, '_robot_pose_sample', original)
    else:
        original = n._door_lidar_scan_snapshot
        n._door_lidar_scan_snapshot = lambda: None
        restore = lambda: setattr(n, '_door_lidar_scan_snapshot', original)
    with pytest.raises(ValueError):
        n._metric_inputs(active=True)
    restore()
    assert len(n._metric_inputs(active=True)) == 7


def test_map_processing_time_consumes_freshness_window(monkeypatch):
    n, _ = runtime(monkeypatch)
    import explore.metric_frontier_runtime as module
    clock = [10.02]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    n._metric_self_body_enabled = False
    def delayed_pose():
        clock[0] = 15.01
        return (.05, .05, 0.), 0.
    n._robot_pose_sample = delayed_pose
    # Costmap is newer; only the original raw/status window has expired.
    n._global_costmap_received_at = 11.
    with pytest.raises(ValueError, match='stale_after_processing'):
        n._metric_inputs()


@pytest.mark.parametrize('lost,selected_age,processing', [('pose', 0., .81),
    ('scan', 0., .51), ('scan', .49, .02)])
@pytest.mark.parametrize('cached', [False, True])
def test_final_mask_work_cannot_extend_pose_or_scan_freshness(monkeypatch, lost, selected_age, processing, cached):
    n, _ = runtime(monkeypatch)
    import explore.metric_frontier_runtime as module
    clock = [10.02]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    scan = dict(received_at=10.02-selected_age, frame_id='laser_frame', key=(100, 20000000, 720))
    n._door_lidar_scan_snapshot = lambda: scan
    n._metric_status = {}
    n._status_phase = 'metric_navigation'
    n._wohnungserkundung_active_child = object()
    raw_stamp = n._metric_raw[1].source_stamp_ns
    if lost == 'pose':
        n._metric_self_body_enabled = False
    if not cached:
        n._metric_known_geometry_cache = None
    original = n._metric_known_geometry
    def delayed_mask(*args, **kwargs):
        result = original(*args, **kwargs)
        clock[0] += processing
        return result
    # Delay the current geometry boundary, including a cache hit. Cached
    # arithmetic never exempts the selected pose/scan from the final ages.
    n._metric_known_geometry = delayed_mask
    with pytest.raises(ValueError, match=lost + '_stale_after_processing'):
        n._metric_inputs(active=True)
    receipt = n._metric_status['geometry_snapshot_rejection']
    assert receipt['reason'] == ('pose' if lost == 'pose' else 'self_body_scan') + '_stale_after_processing'
    assert receipt['selected_age_s'] == pytest.approx(selected_age)
    assert receipt['processing_elapsed_s'] == pytest.approx(processing)
    assert receipt['final_age_s'] == pytest.approx(selected_age+processing)
    assert receipt['limit_s'] == (.8 if lost == 'pose' else .5)
    assert receipt['checked_at'] == pytest.approx(clock[0])
    assert receipt['phase'] == 'metric_navigation' and receipt['active'] and receipt['active_child']
    assert n._metric_raw[1].source_stamp_ns == raw_stamp
    assert scan['received_at'] == pytest.approx(10.02-selected_age)
    if lost == 'scan':
        assert receipt['age_basis'] == 'scan_callback_receipt'
        assert receipt['scan_key'] == scan['key']
        assert receipt['received_at'] == scan['received_at']


def test_stamp_age_expires_during_processing_despite_recent_dds_receipt(monkeypatch):
    n, _ = runtime(monkeypatch)
    clock = iter((104_990_000_000, 104_990_000_000, 105_010_000_000))
    n.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=next(clock)))
    with pytest.raises(ValueError, match='map_stamp_stale_after_processing'):
        n._metric_inputs()


def test_harmless_content_and_growth_keep_work_context_and_valid_goal(monkeypatch):
    n, g = runtime(monkeypatch)
    # Goal proof uses normal observed free space; no start-unknown exception.
    g = copy.deepcopy(g)
    g.data = [0] * 10000
    g.header.stamp.nanosec = 10_000_000
    n._on_map(g)
    n._on_metric_map_status(status(g, accepted=2, observed=2, when=100.02))
    inputs = n._metric_inputs()
    n._metric_start_egress_enabled = False
    context = n._metric_work_context()
    target = (.65, .05)
    route = n._metric_route(inputs, target, 0.)
    assert route is not None
    new = copy.deepcopy(g)
    new.info.height = 101
    new.data = list(g.data) + [-1] * 100
    new.header.stamp.nanosec = 20_000_000
    n._on_map(new)
    n._on_metric_map_status(status(new, accepted=3, observed=3, when=100.03))
    assert n._metric_work_is_current(context)
    assert n._metric_route(n._metric_inputs(active=True), target, 0.) is not None


def path_for(target):
    path = Path()
    path.header.frame_id = 'map'
    path.header.stamp.sec = 100
    p = PoseStamped()
    p.pose.position.x, p.pose.position.y = target.x, target.y
    path.poses = [p]
    return path


@pytest.mark.parametrize('transition', ['session', 'resolution', 'fault'])
def test_late_plan_callback_cannot_revive_work_in_new_context(monkeypatch, transition):
    n, g = runtime(monkeypatch)
    n._metric_active = candidate()
    n._metric_active_context = n._metric_work_context()
    n._metric_plan_after_ns = 99_000_000_000
    path = path_for(n._metric_active)
    n._on_metric_nav_plan(path)
    assert n._metric_nav_path is path
    if transition == 'session':
        n._metric_correlation = replace(n._metric_correlation,
            context=replace(n._metric_correlation.context, session_id='next-session'))
    elif transition == 'resolution':
        newer = copy.deepcopy(g)
        newer.info.resolution = .2
        newer.header.stamp.nanosec = 10_000_000
        n._on_map(newer)
    else:
        n._metric_fault = 'map_epoch_changed'
    late = path_for(n._metric_active)
    n._on_metric_nav_plan(late)
    assert n._metric_nav_path is path


def test_already_finished_planner_result_is_ignored_after_context_change(monkeypatch):
    n, _ = runtime(monkeypatch)
    import explore.metric_frontier_runtime as module
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    n._metric_controller_contract = lambda stop: True
    cancels = []
    result = SimpleNamespace(done=lambda: True, result=lambda: SimpleNamespace(
        status=4, result=SimpleNamespace(path=path_for(candidate()))))
    def get_result():
        n._metric_fault = 'new-map-epoch'
        return result
    handle = SimpleNamespace(accepted=True, get_result_async=get_result,
                             cancel_goal_async=lambda: cancels.append(True))
    accept = SimpleNamespace(done=lambda: True, result=lambda: handle)
    n._metric_planner = SimpleNamespace(wait_for_server=lambda **_: True,
                                       send_goal_async=lambda _: accept)
    from builtin_interfaces.msg import Time
    n.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(
        nanoseconds=100_000_000_000, to_msg=lambda: Time(sec=100)))
    path, reason = n._metric_request_nav_plan(candidate(), lambda: False)
    assert path is None and reason == 'nav2_plan_timeout_or_stop'
    assert cancels == [True]


def test_map_callback_waits_for_atomic_evidence_selection(monkeypatch):
    n, g = runtime(monkeypatch)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    original = n._metric_inputs_locked
    def evaluate(active):
        entered.set()
        assert release.wait(2.)
        return original(active)
    n._metric_inputs_locked = evaluate
    outcomes = []
    worker = threading.Thread(target=lambda: outcomes.append(n._metric_inputs()))
    worker.start()
    assert entered.wait(2.)
    new = copy.deepcopy(g)
    new.header.stamp.nanosec = 10_000_000
    callback = threading.Thread(target=lambda: (n._on_map(new), finished.set()))
    callback.start()
    assert not finished.wait(.02)
    release.set()
    worker.join(2.)
    callback.join(2.)
    assert not worker.is_alive() and not callback.is_alive()
    assert outcomes[0][0] is g and n._metric_raw[0] is new


@pytest.mark.parametrize('update', ['growth', 'source_loss', 'epoch', 'resolution'])
def test_real_parent_loop_revalidates_child_and_ignores_late_success(monkeypatch, update):
    """Only the absent hardware/action peer is doubled; parent/map/route are real."""
    n, g = runtime(monkeypatch)
    import explore.metric_frontier_runtime as module
    monkeypatch.setattr(module.rclpy, 'ok', lambda: True)
    g = copy.deepcopy(g)
    g.data = [0] * 10000
    g.header.stamp.nanosec = 10_000_000
    n._on_map(g)
    n._on_metric_map_status(status(g, accepted=2, observed=2, when=100.02))
    n._metric_self_body_enabled = n._metric_start_egress_enabled = False
    for key, value in dict(_overall_timeout_s=100., _goal_timeout_s=30.,
            _frontier_revisit_radius=.6, _metric_retry_s=30., _metric_retry_limit=2,
            _max_frontier_goals=1, _max_failed_goals=2, _initial_scan_enabled=False,
            _metric_start_strategy='configured_scan', _blacklist=[],
            _frontier_rank_stats={}, _frontiers_remaining=1,
            _visited_frontier_goals=[], _replan_period_s=0., _hwt_hold_announced=False,
            _wohnungserkundung_active_child=None).items():
        setattr(n, key, value)
    n._wohnungserkundung_runtime_lock = threading.Lock()
    n._wohnungserkundung_hwt_hold = lambda: False
    n._metric_confirm_stop = lambda *_: True
    n._metric_operating_snapshot = lambda: dict(safe=True, first_rejecting_predicate=None)
    n._finish_result = lambda result, _: result
    target = candidate(xy=(.65, .05))
    def select(inputs, policy, _):
        key = policy.identify(target.frontier_xy)
        return [replace(target, task_id=key)]
    n._metric_select = select
    path = path_for(target)
    path.poses[-1].pose.orientation.w = 1.
    start = PoseStamped()
    start.pose.position.x = start.pose.position.y = .05
    path.poses.insert(0, start)
    n._metric_request_nav_plan = lambda *_: (path, None)
    n._prealign_to_goal = lambda *_, **__: ('skipped',)
    stopped = []
    def navigate(*_, stop_requested, **__):
        if update == 'source_loss':
            n._metric_raw = (*n._metric_raw[:2], 4.)
        elif update == 'epoch':
            n._metric_fault = 'map_epoch_changed'
        else:
            newer = copy.deepcopy(g)
            newer.header.stamp.nanosec = 20_000_000
            if update == 'growth':
                newer.info.height = 101
                newer.data = list(g.data) + [-1] * 100
            else:
                newer.info.resolution = .11
            n._on_map(newer)
            n._on_metric_map_status(status(newer, accepted=3, observed=3, when=100.03))
        stopped.append(stop_requested())
        n._robot_pose_sample = lambda: ((target.x, target.y, target.yaw), 0.)
        return 'success'  # deliberately late success, even after stop
    n._navigate_to = navigate
    terminal = []
    parent = SimpleNamespace(is_cancel_requested=False, publish_feedback=lambda _: None,
                             abort=lambda: terminal.append('abort'), canceled=lambda: terminal.append('cancel'))
    result = n._execute_metric_frontier(parent, 100., .3)
    assert stopped == [update != 'growth']
    assert n._frontiers_visited_status == (1 if update == 'growth' else 0)
    if update == 'growth':
        assert n._metric_status['chain'][0]['decision'] == 'arrival_without_observation'
        assert n._metric_status['chain'][0]['observed_cells'] == 0
    else:
        assert not n._metric_status['chain']
        assert 'failed' in result.message
    assert terminal == ['abort']  # no full-apartment completion claim


@pytest.mark.parametrize('order', ['raw_first', 'status_first'])
def test_actual_map_producer_duplicate_growth_and_delayed_input_share_revision_contract(monkeypatch, order):
    from robot_map_manager.robot_map_manager_node import RobotMapManager
    from robot_map_manager.map_core import RawDuplicateGuard
    n, g = runtime(monkeypatch)
    manager = RobotMapManager.__new__(RobotMapManager)
    manager.raw_duplicate_guard = RawDuplicateGuard(window_s=1.)
    manager._latest_map = manager._latest_fingerprint = None
    for field in ('accepted_maps', 'observed_maps', 'duplicate_maps', 'early_duplicate_maps', 'rejected_maps'):
        setattr(manager, '_' + field, 0)
    manager._publish_status = lambda **_: None
    manager.get_logger = lambda: SimpleNamespace(warning=lambda _: None)
    import explore.metric_frontier_runtime as module
    clock = [10.02]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    def publish(snapshot):
        msg = status(snapshot, accepted=manager._accepted_maps,
                     observed=manager._observed_maps, when=100.+clock[0]-10.)
        callbacks = [lambda: n._on_map(snapshot), lambda: n._on_metric_map_status(msg)]
        if order == 'status_first':
            callbacks.reverse()
        for callback in callbacks:
            callback()
        assert n._metric_fault is None
    manager._on_map(g, '/map')
    publish(g)
    # Exact duplicate after the early duplicate window must not invent a revision.
    clock[0] = 12.02
    manager._on_map(g, '/map')
    assert manager._observed_maps == manager._accepted_maps == 1
    publish(g)
    newer = copy.deepcopy(g)
    newer.header.stamp.nanosec = 10_000_000
    manager._on_map(newer, '/map')
    assert (manager._accepted_maps, manager._observed_maps) == (1, 2)
    publish(newer)
    grown = copy.deepcopy(newer)
    grown.info.height = 101
    grown.data = list(g.data) + [-1] * 100
    grown.header.stamp.nanosec = 20_000_000
    manager._on_map(grown, '/map')
    assert (manager._accepted_maps, manager._observed_maps) == (2, 3)
    publish(grown)
    latest, received = manager._latest_map, manager._last_map_received_wall
    clock[0] = 14.02
    manager._on_map(g, '/map')
    assert manager._latest_map is latest and manager._last_map_received_wall == received
    assert (manager._accepted_maps, manager._observed_maps) == (2, 3)
    publish(grown)
    assert n._metric_correlation.map_revision == 3
    conflict = copy.deepcopy(grown)
    conflict.data[0] = 100
    manager._on_map(conflict, '/map')
    assert manager._rejected_maps == 1 and manager._latest_map is latest
    assert manager._last_map_received_wall == received
    assert (manager._accepted_maps, manager._observed_maps) == (2, 3)
