"""Sauberes Ende bei Signalen (ros_ende.py): Marke statt Ausnahme.

Befund KI-F9 (Lauf 2w): Unter Humble wurde aus Strg+C mitten im Umwandeln
einer Nachricht ein RuntimeError, und die Aufnahme schrieb nichts. Geprüft
wird das Muster des Erkunders der Hauptlinie: Ein Signal setzt nur eine
Marke, rclpy läuft ohne eigenen Handler, und es wird geordnet beendet.
"""
import random
import signal
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

import ros_ende
from ros_ende import Ende, ros_beenden, ros_starten

WERKZEUGE = Path(__file__).resolve().parents[1] / 'werkzeuge'


def test_ein_signal_setzt_nur_die_marke_und_die_vorigen_handler_kommen_zurueck():
    vorher_int = signal.getsignal(signal.SIGINT)
    vorher_term = signal.getsignal(signal.SIGTERM)
    ende = Ende().anmelden()
    try:
        assert not ende.gesetzt()
        signal.raise_signal(signal.SIGINT)          # wirft nicht
        assert ende.gesetzt() and ende.signal == 'SIGINT'
        signal.raise_signal(signal.SIGTERM)         # zweites Signal: bleibt beim ersten
        assert ende.signal == 'SIGINT'
    finally:
        ende.abmelden()
    assert signal.getsignal(signal.SIGINT) is vorher_int
    assert signal.getsignal(signal.SIGTERM) is vorher_term


def test_als_kontext_angemeldet_und_wieder_abgemeldet():
    vorher = signal.getsignal(signal.SIGINT)
    with Ende() as ende:
        assert signal.getsignal(signal.SIGINT) != vorher
        signal.raise_signal(signal.SIGINT)
        assert ende.gesetzt()
    assert signal.getsignal(signal.SIGINT) is vorher


def _falsches_rclpy(monkeypatch, ereignisse, ok=False):
    """Ein gespieltes rclpy-Modul, das jeden Aufruf mitschreibt."""
    falsch = types.ModuleType('rclpy')
    signale = types.ModuleType('rclpy.signals')

    class SignalHandlerOptions:
        NO = 'NO'
        ALL = 'ALL'

    signale.SignalHandlerOptions = SignalHandlerOptions
    zustand = {'ok': ok}
    falsch.ok = lambda: zustand['ok']

    def init(**kwargs):
        ereignisse.append(('init', kwargs))
        zustand['ok'] = True

    def shutdown():
        ereignisse.append(('shutdown',))
        zustand['ok'] = False

    falsch.init, falsch.shutdown, falsch.signals = init, shutdown, signale
    monkeypatch.setitem(sys.modules, 'rclpy', falsch)
    monkeypatch.setitem(sys.modules, 'rclpy.signals', signale)
    return falsch


def test_rclpy_startet_ohne_eigene_signal_handler(monkeypatch):
    ereignisse = []
    _falsches_rclpy(monkeypatch, ereignisse)
    assert ros_starten(args=['x']) is True
    assert ereignisse == [('init', {'args': ['x'], 'signal_handler_options': 'NO'})]
    # Läuft schon ein Kontext (Tests, eingebettet), bleibt er unberührt.
    assert ros_starten() is False
    assert len(ereignisse) == 1


def test_beenden_in_fester_reihenfolge_auch_wenn_eine_stufe_scheitert(monkeypatch):
    ereignisse = []
    _falsches_rclpy(monkeypatch, ereignisse, ok=True)

    class Ausfuehrer:
        def shutdown(self, timeout_sec):
            ereignisse.append(('ausfuehrer', timeout_sec))
            raise RuntimeError('schon beendet')

    class Knoten:
        def __init__(self, name):
            self.name = name

        def destroy_node(self):
            ereignisse.append(('knoten', self.name))
            if self.name == 'a':
                raise RuntimeError('kaputt')

    ros_beenden([Knoten('a'), None, Knoten('b')], ausfuehrer=Ausfuehrer())
    assert ereignisse == [('ausfuehrer', 5.0), ('knoten', 'a'), ('knoten', 'b'),
                          ('shutdown',)]
    # Fremder Kontext: nur Knoten, kein shutdown
    ereignisse.clear()
    ros_beenden([Knoten('c')], eigener_kontext=False)
    assert ereignisse == [('knoten', 'c')]


