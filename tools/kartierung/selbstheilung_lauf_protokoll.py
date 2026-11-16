#!/usr/bin/env python3
"""Rein lesendes Fahrtprotokoll für eine Laborfahrt im Selbstheilungsbetrieb.

Konzept: docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md §11 (Abnahmestufe 1).

Vor dem Missionsstart starten. Das Werkzeug abonniert nur Status- und
Messtopics, publiziert nichts und ruft keinen Dienst auf. Es endet von selbst
einige Sekunden nach dem Missionsende (oder nach --max-s / Strg-C) und
schreibt eine JSON-Zusammenfassung:

  - Zustandsfolge des Selbstheilungsbetriebs (Ziele, Heilungen, Warten,
    Umsehen, Spurrückfahrt, Endzustand und Grund),
  - HWT-Erholungszustände, Not-Aus-Wechsel, Tempolimit-Wechsel,
  - Fahrbefehle auf /cmd_vel (Maximum), gefahrene Strecke laut /odom,
  - jede Rückwärtsfahrt (v < 0 auf /cmd_vel; RPP fährt nie rückwärts, also
    nur BackUp): Beginn, Dauer, kleinste Geschwindigkeit und die dabei laut
    /odom zurückgelegte Strecke (SH-8: 7 von 8 Rückfahrten an der Zeitgrenze),
  - Tempo-Folge (ab 15.11.2026): befohlener Weg und Drehwinkel (Integral der
    Befehle auf /cmd_vel während der Mission) gegen gefahrenen Weg und
    Drehwinkel laut /odom. Anlass: Bis AT-2 setzte der Antrieb nur etwa ein
    Fünftel um; diese Zahl zeigt in jeder Fahrt, ob er den Befehlen folgt,
  - Wackeln (ab 15.11.2026): Drehrate um die beiden waagerechten Achsen aus
    dem HWT601 (/shadow/hwt601/imu/data_raw), in Ruhe vor der Mission und
    während der Fahrt, dazu die stärksten Sekunden mit dem Befehl dabei.
    Anlass: Christopher sah in AT-2 Ruckeln beim Anfahren; bisher gab es
    dafür keine Messgröße. Fehlt das Topic, steht dort „keine Daten“, und
    das Werkzeug meldet es schon beim Start („Messquelle Wackeln: FEHLT“).
    In SH-8c blieb die Messung leer, weil hier der Name aus dem allgemeinen
    Profil stand statt des Namens im laufenden Stack,
  - Lücken im VL53-Status (länger als 0,8 s),
  - Abdeckungskurve: freie, belegte und bekannte Kartenfläche alle 30 s
    während der Fahrt und die Zeit, bis 85/90/95 % der freien Endfläche
    erreicht waren (Fahrplan MASTERPLAN §9, 09.11.2026),
  - Nahbild (ab 16.11.2026): einmal je Sekunde die tödlichen Zellen der
    lokalen Kostenkarte bis 0,8 m um den Roboter, in Roboterkoordinaten
    (vor, links, in cm), dazu wie viele in der Kontur liegen, der freie Platz
    links und rechts und die Breite der Stelle. Anlass: In W-1 hielt der
    Regler an der Tür an („collision ahead“), und niemand konnte sagen, was
    er dort sah; die gesicherte Karte war veraltet. Keine Kartenkoordinaten,
  - die automatisch prüfbaren Kriterien der Abnahmestufe 1,
  - mit --stellprobe-m: Stellprobe (MASTERPLAN §9, Regel 6). Gemessen wird
    die Entfernung vom Standort beim Missionsstart; das Protokoll endet,
    sobald sie erreicht ist (plus Nachlauf) oder das Fenster abgelaufen ist.

Kontaktfreiheit, Eingriffe und der Nav2-Zustand nach der Fahrt sind
Beobachtungen bzw. eigene Prüfungen und stehen als „manuell“ im Ergebnis.
"""

import argparse
import json
import math
import os
import sys
import time


