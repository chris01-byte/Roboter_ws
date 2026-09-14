"""Pure immutable metric scope for bounded apartment exploration goals."""

from dataclasses import dataclass
import hashlib
import math
from typing import Tuple

import numpy as np

from .portal_memory import Point2D, PortalMapContext


class ExplorationScopeError(ValueError):
    """A scope or its exact map projection is unsafe or inconsistent."""


def _orientation(a: Point2D, b: Point2D, c: Point2D) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _on_segment(first: Point2D, middle: Point2D, second: Point2D) -> bool:
    return (
        min(first.x, second.x) - 1e-12 <= middle.x
        <= max(first.x, second.x) + 1e-12
        and min(first.y, second.y) - 1e-12 <= middle.y
        <= max(first.y, second.y) + 1e-12
    )


def _segments_intersect(
        first_a: Point2D, first_b: Point2D,
        second_a: Point2D, second_b: Point2D) -> bool:
    first = _orientation(first_a, first_b, second_a)
    second = _orientation(first_a, first_b, second_b)
    third = _orientation(second_a, second_b, first_a)
    fourth = _orientation(second_a, second_b, first_b)
    if first * second < -1e-12 and third * fourth < -1e-12:
        return True
    return (
        (abs(first) <= 1e-12
         and _on_segment(first_a, second_a, first_b))
        or (abs(second) <= 1e-12
            and _on_segment(first_a, second_b, first_b))
        or (abs(third) <= 1e-12
            and _on_segment(second_a, first_a, second_b))
        or (abs(fourth) <= 1e-12
            and _on_segment(second_a, first_b, second_b))
    )


@dataclass(frozen=True)
class AuthorizedExplorationScope:
    """A user-reviewed simple polygon bound to one map/session context."""

    scope_id: str
    context: PortalMapContext
    vertices: Tuple[Point2D, ...]
    max_vertices: int = 64

    def __post_init__(self) -> None:
        if (
                not isinstance(self.scope_id, str)
                or not self.scope_id
                or len(self.scope_id) > 128
                or not self.scope_id.isascii()
                or not self.scope_id[0].isalnum()
                or any(
                    not (character.isalnum() or character in "_.:-")
                    for character in self.scope_id)):
            raise ExplorationScopeError("scope_id ist ungueltig")
        if not isinstance(self.context, PortalMapContext):
            raise ExplorationScopeError(
                "context muss PortalMapContext sein")
        if (
                isinstance(self.max_vertices, bool)
                or not isinstance(self.max_vertices, int)
                or self.max_vertices < 3):
            raise ExplorationScopeError(
                "max_vertices muss mindestens drei sein")
        if (
                not isinstance(self.vertices, tuple)
                or len(self.vertices) < 3
                or len(self.vertices) > self.max_vertices
                or any(
                    not isinstance(vertex, Point2D)
                    for vertex in self.vertices)):
            raise ExplorationScopeError(
                "vertices muss ein begrenztes Point2D-Tupel sein")
        if len(set((item.x, item.y) for item in self.vertices)) != (
                len(self.vertices)):
            raise ExplorationScopeError(
                "Scope-Ecken muessen eindeutig sein")
        twice_area = sum(
            first.x * second.y - second.x * first.y
            for first, second in zip(
                self.vertices, self.vertices[1:] + self.vertices[:1]))
        if abs(twice_area) <= 1e-12:
            raise ExplorationScopeError(
                "Scope-Polygon braucht positive Flaeche")
        edges = tuple(zip(
            self.vertices, self.vertices[1:] + self.vertices[:1]))
        for first_index, first_edge in enumerate(edges):
            for second_index in range(first_index + 1, len(edges)):
                if (
                        second_index == first_index + 1
                        or (first_index == 0
                            and second_index == len(edges) - 1)):
                    continue
                if _segments_intersect(
                        *first_edge, *edges[second_index]):
                    raise ExplorationScopeError(
                        "Scope-Polygon darf sich nicht schneiden")

    @property
    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(b"we-exploration-scope-v1\0")
        for value in (
                self.scope_id,
                self.context.session_id,
                self.context.map_id,
                self.context.frame_id):
            digest.update(value.encode("ascii"))
            digest.update(b"\0")
        for vertex in self.vertices:
            digest.update(float(vertex.x).hex().encode("ascii"))
            digest.update(b"\0")
            digest.update(float(vertex.y).hex().encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()


def rasterize_scope(
        scope: AuthorizedExplorationScope, *,
        context: PortalMapContext,
        width: int,
        height: int,
        resolution_m: float,
        origin_x_m: float,
        origin_y_m: float,
        origin_yaw_rad: float,
        maximum_cells: int,
) -> np.ndarray:
    """Return cell-centre inclusion for one exact planar map geometry."""
    if not isinstance(scope, AuthorizedExplorationScope):
        raise ExplorationScopeError(
            "scope muss AuthorizedExplorationScope sein")
    if context != scope.context:
        raise ExplorationScopeError(
            "Scope passt nicht zum Kartenkontext")
    if (
            isinstance(width, bool) or not isinstance(width, int)
            or isinstance(height, bool) or not isinstance(height, int)
            or isinstance(maximum_cells, bool)
            or not isinstance(maximum_cells, int)
            or width <= 0 or height <= 0 or maximum_cells <= 0
            or width * height > maximum_cells):
        raise ExplorationScopeError(
            "Kartendimensionen ueberschreiten die Scope-Grenze")
    metric = (
        resolution_m, origin_x_m, origin_y_m, origin_yaw_rad)
    if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in metric) or resolution_m <= 0.0:
        raise ExplorationScopeError(
            "Scope-Projektion braucht endliche Kartengeometrie")

    rows, columns = np.indices((height, width), dtype=np.float64)
    local_x = (columns + 0.5) * float(resolution_m)
    local_y = (rows + 0.5) * float(resolution_m)
    cosine = math.cos(float(origin_yaw_rad))
    sine = math.sin(float(origin_yaw_rad))
    world_x = float(origin_x_m) + cosine * local_x - sine * local_y
    world_y = float(origin_y_m) + sine * local_x + cosine * local_y

    inside = np.zeros((height, width), dtype=bool)
    boundary = np.zeros((height, width), dtype=bool)
    vertices = scope.vertices
    for first, second in zip(vertices, vertices[1:] + vertices[:1]):
        dx = second.x - first.x
        dy = second.y - first.y
        cross = (
            (world_x - first.x) * dy
            - (world_y - first.y) * dx)
        dot = (
            (world_x - first.x) * (world_x - second.x)
            + (world_y - first.y) * (world_y - second.y))
        boundary |= (np.abs(cross) <= 1e-10) & (dot <= 1e-10)
        crossing = (
            (first.y > world_y) != (second.y > world_y))
        denominator = second.y - first.y
        if abs(denominator) <= 1e-15:
            continue
        crossing_x = (
            (second.x - first.x) * (world_y - first.y)
            / denominator + first.x)
        inside ^= crossing & (world_x < crossing_x)
    return inside | boundary
