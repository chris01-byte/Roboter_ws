"""Initial private placement cells never become public return authority."""
import numpy as np
import pytest
from test_metric_map_lifecycle import runtime


@pytest.mark.parametrize('distance',[.12,.7])
def test_actual_bound_callbacks_retire_departed_placement_cells_without_regrowth(monkeypatch,distance):
    n,g=runtime(monkeypatch,placement_shadow=True,body_reference=(0.,0.,0.))
    first=n._metric_inputs()
    unknown=np.asarray(g.data).reshape(first[3].shape)<0
    initial=first[3]&unknown
    assert initial.any()
    source=first[1];captured=[e.fixed.unknown.copy() for e in n._metric_egress]
    n._robot_pose_sample=lambda:((.05+distance,.05,0.),0.)
    departed=n._metric_inputs()
    remaining=departed[3]&unknown
    assert np.count_nonzero(remaining)<np.count_nonzero(initial)
    if distance==.7:assert not remaining.any()
    assert not (remaining&~initial).any()
    n._robot_pose_sample=lambda:((.05,.05,0.),0.)
    returned=n._metric_inputs()
    assert not ((returned[3]&unknown)&~remaining).any()
    assert list(g.data)==list(first[0].data) and returned[1]==source
    assert all(np.array_equal(e.fixed.unknown,old) for e,old in zip(n._metric_egress,captured))


def test_virtual_current_body_needs_real_private_egress_for_a_turn(monkeypatch):
    n,g=runtime(monkeypatch,placement_shadow=True,body_reference=(0.,0.,0.))
    n._metric_path_validation='rpp_rollout';inputs=n._metric_inputs()
    assert (inputs[3]&(np.asarray(g.data).reshape(inputs[3].shape)<0)).any()
    assert n._metric_waypoints_clear(inputs,((.05,.05),(.75,.05)),0.) is not None
    # Formerly every raw unknown was whitelisted, so the ordinary checker
    # silently authorized rotation without the private monotone proof.
    assert n._metric_waypoints_clear(inputs,((.05,.05),(.05,.75)),np.pi/2) is None


def test_recorded_b60_public_selection_never_uses_82_old_private_raw_unknowns(monkeypatch):
    import time
    import explore.metric_frontier_runtime as module
    from test_metric_public_cooldown import frozen
    n,inputs,p=frozen();now=time.monotonic()
    original=np.asarray(inputs[0].data).reshape(inputs[3].shape)
    private=inputs[3]&(original<0)
    assert np.count_nonzero(private)==82
    monkeypatch.setattr(module.time,'monotonic',lambda:now+31.)
    n._global_costmap_received_at=now+31.
    choices=n._metric_select(inputs,p,.3)
    assert choices
    public=(inputs[0],inputs[1],inputs[2],inputs[3]&(original==0),*inputs[4:])
    for c in choices:
        assert c.observation_points
        assert n._metric_standard_waypoints_clear(public,c.route,c.yaw) is not None
    assert np.count_nonzero(private)==82  # input/raw evidence never rewritten
    assert p.attempts['metric-task-1'].completed and p.attempts['metric-task-1'].tries==1


def test_fully_observed_current_body_cannot_take_the_initial_departure_exception():
    from test_metric_frontier import adaptive_fixture
    from explore.metric_frontier import MetricTaskPolicy
    from explore.metric_frontier_candidates import LidarView
    n,inputs=adaptive_fixture()
    n._metric_start_egress_enabled=True;n._metric_egress=None
    n._metric_egress_identity=None;n._metric_egress_expired=False
    n._metric_body_anchor_expired=False;n._metric_body_reference=lambda:None
    n._metric_path_validation='rpp_rollout';n._metric_candidate_source='boundary_samples'
    n._metric_status={}
    n._metric_observation_view=lambda:LidarView((.245,0.,np.pi/2),
                                               np.linspace(-np.pi,np.pi,360),4.,.05)
    choices=n._metric_select(inputs,MetricTaskPolicy(.6,30.,2),.3)
    assert choices and all(e.valid for e in n._metric_egress)
    assert not any(e.unknown.any() for e in n._metric_egress)
    assert not n._frontier_rank_stats.get('bounded_start_observation',False)
