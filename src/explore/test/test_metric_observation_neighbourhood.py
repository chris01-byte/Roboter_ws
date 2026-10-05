"""A served observer position does not serve every different boundary in view."""
from dataclasses import replace
import inspect
import math
import time

import pytest

from explore.metric_frontier import MetricTaskPolicy
from test_metric_frontier import candidate
from explore.metric_checkpoint import restore_policy
from test_metric_robot_side_observation import fixture as recorded_fixture


def eligible(policy, *args, **kwargs):
    # Compare the original policy's actual decision too: it had no view
    # argument and therefore suppressed the distinct boundary unconditionally.
    if 'observation_points' not in inspect.signature(policy.eligible).parameters:
        kwargs.pop('observation_points', None)
    return policy.eligible(*args, **kwargs)


def fixture():
    policy = MetricTaskPolicy(.6, 30., 2)
    old = policy.identify((-.7349999835714698, 1.6949999621137977))
    observed = replace(candidate(old, (.69442, -.00545)),
                       frontier_xy=policy.attempts[old].frontier_xy,
                       evidence_key='actual old boundary evidence')
    policy.record(observed, 'observed', 10., observed.fingerprint)
    new = policy.identify((1.304999970830977, .13499999698251486))
    return policy, old, new


def test_new_finite_frontier_area_can_reuse_nearby_position_without_serving_it():
    policy, old, new = fixture()
    kwargs = dict(task_id=new, target_xy=(.855, -.105), now=41.,
                  fingerprint='b'*64, evidence_key='actual different boundary evidence')
    assert not policy.eligible(**kwargs)  # IDs/digests alone retain old protection
    assert eligible(policy, **kwargs, observation_points=((1.275, .135),))
    assert policy.attempts[old].tries == 1 and policy.attempts[old].completed
    assert policy.attempts[new].tries == 0 and not policy.attempts[new].completed


@pytest.mark.parametrize('points', [(), ((-.735, 1.695),), ((.0, 1.0),),
    ((1.275, .135), (-.735, 1.695)), ((math.nan, .135),), ((1.275,),)])
def test_missing_overlapping_or_invalid_view_never_reopens_served_alias(points):
    policy, _, new = fixture()
    assert not eligible(policy, new, (.855, -.105), 41., 'b'*64, 'different',
                               observation_points=points)


@pytest.mark.parametrize('guard', ['cooldown', 'served_try_cap', 'task_try_cap', 'failure_cap'])
def test_distinct_measured_frontier_view_never_resets_original_limits(guard):
    policy, old, new = fixture()
    now = 39. if guard == 'cooldown' else 41.
    if guard == 'served_try_cap':
        policy.attempts[old].tries = 3
    if guard == 'task_try_cap':
        policy.attempts[new].tries = 3
    if guard == 'failure_cap':
        policy.attempts[new].failures = 2
    assert not eligible(policy, new, (.855, -.105), now, 'b'*64, 'different',
                               observation_points=((1.275, .135),))


def test_actual_a48_served_boundaries_keep_a_bounded_different_observation():
    node, inputs, metadata = recorded_fixture('ap06_a48_selection')
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    assert policy.attempts['metric-task-4'].completed
    assert policy.attempts['metric-task-5'].completed
    assert policy.attempts['metric-task-2'].tries == 3
    assert node._metric_select(inputs, policy, .3) == []  # original actual cap
    # Counter variant models the earlier first rejection. All actual later
    # maps, finite scan angles and the other served histories remain intact.
    policy.attempts['metric-task-2'].tries = 1
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan
    selected = candidates[0]
    assert selected.observation_points and node._frontier_rank_stats['robot_side_observation']
    assert node._metric_waypoints_clear(inputs, selected.route, selected.yaw) is not None
    assert math.dist((selected.x, selected.y), policy.attempts['metric-task-4'].target_xy) < policy.radius
    assert policy.attempts['metric-task-4'].tries == 1
    assert policy.attempts['metric-task-5'].tries == 1
    assert policy.attempts['metric-task-2'].tries == 1
