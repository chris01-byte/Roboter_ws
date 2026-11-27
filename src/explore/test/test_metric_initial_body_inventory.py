"""Stationary self-body evidence must survive withdrawal into fixed egress."""
import numpy as np

from explore.metric_frontier import StartEgressEvidence
from explore.metric_egress_reference import ReferencedStartEgress
from test_metric_frontier import adaptive_fixture


def fixture():
    node, inputs = adaptive_fixture()
    grid = inputs[0]
    raw = np.zeros((grid.info.height,grid.info.width),dtype=int)
    raw[18:23,9:13] = -1  # within the initial physical body, no exterior bubble
    grid.data = raw.ravel().tolist()
    initial_allowed = raw == 0
    initial_allowed[18:23,9:13] = True  # existing one-shot stationary placement facts
    inside = np.ones(raw.shape,dtype=bool)
    capture = StartEgressEvidence.capture(grid,raw,initial_allowed,inside,
        inputs[2],node._metric_bounds,node._world_to_grid)
    return node,grid,raw,inside,capture


def test_departure_keeps_initial_raw_unknown_even_when_stationary_mask_allowed_it():
    node,grid,raw,inside,capture = fixture()
    assert capture.valid and np.count_nonzero(capture.unknown) == 20
    evidence = ReferencedStartEgress(capture,(0.,0.,0.))
    trajectory = [(float(x),.05,0.) for x in np.linspace(.05,.7,80)]
    valid,reason = evidence.check_trajectory(trajectory,raw,raw == 0,node._world_to_grid)
    assert valid,reason  # stationary whitelist is absent throughout this proof
    exterior = raw.copy();exterior[20,17] = -1
    evidence.refresh(grid,exterior,inside,(0.,0.,0.))
    valid,reason = evidence.check_trajectory(trajectory,exterior,exterior == 0,node._world_to_grid)
    assert not valid and reason == 'start_egress_new_unknown_or_obstacle'


def test_observed_initial_body_cell_is_retired_without_recapture_or_regrowth():
    node,grid,raw,inside,capture = fixture()
    evidence = ReferencedStartEgress(capture,(0.,0.,0.))
    observed = raw.copy();observed[20,11] = 0
    evidence.refresh(grid,observed,inside,(0.,0.,0.))
    area = evidence.retained_region.area
    assert not evidence.fixed.unknown[20,11]
    evidence.refresh(grid,raw,inside,(0.,0.,0.))
    assert evidence.retained_region.area == area
    assert not evidence.unknown[20,11]
    valid,reason = evidence.check_trajectory([(.15,.05,0.)],raw,raw == 0,node._world_to_grid)
    assert not valid and reason == 'start_egress_new_unknown_or_obstacle'
