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
from explore.exploration_child_goal import ExplorationGoalIntent  # noqa: E402
from explore.frontier_goal_candidate import (  # noqa: E402
    FrontierGoalCandidateCapacityError,
    FrontierGoalCandidateError,
    build_frontier_goal_candidate,
)
from explore.frontier_task_evidence import (  # noqa: E402
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


CONTEXT = PortalMapContext("session-m3k", "map-epoch-1", "map")
STAMP_NS = 1_800_000_000_000_000_000


def _map(*, barrier=False, origin=None, width=21, height=21):
    resolution = 0.1
    selected_origin = origin or (
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
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


def _task(*, task_id="task-frontier_000001",
          region_id="region-1", subject_id="frontier_000001",
          kind=RegionTaskKind.FRONTIER, state=RegionTaskState.OPEN):
    return RegionTaskSnapshot(
        task_id=task_id,
        region_id=region_id,
        kind=kind,
        subject_id=subject_id,
        state=state,
        created_revision=3,
        last_revision=7,
    )


def _track(*, frontier_id="frontier_000001", revision=7,
           x=1.45, y=1.05):
    return FrontierTrackSnapshot(
        frontier_id=frontier_id,
        centroid=Point2D(x, y),
        size_cells=8,
        first_revision=3,
        last_revision=revision,
        observation_count=3,
    )


def _intent(*, task_id="task-frontier_000001", region_id="region-1",
            revision=7):
    return ExplorationGoalIntent(
        intent_id=f"intent-{revision}-{task_id}",
        task_id=task_id,
        region_id=region_id,
        context=CONTEXT,
        map_revision=revision,
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


def _inputs(*, map_values=None, robot_xy=(0.55, 1.05), task=None,
            tracks=None, policy=None):
    values = _map() if map_values is None else map_values
    selected_task = _task() if task is None else task
    selected_tracks = (_track(),) if tracks is None else tracks
    selected_policy = _policy() if policy is None else policy
    evidence = build_frontier_task_evidence(
        **values,
        robot_xy=robot_xy,
        tasks=(selected_task,),
        tracks=selected_tracks,
        policy=selected_policy,
    )
    return {
        "intent": _intent(
            task_id=selected_task.task_id,
            region_id=selected_task.region_id),
        **values,
        "robot_xy": robot_xy,
        "task": selected_task,
        "tracks": selected_tracks,
        "evidence": evidence,
        "policy": selected_policy,
    }


def test_exact_available_frontier_produces_numeric_map_candidate():
    candidate = build_frontier_goal_candidate(**_inputs())

    assert candidate.intent_id == "intent-7-task-frontier_000001"
    assert candidate.frontier_id == "frontier_000001"
    assert candidate.map_revision == 7
    assert candidate.frame_id == "map"
    assert candidate.source_stamp_ns == STAMP_NS
    assert candidate.target_row == 10
    assert candidate.target_col == 14
    assert math.isclose(candidate.target_x_m, 1.45, abs_tol=1e-9)
    assert math.isclose(candidate.target_y_m, 1.05, abs_tol=1e-9)
    assert math.isclose(candidate.target_yaw_rad, 0.0, abs_tol=1e-9)
    assert math.isclose(candidate.route_length_m, 0.9, abs_tol=1e-9)
    assert candidate.information_gain_square_m > 0.0
    assert not hasattr(candidate, "path")
    assert not hasattr(candidate, "authorization")


def test_rotated_origin_preserves_metric_target_and_heading():
    angle = math.pi / 2.0
    rotated = _map(origin=(
        2.0, -1.0, 0.0, 0.0, 0.0,
        math.sin(angle / 2.0), math.cos(angle / 2.0)))
    robot_xy = (0.95, -0.45)
    track = _track(x=0.95, y=0.45)

    candidate = build_frontier_goal_candidate(**_inputs(
        map_values=rotated,
        robot_xy=robot_xy,
        tracks=(track,),
    ))

    assert math.isclose(candidate.target_x_m, 0.95, abs_tol=1e-9)
    assert math.isclose(candidate.target_y_m, 0.45, abs_tol=1e-9)
    assert math.isclose(candidate.target_yaw_rad, math.pi / 2.0, abs_tol=1e-9)


def test_goal_faces_frontier_when_safe_cell_is_offset():
    track = _track(x=1.55, y=1.05)
    candidate = build_frontier_goal_candidate(**_inputs(tracks=(track,)))

    assert candidate.target_col == 14
    assert candidate.target_x_m < candidate.frontier_x_m
    assert math.isclose(candidate.target_yaw_rad, 0.0, abs_tol=1e-9)


@pytest.mark.parametrize("change,match", [
    ({"intent": _intent(revision=8)}, "korrelation"),
    ({"intent": _intent(task_id="task-other")}, "Aufgabe passt"),
    ({"task": _task(region_id="region-other")}, "Aufgabe passt"),
    ({"task": _task(kind=RegionTaskKind.PORTAL)}, "offene Frontier"),
    ({"tracks": (_track(revision=6),)}, "Zielrevision"),
])
def test_context_task_and_revision_mismatches_fail_closed(change, match):
    inputs = _inputs()
    inputs.update(change)

    with pytest.raises(FrontierGoalCandidateError, match=match):
        build_frontier_goal_candidate(**inputs)


def test_missing_duplicate_and_wrong_track_fail_closed():
    inputs = _inputs()
    with pytest.raises(FrontierGoalCandidateError, match="genau einen"):
        build_frontier_goal_candidate(**{**inputs, "tracks": ()})
    with pytest.raises(FrontierGoalCandidateError, match="Duplikate"):
        build_frontier_goal_candidate(**{
            **inputs, "tracks": (_track(), _track())})
    with pytest.raises(FrontierGoalCandidateError, match="genau einen"):
        build_frontier_goal_candidate(**{
            **inputs, "tracks": (_track(frontier_id="frontier-other"),)})


def test_missing_pose_and_unreachable_map_fail_closed():
    inputs = _inputs()
    with pytest.raises(FrontierGoalCandidateError, match="Roboterpose"):
        build_frontier_goal_candidate(**{
            **inputs, "robot_xy": None})

    blocked_values = _map(barrier=True)
    blocked = _inputs(map_values=blocked_values)
    assert blocked["evidence"].utilities == ()
    with pytest.raises(FrontierGoalCandidateError, match="eindeutige"):
        build_frontier_goal_candidate(**blocked)


def test_wrong_scalar_route_or_source_snapshot_fails_closed():
    inputs = _inputs()
    utility = inputs["evidence"].utilities[0]
    inputs["evidence"] = replace(
        inputs["evidence"],
        utilities=(replace(
            utility,
            geodesic_path_length_m=utility.geodesic_path_length_m + 0.1),),
    )
    with pytest.raises(FrontierGoalCandidateError, match="Wegevidenz"):
        build_frontier_goal_candidate(**inputs)

    information = _inputs()
    utility = information["evidence"].utilities[0]
    information["evidence"] = replace(
        information["evidence"],
        utilities=(replace(
            utility,
            information_gain_square_m=(
                utility.information_gain_square_m + 0.1)),),
    )
    with pytest.raises(FrontierGoalCandidateError, match="Informationsevidenz"):
        build_frontier_goal_candidate(**information)

    fresh = _inputs()
    cells = list(fresh["cells"])
    cells[0] = 100
    with pytest.raises(FrontierGoalCandidateError, match="Korrelation"):
        build_frontier_goal_candidate(**{**fresh, "cells": cells})


def test_map_and_track_bounds_apply_before_search():
    too_large = _map(width=22, height=21)
    values = _inputs(
        map_values=too_large,
        policy=_policy(max_cells=22 * 21),
    )
    values["policy"] = _policy(max_cells=21 * 21)
    with pytest.raises(FrontierGoalCandidateCapacityError):
        build_frontier_goal_candidate(**values)

    normal = _inputs(policy=_policy(max_tracks=1))
    with pytest.raises(FrontierGoalCandidateCapacityError):
        build_frontier_goal_candidate(**{
            **normal,
            "tracks": (_track(), _track(frontier_id="frontier-other")),
        })


def test_module_has_no_ros_nav_action_command_or_motion_imports():
    source = (PACKAGE_ROOT / "explore" / "frontier_goal_candidate.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not any(name.startswith("rclpy") for name in imported)
    assert not any(name.startswith("nav2") for name in imported)
    assert not any(name.startswith("geometry_msgs") for name in imported)
    assert "ActionClient" not in source
    assert "Twist" not in source
    assert "cmd_vel" not in source