def test_kein_werkzeug_startet_rclpy_mit_den_vorgabe_handlern():
    """Jedes ROS-Werkzeug dieser Linie geht über ros_ende (gleiches Muster überall)."""
    for datei in sorted(WERKZEUGE.glob('*.py')):
        text = datei.read_text(encoding='utf-8')
        if datei.name == 'ros_ende.py':
            continue
        assert 'rclpy.init(' not in text, f'{datei.name}: rclpy.init direkt'
        assert 'rclpy.spin(' not in text, f'{datei.name}: rclpy.spin blockiert Signale'
        if 'import rclpy' in text and 'def main(' in text:       # Programme, keine Bibliotheken
            assert 'from ros_ende import' in text and 'ros_starten' in text, datei.name


KIND = textwrap.dedent('''
    import sys, time
    sys.path.insert(0, {werkzeuge!r})
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan
    from tf2_msgs.msg import TFMessage
    from geometry_msgs.msg import TransformStamped
    from ros_ende import Ende, ros_beenden, ros_starten

    ende = Ende().anmelden()
    eigener = ros_starten()
    knoten = rclpy.create_node('ki_test_signal_kind')
    zaehler = {{'tf': 0, 'scan': 0}}
    knoten.create_subscription(TFMessage, '/kitest_tf', lambda m: zaehler.__setitem__(
        'tf', zaehler['tf'] + 1), 50)
    knoten.create_subscription(LaserScan, '/kitest_scan', lambda m: zaehler.__setitem__(
        'scan', zaehler['scan'] + 1), qos_profile_sensor_data)
    tf_sender = knoten.create_publisher(TFMessage, '/kitest_tf', 50)
    scan_sender = knoten.create_publisher(LaserScan, '/kitest_scan', qos_profile_sensor_data)
    scan = LaserScan(); scan.ranges = [1.0] * 2160
    tf = TFMessage(); tf.transforms = [TransformStamped() for _ in range(5)]
    print('BEREIT', flush=True)
    letzte_tf = letzte_scan = 0.0
    try:
        while not ende.gesetzt() and rclpy.ok():
            jetzt = time.monotonic()
            if jetzt - letzte_tf >= 0.002:
                letzte_tf = jetzt
                tf_sender.publish(tf)
            if jetzt - letzte_scan >= 0.02:
                letzte_scan = jetzt
                scan_sender.publish(scan)
            rclpy.spin_once(knoten, timeout_sec=0.0005)
    finally:
        ros_beenden([knoten], eigener_kontext=eigener)
        ende.abmelden()
    print(f'sauber beendet ({{ende.signal}}), empfangen tf={{zaehler["tf"]}} '
          f'scan={{zaehler["scan"]}}', flush=True)
''')


def test_signal_mitten_im_lesen_endet_jedes_mal_sauber(tmp_path):
    """Kindprozess liest und sendet dicht (TF 500 Hz, Scan 50 Hz); je ein SIGINT."""
    pytest.importorskip('rclpy')
    skript = tmp_path / 'kind.py'
    skript.write_text(KIND.format(werkzeuge=str(WERKZEUGE)), encoding='utf-8')
    zufall = random.Random(7)
    for durchgang in range(8):
        kind = subprocess.Popen([sys.executable, str(skript)], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(50):                 # ROS-Warnungen vor der Zeile überspringen
                if kind.stdout.readline().strip() == 'BEREIT':
                    break
            else:
                pytest.fail('Kindprozess meldet sich nicht')
            signal_art = signal.SIGTERM if durchgang == 3 else signal.SIGINT
            try:
                kind.wait(timeout=zufall.uniform(0.3, 1.5))
            except subprocess.TimeoutExpired:
                pass
            kind.send_signal(signal_art)        # genau ein Signal an genau diese PID
            ausgabe, _ = kind.communicate(timeout=20)
        finally:
            if kind.poll() is None:
                kind.kill()
        assert kind.returncode == 0, ausgabe
        assert 'sauber beendet' in ausgabe and 'Traceback' not in ausgabe, ausgabe
        assert ros_ende.ENDE_SIGNALE == (signal.SIGINT, signal.SIGTERM)