TERMINAL = ('success', 'partial', 'blocked', 'failed', 'canceled')
SAUBERES_ENDE = ('exploration_complete', 'usable_partial', 'blocked_help_required')
VL53_LUECKE_S = 0.8
RUECKFAHRT_PAUSE_S = 1.0     # so lange ohne v < 0, dann gilt die Rückfahrt als beendet
BEFEHL_MAX_DT_S = 0.25       # länger gilt ein Befehl an der Basis nicht (Watchdog)
WACKELN_NAH_S = 1.5          # so lange nach Anfahren/Anhalten zählt eine Spitze dazu
WACKELN_SPITZEN = 5
IMU_TOPIC = '/shadow/hwt601/imu/data_raw'   # so heißt es im laufenden HWT-Stack
WEG_SCHRITT_M = 0.005        # gefahrener Weg zählt in Schritten ab dieser Größe
DREH_SCHRITT_RAD = 0.02      # ebenso die Drehung (Messrauschen summiert sich sonst auf)
ABDECKUNG_TAKT_S = 30.0
NAHBILD_TAKT_S = 1.0         # so oft wird die lokale Karte um den Roboter festgehalten
NAHBILD_UMKREIS_M = 0.8      # tödliche Zellen bis zu diesem Abstand von base_link
# Kontur wie in nav2_params_real.yaml (lokale Kostenkarte) und ihr Polster.
KONTUR_VORN_M, KONTUR_HINTEN_M, KONTUR_HALB_M, KONTUR_POLSTER_M = 0.31, 0.11, 0.23, 0.02
KOSTEN_TOEDLICH = 100
ABDECKUNG_ANTEILE = (0.85, 0.90, 0.95)
MANUELL = (
    'kein Kontakt mit Hindernissen oder Wänden (Beobachtung Christopher)',
    'kein Eingriff: kein Stopp, kein Not-Aus, kein Umsetzen (Beobachtung Christopher)',
    'Nav2 nach der Fahrt in einem klaren Zustand (ros2 lifecycle get)',
    'kein Absturz: kein "process has died" im launch.log',
)


