"""Whole-body sweep keeps every scalar guard while reducing allocations."""
import math
import numpy as np
import pytest
from explore.metric_frontier import footprint_clear, footprint_cells, footprint_poses_clear
from test_metric_motion_geometry import door_inputs


@pytest.mark.parametrize('origin_yaw',[0.,.17,-.42])
@pytest.mark.parametrize('reserve',[(0.,0.),(.05,.02),(.4,.15)])
def test_batch_sweep_preserves_occupied_unknown_scope_edges_and_full_reserves(origin_yaw,reserve):
    node,inputs=door_inputs(.68,.02);grid=inputs[0]
    grid.info.origin.orientation.z=math.sin(origin_yaw/2)
    grid.info.origin.orientation.w=math.cos(origin_yaw/2)
    rng=np.random.default_rng(602)
    # Ordered straight/corner poses plus grid edges; compare genuine guards
    # on both a free corridor and mixed observed/occupied/unknown mask.
    poses=np.column_stack((np.linspace(-1.8,1.8,80),np.linspace(-.7,.7,80),
                           rng.uniform(-math.pi,math.pi,80)))
    for mask in (inputs[3],rng.random(inputs[3].shape)>.08,np.ones(inputs[3].shape,dtype=bool)):
        for chunk in np.array_split(poses,10):
            expected=all(footprint_clear(*p,grid,mask,node._world_to_grid,
                node._grid_to_world,node._metric_bounds,heading_half_angle=reserve[0],
                center_deviation_m=reserve[1]) for p in chunk)
            assert footprint_poses_clear(chunk,grid,mask,node._world_to_grid,node._metric_bounds,
                heading_half_angle=reserve[0],center_deviation_m=reserve[1]) is expected


def test_actual_door_sweep_keeps_rotational_and_new_obstacle_rejection():
    node,inputs=door_inputs(.68,.02);grid=inputs[0];mask=inputs[3].copy()
    straight=np.column_stack((np.linspace(-.9,.9,181),np.zeros(181),np.zeros(181)))
    assert footprint_poses_clear(straight,grid,mask,node._world_to_grid,
        node._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)
    turning=straight.copy();turning[90,2]=math.pi/2
    assert not footprint_poses_clear(turning,grid,mask,node._world_to_grid,
        node._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)
    col,row=node._world_to_grid(0.,0.,grid.info);mask[row,col]=False
    assert not footprint_poses_clear(straight,grid,mask,node._world_to_grid,
        node._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)


@pytest.mark.parametrize('origin_yaw',[0.,.17])
def test_clear_nominal_heading_still_checks_reserved_heading_extremes(origin_yaw):
    node,inputs=door_inputs(.68,.02);grid=inputs[0]
    grid.info.origin.orientation.z=math.sin(origin_yaw/2)
    grid.info.origin.orientation.w=math.cos(origin_yaw/2)
    pose=(.2,.2,.23);mask=np.ones(inputs[3].shape,bool)
    nominal=set(zip(*footprint_cells(*pose,grid,node._world_to_grid,node._metric_bounds,
        heading_half_angle=0.,center_deviation_m=.02)))
    swept=set(zip(*footprint_cells(*pose,grid,node._world_to_grid,node._metric_bounds,
        heading_half_angle=.05,center_deviation_m=.02)))
    assert swept-nominal
    for row,col in swept-nominal:
        mask[row,col]=False
        assert footprint_clear(*pose,grid,mask,node._world_to_grid,node._grid_to_world,
            node._metric_bounds,heading_half_angle=0.,center_deviation_m=.02)
        assert not footprint_poses_clear([pose],grid,mask,node._world_to_grid,
            node._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)
        mask[row,col]=True


@pytest.mark.parametrize('origin_yaw',[0.,.17])
@pytest.mark.parametrize('yaw',[0.,.05,-.05,math.pi/4,math.pi,-math.pi/2])
def test_single_forbidden_reserved_cell_keeps_scalar_corner_and_heading_authority(origin_yaw,yaw):
    node,inputs=door_inputs(.68,.02);grid=inputs[0]
    grid.info.origin.orientation.z=math.sin(origin_yaw/2)
    grid.info.origin.orientation.w=math.cos(origin_yaw/2)
    pose=(.2+1e-12,.2-1e-12,yaw)
    mask=np.ones(inputs[3].shape,bool)
    rr,cc=footprint_cells(*pose,grid,node._world_to_grid,node._metric_bounds,
                          heading_half_angle=.05,center_deviation_m=.02)
    assert footprint_poses_clear([pose],grid,mask,node._world_to_grid,node._metric_bounds,
                                heading_half_angle=.05,center_deviation_m=.02)
    # Test isolated forbidden cells, including the sampled rotated corners;
    # another nearby obstruction must not conceal a wrongly omitted cell.
    for index in np.unique(np.linspace(0,len(rr)-1,40,dtype=int)):
        mask[rr[index],cc[index]]=False
        assert not footprint_clear(*pose,grid,mask,node._world_to_grid,node._grid_to_world,
            node._metric_bounds,heading_half_angle=.05,center_deviation_m=.02)
        assert not footprint_poses_clear([pose],grid,mask,node._world_to_grid,node._metric_bounds,
            heading_half_angle=.05,center_deviation_m=.02)
        mask[rr[index],cc[index]]=True
