"""Die Wahl der KI an den Fahrteil übergeben.

Die KI wählt eine Nummer aus den vermessenen Öffnungen einer Blickrunde. Damit
der Fahrteil genau diese Öffnung anfährt, wird sie mit ihrem Ort in der Karte
festgehalten: aus dem Standpunktrahmen der Runde (Antriebsmitte, Blick der
ersten Aufnahme) über die Lage des Roboters am Ende der Runde und den
Drehwinkel der letzten Aufnahme gegen die erste. Der Fahrteil misst später
neu und nimmt die türbreite Öffnung, die an diesem Ort liegt.

Die Datei bleibt auf dem Roboter, außerhalb des Repositorys: Sie enthält
Koordinaten der Wohnung. In Ausgaben für Menschen stehen nur Maße vom
Roboter aus.
"""
from __future__ import annotations

import json
import math
from typing import Optional, Sequence, Tuple

from .fahrziel import TUER_MAX_M, TUER_MIN_M, im_standpunktrahmen

WAHL_SCHEMA = 1
# So lange gilt eine Wahl: Danach kann der Roboter bewegt worden sein.
MAX_ALTER_S = 900.0
# Neu vermessen liegt die Mitte der gewählten Tür höchstens so weit von der
# Mitte aus der Blickrunde entfernt (Drehwinkel, Wandern beim Drehen, SLAM)…
WAHL_ABSTAND_M = 0.40
# … und jede andere türbreite Öffnung mindestens so viel weiter weg.
WAHL_EINDEUTIG_M = 0.15

ARTEN_TEXT = {
    'tuer_offen': 'offene Tür', 'durchgang': 'Durchgang',
    'tuer_geschlossen': 'geschlossene Tür', 'glas': 'Glas', 'spiegel': 'Spiegel',
    'moebelspalt': 'Lücke an Möbeln', 'nische': 'Nische', 'wand': 'Wand',
    'unklar': 'unklar',
}


def _winkel(w: float) -> float:
    return math.atan2(math.sin(w), math.cos(w))


def _zahlen(werte, anzahl: int) -> Optional[Tuple[float, ...]]:
    if not isinstance(werte, (list, tuple)) or len(werte) != anzahl:
        return None
    try:
        zahlen = tuple(float(v) for v in werte)
    except (TypeError, ValueError):
        return None
    if any(isinstance(v, bool) for v in werte) or not all(math.isfinite(z) for z in zahlen):
        return None
    return zahlen


def standpunkt_in_der_karte(karte: Optional[dict], gier_ende_rad: Optional[float],
                            rahmen: str = 'map') -> Optional[Tuple[float, float, float]]:
    """Lage des Standpunktrahmens einer Blickrunde in der Karte: (x, y, gier).

    ``karte``: was die Aufnahme am Ende der Runde festhielt (``rahmen``,
    ``basis_ende`` = [x, y, gier]). ``gier_ende_rad``: Drehwinkel der
    letzten Aufnahme gegen die erste (aus den Scans). Die Antriebsmitte
    bleibt beim Drehen auf der Stelle; der Blick der ersten Aufnahme ist der
    Blick am Ende, um diesen Winkel zurückgedreht.
    """
    if not karte or gier_ende_rad is None or not math.isfinite(gier_ende_rad):
        return None
    if karte.get('rahmen') != rahmen:
        return None
    basis = _zahlen(karte.get('basis_ende'), 3)
    if basis is None:
        return None
    x, y, gier = basis
    return x, y, _winkel(gier - gier_ende_rad)


def in_die_karte(punkt: Sequence[float],
                 standpunkt: Sequence[float]) -> Tuple[float, float]:
    """Ein Punkt des Standpunktrahmens in der Karte."""
    x, y, gier = (float(v) for v in standpunkt)
    c, s = math.cos(gier), math.sin(gier)
    px, py = float(punkt[0]), float(punkt[1])
    return x + c * px - s * py, y + s * px + c * py


