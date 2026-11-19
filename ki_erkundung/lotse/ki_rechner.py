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
    denken: Optional[bool] = None          # was als Denkschalter gesendet wurde

    def als_dict(self) -> dict:
        """Für die Ergebnisdatei: ohne den Antworttext."""
        return {'dauer_s': round(self.dauer_s, 2), 'fehler': self.fehler,
                'mit_schema': self.mit_schema, 'denken': self.denken,
                'meta': self.meta}

    def als_nachricht(self) -> dict:
        """Für die Übertragung zwischen KI-Rechner und Roboter: mit Text."""
        return dict(self.als_dict(), text=self.text)

    @classmethod
    def aus_nachricht(cls, nachricht: dict) -> 'Rohantwort':
        text = nachricht.get('text')
        fehler = nachricht.get('fehler')
        if fehler is None and not isinstance(text, str):
            fehler = 'antwort_unlesbar'
        return cls(text=text if isinstance(text, str) else None,
                   dauer_s=float(nachricht.get('dauer_s') or 0.0), fehler=fehler,
                   mit_schema=bool(nachricht.get('mit_schema', True)),
                   meta=dict(nachricht.get('meta') or {}),
                   denken=nachricht.get('denken'))


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


def _hole(url: str, zeitgrenze_s: float):
    try:
        with _DIREKT.open(url, timeout=zeitgrenze_s) as antwort:
            return json.loads(antwort.read().decode('utf-8'))
    except (urllib.error.URLError, socket.timeout, TimeoutError, ValueError, OSError):
        return None


def _nutzlast(frage: Frage, bilder: Sequence[bytes], modell: str,
              mit_schema: bool, optionen: Optional[dict],
              denken: Optional[bool]) -> dict:
    einstellungen = {'temperature': 0.0, 'seed': 1, 'num_ctx': 8192}
    einstellungen.update(optionen or {})
    nutzlast = {
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
    if denken is not None:
        nutzlast['think'] = bool(denken)
    return nutzlast


def frage_stellen(frage: Frage, bilder: Sequence[bytes], modell: str,
                  url: str = STANDARD_URL, zeitgrenze_s: float = 60.0,
                  optionen: Optional[dict] = None, mit_schema: bool = True,
                  denken: Optional[bool] = None) -> Rohantwort:
    """Eine Frage mit Bildern stellen und die Rohantwort zurückgeben.

    ``denken``: Denkschalter für Modelle, die vor der Antwort „nachdenken“
    (zum Beispiel Qwen3.5). ``False`` schaltet es ab (kürzere Antwortzeit),
    ``True`` an, ``None`` sendet nichts und lässt die Vorgabe des Modells.

    Lehnt der Dienst die Anfrage ab (ältere Fassung, Modell ohne
    Denkschalter), wird erst ohne Denkschalter und dann mit einfachem
    JSON-Zwang statt Schema wiederholt; was am Ende galt, steht in der
    Rohantwort.
    """
    ziel = url.rstrip('/') + '/api/chat'
    beginn = time.monotonic()

    def versuch(schema: bool, schalter: Optional[bool]) -> Rohantwort:
        def ohne(fehler: str) -> Rohantwort:
            return Rohantwort(None, time.monotonic() - beginn, fehler, schema,
                              denken=schalter)
        try:
            roh = _post(ziel, _nutzlast(frage, bilder, modell, schema, optionen, schalter),
                        max(0.1, zeitgrenze_s - (time.monotonic() - beginn)))
        except urllib.error.HTTPError as fehler:
            return ohne(f'http_{fehler.code}')
        except (socket.timeout, TimeoutError):
            return ohne('zeitgrenze')
        except urllib.error.URLError as fehler:
            grund = getattr(fehler, 'reason', None)
            return ohne('zeitgrenze' if isinstance(grund, (socket.timeout, TimeoutError))
                        else 'nicht_erreichbar')
        except (ValueError, OSError):
            return ohne('antwort_unlesbar')
        text = (roh.get('message') or {}).get('content') if isinstance(roh, dict) else None
        if not isinstance(text, str):
            return ohne('antwort_unlesbar')
        meta = {}
        for schluessel in ('total_duration', 'load_duration', 'prompt_eval_duration',
                           'eval_duration'):
            if isinstance(roh.get(schluessel), (int, float)):
                meta[schluessel.replace('duration', 's')] = round(roh[schluessel] / 1e9, 3)
        for schluessel in ('prompt_eval_count', 'eval_count'):
            if isinstance(roh.get(schluessel), int):
                meta[schluessel] = roh[schluessel]
        return Rohantwort(text, time.monotonic() - beginn, None, schema, meta, schalter)

    folge = [(mit_schema, denken)]
    if denken is not None:
        folge.append((mit_schema, None))
    if mit_schema:
        folge.append((False, None))
    ergebnis = versuch(*folge[0])
    for schema, schalter in folge[1:]:
        if ergebnis.fehler not in ('http_400', 'http_500'):
            break
        ergebnis = versuch(schema, schalter)
    return ergebnis


def modelle(url: str = STANDARD_URL, zeitgrenze_s: float = 5.0) -> Optional[List[str]]:
    """Namen der auf dem KI-Rechner vorhandenen Modelle; None = nicht erreichbar."""
    daten = _hole(url.rstrip('/') + '/api/tags', zeitgrenze_s)
    if not isinstance(daten, dict):
        return None
    return sorted(str(m.get('name')) for m in daten.get('models', [])
                  if isinstance(m, dict) and m.get('name'))


def umgebung(modell: str, url: str = STANDARD_URL, zeitgrenze_s: float = 5.0) -> dict:
    """Womit geantwortet wird: Fassung des Dienstes und Kennung des Modells.

    Damit ein Trockenlauf später nachvollziehbar und wiederholbar ist. Der
    Modellname allein genügt nicht: Unter demselben Namen kann nach einem
    Update ein anderes Modell liegen; die Kennung (``digest``) ändert sich dann.
    """
    wurzel = url.rstrip('/')
    ergebnis = {'modell': modell, 'dienst_fassung': None, 'modell_kennung': None,
                'quantisierung': None, 'parameter': None, 'groesse_gb': None}
    fassung = _hole(wurzel + '/api/version', zeitgrenze_s)
    if isinstance(fassung, dict) and isinstance(fassung.get('version'), str):
        ergebnis['dienst_fassung'] = fassung['version']
    daten = _hole(wurzel + '/api/tags', zeitgrenze_s)
    for eintrag in (daten or {}).get('models', []) if isinstance(daten, dict) else []:
        if not isinstance(eintrag, dict):
            continue
        if eintrag.get('name') in (modell, f'{modell}:latest'):
            einzelheiten = eintrag.get('details') or {}
            ergebnis['modell_kennung'] = eintrag.get('digest')
            ergebnis['quantisierung'] = einzelheiten.get('quantization_level')
            ergebnis['parameter'] = einzelheiten.get('parameter_size')
            if isinstance(eintrag.get('size'), (int, float)):
                ergebnis['groesse_gb'] = round(eintrag['size'] / 1e9, 2)
            break
    return ergebnis
