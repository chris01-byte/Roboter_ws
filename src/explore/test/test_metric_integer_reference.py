"""Integer projection agrees with the retained exact polygon path."""
import copy
import numpy as np
import pytest

from test_metric_partial_reference import snapshot


@pytest.mark.parametrize('reference_cells', [
    (0.,0.,0.), (3.608224830031759e-14,1.2809848667916232e-14,-5.3234317990218224e-17),
    (1.,0.,0.), (-1.,2.,0.), (.3,0.,0.), (0.,0.,1e-11),
])
@pytest.mark.parametrize('growth', [False, True])
@pytest.mark.parametrize('withdrawal', ['none', 'observation', 'scope'])
def test_reference_growth_and_withdrawal_match_exact_polygon_projection(
        reference_cells, growth, withdrawal):
    _, fast, grid, arrays, _, inside = snapshot()
    exact = copy.deepcopy(fast)
    occupancy = arrays['initial_0'].copy()
    if withdrawal == 'observation':
        rows, cols = np.nonzero(fast.fixed.unknown)
        occupancy[rows[::17],cols[::17]] = 0
    elif withdrawal == 'scope':
        rows, cols = np.nonzero(fast.fixed.unknown)
        inside[rows[::17],cols[::17]] = False
    if growth:
        occupancy = np.pad(occupancy, ((1,2),(2,1)), constant_values=-1)
        inside = np.pad(inside, ((1,2),(2,1)), constant_values=False)
        grid.info.origin.position.x -= 2*grid.info.resolution
        grid.info.origin.position.y -= grid.info.resolution
        grid.info.height, grid.info.width = occupancy.shape
    grid.data = occupancy.ravel().tolist()
    dx, dy, yaw = reference_cells
    reference = (dx*grid.info.resolution,dy*grid.info.resolution,yaw)
    original = fast.fixed.unknown.copy()
    for value in (fast,exact):
        if value is exact:
            # Conservative flag forces the existing GEOS full-cell proof;
            # the same geometric region remains the independent reference.
            value._whole_cells = False
        value.refresh(grid,occupancy,inside,reference)
    assert fast.current_reference == reference  # no rounded or replaced TF
    assert np.array_equal(fast.fixed.unknown,exact.fixed.unknown)
    assert np.array_equal(fast.unknown,exact.unknown)
    assert fast.retained_region.symmetric_difference(exact.retained_region).area <= 1e-9
    assert not np.any(fast.fixed.unknown & ~original)
    assert fast.remaining_area == exact.remaining_area
    assert fast.departed_distance == exact.departed_distance
    # A subsequently unknown raster cannot regain observed or scope permits.
    occupancy[:] = arrays['initial_0'].min()
    for value in (fast,exact):
        if value is exact:
            value._whole_cells = False
        value.refresh(grid,occupancy,inside,reference)
    assert np.array_equal(fast.fixed.unknown,exact.fixed.unknown)
    assert np.array_equal(fast.unknown,exact.unknown)
    assert fast.retained_region.symmetric_difference(exact.retained_region).area <= 1e-9


def test_reference_correction_without_new_rays_keeps_fixed_inventory():
    _, evidence, grid, arrays, _, inside = snapshot()
    original = evidence.fixed.unknown.copy()
    for reference in ((grid.info.resolution,0.,0.), (0.,0.,0.),
                      (3.608224830031759e-16,1.2809848667916232e-16,-5.3234317990218224e-17)):
        evidence.refresh(grid,arrays['initial_0'],inside,reference)
        assert np.array_equal(evidence.fixed.unknown,original)
        assert evidence.retained_region.area == int(original.sum())
