"""Read-only contract for resolving a room into a safe semantic map goal.

This module intentionally has no ROS dependency.  The mission manager only
caches the semantic map manager's transient-local status and validates it
again here.  It does not issue a navigation command.
"""

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Dict, Optional, Sequence, Tuple


# Der Backend-Vertrag erlaubt persistierte Semantikdokumente bis 4 MiB. Der
# Status enthaelt dasselbe oeffentliche Raumdokument plus einen kleinen
# Diagnose-Umschlag; 5 MiB halten beide Seiten kompatibel und bleiben dennoch
# strikt begrenzt.
MAXIMUM_STATUS_BYTES = 5 * 1024 * 1024
MAXIMUM_ROOMS = 256
MAXIMUM_POLYGON_POINTS = 64
MAXIMUM_TOTAL_POLYGON_POINTS = 4096
MAXIMUM_COORDINATE_ABS = 100_000.0
MINIMUM_POLYGON_AREA = 1e-6


@dataclass(frozen=True)
class SemanticRoom:
    room_id: str
    name: str
    polygon: Tuple[Tuple[float, float], ...]
    navigation_goal: Optional[Tuple[float, float, float]]


@dataclass(frozen=True)
class SemanticMapSnapshot:
    fingerprint: str
    frame_id: str
    revision: int
    rooms: Tuple[SemanticRoom, ...]


@dataclass(frozen=True)
class ResolvedRoomGoal:
    room_id: str
    room_name: str
    map_fingerprint: str
    map_revision: int
    frame_id: str
    x: float
    y: float
    yaw: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            'room_id': self.room_id,
            'room_name': self.room_name,
            'map_fingerprint': self.map_fingerprint,
            'map_revision': self.map_revision,
            'frame_id': self.frame_id,
            'pose': {'x': self.x, 'y': self.y, 'yaw': self.yaw},
        }


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _finite_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _finite_coordinate(value: Any) -> Optional[float]:
    number = _finite_number(value)
    if number is None or abs(number) > MAXIMUM_COORDINATE_ABS:
        return None
    return number


def _polygon_point(value: Any) -> Optional[Tuple[float, float]]:
    if isinstance(value, dict):
        x = _finite_coordinate(value.get('x'))
        y = _finite_coordinate(value.get('y'))
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        x = _finite_coordinate(value[0])
        y = _finite_coordinate(value[1])
    else:
        return None
    if x is None or y is None:
        return None
    return x, y


def _signed_double_area(polygon: Sequence[Tuple[float, float]]) -> float:
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(
            polygon,
            tuple(polygon[1:]) + tuple(polygon[:1]),
        )
    )


