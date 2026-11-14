"""Recorded native plans require a checked public turn before their RPP leg."""
import math
import numpy as np
import pytest
from explore.metric_frontier import MetricCandidate, lookahead_point, rpp_trajectory, footprint_poses_clear
from test_metric_departure import fixture, path


def recorded():
    n,inputs,meta=fixture('ap06_b63_public_alignment')
    record=meta['plans'][0]
    target=MetricCandidate('recorded',*record['goal'],tuple(record['goal'][:2]),
                           (),1.,0.,inputs[1].fingerprint,1)
    return n,inputs,record,target


def test_corrected_native_cell_center_path_requires_public_alignment_before_motion():
    n,inputs,record,target=recorded()
    before=[list(inputs[i].data) for i in (0,5)]
    route=n._metric_validate_nav_plan(inputs,path(record),target,public_only=True)
    assert route is not None,n._metric_last_route_rejection
    # Native .35-rad handoff alone still clips the real observed door post.
    native=rpp_trajectory(route,inputs[2],inputs[0].info.resolution,.02,n._metric_bounds,
                          prealign_to_first_leg=True,external_prealignment=False)
    assert not all(footprint_poses_clear(native,g,allowed,n._world_to_grid,n._metric_bounds,
                    heading_half_angle=.05,center_deviation_m=.02)
                   for g,allowed in ((inputs[0],inputs[3]),(inputs[5],inputs[6])))
    assert [list(inputs[i].data) for i in (0,5)]==before


def test_candidate_geometry_cannot_borrow_alignment_from_an_unbound_native_path():
    n,inputs,record,target=recorded()
    route=n._metric_validate_nav_plan(inputs,path(record),target,public_only=True)
    assert route is not None
    assert n._metric_standard_waypoints_clear(inputs,route,target.yaw) is None
    assert n._metric_last_route_rejection=='footprint_sweep_invalid'
    assert n._metric_validate_nav_plan(inputs,path(record),target,public_only=True) is not None


def test_checked_public_alignment_uses_actual_carrot_and_existing_turn_owner():
    n,inputs,record,target=recorded()
    route=n._metric_validate_nav_plan(inputs,path(record),target,public_only=True)
    assert route is not None
    calls=[]
    n._prealign_to_goal=lambda *args,**kwargs:(calls.append((args,kwargs)) or ('success',0.,0.,0.))
    stop=lambda:False
    result=n._metric_align_nav_departure(route,inputs[2],stop,inputs=inputs)
    assert result[0]=='success' and len(calls)==1
    assert np.allclose(calls[0][0][:2],lookahead_point(inputs[2][:2],route[1:],.4))
    assert calls[0][0][2]==inputs[2] and calls[0][1]['stop_requested'] is stop


@pytest.mark.parametrize('which',(0,5))
def test_current_raw_unknown_never_authorizes_public_alignment(which):
    n,inputs,record,target=recorded()
    route=(inputs[2][:2],tuple(record['goal'][:2]))
    c,r=n._world_to_grid(*inputs[2][:2],inputs[which].info)
    inputs[which].data[r*inputs[which].info.width+c]=-1
    n._prealign_to_goal=lambda *a,**k:pytest.fail('unknown body cannot authorize a public turn')
    assert n._metric_align_nav_departure(route,inputs[2],lambda:False,inputs=inputs)[0]=='controller_owned'


def test_cancel_prevents_public_alignment_dispatch():
    n,inputs,record,_=recorded();route=(inputs[2][:2],tuple(record['goal'][:2]))
    n._prealign_to_goal=lambda *a,**k:pytest.fail('cancelled public turn was dispatched')
    assert n._metric_align_nav_departure(route,inputs[2],lambda:True,inputs=inputs)[0]=='interrupted'


def test_active_native_child_cannot_borrow_an_imaginary_public_alignment():
    n,inputs,record,target=recorded()
    n._wohnungserkundung_active_child=target
    assert n._metric_validate_nav_plan(inputs,path(record),target,public_only=True) is None
    assert n._metric_last_route_rejection=='footprint_sweep_invalid'
