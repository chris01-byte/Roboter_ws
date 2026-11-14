"""A geometrically rejected read-only plan is not a failed physical goal."""
import math
import copy

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from test_metric_progress import parent_fixture
from test_metric_map_lifecycle import status as map_status


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


def _alignment_parent(monkeypatch):
    node, grid, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_path_validation = 'rpp_rollout'
    node._max_frontier_goals = node._max_failed_goals = 1
    planned = []
    def planner(target, _stopped):
        planned.append(target)
        path = Path(); path.header.frame_id = 'map'
        for x, y in target.route:
            pose = PoseStamped(); pose.pose.position.x = x; pose.pose.position.y = y
            pose.pose.orientation.z = math.sin(target.yaw/2)
            pose.pose.orientation.w = math.cos(target.yaw/2)
            path.poses.append(pose)
        return path, None
    node._metric_request_nav_plan = planner
    # Independent read-only observation/future-plan peers. Selection, current
    # input correlation, body/spin/native-route proofs and parent are real.
    node._metric_native_observation_ready = lambda *_: True
    node._metric_departure_plan_ready = lambda *_: True
    node._navigate_to = lambda *_, **__: pytest.fail('unproved translation dispatched')
    def update_cells(cells=()):
        clock[0] += .01
        raw, cost = copy.deepcopy(node._metric_raw[0]), copy.deepcopy(node._global_costmap)
        now = 100+clock[0]-10
        for current in (raw, cost):
            current.header.stamp.sec = int(now)
            current.header.stamp.nanosec = round((now-int(now))*1e9)
            for x, y, value in cells:
                col, row = node._world_to_grid(x, y, current.info)
                current.data[row*current.info.width+col] = value
        node._on_map(raw); node._on_global_costmap(cost)
        node._on_metric_map_status(map_status(raw, accepted=3 if cells else 2, observed=3, when=now))
    return node, clock, parent, terminal, planned, update_cells


@pytest.mark.parametrize('rotation_cell', [None, 100, -1])
def test_parent_alignment_uses_public_current_spin_but_dispatch_rechecks_actual_translation(monkeypatch, rotation_cell):
    node, _, parent, terminal, planned, update_cells = _alignment_parent(monkeypatch)
    phase, calls, stopped = ['planning'], [], []
    original = node._metric_navigation_geometry_ready
    def geometry(inputs, target):
        calls.append(phase[0])
        return original(inputs, target)
    node._metric_navigation_geometry_ready = geometry
    def alignment(route, pose, stop_requested, *, inputs):
        target = planned[-1]
        assert node._wohnungserkundung_active_child is None
        # A real newly occupied distant endpoint invalidates translation;
        # it does not overlap the complete current rotation envelope.
        assert math.dist(pose[:2], (target.x, target.y)) > .6
        cells = [(target.x, target.y, 100)]
        if rotation_cell is not None:
            cells.append((*pose[:2], rotation_cell))
        update_cells(cells)
        current = node._metric_inputs(active=True)
        assert node._metric_scan_geometry_ready(node._metric_public_inputs(current)) is (rotation_cell is None)
        assert not original(current, target)  # actual native path is now blocked
        phase[0] = 'alignment'
        stopped.append(stop_requested())
        phase[0] = 'before_nav_dispatch'
        return ('interrupted' if stopped[-1] else 'success', .08, .3, .22)
    node._metric_align_nav_departure = alignment
    result = node._execute_metric_frontier(parent, 10., .3)
    assert planned and not result.success and terminal == ['abort']
    assert stopped == [rotation_cell is not None]
    if rotation_cell is None:
        assert 'alignment' not in calls  # no repeated whole-future-path proof during public spin
        assert 'before_nav_dispatch' in calls  # original full route still owns actual translation
    else:
        assert 'alignment' in calls  # unsafe public spin falls back to the original full route
    assert node._metric_status['attempts'] == node._metric_status['failures'] == 1
    record = node._metric_status['chain'][0]
    assert record['decision'] == 'route_invalidated' and not record['child_dispatched']
    assert record['alignment'] == node._metric_status['departure_alignment']
    assert record['alignment']['task'] == planned[0].task_id
    alignment_status = 'interrupted' if rotation_cell is not None else 'success'
    assert record['alignment']['result'] == [alignment_status, .08, .3, .22]
    assert record['alignment']['status'] == alignment_status
    assert record['alignment']['achieved_angle_rad'] == .08
    assert record['alignment']['residual_error_rad'] == .22


