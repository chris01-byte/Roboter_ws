"""An expired computation must stop before bounded fresh-input revalidation.

Parent, policy, map correlator and path checks are product code. Action peers
and a single measured-processing error are injected; no source age is reset.
"""
import copy
import math
import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from test_metric_map_lifecycle import status
from test_metric_progress import parent_fixture


@pytest.mark.parametrize('reason', ['start_motion_wheel_stale_after_processing',
                                    'start_motion_wheel_tf_disagreement',
                                    'pose_stale_after_processing', 'self_body_scan_stale_after_processing'])
@pytest.mark.parametrize('fault', ['fresh', 'source_gap', 'persistent', 'retry_budget', 'cancel', 'deadline',
                                   'context', 'unsafe_stop', 'cancel_failed'])
def test_expired_motion_snapshot_replans_only_after_stop_with_same_limits(monkeypatch, fault, reason):
    node, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._max_frontier_goals = 2 if fault != 'retry_budget' else 5
    if fault == 'retry_budget':
        node._metric_retry_limit = 1
    planned, navigation, confirmed = [], [], []
    actual_inputs = node._metric_inputs
    pending_error = [False]
    post_stop_error = [False]
    source_gap = {'pose_stale_after_processing': 'pose_missing_stale_or_invalid',
                  'self_body_scan_stale_after_processing': 'self_body_scan_stale'}.get(
                      reason, 'start_motion_wheel_missing_stale_or_invalid')
    def inputs(*args, **kwargs):
        if post_stop_error[0]:
            post_stop_error[0] = False
            node._metric_status['geometry_snapshot_rejection'] = dict(reason=reason, selection='post_child')
            raise ValueError(reason)
        if pending_error[0]:
            if fault != 'persistent':
                pending_error[0] = False
            node._metric_status['geometry_snapshot_rejection'] = dict(reason=reason, selection='during_child')
            raise ValueError(reason)
        if fault == 'source_gap' and navigation:
            raise ValueError(source_gap)
        return actual_inputs(*args, **kwargs)
    node._metric_inputs = inputs
    def planner(target, *_):
        planned.append((target, clock[0]))
        path = Path(); path.header.frame_id = 'map'
        for x, y in target.route:
            pose = PoseStamped(); pose.pose.position.x = x; pose.pose.position.y = y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        return path, None
    node._metric_request_nav_plan = planner
    node._prealign_to_goal = lambda *_, **__: ('skipped',)
    def confirm(*_):
        assert node._wohnungserkundung_active_child is None
        confirmed.append(len(navigation))
        if fault == 'fresh' and len(navigation) == 1 and reason in (
                'pose_stale_after_processing', 'self_body_scan_stale_after_processing'):
            post_stop_error[0] = True
        return not (fault == 'unsafe_stop' and navigation)
    node._metric_confirm_stop = confirm
    def navigate(*_, stop_requested, **__):
        assert node._wohnungserkundung_active_child is not None
        target = planned[-1][0]; navigation.append(clock[0]); clock[0] += .1
        if len(navigation) == 1 or fault == 'retry_budget':
            pending_error[0] = True
            assert stop_requested()  # old geometry never authorizes more motion
            if fault == 'cancel':
                parent.is_cancel_requested = True
            if fault == 'deadline':
                clock[0] += 10.
            if fault == 'context':
                node._metric_fault = 'map_epoch_changed'
            if fault == 'cancel_failed':
                return 'cancel_failed'
            return 'canceled'  # terminal action peer; production parent now owns stop
        assert confirmed[-1] == 1
        assert not stop_requested()
        newer = copy.deepcopy(grid)
        for xy in target.observation_points:
            col, row = node._world_to_grid(*xy, newer.info)
            newer.data[row*newer.info.width+col] = 0
        newer.header.stamp.nanosec = int((clock[0]-10)*1e9)
        node._on_map(newer)
        node._on_metric_map_status(status(newer, accepted=3, observed=3, when=100+clock[0]-10))
        node._robot_pose_sample = lambda: ((target.x, target.y, target.yaw), 0.)
        return 'success'
    node._navigate_to = navigate
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success  # fixed two-attempt fixture is partial, never whole acceptance
    if fault in ('fresh', 'retry_budget'):
        assert len(planned) == len(navigation) == 2
        assert planned[0][0].task_id == planned[1][0].task_id
        task = node._metric_checkpoint['policy']['tasks'][planned[0][0].task_id]
        assert task['tries'] == node._metric_status['attempts'] == 2
        assert node._metric_checkpoint['remaining_s'] < 10.
        assert node._metric_status['chain'][0]['decision'] == 'geometry_snapshot_revalidate'
        if fault == 'fresh':
            assert node._metric_status['arrivals'] == node._metric_status['observations'] == 1
            if reason in ('pose_stale_after_processing', 'self_body_scan_stale_after_processing'):
                receipt = node._metric_status['chain'][0]['geometry_snapshot_rejection']
                assert receipt == dict(reason=reason, selection='during_child')
                assert node._metric_status['geometry_snapshot_rejection']['selection'] == 'post_child'
        else:
            assert node._metric_status['reason'] == 'geometry_snapshot_retry_budget_exhausted'
            assert node._metric_status['arrivals'] == 0
    else:
        assert len(planned) == len(navigation) == 1
        if fault == 'persistent':
            assert node._metric_status['reason'] == reason
            assert clock[0] >= navigation[0]+2.
        elif fault == 'source_gap':
            assert node._metric_status['reason'] == source_gap
        elif fault == 'cancel':
            assert terminal == ['cancel']
        elif fault == 'context':
            assert node._metric_status['reason'] == 'map_epoch_changed'
        elif fault == 'unsafe_stop':
            assert node._metric_status['reason'] == 'post_child_state_or_standstill_unconfirmed'
        elif fault == 'cancel_failed':
            assert node._metric_status['reason'] == 'child_cancel_failed'
        else:
            assert node._metric_status['reason'] == 'budget_exhausted'
    assert node._wohnungserkundung_active_child is None


