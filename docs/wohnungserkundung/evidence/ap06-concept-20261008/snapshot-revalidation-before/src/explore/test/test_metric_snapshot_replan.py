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
