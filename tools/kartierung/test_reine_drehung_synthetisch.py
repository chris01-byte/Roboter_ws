#!/usr/bin/env python3
"""Regressionstest: verarbeitet slam_toolbox eine reine Drehung auf der Stelle?

WOZU: Der Humble-Zweig von slam_toolbox verwirft Scans vor Karto anhand der
Translation allein (Issue #807). Bei einer Drehung auf der Stelle ist die
Translation null, also wird jeder Scan verworfen und die Karte waechst nicht.
Der gepinnte Backport von PR #808 stellt die beabsichtigte ODER-Logik her und
macht das Verhalten ueber ``check_min_dist_and_heading_precisely`` schaltbar.

WAS DIESER TEST LEISTET: Er faehrt denselben synthetischen Datensatz zweimal
durch einen echten ``async_slam_toolbox_node`` - einmal mit dem Schalter auf
``true``, einmal auf ``false`` - und vergleicht, wie viele Posegraph-Knoten
dabei entstehen. Das ist ein A/B-Beweis ueber das VERHALTEN, nicht nur ueber die
Herkunft des Binaerpakets.

Der Test ist schaerfer als ein Fahrversuch: ``base_link`` bleibt exakt auf
(0, 0), die Translation ist also mathematisch null. Auf dem echten Roboter
rauscht die Odometrie, wodurch gelegentlich doch ein Knoten durchrutscht und
der Befund verwaschen wird.

KEINE HARDWARE: Es werden weder LiDAR noch Motoren noch RS485 benoetigt oder
angefasst. Der Test laeuft in einer eigenen ROS-Domaene (Standard 91), damit er
einen laufenden Roboter nicht sehen und nicht stoeren kann. Er publiziert
niemals auf /cmd_vel.

VORAUSSETZUNG: Das gepatchte Overlay muss gesourct sein.

    source /opt/ros/humble/setup.bash
    source ~/amadeus_slam_toolbox_ws/install/setup.bash
    source ~/roboter_ws/install/local_setup.bash
    python3 tools/kartierung/test_reine_drehung_synthetisch.py

Rueckgabewert 0 = beide Varianten verhalten sich wie erwartet.
"""
import argparse
import math
import os
import signal
import subprocess
import sys
import tempfile
import time

# Eigene ROS-Domaene setzen, BEVOR rclpy einen Kontext anlegt. Sonst wuerde der
# Test die synthetische Odometrie in den Graphen eines laufenden Roboters
# publizieren - genau das darf nie passieren.
_STANDARD_DOMAENE = '91'
if '--domaene' in sys.argv:
    _STANDARD_DOMAENE = sys.argv[sys.argv.index('--domaene') + 1]
os.environ['ROS_DOMAIN_ID'] = _STANDARD_DOMAENE

import rclpy                                        # noqa: E402
import yaml                                         # noqa: E402
from ament_index_python.packages import get_package_prefix  # noqa: E402
from geometry_msgs.msg import TransformStamped      # noqa: E402
from rclpy.duration import Duration                 # noqa: E402
from rclpy.node import Node                         # noqa: E402
from sensor_msgs.msg import LaserScan               # noqa: E402
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster  # noqa: E402
from visualization_msgs.msg import MarkerArray      # noqa: E402

from slam_graph_marker import zaehle_knoten_marker  # noqa: E402

HIER = os.path.dirname(os.path.abspath(__file__))
KONFIG = os.path.join(
    HIER, '..', '..', 'src', 'amadeus_lidar_bringup', 'config',
    'slam_toolbox_amadeus.yaml')

# Gemessene Montagepose des STL-27L, identisch zu stl27l.launch.py. Der
# Gierwinkel wird aus dem Quaternion abgeleitet, damit beide nicht auseinander
# laufen koennen.
MONTAGE_X, MONTAGE_Y, MONTAGE_Z = 0.245, 0.0, 0.660
MONTAGE_QZ, MONTAGE_QW = -0.707108, 0.707105
MONTAGE_YAW = 2.0 * math.atan2(MONTAGE_QZ, MONTAGE_QW)

# Ablauf einer Variante, in Sekunden.
RUHE_VOR = 8.0        # Stabilisierung; danach wird die Grundlinie gelesen
DREHUNG = 15.0        # volle 360 Grad, rund 0.42 rad/s
NACHLAUF = 3.0        # Stillstand, damit die letzte Graphmeldung noch ankommt
RUHE_NACH = 5.0       # Stillstand: hier darf nichts mehr dazukommen

SCANRATE = 10.0       # Hz, wie der echte STL-27L
STRAHLEN = 360
RANGE_MIN, RANGE_MAX = 0.02, 25.0

