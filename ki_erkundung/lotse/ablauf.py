"""Ablauf des Trockenlaufs für eine Blickrunde.

    Blickrunde laden -> Drehwinkel bestimmen -> Bilder wählen
    -> Rundum-Profil -> Öffnungen vermessen -> Nummern einzeichnen, Skizze
    -> Frage bauen -> (KI fragen) -> Antwort prüfen -> Wahl nachmessen

Bis einschließlich „Frage bauen“ braucht der Ablauf keinen KI-Rechner.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
from PIL import Image

from .antwort import pruefe, wahl_nachmessen
from .blickrunde import (Blickrunde, bilder_waehlen, gier_schaetzen,
                         profil_ursprung, rundum_profil)
from .frage import Frage, baue_frage
from .kandidaten import Oeffnung, oeffnungen
from .ki_rechner import STANDARD_URL, Rohantwort, frage_stellen
from .markierung import (als_jpeg, marken_fuer_bild, markiere, sichtbar_in,
                         skizze, uebersicht)


@dataclass
class Vorbereitung:
    """Alles, was für eine Blickrunde vor der Frage an die KI entsteht."""

    name: str
    auswahl: dict                       # Ergebnis von bilder_waehlen
    guete_min: float                    # schwächste Zuordnung der Drehwinkel
    oeffnungen: List[Oeffnung]
    sichtbar: Dict[int, List[int]]
    frage: Frage
    fotos: List[Image.Image] = field(default_factory=list)     # markiert
    skizze: Optional[Image.Image] = None
    blatt: Optional[Image.Image] = None                        # alles auf einem Blatt
    kamera_winkel_grad: Sequence[float] = (0.0, 0.0)
    # Von wo aus vermessen wurde (Standpunktrahmen) und was dabei geprüft wurde
    ursprung: Sequence[float] = (0.0, 0.0)
    protokoll: List[dict] = field(default_factory=list)

    def bilder_fuer_ki(self, mosaik: bool = False) -> List[bytes]:
        if mosaik:
            return [als_jpeg(self.blatt)] if self.blatt is not None else []
        bilder = [als_jpeg(f) for f in self.fotos]
        if self.skizze is not None:
            bilder.append(als_jpeg(self.skizze))
        return bilder

    def als_dict(self) -> dict:
        return {
            'name': self.name,
            'vollstaendig': bool(self.auswahl['vollstaendig']),
            'gedreht_grad': self.auswahl['gedreht_grad'],
            'drehsinn': self.auswahl['drehsinn'],
            'guete_min': round(self.guete_min, 2),
            'bilder': [{'bild': b['bild'], 'aufnahme': b['aufnahme'],
                        'gier_grad': round(math.degrees(b['gier_rad']), 1),
                        'abweichung_grad': b['abweichung_grad']}
                       for b in self.auswahl['bilder']],
            'oeffnungen': [o.als_dict() for o in self.oeffnungen],
            'sichtbar_in': {str(k): v for k, v in sorted(self.sichtbar.items())},
            'kamera_winkel_grad': [round(v, 1) for v in self.kamera_winkel_grad],
            'vermessen_von': ('antriebsmitte' if not any(self.ursprung) else 'lidar'),
            'protokoll': list(self.protokoll),
        }


def bereite_vor(runde: Blickrunde, anzahl_bilder: int = 8,
                mosaik: bool = False,
                verlauf: Optional[Sequence[str]] = None) -> Vorbereitung:
    """Eine Blickrunde bis zur fertigen Frage aufbereiten."""
    scans = [runde.scan(i) for i in range(len(runde.aufnahmen))]
    if not scans or any(s is None for s in scans):
        raise ValueError(f'{runde.name}: Blickrunde ohne LiDAR-Scans; '
                         'ohne sie gibt es weder Drehwinkel noch Vorschläge')
    boden_lidar = runde.boden_lidar()
    boden_kamera = runde.boden_kamera()
    kamera = runde.kamera()
    gier, guete = gier_schaetzen(scans, boden_lidar, runde.vorgabe_gier())
    auswahl = bilder_waehlen(gier, anzahl_bilder)
    # Im Stand vom Ort des LiDAR aus vermessen, nach einer Drehung von der
    # Antriebsmitte aus (siehe profil_ursprung).
    ursprung = profil_ursprung(gier, boden_lidar)
    winkel, entfernung = rundum_profil(scans, gier, boden_lidar, ursprung=ursprung)
    protokoll: List[dict] = []
    gefunden = oeffnungen(winkel, entfernung, ursprung=ursprung, protokoll=protokoll)

    marken_je_bild = {}
    fotos = []
    for eintrag in auswahl['bilder']:
        marken = marken_fuer_bild(gefunden, eintrag['gier_rad'], boden_kamera, kamera)
        marken_je_bild[eintrag['bild']] = marken
        fotos.append(markiere(runde.bild_bytes(eintrag['aufnahme']), marken,
                              schild=f'B{eintrag["bild"]}'))
    sichtbar = sichtbar_in(marken_je_bild)
    skizze_bild = skizze(winkel, entfernung, gefunden,
                         [b['gier_rad'] for b in auswahl['bilder']],
                         ursprung=ursprung)
    frage = baue_frage(gefunden, len(auswahl['bilder']), sichtbar,
                       drehsinn=auswahl['drehsinn'], verlauf=verlauf,
                       als_mosaik=mosaik, schritt_grad=360.0 / anzahl_bilder,
                       vollstaendig=auswahl['vollstaendig'])
    return Vorbereitung(
        name=runde.name, auswahl=auswahl,
        guete_min=float(np.min(guete)) if len(guete) else 0.0,
        oeffnungen=gefunden, sichtbar=sichtbar, frage=frage, fotos=fotos,
        skizze=skizze_bild, blatt=uebersicht(fotos, skizze_bild),
        kamera_winkel_grad=kamera.oeffnungswinkel_grad(),
        ursprung=(float(ursprung[0]), float(ursprung[1])), protokoll=protokoll)


def befrage(vorbereitung: Vorbereitung, modell: str, url: str = STANDARD_URL,
            zeitgrenze_s: float = 60.0, wiederholung: int = 0,
            mosaik: bool = False, optionen: Optional[dict] = None,
            denken: Optional[bool] = None,
            weg: Optional[Callable[..., Rohantwort]] = None) -> dict:
    """Den KI-Rechner fragen, die Antwort prüfen und die Wahl nachmessen.

    ``weg``: Übertragungsweg mit derselben Aufrufform wie
    ``ki_rechner.frage_stellen``. Ohne Angabe wird Ollama unter ``url``
    direkt gefragt (auf dem KI-Rechner selbst); der Roboter setzt hier den
    Weg über ROS zum KI-Rechner ein.
    """
    roh = (weg or frage_stellen)(
        vorbereitung.frage, vorbereitung.bilder_fuer_ki(mosaik), modell, url=url,
        zeitgrenze_s=zeitgrenze_s, optionen=optionen, denken=denken)
    eintrag = {'modell': modell, 'wiederholung': wiederholung}
    eintrag.update(roh.als_dict())
    if roh.fehler is None:
        pruefung = pruefe(roh.text, vorbereitung.frage.angeboten)
        eintrag['pruefung'] = pruefung.als_dict()
        eintrag['nachmessen'] = (wahl_nachmessen(pruefung.wahl, vorbereitung.oeffnungen)
                                 if pruefung.gueltig else None)
    return eintrag
