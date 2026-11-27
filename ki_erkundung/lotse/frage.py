"""Die Frage an den Lotsen zusammenstellen (Fassung 2, nach KI-F9N).

Fassung 2 (Bewertung nach KI-F9, §2): In KI-F9, Lauf 2, glich die Antwort in
Wahl, Arten und Zahlen genau dem Beispiel aus der Frage, und die KI wählte ein
Fensterrollo. Seither: ein Muster ohne Werte zum Abschreiben (wer es abschreibt,
wählt nichts), erst einordnen, dann wählen, eine eigene Art „fenster“ und
„lieber keine Wahl als eine falsche“.

Die Frage enthält alles, was die KI braucht: Sie ist zustandslos, das
Gedächtnis liegt beim Roboter. Dieselbe Frage lässt sich deshalb beliebig oft
und mit verschiedenen Modellen stellen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .kandidaten import Oeffnung

ARTEN = ('tuer_offen', 'tuer_geschlossen', 'durchgang', 'fenster', 'glas', 'spiegel',
         'moebel', 'moebelspalt', 'nische', 'wand', 'unklar')
# Nur durch diese Arten darf die KI den Roboter schicken.
ARTEN_AUSGANG = ('tuer_offen', 'durchgang')
ROBOTER_BREITE_M = 0.46

SYSTEM = (
    'Du bist der Lotse eines fahrenden Haushaltsroboters. Der Roboter '
    'erkundet eine ihm unbekannte Wohnung und zeigt dir, was seine Kamera '
    'sieht. Du entscheidest, durch welche Öffnung er den Raum verlassen '
    'soll. Du steuerst keine Motoren; der Roboter misst deine Wahl nach und '
    'fährt selbst. Eine falsche Wahl ist schlimmer als keine. Antworte '
    'ausschließlich mit einem JSON-Objekt nach dem vorgegebenen Muster, ohne '
    'weiteren Text.'
)

# Das Antwortmuster: gültiges JSON ohne Werte, die das Modell abschreiben kann.
# Die Nummer 0 gibt es nie, „ART“ ist keine Art, und die Wahl ist null: Wer das
# Muster abschreibt, wählt nichts (KI-F9, Lauf 2, schrieb das alte Beispiel ab).
ANTWORTMUSTER = ('{"kandidaten": [{"nr": 0, "art": "ART", "sicherheit": 0.0}], '
                 '"begruendung": "SATZ", "wahl": null, "raum": "RAUM", "gefahren": []}')


@dataclass
class Frage:
    """Text, Antwortschema und die angebotenen Nummern einer Frage."""

    system: str
    text: str
    schema: dict
    angeboten: List[int] = field(default_factory=list)
    # Nur diese Nummern darf die KI wählen: die in einem Foto stehen. ``None``
    # (Fragen aus älteren Fassungen) lässt alle angebotenen zu.
    waehlbar: Optional[List[int]] = None


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


def antwortschema(angeboten: Sequence[int],
                  waehlbar: Optional[Sequence[int]] = None) -> dict:
    """JSON-Schema der Antwort; ``wahl`` lässt nur wählbare Nummern zu.

    Wählbar sind die angebotenen Nummern, die in einem Foto stehen. Eine
    Öffnung, die nur der Laser kennt, kann die KI nicht beurteilen.
    """
    nummern = [int(n) for n in (angeboten if waehlbar is None else waehlbar)]
    # Reihenfolge der Felder = Reihenfolge, in der das Modell schreibt: erst
    # jede Nummer einordnen, dann begründen, dann wählen.
    return {
        'type': 'object',
        'properties': {
            'kandidaten': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'nr': {'type': 'integer'},
                        'art': {'type': 'string', 'enum': list(ARTEN)},
                        'sicherheit': {'type': 'number'},
                    },
                    'required': ['nr', 'art', 'sicherheit'],
                },
            },
            'begruendung': {'type': 'string'},
            'wahl': {'enum': nummern + [None]},
            'raum': {'type': 'string'},
            'gefahren': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['kandidaten', 'begruendung', 'wahl', 'raum', 'gefahren'],
    }


def baue_frage(oeffnungen: Sequence[Oeffnung], anzahl_bilder: int,
               sichtbar: Dict[int, List[int]], drehsinn: int = 1,
               verlauf: Optional[Sequence[str]] = None,
               mit_skizze: bool = True, als_mosaik: bool = False,
               schritt_grad: Optional[float] = None,
               vollstaendig: bool = True,
               am_rand: Optional[Dict[int, List[int]]] = None) -> Frage:
    """Die Frage für eine Blickrunde bauen.

    ``sichtbar``: je Nummer die Bilder, in denen sie eingezeichnet ist.
    ``am_rand``: je Nummer die Bilder, in denen sie nur am unteren Bildrand
    steht, weil die Öffnung näher liegt, als das Bild reicht.
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
    waehlbar = [nr for nr in angeboten if sichtbar.get(nr)]
    if oeffnungen:
        zeilen.append(
            f'Der Laser hat {len(oeffnungen)} Öffnung(en) vermessen. Jede hat '
            'eine Nummer. Sie steht im Foto als weiße Scheibe am Boden der '
            'Öffnung' + (' und in der Skizze.' if mit_skizze else '.')
            + ' Richtungen beziehen sich auf B1.')
        zeilen.append('')
        zeilen.append('Nr. | Breite | Entfernung | Richtung | zu sehen in')
        unten = am_rand or {}
        for o in oeffnungen:
            bilder = ', '.join(
                f'B{b}' + (' (unterer Bildrand)' if b in unten.get(int(o.nr), []) else '')
                for b in sichtbar.get(int(o.nr), [])) or 'keinem Foto'
            schmal = '' if o.befahrbar else ' (zu schmal für den Roboter)'
            zeilen.append(
                f'{o.nr} | {o.breite_m:.2f} m{schmal} | {o.entfernung_m:.1f} m | '
                f'{richtung_text(o.richtung_grad)} | {bilder}'.replace('.', ','))
        if any(unten.get(int(o.nr)) for o in oeffnungen):
            zeilen += ['', 'Steht eine Nummer am unteren Bildrand, liegt die Öffnung '
                       'näher am Roboter, als das Foto reicht: Ihr Boden ist nicht im '
                       'Bild. Das Foto zeigt über der Nummer, was hinter der Öffnung '
                       'liegt. Ist dort eine Wand, ist es kein Ausgang.']
        if len(waehlbar) < len(angeboten):
            zeilen += ['', 'Nummern, die in keinem Foto stehen, kennt nur der Laser. Du '
                       'kannst sie nicht beurteilen: Ordne sie als unklar ein und wähle '
                       'sie nicht.']
    else:
        zeilen.append('Der Laser hat keine Öffnung vermessen.')
    zeilen += [
        '',
        'Aufgabe:',
        '1. Ordne jede Nummer aus der Tabelle ein (kandidaten, art). Schau dazu '
        'bei jeder Nummer: Reicht die Öffnung bis zum Boden? Was ist dahinter: '
        'ein Raum oder Flur, draußen, Glas, ein Rollo, ein Möbel? Die Arten: '
        'tuer_offen = offene Zimmertür, reicht bis zum Boden, dahinter ein '
        'anderer Raum oder Flur; tuer_geschlossen = Tür, aber geschlossen; '
        'durchgang = offener Durchgang ohne Tür, reicht bis zum Boden; '
        'fenster = Fenster, auch mit Rollo, Jalousie oder Vorhang, beginnt meist '
        'erst über dem Boden an einer Fensterbank, dahinter ist draußen; '
        'glas = Glastür oder Glasscheibe bis zum Boden; spiegel = Spiegel; '
        'moebel = an der Nummer steht ein Möbelstück (Regal, Schrank, Stuhl, '
        'Tisch); moebelspalt = Lücke zwischen oder neben Möbeln; '
        'nische = Nische, Schrank oder Sackgasse; wand = die Nummer steht auf '
        'einer Wand oder auf Mauerwerk, dort ist keine Öffnung; unklar = nicht '
        'zu erkennen. sicherheit = wie sicher du bei dieser Einordnung bist, von '
        '0 (geraten) bis 1 (eindeutig).',
        '2. Begründe in einem kurzen Satz, was du bei der gewählten Nummer siehst, '
        'oder warum keine passt (begruendung).',
        '3. Wähle die Nummer, durch die der Roboter den Raum verlassen soll '
        '(wahl). Erlaubt sind nur Nummern aus der Tabelle mit art tuer_offen '
        f'oder durchgang. Der Roboter ist {int(ROBOTER_BREITE_M * 100)} cm '
        'breit. Lieber keine Wahl als eine falsche: Bist du nicht sicher, dass '
        'es eine offene Tür oder ein Durchgang in einen anderen Raum ist, setze '
        'wahl auf null. Das ist eine richtige Antwort; der Roboter bleibt dann '
        'stehen. Ein Fenster ist nie ein Ausgang.',
        '4. Nenne den Raum, in dem der Roboter steht (raum), zum Beispiel '
        'Flur, Wohnzimmer, Schlafzimmer, Küche, Bad, Arbeitszimmer, '
        'Abstellraum oder unklar.',
        '5. Nenne Gefahren für einen fahrenden Roboter, die du siehst '
        '(gefahren), zum Beispiel Treppe, Kabel am Boden, Glas. Sonst eine '
        'leere Liste.',
        '',
        'Bisheriger Verlauf an diesem Standpunkt: '
        + ('; '.join(verlauf) if verlauf else 'keiner.'),
        '',
        'Antwortmuster (nur die Form: je Nummer aus der Tabelle ein Eintrag in '
        'kandidaten; die 0 und die großgeschriebenen Wörter durch deine Angaben '
        'ersetzen):',
        ANTWORTMUSTER,
    ]
    return Frage(system=SYSTEM, text='\n'.join(zeilen),
                 schema=antwortschema(angeboten, waehlbar), angeboten=angeboten,
                 waehlbar=waehlbar)
