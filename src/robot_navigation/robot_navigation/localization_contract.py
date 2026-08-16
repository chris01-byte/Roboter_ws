"""ROS-unabhaengiger Vertrag fuer eine belastbare Kartenlokalisierung."""

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Optional, Sequence, Tuple


MAXIMUM_STATUS_BYTES = 1024 * 1024
_FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
_INITIALIZATION_ID_RE = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class MapBinding:
    fingerprint: str
    frame_id: str


@dataclass(frozen=True)
class CovarianceQuality:
    x_stddev_m: float
    y_stddev_m: float
    yaw_stddev_rad: float


@dataclass(frozen=True)
class GlobalScanMatch:
    fingerprint: str
    generation: int
    initialization_id: str
    x_m: float
    y_m: float
    yaw_rad: float
    score: float
    endpoint_ratio: float
    score_ratio: float


def _decode_json_status(data: Any, label: str) -> Tuple[Optional[dict], Optional[str]]:
    if not isinstance(data, str):
        return None, f"{label} muss Text sein"
    try:
        size = len(data.encode("utf-8"))
    except UnicodeError:
        return None, f"{label} enthaelt ungueltiges Unicode"
    if size > MAXIMUM_STATUS_BYTES:
        return None, f"{label} ist groesser als {MAXIMUM_STATUS_BYTES} Bytes"
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, TypeError, RecursionError, UnicodeError):
        return None, f"{label} enthaelt kein gueltiges JSON"
    if not isinstance(payload, dict):
        return None, f"{label} muss ein JSON-Objekt sein"
    if payload.get("schema_version") != 1:
        return None, f"{label} hat keine unterstuetzte schema_version"
    if payload.get("ok") is not True:
        return None, f"{label} bestaetigt den Zustand nicht mit ok=true"
    return payload, None


def _binding(fingerprint: Any, frame_id: Any, label: str):
    if not isinstance(fingerprint, str) or _FINGERPRINT_RE.fullmatch(fingerprint) is None:
        return None, f"{label} enthaelt keinen gueltigen Karten-Fingerprint"
    if not isinstance(frame_id, str) or frame_id.strip() != "map":
        return None, f"{label} verwendet nicht den Frame 'map'"
    return MapBinding(fingerprint=fingerprint, frame_id="map"), None


def decode_map_manager_binding(data: Any):
    """Liest den Fingerprint einer eindeutig publizierten metrischen Karte."""
    payload, error = _decode_json_status(data, "Kartenmanager-Status")
    if error:
        return None, error
    map_status = payload.get("map")
    if not isinstance(map_status, dict):
        return None, "Kartenmanager-Status enthaelt kein map-Objekt"
    if map_status.get("snapshot_available", map_status.get("available")) is not True:
        return None, "Kartenmanager hat keinen Karten-Snapshot"
    publisher_count = map_status.get("publisher_count")
    if isinstance(publisher_count, bool) or publisher_count != 1:
        return None, (
            "Die metrische Karte braucht genau einen Publisher; "
            f"gemeldet sind {publisher_count!r}"
        )
    summary = map_status.get("summary")
    if not isinstance(summary, dict):
        return None, "Kartenmanager-Status enthaelt keine map.summary"
    return _binding(
        summary.get("fingerprint"), summary.get("frame_id"),
        "Kartenmanager-Status")


def decode_semantic_binding(data: Any):
    """Liest nur einen editierbaren, vom Kartenmanager bestaetigten Bezug."""
    payload, error = _decode_json_status(data, "Semantik-Status")
    if error:
        return None, error
    semantic_map = payload.get("semantic_map")
    if not isinstance(semantic_map, dict):
        return None, "Semantik-Status enthaelt keine semantic_map"
    if semantic_map.get("editable") is not True:
        return None, "Semantische Karte ist nicht freigegeben/editierbar"
    map_ref = semantic_map.get("map_ref")
    if not isinstance(map_ref, dict):
        return None, "Semantik-Status enthaelt keine map_ref"
    binding, error = _binding(
        map_ref.get("fingerprint"), map_ref.get("frame_id"),
        "Semantik-Status")
    if error:
        return None, error
    manager = payload.get("map_manager")
    if not isinstance(manager, dict):
        return None, "Semantik-Status enthaelt keinen Kartenmanager-Bezug"
    if manager.get("observed_fingerprint") != binding.fingerprint:
        return None, "Semantik und beobachtete metrische Karte stimmen nicht ueberein"
    return binding, None


