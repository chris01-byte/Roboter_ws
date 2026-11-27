"""B65's ideal endpoint advertises sight that disappears at the RPP stop.

Own recorded synthetic rasters, measured finite scan bins and original policy;
no live source health, hardware motion or whole-mission receipt is supplied.
"""
from dataclasses import replace
import math
import time
import pytest

from explore.metric_frontier import MetricCandidate, MetricTaskPolicy, MetricAttempt
from explore.metric_frontier_candidates import visible_boundary_cells
from test_metric_robot_side_observation import fixture


def recorded():
    node,inputs,metadata=fixture('ap06_b65_stop_observation')
    stored=metadata['policy']
    policy=MetricTaskPolicy(stored['radius'],stored['cooldown_s'],stored['retry_limit'])
    policy.next_id=stored['next_id']
    for key,value in stored['tasks'].items():
        fields=dict(value)
        fields['retry_after']=time.monotonic()+fields.pop('retry_remaining_s')
        fields['frontier_xy']=tuple(fields['frontier_xy'])
        fields['target_xy']=tuple(fields['target_xy'])
        policy.attempts[key]=MetricAttempt(**fields)
    bad=metadata['candidate']
    candidate=MetricCandidate('original-b65',*bad['goal'],tuple(bad['frontier']),
        tuple(tuple(p) for p in bad['route']),.6,0.,inputs[1].fingerprint,
        inputs[1].map_revision,False,tuple(tuple(p) for p in bad['points']))
    return node,inputs,metadata,policy,candidate


def test_original_b65_endpoint_opportunity_does_not_authorize_its_native_stop():
    node,inputs,_,_,candidate=recorded()
    mask=node._metric_scope_mask(inputs)
    view=node._metric_observation_view()
    nominal=visible_boundary_cells(inputs[0],mask,(candidate.x,candidate.y,candidate.yaw),view)
    points={node._grid_to_world(c,r,inputs[0].info) for r,c in nominal}
    assert len(points.intersection(candidate.observation_points))==24
    original=[list(inputs[i].data) for i in (0,5)]
    assert not node._metric_native_observation_ready(
        inputs,candidate.route,candidate,inputs,candidate.observation_points)
    assert node._metric_status['native_stop_observation']['potential_points']==0
    assert [list(inputs[i].data) for i in (0,5)]==original


def test_public_selection_rejects_false_view_and_keeps_original_cooldown_history():
    from test_metric_public_cooldown import frozen
    _,_,_,_,bad=recorded()
    node,inputs,policy=frozen('ap06_b65_selection_exact')
    assert not node._metric_egress_expired
    assert all(not e.valid and not e.unknown.any() for e in node._metric_egress)
    before={k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items()}
    selected=node._metric_select(inputs,policy,.3)
    for candidate in selected:
        assert (candidate.x,candidate.y,candidate.yaw)!=(bad.x,bad.y,bad.yaw)
        if not candidate.requires_nav2_plan:
            stop=node._metric_rollout_stop_pose(inputs,candidate.route,candidate.yaw)
            visible=visible_boundary_cells(inputs[0],node._metric_scope_mask(inputs),stop,
                                           node._metric_observation_view())
            points={node._grid_to_world(c,r,inputs[0].info) for r,c in visible}
            assert points.intersection(candidate.observation_points)
    if not selected:
        # The original capture is immediately after task 1's observation.
        # A truthful bounded cooldown wait is preferable to its false view.
        assert 0 < node._frontier_rank_stats['bounded_public_observation_wait_s'] <= policy.cooldown_s
    assert before=={k:(policy.attempts[k].tries,policy.attempts[k].failures,
                       policy.attempts[k].completed) for k in before}


def test_native_stop_can_authorize_a_distinct_finite_unknown_view_without_a_receipt():
    node,inputs,_,_,candidate=recorded()
    stop=node._metric_rollout_stop_pose(inputs,candidate.route,candidate.yaw,native_plan=True)
    visible=visible_boundary_cells(inputs[0],node._metric_scope_mask(inputs),stop,
                                   node._metric_observation_view())
    assert visible
    r,c=next(iter(visible));point=node._grid_to_world(c,r,inputs[0].info)
    task=replace(candidate,task_id='distinct-boundary',frontier_xy=point,
                 observation_points=(point,))
    assert node._metric_native_observation_ready(inputs,task.route,task,inputs,(point,))
    assert node._metric_status['native_stop_observation']['potential_points']==1
    assert math.dist(stop[:2],(candidate.x,candidate.y))<=.15


def test_original_b65_after_cooldown_can_observe_from_a_wholly_public_turning_refuge():
    from test_metric_public_cooldown import frozen
    # Hypothetical elapsed original cooldown on the frozen geometry only;
    # processing deadlines still use a continuously advancing real clock.
    node,inputs,policy=frozen('ap06_b65_selection_exact',elapsed_s=31.)
    before={k:(a.tries,a.failures,a.completed) for k,a in policy.attempts.items()}
    candidates=node._metric_select(inputs,policy,.3)
    assert candidates and not candidates[0].requires_nav2_plan,node._frontier_rank_stats
    candidate=candidates[0]
    stop=node._metric_rollout_stop_pose(inputs,candidate.route,candidate.yaw)
    assert node._metric_scan_geometry_ready((inputs[0],inputs[1],stop,*inputs[3:]))
    assert node._metric_waypoints_clear(inputs,candidate.route,candidate.yaw) is not None
    visible=visible_boundary_cells(inputs[0],node._metric_scope_mask(inputs),stop,
                                   node._metric_observation_view())
    actual_points={node._grid_to_world(c,r,inputs[0].info) for r,c in visible}
    assert set(candidate.observation_points)<=actual_points
    assert before=={k:(policy.attempts[k].tries,policy.attempts[k].failures,
                       policy.attempts[k].completed) for k in before}


def test_native_stop_requires_a_current_finite_scan_view():
    node,inputs,_,_,candidate=recorded()
    def stale_view():
        raise ValueError('candidate_lidar_stamp_stale')
    node._metric_observation_view=stale_view
    with pytest.raises(ValueError,match='candidate_lidar_stamp_stale'):
        node._metric_native_observation_ready(inputs,candidate.route,candidate,
                                               inputs,candidate.observation_points)
    assert 'native_stop_observation' not in node._metric_status
