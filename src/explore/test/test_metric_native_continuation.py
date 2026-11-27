"""Recorded B126 public entry; actual C++ paths, no live health/mission claim."""
import copy
import json
import math
import time
from pathlib import Path

import pytest
from explore.metric_frontier import MetricCandidate
from explore.metric_checkpoint import policy_state, restore_policy, validate_checkpoint
from test_metric_departure import path
from test_metric_public_cooldown import frozen
from test_metric_progress import checkpoint_document

NAME = 'ap06_b126_native_continuation'


def actual():
    n, inputs, policy = frozen(NAME, elapsed_s=31.)
    meta = json.loads((Path(__file__).parent/'data'/NAME).with_suffix('.json').read_text())
    return n, inputs, policy, meta


def rejected_then_alternative():
    n, inputs, policy, meta = actual()
    first = n._metric_select(inputs, policy, .3)[0]
    assert first.task_id == 'metric-task-4' and first.requires_nav2_plan
    assert len(first.observation_points) == 5
    assert n._metric_validate_nav_plan(inputs, path(meta['rejected_native_plans'][0]), first,
                                       public_only=True) is None
    # One counted hypothetical attempt of the ACTUAL failed native query.
    # It does not reset the recorded prior arrival, cooldown or failure cap.
    policy.record(first, 'proposal_rejected', time.monotonic()-31., inputs[1].fingerprint,
                  count_failure=False)
    assert policy.attempts[first.task_id].tries == 2
    assert policy.attempts[first.task_id].failures == 0
    assert policy.attempts[first.task_id].partial_observation
    second = n._metric_select(inputs, policy, .3)[0]
    assert second.task_id == first.task_id and second.requires_nav2_plan
    assert second.x == pytest.approx(meta['expected_candidate']['goal'][0])
    assert second.y == pytest.approx(meta['expected_candidate']['goal'][1])
    assert policy.attempts[second.task_id].tries == 2
    return n, inputs, policy, meta, second


def test_partial_task_survives_rejected_query_and_finds_actual_native_alternative():
    n, inputs, policy, meta, second = rejected_then_alternative()
    route = n._metric_validate_nav_plan(inputs, path(meta['native_plans'][0]), second, public_only=True)
    assert route is not None
    assert n._metric_native_observation_ready(inputs, route, second, inputs, second.observation_points)
    stop = n._metric_rollout_stop_pose(inputs, route, second.yaw, native_plan=True)
    assert .14 < math.dist(stop[:2], (second.x, second.y)) <= .15
    assert not n._metric_scan_geometry_ready((inputs[0], inputs[1], stop, *inputs[3:]))
    assert policy.attempts['metric-task-1'].completed and policy.attempts['metric-task-1'].tries == 1


def departure(n, inputs, meta, second):
    route = n._metric_validate_nav_plan(inputs, path(meta['native_plans'][0]), second, public_only=True)
    assert route is not None
    queries = []
    def recorded(target, stopped, **kwargs):
        queries.append((target, kwargs))
        for record in meta['native_plans'][1:]:
            if (math.dist(record['goal'][:2], (target.x, target.y)) < 1e-8 and
                    abs(record['goal'][2]-target.yaw) < 1e-8):
                return path(record), record['error']
        return None, 'unrecorded_query'
    n._metric_request_nav_plan = recorded
    n._metric_active = None
    from rclpy.clock import Clock
    n._clock = Clock()
    return n._metric_departure_plan_ready(inputs, route, second, lambda: False), queries


def test_whole_known_native_forward_departure_to_current_finite_view():
    n, inputs, _, meta = actual()
    c = meta['expected_candidate']
    second = MetricCandidate(c['task'], *c['goal'], tuple(c['frontier']), (), 1., 0.,
        inputs[1].fingerprint, inputs[1].map_revision, True, tuple(tuple(p) for p in c['points']))
    allowed, queries = departure(n, inputs, meta, second)
    assert allowed and len(queries) == 3
    # Failed native reverse turn plus ACTUAL forward path, not a guessed chord.
    assert queries[1][0].x > second.x
    assert n._metric_nav_path is None


