"""v17 A: a nominal one-cell SLAM correction is a whole-cell lattice shift.

slam_toolbox corrects map->odom in exact float64 steps of its search
resolution (0.01 m), while OccupancyGrid.info.resolution is float32
(0.009999999776...). One correction step therefore maps to 1.0000000224
cells. A 2e-8 cell (0.2 nm) representation residue must not divert the
inventory into the partial-cell path, where it erodes boundary cells and
invalidates the start egress (original v17 door68_start_a,
start_reference.current = (-0.010000000000000064, 0, 0)).
"""
import copy
import numpy as np
from explore.metric_egress_reference import LATTICE_TOLERANCE_CELLS, lattice_offset
from test_metric_partial_reference import snapshot


def _refreshed(reference):
    node, evidence, grid, a, m, inside = snapshot()
    occupancy = a['initial_0']
    grid = copy.deepcopy(grid)
    grid.data = occupancy.ravel().tolist()
    evidence.refresh(grid, occupancy, inside, reference)
    return evidence


def test_nominal_one_cell_correction_equals_exact_lattice_shift():
    node, evidence, grid, a, m, inside = snapshot()
    resolution = grid.info.resolution            # float32 value as float64
    nominal = round(resolution, 6)                # float64 decimal, like 0.01
    assert 1e-9 < abs(nominal/resolution-1.) < LATTICE_TOLERANCE_CELLS
    exact = _refreshed((resolution, 0., 0.))
    corrected = _refreshed((nominal, 0., 0.))
    assert np.array_equal(corrected.fixed.unknown, exact.fixed.unknown)
    assert np.array_equal(corrected.unknown, exact.unknown)
    assert corrected.retained_region.area == exact.retained_region.area
    assert corrected.valid == exact.valid


def test_lattice_tolerance_absorbs_float32_residue_but_not_real_shifts():
    node, evidence, grid, a, m, inside = snapshot()
    resolution = grid.info.resolution
    target = evidence.fixed.grid
    identity = (0., 0., 0.)
    # Sign convention: offset is the target index of the source origin.
    assert list(lattice_offset(grid, (round(resolution, 6), 0., 0.), target, identity)) == [-1, 0]
    assert list(lattice_offset(grid, (-round(resolution, 6), 0., 0.), target, identity)) == [1, 0]
    # Genuine sub-cell shifts and rotations keep the exact polygon path.
    assert lattice_offset(grid, (resolution/2, 0., 0.), target, identity) is None
    assert lattice_offset(grid, (resolution*1.001, 0., 0.), target, identity) is None
    assert lattice_offset(grid, (0., 0., 1e-4), target, identity) is None


def test_first_body_survives_map_growth_with_float32_origins():
    """Raster growth shifts the origin by whole cells, stored as float32."""
    from types import SimpleNamespace
    from explore.metric_frontier_runtime import MetricFrontierRuntime
    resolution = float(np.float32(0.01))
    cells = np.zeros((40, 50), dtype=bool)
    cells[10:14, 20:25] = True
    old_origin = (float(np.float32(-5.12)), float(np.float32(-0.92)))
    new_origin = (float(np.float32(-5.12-0.01*37)), float(np.float32(-0.92-0.01*5)))
    node = SimpleNamespace(_metric_body_cells=cells.copy(),
        _metric_body_grid_identity=('ctx', 50, 40, resolution, old_origin, 0.))
    grown = ('ctx', 100, 60, resolution, new_origin, 0.)
    assert MetricFrontierRuntime._metric_rebase_first_body(node, grown)
    assert node._metric_body_cells.shape == (60, 100)
    assert node._metric_body_cells.sum() == cells.sum()
    assert node._metric_body_cells[15:19, 57:62].all()
    # A genuine half-cell origin change is not the same lattice.
    node = SimpleNamespace(_metric_body_cells=cells.copy(),
        _metric_body_grid_identity=('ctx', 50, 40, resolution, old_origin, 0.))
    shifted = ('ctx', 100, 60, resolution, (old_origin[0]-0.005, old_origin[1]), 0.)
    assert not MetricFrontierRuntime._metric_rebase_first_body(node, shifted)