@pytest.mark.parametrize('reason', ['pose_stale_after_processing', 'self_body_scan_stale_after_processing'])
@pytest.mark.parametrize('fault', ['fresh', 'persistent', 'unsafe_stop', 'source_gap', 'context', 'cancel', 'deadline'])
def test_before_task_selection_waits_only_at_stop_in_one_source_window(monkeypatch, reason, fault):
    import explore.metric_frontier_runtime as module
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'known')
    started = clock[0]
    actual_inputs, actual_select = node._metric_inputs, node._metric_select
    calls, selections = [], []
    def inputs(*args, **kwargs):
        calls.append(clock[0])
        if fault == 'fresh' and len(calls) > 1 or fault == 'context' and len(calls) > 1:
            return actual_inputs(*args, **kwargs)
        if fault == 'source_gap':
            raise ValueError('self_body_scan_stale')
        # Alternating the two transient reasons cannot restart the same wait.
        raise ValueError(reason if len(calls) % 2 else (
            'pose_stale_after_processing' if reason.startswith('self_body') else 'self_body_scan_stale_after_processing'))
    node._metric_inputs = inputs
    def select(*args):
        selections.append(clock[0])
        return actual_select(*args)
    node._metric_select = select
    node._navigate_to = lambda *_, **__: pytest.fail('source waiting must not dispatch motion')
    node._metric_request_nav_plan = lambda *_, **__: pytest.fail('source waiting must not request a path')
    if fault == 'unsafe_stop':
        node._metric_operating_snapshot = lambda require_stop=False: dict(
            safe=not require_stop, first_rejecting_predicate='stable_standstill_not_confirmed' if require_stop else None)
    def tick(delay):
        clock[0] += max(.05, delay)
        if fault == 'cancel':
            parent.is_cancel_requested = True
        if fault == 'context':
            node._metric_fault = 'map_epoch_changed'
    monkeypatch.setattr(module.time, 'sleep', tick)
    result = node._execute_metric_frontier(parent, .1 if fault == 'deadline' else 10., .3)
    assert node._metric_status['attempts'] == node._metric_status['arrivals'] == node._metric_status['observations'] == 0
    assert node._wohnungserkundung_active_child is None
    if fault == 'fresh':
        assert result.success and selections and selections[0] >= started+.05
    else:
        assert not result.success and not selections
        if fault == 'persistent':
            assert 2. <= clock[0]-started < 2.051
            assert node._metric_status['reason'] in module._PROCESSING_AGE_ERRORS
        elif fault == 'cancel':
            assert terminal == ['cancel'] and clock[0]-started <= .051
        elif fault == 'deadline':
            assert node._metric_status['reason'] == 'budget_exhausted'
            assert clock[0]-started < .151
        elif fault == 'context':
            assert node._metric_status['reason'] == 'map_epoch_changed'
        else:
            assert len(calls) == 1 and clock[0] == started
            assert node._metric_status['reason'] == ('self_body_scan_stale' if fault == 'source_gap' else reason)