class LaufProtokoll:
    """Sammelt Ereignisse einer Fahrt; ohne ROS testbar."""

    def __init__(self, start):
        self.start = start
        self.ereignisse = []
        self.self_healing = None
        self.explore_status = None
        self.gestartet_um = None
        self.beendet_um = None
        self._sh_schluessel = None
        self._mission_zustand = None
        self.mission_letzter = None
        self.estop = None
        self.estop_aktiv_waehrend_fahrt = False
        self.tempolimit = None
        self.cmd = dict(nachrichten=0, ungleich_null=0, max_v=0.0, max_w=0.0)
        self.odom_letzte = None
        self.strecke_m = 0.0
        self.rueckfahrten = []
        self._rueckfahrt = None          # offene Rückwärtsfahrt
        # Tempo-Folge: Befehl gegen Odometrie, nur während der Mission.
        self.folge = dict(befohlen_m=0.0, gefahren_m=0.0, befohlen_rad=0.0, gedreht_rad=0.0,
                          gefahren_roh_m=0.0, gedreht_roh_rad=0.0)
        self._cmd_letzter = None         # (t, v, w)
        self._gier_letzte = None
        self._weg_anker = None           # Punkt, ab dem der nächste Wegschritt zählt
        self._gier_anker = None
        self._anfahren_um = None
        self._anhalten_um = None
        # Wackeln: Drehrate um die waagerechten Achsen.
        self.wackeln_ruhe = dict(n=0, quadrate=0.0, max=0.0)
        self.wackeln_fahrt = dict(n=0, quadrate=0.0, max=0.0)
        self._wackeln_sekunden = {}      # Sekunde der Mission -> stärkster Wert
        self.vl53_letzte = None
        self.vl53_luecken = 0
        self.vl53_max_luecke_s = 0.0
        self.hwt_zustand = None
        self.abdeckung = []
        self._abdeckung_letzte = None
        # Nahbild: tödliche Zellen der lokalen Karte um den Roboter (W-1N: an der
        # Tür fehlte das Bild dessen, was den Regler anhielt).
        self.nahbilder = []
        self._nahbild_letztes = None
        # Stellprobe: Entfernung vom Standort beim Missionsstart.
        self.stellprobe_start = None
        self.stellprobe_max_m = 0.0
        self.stellprobe_weg = None       # dict beim ersten Erreichen der Schwelle
        self.stellprobe_weg_um = None

    def _t(self, t):
        return round(t - self.start, 2)

    def _ereignis(self, t, art, **daten):
        self.ereignisse.append(dict(t_s=self._t(t), art=art, **daten))

    def faehrt(self):
        return self.gestartet_um is not None and self.beendet_um is None

    # --- Eingänge -------------------------------------------------------
    def explore(self, status, t):
        self.explore_status = status
        hwt = status.get('hwt_recovery_state')
        if hwt is not None and hwt != self.hwt_zustand:
            self._ereignis(t, 'hwt', zustand=hwt, vorher=self.hwt_zustand)
            self.hwt_zustand = hwt
        sh = status.get('self_healing')
        if not isinstance(sh, dict):
            return
        self.self_healing = sh
        zustand = sh.get('state')
        schluessel = tuple(sh.get(k) for k in (
            'state', 'reason', 'waiting_for', 'goals_reached', 'heals',
            'deferred_goals', 'track_backs', 'look_arounds'))
        if schluessel != self._sh_schluessel:
            self._sh_schluessel = schluessel
            self._ereignis(t, 'selbstheilung', **{k: sh.get(k) for k in (
                'state', 'outcome', 'reason', 'waiting_for', 'goals_reached', 'heals',
                'deferred_goals', 'track_backs', 'look_arounds')})
        if zustand in ('running', 'waiting', 'checking_completion') and self.gestartet_um is None:
            self.gestartet_um = t
        if zustand in TERMINAL and self.gestartet_um is not None and self.beendet_um is None:
            self.beendet_um = t

    def mission(self, status, t):
        self.mission_letzter = status
        zustand = status.get('state')
        if zustand != self._mission_zustand:
            self._ereignis(t, 'mission', zustand=zustand)
            self._mission_zustand = zustand

    def estop_wert(self, aktiv, t):
        if aktiv != self.estop:
            self._ereignis(t, 'not_aus', aktiv=aktiv)
            self.estop = aktiv
        if aktiv and self.faehrt():
            self.estop_aktiv_waehrend_fahrt = True

    def tempo(self, limit, t):
        limit = round(float(limit), 3)
        if limit != self.tempolimit:
            self._ereignis(t, 'tempolimit', mps=limit)
            self.tempolimit = limit

    def cmd_vel(self, v, w, t=None):
        self.cmd['nachrichten'] += 1
        if v != 0.0 or w != 0.0:
            self.cmd['ungleich_null'] += 1
        self.cmd['max_v'] = max(self.cmd['max_v'], abs(v))
        self.cmd['max_w'] = max(self.cmd['max_w'], abs(w))
        if t is None:
            return
        letzter = self._cmd_letzter
        if letzter is not None:
            if self.faehrt():
                dt = min(t - letzter[0], BEFEHL_MAX_DT_S)
                self.folge['befohlen_m'] += abs(letzter[1])*dt
                self.folge['befohlen_rad'] += abs(letzter[2])*dt
            stand, steht = (letzter[1] == 0.0 and letzter[2] == 0.0), (v == 0.0 and w == 0.0)
            if stand and not steht:
                self._anfahren_um = t
            elif steht and not stand:
                self._anhalten_um = t
        elif v != 0.0 or w != 0.0:
            self._anfahren_um = t
        self._cmd_letzter = (t, v, w)
        if v < -1e-4:
            r = self._rueckfahrt
            if r is None:
                self._rueckfahrt = dict(start=t, letzte=t, start_xy=self.odom_letzte,
                                        v_min=v, befehle=1)
            else:
                r['letzte'] = t
                r['v_min'] = min(r['v_min'], v)
                r['befehle'] += 1
        else:
            self._rueckfahrt_pruefen(t)

    def _rueckfahrt_pruefen(self, t, erzwingen=False):
        r = self._rueckfahrt
        if r is None or not (erzwingen or t - r['letzte'] > RUECKFAHRT_PAUSE_S):
            return
        self._rueckfahrt = None
        strecke = (None if r['start_xy'] is None or self.odom_letzte is None
                   else round(math.dist(r['start_xy'], self.odom_letzte), 3))
        eintrag = dict(t_s=self._t(r['start']), dauer_s=round(r['letzte'] - r['start'], 1),
                       v_min=round(r['v_min'], 3), befehle=r['befehle'],
                       strecke_odom_m=strecke)
        self.rueckfahrten.append(eintrag)
        self._ereignis(r['start'], 'rueckfahrt', **{k: v for k, v in eintrag.items()
                                                    if k != 't_s'})

    def odom(self, x, y, t=None, gier=None):
        if not (math.isfinite(x) and math.isfinite(y)):
            return
        if self.odom_letzte is not None:
            schritt = math.dist(self.odom_letzte, (x, y))
            if schritt < 0.5:          # Sprünge (Neustart, Reset) nicht addieren
                self.strecke_m += schritt
                if self.faehrt():
                    self.folge['gefahren_roh_m'] += schritt
            else:
                self._weg_anker = None
        self.odom_letzte = (x, y)
        # Weg in Schritten ab 5 mm: Zittern der Position im Stand oder beim
        # Drehen summiert sich so nicht zu Weg auf (SH-8c s1a: 2,35 roh).
        if not self.faehrt() or self._weg_anker is None:
            self._weg_anker = (x, y)
        else:
            schritt = math.dist(self._weg_anker, (x, y))
            if schritt >= WEG_SCHRITT_M:
                self.folge['gefahren_m'] += schritt
                self._weg_anker = (x, y)
        if gier is not None and math.isfinite(gier):
            def differenz(a, b):
                return abs(math.atan2(math.sin(a - b), math.cos(a - b)))
            if self._gier_letzte is not None and self.faehrt():
                dreh = differenz(gier, self._gier_letzte)
                if dreh < 0.5:
                    self.folge['gedreht_roh_rad'] += dreh
            self._gier_letzte = gier
            if not self.faehrt() or self._gier_anker is None:
                self._gier_anker = gier
            else:
                dreh = differenz(gier, self._gier_anker)
                if dreh >= 0.5:
                    self._gier_anker = gier
                elif dreh >= DREH_SCHRITT_RAD:
                    self.folge['gedreht_rad'] += dreh
                    self._gier_anker = gier
        if t is not None:
            self._rueckfahrt_pruefen(t)

    def imu(self, rate_x, rate_y, t):
        """Drehrate um die beiden waagerechten Achsen (Nicken und Rollen)."""
        wert = math.hypot(rate_x, rate_y)
        if not math.isfinite(wert):
            return
        if self.faehrt():
            ziel = self.wackeln_fahrt
            sekunde = int(t - self.gestartet_um)
            bisher = self._wackeln_sekunden.get(sekunde)
            if bisher is None or wert > bisher['radps']:
                cmd = self._cmd_letzter or (t, 0.0, 0.0)
                if self._anfahren_um is not None and 0 <= t - self._anfahren_um <= WACKELN_NAH_S:
                    lage = 'anfahren'
                elif self._anhalten_um is not None and 0 <= t - self._anhalten_um <= WACKELN_NAH_S:
                    lage = 'anhalten'
                elif cmd[1] == 0.0 and cmd[2] == 0.0:
                    lage = 'steht'
                else:
                    lage = 'fahrt'
                self._wackeln_sekunden[sekunde] = dict(
                    t_s=self._t(t), radps=wert, v=cmd[1], w=cmd[2], lage=lage)
        elif self.gestartet_um is None:
            ziel = self.wackeln_ruhe
        else:
            return
        ziel['n'] += 1
        ziel['quadrate'] += wert*wert
        ziel['max'] = max(ziel['max'], wert)

    def tempo_folge(self):
        f = self.folge
        return {
            'befohlener_weg_m': round(f['befohlen_m'], 2),
            'gefahrener_weg_m': round(f['gefahren_m'], 2),
            'weg_gefahren_zu_befohlen': (round(f['gefahren_m']/f['befohlen_m'], 2)
                                         if f['befohlen_m'] >= 0.2 else None),
            'befohlene_drehung_rad': round(f['befohlen_rad'], 2),
            'gedrehte_drehung_rad': round(f['gedreht_rad'], 2),
            'drehung_gedreht_zu_befohlen': (round(f['gedreht_rad']/f['befohlen_rad'], 2)
                                            if f['befohlen_rad'] >= 0.3 else None),
            # Summe aller Einzelschritte ohne Schwelle; liegt sie deutlich über
            # dem Wert oben, zittert die Odometrie.
            'gefahrener_weg_roh_m': round(f['gefahren_roh_m'], 2),
            'gedrehte_drehung_roh_rad': round(f['gedreht_roh_rad'], 2),
        }

    def wackeln(self):
        def kennwerte(z):
            if not z['n']:
                return None
            return {'messwerte': z['n'], 'rms_radps': round(math.sqrt(z['quadrate']/z['n']), 4),
                    'max_radps': round(z['max'], 4)}
        if not self.wackeln_ruhe['n'] and not self.wackeln_fahrt['n']:
            return {'daten': 'keine Daten'}
        spitzen = sorted(self._wackeln_sekunden.values(), key=lambda e: -e['radps'])
        zaehler = {}
        for eintrag in self._wackeln_sekunden.values():
            zaehler[eintrag['lage']] = max(zaehler.get(eintrag['lage'], 0.0), eintrag['radps'])
        return {
            'groesse': 'Betrag der Drehrate um die beiden waagerechten Achsen, rad/s',
            'ruhe_vor_der_mission': kennwerte(self.wackeln_ruhe),
            'waehrend_der_mission': kennwerte(self.wackeln_fahrt),
            'staerkste_je_lage_radps': {k: round(v, 4) for k, v in sorted(zaehler.items())},
            'staerkste_sekunden': [
                {k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items()}
                for e in spitzen[:WACKELN_SPITZEN]],
        }

    def stellprobe(self, x, y, t, schwelle_m):
        """Entfernung vom Standort beim Missionsstart; merkt das erste Erreichen."""
        if not self.faehrt() or not (math.isfinite(x) and math.isfinite(y)):
            return
        if self.stellprobe_start is None:
            self.stellprobe_start = (x, y)
        entfernung = math.dist(self.stellprobe_start, (x, y))
        self.stellprobe_max_m = max(self.stellprobe_max_m, entfernung)
        if schwelle_m > 0 and entfernung >= schwelle_m and self.stellprobe_weg is None:
            sh = self.self_healing or {}
            self.stellprobe_weg_um = t
            self.stellprobe_weg = dict(
                nach_s=round(t - self.gestartet_um, 1), entfernung_m=round(entfernung, 3),
                heilungen_bis_dahin=sh.get('heals'), rueckfahrten_bis_dahin=sh.get('track_backs'),
                ziele_bis_dahin=sh.get('goals_reached'))

    def stellprobe_ergebnis(self, schwelle_m):
        """befreit / nicht_blockiert / nicht_befreit; None ohne Stellprobe oder Fahrt."""
        if schwelle_m <= 0 or self.gestartet_um is None:
            return None
        weg = self.stellprobe_weg
        if weg is None:
            urteil = 'nicht_befreit'
        elif not weg['heilungen_bis_dahin']:
            urteil = 'nicht_blockiert'     # ohne Heilung weggefahren: Stelle sagt nichts aus
        else:
            urteil = 'befreit'
        return dict(schwelle_m=schwelle_m, urteil=urteil, weg=weg,
                    max_entfernung_m=round(self.stellprobe_max_m, 3))

    def vl53(self, t):
        if self.vl53_letzte is not None and self.faehrt():
            luecke = t - self.vl53_letzte
            if luecke > VL53_LUECKE_S:
                self.vl53_luecken += 1
                self.vl53_max_luecke_s = max(self.vl53_max_luecke_s, luecke)
                self._ereignis(t, 'vl53_luecke', dauer_s=round(luecke, 3))
        self.vl53_letzte = t

    def karte(self, werte, aufloesung, t):
        """Abdeckungskurve: höchstens alle 30 s und nur während der Fahrt."""
        if not self.faehrt() or not aufloesung > 0:
            return
        if self._abdeckung_letzte is not None and t - self._abdeckung_letzte < ABDECKUNG_TAKT_S:
            return
        self._abdeckung_letzte = t
        self.abdeckung.append(dict(t_s=self._t(t),
                                   fahrt_s=round(t - self.gestartet_um, 1),
                                   **flaechen(werte, aufloesung)))

    def lokale_karte(self, werte, breite, hoehe, aufloesung, ursprung, t):
        """Nahbild: höchstens einmal je Sekunde und nur während der Fahrt."""
        if not self.faehrt() or self.odom_letzte is None or self._gier_letzte is None:
            return
        if self._nahbild_letztes is not None and t - self._nahbild_letztes < NAHBILD_TAKT_S:
            return
        bild = nahbild(werte, breite, hoehe, aufloesung, ursprung,
                       (self.odom_letzte[0], self.odom_letzte[1], self._gier_letzte))
        if bild is None:
            return
        self._nahbild_letztes = t
        befehl = self._cmd_letzter
        frisch = befehl is not None and t - befehl[0] <= BEFEHL_MAX_DT_S
        self.nahbilder.append(dict(
            t_s=self._t(t), fahrt_s=round(t - self.gestartet_um, 1),
            befehl=[round(befehl[1], 3), round(befehl[2], 3)] if frisch else None, **bild))

    def nahbild_uebersicht(self):
        """Wie oft tödliche Zellen in der Kontur lagen und wie eng es war."""
        if not self.nahbilder:
            return None
        breiten = sorted(b['breite_m'] for b in self.nahbilder if b['breite_m'] is not None)
        return dict(
            bilder=len(self.nahbilder),
            mit_zellen_in_gepolsterter_kontur=sum(b['in_kontur'] > 0 for b in self.nahbilder),
            mit_zellen_in_kontur_ohne_polster=sum(
                b['in_kontur_ohne_polster'] > 0 for b in self.nahbilder),
            engste_breite_am_roboter_m=breiten[0] if breiten else None,
            bilder_mit_breite_unter_0_9_m=sum(b < 0.9 for b in breiten))

    def abdeckung_zeiten(self):
        """Fahrzeit bis zu 85/90/95 % der freien Fläche am Ende (Endfläche = 100 %)."""
        if not self.abdeckung:
            return None
        ende = self.abdeckung[-1]['frei_m2']
        zeiten = {}
        for anteil in ABDECKUNG_ANTEILE:
            treffer = [p['fahrt_s'] for p in self.abdeckung
                       if ende > 0 and p['frei_m2'] >= anteil*ende]
            zeiten[f'{int(anteil*100)}_prozent_s'] = treffer[0] if treffer else None
        return dict(frei_ende_m2=ende, **zeiten)

    # --- Ergebnis -------------------------------------------------------
    def kriterien(self):
        sh = self.self_healing or {}
        ziele = sh.get('goals_reached') or 0
        return {
            'fahrt_begonnen': self.gestartet_um is not None,
            'fahrt_beendet': self.beendet_um is not None,
            'mehrere_ziele_erreicht': ziele >= 2,
            'sauberes_ende': sh.get('outcome') in SAUBERES_ENDE,
            'kein_not_aus_waehrend_fahrt': not self.estop_aktiv_waehrend_fahrt,
        }

    def zusammenfassung(self):
        if self._rueckfahrt is not None:
            self._rueckfahrt_pruefen(self._rueckfahrt['letzte'], erzwingen=True)
        sh = self.self_healing or {}
        dauer = (None if self.gestartet_um is None or self.beendet_um is None
                 else round(self.beendet_um - self.gestartet_um, 1))
        kriterien = self.kriterien()
        return {
            'schema_version': 3,
            'dauer_s': dauer,
            'endzustand': {k: sh.get(k) for k in (
                'state', 'outcome', 'reason', 'goals_reached', 'heals',
                'deferred_goals', 'track_backs', 'look_arounds')},
            # EK-1 (ab 16.11.2026): Schwenks, ausgelassene schmale Lücken, Ziele ohne Kartengewinn.
            'suche': {k: sh.get(k) for k in ('scans', 'shallow_frontiers', 'visited_without_gain')},
            'heilungsverlauf': (sh.get('ladder') or {}).get('history'),
            'karte_speicherbar': (self.explore_status or {}).get('map_ready_to_save'),
            'hwt_endzustand': self.hwt_zustand,
            'fahrbefehle': {k: (round(v, 3) if isinstance(v, float) else v)
                            for k, v in self.cmd.items()},
            'strecke_odom_m': round(self.strecke_m, 2),
            'rueckfahrten': self.rueckfahrten,
            'tempo_folge': self.tempo_folge(),
            'wackeln': self.wackeln(),
            'vl53_luecken': {'anzahl': self.vl53_luecken,
                             'max_s': round(self.vl53_max_luecke_s, 3)},
            'abdeckung': self.abdeckung_zeiten(),
            'abdeckungskurve': self.abdeckung,
            'nahbild': self.nahbild_uebersicht(),
            'nahbilder': self.nahbilder,
            'kriterien_automatisch': kriterien,
            'automatisch_erfuellt': all(kriterien.values()),
            'kriterien_manuell': list(MANUELL),
            'ereignisse': self.ereignisse,
        }