def test_departure_cannot_borrow_a_view_when_sensor_has_no_usable_rays():
    n, inputs, _, meta, second = rejected_then_alternative()
    view = n._metric_observation_view()
    from dataclasses import replace
    import numpy as np
    n._metric_observation_view = lambda: replace(view, angles=np.empty((0, 2)))
    allowed, _ = departure(n, inputs, meta, second)
    assert not allowed


@pytest.mark.parametrize('source', (3, 6))
def test_native_continuation_does_not_cross_unknown_reserved_body(source):
    n, inputs, _, meta, second = rejected_then_alternative()
    grid = inputs[0 if source == 3 else 5]
    col, row = n._world_to_grid(1.8, -.6, grid.info)
    inputs[source][row, col] = False
    allowed, _ = departure(n, inputs, meta, second)
    assert not allowed


def test_last_original_try_blocks_further_retained_queries():
    n, inputs, policy, _, second = rejected_then_alternative()
    policy.record(second, 'proposal_rejected', time.monotonic()-31., inputs[1].fingerprint,
                  count_failure=False)
    assert policy.attempts[second.task_id].tries == 3
    before = copy.deepcopy(policy.attempts[second.task_id])
    choices = n._metric_select(inputs, policy, .3)
    assert not any(c.task_id == second.task_id for c in choices)
    assert policy.attempts[second.task_id] == before


def test_partial_obligation_round_trip_survives_pending_and_planner_rejection():
    _, _, p, _, second = rejected_then_alternative()
    p.record(second, 'pending', 100., second.fingerprint)
    state = checkpoint_document()
    state.update(attempts=4, failures=0, arrivals=2, observations=2)
    state['policy'] = policy_state(p, 100.)
    saved = json.loads(json.dumps(state))
    restored, remaining = restore_policy(saved, 200., 1010.)
    assert remaining == 90.
    task = restored.attempts[second.task_id]
    assert task.partial_observation and task.tries == 3 and task.failures == 0
    assert not restored.eligible(second.task_id, (second.x, second.y+.03), 250.,
                                 second.fingerprint, 'new', observation_points=second.observation_points)


@pytest.mark.parametrize('invalid', (1, 'true', None))
def test_checkpoint_rejects_non_boolean_partial_obligation(invalid):
    state = checkpoint_document()
    state['policy']['tasks']['metric-task-1']['partial_observation'] = invalid
    with pytest.raises(ValueError, match='partial_state_invalid'):
        validate_checkpoint(state)


def test_original_checkpoint_restores_partial_reason_without_inventing_prior_receipts():
    state = checkpoint_document()
    state['schema_version'] = 1
    task = state['policy']['tasks']['metric-task-1']
    task.pop('partial_observation')
    task.update(reason='partially_observed', failures=0)
    state.update(failures=0, observations=1)
    p, _ = restore_policy(state, 200., 1010.)
    assert p.attempts['metric-task-1'].partial_observation
    assert p.attempts['metric-task-1'].tries == 1
    assert state['observations'] == 1


def test_same_spatial_task_keeps_cooldown_outside_its_old_goal_neighbourhood():
    from explore.metric_frontier import MetricTaskPolicy
    p = MetricTaskPolicy(.6, 30., 2)
    key = p.identify((3., 0.))
    c = MetricCandidate(key, 0., 0., 0., (3., 0.), (), 1., 0., 'map', 1,
                        evidence_key='local')
    p.record(c, 'partially_observed', 0., 'map')
    p.record(c, 'proposal_rejected', 10., 'map', count_failure=False)
    assert not p.eligible(key, (1., 0.), 39.999, 'map', 'local')
    assert p.eligible(key, (1., 0.), 40., 'map', 'local')
    assert (p.attempts[key].tries, p.attempts[key].failures) == (2, 0)


def test_real_failed_task_needs_new_evidence_even_at_a_distant_goal():
    from explore.metric_frontier import MetricTaskPolicy
    p = MetricTaskPolicy(.6, 30., 2)
    key = p.identify((3., 0.))
    c = MetricCandidate(key, 0., 0., 0., (3., 0.), (), 1., 0., 'map', 1,
                        evidence_key='local')
    p.record(c, 'task_unreached_cause_unproven', 10., 'map')
    assert not p.eligible(key, (1., 0.), 40., 'map', 'local')
    assert p.eligible(key, (1., 0.), 40., 'map', 'new-local')
    assert (p.attempts[key].tries, p.attempts[key].failures) == (1, 1)
