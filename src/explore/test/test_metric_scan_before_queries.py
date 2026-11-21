"""A known safe scan supplies perception before spending unsafe path queries."""
from dataclasses import replace

import pytest

from explore.metric_frontier import MetricTaskPolicy
from test_metric_robot_side_observation import fixture


@pytest.mark.parametrize('kind,pending,expected', [
    ('query', True, 'full_scan'), ('proved', True, 'observation_goal'),
    ('query', False, 'observation_goal')])
def test_safe_round_scan_precedes_only_unproved_queries(kind, pending, expected):
    node, inputs, _ = fixture('ap06_a48_selection')
    policy = MetricTaskPolicy(.6, 30., 2)
    actual = node._metric_select(inputs, policy, .3)
    assert actual and actual[0].observation_points
    # Candidate peer only: geometry, scope, map contents and scan checks are
    # production code on actual rasters. Declared query grants no movement.
    query = replace(actual[0], requires_nav2_plan=kind == 'query')
    node._metric_select = lambda *_: [query]
    before = [list(inputs[i].data) for i in (0, 5)]
    counters = [(a.tries, a.failures) for a in policy.attempts.values()]
    decision, candidates = node._metric_start_decision(inputs, policy, .3, pending)
    assert decision['scan_admissible'] and decision['scan_useful']
    assert decision['selected_motion'] == expected
    assert candidates == [query]
    assert counters == [(a.tries, a.failures) for a in policy.attempts.values()]
    assert [list(inputs[i].data) for i in (0, 5)] == before


def test_unknown_rotated_body_cannot_gain_scan_permission_from_query():
    node, inputs, _ = fixture('ap06_a48_selection')
    policy = MetricTaskPolicy(.6, 30., 2)
    actual = node._metric_select(inputs, policy, .3)
    node._metric_select = lambda *_: [replace(actual[0], requires_nav2_plan=True)]
    col, row = node._world_to_grid(inputs[2][0]+.3, inputs[2][1], inputs[0].info)
    inputs[3][row, col] = False
    decision, _ = node._metric_start_decision(inputs, policy, .3, True)
    assert not decision['scan_admissible']
    assert decision['selected_motion'] == 'observation_goal'
