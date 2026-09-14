"""Fail-closed normalization of passive portal-plan candidates.

The current explorer's ``PortalPlan`` only carries costmap-derived geometry
and navigation targets.  This pure adapter therefore requires the caller to
supply the missing context, map revision, observation identity, and metric
uncertainty explicitly.  It never upgrades a plan to structural evidence and
has no ROS, planner, goal, traversal, filesystem, or actuator dependency.
"""

from dataclasses import dataclass
from typing import Tuple

from .portal_memory import (
    Point2D,
    PortalMapContext,
    PortalMemoryError,
    PortalObservation,
    PortalStructuralEvidence,
)


class PortalPlanAdapterError(ValueError):
    """A portal-plan candidate cannot be normalized without invention."""


@dataclass(frozen=True)
class PortalPlanCandidate:
    """Explicit passive inputs corresponding to one current portal plan.

    ``staging_xy`` is the near side in the declared map frame and
    ``target_xy`` the far side.  ``observation_id`` must be stable for an exact
    replay, but must not be derived from a transient list index.
    """

    observation_id: str
    context: PortalMapContext
    map_revision: int
    staging_xy: Tuple[float, float]
    target_xy: Tuple[float, float]
    uncertainty_m: float

    def __post_init__(self) -> None:
        _observation_from_candidate(self)


def _point_from_xy(value: object, name: str) -> Point2D:
    if not isinstance(value, tuple) or len(value) != 2:
        raise PortalPlanAdapterError(
            f"{name} muss ein unveraenderliches XY-Paar sein")
    try:
        return Point2D(value[0], value[1])
    except PortalMemoryError as exc:
        raise PortalPlanAdapterError(
            f"{name} ist keine endliche metrische Position") from exc


def _observation_from_candidate(
        candidate: PortalPlanCandidate) -> PortalObservation:
    if not isinstance(candidate.context, PortalMapContext):
        raise PortalPlanAdapterError(
            "context muss PortalMapContext sein")
    near_side = _point_from_xy(candidate.staging_xy, "staging_xy")
    far_side = _point_from_xy(candidate.target_xy, "target_xy")
    try:
        return PortalObservation(
            observation_id=candidate.observation_id,
            context=candidate.context,
            map_revision=candidate.map_revision,
            near_side=near_side,
            far_side=far_side,
            uncertainty_m=candidate.uncertainty_m,
            structural_evidence=PortalStructuralEvidence.INSUFFICIENT,
        )
    except PortalMemoryError as exc:
        raise PortalPlanAdapterError(
            "Portalplan-Eingang verletzt den Beobachtungsvertrag") from exc


def normalize_portal_plan_candidate(
        candidate: PortalPlanCandidate,
        expected_context: PortalMapContext) -> PortalObservation:
    """Return one unqualified observation without changing any state.

    A separately reviewed detector contract may one day provide qualified
    evidence.  This adapter deliberately cannot do so: a costmap bridge alone
    is insufficient and never proves a traversal.
    """
    if not isinstance(candidate, PortalPlanCandidate):
        raise PortalPlanAdapterError(
            "candidate muss PortalPlanCandidate sein")
    if not isinstance(expected_context, PortalMapContext):
        raise PortalPlanAdapterError(
            "expected_context muss PortalMapContext sein")
    if candidate.context != expected_context:
        raise PortalPlanAdapterError(
            "Portalplan passt nicht zu Sitzung, Karte und Frame")

    return _observation_from_candidate(candidate)
