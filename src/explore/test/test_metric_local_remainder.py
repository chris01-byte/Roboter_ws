"""Measured B147 tiny residual and actual C++ alternatives; no whole-run claim."""
import copy
import json
import math
import time
from pathlib import Path
from dataclasses import replace

import numpy as np
import pytest
from explore.metric_frontier import MetricCandidate
from explore.metric_progress import local_small_remainder
from test_metric_public_cooldown import frozen
from test_metric_departure import path

NAME = 'ap06_b147_local_remainder'


def actual():
    n, inputs, policy = frozen(NAME, elapsed_s=31.)
    meta = json.loads((Path(__file__).parent/'data'/NAME).with_suffix('.json').read_text())
    return n, inputs, policy, meta


def omitted(n, inputs, anchor):
    return local_small_remainder(inputs[0], n._metric_scope_mask(inputs), inputs[2],
        anchor, n._world_to_grid, n._grid_to_world, .3)


def classify_current_residual(n, inputs, policy):
    # Explicit future-classification component on ORIGINAL completed B147
    # history. No historical arrival/receipt is rewritten or qualified here.
    for key, attempt in policy.attempts.items():
        if attempt.completed and omitted(n, inputs, attempt.frontier_xy):
            before = copy.deepcopy(attempt)
            candidate = MetricCandidate(key, *attempt.target_xy, 0., attempt.frontier_xy,
                (), 0., 0., attempt.fingerprint, inputs[1].map_revision)
            policy.record(candidate, 'partially_observed', attempt.retry_after-policy.cooldown_s,
                attempt.fingerprint, attempt.evidence_key, count_try=False,
                arrival_xy=attempt.target_xy)
            assert attempt.tries == before.tries and attempt.failures == before.failures
            assert attempt.retry_after == before.retry_after


def test_original_complete_view_leaves_four_reachable_filtered_local_boundary_cells():
    n, inputs, policy, _ = actual()
    task = policy.attempts['metric-task-4']
    assert task.completed and task.tries == 1
    assert omitted(n, inputs, task.frontier_xy) == 4
    assert omitted(n, inputs, (100., 100.)) == 0
    assert task.completed and not task.partial_observation  # measurement is read-only


def test_filtered_residual_does_not_count_a_disconnected_free_island():
    from test_metric_progress import grid
    from explore.explore_node import ExploreNode
    g = grid(); data = np.zeros((g.info.height, g.info.width), dtype=int)
    data[10:17, 20:27] = 100
    data[11:16, 21:26] = 0
    data[13, 23] = -1
    g.data = data.ravel().tolist()
    anchor = ExploreNode._grid_to_world(23, 13, g.info)
    pose = (*ExploreNode._grid_to_world(5, 5, g.info), 0.)
    assert local_small_remainder(g, np.ones(data.shape,bool), pose, anchor,
        ExploreNode._world_to_grid, ExploreNode._grid_to_world, 1.) == 0


def test_actual_current_corner_retains_same_try_history_and_finds_native_alternative():
    n, inputs, policy, meta = actual()
    classify_current_residual(n, inputs, policy)
    n._metric_status = {}
    first = n._metric_select(inputs, policy, .3)[0]
    assert first.task_id == 'metric-task-4' and first.requires_nav2_plan
    assert (first.x, first.y, first.yaw) == pytest.approx(meta['expected_candidates'][0]['candidate']['goal'])
    assert n._metric_validate_nav_plan(inputs, path(meta['native_plans'][0]), first, public_only=True) is None
    policy.record(first, 'proposal_rejected', time.monotonic()-31., inputs[1].fingerprint,
        n._metric_local_evidence(inputs, policy.attempts[first.task_id].frontier_xy), count_failure=False)
    second = n._metric_select(inputs, policy, .3)[0]
    assert second.task_id == first.task_id and second.requires_nav2_plan
    assert (second.x, second.y, second.yaw) == pytest.approx(meta['expected_candidates'][1]['candidate']['goal'])
    assert policy.attempts[second.task_id].tries == 2
    assert policy.attempts[second.task_id].failures == 0
    route = n._metric_validate_nav_plan(inputs, path(meta['native_plans'][1]), second, public_only=True)
    assert route is not None
    assert n._metric_native_observation_ready(inputs, route, second, inputs, second.observation_points)
    from rclpy.clock import Clock
    n._clock = Clock(); n._metric_active = None
    queries = []
    def recorded(target, stopped, **kwargs):
        queries.append(target)
        for record in meta['native_plans'][2:]:
            if math.dist(record['goal'][:2], (target.x,target.y)) < 1e-8 and abs(record['goal'][2]-target.yaw) < 1e-8:
                return path(record), record['error']
        return None, 'unrecorded_query'
    n._metric_request_nav_plan = recorded
    assert n._metric_departure_plan_ready(inputs, route, second, lambda: False)
    assert len(queries) == 3
    assert policy.attempts[second.task_id].tries == 2  # forecasts never count arrival or gain


