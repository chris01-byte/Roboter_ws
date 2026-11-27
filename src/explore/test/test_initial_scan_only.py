"""Nur Rundblick (initial_scan_only): einmal drehen, stehen bleiben, kein Ziel.

Anschlussstelle für die getrennte Linie ki_erkundung (Freigabe des
Projektinhabers vom 21.11.2026). Vorgabe aus; ausgeschaltet verhält sich der
Erkunder wie zuvor. Eingeschaltet läuft ein eigener kurzer Ablauf vor jeder
Erkundungsstrategie.
"""
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_SRC = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT))

import explore.explore_node as explore_node_module  # noqa: E402
from explore.explore_node import ExploreNode  # noqa: E402


@pytest.fixture
def uhr(monkeypatch):
    """Die Schleifen des Erkunders ohne ROS und ohne echtes Warten."""
    zeit = [100.0]
    monkeypatch.setattr(explore_node_module.rclpy, 'ok', lambda: True)
    monkeypatch.setattr(explore_node_module.time, 'monotonic', lambda: zeit[0])
    monkeypatch.setattr(
        explore_node_module.time, 'sleep',
        lambda seconds: zeit.__setitem__(0, zeit[0] + max(seconds, 0.001)))
    return zeit


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


def knoten(scan_only, scan=('success', 2.0 * math.pi)):
    """Erkunder ohne ROS mit dem, was die Abläufe bis zum Rundblick brauchen."""
    node = ExploreNode.__new__(ExploreNode)
    node._initial_scan_only = scan_only
    node._initial_scan_enabled = True
    node._door_distance = 0.0
    node._overall_timeout_s = 400.0
    node._min_frontier_m = 0.3
    node._return_to_start_p = False
    node._map_timeout_s = 5.0
    node._replan_period_s = 0.0
    node._global_frame = 'map'
    for name in ('_blacklist', '_coverage_path'):
        setattr(node, name, [])
    for name in ('_visited_frontier_goals', '_visited_portals'):
        setattr(node, name, set())
    node._map = SimpleNamespace(
        header=SimpleNamespace(frame_id='map'), data=[0, 0, 100, -1],
        info=SimpleNamespace(resolution=0.05))
    node._map_is_fresh = lambda: True
    node._robot_pose = lambda: (1.0, 2.0, 0.0)
    node._record_coverage_pose = lambda xy: None
    node.statuses = []
    node._publish_status = node.statuses.append
    node.logs = []
    node.get_logger = lambda: SimpleNamespace(
        info=node.logs.append, warn=node.logs.append, error=node.logs.append)
    node.scans = []

    def scan_in_place(stop_requested=lambda: False, **kwargs):
        node.scans.append(kwargs)
        return scan

    node._scan_in_place = scan_in_place
    node.strategies = []

    def frontier_planning(*args, **kwargs):
        raise Weiter()

    def strategy(name):
        def run(*args, **kwargs):
            node.strategies.append(name)
            return name
        return run

    node._detect_frontiers = frontier_planning
    node._navigate_to = strategy('navigate_to')
    node._execute_self_healing = strategy('self_healing')
    node._execute_metric_frontier = strategy('metric_frontier')
    node._execute_wohnungserkundung_navigation = strategy('wohnungserkundung')
    return node


def test_schalter_ist_in_code_profilen_und_startdateien_in_der_vorgabe_aus():
    source = (PACKAGE_ROOT / 'explore' / 'explore_node.py').read_text(encoding='utf-8')
    assert "'initial_scan_only', False" in source
    assert [path.name for path in sorted((PACKAGE_ROOT / 'config').glob('*.yaml'))
            if 'initial_scan_only' in path.read_text(encoding='utf-8')] == []
    for datei in (PACKAGE_ROOT / 'launch' / 'explore.launch.py',
                  REPO_SRC / 'robot_navigation' / 'launch' / 'nav_mapping.launch.py',
                  REPO_SRC / 'robot_bringup' / 'launch' / 'app_mapping.launch.py'):
        text = datei.read_text(encoding='utf-8')
        assert "'initial_scan_only', default_value='false'" in text, datei.name
    # durchgereicht von der App-Kartierung bis zum Erkunder
    assert ("'initial_scan_only': LaunchConfiguration('initial_scan_only')"
            in (REPO_SRC / 'robot_bringup' / 'launch' / 'app_mapping.launch.py').read_text(
                encoding='utf-8'))
    assert ("'initial_scan_only': initial_scan_only"
            in (REPO_SRC / 'robot_navigation' / 'launch' / 'nav_mapping.launch.py').read_text(
                encoding='utf-8'))
    assert ("'initial_scan_only': ParameterValue(\n"
            "                        LaunchConfiguration('initial_scan_only'), value_type=bool)"
            in (PACKAGE_ROOT / 'launch' / 'explore.launch.py').read_text(encoding='utf-8'))


