"""ROS-unabhängiger Kern für Amadeus' manuelle semantische Raumkarte.

Der Kern kennt weder ROS noch Navigation. Er validiert die Bindung an einen
unveränderlichen Kartenfingerabdruck, Raumgeometrien, JSON-Kommandos und die
atomare, revisionsbasierte Ablage. Dadurch kann die sicherheitsrelevante
Fail-closed-Logik auf jedem Entwicklungsrechner getestet werden.
"""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any, Iterator, Optional, Sequence
import unicodedata
import uuid


SCHEMA_VERSION = 1
MAXIMUM_COMMAND_BYTES = 64 * 1024
MAXIMUM_STATUS_BYTES = 512 * 1024
MAXIMUM_DOCUMENT_BYTES = 4 * 1024 * 1024
MAXIMUM_ROOMS = 256
MAXIMUM_POLYGON_POINTS = 64
MAXIMUM_TOTAL_POLYGON_POINTS = 4_096
MAXIMUM_REQUEST_LOG_ENTRIES = 256
MAXIMUM_COORDINATE_ABS = 100_000.0
MINIMUM_POLYGON_AREA = 1e-6
DEFAULT_MAXIMUM_REVISIONS_PER_MAP = 2_048
DEFAULT_MAXIMUM_STORAGE_BYTES = 1024 * 1024 * 1024
DEFAULT_MINIMUM_FREE_SPACE_BYTES = 512 * 1024 * 1024
DEFAULT_REQUEST_CACHE_ENTRIES = 128
DEFAULT_REQUEST_CACHE_BYTES = 64 * 1024
MAXIMUM_STORAGE_SCAN_ENTRIES = 100_000
_REQUEST_CACHE_ENTRY_OVERHEAD_BYTES = 256

_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_MAP_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAP_VERSION_RE = re.compile(
    r"^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{12}(?:-[0-9]{2})?$"
)
_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class SemanticValidationError(ValueError):
    """Eingaben verletzen den Vertrag der semantischen Karte."""


class CommandValidationError(SemanticValidationError):
    """Ein JSON-Kommando ist syntaktisch oder semantisch ungültig."""


class RevisionConflictError(SemanticValidationError):
    """base_revision stimmt nicht mehr mit der gespeicherten Revision überein."""


class MapMismatchError(SemanticValidationError):
    """Kommando oder Datei gehört nicht zur aktuell bestätigten Karte."""


class RequestIDConflict(CommandValidationError):
    """Eine request_id wurde bereits für ein anderes Kommando verwendet."""


class SemanticStorageError(RuntimeError):
    """Die semantische Karte konnte nicht sicher gelesen/geschrieben werden."""


def default_storage_root(home: Optional[Path] = None) -> Path:
    """Standardpfad getrennt von Workspace und metrischen Kartenartefakten."""

    base = Path.home() if home is None else Path(home)
    return base / ".local" / "share" / "amadeus" / "semantic_maps"


def _finite_number(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise SemanticValidationError(f"{name} muss eine endliche Zahl sein.")
    result = float(value)
    if abs(result) > MAXIMUM_COORDINATE_ABS:
        raise SemanticValidationError(
            f"{name} überschreitet den erlaubten Betrag von "
            f"{MAXIMUM_COORDINATE_ABS:g}."
        )
    return result


def _positive_int(value: Any, name: str, *, maximum: int = 1_000_000) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise SemanticValidationError(
            f"{name} muss eine positive Ganzzahl bis {maximum} sein."
        )
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SemanticValidationError(
            f"{name} muss eine nichtnegative Ganzzahl sein."
        )
    return value


def _strict_object(
    value: Any,
    *,
    name: str,
    required: set[str],
    optional: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SemanticValidationError(f"{name} muss ein JSON-Objekt sein.")
    missing = sorted(required - set(value))
    if missing:
        raise SemanticValidationError(
            f"{name} fehlen Felder: {', '.join(missing)}."
        )
    unexpected = sorted(set(value) - required - optional)
    if unexpected:
        raise SemanticValidationError(
            f"{name} enthält unbekannte Felder: {', '.join(unexpected)}."
        )
    return value


def _validate_text(value: Any, name: str, *, maximum_chars: int) -> str:
    if not isinstance(value, str):
        raise SemanticValidationError(f"{name} muss eine Zeichenkette sein.")
    normalized = unicodedata.normalize("NFC", value).strip()
    if (
        not normalized
        or len(normalized) > maximum_chars
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in normalized)
    ):
        raise SemanticValidationError(
            f"{name} ist leer, zu lang oder enthält Steuerzeichen."
        )
    return normalized


def _validated_origin(value: Any) -> dict[str, Any]:
    origin = _strict_object(
        value,
        name="map_ref.origin",
        required={"position", "orientation"},
        optional={"yaw"},
    )
    position = _strict_object(
        origin["position"],
        name="map_ref.origin.position",
        required={"x", "y", "z"},
    )
    orientation = _strict_object(
        origin["orientation"],
        name="map_ref.origin.orientation",
        required={"x", "y", "z", "w"},
    )
    clean_position = {
        axis: _finite_number(position[axis], f"map_ref.origin.position.{axis}")
        for axis in ("x", "y", "z")
    }
    clean_orientation = {
        axis: _finite_number(
            orientation[axis], f"map_ref.origin.orientation.{axis}"
        )
        for axis in ("x", "y", "z", "w")
    }
    norm = math.sqrt(sum(value * value for value in clean_orientation.values()))
    if norm <= 1e-12 or abs(norm - 1.0) > 1e-3:
        raise SemanticValidationError(
            f"map_ref.origin.orientation ist nicht normalisiert (Norm {norm:.9g})."
        )
    x = clean_orientation["x"]
    y = clean_orientation["y"]
    z = clean_orientation["z"]
    w = clean_orientation["w"]
    calculated_yaw = math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )
    if "yaw" in origin:
        declared_yaw = _finite_number(origin["yaw"], "map_ref.origin.yaw")
        angular_error = math.atan2(
            math.sin(declared_yaw - calculated_yaw),
            math.cos(declared_yaw - calculated_yaw),
        )
        if abs(angular_error) > 1e-6:
            raise SemanticValidationError(
                "map_ref.origin.yaw widerspricht der Quaternion."
            )
    return {
        "position": clean_position,
        "orientation": clean_orientation,
        "yaw": calculated_yaw,
    }


