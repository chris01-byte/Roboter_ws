"""A protected parent stop during read-only planning must keep its cause."""
import pytest
from test_metric_progress import parent_fixture


@pytest.mark.parametrize('predicate', ('actuator_or_encoder_state_invalid', None))
def test_parent_keeps_observed_source_stop_instead_of_planner_timeout(monkeypatch, predicate):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'open')
    signal = [None]
    # Only absent source/action peers are doubled; the parent and its stop
    # callback, map inputs, candidate selection and result decision are real.
    node._metric_operating_snapshot = lambda **_: dict(
        safe=signal[0] is None, first_rejecting_predicate=signal[0])
    requests = []
    def planner(target, stopped):
        requests.append(target)
        if predicate:
            signal[0] = predicate
            assert stopped()
            signal[0] = None  # healed arrival cannot erase the observed stop
        return None, 'nav2_plan_timeout_or_stop'
    node._metric_request_nav_plan = planner
    result = node._execute_metric_frontier(parent, 10., .3)
    assert requests and not result.success and terminal == ['abort']
    assert node._metric_status['reason'] == (predicate or 'nav2_plan_timeout_or_stop')
    assert node._metric_status['arrivals'] == node._metric_status['observations'] == 0
    assert node._wohnungserkundung_active_child is None
