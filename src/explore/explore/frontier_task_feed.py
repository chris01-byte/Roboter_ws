"""Pure, bounded tracking for passive frontier-task observations.

The feed consumes already detected, unfiltered frontier clusters from one
exactly correlated raw map.  It never ranks, blacklists, completes, selects or
executes a task.  A missing cluster therefore cannot make work disappear.
"""

from dataclasses import dataclass, replace
import hashlib
import math
import struct
from typing import Iterable, Optional, Tuple

from .portal_memory import Point2D, PortalMapContext
from .portal_source_adapter import PortalSourceCorrelation


class FrontierTaskFeedError(ValueError):
    """The passive frontier inventory is invalid or contradictory."""


class FrontierTaskFeedCapacityError(FrontierTaskFeedError):
    """A configured hard in-memory bound would be exceeded."""


def _positive_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FrontierTaskFeedError(
            f"{name} muss eine positive Ganzzahl sein")
    return value


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FrontierTaskFeedError(f"{name} muss endlich und nichtnegativ sein")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0:
        raise FrontierTaskFeedError(f"{name} muss endlich und nichtnegativ sein")
    return normalized


@dataclass(frozen=True)
class FrontierTaskPolicy:
    """Conservative association threshold and hard track bound."""

    association_radius_m: float = 0.60
    max_frontiers: int = 4096

    def __post_init__(self) -> None:
        radius = _finite_nonnegative(
            self.association_radius_m, "association_radius_m")
        if radius <= 0.0:
            raise FrontierTaskFeedError(
                "association_radius_m muss positiv sein")
        object.__setattr__(self, "association_radius_m", radius)
        _positive_integer(self.max_frontiers, "max_frontiers")


@dataclass(frozen=True)
class FrontierClusterObservation:
    """One unfiltered frontier cluster in metric map coordinates."""

    centroid: Point2D
    size_cells: int

    def __post_init__(self) -> None:
        if not isinstance(self.centroid, Point2D):
            raise FrontierTaskFeedError("centroid muss Point2D sein")
        _positive_integer(self.size_cells, "size_cells")


@dataclass(frozen=True)
class FrontierInventory:
    """All raw frontier clusters from one exact map revision."""

    inventory_id: str
    context: PortalMapContext
    map_revision: int
    clusters: Tuple[FrontierClusterObservation, ...]

    def __post_init__(self) -> None:
        if (
                not isinstance(self.inventory_id, str)
                or not self.inventory_id.startswith("frontier-inventory-")
                or len(self.inventory_id) > 128
                or not self.inventory_id.isascii()):
            raise FrontierTaskFeedError("inventory_id ist ungueltig")
        if not isinstance(self.context, PortalMapContext):
            raise FrontierTaskFeedError("context muss PortalMapContext sein")
        if (
                isinstance(self.map_revision, bool)
                or not isinstance(self.map_revision, int)
                or self.map_revision < 0):
            raise FrontierTaskFeedError(
                "map_revision muss eine nichtnegative Ganzzahl sein")
        if not isinstance(self.clusters, tuple) or any(
                not isinstance(cluster, FrontierClusterObservation)
                for cluster in self.clusters):
            raise FrontierTaskFeedError(
                "clusters muss ein Tupel aus FrontierClusterObservation sein")


@dataclass(frozen=True)
class FrontierAssignment:
    """Stable passive frontier identity assigned to one current cluster."""

    frontier_id: str
    observation: FrontierClusterObservation
    created: bool


@dataclass(frozen=True)
class FrontierInventoryResult:
    """Deterministic, replayable outcome for one complete inventory."""

    inventory_id: str
    map_revision: int
    assignments: Tuple[FrontierAssignment, ...]
    duplicate: bool = False


@dataclass(frozen=True)
class FrontierTrackSnapshot:
    frontier_id: str
    centroid: Point2D
    size_cells: int
    first_revision: int
    last_revision: int
    observation_count: int


@dataclass
class _FrontierTrack:
    frontier_id: str
    centroid: Point2D
    size_cells: int
    first_revision: int
    last_revision: int
    observation_count: int = 1