@dataclass(frozen=True)
class MapReference:
    """Bestätigte, gespeicherte metrische Karte samt Darstellungsgeometrie."""

    name: str
    version: str
    fingerprint: str
    frame_id: str
    width: int
    height: int
    resolution: float
    origin: dict[str, Any]

    @classmethod
    def from_dict(cls, value: Any) -> "MapReference":
        payload = _strict_object(
            value,
            name="map_ref",
            required={
                "name",
                "version",
                "fingerprint",
                "frame_id",
                "width",
                "height",
                "resolution",
                "origin",
            },
        )
        name = payload["name"]
        if not isinstance(name, str) or not _MAP_NAME_RE.fullmatch(name):
            raise SemanticValidationError("map_ref.name ist ungültig.")
        version = payload["version"]
        if not isinstance(version, str) or not _MAP_VERSION_RE.fullmatch(version):
            raise SemanticValidationError("map_ref.version ist ungültig.")
        fingerprint = payload["fingerprint"]
        if (
            not isinstance(fingerprint, str)
            or not _FINGERPRINT_RE.fullmatch(fingerprint)
        ):
            raise SemanticValidationError(
                "map_ref.fingerprint muss aus genau 64 kleinen Hexzeichen bestehen."
            )
        frame_id = _validate_text(payload["frame_id"], "map_ref.frame_id", maximum_chars=128)
        width = _positive_int(payload["width"], "map_ref.width")
        height = _positive_int(payload["height"], "map_ref.height")
        if width * height > 4_000_000:
            raise SemanticValidationError(
                "map_ref enthält mehr als 4.000.000 Rasterzellen."
            )
        resolution = _finite_number(payload["resolution"], "map_ref.resolution")
        if resolution <= 0.0:
            raise SemanticValidationError("map_ref.resolution muss positiv sein.")
        return cls(
            name=name,
            version=version,
            fingerprint=fingerprint,
            frame_id=frame_id,
            width=width,
            height=height,
            resolution=resolution,
            origin=_validated_origin(payload["origin"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "frame_id": self.frame_id,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "origin": self.origin,
        }

    @property
    def extent(self) -> tuple[float, float]:
        return self.width * self.resolution, self.height * self.resolution

    def world_to_grid_meters(self, point: "Point2D") -> tuple[float, float]:
        dx = point.x - self.origin["position"]["x"]
        dy = point.y - self.origin["position"]["y"]
        yaw = self.origin["yaw"]
        return (
            math.cos(yaw) * dx + math.sin(yaw) * dy,
            -math.sin(yaw) * dx + math.cos(yaw) * dy,
        )

    def contains_map_point(self, point: "Point2D", *, tolerance: float = 1e-9) -> bool:
        local_x, local_y = self.world_to_grid_meters(point)
        extent_x, extent_y = self.extent
        return (
            -tolerance <= local_x <= extent_x + tolerance
            and -tolerance <= local_y <= extent_y + tolerance
        )


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    @classmethod
    def from_dict(cls, value: Any, *, name: str = "point") -> "Point2D":
        payload = _strict_object(value, name=name, required={"x", "y"})
        return cls(
            x=_finite_number(payload["x"], f"{name}.x"),
            y=_finite_number(payload["y"], f"{name}.y"),
        )

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class NavigationGoal:
    x: float
    y: float
    yaw: float

    @classmethod
    def from_dict(cls, value: Any) -> "NavigationGoal":
        payload = _strict_object(
            value,
            name="room.navigation_goal",
            required={"x", "y", "yaw"},
        )
        yaw = _finite_number(payload["yaw"], "room.navigation_goal.yaw")
        if yaw < -math.pi or yaw > math.pi:
            raise SemanticValidationError(
                "room.navigation_goal.yaw muss zwischen -π und +π liegen."
            )
        return cls(
            x=_finite_number(payload["x"], "room.navigation_goal.x"),
            y=_finite_number(payload["y"], "room.navigation_goal.y"),
            yaw=yaw,
        )

    @property
    def point(self) -> Point2D:
        return Point2D(self.x, self.y)

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "yaw": self.yaw}


def _cross(a: Point2D, b: Point2D, c: Point2D) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _point_on_segment(point: Point2D, a: Point2D, b: Point2D, *, eps: float = 1e-9) -> bool:
    return (
        abs(_cross(a, b, point)) <= eps
        and min(a.x, b.x) - eps <= point.x <= max(a.x, b.x) + eps
        and min(a.y, b.y) - eps <= point.y <= max(a.y, b.y) + eps
    )


def _segments_intersect(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> bool:
    eps = 1e-9
    o1 = _cross(a, b, c)
    o2 = _cross(a, b, d)
    o3 = _cross(c, d, a)
    o4 = _cross(c, d, b)
    if (
        ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps))
        and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps))
    ):
        return True
    return (
        (abs(o1) <= eps and _point_on_segment(c, a, b))
        or (abs(o2) <= eps and _point_on_segment(d, a, b))
        or (abs(o3) <= eps and _point_on_segment(a, c, d))
        or (abs(o4) <= eps and _point_on_segment(b, c, d))
    )


def _polygon_area(points: Sequence[Point2D]) -> float:
    doubled_area = 0.0
    for index, current in enumerate(points):
        following = points[(index + 1) % len(points)]
        doubled_area += current.x * following.y - following.x * current.y
    return 0.5 * doubled_area


def _validate_simple_polygon(points: Sequence[Point2D]) -> None:
    if len(points) < 3 or len(points) > MAXIMUM_POLYGON_POINTS:
        raise SemanticValidationError(
            f"room.polygon benötigt 3 bis {MAXIMUM_POLYGON_POINTS} Punkte."
        )
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        if math.hypot(point.x - following.x, point.y - following.y) <= 1e-9:
            raise SemanticValidationError(
                "room.polygon enthält aufeinanderfolgende gleiche Punkte."
            )
    if len({(point.x, point.y) for point in points}) != len(points):
        raise SemanticValidationError("room.polygon enthält doppelte Punkte.")
    if abs(_polygon_area(points)) < MINIMUM_POLYGON_AREA:
        raise SemanticValidationError("room.polygon besitzt keine nutzbare Fläche.")

    edge_count = len(points)
    for first in range(edge_count):
        a = points[first]
        b = points[(first + 1) % edge_count]
        for second in range(first + 1, edge_count):
            if second == first:
                continue
            if (second + 1) % edge_count == first or (first + 1) % edge_count == second:
                continue
            c = points[second]
            d = points[(second + 1) % edge_count]
            if _segments_intersect(a, b, c, d):
                raise SemanticValidationError(
                    "room.polygon darf sich nicht selbst schneiden oder berühren."
                )


def _preflight_room_polygon_points(value: Any, *, name: str = "room") -> int:
    """Begrenzt Polygonarbeit, bevor Punkte oder O(P²)-Schnitte entstehen."""

    if not isinstance(value, dict):
        raise SemanticValidationError(f"{name} muss ein JSON-Objekt sein.")
    raw_polygon = value.get("polygon")
    if not isinstance(raw_polygon, list):
        raise SemanticValidationError(f"{name}.polygon muss eine JSON-Liste sein.")
    point_count = len(raw_polygon)
    if point_count < 3 or point_count > MAXIMUM_POLYGON_POINTS:
        raise SemanticValidationError(
            f"{name}.polygon benötigt 3 bis {MAXIMUM_POLYGON_POINTS} Punkte."
        )
    return point_count


def _preflight_document_polygon_points(raw_rooms: Sequence[Any]) -> int:
    total = 0
    for index, raw_room in enumerate(raw_rooms):
        total += _preflight_room_polygon_points(
            raw_room, name=f"rooms[{index}]"
        )
        if total > MAXIMUM_TOTAL_POLYGON_POINTS:
            raise SemanticValidationError(
                "Semantische Karte überschreitet das Gesamtlimit von "
                f"{MAXIMUM_TOTAL_POLYGON_POINTS} Polygonpunkten."
            )
    return total


