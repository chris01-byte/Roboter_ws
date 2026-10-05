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


@pytest.mark.parametrize('fault', ['body', 'sight', 'tries', 'deadline', 'cone'])
def test_public_observation_keeps_original_body_sight_history_and_budget(fault):
    node, inputs, policy = recorded()
    scope = node._metric_scope_mask(inputs)
    frontiers = [Frontier(f.xy, f.size) for f in boundary_samples(inputs[0], scope, node._grid_to_world, .3)]
    if fault == 'body':
        c, r = node._world_to_grid(*inputs[2][:2], inputs[0].info)
        inputs[3][r, c] = False
    if fault == 'sight':
        node._metric_observation_view = lambda: LidarView((.245, 0., math.pi/2), np.array([]), 4., .05)
    if fault == 'tries':
        for f in frontiers: policy.identify((f.cx, f.cy))
        for task in policy.attempts.values(): task.tries = 3
    if fault == 'cone':
        node._frontier_forward_cone_half_angle = .001
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs, 'policy': policy}
    before = {k: (a.tries, a.failures, a.completed) for k, a in policy.attempts.items()}
    started = time.monotonic()-(5. if fault == 'deadline' else 0.)
    assert node._metric_public_observation(inputs, frontiers, policy, scope, started) is None
    assert before == {k: (a.tries, a.failures, a.completed)
                      for k, a in policy.attempts.items() if k in before}
