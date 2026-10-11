"""Independent audit counterexamples for actual LAB runtime decisions."""
import math
import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

from explore.lab_slots_runtime import live_guard
from explore.portal_memory import Point2D
from test_lab_slots import lab
from test_metric_map_lifecycle import status as map_status


def path_at(points, yaw=0.):
    path = Path()
    path.header.frame_id = 'map'
    for x, y in points:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x, pose.pose.position.y = x, y
        pose.pose.orientation.z = math.sin(yaw / 2.)
        pose.pose.orientation.w = math.cos(yaw / 2.)
        path.poses.append(pose)
    return path


def test_live_remaining_route_does_not_invent_a_turn_towards_passed_waypoints(monkeypatch):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    node._metric_path_validation = 'rpp_rollout'
    node._metric_scope = replace(node._metric_scope, vertices=tuple(
        Point2D(x, y) for x, y in ((-2., -.35), (2., -.35), (2., .45), (-2., .45))))
    # Current pose is (.05, .05, 0). Native RPP prunes the passed part;
    # the remaining straight passage fits, including the full body reserve.
    node._metric_nav_path = path_at([(-.8, .05), (-.4, .05), (.05, .05), (.4, .05), (1., .05)])
    node._metric_active = SimpleNamespace(x=1., y=.05, yaw=0.)
    assert node._metric_validate_nav_plan(node._metric_inputs(), node._metric_nav_path, node._metric_active) is not None, node._metric_last_route_rejection
    assert live_guard(node, context=node._metric_work_context()) is None


def test_live_changed_path_checks_final_heading_against_scope(monkeypatch):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    node._metric_scope = replace(node._metric_scope, vertices=tuple(
        Point2D(x, y) for x, y in ((-2., -.27), (2., -.27), (2., .37), (-2., .37))))
    node._metric_nav_path = path_at([(.05, .05), (.8, .05)], math.pi / 2)
    node._metric_active = SimpleNamespace(x=.8, y=.05, yaw=math.pi / 2)
    # Straight travel fits, but the native final-heading correction does not.
    assert live_guard(node, context=node._metric_work_context()) == 'lab_route_outside_scope'


@pytest.mark.parametrize('interruption', ['hwt_hold', 'source_gap'])
def test_initial_scan_resumes_even_when_it_uses_last_task_budget(monkeypatch, interruption):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    node._max_frontier_goals = 1
    calls = []
    held = [False]
    gap_until = [0.]
    node._wohnungserkundung_hwt_hold = lambda: held[0]
    node._metric_operating_snapshot = lambda **kw: dict(safe=clock[0] >= gap_until[0],
        first_rejecting_predicate=None if clock[0] >= gap_until[0] else 'vl53_cloud_missing_stale_or_invalid')
    def resume(*args, **kw):
        held[0] = node._hwt_hold_announced = False
        return 'resumed'
    node._wohnungserkundung_wait_for_hwt_resume = resume
    def turn(*, stop_requested, angle_rad):
        calls.append(angle_rad)
        if len(calls) == 1:
            if interruption == 'hwt_hold':
                held[0] = node._hwt_hold_announced = True
            else:
                gap_until[0] = clock[0] + .2
            assert stop_requested()
            return 'interrupted', .2
        parent.is_cancel_requested = True
        return 'success', angle_rad
    node._scan_in_place = turn
    node._execute_metric_frontier(parent, 10., .3)
    assert len(calls) == 2
    assert calls[1] == pytest.approx(2 * math.pi - .2)
    assert node._metric_status['attempts'] == 1


@pytest.mark.parametrize('recovery_s', [.2, 3.])
def test_hold_after_arrival_preserves_observation_task_and_does_not_navigate_again(monkeypatch, recovery_s):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    node._initial_scan_enabled = False
    node._max_frontier_goals = 1
    held = [False]
    stop_checks = []
    targets = []
    resumes = []
    node._wohnungserkundung_hwt_hold = lambda: held[0]
    def confirm(*args):
        stop_checks.append(True)
        if len(stop_checks) == 2:
            held[0] = node._hwt_hold_announced = True
        return True
    node._metric_confirm_stop = confirm
    def navigate(x, y, timeout, *, goal_yaw, **kwargs):
        targets.append(node._metric_active.task_id)
        assert len(targets) == 1, 'Terminal successful child must not be re-dispatched for observation'
        node._robot_pose_sample = lambda: ((x, y, goal_yaw), 0.)
        return 'success'
    node._navigate_to = navigate
    def resume(*args, require_target):
        resumes.append(True)
        assert node._metric_active is not None, 'An interrupted observation must retain the arrived task'
        assert node._metric_active.task_id == targets[0]
        assert node._metric_status.get('failures', 0) == 0
        target = node._metric_active
        clock[0] += recovery_s
        newer = copy.deepcopy(grid)
        assert target.observation_points
        for x, y in target.observation_points:
            col, row = node._world_to_grid(x, y, newer.info)
            newer.data[row * newer.info.width + col] = 0
        newer.header.stamp.nanosec = int((clock[0] - 10.) * 1e9)
        node._on_map(newer)
        node._on_metric_map_status(map_status(newer, accepted=3, observed=3, when=100. + clock[0] - 10.))
        held[0] = node._hwt_hold_announced = False
        return 'resumed'
    node._wohnungserkundung_wait_for_hwt_resume = resume
    node._execute_metric_frontier(parent, 10., .3)
    assert resumes == [True] and terminal == ['abort']
    assert len(targets) == node._metric_status['attempts'] == 1
    assert node._metric_status['observations'] == (1 if recovery_s < 2. else 0)
    if recovery_s < 2.:
        assert node._metric_status['arrivals'] == 1
        assert node._metric_status['failures'] == 0
    else:
        # The original observation window and job deadline must not restart.
        assert clock[0] < 10.02 + recovery_s + 1.
    assert node._metric_status['first_trigger']['reason'] == 'hwt_hold'
    assert node._metric_status['chain'][-1]['continued_observation'] is True
    assert node._metric_status['terminal_reason'] == 'budget_exhausted'