def point_strictly_inside_polygon(point: Point2D, polygon: Sequence[Point2D]) -> bool:
    """Ray-casting mit explizitem Ausschluss der unsicheren Polygonkante."""

    for index, a in enumerate(polygon):
        b = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, a, b):
            return False
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if (current.y > point.y) != (previous.y > point.y):
            crossing_x = (
                (previous.x - current.x)
                * (point.y - current.y)
                / (previous.y - current.y)
                + current.x
            )
            if point.x < crossing_x:
                inside = not inside
        previous = current
    return inside


@dataclass(frozen=True)
class Room:
    id: str
    name: str
    polygon: tuple[Point2D, ...]
    navigation_goal: NavigationGoal
    color: Optional[str] = None

    @classmethod
    def from_dict(cls, value: Any, *, map_ref: MapReference) -> "Room":
        payload = _strict_object(
            value,
            name="room",
            required={"id", "name", "polygon", "navigation_goal"},
            optional={"color"},
        )
        room_id = payload["id"]
        if not isinstance(room_id, str) or not _SAFE_ID_RE.fullmatch(room_id):
            raise SemanticValidationError(
                "room.id muss 1–64 kleine ASCII-Zeichen aus a-z, 0-9, _ oder - enthalten."
            )
        name = _validate_text(payload["name"], "room.name", maximum_chars=80)
        raw_polygon = payload["polygon"]
        _preflight_room_polygon_points(payload)
        polygon = tuple(
            Point2D.from_dict(point, name=f"room.polygon[{index}]")
            for index, point in enumerate(raw_polygon)
        )
        _validate_simple_polygon(polygon)
        for index, point in enumerate(polygon):
            if not map_ref.contains_map_point(point):
                raise SemanticValidationError(
                    f"room.polygon[{index}] liegt außerhalb der metrischen Karte."
                )
        navigation_goal = NavigationGoal.from_dict(payload["navigation_goal"])
        if not map_ref.contains_map_point(navigation_goal.point):
            raise SemanticValidationError(
                "room.navigation_goal liegt außerhalb der metrischen Karte."
            )
        if not point_strictly_inside_polygon(navigation_goal.point, polygon):
            raise SemanticValidationError(
                "room.navigation_goal muss strikt innerhalb des Raum-Polygons liegen."
            )
        color = payload.get("color")
        if color is not None:
            if not isinstance(color, str) or not _COLOR_RE.fullmatch(color):
                raise SemanticValidationError(
                    "room.color muss als #RRGGBB angegeben werden."
                )
            color = color.upper()
        return cls(
            id=room_id,
            name=name,
            polygon=polygon,
            navigation_goal=navigation_goal,
            color=color,
        )

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "polygon": [point.as_dict() for point in self.polygon],
            "navigation_goal": self.navigation_goal.as_dict(),
        }
        if self.color is not None:
            payload["color"] = self.color
        return payload


@dataclass(frozen=True)
class SemanticCommand:
    command: str
    request_id: Optional[str]
    map_fingerprint: Optional[str] = None
    base_revision: Optional[int] = None
    room: Optional[dict[str, Any]] = None
    room_id: Optional[str] = None
    map_ref_selector: Optional[dict[str, str]] = None


def parse_command_json(text: Any) -> SemanticCommand:
    if not isinstance(text, str):
        raise CommandValidationError("Kommando muss als JSON-Zeichenkette ankommen.")
    # UTF-8 benötigt niemals weniger Bytes als die Zahl der Unicode-Codepoints.
    # Riesige Eingaben daher ohne zweite Vollkopie verwerfen.
    if len(text) > MAXIMUM_COMMAND_BYTES:
        raise CommandValidationError(
            f"Kommando überschreitet {MAXIMUM_COMMAND_BYTES} Bytes."
        )
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise CommandValidationError("Kommando enthält ungültiges Unicode.") from error
    if encoded_size > MAXIMUM_COMMAND_BYTES:
        raise CommandValidationError(
            f"Kommando überschreitet {MAXIMUM_COMMAND_BYTES} Bytes."
        )
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise CommandValidationError("Kommando enthält kein gültiges JSON.") from error
    if not isinstance(payload, dict):
        raise CommandValidationError("Kommando muss ein JSON-Objekt sein.")
    command = payload.get("command")
    if command not in {"bind_map", "get", "upsert_room", "delete_room", "status"}:
        raise CommandValidationError(
            "command muss bind_map, get, upsert_room, delete_room oder status sein."
        )
    schemas = {
        "get": ({"command"}, {"request_id"}),
        "status": ({"command"}, {"request_id"}),
        "bind_map": ({"command", "map_ref"}, {"request_id"}),
        "upsert_room": (
            {"command", "map_fingerprint", "base_revision", "room"},
            {"request_id"},
        ),
        "delete_room": (
            {"command", "map_fingerprint", "base_revision", "room_id"},
            {"request_id"},
        ),
    }
    required, optional = schemas[command]
    try:
        _strict_object(payload, name="command", required=required, optional=optional)
    except SemanticValidationError as error:
        raise CommandValidationError(str(error)) from error
    request_id = payload.get("request_id")
    if request_id is not None and (
        not isinstance(request_id, str) or not _REQUEST_ID_RE.fullmatch(request_id)
    ):
        raise CommandValidationError(
            "request_id muss 1–64 sichere ASCII-Zeichen enthalten."
        )

    if command == "bind_map":
        try:
            selector = _strict_object(
                payload["map_ref"],
                name="map_ref",
                required={"name", "version", "fingerprint"},
            )
        except SemanticValidationError as error:
            raise CommandValidationError(str(error)) from error
        name = selector["name"]
        version = selector["version"]
        fingerprint = selector["fingerprint"]
        if not isinstance(name, str) or not _MAP_NAME_RE.fullmatch(name):
            raise CommandValidationError("map_ref.name ist ungültig.")
        if not isinstance(version, str) or not _MAP_VERSION_RE.fullmatch(version):
            raise CommandValidationError("map_ref.version ist ungültig.")
        if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise CommandValidationError("map_ref.fingerprint ist ungültig.")
        return SemanticCommand(
            command=command,
            request_id=request_id,
            map_ref_selector={
                "name": name,
                "version": version,
                "fingerprint": fingerprint,
            },
        )

    if command in {"upsert_room", "delete_room"}:
        fingerprint = payload["map_fingerprint"]
        if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise CommandValidationError("map_fingerprint ist ungültig.")
        revision = payload["base_revision"]
        try:
            revision = _nonnegative_int(revision, "base_revision")
        except SemanticValidationError as error:
            raise CommandValidationError(str(error)) from error
        if request_id is None:
            raise CommandValidationError(
                "Schreibkommandos benötigen eine request_id für idempotente Wiederholung."
            )
        if command == "upsert_room":
            if not isinstance(payload["room"], dict):
                raise CommandValidationError("room muss ein JSON-Objekt sein.")
            try:
                _preflight_room_polygon_points(payload["room"])
            except SemanticValidationError as error:
                raise CommandValidationError(str(error)) from error
            return SemanticCommand(
                command=command,
                request_id=request_id,
                map_fingerprint=fingerprint,
                base_revision=revision,
                room=payload["room"],
            )
        room_id = payload["room_id"]
        if not isinstance(room_id, str) or not _SAFE_ID_RE.fullmatch(room_id):
            raise CommandValidationError("room_id ist ungültig.")
        return SemanticCommand(
            command=command,
            request_id=request_id,
            map_fingerprint=fingerprint,
            base_revision=revision,
            room_id=room_id,
        )

    return SemanticCommand(command=command, request_id=request_id)