@pytest.mark.parametrize('fault', ['cooldown','try_cap','empty_rays'])
def test_new_corner_query_keeps_original_cooldown_cap_and_finite_view(fault):
    n, inputs, policy, _ = actual(); classify_current_residual(n,inputs,policy)
    task = policy.attempts['metric-task-4']
    if fault == 'cooldown':task.retry_after = time.monotonic()+30.
    elif fault == 'try_cap':task.tries = 3
    else:
        view = n._metric_observation_view()
        n._metric_observation_view = lambda: replace(view,angles=np.empty((0,2)))
    before = copy.deepcopy(task)
    if fault == 'empty_rays':
        from explore.explore_node import Frontier
        from explore.metric_frontier_candidates import boundary_samples
        scope = n._metric_scope_mask(inputs)
        samples = boundary_samples(inputs[0],scope,n._grid_to_world,.3,
            retained_anchors=(task.frontier_xy,))
        sample = min(samples,key=lambda s:math.dist(s.xy,task.frontier_xy))
        frontier = Frontier(sample.xy,sample.size)
        frontier.approach_direction = sample.inward; frontier.retained_observation = True
        seed = MetricCandidate('',*inputs[2],sample.xy,(),0.,0.,
            inputs[1].fingerprint,inputs[1].map_revision,True,())
        assert n._metric_refine_native_observation(inputs,frontier,policy,scope,seed,
            'metric-task-4',time.monotonic()+.5) is None
    else:
        assert not any(c.task_id == 'metric-task-4' for c in n._metric_select(inputs,policy,.3))
    assert task == before


def test_corner_directions_follow_rotated_raster_and_cardinal_face_is_unchanged():
    n, inputs, _, _ = actual(); g = copy.deepcopy(inputs[0])
    angle = .37; g.info.origin.orientation.z = math.sin(angle/2); g.info.origin.orientation.w = math.cos(angle/2)
    assert n._metric_corner_face_headings(g,(math.cos(angle),math.sin(angle))) == ()
    normal = (math.cos(angle+math.pi/4),math.sin(angle+math.pi/4))
    assert n._metric_corner_face_headings(g,normal) == pytest.approx(tuple(angle+a for a in (0.,math.pi/2,-math.pi/2,math.pi)))


def test_actual_parent_keeps_tiny_local_work_after_resolving_every_original_ray(monkeypatch):
    from test_metric_progress import parent_fixture
    from test_metric_map_lifecycle import status
    from explore.metric_progress import observation_complete
    n,g,clock,parent,terminal = parent_fixture(monkeypatch,'open')
    n._max_frontier_goals = 1
    chosen = []; baselines = []
    baseline = n._metric_observation_baseline
    def captured_baseline(*args):
        value = baseline(*args); baselines.append(value)
        return value
    n._metric_observation_baseline = captured_baseline
    def plan(target,*_):
        chosen.append(target)
        return path(dict(points=target.route,goal=(target.x,target.y,target.yaw))),None
    n._metric_request_nav_plan = plan
    n._prealign_to_goal = lambda *_,**__:('skipped',)
    def navigate(*_,**__):
        target = chosen[-1]; clock[0]+=.1
        n._robot_pose_sample = lambda:((target.x,target.y,target.yaw),0.)
        newer = copy.deepcopy(g)
        for xy in target.observation_points:
            col,row = n._world_to_grid(*xy,newer.info)
            newer.data[row*newer.info.width+col] = 0
        # Genuine still-unknown local pocket separate from the selected rays.
        xy = (target.frontier_xy[0]-.4,target.frontier_xy[1]+.4)
        col,row = n._world_to_grid(*xy,newer.info)
        assert newer.data[row*newer.info.width+col] == 0
        newer.data[row*newer.info.width+col] = -1
        newer.header.stamp.nanosec = 100_000_000
        n._on_map(newer); n._on_metric_map_status(status(newer,accepted=3,observed=3,when=100.1))
        assert observation_complete(baselines[-1],newer,n._metric_inputs(active=True)[1],
            n._world_to_grid,n._grid_to_world)
        return 'success'
    n._navigate_to = navigate
    result = n._execute_metric_frontier(parent,10.,1.)
    assert terminal == ['abort'] and not result.success
    assert n._metric_status['arrivals'] == n._metric_status['observations'] == 1
    assert n._metric_status['chain'][0]['decision'] == 'partially_observed'
    assert n._metric_status['local_omitted_boundary_cells'] > 0
    task = n._metric_checkpoint['policy']['tasks'][chosen[0].task_id]
    assert task['tries'] == 1 and task['failures'] == 0
    assert task['partial_observation'] and not task['completed']
