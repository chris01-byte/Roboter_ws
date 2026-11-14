"""Actual adaptive post-observation selection shares optional geometry work.

Own recorded synthetic Source-A rasters/history/finite sight. This is geometry
and policy evidence, with no live source health or movement receipt.
"""
import copy
import time

import pytest
from test_metric_public_cooldown import frozen


def test_actual_adaptive_selection_cannot_spend_public_window_again_on_side_search(monkeypatch):
    n, inputs, policy = frozen('ap06_a_optional_geometry_budget')
    n._metric_start_strategy = 'adaptive'
    before = copy.deepcopy(policy.__dict__)
    actual, spent = n._metric_public_search, []
    def traced(*args, **kwargs):
        started = time.monotonic()
        try:
            return actual(*args, **kwargs)
        finally:
            spent.append(time.monotonic()-started)
    n._metric_public_search = traced  # timing only; actual selection/geometric decision retained
    decision, candidates = n._metric_start_decision(inputs, policy, .3, False)
    assert candidates and decision['selected_motion'] != 'full_scan'
    candidate = candidates[0]
    assert (candidate.x, candidate.y, candidate.yaw) == pytest.approx(
        (-.04792893111683941, .7620710507782498, 2.6411186168144054))
    assert len(candidate.observation_points) == 102
    assert candidate.evidence_key == '3caab1cc428648fae89a6608457b0e212f18cea5819b3e5b1d21fa9aa81871b5'
    # The existing two-second public allocation is shared, not renewed by
    # each optional side helper. Allow one existing atomic geometry overrun.
    assert sum(spent) <= 2.2, spent
    assert n._metric_status['candidate_timing']['elapsed_s'] < 5.
    for key, old in before['attempts'].items():
        current = policy.attempts[key]
        assert (current.tries, current.failures, current.completed, current.retry_after) == (
            old.tries, old.failures, old.completed, old.retry_after)


def test_shared_window_keeps_remaining_time_and_restores_nested_deadline_on_exception(monkeypatch):
    import threading
    from test_metric_frontier import adaptive_fixture
    n, inputs = adaptive_fixture()
    n._metric_selection_cache = threading.local()
    owner = dict(inputs=inputs, optional_geometry_remaining_s=2., optional_geometry_elapsed_s=0.)
    n._metric_selection_cache.memo = owner
    n._metric_selection_cache.optional_geometry_deadline = 99.
    clock = [10.]
    monkeypatch.setattr('explore.metric_frontier_runtime.time.monotonic', lambda: clock[0])
    def rejected(*_):
        assert n._metric_optional_geometry_until(50.) == 12.
        clock[0] += 1.5
        raise ValueError('changed_geometry')
    with pytest.raises(ValueError, match='changed_geometry'):
        n._metric_public_search(inputs, None, rejected)
    assert n._metric_selection_cache.memo is owner
    assert n._metric_selection_cache.optional_geometry_deadline == 99.
    def next_search(*_):
        assert n._metric_optional_geometry_until(50.) == 12.  # same original allocation end
        clock[0] += .5
    n._metric_public_search(inputs, None, next_search)
    assert n._metric_selection_cache.optional_geometry_deadline == 99.
    assert n._metric_public_search(inputs, None, lambda *_: pytest.fail('no renewed window')) is None
    assert owner['optional_geometry_elapsed_s'] == 2.


def test_helper_outside_selection_keeps_original_independent_window(monkeypatch):
    from test_metric_frontier import adaptive_fixture
    n, inputs = adaptive_fixture()
    n._metric_selection_cache = None
    calls = []
    def measured(*_):
        calls.append(True)
        assert n._metric_optional_geometry_until(12.) == 12.
        return 'geometry only'
    assert n._metric_public_search(inputs, None, measured) == 'geometry only'
    assert calls == [True]
