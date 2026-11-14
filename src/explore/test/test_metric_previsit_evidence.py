"""First-pass policy queries need no digest; the selected task always does."""
import copy
import time
import pytest
from explore.metric_progress import local_evidence
from test_metric_public_cooldown import frozen


def test_unvisited_selection_binds_actual_digest_only_for_selected_candidates(monkeypatch):
    import explore.metric_frontier_runtime as runtime
    node, inputs, policy = frozen('ap06_a227_start_selection')
    assert not policy.attempts
    reads = []
    def measured(*args, **kwargs):
        reads.append(args[1])
        return local_evidence(*args, **kwargs)
    monkeypatch.setattr(runtime, 'local_evidence', measured)
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates
    assert len(reads) == len(candidates)
    for candidate in candidates:
        attempt = policy.attempts[candidate.task_id]
        assert candidate.evidence_key == local_evidence(inputs[0], attempt.frontier_xy,
            node._grid_to_world, batch_projection=True)
        assert not attempt.tries and not attempt.failures and not attempt.completed
        assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None


@pytest.mark.parametrize('history', ['pending', 'failed', 'observed', 'proposal_rejected'])
def test_any_real_history_keeps_actual_policy_digest(history):
    import threading
    node, inputs, policy = frozen('ap06_a227_start_selection')
    candidate = node._metric_select(inputs, policy, .3)[0]
    policy.record(candidate, history, time.monotonic(), candidate.fingerprint,
        candidate.evidence_key)
    before = copy.deepcopy(policy.attempts)
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = dict(inputs=inputs, policy=policy)
    actual = node._metric_policy_evidence(inputs, policy, candidate.task_id)
    expected = local_evidence(inputs[0], policy.attempts[candidate.task_id].frontier_xy,
        node._grid_to_world, batch_projection=True)
    assert actual == expected
    assert policy.attempts == before