# Mindestzahl neuer Knoten, damit die Drehung als "verarbeitet" gilt.
# Theoretisch sind 2*pi/0.15 = 41 moeglich; Zeitfilter und Scanmatching
# duerfen das reduzieren. 5 ist bewusst weit unterhalb und trotzdem weit
# oberhalb des Fehlerbilds (dort sind es exakt 0).
MINDEST_KNOTEN = 5


class SynthetischerRaum:
    """Rechteckiger Raum mit einer Saeule, die die 180-Grad-Symmetrie bricht.

    Ohne die Saeule saehe ein Scan nach einer 180-Grad-Drehung fast genauso aus
    wie vorher; das Scanmatching koennte die Drehung dann wegerklaeren.
    """

    def __init__(self):
        # Rund 3.8 x 4.9 m, wie der dokumentierte Testraum.
        self.x0, self.x1 = -1.9, 1.9
        self.y0, self.y1 = -2.45, 2.45
        self.saeule = (0.9, -1.3, 0.18)   # x, y, Radius

    def strahl(self, px, py, richtung):
        """Entfernung vom Punkt (px, py) in Richtung ``richtung`` bis zur Wand."""
        dx, dy = math.cos(richtung), math.sin(richtung)
        t = float('inf')

        if dx > 1e-9:
            t = min(t, (self.x1 - px) / dx)
        elif dx < -1e-9:
            t = min(t, (self.x0 - px) / dx)
        if dy > 1e-9:
            t = min(t, (self.y1 - py) / dy)
        elif dy < -1e-9:
            t = min(t, (self.y0 - py) / dy)

        cx, cy, r = self.saeule
        ox, oy = px - cx, py - cy
        b = ox * dx + oy * dy
        c = ox * ox + oy * oy - r * r
        disk = b * b - c
        if disk >= 0.0:
            wurzel = math.sqrt(disk)
            for kandidat in (-b - wurzel, -b + wurzel):
                if kandidat > 1e-6:
                    t = min(t, kandidat)
                    break

        return min(t, RANGE_MAX)


def gierwinkel_zum_zeitpunkt(tau):
    """Bewegungsprofil: Stillstand, volle Drehung, Stillstand.

    Die Position bleibt dabei immer exakt (0, 0) - nur der Gierwinkel aendert
    sich. Genau dieser Fall wurde vom Vorfilter verworfen.
    """
    if tau < RUHE_VOR:
        return 0.0
    if tau < RUHE_VOR + DREHUNG:
        return 2.0 * math.pi * (tau - RUHE_VOR) / DREHUNG
    return 2.0 * math.pi


def parameterdatei_schreiben(schalter):
    """Amadeus-Konfiguration uebernehmen und nur den Schalter umlegen."""
    with open(KONFIG, 'r') as f:
        konfig = yaml.safe_load(f)
    p = konfig['slam_toolbox']['ros__parameters']
    p['check_min_dist_and_heading_precisely'] = schalter
    # Der Test speichert keine Karte und laedt keine; er soll nichts hinterlassen.
    p.pop('map_file_name', None)

    handle, pfad = tempfile.mkstemp(prefix='slam_ab_', suffix='.yaml')
    with os.fdopen(handle, 'w') as f:
        yaml.safe_dump(konfig, f)
    return pfad, p


class SyntheseKnoten(Node):
    """Publiziert synthetische TF und Scans und zaehlt die Posegraph-Knoten."""

    def __init__(self, raum):
        super().__init__('reine_drehung_synthetisch')
        self.raum = raum
        self.tf = TransformBroadcaster(self)
        self.tf_statisch = StaticTransformBroadcaster(self)
        self.knoten = 0
        self.graphmeldungen = 0
        self.create_subscription(
            MarkerArray, '/slam_toolbox/graph_visualization', self._auf_graph, 10)
        self._montage_senden()

    def _auf_graph(self, msg):
        self.graphmeldungen += 1
        self.knoten = zaehle_knoten_marker(msg.markers)

    def _montage_senden(self):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'base_link'
        t.child_frame_id = 'laser_frame'
        t.transform.translation.x = MONTAGE_X
        t.transform.translation.y = MONTAGE_Y
        t.transform.translation.z = MONTAGE_Z
        t.transform.rotation.z = MONTAGE_QZ
        t.transform.rotation.w = MONTAGE_QW
        self.tf_statisch.sendTransform(t)

    def odometrie_senden(self, yaw):
        """odom -> base_link. Position bleibt exakt null, nur Yaw aendert sich."""
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.z = math.sin(yaw / 2.0)
        t.transform.rotation.w = math.cos(yaw / 2.0)
        self.tf.sendTransform(t)

    def scan_senden(self, veroeffentlicher, yaw):
        """Scan aus der Sicht des mitgedrehten LiDAR erzeugen."""
        # Der LiDAR sitzt 0.245 m vor der Drehachse und wandert bei einer
        # Drehung auf einem Kreis. Fuer den Vorfilter zaehlt aber die Pose von
        # base_link, und die bleibt bei (0, 0).
        lx = math.cos(yaw) * MONTAGE_X - math.sin(yaw) * MONTAGE_Y
        ly = math.sin(yaw) * MONTAGE_X + math.cos(yaw) * MONTAGE_Y
        lyaw = yaw + MONTAGE_YAW

        inkrement = 2.0 * math.pi / STRAHLEN
        scan = LaserScan()
        # Leicht in die Vergangenheit stempeln, damit die TF sicher vorliegt.
        jetzt = self.get_clock().now()
        scan.header.stamp = (jetzt - Duration(seconds=0.05)).to_msg()
        scan.header.frame_id = 'laser_frame'
        scan.angle_min = -math.pi
        scan.angle_max = -math.pi + (STRAHLEN - 1) * inkrement
        scan.angle_increment = inkrement
        scan.time_increment = 0.0
        scan.scan_time = 1.0 / SCANRATE
        scan.range_min = RANGE_MIN
        scan.range_max = RANGE_MAX
        scan.ranges = [
            self.raum.strahl(lx, ly, lyaw + (-math.pi + k * inkrement))
            for k in range(STRAHLEN)
        ]
        veroeffentlicher.publish(scan)