@pytest.mark.parametrize('fault_fields', [
    {'encoder_timing_recovery': {'fault_latched': True,
                                 'fault_reason': 'encoder_timing_continuity_unproven'}},
    {'feedback_output_fault_latched': True},
])
def test_known_encoder_or_output_latch_is_not_treated_as_a_short_source_gap(monkeypatch, fault_fields):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    wheel = dict(encoder_config_fault_latched=False, **fault_fields)
    node._metric_operating_snapshot = lambda **kw: dict(safe=False,
        first_rejecting_predicate='actuator_or_encoder_state_invalid', encoder_state=wheel)
    node._scan_in_place = lambda **kw: pytest.fail('Latched source fault cannot move')
    node._execute_metric_frontier(parent, 10., .3)
    assert terminal == ['abort']
    assert node._metric_status['outcome'] == 'error'
    assert node._metric_status['recoveries'] == 0
    assert wheel == dict(encoder_config_fault_latched=False, **fault_fields)


def test_delayed_stop_confirmation_after_arrival_never_resends_the_terminal_child(monkeypatch):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    node._initial_scan_enabled = False
    node._max_frontier_goals = 1
    confirmations = []
    targets = []
    def confirm(*args):
        confirmations.append(True)
        return len(confirmations) != 2
    node._metric_confirm_stop = confirm
    def navigate(x, y, timeout, *, goal_yaw, **kwargs):
        targets.append(node._metric_active)
        assert len(targets) == 1
        node._robot_pose_sample = lambda: ((x, y, goal_yaw), 0.)
        clock[0] += .1
        newer = copy.deepcopy(grid)
        for px, py in targets[0].observation_points:
            col, row = node._world_to_grid(px, py, newer.info)
            newer.data[row * newer.info.width + col] = 0
        newer.header.stamp.nanosec = int((clock[0] - 10.) * 1e9)
        node._on_map(newer)
        node._on_metric_map_status(map_status(newer, accepted=3, observed=3, when=100. + clock[0] - 10.))
        return 'success'
    node._navigate_to = navigate
    node._execute_metric_frontier(parent, 10., .3)
    assert len(targets) == node._metric_status['attempts'] == 1
    assert node._metric_status['arrivals'] == node._metric_status['observations'] == 1
    assert node._metric_status['failures'] == 0
    assert node._metric_status['chain'][-1]['continued_observation'] is True


@pytest.mark.parametrize('change, reason', [
    ('frame', 'nav2_plan_missing_or_wrong_frame'),
    ('pose_frame', 'nav2_plan_orientation_or_frames_invalid'),
    ('goal_yaw', 'nav2_plan_goal_orientation_invalid'),
    ('nan', 'nav2_plan_goal_or_values_invalid'),
])
def test_live_replacement_path_keeps_the_native_plan_contract(monkeypatch, change, reason):
    node, grid, clock, parent, terminal = lab(monkeypatch)
    path = path_at([(.05, .05), (.4, .05), (.8, .05)])
    node._metric_active = SimpleNamespace(x=.8, y=.05, yaw=0.)
    if change == 'frame':
        path.header.frame_id = 'odom'
    elif change == 'pose_frame':
        path.poses[1].header.frame_id = 'odom'
    elif change == 'goal_yaw':
        path.poses[-1].pose.orientation.z = math.sin(.2)
        path.poses[-1].pose.orientation.w = math.cos(.2)
    else:
        path.poses[1].pose.position.x = float('nan')
    node._metric_nav_path = path
    assert live_guard(node, context=node._metric_work_context()) == reason
