from pathlib import Path
import sys

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from explore.lidar_motion import LidarMotionEstimate  # noqa: E402
from explore.exploration_scope import AuthorizedExplorationScope  # noqa: E402
from explore.portal_frozen_scan_runtime import (  # noqa: E402
    ExactTimeMapPose,
    FrozenScanMonitorPolicy,
    FrozenScanPortalMonitor,
    FrozenScanSample,
)
from explore.portal_memory import (  # noqa: E402
    Point2D,
    PortalConfirmationState,
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from explore.portal_task_evidence import PortalGoalCandidate  # noqa: E402
from explore.portal_traversal_evidence import PortalTraversalPolicy  # noqa: E402
from explore.portal_traversal_runtime import (  # noqa: E402
    PortalTraversalRuntimePolicy,
)
import explore.portal_frozen_scan_runtime as runtime_module  # noqa: E402


CONTEXT = PortalMapContext("session-frozen", "map-frozen", "map")


def scope():
    return AuthorizedExplorationScope(
        "scope-frozen",
        CONTEXT,
        (
            Point2D(-1.0, -1.0), Point2D(2.0, -1.0),
            Point2D(2.0, 1.0), Point2D(-1.0, 1.0),
        ),
    )


def candidate(direction=TraversalDirection.A_TO_B):
    return PortalGoalCandidate(
        intent_id="intent-frozen-10",
        task_id="task-portal_000001",
        region_id="region_000002",
        portal_id="portal_000001",
        direction=direction,
        context=CONTEXT,
        map_revision=10,
        frame_id="map",
        source_fingerprint="a" * 64,
        source_stamp_ns=4_000_000_000,
        scope_id="scope-frozen",
        scope_fingerprint=scope().fingerprint,
        target_x_m=1.5,
        target_y_m=0.0,
        target_yaw_rad=0.0,
        target_row=0,
        target_col=3,
        route_length_m=2.0,
        path_cells=((0, 0), (0, 1), (0, 2), (0, 3)),
    )


def portal():
    return PortalSnapshot(
        portal_id="portal_000001",
        side_a=Point2D(0.0, 0.0),
        side_b=Point2D(1.0, 0.0),
        first_revision=8,
        last_revision=9,
        observation_count=2,
        evidence_count=2,
        qualified_evidence_count=2,
        confirmation_state=PortalConfirmationState.CONFIRMED,
        confirmed=True,
        confirmed_traversal_count=0,
    )


def traversal_policy():
    return PortalTraversalPolicy(
        chassis_front_overhang_m=0.30,
        chassis_rear_overhang_m=0.30,
        start_clearance_m=0.10,
        exit_clearance_m=0.10,
        maximum_lateral_deviation_m=0.20,
        maximum_pose_step_m=0.85,
        maximum_pose_speed_mps=0.90,
        maximum_yaw_error_rad=0.25,
        maximum_yaw_step_rad=0.20,
        maximum_backward_step_m=0.05,
        maximum_motion_disagreement_m=0.15,
        maximum_source_age_ns=500_000_000,
        maximum_revision_lag=1,
        minimum_pose_samples=3,
    )


def monitor_policy(**changes):
    values = {
        "max_cost_m": 0.08,
        "min_support_ratio": 0.45,
        "min_distinct_gap_m": 0.01,
        "maximum_scan_step_m": 0.85,
        "maximum_scan_yaw_step_rad": 0.20,
        "maximum_consecutive_rejections": 2,
    }
    values.update(changes)
    return FrozenScanMonitorPolicy(**values)


def scan(index, independent_progress):
    points = np.zeros((200, 2), dtype=np.float64)
    points[0, 0] = independent_progress
    return FrozenScanSample(
        f"scan-{index}", index * 1_000_000_000, points)


class FakeMatcher:
    def __init__(self, _points):
        pass

    def estimate(self, points, _previous):
        return LidarMotionEstimate(
            x_m=float(points[0, 0]),
            y_m=0.0,
            yaw_rad=0.0,
            cost_m=0.01,
            support_ratio=0.9,
            distinct_cost_m=0.04,
        )


def build_monitor(monkeypatch, scans, poses, **changes):
    monkeypatch.setattr(runtime_module, "LidarReferenceMatcher", FakeMatcher)
    scan_values = iter(scans)
    pose_by_stamp = {pose.stamp_ns: pose for pose in poses}
    arguments = {
        "candidate": candidate(),
        "portal": portal(),
        "traversal_policy": traversal_policy(),
        "runtime_policy": PortalTraversalRuntimePolicy(max_samples=8),
        "monitor_policy": monitor_policy(),
        "scope": scope(),
        "scope_clearance_m": 0.1,
        "read_scan": lambda: next(scan_values, None),
        "pose_at_stamp": pose_by_stamp.get,
    }
    arguments.update(changes)
    return FrozenScanPortalMonitor(**arguments)


def poses(xs):
    return tuple(
        ExactTimeMapPose(
            CONTEXT, 10, index * 1_000_000_000, x, 0.0, 0.0)
        for index, x in enumerate(xs, start=1)
    )


def test_frozen_scan_monitor_pairs_exact_pose_and_confirms(monkeypatch):
    selected_scans = tuple(
        scan(index, progress)
        for index, progress in enumerate((0.0, 0.6, 1.2, 2.0), start=1)
    )
    monitor = build_monitor(
        monkeypatch,
        selected_scans,
        poses((-0.5, 0.1, 0.7, 1.5)),
    )

    assert [monitor.observe() for _item in selected_scans] == [True] * 4
    outcome = monitor.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)

    assert monitor.fault is None
    assert outcome.confirmed is True
    assert outcome.sample_count == 4
    assert outcome.assessment.independent_forward_progress_m == 2.0