def matching_bindings(
        map_binding: Optional[MapBinding],
        semantic_binding: Optional[MapBinding]) -> bool:
    return (
        map_binding is not None
        and semantic_binding is not None
        and map_binding == semantic_binding
    )


def initialization_matches_bindings(
        map_binding: Optional[MapBinding],
        semantic_binding: Optional[MapBinding],
        initialized_fingerprint: Optional[str]) -> bool:
    """Bindet einen globalen AMCL-Reset unverwechselbar an seine Karte."""
    return (
        matching_bindings(map_binding, semantic_binding)
        and isinstance(initialized_fingerprint, str)
        and map_binding.fingerprint == initialized_fingerprint
    )


def _finite_number(value: Any, label: str):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, f"{label} muss eine Zahl sein"
    number = float(value)
    if not math.isfinite(number):
        return None, f"{label} muss endlich sein"
    return number, None


def decode_global_scan_match(
        data: Any, *, expected_fingerprint: Optional[str],
        expected_generation: int, expected_initialization_id: Optional[str],
        minimum_score: float, minimum_endpoint_ratio: float,
        minimum_score_ratio: float):
    """Prueft einen Vollscan-Treffer gegen Karte und konkreten Global-Reset."""
    payload, error = _decode_json_status(data, "Vollscan-Status")
    if error:
        return None, error
    if payload.get("state") != "accepted":
        return None, "Vollscan-Status ist nicht akzeptiert"
    fingerprint = payload.get("map_fingerprint")
    if (
            not isinstance(fingerprint, str)
            or _FINGERPRINT_RE.fullmatch(fingerprint) is None):
        return None, "Vollscan-Status enthaelt keinen gueltigen Karten-Fingerprint"
    generation = payload.get("global_initialization_generation")
    if (
            isinstance(generation, bool)
            or not isinstance(generation, int)
            or generation <= 0):
        return None, "Vollscan-Status enthaelt keine gueltige Reset-Generation"
    initialization_id = payload.get("global_initialization_id")
    if (
            not isinstance(initialization_id, str)
            or _INITIALIZATION_ID_RE.fullmatch(initialization_id) is None):
        return None, "Vollscan-Status enthaelt keine gueltige Reset-ID"
    if fingerprint != expected_fingerprint:
        return None, "Vollscan-Treffer gehoert nicht zur aktuellen Karte"
    if generation != expected_generation:
        return None, "Vollscan-Treffer gehoert nicht zur aktuellen Reset-Generation"
    if initialization_id != expected_initialization_id:
        return None, "Vollscan-Treffer gehoert nicht zum aktuellen Global-Reset"

    pose = payload.get("pose")
    if not isinstance(pose, dict):
        return None, "Vollscan-Status enthaelt keine Pose"
    numbers = {}
    for key, label in (
            ("x_m", "Vollscan-x"),
            ("y_m", "Vollscan-y"),
            ("yaw_rad", "Vollscan-Winkel")):
        numbers[key], error = _finite_number(pose.get(key), label)
        if error:
            return None, error
    for key, label in (
            ("score", "Vollscan-Score"),
            ("endpoint_within_0_15_m_ratio", "Vollscan-Wandtrefferquote"),
            ("score_ratio", "Vollscan-Bestenabstand")):
        numbers[key], error = _finite_number(payload.get(key), label)
        if error:
            return None, error
    if not (0.0 <= numbers["score"] <= 1.0):
        return None, "Vollscan-Score liegt nicht zwischen 0 und 1"
    if not (0.0 <= numbers["endpoint_within_0_15_m_ratio"] <= 1.0):
        return None, "Vollscan-Wandtrefferquote liegt nicht zwischen 0 und 1"
    if numbers["score_ratio"] < 1.0:
        return None, "Vollscan-Bestenabstand ist ungueltig"
    limits = (minimum_score, minimum_endpoint_ratio, minimum_score_ratio)
    if not all(math.isfinite(limit) and limit > 0.0 for limit in limits):
        raise ValueError("Vollscan-Grenzen muessen endlich und positiv sein")
    if numbers["score"] < minimum_score:
        return None, "Vollscan-Gesamtscore ist zu klein"
    if numbers["endpoint_within_0_15_m_ratio"] < minimum_endpoint_ratio:
        return None, "Vollscan-Wandtrefferquote ist zu klein"
    if numbers["score_ratio"] < minimum_score_ratio:
        return None, "Vollscan-Treffer ist nicht eindeutig genug"
    return GlobalScanMatch(
        fingerprint=fingerprint,
        generation=generation,
        initialization_id=initialization_id,
        x_m=numbers["x_m"],
        y_m=numbers["y_m"],
        yaw_rad=numbers["yaw_rad"],
        score=numbers["score"],
        endpoint_ratio=numbers["endpoint_within_0_15_m_ratio"],
        score_ratio=numbers["score_ratio"]), None