@pytest.mark.parametrize('reason', ['pose_stale_after_processing', 'self_body_scan_stale_after_processing'])
@pytest.mark.parametrize('fault', ['fresh', 'persistent', 'source_gap', 'unsafe_stop', 'cancel', 'task_deadline'])
def test_stationary_observation_discards_expired_gain_without_restarting_deadline(monkeypatch, reason, fault):
    import explore.metric_frontier_runtime as module
    node, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._max_frontier_goals = 1
    if fault == 'task_deadline':
        node._goal_timeout_s = .25
    chosen, navigation, gains, failures = [], [], [], []
    actual_inputs, actual_gain = node._metric_inputs, module.measured_gain
    reject_final = [False]
    def planner(target, *_):
        chosen.append(target)
        path = Path(); path.header.frame_id = 'map'
        for x, y in target.route:
            pose = PoseStamped(); pose.pose.position.x = x; pose.pose.position.y = y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        return path, None
    node._metric_request_nav_plan = planner
    node._prealign_to_goal = lambda *_, **__: ('skipped',)
    def navigate(*_, **__):
        navigation.append(clock[0]); clock[0] += .1
        target = chosen[-1]
        newer = copy.deepcopy(grid)
        for xy in target.observation_points:
            col, row = node._world_to_grid(*xy, newer.info)
            newer.data[row*newer.info.width+col] = 0
        newer.header.stamp.nanosec = int((clock[0]-10)*1e9)
        node._on_map(newer)
        node._on_metric_map_status(status(newer, accepted=3, observed=3, when=100+clock[0]-10))
        node._robot_pose_sample = lambda: ((target.x, target.y, target.yaw), 0.)
        return 'success'
    node._navigate_to = navigate
    def measured_gain(*args):
        gain = actual_gain(*args)
        assert gain  # real new visible cells, invalidated by the later failed proof
        gains.append(clock[0])
        reject_final[0] = fault != 'fresh' or len(gains) == 1
        return gain
    monkeypatch.setattr(module, 'measured_gain', measured_gain)
    def inputs(*args, **kwargs):
        if reject_final[0]:
            reject_final[0] = False
            failures.append(clock[0])
            assert node._wohnungserkundung_active_child is None
            raise ValueError('self_body_scan_stale' if fault == 'source_gap' else reason)
        return actual_inputs(*args, **kwargs)
    node._metric_inputs = inputs
    if fault == 'unsafe_stop':
        node._metric_operating_snapshot = lambda require_stop=False: dict(
            safe=not failures, first_rejecting_predicate='stable_standstill_not_confirmed' if failures else None)
    def tick(delay):
        clock[0] += max(.05, delay)
        if fault == 'cancel' and failures:
            parent.is_cancel_requested = True
    monkeypatch.setattr(module.time, 'sleep', tick)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and len(chosen) == len(navigation) == 1
    assert node._metric_status['attempts'] == 1 and node._metric_status['arrivals'] == 1
    assert node._wohnungserkundung_active_child is None and failures
    if fault == 'fresh':
        assert len(gains) == 2 and node._metric_status['observations'] == 1
        assert node._metric_status['chain'][0]['observed_cells'] > 0
        assert clock[0]-failures[0] < .5
    else:
        assert node._metric_status['observations'] == 0
        if fault in ('persistent', 'task_deadline'):
            assert node._metric_status['chain'][0]['observed_cells'] == 0
            assert node._metric_status['chain'][0]['decision'] == 'arrival_without_observation'
            window = 2. if fault == 'persistent' else .15
            assert window <= clock[0]-failures[0] < window+.31  # existing post-task .25 s pause
        elif fault == 'cancel':
            assert terminal == ['cancel']
        else:
            assert node._metric_status['reason'] == (
                'self_body_scan_stale' if fault == 'source_gap' else 'observation_sources_or_stop_invalid')
