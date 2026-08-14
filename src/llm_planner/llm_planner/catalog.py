"""Strict, ROS-independent parsing for Amadeus' semantic catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable


MAXIMUM_CATALOG_BYTES = 512 * 1024
MAXIMUM_ITEMS_PER_FIELD = 256
MAXIMUM_NAME_CHARACTERS = 80


class CatalogValidationError(ValueError):
    """The dynamic catalog is malformed or exceeds its resource bounds."""


@dataclass(frozen=True)
class CatalogSnapshot:
    rooms: tuple[str, ...]
    targets: tuple[str, ...]
    objects: tuple[str, ...]


def _validate_existing(values: Iterable[str], field: str) -> tuple[str, ...]:
    return _normalize_names(list(values), field)


def _normalize_names(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CatalogValidationError(f"{field} muss eine Liste sein.")
    if not value:
        raise CatalogValidationError(f"{field} darf die bestehende Liste nicht leeren.")
    if len(value) > MAXIMUM_ITEMS_PER_FIELD:
        raise CatalogValidationError(
            f"{field} enthaelt mehr als {MAXIMUM_ITEMS_PER_FIELD} Eintraege."
        )

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        # Der semantische Kartenmanager darf fuer Diagnosezwecke zusaetzlich
        # Raumobjekte ausgeben. Fuer den Sprachplaner ist nur deren Name relevant.
        if isinstance(item, dict) and field == "rooms":
            item = item.get("name")
        if not isinstance(item, str):
            raise CatalogValidationError(f"{field} enthaelt einen ungueltigen Namen.")
        clean = item.strip()
        if not clean or len(clean) > MAXIMUM_NAME_CHARACTERS:
            raise CatalogValidationError(f"{field} enthaelt einen ungueltigen Namen.")
        if any(ord(character) < 32 or ord(character) == 127 for character in clean):
            raise CatalogValidationError(f"{field} enthaelt Steuerzeichen.")
        key = clean.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(clean)
    if not normalized:
        raise CatalogValidationError(f"{field} enthaelt keine verwendbaren Namen.")
    return tuple(normalized)


def merge_catalog_json(
    text: Any,
    *,
    rooms: Iterable[str],
    targets: Iterable[str],
    objects: Iterable[str],
) -> CatalogSnapshot:
    """Merge a bounded partial JSON catalog without erasing safe fallbacks."""

    if not isinstance(text, str):
        raise CatalogValidationError("Katalog muss als JSON-Zeichenkette ankommen.")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise CatalogValidationError("Katalog enthaelt ungueltiges Unicode.") from error
    if encoded_size > MAXIMUM_CATALOG_BYTES:
        raise CatalogValidationError("Katalog ist zu gross.")
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise CatalogValidationError("Katalog enthaelt kein gueltiges JSON.") from error
    if not isinstance(payload, dict):
        raise CatalogValidationError("Katalog muss ein JSON-Objekt sein.")
    if payload.get("schema_version") != 1:
        raise CatalogValidationError("Katalog hat keine unterstuetzte schema_version.")
    if payload.get("source") != "semantic_map_manager":
        raise CatalogValidationError(
            "Katalog stammt nicht vom semantic_map_manager."
        )
    if "ok" in payload and payload.get("ok") is not True:
        raise CatalogValidationError("Katalog ist nicht freigegeben (ok != true).")

    current = {
        "rooms": _validate_existing(rooms, "rooms"),
        "targets": _validate_existing(targets, "targets"),
        "objects": _validate_existing(objects, "objects"),
    }
    if "targets" in payload or "objects" in payload:
        raise CatalogValidationError(
            "Semantik-Katalog darf nur die Raumliste aktualisieren."
        )
    if "rooms" not in payload:
        raise CatalogValidationError("Semantik-Katalog enthaelt keine Raumliste.")
    merged: dict[str, tuple[str, ...]] = dict(current)
    if payload["rooms"] == []:
        merged["rooms"] = current["rooms"]
    else:
        merged["rooms"] = _normalize_names(payload["rooms"], "rooms")
    return CatalogSnapshot(
        rooms=merged["rooms"],
        targets=merged["targets"],
        objects=merged["objects"],
    )
