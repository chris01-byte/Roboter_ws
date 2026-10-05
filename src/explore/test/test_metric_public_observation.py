"""Actual later A53 geometry/history: observe before a distant unsafe approach."""
import math
import time
import threading
from dataclasses import replace

import numpy as np
import pytest

from explore.metric_checkpoint import restore_policy
from explore.metric_frontier_candidates import boundary_samples, LidarView
from explore.explore_node import Frontier
from test_metric_robot_side_observation import fixture


def recorded():
    node, inputs, metadata = fixture('ap06_a53_selection')
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    return node, inputs, policy


def test_actual_exhausted_history_keeps_a_different_proved_current_view():
    node, inputs, policy = recorded()
    before = {k: (a.tries, a.failures, a.completed) for k, a in policy.attempts.items()}
    node._global_costmap_received_at = time.monotonic()
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan, node._frontier_rank_stats
    candidate = candidates[0]
    assert node._frontier_rank_stats['bounded_public_observation']
    assert candidate.observation_points
    assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None
    assert before == {k: (a.tries, a.failures, a.completed)
                      for k, a in policy.attempts.items() if k in before}
    assert policy.attempts[candidate.task_id].tries < 3
    assert node._min_goal_dist_m <= math.dist(inputs[2][:2], (candidate.x, candidate.y))+1e-12
    assert math.dist(inputs[2][:2], (candidate.x, candidate.y)) <= node._min_goal_dist_m+node._goal_search_m+1e-12


@pytest.mark.parametrize('fault', ['body', 'sight', 'tries', 'completed', 'deadline', 'cone'])
def test_public_observation_keeps_original_body_sight_history_and_budget(fault):
    node, inputs, policy = recorded()
    scope = node._metric_scope_mask(inputs)
    frontiers = [Frontier(f.xy, f.size) for f in boundary_samples(inputs[0], scope, node._grid_to_world, .3)]
    if fault == 'body':
        c, r = node._world_to_grid(*inputs[2][:2], inputs[0].info)
        inputs[3][r, c] = False
    if fault == 'sight':
        node._metric_observation_view = lambda: LidarView((.245, 0., math.pi/2), np.array([]), 4., .05)
    if fault in ('tries', 'completed'):
        for f in frontiers: policy.identify((f.cx, f.cy))
        for task in policy.attempts.values():
            if fault == 'tries': task.tries = 3
            else: task.completed = True
    if fault == 'cone':
        node._frontier_forward_cone_half_angle = .001
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs, 'policy': policy}
    before = {k: (a.tries, a.failures, a.completed) for k, a in policy.attempts.items()}
    started = time.monotonic()-(5. if fault == 'deadline' else 0.)
    assert node._metric_public_observation(inputs, frontiers, policy, scope, started) is None
    assert before == {k: (a.tries, a.failures, a.completed)
                      for k, a in policy.attempts.items() if k in before}


def test_actual_a54_short_view_precedes_unproved_distant_approach_work():
    node, inputs, metadata = fixture('ap06_a54_selection')
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    before = {k: (a.tries, a.failures, a.completed) for k, a in policy.attempts.items()}
    def unavailable(*_, **__):
        pytest.fail('Bounded proved public view must precede distant unproved approach work')
    node._frontier_approach_goal = unavailable
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan
    assert candidates[0].observation_points
    assert node._metric_waypoints_clear(inputs, candidates[0].route, candidates[0].yaw) is not None
    assert before == {k: (a.tries, a.failures, a.completed)
                      for k, a in policy.attempts.items() if k in before}


@pytest.mark.parametrize('name', ['ap06_a53_selection', 'ap06_a54_selection', 'ap06_a55_selection'])
def test_public_view_does_not_require_private_ledger_epoch_expiry(name):
    from explore.metric_frontier import StartEgressEvidence
    node, inputs, metadata = fixture(name)
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    # Public current body, invalid private ledger with no current exemptions:
    # this is the actual A53-55 state boundary, not a reconstruction of the
    # historical first inventory. Failure of the private monotone permission
    # does not mean the map/session identity itself has expired.
    node._metric_egress_expired = False
    node._metric_body_anchor_expired = False
    evidence = []
    for grid, allowed in ((inputs[0], inputs[3]), (inputs[5], inputs[6])):
        item = StartEgressEvidence.capture(grid,
            np.asarray(grid.data).reshape(allowed.shape), allowed,
            np.ones_like(allowed), inputs[2], node._metric_bounds, node._world_to_grid)
        assert not item.unknown.any()
        item.valid = False; item.reason = 'start_egress_approaches_unknown'
        evidence.append(item)
    node._metric_egress = tuple(evidence)
    node._metric_egress_identity = (inputs[1].context,
        tuple(node._metric_grid_geometry(g) for g in (inputs[0], inputs[5])))
    before = {k: (a.tries, a.failures, a.completed) for k, a in policy.attempts.items()}
    candidates = node._metric_select(inputs, policy, .3)
    assert node._frontier_rank_stats.get('bounded_public_observation')
    assert candidates and not candidates[0].requires_nav2_plan
    assert candidates[0].observation_points
    assert not node._metric_egress_expired
    assert all(not e.valid and not e.unknown.any() for e in evidence)
    assert before == {k: (a.tries, a.failures, a.completed)
                      for k, a in policy.attempts.items() if k in before}
    assert node._metric_waypoints_clear(inputs, candidates[0].route, candidates[0].yaw) is not None