@dataclass(frozen=True)
class MapManagerObservation:
    fingerprint: str
    map_summary: dict[str, Any]
    confirmed_references: tuple[MapReference, ...]


def parse_map_manager_status(text: Any) -> Optional[MapManagerObservation]:
    """Extrahiert nur belegte Kartenreferenzen aus dem fremden Statusvertrag.

    Ein Live-Snapshot ohne gespeicherte ``last_saved``-/``saved``-/``maps``-
    Referenz bestätigt zwar den Fingerabdruck, ist aber absichtlich nicht
    editierbar. Unbekannte zusätzliche Statusfelder werden toleriert, da sie
    dem anderen Paket gehören.
    """

    if not isinstance(text, str):
        raise SemanticValidationError("Kartenmanager-Status muss Text sein.")
    if len(text) > MAXIMUM_STATUS_BYTES:
        raise SemanticValidationError("Kartenmanager-Status ist zu groß.")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise SemanticValidationError(
            "Kartenmanager-Status enthält ungültiges Unicode."
        ) from error
    if encoded_size > MAXIMUM_STATUS_BYTES:
        raise SemanticValidationError("Kartenmanager-Status ist zu groß.")
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise SemanticValidationError(
            "Kartenmanager-Status enthält kein gültiges JSON."
        ) from error
    if not isinstance(payload, dict):
        raise SemanticValidationError("Kartenmanager-Status muss ein Objekt sein.")
    # Ein Fehlerstatus kann einen alten map.summary-Snapshot enthalten. Er ist
    # Diagnose, aber kein Beleg für eine aktuelle/editierbare Kartenbindung.
    if payload.get("ok") is not True:
        raise SemanticValidationError(
            "Kartenmanager-Status bestätigt den Zustand nicht mit ok=true."
        )
    map_status = payload.get("map")
    if not isinstance(map_status, dict):
        raise SemanticValidationError("Kartenmanager-Status enthält kein map-Objekt.")
    snapshot_available = map_status.get(
        "snapshot_available", map_status.get("available", False)
    )
    if not isinstance(snapshot_available, bool):
        raise SemanticValidationError("map.snapshot_available muss boolesch sein.")
    if not snapshot_available:
        return None
    summary = map_status.get("summary")
    if not isinstance(summary, dict):
        raise SemanticValidationError("Kartenmanager-Status enthält keine map.summary.")
    required_summary = {
        "fingerprint",
        "frame_id",
        "width",
        "height",
        "resolution",
        "origin",
    }
    missing = sorted(required_summary - set(summary))
    if missing:
        raise SemanticValidationError(
            f"map.summary fehlen Felder: {', '.join(missing)}."
        )
    fingerprint = summary["fingerprint"]
    if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
        raise SemanticValidationError("map.summary.fingerprint ist ungültig.")

    records: list[Any] = []
    storage = payload.get("storage")
    if isinstance(storage, dict) and storage.get("last_saved") is not None:
        records.append(storage["last_saved"])
    if payload.get("saved") is not None:
        records.append(payload["saved"])
    maps = payload.get("maps")
    if isinstance(maps, list):
        records.extend(maps)

    confirmed: list[MapReference] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("fingerprint") != fingerprint:
            continue
        merged = {
            "name": record.get("name"),
            "version": record.get("version"),
            "fingerprint": fingerprint,
            "frame_id": summary["frame_id"],
            "width": summary["width"],
            "height": summary["height"],
            "resolution": summary["resolution"],
            "origin": summary["origin"],
        }
        # Wenn ein SavedMap seine Geometrie deklariert, muss sie mit dem
        # aktuell sichtbaren Snapshot übereinstimmen; sonst ist es keine
        # belastbare Bestätigung für diesen Live-Zustand.
        if any(
            key in record and record[key] != summary[key]
            for key in ("frame_id", "width", "height", "resolution")
        ):
            continue
        try:
            reference = MapReference.from_dict(merged)
        except SemanticValidationError:
            continue
        key = (reference.name, reference.version, reference.fingerprint)
        if key not in seen:
            seen.add(key)
            confirmed.append(reference)
    return MapManagerObservation(
        fingerprint=fingerprint,
        map_summary=summary,
        confirmed_references=tuple(confirmed),
    )


def map_status_is_fresh(
    *,
    last_received_monotonic: Optional[float],
    now_monotonic: float,
    timeout_s: float,
) -> bool:
    """ROS-freie, rücksprungsichere Frischeprüfung für Schreibfreigaben."""

    if last_received_monotonic is None:
        return False
    values = {
        "last_received_monotonic": last_received_monotonic,
        "now_monotonic": now_monotonic,
        "timeout_s": timeout_s,
    }
    clean: dict[str, float] = {}
    for name, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise SemanticValidationError(f"{name} muss eine endliche Zahl sein.")
        clean[name] = float(value)
    last = clean["last_received_monotonic"]
    now = clean["now_monotonic"]
    timeout = clean["timeout_s"]
    if timeout <= 0.0:
        raise SemanticValidationError("timeout_s muss positiv sein.")
    age = now - last
    return 0.0 <= age <= timeout


@dataclass(frozen=True)
class SemanticDocument:
    map_ref: MapReference
    revision: int
    rooms: tuple[Room, ...]
    updated_at: str
    request_log: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_dict(cls, value: Any) -> "SemanticDocument":
        payload = _strict_object(
            value,
            name="semantic document",
            required={
                "schema_version",
                "map_ref",
                "revision",
                "rooms",
                "updated_at",
                "request_log",
            },
        )
        if payload["schema_version"] != SCHEMA_VERSION:
            raise SemanticValidationError("Unbekannte semantic schema_version.")
        map_ref = MapReference.from_dict(payload["map_ref"])
        revision = _nonnegative_int(payload["revision"], "revision")
        raw_rooms = payload["rooms"]
        if not isinstance(raw_rooms, list) or len(raw_rooms) > MAXIMUM_ROOMS:
            raise SemanticValidationError(
                f"rooms muss eine Liste mit höchstens {MAXIMUM_ROOMS} Räumen sein."
            )
        _preflight_document_polygon_points(raw_rooms)
        rooms = tuple(Room.from_dict(room, map_ref=map_ref) for room in raw_rooms)
        ids = [room.id for room in rooms]
        if len(set(ids)) != len(ids):
            raise SemanticValidationError("Raum-IDs müssen eindeutig sein.")
        names = [room.name.casefold() for room in rooms]
        if len(set(names)) != len(names):
            raise SemanticValidationError("Raumnamen müssen eindeutig sein.")
        updated_at = _validate_text(payload["updated_at"], "updated_at", maximum_chars=40)
        request_log = _validate_request_log(payload["request_log"])
        return cls(
            map_ref=map_ref,
            revision=revision,
            rooms=rooms,
            updated_at=updated_at,
            request_log=request_log,
        )

    def as_dict(self, *, include_request_log: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "map_ref": self.map_ref.as_dict(),
            "revision": self.revision,
            "rooms": [room.as_dict() for room in self.rooms],
            "updated_at": self.updated_at,
        }
        if include_request_log:
            payload["request_log"] = list(self.request_log)
        return payload


