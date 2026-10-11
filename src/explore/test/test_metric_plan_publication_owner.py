"""Actual adaptive parent and plan callbacks retain the native child owner."""
import pytest
from explore.metric_frontier import MetricCandidate
from test_metric_map_lifecycle import runtime, path_for

@pytest.mark.parametrize('offset', [0., .04])
def test_readonly_planner_publication_cannot_become_active_navigation_path(monkeypatch, offset):
    n, _ = runtime(monkeypatch)
    n._metric_active = MetricCandidate('current', .9, .0, .0, (.9,.0), (), 1., 0., 'a'*64, 1)
    n._metric_active_context = n._metric_work_context()
    n._metric_plan_after_ns = 99_000_000_000
    n._wohnungserkundung_active_child = None
    incoming = path_for(n._metric_active)
    incoming.poses[-1].pose.position.x += offset
    n._on_metric_nav_plan(incoming)
    assert n._metric_nav_path is None, 'No navigation child owns this read-only topic publication'

def test_current_native_child_path_remains_accepted_and_context_bound(monkeypatch):
    n, _ = runtime(monkeypatch)
    n._metric_active = MetricCandidate('current', .9, .0, .0, (.9,.0), (), 1., 0., 'a'*64, 1)
    n._metric_active_context = n._metric_work_context()
    n._metric_plan_after_ns = 99_000_000_000
    n._wohnungserkundung_active_child = n._metric_active
    incoming = path_for(n._metric_active)
    n._on_metric_nav_plan(incoming)
    assert n._metric_nav_path is incoming
    n._metric_fault = 'different_epoch'
    late = path_for(n._metric_active)
    n._on_metric_nav_plan(late)
    assert n._metric_nav_path is incoming

def test_actual_adaptive_parent_starts_native_publication_epoch_after_readonly_query(monkeypatch):
    import copy,math
    from nav_msgs.msg import Path
    from geometry_msgs.msg import PoseStamped
    from test_metric_progress import parent_fixture
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_start_strategy = 'adaptive'
    queries=[];dispatch=[]
    def stamp(path):
        ns=node.get_clock().now().nanoseconds
        path.header.stamp.sec,path.header.stamp.nanosec=divmod(ns,10**9)
    def planner(target, stopped):
        path=Path();path.header.frame_id='map';stamp(path)
        for x,y in target.route:
            pose=PoseStamped();pose.pose.position.x=x;pose.pose.position.y=y
            pose.pose.orientation.z=math.sin(target.yaw/2);pose.pose.orientation.w=math.cos(target.yaw/2)
            path.poses.append(pose)
        node._metric_plan_after_ns=node.get_clock().now().nanoseconds
        queries.append(path)
        clock[0]+=.2  # actual planning/alignment elapsed time, no budget reset
        return path,None  # action transport only; real selection and full path proof below
    node._metric_request_nav_plan=planner
    node._prealign_to_goal=lambda *_,**__: ('skipped',)
    def navigate(*_,**__):
        assert node._wohnungserkundung_active_child is node._metric_active
        dispatch.append(True)
        assert node._metric_plan_after_ns==node.get_clock().now().nanoseconds
        retained=node._metric_nav_path
        delayed=copy.deepcopy(queries[-1]);node._on_metric_nav_plan(delayed)
        assert node._metric_nav_path is retained
        current=copy.deepcopy(delayed);stamp(current);node._on_metric_nav_plan(current)
        assert node._metric_nav_path is current
        parent.is_cancel_requested=True
        return 'canceled'
    node._navigate_to=navigate
    result=node._execute_metric_frontier(parent,10.,.3)
    assert queries and dispatch and not result.success and terminal==['cancel']
    assert node._wohnungserkundung_active_child is None