def test_nur_rundblick_dreht_einmal_und_endet_erfolgreich_ohne_ziel(uhr):
    node, handle = knoten(True), Handle()
    result = node._execute_reserved(handle)
    assert result.success is True
    assert result.message == (
        'Nur Rundblick abgeschlossen: 360.0 Grad gedreht; kein Ziel angefahren')
    assert handle.calls == ['succeed']
    assert node.scans == [{}]                      # der ganze Rundblick, genau einmal
    assert node.strategies == []
    assert result.frontiers_visited == 0
    assert result.explored_area_m2 == pytest.approx(2 * 0.05 ** 2)
    assert node.statuses == ['running', 'running']
    assert node._status_phase == 'initial_scan'


@pytest.mark.parametrize('schalter', [
    '_self_healing_enabled', '_metric_enabled', '_wohnungserkundung_navigation_enabled'])
def test_nur_rundblick_gilt_vor_jeder_erkundungsstrategie(uhr, schalter):
    """Auch im Selbstheilungsbetrieb (dem zuletzt real gelaufenen Stack) fährt nichts los."""
    node, handle = knoten(True), Handle()
    setattr(node, schalter, True)
    result = node._execute_reserved(handle)
    assert result.success is True and handle.calls == ['succeed']
    assert node.scans == [{}] and node.strategies == []


def test_ohne_schalter_bleibt_die_wahl_der_strategie_wie_bisher(uhr):
    node = knoten(False)
    with pytest.raises(Weiter):                    # Standardweg: nach dem Rundblick Frontiers
        node._execute_reserved(Handle())
    assert node.scans == [{}]
    for schalter, name in (('_self_healing_enabled', 'self_healing'),
                           ('_metric_enabled', 'metric_frontier'),
                           ('_wohnungserkundung_navigation_enabled', 'wohnungserkundung')):
        node = knoten(False)
        setattr(node, schalter, True)
        assert node._execute_reserved(Handle()) == name
        assert node.strategies == [name] and node.scans == []
    # ein Knoten ohne das Attribut (ältere Testknoten) verhält sich wie ausgeschaltet
    node = knoten(False)
    del node._initial_scan_only
    with pytest.raises(Weiter):
        node._execute_reserved(Handle())


@pytest.mark.parametrize('status', ['no_progress', 'odom_stale', 'timeout', 'stop_timeout'])
def test_fehlgeschlagener_rundblick_ist_ein_fehlschlag(uhr, status):
    node, handle = knoten(True, scan=(status, 1.0)), Handle()
    result = node._execute_reserved(handle)
    assert result.success is False and handle.calls == ['abort']
    assert result.message == f'Nur Rundblick fehlgeschlagen: {status}; erreicht 57.3 Grad'
    assert node.strategies == []


def test_abbruch_vor_und_waehrend_des_rundblicks(uhr):
    node, handle = knoten(True), Handle()
    handle.is_cancel_requested = True
    result = node._execute_reserved(handle)
    assert handle.calls == ['canceled'] and result.success is False
    assert node.scans == [] and 'nichts bewegt' in result.message

    node, handle = knoten(True), Handle()

    def scan_in_place(stop_requested=lambda: False, **kwargs):
        assert stop_requested() is False
        handle.is_cancel_requested = True
        assert stop_requested() is True            # der Abbruch hält die Drehung an
        return 'interrupted', 0.5

    node._scan_in_place = scan_in_place
    result = node._execute_reserved(handle)
    assert handle.calls == ['canceled'] and result.success is False
    assert result.message == 'Nur Rundblick abgebrochen nach 28.6 Grad'


