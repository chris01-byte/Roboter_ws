import copy
import pytest
import explore.metric_frontier_runtime as module
from test_metric_frontier import adaptive_fixture
from explore.metric_progress import local_evidence


def test_rejected_exact_native_target_retains_its_original_evidence_anchor():
    from explore.metric_frontier import MetricTaskPolicy,MetricCandidate
    node,inputs=adaptive_fixture();policy=MetricTaskPolicy(.6,30.,2)
    old_anchor=(1.5,.5);new_anchor=(1.5,-.5);goal=(1.,0.)
    old=policy.identify(old_anchor);new=policy.identify(new_anchor)
    old_digest=local_evidence(inputs[0],old_anchor,node._grid_to_world,batch_projection=True)
    new_digest=local_evidence(inputs[0],new_anchor,node._grid_to_world,batch_projection=True)
    assert old_digest!=new_digest  # same grid, genuinely DIFFERENT local windows
    c=MetricCandidate(old,*goal,0.,old_anchor,(),1.,0.,inputs[1].fingerprint,1,evidence_key=old_digest)
    policy.record(c,'pending',10.,c.fingerprint)
    policy.record(c,'proposal_rejected',10.,c.fingerprint,old_digest,count_try=False,count_failure=False)
    assert policy.identify(new_anchor,goal)==old, 'Same rejected target must compare the original local evidence window'
    assert not policy.eligible(old,goal,41.,c.fingerprint,old_digest)


def test_actual_adaptive_rejected_native_target_is_not_new_input_at_another_anchor():
    from test_metric_public_cooldown import frozen
    import math
    node, inputs, policy = frozen('ap06_a_rejected_query_anchor')
    node._metric_start_strategy = 'adaptive'
    original = copy.deepcopy(policy.attempts['metric-task-14'])
    assert original.reason == 'proposal_rejected' and original.tries == 1
    assert original.evidence_key == node._metric_local_evidence(inputs, original.frontier_xy)
    decision, candidates = node._metric_start_decision(inputs, policy, .3, False)
    assert all(math.dist((c.x,c.y), original.target_xy) > 1e-12 for c in candidates), (
        'Unchanged map and exact rejected target must not become a new query through an untried anchor',
        candidates)
    assert policy.attempts['metric-task-14'] == original
    assert decision['selected_motion'] != 'full_scan'


@pytest.mark.parametrize('delta', [0., 5e-13, -5e-13])
def test_same_query_retains_original_limits_even_next_to_an_untried_anchor(delta):
    from dataclasses import replace
    from explore.metric_frontier import MetricTaskPolicy
    from test_metric_frontier import candidate
    policy = MetricTaskPolicy(.6, 30., 2)
    old = policy.identify((1.5, .5))
    newer = policy.identify((1.5, -.5))
    first = replace(candidate(old), frontier_xy=(1.5, .5), evidence_key='same-local')
    policy.record(first, 'proposal_rejected', 10., first.fingerprint, count_failure=False)
    target = (first.x+delta, first.y)
    assert policy.identify((1.5, -.5), target, create=False) == old
    assert not policy.eligible(old, target, 39.999, first.fingerprint, 'new-local')
    assert not policy.eligible(old, target, 40., first.fingerprint, 'same-local')
    assert policy.eligible(old, target, 40., first.fingerprint, 'new-local')
    policy.attempts[old].tries = 3
    assert not policy.eligible(old, target, 100., first.fingerprint, 'new-local')
    assert policy.attempts[newer].tries == 0


def test_different_query_and_distinct_completed_view_keep_existing_identity_policy():
    from dataclasses import replace
    from explore.metric_frontier import MetricTaskPolicy
    from test_metric_frontier import candidate
    policy = MetricTaskPolicy(.6, 30., 2)
    old = policy.identify((1.5, .5))
    newer = policy.identify((1.5, -.5))
    first = replace(candidate(old), frontier_xy=(1.5, .5), evidence_key='same-local')
    policy.record(first, 'proposal_rejected', 10., first.fingerprint, count_failure=False)
    different = (first.x, first.y-.127)
    assert policy.identify((1.5, -.5), different) == newer
    assert not policy.eligible(newer, different, 39.999, first.fingerprint, 'same-local')
    assert policy.eligible(newer, different, 40., first.fingerprint, 'same-local')
    policy.record(first, 'observed', 40., first.fingerprint, count_try=False)
    points = ((1.5, -1.1),)
    assert policy.identify((1.5, -1.1), (first.x, first.y), observation_points=points) != old
    assert policy.attempts[old].completed and policy.attempts[old].retry_after == 70.
