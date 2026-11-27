"""v17 B/C: a selection budget overrun at standstill is retried, not terminal.

Original v17 B and C ended failed/frontier_candidate_processing_budget_exhausted
after 5.89 s / 5.71 s wall time at confirmed standstill. With the self-healing
profile the product parent confirms standstill and selects again on fresh
inputs within the unchanged per-selection budget. Default 0 keeps the original
AP06 terminal behaviour.
"""
import pytest

from test_metric_progress import parent_fixture


def _overrun(node, overruns):
    original = node._metric_select
    calls = []
    def select(*args, **kwargs):
        calls.append(1)
        if len(calls) <= overruns:
            raise ValueError('frontier_candidate_processing_budget_exhausted')
        return original(*args, **kwargs)
    node._metric_select = select
    return calls


def test_default_keeps_original_terminal_budget_failure(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'known')
    _overrun(node, 1)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort']
    assert node._metric_status['reason'] == 'frontier_candidate_processing_budget_exhausted'


def test_bounded_retry_heals_a_single_overrun(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'known')
    node._metric_selection_budget_retries = 2
    calls = _overrun(node, 1)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert result.success and terminal == ['success'], node._metric_status
    assert len(calls) >= 2
    retries = [r for r in node._metric_status['reactions'] if r['phase'] == 'selection_retry']
    assert len(retries) == 1 and retries[0]['retry'] == 1


def test_retries_are_bounded_and_require_confirmed_standstill(monkeypatch):
    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'known')
    node._metric_selection_budget_retries = 2
    calls = _overrun(node, 10)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and terminal == ['abort']
    assert len(calls) == 3  # first try + two bounded retries
    assert node._metric_status['reason'] == 'frontier_candidate_processing_budget_exhausted'

    node, _, _, parent, terminal = parent_fixture(monkeypatch, 'known')
    node._metric_selection_budget_retries = 2
    confirmations = []
    node._metric_confirm_stop = lambda *_: confirmations.append(1) or len(confirmations) == 1
    calls = _overrun(node, 1)
    result = node._execute_metric_frontier(parent, 10., .3)
    assert not result.success and len(calls) == 1 and len(confirmations) == 2
    assert node._metric_status['reason'] == 'frontier_candidate_processing_budget_exhausted'
