"""Bound first-hit work without changing finite rays, corners or scope."""
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
from nav_msgs.msg import OccupancyGrid

from explore.metric_frontier_candidates import LidarView, visible_boundary_cells
from test_metric_departure import fixture
from test_metric_frontier_candidates import scope_mask

spec = importlib.util.spec_from_file_location('visibility_reference',
    Path(__file__).parent/'data/ap06_visibility_reference.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


@pytest.mark.parametrize('column,blocker', [(15, None), (16, None), (17, None),
    (40, 'wall'), (40, 'scope'), (40, 'near_unknown')])
def test_first_hit_crossing_work_block_preserves_stop_and_no_gain_behind_it(monkeypatch, column, blocker):
    grid = OccupancyGrid(); grid.info.width = 200; grid.info.height = 3
    grid.info.resolution = .03; grid.info.origin.orientation.w = 1.
    data = np.zeros((3, 200), np.int8); data[:, column] = -1
    inside = np.ones(data.shape, bool)
    if blocker == 'wall':
        data[:, 16] = 100
    elif blocker == 'scope':
        inside[:, 16] = False
    elif blocker == 'near_unknown':
        data[:, 16] = -1
    grid.data = data.ravel().tolist()
    view = LidarView((0., 0., 0.), np.zeros(64), 4., .6 if blocker == 'near_unknown' else 0.)
    matrices = []; original = np.floor
    def measured(values):
        matrices.append(values.shape)
        return original(values)
    monkeypatch.setattr('explore.metric_frontier_candidates.np.floor', measured)
    result = visible_boundary_cells(grid, inside, (0., .045, 0.), view)
    assert result == (frozenset() if blocker else frozenset({(1, column)}))
    # Every finite ray still exists; no full-range matrix after a first stop.
    assert matrices and max(shape[1] for shape in matrices) <= 33


@pytest.mark.parametrize('seed', range(12))
def test_incremental_first_hits_match_original_for_rotated_scopes_and_occluders(seed):
    rng = np.random.default_rng(seed)
    grid = OccupancyGrid(); grid.info.width = 70; grid.info.height = 60
    grid.info.resolution = (.03, .1, .2)[seed % 3]
    grid.info.origin.position.x = -.27; grid.info.origin.position.y = .13
    yaw = .37*seed
    grid.info.origin.orientation.z = math.sin(yaw/2)
    grid.info.origin.orientation.w = math.cos(yaw/2)
    data = rng.choice([-1, 0, 100], (60, 70), p=[.05, .93, .02]).astype(np.int8)
    inside = rng.random(data.shape) > .01
    data[20:40, 25:45] = 0; inside[20:40, 25:45] = True
    grid.data = data.ravel().tolist()
    x, y = 35*grid.info.resolution, 30*grid.info.resolution
    pose = (-.27+math.cos(yaw)*x-math.sin(yaw)*y,
            .13+math.sin(yaw)*x+math.cos(yaw)*y, yaw+.17*seed)
    angles = np.linspace(-math.pi, math.pi, 2160, endpoint=False)
    angles = angles[(angles < .9) | (angles > 2.1)]
    view = LidarView((.245, 0., math.pi/2), angles, 4., .05)
    assert visible_boundary_cells(grid, inside, pose, view) == reference.visible_boundary_cells(
        grid, inside, pose, view)


@pytest.mark.parametrize('yaw', [-math.pi, -.7, 0., .7, math.pi/2])
def test_actual_c44_finite_rays_keep_original_first_hit_cells(yaw):
    node, inputs, _ = fixture('ap06_c44_selection')
    arrays = np.load(Path(__file__).parent/'data/ap06_c44_selection.npz')
    view = LidarView((.245, 0., math.pi/2), arrays['angles'], 4., .05)
    inside = scope_mask(node, inputs)
    for xy in (inputs[2][:2], (.3, -.3), (2.8, -.7)):
        assert visible_boundary_cells(inputs[0], inside, (*xy, yaw), view) == reference.visible_boundary_cells(
            inputs[0], inside, (*xy, yaw), view)
