"""Measured native TF correction: retire only observed physical portions."""
import copy
import json
from pathlib import Path
import numpy as np
from explore.metric_egress_reference import ReferencedStartEgress
from explore.metric_frontier import StartEgressEvidence
from test_metric_start_observation import fixture


def snapshot():
    data=Path(__file__).parent/'data'
    arrays=np.load(data/'ap06_reference_partial_cells.npz')
    metadata=json.loads((data/'ap06_reference_partial_cells.json').read_text())
    node,inputs,_=fixture();grid=copy.deepcopy(inputs[0])
    geometry=metadata['rasters'][0]['initial']
    grid.info.height,grid.info.width=geometry['shape']
    grid.info.resolution=geometry['resolution']
    grid.info.origin.position.x,grid.info.origin.position.y=geometry['origin']
    initial=arrays['initial_0'];grid.data=initial.ravel().tolist()
    inside=np.ones(initial.shape,dtype=bool)
    captured=StartEgressEvidence.capture(grid,initial,initial==0,inside,
        (0.,0.,0.),node._metric_bounds,node._world_to_grid)
    assert captured.valid and np.array_equal(captured.unknown,arrays['inventory_before_0'])
    current=copy.deepcopy(grid);current.data=arrays['current_0'].ravel().tolist()
    evidence=ReferencedStartEgress(captured,(0.,0.,0.))
    return node,evidence,current,arrays,metadata,inside


def test_actual_one_centimetre_reference_correction_preserves_proved_departure():
    node,evidence,grid,a,m,inside=snapshot()
    original=evidence.fixed.unknown.copy()
    evidence.refresh(grid,a['current_0'],inside,m['reference'])
    valid,reason=evidence.check_trajectory([m['pose']],a['current_0'],a['known_0'],
                                         node._world_to_grid,commit=True)
    assert valid,reason
    assert not np.any(evidence.fixed.unknown & ~original)
    # All new rays in this snapshot lie outside the initial inventory.
    # A TF correction alone cannot invent an observation of its boundary.
    assert evidence.retained_region.area == original.sum()
    # Whole current unknown cells require real coverage even when an original
    # cell has both retained unknown and permanently observed physical parts.
    assert evidence.unknown[40,38]


def test_observed_partial_cell_never_regains_authority_after_map_turns_unknown():
    node,evidence,grid,a,m,inside=snapshot();occupancy=a['current_0'].copy()
    evidence.refresh(grid,occupancy,inside,m['reference'])
    assert evidence.unknown[40,38]
    occupancy[40,38]=0
    evidence.refresh(grid,occupancy,inside,m['reference'])
    retired_area=evidence.retained_region.area
    occupancy[40,38]=-1
    evidence.refresh(grid,occupancy,inside,m['reference'])
    assert evidence.retained_region.area<=retired_area+1e-9
    assert not evidence.unknown[40,38]
    known=a['known_0'].copy();known[40,38]=False
    valid,reason=evidence.check_trajectory([m['pose']],occupancy,known,node._world_to_grid)
    assert not valid and reason=='start_egress_new_unknown_or_obstacle'


def test_reference_refinement_without_new_measurement_cannot_retire_inventory():
    node,evidence,grid,a,m,inside=snapshot()
    occupancy=a['initial_0'];original=evidence.retained_region.area
    evidence.refresh(grid,occupancy,inside,m['reference'])
    evidence.refresh(grid,occupancy,inside,(0.,0.,0.))
    assert evidence.retained_region.area==original
    assert np.array_equal(evidence.unknown,a['inventory_before_0'])
    valid,reason=evidence.check_trajectory([(0.08685,0.,0.)],occupancy,
        occupancy==0,node._world_to_grid,commit=True)
    assert valid,reason


def test_measured_goal_retains_fixed_first_body_proof_on_tf_refinement(monkeypatch):
    from types import SimpleNamespace
    from dataclasses import replace
    from geometry_msgs.msg import TransformStamped
    from explore.portal_source_adapter import raw_map_portal_source_from_values
    from explore.metric_frontier import footprint_clear
    from test_metric_frontier import body_input_fixture
    node,evidence,grid,arrays,metadata,inside=snapshot()
    runtime=body_input_fixture(monkeypatch,10.01)
    runtime._robot_pose_sample=lambda:((0.,0.,0.),0.)
    grid.header.stamp.sec=100
    source=raw_map_portal_source_from_values(**runtime._metric_grid_values(grid))
    runtime._metric_raw=(grid,source,10.)
    runtime._metric_correlation=replace(runtime._metric_correlation,fingerprint=source.fingerprint)
    runtime._global_costmap=grid
    transform=TransformStamped();transform.header.stamp.sec=100
    transform.transform.rotation.w=1.
    runtime._tf_buffer=SimpleNamespace(lookup_transform=lambda *_:transform)
    first=runtime._metric_inputs()[3].copy()
    transform.transform.translation.x=.01
    runtime._robot_pose_sample=lambda:(tuple(metadata['pose']),0.)
    current=runtime._metric_inputs()[3]
    assert np.array_equal(first,current)
    assert footprint_clear(.36,0.,0.,grid,current,node._world_to_grid,node._grid_to_world,
        node._metric_bounds,heading_half_angle=.4,center_deviation_m=.15)
    # A real obstacle at the same first-body cell remains forbidden.
    row,col=47,43
    grid.data[row*grid.info.width+col]=100
    source=raw_map_portal_source_from_values(**runtime._metric_grid_values(grid))
    runtime._metric_raw=(grid,source,10.)
    runtime._metric_correlation=replace(runtime._metric_correlation,fingerprint=source.fingerprint)
    assert not runtime._metric_inputs()[3][row,col]
