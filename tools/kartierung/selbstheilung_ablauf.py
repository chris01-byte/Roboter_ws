#!/usr/bin/env python3
"""Ablaufauswertung einer Erkundungsfahrt (nur lesend, ohne ROS).

Anlass (W-1, 15.11.2026): In der zweiten Wohnungsfahrt begann Amadeus 27
Ziele und erreichte 2, drehte sich rund 20-mal um sich selbst und kam nicht
aus dem Laborraum heraus. Der Projektinhaber sah „immer wieder dieselben
Ziele“ und „keine Struktur“. Dieses Werkzeug beantwortet aus den vorhandenen
Aufzeichnungen, ohne neue Fahrt:

  1. Ziele: Wie viele verschiedene Ziele gab es, wie oft wurde jedes
     angefahren, mit welchem Ausgang? (Raster 0,25 m wie im Explorer)
  2. Abbrüche: Warum endete ein Anlauf mit „Goal canceled“? Zugeordnet wird
     die Wartephase oder der HWT-Zustand, der zur selben Zeit begann.
  3. Warten: wie oft, wie lange und worauf der Explorer gewartet hat.
  4. Verlauf je Minute: begonnene und beendete Anläufe, Wartezeit, freie
     Fläche, Zeit- und Reglerfehler.
  5. Die häufigsten Warnungen und Fehler im Log (Zahlen unkenntlich).
  6. Logauszüge um Abbrüche und starke Wackelspitzen (Koordinaten unkenntlich).
  7. Die Anläufe der Reihe nach, mit ``--tuer`` auch ihr Bezug zur Tür: Wie
     weit von der Tür begann jeder Anlauf (das ist zugleich die Stelle, an
     der der vorige endete), wie weit lag sein Ziel von der Tür, und lag es
     vom Startplatz aus gesehen hinter ihr?
  8. Warte- und HWT-Phasen der Reihe nach und die Rückfahrten mit ihrem
     Ausgang; bei einer abgebrochenen Rückfahrt der Grund wie bei den Zielen.
  9. Nahbild (Fahrtprotokoll ab Schema 3): was die lokale Karte um den
     Roboter zeigte, als der Regler anhielt („Controller patience exceeded“),
     und die Engstellen der Fahrt (Breite am Roboter unter 0,9 m).

Eingaben: das ``launch.log`` der Fahrt und das ``protokoll.json`` des
Fahrtprotokolls. Die Ausgabe enthält keine Koordinaten; Ziele erscheinen nur
als laufende Nummer mit Abständen. Das Werkzeug öffnet nur diese Dateien.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter

import selbstheilung_anlaeufe as an

STUFE = re.compile(r'\[(DEBUG|INFO|WARN|ERROR|FATAL)\]\s+\[(\d+\.\d+)\]\s+\[([\w.]+)\]:\s+(.*)')
RASTER_M = 0.25                  # wie der Schlüssel der Anläufe im Explorer
ZEITGRENZE_S = 145.0             # ab hier gilt ein Abbruch als Zielzeit (150 s) abgelaufen
FENSTER_VOR_S, FENSTER_NACH_S = 8.0, 6.0   # Abbruch gegen Beginn einer Wartephase
ZAEHLER = (
    ('kollision_voraus', 'detected collision ahead'),
    ('geduld_regler', 'Controller patience exceeded'),
    ('tf_zukunft', 'extrapolation into the future'),
    ('tf_pose', 'Unable to transform robot pose'),
    ('takt_verfehlt', 'missed its desired rate'),
    ('queue_voll', 'queue is full'),
    ('planer_kein_weg', 'failed to create plan'),
    ('rueckfahrt', 'Running backup'),
)
ZAHL = re.compile(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')
PAAR = re.compile(r'\(\s*[-+]?\d+\.\d+\s*,\s*[-+]?\d+\.\d+\s*\)')
LAUFEND = ('running', 'waiting', 'checking_completion')
TUER_NAH_M = 1.0                 # näher als so gilt ein Standort als „an der Tür“
RUECKFAHRT_ENDE = (('backup completed successfully', 'vollständig'),
                   ('backup failed', 'gescheitert'), ('Canceling backup', 'abgebrochen'))
PHASEN_HOECHSTENS = 60
ENGSTELLE_M = 0.9                # schmaler als so gilt eine Stelle als Engstelle
NAHBILD_FENSTER_S = 1.5          # so weit darf das Nahbild vom Reglerhalt entfernt liegen
ENGSTELLE_PAUSE_S = 3.0          # so lange ohne enges Bild, dann ist die Engstelle vorbei


def log_eintraege(text):
    """(Zeit, Stufe, Knoten, Meldung) aus ROS-Logzeilen eines launch.log."""
    for zeile in text.splitlines():
        treffer = STUFE.search(zeile)
        if treffer:
            yield float(treffer.group(2)), treffer.group(1), treffer.group(3), treffer.group(4)


def anlaeufe_aus_log(eintraege):
    """Anläufe mit absoluten Zeiten: Beginn, Ende, Ausgang, Start- und Zielpunkt."""
    anlaeufe, offen = [], None
    for t, _, knoten, meldung in eintraege:
        if knoten != 'bt_navigator':
            continue
        beginn = an.BEGINN.search(meldung)
        if beginn:
            x0, y0, x1, y1 = (float(v) for v in beginn.groups())
            offen = dict(beginn=t, von=(x0, y0), ziel=(x1, y1),
                         entfernung_m=math.dist((x0, y0), (x1, y1)))
            continue
        ende = an.ENDE.search(meldung)
        if ende and offen is not None:
            offen.update(ende=t, dauer_s=t - offen['beginn'], ausgang=an.AUSGANG[ende.group(1)])
            anlaeufe.append(offen)
            offen = None
    if offen is not None:
        offen.update(ende=None, dauer_s=None, ausgang='offen')
        anlaeufe.append(offen)
    return anlaeufe


def ziel_schluessel(punkt):
    return (round(punkt[0]/RASTER_M), round(punkt[1]/RASTER_M))


def ziele(anlaeufe, mission_beginn=None, tuer=None):
    """Ziele als Gruppen im 0,25-m-Raster, ohne Koordinaten."""
    gruppen = {}
    for a in anlaeufe:
        g = gruppen.setdefault(ziel_schluessel(a['ziel']), dict(
            versuche=0, erreicht=0, gescheitert=0, abgebrochen=0, offen=0,
            zeit_s=0.0, erster=a['beginn'], letzter=a['beginn'], punkt=a['ziel'],
            nach_erreichen_erneut=0))
        if g['erreicht']:
            g['nach_erreichen_erneut'] += 1
        g['versuche'] += 1
        g[a['ausgang']] += 1
        g['zeit_s'] += a['dauer_s'] or 0.0
        g['letzter'] = a['beginn']
    start = anlaeufe[0]['von'] if anlaeufe else None
    null = mission_beginn if mission_beginn is not None else (
        anlaeufe[0]['beginn'] if anlaeufe else 0.0)
    liste = []
    for nummer, g in enumerate(sorted(gruppen.values(), key=lambda g: (-g['versuche'], g['erster'])), 1):
        eintrag = dict(ziel=nummer, versuche=g['versuche'], erreicht=g['erreicht'],
                       gescheitert=g['gescheitert'], abgebrochen=g['abgebrochen'],
                       zeit_s=round(g['zeit_s'], 1),
                       erster_anlauf_s=round(g['erster'] - null, 1),
                       letzter_anlauf_s=round(g['letzter'] - null, 1),
                       abstand_vom_start_m=round(math.dist(start, g['punkt']), 2),
                       nach_erreichen_erneut=g['nach_erreichen_erneut'])
        if tuer is not None:
            eintrag['abstand_tuer_m'] = round(math.dist(tuer, g['punkt']), 2)
        liste.append(eintrag)
    versuche = [g['versuche'] for g in liste]
    gesamt = sum(versuche)
    uebersicht = dict(
        anlaeufe=gesamt, verschiedene_ziele=len(liste),
        wiederholte_anlaeufe=gesamt - len(liste),
        meistversuchtes_ziel=max(versuche) if versuche else 0,
        anteil_der_drei_haeufigsten=(round(sum(sorted(versuche, reverse=True)[:3])/gesamt, 2)
                                     if gesamt else None),
        ziele_nie_erreicht=sum(1 for g in liste if not g['erreicht']),
        zeit_in_nie_erreichten_zielen_s=round(
            sum(g['zeit_s'] for g in liste if not g['erreicht']), 1))
    return liste, uebersicht


def ziel_nummern(anlaeufe):
    """Laufende Nummer je Ziel, in derselben Reihenfolge wie die Zielliste."""
    zahl, erster = Counter(), {}
    for a in anlaeufe:
        key = ziel_schluessel(a['ziel'])
        zahl[key] += 1
        erster.setdefault(key, a['beginn'])
    return {key: nummer for nummer, key in
            enumerate(sorted(zahl, key=lambda k: (-zahl[k], erster[k])), 1)}


def hinter_der_tuer(punkt, startplatz, tuer):
    """Wie weit ein Punkt in Richtung Startplatz→Tür hinter der Tür liegt (m).

    Positiv heißt: vom Startplatz aus gesehen weiter weg als die Tür. Das ist
    eine Näherung ohne Karte; ein Punkt im selben Raum schräg neben der Tür
    kann einen kleinen positiven Wert bekommen.
    """
    weite = math.dist(startplatz, tuer)
    if weite < 1e-6:
        return None
    ex, ey = (tuer[0] - startplatz[0])/weite, (tuer[1] - startplatz[1])/weite
    return (punkt[0] - tuer[0])*ex + (punkt[1] - tuer[1])*ey


def reihenfolge(anlaeufe, gruende, beginn_log, tuer=None):
    """Die Anläufe der Reihe nach, ohne Koordinaten; mit Tür auch ihr Bezug dazu."""
    nummern = ziel_nummern(anlaeufe)
    startplatz = anlaeufe[0]['von'] if anlaeufe else None
    null = beginn_log if beginn_log is not None else (anlaeufe[0]['beginn'] if anlaeufe else 0.0)
    zeilen = []
    for nummer, a in enumerate(anlaeufe, 1):
        zeile = dict(nr=nummer, beginn_s=round(a['beginn'] - null, 1),
                     dauer_s=None if a['dauer_s'] is None else round(a['dauer_s'], 1),
                     ausgang=a['ausgang'], ziel=nummern[ziel_schluessel(a['ziel'])],
                     luftlinie_m=round(a['entfernung_m'], 2), grund=gruende.get(nummer))
        if tuer is not None:
            hinter = hinter_der_tuer(a['ziel'], startplatz, tuer)
            zeile.update(start_tuer_m=round(math.dist(a['von'], tuer), 2),
                         ziel_tuer_m=round(math.dist(a['ziel'], tuer), 2),
                         ziel_hinter_tuer_m=None if hinter is None else round(hinter, 2))
        zeilen.append(zeile)
    return zeilen


def tuerbezug(zeilen):
    """Zusammenfassung: Wo begannen die Anläufe, und wohin wollten sie?"""
    if not zeilen or 'start_tuer_m' not in zeilen[0]:
        return None

    def nach_ausgang(auswahl):
        return dict(Counter(z['ausgang'] for z in auswahl))

    an_tuer = [z for z in zeilen if z['start_tuer_m'] < TUER_NAH_M]
    hinter = [z for z in zeilen if (z['ziel_hinter_tuer_m'] or 0.0) > 0.0]
    zur_tuer = [z for z in zeilen if z['ziel_tuer_m'] < TUER_NAH_M
                and not (z['ziel_hinter_tuer_m'] or 0.0) > 0.0]
    rest = [z for z in zeilen if z not in hinter and z not in zur_tuer]
    return dict(
        nah_m=TUER_NAH_M,
        startplatz_zur_tuer_m=zeilen[0]['start_tuer_m'],
        kleinster_abstand_eines_starts_m=min(z['start_tuer_m'] for z in zeilen),
        anlaeufe_mit_start_an_der_tuer=dict(anzahl=len(an_tuer), ausgang=nach_ausgang(an_tuer)),
        anlaeufe_mit_ziel_hinter_der_tuer=dict(anzahl=len(hinter), ausgang=nach_ausgang(hinter)),
        anlaeufe_mit_ziel_an_der_tuer_davor=dict(anzahl=len(zur_tuer),
                                                 ausgang=nach_ausgang(zur_tuer)),
        anlaeufe_mit_ziel_woanders=dict(anzahl=len(rest), ausgang=nach_ausgang(rest)),
        zeit_mit_start_an_der_tuer_s=round(sum(z['dauer_s'] or 0.0 for z in an_tuer), 1))


def ereignisse_aus(protokoll):
    if 'ereignisse' not in protokoll and isinstance(protokoll.get('fahrtprotokoll'), dict):
        protokoll = protokoll['fahrtprotokoll']
    return sorted(protokoll.get('ereignisse') or [], key=lambda e: e['t_s']), protokoll


def mission_im_protokoll(ereignisse):
    """(Beginn, Ende) der Mission in Protokollzeit."""
    sh = [e for e in ereignisse if e.get('art') == 'selbstheilung']
    beginn = next((e['t_s'] for e in sh if e.get('state') in LAUFEND), None)
    ende = sh[-1]['t_s'] if sh else None
    return beginn, ende


def wartephasen(ereignisse):
    """Phasen, in denen der Explorer wartete: [(Beginn, Ende, Grund)] in Protokollzeit."""
    phasen, offen = [], None
    for e in ereignisse:
        if e.get('art') != 'selbstheilung':
            continue
        wartet = e.get('state') == 'waiting'
        grund = e.get('waiting_for') or 'ohne_angabe'
        if offen is not None and (not wartet or grund != offen[1]):
            phasen.append((offen[0], e['t_s'], offen[1]))
            offen = None
        if wartet and offen is None:
            offen = (e['t_s'], grund)
    if offen is not None:
        letzter = ereignisse[-1]['t_s'] if ereignisse else offen[0]
        phasen.append((offen[0], letzter, offen[1]))
    return phasen


def hwt_phasen(ereignisse):
    """Zeiten, in denen der HWT-Zustand nicht HEALTHY war: [(Beginn, Ende, Zustand)]."""
    wechsel = [e for e in ereignisse if e.get('art') == 'hwt']
    phasen = []
    for i, e in enumerate(wechsel):
        ende = wechsel[i+1]['t_s'] if i+1 < len(wechsel) else (ereignisse[-1]['t_s'])
        if e.get('zustand') not in ('HEALTHY', None):
            phasen.append((e['t_s'], ende, str(e['zustand'])))
    return phasen


def zeitversatz(anlaeufe, ereignisse):
    """Logzeit minus Protokollzeit, geschätzt aus erreichten Zielen oder dem Missionsbeginn."""
    erfolge_log = [a['ende'] for a in anlaeufe if a['ausgang'] == 'erreicht']
    erfolge_prot, bisher = [], 0
    for e in ereignisse:
        n = e.get('goals_reached') if e.get('art') == 'selbstheilung' else None
        if isinstance(n, int) and n > bisher:
            erfolge_prot += [e['t_s']]*(n - bisher)
            bisher = n
    paare = [l - p for l, p in zip(erfolge_log, erfolge_prot)]
    if paare:
        paare.sort()
        return paare[len(paare)//2], f'{len(paare)} erreichte Ziele'
    beginn, _ = mission_im_protokoll(ereignisse)
    if beginn is not None and anlaeufe:
        return anlaeufe[0]['beginn'] - beginn - 2.0, 'Missionsbeginn (ungenau)'
    return None, 'keine Zuordnung'


def heilungen_mit_grund(ereignisse, protokoll):
    """Zeit (Protokoll) und Grund jeder Heilung: Zählerstand gegen den Heilungsverlauf."""
    verlauf = protokoll.get('heilungsverlauf') or []
    zaehler = [e['heals'] for e in ereignisse
               if e.get('art') == 'selbstheilung' and isinstance(e.get('heals'), int)]
    # Der Explorer behält nur die letzten 40 Einträge; ältere Heilungen bleiben ohne Grund.
    fehlend = max(0, (max(zaehler) if zaehler else 0) - len(verlauf))
    heilungen, bisher = [], None
    for e in ereignisse:
        n = e.get('heals') if e.get('art') == 'selbstheilung' else None
        if not isinstance(n, int):
            continue
        if bisher is not None and n > bisher:
            for nummer in range(bisher + 1, n + 1):
                stelle = nummer - 1 - fehlend
                eintrag = verlauf[stelle] if 0 <= stelle < len(verlauf) else {}
                heilungen.append((e['t_s'], eintrag.get('reason')))
        bisher = n
    return heilungen


def abbruchgrund(anlauf, warten, hwt, versatz, heilungen=()):
    """Grund für „Goal canceled“: Zielzeit, EK-1 D, Wartephase oder HWT-Zustand."""
    if anlauf['dauer_s'] is not None and anlauf['dauer_s'] >= ZEITGRENZE_S:
        return 'zielzeit_abgelaufen'
    if versatz is None:
        return 'nicht_zuordenbar'
    t = anlauf['ende'] - versatz
    for t_heilung, grund in heilungen:
        # EK-1 D: Der Explorer bricht nach 45 s ohne Weggewinn selbst ab und
        # verbucht das als Fehlversuch (das Protokoll sieht es bis 2 s später).
        if grund == 'nav_no_progress' and -FENSTER_NACH_S <= t - t_heilung <= 2.0:
            return 'kein_weggewinn'
    for beginn, _, grund in warten:
        if -FENSTER_VOR_S <= beginn - t <= FENSTER_NACH_S:
            return f'warten:{grund}'
    for beginn, _, zustand in hwt:
        if -FENSTER_VOR_S <= beginn - t <= FENSTER_NACH_S:
            return f'hwt:{zustand}'
    return 'kein_warten_im_fenster'


def rueckfahrten_aus_log(eintraege):
    """Rückfahrten des Behavior-Servers: Beginn, Ende und Ausgang (Logzeit)."""
    fahrten, offen = [], None
    for t, _, knoten, meldung in eintraege:
        if knoten != 'behavior_server':
            continue
        if 'Running backup' in meldung:
            if offen is not None:
                fahrten.append(dict(beginn=offen, ende=None, ausgang='offen'))
            offen = t
            continue
        for muster, ausgang in RUECKFAHRT_ENDE:
            if muster in meldung and offen is not None:
                fahrten.append(dict(beginn=offen, ende=t, ausgang=ausgang))
                offen = None
                break
    if offen is not None:
        fahrten.append(dict(beginn=offen, ende=None, ausgang='offen'))
    return fahrten


def grund_im_zeitraum(beginn_log, ende_log, warten, hwt, versatz, rand_s=2.0):
    """Wartephase oder HWT-Zustand, der zwischen Beginn und Ende (Logzeit) begann."""
    if versatz is None or ende_log is None:
        return 'nicht_zuordenbar'
    von, bis = beginn_log - versatz - rand_s, ende_log - versatz + rand_s
    for beginn, _, grund in warten:
        if von <= beginn <= bis:
            return f'warten:{grund}'
    for beginn, _, zustand in hwt:
        if von <= beginn <= bis:
            return f'hwt:{zustand}'
    return 'kein_warten_im_zeitraum'


def phasenliste(warten, hwt, versatz, beginn_log):
    """Warte- und HWT-Phasen der Reihe nach, in Sekunden seit Missionsbeginn."""
    if versatz is None or beginn_log is None:
        return []
    phasen = [(b, e, f'warten:{g}') for b, e, g in warten] + [(b, e, f'hwt:{z}') for b, e, z in hwt]
    return [dict(beginn_s=round(b + versatz - beginn_log, 1), dauer_s=round(e - b, 1), was=was)
            for b, e, was in sorted(phasen)]


def nahbild_zum_zeitpunkt(nahbilder, t_prot, fenster_s=NAHBILD_FENSTER_S):
    """Das Nahbild, das einem Zeitpunkt (Protokollzeit) am nächsten liegt."""
    if not nahbilder:
        return None
    bild = min(nahbilder, key=lambda b: abs(b['t_s'] - t_prot))
    return bild if abs(bild['t_s'] - t_prot) <= fenster_s else None


def reglerhalte(eintraege, nahbilder, versatz, beginn_log):
    """Je „Controller patience exceeded“: was die lokale Karte um den Roboter zeigte."""
    if versatz is None or beginn_log is None:
        return []
    halte = []
    for t, _, knoten, meldung in eintraege:
        if knoten != 'controller_server' or 'Controller patience exceeded' not in meldung:
            continue
        bild = nahbild_zum_zeitpunkt(nahbilder, t - versatz)
        halt = dict(halt_s=round(t - beginn_log, 1), nahbild=bild is not None)
        if bild is not None:
            halt.update({k: bild.get(k) for k in (
                'in_kontur', 'in_kontur_ohne_polster', 'naechste_m', 'seite',
                'links_m', 'rechts_m', 'breite_m')})
        halte.append(halt)
    return halte


def engstellen(nahbilder, versatz, beginn_log):
    """Abschnitte der Fahrt, in denen die Stelle am Roboter schmaler als 0,9 m war."""
    if versatz is None or beginn_log is None:
        return []
    abschnitte, offen = [], None
    for bild in nahbilder:
        eng = bild.get('breite_m') is not None and bild['breite_m'] < ENGSTELLE_M
        if offen is not None and bild['t_s'] - offen['_letzte'] > ENGSTELLE_PAUSE_S:
            abschnitte.append(offen)
            offen = None
        if not eng:
            continue
        if offen is None:
            offen = dict(beginn_s=round(bild['t_s'] + versatz - beginn_log, 1), bilder=0,
                         engste_breite_m=bild['breite_m'], meiste_zellen_in_kontur=0,
                         _erste=bild['t_s'], _letzte=bild['t_s'])
        offen['bilder'] += 1
        offen['_letzte'] = bild['t_s']
        offen['engste_breite_m'] = min(offen['engste_breite_m'], bild['breite_m'])
        offen['meiste_zellen_in_kontur'] = max(offen['meiste_zellen_in_kontur'],
                                               bild.get('in_kontur') or 0)
    if offen is not None:
        abschnitte.append(offen)
    for a in abschnitte:
        a['dauer_s'] = round(a.pop('_letzte') - a.pop('_erste'), 1)
    return abschnitte


def summen(phasen):
    aus = {}
    for beginn, ende, grund in phasen:
        s = aus.setdefault(grund, dict(anzahl=0, summe_s=0.0, laengste_s=0.0))
        s['anzahl'] += 1
        s['summe_s'] = round(s['summe_s'] + (ende - beginn), 1)
        s['laengste_s'] = round(max(s['laengste_s'], ende - beginn), 1)
    return aus


def minuten(anlaeufe, eintraege, warten, kurve, beginn_log, ende_log, versatz):
    """Verlauf je Minute der Mission."""
    if beginn_log is None or ende_log is None or ende_log <= beginn_log:
        return []
    zahl = int((ende_log - beginn_log)//60) + 1
    zeilen = [dict(minute=i + 1, begonnen=0, erreicht=0, gescheitert=0, abgebrochen=0,
                   warten_s=0.0, frei_m2=None, **{name: 0 for name, _ in ZAEHLER})
              for i in range(zahl)]

    def fach(t):
        i = int((t - beginn_log)//60)
        return zeilen[i] if 0 <= i < zahl else None

    for a in anlaeufe:
        z = fach(a['beginn'])
        if z:
            z['begonnen'] += 1
        z = fach(a['ende']) if a['ende'] is not None else None
        if z and a['ausgang'] in z:
            z[a['ausgang']] += 1
    for t, _, _, meldung in eintraege:
        z = fach(t)
        if z:
            for name, muster in ZAEHLER:
                if muster in meldung:
                    z[name] += 1
    if versatz is not None:
        for b, e, _ in warten:
            t = b + versatz
            while t < e + versatz:
                z = fach(t)
                grenze = min(e + versatz, beginn_log + (int((t - beginn_log)//60) + 1)*60)
                if z:
                    z['warten_s'] = round(z['warten_s'] + grenze - t, 1)
                t = grenze
    for punkt in kurve or []:
        i = int(punkt['fahrt_s']//60)
        if 0 <= i < zahl:
            zeilen[i]['frei_m2'] = punkt.get('frei_m2')
    return zeilen


def meldungen(eintraege, beginn_log, anzahl=25):
    """Häufigste Warnungen und Fehler, Zahlen durch # ersetzt."""
    zaehler, erste, letzte = Counter(), {}, {}
    for t, stufe, knoten, meldung in eintraege:
        if stufe not in ('WARN', 'ERROR', 'FATAL'):
            continue
        text = ZAHL.sub('#', meldung)
        text = re.sub(r'\s+', ' ', text).strip()[:150]
        key = (stufe, knoten, text)
        zaehler[key] += 1
        erste.setdefault(key, t)
        letzte[key] = t
    null = beginn_log or 0.0
    return [dict(anzahl=n, stufe=k[0], knoten=k[1], meldung=k[2],
                 erste_min=round((erste[k] - null)/60, 1), letzte_min=round((letzte[k] - null)/60, 1))
            for k, n in zaehler.most_common(anzahl)]