def knoten_programm():
    """Pfad der ausfuehrbaren Datei ermitteln und die Herkunft pruefen.

    Bewusst NICHT ueber ``ros2 run``: dieser Wrapper reicht SIGINT nicht an das
    Kindprogramm weiter, der Knoten bliebe beim Aufraeumen haengen. Der direkte
    Aufruf macht ausserdem sichtbar, aus welchem Workspace das Binaerpaket
    stammt - ohne das gepatchte Overlay ist dieser Test bedeutungslos.
    """
    prefix = get_package_prefix('slam_toolbox')
    programm = os.path.join(prefix, 'lib', 'slam_toolbox',
                            'async_slam_toolbox_node')
    if not os.path.exists(programm):
        raise RuntimeError(f'Nicht gefunden: {programm}')
    if prefix.startswith('/opt/ros'):
        raise RuntimeError(
            f'slam_toolbox kommt aus {prefix}. Das ist die unveraenderte '
            f'apt-Version ohne den Backport; der Schalter existiert dort nicht. '
            f'Zuerst das Overlay sourcen.')
    return programm


def warte_auf_knoten(n, name, frist=30.0):
    """Wartet, bis der genannte ROS-Knoten im Graphen sichtbar ist."""
    ende = time.monotonic() + frist
    while time.monotonic() < ende:
        rclpy.spin_once(n, timeout_sec=0.2)
        if name in n.get_node_names():
            return True
    return False


