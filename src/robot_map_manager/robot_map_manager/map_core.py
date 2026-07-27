"""ROS-unabhängiger Kern für Kartenvalidierung, Protokoll und Speicherung.

Dieses Modul importiert absichtlich kein ROS-Paket. Dadurch lassen sich alle
Dateisystem- und Validierungsregeln auch auf einem Entwicklungsrechner nur mit
der Python-Standardbibliothek testen.
"""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import heapq
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import time
from typing import Any, Iterable, Optional, Sequence
import uuid


MAXIMUM_CELL_COUNT = 4_000_000
MAXIMUM_DIMENSION = 100_000
MAXIMUM_COMMAND_BYTES = 4_096
MAXIMUM_METADATA_BYTES = 128 * 1_024
MAXIMUM_LIST_ENTRIES = 1_000
QUATERNION_NORM_TOLERANCE = 1e-3

_MAP_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_VERSION_RE = re.compile(
    r"^\d{8}T\d{12}Z-[0-9a-f]{12}(?:-\d{2})?$"
)
_STAGING_RE = re.compile(r"^\.tmp-[0-9a-f]{32}$")
_STAGING_ARTIFACTS = {
    "occupancy.bin",
    "map.pgm",
    "map.yaml",
    "metadata.json",
}
_IDENTITY_TRANSLATION = bytes(range(256))
_VALID_COMPACT_CELL_BYTES = bytes(range(101)) + b"\xff"


class MapValidationError(ValueError):
    """Die OccupancyGrid-Daten verletzen den Kartenvertrag."""


class CommandValidationError(ValueError):
    """Ein JSON-Kommando ist syntaktisch oder semantisch ungültig."""


class MapStorageError(RuntimeError):
    """Eine Karte konnte nicht sicher im Repository gespeichert werden."""


class SaveProtectionError(MapStorageError):
    """Ein konfiguriertes Speicherlimit verhindert eine neue Version."""


class RequestIDConflict(CommandValidationError):
    """Eine request_id wurde bereits für ein anderes Kommando verwendet."""


@dataclass(frozen=True)
class StoragePolicy:
    minimum_save_interval_s: float = 5.0
    minimum_list_interval_s: float = 10.0
    maximum_list_verify_bytes: int = 128 * 1024 * 1024
    minimum_free_space_bytes: int = 512 * 1024 * 1024
    maximum_versions_per_map: int = 100
    maximum_total_storage_bytes: int = 2 * 1024 * 1024 * 1024
    maximum_map_names: int = 16
    staging_cleanup_min_age_s: float = 3600.0
    staging_cleanup_max_entries: int = 32

    def validated(self) -> "StoragePolicy":
        finite_fields = {
            "minimum_save_interval_s": self.minimum_save_interval_s,
            "minimum_list_interval_s": self.minimum_list_interval_s,
            "staging_cleanup_min_age_s": self.staging_cleanup_min_age_s,
        }
        for name, value in finite_fields.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) < 0.0
            ):
                raise MapStorageError(f"{name} muss eine nichtnegative endliche Zahl sein.")
        integer_fields = {
            "maximum_list_verify_bytes": self.maximum_list_verify_bytes,
            "minimum_free_space_bytes": self.minimum_free_space_bytes,
            "maximum_versions_per_map": self.maximum_versions_per_map,
            "maximum_total_storage_bytes": self.maximum_total_storage_bytes,
            "maximum_map_names": self.maximum_map_names,
            "staging_cleanup_max_entries": self.staging_cleanup_max_entries,
        }
        for name, value in integer_fields.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise MapStorageError(f"{name} muss eine nichtnegative Ganzzahl sein.")
        if self.maximum_versions_per_map == 0:
            raise MapStorageError("maximum_versions_per_map muss größer als null sein.")
        if self.maximum_list_verify_bytes == 0:
            raise MapStorageError("maximum_list_verify_bytes muss größer als null sein.")
        if self.maximum_total_storage_bytes == 0:
            raise MapStorageError("maximum_total_storage_bytes muss größer als null sein.")
        if self.maximum_map_names == 0:
            raise MapStorageError("maximum_map_names muss größer als null sein.")
        return self


class BoundedRequestCache:
    """Begrenzter Laufzeitcache für idempotente JSON-Kommandos."""

    def __init__(self, maximum_entries: int) -> None:
        if (
            isinstance(maximum_entries, bool)
            or not isinstance(maximum_entries, int)
            or maximum_entries <= 0
            or maximum_entries > 10_000
        ):
            raise ValueError("maximum_entries muss zwischen 1 und 10000 liegen.")
        self.maximum_entries = maximum_entries
        self._entries: OrderedDict[str, tuple[tuple[Any, ...], str]] = OrderedDict()

    def lookup(
        self,
        request_id: str,
        signature: tuple[Any, ...],
    ) -> Optional[str]:
        entry = self._entries.get(request_id)
        if entry is None:
            return None
        stored_signature, response = entry
        if stored_signature != signature:
            raise RequestIDConflict(
                "request_id wurde bereits für ein anderes Kommando verwendet."
            )
        self._entries.move_to_end(request_id)
        return response

    def store(
        self,
        request_id: str,
        signature: tuple[Any, ...],
        response: str,
    ) -> None:
        existing = self._entries.get(request_id)
        if existing is not None and existing[0] != signature:
            raise RequestIDConflict(
                "request_id wurde bereits für ein anderes Kommando verwendet."
            )
        self._entries[request_id] = (signature, response)
        self._entries.move_to_end(request_id)
        while len(self._entries) > self.maximum_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)


class MinimumIntervalGuard:
    """Globale monotone Abkühlzeit, unabhängig von wechselnden IDs."""

    def __init__(self, minimum_interval_s: float) -> None:
        if (
            isinstance(minimum_interval_s, bool)
            or not isinstance(minimum_interval_s, (int, float))
            or not math.isfinite(float(minimum_interval_s))
            or float(minimum_interval_s) < 0.0
        ):
            raise ValueError(
                "minimum_interval_s muss eine nichtnegative endliche Zahl sein."
            )
        self.minimum_interval_s = float(minimum_interval_s)
        self._last_acquired: Optional[float] = None

    def acquire(self, *, now: float) -> tuple[bool, float]:
        if (
            isinstance(now, bool)
            or not isinstance(now, (int, float))
            or not math.isfinite(float(now))
        ):
            raise ValueError("now muss eine endliche monotone Zeit sein.")
        current = float(now)
        if self._last_acquired is None or self.minimum_interval_s == 0.0:
            self._last_acquired = current
            return True, 0.0
        elapsed = current - self._last_acquired
        if elapsed < 0.0:
            return False, self.minimum_interval_s
        remaining = self.minimum_interval_s - elapsed
        if remaining > 0.0:
            return False, remaining
        self._last_acquired = current
        return True, 0.0