def test_missing_fresh_scan_fails_after_bounded_rejections(monkeypatch):
    monitor = build_monitor(monkeypatch, (), ())

    assert monitor.observe() is True
    assert monitor.observe() is False
    outcome = monitor.finish(
        execution_succeeded=False, evaluated_at_ns=1)

    assert monitor.fault == "fresh_scan_unavailable"
    assert outcome.confirmed is False
    assert outcome.reason == "monitor_failed:fresh_scan_unavailable"


def test_scan_without_exact_time_pose_never_enters_evidence(monkeypatch):
    monitor = build_monitor(
        monkeypatch,
        (scan(1, 0.0), scan(2, 0.1)),
        (),
    )

    assert monitor.observe() is True
    assert monitor.observe() is False

    assert monitor.fault == "exact_time_map_pose_unavailable"


def test_unreliable_or_jumping_scan_cancels_fail_closed(monkeypatch):
    monitor = build_monitor(
        monkeypatch,
        (scan(1, 0.0), scan(2, 1.0), scan(3, 2.0)),
        poses((-0.5, 0.0, 0.5)),
        monitor_policy=monitor_policy(
            maximum_scan_step_m=0.2,
            maximum_consecutive_rejections=1),
    )

    assert monitor.observe() is True
    assert monitor.observe() is False
    assert monitor.fault == "scan_match_not_reliable"


def test_duplicate_scan_is_ignored_without_duplicate_pose(monkeypatch):
    first = scan(1, 0.0)
    values = iter((first, first, scan(2, 0.6)))
    pose_values = poses((-0.5, 0.1))
    pose_by_stamp = {pose.stamp_ns: pose for pose in pose_values}
    monkeypatch.setattr(runtime_module, "LidarReferenceMatcher", FakeMatcher)
    monitor = FrozenScanPortalMonitor(
        candidate(),
        portal(),
        traversal_policy(),
        PortalTraversalRuntimePolicy(max_samples=8),
        monitor_policy(),
        scope(),
        0.1,
        lambda: next(values),
        pose_by_stamp.get,
    )

    assert monitor.observe() is True
    assert monitor.observe() is True
    assert monitor.observe() is True
    outcome = monitor.finish(
        execution_succeeded=True, evaluated_at_ns=2_100_000_000)

    assert outcome.sample_count == 2
    assert outcome.confirmed is False
    assert outcome.reason == "source_map_stamp_in_future"


def test_runtime_pose_outside_authorized_scope_stops_immediately(monkeypatch):
    monitor = build_monitor(
        monkeypatch,
        (scan(1, 0.0),),
        poses((2.5,)),
    )

    assert monitor.observe() is False
    assert monitor.fault == "pose_left_authorized_scope"


def test_monitor_waits_for_alignment_while_still_before_portal(monkeypatch):
    selected_poses = (
        ExactTimeMapPose(CONTEXT, 10, 1_000_000_000, -0.5, 0.0, 0.5),
        ExactTimeMapPose(CONTEXT, 10, 2_000_000_000, -0.5, 0.0, 0.0),
    )
    monitor = build_monitor(
        monkeypatch,
        (scan(1, 0.0), scan(2, 0.0)),
        selected_poses,
    )

    assert monitor.observe() is True
    assert monitor.observe() is True
    outcome = monitor.finish(
        execution_succeeded=True, evaluated_at_ns=4_100_000_000)

    assert monitor.fault is None
    assert outcome.sample_count == 1
    assert outcome.reason == "insufficient_paired_samples"


def test_monitor_fails_if_crossing_begins_before_reference(monkeypatch):
    monitor = build_monitor(
        monkeypatch,
        (scan(1, 0.0),),
        poses((0.0,)),
    )

    assert monitor.observe() is False
    assert monitor.fault == "crossing_started_before_monitor"
