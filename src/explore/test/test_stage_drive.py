"""Etappenfahrt (stage_drive_only): ein Fahrziel ohne Nav2 anfahren.

Zweite Anschlussstelle für die getrennte Linie ki_erkundung (Freigabe des
Projektinhabers vom 21.11.2026). Vorgabe aus; ausgeschaltet verhält sich der
Erkunder wie zuvor. Eingeschaltet wartet ein eigener kurzer Ablauf auf genau
ein Fahrziel und fährt es mit den vorhandenen Bausteinen an: Drehen auf der
Stelle und gerade, vom Laser gemessene Etappen. Ohne Ziel bewegt sich nichts.
"""
import json
import math
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_SRC = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT))

import explore.explore_node as explore_node_module  # noqa: E402
from explore.explore_node import ExploreNode  # noqa: E402
from explore.stage_drive import (  # noqa: E402
    StageLimits, next_stage, obstacle_ahead_m, parse_stage_target,
)

JETZT = 1_800_000_000.0
echte_zeit = __import__('time').perf_counter    # die Uhr des Erkunders wird in Tests ersetzt
GRENZEN = StageLimits()


def ziel(punkte, *, quelle='test', frame='map', zeit_s=JETZT, kennung='z1', **mehr):
    return json.dumps({
        'kennung': kennung, 'quelle': quelle, 'frame': frame,
        'zeit_s': zeit_s, 'punkte': punkte, **mehr})


def pruefe(text, start=(0.0, 0.0), grenzen=GRENZEN):
    return parse_stage_target(
        text, frame='map', now_s=JETZT, start_xy=start, limits=grenzen)


# ----------------------------- Rechenregeln -----------------------------
def test_gueltiges_fahrziel_wird_mit_quelle_und_laenge_angenommen():
    target = pruefe(ziel([[1.0, 0.0], [1.0, 1.5]], quelle='ki', kennung='tuer-2'))
    assert target.kennung == 'tuer-2'
    assert target.quelle == 'ki'
    assert target.punkte == ((1.0, 0.0), (1.0, 1.5))
    assert target.laenge_m == pytest.approx(2.5)


@pytest.mark.parametrize('text, grund', [
    ('kein json', 'target_not_json'),
    ('[1, 2]', 'target_not_object'),
    (ziel([[0.5, 0.0]], kennung=''), 'target_id_invalid'),
    (ziel([[0.5, 0.0]], quelle='regel'), 'target_source_invalid'),
    (ziel([[0.5, 0.0]], frame='odom'), 'target_frame_mismatch'),
    (ziel([[0.5, 0.0]], zeit_s='gestern'), 'target_time_invalid'),
    (ziel([[0.5, 0.0]], zeit_s=JETZT + 60.0), 'target_time_invalid'),
    (ziel([[0.5, 0.0]], zeit_s=JETZT - 31.0), 'target_stale'),
    (ziel([]), 'target_point_count_invalid'),
    (ziel([[0.5, 0.0]] * 4), 'target_point_count_invalid'),
    (ziel([[0.5]]), 'target_point_invalid'),
    (ziel([[0.5, 'x']]), 'target_point_invalid'),
    (ziel([[0.5, True]]), 'target_point_invalid'),
    (ziel([[float('nan'), 0.0]]), 'target_point_invalid'),
    (ziel([[2.6, 0.0]]), 'target_leg_too_long'),
    (ziel([[1.0, 0.0], [1.05, 0.0]]), 'target_leg_too_short'),
    (ziel([[2.0, 0.0], [2.0, 2.0], [0.5, 2.0]]), 'target_total_too_long'),
    (ziel([[0.05, 0.0]]), 'target_total_too_short'),
])
def test_mangelhaftes_fahrziel_wird_mit_grund_verworfen(text, grund):
    with pytest.raises(ValueError, match=grund):
        pruefe(text)


def test_erster_punkt_darf_am_standort_liegen_dann_zaehlt_die_naechste_strecke():
    target = pruefe(ziel([[0.02, 0.0], [1.2, 0.0]]))
    assert target.laenge_m == pytest.approx(1.2)


def test_strecken_werden_vom_standort_des_roboters_aus_gemessen():
    assert pruefe(ziel([[3.0, 2.0]]), start=(2.0, 2.0)).laenge_m == pytest.approx(1.0)
    with pytest.raises(ValueError, match='target_leg_too_long'):
        pruefe(ziel([[3.0, 2.0]]), start=(0.0, 2.0))


@pytest.mark.parametrize('aendern', [
    dict(max_points=0), dict(max_points=True), dict(min_leg_m=0.0),
    dict(max_leg_m=float('inf')), dict(min_leg_m=3.0), dict(max_total_m=1.0),
    dict(max_age_s=-1.0),
])
def test_unsinnige_grenzen_werden_abgelehnt(aendern):
    with pytest.raises(ValueError, match='stage_limits_invalid'):
        StageLimits(**aendern)


REGEL = dict(arrive_tolerance_m=0.10, aim_min_distance_m=0.35,
             align_tolerance_rad=0.06, stage_max_m=0.50)


