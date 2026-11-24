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
from typing import List, Optional, Sequence, Tuple

import numpy as np

# Gehäusebreite 0,46 m; mit je 7 cm Luft. Öffnungen darunter werden gezeigt,
# aber als nicht befahrbar markiert.
BEFAHRBAR_AB_M = 0.60
# Bis zu dieser Breite gilt eine Lücke als türgroß. Breitere Lücken sind
# meist freier Raum zwischen Möbeln; hinter ihnen wird weitergesucht.
TUERBREIT_M = 1.3
# Zwei Lücken, deren Mitten näher liegen, sind für die KI dieselbe Öffnung: In
# KI-F9, Lauf 2, standen zwei Nummern 0,13 m auseinander im Foto übereinander.
# Nur für die Liste an die KI; der Fahrteil sieht beide und prüft selbst, ob
# seine Wahl eindeutig ist.
MITTEN_GLEICH_M = 0.30
# Hinter einer türgroßen Lücke werden ihre Kanten übersprungen: So verdrängt eine
# Tür, die man durch eine nahe Tür hindurch sieht, die nahe nicht. Ausnahme: eine
# breite Lücke (über SPERRE_BREIT_M), die im Blickwinkel mehr als SPERRE_MAX_GRAD
# umspannt. Eine so nahe Lücke zu einem frei stehenden Möbel verdeckte sonst die
# Tür dahinter (Bewertung nach KI-F9, §2; Zufallszimmer 589). Eine nahe Tür bis
# 1,0 m sperrt immer; mit der Grenze allein nach Grad verdrängte die Tür
# gegenüber die nahe in 348 von 493 Fällen (Gegenprüfung Schritt 3).
SPERRE_MAX_GRAD = 60.0
SPERRE_BREIT_M = 1.0

# Wie die zweite Kante einer Öffnung gefunden wurde.
SCHLUSS_SPRUNG = 'sprung'      # die Entfernung springt wieder nach vorn
SCHLUSS_LINIE = 'linie'        # das Profil kehrt auf die Wandlinie zurück
SCHLUSS_BLATT = 'blatt'        # ein offenes Türblatt verdeckt den zweiten Pfosten
SCHLUSS_LOT = 'lot'            # wie „blatt“, das Blatt selbst war aber nicht zu verfolgen


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
    schluss: str = SCHLUSS_SPRUNG
    # Wo die Nummer stehen soll, wenn die Mitte verdeckt ist (Türblatt):
    # Mitte des Stücks der Schwelle, das vom Standpunkt aus zu sehen ist.
    marke: Optional[Tuple[float, float]] = None

    @property
    def marke_oder_mitte(self) -> Tuple[float, float]:
        return self.marke if self.marke is not None else self.mitte

    def als_dict(self) -> dict:
        werte = {
            'nr': self.nr,
            'breite_m': round(self.breite_m, 2),
            'mitte': [round(self.mitte[0], 2), round(self.mitte[1], 2)],
            'pfosten': [[round(v, 2) for v in p] for p in self.pfosten],
            'richtung_grad': round(self.richtung_grad, 1),
            'entfernung_m': round(self.entfernung_m, 2),
            'tiefe_m': round(self.tiefe_m, 2),
            'befahrbar': self.befahrbar,
            'schluss': self.schluss,
        }
        if self.marke is not None:
            werte['marke'] = [round(self.marke[0], 2), round(self.marke[1], 2)]
        return werte


