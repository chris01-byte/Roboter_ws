"""Distinct planning poses keep the same task, cooldown and original budget."""
from dataclasses import replace

from explore.metric_frontier import MetricTaskPolicy
from test_metric_frontier import candidate


def test_rejected_query_can_try_distinct_pose_without_new_scan_or_reset():
    policy = MetricTaskPolicy(.6, 30., 2)
    key = policy.identify((1.5, 0.))
    first = replace(candidate(key), evidence_key='same-real-local-raster')
    policy.record(first, 'proposal_rejected', 10., first.fingerprint,
                  count_failure=False)
    second = replace(first, y=-.18)
    assert policy.identify(second.frontier_xy, (second.x, second.y)) == key
    assert not policy.eligible(key, (second.x, second.y), 39., first.fingerprint, first.evidence_key)
    assert not policy.eligible(key, (first.x, first.y), 41., first.fingerprint, first.evidence_key)
    assert policy.eligible(key, (first.x, -.15), 41., first.fingerprint, first.evidence_key)
    assert policy.eligible(key, (second.x, second.y), 41., first.fingerprint, first.evidence_key)
    policy.record(second, 'proposal_rejected', 41., first.fingerprint, count_failure=False)
    third = replace(first, x=1.18)
    assert policy.eligible(key, (third.x, third.y), 72., first.fingerprint, first.evidence_key)
    policy.record(third, 'proposal_rejected', 72., first.fingerprint, count_failure=False)
    assert policy.attempts[key].tries == 3 and policy.attempts[key].failures == 0
    assert not policy.eligible(key, (first.x, first.y), 1000., first.fingerprint, 'new-real-local-raster')


def test_real_failed_motion_and_served_pose_still_need_new_local_measurement():
    for outcome in ('route_invalidated', 'observed'):
        policy = MetricTaskPolicy(.6, 30., 2)
        key = policy.identify((1.5, 0.))
        first = replace(candidate(key), evidence_key='same-real-local-raster')
        policy.record(first, outcome, 10., first.fingerprint)
        assert not policy.eligible(key, (first.x, -.18), 41., first.fingerprint, first.evidence_key)


def test_c119_nearby_readonly_query_keeps_cooldown_and_spatial_caps():
    policy = MetricTaskPolicy(.8, 30., 2)
    key = policy.identify((3.434999923, -.614999986))
    first = replace(candidate(key), x=2.6967139720713553, y=-.12695889127380325,
                    frontier_xy=(3.434999923, -.614999986), evidence_key='same-local')
    policy.record(first, 'proposal_rejected', 10., first.fingerprint, count_failure=False)
    second = replace(first, x=2.7, y=0.)
    assert policy.identify(second.frontier_xy, (second.x, second.y)) == key
    assert not policy.eligible(key, (second.x, second.y), 39.999, first.fingerprint, first.evidence_key)
    assert not policy.eligible(key, (first.x, first.y), 40., first.fingerprint, first.evidence_key)
    assert policy.eligible(key, (second.x, second.y), 40., first.fingerprint, first.evidence_key)
    for now, target in ((40., second), (70., replace(second, x=2.79))):
        policy.record(target, 'proposal_rejected', now, first.fingerprint, count_failure=False)
    assert policy.attempts[key].tries == 3 and policy.attempts[key].failures == 0
    assert not policy.eligible(key, (2.8, 0.), 100., first.fingerprint, 'new-local')
