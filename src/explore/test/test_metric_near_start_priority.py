"""Actual A227: a proved first observation precedes unproved distant work."""
import copy
import math
import pytest
from test_metric_public_cooldown import frozen


def test_first_useful_departure_retains_progress_after_native_arrival_tolerance():
    node, inputs, policy = frozen('ap06_a227_start_selection')
    maps = [list(inputs[i].data) for i in (0, 5)]
    chosen = node._metric_select(inputs, policy, .3)[0]
    stop = node._metric_rollout_stop_pose(inputs, chosen.route, chosen.yaw)
    # The original 15-cm native arrival disk swallowed half the short goal.
    # This scene admits a useful, fully proved farther view in the SAME search.
    assert math.dist(stop[:2], inputs[2][:2]) >= .25
    assert math.dist((chosen.x, chosen.y), inputs[2][:2]) <= node._min_goal_dist_m+node._goal_search_m
    assert chosen.observation_points and not chosen.requires_nav2_plan
    assert node._metric_waypoints_clear(inputs, chosen.route, chosen.yaw) is not None
    assert maps == [list(inputs[i].data) for i in (0, 5)]
    assert not any(a.tries or a.failures for a in policy.attempts.values())


def test_actual_initial_private_departure_is_not_starved_by_distant_queries():
    node, inputs, policy = frozen('ap06_a227_start_selection')
    assert not policy.attempts and all(e.valid for e in node._metric_egress)
    before = copy.deepcopy(node._metric_egress)
    maps = [list(inputs[i].data) for i in (0, 5)]
    def distant(*_, **__):
        pytest.fail('Proved short private departure must precede distant approaches')
    node._frontier_approach_goal = distant
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and node._frontier_rank_stats['bounded_start_observation']
    chosen = candidates[0]
    assert chosen.observation_points and not chosen.requires_nav2_plan
    assert node._metric_waypoints_clear(inputs, chosen.route, chosen.yaw) is not None
    assert maps == [list(inputs[i].data) for i in (0, 5)]
    assert all(a.tries == 0 and a.failures == 0 for a in policy.attempts.values())
    for old, now in zip(before, node._metric_egress):
        assert old.fixed.remaining_area == now.fixed.remaining_area
        assert old.fixed.departed_distance == now.fixed.departed_distance
        assert old.valid == now.valid and old.reference == now.reference
        assert old.fixed.initial_polygon == now.fixed.initial_polygon


@pytest.mark.parametrize('fault', ['no_route', 'no_view', 'cooldown', 'capped'])
def test_short_departure_cannot_bypass_route_view_or_original_history(monkeypatch, fault):
    import time
    import explore.metric_frontier_runtime as runtime
    node, inputs, policy = frozen('ap06_a227_start_selection')
    chosen = node._metric_select(inputs, policy, .3)[0]
    if fault in ('cooldown', 'capped'):
        policy.record(chosen, 'failed', time.monotonic(), chosen.fingerprint)
        if fault == 'capped':
            policy.attempts[chosen.task_id].tries = policy.retry_limit+1
        previous = copy.deepcopy(policy.attempts[chosen.task_id])
    elif fault == 'no_route':
        node._metric_route = lambda *_: None
    else:
        monkeypatch.setattr(runtime, 'visible_boundary_cells', lambda *_: set())
    class DistantSearch(Exception):
        pass
    def distant(*_, **__):
        raise DistantSearch()
    node._frontier_approach_goal = distant
    try:
        candidates = node._metric_select(inputs, policy, .3)
    except DistantSearch:
        candidates = []  # Original independent search remains available.
    assert not candidates
    assert not node._frontier_rank_stats.get('bounded_start_observation')
    if fault in ('cooldown', 'capped'):
        assert policy.attempts[chosen.task_id] == previous
