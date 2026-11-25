"""Die Antwort des Lotsen prüfen.

Grundsatz: Eine Antwort wird entweder vollständig verstanden oder verworfen.
Eine verworfene Antwort führt nie zu einer Fahrt; dann entscheidet die
vorhandene Regel. Diese Prüfung läuft später auf dem Roboter und schon jetzt
im Trockenlauf.

Geprüft wird nur die Form und die innere Stimmigkeit. Ob die gewählte
Öffnung befahrbar ist, misst danach die Vermessung (``wahl_nachmessen``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .frage import ARTEN, ARTEN_AUSGANG
from .kandidaten import Oeffnung

MAX_TEXT = 400
MAX_RAUM = 40
MAX_GEFAHREN = 5


@dataclass
class Pruefung:
    """Ergebnis der Prüfung einer Antwort."""

    gueltig: bool
    wahl: Optional[int] = None
    arten: Dict[int, str] = field(default_factory=dict)
    sicherheit: Dict[int, float] = field(default_factory=dict)
    raum: Optional[str] = None
    begruendung: str = ''
    gefahren: List[str] = field(default_factory=list)
    fehler: List[str] = field(default_factory=list)       # Gründe für „verworfen“
    toleriert: List[str] = field(default_factory=list)    # hingenommene Abweichungen
    # Die Nummer, die die KI als Wahl nannte, auch wenn die Antwort verworfen
    # wird: Sonst ist eine verworfene Fensterwahl in der Auswertung nicht mehr
    # zu sehen (zweite Gegenprüfung Schritt 3).
    genannt: Optional[int] = None

    def als_dict(self) -> dict:
        return {
            'gueltig': self.gueltig, 'wahl': self.wahl,
            'arten': {str(k): v for k, v in sorted(self.arten.items())},
            'sicherheit': {str(k): round(v, 2) for k, v in sorted(self.sicherheit.items())},
            'raum': self.raum, 'begruendung': self.begruendung,
            'gefahren': self.gefahren, 'fehler': self.fehler,
            'toleriert': self.toleriert, 'genannt': self.genannt,
        }


def _json_objekt(text: str):
    """Das JSON-Objekt einer Antwort; (Objekt, umrahmt) oder (None, False)."""
    try:
        wert = json.loads(text)
        return (wert, False) if isinstance(wert, dict) else (None, False)
    except (ValueError, TypeError):
        pass
    if not isinstance(text, str):
        return None, False
    start = text.find('{')
    while start != -1:                     # erstes vollständige Objekt im Text
        tiefe, in_text, maske = 0, False, False
        for i in range(start, len(text)):
            zeichen = text[i]
            if in_text:
                if maske:
                    maske = False
                elif zeichen == '\\':
                    maske = True
                elif zeichen == '"':
                    in_text = False
            elif zeichen == '"':
                in_text = True
            elif zeichen == '{':
                tiefe += 1
            elif zeichen == '}':
                tiefe -= 1
                if tiefe == 0:
                    try:
                        wert = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    return (wert, True) if isinstance(wert, dict) else (None, False)
        start = text.find('{', start + 1)
    return None, False


def _nummer(wert) -> Optional[int]:
    """Eine ganze Zahl aus Zahl oder Ziffernfolge; sonst None. Kein bool."""
    if isinstance(wert, bool):
        return None
    if isinstance(wert, int):
        return wert
    if isinstance(wert, float) and wert.is_integer():
        return int(wert)
    if isinstance(wert, str) and wert.strip().lstrip('-').isdigit():
        return int(wert.strip())
    return None


def pruefe(antwort_text, angeboten: Sequence[int],
           waehlbar: Optional[Sequence[int]] = None) -> Pruefung:
    """Antworttext gegen die angebotenen Nummern prüfen.

    ``waehlbar``: die Nummern, die in einem Foto stehen. Wählt die KI eine
    Öffnung, die sie nicht sehen konnte, wird die Antwort verworfen.
    """
    angeboten = [int(n) for n in angeboten]
    objekt, umrahmt = _json_objekt(antwort_text)
    if objekt is None:
        return Pruefung(gueltig=False, fehler=['kein_json'])
    ergebnis = Pruefung(gueltig=True)
    if umrahmt:
        ergebnis.toleriert.append('json_umrahmt')

    # --- Einordnung der Kandidaten
    kandidaten = objekt.get('kandidaten')
    if kandidaten is None:
        kandidaten = []
        ergebnis.toleriert.append('kandidaten_fehlen')
    if not isinstance(kandidaten, list):
        return Pruefung(gueltig=False, fehler=['kandidaten_keine_liste'])
    for eintrag in kandidaten:
        if not isinstance(eintrag, dict):
            ergebnis.toleriert.append('kandidat_unlesbar')
            continue
        nr = _nummer(eintrag.get('nr'))
        if nr is None or nr not in angeboten:
            ergebnis.toleriert.append('fremde_nummer_eingeordnet')
            continue
        art = eintrag.get('art')
        if art not in ARTEN:
            ergebnis.toleriert.append('art_unbekannt')
            art = 'unklar'
        if nr in ergebnis.arten and ergebnis.arten[nr] != art:
            # Zweimal verschieden eingeordnet (etwa erst Fenster, dann offene
            # Tür): widersprüchlich heißt unklar, die spätere Angabe gilt nicht.
            ergebnis.toleriert.append('nummer_doppelt_eingeordnet')
            art = 'unklar'
        ergebnis.arten[nr] = art
        sicher = eintrag.get('sicherheit')
        if isinstance(sicher, (int, float)) and not isinstance(sicher, bool):
            ergebnis.sicherheit[nr] = min(1.0, max(0.0, float(sicher)))
    for nr in angeboten:
        ergebnis.arten.setdefault(nr, 'unklar')

    # --- Wahl
    if 'wahl' not in objekt:
        return Pruefung(gueltig=False, fehler=['wahl_fehlt'])
    roh = objekt['wahl']
    if roh is None:
        ergebnis.wahl = None
    else:
        nr = _nummer(roh)
        if nr is None:
            return Pruefung(gueltig=False, fehler=['wahl_unlesbar'])
        if nr not in angeboten:
            return Pruefung(gueltig=False, fehler=['wahl_nicht_angeboten'], genannt=nr)
        if waehlbar is not None and nr not in [int(n) for n in waehlbar]:
            return Pruefung(gueltig=False, fehler=['wahl_nicht_im_foto'], genannt=nr)
        ergebnis.genannt = nr
        if isinstance(roh, str):
            ergebnis.toleriert.append('wahl_als_text')
        elif isinstance(roh, float):
            ergebnis.toleriert.append('wahl_als_kommazahl')
        if ergebnis.arten.get(nr) not in ARTEN_AUSGANG:
            # Die KI widerspricht sich: Sie wählt etwas, das sie selbst nicht
            # als offene Tür oder Durchgang einordnet.
            ergebnis.gueltig = False
            ergebnis.fehler.append('wahl_widerspricht_einordnung')
        ergebnis.wahl = nr if ergebnis.gueltig else None

    # --- Freitext
    raum = objekt.get('raum')
    if isinstance(raum, str) and raum.strip():
        ergebnis.raum = raum.strip()[:MAX_RAUM]
    begruendung = objekt.get('begruendung')
    if isinstance(begruendung, str):
        ergebnis.begruendung = begruendung.strip()[:MAX_TEXT]
    gefahren = objekt.get('gefahren')
    if isinstance(gefahren, list):
        ergebnis.gefahren = [str(g).strip()[:120] for g in gefahren
                             if isinstance(g, str) and g.strip()][:MAX_GEFAHREN]
    return ergebnis


def wahl_nachmessen(wahl: Optional[int], oeffnungen: Sequence[Oeffnung]) -> Optional[str]:
    """Die geprüfte Wahl gegen die Vermessung halten.

    Rückgabe: None, wenn nichts dagegen spricht; sonst der Grund, aus dem
    der Roboter die Wahl nicht ausführen würde.
    """
    if wahl is None:
        return None
    for o in oeffnungen:
        if int(o.nr) == int(wahl):
            return None if o.befahrbar else 'zu_schmal'
    return 'nicht_vermessen'
