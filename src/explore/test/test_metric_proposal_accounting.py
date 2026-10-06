"""A geometrically rejected read-only plan is not a failed physical goal."""
import math

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from test_metric_progress import parent_fixture


@pytest.mark.parametrize('unsafe_plan', (True, False))
def test_parent_keeps_attempt_limits_and_counts_only_dispatched_goal_failures(monkeypatch,unsafe_plan):
    node, _, clock, parent, terminal = parent_fixture(monkeypatch,'open')
    node._max_frontier_goals = node._max_failed_goals = 1
    node._prealign_to_goal = lambda *_args, **_kw: ('skipped',)
    dispatched = []
    def planner(target, _stopped):
        planned = Path(); planned.header.frame_id = 'map'
        points = ((target.route[0],(3.,.05),(target.x,target.y))
                  if unsafe_plan else target.route)
        for x,y in points:
            pose = PoseStamped();pose.pose.position.x=x;pose.pose.position.y=y
            pose.pose.orientation.z=math.sin(target.yaw/2)
            pose.pose.orientation.w=math.cos(target.yaw/2)
            planned.poses.append(pose)
        return planned,None
    node._metric_request_nav_plan = planner
    def navigate(*_args, **_kw):
        dispatched.append(True);clock[0]+=.1
        return 'aborted'
    node._navigate_to = navigate
    result = node._execute_metric_frontier(parent,10.,.3)
    assert not result.success and terminal == ['abort']
    assert node._metric_status['attempts'] == 1  # rejected proposals still use the fixed cap
    assert node._metric_status['failures'] == int(not unsafe_plan)
    assert bool(dispatched) is (not unsafe_plan)
    chain = node._metric_status['chain']
    assert chain[0]['child_dispatched'] is (not unsafe_plan)
    assert chain[0]['observed_cells'] == 0 and not chain[0]['arrived']
    assert chain[0]['decision'] == ('proposal_rejected' if unsafe_plan else 'task_unreached_cause_unproven')
    tasks = node._metric_checkpoint['policy']['tasks'].values()
    assert sum(t['tries'] for t in tasks) == 1
    assert sum(t['failures'] for t in tasks) == int(not unsafe_plan)
    assert all(not t['completed'] for t in tasks)


def test_route_rejected_before_planner_is_readonly_and_consumes_original_cap(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._max_frontier_goals = node._max_failed_goals = 1
    calls = []
    def no_geometry(*_):
        node._metric_last_route_rejection = 'goal_orientation_invalid'
        return False
    node._metric_navigation_geometry_ready = no_geometry
    node._metric_request_nav_plan = lambda *_: calls.append('planner')
    node._navigate_to = lambda *_args, **_kw: calls.append('motion')
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort'] and not calls
    assert node._metric_status['attempts'] == 1
    assert node._metric_status['failures'] == node._metric_status['arrivals'] == 0
    chain = node._metric_status['chain'][0]
    assert chain['decision'] == 'proposal_rejected' and not chain['child_dispatched']
    tasks = node._metric_checkpoint['policy']['tasks'].values()
    assert sum(t['tries'] for t in tasks) == 1 and sum(t['failures'] for t in tasks) == 0
    assert not any(t['completed'] for t in tasks)


def test_route_rejected_after_alignment_keeps_motion_failure_without_nav_child(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._max_frontier_goals = node._max_failed_goals = 1
    aligned, dispatched = [], []
    def planner(target, _stopped):
        path = Path(); path.header.frame_id = 'map'
        for x, y in target.route:
            pose = PoseStamped(); pose.pose.position.x = x; pose.pose.position.y = y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        return path, None
    original = node._metric_navigation_geometry_ready
    node._metric_request_nav_plan = planner
    node._metric_navigation_geometry_ready = lambda *args: not aligned and original(*args)
    def alignment(*_args, **_kwargs):
        aligned.append(True)
        return 'success', .3, .3, 0.
    node._metric_align_nav_departure = alignment
    node._navigate_to = lambda *_args, **_kwargs: dispatched.append(True)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort'] and aligned and not dispatched
    assert node._metric_status['attempts'] == node._metric_status['failures'] == 1
    assert node._metric_status['arrivals'] == node._metric_status['observations'] == 0
    assert node._metric_status['chain'][0]['decision'] == 'route_invalidated'
    assert not node._metric_status['chain'][0]['child_dispatched']
    tasks = node._metric_checkpoint['policy']['tasks'].values()
    assert sum(t['tries'] for t in tasks) == sum(t['failures'] for t in tasks) == 1