def test_naechster_schritt_angekommen_ausrichten_fahren():
    assert next_stage((0.0, 0.0, 0.0), (0.05, 0.05), **REGEL)[0] == 'arrived'
    schritt, winkel = next_stage((0.0, 0.0, 0.0), (1.0, 1.0), **REGEL)
    assert schritt == 'align' and winkel == pytest.approx(math.pi / 4)
    schritt, winkel = next_stage((0.0, 0.0, 0.0), (1.0, -1.0), **REGEL)
    assert schritt == 'align' and winkel == pytest.approx(-math.pi / 4)
    assert next_stage((0.0, 0.0, 0.0), (0.4, 0.0), **REGEL) == ('drive', pytest.approx(0.4))


def test_lange_strecken_werden_in_gleich_lange_etappen_geteilt():
    assert next_stage((0.0, 0.0, 0.0), (0.5, 0.0), **REGEL)[1] == pytest.approx(0.5)
    assert next_stage((0.0, 0.0, 0.0), (0.62, 0.0), **REGEL)[1] == pytest.approx(0.31)
    assert next_stage((0.0, 0.0, 0.0), (1.3, 0.0), **REGEL)[1] == pytest.approx(1.3 / 3)
    for abstand in (0.36, 0.5, 0.51, 0.99, 1.0, 1.01, 2.5):
        schritt, laenge = next_stage((0.0, 0.0, 0.0), (abstand, 0.0), **REGEL)
        assert schritt == 'drive' and 0.17 < laenge <= 0.5 + 1e-9


def test_nahe_am_punkt_wird_nicht_mehr_neu_gezielt():
    # 0,30 m entfernt und 20 Grad daneben: kein Ausrichten, nur der Rest geradeaus
    punkt = (0.30 * math.cos(math.radians(20)), 0.30 * math.sin(math.radians(20)))
    schritt, laenge = next_stage((0.0, 0.0, 0.0), punkt, **REGEL)
    assert schritt == 'drive' and laenge == pytest.approx(0.30 * math.cos(math.radians(20)))
    # seitlich daneben oder schon vorbei: angekommen, kein Rückwärts
    assert next_stage((0.0, 0.0, 0.0), (0.0, 0.3), **REGEL)[0] == 'arrived'
    assert next_stage((0.0, 0.0, 0.0), (-0.2, 0.05), **REGEL)[0] == 'arrived'


def test_kleiner_winkelfehler_wird_nicht_nachgestellt():
    punkt = (math.cos(0.05), math.sin(0.05))
    assert next_stage((0.0, 0.0, 0.0), punkt, **REGEL)[0] == 'drive'
    punkt = (math.cos(0.07), math.sin(0.07))
    assert next_stage((0.0, 0.0, 0.0), punkt, **REGEL)[0] == 'align'


@pytest.mark.parametrize('aendern', [
    dict(arrive_tolerance_m=0.0), dict(stage_max_m=0.05),
    dict(aim_min_distance_m=0.05), dict(align_tolerance_rad=0.0),
])
def test_unsinnige_regelwerte_werden_abgelehnt(aendern):
    with pytest.raises(ValueError, match='stage_values_invalid'):
        next_stage((0.0, 0.0, 0.0), (1.0, 0.0), **{**REGEL, **aendern})
    with pytest.raises(ValueError, match='stage_values_invalid'):
        next_stage((0.0, float('nan'), 0.0), (1.0, 0.0), **REGEL)


# ------------------------- Ablauf im Erkunder -------------------------
class Uhr:
    def __init__(self):
        self.zeit = 100.0
        self.bei_schlaf = []

    def schlafe(self, sekunden):
        self.zeit += max(sekunden, 0.001)
        for aufgabe in list(self.bei_schlaf):
            aufgabe()


@pytest.fixture
def uhr(monkeypatch):
    """Die Schleifen des Erkunders ohne ROS und ohne echtes Warten."""
    uhr = Uhr()
    monkeypatch.setattr(explore_node_module.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: uhr.zeit)
    monkeypatch.setattr(explore_node_module.time, 'time', lambda: JETZT)
    monkeypatch.setattr(explore_node_module.time, 'sleep', uhr.schlafe)
    return uhr


class Weiter(Exception):
    """Der Standardweg hat die Frontier-Planung erreicht."""


class Handle:
    def __init__(self, return_to_start=False):
        self.request = SimpleNamespace(
            timeout_s=0.0, min_frontier_size_m=0.0, return_to_start=return_to_start)
        self.is_cancel_requested = False
        self.calls = []

    def succeed(self):
        self.calls.append('succeed')

    def abort(self):
        self.calls.append('abort')

    def canceled(self):
        self.calls.append('canceled')