def pose_matches_global_scan(
        x_m: float, y_m: float, yaw_rad: float,
        match: GlobalScanMatch, *, maximum_position_error_m: float,
        maximum_yaw_error_rad: float):
    """Bestaetigt, dass AMCL den akzeptierten LiDAR-Startwert annahm."""
    values = (
        x_m, y_m, yaw_rad, maximum_position_error_m,
        maximum_yaw_error_rad)
    if not all(math.isfinite(value) for value in values):
        return False, "AMCL/Vollscan-Vergleich enthaelt ungueltige Werte"
    if maximum_position_error_m <= 0.0 or maximum_yaw_error_rad <= 0.0:
        raise ValueError("AMCL/Vollscan-Grenzen muessen positiv sein")
    position_error = math.hypot(x_m - match.x_m, y_m - match.y_m)
    yaw_error = angular_distance(yaw_rad, match.yaw_rad)
    if position_error > maximum_position_error_m:
        return False, (
            f'AMCL ist {position_error:.3f} m vom Vollscan-Treffer entfernt')
    if yaw_error > maximum_yaw_error_rad:
        return False, (
            'AMCL-Winkel ist '
            f'{math.degrees(yaw_error):.1f} Grad vom Vollscan-Treffer entfernt')
    return True, "bestaetigt"


def covariance_quality(
        covariance: Any,
        *,
        maximum_position_stddev_m: float,
        maximum_yaw_stddev_rad: float):
    """Prueft die drei fuer den ebenen Roboter relevanten AMCL-Varianzen."""
    if isinstance(covariance, (str, bytes, bytearray)):
        return None, "AMCL-Kovarianz muss genau 36 Werte enthalten"
    try:
        covariance_length = len(covariance)
    except (TypeError, AttributeError):
        covariance_length = -1
    if covariance_length != 36:
        return None, "AMCL-Kovarianz muss genau 36 Werte enthalten"
    limits = (maximum_position_stddev_m, maximum_yaw_stddev_rad)
    if not all(math.isfinite(value) and value > 0.0 for value in limits):
        return None, "Kovarianzgrenzen muessen endlich und positiv sein"
    variances = []
    for index in (0, 7, 35):
        value = covariance[index]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, "AMCL-Kovarianz enthaelt keinen Zahlenwert"
        value = float(value)
        if not math.isfinite(value) or value < 0.0:
            return None, "AMCL-Kovarianz enthaelt eine ungueltige Varianz"
        variances.append(value)
    quality = CovarianceQuality(*(math.sqrt(value) for value in variances))
    if (
            quality.x_stddev_m > maximum_position_stddev_m
            or quality.y_stddev_m > maximum_position_stddev_m):
        return quality, "AMCL-Positionsunsicherheit ist noch zu gross"
    if quality.yaw_stddev_rad > maximum_yaw_stddev_rad:
        return quality, "AMCL-Winkelunsicherheit ist noch zu gross"
    return quality, None