def _kreuz(a: np.ndarray, b: np.ndarray):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _suche(w: np.ndarray, r: np.ndarray, *, min_breite_m: float,
           max_breite_m: float, max_breite_linie_m: float, min_tiefe_m: float,
           min_tiefe_median_m: float, sprung_m: float, min_abstand_m: float,
           max_abstand_m: float, weit_m: float, max_spanne_grad: float,
           anteil_frei: float, anteil_frei_linie: float,
           linie_toleranz_m: float, tuerbreit_m: float, blatt_min_m: float,
           blatt_max_m: float, sperre_max_grad: float = SPERRE_MAX_GRAD,
           sperre_breit_m: float = SPERRE_BREIT_M) -> Tuple[List[dict], List[dict]]:
    """Öffnungen in aufsteigender Winkelrichtung suchen (eine Durchlaufrichtung).

    Rückgabe: (angenommene Lücken, abgelehnte Lücken mit Grund). Abgelehnt
    und vermerkt wird nur, was von der Breite her eine Öffnung sein könnte.
    """
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
    abgelehnt: List[dict] = []

    def wandlinie(a: int) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Richtung der geraden Wand, die am Kantenpunkt ``a`` endet.

        Zuerst mit einem langen Stück Wand (bis 0,7 m): Je länger die
        Stütze, desto genauer die Richtung; aus 0,3 m Wand mit 2 cm Rauschen
        folgt die Linie einer 0,8 m entfernten Kante nur auf etwa 7 cm
        genau. Ist das lange Stück nicht gerade (Ecke), zählt das kurze.

        Rückgabe: (Richtung oder ``None``, Grund, warum keine Linie entstand).
        An echten Aufnahmen fehlte die Linie oft (KI-0N, 21.11.2026); der
        Grund steht deshalb im Protokoll.
        """
        stuetze = [a]
        for zurueck in range(1, 90):
            i = a - zurueck
            if i < 0 and not rundum:
                break
            i %= n
            if not echt[i] or steigend[i] or fallend[i]:
                break
            stuetze.append(i)
            if np.hypot(*(roh[i] - roh[a])) >= 0.70:
                break
        abstand = np.hypot(*(roh[stuetze] - roh[a]).T)
        grund = None
        for laenge in (0.70, 0.30):
            auswahl = [i for i, d in zip(stuetze, abstand) if d <= laenge + 1e-9]
            reichweite = float(np.hypot(*(roh[auswahl[-1]] - roh[a])))
            if len(auswahl) < 4:
                grund = grund or f'wand_{len(auswahl)}_punkte'
                continue
            if reichweite < 0.12:
                grund = grund or f'wand_nur_{reichweite:.2f}m'
                continue
            punkte = roh[auswahl]
            _, werte, achsen = np.linalg.svd(punkte - punkte.mean(axis=0))
            krumm = float(werte[1] / math.sqrt(len(auswahl)))
            if krumm <= 0.02:                              # gerade Wand
                return achsen[0], None
            grund = f'wand_krumm_{krumm:.3f}'
        return None, grund

    def messe(pfosten_a: np.ndarray, pfosten_b: np.ndarray, dazwischen: np.ndarray,
              mindestanteil: float, hoechstbreite: float, schluss: str) -> Optional[dict]:
        """Lücke zwischen zwei Pfosten prüfen; ``dazwischen`` sind die Strahlen hindurch.

        Rückgabe: ``None``, wenn die Breite nicht zu einer Öffnung passt;
        sonst die Lücke mit ``grund`` (``None`` = angenommen).
        """
        if len(dazwischen) < 1:
            return None
        ab = pfosten_b - pfosten_a
        breite = float(np.hypot(ab[0], ab[1]))
        if breite < min_breite_m or breite > hoechstbreite:
            return None
        mitte = (pfosten_a + pfosten_b) / 2.0
        luecke = {'breite': breite, 'mitte': mitte, 'a': pfosten_a.copy(),
                  'b': pfosten_b.copy(), 'schluss': schluss, 'marke': None,
                  'entfernung': float(np.hypot(mitte[0], mitte[1])),
                  'strahlen': int(len(dazwischen)), 'tiefe': None,
                  'anteil_tief': None, 'anteil_davor': None, 'grund': None,
                  'blatt': None}

        def ablehnen(grund: str) -> dict:
            luecke['grund'] = grund
            return luecke

        nenner = _kreuz(richtungen[dazwischen], ab)
        with np.errstate(divide='ignore', invalid='ignore'):
            bis_sehne = _kreuz(pfosten_a, ab) / nenner
        gut = np.isfinite(bis_sehne) & (bis_sehne > 0)
        if gut.sum() < max(1, int(0.8 * len(dazwischen))):
            return ablehnen('blick_zu_flach')
        # Freie Tiefe quer zur Lücke, nicht entlang des Strahls: Schräg
        # gesehen wäre sonst jede flache Nische „tief“.
        quer_anteil = np.abs(nenner[gut]) / breite
        mehr = (rr[dazwischen][gut] - bis_sehne[gut]) * quer_anteil
        luecke['tiefe'] = float(np.median(mehr))
        luecke['anteil_tief'] = float(np.mean(mehr >= min_tiefe_m))
        # Strahlen, die schon vor der Verbindung der Pfosten enden: Dort steht
        # etwas in der Lücke (zum Beispiel ein Türblatt von der Kante gesehen).
        luecke['anteil_davor'] = float(np.mean(mehr < -0.05))
        if (luecke['anteil_tief'] < mindestanteil
                or luecke['tiefe'] < min_tiefe_median_m):
            return ablehnen('zu_flach')
        if not (min_abstand_m <= luecke['entfernung'] <= max_abstand_m):
            return ablehnen('entfernung')
        return luecke

    def abstand_zur_strecke(punkt: np.ndarray, p: np.ndarray, q: np.ndarray) -> float:
        pq = q - p
        lage = float(np.dot(punkt - p, pq)) / max(1e-9, float(np.dot(pq, pq)))
        return float(np.hypot(*(punkt - (p + min(1.0, max(0.0, lage)) * pq))))

    def tuer_mit_blatt(a: int, t: int, anzahl_dazwischen: int,
                       linie: Optional[np.ndarray], seite: float,
                       linie_grund: Optional[str] = None
                       ) -> Tuple[Optional[dict], Optional[str]]:
        """Tür, deren offenes Blatt den zweiten Pfosten verdeckt.

        Von der Scharnierseite gesehen endet die sichtbare Lücke nicht am
        Türpfosten, sondern an der Spitze des offenen Türblatts; ein 85 cm
        breites Blatt im rechten Winkel ergibt so eine 1,20 m breite Lücke,
        deren Mitte neben der Tür liegt (Befund KI-0 am 21.11.2026: 1,22 m).
        Erkannt wird das Blatt als gerades, zusammenhängendes Stück, das an
        der Kante ``t`` vor der Wand beginnt und auf die Wandlinie des
        sichtbaren Pfostens ``a`` zurückläuft. Der zweite Pfosten ist dann
        das Scharnier; die lichte Breite ist der Abstand des sichtbaren
        Pfostens zum Blatt (bei weniger als 90° Öffnung steht es im Weg).

        Rückgabe: (Lücke oder ``None``, Grund, warum kein Blatt erkannt wurde).
        """
        if linie is None or seite == 0.0:
            return None, linie_grund or 'keine_wandlinie'
        vz = 1.0 if seite > 0 else -1.0
        quer_davor = float(_kreuz(linie, roh[t] - roh[a])) * vz
        if quer_davor < 0.15:
            return None, None               # die Kante liegt nicht vor der Wand
        spitze = kante_zu[t]
        vor_der_wand = quer_davor
        blatt = [t]
        weg, h, warum = 0.0, None, 'kehrt_nicht_zur_wand'
        for versatz in range(1, 120):
            i = t + versatz
            if i >= n and not rundum:
                warum = 'profil_endet'
                break
            i %= n
            if not echt[i]:
                warum = 'luecke_im_blatt'
                break
            # Fast von der Kante gesehen liegen die Messpunkte auf dem
            # Blatt weit auseinander; es muss dann stetig zur Wand laufen.
            stueck = float(np.hypot(*(roh[i] - roh[blatt[-1]])))
            quer = float(_kreuz(linie, roh[i] - roh[a])) * vz
            if stueck > sprung_m and not (stueck <= 0.6 and quer < quer_davor - 0.05):
                warum = 'nicht_zusammenhaengend'
                break
            weg += stueck
            if weg > blatt_max_m + 0.3:
                warum = 'zu_lang'
                break
            if abs(quer) <= linie_toleranz_m + 0.03 * abs(
                    float(np.dot(linie, roh[i] - roh[a]))):
                h = i
                break
            if quer < 0.0:
                warum = 'hinter_der_wand'
                break
            blatt.append(i)
            quer_davor = quer
        schluss = SCHLUSS_BLATT
        if h is None:
            # Das Blatt ist nicht zu verfolgen (von der Kante gesehen, oder
            # es ist die Ecke eines Möbels, dessen Seite nicht zu sehen ist).
            # Dann zählt als zweiter Pfosten der Punkt der Wand, der der
            # Kante am nächsten liegt (ihr Lot): Was dort von der Wand
            # absteht, reicht im ungünstigen Fall bis an die Wand.
            if vor_der_wand > blatt_max_m:
                return None, warum
            schluss = SCHLUSS_LOT
            scharnier = roh[a] + linie * float(np.dot(linie, spitze - roh[a]))
        else:
            scharnier = roh[h].copy()
            if len(blatt) >= 4:
                punkte = roh[blatt]
                schwerpunkt = punkte.mean(axis=0)
                _, werte, achsen = np.linalg.svd(punkte - schwerpunkt)
                if werte[1] / math.sqrt(len(blatt)) > 0.03:
                    return None, 'nicht_gerade'
                nenner = float(_kreuz(achsen[0], linie))
                if abs(nenner) > 0.2:       # Blatt steht nicht längs der Wand
                    scharnier = schwerpunkt + achsen[0] * (
                        float(_kreuz(roh[a] - schwerpunkt, linie)) / nenner)
        # Der zweite Pfosten muss in Suchrichtung hinter dem ersten liegen. Fällt
        # das Lot auf die andere Seite, ist die „Lücke“ verkehrt herum: Ihre
        # Strahlen gehen nicht hindurch (die freie Tiefe ist ein Scheinwert),
        # und im Blickwinkel überdeckt sie fast den ganzen Rundblick. So hat in
        # KI-F9, Lauf 2, eine Lücke am Fenster die Labortür verdrängt (KI-F9N).
        if float(_kreuz(kante_auf[a], scharnier)) <= 0.0:
            return None, f'{schluss}_verkehrt'
        laenge = float(np.hypot(*(scharnier - spitze)))
        tuer = float(np.hypot(*(scharnier - kante_auf[a])))
        if schluss == SCHLUSS_BLATT and not (blatt_min_m <= laenge <= blatt_max_m):
            return None, f'laenge_{laenge:.2f}'
        if schluss == SCHLUSS_LOT and blatt_min_m > blatt_max_m:
            return None, warum              # Regel abgeschaltet
        dazwischen = (a + 1 + np.arange(anzahl_dazwischen)) % n
        luecke = messe(kante_auf[a], scharnier, dazwischen, anteil_frei_linie,
                       max_breite_linie_m, schluss)
        if luecke is None:
            return None, f'tuer_{tuer:.2f}'
        luecke['blatt'] = (f'blatt_{laenge:.2f}' if schluss == SCHLUSS_BLATT
                           else f'lot_statt_{warum}')
        if luecke['grund'] is not None:
            return luecke, None
        luecke['breite'] = min(tuer, abstand_zur_strecke(kante_auf[a], scharnier, spitze))
        if luecke['breite'] < min_breite_m:
            return ablehnen_fertig(luecke, 'blatt_im_weg'), None
        # Nummer auf das sichtbare Stück der Schwelle setzen: vom Pfosten bis
        # dorthin, wo der Blick an der Blattspitze vorbei die Schwelle trifft.
        ab = scharnier - kante_auf[a]
        nenner = float(_kreuz(spitze, ab))
        if abs(nenner) > 1e-9:
            anteil = float(_kreuz(kante_auf[a], ab)) / nenner
            sicht = spitze * anteil
            lage = float(np.dot(sicht - kante_auf[a], ab)) / float(np.dot(ab, ab))
            if anteil > 0 and 0.15 <= lage < 1.0:
                luecke['marke'] = (kante_auf[a] + sicht) / 2.0
        return luecke, None

    def ablehnen_fertig(luecke: dict, grund: str) -> dict:
        luecke['grund'] = grund
        return luecke

    gefunden = []
    gesperrt_bis = -1                       # Kanten innerhalb einer Tür überspringen
    for a in np.flatnonzero(steigend):
        a = int(a)
        if a <= gesperrt_bis or not echt[a]:
            continue
        linie, linie_grund = wandlinie(a)
        seite_betrachter = 0.0 if linie is None else float(_kreuz(linie, -roh[a]))
        war_dahinter = False
        zulaessig: List[Tuple[dict, int]] = []
        for versatz in range(1, max_bins + 1):
            j = a + versatz
            if j >= n and not rundum:
                break
            j %= n
            if not bekannt[j]:
                break                       # keine Öffnung über Unbeobachtetes hinweg
            versuche = []
            # Zweite Kante, Fall 1: die Entfernung springt wieder nach vorn.
            # Zuerst prüfen, ob dort ein offenes Türblatt beginnt.
            if fallend[j]:
                b = (j + 1) % n
                if echt[b]:
                    mit_blatt, kein_blatt = tuer_mit_blatt(a, b, versatz, linie,
                                                           seite_betrachter, linie_grund)
                    if mit_blatt is not None:
                        versuche.append(mit_blatt)
                    if mit_blatt is None or mit_blatt['grund'] is not None:
                        einfach = messe(kante_auf[a], kante_zu[b],
                                        (a + 1 + np.arange(versatz)) % n,
                                        anteil_frei, max_breite_m, SCHLUSS_SPRUNG)
                        if einfach is not None:
                            einfach['blatt'] = kein_blatt
                            if mit_blatt is not None and einfach['grund'] is None:
                                # Das Blatt wurde erkannt, die Tür dahinter aber
                                # nicht bestätigt: Die Lücke bis zur Blattspitze
                                # ist dann kein Ersatz für die Tür.
                                einfach['grund'] = 'nur_bis_zur_blattspitze'
                            versuche.append(einfach)
            # Zweite Kante, Fall 2: das Profil kehrt auf die Linie der Wand
            # zurück, in der die Lücke liegt. Nötig für Türen, die schräg
            # gesehen werden: Hinter dem fernen Pfosten liegt die Seitenwand
            # des Nachbarraums oft so dicht, dass kein Sprung entsteht. Weil
            # beide Pfosten hier in einer geraden Wand liegen, genügt ein
            # kleinerer Anteil frei durchgehender Strahlen.
            if linie is not None and echt[j]:
                quer = float(_kreuz(linie, roh[j] - roh[a]))
                laengs = abs(float(np.dot(linie, roh[j] - roh[a])))
                if (war_dahinter and abs(quer) <= linie_toleranz_m
                        and laengs >= 0.8 * min_breite_m and versatz >= 2
                        and not any(v['grund'] is None for v in versuche)):
                    auf_linie = messe(kante_auf[a], kante_zu[j],
                                      (a + 1 + np.arange(versatz - 1)) % n,
                                      anteil_frei_linie, max_breite_linie_m,
                                      SCHLUSS_LINIE)
                    if auf_linie is not None:
                        versuche.append(auf_linie)
                war_dahinter = (abs(quer) > linie_toleranz_m
                                and quer * seite_betrachter < 0.0)
            for versuch in versuche:
                if versuch['grund'] is None:
                    zulaessig.append((versuch, versatz))
                else:
                    abgelehnt.append(versuch)
        if not zulaessig:
            continue
        # Von dieser Kante aus zählt die schmalste zulässige Lücke: Die lichte
        # Breite an einem Pfosten ist der Abstand zum nächsten Hindernis
        # gegenüber. (Bis 21.11.2026 zählte die erste gefundene; durch eine
        # Tür hindurch gesehen war das oft die Kante einer ferneren Öffnung.)
        beste, versatz = min(zulaessig, key=lambda eintrag: eintrag[0]['breite'])
        for versuch, _ in zulaessig:
            if versuch is not beste:
                versuch['grund'] = 'schmalere_gewaehlt'
                abgelehnt.append(versuch)
        gefunden.append(beste)
        # Hinter einer breiten Lücke (freier Raum zwischen Möbeln)
        # weitersuchen: Dort kann die eigentliche Tür liegen. Am 21.11.2026
        # wurde eine offene Tür in 4–5 m nicht angeboten, nur die 2,25 m
        # breite Möbellücke davor.
        if beste['breite'] <= tuerbreit_m and (
                beste['breite'] <= sperre_breit_m
                or versatz * schritt <= math.radians(sperre_max_grad)):
            gesperrt_bis = a + versatz
    return gefunden, abgelehnt


def _gespiegelt(g: dict) -> dict:
    """Eine Lücke aus dem rückwärts durchlaufenen Profil zurückspiegeln."""
    spiegel = np.array([1.0, -1.0])
    neu = dict(g)
    neu['mitte'] = g['mitte'] * spiegel
    neu['a'], neu['b'] = g['b'] * spiegel, g['a'] * spiegel
    neu['marke'] = None if g.get('marke') is None else g['marke'] * spiegel
    return neu


def _ueberdeckung(g: dict, v: dict) -> float:
    """Gemeinsamer Winkelbereich zweier Lücken in rad."""
    beste = 0.0
    for umlauf in (-2 * math.pi, 0.0, 2 * math.pi):
        anfang = max(g['von'], v['von'] + umlauf)
        ende = min(g['von'] + g['spanne'], v['von'] + umlauf + v['spanne'])
        beste = max(beste, ende - anfang)
    return beste


def _zeile(g: dict, ursprung: np.ndarray, ergebnis: str, nr: Optional[int] = None) -> dict:
    """Eine geprüfte Lücke als kurze Protokollzeile (nur Maße, keine Karte)."""
    mitte = g['mitte'] + ursprung

    def gerundet(wert, stellen=2):
        return None if wert is None else round(float(wert), stellen)

    def polar(punkt) -> List[float]:
        p = np.asarray(punkt, dtype=float) + ursprung
        return [round(math.degrees(math.atan2(p[1], p[0])), 1),
                round(float(np.hypot(p[0], p[1])), 2)]

    return {
        # die beiden Kanten der Lücke: Richtung in Grad und Entfernung in m
        'pfosten': [polar(g['a']), polar(g['b'])],
        'ergebnis': ergebnis, 'nr': nr, 'schluss': g['schluss'],
        'breite_m': gerundet(g['breite']),
        'richtung_grad': gerundet(math.degrees(math.atan2(mitte[1], mitte[0])), 1),
        'entfernung_m': gerundet(np.hypot(mitte[0], mitte[1])),
        'strahlen': g['strahlen'], 'tiefe_m': gerundet(g['tiefe']),
        'anteil_tief': gerundet(g['anteil_tief']),
        'anteil_davor': gerundet(g['anteil_davor']),
        'blatt': g.get('blatt'),
    }


def oeffnungen(winkel_rad, entfernung_m, *,
               ursprung: Sequence[float] = (0.0, 0.0),
               protokoll: Optional[List[dict]] = None,
               min_breite_m: float = 0.55, max_breite_m: float = 2.5,
               max_breite_linie_m: float = 1.5,
               min_tiefe_m: float = 0.5, min_tiefe_median_m: float = 0.6,
               befahrbar_ab_m: float = BEFAHRBAR_AB_M,
               sprung_m: float = 0.35, min_abstand_m: float = 0.3,
               max_abstand_m: float = 6.0, weit_m: float = 8.0,
               max_spanne_grad: float = 150.0, anteil_frei: float = 0.85,
               anteil_frei_linie: float = 0.6, linie_toleranz_m: float = 0.06,
               tuerbreit_m: float = TUERBREIT_M, blatt_min_m: float = 0.5,
               blatt_max_m: float = 1.1, max_anzahl: int = 8,
               mitten_gleich_m: float = 0.0,
               sperre_max_grad: float = SPERRE_MAX_GRAD,
               sperre_breit_m: float = SPERRE_BREIT_M) -> List[Oeffnung]:
    """Öffnungen in einem Rundum-Profil finden.

    ``winkel_rad``: aufsteigende, gleichmäßige Richtungen, gesehen vom Punkt
    ``ursprung`` (im Standpunktrahmen; im Stand ist das der Ort des LiDAR,
    bei einer Drehung die Antriebsmitte).
    ``entfernung_m``: Entfernung je Richtung; ``nan`` = nicht beobachtet,
    ``inf`` = kein Echo (frei bis zur Reichweite).
    ``protokoll``: Liste, in die je geprüfter Lücke eine Zeile mit Maßen und
    Ergebnis geschrieben wird (angeboten oder Grund der Ablehnung).

    Eine Lücke zählt, wenn hinter der Verbindung ihrer Kanten bei mindestens
    ``anteil_frei`` der Strahlen ``min_tiefe_m`` frei sind und im Mittel
    (Median) ``min_tiefe_median_m``, gemessen quer zur Lücke. Der Median
    verlangt, dass das Gehäuse (0,42 m lang) hineinpasst; eine 50 cm tiefe
    Schranknische zählt deshalb nicht. Liegen beide Kanten in einer geraden
    Wand (Tür, schräg gesehen),
    genügt ``anteil_frei_linie``, weil hinter dem fernen Pfosten oft sofort
    die Seitenwand des Nachbarraums liegt; solche Lücken sind höchstens
    ``max_breite_linie_m`` breit. Verdeckt ein offenes Türblatt den zweiten
    Pfosten, wird die Tür vom sichtbaren Pfosten bis zum Scharnier vermessen
    (``schluss`` = „blatt“).

    Gesucht wird in beiden Drehrichtungen, weil je nach Blickwinkel die
    erste oder die zweite Kante die undeutliche ist.

    ``mitten_gleich_m``: Lücken, deren Mitten näher liegen, gelten als
    dieselbe Öffnung (die schmalere bleibt). Für die Liste an die KI
    ``MITTEN_GLEICH_M``; der Fahrteil lässt 0 und prüft Eindeutigkeit selbst.
    ``sperre_max_grad``, ``sperre_breit_m``: Kanten hinter einer türgroßen
    Lücke werden übersprungen, wenn sie höchstens ``sperre_breit_m`` breit ist
    oder im Blickwinkel höchstens ``sperre_max_grad`` umspannt.

    Rückgabe: höchstens ``max_anzahl`` Öffnungen im Standpunktrahmen,
    nummeriert ab 1 in Drehrichtung gegen den Uhrzeigersinn, beginnend bei
    „vorn“.
    """
    w = np.asarray(winkel_rad, dtype=float)
    r = np.asarray(entfernung_m, dtype=float)
    if len(w) < 8 or len(r) != len(w):
        return []
    versatz = np.asarray(ursprung, dtype=float)
    werte = dict(min_breite_m=min_breite_m, max_breite_m=max_breite_m,
                 max_breite_linie_m=max_breite_linie_m, min_tiefe_m=min_tiefe_m,
                 min_tiefe_median_m=min_tiefe_median_m, sprung_m=sprung_m,
                 min_abstand_m=min_abstand_m, max_abstand_m=max_abstand_m,
                 weit_m=weit_m, max_spanne_grad=max_spanne_grad,
                 anteil_frei=anteil_frei, anteil_frei_linie=anteil_frei_linie,
                 linie_toleranz_m=linie_toleranz_m, tuerbreit_m=tuerbreit_m,
                 blatt_min_m=blatt_min_m, blatt_max_m=blatt_max_m,
                 sperre_max_grad=sperre_max_grad, sperre_breit_m=sperre_breit_m)
    alle, abgelehnt = _suche(w, r, **werte)
    rueck, rueck_abgelehnt = _suche(-w[::-1], r[::-1], **werte)   # gespiegelt, also rückwärts
    alle += [_gespiegelt(g) for g in rueck]
    abgelehnt += [_gespiegelt(g) for g in rueck_abgelehnt]
    for g in alle:
        g['von'] = math.atan2(g['a'][1], g['a'][0])
        g['spanne'] = (math.atan2(g['b'][1], g['b'][0]) - g['von']) % (2 * math.pi)
    # Netz unter der Prüfung in ``tuer_mit_blatt``: Keine Lücke überdeckt mehr als
    # einen halben Rundblick; mehr heißt, ihre Kanten liegen verkehrt herum.
    verdraengt: List[Tuple[dict, str]] = [(g, 'verkehrt') for g in alle
                                          if g['spanne'] > math.pi]
    alle = [g for g in alle if g['spanne'] <= math.pi]

    # Überdecken sich zwei Lücken im Blickwinkel, bleibt eine:
    # - türgroß vor breit: Hinter einer breiten Möbellücke zählt die Tür.
    # - sonst die schmalere. Sonst entsteht aus einer Möbelkante und einem
    #   Türpfosten eine breite Scheinöffnung quer über die echte Tür (und
    #   dieselbe Tür doppelt aus beiden Durchlaufrichtungen).
    # Die Regel „von zwei türgroßen die nähere“ (für eine Tür, durch die man
    # eine zweite sieht) galt nur am 21.11.2026: An der echten Labortür
    # verdrängte damit eine 0,90 m breite Lücke 0,5 m vor der Tür die Tür
    # selbst, und die Nummer stand auf der Türzarge (KI-0R). Ohne sie hatte
    # dieselbe Aufnahme die Tür richtig angeboten (KI-0N).
    gefunden: List[dict] = []
    for g in sorted(alle, key=lambda g: (g['breite'] > tuerbreit_m, g['breite'])):
        if all(_ueberdeckung(g, v) <= 0.5 * min(g['spanne'], v['spanne'])
               and float(np.hypot(*(g['mitte'] - v['mitte']))) >= mitten_gleich_m
               for v in gefunden):
            gefunden.append(g)
        else:
            verdraengt.append((g, 'ueberdeckt'))

    if len(gefunden) > max_anzahl:
        gefunden.sort(key=lambda g: -min(g['breite'], 1.2) * min(g['tiefe'], 3.0))
        verdraengt += [(g, 'zu_viele') for g in gefunden[max_anzahl:]]
        gefunden = gefunden[:max_anzahl]

    def im_standpunkt(g: dict) -> dict:
        mitte = g['mitte'] + versatz
        return {'mitte': mitte, 'a': g['a'] + versatz, 'b': g['b'] + versatz,
                'marke': None if g.get('marke') is None else g['marke'] + versatz,
                'richtung': math.degrees(math.atan2(mitte[1], mitte[0])),
                'entfernung': float(np.hypot(mitte[0], mitte[1]))}

    fertig = [dict(g, **im_standpunkt(g)) for g in gefunden]
    fertig.sort(key=lambda g: g['richtung'] % 360.0)
    ergebnis = [
        Oeffnung(nr=i + 1, breite_m=g['breite'],
                 mitte=(float(g['mitte'][0]), float(g['mitte'][1])),
                 pfosten=((float(g['a'][0]), float(g['a'][1])),
                          (float(g['b'][0]), float(g['b'][1]))),
                 richtung_grad=g['richtung'], entfernung_m=g['entfernung'],
                 tiefe_m=g['tiefe'], befahrbar=g['breite'] >= befahrbar_ab_m,
                 schluss=g['schluss'],
                 marke=(None if g['marke'] is None
                        else (float(g['marke'][0]), float(g['marke'][1]))))
        for i, g in enumerate(fertig)
    ]
    if protokoll is not None:
        for nr, g in enumerate(fertig, start=1):
            # ``g`` liegt schon im Standpunktrahmen
            protokoll.append(_zeile(g, np.zeros(2), 'angeboten', nr))
        protokoll += [_zeile(g, versatz, grund) for g, grund in verdraengt]
        protokoll += [_zeile(g, versatz, g['grund']) for g in abgelehnt]
    return ergebnis


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
