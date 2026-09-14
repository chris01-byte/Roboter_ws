from dataclasses import replace
import ast
import math
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from amadeus_map_identity import (  # noqa: E402
    compact_occupancy_cells,
    map_snapshot_fingerprint,
)
from explore.frontier_task_evidence import (  # noqa: E402
    FrontierTaskEvidenceCapacityError,
    FrontierTaskEvidenceError,
    FrontierTaskEvidencePolicy,
    build_frontier_task_evidence,
)
from explore.frontier_task_feed import FrontierTrackSnapshot  # noqa: E402
from explore.portal_memory import Point2D, PortalMapContext  # noqa: E402
from explore.portal_source_adapter import PortalSourceCorrelation  # noqa: E402
from explore.region_graph import (  # noqa: E402
    RegionTaskKind,
    RegionTaskSnapshot,
    RegionTaskState,
)
from explore.exploration_policy import TaskAvailabilityState  # noqa: E402


CONTEXT = PortalMapContext("session-m3g", "map-epoch-1", "map")
STAMP_NS = 1_800_000_000_000_000_000


def _map(*, barrier=False, origin=None):
    width = 21
    height = 21
    resolution = 0.1
    selected_origin = origin or (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
    cells = [0] * (width * height)
    for row in range(height):
        for col in range(15, width):
            cells[row * width + col] = -1
    if barrier:
        for row in range(height):
            cells[row * width + 10] = 100
    compact = compact_occupancy_cells(
        cells=cells, cell_count=width * height)
    fingerprint = map_snapshot_fingerprint(
        width=width,
        height=height,
        resolution=resolution,
        frame_id="map",
        origin=selected_origin,
        compact_cells=compact,
    )
    correlation = PortalSourceCorrelation(
        context=CONTEXT,
        map_revision=7,
        fingerprint=fingerprint,
        source_stamp_ns=STAMP_NS,
    )
    return {
        "correlation": correlation,
        "width": width,
        "height": height,
        "resolution": resolution,
        "frame_id": "map",
        "origin": selected_origin,
        "cells": cells,
        "source_stamp_ns": STAMP_NS,
    }


def _task(task_id="task-frontier_000001", *,
          kind=RegionTaskKind.FRONTIER, subject_id="frontier_000001"):
    return RegionTaskSnapshot(
        task_id=task_id,
        region_id="region-1",
        kind=kind,
        subject_id=subject_id,
        state=RegionTaskState.OPEN,
        created_revision=3,
        last_revision=7,
    )


def _track(*, revision=7, x=1.45, y=1.05):
    return FrontierTrackSnapshot(
        frontier_id="frontier_000001",
        centroid=Point2D(x, y),
        size_cells=8,
        first_revision=3,
        last_revision=revision,
        observation_count=3,
    )


def _policy(**changes):
    values = {
        "clearance_m": 0.1,
        "robot_seed_search_m": 0.2,
        "task_cell_search_m": 0.2,
        "information_radius_m": 0.4,
    }
    values.update(changes)
    return FrontierTaskEvidencePolicy(**values)


def _build(*, map_values=None, robot_xy=(0.55, 1.05),
           tasks=None, tracks=None, policy=None):
    values = _map() if map_values is None else map_values
    return build_frontier_task_evidence(
        **values,
        robot_xy=robot_xy,
        tasks=(_task(),) if tasks is None else tasks,
        tracks=(_track(),) if tracks is None else tracks,
        policy=_policy() if policy is None else policy,
    )


def test_current_reachable_frontier_gets_scalar_evidence_without_goal():
    result = _build()

    assert result.source_map_revision == 7
    assert result.robot_seed_available is True
    assert result.current_frontier_track_count == 1
    assert len(result.availability) == 1
    assert result.availability[0].state is TaskAvailabilityState.AVAILABLE
    assert result.availability[0].recheck_condition == (
        "revalidate_before_navigation")
    assert len(result.utilities) == 1
    utility = result.utilities[0]
    assert utility.task_id == "task-frontier_000001"
    assert math.isclose(utility.geodesic_path_length_m, 0.9, abs_tol=1e-9)
    assert utility.information_gain_square_m > 0.0
    assert not hasattr(utility, "goal")
    assert not hasattr(utility, "path")


def test_occupied_barrier_keeps_task_visible_and_temporarily_blocked():
    result = _build(map_values=_map(barrier=True))

    assert result.availability[0].state is (
        TaskAvailabilityState.TEMPORARILY_BLOCKED)
    assert result.availability[0].reason == "no_current_raw_map_route"
    assert result.utilities == ()


def test_target_search_does_not_jump_across_barrier_to_reachable_side():
    result = _build(
        map_values=_map(barrier=True),
        policy=_policy(task_cell_search_m=0.6),
    )

    assert result.availability[0].state is (
        TaskAvailabilityState.TEMPORARILY_BLOCKED)
    assert result.availability[0].reason == "no_current_raw_map_route"
    assert result.utilities == ()


def test_missing_robot_pose_keeps_task_unknown_without_utility():
    result = _build(robot_xy=None)

    assert result.robot_seed_available is False
    assert result.availability[0].state is TaskAvailabilityState.UNKNOWN
    assert result.availability[0].reason == "missing_robot_pose"
    assert result.utilities == ()


def test_stale_frontier_track_never_becomes_available():
    result = _build(tracks=(_track(revision=6),))

    assert result.current_frontier_track_count == 0
    assert result.availability[0].state is TaskAvailabilityState.UNKNOWN
    assert result.availability[0].reason == (
        "frontier_not_observed_in_current_revision")
    assert result.utilities == ()


def test_missing_and_nonfrontier_tasks_receive_complete_unknown_evidence():
    portal = _task(
        "task-portal-1", kind=RegionTaskKind.PORTAL,
        subject_id="portal-1")
    missing = _task(
        "task-frontier_000002", subject_id="frontier_000002")

    result = _build(tasks=(portal, missing))

    by_id = {item.task_id: item for item in result.availability}
    assert set(by_id) == {"task-portal-1", "task-frontier_000002"}
    assert by_id["task-portal-1"].reason == "unsupported_task_kind"
    assert by_id["task-frontier_000002"].reason == (
        "missing_frontier_track")
    assert result.utilities == ()


def test_no_unknown_cells_filters_but_does_not_remove_task():
    values = _map()
    values["cells"] = [0] * (values["width"] * values["height"])
    compact = compact_occupancy_cells(
        cells=values["cells"],
        cell_count=values["width"] * values["height"],
    )
    values["correlation"] = replace(
        values["correlation"],
        fingerprint=map_snapshot_fingerprint(
            width=values["width"], height=values["height"],
            resolution=values["resolution"], frame_id=values["frame_id"],
            origin=values["origin"], compact_cells=compact,
        ),
    )

    result = _build(map_values=values)

    assert result.availability[0].state is TaskAvailabilityState.FILTERED
    assert result.availability[0].reason == "no_current_information_gain"
    assert result.utilities == ()


def test_exact_raw_map_identity_is_mandatory():
    values = _map()
    values["cells"][0] = 100

    with pytest.raises(
            FrontierTaskEvidenceError,
            match="passt nicht zur Korrelation"):
        _build(map_values=values)


def test_rotated_origin_preserves_metric_route_and_information():
    yaw = math.pi / 2.0
    origin = (
        3.0, -2.0, 0.0, 0.0, 0.0,
        math.sin(yaw / 2.0), math.cos(yaw / 2.0),
    )
    values = _map(origin=origin)

    def rotate(local_x, local_y):
        return 3.0 - local_y, -2.0 + local_x

    robot = rotate(0.55, 1.05)
    frontier = rotate(1.45, 1.05)
    result = _build(
        map_values=values,
        robot_xy=robot,
        tracks=(_track(x=frontier[0], y=frontier[1]),),
    )

    assert result.availability[0].state is TaskAvailabilityState.AVAILABLE
    assert math.isclose(
        result.utilities[0].geodesic_path_length_m, 0.9, abs_tol=1e-9)


def test_input_order_does_not_change_canonical_task_order():
    first = _task()
    second = _task(
        "task-frontier_000002", subject_id="frontier_000002")
    second_track = replace(
        _track(), frontier_id="frontier_000002", centroid=Point2D(1.45, 0.85))

    forward = _build(tasks=(first, second), tracks=(_track(), second_track))
    reverse = _build(
        tasks=(second, first), tracks=(second_track, _track()))

    assert forward == reverse
    assert tuple(item.task_id for item in forward.availability) == (
        "task-frontier_000001", "task-frontier_000002")


@pytest.mark.parametrize("robot_xy", ["pose", (1.0,), (math.nan, 1.0)])
def test_invalid_robot_pose_is_rejected(robot_xy):
    with pytest.raises(FrontierTaskEvidenceError, match="robot_xy"):
        _build(robot_xy=robot_xy)


def test_capacity_and_future_revision_fail_closed():
    with pytest.raises(FrontierTaskEvidenceCapacityError):
        _build(policy=_policy(max_cells=100))
    with pytest.raises(FrontierTaskEvidenceError, match="vor der aktuellen"):
        _build(tracks=(_track(revision=8),))
    with pytest.raises(FrontierTaskEvidenceError, match="Aufgabe liegt"):
        _build(tasks=(replace(_task(), last_revision=8),))


def test_module_has_no_ros_navigation_or_motion_imports():
    source = (PACKAGE_ROOT / "explore" / "frontier_task_evidence.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(name.startswith("rclpy") for name in imports)
    assert not any(name.startswith("nav2") for name in imports)
    assert not any(name.startswith("geometry_msgs") for name in imports)
    assert "Twist" not in source
    assert "PoseStamped" not in source