def auszug(eintraege, t_log, halb_s=3.0, hoechstens=40):
    """Logzeilen um einen Zeitpunkt, Koordinatenpaare unkenntlich."""
    zeilen = [f'{t - t_log:+6.2f} s [{stufe}] {knoten}: {PAAR.sub("(…)", meldung)[:200]}'
              for t, stufe, knoten, meldung in eintraege if abs(t - t_log) <= halb_s]
    if len(zeilen) > hoechstens:
        kopf = hoechstens//2
        zeilen = zeilen[:kopf] + [f'   … {len(zeilen) - hoechstens} Zeilen ausgelassen …'] \
            + zeilen[-(hoechstens - kopf):]
    return zeilen


def auswerten(log_text, protokoll, tuer=None):
    eintraege = sorted(log_eintraege(log_text), key=lambda e: e[0])
    anlaeufe = anlaeufe_aus_log(eintraege)
    ereignisse, protokoll = ereignisse_aus(protokoll or {})
    warten, hwt = wartephasen(ereignisse), hwt_phasen(ereignisse)
    versatz, versatz_art = zeitversatz(anlaeufe, ereignisse)
    beginn_p, ende_p = mission_im_protokoll(ereignisse)
    if versatz is not None and beginn_p is not None:
        beginn_log, ende_log = beginn_p + versatz, ende_p + versatz
    elif anlaeufe:
        beginn_log = anlaeufe[0]['beginn']
        ende_log = max(a['ende'] or a['beginn'] for a in anlaeufe)
    else:
        beginn_log = ende_log = None
    zielliste, uebersicht = ziele(anlaeufe, beginn_log, tuer)
    abbrueche = Counter()
    faelle = []
    gruende = {}
    heilungen = heilungen_mit_grund(ereignisse, protokoll)
    for nummer, a in enumerate(anlaeufe, 1):
        if a['ausgang'] != 'abgebrochen':
            continue
        grund = abbruchgrund(a, warten, hwt, versatz, heilungen)
        gruende[nummer] = grund
        abbrueche[grund] += 1
        faelle.append(dict(ende_s=round(a['ende'] - (beginn_log or 0.0), 1),
                           dauer_s=round(a['dauer_s'], 1), grund=grund, _ende=a['ende']))
    kurve = protokoll.get('abdeckungskurve')
    spitzen = [s for s in ((protokoll.get('wackeln') or {}).get('staerkste_sekunden') or [])
               if s.get('radps', 0) >= 0.1]
    auszuege = []
    for fall in faelle[:6]:
        auszuege.append(dict(anlass=f"Abbruch bei {fall['ende_s']} s ({fall['grund']})",
                             zeilen=auszug(eintraege, fall['_ende'])))
    if versatz is not None:
        gesehen = []
        for s in spitzen:
            if all(abs(s['t_s'] - g) > 5.0 for g in gesehen):
                gesehen.append(s['t_s'])
                t_log = s['t_s'] + versatz
                auszuege.append(dict(
                    anlass=(f"Wackelspitze {s['radps']} rad/s bei "
                            f"{round(t_log - beginn_log, 1)} s (Lage {s.get('lage')})"),
                    zeilen=auszug(eintraege, t_log)))
    for fall in faelle:
        del fall['_ende']
    dauer = None if beginn_log is None else round(ende_log - beginn_log, 1)
    nahbilder = protokoll.get('nahbilder') or []
    der_reihe_nach = reihenfolge(anlaeufe, gruende, beginn_log, tuer)
    rueckfahrten = []
    for r in rueckfahrten_aus_log(eintraege):
        rueckfahrten.append(dict(
            beginn_s=round(r['beginn'] - (beginn_log or 0.0), 1),
            dauer_s=None if r['ende'] is None else round(r['ende'] - r['beginn'], 1),
            ausgang=r['ausgang'],
            grund=(grund_im_zeitraum(r['beginn'], r['ende'], warten, hwt, versatz)
                   if r['ausgang'] == 'abgebrochen' else None)))
    drittel = None
    if kurve:
        ende_frei = kurve[-1]['frei_m2']
        erfasst = next((p['fahrt_s'] for p in kurve if ende_frei and p['frei_m2'] >= .85*ende_frei),
                       None)
        if erfasst is not None and beginn_log is not None:
            danach = [a for a in anlaeufe if a['beginn'] - beginn_log >= erfasst]
            drittel = dict(raum_zu_85_prozent_erfasst_nach_s=erfasst,
                           anlaeufe_danach=len(danach),
                           davon_erreicht=sum(a['ausgang'] == 'erreicht' for a in danach),
                           flaeche_danach_m2=round(ende_frei - next(
                               p['frei_m2'] for p in kurve if p['fahrt_s'] >= erfasst), 2))
    return dict(
        dauer_s=dauer, zeitzuordnung=versatz_art,
        ziele_uebersicht=uebersicht, ziele=zielliste,
        ausgaenge=dict(Counter(a['ausgang'] for a in anlaeufe)),
        abbruchgruende=dict(abbrueche), abbrueche=faelle,
        warten=summen(warten), hwt_nicht_gesund=summen(hwt),
        warten_gesamt_s=round(sum(e - b for b, e, _ in warten), 1),
        nach_dem_erfassen=drittel,
        anlaeufe=der_reihe_nach, tuerbezug=tuerbezug(der_reihe_nach),
        phasen=phasenliste(warten, hwt, versatz, beginn_log), rueckfahrten=rueckfahrten,
        nahbild=protokoll.get('nahbild'),
        reglerhalte=reglerhalte(eintraege, nahbilder, versatz, beginn_log),
        engstellen=engstellen(nahbilder, versatz, beginn_log),
        minuten=minuten(anlaeufe, eintraege, warten, kurve, beginn_log, ende_log, versatz),
        haeufigste_meldungen=meldungen(eintraege, beginn_log),
        auszuege=auszuege)


