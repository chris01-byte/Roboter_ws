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


def abbruchgrund(anlauf, warten, hwt, versatz):
    """Grund für „Goal canceled“: Wartephase oder HWT-Zustand, der dabei begann."""
    if anlauf['dauer_s'] is not None and anlauf['dauer_s'] >= ZEITGRENZE_S:
        return 'zielzeit_abgelaufen'
    if versatz is None:
        return 'nicht_zuordenbar'
    t = anlauf['ende'] - versatz
    for beginn, _, grund in warten:
        if -FENSTER_VOR_S <= beginn - t <= FENSTER_NACH_S:
            return f'warten:{grund}'
    for beginn, _, zustand in hwt:
        if -FENSTER_VOR_S <= beginn - t <= FENSTER_NACH_S:
            return f'hwt:{zustand}'
    return 'kein_warten_im_fenster'


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
    for a in anlaeufe:
        if a['ausgang'] != 'abgebrochen':
            continue
        grund = abbruchgrund(a, warten, hwt, versatz)
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
