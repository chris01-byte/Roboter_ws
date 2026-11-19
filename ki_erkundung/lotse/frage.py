"""Die Frage an den Lotsen zusammenstellen (Fassung 1, Trockenlauf).

Die Frage enthält alles, was die KI braucht: Sie ist zustandslos, das
Gedächtnis liegt beim Roboter. Dieselbe Frage lässt sich deshalb beliebig oft
und mit verschiedenen Modellen stellen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .kandidaten import Oeffnung

ARTEN = ('tuer_offen', 'tuer_geschlossen', 'durchgang', 'glas', 'spiegel',
         'moebelspalt', 'nische', 'unklar')
# Nur durch diese Arten darf die KI den Roboter schicken.
ARTEN_AUSGANG = ('tuer_offen', 'durchgang')
ROBOTER_BREITE_M = 0.46

SYSTEM = (
    'Du bist der Lotse eines fahrenden Haushaltsroboters. Der Roboter '
    'erkundet eine ihm unbekannte Wohnung und zeigt dir, was seine Kamera '
    'sieht. Du entscheidest, durch welche Öffnung er den Raum verlassen '
    'soll. Du steuerst keine Motoren; der Roboter misst deine Wahl nach und '
    'fährt selbst. Antworte ausschließlich mit einem JSON-Objekt nach dem '
    'vorgegebenen Muster, ohne weiteren Text.'
)


@dataclass
class Frage:
    """Text, Antwortschema und die angebotenen Nummern einer Frage."""

    system: str
    text: str
    schema: dict
    angeboten: List[int] = field(default_factory=list)


def richtung_text(grad: float) -> str:
    """Peilung in Worten, bezogen auf Bild 1."""
    betrag = int(round(abs(grad)))
    if betrag < 8:
        return 'geradeaus'
    if betrag > 172:
        return 'genau hinter dem Roboter'
    seite = 'links' if grad > 0 else 'rechts'
    zusatz = ', schräg hinten' if betrag > 110 else ''
    return f'{betrag}° {seite}{zusatz}'


def antwortschema(angeboten: Sequence[int]) -> dict:
    """JSON-Schema der Antwort; ``wahl`` lässt nur angebotene Nummern zu."""
    nummern = [int(n) for n in angeboten]
    return {
        'type': 'object',
        'properties': {
            'wahl': {'enum': nummern + [None]},
            'begruendung': {'type': 'string'},
            'kandidaten': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'nr': {'type': 'integer'},
                        'art': {'type': 'string', 'enum': list(ARTEN)},
                        'sicherheit': {'type': 'number'},
                    },
                    'required': ['nr', 'art'],
                },
            },
            'raum': {'type': 'string'},
            'gefahren': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['wahl', 'begruendung', 'kandidaten', 'raum', 'gefahren'],
    }


def baue_frage(oeffnungen: Sequence[Oeffnung], anzahl_bilder: int,
               sichtbar: Dict[int, List[int]], drehsinn: int = 1,
               verlauf: Optional[Sequence[str]] = None,
               mit_skizze: bool = True, als_mosaik: bool = False,
               schritt_grad: Optional[float] = None,
               vollstaendig: bool = True) -> Frage:
    """Die Frage für eine Blickrunde bauen.

    ``sichtbar``: je Nummer die Bilder, in denen sie eingezeichnet ist.
    ``als_mosaik``: Alle Fotos und die Skizze stehen auf einem einzigen Blatt
    (für Modelle, die nur ein Bild je Frage annehmen).
    ``vollstaendig``: Falsch, wenn sich der Roboter nicht ganz herumgedreht
    hat (im Stand aufgenommen oder Teilschwenk); die Frage sagt das dann.
    """
    schritt = round(schritt_grad if schritt_grad else 360 / max(1, anzahl_bilder))
    herum = 'gegen den Uhrzeigersinn' if drehsinn >= 0 else 'im Uhrzeigersinn'
    if anzahl_bilder <= 1:
        lage = 'Der Roboter steht in einem Raum und schaut in eine Richtung.'
    elif vollstaendig:
        lage = ('Der Roboter steht in einem Raum und hat sich einmal um sich '
                'selbst gedreht.')
    else:
        lage = ('Der Roboter steht in einem Raum und hat sich ein Stück '
                'gedreht, aber nicht ganz herum. Was hinter ihm liegt, zeigen '
                'die Fotos nicht.')
    zeilen = [lage, '']
    if anzahl_bilder <= 1:
        zeilen.append(
            'Bild: B1 ist ein Foto seiner Kamera; der Name steht oben links '
            'im Foto.'
            + ((' Das zweite Feld auf dem Blatt' if als_mosaik else ' Das zweite Bild')
               + ' ist eine Skizze von oben.' if mit_skizze else ''))
    elif als_mosaik:
        zeilen.append(
            f'Bild: ein Blatt mit {anzahl_bilder} Fotos seiner Kamera, oben '
            f'links beschriftet mit B1 bis B{anzahl_bilder}, je {schritt}° '
            f'weitergedreht ({herum}).'
            + (' Das letzte Feld ist eine Skizze von oben.' if mit_skizze else ''))
    else:
        zeilen.append(
            f'Bilder: B1 bis B{anzahl_bilder} sind Fotos seiner Kamera, je '
            f'{schritt}° weitergedreht ({herum}); der Name steht oben links '
            'im Foto.'
            + (' Das letzte Bild ist eine Skizze von oben.' if mit_skizze else ''))
    zeilen.append(
        'Die Kamera sitzt 1,34 m hoch und schaut leicht nach unten: Du siehst '
        'den Boden und den unteren Teil von Wänden, Türen und Möbeln, keine '
        'Decke.')
    if mit_skizze:
        zeilen.append(
            'In der Skizze steht der Roboter in der Mitte, die Blickrichtung '
            'von B1 zeigt nach oben, schwarze Punkte sind Laser-Messpunkte '
            'auf Wänden und Möbeln, die Ringe haben 1 m Abstand.')
    zeilen.append('')
    angeboten = [int(o.nr) for o in oeffnungen]
    if oeffnungen:
        zeilen.append(
            f'Der Laser hat {len(oeffnungen)} Öffnung(en) vermessen. Jede hat '
            'eine Nummer. Sie steht im Foto als weiße Scheibe am Boden der '
            'Öffnung' + (' und in der Skizze.' if mit_skizze else '.')
            + ' Richtungen beziehen sich auf B1.')
        zeilen.append('')
        zeilen.append('Nr. | Breite | Entfernung | Richtung | zu sehen in')
        for o in oeffnungen:
            bilder = ', '.join(f'B{b}' for b in sichtbar.get(int(o.nr), [])) or 'keinem Foto'
            schmal = '' if o.befahrbar else ' (zu schmal für den Roboter)'
            zeilen.append(
                f'{o.nr} | {o.breite_m:.2f} m{schmal} | {o.entfernung_m:.1f} m | '
                f'{richtung_text(o.richtung_grad)} | {bilder}'.replace('.', ','))
    else:
        zeilen.append('Der Laser hat keine Öffnung vermessen.')
    zeilen += [
        '',
        'Aufgabe:',
        '1. Ordne jede Nummer ein (art): tuer_offen = offene Zimmertür; '
        'tuer_geschlossen = Tür, aber geschlossen; durchgang = offener '
        'Durchgang ohne Tür; glas = Glastür, Fenster oder Glasscheibe; '
        'spiegel = Spiegel; moebelspalt = Lücke zwischen oder neben Möbeln; '
        'nische = Nische, Schrank oder Sackgasse; unklar = nicht zu erkennen.',
        '2. Wähle die Nummer, durch die der Roboter den Raum verlassen soll '
        '(wahl). Erlaubt sind nur Nummern aus der Tabelle mit art tuer_offen '
        f'oder durchgang. Der Roboter ist {int(ROBOTER_BREITE_M * 100)} cm '
        'breit. Gibt es keinen geeigneten Ausgang, setze wahl auf null.',
        '3. Nenne den Raum, in dem der Roboter steht (raum), zum Beispiel '
        'Flur, Wohnzimmer, Schlafzimmer, Küche, Bad, Arbeitszimmer, '
        'Abstellraum oder unklar.',
        '4. Nenne Gefahren für einen fahrenden Roboter, die du siehst '
        '(gefahren), zum Beispiel Treppe, Kabel am Boden, Glas. Sonst eine '
        'leere Liste.',
        '',
        'Bisheriger Verlauf an diesem Standpunkt: '
        + ('; '.join(verlauf) if verlauf else 'keiner.'),
        '',
        'Antwortmuster:',
        '{"wahl": 2, "begruendung": "ein kurzer Satz", "kandidaten": '
        '[{"nr": 1, "art": "moebelspalt", "sicherheit": 0.8}, '
        '{"nr": 2, "art": "tuer_offen", "sicherheit": 0.9}], '
        '"raum": "Flur", "gefahren": []}',
    ]
    return Frage(system=SYSTEM, text='\n'.join(zeilen),
                 schema=antwortschema(angeboten), angeboten=angeboten)
