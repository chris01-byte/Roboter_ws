"""Vermessene Vorschläge: Öffnungen im Rundum-Profil eines Standpunkts.

Eine **Öffnung** ist eine Lücke zwischen zwei Kanten (Pfosten), hinter der
es frei weitergeht. Gefunden wird sie im Profil „Entfernung über Richtung“:
An der ersten Kante springt die Entfernung nach hinten; die zweite Kante ist
entweder ein Sprung zurück nach vorn oder die Stelle, an der das Profil auf
die Linie der Wand zurückkehrt, in der die Lücke liegt.

Die Vermessung sagt nur, **wo** eine Lücke ist und wie breit. **Was** sie ist
(Tür, Glas, Spalt neben einem Schrank), entscheidet die KI am Bild.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

# Gehäusebreite 0,46 m; mit je 7 cm Luft. Öffnungen darunter werden gezeigt,
# aber als nicht befahrbar markiert.
BEFAHRBAR_AB_M = 0.60


@dataclass(frozen=True)
class Oeffnung:
    """Eine vermessene Öffnung im Standpunktrahmen."""

    nr: int
    breite_m: float
    mitte: Tuple[float, float]
    pfosten: Tuple[Tuple[float, float], Tuple[float, float]]
    richtung_grad: float      # Peilung der Mitte; 0 = vorn, positiv = links
    entfernung_m: float
    tiefe_m: float            # freie Tiefe hinter der Öffnung (Median)
    befahrbar: bool

    def als_dict(self) -> dict:
        return {
            'nr': self.nr,
            'breite_m': round(self.breite_m, 2),
            'mitte': [round(self.mitte[0], 2), round(self.mitte[1], 2)],
            'pfosten': [[round(v, 2) for v in p] for p in self.pfosten],
            'richtung_grad': round(self.richtung_grad, 1),
            'entfernung_m': round(self.entfernung_m, 2),
            'tiefe_m': round(self.tiefe_m, 2),
            'befahrbar': self.befahrbar,
        }


def _kreuz(a: np.ndarray, b: np.ndarray):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _suche(w: np.ndarray, r: np.ndarray, *, min_breite_m: float,
           max_breite_m: float, max_breite_linie_m: float, min_tiefe_m: float,
           min_tiefe_median_m: float, sprung_m: float, min_abstand_m: float,
           max_abstand_m: float, weit_m: float, max_spanne_grad: float,
           anteil_frei: float, anteil_frei_linie: float,
           linie_toleranz_m: float) -> List[dict]:
    """Öffnungen in aufsteigender Winkelrichtung suchen (eine Durchlaufrichtung)."""
    n = len(w)
    schritt = float(w[1] - w[0])
    rundum = abs((w[-1] - w[0]) + schritt - 2 * math.pi) < schritt / 2.0
    bekannt = ~np.isnan(r)
    rr = np.where(np.isnan(r), np.nan,
                  np.minimum(np.where(np.isinf(r), weit_m, r), weit_m))
    echt = bekannt & (rr < weit_m)          # dort liegt wirklich ein Messpunkt
    richtungen = np.column_stack([np.cos(w), np.sin(w)])
    roh = np.column_stack([rr * np.cos(w), rr * np.sin(w)])
    # Die wahre Kante liegt zwischen dem letzten Strahl auf dem Pfosten und
    # dem ersten Strahl durch die Lücke: Kantenpunkt um einen halben Schritt
    # zur Lücke hin setzen, sonst wird jede Öffnung um einen Schritt zu breit.
    halb = schritt / 2.0
    kante_auf = np.column_stack([rr * np.cos(w + halb), rr * np.sin(w + halb)])
    kante_zu = np.column_stack([rr * np.cos(w - halb), rr * np.sin(w - halb)])

    nxt = np.roll(rr, -1)
    paar = bekannt & np.roll(bekannt, -1)
    if not rundum:
        paar[-1] = False
    with np.errstate(invalid='ignore'):
        steigend = paar & (nxt - rr > sprung_m)     # naher Punkt bei i
        fallend = paar & (rr - nxt > sprung_m)      # naher Punkt bei i+1
    max_bins = int(round(math.radians(max_spanne_grad) / schritt))

    def wandlinie(a: int) -> Optional[np.ndarray]:
        """Richtung der geraden Wand, die am Kantenpunkt ``a`` endet."""
        stuetze = [a]
        for zurueck in range(1, 40):
            i = a - zurueck
            if i < 0 and not rundum:
                break
            i %= n
            if not echt[i] or steigend[i] or fallend[i]:
                break
            stuetze.append(i)
            if np.hypot(*(roh[i] - roh[a])) >= 0.30:
                break
        if len(stuetze) < 4 or np.hypot(*(roh[stuetze[-1]] - roh[a])) < 0.12:
            return None
        punkte = roh[stuetze]
        _, werte, achsen = np.linalg.svd(punkte - punkte.mean(axis=0))
        if werte[1] / math.sqrt(len(stuetze)) > 0.02:      # keine gerade Wand
            return None
        return achsen[0]

    def pruefe(a: int, b: int, anzahl_dazwischen: int, mindestanteil: float,
               hoechstbreite: float) -> Optional[dict]:
        """Lücke zwischen den Kantenpunkten ``a`` und ``b`` prüfen."""
        if anzahl_dazwischen < 1 or not echt[b]:
            return None
        pfosten_a, pfosten_b = kante_auf[a], kante_zu[b]
        ab = pfosten_b - pfosten_a
        breite = float(np.hypot(ab[0], ab[1]))
        if breite < min_breite_m or breite > hoechstbreite:
            return None
        dazwischen = (a + 1 + np.arange(anzahl_dazwischen)) % n
        nenner = _kreuz(richtungen[dazwischen], ab)
        with np.errstate(divide='ignore', invalid='ignore'):
            bis_sehne = _kreuz(pfosten_a, ab) / nenner
        gut = np.isfinite(bis_sehne) & (bis_sehne > 0)
        if gut.sum() < max(1, int(0.8 * len(dazwischen))):
            return None
        # Freie Tiefe quer zur Lücke, nicht entlang des Strahls: Schräg
        # gesehen wäre sonst jede flache Nische „tief“.
        quer_anteil = np.abs(nenner[gut]) / breite
        mehr = (rr[dazwischen][gut] - bis_sehne[gut]) * quer_anteil
        if (np.mean(mehr >= min_tiefe_m) < mindestanteil
                or float(np.median(mehr)) < min_tiefe_median_m):
            return None
        mitte = (pfosten_a + pfosten_b) / 2.0
        entfernung = float(np.hypot(mitte[0], mitte[1]))
        if not (min_abstand_m <= entfernung <= max_abstand_m):
            return None
        return {'breite': breite, 'mitte': mitte, 'a': pfosten_a.copy(),
                'b': pfosten_b.copy(), 'entfernung': entfernung,
                'tiefe': float(np.median(mehr))}

    gefunden = []
    gesperrt_bis = -1                       # Kanten innerhalb einer Öffnung überspringen
    for a in np.flatnonzero(steigend):
        a = int(a)
        if a <= gesperrt_bis or not echt[a]:
            continue
        linie = wandlinie(a)
        seite_betrachter = 0.0 if linie is None else float(_kreuz(linie, -roh[a]))
        war_dahinter = False
        for versatz in range(1, max_bins + 1):
            j = a + versatz
            if j >= n and not rundum:
                break
            j %= n
            if not bekannt[j]:
                break                       # keine Öffnung über Unbeobachtetes hinweg
            treffer = None
            # Zweite Kante, Fall 1: die Entfernung springt wieder nach vorn.
            if fallend[j]:
                treffer = pruefe(a, (j + 1) % n, versatz, anteil_frei, max_breite_m)
            # Zweite Kante, Fall 2: das Profil kehrt auf die Linie der Wand
            # zurück, in der die Lücke liegt. Nötig für Türen, die schräg
            # gesehen werden: Hinter dem fernen Pfosten liegt die Seitenwand
            # des Nachbarraums oft so dicht, dass kein Sprung entsteht. Weil
            # beide Pfosten hier in einer geraden Wand liegen, genügt ein
            # kleinerer Anteil frei durchgehender Strahlen.
            if treffer is None and linie is not None and echt[j]:
                quer = float(_kreuz(linie, roh[j] - roh[a]))
                laengs = abs(float(np.dot(linie, roh[j] - roh[a])))
                if (war_dahinter and abs(quer) <= linie_toleranz_m
                        and laengs >= 0.8 * min_breite_m):
                    treffer = pruefe(a, j, versatz - 1, anteil_frei_linie,
                                     max_breite_linie_m)
                war_dahinter = (abs(quer) > linie_toleranz_m
                                and quer * seite_betrachter < 0.0)
            if treffer is not None:
                gefunden.append(treffer)
                gesperrt_bis = a + versatz
                break
    return gefunden


def _ueberdeckung(g: dict, v: dict) -> float:
    """Gemeinsamer Winkelbereich zweier Lücken in rad."""
    beste = 0.0
    for umlauf in (-2 * math.pi, 0.0, 2 * math.pi):
        anfang = max(g['von'], v['von'] + umlauf)
        ende = min(g['von'] + g['spanne'], v['von'] + umlauf + v['spanne'])
        beste = max(beste, ende - anfang)
    return beste


def oeffnungen(winkel_rad, entfernung_m, *,
               min_breite_m: float = 0.55, max_breite_m: float = 2.5,
               max_breite_linie_m: float = 1.5,
               min_tiefe_m: float = 0.5, min_tiefe_median_m: float = 0.6,
               befahrbar_ab_m: float = BEFAHRBAR_AB_M,
               sprung_m: float = 0.35, min_abstand_m: float = 0.3,
               max_abstand_m: float = 6.0, weit_m: float = 8.0,
               max_spanne_grad: float = 150.0, anteil_frei: float = 0.85,
               anteil_frei_linie: float = 0.6, linie_toleranz_m: float = 0.06,
               max_anzahl: int = 8) -> List[Oeffnung]:
    """Öffnungen in einem Rundum-Profil finden.

    ``winkel_rad``: aufsteigende, gleichmäßige Richtungen im Standpunktrahmen.
    ``entfernung_m``: Entfernung je Richtung; ``nan`` = nicht beobachtet,
    ``inf`` = kein Echo (frei bis zur Reichweite).

    Eine Lücke zählt, wenn hinter der Verbindung ihrer Kanten bei mindestens
    ``anteil_frei`` der Strahlen ``min_tiefe_m`` frei sind und im Mittel
    (Median) ``min_tiefe_median_m``, gemessen quer zur Lücke. Der Median
    verlangt, dass das Gehäuse (0,42 m lang) hineinpasst; eine 50 cm tiefe
    Schranknische zählt deshalb nicht. Liegen beide Kanten in einer geraden
    Wand (Tür, schräg gesehen),
    genügt ``anteil_frei_linie``, weil hinter dem fernen Pfosten oft sofort
    die Seitenwand des Nachbarraums liegt; solche Lücken sind höchstens
    ``max_breite_linie_m`` breit.

    Gesucht wird in beiden Drehrichtungen, weil je nach Blickwinkel die
    erste oder die zweite Kante die undeutliche ist.

    Rückgabe: höchstens ``max_anzahl`` Öffnungen, nummeriert ab 1 in
    Drehrichtung gegen den Uhrzeigersinn, beginnend bei „vorn“.
    """
    w = np.asarray(winkel_rad, dtype=float)
    r = np.asarray(entfernung_m, dtype=float)
    if len(w) < 8 or len(r) != len(w):
        return []
    werte = dict(min_breite_m=min_breite_m, max_breite_m=max_breite_m,
                 max_breite_linie_m=max_breite_linie_m, min_tiefe_m=min_tiefe_m,
                 min_tiefe_median_m=min_tiefe_median_m, sprung_m=sprung_m,
                 min_abstand_m=min_abstand_m, max_abstand_m=max_abstand_m,
                 weit_m=weit_m, max_spanne_grad=max_spanne_grad,
                 anteil_frei=anteil_frei, anteil_frei_linie=anteil_frei_linie,
                 linie_toleranz_m=linie_toleranz_m)
    alle = _suche(w, r, **werte)
    spiegel = np.array([1.0, -1.0])
    for g in _suche(-w[::-1], r[::-1], **werte):      # gespiegelt, also rückwärts
        alle.append({'breite': g['breite'], 'mitte': g['mitte'] * spiegel,
                     'a': g['b'] * spiegel, 'b': g['a'] * spiegel,
                     'entfernung': g['entfernung'], 'tiefe': g['tiefe']})
    for g in alle:
        g['richtung'] = math.degrees(math.atan2(g['mitte'][1], g['mitte'][0]))
        g['von'] = math.atan2(g['a'][1], g['a'][0])
        g['spanne'] = (math.atan2(g['b'][1], g['b'][0]) - g['von']) % (2 * math.pi)

    # Überdecken sich zwei Lücken im Blickwinkel, bleibt die schmalere. Sonst
    # entsteht aus einer Möbelkante und einem Türpfosten eine breite
    # Scheinöffnung quer über die echte Tür (und dieselbe Tür doppelt aus
    # beiden Durchlaufrichtungen).
    gefunden: List[dict] = []
    for g in sorted(alle, key=lambda g: g['breite']):
        if all(_ueberdeckung(g, v) <= 0.5 * min(g['spanne'], v['spanne'])
               for v in gefunden):
            gefunden.append(g)

    if len(gefunden) > max_anzahl:
        gefunden.sort(key=lambda g: -min(g['breite'], 1.2) * min(g['tiefe'], 3.0))
        gefunden = gefunden[:max_anzahl]
    gefunden.sort(key=lambda g: g['richtung'] % 360.0)
    return [
        Oeffnung(nr=i + 1, breite_m=g['breite'],
                 mitte=(float(g['mitte'][0]), float(g['mitte'][1])),
                 pfosten=((float(g['a'][0]), float(g['a'][1])),
                          (float(g['b'][0]), float(g['b'][1]))),
                 richtung_grad=g['richtung'], entfernung_m=g['entfernung'],
                 tiefe_m=g['tiefe'], befahrbar=g['breite'] >= befahrbar_ab_m)
        for i, g in enumerate(gefunden)
    ]


def lecks_schliessen(entfernung_m, sprung_m: float = 0.35) -> np.ndarray:
    """Einzelne Ausreißer nach hinten glätten.

    Ein einzelner Strahl, der zwischen zwei nahen Nachbarn weit nach hinten
    reicht, ist ein Leck im Raster (Strahl zwischen zwei Wandzellen), keine
    Öffnung. Er wird auf den ferneren der beiden Nachbarn gesetzt.
    """
    r = np.asarray(entfernung_m, dtype=float).copy()
    davor, danach = np.roll(r, 1), np.roll(r, -1)
    with np.errstate(invalid='ignore'):
        nachbarn = np.fmax(davor, danach)
        leck = (np.isfinite(davor) & np.isfinite(danach) & ~np.isnan(r)
                & (r > nachbarn + sprung_m))
    r[leck] = nachbarn[leck]
    return r
