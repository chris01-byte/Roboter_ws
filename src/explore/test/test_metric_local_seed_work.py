"""Reduced geometry work must match the original complete raster proof."""
import math
import threading
from types import SimpleNamespace

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid

from explore.explore_node import ExploreNode
from test_metric_frontier import egress_fixture


@pytest.mark.parametrize('angle', [0., .17, -1.4, math.pi/2])
@pytest.mark.parametrize('grid_pose', [(120.49, 119.51), (5.2, 5.6), (300.999, 140.001)])
def test_local_connections_equal_full_raster_for_rotation_edges_and_unknown(angle, grid_pose):
    g = OccupancyGrid()
    g.info.width, g.info.height, g.info.resolution = 320, 160, .01
    g.info.origin.position.x, g.info.origin.position.y = -.153, -1.317
    g.info.origin.orientation.z, g.info.origin.orientation.w = math.sin(angle/2), math.cos(angle/2)
    node = ExploreNode.__new__(ExploreNode)
    node._goal_clearance_m = .1
    unknown = np.zeros((160,320), bool)
    unknown[:, 121] = True
    known = ~unknown
    safe = known.copy()
    safe[::7, ::11] = False
    node._metric_egress = [SimpleNamespace(unknown=np.zeros_like(known))]
    xy = node._grid_to_world(*grid_pose, g.info)
    pose = (*xy, angle+.17)
    sc, sr = node._world_to_grid(*xy, g.info)
    inputs = (g, None, pose, known, safe, None, None)
    expected = []
    for r, c in zip(*np.nonzero(safe)):
        point = node._grid_to_world(c, r, g.info)
        distance = math.dist(pose[:2], point)
        error = abs(math.atan2(math.sin(math.atan2(point[1]-pose[1], point[0]-pose[0])-pose[2]),
                              math.cos(math.atan2(point[1]-pose[1], point[0]-pose[0])-pose[2])))
        if (distance <= node._goal_clearance_m+.25 and error <= .17
                and node._metric_grid_line_clear(known, (sr,sc), (r,c))):
            expected.append((error,point,r,c))
    # Count real scalar projections; no platform-dependent timing assertion.
    projected = []
    original = node._grid_to_world
    def counted(*args):
        projected.append(1)
        return original(*args)
    node._grid_to_world = counted
    assert node._metric_local_route_seeds(inputs,safe,(sr,sc)) == expected
    assert len(projected) < np.count_nonzero(safe) / 4


@pytest.mark.parametrize('ledger', ['remaining_area', 'departed_distance'])
def test_selection_key_preserves_equal_history_and_detects_in_place_ledger_change(ledger):
    node, inputs = egress_fixture()
    node._metric_selection_cache = threading.local()
    node._metric_selection_cache.memo = {'inputs': inputs}
    evidence = node._metric_egress[0]
    values = getattr(evidence, ledger)
    if len(values) < 2:
        values.update({(0,0):.01, (0,1):.02})
    original = node._metric_selection_memo(inputs)[1]
    setattr(evidence, ledger, dict(reversed(tuple(values.items()))))
    assert node._metric_selection_memo(inputs)[1] == original
    key = next(iter(getattr(evidence, ledger)))
    getattr(evidence, ledger)[key] += .001
    assert node._metric_selection_memo(inputs)[1] != original