def _cross(
        a: Tuple[float, float],
        b: Tuple[float, float],
        c: Tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_segment(
        point: Tuple[float, float],
        start: Tuple[float, float],
        end: Tuple[float, float],
        tolerance: float = 1e-9) -> bool:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > tolerance:
        return False
    dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
    return dot <= tolerance


def _segments_intersect(
        a: Tuple[float, float],
        b: Tuple[float, float],
        c: Tuple[float, float],
        d: Tuple[float, float],
        tolerance: float = 1e-9) -> bool:
    o1 = _cross(a, b, c)
    o2 = _cross(a, b, d)
    o3 = _cross(c, d, a)
    o4 = _cross(c, d, b)
    if (
            ((o1 > tolerance and o2 < -tolerance)
             or (o1 < -tolerance and o2 > tolerance))
            and ((o3 > tolerance and o4 < -tolerance)
                 or (o3 < -tolerance and o4 > tolerance))):
        return True
    return (
        (abs(o1) <= tolerance and _point_on_segment(c, a, b))
        or (abs(o2) <= tolerance and _point_on_segment(d, a, b))
        or (abs(o3) <= tolerance and _point_on_segment(a, c, d))
        or (abs(o4) <= tolerance and _point_on_segment(b, c, d))
    )


def _simple_polygon_error(polygon: Sequence[Tuple[float, float]]) -> Optional[str]:
    if len(polygon) < 3 or len(polygon) > MAXIMUM_POLYGON_POINTS:
        return f'braucht 3 bis {MAXIMUM_POLYGON_POINTS} Polygonpunkte'
    if len(set(polygon)) != len(polygon):
        return 'enthaelt doppelte Polygonpunkte'
    for index, point in enumerate(polygon):
        following = polygon[(index + 1) % len(polygon)]
        if math.hypot(point[0] - following[0], point[1] - following[1]) <= 1e-9:
            return 'enthaelt aufeinanderfolgende gleiche Polygonpunkte'
    if abs(_signed_double_area(polygon)) < 2.0 * MINIMUM_POLYGON_AREA:
        return 'hat ein Polygon ohne nutzbare Flaeche'

    edge_count = len(polygon)
    for first in range(edge_count):
        a = polygon[first]
        b = polygon[(first + 1) % edge_count]
        for second in range(first + 1, edge_count):
            if ((second + 1) % edge_count == first
                    or (first + 1) % edge_count == second):
                continue
            c = polygon[second]
            d = polygon[(second + 1) % edge_count]
            if _segments_intersect(a, b, c, d):
                return 'hat ein selbstschneidendes oder sich beruehrendes Polygon'
    return None


def point_in_polygon(
        point: Tuple[float, float],
        polygon: Sequence[Tuple[float, float]]) -> bool:
    """Return True for points inside or on the boundary of a polygon."""
    inside = False
    px, py = point
    for start, end in zip(
            polygon, tuple(polygon[1:]) + tuple(polygon[:1])):
        if _point_on_segment(point, start, end):
            return True
        x1, y1 = start
        x2, y2 = end
        if (y1 > py) != (y2 > py):
            crossing_x = (x2 - x1) * (py - y1) / (y2 - y1) + x1
            if px < crossing_x:
                inside = not inside
    return inside


def point_strictly_inside_polygon(
        point: Tuple[float, float],
        polygon: Sequence[Tuple[float, float]]) -> bool:
    """Return True only inside, never on a wall or polygon boundary."""
    for start, end in zip(
            polygon, tuple(polygon[1:]) + tuple(polygon[:1])):
        if _point_on_segment(point, start, end):
            return False
    return point_in_polygon(point, polygon)


def decode_semantic_map_status(
        data: str,
        expected_frame_id: str = 'map',
        expected_fingerprint: str = '',
) -> Tuple[Optional[SemanticMapSnapshot], Optional[str]]:
    """Validate the JSON status published by ``semantic_map_manager``.

    The whole snapshot is rejected on a malformed room or duplicate room
    identity.  A missing ``navigation_goal`` is allowed while a room is still
    being edited, but that room cannot be resolved for a mission.
    """
    if not isinstance(data, str):
        return None, 'Semantik-Status muss Text sein'
    try:
        encoded_size = len(data.encode('utf-8'))
    except UnicodeError:
        return None, 'Semantik-Status enthaelt ungueltiges Unicode'
    if encoded_size > MAXIMUM_STATUS_BYTES:
        return None, f'Semantik-Status ist groesser als {MAXIMUM_STATUS_BYTES} Bytes'
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        return None, f'Ungueltiger Semantik-Status: {exc}'
    if not isinstance(payload, dict):
        return None, 'Semantik-Status muss ein JSON-Objekt sein'
    if payload.get('schema_version') != 1:
        return None, 'Semantik-Status hat keine unterstuetzte schema_version'
    if payload.get('ok') is not True:
        return None, 'Semantik-Status ist nicht freigegeben (ok != true)'

    semantic_map = payload.get('semantic_map')
    if not isinstance(semantic_map, dict):
        return None, 'semantic_map fehlt oder ist kein Objekt'
    if semantic_map.get('editable') is not True:
        return None, 'Semantik-Status ist nicht editierbar/freigegeben'
    map_ref = semantic_map.get('map_ref')
    if not isinstance(map_ref, dict):
        return None, 'semantic_map.map_ref fehlt oder ist kein Objekt'

    fingerprint = _non_empty_string(map_ref.get('fingerprint'))
    if fingerprint is None:
        return None, 'Karten-Fingerprint fehlt'
    if re.fullmatch(r'[0-9a-f]{64}', fingerprint) is None:
        return None, 'Karten-Fingerprint muss aus 64 kleinen Hexzeichen bestehen'
    expected_fingerprint = expected_fingerprint.strip()
    if expected_fingerprint and fingerprint != expected_fingerprint:
        return None, 'Karten-Fingerprint stimmt nicht mit der erwarteten Karte ueberein'

    frame_id = _non_empty_string(map_ref.get('frame_id'))
    if frame_id is None:
        return None, 'Karten-Frame fehlt'
    expected_frame_id = expected_frame_id.strip()
    if expected_frame_id and frame_id != expected_frame_id:
        return None, (
            f'Unerwarteter Karten-Frame {frame_id!r}; erwartet {expected_frame_id!r}')

    revision = semantic_map.get('revision')
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        return None, 'Semantik-Revision muss eine nichtnegative Ganzzahl sein'

    room_payloads = semantic_map.get('rooms')
    if not isinstance(room_payloads, list) or len(room_payloads) > MAXIMUM_ROOMS:
        return None, f'semantic_map.rooms muss eine Liste mit hoechstens {MAXIMUM_ROOMS} Raeumen sein'

    rooms = []
    known_ids = set()
    known_names = set()
    total_polygon_points = 0
    for index, room_payload in enumerate(room_payloads):
        if not isinstance(room_payload, dict):
            return None, f'Raum {index} ist kein Objekt'
        room_id = _non_empty_string(room_payload.get('id'))
        name = _non_empty_string(room_payload.get('name'))
        if room_id is None or name is None:
            return None, f'Raum {index} braucht nichtleere Felder id und name'
        if re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', room_id) is None:
            return None, f'Raum {index} hat eine ungueltige ID'
        if len(name) > 80 or any(ord(character) < 32 for character in name):
            return None, f'Raum {index} hat einen ungueltigen Namen'
        folded_id = room_id.casefold()
        folded_name = name.casefold()
        if folded_id in known_ids:
            return None, f'Doppelte Raum-ID: {room_id}'
        if folded_name in known_names:
            return None, f'Doppelter Raumname: {name}'
        known_ids.add(folded_id)
        known_names.add(folded_name)

        polygon_payload = room_payload.get('polygon')
        if not isinstance(polygon_payload, list):
            return None, f'Raum {name!r} braucht eine Polygonliste'
        total_polygon_points += len(polygon_payload)
        if total_polygon_points > MAXIMUM_TOTAL_POLYGON_POINTS:
            return None, (
                'Semantikkarte enthaelt mehr als '
                f'{MAXIMUM_TOTAL_POLYGON_POINTS} Polygonpunkte insgesamt')
        polygon = []
        for point_payload in polygon_payload:
            point = _polygon_point(point_payload)
            if point is None:
                return None, f'Raum {name!r} enthaelt einen ungueltigen Polygonpunkt'
            polygon.append(point)
        polygon_error = _simple_polygon_error(polygon)
        if polygon_error is not None:
            return None, f'Raum {name!r} {polygon_error}'

        goal_payload = room_payload.get('navigation_goal')
        navigation_goal = None
        if goal_payload is not None:
            if not isinstance(goal_payload, dict):
                return None, f'Raum {name!r} hat kein gueltiges navigation_goal-Objekt'
            x = _finite_coordinate(goal_payload.get('x'))
            y = _finite_coordinate(goal_payload.get('y'))
            yaw = _finite_number(goal_payload.get('yaw'))
            if x is None or y is None or yaw is None:
                return None, f'Raum {name!r} hat keine endliche Zielpose x/y/yaw'
            if yaw < -math.pi or yaw > math.pi:
                return None, f'Raum {name!r} hat einen yaw ausserhalb [-pi,+pi]'
            navigation_goal = (x, y, yaw)
            if not point_strictly_inside_polygon((x, y), polygon):
                return None, (
                    f'Navigationsziel von Raum {name!r} liegt nicht strikt '
                    'innerhalb des Polygons')

        rooms.append(SemanticRoom(
            room_id=room_id,
            name=name,
            polygon=tuple(polygon),
            navigation_goal=navigation_goal,
        ))

    return SemanticMapSnapshot(
        fingerprint=fingerprint,
        frame_id=frame_id,
        revision=revision,
        rooms=tuple(rooms),
    ), None


def resolve_room_goal(
        snapshot: SemanticMapSnapshot,
        room_name: Any = None,
        room_id: Any = None,
) -> Tuple[Optional[ResolvedRoomGoal], Optional[str]]:
    """Resolve an exact, unambiguous room reference in a valid snapshot."""
    name = _non_empty_string(room_name)
    identifier = _non_empty_string(room_id)
    if name is None and identifier is None:
        return None, 'Raumname oder Raum-ID fehlt'

    matches = []
    for room in snapshot.rooms:
        id_matches = identifier is None or room.room_id.casefold() == identifier.casefold()
        name_matches = name is None or room.name.casefold() == name.casefold()
        if id_matches and name_matches:
            matches.append(room)
    if not matches:
        supplied = identifier or name
        return None, f'Raum {supplied!r} ist in der aktiven semantischen Karte unbekannt'
    if len(matches) != 1:
        return None, 'Raumreferenz ist nicht eindeutig'

    room = matches[0]
    if room.navigation_goal is None:
        return None, f'Raum {room.name!r} hat noch kein Navigationsziel'
    x, y, yaw = room.navigation_goal
    return ResolvedRoomGoal(
        room_id=room.room_id,
        room_name=room.name,
        map_fingerprint=snapshot.fingerprint,
        map_revision=snapshot.revision,
        frame_id=snapshot.frame_id,
        x=x,
        y=y,
        yaw=yaw,
    ), None


def semantic_snapshot_is_fresh(
        received_monotonic: Any,
        now_monotonic: Any,
        stale_timeout_s: Any) -> bool:
    """Validate receipt freshness using a monotonic clock.

    A backward clock jump, missing timestamp, non-finite value or invalid
    timeout fails closed.  ROS time is deliberately not used here.
    """
    received = _finite_number(received_monotonic)
    now = _finite_number(now_monotonic)
    timeout = _finite_number(stale_timeout_s)
    if received is None or now is None or timeout is None or timeout <= 0.0:
        return False
    age = now - received
    return 0.0 <= age <= timeout
