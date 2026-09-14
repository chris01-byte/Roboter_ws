"""Frozen-range-scan adapter for one regular Nav2 portal child.

All sensor and TF access is injected.  The adapter only correlates immutable
scan points with an exact-time map pose and feeds the bounded M3/T session.
"""

from dataclasses import dataclass
import math
from typing import Callable, Optional

import numpy as np

from .lidar_motion import (
    LidarReferenceMatcher,
    motion_estimate_is_reliable,
    normalize_angle,
)
from .exploration_scope import (
    AuthorizedExplorationScope,
    point_within_scope_clearance,
)
from .portal_memory import (
    PortalMapContext,
    PortalSnapshot,
    TraversalDirection,
)
from .portal_task_evidence import PortalGoalCandidate
from .portal_traversal_evidence import (
    IndependentMotionSource,
    PortalTraversalPolicy,
)
from .portal_traversal_runtime import (
    PairedTraversalReading,
    PortalTraversalRuntimeOutcome,
    PortalTraversalRuntimePolicy,
    PortalTraversalRuntimeSession,
)


class PortalFrozenScanRuntimeError(ValueError):
    """The frozen scan or exact-time pose stream is unusable."""


@dataclass(frozen=True)
class FrozenScanSample:
    sample_id: str
    stamp_ns: int
    points: np.ndarray

    def __post_init__(self) -> None:
        if (
                not isinstance(self.sample_id, str)
                or not self.sample_id
                or len(self.sample_id) > 128
                or not self.sample_id.isascii()):
            raise PortalFrozenScanRuntimeError(
                "sample_id ist ungueltig")
        if (
                isinstance(self.stamp_ns, bool)
                or not isinstance(self.stamp_ns, int)
                or self.stamp_ns < 0):
            raise PortalFrozenScanRuntimeError(
                "stamp_ns muss nichtnegativ sein")
        points = np.asarray(self.points, dtype=np.float64)
        if (
                points.ndim != 2
                or points.shape[1:] != (2,)
                or points.shape[0] < 200
                or points.shape[0] > 65536
                or not np.all(np.isfinite(points))):
            raise PortalFrozenScanRuntimeError(
                "Scan braucht 200 bis 65536 endliche XY-Punkte")
        immutable = points.copy()
        immutable.setflags(write=False)
        object.__setattr__(self, "points", immutable)


@dataclass(frozen=True)
class ExactTimeMapPose:
    context: PortalMapContext
    map_revision: int
    stamp_ns: int
    x: float
    y: float
    yaw: float

    def __post_init__(self) -> None:
        if not isinstance(self.context, PortalMapContext):
            raise PortalFrozenScanRuntimeError(
                "context muss PortalMapContext sein")
        for name in ("map_revision", "stamp_ns"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0):
                raise PortalFrozenScanRuntimeError(
                    f"{name} muss nichtnegativ sein")
        if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in (self.x, self.y, self.yaw)):
            raise PortalFrozenScanRuntimeError(
                "Kartenpose muss endlich sein")


@dataclass(frozen=True)
class FrozenScanMonitorPolicy:
    max_cost_m: float
    min_support_ratio: float
    min_distinct_gap_m: float
    maximum_scan_step_m: float
    maximum_scan_yaw_step_rad: float
    maximum_consecutive_rejections: int

    def __post_init__(self) -> None:
        for name in (
                "max_cost_m", "min_distinct_gap_m",
                "maximum_scan_step_m", "maximum_scan_yaw_step_rad"):
            value = getattr(self, name)
            if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) <= 0.0):
                raise PortalFrozenScanRuntimeError(
                    f"{name} muss endlich und positiv sein")
        if (
                isinstance(self.min_support_ratio, bool)
                or not isinstance(self.min_support_ratio, (int, float))
                or not math.isfinite(float(self.min_support_ratio))
                or not 0.0 < float(self.min_support_ratio) <= 1.0):
            raise PortalFrozenScanRuntimeError(
                "min_support_ratio muss in (0, 1] liegen")
        if (
                isinstance(self.maximum_consecutive_rejections, bool)
                or not isinstance(self.maximum_consecutive_rejections, int)
                or self.maximum_consecutive_rejections <= 0
                or self.maximum_consecutive_rejections > 64):
            raise PortalFrozenScanRuntimeError(
                "maximum_consecutive_rejections ist ungueltig")