def flaechen(werte, aufloesung):
    """Freie, belegte und bekannte Fläche einer OccupancyGrid-Wertefolge in m²."""
    import numpy as np
    zellen = np.asarray(werte, dtype=np.int16)
    zelle_m2 = float(aufloesung)**2
    frei = int(np.count_nonzero((zellen >= 0) & (zellen < 25)))
    belegt = int(np.count_nonzero(zellen >= 65))
    bekannt = int(np.count_nonzero(zellen >= 0))
    return dict(frei_m2=round(frei*zelle_m2, 2), belegt_m2=round(belegt*zelle_m2, 2),
                bekannt_m2=round(bekannt*zelle_m2, 2))


def kontur_seite(x, y, vorn=KONTUR_VORN_M, hinten=KONTUR_HINTEN_M, halb=KONTUR_HALB_M,
                 polster=KONTUR_POLSTER_M):
    """Abstand eines Punkts (Roboterkoordinaten) zur gepolsterten Kontur und seine Seite.

    Innerhalb ist der Abstand 0 und die Seite die nächste Kante; außerhalb
    nennt die Seite, wohin der Punkt liegt („vorn links“ für eine Ecke).
    """
    v, h, b = vorn + polster, hinten + polster, halb + polster
    aussen_x = max(x - v, -h - x, 0.0)
    aussen_y = max(abs(y) - b, 0.0)
    laengs = 'vorn' if x > v else 'hinten' if x < -h else ''
    quer = ('links' if y > 0 else 'rechts') if abs(y) > b else ''
    if not laengs and not quer:                                 # in der Kontur: nächste Kante
        kanten = {'vorn': v - x, 'hinten': x + h, 'links': b - y, 'rechts': y + b}
        return 0.0, min(kanten, key=kanten.get)
    return math.hypot(aussen_x, aussen_y), ' '.join(t for t in (laengs, quer) if t)


