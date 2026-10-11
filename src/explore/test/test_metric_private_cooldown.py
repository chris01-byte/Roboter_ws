"""Cooldown is bounded waiting work, never retained geometry or live authority."""
import copy
import math

import pytest

from explore.metric_frontier import MetricCandidate, MetricTaskPolicy
from explore.metric_frontier_runtime import MetricFrontierRuntime
from test_metric_progress import parent_fixture
from test_metric_public_cooldown import frozen


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
@pytest.mark.parametrize('strategy', ['adaptive', 'configured_scan'])
def test_waiting_parent_checks_live_faults_and_never_retains_a_goal(monkeypatch, fault, strategy):
    # Only inject a selection's time-only result. Parent/source joining,
    # checkpoints, absolute budgets and fault transitions are product code.
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    node._metric_start_strategy = strategy
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


@pytest.mark.parametrize('strategy', ['adaptive', 'configured_scan'])
@pytest.mark.parametrize('fault', ['deadline', 'cancel', 'source', 'hold', 'context'])
def test_actual_selection_runs_once_during_original_private_pause(monkeypatch, strategy, fault):
    """Actual captured geometry, policy, selection and adaptive decision.

    Only the live input/health boundary and clock are the component fixture.
    This is an ordering proof, not a live source or complete mission receipt.
    """
    import explore.metric_frontier_runtime as module
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    geometry, inputs, policy = frozen('ap06_a_private_cooldown')
    node.__dict__.update(geometry.__dict__)
    node._metric_start_strategy = strategy
    node._metric_scope_binding = inputs[1].fingerprint
    began = clock[0]
    def current_inputs(**_):
        if clock[0] >= began+.5:
            if fault == 'cancel': parent.is_cancel_requested = True
            if fault == 'source': raise ValueError('start_motion_wheel_missing_stale_or_invalid')
            if fault == 'context': node._metric_context_generation = 1
        return inputs
    node._metric_inputs = current_inputs
    if fault == 'hold':
        node._wohnungserkundung_hwt_hold = lambda: clock[0] >= began+.5
        node._wohnungserkundung_wait_for_hwt_resume = lambda *_a, **_k: 'stopped'
    monkeypatch.setattr(module, 'MetricTaskPolicy', lambda *_: policy)
    before = {k:(a.tries, a.failures, a.completed, a.retry_after)
              for k,a in policy.attempts.items()}
    calls = []
    select = node._metric_select
    def counted(*args, **kwargs):
        calls.append(clock[0])
        return select(*args, **kwargs)
    node._metric_select = counted
    def forbidden(*_args, **_kwargs):
        pytest.fail('Cooldown must not dispatch a plan or movement')
    node._navigate_to = node._metric_request_nav_plan = forbidden
    result = node._execute_metric_frontier(parent, .75, .3)
    assert terminal == (['cancel'] if fault == 'cancel' else ['abort']) and not result.success
    assert node._metric_status['reason'] == dict(deadline='budget_exhausted',
        context='budget_exhausted',cancel='user_canceled',hold='hwt_stopped',
        source='start_motion_wheel_missing_stale_or_invalid')[fault]
    assert node._frontier_rank_stats['bounded_private_observation_wait_s'] > .75
    assert len(calls) == (2 if fault == 'context' else 1), calls
    if fault == 'context': assert calls[1] >= began+.5
    assert node._metric_status['attempts'] == node._metric_status['arrivals'] == 0
    assert before == {k:(a.tries, a.failures, a.completed, a.retry_after)
                      for k,a in policy.attempts.items() if k in before}


def test_adaptive_parent_reproves_actual_route_after_original_pause(monkeypatch):
    import explore.metric_frontier_runtime as module
    node, _, clock, parent, terminal = parent_fixture(monkeypatch, 'open')
    geometry, inputs, policy = frozen('ap06_a_private_cooldown')
    node.__dict__.update(geometry.__dict__)
    node._metric_scope_binding = inputs[1].fingerprint
    node._metric_inputs = lambda **_: inputs
    node._overall_timeout_s = 40.  # unit episode can include the original 30-s policy
    monkeypatch.setattr(module, 'MetricTaskPolicy', lambda *_: policy)
    actual = node._metric_select
    calls, wake = [], []
    def selected(*args, **kwargs):
        choices = actual(*args, **kwargs)
        calls.append(clock[0])
        if len(calls) == 1:
            assert choices == []
            wake.append(node._frontier_rank_stats['bounded_private_observation_until'])
            return choices
        assert clock[0] >= wake[0] and choices
        assert choices[0].observation_points and not choices[0].requires_nav2_plan
        # End the component episode after the REAL fresh selection, before
        # the navigation boundary. This is not a motion/arrival receipt.
        raise ValueError('actual_selection_reproved_after_original_pause')
    node._metric_select = selected
    result = node._execute_metric_frontier(parent, 40., .3)
    assert not result.success and terminal == ['abort']
    assert len(calls) == 2 and calls[1] >= wake[0]
    assert node._metric_status['reason'] == 'actual_selection_reproved_after_original_pause'
    assert node._metric_status['attempts'] == node._metric_status['observations'] == 0
