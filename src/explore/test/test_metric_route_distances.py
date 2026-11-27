"""A selection-local distance field cannot carry routes across input changes."""
import numpy as np
from explore.metric_frontier import route_cells


def test_mask_start_shape_and_corner_changes_keep_actual_reachability():
    cache={};mask=np.ones((9,9),dtype=bool)
    for start in [(0,0),(8,0)]:
        for target in [(8,8),(4,7),(0,8)]:
            assert route_cells(mask,start,target,cache)==route_cells(mask,start,target)
    mask[:,4]=False
    assert route_cells(mask,(0,0),(8,8),cache) is None
    mask[4,4]=True
    assert route_cells(mask,(0,0),(8,8),cache)==route_cells(mask,(0,0),(8,8))
    # No cached diagonal escape around an actually blocked corner.
    mask[:]=False;mask[0,0]=mask[1,1]=True
    assert route_cells(mask,(0,0),(1,1),cache) is None
    reshaped=np.ones((3,27),dtype=bool)
    assert route_cells(reshaped,(0,0),(2,26),cache)==route_cells(reshaped,(0,0),(2,26))


def test_many_maps_cannot_create_unbounded_geometry_history():
    cache={}
    for width in range(3,24):
        mask=np.ones((5,width),dtype=bool)
        assert route_cells(mask,(0,0),(4,width-1),cache)==route_cells(mask,(0,0),(4,width-1))
    assert len(cache)<=8
