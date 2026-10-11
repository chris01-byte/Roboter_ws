"""An actual adaptive query rejection retains the guard and bounded retry."""
import math

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from test_metric_progress import parent_fixture


def test_actual_adaptive_stop_rotation_rejection_is_a_bounded_proposal(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_start_strategy = 'adaptive'
    node._metric_path_validation = 'rpp_rollout'
    node._max_frontier_goals = 1
    queries, rejected = [], []
    validate = node._metric_validate_nav_plan

    def validate_actual(*args, **kwargs):
        route = validate(*args, **kwargs)
        rejected.append((route, node._metric_last_route_rejection))
        return route

    node._metric_validate_nav_plan = validate_actual

    def planner(target, stopped):
        assert not stopped()
        # Alternative native path to the actual, unmodified adaptive target.
        # Its RPP translation is clear; the real stop's final turn crosses
        # unknown raw cells. Only action transport is replaced by this path.
        points = (target.route[0], (target.x-.5, target.route[0][1]+1.),
                  (target.x, target.route[0][1]+1.), (target.x, target.y))
        path = Path()
        path.header.frame_id = 'map'
        for x, y in points:
            pose = PoseStamped()
            pose.pose.position.x, pose.pose.position.y = x, y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        inputs = node._metric_inputs(active=True)
        trajectory, clear, _ = node._metric_checked_public_rollout(
            inputs, points, native_plan=True)
        assert clear and trajectory  # isolate rotation from translation
        queries.append(target)
        return path, None

    node._metric_request_nav_plan = planner
    node._navigate_to = lambda *_, **__: pytest.fail('Rejected rotation cannot move')
    node._prealign_to_goal = lambda *_, **__: pytest.fail('Rejected rotation cannot align')
    result = node._execute_metric_frontier(parent, 10., .3)

    assert len(queries) == 1
    assert rejected == [(None, 'goal_stop_rotation_invalid')]
    assert not result.success and terminal == ['abort']
    state = node._metric_status
    assert state['first_trigger']['phase'] == 'native_route_rejected'
    assert state['first_trigger']['reason'] == 'nav2_plan_goal_stop_rotation_invalid'
    assert state['terminal_reason'] == 'budget_exhausted'
    assert state['chain'][0]['decision'] == 'proposal_rejected'
    assert state['chain'][0]['child_dispatched'] is False
    assert state['failures'] == 0
    assert node._metric_checkpoint['attempts'] == 1
    assert node._wohnungserkundung_active_child is None


@pytest.mark.parametrize('fault', ['frame', 'orientation', 'nonfinite_goal'])
def test_actual_adaptive_invalid_plan_contract_still_terminates(monkeypatch, fault):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_start_strategy = 'adaptive'
    node._metric_path_validation = 'rpp_rollout'
    node._max_frontier_goals = 2
    queries = []

    def planner(target, stopped):
        assert not stopped()
        path = Path()
        path.header.frame_id = 'foreign' if fault == 'frame' else 'map'
        for x, y in target.route:
            pose = PoseStamped()
            pose.pose.position.x, pose.pose.position.y = x, y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        if fault == 'orientation':
            path.poses[-1].pose.orientation.w = float('nan')
        if fault == 'nonfinite_goal':
            path.poses[-1].pose.position.x = float('nan')
        queries.append(target)
        return path, None

    node._metric_request_nav_plan = planner
    node._navigate_to = lambda *_, **__: pytest.fail('Invalid plan cannot move')
    node._prealign_to_goal = lambda *_, **__: pytest.fail('Invalid plan cannot align')
    result = node._execute_metric_frontier(parent, 10., .3)
    reason = dict(frame='nav2_plan_missing_or_wrong_frame',
                  orientation='nav2_plan_orientation_or_frames_invalid',
                  nonfinite_goal='nav2_plan_goal_or_values_invalid')[fault]
    assert len(queries) == 1 and not result.success and terminal == ['abort']
    assert node._metric_status['terminal_reason'] == 'nav2_plan_' + reason
    assert node._metric_status['first_trigger']['reason'] == 'nav2_plan_' + reason
    assert not node._metric_status['chain']
    assert node._wohnungserkundung_active_child is None