def knoten(etappenfahrt=True, rundblick=False):
    """Erkunder ohne ROS; Drehen und Fahren bewegen eine gedachte Pose."""
    node = ExploreNode.__new__(ExploreNode)
    node._stage_drive_only = etappenfahrt
    node._initial_scan_only = rundblick
    node._initial_scan_enabled = True
    node._door_distance = 0.0
    node._overall_timeout_s = 2400.0
    node._min_frontier_m = 0.3
    node._return_to_start_p = False
    node._map_timeout_s = 5.0
    node._replan_period_s = 0.0
    node._global_frame = 'map'
    node._stage_target_wait = 420.0
    node._stage_max_m = 0.50
    node._stage_speed = 0.05
    node._stage_turn_speed = 0.08
    node._stage_turn_timeout = 90.0
    node._stage_align_tolerance = 0.06
    node._stage_align_stop_margin = 0.03
    node._stage_max_aligns = 6
    node._stage_arrive_tolerance = 0.10
    node._stage_aim_min_distance = 0.35
    node._stage_max_stages = 16
    node._stage_front_reserve = 0.15
    node._stage_near_stop = 0.25
    node._stage_costmap_timeout = 3.0
    node._stage_near_cache = (0.0, 'unknown', None)
    node._stage_limits = StageLimits()
    node._stage_target_lock = threading.Lock()
    node._stage_target_raw = None
    node._stage_target_listening = False
    node._prealign_settle_s = 1.0
    node._prealign_rate_check_after = 15.0
    node._prealign_min_average_rate = 0.01
    node._portal_front_overhang = 0.33
    for name in ('_blacklist', '_coverage_path'):
        setattr(node, name, [])
    for name in ('_visited_frontier_goals', '_visited_portals'):
        setattr(node, name, set())
    node._map = SimpleNamespace(
        header=SimpleNamespace(frame_id='map'), data=[0, 0, 100, -1],
        info=SimpleNamespace(resolution=0.05))
    node._map_is_fresh = lambda: True
    node.pose = [0.0, 0.0, 0.0]
    node._robot_pose = lambda: tuple(node.pose)
    node._record_coverage_pose = lambda xy: None
    node.statuses = []
    node._publish_status = lambda state: node.statuses.append(
        (state, node._status_phase, node._status_message))
    node.logs = []
    node.get_logger = lambda: SimpleNamespace(
        info=node.logs.append, warn=node.logs.append, error=node.logs.append)
    node.bewegungen = []
    node.ueberdrehen = 0.03          # so viel dreht der Roboter beim Bremsen nach
    node.nachlauf = 0.02             # so viel rollt er nach dem Schaltpunkt
    node.drehstatus = 'success'
    node.etappenstatus = 'success'
    node.streifen = ('success', 3.0)
    node.nahbereich = [('clear', None)]     # Folge der Antworten; die letzte bleibt
    node.etappendauer = 0.0                 # so lange „fährt“ eine Etappe in echter Zeit

    def rotate(angle, speed, timeout, stop_requested=lambda: False, **kwargs):
        node.bewegungen.append(('drehen', round(math.degrees(angle), 1), speed))
        if node.drehstatus != 'success':
            return node.drehstatus, 0.0
        gedreht = abs(angle) + node.ueberdrehen
        node.pose[2] += math.copysign(gedreht, angle)
        return 'success', gedreht

    def drive(distance, budget, speed, timeout, stop_requested=lambda: False):
        node.bewegungen.append(
            ('fahren', round(distance, 3), round(budget, 3), speed, round(timeout, 1)))
        # so fragt die echte Etappe laufend; der Wächter läuft daneben in echter Zeit
        ende = echte_zeit() + node.etappendauer
        while True:
            if stop_requested():
                return 'interrupted', 0.07, 0.08, 0.0, 0.0, 0.02, 0.9, 0
            if echte_zeit() >= ende:
                break
            threading.Event().wait(0.005)
        if node.etappenstatus != 'success':
            return node.etappenstatus, 0.07, 0.08, 0.0, 0.0, 0.02, 0.9, 0
        weg = distance + node.nachlauf
        node.pose[0] += weg * math.cos(node.pose[2])
        node.pose[1] += weg * math.sin(node.pose[2])
        return 'success', weg, weg + 0.005, -0.01, 0.01, 0.02, 0.9, 0

    def scan_in_place(stop_requested=lambda: False, **kwargs):
        node.bewegungen.append(('rundblick',))
        return 'success', 2.0 * math.pi

    node._rotate_in_place = rotate
    node._drive_forward_lidar = drive
    node._scan_in_place = scan_in_place
    node._stage_corridor = lambda stage_m: node.streifen

    def near_field(max_age_s=0.2):
        return node.nahbereich.pop(0) if len(node.nahbereich) > 1 else node.nahbereich[0]

    node._stage_near_field = near_field
    echter_waechter = ExploreNode._stage_watch_near_field
    node._stage_watch_near_field = lambda halt, fertig, nah: echter_waechter(
        node, halt, fertig, nah, period_s=0.01)
    node.strategies = []

    def strategy(name):
        def run(*args, **kwargs):
            node.strategies.append(name)
            return name
        return run

    def frontier_planning(*args, **kwargs):
        raise Weiter()

    node._detect_frontiers = frontier_planning
    node._navigate_to = strategy('navigate_to')
    node._execute_self_healing = strategy('self_healing')
    node._execute_metric_frontier = strategy('metric_frontier')
    node._execute_wohnungserkundung_navigation = strategy('wohnungserkundung')
    return node


def sende_beim_warten(uhr, node, *texte):
    """Schicke die Fahrziele nacheinander, sobald der Erkunder darauf wartet."""
    offen = list(texte)

    def aufgabe():
        if offen and node._stage_target_listening and node._stage_target_raw is None:
            node._on_stage_target(SimpleNamespace(data=offen.pop(0)))

    uhr.bei_schlaf.append(aufgabe)
    return offen