def text(ergebnis):
    """Kurzfassung als Text (ohne Koordinaten)."""
    z = ergebnis['ziele_uebersicht']
    aus = [f"Dauer {ergebnis['dauer_s']} s; Zeitzuordnung über {ergebnis['zeitzuordnung']}",
           f"Anläufe {z['anlaeufe']} auf {z['verschiedene_ziele']} verschiedene Ziele; "
           f"wiederholt {z['wiederholte_anlaeufe']}; häufigstes Ziel {z['meistversuchtes_ziel']}×; "
           f"Anteil der drei häufigsten {z['anteil_der_drei_haeufigsten']}",
           f"Ausgänge {ergebnis['ausgaenge']}",
           f"Abbruchgründe {ergebnis['abbruchgruende']}",
           f"Warten gesamt {ergebnis['warten_gesamt_s']} s: {ergebnis['warten']}",
           f"HWT nicht HEALTHY: {ergebnis['hwt_nicht_gesund']}",
           f"Nach dem Erfassen des Raums: {ergebnis['nach_dem_erfassen']}", '',
           'Ziel  Vers. erreicht gesch. abgebr.  Zeit s  erster s  letzter s  vom Start m'
           + ('  zur Tür m' if ergebnis['ziele'] and 'abstand_tuer_m' in ergebnis['ziele'][0] else '')]
    for g in ergebnis['ziele']:
        zeile = (f"{g['ziel']:4d} {g['versuche']:6d} {g['erreicht']:8d} {g['gescheitert']:6d} "
                 f"{g['abgebrochen']:7d} {g['zeit_s']:7.1f} {g['erster_anlauf_s']:9.1f} "
                 f"{g['letzter_anlauf_s']:10.1f} {g['abstand_vom_start_m']:12.2f}")
        if 'abstand_tuer_m' in g:
            zeile += f"{g['abstand_tuer_m']:11.2f}"
        aus.append(zeile)
    mit_tuer = bool(ergebnis['anlaeufe']) and 'start_tuer_m' in ergebnis['anlaeufe'][0]
    aus += ['', 'Anläufe der Reihe nach (der Start eines Anlaufs ist die Stelle, an der der vorige endete):',
            '  Nr  Beginn s  Dauer s  Ausgang      Ziel  Luftlinie m'
            + ('  Start→Tür m  Ziel→Tür m  Ziel hinter Tür m' if mit_tuer else '') + '  Grund']
    for a in ergebnis['anlaeufe']:
        dauer = '      -' if a['dauer_s'] is None else f"{a['dauer_s']:7.1f}"
        zeile = (f"{a['nr']:4d} {a['beginn_s']:9.1f} {dauer}  {a['ausgang']:<11s} "
                 f"{a['ziel']:5d} {a['luftlinie_m']:12.2f}")
        if mit_tuer:
            hinter = '      -' if a['ziel_hinter_tuer_m'] is None else f"{a['ziel_hinter_tuer_m']:+7.2f}"
            zeile += f"{a['start_tuer_m']:13.2f}{a['ziel_tuer_m']:12.2f}{hinter:>19s}"
        aus.append(zeile + (f"  {a['grund']}" if a['grund'] else ''))
    if ergebnis['tuerbezug']:
        t = ergebnis['tuerbezug']
        aus += ['', f"Türbezug (an der Tür = näher als {t['nah_m']} m; „hinter der Tür“ ist eine "
                    'Näherung in Richtung Startplatz→Tür):',
                f"  Startplatz zur Tür {t['startplatz_zur_tuer_m']} m; kleinster Abstand eines "
                f"Starts {t['kleinster_abstand_eines_starts_m']} m",
                f"  Start an der Tür: {t['anlaeufe_mit_start_an_der_tuer']}; Zeit in diesen "
                f"Anläufen {t['zeit_mit_start_an_der_tuer_s']} s",
                f"  Ziel hinter der Tür: {t['anlaeufe_mit_ziel_hinter_der_tuer']}",
                f"  Ziel an der Tür, davor: {t['anlaeufe_mit_ziel_an_der_tuer_davor']}",
                f"  Ziel woanders: {t['anlaeufe_mit_ziel_woanders']}"]
    aus += ['', 'Rückfahrten (Beginn s, Dauer s, Ausgang, Grund eines Abbruchs):']
    for r in ergebnis['rueckfahrten']:
        dauer = '-' if r['dauer_s'] is None else f"{r['dauer_s']:.1f}"
        aus.append(f"  {r['beginn_s']:8.1f} {dauer:>6s}  {r['ausgang']}"
                   + (f"  {r['grund']}" if r['grund'] else ''))
    phasen = ergebnis['phasen']
    aus += ['', f'Warte- und HWT-Phasen der Reihe nach ({len(phasen)}; Beginn s, Dauer s, was):']
    for ph in phasen[:PHASEN_HOECHSTENS]:
        aus.append(f"  {ph['beginn_s']:8.1f} {ph['dauer_s']:6.1f}  {ph['was']}")
    if len(phasen) > PHASEN_HOECHSTENS:
        aus.append(f'  … {len(phasen) - PHASEN_HOECHSTENS} weitere ausgelassen (stehen im JSON)')
    aus += ['', f"Nahbild (lokale Karte bis 0,8 m um den Roboter, einmal je Sekunde): "
                f"{ergebnis['nahbild'] or 'keine Daten (Fahrtprotokoll vor Schema 3)'}"]
    if ergebnis['engstellen']:
        aus.append(f'Engstellen (Breite am Roboter unter {ENGSTELLE_M} m): '
                   'Beginn s, Dauer s, engste Breite m, meiste tödliche Zellen in der Kontur')
        for e in ergebnis['engstellen']:
            aus.append(f"  {e['beginn_s']:8.1f} {e['dauer_s']:6.1f} {e['engste_breite_m']:6.2f} "
                       f"{e['meiste_zellen_in_kontur']:4d}")
    if ergebnis['reglerhalte']:
        aus.append('Reglerhalte („Controller patience exceeded“): Zeit s, tödliche Zellen in der '
                   'Kontur mit / ohne Polster, nächste Zelle m und Seite, frei links m, frei '
                   'rechts m, Breite m')

        def zahl(wert):
            return '   -' if wert is None else f'{wert:4.2f}'

        for h in ergebnis['reglerhalte']:
            if not h['nahbild']:
                aus.append(f"  {h['halt_s']:8.1f}  kein Nahbild in der Nähe")
                continue
            aus.append(f"  {h['halt_s']:8.1f} {h['in_kontur']:3d} / {h['in_kontur_ohne_polster']:<3d} "
                       f"{zahl(h['naechste_m'])} {(h['seite'] or '-'):<13s} "
                       f"{zahl(h['links_m'])} {zahl(h['rechts_m'])} {zahl(h['breite_m'])}")
    aus += ['', 'Min. beg. err. gesch. abgebr. warten s  frei m²  Koll.voraus Geduld TF-Zuk. '
                'TF-Pose Takt Queue kein Weg Rückf.']
    for m in ergebnis['minuten']:
        frei = '      -' if m['frei_m2'] is None else f"{m['frei_m2']:7.2f}"
        aus.append(f"{m['minute']:4d} {m['begonnen']:4d} {m['erreicht']:4d} {m['gescheitert']:6d} "
                   f"{m['abgebrochen']:7d} {m['warten_s']:8.1f} {frei} {m['kollision_voraus']:12d} "
                   f"{m['geduld_regler']:6d} {m['tf_zukunft']:7d} {m['tf_pose']:7d} "
                   f"{m['takt_verfehlt']:4d} {m['queue_voll']:5d} {m['planer_kein_weg']:8d} "
                   f"{m['rueckfahrt']:6d}")
    aus += ['', 'Häufigste Warnungen und Fehler (Zahlen als #):']
    for m in ergebnis['haeufigste_meldungen']:
        aus.append(f"{m['anzahl']:6d}× [{m['stufe']}] {m['knoten']}: {m['meldung']} "
                   f"(Minute {m['erste_min']}–{m['letzte_min']})")
    for a in ergebnis['auszuege']:
        aus += ['', f"Auszug: {a['anlass']}"] + ['  ' + z for z in a['zeilen']]
    return '\n'.join(aus)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--log', nargs='+', required=True, help='launch.log der Fahrt')
    parser.add_argument('--protokoll', help='protokoll.json des Fahrtprotokolls')
    parser.add_argument('--tuer', nargs=2, type=float, metavar=('X', 'Y'),
                        help='Punkt in der Tür (Kartenrahmen dieser Fahrt); bleibt lokal, '
                             'ausgegeben wird nur der Abstand der Ziele dazu')
    parser.add_argument('--json', help='Ergebnis zusätzlich als JSON (lokal, nicht ins Repo)')
    args = parser.parse_args(argv)
    log_text = ''
    for pfad in args.log:
        with open(pfad, 'r', encoding='utf-8', errors='replace') as handle:
            log_text += handle.read() + '\n'
    protokoll = None
    if args.protokoll:
        with open(args.protokoll, 'r', encoding='utf-8') as handle:
            protokoll = json.load(handle)
    ergebnis = auswerten(log_text, protokoll, tuple(args.tuer) if args.tuer else None)
    print(text(ergebnis))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == '__main__':
    sys.exit(main())
