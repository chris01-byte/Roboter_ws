"""Same measured finite scan, native SLAM rasters; component, no mission claim."""
import json
from pathlib import Path

import numpy as np
import pytest
import yaml
from nav_msgs.msg import OccupancyGrid
from rclpy.serialization import deserialize_message
from explore.explore_node import ExploreNode
from explore.metric_frontier import footprint_poses_clear, footprint_cells

DATA = Path(__file__).parent/'data/ap06_b166_recorded_raster'


def recorded(resolution):
    with np.load(DATA.with_suffix('.npz'), allow_pickle=False) as arrays:
        grid = deserialize_message(arrays[{.01: 'map01', .02: 'map02', .03: 'map03'}[resolution]].tobytes(), OccupancyGrid)
    assert grid.info.resolution == pytest.approx(resolution)
    values = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    return grid, values == 0


def clear(grid, known, *, angle=.05, deviation=.02):
    return footprint_poses_clear([(2.6, -.435, 0.)], grid, known,
        ExploreNode._world_to_grid, (-.13, .33, -.25, .25),
        heading_half_angle=angle, center_deviation_m=deviation)


def test_product_raster_preserves_reserved_clearance_from_actual_occupied_posts():
    config = Path(__file__).parents[2]/'amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml'
    resolution = yaml.safe_load(config.read_text())['slam_toolbox']['ros__parameters']['resolution']
    grid, _ = recorded(resolution)
    rows, cols = footprint_cells(2.6, -.435, 0., grid, ExploreNode._world_to_grid,
        heading_half_angle=.05, center_deviation_m=.02)
    values = np.asarray(grid.data).reshape(grid.info.height, grid.info.width)
    # Occupied-post geometry only. This cannot turn unobserved cells into free
    # space or grant motion: the separate full-unknown test below must fail.
    assert not np.any(values[rows, cols] == 100), 'old raster loses reserved occupied-post clearance'
    coarse, coarse_known = recorded(.03)
    assert not clear(coarse, coarse_known)
    rows, cols = footprint_cells(2.6, -.435, 0., coarse, ExploreNode._world_to_grid,
        heading_half_angle=.05, center_deviation_m=.02)
    assert np.any(np.asarray(coarse.data).reshape(coarse_known.shape)[rows, cols] == 100)


def test_one_centimetre_single_scan_hole_still_blocks_the_full_body_proof():
    grid, known = recorded(.01)
    col, row = ExploreNode._world_to_grid(2.495, -.715, grid.info)
    assert grid.data[row*grid.info.width+col] == -1
    assert not clear(grid, known)  # one scan is not accumulated mission coverage


def test_finer_raster_keeps_original_heading_and_tracking_reserves():
    grid, known = recorded(.02)
    assert clear(grid, known)
    assert not clear(grid, known, angle=.20)
    assert not clear(grid, known, deviation=.08)


def test_recorded_raster_unknown_inside_body_still_blocks():
    grid, known = recorded(.02)
    assert clear(grid, known)
    rows, cols = footprint_cells(2.6, -.435, 0., grid, ExploreNode._world_to_grid,
        heading_half_angle=.05, center_deviation_m=.02)
    known[rows[len(rows)//2], cols[len(cols)//2]] = False
    assert not clear(grid, known)


def test_native_single_scan_post_quantization_is_measured_separately_from_mission():
    meta = json.loads(DATA.with_suffix('.json').read_text())
    assert meta['source_candidate'] == '2058fec'
    assert 'not full mission replay' in meta['kind']
    gaps = {m['resolution']: m['observed_gap'] for m in meta['maps']}
    assert gaps[.03] == pytest.approx(.66)
    assert gaps[.02] == pytest.approx(.68)
    assert gaps[.01] == pytest.approx(.68)
