"""Cooldown is bounded waiting work, never retained geometry or live authority."""
import copy
import math

import pytest

from explore.metric_frontier import MetricCandidate, MetricTaskPolicy
from explore.metric_frontier_runtime import MetricFrontierRuntime
from test_metric_progress import parent_fixture


def waiting_policy():
    policy = MetricTaskPolicy(.6, 30., 2)
    first = policy.identify((0., 1.), (0., 0.))
    candidate = MetricCandidate(first, 0., 0., 0., (0., 1.), (), 0., 0., 'a'*64, 1,
                                evidence_key='b'*64)
    policy.record(candidate, 'observed', 100., 'a'*64, arrival_xy=(0., 0.))
    points = ((2., 0.),)
    key = policy.identify((2., 0.), (.5, 0.), observation_points=points)
    assert key != first
    return policy, first, key, points


def test_original_wake_time_and_actual_limits_remain_unchanged():
    policy, _, key, points = waiting_policy()
    before = copy.deepcopy(policy.__dict__)
    wake = MetricFrontierRuntime._metric_observation_cooldown_until(
        policy, key, (.5, 0.), 'c'*64, 'd'*64, points, 120.)
    assert wake == 130.
    assert not policy.eligible(key, (.5, 0.), 129.999, 'c'*64, 'd'*64, observation_points=points)
    assert policy.eligible(key, (.5, 0.), 130., 'c'*64, 'd'*64, observation_points=points)
    assert policy.__dict__ == before
    assert MetricFrontierRuntime._metric_observation_cooldown_until(
        policy, key, (.5, 0.), 'c'*64, 'd'*64, points, 130.) is None


@pytest.mark.parametrize('fault', ['empty_view', 'nonfinite_view', 'served_boundary',
                                  'attempts', 'failures', 'same_evidence'])
def test_nontime_rejection_cannot_become_waiting_authority(fault):
    policy, first, key, points = waiting_policy()
    evidence = 'd'*64
    if fault == 'empty_view': points = ()
    if fault == 'nonfinite_view': points = ((math.nan, 0.),)
    if fault == 'served_boundary': points = ((.1, 1.),)
    if fault == 'attempts': policy.attempts[key].tries = 3
    if fault == 'failures': policy.attempts[key].failures = 2
    if fault == 'same_evidence': key, evidence = first, 'b'*64
    before = copy.deepcopy(policy.__dict__)
    assert MetricFrontierRuntime._metric_observation_cooldown_until(
        policy, key, (.5, 0.), 'c'*64, evidence, points, 120.) is None
    assert policy.__dict__ == before


@pytest.mark.parametrize('fault', ['wake', 'context', 'cancel', 'deadline',
                                  'source', 'hold', 'standstill'])
def test_waiting_parent_checks_live_faults_and_never_retains_a_goal(monkeypatch, fault):
    # Only inject a selection's time-only result. Parent/source joining,
    # checkpoints, absolute budgets and fault transitions are product code.
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    began = clock[0]
    selections, samples, holds = [], [], []
    actual_inputs = node._metric_inputs
    def inputs(*args, **kwargs):
        samples.append(clock[0])
        if fault == 'source' and clock[0] >= began+.5:
            raise ValueError('start_motion_wheel_missing_stale_or_invalid')
        if fault == 'context' and clock[0] >= began+.5:
            node._metric_context_generation = 1
        if fault == 'cancel' and clock[0] >= began+.5:
            parent.is_cancel_requested = True
        return actual_inputs(*args, **kwargs)
    node._metric_inputs = inputs
    def select(*_):
        selections.append(clock[0])
        if len(selections) > 1:
            raise ValueError('fresh_reselection')
        node._frontier_rank_stats = dict(bounded_private_observation_until=began+1.)
        return []
    node._metric_select = select
    def forbidden(*_args, **_kwargs):
        raise AssertionError('waiting must not plan, move, or perform public completion')
    node._navigate_to = node._metric_request_nav_plan = forbidden
    monkeypatch.setattr('explore.metric_frontier_runtime.reachable_remainder', forbidden)
    if fault == 'hold':
        node._wohnungserkundung_hwt_hold = lambda: clock[0] >= began+.5
        node._wohnungserkundung_wait_for_hwt_resume = lambda *_a, **_k: holds.append(clock[0]) or 'stopped'
    if fault == 'standstill':
        node._metric_operating_snapshot = lambda require_stop=False: dict(
            safe=not (require_stop and clock[0] >= began+.5),
            first_rejecting_predicate='standstill_unconfirmed' if clock[0] >= began+.5 else None)
    result = node._execute_metric_frontier(parent, .6 if fault == 'deadline' else 10., .3)
    assert not result.success
    assert node._wohnungserkundung_active_child is None
    assert node._metric_status['attempts'] == node._metric_status['failures'] == 0
    assert node._metric_status['arrivals'] == node._metric_status['observations'] == 0
    assert node._metric_status['chain'] == []
    assert node._metric_checkpoint['remaining_s'] < 10.
    assert len(samples) >= (2 if fault == 'hold' else 3)  # HOLD is checked even before inputs
    if fault in ('wake', 'context'):
        assert len(selections) == 2
        assert selections[1] >= began+(1. if fault == 'wake' else .5)
        assert node._metric_status['reason'] == 'fresh_reselection'
        assert 'task_cooldown_wait_s' not in node._metric_status
    else:
        assert len(selections) == 1
        assert node._metric_status['reason'] == dict(cancel='user_canceled',
            deadline='budget_exhausted', source='start_motion_wheel_missing_stale_or_invalid',
            hold='hwt_stopped', standstill='standstill_unconfirmed')[fault]
        assert bool(holds) is (fault == 'hold')