def wahl_aufschreiben(vorbereitung, eintrag: dict,
                      standpunkt: Optional[Sequence[float]], *, jetzt_s: float,
                      rahmen: str = 'map') -> dict:
    """Die geprüfte Wahl der KI als Inhalt der Wahl-Datei.

    ``vorbereitung``: aus ``ablauf.bereite_vor``; ``eintrag``: aus
    ``ablauf.befrage``. ``ValueError`` mit Grund, wenn die Wahl nicht an den
    Fahrteil gehen darf: keine oder eine verworfene Antwort, „kein
    geeigneter Ausgang“, Einwand der Vermessung, Lage in der Karte fehlt.
    """
    if eintrag.get('fehler'):
        raise ValueError(f'keine Antwort der KI ({eintrag["fehler"]})')
    pruefung = eintrag.get('pruefung') or {}
    if not pruefung.get('gueltig'):
        raise ValueError('Antwort der KI verworfen ('
                         + (', '.join(pruefung.get('fehler') or []) or 'ungültig') + ')')
    nr = pruefung.get('wahl')
    if nr is None:
        raise ValueError('die KI nennt keinen geeigneten Ausgang')
    if eintrag.get('nachmessen'):
        raise ValueError(f'die Vermessung spricht gegen die Wahl ({eintrag["nachmessen"]})')
    treffer = [o for o in vorbereitung.oeffnungen if int(o.nr) == int(nr)]
    if not treffer:
        raise ValueError(f'Nummer {nr} ist nicht vermessen')
    if standpunkt is None:
        raise ValueError('die Lage der Runde in der Karte fehlt; die Wahl lässt sich '
                         'nicht übergeben')
    o = treffer[0]
    pfosten = [in_die_karte(q, standpunkt) for q in o.pfosten]
    mitte = (0.5 * (pfosten[0][0] + pfosten[1][0]), 0.5 * (pfosten[0][1] + pfosten[1][1]))
    gier_ende = vorbereitung.gier_ende_rad or 0.0
    richtung_ende = math.degrees(_winkel(math.radians(o.richtung_grad) - gier_ende))
    sicherheit = (pruefung.get('sicherheit') or {}).get(str(nr))
    return {
        'schema': WAHL_SCHEMA, 'art': 'ki_wahl', 'runde': vorbereitung.name,
        'erzeugt_s': round(float(jetzt_s), 1), 'quelle': 'ki',
        'modell': eintrag.get('modell'), 'dauer_s': round(float(eintrag.get('dauer_s') or 0), 2),
        'nr': int(nr), 'einordnung': (pruefung.get('arten') or {}).get(str(nr), 'unklar'),
        'sicherheit': sicherheit, 'begruendung': pruefung.get('begruendung') or '',
        'raum': pruefung.get('raum'), 'gefahren': list(pruefung.get('gefahren') or []),
        'breite_m': round(float(o.breite_m), 3),
        'tuerbreit': bool(TUER_MIN_M <= float(o.breite_m) <= TUER_MAX_M),
        'entfernung_m': round(float(o.entfernung_m), 3),
        'richtung_ende_grad': round(richtung_ende, 1),
        'rahmen': rahmen,
        'mitte': [round(mitte[0], 4), round(mitte[1], 4)],
        'pfosten': [[round(p[0], 4), round(p[1], 4)] for p in pfosten],
    }


def wahl_lesen(text: str, *, jetzt_s: float, rahmen: str = 'map',
               max_alter_s: float = MAX_ALTER_S) -> dict:
    """Eine Wahl-Datei prüfen; ``ValueError`` mit Grund bei jedem Mangel."""
    try:
        wahl = json.loads(text)
    except (TypeError, ValueError) as fehler:
        raise ValueError('Wahl: kein JSON') from fehler
    if not isinstance(wahl, dict) or wahl.get('art') != 'ki_wahl':
        raise ValueError('Wahl: keine Wahl der KI')
    if wahl.get('schema') != WAHL_SCHEMA:
        raise ValueError(f'Wahl: unbekanntes Schema {wahl.get("schema")!r}')
    if wahl.get('quelle') != 'ki':
        raise ValueError('Wahl: Quelle ist nicht die KI')
    if wahl.get('rahmen') != rahmen:
        raise ValueError(f'Wahl: Rahmen {wahl.get("rahmen")!r} statt {rahmen!r}')
    nr = wahl.get('nr')
    if isinstance(nr, bool) or not isinstance(nr, int):
        raise ValueError('Wahl: Nummer fehlt')
    if _zahlen(wahl.get('mitte'), 2) is None:
        raise ValueError('Wahl: Ort in der Karte fehlt')
    erzeugt = wahl.get('erzeugt_s')
    if isinstance(erzeugt, bool) or not isinstance(erzeugt, (int, float)):
        raise ValueError('Wahl: Zeit fehlt')
    alter = float(jetzt_s) - float(erzeugt)
    if alter < -5.0:
        raise ValueError('Wahl: Zeit liegt in der Zukunft')
    if alter > max_alter_s:
        raise ValueError(f'Wahl: {alter:.0f} s alt, gilt höchstens {max_alter_s:.0f} s')
    return wahl


