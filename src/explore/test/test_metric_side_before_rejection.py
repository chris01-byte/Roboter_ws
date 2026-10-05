"""Later A51 rasters: reject a pose, not every safe view of its frontier."""
import copy
import time

import pytest

from explore.metric_frontier import MetricTaskPolicy
from explore.metric_checkpoint import restore_policy
from test_metric_robot_side_observation import fixture


@pytest.mark.parametrize('served', [False, True])
def test_invalid_normal_approach_keeps_proved_robot_side_observation(served):
    node, inputs, metadata = fixture('ap06_a51_selection')
    policy = MetricTaskPolicy(.6, 30., 2)
    if served:
        original, _ = restore_policy(metadata['checkpoint'], time.monotonic(),
                                      metadata['checkpoint']['saved_wall_time'])
        # Explicit earlier-history component variant on later rasters:
        # retain the actual first completed observer, not later failed tries.
        policy.attempts['metric-task-4'] = copy.deepcopy(original.attempts['metric-task-4'])
        policy.next_id = 4
    node._global_costmap_received_at = time.monotonic()
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan, node._frontier_rank_stats
    candidate = candidates[0]
    assert candidate.observation_points and candidate.frontier_xy[0] < 1.4
    assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None
    assert policy.attempts[candidate.task_id].tries == 0
    if served:
        old = policy.attempts['metric-task-4']
        assert old.completed and old.tries == 1 and old.failures == 0
        assert candidate.task_id != 'metric-task-4'


def test_recorded_exhausted_a51_history_stays_exhausted():
    node, inputs, metadata = fixture('ap06_a51_selection')
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    node._global_costmap_received_at = time.monotonic()
    before = [(key, a.tries, a.failures, a.completed) for key, a in policy.attempts.items()]
    assert node._metric_select(inputs, policy, .3) == []
    assert before == [(key, a.tries, a.failures, a.completed) for key, a in policy.attempts.items()]


def test_actual_native_side_arrival_and_departure_paths_remain_proved():
    from explore.metric_frontier import MetricCandidate
    from test_metric_departure import path
    node, inputs, metadata = fixture('ap06_a51_selection')
    records = metadata['plans']; first = records[0]
    target = MetricCandidate('component', *first['goal'], tuple(first['goal'][:2]),
        (), 1., 0., inputs[1].fingerprint, 1)
    route = node._metric_validate_nav_plan(inputs, path(first), target, public_only=True)
    assert route is not None
    calls = []
    def planner(candidate, stopped, *, start_pose):
        import numpy as np
        assert not stopped()
        calls.append(candidate)
        record = records[len(calls)]
        assert np.allclose(start_pose, record['start_pose'], atol=1e-8)
        assert np.allclose((candidate.x, candidate.y, candidate.yaw), record['goal'], atol=1e-8)
        return path(record), record['error']
    node._metric_request_nav_plan = planner
    assert node._metric_departure_plan_ready(inputs, route, target, lambda: False)
    assert len(calls) == len(records)-1
