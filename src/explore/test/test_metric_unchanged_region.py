"""Unchanged physical authority can reuse geometry, never a live verdict."""
import copy
import numpy as np
import pytest

from explore import metric_egress_reference as module
from test_metric_partial_reference import snapshot


def test_subcell_reference_only_reuses_region_but_projects_current_cells(monkeypatch):
    node,evidence,grid,arrays,metadata,inside = snapshot()
    region = evidence.retained_region
    retained = evidence.fixed.unknown.copy()
    original = module.positive_cell_intersections
    calls = []
    def counted(*args):
        calls.append(True)
        return original(*args)
    monkeypatch.setattr(module,'positive_cell_intersections',counted)
    views = []
    for dx in (.01,.011,0.):
        reference=(dx,0.,0.)
        evidence.refresh(grid,arrays['initial_0'],inside,reference)
        assert evidence.current_reference == reference
        assert evidence.retained_region is region
        assert np.array_equal(evidence.fixed.unknown,retained)
        views.append(evidence.unknown.copy())
    assert not calls  # no repeated test of unchanged fixed physical cells
    assert not np.array_equal(views[0],views[-1])
    assert np.array_equal(views[-1],retained)
    # The full current contour and original departure ledger are still checked.
    valid,reason=evidence.check_trajectory([(0.08685,0.,0.)],arrays['initial_0'],
        arrays['initial_0']==0,node._world_to_grid,commit=True)
    assert valid,reason
    before=copy.deepcopy(evidence.remaining_area)
    valid,reason=evidence.check_trajectory([(0.,0.,0.)],arrays['initial_0'],
        arrays['initial_0']==0,node._world_to_grid,commit=True)
    assert not valid
    assert reason in ('start_egress_approaches_unknown','start_egress_reentry_or_added_cell_area')
    assert evidence.remaining_area == before


@pytest.mark.parametrize('withdrawal',['observation','scope','extent'])
def test_real_physical_withdrawal_rechecks_fixed_cells_and_never_regrows(monkeypatch,withdrawal):
    _,evidence,grid,arrays,_,inside = snapshot()
    region = evidence.retained_region
    occupancy=arrays['initial_0'].copy()
    original=module.positive_cell_intersections
    calls=[]
    def counted(*args):
        calls.append(True)
        return original(*args)
    monkeypatch.setattr(module,'positive_cell_intersections',counted)
    row,col=np.argwhere(evidence.fixed.unknown)[0]
    if withdrawal=='observation':
        occupancy[row,col]=0
    elif withdrawal=='scope':
        inside[row,col]=False
    else:
        occupancy=occupancy[:row+1,:]
        inside=inside[:row+1,:]
        grid.info.height=occupancy.shape[0]
    grid.data=occupancy.ravel().tolist()
    # Noninteger correction keeps the actual exact polygon path active.
    evidence.refresh(grid,occupancy,inside,(.011,0.,0.))
    assert calls
    assert evidence.retained_region is not region
    assert evidence.retained_region.area < region.area
    retired=evidence.fixed.unknown.copy()
    retained_area=evidence.retained_region.area
    occupancy[:]=-1
    grid.data=occupancy.ravel().tolist()
    evidence.refresh(grid,occupancy,inside,(.011,0.,0.))
    assert not np.any(evidence.fixed.unknown & ~retired)
    assert evidence.retained_region.area <= retained_area+1e-9