class RawDuplicateGuard:
    """Unterdrückt nur zeitnahe Cross-QoS-Duplikate mit ROS-Identität."""

    def __init__(self, window_s: float) -> None:
        if (
            isinstance(window_s, bool)
            or not isinstance(window_s, (int, float))
            or not math.isfinite(float(window_s))
            or float(window_s) < 0.0
        ):
            raise ValueError("window_s muss eine nichtnegative endliche Zahl sein.")
        self.window_s = float(window_s)
        self._last_signature: Optional[tuple[Any, ...]] = None
        self._last_source: Optional[str] = None
        self._last_seen = 0.0
        self._last_was_valid = False

    def is_duplicate(
        self,
        signature: tuple[Any, ...],
        *,
        source: str,
        now: float,
        has_ros_identity: bool,
    ) -> bool:
        if not has_ros_identity or self.window_s == 0.0:
            self._remember(signature, source, now, valid=False)
            return False
        duplicate = (
            self._last_was_valid
            and signature == self._last_signature
            and source != self._last_source
            and 0.0 <= now - self._last_seen <= self.window_s
        )
        if not duplicate:
            self._remember(signature, source, now, valid=False)
        return duplicate

    def mark_valid(
        self,
        signature: tuple[Any, ...],
        *,
        source: str,
        now: float,
    ) -> None:
        """Markiert nur eine vollständig validierte Erstlieferung als überspringbar."""

        self._remember(signature, source, now, valid=True)

    def _remember(
        self,
        signature: tuple[Any, ...],
        source: str,
        now: float,
        *,
        valid: bool,
    ) -> None:
        self._last_signature = signature
        self._last_source = source
        self._last_seen = now
        self._last_was_valid = valid


def validate_transform_timestamp(
    *,
    stamp_ns: int,
    now_ns: int,
    maximum_age_s: float,
    future_tolerance_s: float = 0.25,
) -> tuple[bool, Optional[float]]:
    """Prüft TF-Zeitstempel; null nutzt nur die übliche Static-TF-Konvention.

    Ein Nullstempel beweist nicht, dass die Quelle tatsächlich ``/tf_static``
    war. Er bedeutet hier ausschließlich, dass keine ehrliche Altersprüfung
    möglich ist und die TF gemäß Konvention alterslos akzeptiert wird.
    """

    if (
        isinstance(stamp_ns, bool)
        or not isinstance(stamp_ns, int)
        or stamp_ns < 0
        or isinstance(now_ns, bool)
        or not isinstance(now_ns, int)
        or now_ns < 0
    ):
        raise MapValidationError("TF-Zeitstempel müssen nichtnegative Ganzzahlen sein.")
    maximum_age = _require_finite_number(maximum_age_s, "maximum_age_s")
    future_tolerance = _require_finite_number(
        future_tolerance_s,
        "future_tolerance_s",
    )
    if maximum_age <= 0.0 or future_tolerance < 0.0:
        raise MapValidationError("TF-Altersgrenzen sind ungültig.")
    if stamp_ns == 0:
        return True, None
    age = (now_ns - stamp_ns) / 1_000_000_000.0
    if age < -future_tolerance:
        raise MapValidationError(
            f"Dynamische TF liegt {-age:.3f} s in der Zukunft."
        )
    if age > maximum_age:
        raise MapValidationError(
            f"Dynamische TF ist {age:.3f} s alt; erlaubt sind höchstens "
            f"{maximum_age:.3f} s."
        )
    return False, age


def default_storage_root(home: Optional[Path] = None) -> Path:
    """Liefert den standardmäßigen, vom Workspace getrennten Kartenpfad."""

    base = Path.home() if home is None else Path(home)
    return base / ".local" / "share" / "amadeus" / "maps"


def validate_grid_shape_and_length(
    width: Any,
    height: Any,
    data_length: Any,
    *,
    maximum_cell_count: int = MAXIMUM_CELL_COUNT,
) -> int:
    """Prüft billige Grid-Grenzen, bevor Zellinhalte gehasht werden."""

    if (
        isinstance(width, bool)
        or not isinstance(width, int)
        or isinstance(height, bool)
        or not isinstance(height, int)
        or width <= 0
        or height <= 0
        or width > MAXIMUM_DIMENSION
        or height > MAXIMUM_DIMENSION
    ):
        raise MapValidationError(
            f"Ungültige Kartenabmessungen {width!r} × {height!r}."
        )
    cell_count = width * height
    if cell_count > maximum_cell_count:
        raise MapValidationError(
            f"Karte enthält {cell_count} Zellen; erlaubt sind höchstens "
            f"{maximum_cell_count}."
        )
    if (
        isinstance(data_length, bool)
        or not isinstance(data_length, int)
        or data_length < 0
    ):
        raise MapValidationError(
            "Kartendaten müssen eine bekannte nichtnegative Länge besitzen."
        )
    if data_length != cell_count:
        raise MapValidationError(
            f"Karte erwartet {cell_count} Zellwerte, enthält aber "
            f"{data_length}."
        )
    return cell_count


def validate_map_name(value: Any) -> str:
    """Validiert einen als Verzeichnisnamen verwendeten Kartennamen strikt."""

    if not isinstance(value, str) or not _MAP_NAME_RE.fullmatch(value):
        raise MapValidationError(
            "Kartenname muss 1–64 Zeichen lang sein und ausschließlich "
            "Kleinbuchstaben, Ziffern, '_' oder '-' enthalten."
        )
    return value


def _require_finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapValidationError(f"{field} muss eine endliche Zahl sein.")
    result = float(value)
    if not math.isfinite(result):
        raise MapValidationError(f"{field} muss eine endliche Zahl sein.")
    return result


def validate_quaternion(
    values: Sequence[Any],
    *,
    tolerance: float = QUATERNION_NORM_TOLERANCE,
) -> tuple[float, float, float, float]:
    """Validiert eine endliche, normalisierte Quaternion ohne sie umzudeuten."""

    if len(values) != 4:
        raise MapValidationError("Quaternion muss genau vier Komponenten enthalten.")
    x, y, z, w = (
        _require_finite_number(value, f"Quaternion[{index}]")
        for index, value in enumerate(values)
    )
    norm_squared = x * x + y * y + z * z + w * w
    if norm_squared <= 1e-12:
        raise MapValidationError("Quaternion darf nicht die Nullquaternion sein.")
    norm = math.sqrt(norm_squared)
    if abs(norm - 1.0) > tolerance:
        raise MapValidationError(
            f"Quaternion ist nicht normalisiert (Norm {norm:.9g})."
        )
    return x, y, z, w