def frontier_inventory_from_clusters(
        correlation: PortalSourceCorrelation,
        clusters: Iterable[Tuple[float, float, int]], *,
        maximum_clusters: int = 4096) -> FrontierInventory:
    """Bind all unfiltered clusters to one exact raw-map correlation."""
    if not isinstance(correlation, PortalSourceCorrelation):
        raise FrontierTaskFeedError(
            "correlation muss PortalSourceCorrelation sein")
    if not isinstance(correlation.context, PortalMapContext):
        raise FrontierTaskFeedError(
            "correlation.context muss PortalMapContext sein")
    if (
            isinstance(correlation.map_revision, bool)
            or not isinstance(correlation.map_revision, int)
            or correlation.map_revision < 0):
        raise FrontierTaskFeedError(
            "correlation.map_revision ist ungueltig")
    if (
            not isinstance(correlation.fingerprint, str)
            or len(correlation.fingerprint) != 64
            or any(character not in "0123456789abcdef"
                   for character in correlation.fingerprint)):
        raise FrontierTaskFeedError(
            "correlation.fingerprint ist ungueltig")
    if (
            isinstance(correlation.source_stamp_ns, bool)
            or not isinstance(correlation.source_stamp_ns, int)
            or correlation.source_stamp_ns < 0):
        raise FrontierTaskFeedError(
            "correlation.source_stamp_ns ist ungueltig")
    limit = _positive_integer(maximum_clusters, "maximum_clusters")
    normalized = []
    try:
        iterator = iter(clusters)
    except TypeError as error:
        raise FrontierTaskFeedError("clusters muss iterierbar sein") from error
    for raw in iterator:
        try:
            x, y, size_cells = raw
        except (TypeError, ValueError) as error:
            raise FrontierTaskFeedError(
                "Frontiercluster braucht x, y und size_cells") from error
        try:
            normalized.append(FrontierClusterObservation(
                centroid=Point2D(x, y),
                size_cells=size_cells,
            ))
        except ValueError as error:
            raise FrontierTaskFeedError(
                "Frontiercluster ist ungueltig") from error
        if len(normalized) > limit:
            raise FrontierTaskFeedCapacityError(
                "Frontierbestand ueberschreitet maximum_clusters")
    normalized.sort(key=lambda item: (
        item.centroid.x, item.centroid.y, item.size_cells))

    digest = hashlib.sha256()
    digest.update(b"we-frontier-inventory-v1\0")
    digest.update(correlation.context.session_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.context.map_id.encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.context.frame_id.encode("ascii"))
    digest.update(str(correlation.map_revision).encode("ascii"))
    digest.update(b"\0")
    digest.update(correlation.fingerprint.encode("ascii"))
    digest.update(b"\0")
    digest.update(str(correlation.source_stamp_ns).encode("ascii"))
    for cluster in normalized:
        digest.update(struct.pack(
            "!dd", cluster.centroid.x, cluster.centroid.y))
        digest.update(str(cluster.size_cells).encode("ascii"))
        digest.update(b"\0")
    return FrontierInventory(
        inventory_id=f"frontier-inventory-{digest.hexdigest()}",
        context=correlation.context,
        map_revision=correlation.map_revision,
        clusters=tuple(normalized),
    )