def _validate_request_log(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or len(value) > MAXIMUM_REQUEST_LOG_ENTRIES:
        raise SemanticValidationError("request_log ist ungültig oder zu groß.")
    clean: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw in enumerate(value):
        entry = _strict_object(
            raw,
            name=f"request_log[{index}]",
            required={"request_id", "signature", "revision", "event", "message"},
        )
        request_id = entry["request_id"]
        signature = entry["signature"]
        event = entry["event"]
        message = entry["message"]
        if not isinstance(request_id, str) or not _REQUEST_ID_RE.fullmatch(request_id):
            raise SemanticValidationError("request_log enthält ungültige request_id.")
        if request_id in ids:
            raise SemanticValidationError("request_log enthält doppelte request_id.")
        ids.add(request_id)
        if not isinstance(signature, str) or not _FINGERPRINT_RE.fullmatch(signature):
            raise SemanticValidationError("request_log enthält ungültige Signatur.")
        revision = _nonnegative_int(entry["revision"], "request_log.revision")
        event = _validate_text(event, "request_log.event", maximum_chars=40)
        message = _validate_text(message, "request_log.message", maximum_chars=300)
        clean.append(
            {
                "request_id": request_id,
                "signature": signature,
                "revision": revision,
                "event": event,
                "message": message,
            }
        )
    return tuple(clean)


@dataclass(frozen=True)
class MutationResult:
    document: SemanticDocument
    event: str
    message: str
    replayed: bool = False
    original_revision: Optional[int] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: Any) -> bytes:
    try:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise SemanticStorageError("Daten sind nicht strikt JSON-serialisierbar.") from error
    # Das abschließende Newline gehört zur Datei und damit zum harten Limit.
    if len(serialized) + 1 > MAXIMUM_DOCUMENT_BYTES:
        raise SemanticStorageError("Semantische Karte überschreitet das Größenlimit.")
    return serialized + b"\n"


def command_signature(command: SemanticCommand) -> str:
    payload: dict[str, Any] = {
        "command": command.command,
        "map_fingerprint": command.map_fingerprint,
        "base_revision": command.base_revision,
        "room": command.room,
        "room_id": command.room_id,
        "map_ref_selector": command.map_ref_selector,
    }
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


