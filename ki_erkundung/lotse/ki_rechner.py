"""Die Frage an den KI-Rechner stellen (Ollama, im Haus).

Nur Standardbibliothek. Es gibt genau einen Weg nach außen: die angegebene
Adresse des Ollama-Dienstes, in der Regel ``http://localhost:11434`` auf dem
KI-Rechner selbst. Bilder werden an keinen anderen Dienst gegeben.

Ein Fehler (nicht erreichbar, Zeitgrenze, unlesbare Antwort) wird als
Ergebnis zurückgegeben, nicht als Ausnahme: Für den Roboter ist „keine
Antwort“ ein normaler Fall, in dem die Regel entscheidet.
"""
from __future__ import annotations

import base64
import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .frage import Frage

STANDARD_URL = 'http://localhost:11434'


@dataclass
class Rohantwort:
    """Was vom KI-Rechner zurückkam."""

    text: Optional[str]
    dauer_s: float
    fehler: Optional[str] = None           # None = Antwort erhalten
    mit_schema: bool = True
    meta: dict = field(default_factory=dict)

    def als_dict(self) -> dict:
        return {'dauer_s': round(self.dauer_s, 2), 'fehler': self.fehler,
                'mit_schema': self.mit_schema, 'meta': self.meta}


# Bewusst ohne Proxy: Die Bilder gehen nur an die angegebene Adresse im Haus,
# auch wenn auf dem Rechner ein Proxy für das Internet eingestellt ist.
_DIREKT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _post(url: str, nutzlast: dict, zeitgrenze_s: float) -> dict:
    daten = json.dumps(nutzlast).encode('utf-8')
    anfrage = urllib.request.Request(
        url, data=daten, headers={'Content-Type': 'application/json'},
        method='POST')
    with _DIREKT.open(anfrage, timeout=zeitgrenze_s) as antwort:
        return json.loads(antwort.read().decode('utf-8'))


def _nutzlast(frage: Frage, bilder: Sequence[bytes], modell: str,
              mit_schema: bool, optionen: Optional[dict]) -> dict:
    einstellungen = {'temperature': 0.0, 'seed': 1, 'num_ctx': 8192}
    einstellungen.update(optionen or {})
    return {
        'model': modell,
        'stream': False,
        'format': frage.schema if mit_schema else 'json',
        'options': einstellungen,
        'messages': [
            {'role': 'system', 'content': frage.system},
            {'role': 'user', 'content': frage.text,
             'images': [base64.b64encode(bytes(b)).decode('ascii') for b in bilder]},
        ],
    }


def frage_stellen(frage: Frage, bilder: Sequence[bytes], modell: str,
                  url: str = STANDARD_URL, zeitgrenze_s: float = 60.0,
                  optionen: Optional[dict] = None,
                  mit_schema: bool = True) -> Rohantwort:
    """Eine Frage mit Bildern stellen und die Rohantwort zurückgeben.

    Lehnt der Dienst das Antwortschema ab (ältere Fassung), wird einmal mit
    einfachem JSON-Zwang wiederholt; das steht dann in ``mit_schema``.
    """
    ziel = url.rstrip('/') + '/api/chat'
    beginn = time.monotonic()

    def versuch(schema: bool) -> Rohantwort:
        try:
            roh = _post(ziel, _nutzlast(frage, bilder, modell, schema, optionen),
                        max(0.1, zeitgrenze_s - (time.monotonic() - beginn)))
        except urllib.error.HTTPError as fehler:
            return Rohantwort(None, time.monotonic() - beginn,
                              f'http_{fehler.code}', schema)
        except (socket.timeout, TimeoutError):
            return Rohantwort(None, time.monotonic() - beginn, 'zeitgrenze', schema)
        except urllib.error.URLError as fehler:
            grund = getattr(fehler, 'reason', None)
            art = ('zeitgrenze' if isinstance(grund, (socket.timeout, TimeoutError))
                   else 'nicht_erreichbar')
            return Rohantwort(None, time.monotonic() - beginn, art, schema)
        except (ValueError, OSError):
            return Rohantwort(None, time.monotonic() - beginn,
                              'antwort_unlesbar', schema)
        dauer = time.monotonic() - beginn
        text = (roh.get('message') or {}).get('content') if isinstance(roh, dict) else None
        if not isinstance(text, str):
            return Rohantwort(None, dauer, 'antwort_unlesbar', schema)
        meta = {}
        for schluessel in ('total_duration', 'load_duration', 'prompt_eval_duration',
                           'eval_duration'):
            if isinstance(roh.get(schluessel), (int, float)):
                meta[schluessel.replace('duration', 's')] = round(roh[schluessel] / 1e9, 3)
        for schluessel in ('prompt_eval_count', 'eval_count'):
            if isinstance(roh.get(schluessel), int):
                meta[schluessel] = roh[schluessel]
        return Rohantwort(text, dauer, None, schema, meta)

    ergebnis = versuch(mit_schema)
    if mit_schema and ergebnis.fehler in ('http_400', 'http_500'):
        ergebnis = versuch(False)
    return ergebnis


def modelle(url: str = STANDARD_URL, zeitgrenze_s: float = 5.0) -> Optional[List[str]]:
    """Namen der auf dem KI-Rechner vorhandenen Modelle; None = nicht erreichbar."""
    try:
        with _DIREKT.open(url.rstrip('/') + '/api/tags',
                          timeout=zeitgrenze_s) as antwort:
            daten = json.loads(antwort.read().decode('utf-8'))
    except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError, OSError):
        return None
    return sorted(str(m.get('name')) for m in daten.get('models', [])
                  if isinstance(m, dict) and m.get('name'))
