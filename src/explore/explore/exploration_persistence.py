"""Versioned, map-bound persistence for passive WE exploration state.

This module stores no map cells and no semantic/manual room data.  It accepts
only a validated robot_map_manager version binding and makes one immutable JSON
revision visible at a time by atomic rename.  Loading is passive: it returns
data but cannot create a navigation intent or authorize motion.
"""

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets


class ExplorationPersistenceError(ValueError):
    """Stored data or its map-manager binding is unavailable or invalid."""


_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_FINGERPRINT = re.compile(r"[0-9a-f]{64}\Z")
_STATE_FILE = re.compile(r"state-([0-9]{8})\.json\Z")


def _safe_id(value, name):
    if not isinstance(value, str) or _SAFE_ID.fullmatch(value) is None:
        raise ExplorationPersistenceError(f"{name} ist ungueltig")
    return value


def _positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExplorationPersistenceError(
            f"{name} muss eine positive Ganzzahl sein")
    return value


def _positive_float(value, name):
    if (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(float(value)) or float(value) <= 0.0):
        raise ExplorationPersistenceError(
            f"{name} muss endlich und positiv sein")
    return float(value)


@dataclass(frozen=True)
class MapVersionBinding:
    name: str
    version: str
    fingerprint: str
    width: int
    height: int
    resolution: float
    frame_id: str

    def __post_init__(self):
        _safe_id(self.name, "name")
        _safe_id(self.version, "version")
        if not isinstance(self.fingerprint, str) or _FINGERPRINT.fullmatch(
                self.fingerprint) is None:
            raise ExplorationPersistenceError("fingerprint ist ungueltig")
        _positive_int(self.width, "width")
        _positive_int(self.height, "height")
        object.__setattr__(
            self, "resolution", _positive_float(self.resolution, "resolution"))
        _safe_id(self.frame_id, "frame_id")

    def as_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "fingerprint": self.fingerprint,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "frame_id": self.frame_id,
        }


def binding_from_map_manager_status(
        serialized: str, *, maximum_age_seconds: float = 2.0,
        require_successful_save_event: bool = False) -> MapVersionBinding:
    """Extract one exact current saved-map binding from a fresh status."""
    limit = _positive_float(maximum_age_seconds, "maximum_age_seconds")
    if not isinstance(serialized, str) or len(serialized.encode("utf-8")) > (
            1_048_576):
        raise ExplorationPersistenceError("Kartenmanagerstatus ist zu gross")
    try:
        root = json.loads(serialized)
        if not isinstance(root, dict) or root.get("schema_version") != 1:
            raise ExplorationPersistenceError(
                "Kartenmanagerstatus besitzt kein bekanntes Schema")
        if require_successful_save_event and not (
                root.get("event") == "save_result" and root.get("ok") is True):
            raise ExplorationPersistenceError(
                "WE-Speicherung braucht ein erfolgreiches save_result")
        map_data = root["map"]
        summary = map_data["summary"]
        saved = (
            root.get("saved") if require_successful_save_event
            else root["storage"]["last_saved"])
        if not isinstance(saved, dict):
            raise ExplorationPersistenceError(
                "Kartenmanager meldet keine gespeicherte Version")
        age = map_data["age_seconds"]
        if (
                isinstance(age, bool) or not isinstance(age, (int, float))
                or not math.isfinite(float(age)) or not 0.0 <= age <= limit):
            raise ExplorationPersistenceError(
                "Kartenmanagerstatus ist nicht frisch")
        binding = MapVersionBinding(
            name=saved["name"], version=saved["version"],
            fingerprint=saved["fingerprint"], width=saved["width"],
            height=saved["height"], resolution=saved["resolution"],
            frame_id=saved["frame_id"],
        )
        current = MapVersionBinding(
            name=binding.name, version=binding.version,
            fingerprint=summary["fingerprint"], width=summary["width"],
            height=summary["height"], resolution=summary["resolution"],
            frame_id=summary["frame_id"],
        )
    except ExplorationPersistenceError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ExplorationPersistenceError(
            "Kartenmanagerstatus ist unvollstaendig oder ungueltig") from error
    if current != binding:
        raise ExplorationPersistenceError(
            "Gespeicherte Version passt nicht zur aktuellen Karte")
    return binding


@dataclass(frozen=True)
class LoadedExplorationState:
    binding: MapVersionBinding
    sequence: int
    state: dict
    path: Path