def nahbild(werte, breite, hoehe, aufloesung, ursprung, pose, umkreis_m=NAHBILD_UMKREIS_M):
    """Tödliche Zellen einer Kostenkarte um den Roboter, in Roboterkoordinaten.

    ``pose`` ist (x, y, Gier) im Rahmen der Karte. Ergebnis ohne
    Kartenkoordinaten: Zellen als [vor, links] in Zentimetern, wie viele in der
    Kontur liegen, die nächste Zelle zur gepolsterten Kontur, der freie Platz
    links und rechts neben dem Roboter und daraus die Breite der Stelle.
    """
    if not (aufloesung > 0 and breite > 0 and hoehe > 0) or len(werte) != breite*hoehe:
        return None
    x0, y0, gier = pose
    c, s = math.cos(gier), math.sin(gier)
    n = int(math.ceil(umkreis_m/aufloesung))
    i0 = int(math.floor((x0 - ursprung[0])/aufloesung))
    j0 = int(math.floor((y0 - ursprung[1])/aufloesung))
    zellen, in_kontur, ohne_polster = [], 0, 0
    naechste = None
    links = rechts = None
    for j in range(max(0, j0 - n), min(hoehe, j0 + n + 1)):
        zeile = j*breite
        for i in range(max(0, i0 - n), min(breite, i0 + n + 1)):
            if werte[zeile + i] < KOSTEN_TOEDLICH:
                continue
            dx = ursprung[0] + (i + .5)*aufloesung - x0
            dy = ursprung[1] + (j + .5)*aufloesung - y0
            if dx*dx + dy*dy > umkreis_m*umkreis_m:
                continue
            x, y = c*dx + s*dy, -s*dx + c*dy                    # vor dem Roboter, links von ihm
            zellen.append([round(x*100), round(y*100)])
            abstand, seite = kontur_seite(x, y)
            if abstand == 0.0:
                in_kontur += 1
                if -KONTUR_HINTEN_M <= x <= KONTUR_VORN_M and abs(y) <= KONTUR_HALB_M:
                    ohne_polster += 1
            if naechste is None or abstand < naechste[0]:
                naechste = (abstand, seite)
            if -KONTUR_HINTEN_M <= x <= KONTUR_VORN_M:           # neben dem Roboter
                frei = abs(y) - KONTUR_HALB_M - KONTUR_POLSTER_M
                if y > 0 and (links is None or frei < links):
                    links = frei
                if y < 0 and (rechts is None or frei < rechts):
                    rechts = frei
    kontur_breite = 2*(KONTUR_HALB_M + KONTUR_POLSTER_M)
    return dict(
        in_kontur=in_kontur, in_kontur_ohne_polster=ohne_polster,
        naechste_m=None if naechste is None else round(naechste[0], 2),
        seite=None if naechste is None else naechste[1],
        links_m=None if links is None else round(links, 2),
        rechts_m=None if rechts is None else round(rechts, 2),
        breite_m=(None if links is None or rechts is None
                  else round(links + rechts + kontur_breite, 2)),
        zellen=zellen)


