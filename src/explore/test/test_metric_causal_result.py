"""First observed guard, later recovery and terminal reason stay distinct."""
import math

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from test_metric_progress import parent_fixture


def test_readonly_native_rejection_is_retained_before_terminal_budget(monkeypatch):
    n, _, _, parent, _ = parent_fixture(monkeypatch, 'open')
    n._max_frontier_goals = 1
    n._prealign_to_goal = lambda *_, **__: ('skipped',)
    def planner(target, _stop):
        path = Path(); path.header.frame_id = 'map'
        for x, y in (target.route[0], (3., .05), (target.x, target.y)):
            p = PoseStamped(); p.pose.position.x, p.pose.position.y = x, y
            p.pose.orientation.z, p.pose.orientation.w = math.sin(target.yaw/2), math.cos(target.yaw/2)
            path.poses.append(p)
        return path, None
    n._metric_request_nav_plan = planner
    n._navigate_to = lambda *_, **__: pytest.fail('Rejected geometry cannot move')
    result = n._execute_metric_frontier(parent, 10., .3)
    assert not result.success
    assert n._metric_status['first_trigger']['phase'] == 'native_route_rejected'
    assert n._metric_status['first_trigger']['reason'].startswith('nav2_plan_')
    assert n._metric_status['terminal_reason'] == n._metric_status['reason'] == 'budget_exhausted'
    assert n._metric_status['reactions'][-1]['phase'] == 'terminal'
    assert n._metric_status['chain'][0]['decision'] == 'proposal_rejected'
    assert n._metric_status['failures'] == 0


def test_first_scan_trigger_survives_later_route_rejection_and_bounded_history(monkeypatch):
    n, _, _, _, _ = parent_fixture(monkeypatch, 'known')
    n._metric_status = dict(first_trigger=None, reactions=[])
    measured = dict(achieved_angle_rad=5.6421, target_angle_rad=2*math.pi)
    n._metric_record_transition('scan_interrupted', 'scan_task_budget_exhausted', scan=measured)
    measured['achieved_angle_rad'] = 99.  # never mutate the original receipt
    for i in range(50):
        n._metric_record_transition('native_route_rejected', 'footprint_sweep_invalid', ordinal=i)
    n._metric_status['terminal_reason'] = 'frontier_candidate_processing_budget_exhausted'
    n._metric_record_transition('terminal', n._metric_status['terminal_reason'])
    first = n._metric_status['first_trigger']
    assert first['reason'] == 'scan_task_budget_exhausted'
    assert first['scan']['achieved_angle_rad'] == 5.6421
    assert len(n._metric_status['reactions']) == 40
    assert n._metric_status['reactions'][-1]['reason'] != first['reason']


def test_user_cancel_retains_earlier_actual_guard_receipt(monkeypatch):
    n, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    actual = n._metric_inputs
    def inputs(*args, **kwargs):
        if n._metric_status.get('first_trigger') is not None:
            parent.is_cancel_requested = True
        if parent.is_cancel_requested:
            return actual(*args, **kwargs)
        raise ValueError('pose_stale_after_processing')
    n._metric_inputs = inputs
    result = n._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['cancel']
    assert n._metric_status['first_trigger']['reason'] == 'pose_stale_after_processing'
    assert n._metric_status['terminal_reason'] == 'user_canceled'
