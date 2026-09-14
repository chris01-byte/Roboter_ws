from dataclasses import replace
import math
from pathlib import Path
import sys

import numpy as np
import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SHARED_ROOT = Path(__file__).resolve().parents[2] / "amadeus_map_identity"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(SHARED_ROOT))

from explore.portal_memory import (  # noqa: E402
    PortalMapContext,
    PortalMemory,
    PortalStructuralEvidence,
)
from explore.portal_plan_adapter import (  # noqa: E402
    normalize_portal_plan_candidate,
)
from explore.portal_source_adapter import (  # noqa: E402
    PortalSourceCorrelation,
    raw_map_portal_source_from_values,
)
from explore.raw_map_portal_adapter import (  # noqa: E402
    RawMapPortalCandidateError,
    correlated_connected_portal_candidates,
)


CONTEXT = PortalMapContext("we-m2ao-session", "map-epoch-1", "map")
RESOLUTION = 0.05
IDENTITY_ORIGIN = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)


def _occupancy():
    occupancy = np.full((60, 100), -1, dtype=np.int8)
    occupancy[5:55, 3:48] = 0
    occupancy[5:55, 52:97] = 0
    occupancy[27:33, 48:52] = 0
    return occupancy


def _source_and_correlation(
        occupancy, *, origin=IDENTITY_ORIGIN, stamp=100, revision=1):
    height, width = occupancy.shape
    source = raw_map_portal_source_from_values(
        width=width,
        height=height,
        resolution=RESOLUTION,
        frame_id="map",
        origin=origin,
        cells=occupancy.ravel(),
        source_stamp_ns=stamp,
    )
    correlation = PortalSourceCorrelation(
        context=CONTEXT,
        map_revision=revision,
        fingerprint=source.fingerprint,
        source_stamp_ns=source.source_stamp_ns,
    )
    return source, correlation


def _arguments(
        occupancy, *, origin=IDENTITY_ORIGIN, stamp=100, revision=1,
        robot_xy=(1.025, 1.525)):
    source, correlation = _source_and_correlation(
        occupancy, origin=origin, stamp=stamp, revision=revision)
    height, width = occupancy.shape
    return source, correlation, {
        "width": width,
        "height": height,
        "resolution": RESOLUTION,
        "frame_id": "map",
        "origin": origin,
        "cells": occupancy.ravel(),
        "source_stamp_ns": stamp,
        "robot_xy": robot_xy,
        "uncertainty_m": 0.02,
        "analysis_clearance_m": 0.20,
        "min_target_area_m2": 0.40,
        "min_gap_m": 0.12,
        "max_gap_m": 0.80,
        "exit_margin_m": 0.25,
        "max_traverse_distance_m": 1.00,
    }


def test_exact_snapshot_produces_stable_unqualified_candidate():
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(occupancy)

    first = correlated_connected_portal_candidates(
        correlation, **arguments)
    replay = correlated_connected_portal_candidates(
        correlation, **arguments)

    assert replay == first
    assert len(first) == 1
    candidate = first[0]
    assert candidate.observation_id.startswith("raw-connected-")
    assert len(candidate.observation_id) == 78
    assert candidate.context == CONTEXT
    assert candidate.map_revision == 1
    observation = normalize_portal_plan_candidate(candidate, CONTEXT)
    assert observation.structural_evidence is (
        PortalStructuralEvidence.INSUFFICIENT)
    assert np.array_equal(occupancy, _occupancy())


def test_growth_and_rotation_keep_metric_portal_identity_in_memory():
    base = _occupancy()
    _source, base_correlation, base_arguments = _arguments(base)
    base_candidate, = correlated_connected_portal_candidates(
        base_correlation, **base_arguments)

    grown = np.pad(
        base, ((10, 0), (20, 0)),
        mode="constant", constant_values=-1).astype(np.int8)
    grown_origin = (-1.0, -0.5, 0.0, 0.0, 0.0, 0.0, 1.0)
    _source, grown_correlation, grown_arguments = _arguments(
        grown, origin=grown_origin, stamp=200, revision=2)
    grown_candidate, = correlated_connected_portal_candidates(
        grown_correlation, **grown_arguments)

    rotated = np.rot90(base).copy()
    yaw = math.pi / 2.0
    rotated_origin = (
        base.shape[1] * RESOLUTION,
        0.0,
        0.0,
        0.0,
        0.0,
        math.sin(yaw / 2.0),
        math.cos(yaw / 2.0),
    )
    _source, rotated_correlation, rotated_arguments = _arguments(
        rotated, origin=rotated_origin, stamp=300, revision=3)
    rotated_candidate, = correlated_connected_portal_candidates(
        rotated_correlation, **rotated_arguments)

    np.testing.assert_allclose(
        (*base_candidate.staging_xy, *base_candidate.target_xy),
        (*grown_candidate.staging_xy, *grown_candidate.target_xy))
    np.testing.assert_allclose(
        (*base_candidate.staging_xy, *base_candidate.target_xy),
        (*rotated_candidate.staging_xy, *rotated_candidate.target_xy),
        atol=1e-12)
    assert len({
        base_candidate.observation_id,
        grown_candidate.observation_id,
        rotated_candidate.observation_id,
    }) == 3

    memory = PortalMemory(CONTEXT)
    portal_ids = tuple(
        memory.observe(normalize_portal_plan_candidate(
            candidate, CONTEXT)).portal_id
        for candidate in (
            base_candidate, grown_candidate, rotated_candidate)
    )
    assert portal_ids == ("portal_000001",) * 3
    assert len(memory.snapshots()) == 1


@pytest.mark.parametrize("change", [
    {"source_stamp_ns": 101},
    {"frame_id": "odom"},
])
def test_stamp_or_frame_mismatch_fails_before_candidate_output(change):
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(occupancy)
    arguments.update(change)

    with pytest.raises(RawMapPortalCandidateError):
        correlated_connected_portal_candidates(correlation, **arguments)


def test_cell_or_correlation_fingerprint_mismatch_fails_closed():
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(occupancy)
    changed = occupancy.copy()
    changed[10, 10] = 100

    with pytest.raises(RawMapPortalCandidateError):
        correlated_connected_portal_candidates(
            correlation, **{**arguments, "cells": changed.ravel()})
    with pytest.raises(RawMapPortalCandidateError):
        correlated_connected_portal_candidates(
            replace(correlation, fingerprint="a" * 64), **arguments)


@pytest.mark.parametrize("origin", [
    (0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 1.0),
    (0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 1.0),
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0),
])
def test_nonplanar_or_unnormalized_origin_is_rejected(origin):
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(occupancy)

    with pytest.raises(RawMapPortalCandidateError):
        correlated_connected_portal_candidates(
            correlation, **{**arguments, "origin": origin})


def test_robot_outside_exact_map_has_explicit_empty_result():
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(
        occupancy, robot_xy=(-10.0, -10.0))

    assert correlated_connected_portal_candidates(
        correlation, **arguments) == ()


@pytest.mark.parametrize("change", [
    {"uncertainty_m": -0.01},
    {"analysis_clearance_m": 0.0},
    {"min_gap_m": 0.8, "max_gap_m": 0.8},
])
def test_invalid_uncertainty_or_detector_bounds_fail_closed(change):
    occupancy = _occupancy()
    _source, correlation, arguments = _arguments(occupancy)
    arguments.update(change)

    with pytest.raises(RawMapPortalCandidateError):
        correlated_connected_portal_candidates(correlation, **arguments)