def test_schalter_ist_in_code_profilen_und_startdateien_in_der_vorgabe_aus():
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text(encoding='utf-8')
    assert "'stage_drive_only', False" in source
    assert [path.name for path in sorted((PACKAGE_ROOT / 'config').glob('*.yaml'))
            if 'stage_drive' in path.read_text(encoding='utf-8')] == []
    for datei in (PACKAGE_ROOT / 'launch' / 'explore.launch.py',
                  REPO_SRC / 'robot_navigation' / 'launch' / 'nav_mapping.launch.py',
                  REPO_SRC / 'robot_bringup' / 'launch' / 'app_mapping.launch.py'):
        text = datei.read_text(encoding='utf-8')
        assert "'stage_drive_only', default_value='false'" in text, datei.name
    assert ("'stage_drive_only': LaunchConfiguration('stage_drive_only')"
            in (REPO_SRC / 'robot_bringup' / 'launch' / 'app_mapping.launch.py').read_text(
                encoding='utf-8'))
    assert ("'stage_drive_only': LaunchConfiguration('stage_drive_only')"
            in (REPO_SRC / 'robot_navigation' / 'launch' / 'nav_mapping.launch.py').read_text(
                encoding='utf-8'))
    assert ("'stage_drive_only': ParameterValue(\n"
            "                        LaunchConfiguration('stage_drive_only'), value_type=bool)"
            in (PACKAGE_ROOT / 'launch' / 'explore.launch.py').read_text(encoding='utf-8'))


def test_das_fahrziel_wird_nur_abonniert_wenn_der_schalter_an_ist():
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text(encoding='utf-8')
    assert ('        if self._stage_drive_only:\n'
            '            self.create_subscription(\n'
            '                String, self._stage_target_topic, self._on_stage_target') in source
    assert source.count('self._on_stage_target') == 1


def test_eine_gerade_etappe_von_einem_halben_meter(uhr):
    node, handle = knoten(), Handle()
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is True
    assert handle.calls == ['succeed']
    # Wegbudget und Zeit wie beim real bestandenen Test vom 11.09.2026
    assert node.bewegungen == [('fahren', 0.5, 0.9, 0.05, 50.0)]
    assert result.message == (
        'Etappenfahrt abgeschlossen: 1 Etappe(n), 0.52 m gefahren, '
        '0 Grad ausgerichtet; Quelle test; kein Nav2-Ziel')
    assert node.strategies == []
    assert any('Fahrziel angenommen: Quelle=test' in zeile for zeile in node.logs)


def test_ohne_fahrziel_bewegt_sich_nichts_und_der_auftrag_meldet_es(uhr):
    node, handle = knoten(), Handle()
    start = uhr.zeit
    result = node._execute_reserved(handle)
    assert result.success is False
    assert handle.calls == ['abort']
    assert node.bewegungen == []
    assert result.message.startswith(
        'Etappenfahrt: kein gueltiges Fahrziel erhalten nach 420 s (0 verworfen)')
    assert 419.0 <= uhr.zeit - start <= 422.0
    wartend = [s for s in node.statuses if s[1] == 'stage_drive_wait_target']
    assert wartend and 'Der Roboter steht.' in wartend[0][2]
    assert node.strategies == []


def test_ausrichten_dann_etappen_bis_vor_die_tuer_und_hindurch(uhr):
    node, handle = knoten(), Handle()
    vorpunkt, auslauf = [1.0, 1.0], [2.3, 1.0]
    sende_beim_warten(uhr, node, ziel([vorpunkt, auslauf], quelle='ki', kennung='tuer-1'))
    result = node._execute_reserved(handle)
    assert result.success is True, result.message
    arten = [bewegung[0] for bewegung in node.bewegungen]
    assert arten[0] == 'drehen' and arten[1] == 'fahren'
    assert 'navigate_to' not in node.strategies
    # Beide Punkte erreicht: am Ende steht der Roboter nahe am Auslaufpunkt
    assert math.hypot(node.pose[0] - 2.3, node.pose[1] - 1.0) <= 0.12
    # Keine Etappe länger als ein halber Meter, keine schneller als 0,05 m/s
    etappen = [bewegung for bewegung in node.bewegungen if bewegung[0] == 'fahren']
    assert all(etappe[1] <= 0.5 + 1e-9 and etappe[3] == 0.05 for etappe in etappen)
    assert 5 <= len(etappen) <= 8
    assert 'Quelle ki' in result.message
    # Nach dem Vorpunkt wird auf die Türachse ausgerichtet
    assert sum(1 for art in arten if art == 'drehen') >= 2


def test_ausrichten_haelt_vor_dem_ziel_an_und_stellt_nach(uhr):
    node, handle = knoten(), Handle()
    node.ueberdrehen = 0.0
    sende_beim_warten(uhr, node, ziel([[0.0, 1.0]]))
    result = node._execute_reserved(handle)
    assert result.success is True, result.message
    drehungen = [b for b in node.bewegungen if b[0] == 'drehen']
    # 90 Grad Fehler: erst 90 minus 1,7 Grad Haltereserve; der Rest liegt in der Toleranz
    assert drehungen[0][1] == pytest.approx(math.degrees(math.pi / 2 - 0.03), abs=0.1)
    assert all(drehung[2] == 0.08 for drehung in drehungen)


def test_mangelhafte_fahrziele_werden_verworfen_und_gezaehlt(uhr):
    node, handle = knoten(), Handle()
    sende_beim_warten(
        uhr, node, 'quatsch', ziel([[0.5, 0.0]], frame='odom'),
        ziel([[0.5, 0.0]], zeit_s=JETZT - 100.0), ziel([[9.0, 0.0]]),
        ziel([[0.5, 0.0]], quelle='regel'))
    result = node._execute_reserved(handle)
    assert result.success is False
    assert node.bewegungen == []
    assert '(5 verworfen)' in result.message
    for grund in ('target_not_json', 'target_frame_mismatch', 'target_stale',
                  'target_leg_too_long', 'target_source_invalid'):
        assert any(grund in zeile for zeile in node.logs), grund