class ExplorationStateRepository:
    """Small immutable WE metadata repository with old-valid fallback."""

    def __init__(
            self, root: Path, *, maximum_document_bytes: int = 4_194_304,
            maximum_versions: int = 64):
        if not isinstance(root, Path) or not root.is_absolute():
            raise ExplorationPersistenceError(
                "WE-Speicherwurzel muss ein absoluter Path sein")
        self.root = root
        self.maximum_document_bytes = _positive_int(
            maximum_document_bytes, "maximum_document_bytes")
        self.maximum_versions = _positive_int(
            maximum_versions, "maximum_versions")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or not self.root.is_dir():
            raise ExplorationPersistenceError(
                "WE-Speicherwurzel ist kein sicheres Verzeichnis")

    def save(self, binding: MapVersionBinding, state: dict) -> Path:
        if not isinstance(binding, MapVersionBinding):
            raise ExplorationPersistenceError(
                "binding muss MapVersionBinding sein")
        if not isinstance(state, dict):
            raise ExplorationPersistenceError("state muss ein Objekt sein")
        directory = self._directory(binding)
        map_directory = directory.parent
        map_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if map_directory.is_symlink():
            raise ExplorationPersistenceError(
                "WE-Kartenverzeichnis darf kein Symlink sein")
        directory.mkdir(exist_ok=True, mode=0o700)
        if directory.is_symlink():
            raise ExplorationPersistenceError(
                "WE-Versionsverzeichnis darf kein Symlink sein")
        existing = self._state_files(directory)
        if existing:
            try:
                latest = self._load_file(
                    existing[-1][1], binding, existing[-1][0])
            except ExplorationPersistenceError:
                latest = None
            if latest is not None and latest.state == state:
                return latest.path
        if len(existing) >= self.maximum_versions:
            raise ExplorationPersistenceError(
                "WE-Speicher hat seine Versionsgrenze erreicht")
        sequence = 1 if not existing else existing[-1][0] + 1
        document = {
            "schema_version": 1,
            "sequence": sequence,
            "map_binding": binding.as_dict(),
            "manual_room_data": "external_preserved",
            "state": state,
            "state_sha256": hashlib.sha256(json.dumps(
                state, ensure_ascii=True, sort_keys=True,
                separators=(",", ":"), allow_nan=False
            ).encode("utf-8")).hexdigest(),
        }
        encoded = json.dumps(
            document, ensure_ascii=True, sort_keys=True,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > self.maximum_document_bytes:
            raise ExplorationPersistenceError("WE-Zustandsdokument ist zu gross")
        target = directory / f"state-{sequence:08d}.json"
        temporary = directory / f".tmp-{secrets.token_hex(16)}"
        try:
            fd = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                raise
            try:
                os.link(temporary, target, follow_symlinks=False)
            except FileExistsError as error:
                raise ExplorationPersistenceError(
                    "WE-Zustandsrevision existiert bereits") from error
            self._fsync_directory(directory)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return target

    def load(self, binding: MapVersionBinding) -> LoadedExplorationState:
        if not isinstance(binding, MapVersionBinding):
            raise ExplorationPersistenceError(
                "binding muss MapVersionBinding sein")
        directory = self._directory(binding)
        errors = []
        for sequence, path in reversed(self._state_files(directory)):
            try:
                loaded = self._load_file(path, binding, sequence)
            except ExplorationPersistenceError as error:
                errors.append(str(error))
                continue
            return loaded
        detail = errors[0] if errors else "keine gespeicherte WE-Version"
        raise ExplorationPersistenceError(
            f"Kein gueltiger WE-Zustand fuer die Kartenbindung: {detail}")

    def _load_file(self, path, binding, sequence):
        try:
            size = path.stat().st_size
            if size <= 0 or size > self.maximum_document_bytes:
                raise ExplorationPersistenceError(
                    "WE-Zustandsdatei besitzt eine ungueltige Groesse")
            if path.is_symlink():
                raise ExplorationPersistenceError(
                    "WE-Zustandsdatei darf kein Symlink sein")
            root = json.loads(path.read_text(encoding="utf-8"))
            if (
                    not isinstance(root, dict)
                    or root.get("schema_version") != 1
                    or root.get("sequence") != sequence
                    or root.get("manual_room_data") != "external_preserved"):
                raise ExplorationPersistenceError(
                    "WE-Zustandsdatei besitzt kein bekanntes Schema")
            stored = MapVersionBinding(**root["map_binding"])
            if stored != binding:
                raise ExplorationPersistenceError(
                    "WE-Zustand passt nicht zu Fingerprint oder Geometrie")
            state = root["state"]
            if not isinstance(state, dict):
                raise ExplorationPersistenceError(
                    "WE-Zustand ist kein Objekt")
            checksum = hashlib.sha256(json.dumps(
                state, ensure_ascii=True, sort_keys=True,
                separators=(",", ":"), allow_nan=False
            ).encode("utf-8")).hexdigest()
            if root.get("state_sha256") != checksum:
                raise ExplorationPersistenceError(
                    "WE-Zustandsdatei besitzt eine falsche Pruefsumme")
        except ExplorationPersistenceError:
            raise
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ExplorationPersistenceError(
                "WE-Zustandsdatei ist beschaedigt") from error
        return LoadedExplorationState(binding, sequence, state, path)

    def _directory(self, binding):
        directory = self.root / binding.name / binding.version
        root = self.root.resolve()
        if root not in directory.resolve().parents:
            raise ExplorationPersistenceError(
                "WE-Versionsverzeichnis verlaesst die Speicherwurzel")
        return directory

    def _state_files(self, directory):
        if not directory.is_dir() or directory.is_symlink():
            return []
        result = []
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise ExplorationPersistenceError(
                "WE-Versionsverzeichnis kann nicht gelesen werden") from error
        for path in children[: self.maximum_versions * 4]:
            match = _STATE_FILE.fullmatch(path.name)
            if match is not None and path.is_file() and not path.is_symlink():
                result.append((int(match.group(1)), path))
        return sorted(result)

    @staticmethod
    def _fsync_directory(directory):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