@dataclass(frozen=True)
class MapOrigin:
    position_x: float
    position_y: float
    position_z: float
    orientation_x: float
    orientation_y: float
    orientation_z: float
    orientation_w: float

    def validated(self) -> "MapOrigin":
        position = (
            _require_finite_number(self.position_x, "origin.position.x"),
            _require_finite_number(self.position_y, "origin.position.y"),
            _require_finite_number(self.position_z, "origin.position.z"),
        )
        quaternion = validate_quaternion(
            (
                self.orientation_x,
                self.orientation_y,
                self.orientation_z,
                self.orientation_w,
            )
        )
        return MapOrigin(*position, *quaternion)

    @property
    def yaw(self) -> float:
        return math.atan2(
            2.0
            * (
                self.orientation_w * self.orientation_z
                + self.orientation_x * self.orientation_y
            ),
            1.0
            - 2.0
            * (
                self.orientation_y * self.orientation_y
                + self.orientation_z * self.orientation_z
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "position": {
                "x": self.position_x,
                "y": self.position_y,
                "z": self.position_z,
            },
            "orientation": {
                "x": self.orientation_x,
                "y": self.orientation_y,
                "z": self.orientation_z,
                "w": self.orientation_w,
            },
            "yaw": self.yaw,
        }


def _validated_compact_cells(cells: Iterable[Any], cell_count: int) -> bytes:
    """Übernimmt ROS-int8-Puffer schnell, mit vollständiger Werteprüfung."""

    try:
        view = memoryview(cells)
    except TypeError:
        view = None

    if (
        view is not None
        and view.ndim == 1
        and view.itemsize == 1
        and view.c_contiguous
        and view.format in {"b", "B", "c"}
    ):
        compact = view.cast("B").tobytes()
        if len(compact) != cell_count:
            raise MapValidationError(
                f"Karte erwartet {cell_count} Zellwerte, enthält aber "
                f"{len(compact)}."
            )
        # bytes.translate arbeitet in C. Nach dem Löschen aller erlaubten
        # Werte bleiben ausschließlich ungültige int8-Bitmuster übrig.
        invalid = compact.translate(
            _IDENTITY_TRANSLATION,
            _VALID_COMPACT_CELL_BYTES,
        )
        if invalid:
            raw_value = invalid[0]
            signed_value = raw_value if raw_value < 128 else raw_value - 256
            raise MapValidationError(
                f"Kartenwert {signed_value!r} liegt nicht als Ganzzahl "
                "zwischen -1 und 100 vor."
            )
        return compact

    compact_cells = bytearray()
    try:
        iterator = iter(cells)
    except TypeError as error:
        raise MapValidationError("Kartendaten müssen iterierbar sein.") from error
    for index, value in enumerate(iterator):
        if index >= cell_count:
            raise MapValidationError(
                f"Karte erwartet {cell_count} Zellwerte, enthält aber mehr."
            )
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < -1
            or value > 100
        ):
            raise MapValidationError(
                f"Kartenwert {value!r} an Position {index} liegt nicht "
                "als Ganzzahl zwischen -1 und 100 vor."
            )
        compact_cells.append(255 if value == -1 else value)
    if len(compact_cells) != cell_count:
        raise MapValidationError(
            f"Karte erwartet {cell_count} Zellwerte, enthält aber "
            f"{len(compact_cells)}."
        )
    return bytes(compact_cells)


def raw_cell_digest(
    cells: Iterable[Any],
) -> tuple[int, str, Optional[bytes]]:
    """Signiert den vollständigen ROS-int8-Inhalt vor der Snapshot-Konvertierung.

    Für den üblichen zusammenhängenden ``array('b')``-Puffer scannt hashlib
    direkt in C und es entsteht keine Millionen-Zellen-Python-Schleife. Der
    optionale dritte Rückgabewert enthält nur beim generischen Fallback bereits
    validierte kompakte Zellen, damit diese nicht nochmals konvertiert werden.
    """

    try:
        view = memoryview(cells)
    except TypeError:
        view = None
    if (
        view is not None
        and view.ndim == 1
        and view.itemsize == 1
        and view.c_contiguous
        and view.format in {"b", "B", "c"}
    ):
        if view.nbytes > MAXIMUM_CELL_COUNT:
            raise MapValidationError(
                f"Karte enthält mehr als {MAXIMUM_CELL_COUNT} Zellwerte."
            )
        return view.nbytes, hashlib.sha256(view).hexdigest(), None

    try:
        cell_count = len(cells)  # type: ignore[arg-type]
    except (TypeError, OverflowError) as error:
        raise MapValidationError(
            "Kartendaten müssen eine bekannte Länge besitzen."
        ) from error
    if cell_count > MAXIMUM_CELL_COUNT:
        raise MapValidationError(
            f"Karte enthält mehr als {MAXIMUM_CELL_COUNT} Zellwerte."
        )
    compact = _validated_compact_cells(cells, cell_count)
    return cell_count, hashlib.sha256(compact).hexdigest(), compact