# ---------------------------------------------------------------------------
#  ROS-Teil (nur Abonnements)
# ---------------------------------------------------------------------------

def _json(msg):
    try:
        daten = json.loads(msg.data)
    except (ValueError, TypeError):
        return None
    return daten if isinstance(daten, dict) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--json', required=True, help='Zusammenfassung (lokal, nicht ins Repo)')
    parser.add_argument('--max-s', type=float, default=1800.0,
                        help='Sicherheitsende des Protokolls (Standard 30 min)')
    parser.add_argument('--nachlauf-s', type=float, default=5.0,
                        help='So lange nach dem Missionsende weiter mitschreiben')
    parser.add_argument('--stellprobe-m', type=float, default=0.0,
                        help='Stellprobe: Ende, sobald der Roboter so weit vom Standort beim '
                             'Missionsstart entfernt ist (0 = aus)')
    parser.add_argument('--lokale-karte', default='/local_costmap/costmap',
                        help='lokale Kostenkarte für das Nahbild (nur lesend)')
    parser.add_argument('--imu-topic', default=IMU_TOPIC,
                        help='sensor_msgs/Imu für die Messgröße Wackeln (nur lesend)')
    parser.add_argument('--stellprobe-fenster-s', type=float, default=300.0,
                        help='Stellprobe: Ende spätestens so lange nach dem Missionsstart')
    args = parser.parse_args(argv)

    import rclpy
    from geometry_msgs.msg import Twist
    from nav2_msgs.msg import SpeedLimit
    from nav_msgs.msg import OccupancyGrid, Odometry
    from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                           qos_profile_sensor_data)
    from robot_interfaces.msg import NearFieldStatus
    from sensor_msgs.msg import Imu
    from std_msgs.msg import Bool, String

    rclpy.init()
    node = rclpy.create_node('selbstheilung_lauf_protokoll')
    protokoll = LaufProtokoll(time.monotonic())
    jetzt = time.monotonic
    latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def on_explore(msg):
        daten = _json(msg)
        if daten is not None:
            protokoll.explore(daten, jetzt())

    def on_mission(msg):
        daten = _json(msg)
        if daten is not None:
            protokoll.mission(daten, jetzt())

    node.create_subscription(String, '/explore/status_json', on_explore, 10)
    node.create_subscription(String, '/mission_manager/status_json', on_mission, latched)
    node.create_subscription(Bool, '/safety/estop',
                             lambda m: protokoll.estop_wert(bool(m.data), jetzt()), latched)
    node.create_subscription(SpeedLimit, '/speed_limit',
                             lambda m: protokoll.tempo(m.speed_limit, jetzt()), 10)
    node.create_subscription(Twist, '/cmd_vel',
                             lambda m: protokoll.cmd_vel(m.linear.x, m.angular.z, jetzt()),
                             qos_profile_sensor_data)
    def on_odom(m):
        x, y = m.pose.pose.position.x, m.pose.pose.position.y
        q = m.pose.pose.orientation
        gier = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        protokoll.odom(x, y, jetzt(), gier)
        protokoll.stellprobe(x, y, jetzt(), args.stellprobe_m)

    node.create_subscription(Odometry, '/odom', on_odom, qos_profile_sensor_data)
    node.create_subscription(
        Imu, args.imu_topic,
        lambda m: protokoll.imu(m.angular_velocity.x, m.angular_velocity.y, jetzt()),
        qos_profile_sensor_data)
    node.create_subscription(NearFieldStatus, '/near_field/status',
                             lambda m: protokoll.vl53(jetzt()), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map',
                             lambda m: protokoll.karte(m.data, m.info.resolution, jetzt()),
                             latched)
    node.create_subscription(
        OccupancyGrid, args.lokale_karte,
        lambda m: protokoll.lokale_karte(
            m.data, m.info.width, m.info.height, m.info.resolution,
            (m.info.origin.position.x, m.info.origin.position.y), jetzt()),
        latched)

    # Messquelle prüfen, bevor die Fahrt beginnt: In SH-8c blieb „wackeln“ leer,
    # weil das Topic anders hieß; das soll vor der Mission auffallen.
    frist = jetzt() + 3.0
    while jetzt() < frist and node.count_publishers(args.imu_topic) == 0:
        rclpy.spin_once(node, timeout_sec=0.1)
    sender = node.count_publishers(args.imu_topic)
    print(f'Messquelle Wackeln: {"OK" if sender else "FEHLT"} '
          f'({args.imu_topic}, {sender} Sender)', flush=True)
    print('Fahrtprotokoll läuft; wartet auf den Missionsstart.', flush=True)
    ende = jetzt() + args.max_s
    ende_grund = None
    try:
        while rclpy.ok() and jetzt() < ende:
            rclpy.spin_once(node, timeout_sec=0.1)
            if (protokoll.beendet_um is not None
                    and jetzt() - protokoll.beendet_um >= args.nachlauf_s):
                break
            if args.stellprobe_m > 0 and protokoll.gestartet_um is not None:
                if (protokoll.stellprobe_weg_um is not None
                        and jetzt() - protokoll.stellprobe_weg_um >= args.nachlauf_s):
                    ende_grund = 'stellprobe_weg'
                    break
                if jetzt() - protokoll.gestartet_um >= args.stellprobe_fenster_s:
                    ende_grund = 'stellprobe_fenster'
                    break
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    ergebnis = protokoll.zusammenfassung()
    ergebnis['protokoll_ende'] = ('missionsende' if protokoll.beendet_um is not None
                                  else ende_grund or 'zeitlimit_oder_abbruch')
    ergebnis['stellprobe'] = protokoll.stellprobe_ergebnis(args.stellprobe_m)
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, 'w', encoding='utf-8') as handle:
        json.dump(ergebnis, handle, ensure_ascii=False, indent=2)
    ausgabe = {k: v for k, v in ergebnis.items()
               if k not in ('ereignisse', 'heilungsverlauf', 'abdeckungskurve')}
    print(json.dumps(ausgabe, ensure_ascii=False, indent=2))
    if args.stellprobe_m > 0:
        return 0        # Urteil der Stellprobe steht im Ergebnis, nicht im Exit-Code
    return 0 if ergebnis['automatisch_erfuellt'] else 1


if __name__ == '__main__':
    sys.exit(main())
