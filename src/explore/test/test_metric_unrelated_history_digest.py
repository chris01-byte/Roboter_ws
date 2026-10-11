"""The actual adaptive selector hashes history only where it can affect policy."""
import copy
import threading
import time

import pytest

from explore.metric_frontier import MetricAttempt
from explore.metric_progress import local_evidence
from test_metric_public_cooldown import frozen


def test_adaptive_unvisited_target_with_unrelated_history_hashes_only_selected_task(monkeypatch):
    import explore.metric_frontier_runtime as runtime
    node, inputs, policy = frozen('ap06_a227_start_selection')
    policy.next_id += 1
    old_key = f'metric-task-{policy.next_id}'
    policy.attempts[old_key] = MetricAttempt((30., 30.), (30., 30.),
        tries=1, completed=True, evidence_key='retained-unrelated-measurement')
    old = copy.deepcopy(policy.attempts[old_key])
    reads = []
    def measured(*args, **kwargs):
        reads.append(args[1])
        return local_evidence(*args, **kwargs)
    monkeypatch.setattr(runtime, 'local_evidence', measured)
    decision, candidates = node._metric_start_decision(inputs, policy, .3, False)
    assert decision['strategy'] == 'adaptive'
    assert decision['selected_motion'] == 'observation_goal' and candidates
    assert len(reads) == len(candidates)
    assert policy.attempts[old_key] == old
    for candidate in candidates:
        assert candidate.evidence_key == local_evidence(inputs[0],
            policy.attempts[candidate.task_id].frontier_xy, node._grid_to_world,
            batch_projection=True)


@pytest.mark.parametrize('kind', ['failed', 'partial', 'completed', 'proposal', 'capped'])
def test_unvisited_target_near_real_history_retains_actual_digest(kind):
    node, inputs, policy = frozen('ap06_a227_start_selection')
    goal = inputs[2][:2]
    policy.next_id += 1
    old_key = f'metric-task-{policy.next_id}'
    old = MetricAttempt((30., 30.), goal, tries=1, retry_after=time.monotonic()+30.,
                        evidence_key='retained-nearby-measurement')
    old.failures = 1 if kind == 'failed' else 0
    old.completed = kind == 'completed'
    old.partial_observation = kind == 'partial'
    old.reason = 'proposal_rejected' if kind == 'proposal' else kind
    if kind == 'capped':
        old.tries = policy.retry_limit+1
    policy.attempts[old_key] = old
    key = policy.identify((5., 5.))
    before = copy.deepcopy(policy.attempts)
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = dict(inputs=inputs, policy=policy)
    actual = node._metric_policy_evidence(inputs, policy, key, goal)
    assert actual == local_evidence(inputs[0], policy.attempts[key].frontier_xy,
                                   node._grid_to_world, batch_projection=True)
    assert policy.attempts == before


def test_two_checked_positions_cannot_skip_history_at_the_other_stop():
    node, inputs, policy = frozen('ap06_a227_start_selection')
    first, second = (20., 20.), (30., 30.)
    policy.next_id += 1
    old_key = f'metric-task-{policy.next_id}'
    policy.attempts[old_key] = MetricAttempt(second, second, tries=1, completed=True)
    key = policy.identify((5., 5.))
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = dict(inputs=inputs, policy=policy)
    assert node._metric_policy_evidence(inputs, policy, key, first, second) == local_evidence(
        inputs[0], policy.attempts[key].frontier_xy, node._grid_to_world, batch_projection=True)


def test_recorded_terminal_b_query_keeps_exact_goal_view_digest_and_attempt_caps():
    node, inputs, policy = frozen('ap06_b13_budget_history')
    before = copy.deepcopy(policy.attempts)
    candidates = node._metric_select(inputs, policy, .3)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert (candidate.x, candidate.y, candidate.yaw) == (
        1.4849999668076634, -0.48499998915940523, 0.)
    assert candidate.requires_nav2_plan
    assert len(candidate.observation_points) == 90
    assert candidate.evidence_key == '5c36088224972a4448398e223180b698796d450a5eeffa3dcc02bc9e85478365'
    assert all(policy.attempts[key] == old for key, old in before.items())
