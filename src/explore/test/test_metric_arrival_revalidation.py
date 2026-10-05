"""A terminal Nav2 SUCCESS outside the exact arrival disk is no receipt.

Production parent, exact pair, scope, routes and measured gain remain active.
Only the absent action peer and deterministic clock are supplied here.
"""
import copy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
import pytest
from test_metric_progress import parent_fixture
from test_metric_map_lifecycle import status


@pytest.mark.parametrize('fault', ['xy', 'yaw', 'all_miss', 'total',
                                  'cancel', 'epoch', 'source', 'deadline'])
def test_bounded_same_task_arrival_revalidation_keeps_original_guards(monkeypatch, fault):
    n, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    n._max_frontier_goals = 2
    if fault == 'total': n._max_frontier_goals = 1
    if fault == 'all_miss':
        n._metric_retry_limit = 1
        n._max_frontier_goals = 3  # per-task cap, independent of total cap
    chosen = []; children = []
    def planner(target, *_):
        chosen.append(target)
        path = Path(); path.header.frame_id = 'map'; path.header.stamp.sec = 100
        for x, y in target.route:
            p = PoseStamped(); p.pose.position.x = x; p.pose.position.y = y
            p.pose.orientation.w = 1.; path.poses.append(p)
        return path, None
    n._metric_request_nav_plan = planner
    n._prealign_to_goal = lambda *_, **__: ('skipped',)
    def navigate(*_, **__):
        target = chosen[-1]; children.append(target); clock[0] += .1
        # Fresh measured position misses by 5 mm; never widen .15 m/.4 rad.
        missed = len(children) == 1 or fault == 'all_miss'
        xy_error = .14 if fault == 'yaw' or not missed else .155
        yaw_error = .405 if fault == 'yaw' and missed else 0.
        n._robot_pose_sample = lambda: ((target.x-xy_error, target.y,
                                        target.yaw+yaw_error), 0.)
        if not missed:
            newer = copy.deepcopy(grid)
            for xy in children[0].observation_points:
                col, row = n._world_to_grid(*xy, newer.info)
                newer.data[row*newer.info.width+col] = 0
            newer.header.stamp.nanosec = int((clock[0]-10)*1e9)
            n._on_map(newer)
            n._on_metric_map_status(status(newer, accepted=3, observed=3,
                                          when=100+clock[0]-10))
        if fault == 'cancel': parent.is_cancel_requested = True
        if fault == 'epoch': n._metric_fault = 'map_epoch_changed'
        if fault == 'source':
            n._metric_operating_snapshot = lambda **_: dict(safe=False,
                first_rejecting_predicate='source_missing')
        if fault == 'deadline': clock[0] += n._goal_timeout_s
        return 'success'
    n._navigate_to = navigate
    result = n._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal
    assert children and n._wohnungserkundung_active_child is None
    checkpoint = n._metric_checkpoint
    if fault in ('xy', 'yaw', 'all_miss'):
        assert len(children) == 2
        assert children[0].task_id == children[1].task_id
        assert checkpoint['attempts'] == 2
        task = checkpoint['policy']['tasks'][children[0].task_id]
        assert task['tries'] == 2
        chain = n._metric_status['chain']
        assert chain[0]['decision'] == 'arrival_revalidate'
        assert not chain[0]['arrived'] and chain[0]['observed_cells'] == 0
        if fault == 'all_miss':
            assert n._metric_status['arrivals'] == n._metric_status['observations'] == 0
            assert task['failures'] == 1 and not task['completed']
        else:
            assert n._metric_status['arrivals'] == n._metric_status['observations'] == 1
            assert task['completed'] and task['failures'] == 0
    else:
        assert len(children) == 1
        assert checkpoint['attempts'] == 1
        assert n._metric_status['arrivals'] == n._metric_status['observations'] == 0
