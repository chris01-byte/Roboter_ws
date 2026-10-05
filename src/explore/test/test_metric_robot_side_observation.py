"""Actual A47 maps expose a useful observation before an unsafe door entry.

These later idle rasters and native paths are component evidence. Modified
history below models an earlier bounded proposal rejection, never a mission
receipt or permission to reset the recorded exhausted history.
"""
import math
from pathlib import Path
import time

import numpy as np
import pytest

from explore.metric_frontier import MetricCandidate, MetricTaskPolicy
from explore.metric_frontier_candidates import LidarView
from explore.metric_checkpoint import restore_policy
from test_metric_departure import fixture as recorded_fixture, path


def fixture(name='ap06_a47_selection'):
    node, inputs, metadata = recorded_fixture(name)
    arrays = np.load(Path(__file__).parent/'data'/(name+'.npz'))
    node._metric_observation_view = lambda: LidarView(
        (.245, 0., math.pi/2), arrays['angles'], 4., .05)
    node._metric_candidate_source = 'boundary_samples'
    node._metric_start_egress_enabled = True
    node._metric_egress_expired = True  # public proof only; no private recapture
    node._metric_egress = None
    node._metric_prepare_egress = type(node)._metric_prepare_egress.__get__(node)
    node._global_costmap = inputs[5]
    node._metric_nav_path = None
    node._prealign_handoff_tolerance = .02
    return node, inputs, metadata


@pytest.mark.parametrize('prior_rejection', [False, True])
def test_useful_proved_robot_side_pose_precedes_unsafe_passage_query(prior_rejection):
    node, inputs, _ = fixture()
    policy = MetricTaskPolicy(.6, 30., 2)
    anchor = (1.304999970830977, .13499999698251486)
    key = policy.identify(anchor)
    if prior_rejection:
        attempt = policy.attempts[key]
        attempt.tries = 1
        attempt.reason = 'proposal_rejected'
        attempt.target_xy = (1.304999970830977, .46499998960644007)
        attempt.evidence_key = 'older actual local evidence'
    before = [bytes(np.asarray(inputs[i].data, dtype=np.int8)) for i in (0, 5)]
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan, node._frontier_rank_stats
    candidate = candidates[0]
    assert candidate.task_id == key and candidate.observation_points
    assert node._frontier_rank_stats['robot_side_observation']
    assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None
    distance = math.dist(inputs[2][:2], anchor)
    desired = tuple(anchor[i]+node._approach_dist_m*(inputs[2][i]-anchor[i])/distance for i in (0, 1))
    assert max(abs(candidate.x-desired[0]), abs(candidate.y-desired[1])) <= node._goal_search_m+inputs[0].info.resolution
    assert policy.attempts[key].tries == int(prior_rejection)
    assert policy.attempts[key].failures == 0
    assert [bytes(np.asarray(inputs[i].data, dtype=np.int8)) for i in (0, 5)] == before


def test_original_exhausted_a47_policy_stays_exhausted():
    node, inputs, metadata = fixture()
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    assert policy.attempts['metric-task-2'].tries == 3
    assert node._metric_select(inputs, policy, .3) == []
    assert policy.attempts['metric-task-2'].tries == 3
    assert not policy.attempts['metric-task-2'].completed


def test_robot_side_choice_keeps_an_earlier_served_neighbourhood():
    node, inputs, metadata = fixture()
    state = metadata['checkpoint']
    policy, _ = restore_policy(state, time.monotonic(), state['saved_wall_time'])
    # Model the earlier first rejection, retaining all the other actual
    # failed/served neighbours. This is not the exhausted recorded policy.
    policy.attempts['metric-task-2'].tries = 1
    candidates = node._metric_select(inputs, policy, .3)
    assert candidates and not candidates[0].requires_nav2_plan
    candidate = candidates[0]
    served = policy.attempts['metric-task-5']
    assert served.completed
    assert math.dist((candidate.x, candidate.y), served.target_xy) >= policy.radius
    assert candidate.observation_points
    assert node._metric_waypoints_clear(inputs, candidate.route, candidate.yaw) is not None
    assert policy.attempts['metric-task-2'].tries == 1
    assert policy.attempts['metric-task-4'].failures == 1


def test_without_finite_ray_coverage_robot_side_geometry_grants_no_candidate():
    node, inputs, _ = fixture()
    node._metric_observation_view = lambda: LidarView((.245, 0., math.pi/2), np.array([]), 4., .05)
    assert node._metric_select(inputs, MetricTaskPolicy(.6, 30., 2), .3) == []


@pytest.mark.parametrize('index,valid', [(0, False), (1, True)])
def test_actual_native_door_and_robot_side_paths_keep_full_body_proof(index, valid):
    node, inputs, metadata = fixture()
    record = metadata['plans'][index]
    target = MetricCandidate('component', *record['goal'], tuple(record['goal'][:2]),
                             (), 1., 0., inputs[1].fingerprint, 1)
    route = node._metric_validate_nav_plan(inputs, path(record), target, public_only=True)
    assert (route is not None) is valid
    if valid:
        assert node._metric_departure_plan_ready(inputs, route, target, lambda: False)
    else:
        assert node._metric_last_route_rejection == 'footprint_sweep_invalid'