def test_full_spin_unavailable_retains_original_valid_narrow_route_fallback(monkeypatch):
    node, _, parent, terminal, planned, update_cells = _alignment_parent(monkeypatch)
    original = node._metric_navigation_geometry_ready
    called, checked = [], []
    node._metric_navigation_geometry_ready = lambda *args: (called.append(True) or original(*args))
    def alignment(route, pose, stop_requested, *, inputs):
        # An unseen patch behind the robot invalidates a complete spin but
        # lies outside its current forward-only native trajectory.
        update_cells([(pose[0]-.45, pose[1], -1)])
        current = node._metric_inputs(active=True)
        assert not node._metric_scan_geometry_ready(node._metric_public_inputs(current))
        assert original(current, planned[-1])
        before = len(called)
        checked.append(stop_requested())
        assert len(called) == before+1
        return 'insufficient_rotation', .06, .4, .34
    node._metric_align_nav_departure = alignment
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort'] and checked == [False]
    record = node._metric_status['chain'][0]
    assert record['result'] == 'alignment_failed'
    assert record['alignment']['result'] == ['insufficient_rotation', .06, .4, .34]
    assert not record['child_dispatched']


def test_alignment_callback_with_active_child_keeps_original_whole_route_gate(monkeypatch):
    node, _, parent, terminal, planned, update_cells = _alignment_parent(monkeypatch)
    checked = []
    def alignment(route, pose, stop_requested, *, inputs):
        target = planned[-1]
        update_cells([(target.x, target.y, 100)])
        assert node._metric_scan_geometry_ready(node._metric_public_inputs(node._metric_inputs(active=True)))
        # The phase callback cannot lend another active navigator a turn-only
        # permit, even though the public current spin itself remains valid.
        node._wohnungserkundung_active_child = target
        try:
            checked.append(stop_requested())
        finally:
            node._wohnungserkundung_active_child = None
        return 'interrupted', .06, .4, .34
    node._metric_align_nav_departure = alignment
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort'] and checked == [True]
    assert node._metric_status['chain'][0]['stop_reason'] == 'route_invalidated'


@pytest.mark.parametrize('fault, expected', [
    ('cancel', 'user_canceled'), ('source', 'encoder_feedback_stale'),
    ('pose', 'pose_missing_stale_or_invalid'), ('context', 'map_work_context_changed'),
    ('stale_pose', 'pose_missing_stale_or_invalid'), ('stale_costmap', 'costmap_missing_or_stale'),
    ('discontinuity', 'pose_discontinuity'), ('mission_budget', 'budget_exhausted'),
    ('task_budget', 'failure_budget_exhausted')])
def test_alignment_phase_keeps_actual_parent_cancel_source_pose_and_budget_guards(monkeypatch, fault, expected):
    node, clock, parent, terminal, planned, update_cells = _alignment_parent(monkeypatch)
    checked = []
    def alignment(route, pose, stop_requested, *, inputs):
        if fault == 'cancel':
            parent.is_cancel_requested = True
        elif fault == 'source':
            node._metric_operating_snapshot = lambda **_: dict(safe=False, first_rejecting_predicate=expected)
        elif fault == 'pose':
            node._robot_pose_sample = lambda: (None, None)
        elif fault == 'context':
            node._metric_work_is_current = lambda _: False
        elif fault == 'stale_pose':
            node._robot_pose_sample = lambda: (pose, node._door_pose_timeout+.01)
        elif fault == 'stale_costmap':
            node._global_costmap_received_at = clock[0]-node._map_timeout_s-.01
        elif fault == 'discontinuity':
            node._robot_pose_sample = lambda: ((pose[0]+.8, pose[1], pose[2]), 0.)
        elif fault == 'mission_budget':
            clock[0] += 11.
        elif fault == 'task_budget':
            clock[0] += node._goal_timeout_s
            update_cells()  # actual newer map/cost samples; the task deadline stays expired
        checked.append(stop_requested())
        return 'interrupted', .06, .4, .34
    node._metric_align_nav_departure = alignment
    result = node._execute_metric_frontier(parent, 10., .3)
    assert planned and checked == [True] and not result.success
    assert terminal == (['cancel'] if fault == 'cancel' else ['abort'])
    assert node._metric_status['reason'] == expected
    assert node._metric_status['arrivals'] == node._metric_status['observations'] == 0
    assert node._metric_status['departure_alignment']['result'] == ['interrupted', .06, .4, .34]
    if fault == 'task_budget':
        assert node._metric_status['chain'][0]['stop_reason'] == 'task_budget_exhausted'
        assert node._metric_status['chain'][0]['alignment']['status'] == 'interrupted'