class RequestSignatureCache:
    """Kleiner, byte-begrenzter Laufzeitcache ohne alte Statusantworten.

    Persistente Idempotenz von Schreibkommandos liegt im ``request_log`` des
    Dokuments. Dieser Cache erkennt zusätzlich die Wiederverwendung einer ID
    für ein anderes Kommando innerhalb eines Node-Laufs. Er hält absichtlich
    nur ID und Signatur: Ein Replay wird erneut gegen den aktuellen
    Karten-/Stale-Zustand ausgeführt und erzeugt immer einen frischen Snapshot.
    """

    def __init__(self, *, max_entries: int, max_bytes: int) -> None:
        for value, name in (
            (max_entries, "max_entries"),
            (max_bytes, "max_bytes"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SemanticValidationError(f"{name} muss eine positive Ganzzahl sein.")
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: OrderedDict[str, tuple[str, int]] = OrderedDict()
        self._bytes_used = 0

    @staticmethod
    def _entry_charge(request_id: str, signature: str) -> int:
        return (
            _REQUEST_CACHE_ENTRY_OVERHEAD_BYTES
            + len(request_id.encode("utf-8"))
            + len(signature.encode("ascii"))
        )

    @property
    def bytes_used(self) -> int:
        return self._bytes_used

    def __len__(self) -> int:
        return len(self._entries)

    def check(self, request_id: Optional[str], signature: str) -> bool:
        """Meldet exaktes Replay; widersprüchliche ID bleibt fail-closed."""

        if request_id is None:
            return False
        existing = self._entries.get(request_id)
        if existing is None:
            return False
        stored_signature, _ = existing
        if stored_signature != signature:
            raise RequestIDConflict(
                "request_id wurde bereits für ein anderes Kommando verwendet."
            )
        self._entries.move_to_end(request_id)
        return True

    def remember(self, request_id: Optional[str], signature: str) -> None:
        if request_id is None:
            return
        charge = self._entry_charge(request_id, signature)
        if charge > self.max_bytes:
            # Bei den streng validierten IDs/Signaturen praktisch unerreichbar,
            # aber niemals für einen einzelnen Eintrag das Bytebudget reißen.
            return
        existing = self._entries.get(request_id)
        if existing is not None:
            stored_signature, stored_charge = existing
            if stored_signature != signature:
                raise RequestIDConflict(
                    "request_id wurde bereits für ein anderes Kommando verwendet."
                )
            self._bytes_used -= stored_charge
        self._entries[request_id] = (signature, charge)
        self._bytes_used += charge
        self._entries.move_to_end(request_id)
        while (
            len(self._entries) > self.max_entries
            or self._bytes_used > self.max_bytes
        ):
            _, (_, removed_charge) = self._entries.popitem(last=False)
            self._bytes_used -= removed_charge


class SemanticMapRepository:
    """Atomare, revisionsbasierte Ablage pro metrischem Fingerabdruck."""

    def __init__(
        self,
        root: Path,
        *,
        max_revisions_per_map: int = DEFAULT_MAXIMUM_REVISIONS_PER_MAP,
        max_storage_bytes: int = DEFAULT_MAXIMUM_STORAGE_BYTES,
        min_free_space_bytes: int = DEFAULT_MINIMUM_FREE_SPACE_BYTES,
    ) -> None:
        self.root = Path(root)
        if not self.root.is_absolute():
            raise SemanticStorageError("Speicherwurzel muss absolut sein.")
        self.max_revisions_per_map = self._positive_limit(
            max_revisions_per_map, "max_revisions_per_map"
        )
        self.max_storage_bytes = self._positive_limit(
            max_storage_bytes, "max_storage_bytes"
        )
        self.min_free_space_bytes = self._positive_limit(
            min_free_space_bytes, "min_free_space_bytes"
        )
        self._ensure_directory(self.root)
        self._lock_path = self.root / ".repository.lock"
        self._ensure_lock_file()

    @staticmethod
    def _positive_limit(value: Any, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SemanticStorageError(f"{name} muss eine positive Ganzzahl sein.")
        return value

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            info = path.lstat()
        except OSError as error:
            raise SemanticStorageError(
                f"Speicherverzeichnis kann nicht angelegt werden: {error}"
            ) from error
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise SemanticStorageError("Speicherverzeichnis darf kein Symlink sein.")

    def _ensure_lock_file(self) -> None:
        try:
            descriptor = os.open(
                self._lock_path,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            os.close(descriptor)
            info = self._lock_path.lstat()
        except OSError as error:
            raise SemanticStorageError(f"Repository-Lock nicht nutzbar: {error}") from error
        if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise SemanticStorageError("Repository-Lock muss eine reguläre Datei sein.")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        try:
            descriptor = os.open(
                self._lock_path,
                os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        except OSError as error:
            raise SemanticStorageError(f"Repository-Lock fehlgeschlagen: {error}") from error
        finally:
            if "descriptor" in locals():
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)

    def _map_directory(self, fingerprint: str, *, create: bool) -> Path:
        if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise SemanticStorageError("Ungültiger Kartenfingerabdruck.")
        path = self.root / fingerprint
        if create:
            self._ensure_directory(path)
            # Macht den neuen Fingerprint-Verzeichniseintrag stromausfallsicher.
            self._sync_directory(self.root)
            self._ensure_directory(path / "revisions")
            self._sync_directory(path)
        elif path.exists():
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise SemanticStorageError("Kartenablage darf kein Symlink sein.")
        return path

    @staticmethod
    def _read_json_file(path: Path) -> dict[str, Any]:
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise SemanticStorageError("Semantikdatei ist keine reguläre Datei.")
            if info.st_size <= 0 or info.st_size > MAXIMUM_DOCUMENT_BYTES:
                raise SemanticStorageError("Semantikdatei hat eine ungültige Größe.")
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                chunks: list[bytes] = []
                remaining = MAXIMUM_DOCUMENT_BYTES + 1
                while remaining > 0:
                    chunk = os.read(descriptor, remaining)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                data = b"".join(chunks)
            finally:
                os.close(descriptor)
            if len(data) > MAXIMUM_DOCUMENT_BYTES:
                raise SemanticStorageError("Semantikdatei überschreitet das Größenlimit.")
            payload = json.loads(data.decode("utf-8"))
        except SemanticStorageError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
            raise SemanticStorageError(f"Semantikdatei ist beschädigt: {error}") from error
        if not isinstance(payload, dict):
            raise SemanticStorageError("Semantikdatei enthält kein JSON-Objekt.")
        return payload

    def _newest_revision_path(self, map_directory: Path) -> Optional[Path]:
        revisions = map_directory / "revisions"
        try:
            revision_info = revisions.lstat()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise SemanticStorageError(
                f"Revisionsverzeichnis kann nicht gelesen werden: {error}"
            ) from error
        if not stat.S_ISDIR(revision_info.st_mode) or stat.S_ISLNK(
            revision_info.st_mode
        ):
            raise SemanticStorageError("Revisionsverzeichnis darf kein Symlink sein.")

        newest_candidate: Optional[Path] = None
        revision_count = 0
        try:
            for entry in revisions.iterdir():
                if not re.fullmatch(r"[0-9]{20}\.json", entry.name):
                    continue
                if entry.is_symlink():
                    continue
                revision_count += 1
                if revision_count > self.max_revisions_per_map:
                    raise SemanticStorageError(
                        "Revisionsablage überschreitet das konfigurierte Limit."
                    )
                if newest_candidate is None or entry.name > newest_candidate.name:
                    newest_candidate = entry
        except OSError as error:
            raise SemanticStorageError(
                f"Revisionsverzeichnis kann nicht aufgelistet werden: {error}"
            ) from error
        return newest_candidate

    def _load_revision_document(
        self, revision_path: Path, fingerprint: str
    ) -> SemanticDocument:
        try:
            document = SemanticDocument.from_dict(
                self._read_json_file(revision_path)
            )
        except SemanticValidationError as error:
            raise SemanticStorageError(
                f"Revisionsdatei ist semantisch ungültig: {error}"
            ) from error
        expected_name = f"{document.revision:020d}.json"
        if revision_path.name != expected_name:
            raise SemanticStorageError(
                "Revisionsdateiname widerspricht ihrem Revisionsinhalt."
            )
        if document.map_ref.fingerprint != fingerprint:
            raise SemanticStorageError(
                "Revisionsdatei gehört zu einem anderen Fingerabdruck."
            )
        return document

    @staticmethod
    def _validate_orphan_successor(
        current: SemanticDocument, successor: SemanticDocument
    ) -> None:
        """Akzeptiert ausschließlich den vom Repository erzeugbaren Folgezustand."""

        if successor.revision != current.revision + 1:
            raise SemanticStorageError(
                "Neuere Revisionsdatei besitzt keine lückenlose Folgerevision."
            )
        if successor.map_ref != current.map_ref:
            raise SemanticStorageError(
                "Neuere Revisionsdatei widerspricht der gebundenen Kartenreferenz."
            )
        current_log = list(current.request_log)
        expected_prefix = (
            current_log
            if len(current_log) < MAXIMUM_REQUEST_LOG_ENTRIES
            else current_log[1:]
        )
        successor_log = list(successor.request_log)
        if (
            len(successor_log) != len(expected_prefix) + 1
            or successor_log[:-1] != expected_prefix
            or successor_log[-1]["revision"] != successor.revision
        ):
            raise SemanticStorageError(
                "Neuere Revisionsdatei ist kein gültiger request-log-Nachfolger."
            )

    def _load_unlocked(self, fingerprint: str) -> Optional[SemanticDocument]:
        map_directory = self._map_directory(fingerprint, create=False)
        current = map_directory / "current.json"
        try:
            current.lstat()
            current_exists = True
        except FileNotFoundError:
            current_exists = False
        except OSError as error:
            raise SemanticStorageError(
                f"current.json kann nicht geprüft werden: {error}"
            ) from error

        newest_candidate = self._newest_revision_path(map_directory)
        if not current_exists:
            # Ein Stromausfall kann nach dem fsync der unveränderlichen
            # Revision, aber vor dem atomaren current.json-Rename liegen. Eine
            # vollständig validierte jüngste Revision ist dann der ehrliche
            # Commit und wird unter dem Repository-Lock wieder als current
            # sichtbar gemacht. Fremde Namen/Symlinks werden ignoriert.
            if newest_candidate is None:
                return None
            recovered = self._load_revision_document(newest_candidate, fingerprint)
            recovered_data = _json_bytes(recovered.as_dict())
            self._require_write_budget(len(recovered_data))
            self._atomic_replace_file(current, recovered_data)
            self._sync_directory(map_directory)
            return recovered
        try:
            document = SemanticDocument.from_dict(self._read_json_file(current))
        except SemanticValidationError as error:
            raise SemanticStorageError(f"Semantikdatei ist semantisch ungültig: {error}") from error
        if document.map_ref.fingerprint != fingerprint:
            raise SemanticStorageError(
                "Semantikdatei liegt im Verzeichnis eines anderen Fingerabdrucks."
            )
        if newest_candidate is None:
            raise SemanticStorageError(
                "current.json besitzt keine unveränderliche Revisionsdatei."
            )

        current_revision_path = (
            map_directory / "revisions" / f"{document.revision:020d}.json"
        )
        archived_current = self._load_revision_document(
            current_revision_path, fingerprint
        )
        if _json_bytes(archived_current.as_dict()) != _json_bytes(document.as_dict()):
            raise SemanticStorageError(
                "current.json widerspricht seiner unveränderlichen Revision."
            )

        newest_revision = int(newest_candidate.stem)
        if newest_revision == document.revision:
            return document
        if newest_revision <= document.revision:
            raise SemanticStorageError(
                "Revisionsablage liegt hinter current.json zurück."
            )

        # Vollständig publizierte Revision + fehlgeschlagenes current-Rename:
        # Der alte Zeiger existiert noch, dennoch ist genau der lückenlose,
        # request-log-konsistente Nachfolger bereits der ehrliche Commit.
        successor = self._load_revision_document(newest_candidate, fingerprint)
        self._validate_orphan_successor(document, successor)
        successor_data = _json_bytes(successor.as_dict())
        self._require_write_budget(len(successor_data))
        self._atomic_replace_file(current, successor_data)
        self._sync_directory(map_directory)
        return successor

    def load(self, fingerprint: str) -> Optional[SemanticDocument]:
        with self._lock():
            return self._load_unlocked(fingerprint)

    def bind_map(self, map_ref: MapReference) -> SemanticDocument:
        """Initialisiert Revision 0 oder lädt die bestehende Fingerprint-Ablage.

        Identische Karteninhalte können vom metrischen Manager mehrfach unter
        neuer Version gespeichert werden. Der erste bestätigte ``map_ref``
        bleibt deshalb die kanonische Referenz der Overlay-Ablage; spätere
        Versionen mit exakt gleicher Geometrie und gleichem Fingerprint dürfen
        sie erneut aktivieren.
        """

        if not isinstance(map_ref, MapReference):
            raise SemanticStorageError("bind_map benötigt eine gültige MapReference.")
        with self._lock():
            existing = self._load_unlocked(map_ref.fingerprint)
            if existing is not None:
                if not self._same_geometry(existing.map_ref, map_ref):
                    raise MapMismatchError(
                        "Gespeicherte Semantik-Geometrie widerspricht der aktuellen Karte."
                    )
                return existing
            document = SemanticDocument(
                map_ref=map_ref,
                revision=0,
                rooms=(),
                updated_at=_utc_now(),
                request_log=(),
            )
            self._commit_unlocked(document)
            return document

    @staticmethod
    def _same_geometry(left: MapReference, right: MapReference) -> bool:
        return (
            left.fingerprint == right.fingerprint
            and left.frame_id == right.frame_id
            and left.width == right.width
            and left.height == right.height
            and left.resolution == right.resolution
            and left.origin == right.origin
        )

    def upsert_room(
        self,
        *,
        map_fingerprint: str,
        base_revision: int,
        room_payload: dict[str, Any],
        request_id: str,
        signature: str,
    ) -> MutationResult:
        with self._lock():
            current = self._require_document_unlocked(map_fingerprint)
            replay = self._request_replay(current, request_id, signature)
            if replay is not None:
                return replay
            self._require_revision(current, base_revision)
            incoming_point_count = _preflight_room_polygon_points(room_payload)
            raw_room_id = room_payload.get("id") if isinstance(room_payload, dict) else None
            replaced_point_count = next(
                (
                    len(existing.polygon)
                    for existing in current.rooms
                    if existing.id == raw_room_id
                ),
                0,
            )
            projected_point_count = (
                sum(len(existing.polygon) for existing in current.rooms)
                - replaced_point_count
                + incoming_point_count
            )
            if projected_point_count > MAXIMUM_TOTAL_POLYGON_POINTS:
                raise SemanticValidationError(
                    "Mutation überschreitet das Gesamtlimit von "
                    f"{MAXIMUM_TOTAL_POLYGON_POINTS} Polygonpunkten."
                )
            room = Room.from_dict(room_payload, map_ref=current.map_ref)
            rooms = {existing.id: existing for existing in current.rooms}
            for existing in current.rooms:
                if existing.id != room.id and existing.name.casefold() == room.name.casefold():
                    raise SemanticValidationError(
                        f"Raumname '{room.name}' ist bereits vergeben."
                    )
            event = "room_updated" if room.id in rooms else "room_created"
            rooms[room.id] = room
            if len(rooms) > MAXIMUM_ROOMS:
                raise SemanticValidationError(
                    f"Es sind höchstens {MAXIMUM_ROOMS} Räume erlaubt."
                )
            if sum(len(item.polygon) for item in rooms.values()) > MAXIMUM_TOTAL_POLYGON_POINTS:
                raise SemanticValidationError(
                    "Semantische Karte überschreitet das Gesamtlimit von "
                    f"{MAXIMUM_TOTAL_POLYGON_POINTS} Polygonpunkten."
                )
            message = (
                f"Raum '{room.name}' aktualisiert."
                if event == "room_updated"
                else f"Raum '{room.name}' angelegt."
            )
            document = self._mutated_document(
                current,
                rooms=tuple(sorted(rooms.values(), key=lambda item: item.id)),
                request_id=request_id,
                signature=signature,
                event=event,
                message=message,
            )
            self._commit_unlocked(document)
            return MutationResult(document=document, event=event, message=message)

    def delete_room(
        self,
        *,
        map_fingerprint: str,
        base_revision: int,
        room_id: str,
        request_id: str,
        signature: str,
    ) -> MutationResult:
        with self._lock():
            current = self._require_document_unlocked(map_fingerprint)
            replay = self._request_replay(current, request_id, signature)
            if replay is not None:
                return replay
            self._require_revision(current, base_revision)
            rooms = {room.id: room for room in current.rooms}
            removed = rooms.pop(room_id, None)
            if removed is None:
                raise SemanticValidationError(f"Raum-ID '{room_id}' existiert nicht.")
            message = f"Raum '{removed.name}' gelöscht."
            document = self._mutated_document(
                current,
                rooms=tuple(sorted(rooms.values(), key=lambda item: item.id)),
                request_id=request_id,
                signature=signature,
                event="room_deleted",
                message=message,
            )
            self._commit_unlocked(document)
            return MutationResult(document=document, event="room_deleted", message=message)

    def _require_document_unlocked(self, fingerprint: str) -> SemanticDocument:
        current = self._load_unlocked(fingerprint)
        if current is None:
            raise MapMismatchError(
                "Für diesen Kartenfingerabdruck ist keine semantische Karte gebunden."
            )
        return current

    @staticmethod
    def _require_revision(document: SemanticDocument, base_revision: int) -> None:
        if document.revision != base_revision:
            raise RevisionConflictError(
                f"Revision veraltet: erwartet {document.revision}, erhalten {base_revision}."
            )

    @staticmethod
    def _request_replay(
        document: SemanticDocument,
        request_id: str,
        signature: str,
    ) -> Optional[MutationResult]:
        for entry in document.request_log:
            if entry["request_id"] != request_id:
                continue
            if entry["signature"] != signature:
                raise RequestIDConflict(
                    "request_id wurde bereits für ein anderes Kommando verwendet."
                )
            return MutationResult(
                document=document,
                event=entry["event"],
                message=entry["message"],
                replayed=True,
                original_revision=entry["revision"],
            )
        return None

    @staticmethod
    def _mutated_document(
        current: SemanticDocument,
        *,
        rooms: tuple[Room, ...],
        request_id: str,
        signature: str,
        event: str,
        message: str,
    ) -> SemanticDocument:
        revision = current.revision + 1
        log = list(current.request_log)
        log.append(
            {
                "request_id": request_id,
                "signature": signature,
                "revision": revision,
                "event": event,
                "message": message,
            }
        )
        log = log[-MAXIMUM_REQUEST_LOG_ENTRIES:]
        return SemanticDocument(
            map_ref=current.map_ref,
            revision=revision,
            rooms=rooms,
            updated_at=_utc_now(),
            request_log=tuple(log),
        )

    def _commit_unlocked(self, document: SemanticDocument) -> None:
        # Rundlauf durch den Validator verhindert, dass intern erzeugte Daten
        # einen anderen Vertrag besitzen als später geladene Dateien.
        validated = SemanticDocument.from_dict(document.as_dict())
        data = _json_bytes(validated.as_dict())
        map_directory = self._map_directory(document.map_ref.fingerprint, create=True)
        revisions = map_directory / "revisions"
        revision_path = revisions / f"{document.revision:020d}.json"
        current_path = map_directory / "current.json"
        try:
            revision_path.lstat()
            revision_exists = True
        except FileNotFoundError:
            revision_exists = False
        except OSError as error:
            raise SemanticStorageError(
                f"Revisionsdatei kann nicht geprüft werden: {error}"
            ) from error
        if revision_exists:
            existing = self._read_json_file(revision_path)
            if _json_bytes(existing) != data:
                raise SemanticStorageError(
                    "Revisionsdatei existiert bereits mit anderem Inhalt."
                )
        else:
            if document.revision >= self.max_revisions_per_map:
                raise SemanticStorageError(
                    "Maximale Zahl unveränderlicher Revisionen für diese Karte "
                    f"erreicht ({self.max_revisions_per_map})."
                )
        # Bei einer neuen Revision existieren kurzzeitig Revisionstemp und
        # current.json-Temp parallel. Bei einer vorhandenen Revision nur das
        # neue current.json-Temp. Die konservative Reserve verhindert, dass
        # der atomare Commit selbst die Platte bis auf 0 Bytes füllt.
        required_peak_bytes = len(data) * (2 if not revision_exists else 1)
        self._require_write_budget(required_peak_bytes)
        if not revision_exists:
            self._publish_immutable_file(revision_path, data)
        self._atomic_replace_file(current_path, data)
        self._sync_directory(map_directory)

    def _require_write_budget(self, required_peak_bytes: int) -> None:
        if required_peak_bytes <= 0:
            raise SemanticStorageError("Ungültige Speicherreserve für Commit.")
        used_bytes = self._repository_size_bytes()
        if (
            used_bytes > self.max_storage_bytes
            or required_peak_bytes > self.max_storage_bytes - used_bytes
        ):
            raise SemanticStorageError(
                "Semantische Kartenablage würde das konfigurierte Größenlimit "
                f"von {self.max_storage_bytes} Bytes überschreiten."
            )
        try:
            free_bytes = shutil.disk_usage(self.root).free
        except OSError as error:
            raise SemanticStorageError(
                f"Freier Speicher kann nicht bestimmt werden: {error}"
            ) from error
        if free_bytes - required_peak_bytes < self.min_free_space_bytes:
            raise SemanticStorageError(
                "Commit verweigert: Die konfigurierte Freispeicherreserve von "
                f"{self.min_free_space_bytes} Bytes würde unterschritten."
            )

    def _repository_size_bytes(self) -> int:
        """Logische Dateigröße ohne Symlink-Folgen und Hardlink-Doppelzählung."""

        total = 0
        seen_inodes: set[tuple[int, int]] = set()
        pending = [self.root]
        scanned_entries = 0
        while pending:
            directory = pending.pop()
            try:
                entries = os.scandir(directory)
            except OSError as error:
                raise SemanticStorageError(
                    f"Speicherbelegung kann nicht geprüft werden: {error}"
                ) from error
            try:
                with entries:
                    for entry in entries:
                        scanned_entries += 1
                        if scanned_entries > MAXIMUM_STORAGE_SCAN_ENTRIES:
                            raise SemanticStorageError(
                                "Semantische Kartenablage enthält zu viele Einträge."
                            )
                        try:
                            info = entry.stat(follow_symlinks=False)
                        except OSError as error:
                            raise SemanticStorageError(
                                f"Speichereintrag kann nicht geprüft werden: {error}"
                            ) from error
                        if stat.S_ISLNK(info.st_mode):
                            raise SemanticStorageError(
                                "Semantische Kartenablage enthält einen unerlaubten "
                                "Symlink."
                            )
                        if stat.S_ISDIR(info.st_mode):
                            pending.append(Path(entry.path))
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            raise SemanticStorageError(
                                "Semantische Kartenablage enthält einen unerlaubten "
                                "Dateityp."
                            )
                        inode = (info.st_dev, info.st_ino)
                        if inode in seen_inodes:
                            continue
                        seen_inodes.add(inode)
                        total += info.st_size
                        if total > self.max_storage_bytes:
                            return total
            except OSError as error:
                raise SemanticStorageError(
                    f"Speicherbelegung kann nicht geprüft werden: {error}"
                ) from error
        return total

    @staticmethod
    def _write_new_file(path: Path, data: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(path, flags, 0o600)
            try:
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("write lieferte 0 Bytes")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise SemanticStorageError(f"Revisionsdatei konnte nicht geschrieben werden: {error}") from error

    @staticmethod
    def _publish_immutable_file(path: Path, data: bytes) -> None:
        """Publiziert vollständige Daten atomar, ohne ein Ziel zu überschreiben."""

        temporary = path.parent / f".tmp-revision-{uuid.uuid4().hex}"
        try:
            SemanticMapRepository._write_new_file(temporary, data)
            try:
                # Der Hardlink wird als einzelner Verzeichniseintrag atomar
                # angelegt und schlägt bei vorhandenem Ziel mit EEXIST fehl.
                # Sein Inode wurde als Tempdatei bereits vollständig
                # geschrieben und fsync't.
                os.link(temporary, path, follow_symlinks=False)
            except FileExistsError as error:
                raise SemanticStorageError(
                    "Revisionsdatei wurde parallel angelegt; Commit abgebrochen."
                ) from error
            except OSError as error:
                raise SemanticStorageError(
                    f"Revisionsdatei konnte nicht atomar veröffentlicht werden: {error}"
                ) from error
            temporary.unlink()
            SemanticMapRepository._sync_directory(path.parent)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    @staticmethod
    def _atomic_replace_file(path: Path, data: bytes) -> None:
        temporary = path.parent / f".tmp-{uuid.uuid4().hex}"
        try:
            SemanticMapRepository._write_new_file(temporary, data)
            os.replace(temporary, path)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    @staticmethod
    def _sync_directory(path: Path) -> None:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(path, flags)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as error:
            raise SemanticStorageError(f"Verzeichnis konnte nicht synchronisiert werden: {error}") from error


def activate_map_observation(
    repository: SemanticMapRepository,
    observation: MapManagerObservation,
) -> Optional[SemanticDocument]:
    """Löst die Erst-/Neustartbindung vollständig ROS-unabhängig auf."""

    if not isinstance(repository, SemanticMapRepository):
        raise SemanticStorageError("repository besitzt den falschen Typ.")
    if not isinstance(observation, MapManagerObservation):
        raise SemanticValidationError("observation besitzt den falschen Typ.")
    existing = repository.load(observation.fingerprint)
    if existing is not None:
        summary = observation.map_summary
        live_reference = MapReference.from_dict(
            {
                "name": existing.map_ref.name,
                "version": existing.map_ref.version,
                "fingerprint": observation.fingerprint,
                "frame_id": summary["frame_id"],
                "width": summary["width"],
                "height": summary["height"],
                "resolution": summary["resolution"],
                "origin": summary["origin"],
            }
        )
        return repository.bind_map(live_reference)
    if not observation.confirmed_references:
        return None
    return repository.bind_map(observation.confirmed_references[0])


def public_document(document: Optional[SemanticDocument]) -> Optional[dict[str, Any]]:
    if document is None:
        return None
    return document.as_dict(include_request_log=False)


def json_message(payload: dict[str, Any]) -> str:
    """Statusserialisierung ohne NaN/Infinity und ohne unnötige Leerzeichen."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