class FrontierTaskTracker:
    """Associate only unambiguous clusters; preserve all previous tracks."""

    def __init__(
            self, context: PortalMapContext, *,
            policy: Optional[FrontierTaskPolicy] = None) -> None:
        if not isinstance(context, PortalMapContext):
            raise FrontierTaskFeedError("context muss PortalMapContext sein")
        if policy is not None and not isinstance(policy, FrontierTaskPolicy):
            raise FrontierTaskFeedError("policy muss FrontierTaskPolicy sein")
        self._context = context
        self._policy = policy or FrontierTaskPolicy()
        self._tracks: dict[str, _FrontierTrack] = {}
        self._last_inventory: Optional[
            tuple[FrontierInventory, FrontierInventoryResult]] = None
        self._next_frontier_number = 1
        self._latest_revision: Optional[int] = None

    @property
    def latest_revision(self) -> Optional[int]:
        return self._latest_revision

    def observe(self, inventory: FrontierInventory) -> FrontierInventoryResult:
        if not isinstance(inventory, FrontierInventory):
            raise FrontierTaskFeedError("inventory muss FrontierInventory sein")
        if inventory.context != self._context:
            raise FrontierTaskFeedError(
                "Frontierbestand passt nicht zum aktiven Kartenkontext")
        previous = self._last_inventory
        if previous is not None and previous[0].inventory_id == (
                inventory.inventory_id):
            previous_inventory, previous_result = previous
            if previous_inventory != inventory:
                raise FrontierTaskFeedError(
                    "inventory_id wurde widerspruechlich wiederverwendet")
            return replace(previous_result, duplicate=True)
        if (
                self._latest_revision is not None
                and inventory.map_revision <= self._latest_revision):
            raise FrontierTaskFeedError(
                "Kartenrevision besitzt bereits einen anderen oder neueren "
                "Frontierbestand")

        track_ids = tuple(sorted(self._tracks))
        observation_neighbors = []
        track_neighbors = {track_id: [] for track_id in track_ids}
        for index, cluster in enumerate(inventory.clusters):
            neighbors = []
            for track_id in track_ids:
                track = self._tracks[track_id]
                distance = math.hypot(
                    cluster.centroid.x - track.centroid.x,
                    cluster.centroid.y - track.centroid.y,
                )
                if distance <= self._policy.association_radius_m:
                    neighbors.append((distance, track_id))
                    track_neighbors[track_id].append((distance, index))
            observation_neighbors.append(tuple(neighbors))

        def unique_nearest(values):
            ordered = sorted(values)
            if not ordered:
                return None
            if len(ordered) > 1 and math.isclose(
                    ordered[0][0], ordered[1][0],
                    rel_tol=0.0, abs_tol=1e-9):
                return None
            return ordered[0][1]

        observation_choices = {
            index: unique_nearest(neighbors)
            for index, neighbors in enumerate(observation_neighbors)
        }
        track_choices = {
            track_id: unique_nearest(neighbors)
            for track_id, neighbors in track_neighbors.items()
        }
        matched = {}
        for index, track_id in observation_choices.items():
            if track_id is not None and track_choices[track_id] == index:
                matched[index] = track_id
        new_count = len(inventory.clusters) - len(matched)
        if len(self._tracks) + new_count > self._policy.max_frontiers:
            raise FrontierTaskFeedCapacityError(
                "Frontiergedaechtnis ist voll")

        assignments = []
        for index, cluster in enumerate(inventory.clusters):
            track_id = matched.get(index)
            created = track_id is None
            if created:
                track_id = f"frontier_{self._next_frontier_number:06d}"
                self._next_frontier_number += 1
                self._tracks[track_id] = _FrontierTrack(
                    frontier_id=track_id,
                    centroid=cluster.centroid,
                    size_cells=cluster.size_cells,
                    first_revision=inventory.map_revision,
                    last_revision=inventory.map_revision,
                )
            else:
                track = self._tracks[track_id]
                track.centroid = cluster.centroid
                track.size_cells = cluster.size_cells
                track.last_revision = inventory.map_revision
                track.observation_count += 1
            assignments.append(FrontierAssignment(
                frontier_id=track_id,
                observation=cluster,
                created=created,
            ))
        result = FrontierInventoryResult(
            inventory_id=inventory.inventory_id,
            map_revision=inventory.map_revision,
            assignments=tuple(assignments),
        )
        self._last_inventory = (inventory, result)
        self._latest_revision = inventory.map_revision
        return result

    def tracks(self) -> Tuple[FrontierTrackSnapshot, ...]:
        return tuple(
            FrontierTrackSnapshot(
                frontier_id=track.frontier_id,
                centroid=track.centroid,
                size_cells=track.size_cells,
                first_revision=track.first_revision,
                last_revision=track.last_revision,
                observation_count=track.observation_count,
            )
            for track in sorted(
                self._tracks.values(), key=lambda item: item.frontier_id)
        )
