"""Positive, revision-bound completion evidence for one reached frontier.

Navigation success is only the trigger for a later check.  A task is resolved
only when an exactly correlated newer raw map has no current frontier near the
old information window, keeps the reached target free, and observes the whole
window as known.  The module has no ROS, navigation, clock, or device access.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import math
from typing import Any, Iterable, Optional, Tuple

import numpy as np

from .child_result_policy import (
    ChildResultDisposition,
    ChildResultDispositionState,
)
from .exploration_policy import TaskAttemptOutcome
from .frontier_goal_candidate import FrontierGoalCandidate
from .frontier_task_evidence import (
    FrontierTaskEvidenceCapacityError,
    FrontierTaskEvidenceError,
    FrontierTaskEvidencePolicy,
    _validated_snapshot,
    _world_to_grid,
)
from .frontier_task_feed import FrontierTrackSnapshot
from .portal_memory import PortalMapContext
from .portal_source_adapter import PortalSourceCorrelation


class FrontierTaskResolutionError(ValueError):
    """The successful goal and newer raw-map evidence are inconsistent."""


class FrontierTaskResolutionCapacityError(FrontierTaskResolutionError):
    """A configured hard input or raw-map bound would be exceeded."""


class FrontierTaskResolutionState(str, Enum):
    CURRENT_FRONTIER_PRESENT = "current_frontier_present"
    TARGET_NOT_FREE = "target_not_free"
    INFORMATION_WINDOW_INCOMPLETE = "information_window_incomplete"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class FrontierTaskResolutionEvidence:
    resolution_id: str
    context: PortalMapContext
    task_id: str
    region_id: str
    frontier_id: str
    intent_id: str
    child_result_id: str
    goal_map_revision: int
    evidence_map_revision: int
    source_fingerprint: str
    source_stamp_ns: int
    state: FrontierTaskResolutionState
    reason: str
    checked_information_cells: int
    unknown_information_cells: int

    def __post_init__(self) -> None:
        for name in (
                "resolution_id", "task_id", "region_id", "frontier_id",
                "intent_id", "child_result_id"):
            value = getattr(self, name)
            if (
                    not isinstance(value, str) or not value or len(value) > 128
                    or not value.isascii() or not value[0].isalnum()
                    or any(
                        not (character.isalnum() or character in "_.:-")
                        for character in value)):
                raise FrontierTaskResolutionError(f"{name} ist ungueltig")
        if not isinstance(self.context, PortalMapContext):
            raise FrontierTaskResolutionError("context ist ungueltig")
        integer_fields = (
            self.goal_map_revision,
            self.evidence_map_revision,
            self.source_stamp_ns,
            self.checked_information_cells,
            self.unknown_information_cells,
        )
        if any(
                isinstance(value, bool) or not isinstance(value, int)
                or value < 0 for value in integer_fields):
            raise FrontierTaskResolutionError(
                "Revisions-, Zeit- oder Zellwerte sind ungueltig")
        if self.evidence_map_revision <= self.goal_map_revision:
            raise FrontierTaskResolutionError(
                "Abschlussevidenz muss neuer als das Ziel sein")
        if (
                not isinstance(self.source_fingerprint, str)
                or len(self.source_fingerprint) != 64
                or any(character not in "0123456789abcdef"
                       for character in self.source_fingerprint)):
            raise FrontierTaskResolutionError(
                "source_fingerprint ist ungueltig")
        if not isinstance(self.state, FrontierTaskResolutionState):
            raise FrontierTaskResolutionError("state ist ungueltig")
        if (
                not isinstance(self.reason, str) or not self.reason.strip()
                or len(self.reason) > 256):
            raise FrontierTaskResolutionError("reason ist ungueltig")
        if self.unknown_information_cells > self.checked_information_cells:
            raise FrontierTaskResolutionError(
                "Unbekannte Zellen ueberschreiten das Prueffenster")
        if (
                self.state is FrontierTaskResolutionState.RESOLVED
                and (
                    self.checked_information_cells <= 0
                    or self.unknown_information_cells != 0)):
            raise FrontierTaskResolutionError(
                "Positive Evidenz braucht ein vollstaendig bekanntes Fenster")

    @property
    def resolved(self) -> bool:
        return self.state is FrontierTaskResolutionState.RESOLVED


def _validate_success(
        candidate: FrontierGoalCandidate,
        disposition: ChildResultDisposition) -> None:
    if not isinstance(candidate, FrontierGoalCandidate):
        raise FrontierTaskResolutionError(
            "candidate muss FrontierGoalCandidate sein")
    if not isinstance(disposition, ChildResultDisposition):
        raise FrontierTaskResolutionError(
            "disposition muss ChildResultDisposition sein")
    attempt = disposition.attempt
    if (
            disposition.state is not ChildResultDispositionState.PROGRESSED
            or attempt is None
            or attempt.outcome is not TaskAttemptOutcome.PROGRESSED
            or disposition.terminates_exploration
            or disposition.intent_id != candidate.intent_id
            or disposition.task_id != candidate.task_id
            or disposition.map_revision != candidate.map_revision
            or attempt.task_id != candidate.task_id
            or attempt.map_revision != candidate.map_revision
            or attempt.context.frame_id != candidate.frame_id):
        raise FrontierTaskResolutionError(
            "Frontierabschluss braucht den passenden erfolgreichen Versuch")


def _resolution_id(
        disposition: ChildResultDisposition,
        correlation: PortalSourceCorrelation) -> str:
    digest = hashlib.sha256()
    digest.update(b"we-frontier-resolution-v1\0")
    digest.update(disposition.result_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(correlation.map_revision).encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.fingerprint.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(correlation.source_stamp_ns).encode("ascii"))
    return f"frontier-resolution-{digest.hexdigest()}"


def build_frontier_task_resolution_evidence(
        candidate: FrontierGoalCandidate,
        disposition: ChildResultDisposition,
        correlation: PortalSourceCorrelation, *,
        width: int, height: int, resolution: float, frame_id: str,
        origin: Tuple[float, float, float, float, float, float, float],
        cells: Iterable[Any], source_stamp_ns: int,
        tracks: Tuple[FrontierTrackSnapshot, ...],
        policy: Optional[FrontierTaskEvidencePolicy] = None,
) -> FrontierTaskResolutionEvidence:
    """Assess one complete newer frontier inventory and exact raw map."""
    _validate_success(candidate, disposition)
    if not isinstance(correlation, PortalSourceCorrelation):
        raise FrontierTaskResolutionError(
            "correlation muss PortalSourceCorrelation sein")
    attempt = disposition.attempt
    if (
            correlation.context != attempt.context
            or correlation.context.frame_id != candidate.frame_id
            or correlation.map_revision <= candidate.map_revision):
        raise FrontierTaskResolutionError(
            "Abschlussevidenz braucht einen neueren passenden Kartenstand")
    selected_policy = policy or FrontierTaskEvidencePolicy()
    if not isinstance(selected_policy, FrontierTaskEvidencePolicy):
        raise FrontierTaskResolutionError(
            "policy muss FrontierTaskEvidencePolicy sein")
    if not isinstance(tracks, tuple) or any(
            not isinstance(track, FrontierTrackSnapshot) for track in tracks):
        raise FrontierTaskResolutionError(
            "tracks muss ein Tupel aus FrontierTrackSnapshot sein")
    if len(tracks) > selected_policy.max_tracks:
        raise FrontierTaskResolutionCapacityError(
            "Frontierbestand ueberschreitet die Abschlussgrenze")
    track_ids = tuple(track.frontier_id for track in tracks)
    if len(set(track_ids)) != len(track_ids):
        raise FrontierTaskResolutionError(
            "Frontierbestand enthaelt Duplikate")
    if any(track.last_revision > correlation.map_revision for track in tracks):
        raise FrontierTaskResolutionError(
            "Frontiertrack liegt vor der Evidenzrevision")
    try:
        occupancy, resolution_m, clean_origin, map_yaw = _validated_snapshot(
            correlation,
            width=width,
            height=height,
            resolution=resolution,
            frame_id=frame_id,
            origin=origin,
            cells=cells,
            source_stamp_ns=source_stamp_ns,
            max_cells=selected_policy.max_cells,
        )
    except FrontierTaskEvidenceCapacityError as error:
        raise FrontierTaskResolutionCapacityError(str(error)) from error
    except FrontierTaskEvidenceError as error:
        raise FrontierTaskResolutionError(str(error)) from error

    current_tracks = tuple(
        track for track in tracks
        if track.last_revision == correlation.map_revision)
    nearby_current = any(
        math.hypot(
            track.centroid.x - candidate.frontier_x_m,
            track.centroid.y - candidate.frontier_y_m,
        ) <= selected_policy.information_radius_m
        for track in current_tracks
    )
    target_row, target_col = _world_to_grid(
        (candidate.target_x_m, candidate.target_y_m),
        clean_origin,
        map_yaw,
        resolution_m,
    )
    target_free = (
        0 <= target_row < occupancy.shape[0]
        and 0 <= target_col < occupancy.shape[1]
        and occupancy[target_row, target_col] == 0
    )
    frontier_row, frontier_col = _world_to_grid(
        (candidate.frontier_x_m, candidate.frontier_y_m),
        clean_origin,
        map_yaw,
        resolution_m,
    )
    radius_cells = max(1, int(math.ceil(
        selected_policy.information_radius_m / resolution_m)))
    complete_bounds = (
        frontier_row - radius_cells >= 0
        and frontier_row + radius_cells < occupancy.shape[0]
        and frontier_col - radius_cells >= 0
        and frontier_col + radius_cells < occupancy.shape[1]
    )
    checked_cells = 0
    unknown_cells = 0
    if complete_bounds:
        row0 = frontier_row - radius_cells
        row1 = frontier_row + radius_cells + 1
        col0 = frontier_col - radius_cells
        col1 = frontier_col + radius_cells + 1
        yy, xx = np.ogrid[row0:row1, col0:col1]
        disk = (
            (yy - frontier_row) ** 2 + (xx - frontier_col) ** 2
            <= radius_cells ** 2)
        window = occupancy[row0:row1, col0:col1]
        checked_cells = int(np.count_nonzero(disk))
        unknown_cells = int(np.count_nonzero((window < 0) & disk))

    if nearby_current:
        state = FrontierTaskResolutionState.CURRENT_FRONTIER_PRESENT
        reason = "current_frontier_remains_in_information_window"
    elif not target_free:
        state = FrontierTaskResolutionState.TARGET_NOT_FREE
        reason = "reached_target_not_confirmed_free"
    elif not complete_bounds or unknown_cells:
        state = FrontierTaskResolutionState.INFORMATION_WINDOW_INCOMPLETE
        reason = (
            "information_window_outside_map"
            if not complete_bounds else "unknown_cells_remain")
    else:
        state = FrontierTaskResolutionState.RESOLVED
        reason = "new_map_confirms_frontier_information_resolved"

    return FrontierTaskResolutionEvidence(
        resolution_id=_resolution_id(disposition, correlation),
        context=correlation.context,
        task_id=candidate.task_id,
        region_id=candidate.region_id,
        frontier_id=candidate.frontier_id,
        intent_id=candidate.intent_id,
        child_result_id=disposition.result_id,
        goal_map_revision=candidate.map_revision,
        evidence_map_revision=correlation.map_revision,
        source_fingerprint=correlation.fingerprint,
        source_stamp_ns=correlation.source_stamp_ns,
        state=state,
        reason=reason,
        checked_information_cells=checked_cells,
        unknown_information_cells=unknown_cells,
    )