def test_ohne_karte_pose_oder_mit_falschem_kartenframe_wird_nicht_gedreht(uhr):
    node, handle = knoten(True), Handle()
    node._map = None
    result = node._execute_reserved(handle)
    assert handle.calls == ['abort'] and node.scans == []
    assert result.message == 'Nur Rundblick: SLAM-Karte fehlt; nichts bewegt'
    assert 5.0 < uhr[0] - 100.0 < 6.0              # gewartet bis zur Kartenfrist

    node, handle = knoten(True), Handle()
    node._robot_pose = lambda: None
    result = node._execute_reserved(handle)
    assert handle.calls == ['abort'] and node.scans == []
    assert 'Roboterpose im Kartenframe fehlt' in result.message

    node, handle = knoten(True), Handle()
    node._map.header.frame_id = 'odom'
    result = node._execute_reserved(handle)
    assert handle.calls == ['abort'] and node.scans == []
    assert "Kartenframe 'odom' passt nicht zu 'map'" in result.message


def test_karte_die_waehrend_der_drehung_verschwindet_haelt_die_drehung_an(uhr):
    node, handle = knoten(True), Handle()

    def scan_in_place(stop_requested=lambda: False, **kwargs):
        node._map = None
        return ('interrupted', 0.3) if stop_requested() else ('success', 6.28)

    node._scan_in_place = scan_in_place
    result = node._execute_reserved(handle)
    assert handle.calls == ['abort']
    assert result.message == 'Nur Rundblick fehlgeschlagen: interrupted; erreicht 17.2 Grad'


@pytest.mark.parametrize('aendern,grund', [
    (lambda n, h: setattr(n, '_initial_scan_enabled', False), 'initial_scan_disabled'),
    (lambda n, h: setattr(n, '_door_distance', 0.4), 'door_traverse_configured'),
    (lambda n, h: setattr(n, '_return_to_start_p', True), 'unsupported_return_request'),
    (lambda n, h: setattr(h.request, 'return_to_start', True), 'unsupported_return_request'),
])
def test_nur_rundblick_lehnt_einstellungen_ab_die_eine_fahrt_verlangen(uhr, aendern, grund):
    node, handle = knoten(True), Handle()
    aendern(node, handle)
    result = node._execute_reserved(handle)
    assert result.success is False
    assert result.message == f'initial_scan_only:{grund}'
    assert handle.calls == ['abort']
    assert node.scans == [] and node.statuses == [] and node.strategies == []


def test_gedreht_wird_mit_dem_vorhandenen_abschnittsweisen_rundblick(uhr):
    """Acht Abschnitte von 45 Grad mit Halt dazwischen, danach kein weiterer Befehl."""
    node, handle = knoten(True), Handle()
    del node._scan_in_place                        # der echte Rundblick des Erkunders
    node._initial_scan_segment_angle = math.pi / 4.0
    node._initial_scan_angle = 2.0 * math.pi
    node._initial_scan_speed = 0.10                # Profil des Selbstheilungsbetriebs
    node._initial_scan_timeout = 280.0
    node._initial_scan_segment_pause = 1.0
    rotations, stops = [], []
    node._publish_scan_stop = lambda: stops.append(uhr[0])

    def rotate_in_place(angle, speed, timeout, stop_requested):
        rotations.append((angle, speed))
        uhr[0] += angle / speed
        return 'success', angle

    node._rotate_in_place = rotate_in_place
    result = node._execute_reserved(handle)
    assert result.success is True and handle.calls == ['succeed']
    assert len(rotations) == 8
    assert all(angle == pytest.approx(math.pi / 4.0) and speed == pytest.approx(0.10)
               for angle, speed in rotations)
    assert len(stops) >= 8                          # in jeder Pause wird Null gesendet
    assert node.strategies == []
    assert uhr[0] - 100.0 == pytest.approx(2.0 * math.pi / 0.10 + 8 * 1.0, abs=1.0)