@dataclass(frozen=True)
class MapSnapshot:
    width: int
    height: int
    resolution: float
    frame_id: str
    origin: MapOrigin
    # Kompakte uint8-Kodierung: 0...100 unverändert, 255 entspricht ROS -1.
    cells: bytes = field(repr=False)
    source_stamp_ns: int = 0
    fingerprint: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.width, bool)
            or not isinstance(self.width, int)
            or isinstance(self.height, bool)
            or not isinstance(self.height, int)
            or self.width <= 0
            or self.height <= 0
            or self.width > MAXIMUM_DIMENSION
            or self.height > MAXIMUM_DIMENSION
            or self.width * self.height > MAXIMUM_CELL_COUNT
        ):
            raise MapValidationError("MapSnapshot enthält ungültige Dimensionen.")
        clean_resolution = _require_finite_number(self.resolution, "resolution")
        if clean_resolution <= 0.0:
            raise MapValidationError("Kartenauflösung muss größer als null sein.")
        if not isinstance(self.frame_id, str):
            raise MapValidationError("frame_id muss eine Zeichenkette sein.")
        clean_frame = self.frame_id.strip()
        if (
            not clean_frame
            or len(clean_frame) > 128
            or any(ord(character) < 0x20 for character in clean_frame)
        ):
            raise MapValidationError("frame_id ist leer, zu lang oder enthält Steuerzeichen.")
        if not isinstance(self.origin, MapOrigin):
            raise MapValidationError("Kartenursprung hat nicht die erwartete Struktur.")
        clean_origin = self.origin.validated()
        if not isinstance(self.cells, bytes):
            raise MapValidationError("Interne Kartenzellen müssen kompakt als bytes vorliegen.")
        if len(self.cells) != self.width * self.height:
            raise MapValidationError("Kompakte Kartendaten haben die falsche Länge.")
        if self.cells.translate(
            _IDENTITY_TRANSLATION,
            _VALID_COMPACT_CELL_BYTES,
        ):
            raise MapValidationError(
                "Kompakte Kartendaten enthalten ungültige Zellwerte."
            )
        if (
            isinstance(self.source_stamp_ns, bool)
            or not isinstance(self.source_stamp_ns, int)
            or self.source_stamp_ns < 0
        ):
            raise MapValidationError("source_stamp_ns muss eine nichtnegative Ganzzahl sein.")

        object.__setattr__(self, "resolution", clean_resolution)
        object.__setattr__(self, "frame_id", clean_frame)
        object.__setattr__(self, "origin", clean_origin)

        # Der Fingerabdruck wird genau einmal berechnet. Das ist bei Karten
        # mit mehreren Millionen Zellen wichtig, weil er in Status und
        # Duplikatprüfung häufig gelesen wird.
        digest = hashlib.sha256()
        digest.update(struct.pack("!IId", self.width, self.height, self.resolution))
        frame_bytes = self.frame_id.encode("utf-8")
        digest.update(struct.pack("!H", len(frame_bytes)))
        digest.update(frame_bytes)
        digest.update(
            struct.pack(
                "!7d",
                self.origin.position_x,
                self.origin.position_y,
                self.origin.position_z,
                self.origin.orientation_x,
                self.origin.orientation_y,
                self.origin.orientation_z,
                self.origin.orientation_w,
            )
        )
        digest.update(self.cells)
        object.__setattr__(self, "fingerprint", digest.hexdigest())

    @classmethod
    def from_values(
        cls,
        *,
        width: Any,
        height: Any,
        resolution: Any,
        frame_id: Any,
        origin: MapOrigin,
        cells: Iterable[Any],
        source_stamp_ns: Any = 0,
        maximum_cell_count: int = MAXIMUM_CELL_COUNT,
    ) -> "MapSnapshot":
        if (
            isinstance(width, bool)
            or not isinstance(width, int)
            or isinstance(height, bool)
            or not isinstance(height, int)
        ):
            raise MapValidationError("Kartenbreite und -höhe müssen Ganzzahlen sein.")
        if width <= 0 or height <= 0:
            raise MapValidationError(
                f"Ungültige Kartenabmessungen {width} × {height}."
            )
        if width > MAXIMUM_DIMENSION or height > MAXIMUM_DIMENSION:
            raise MapValidationError(
                f"Kartenabmessungen überschreiten {MAXIMUM_DIMENSION} Zellen."
            )
        cell_count = width * height
        if cell_count > maximum_cell_count:
            raise MapValidationError(
                f"Karte enthält {cell_count} Zellen; erlaubt sind höchstens "
                f"{maximum_cell_count}."
            )

        clean_resolution = _require_finite_number(resolution, "resolution")
        if clean_resolution <= 0.0:
            raise MapValidationError("Kartenauflösung muss größer als null sein.")

        if not isinstance(frame_id, str):
            raise MapValidationError("frame_id muss eine Zeichenkette sein.")
        clean_frame = frame_id.strip()
        if (
            not clean_frame
            or len(clean_frame) > 128
            or any(ord(character) < 0x20 for character in clean_frame)
        ):
            raise MapValidationError("frame_id ist leer, zu lang oder enthält Steuerzeichen.")

        if not isinstance(origin, MapOrigin):
            raise MapValidationError("Kartenursprung hat nicht die erwartete Struktur.")
        clean_origin = origin.validated()

        compact_cells = _validated_compact_cells(cells, cell_count)

        if (
            isinstance(source_stamp_ns, bool)
            or not isinstance(source_stamp_ns, int)
            or source_stamp_ns < 0
        ):
            raise MapValidationError("source_stamp_ns muss eine nichtnegative Ganzzahl sein.")

        return cls(
            width=width,
            height=height,
            resolution=clean_resolution,
            frame_id=clean_frame,
            origin=clean_origin,
            cells=compact_cells,
            source_stamp_ns=source_stamp_ns,
        )

    def summary(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "frame_id": self.frame_id,
            "origin": self.origin.as_dict(),
            "source_stamp_ns": self.source_stamp_ns,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class MapCommand:
    command: str
    name: Optional[str] = None
    request_id: Optional[str] = None


def parse_command_json(text: Any) -> MapCommand:
    """Dekodiert genau die Kommandos save, list und status."""

    if not isinstance(text, str):
        raise CommandValidationError("Kommando muss als JSON-Zeichenkette ankommen.")
    if len(text.encode("utf-8")) > MAXIMUM_COMMAND_BYTES:
        raise CommandValidationError("Kommando überschreitet 4096 Bytes.")
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise CommandValidationError("Kommando enthält kein gültiges JSON.") from error
    if not isinstance(payload, dict):
        raise CommandValidationError("Kommando muss ein JSON-Objekt sein.")

    allowed = {"command", "name", "request_id"}
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise CommandValidationError(
            f"Unbekannte Kommandofelder: {', '.join(unexpected)}."
        )

    command = payload.get("command")
    if command not in {"save", "list", "status"}:
        raise CommandValidationError(
            "Feld 'command' muss 'save', 'list' oder 'status' sein."
        )

    request_id = payload.get("request_id")
    if request_id is not None and (
        not isinstance(request_id, str)
        or not _REQUEST_ID_RE.fullmatch(request_id)
    ):
        raise CommandValidationError(
            "request_id muss 1–64 sichere ASCII-Zeichen enthalten."
        )

    name = payload.get("name")
    if name is not None:
        try:
            name = validate_map_name(name)
        except MapValidationError as error:
            raise CommandValidationError(str(error)) from error
    if command == "status" and name is not None:
        raise CommandValidationError("'status' akzeptiert keinen Kartennamen.")

    return MapCommand(command=command, name=name, request_id=request_id)


@dataclass(frozen=True)
class SavedMap:
    name: str
    version: str
    path: Path
    saved_at: str
    width: int
    height: int
    resolution: float
    frame_id: str
    fingerprint: str
    durability_warning: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "path": str(self.path),
            "saved_at": self.saved_at,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "frame_id": self.frame_id,
            "fingerprint": self.fingerprint,
            "durability_warning": self.durability_warning,
        }


@dataclass(frozen=True)
class ListVersionsReport:
    records: tuple[SavedMap, ...]
    requested_limit: int
    candidate_count: int
    selected_candidate_count: int
    metadata_candidates_inspected: int
    artifact_candidates_reserved: int
    artifact_verification_bytes_reserved: int
    maximum_list_verify_bytes: int
    truncation_reasons: tuple[str, ...]

    @property
    def truncated(self) -> bool:
        return bool(self.truncation_reasons)

    def policy_dict(self) -> dict[str, Any]:
        return {
            "truncated": self.truncated,
            "truncation_reasons": list(self.truncation_reasons),
            "requested_limit": self.requested_limit,
            "candidate_count": self.candidate_count,
            "selected_candidate_count": self.selected_candidate_count,
            "metadata_candidates_inspected": self.metadata_candidates_inspected,
            "artifact_candidates_reserved": self.artifact_candidates_reserved,
            "artifact_verification_bytes_reserved": (
                self.artifact_verification_bytes_reserved
            ),
            "maximum_list_verify_bytes": self.maximum_list_verify_bytes,
        }


