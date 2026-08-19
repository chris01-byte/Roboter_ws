"""Strict parser for the optional semantic catalog topic."""

import json
from typing import Any, Dict, List, Optional, Tuple


MAXIMUM_CATALOG_BYTES = 512 * 1024
MAXIMUM_ENTRIES_PER_SECTION = 256
MAXIMUM_NAME_CHARACTERS = 80


def _entry_name(entry: Any, section: str) -> Optional[str]:
    if isinstance(entry, str):
        value = entry.strip()
        return value or None
    if isinstance(entry, dict):
        candidates = ('name', 'class_name') if section == 'objects' else ('name',)
        for key in candidates:
            candidate = entry.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
    return None


def _normalise_entries(entries: Any, section: str) -> Tuple[Optional[List[str]], Optional[str]]:
    if not isinstance(entries, list):
        return None, f'{section} muss eine Liste sein'
    if len(entries) > MAXIMUM_ENTRIES_PER_SECTION:
        return None, (
            f'{section} enthaelt mehr als '
            f'{MAXIMUM_ENTRIES_PER_SECTION} Eintraege')
    result = []
    seen = set()
    for index, entry in enumerate(entries):
        name = _entry_name(entry, section)
        if name is None:
            return None, f'{section}[{index}] hat keinen gueltigen Namen'
        if (
                len(name) > MAXIMUM_NAME_CHARACTERS
                or any(ord(character) < 32 or ord(character) == 127
                       for character in name)):
            return None, f'{section}[{index}] hat einen ungueltigen Namen'
        folded = name.casefold()
        if folded not in seen:
            result.append(name)
            seen.add(folded)
    return result, None


def decode_catalog_payload(data: str) -> Tuple[Optional[Dict[str, List[str]]], Optional[str]]:
    """Return only present, fully valid catalog sections.

    Empty lists are ignored so a publisher startup/error state cannot erase
    the configured fallback.  If ``ok`` is present it must be true, so an
    unavailable semantic source cannot replace the last valid catalog with
    misleading data.
    """
    if not isinstance(data, str):
        return None, 'Semantik-Katalog muss Text sein'
    try:
        encoded_size = len(data.encode('utf-8'))
    except UnicodeError:
        return None, 'Semantik-Katalog enthaelt ungueltiges Unicode'
    if encoded_size > MAXIMUM_CATALOG_BYTES:
        return None, (
            f'Semantik-Katalog ist groesser als '
            f'{MAXIMUM_CATALOG_BYTES} Bytes')
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, TypeError, RecursionError) as exc:
        return None, f'Ungueltiger Semantik-Katalog: {exc}'
    if not isinstance(payload, dict):
        return None, 'Semantik-Katalog muss ein JSON-Objekt sein'
    if payload.get('schema_version') != 1:
        return None, 'Semantik-Katalog hat keine unterstuetzte schema_version'
    if payload.get('source') != 'semantic_map_manager':
        return None, 'Semantik-Katalog stammt nicht vom semantic_map_manager'
    if 'ok' in payload and payload.get('ok') is not True:
        return None, 'Semantik-Katalog ist nicht freigegeben (ok != true)'

    # Dieser Topic-Vertrag gehoert ausschliesslich dem semantic_map_manager.
    # Reale Objekte und Ablageziele bleiben in ihrer statischen, geprueften
    # Allowlist und duerfen nicht ueber eine offene Topic-Nachricht erweitert
    # werden.
    if 'objects' in payload or 'targets' in payload:
        return None, 'Semantik-Katalog darf nur die Raumliste aktualisieren'
    if 'rooms' not in payload:
        return None, 'Semantik-Katalog enthaelt keine Raumliste'
    entries, error = _normalise_entries(payload['rooms'], 'rooms')
    if error is not None:
        return None, error
    if entries is None:
        return None, 'Semantik-Katalog enthaelt keine lesbare Raumliste'
    return {'rooms': entries}, None
