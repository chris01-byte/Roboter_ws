from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.exploration_scope import (  # noqa: E402
    AuthorizedExplorationScope,
    ExplorationScopeError,
    point_within_scope_clearance,
    rasterize_scope,
)
from explore.portal_memory import Point2D, PortalMapContext  # noqa: E402


CONTEXT = PortalMapContext("session-scope", "map-scope", "map")


def scope(vertices=None):
    return AuthorizedExplorationScope(
        "scope-test",
        CONTEXT,
        tuple(vertices or (
            Point2D(0.0, 0.0),
            Point2D(2.0, 0.0),
            Point2D(2.0, 1.0),
            Point2D(0.0, 1.0),
        )),
    )


def raster(value=None, **changes):
    arguments = {
        "scope": value or scope(),
        "context": CONTEXT,
        "width": 4,
        "height": 4,
        "resolution_m": 0.5,
        "origin_x_m": 0.0,
        "origin_y_m": 0.0,
        "origin_yaw_rad": 0.0,
        "maximum_cells": 16,
    }
    arguments.update(changes)
    return rasterize_scope(**arguments)


def test_scope_raster_contains_only_authorized_cell_centres():
    mask = raster()

    assert mask.dtype == np.bool_
    assert mask.tolist() == [
        [True, True, True, True],
        [True, True, True, True],
        [False, False, False, False],
        [False, False, False, False],
    ]


def test_rotated_map_geometry_is_projected_in_world_coordinates():
    mask = raster(
        width=2,
        height=4,
        origin_x_m=2.0,
        origin_y_m=0.0,
        origin_yaw_rad=1.5707963267948966,
        maximum_cells=8,
    )

    unrotated = raster(
        width=2,
        height=4,
        origin_x_m=2.0,
        origin_y_m=0.0,
        maximum_cells=8,
    )

    assert np.count_nonzero(mask) == 8
    assert np.count_nonzero(unrotated) == 0


def test_scope_context_and_cell_capacity_fail_closed():
    with pytest.raises(ExplorationScopeError):
        raster(context=replace(CONTEXT, map_id="other-map"))
    with pytest.raises(ExplorationScopeError):
        raster(maximum_cells=15)


def test_scope_fingerprint_changes_when_geometry_changes_under_same_id():
    changed = scope((
        Point2D(0.0, 0.0), Point2D(2.1, 0.0),
        Point2D(2.1, 1.0), Point2D(0.0, 1.0),
    ))

    assert scope().fingerprint == scope().fingerprint
    assert changed.fingerprint != scope().fingerprint


def test_metric_runtime_point_requires_inside_edge_clearance():
    assert point_within_scope_clearance(
        scope(), context=CONTEXT, x_m=1.0, y_m=0.5,
        clearance_m=0.2) is True
    assert point_within_scope_clearance(
        scope(), context=CONTEXT, x_m=0.1, y_m=0.5,
        clearance_m=0.2) is False
    assert point_within_scope_clearance(
        scope(), context=CONTEXT, x_m=2.1, y_m=0.5,
        clearance_m=0.2) is False


@pytest.mark.parametrize("vertices", [
    (Point2D(0.0, 0.0), Point2D(1.0, 0.0)),
    (
        Point2D(0.0, 0.0), Point2D(1.0, 1.0),
        Point2D(0.0, 1.0), Point2D(1.0, 0.0),
    ),
    (
        Point2D(0.0, 0.0), Point2D(1.0, 0.0),
        Point2D(0.0, 0.0),
    ),
])
def test_degenerate_duplicate_or_self_intersecting_scope_is_rejected(vertices):
    with pytest.raises(ExplorationScopeError):
        scope(vertices)


def test_cached_scope_projection_keeps_caller_mutations_private():
    import explore.exploration_scope as module
    module._scope_projection.cache_clear()
    expected = raster()
    changed = raster()
    changed[:] = ~changed
    assert np.array_equal(raster(), expected)
    assert module._scope_projection.cache_info().hits == 2


def test_cached_projection_still_validates_context_types_and_capacity():
    raster()
    for changes in (
        dict(context=replace(CONTEXT, map_id='other')),
        dict(maximum_cells=15), dict(width=True),
        dict(resolution_m=True), dict(origin_x_m=float('nan')),
    ):
        with pytest.raises(ExplorationScopeError):
            raster(**changes)


@pytest.mark.parametrize('changes', [
    dict(width=5, maximum_cells=25), dict(height=5, maximum_cells=25),
    dict(resolution_m=.3), dict(origin_x_m=.7), dict(origin_y_m=.7),
    dict(origin_yaw_rad=.3),
])
def test_geometry_changes_cannot_reuse_previous_scope_projection(changes):
    import explore.exploration_scope as module
    module._scope_projection.cache_clear()
    raster()
    actual = raster(**changes)
    assert module._scope_projection.cache_info().misses == 2
    module._scope_projection.cache_clear()
    assert np.array_equal(actual, raster(**changes))


def test_changed_polygon_and_context_are_distinct_and_cache_is_bounded():
    import explore.exploration_scope as module
    module._scope_projection.cache_clear()
    initial = raster()
    smaller = scope((Point2D(0.,0.),Point2D(.5,0.),Point2D(.5,.5),Point2D(0.,.5)))
    assert not np.array_equal(raster(smaller), initial)
    other = replace(scope(), context=replace(CONTEXT, session_id='new-session'))
    assert np.array_equal(raster(other, context=other.context), initial)
    assert module._scope_projection.cache_info().misses == 3
    for offset in range(10):
        raster(origin_x_m=float(offset))
    assert module._scope_projection.cache_info().currsize == 4