def covariance_hysteresis_limits(
        previously_ready: bool,
        *,
        acquire_position_stddev_m: float,
        acquire_yaw_stddev_rad: float,
        release_position_stddev_m: float,
        release_yaw_stddev_rad: float) -> Tuple[float, float]:
    """Waehlt strengere Eintritts- und weitere Verlustgrenzen.

    Die weiteren Grenzen gelten nur, solange die Lokalisierung im unmittelbar
    vorherigen Guard-Tick freigegeben war. Jeder andere harte Fehler setzt den
    Guard auf die strengen Eintrittsgrenzen zurueck.
    """
    limits = (
        acquire_position_stddev_m,
        acquire_yaw_stddev_rad,
        release_position_stddev_m,
        release_yaw_stddev_rad,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in limits):
        raise ValueError('Hysteresegrenzen muessen endlich und positiv sein')
    if (
            release_position_stddev_m < acquire_position_stddev_m
            or release_yaw_stddev_rad < acquire_yaw_stddev_rad):
        raise ValueError(
            'Verlustgrenzen duerfen nicht strenger als Eintrittsgrenzen sein')
    if previously_ready is True:
        return release_position_stddev_m, release_yaw_stddev_rad
    return acquire_position_stddev_m, acquire_yaw_stddev_rad


def transform_stability_hysteresis_limits(
        previously_ready: bool,
        *,
        acquire_translation_m: float,
        acquire_yaw_rad: float,
        release_translation_m: float,
        release_yaw_rad: float) -> Tuple[float, float]:
    """Waehlt strenge Erwerbs- und gemessene Fahrgrenzen fuer map->odom."""
    limits = (
        acquire_translation_m,
        acquire_yaw_rad,
        release_translation_m,
        release_yaw_rad,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in limits):
        raise ValueError('TF-Stabilitaetsgrenzen muessen endlich und positiv sein')
    if (
            release_translation_m < acquire_translation_m
            or release_yaw_rad < acquire_yaw_rad):
        raise ValueError(
            'TF-Verlustgrenzen duerfen nicht strenger als Erwerbsgrenzen sein')
    if previously_ready is True:
        return release_translation_m, release_yaw_rad
    return acquire_translation_m, acquire_yaw_rad


def angular_distance(left: float, right: float) -> float:
    return abs(math.atan2(math.sin(left - right), math.cos(left - right)))


def transform_window_stable(
        samples: Sequence[Tuple[float, float, float, float]],
        *,
        minimum_duration_s: float,
        minimum_samples: int,
        maximum_translation_m: float,
        maximum_yaw_rad: float):
    """Prueft, ob map->odom ueber ein echtes Zeitfenster ruhig geblieben ist."""
    if len(samples) < minimum_samples:
        return False, "Noch zu wenige map->odom-Messpunkte"
    first = samples[0]
    last = samples[-1]
    if last[0] - first[0] < minimum_duration_s:
        return False, "map->odom ist noch nicht lange genug stabil"
    x0, y0, yaw0 = first[1], first[2], first[3]
    maximum_translation = max(
        math.hypot(sample[1] - x0, sample[2] - y0)
        for sample in samples
    )
    maximum_yaw = max(angular_distance(sample[3], yaw0) for sample in samples)
    if maximum_translation > maximum_translation_m:
        return False, "map->odom korrigiert die Position noch zu stark"
    if maximum_yaw > maximum_yaw_rad:
        return False, "map->odom korrigiert den Winkel noch zu stark"
    return True, "stabil"


def transform_window_motion(
        samples: Sequence[Tuple[float, float, float, float]]) -> Tuple[float, float, float]:
    """Liefert Dauer, maximale Translation und maximalen Winkel zum Fensterstart."""
    if not samples:
        return 0.0, 0.0, 0.0
    first = samples[0]
    last = samples[-1]
    maximum_translation = max(
        math.hypot(sample[1] - first[1], sample[2] - first[2])
        for sample in samples
    )
    maximum_yaw = max(
        angular_distance(sample[3], first[3]) for sample in samples)
    return max(0.0, last[0] - first[0]), maximum_translation, maximum_yaw
