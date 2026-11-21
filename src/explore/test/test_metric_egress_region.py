"""Exact first-cell union and scope withdrawal, without freshness relaxation."""
from pathlib import Path
from dataclasses import replace

import numpy as np
import pytest
from shapely.geometry import box
from shapely.ops import unary_union
from explore.metric_egress_reference import cell_region, ReferencedStartEgress
from explore.metric_frontier import StartEgressEvidence
from explore.explore_node import ExploreNode
from test_metric_frontier import egress_fixture


@pytest.mark.parametrize('mask', [
    np.zeros((5, 8), bool),
    np.eye(9, dtype=bool),
    np.array([[1,1,1,1,1], [1,0,1,0,1], [1,1,1,1,1]], bool),
])
def test_union_keeps_each_unknown_cell_and_excludes_free_holes_and_diagonal_gaps(mask):
    expected = unary_union([box(c, r, c+1, r+1) for r, c in zip(*np.nonzero(mask))])
    actual = cell_region(mask)
    assert actual.equals(expected)
    assert actual.area == int(mask.sum())
    for r, c in zip(*np.nonzero(~mask)):
        assert actual.intersection(box(c, r, c+1, r+1)).area == 0.


def test_actual_large_first_inventory_is_exactly_the_original_unit_cell_region():
    from rclpy.serialization import deserialize_message
    from nav_msgs.msg import OccupancyGrid
    p = Path(__file__).parent/'data/ap06_b176_start_raster.npz'
    with np.load(p, allow_pickle=False) as arrays:
        grid = deserialize_message(arrays['controlled01_raw_0'].tobytes(), OccupancyGrid)
    values = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    fixed = StartEgressEvidence.capture(grid, values, values == 0,
        np.ones(values.shape, bool), (0., 0., 0.), (-.13, .33, -.25, .25), ExploreNode._world_to_grid)
    assert fixed.valid and fixed.unknown.sum() == 1082
    before = fixed.unknown.copy()
    evidence = ReferencedStartEgress(fixed, (0., 0., 0.))
    original = unary_union([box(c, r, c+1, r+1) for r, c in zip(*np.nonzero(before))])
    assert evidence.retained_region.equals(original)
    assert np.array_equal(before, evidence.fixed.unknown)


def test_scope_change_between_first_capture_and_refresh_is_not_cached_as_old_scope(monkeypatch):
    from explore import metric_frontier_runtime as runtime
    from explore.portal_memory import Point2D
    node, inputs = egress_fixture()
    node._metric_egress = None  # fresh analytical first capture, no live recovery
    scope = replace(node._metric_scope, scope_id='withdrawn',
        vertices=tuple(Point2D(x,y) for x,y in ((-2.,-2.),(-1.,-2.),(-1.,2.),(-2.,2.))))
    base = runtime.ReferencedStartEgress
    class WithdrawDuringCapture(base):
        def __init__(self, evidence, reference):
            super().__init__(evidence, reference)
            node._metric_scope = scope
    monkeypatch.setattr(runtime, 'ReferencedStartEgress', WithdrawDuringCapture)
    node._metric_input_reference = (0., 0., 0.)
    node._metric_prepare_egress(inputs)
    assert all(not e.valid for e in node._metric_egress)
    assert all(not e.scope_mask.any() for e in node._metric_egress)


def test_raw_and_cost_scope_masks_are_separate_mutable_ledgers():
    from test_metric_egress_reference import referenced_fixture
    node, inputs = referenced_fixture()
    raw, cost = node._metric_egress
    row, col = np.argwhere(raw.scope_mask & cost.scope_mask)[0]
    raw.scope_mask[row, col] = False
    assert cost.scope_mask[row, col]
    assert raw.fixed.scope_mask[row, col]