def test_nach_einem_verworfenen_ziel_wird_das_naechste_gueltige_angenommen(uhr):
    node, handle = knoten(), Handle()
    sende_beim_warten(uhr, node, 'quatsch', ziel([[0.4, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is True
    assert [b[0] for b in node.bewegungen] == ['fahren']


def test_ein_ziel_von_vor_dem_auftrag_zaehlt_nicht(uhr):
    node, handle = knoten(), Handle()
    node._on_stage_target(SimpleNamespace(data=ziel([[0.5, 0.0]])))
    assert node._stage_target_raw is None          # es wird noch nicht zugehört
    result = node._execute_reserved(handle)
    assert result.success is False and node.bewegungen == []
    # nach dem Auftrag wird nicht weiter zugehört
    node._on_stage_target(SimpleNamespace(data=ziel([[0.5, 0.0]])))
    assert node._stage_target_raw is None and node._stage_target_listening is False


def test_nur_ein_ziel_je_auftrag_ein_zweites_waehrend_der_fahrt_wird_ignoriert(uhr):
    node, handle = knoten(), Handle()
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    spaeter = []

    def zweites_ziel():
        if node.bewegungen or not node._stage_target_listening:
            node._on_stage_target(
                SimpleNamespace(data=ziel([[0.0, -2.0]], kennung='zweites')))
            spaeter.append(node._stage_target_raw)

    uhr.bei_schlaf.append(zweites_ziel)
    result = node._execute_reserved(handle)
    assert result.success is True
    assert [b[0] for b in node.bewegungen] == ['fahren']
    assert spaeter and set(spaeter) == {None}


def test_ist_der_streifen_nicht_frei_wird_nicht_gefahren(uhr):
    node, handle = knoten(), Handle()
    node.streifen = ('corridor_blocked', 0.61)
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False and handle.calls == ['abort']
    assert node.bewegungen == []
    assert 'corridor_blocked' in result.message
    assert 'naechstes Hindernis 0.61 m, noetig 0.98 m' in result.message


def test_ist_der_nahbereich_vor_der_etappe_belegt_wird_nicht_gefahren(uhr):
    node, handle = knoten(), Handle()
    node.nahbereich = [('blocked', 0.12)]
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False and handle.calls == ['abort']
    assert node.bewegungen == []
    assert ('Nahbereich vor dem Roboter nicht frei (blocked, 0.12 m vor der '
            'Vorderkante)') in result.message


def test_ohne_frische_kostenkarte_wird_nicht_gefahren(uhr):
    node, handle = knoten(), Handle()
    node.nahbereich = [('costmap_stale', None)]
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False and node.bewegungen == []
    assert 'Nahbereich vor dem Roboter nicht frei (costmap_stale)' in result.message


def test_taucht_in_der_etappe_etwas_im_nahbereich_auf_haelt_sie_an(uhr):
    node, handle = knoten(), Handle()
    # vor der Etappe frei; während sie läuft, meldet der Wächter beim dritten Blick „belegt“
    node.nahbereich = [('clear', None), ('clear', None), ('clear', None),
                       ('blocked', 0.21)]
    node.etappendauer = 2.0
    sende_beim_warten(uhr, node, ziel([[1.5, 0.0]]))
    beginn = echte_zeit()
    result = node._execute_reserved(handle)
    assert echte_zeit() - beginn < 1.0                 # angehalten, nicht zu Ende gefahren
    assert result.success is False and handle.calls == ['abort']
    assert [b[0] for b in node.bewegungen] == ['fahren']               # kein zweiter Anlauf
    assert ('angehalten, Nahbereich vor dem Roboter nicht frei (blocked, '
            '0.21 m vor der Vorderkante)') in result.message
    assert 'abgebrochen' not in result.message        # ein Fehlschlag, kein Nutzerabbruch


@pytest.mark.parametrize('status', ['lateral_deviation', 'lidar_no_progress', 'timeout'])
def test_eine_fehlgeschlagene_etappe_beendet_die_fahrt(uhr, status):
    node, handle = knoten(), Handle()
    node.etappenstatus = status
    sende_beim_warten(uhr, node, ziel([[1.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False and handle.calls == ['abort']
    assert [b[0] for b in node.bewegungen] == ['fahren']          # kein zweiter Versuch
    assert f'Etappe fehlgeschlagen: {status}' in result.message
    assert '1 Etappe(n), 0.07 m gefahren' in result.message


def test_fehlgeschlagenes_ausrichten_beendet_die_fahrt(uhr):
    node, handle = knoten(), Handle()
    node.drehstatus = 'no_progress'
    sende_beim_warten(uhr, node, ziel([[0.0, 1.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False
    assert [b[0] for b in node.bewegungen] == ['drehen']
    assert 'Ausrichtung fehlgeschlagen: no_progress' in result.message


def test_ausrichten_das_nicht_ankommt_endet_nach_sechs_versuchen(uhr):
    node, handle = knoten(), Handle()
    node.ueberdrehen = -10.0          # der Roboter dreht jedes Mal weit daneben
    sende_beim_warten(uhr, node, ziel([[0.0, 1.0]]))
    result = node._execute_reserved(handle)
    assert result.success is False
    assert [b[0] for b in node.bewegungen] == ['drehen'] * 6
    assert 'Ausrichtung auf Punkt 1 gelingt nicht' in result.message


def test_abbruch_beim_warten_und_waehrend_der_fahrt(uhr):
    node, handle = knoten(), Handle()
    uhr.bei_schlaf.append(lambda: setattr(handle, 'is_cancel_requested', True))
    result = node._execute_reserved(handle)
    assert handle.calls == ['canceled'] and node.bewegungen == []
    assert 'abgebrochen beim Warten' in result.message

    uhr.bei_schlaf.clear()
    node, handle = knoten(), Handle()
    sende_beim_warten(uhr, node, ziel([[1.5, 0.0]]))
    echte_fahrt = node._drive_forward_lidar

    def fahrt_mit_abbruch(*args, **kwargs):
        handle.is_cancel_requested = True
        node.etappenstatus = 'interrupted'
        return echte_fahrt(*args, **kwargs)

    node._drive_forward_lidar = fahrt_mit_abbruch
    result = node._execute_reserved(handle)
    assert handle.calls == ['canceled']
    assert [b[0] for b in node.bewegungen] == ['fahren']


@pytest.mark.parametrize('aendern, grund', [
    (dict(return_to_start=True), 'unsupported_return_request'),
    (dict(door=0.6), 'door_traverse_configured'),
    (dict(rundblick_aus=True), 'initial_scan_disabled'),
])
def test_etappenfahrt_lehnt_widerspruechliche_einstellungen_ab(uhr, aendern, grund):
    node = knoten(rundblick=bool(aendern.get('rundblick_aus')))
    node._door_distance = aendern.get('door', 0.0)
    if aendern.get('rundblick_aus'):
        node._initial_scan_enabled = False
    handle = Handle(return_to_start=bool(aendern.get('return_to_start')))
    result = node._execute_reserved(handle)
    assert result.success is False
    assert result.message == f'stage_drive_only:{grund}'
    assert handle.calls == ['abort'] and node.bewegungen == []


def test_mit_beiden_schaltern_kommt_erst_der_rundblick_dann_das_warten(uhr):
    node, handle = knoten(rundblick=True), Handle()
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is True
    assert [b[0] for b in node.bewegungen] == ['rundblick', 'fahren']
    phasen = [status[1] for status in node.statuses]
    assert phasen.index('initial_scan') < phasen.index('stage_drive_wait_target')


def test_fehlgeschlagener_rundblick_beendet_den_auftrag_ohne_fahrt(uhr):
    node, handle = knoten(rundblick=True), Handle()
    node._scan_in_place = lambda stop_requested=lambda: False, **kw: ('no_progress', 1.0)
    result = node._execute_reserved(handle)
    assert result.success is False and node.bewegungen == []
    assert 'Rundblick fehlgeschlagen: no_progress; erreicht 57.3 Grad' in result.message


@pytest.mark.parametrize('schalter', [
    '_self_healing_enabled', '_metric_enabled', '_wohnungserkundung_navigation_enabled'])
def test_etappenfahrt_gilt_vor_jeder_erkundungsstrategie(uhr, schalter):
    node, handle = knoten(), Handle()
    setattr(node, schalter, True)
    sende_beim_warten(uhr, node, ziel([[0.5, 0.0]]))
    result = node._execute_reserved(handle)
    assert result.success is True
    assert node.strategies == []


def test_ohne_schalter_bleibt_alles_wie_bisher(uhr):
    node, handle = knoten(etappenfahrt=False), Handle()
    node._self_healing_enabled = True
    assert node._execute_reserved(handle) == 'self_healing'
    assert node.bewegungen == []
    # auch ein eintreffendes Fahrziel ändert daran nichts
    node._on_stage_target(SimpleNamespace(data=ziel([[0.5, 0.0]])))
    assert node._stage_target_raw is None


def test_ohne_pose_wird_nicht_gewartet_und_nicht_gefahren(uhr):
    node, handle = knoten(), Handle()
    node._robot_pose = lambda: None
    result = node._execute_reserved(handle)
    assert result.success is False and node.bewegungen == []
    assert 'Roboterpose oder Karte fehlt' in result.message


# ----------------------- Streifenprüfung am Scan -----------------------
def streifen_knoten(punkte, alter_s=0.1):
    node = ExploreNode.__new__(ExploreNode)
    node._door_lidar_scan_timeout = 0.5
    node._door_lidar_min_points = 5
    node._stage_lidar_max_range = 8.0
    node._stage_front_reserve = 0.15
    node._portal_corridor_half_width = 0.25
    node._portal_front_overhang = 0.33
    node._portal_lidar_min_far_points = 3
    winkel = np.arctan2([p[1] for p in punkte], [p[0] for p in punkte])
    reihenfolge = np.argsort(winkel)
    entfernung = np.hypot([p[0] for p in punkte], [p[1] for p in punkte])
    # ein Scan mit genau diesen Strahlen (ungleichmäßige Winkel genügen hier nicht),
    # deshalb als feines Raster mit „kein Echo“ dazwischen
    raster = np.full(720, np.inf)
    for index in reihenfolge:
        raster[int(round((winkel[index] + math.pi) / (2 * math.pi) * 720)) % 720] = (
            entfernung[index])
    node._door_lidar_scan_snapshot = lambda: {
        'ranges': raster, 'angle_min': -math.pi, 'angle_increment': 2 * math.pi / 720,
        'range_min': 0.05, 'range_max': 25.0, 'frame_id': 'base_link',
        'received_at': explore_node_module.time.monotonic() - alter_s}
    node._door_lidar_mount = lambda frame_id: (0.0, 0.0, 0.0)
    return node


def wand(x, von=-1.0, bis=1.0, schritt=0.02):
    return [(x, y) for y in np.arange(von, bis + 1e-9, schritt)]


def test_streifen_frei_wenn_dahinter_etwas_gesehen_wird():
    node = streifen_knoten(wand(5.0))                 # Wand in 5 m: weiter als 4 m
    status, naechstes = node._stage_corridor(0.5)
    assert status == 'success' and naechstes == pytest.approx(5.0, abs=0.02)


def test_streifen_blockiert_wenn_etwas_im_weg_steht_oder_nichts_gesehen_wird():
    node = streifen_knoten(wand(0.9))                 # nötig wären 0,98 m
    status, naechstes = node._stage_corridor(0.5)
    assert status == 'corridor_blocked' and naechstes == pytest.approx(0.9, abs=0.02)
    assert streifen_knoten(wand(1.0))._stage_corridor(0.5)[0] == 'success'  # 2 cm Luft reichen
    # ohne Reserve hielte die Etappe erst 2 cm vor der Wand; mit ihr bleiben 15 cm mehr
    # Türpfosten links und rechts außerhalb des Streifens stören nicht
    pfosten = wand(0.6, -0.9, -0.40) + wand(0.6, 0.40, 0.9) + wand(1.9)
    assert streifen_knoten(pfosten)._stage_corridor(0.5)[0] == 'success'
    # ein Pfosten, der in den Streifen ragt, sperrt
    pfosten = wand(0.6, -0.9, -0.20) + wand(0.6, 0.40, 0.9) + wand(1.9)
    assert streifen_knoten(pfosten)._stage_corridor(0.5)[0] == 'corridor_blocked'
    # nur seitliche Wände, voraus nichts gesehen: kein Beleg, also keine Fahrt
    seiten = ([(x, 1.0) for x in np.arange(-2, 2, 0.02)]
              + [(x, -1.0) for x in np.arange(-2, 2, 0.02)])
    assert streifen_knoten(seiten)._stage_corridor(0.5)[0] == 'corridor_blocked'


def test_alter_scan_oder_zu_wenige_punkte_sperren():
    assert streifen_knoten(wand(5.0), alter_s=2.0)._stage_corridor(0.5)[0] == 'lidar_scan_stale'
    assert streifen_knoten([(5.0, 0.0)])._stage_corridor(0.5)[0] == 'lidar_points_insufficient'


# -------------------- Nahbereichs-Halt an der Kostenkarte --------------------
def karte(belegt, breite=80, hoehe=80, zelle=0.05, ursprung=(-2.0, -2.0), wert=100):
    """Kostenkarte mit belegten Zellen an den genannten Punkten (Meter)."""
    daten = np.zeros(breite * hoehe, dtype=np.int8)
    for x, y in belegt:
        spalte = int((x - ursprung[0]) / zelle)
        zeile = int((y - ursprung[1]) / zelle)
        daten[zeile * breite + spalte] = wert
    return daten, breite, hoehe, zelle, ursprung


STREIFEN = dict(front_m=0.33, reach_m=0.25, half_width_m=0.25)


def test_belegte_zelle_dicht_vor_der_vorderkante_wird_mit_abstand_gemeldet():
    daten = karte([(0.50, 0.0)])                       # Zelle 0,50 bis 0,55 m voraus
    abstand = obstacle_ahead_m(*daten, (0.0, 0.0, 0.0), **STREIFEN)
    assert abstand == pytest.approx(0.525 - 0.33, abs=1e-6)
    # weiter weg, seitlich daneben, hinter dem Roboter oder unter ihm: frei
    for punkt in ((0.70, 0.0), (0.45, 0.40), (-0.50, 0.0), (0.10, 0.0)):
        assert obstacle_ahead_m(*karte([punkt]), (0.0, 0.0, 0.0), **STREIFEN) is None
    assert obstacle_ahead_m(*karte([]), (0.0, 0.0, 0.0), **STREIFEN) is None


def test_tuerpfosten_neben_dem_streifen_sperren_nicht_die_aufgeblasene_zone_auch_nicht():
    pfosten = [(0.45, 0.40), (0.45, -0.42), (0.45, 0.45), (0.45, -0.47)]
    assert obstacle_ahead_m(*karte(pfosten), (0.0, 0.0, 0.0), **STREIFEN) is None
    # Zellen mit Kosten unter „belegt“ (aufgeblasen, 99) zählen nicht
    assert obstacle_ahead_m(*karte([(0.45, 0.0)], wert=99), (0.0, 0.0, 0.0), **STREIFEN) is None
    # ein Pfosten, der in den Streifen ragt, sperrt
    assert obstacle_ahead_m(*karte([(0.45, 0.22)]), (0.0, 0.0, 0.0), **STREIFEN) is not None


def test_der_streifen_dreht_und_wandert_mit_dem_roboter():
    daten = karte([(1.0, 1.50)])
    # Roboter bei (1, 1) mit Blick nach +y: die Zelle liegt 0,5 m voraus
    assert obstacle_ahead_m(*daten, (1.0, 1.0, math.pi / 2), **STREIFEN) == pytest.approx(
        0.525 - 0.33, abs=0.03)
    # mit Blick nach +x liegt sie seitlich
    assert obstacle_ahead_m(*daten, (1.0, 1.0, 0.0), **STREIFEN) is None


def test_unsinnige_karten_werden_abgelehnt():
    daten, breite, hoehe, zelle, ursprung = karte([(0.5, 0.0)])
    with pytest.raises(ValueError, match='strip_grid_size_mismatch'):
        obstacle_ahead_m(daten[:-1], breite, hoehe, zelle, ursprung, (0.0, 0.0, 0.0), **STREIFEN)
    with pytest.raises(ValueError, match='strip_values_invalid'):
        obstacle_ahead_m(daten, breite, hoehe, 0.0, ursprung, (0.0, 0.0, 0.0), **STREIFEN)
    with pytest.raises(ValueError, match='strip_values_invalid'):
        obstacle_ahead_m(daten, breite, hoehe, zelle, ursprung, (0.0, float('nan'), 0.0),
                         **STREIFEN)


def nah_knoten(belegt, alter_s=0.5, rahmen='map', pose=(0.0, 0.0, 0.0)):
    node = ExploreNode.__new__(ExploreNode)
    daten, breite, hoehe, zelle, ursprung = karte(belegt)
    node._global_costmap = SimpleNamespace(
        header=SimpleNamespace(frame_id=rahmen), data=daten.tolist(),
        info=SimpleNamespace(
            width=breite, height=hoehe, resolution=zelle,
            origin=SimpleNamespace(position=SimpleNamespace(x=ursprung[0], y=ursprung[1]))))
    node._global_costmap_received_at = explore_node_module.time.monotonic() - alter_s
    node._global_frame = 'map'
    node._robot_pose = lambda: pose
    node._portal_front_overhang = 0.33
    node._portal_corridor_half_width = 0.25
    node._stage_near_stop = 0.25
    node._stage_costmap_timeout = 3.0
    node._stage_near_cache = (0.0, 'unknown', None)
    return node


def test_nahbereich_liest_die_globale_kostenkarte():
    assert nah_knoten([])._stage_near_field() == ('clear', None)
    status, abstand = nah_knoten([(0.50, 0.05)])._stage_near_field()
    assert status == 'blocked' and abstand == pytest.approx(0.195, abs=1e-6)
    assert nah_knoten([(0.45, 0.40)])._stage_near_field() == ('clear', None)


def test_nahbereich_ohne_frische_karte_pose_oder_mit_falschem_rahmen_gibt_nicht_frei():
    assert nah_knoten([], alter_s=5.0)._stage_near_field() == ('costmap_stale', None)
    assert nah_knoten([], rahmen='odom')._stage_near_field() == ('costmap_frame_mismatch', None)
    assert nah_knoten([], pose=None)._stage_near_field() == ('pose_missing', None)
    node = nah_knoten([])
    node._global_costmap = None
    assert node._stage_near_field() == ('costmap_stale', None)


def test_nahbereich_wird_hoechstens_fuenfmal_je_sekunde_neu_gerechnet(monkeypatch):
    zeit = [1000.0]
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: zeit[0])
    node = nah_knoten([])
    assert node._stage_near_field() == ('clear', None)
    node._global_costmap.data = karte([(0.50, 0.0)])[0].tolist()
    node._global_costmap_received_at = zeit[0]
    assert node._stage_near_field() == ('clear', None)        # noch die alte Antwort
    zeit[0] += 0.25
    node._global_costmap_received_at = zeit[0]
    assert node._stage_near_field()[0] == 'blocked'


def test_der_waechter_haelt_bei_belegtem_nahbereich_und_endet_mit_der_etappe():
    node = ExploreNode.__new__(ExploreNode)
    antworten = [('clear', None), ('clear', None), ('blocked', 0.18)]
    node._stage_near_field = lambda max_age_s=0.2: (
        antworten.pop(0) if len(antworten) > 1 else antworten[0])
    halt, fertig, nah = threading.Event(), threading.Event(), {'status': 'clear'}
    faden = threading.Thread(
        target=node._stage_watch_near_field, args=(halt, fertig, nah, 0.01))
    faden.start()
    assert halt.wait(1.0)
    faden.join(1.0)
    assert not faden.is_alive()
    assert nah == {'status': 'blocked', 'abstand': 0.18}

    # bleibt der Nahbereich frei, endet der Wächter, sobald die Etappe fertig ist
    node._stage_near_field = lambda max_age_s=0.2: ('clear', None)
    halt, fertig, nah = threading.Event(), threading.Event(), {'status': 'clear'}
    faden = threading.Thread(
        target=node._stage_watch_near_field, args=(halt, fertig, nah, 0.01))
    faden.start()
    threading.Event().wait(0.05)
    fertig.set()
    faden.join(1.0)
    assert not faden.is_alive() and not halt.is_set() and nah == {'status': 'clear'}


def test_die_fahrschleife_rechnet_den_nahbereich_nicht_selbst():
    """Die Etappe liest nur ein fertiges Ja oder Nein (kein Rechnen zwischen Uhr und Odometrie)."""
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text(encoding='utf-8')
    assert 'stop_requested() or halt.is_set())))' in source
    assert 'stop_requested() or nahbereich_haelt_an()' not in source