def variante_fahren(schalter, ausfuehrlich):
    """Eine Variante komplett durchfahren und die Knotenzahlen zurueckgeben."""
    pfad, params = parameterdatei_schreiben(schalter)
    print(f'\n{"=" * 62}')
    print(f'Variante check_min_dist_and_heading_precisely = {schalter}')
    print(f'  minimum_travel_distance = {params["minimum_travel_distance"]} m')
    print(f'  minimum_travel_heading  = {params["minimum_travel_heading"]} rad')
    print('=' * 62, flush=True)

    # Ausgabe in eine Datei, nicht in eine Pipe: eine ungelesene Pipe laeuft
    # nach rund 64 kB voll und wuerde den Knoten mitten im Lauf blockieren.
    protokoll = tempfile.NamedTemporaryFile(
        prefix='slam_ab_', suffix='.log', delete=False, mode='w+')
    prozess = subprocess.Popen(
        [knoten_programm(), '--ros-args', '-r', '__node:=slam_toolbox',
         '--params-file', pfad],
        stdout=protokoll, stderr=subprocess.STDOUT)

    rclpy.init()
    raum = SynthetischerRaum()
    n = SyntheseKnoten(raum)
    scan_pub = n.create_publisher(LaserScan, '/scan', 10)

    ergebnis = {'schalter': schalter}
    try:
        if not warte_auf_knoten(n, 'slam_toolbox'):
            raise RuntimeError('slam_toolbox ist nicht hochgekommen.')

        gesamt = RUHE_VOR + DREHUNG + NACHLAUF + RUHE_NACH
        t0 = time.monotonic()
        naechster_scan = t0
        naechste_tf = t0
        grundlinie = None
        nach_drehung = None

        while rclpy.ok():
            jetzt = time.monotonic()
            tau = jetzt - t0
            if tau >= gesamt:
                break

            yaw = gierwinkel_zum_zeitpunkt(tau)

            if jetzt >= naechste_tf:
                n.odometrie_senden(yaw)
                naechste_tf += 0.01
            if jetzt >= naechster_scan:
                n.scan_senden(scan_pub, yaw)
                naechster_scan += 1.0 / SCANRATE

            rclpy.spin_once(n, timeout_sec=0.002)

            if grundlinie is None and tau >= RUHE_VOR:
                grundlinie = n.knoten
                print(f'  [{tau:5.1f}s] Grundlinie nach Stillstand: '
                      f'{grundlinie} Knoten', flush=True)
            if nach_drehung is None and tau >= RUHE_VOR + DREHUNG + NACHLAUF:
                nach_drehung = n.knoten
                print(f'  [{tau:5.1f}s] nach 360 Grad Drehung:      '
                      f'{nach_drehung} Knoten', flush=True)

        ende = n.knoten
        print(f'  [{gesamt:5.1f}s] nach abschliessendem Stillstand: '
              f'{ende} Knoten', flush=True)

        ergebnis.update({
            'grundlinie': grundlinie,
            'nach_drehung': nach_drehung,
            'ende': ende,
            'neu_durch_drehung': (nach_drehung - grundlinie),
            'neu_durch_stillstand': (ende - nach_drehung),
            'graphmeldungen': n.graphmeldungen,
        })
    finally:
        n.destroy_node()
        rclpy.shutdown()
        # SIGINT nur an diesen einen Prozess, nie an die Prozessgruppe.
        prozess.send_signal(signal.SIGINT)
        try:
            prozess.wait(timeout=25)
        except subprocess.TimeoutExpired:
            print('  WARNUNG: SIGINT blieb wirkungslos, sende SIGTERM.')
            prozess.terminate()
            prozess.wait(timeout=10)
        protokoll.close()
        if ausfuehrlich:
            print('--- Ausgabe von slam_toolbox ---')
            with open(protokoll.name) as f:
                print(f.read())
        os.unlink(pfad)
        os.unlink(protokoll.name)

    return ergebnis


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--domaene', default=_STANDARD_DOMAENE,
                   help='ROS_DOMAIN_ID fuer die Isolation (Standard 91)')
    p.add_argument('--ausfuehrlich', action='store_true',
                   help='Ausgabe von slam_toolbox mitdrucken')
    args = p.parse_args()

    print(f'Synthetischer Drehtest, ROS_DOMAIN_ID={os.environ["ROS_DOMAIN_ID"]}')
    print('Keine Hardware beteiligt: kein LiDAR, keine Motoren, kein RS485.')

    mit = variante_fahren(True, args.ausfuehrlich)
    ohne = variante_fahren(False, args.ausfuehrlich)

    print(f'\n{"=" * 62}')
    print('ERGEBNIS')
    print('=' * 62)
    print(f'{"Schalter":>10} {"Grundlinie":>11} {"nach Drehung":>13} '
          f'{"neu":>5} {"im Stillstand":>14}')
    for e in (mit, ohne):
        print(f'{str(e["schalter"]):>10} {e["grundlinie"]:>11} '
              f'{e["nach_drehung"]:>13} {e["neu_durch_drehung"]:>5} '
              f'{e["neu_durch_stillstand"]:>14}')

    fehler = []
    if mit['neu_durch_drehung'] < MINDEST_KNOTEN:
        fehler.append(
            f'Mit Schalter true kamen nur {mit["neu_durch_drehung"]} Knoten '
            f'dazu, erwartet mindestens {MINDEST_KNOTEN}. Der Backport wirkt '
            f'nicht.')
    if mit['neu_durch_stillstand'] != 0:
        fehler.append(
            f'Im abschliessenden Stillstand kamen {mit["neu_durch_stillstand"]} '
            f'Knoten dazu, erwartet 0 (Knotenflut).')
    if ohne['neu_durch_drehung'] != 0:
        fehler.append(
            f'Mit Schalter false kamen {ohne["neu_durch_drehung"]} Knoten dazu, '
            f'erwartet 0. Dann misst dieser Test nicht das Fehlerbild aus #807.')

    print()
    if fehler:
        print('FEHLGESCHLAGEN:')
        for f in fehler:
            print(f'  - {f}')
        return 1

    print('BESTANDEN: Die reine Drehung erzeugt nur mit dem Backport Knoten')
    print(f'  ({mit["neu_durch_drehung"]} gegen {ohne["neu_durch_drehung"]}), '
          f'bei identischen synthetischen Eingangsdaten.')
    print(f'  Das entspricht {360.0 / max(mit["neu_durch_drehung"], 1):.1f} '
          f'Grad je Knoten.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
