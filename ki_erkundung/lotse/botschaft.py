"""Frage und Antwort für die Übertragung zwischen Roboter und KI-Rechner packen.

Der Roboter bereitet die Frage vor (Fotos mit Nummern, Skizze, Text) und
schickt sie als eine Nachricht an den Lotsen-Dienst auf dem KI-Rechner. Der
Dienst fragt dort Ollama und schickt die Rohantwort zurück. Geprüft wird die
Antwort wieder auf dem Roboter (``antwort.pruefe``).

Reines Python ohne ROS; das Format ist JSON-Text und damit von der Art der
Verbindung unabhängig.
"""
from __future__ import annotations

import base64
import binascii
import json
from typing import List, Optional, Sequence, Tuple

from . import SCHEMA_VERSION
from .frage import Frage
from .ki_rechner import Rohantwort

MAX_BILDER = 12
MAX_BILD_BYTES = 3_000_000
MAX_ZEITGRENZE_S = 300.0


def packe_frage(frage_id: str, frage: Frage, bilder: Sequence[bytes],
                zeitgrenze_s: float = 60.0, optionen: Optional[dict] = None,
                denken: Optional[bool] = None) -> str:
    return json.dumps({
        'schema_version': SCHEMA_VERSION, 'frage_id': str(frage_id),
        'system': frage.system, 'text': frage.text, 'schema': frage.schema,
        'angeboten': list(frage.angeboten),
        'bilder_b64': [base64.b64encode(bytes(b)).decode('ascii') for b in bilder],
        'zeitgrenze_s': float(zeitgrenze_s), 'optionen': optionen or {},
        'denken': denken,
    }, ensure_ascii=False)


def entpacke_frage(text: str) -> Tuple[str, Frage, List[bytes], float, dict, Optional[bool]]:
    """Eine empfangene Frage lesen und begrenzen; ``ValueError`` bei Unbrauchbarem."""
    try:
        daten = json.loads(text)
    except (ValueError, TypeError) as fehler:
        raise ValueError('kein JSON') from fehler
    if not isinstance(daten, dict) or daten.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('unbekannte Fassung')
    frage_id = daten.get('frage_id')
    if not isinstance(frage_id, str) or not frage_id or len(frage_id) > 80:
        raise ValueError('frage_id fehlt')
    for feld in ('system', 'text'):
        if not isinstance(daten.get(feld), str) or len(daten[feld]) > 20_000:
            raise ValueError(f'{feld} fehlt oder ist zu lang')
    if not isinstance(daten.get('schema'), dict):
        raise ValueError('schema fehlt')
    roh_bilder = daten.get('bilder_b64')
    if not isinstance(roh_bilder, list) or len(roh_bilder) > MAX_BILDER:
        raise ValueError('bilder fehlen oder es sind zu viele')
    bilder = []
    for eintrag in roh_bilder:
        try:
            bild = base64.b64decode(eintrag, validate=True)
        except (binascii.Error, ValueError, TypeError) as fehler:
            raise ValueError('bild nicht lesbar') from fehler
        if not bild or len(bild) > MAX_BILD_BYTES:
            raise ValueError('bild leer oder zu groß')
        bilder.append(bild)
    grenze = daten.get('zeitgrenze_s', 60.0)
    if isinstance(grenze, bool) or not isinstance(grenze, (int, float)):
        raise ValueError('zeitgrenze_s ist keine Zahl')
    optionen = daten.get('optionen') or {}
    if not isinstance(optionen, dict):
        raise ValueError('optionen sind kein Objekt')
    denken = daten.get('denken')
    if denken is not None and not isinstance(denken, bool):
        raise ValueError('denken ist weder wahr noch falsch')
    angeboten = [int(n) for n in daten.get('angeboten') or []
                 if isinstance(n, int) and not isinstance(n, bool)]
    return (frage_id, Frage(daten['system'], daten['text'], daten['schema'], angeboten),
            bilder, min(MAX_ZEITGRENZE_S, max(1.0, float(grenze))), optionen, denken)


def packe_antwort(frage_id: str, modell: str, roh: Rohantwort) -> str:
    return json.dumps(dict(roh.als_nachricht(), schema_version=SCHEMA_VERSION,
                           frage_id=str(frage_id), modell=modell),
                      ensure_ascii=False)


def entpacke_antwort(text: str) -> Tuple[str, Optional[str], Rohantwort]:
    try:
        daten = json.loads(text)
    except (ValueError, TypeError) as fehler:
        raise ValueError('kein JSON') from fehler
    if not isinstance(daten, dict) or daten.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('unbekannte Fassung')
    if not isinstance(daten.get('frage_id'), str):
        raise ValueError('frage_id fehlt')
    modell = daten.get('modell')
    return (daten['frage_id'], modell if isinstance(modell, str) else None,
            Rohantwort.aus_nachricht(daten))
