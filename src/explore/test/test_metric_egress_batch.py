"""Exact retained inventory at real B186 updates; scalar compatibility too."""
import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from rclpy.serialization import deserialize_message
from nav_msgs.msg import OccupancyGrid
from explore import metric_egress_reference as reference
from explore.explore_node import ExploreNode
from explore.metric_frontier_runtime import MetricInputs
from explore.exploration_scope import AuthorizedExplorationScope
from explore.portal_memory import PortalMapContext, Point2D
from explore.portal_source_adapter import PortalSourceCorrelation


@pytest.mark.parametrize('batched', [False, True])
@pytest.mark.parametrize('offset', [0., 1e-11, 1e-7, .5])
def test_exact_cell_authority_matches_scalar_boolean_areas(monkeypatch, batched, offset):
    if batched and not reference._BATCHED_GEOS:
        pytest.skip('Shapely 1.x exercises the scalar compatibility path')
    monkeypatch.setattr(reference, '_BATCHED_GEOS', batched)
    # Hole, disconnected cells, subpixel boundary and actual half-cell loss.
    region = unary_union([box(0,0,4,1),box(0,1,1,4),box(3,1,4,4),box(1,3,3,4),box(6,6,7,7)])
    cells = np.array([(r,c) for r in range(8) for c in range(8)])
    corners = reference.squares(cells) + (offset, 0.)
    retained = [region.intersection(box(c,r,c+1,r+1)).area > 1e-9 for r,c in cells]
    covered = [Polygon(p).difference(region).area <= 1e-9 for p in corners]
    assert np.array_equal(reference.positive_cell_intersections(region,cells),retained)
    assert np.array_equal(reference.fully_covered_polygons(region,corners),covered)


@pytest.mark.parametrize('batched', [False, True])
def test_recorded_b186_reference_updates_preserve_the_same_first_inventory(monkeypatch, batched):
    if batched and not reference._BATCHED_GEOS:
        pytest.skip('Shapely 1.x exercises the scalar compatibility path')
    monkeypatch.setattr(reference, '_BATCHED_GEOS', batched)
    path = Path(__file__).parent/'data/ap06_b186_decision_inputs'
    meta = json.loads(path.with_suffix('.json').read_text())
    node = ExploreNode.__new__(ExploreNode)
    context = PortalMapContext('diagnostic','b186','map')
    node._metric_scope = AuthorizedExplorationScope('b186',context,
        tuple(Point2D(*p) for p in meta['rows'][0]['scope']))
    node._metric_bounds = tuple(meta['rows'][0]['bounds'])
    node._metric_start_egress_enabled = True
    node._metric_egress = None
    node._metric_egress_expired = node._metric_body_anchor_expired = False
    node._wohnungserkundung_evidence_max_cells = 1000000
    node._metric_status = {}
    identity = None
    with np.load(path.with_suffix('.npz'),allow_pickle=False) as data:
        for i,row in enumerate(meta['rows']):
            raw,cost = [deserialize_message(data[f'{i}_{key}'].tobytes(),OccupancyGrid)
                        for key in ('raw_cdr','cost_cdr')]
            a = np.asarray(raw.data).reshape(raw.info.height,raw.info.width)
            b = np.asarray(cost.data).reshape(cost.info.height,cost.info.width)
            inputs = MetricInputs((raw,PortalSourceCorrelation(context,0,'diagnostic',1),
                tuple(row['pose']),a==0,np.zeros_like(a,bool),cost,(b>=0)&(b<100)),
                row['reference'],row['physical_motion'])
            node._metric_prepare_egress(inputs)
            if identity is None:
                identity = node._metric_egress
            assert node._metric_egress is identity
            assert all(e.valid for e in identity)
            assert [int(e.unknown.sum()) for e in identity] == [1082,13]
            assert [int(e.fixed.unknown.sum()) for e in identity] == [1082,13]
    # A later observation retires authority, even on the same tiny TF offsets.
    for evidence in identity:
        grid = evidence.grid
        values = np.asarray(grid.data).reshape(evidence.unknown.shape).copy()
        row,col = np.argwhere(evidence.unknown)[0]
        values[row,col] = 100
        evidence.refresh(grid,values,evidence.scope_mask,evidence.current_reference)
        assert not evidence.unknown[row,col]
        values[row,col] = -1
        evidence.refresh(grid,values,evidence.scope_mask,evidence.current_reference)
        assert not evidence.unknown[row,col]


def test_empty_region_and_empty_candidates_keep_no_authority():
    empty = Polygon()
    cells = np.array([[0,0]])
    assert not reference.positive_cell_intersections(empty,cells).any()
    assert not reference.fully_covered_polygons(empty,reference.squares(cells)).any()
    assert reference.positive_cell_intersections(empty,cells[:0]).size == 0
    assert reference.fully_covered_polygons(empty,np.empty((0,4,2))).size == 0
