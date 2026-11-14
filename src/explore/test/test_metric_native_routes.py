"""Native descent retains every original cell, corner and deterministic tie."""
import itertools
import math

import numpy as np
import pytest
import explore.metric_frontier as geometry
from explore.frontier_task_evidence import _geodesic_distances
from test_metric_native_sweep import native


def native_route(native, mask, distances, start, target):
    return native.descending_route(mask, distances, *start, *target,
                                   math.hypot(1, 0), math.hypot(1, 1))


def test_all_small_maps_keep_original_corners_reachability_and_ties(native):
    for bits in itertools.product((False, True), repeat=6):
        mask = np.asarray(bits, dtype=bool).reshape(2, 3)
        cells = [tuple(cell) for cell in np.argwhere(mask)]
        for start in cells:
            distances = _geodesic_distances(mask, start)
            for target in cells:
                expected = (geometry._descending_route_python(mask, distances, start, target)
                            if np.isfinite(distances[target]) else None)
                assert native_route(native, mask, distances, start, target) == expected


@pytest.mark.parametrize('seed', range(12))
@pytest.mark.parametrize('strided', [False, True])
def test_random_blocked_maps_match_every_original_route_cell(native, seed, strided):
    rng = np.random.default_rng(seed)
    mask = rng.random((24, 31)) > .22
    if strided:
        mask = mask[::-1, ::-1]
    starts = [tuple(cell) for cell in np.argwhere(mask)[::100]]
    targets = [tuple(cell) for cell in np.argwhere(mask)[::37]]
    for start in starts:
        distances = _geodesic_distances(mask, start)
        if strided:
            # Same values, noncontiguous positive strides for the distance field.
            expanded = np.zeros((48, 62))
            expanded[::2, ::2] = distances
            distances = expanded[::2, ::2]
        for target in targets:
            expected = (geometry._descending_route_python(mask, distances, start, target)
                        if np.isfinite(distances[target]) else None)
            assert native_route(native, mask, distances, start, target) == expected


@pytest.mark.parametrize('offset', [0., 1e-9, np.nextafter(1e-9, 0.),
                                    np.nextafter(1e-9, math.inf), .5])
def test_strict_descent_threshold_and_equal_score_order(native, offset):
    mask = np.ones((3, 3), bool)
    distances = np.ones((3, 3))
    distances[0, 0] = 0.
    distances[1, 1] = 1.+offset
    for target in [(1, 1), (2, 2)]:
        assert native_route(native, mask, distances, (0, 0), target) == \
            geometry._descending_route_python(mask, distances, (0, 0), target)


@pytest.mark.parametrize('kind', ['mask_type', 'distance_type', 'dimensions',
                                 'different_shape', 'bad_steps'])
def test_invalid_native_buffers_or_weights_cannot_supply_a_route(native, kind):
    mask = np.ones((3, 3), bool)
    distances = _geodesic_distances(mask, (0, 0))
    args = [mask, distances, 0, 0, 2, 2, math.hypot(1, 0), math.hypot(1, 1)]
    if kind == 'mask_type': args[0] = mask.astype(np.int8)
    if kind == 'distance_type': args[1] = distances.astype(np.float32)
    if kind == 'dimensions': args[0] = mask.ravel()
    if kind == 'different_shape': args[1] = distances[:, :2]
    if kind == 'bad_steps': args[-1] = math.inf
    with pytest.raises((TypeError, ValueError)):
        native.descending_route(*args)


@pytest.mark.parametrize('target', [(-1, 0), (0, -1), (3, 0), (0, 3), (2, 2)])
def test_invalid_or_unreachable_endpoint_returns_no_route(native, target):
    mask = np.eye(3, dtype=bool)
    distances = _geodesic_distances(mask, (0, 0))
    assert native_route(native, mask, distances, (0, 0), target) is None


@pytest.mark.parametrize('available', [False, True])
def test_wrapper_and_missing_native_keep_original_route(native, monkeypatch, available):
    mask = np.ones((9, 13), dtype=bool)
    mask[2:7, 5] = False
    distances = _geodesic_distances(mask, (1, 1))
    expected = geometry._descending_route_python(mask, distances, (1, 1), (7, 11))
    if not available:
        monkeypatch.setattr(geometry, '_reserved_sweep', None)
    assert geometry.route_cells(mask, (1, 1), (7, 11)) == expected


@pytest.mark.parametrize('angle', [0., 1e-15, .17, -1.4, math.pi/2])
@pytest.mark.parametrize('resolution', [.01, .02, .1])
@pytest.mark.parametrize('origin', [(0., 0.), (-2.345, 4.567), (1e8, -1e8)])
def test_route_cell_centres_are_bit_identical_to_scalar_projection(angle, resolution, origin):
    from test_metric_frontier import egress_fixture
    node, inputs = egress_fixture()
    grid = inputs[0]
    grid.info.resolution = resolution
    grid.info.origin.orientation.z = math.sin(angle/2)
    grid.info.origin.orientation.w = math.cos(angle/2)
    grid.info.origin.position.x, grid.info.origin.position.y = origin
    cells = tuple((r, c) for r in range(grid.info.height) for c in range(grid.info.width))
    expected = tuple(node._grid_to_world(c, r, grid.info) for r, c in cells)
    assert node._metric_cell_route_points(grid, cells) == expected
    assert node._metric_cell_route_points(grid, ()) == ()
