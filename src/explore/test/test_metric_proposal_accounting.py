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
