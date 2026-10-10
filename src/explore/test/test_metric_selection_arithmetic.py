"""Exact equivalence of selection arithmetic; no timing/health permission."""
import math
import numpy as np
import pytest
from explore.explore_node import ExploreNode
from explore.metric_frontier import _cell_intersections, _cell_intersections_full
from explore.metric_progress import local_evidence
from test_metric_progress import grid
from test_metric_native_sweep import native


@pytest.mark.parametrize('raw_angle', [0., .17, -math.pi/2])
@pytest.mark.parametrize('cost_angle', [0., -.23, math.pi/2])
@pytest.mark.parametrize('offset', [0., 1e-15, -.035])
def test_batched_seed_projection_matches_scalar_cost_admission(monkeypatch, raw_angle, cost_angle, offset):
    """All cells, including rotated edge contacts and rejected inflated costs."""
    from scipy.ndimage import distance_transform_edt
    from test_metric_frontier import egress_fixture
    node, inputs = egress_fixture()
    raw, _, _, known, _, cost, _ = inputs
    raw.info.origin.orientation.z = math.sin(raw_angle/2)
    raw.info.origin.orientation.w = math.cos(raw_angle/2)
    cost.info.origin.orientation.z = math.sin(cost_angle/2)
    cost.info.origin.orientation.w = math.cos(cost_angle/2)
    cost.info.origin.position.x += offset
    cost.info.origin.position.y -= offset
    cost.data = np.random.default_rng(731).choice([-1, 0, 90, 91, 100], size=len(cost.data)).tolist()
    # This arithmetic-only comparison grants no runtime source/route authority.
    monkeypatch.setattr(node, '_metric_private_start_needed', lambda _: True)
    seed = known | node._metric_egress[0].unknown
    expected = seed & (distance_transform_edt(np.pad(seed, 1))[1:-1, 1:-1]
        *raw.info.resolution >= node._goal_clearance_m+raw.info.resolution/2)
    costs = np.asarray(cost.data).reshape(cost.info.height, cost.info.width)
    for r, c in zip(*np.nonzero(expected)):
        x, y = node._grid_to_world(c, r, raw.info)
        cc, rr = node._world_to_grid(x, y, cost.info)
        if not (0 <= rr < costs.shape[0] and 0 <= cc < costs.shape[1]
                and 0 <= costs[rr, cc] <= node._frontier_goal_max_cost):
            expected[r, c] = False
    assert np.array_equal(node._metric_seed_mask(inputs), expected)


@pytest.mark.parametrize('angle', [0., 1e-15, .17, -1.4, math.pi/2])
@pytest.mark.parametrize('batched', [False, True])
def test_disjoint_clipping_preserves_areas_and_every_contact_vertex(angle, batched):
    rows, cols = np.mgrid[-7:8, -7:8]
    cells = np.column_stack((rows.ravel(), cols.ravel()))
    rotation = np.array([[math.cos(angle),-math.sin(angle)],
                         [math.sin(angle),math.cos(angle)]])
    polygon = np.array([[-1.,-2.],[3.,-2.],[3.,2.],[-1.,2.]]) @ rotation.T
    if batched:
        polygon = np.broadcast_to(polygon,(len(cells),4,2)).copy()
        polygon[::3] += 1e-11  # including contacts close to a cell edge
    expected = _cell_intersections_full(polygon,cells)
    actual = _cell_intersections(polygon,cells)
    assert np.array_equal(actual[0],expected[0])
    assert np.array_equal(actual[2],expected[2])
    assert np.array_equal(actual[1][actual[2]],expected[1][expected[2]])


@pytest.mark.parametrize('angle', [0., 1e-15, .17, -1.4, math.pi/2])
@pytest.mark.parametrize('resolution', [.01, .02, .1])
def test_batched_projection_preserves_original_local_digest(angle, resolution):
    g = grid();g.info.resolution=resolution
    g.info.origin.orientation.z=math.sin(angle/2)
    g.info.origin.orientation.w=math.cos(angle/2)
    values=np.random.default_rng(44).choice([-1,0,100],size=len(g.data))
    g.data=values.tolist()
    to_world=ExploreNode._grid_to_world
    anchors=[to_world(5,5,g.info),to_world(79,39,g.info),(-100.,100.)]
    # Exact radius contact and fractional/rotated raster, not just interior cells.
    point=to_world(25,20,g.info);anchors.append((point[0]+.8,point[1]))
    for anchor in anchors:
        assert local_evidence(g,anchor,to_world,batch_projection=True) == local_evidence(g,anchor,to_world)


@pytest.mark.parametrize('variant', ['original', 'occupied', 'reentry'])
def test_actual_b201_private_trajectory_preserves_original_history_proof(monkeypatch, native, variant):
    import copy
    import json
    from pathlib import Path
    from rclpy.serialization import deserialize_message
    from nav_msgs.msg import OccupancyGrid
    from explore import metric_frontier as module
    from explore.metric_frontier import StartEgressEvidence
    path=Path(__file__).parent/'data/ap06_b201_selection_trajectory'
    rows=json.loads(path.with_suffix('.json').read_text())['rows']
    assert len(rows)==2  # original raw and cost private ledgers
    with np.load(path.with_suffix('.npz'),allow_pickle=False) as data:
        for index,row in enumerate(rows):
            def array(key):return data[f'{index}_{key}'].copy()
            evidence=StartEgressEvidence(
                deserialize_message(array('grid').tobytes(),OccupancyGrid),
                tuple(row['pose']),tuple(row['bounds']),array('unknown'),
                tuple(tuple(p) for p in row['initial_polygon']),row['valid'],row['reason'],
                {(r,c):v for r,c,v in row['remaining_area']},
                {(r,c):v for r,c,v in row['departed_distance']},array('scope'))
            poses,occupancy,allowed=array('poses'),array('occupancy'),array('allowed')
            if variant=='occupied':
                r,c=np.argwhere(evidence.unknown)[0];occupancy[r,c]=100;allowed[r,c]=False
            results=[]
            for clip, distance in ((_cell_intersections_full,module._cell_distances_numpy),
                                   (_cell_intersections,module._cell_distances)):
                monkeypatch.setattr(module,'_cell_intersections',clip)
                monkeypatch.setattr(module,'_cell_distances',distance)
                current=copy.deepcopy(evidence)
                result=current.check_trajectory(poses,occupancy,allowed,
                    ExploreNode._world_to_grid,commit=True)
                if variant=='reentry' and result[0]:
                    result=current.check_trajectory(poses[::-1],occupancy,allowed,
                        ExploreNode._world_to_grid,commit=True)
                    assert not result[0]
                results.append((result,current.remaining_area,current.departed_distance,current.valid))
            assert results[0]==results[1]