class _VerificationBudgetExceeded(RuntimeError):
    """Der nächste Kandidat passt nicht mehr in das Hash-I/O-Budget."""


@dataclass
class _VerificationBudget:
    maximum_bytes: int
    reserved_bytes: int = 0
    reserved_candidates: int = 0

    def reserve(self, byte_count: int) -> None:
        if byte_count > self.maximum_bytes - self.reserved_bytes:
            raise _VerificationBudgetExceeded
        self.reserved_bytes += byte_count
        self.reserved_candidates += 1


class MapRepository:
    """Unveränderliche, versionierte Kartenablage mit atomarem Commit."""

    def __init__(
        self,
        root: Path,
        *,
        default_name: str = "amadeus",
        policy: Optional[StoragePolicy] = None,
    ) -> None:
        root_path = Path(root).expanduser()
        if not root_path.is_absolute():
            raise MapStorageError("Speicherpfad muss absolut sein.")
        self.default_name = validate_map_name(default_name)
        self.policy = (policy or StoragePolicy()).validated()

        if root_path.is_symlink():
            raise MapStorageError("Speicherwurzel darf kein symbolischer Link sein.")
        self._create_storage_root_durably(root_path)
        if not root_path.is_dir() or root_path.is_symlink():
            raise MapStorageError("Speicherwurzel ist kein sicheres Verzeichnis.")
        self.root = root_path.resolve(strict=True)
        self.cleanup_removed = 0
        self.cleanup_errors = 0
        with self._exclusive_lock():
            self._cleanup_staging()

    def _create_storage_root_durably(self, root_path: Path) -> None:
        cursor = root_path
        try:
            while not cursor.exists():
                if cursor.parent == cursor:
                    raise MapStorageError(
                        "Kein existierender Vorfahr der Speicherwurzel gefunden."
                    )
                cursor = cursor.parent
            if not cursor.is_dir():
                raise MapStorageError(
                    "Existierender Vorfahr der Speicherwurzel ist "
                    "kein Verzeichnis."
                )
        except OSError as error:
            raise MapStorageError(
                f"Speicherpfad kann nicht geprüft werden: {error}."
            ) from error

        try:
            root_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError as error:
            raise MapStorageError(
                f"Speicherwurzel kann nicht angelegt werden: {error}."
            ) from error

        try:
            resolved_root = root_path.resolve(strict=True)
            root_device = resolved_root.stat().st_dev
        except OSError as error:
            raise MapStorageError(
                f"Speicherwurzel kann nach dem Anlegen nicht geprüft werden: {error}."
            ) from error

        # Die Prüfung läuft bei jedem Start, nicht nur unmittelbar nach mkdir.
        # Dadurch kann ein fehlgeschlagener fsync nicht dadurch umgangen
        # werden, dass die noch sichtbaren Verzeichnisse beim Retry bereits
        # existieren. Es wird ausschließlich bis zur Mountwurzel desselben
        # st_dev synchronisiert; ein übergeordnetes Dateisystem bleibt
        # unangetastet.
        parent = resolved_root.parent
        synced_parent = False
        while True:
            try:
                parent_status = parent.stat()
            except OSError as error:
                raise MapStorageError(
                    f"Elternkette der Speicherwurzel kann nicht geprüft "
                    f"werden: {parent}: {error}."
                ) from error
            if parent_status.st_dev != root_device:
                break
            try:
                self._sync_directory(parent)
            except OSError as error:
                raise MapStorageError(
                    "Durability-Prüfung der Speicherwurzel fehlgeschlagen; "
                    f"Eltern-fsync von {parent} war nicht möglich: {error}. "
                    "Saves bleiben deaktiviert."
                ) from error
            synced_parent = True
            if parent.parent == parent:
                break
            parent = parent.parent

        # Falls die Speicherwurzel selbst die Mountwurzel ist, existiert kein
        # Elternordner auf demselben st_dev. In diesem Sonderfall wird die
        # Mountwurzel selbst synchronisiert.
        if not synced_parent:
            try:
                self._sync_directory(resolved_root)
            except OSError as error:
                raise MapStorageError(
                    "Durability-Prüfung der Speicherwurzel fehlgeschlagen; "
                    f"Mountwurzel-fsync von {resolved_root} war nicht "
                    f"möglich: {error}. Saves bleiben deaktiviert."
                ) from error

    def save(
        self,
        snapshot: MapSnapshot,
        *,
        name: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> SavedMap:
        if not isinstance(snapshot, MapSnapshot):
            raise MapStorageError("Nur validierte MapSnapshot-Objekte dürfen gespeichert werden.")
        map_name = validate_map_name(name or self.default_name)
        with self._exclusive_lock():
            return self._save_locked(
                snapshot,
                map_name=map_name,
                now=now,
            )

    def _save_locked(
        self,
        snapshot: MapSnapshot,
        *,
        map_name: str,
        now: Optional[datetime],
    ) -> SavedMap:
        timestamp = self._utc_time(now)
        name_directory = self._safe_name_directory(map_name, create=False)
        estimated_bytes = 2 * len(snapshot.cells) + 64 * 1024
        self._enforce_save_policy(
            map_name,
            name_directory,
            timestamp=timestamp,
            estimated_bytes=estimated_bytes,
        )
        name_directory = self._safe_name_directory(map_name, create=True)

        version_base = (
            timestamp.strftime("%Y%m%dT%H%M%S%fZ")
            + "-"
            + snapshot.fingerprint[:12]
        )
        version = self._available_version(name_directory, version_base)
        destination = name_directory / version
        staging = name_directory / f".tmp-{uuid.uuid4().hex}"
        saved_at = timestamp.isoformat().replace("+00:00", "Z")

        try:
            staging.mkdir(mode=0o700)
            occupancy = snapshot.cells
            pgm = self._pgm_bytes(snapshot)
            yaml = self._yaml_text(snapshot).encode("utf-8")

            self._write_bytes(staging / "occupancy.bin", occupancy)
            self._write_bytes(staging / "map.pgm", pgm)
            self._write_bytes(staging / "map.yaml", yaml)

            files = {
                filename: {
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
                for filename, content in (
                    ("occupancy.bin", occupancy),
                    ("map.pgm", pgm),
                    ("map.yaml", yaml),
                )
            }
            metadata = {
                "schema_version": 1,
                "name": map_name,
                "version": version,
                "saved_at": saved_at,
                **snapshot.summary(),
                "cell_encoding": "signed-int8-row-major-from-map-origin",
                "files": files,
            }
            self._write_bytes(
                staging / "metadata.json",
                self._json_bytes(metadata, pretty=True),
            )
            self._sync_directory(staging)
            os.replace(staging, destination)
        except Exception as error:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            if isinstance(error, (MapStorageError, MapValidationError)):
                raise
            raise MapStorageError(
                f"Karte konnte nicht atomar gespeichert werden: {error}."
            ) from error

        durability_warnings: list[str] = []
        sync_targets = [
            (name_directory, "Kartenverzeichnis"),
            (self.root, "Speicherwurzel"),
        ]
        for sync_path, description in sync_targets:
            try:
                self._sync_directory(sync_path)
            except OSError as error:
                # Der atomare Commit ist bereits sichtbar und darf nicht als
                # fehlgeschlagener Save gemeldet oder erneut ausgeführt werden.
                durability_warnings.append(
                    f"{description} konnte nach dem atomaren Commit nicht "
                    f"synchronisiert werden: {error}."
                )
        durability_warning = (
            None
            if not durability_warnings
            else "Version ist atomar sichtbar, aber " + " ".join(
                durability_warnings
            )
        )

        return SavedMap(
            name=map_name,
            version=version,
            path=destination,
            saved_at=saved_at,
            width=snapshot.width,
            height=snapshot.height,
            resolution=snapshot.resolution,
            frame_id=snapshot.frame_id,
            fingerprint=snapshot.fingerprint,
            durability_warning=durability_warning,
        )

    def list_versions(
        self,
        *,
        name: Optional[str] = None,
        limit: int = 100,
    ) -> list[SavedMap]:
        return list(
            self.list_versions_with_report(
                name=name,
                limit=limit,
            ).records
        )

    def list_versions_with_report(
        self,
        *,
        name: Optional[str] = None,
        limit: int = 100,
    ) -> ListVersionsReport:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit <= 0
            or limit > MAXIMUM_LIST_ENTRIES
        ):
            raise MapStorageError(
                f"Listenlimit muss zwischen 1 und {MAXIMUM_LIST_ENTRIES} liegen."
            )
        names = [validate_map_name(name)] if name is not None else self._map_names()
        verification_limit = min(MAXIMUM_LIST_ENTRIES, max(limit, limit * 2))
        candidate_heap: list[tuple[str, str, Path]] = []
        candidate_count = 0
        for map_name in names:
            directory = self._safe_name_directory(map_name, create=False)
            if not directory.exists():
                continue
            try:
                for child in directory.iterdir():
                    if (
                        child.is_symlink()
                        or not child.is_dir()
                        or not _VERSION_RE.fullmatch(child.name)
                    ):
                        continue
                    candidate_count += 1
                    candidate = (child.name, map_name, child)
                    if len(candidate_heap) < verification_limit:
                        heapq.heappush(candidate_heap, candidate)
                    elif candidate[:2] > candidate_heap[0][:2]:
                        heapq.heapreplace(candidate_heap, candidate)
            except OSError as error:
                raise MapStorageError(
                    f"Kartenverzeichnis kann nicht gelesen werden: {error}."
                ) from error

        # Prüfsummen sind die teure Arbeit. Selbst bei sehr vielen Altständen
        # werden nur die begrenzt vielen jüngsten Verzeichnisse geöffnet.
        newest = sorted(
            candidate_heap,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        budget = _VerificationBudget(
            self.policy.maximum_list_verify_bytes
        )
        records: list[SavedMap] = []
        metadata_candidates_inspected = 0
        budget_exhausted = False
        for _version, map_name, child in newest:
            metadata_candidates_inspected += 1
            try:
                record = self._read_record(
                    map_name,
                    child,
                    verification_budget=budget,
                )
            except _VerificationBudgetExceeded:
                budget_exhausted = True
                break
            if record is not None:
                records.append(record)
                if len(records) >= limit:
                    break
        records.sort(key=lambda item: (item.saved_at, item.version), reverse=True)
        reasons: list[str] = []
        if budget_exhausted:
            reasons.append("verification_byte_budget")
        if candidate_count > len(candidate_heap):
            reasons.append("candidate_verification_window")
        if (
            len(records) >= limit
            and candidate_count > metadata_candidates_inspected
        ):
            reasons.append("requested_entry_limit")
        return ListVersionsReport(
            records=tuple(records),
            requested_limit=limit,
            candidate_count=candidate_count,
            selected_candidate_count=len(candidate_heap),
            metadata_candidates_inspected=metadata_candidates_inspected,
            artifact_candidates_reserved=budget.reserved_candidates,
            artifact_verification_bytes_reserved=budget.reserved_bytes,
            maximum_list_verify_bytes=budget.maximum_bytes,
            truncation_reasons=tuple(reasons),
        )

    def _enforce_save_policy(
        self,
        map_name: str,
        name_directory: Path,
        *,
        timestamp: datetime,
        estimated_bytes: int,
    ) -> None:
        existing_names = self._map_names()
        if (
            not name_directory.exists()
            and map_name not in existing_names
            and len(existing_names) >= self.policy.maximum_map_names
        ):
            raise SaveProtectionError(
                "Maximale Zahl unterschiedlicher Kartennamen ist erreicht "
                f"({self.policy.maximum_map_names})."
            )

        versions = self._version_names(name_directory)
        if len(versions) >= self.policy.maximum_versions_per_map:
            raise SaveProtectionError(
                f"Karte '{map_name}' besitzt bereits das Versionslimit "
                f"{self.policy.maximum_versions_per_map}."
            )

        latest_time: Optional[datetime] = None
        for existing_name in existing_names:
            candidate_versions = (
                versions
                if existing_name == map_name
                else self._version_names(self.root / existing_name)
            )
            if not candidate_versions:
                continue
            candidate_time = self._version_time(candidate_versions[-1])
            if latest_time is None or candidate_time > latest_time:
                latest_time = candidate_time
        if latest_time is not None:
            elapsed = (timestamp - latest_time).total_seconds()
            if elapsed < self.policy.minimum_save_interval_s:
                remaining = self.policy.minimum_save_interval_s - elapsed
                raise SaveProtectionError(
                    "Globaler Mindestabstand zwischen Speicherungen ist noch nicht "
                    f"erreicht ({remaining:.3f} s verbleibend)."
                )

        total_bytes = self._total_storage_bytes()
        if (
            total_bytes + estimated_bytes
            > self.policy.maximum_total_storage_bytes
        ):
            raise SaveProtectionError(
                "Konfiguriertes Gesamtlimit der Kartenablage würde "
                f"überschritten ({self.policy.maximum_total_storage_bytes} Bytes)."
            )

        try:
            free_bytes = shutil.disk_usage(self.root).free
        except OSError as error:
            raise MapStorageError(
                f"Freier Speicherplatz konnte nicht ermittelt werden: {error}."
            ) from error
        if (
            free_bytes - estimated_bytes
            < self.policy.minimum_free_space_bytes
        ):
            raise SaveProtectionError(
                "Konfigurierter Mindestfreiraum würde unterschritten "
                f"({self.policy.minimum_free_space_bytes} Bytes)."
            )

    def _version_names(self, directory: Path) -> list[str]:
        if not directory.exists():
            return []
        versions: list[str] = []
        try:
            children = directory.iterdir()
            for child in children:
                if (
                    child.is_symlink()
                    or not child.is_dir()
                    or not _VERSION_RE.fullmatch(child.name)
                ):
                    continue
                versions.append(child.name)
        except OSError as error:
            raise MapStorageError(
                f"Kartenverzeichnis kann nicht gelesen werden: {error}."
            ) from error
        return sorted(versions)

    @staticmethod
    def _version_time(version: str) -> datetime:
        try:
            return datetime.strptime(
                version[:22],
                "%Y%m%dT%H%M%S%fZ",
            ).replace(tzinfo=timezone.utc)
        except ValueError as error:
            raise MapStorageError(
                f"Ungültiger interner Versionszeitstempel: {version}."
            ) from error

    def _total_storage_bytes(self) -> int:
        total = 0

        def raise_walk_error(error: OSError) -> None:
            raise error

        try:
            for current, directory_names, file_names in os.walk(
                self.root,
                topdown=True,
                onerror=raise_walk_error,
                followlinks=False,
            ):
                current_path = Path(current)
                safe_directories: list[str] = []
                for directory_name in directory_names:
                    candidate = current_path / directory_name
                    mode = candidate.lstat().st_mode
                    if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
                        safe_directories.append(directory_name)
                directory_names[:] = safe_directories
                for file_name in file_names:
                    candidate = current_path / file_name
                    file_status = os.stat(candidate, follow_symlinks=False)
                    if stat.S_ISREG(file_status.st_mode):
                        total += file_status.st_size
        except OSError as error:
            raise MapStorageError(
                f"Größe der Kartenablage kann nicht ermittelt werden: {error}."
            ) from error
        return total

    def _cleanup_staging(self) -> None:
        maximum = self.policy.staging_cleanup_max_entries
        if maximum == 0:
            return
        cutoff = time.time() - self.policy.staging_cleanup_min_age_s
        candidates: list[tuple[float, str, str]] = []
        try:
            names = self._map_names()
        except MapStorageError:
            self.cleanup_errors += 1
            return
        for map_name in names:
            name_directory = self.root / map_name
            flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                flags |= os.O_DIRECTORY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                name_descriptor = os.open(name_directory, flags)
                try:
                    child_names = os.listdir(name_descriptor)
                    for child_name in child_names:
                        if not _STAGING_RE.fullmatch(child_name):
                            continue
                        child_status = os.stat(
                            child_name,
                            dir_fd=name_descriptor,
                            follow_symlinks=False,
                        )
                        if (
                            stat.S_ISLNK(child_status.st_mode)
                            or not stat.S_ISDIR(child_status.st_mode)
                            or child_status.st_mtime > cutoff
                        ):
                            continue
                        candidates.append(
                            (child_status.st_mtime, map_name, child_name)
                        )
                finally:
                    os.close(name_descriptor)
            except OSError:
                self.cleanup_errors += 1

        for _modified, map_name, child_name in sorted(candidates)[:maximum]:
            name_directory = self.root / map_name
            flags = os.O_RDONLY
            if hasattr(os, "O_DIRECTORY"):
                flags |= os.O_DIRECTORY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                if (
                    not _MAP_NAME_RE.fullmatch(map_name)
                    or not _STAGING_RE.fullmatch(child_name)
                ):
                    continue
                name_descriptor = os.open(name_directory, flags)
                try:
                    candidate_status = os.stat(
                        child_name,
                        dir_fd=name_descriptor,
                        follow_symlinks=False,
                    )
                    if (
                        stat.S_ISLNK(candidate_status.st_mode)
                        or not stat.S_ISDIR(candidate_status.st_mode)
                        or candidate_status.st_mtime > cutoff
                    ):
                        continue
                    if self._remove_owned_staging(
                        name_descriptor,
                        child_name,
                    ):
                        self.cleanup_removed += 1
                    else:
                        self.cleanup_errors += 1
                finally:
                    os.close(name_descriptor)
            except OSError:
                self.cleanup_errors += 1

    @staticmethod
    def _remove_owned_staging(
        parent_descriptor: int,
        name: str,
    ) -> bool:
        """Löscht nur die flache, exakt bekannte Struktur eigener Stagings."""

        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        staging_descriptor = os.open(
            name,
            flags,
            dir_fd=parent_descriptor,
        )
        try:
            artifact_names = os.listdir(staging_descriptor)
            if any(
                artifact_name not in _STAGING_ARTIFACTS
                for artifact_name in artifact_names
            ):
                return False
            for artifact_name in artifact_names:
                artifact_status = os.stat(
                    artifact_name,
                    dir_fd=staging_descriptor,
                    follow_symlinks=False,
                )
                if not stat.S_ISREG(artifact_status.st_mode):
                    return False
            for artifact_name in artifact_names:
                os.unlink(artifact_name, dir_fd=staging_descriptor)
        finally:
            os.close(staging_descriptor)
        os.rmdir(name, dir_fd=parent_descriptor)
        return True

    def _safe_name_directory(self, name: str, *, create: bool) -> Path:
        clean_name = validate_map_name(name)
        candidate = self.root / clean_name
        if candidate.parent != self.root:
            raise MapStorageError("Kartenpfad verlässt die Speicherwurzel.")
        try:
            if candidate.is_symlink():
                raise MapStorageError(
                    "Kartenverzeichnis darf kein symbolischer Link sein."
                )
            if create:
                candidate.mkdir(exist_ok=True, mode=0o700)
            if candidate.exists() and (
                not candidate.is_dir()
                or candidate.is_symlink()
            ):
                raise MapStorageError(
                    "Kartenpfad ist kein sicheres Verzeichnis."
                )
        except OSError as error:
            raise MapStorageError(
                f"Kartenverzeichnis kann nicht geprüft/angelegt werden: {error}."
            ) from error
        return candidate

    def _map_names(self) -> list[str]:
        names: list[str] = []
        try:
            for child in self.root.iterdir():
                if (
                    child.is_symlink()
                    or not child.is_dir()
                    or not _MAP_NAME_RE.fullmatch(child.name)
                ):
                    continue
                names.append(child.name)
        except OSError as error:
            raise MapStorageError(
                f"Speicherwurzel kann nicht gelesen werden: {error}."
            ) from error
        return sorted(names)

    def _read_record(
        self,
        name: str,
        version_directory: Path,
        *,
        verification_budget: Optional[_VerificationBudget] = None,
    ) -> Optional[SavedMap]:
        metadata_path = version_directory / "metadata.json"
        try:
            if (
                metadata_path.is_symlink()
                or not metadata_path.is_file()
                or metadata_path.stat().st_size > MAXIMUM_METADATA_BYTES
            ):
                return None
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            if payload.get("name") != name or payload.get("version") != version_directory.name:
                return None
            width = payload["width"]
            height = payload["height"]
            resolution = payload["resolution"]
            frame_id = payload["frame_id"]
            fingerprint = payload["fingerprint"]
            saved_at = payload["saved_at"]
            files = payload["files"]
            expected_saved_at = (
                self._version_time(version_directory.name)
                .isoformat()
                .replace("+00:00", "Z")
            )
            if (
                isinstance(width, bool)
                or not isinstance(width, int)
                or isinstance(height, bool)
                or not isinstance(height, int)
                or width <= 0
                or height <= 0
                or width > MAXIMUM_DIMENSION
                or height > MAXIMUM_DIMENSION
                or width * height > MAXIMUM_CELL_COUNT
                or isinstance(resolution, bool)
                or not isinstance(resolution, (int, float))
                or not math.isfinite(float(resolution))
                or float(resolution) <= 0.0
                or not isinstance(frame_id, str)
                or not frame_id.strip()
                or len(frame_id) > 128
                or not isinstance(fingerprint, str)
                or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)
                or not isinstance(saved_at, str)
                or saved_at != expected_saved_at
                or not isinstance(files, dict)
            ):
                return None
            artifact_limits = {
                "occupancy.bin": MAXIMUM_CELL_COUNT,
                "map.pgm": MAXIMUM_CELL_COUNT + 4096,
                "map.yaml": 64 * 1024,
            }
            artifact_descriptors: list[tuple[str, int, str]] = []
            for filename, maximum_size in artifact_limits.items():
                descriptor = files.get(filename)
                if (
                    not isinstance(descriptor, dict)
                    or isinstance(descriptor.get("bytes"), bool)
                    or not isinstance(descriptor.get("bytes"), int)
                    or descriptor["bytes"] < 0
                    or descriptor["bytes"] > maximum_size
                    or (
                        filename == "occupancy.bin"
                        and descriptor["bytes"] != width * height
                    )
                    or not isinstance(descriptor.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"])
                ):
                    return None
                artifact_descriptors.append(
                    (
                        filename,
                        descriptor["bytes"],
                        descriptor["sha256"],
                    )
                )
            if verification_budget is not None:
                verification_budget.reserve(
                    sum(
                        expected_size
                        for _filename, expected_size, _digest
                        in artifact_descriptors
                    )
                )
            for filename, expected_size, expected_sha256 in artifact_descriptors:
                if not self._verify_artifact(
                    version_directory / filename,
                    expected_size=expected_size,
                    expected_sha256=expected_sha256,
                ):
                    return None
            return SavedMap(
                name=name,
                version=version_directory.name,
                path=version_directory,
                saved_at=saved_at,
                width=width,
                height=height,
                resolution=float(resolution),
                frame_id=frame_id,
                fingerprint=fingerprint,
            )
        except (
            OSError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            MapStorageError,
        ):
            return None

    @staticmethod
    def _verify_artifact(
        path: Path,
        *,
        expected_size: int,
        expected_sha256: str,
    ) -> bool:
        if path.is_symlink() or not path.is_file():
            return False
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb") as stream:
                initial_status = os.fstat(stream.fileno())
                if initial_status.st_size != expected_size:
                    return False
                digest = hashlib.sha256()
                remaining = expected_size
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk:
                        return False
                    digest.update(chunk)
                    remaining -= len(chunk)
                final_status = os.fstat(stream.fileno())
                if final_status.st_size != expected_size:
                    return False
            return digest.hexdigest() == expected_sha256
        except OSError:
            return False

    @staticmethod
    def _utc_time(now: Optional[datetime]) -> datetime:
        value = datetime.now(timezone.utc) if now is None else now
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _available_version(directory: Path, base: str) -> str:
        if not (directory / base).exists():
            return base
        for suffix in range(1, 100):
            candidate = f"{base}-{suffix:02d}"
            if not (directory / candidate).exists():
                return candidate
        raise MapStorageError("Zu viele Karten wurden im selben Zeitstempel gespeichert.")

    @staticmethod
    def _pgm_bytes(snapshot: MapSnapshot) -> bytes:
        header = (
            "P5\n"
            "# atomar gespeichert durch robot_map_manager\n"
            f"{snapshot.width} {snapshot.height}\n"
            "255\n"
        ).encode("ascii")
        pixels = bytearray(snapshot.width * snapshot.height)
        offset = 0
        for image_y in range(snapshot.height):
            source_y = snapshot.height - 1 - image_y
            row_start = source_y * snapshot.width
            for x in range(snapshot.width):
                occupancy = snapshot.cells[row_start + x]
                if occupancy == 255:
                    pixel = 205
                else:
                    pixel = ((100 - occupancy) * 254 + 50) // 100
                pixels[offset] = pixel
                offset += 1
        return header + bytes(pixels)

    @staticmethod
    def _yaml_text(snapshot: MapSnapshot) -> str:
        return (
            "image: map.pgm\n"
            f"resolution: {snapshot.resolution:.17g}\n"
            "origin: "
            f"[{snapshot.origin.position_x:.17g}, "
            f"{snapshot.origin.position_y:.17g}, "
            f"{snapshot.origin.yaw:.17g}]\n"
            "negate: 0\n"
            "occupied_thresh: 0.65\n"
            "free_thresh: 0.196\n"
            "mode: trinary\n"
        )

    @staticmethod
    def _json_bytes(payload: dict[str, Any], *, pretty: bool = False) -> bytes:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
            allow_nan=False,
        )
        return (text + ("\n" if pretty else "")).encode("utf-8")

    @contextmanager
    def _exclusive_lock(self):
        lock_path = self.root / ".repository.lock"
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
            lock_status = os.fstat(descriptor)
            if not stat.S_ISREG(lock_status.st_mode):
                raise OSError("Lockpfad ist keine reguläre Datei")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError as error:
            if "descriptor" in locals():
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise MapStorageError(
                f"Exklusiver Repository-Lock kann nicht gesetzt werden: {error}."
            ) from error
        try:
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                # Policy und Commit sind bereits abgeschlossen. Ein Unlock-
                # Fehler darf deshalb keinen erfolgreichen Save umdeuten;
                # close() gibt den flock unter POSIX ebenfalls frei.
                pass
            try:
                os.close(descriptor)
            except OSError:
                pass

    def _write_bytes(self, path: Path, content: bytes) -> None:
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise MapStorageError(
                f"Datei {path.name} konnte nicht geschrieben werden: {error}."
            ) from error

    @staticmethod
    def _sync_directory(path: Path) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def json_message(payload: dict[str, Any]) -> str:
    """Serialisiert Statusdaten strikt ohne NaN/Infinity."""

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