def _komma(wert: float, stellen: int) -> str:
    return f'{wert:.{stellen}f}'.replace('.', ',')


def wahl_satz(wahl: dict) -> str:
    """Die Wahl in einem Satz für den Menschen, nur mit Maßen vom Roboter aus."""
    richtung = float(wahl.get('richtung_ende_grad') or 0.0)
    seite = ('geradeaus' if abs(richtung) < 3.0
             else f'{abs(richtung):.0f}° {"links" if richtung > 0 else "rechts"} '
                  'von seiner Blickrichtung')
    art = ARTEN_TEXT.get(wahl.get('einordnung'), str(wahl.get('einordnung')))
    sicher = wahl.get('sicherheit')
    satz = (f'Die KI wählt Nr. {wahl["nr"]}: {art}'
            + ('' if sicher is None else f' (sicher zu {round(100 * float(sicher)):d} %)')
            + f', {_komma(float(wahl["breite_m"]), 2)} m breit, '
            f'{_komma(float(wahl["entfernung_m"]), 1)} m entfernt, {seite}.')
    if not wahl.get('tuerbreit', True):
        satz += (f' So breit fährt der Fahrteil nicht hindurch (nur {_komma(TUER_MIN_M, 2)} '
                 f'bis {_komma(TUER_MAX_M, 2)} m); er würde nur ein Ende senden.')
    return satz


def zur_wahl(tueren: Sequence, wahl: dict, pose: Sequence[float], *,
             max_abstand_m: float = WAHL_ABSTAND_M,
             eindeutig_m: float = WAHL_EINDEUTIG_M):
    """Unter den neu vermessenen türbreiten Öffnungen die, die die KI gewählt hat.

    ``tueren`` im Standpunktrahmen der neuen Messung, ``pose`` die Lage des
    Roboters in der Karte dabei. Rückgabe ``(oeffnung, abstand_m)``.
    ``ValueError`` mit Grund, wenn keine Mitte höchstens ``max_abstand_m``
    von der gewählten entfernt liegt, oder wenn eine zweite kaum weiter weg
    liegt (dann ist nicht sicher, welche gemeint ist).
    """
    ziel = im_standpunktrahmen(wahl['mitte'], pose)
    naehe = sorted(
        ((math.hypot(0.5 * (o.pfosten[0][0] + o.pfosten[1][0]) - ziel[0],
                     0.5 * (o.pfosten[0][1] + o.pfosten[1][1]) - ziel[1]), o) for o in tueren),
        key=lambda paar: paar[0])
    if not naehe or naehe[0][0] > max_abstand_m:
        weg = math.hypot(ziel[0], ziel[1])
        richtung = math.degrees(math.atan2(ziel[1], ziel[0]))
        raise ValueError(
            f'an der Stelle der gewählten Öffnung ({_komma(weg, 1)} m entfernt, '
            f'{richtung:+.0f}°) ist keine türbreite Öffnung vermessen'
            + ('' if not naehe else
               f'; die nächste liegt {_komma(naehe[0][0], 2)} m daneben'))
    if len(naehe) > 1 and naehe[1][0] - naehe[0][0] < eindeutig_m:
        raise ValueError(
            f'zwei türbreite Öffnungen liegen fast gleich nah an der gewählten '
            f'(Nummern {naehe[0][1].nr} und {naehe[1][1].nr}); nicht eindeutig')
    return naehe[0][1], naehe[0][0]