class FrozenScanPortalMonitor:
    """Observe one bounded scan stream during a regular Nav2 child."""

    def __init__(
            self,
            candidate: PortalGoalCandidate,
            portal: PortalSnapshot,
            traversal_policy: PortalTraversalPolicy,
            runtime_policy: PortalTraversalRuntimePolicy,
            monitor_policy: FrozenScanMonitorPolicy,
            scope: AuthorizedExplorationScope,
            scope_clearance_m: float,
            read_scan: Callable[[], Optional[FrozenScanSample]],
            pose_at_stamp: Callable[[int], Optional[ExactTimeMapPose]],
    ) -> None:
        if not isinstance(monitor_policy, FrozenScanMonitorPolicy):
            raise PortalFrozenScanRuntimeError(
                "monitor_policy muss FrozenScanMonitorPolicy sein")
        if (
                not isinstance(scope, AuthorizedExplorationScope)
                or scope.scope_id != candidate.scope_id
                or scope.fingerprint != candidate.scope_fingerprint
                or scope.context != candidate.context):
            raise PortalFrozenScanRuntimeError(
                "Auftragsscope passt nicht zum Zielkandidaten")
        if (
                isinstance(scope_clearance_m, bool)
                or not isinstance(scope_clearance_m, (int, float))
                or not math.isfinite(float(scope_clearance_m))
                or float(scope_clearance_m) <= 0.0):
            raise PortalFrozenScanRuntimeError(
                "scope_clearance_m muss endlich und positiv sein")
        for callback, name in (
                (read_scan, "read_scan"),
                (pose_at_stamp, "pose_at_stamp")):
            if not callable(callback):
                raise PortalFrozenScanRuntimeError(
                    f"{name} muss aufrufbar sein")
        self._candidate = candidate
        self._portal = portal
        self._session = PortalTraversalRuntimeSession(
            candidate, portal, traversal_policy, runtime_policy)
        self._traversal_policy = traversal_policy
        self._policy = monitor_policy
        self._scope = scope
        self._scope_clearance_m = float(scope_clearance_m)
        self._read_scan = read_scan
        self._pose_at_stamp = pose_at_stamp
        self._matcher = None
        self._last_scan_id = None
        self._last_scan_pose = (0.0, 0.0, 0.0)
        self._reference_map_yaw = None
        self._consecutive_rejections = 0
        self._fault = None
        self._finished = False

    @property
    def fault(self) -> Optional[str]:
        return self._fault

    @staticmethod
    def _portal_axis_yaw(
            candidate: PortalGoalCandidate,
            portal: PortalSnapshot) -> float:
        axis_x = portal.side_b.x - portal.side_a.x
        axis_y = portal.side_b.y - portal.side_a.y
        if candidate.direction is TraversalDirection.B_TO_A:
            axis_x = -axis_x
            axis_y = -axis_y
        if math.hypot(axis_x, axis_y) <= 1e-9:
            raise PortalFrozenScanRuntimeError(
                "Portalachse ist entartet")
        return math.atan2(axis_y, axis_x)

    def _reject(self, reason: str) -> bool:
        self._consecutive_rejections += 1
        if self._consecutive_rejections >= (
                self._policy.maximum_consecutive_rejections):
            self._fault = reason
            return False
        return True

    def observe(self) -> bool:
        """Consume at most one new scan; false requests child cancellation."""
        if self._finished or self._fault is not None:
            return False
        try:
            scan = self._read_scan()
        except Exception:
            self._fault = "scan_reader_error"
            return False
        if not isinstance(scan, FrozenScanSample):
            return self._reject("fresh_scan_unavailable")
        if scan.sample_id == self._last_scan_id:
            return True
        try:
            pose = self._pose_at_stamp(scan.stamp_ns)
        except Exception:
            pose = None
        if (
                not isinstance(pose, ExactTimeMapPose)
                or pose.stamp_ns != scan.stamp_ns
                or pose.context != self._candidate.context
                or pose.map_revision > self._candidate.map_revision):
            self._last_scan_id = scan.sample_id
            return self._reject("exact_time_map_pose_unavailable")
        if not point_within_scope_clearance(
                self._scope,
                context=pose.context,
                x_m=pose.x,
                y_m=pose.y,
                clearance_m=self._scope_clearance_m):
            self._fault = "pose_left_authorized_scope"
            return False

        if self._matcher is None:
            axis_yaw = self._portal_axis_yaw(
                self._candidate, self._portal)
            axis_x = math.cos(axis_yaw)
            axis_y = math.sin(axis_yaw)
            start_anchor = self._portal.side_a
            if self._candidate.direction is TraversalDirection.B_TO_A:
                start_anchor = self._portal.side_b
            relative_x = pose.x - start_anchor.x
            relative_y = pose.y - start_anchor.y
            projection = relative_x * axis_x + relative_y * axis_y
            start_clearance = (
                -projection
                - self._traversal_policy.chassis_front_overhang_m)
            if start_clearance < self._traversal_policy.start_clearance_m:
                self._fault = "crossing_started_before_monitor"
                return False
            lateral = abs(-relative_x * axis_y + relative_y * axis_x)
            heading_error = abs(normalize_angle(pose.yaw - axis_yaw))
            if (
                    lateral
                    > self._traversal_policy.maximum_lateral_deviation_m
                    or heading_error
                    > self._traversal_policy.maximum_yaw_error_rad):
                self._last_scan_id = scan.sample_id
                return True

        try:
            if self._matcher is None:
                self._matcher = LidarReferenceMatcher(scan.points)
                estimate = self._matcher.estimate(
                    scan.points, (0.0, 0.0, 0.0))
                self._reference_map_yaw = pose.yaw
            else:
                estimate = self._matcher.estimate(
                    scan.points, self._last_scan_pose)
        except (ValueError, MemoryError):
            self._last_scan_id = scan.sample_id
            return self._reject("scan_match_error")

        reliable = motion_estimate_is_reliable(
            estimate,
            max_cost_m=self._policy.max_cost_m,
            min_support_ratio=self._policy.min_support_ratio,
            min_distinct_gap_m=self._policy.min_distinct_gap_m,
        )
        if self._matcher is not None and self._session.sample_count > 0:
            reliable = reliable and (
                math.hypot(
                    estimate.x_m - self._last_scan_pose[0],
                    estimate.y_m - self._last_scan_pose[1])
                <= self._policy.maximum_scan_step_m
                and abs(normalize_angle(
                    estimate.yaw_rad - self._last_scan_pose[2]))
                <= self._policy.maximum_scan_yaw_step_rad
            )
        self._last_scan_id = scan.sample_id
        if not reliable:
            return self._reject("scan_match_not_reliable")

        axis_yaw = self._portal_axis_yaw(self._candidate, self._portal)
        local_axis_yaw = normalize_angle(
            axis_yaw - self._reference_map_yaw)
        independent_progress = (
            estimate.x_m * math.cos(local_axis_yaw)
            + estimate.y_m * math.sin(local_axis_yaw)
        )
        try:
            self._session.observe(PairedTraversalReading(
                reading_id=scan.sample_id,
                context=pose.context,
                map_revision=pose.map_revision,
                stamp_ns=pose.stamp_ns,
                x=pose.x,
                y=pose.y,
                yaw=pose.yaw,
                independent_forward_progress_m=independent_progress,
                independent_source=(
                    IndependentMotionSource.FROZEN_RANGE_SCAN),
            ))
        except Exception:
            self._fault = "paired_sample_rejected"
            return False
        self._last_scan_pose = (
            estimate.x_m, estimate.y_m, estimate.yaw_rad)
        self._consecutive_rejections = 0
        return True

    def finish(
            self, *, execution_succeeded: bool,
            evaluated_at_ns: int,
    ) -> PortalTraversalRuntimeOutcome:
        if self._finished:
            raise PortalFrozenScanRuntimeError(
                "Portalmonitor darf nur einmal abgeschlossen werden")
        self._finished = True
        if self._fault is not None:
            return PortalTraversalRuntimeOutcome(
                confirmed=False,
                reason=f"monitor_failed:{self._fault}",
                sample_count=self._session.sample_count,
                assessment=None,
            )
        return self._session.finish(
            execution_succeeded=execution_succeeded,
            evaluated_at_ns=evaluated_at_ns,
        )
