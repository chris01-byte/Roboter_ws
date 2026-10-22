#!/usr/bin/env python3
"""Abnahmestufe 2: geschlossene Robustheitssimulation des Selbstheilungsbetriebs.

Startet die vorhandene Produktkette mit den Produktparametern und dem Profil
`self_healing`:
- Missionsmanager, `bt_orchestrator`, Explorer;
- Nav2 (NavFn, RPP, Behavior-Server, BT-Navigator, Glätter);
- Fahrtor, Kollisionswächter mit Selbstheilungs-Overlay, Safety-Monitor;
- Scan-Normalisierung und `slam_toolbox`.

Die Welt (`sh_robustheit_welt.py`) liefert nur Sensorrohdaten und das
Fahrmodell. Die VL53-Wolken entstehen mit den unveränderten Rechenmethoden des
VL53-Knotens (`ap06_sensors.vl53_producer`). Kein Wahrheits-TF, keine
Wahrheitskarte, kein manuell gesendetes Navigationsziel. Gestartet wird die
Mission wie aus der App: `{"type":"explore"}` an den Missionsmanager.

Je Szenario wird genau eine Störung aus `sh_robustheit_szenarien_v4.json`
ausgelöst (v1–v3 = symmetrische Welt, gleiche Störungen, ältere Abnahme).
Bewertet wird nach dem dort vorab festgelegten Abnahmeteil.

`--experiment` mischt eine zusätzliche Parameterdatei über das Produktprofil.
Solche Läufe sind Messungen für eine Entscheidung, keine Abnahme; das Ergebnis
trägt dann die Qualifikation `experiment_keine_abnahme`.

Grenzen: Cloud, ROS 2 Jazzy statt Humble (nur Plugin-Klassennamen per
`sh_robustheit_jazzy.yaml` angepasst), ideale Odometrie statt HWT601/EKF,
keine echten Gerätelatenzen. Ersetzt keine Jetson- oder Realabnahme.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import numpy as np
import yaml

HIER = Path(__file__).resolve().parent
REPO = HIER.parents[1]
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(REPO/'tools/kartierung'))

ENDE = ('success', 'partial', 'blocked', 'failed', 'canceled')
NAV2 = ('planner_server', 'controller_server', 'behavior_server', 'bt_navigator',
        'velocity_smoother')


# ---------------------------------------------------------------------------
#  Reine Hilfen (ohne ROS testbar)
# ---------------------------------------------------------------------------

def tief_mischen(basis, overlay):
    """Overlay-Werte in eine Parameterstruktur übernehmen (wie ein 2. params-file)."""
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(basis.get(key), dict):
            tief_mischen(basis[key], value)
        else:
            basis[key] = value
    return basis


def jazzy_kompatibel(p):
    """Nur Formatunterschiede Humble -> Jazzy, gleiche Werte.

    Jazzy erwartet Polygonpunkte des collision_monitor als Text
    "[[x, y], ...]" statt als flache Zahlenliste.
    """
    cm = p.get('collision_monitor', {}).get('ros__parameters', {})
    for name in cm.get('polygons', []):
        punkte = cm.get(name, {}).get('points')
        if isinstance(punkte, list) and punkte and not isinstance(punkte[0], list):
            paare = [[float(punkte[i]), float(punkte[i+1])] for i in range(0, len(punkte), 2)]
            cm[name]['points'] = json.dumps(paare)
    return p


def produktparameter(repo):
    """Eine Parameterdatei aus den Produktprofilen; nur Jazzy-Klassennamen ersetzt."""
    def lade(relativ):
        return yaml.safe_load((repo/relativ).read_text(encoding='utf-8'))
    p = lade('src/robot_navigation/config/nav2_params_real.yaml')
    tief_mischen(p, lade('src/robot_navigation/config/nav2_params_self_healing.yaml'))
    tief_mischen(p, lade('tools/simulation/sh_robustheit_jazzy.yaml'))
    bt = p.setdefault('bt_navigator', {}).setdefault('ros__parameters', {})
    bt['default_nav_to_pose_bt_xml'] = str(
        repo/'src/explore/behavior_trees/navigate_to_pose_self_healing.xml')
    bt['default_nav_through_poses_bt_xml'] = str(
        repo/'tools/simulation/navigate_through_poses_no_recovery.xml')
    p['slam_toolbox'] = lade('src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml')['slam_toolbox']
    tief_mischen(p['slam_toolbox'], lade(
        'src/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml')['slam_toolbox'])
    p['slam_toolbox']['ros__parameters']['scan_topic'] = '/scan_normiert'
    kollision = lade('src/vl53_near_field/config/collision_monitor_mapping_params.yaml')
    tief_mischen(kollision, lade(
        'src/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml'))
    p.update(kollision)
    jazzy_kompatibel(p)
    p['lifecycle_manager_navigation'] = {'ros__parameters': {
        'autostart': True, 'node_names': list(NAV2)}}
    p['lifecycle_manager_collision'] = {'ros__parameters': {
        'autostart': True, 'node_names': ['collision_monitor']}}
    return p


def plan_engstelle(alt, abstaende, punkte, t_s, robot_radius, roboter=None, nah_m=1.):
    """Engste Stelle der globalen Pläne (Abstand der Planmitte zum Hindernis).

    Gesamtwert über ganze Pläne (frühe Pläne queren Unbekanntes und dürfen
    nah an noch ungesehene Wände führen) und Nahwert: nur Planpunkte bis
    ``nah_m`` um den Roboter, also der Abschnitt, den der Regler gerade fährt.
    """
    alt = dict(alt or {'abstand_m': None, 'plaene': 0, 'plaene_unter_robot_radius': 0,
                       'nah_abstand_m': None, 'nah_unter_robot_radius': []})
    alt['plaene'] += 1
    if len(abstaende) == 0:
        return alt
    abstaende = np.asarray(abstaende, dtype=float)
    i = int(np.argmin(abstaende))
    wert = float(abstaende[i])
    if wert < robot_radius:
        alt['plaene_unter_robot_radius'] += 1
    if alt['abstand_m'] is None or wert < alt['abstand_m']:
        alt.update(abstand_m=round(wert, 4), punkt=[round(float(v), 3) for v in punkte[i]], t_s=t_s)
    if roboter is not None:
        nah = np.hypot(*(np.asarray(punkte, dtype=float) - np.asarray(roboter[:2])).T) <= nah_m
        if nah.any():
            j = int(np.argmin(np.where(nah, abstaende, np.inf)))
            wert = float(abstaende[j])
            if alt['nah_abstand_m'] is None or wert < alt['nah_abstand_m']:
                alt.update(nah_abstand_m=round(wert, 4),
                           nah_punkt=[round(float(v), 3) for v in punkte[j]], nah_t_s=t_s)
            if wert < robot_radius and len(alt['nah_unter_robot_radius']) < 40:
                alt['nah_unter_robot_radius'].append(
                    {'t_s': t_s, 'abstand_m': round(wert, 4),
                     'punkt': [round(float(v), 3) for v in punkte[j]]})
    return alt


def kostenkarte_ueber(karte, ecken_odom):
    """Belegung der lokalen Kostenkarte über einem Hindernis (Odometrierahmen).

    ``karte``: (Werte HxW, Auflösung, Ursprung x, Ursprung y) im Nav2-Format
    der OccupancyGrid-Übersetzung (100 = tödlich, 99 = eingeschrieben,
    -1 = unbekannt). Liefert, ob der Regler das Hindernis kennen konnte.
    """
    if karte is None:
        return None
    werte, aufloesung, ox, oy = karte
    ecken = np.asarray(ecken_odom, dtype=float)
    lo, hi = ecken.min(axis=0), ecken.max(axis=0)
    c0, r0 = (int(math.floor((v-o)/aufloesung)) for v, o in zip(lo, (ox, oy)))
    c1, r1 = (int(math.floor((v-o)/aufloesung)) for v, o in zip(hi, (ox, oy)))
    r0, c0 = max(r0, 0), max(c0, 0)
    r1, c1 = min(r1, werte.shape[0]-1), min(c1, werte.shape[1]-1)
    if r0 > r1 or c0 > c1:
        return {'zellen': 0, 'im_fenster': False}
    teil = werte[r0:r1+1, c0:c1+1]
    return {'zellen': int(teil.size), 'im_fenster': True,
            'toedlich': int(np.count_nonzero(teil >= 100)),
            'eingeschrieben_oder_mehr': int(np.count_nonzero(teil >= 99)),
            'unbekannt': int(np.count_nonzero(teil < 0)),
            'max': int(teil.max())}


def ausloeser_erfuellt(ausloeser, ziele, pose, geschwindigkeit, seit_start_s):
    if not ausloeser:
        return True
    if ziele < ausloeser.get('ziele_erreicht', 0):
        return False
    if 'x_ueber_m' in ausloeser and not pose[0] > ausloeser['x_ueber_m']:
        return False
    if ausloeser.get('faehrt') and not abs(geschwindigkeit) > 0.03:
        return False
    if seit_start_s < ausloeser.get('nach_start_s', 0.0):
        return False
    return True


def bewerte(abnahme, szenario, zusammenfassung, stoerung, kollision, abgestuerzt, abdeckung=None,
            karte=None):
    """Vorab festgelegte Kriterien; liefert (bestanden, Einzelkriterien).

    Manifest v1: Zielzähler. Manifest v2 (``min_abdeckung_erreichbar``,
    Entscheidung D): Kartenabdeckung der erreichbaren Fläche oder sauberes
    Teilende statt Zielzähler. Manifest v3 (``max_kartenfehler_m``): Abdeckung
    ohne Teilende-Ausnahme und Kartenfehler höchstens ``max_kartenfehler_m``.
    """
    ende = (zusammenfassung.get('endzustand') or {})
    ziele = ende.get('goals_reached') or 0
    erwartet = szenario.get('erwartet') or {}
    k = {
        'mission_beendet': zusammenfassung.get('kriterien_automatisch', {}).get('fahrt_beendet', False),
        'sauberes_ende': ende.get('outcome') in abnahme['erlaubte_enden'],
    }
    v2 = 'min_abdeckung_erreichbar' in abnahme
    anteil = (abdeckung or {}).get('erreichbar_anteil')
    genug = anteil is not None and anteil >= abnahme.get('min_abdeckung_erreichbar', 2.)
    if 'max_kartenfehler_m' in abnahme:
        fehler = (karte or {}).get('maximum_occupied_wall_error_m')
        k['abdeckung_erreichbar'] = genug
        k['karte_plausibel'] = fehler is not None and fehler <= abnahme['max_kartenfehler_m']
    elif v2:
        k['abdeckung_oder_teilende'] = bool(
            genug or (abnahme.get('teilende_genuegt') and ende.get('outcome') == 'usable_partial'))
    else:
        k['mindestens_ziele'] = ziele >= abnahme['min_ziele']
    k['keine_kollision'] = not kollision
    k['kein_prozessabsturz'] = not abgestuerzt
    if szenario.get('stoerung'):
        k['stoerung_ausgeloest'] = stoerung.get('ausgeloest_s') is not None
        if not v2:
            mindest = erwartet.get('min_ziele_nach_stoerung', abnahme['min_ziele_nach_stoerung'])
            k['ziele_nach_stoerung'] = (ziele - (stoerung.get('ziele_bei_ausloesung') or 0)) >= mindest
        teil = erwartet.get('warten_auf_enthaelt')
        if teil:
            k['heilung_beobachtet'] = any(
                e.get('art') == 'selbstheilung' and teil in str(e.get('waiting_for') or '')
                for e in zusammenfassung.get('ereignisse', []))
    return all(k.values()), k


# ---------------------------------------------------------------------------
#  ROS-Teil
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--szenario', required=True)
    parser.add_argument('--ausgabe', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=HIER/'sh_robustheit_szenarien_v4.json')
    parser.add_argument('--domain', type=int, default=231)
    parser.add_argument('--experiment', type=Path, default=None,
                        help='zusätzliche Parameterdatei über dem Produktprofil (keine Abnahme)')
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    szenario = next(s for s in manifest['szenarien'] if s['id'] == args.szenario)
    out = args.ausgabe
    out.mkdir(parents=True, exist_ok=False)
    os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'   # wie am Roboter
    os.environ.pop('CYCLONEDDS_URI', None)
    params_file = out/'produkt_params.yaml'
    parameter = produktparameter(REPO)
    experiment = None
    explorer_bt = REPO/'src/explore/behavior_trees/navigate_to_pose_self_healing.xml'
    if args.experiment is not None:
        experiment = yaml.safe_load(args.experiment.read_text(encoding='utf-8'))
        # Nur für Experimente: anderer Nav2-Baum des Explorers (Pfad relativ zur Datei).
        treiber = dict(experiment.pop('sh_treiber', None) or {})
        if treiber.get('explorer_behavior_tree'):
            explorer_bt = (args.experiment.parent/treiber['explorer_behavior_tree']).resolve()
        jazzy_kompatibel(tief_mischen(parameter, experiment))
        experiment['sh_treiber'] = treiber
    params_file.write_text(yaml.safe_dump(parameter))
    robot_radius = float(parameter['global_costmap']['global_costmap']['ros__parameters']
                         .get('robot_radius', 0.))
    (out/'manifest.json').write_bytes(args.manifest.read_bytes())

    import rclpy
    from ament_index_python.packages import get_package_prefix
    from geometry_msgs.msg import TransformStamped, Twist
    from lifecycle_msgs.srv import ChangeState, GetState
    from nav_msgs.msg import OccupancyGrid, Odometry, Path as NavPath
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.node import Node
    from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                           qos_profile_sensor_data)
    from robot_interfaces.msg import NearFieldStatus
    from sensor_msgs.msg import LaserScan, PointCloud2
    from std_msgs.msg import Bool, String
    from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster

    from ap06_sensors import vl53_producer
    from sh_robustheit_welt import RobustheitsWelt
    from selbstheilung_lauf_protokoll import LaufProtokoll

    welt = RobustheitsWelt(manifest['welt']['door_m'], manifest['welt']['start'],
                           zusatz=manifest['welt'].get('zusatz_hindernisse', ()))
    sensor = manifest['sensor']
    latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
    zustand = dict(vl53_pause_bis=0.0, lidar_pause_bis=0.0, cmd=(0.0, 0.0), cmd_zeit=0.0)

    class Anlage(Node):
        """Fahrmodell und Sensorrohdaten; veröffentlicht keine Karte."""

        def __init__(self):
            super().__init__('sh_simulierte_anlage')
            self.letzt = time.monotonic()
            self.scan_pub = self.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
            self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
            pubs = dict(
                pub_left=self.create_publisher(PointCloud2, '/near_field/left/points', 10),
                pub_right=self.create_publisher(PointCloud2, '/near_field/right/points', 10),
                pub_left_cm=self.create_publisher(PointCloud2, '/near_field/left/points_costmap', 10),
                pub_right_cm=self.create_publisher(PointCloud2, '/near_field/right/points_costmap', 10),
                pub_status=self.create_publisher(NearFieldStatus, '/near_field/status', 10))
            self.vl53 = vl53_producer(self, welt, pubs)
            self.tf = TransformBroadcaster(self)
            self.static = StaticTransformBroadcaster(self)
            transforms = []
            for frame, x, y, z, yaw in (('laser_frame', .245, 0., .660, math.pi/2),
                                        ('vl53_left_link', .290, .095, .215, 0.),
                                        ('vl53_right_link', .290, -.095, .215, 0.)):
                t = TransformStamped()
                t.header.stamp = self.get_clock().now().to_msg()
                t.header.frame_id, t.child_frame_id = 'base_link', frame
                t.transform.translation.x, t.transform.translation.y = x, y
                t.transform.translation.z = z
                t.transform.rotation.z, t.transform.rotation.w = math.sin(yaw/2), math.cos(yaw/2)
                transforms.append(t)
            self.static.sendTransform(transforms)
            self.create_subscription(Twist, '/cmd_vel', self.on_cmd, 10)
            self.create_timer(.01, self.tick)
            self.create_timer(.1, self.sensoren)
            self.zaehler = 0

        def on_cmd(self, msg):
            zustand['cmd'] = (float(msg.linear.x), float(msg.angular.z))
            zustand['cmd_zeit'] = time.monotonic()

        def tick(self):
            jetzt = time.monotonic()
            dt, self.letzt = jetzt - self.letzt, jetzt
            cmd = zustand['cmd'] if jetzt - zustand['cmd_zeit'] <= .25 else (0.0, 0.0)
            welt.zeit_s = round(jetzt - start, 2)
            vorher = welt.engste_stelle
            welt.integrate(cmd, dt)
            if welt.engste_stelle is not vorher and welt.minimum_clearance < .03:
                # Kannte der Regler das Hindernis, an dem es eng wird?
                box, niedrig = welt.naechstes_hindernis()
                welt.engste_stelle['hindernis_niedrig'] = niedrig
                welt.engste_stelle['hindernis'] = [[round(float(v), 3) for v in box.min(axis=0)],
                                                   [round(float(v), 3) for v in box.max(axis=0)]]
                welt.engste_stelle['lokale_kostenkarte'] = kostenkarte_ueber(
                    beobachter.lokal, welt.local(box))
            self.zaehler += 1
            if self.zaehler % 2 == 0:
                self.odom(jetzt)

        def odom(self, jetzt):
            lokal = welt.local([welt.pose[:2]])[0]
            yaw = welt.pose[2] - welt.start[2]
            stamp = self.get_clock().now().to_msg()
            t = TransformStamped()
            t.header.stamp, t.header.frame_id, t.child_frame_id = stamp, 'odom', 'base_link'
            t.transform.translation.x, t.transform.translation.y = float(lokal[0]), float(lokal[1])
            t.transform.rotation.z, t.transform.rotation.w = math.sin(yaw/2), math.cos(yaw/2)
            self.tf.sendTransform(t)
            o = Odometry()
            o.header.stamp, o.header.frame_id, o.child_frame_id = stamp, 'odom', 'base_link'
            o.pose.pose.position.x, o.pose.pose.position.y = float(lokal[0]), float(lokal[1])
            o.pose.pose.orientation.z, o.pose.pose.orientation.w = math.sin(yaw/2), math.cos(yaw/2)
            o.twist.twist.linear.x, o.twist.twist.angular.z = (
                float(welt.velocity[0]), float(welt.velocity[1]))
            self.odom_pub.publish(o)

        def sensoren(self):
            jetzt = time.monotonic()
            if jetzt >= zustand['lidar_pause_bis']:
                winkel, ranges = welt.laser(beams=sensor['lidar_beams'], mask=sensor['mastmaske'])
                scan = LaserScan()
                scan.header.stamp = self.get_clock().now().to_msg()
                scan.header.frame_id = 'laser_frame'
                scan.angle_min, scan.angle_max = 0., float(winkel[-1])
                scan.angle_increment, scan.scan_time = float(winkel[1]), .1
                scan.range_min, scan.range_max = .05, 10.
                scan.ranges = ranges.astype(np.float32).tolist()
                self.scan_pub.publish(scan)
            if jetzt >= zustand['vl53_pause_bis']:
                self.vl53._tick()

    class Beobachter(Node):
        def __init__(self, protokoll):
            super().__init__('sh_beobachter')
            self.protokoll = protokoll
            self.karte = None
            self.erste_karte = None
            self.plan = None
            self.lokal = None          # (Werte, Auflösung, Ursprung x, y) im odom-Rahmen
            self.explore = None
            self.mission = None
            self.befehl = self.create_publisher(String, '/mission_manager/command_json', 10)
            self.karten_pub = self.create_publisher(OccupancyGrid, '/map', latched)
            self.create_subscription(OccupancyGrid, '/map', self.on_map, latched)
            self.create_subscription(String, '/explore/status_json', self.on_explore, 10)
            self.create_subscription(String, '/mission_manager/status_json', self.on_mission, latched)
            self.create_subscription(Bool, '/safety/estop',
                                     lambda m: protokoll.estop_wert(bool(m.data), time.monotonic()),
                                     latched)
            self.create_subscription(Twist, '/cmd_vel',
                                     lambda m: protokoll.cmd_vel(m.linear.x, m.angular.z), 10)
            self.create_subscription(Odometry, '/odom',
                                     lambda m: protokoll.odom(m.pose.pose.position.x,
                                                              m.pose.pose.position.y), 10)
            self.create_subscription(NearFieldStatus, '/near_field/status',
                                     lambda m: protokoll.vl53(time.monotonic()), 10)
            self.create_subscription(NavPath, '/plan', self.on_plan, 10)
            self.create_subscription(OccupancyGrid, '/local_costmap/costmap', self.on_lokal,
                                     QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                                durability=DurabilityPolicy.VOLATILE))
            self.zustand_clients = {n: self.create_client(GetState, f'/{n}/get_state')
                                    for n in (*NAV2, 'collision_monitor')}

        def on_map(self, msg):
            if self.erste_karte is None:
                self.erste_karte = msg
            self.karte = msg

        def on_lokal(self, msg):
            i = msg.info
            self.lokal = (np.asarray(msg.data, dtype=np.int16).reshape(i.height, i.width),
                          i.resolution, i.origin.position.x, i.origin.position.y)

        def on_plan(self, msg):
            # Karte ~ Odometrie ~ Startpose; SLAM-Drift (wenige cm) bleibt als Fehler.
            punkte = welt.karte_zu_welt([(q.pose.position.x, q.pose.position.y)
                                         for q in msg.poses]) if msg.poses else np.zeros((0, 2))
            self.plan = plan_engstelle(self.plan, welt.punkte_abstand(punkte) if len(punkte) else [],
                                       punkte, round(time.monotonic() - start, 2), robot_radius,
                                       roboter=welt.pose.copy())

        def on_explore(self, msg):
            try:
                daten = json.loads(msg.data)
            except ValueError:
                return
            self.explore = daten
            self.protokoll.explore(daten, time.monotonic())

        def on_mission(self, msg):
            try:
                daten = json.loads(msg.data)
            except ValueError:
                return
            self.mission = daten
            self.protokoll.mission(daten, time.monotonic())

        def uebergang(self, name, transition_id):
            """Lifecycle-Übergang (nur slam_toolbox unter Jazzy, siehe Aufrufer)."""
            client = self.create_client(ChangeState, f'/{name}/change_state')
            if not client.wait_for_service(timeout_sec=20.):
                raise TimeoutError(f'{name}/change_state')
            request = ChangeState.Request()
            request.transition.id = transition_id
            future = client.call_async(request)
            ende = time.monotonic() + 20.
            while not future.done() and time.monotonic() < ende:
                time.sleep(.02)
            if not future.done() or not future.result().success:
                raise RuntimeError(f'{name}: Übergang {transition_id} abgelehnt')

        def lifecycle(self, name):
            client = self.zustand_clients[name]
            if not client.service_is_ready():
                return None
            future = client.call_async(GetState.Request())
            ende = time.monotonic() + 2.
            while not future.done() and time.monotonic() < ende:
                time.sleep(.02)
            return future.result().current_state.label if future.done() else None

    prozesse, streams = [], []

    def starte(name, befehl):
        with (out/'befehle.jsonl').open('a') as handle:
            handle.write(json.dumps({'name': name, 'argv': befehl})+'\n')
        stream = (out/f'{name}.log').open('w')
        streams.append(stream)
        prozesse.append((name, subprocess.Popen(
            befehl, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)))

    def exe(paket, name):
        return str(Path(get_package_prefix(paket))/'lib'/paket/name)

    def warte(bedingung, sekunden, was):
        ende = time.monotonic() + sekunden
        while time.monotonic() < ende:
            if bedingung():
                return
            time.sleep(.1)
        raise TimeoutError(was)

    ergebnis = {'szenario': szenario, 'bestanden': False, 'qualifikation': manifest['qualifikation'],
                'wahrheits_tf': False, 'wahrheitskarte': False, 'manuelle_ziele': 0}
    if experiment is not None:
        ergebnis['qualifikation'] = 'experiment_keine_abnahme'
        ergebnis['experiment'] = {'datei': args.experiment.name, 'parameter': experiment}
    stoerung = {'ausgeloest_s': None, 'beendet_s': None, 'ziele_bei_ausloesung': None}
    last = []
    last_verlauf = []          # (s seit Start, 1-min-Last) je Sekunde
    rclpy.init()
    start = time.monotonic()
    protokoll = LaufProtokoll(start)
    anlage, beobachter = Anlage(), Beobachter(protokoll)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(anlage)
    executor.add_node(beobachter)
    threading.Thread(target=executor.spin, daemon=True).start()
    p = ['--ros-args', '--params-file', str(params_file)]
    try:
        starte('scan_normierung', [exe('amadeus_lidar_bringup', 'scan_vereinheitlichen'),
               '--ros-args', '-p', f'strahlen:={sensor["lidar_beams"]}'])
        starte('safety_monitor', [exe('safety_monitor', 'safety_monitor'), '--ros-args',
               '--params-file', str(REPO/'src/safety_monitor/config/safety_monitor_params.yaml')])
        starte('slam_toolbox', [exe('slam_toolbox', 'async_slam_toolbox_node'), *p])
        # Jazzy: slam_toolbox ist ein Lifecycle-Knoten (Humble startet von
        # selbst). Wie das Jazzy-Launchfile: configure (1), dann activate (3).
        beobachter.uebergang('slam_toolbox', 1)
        beobachter.uebergang('slam_toolbox', 3)
        warte(lambda: beobachter.karte is not None, manifest['budgets']['start_s'], 'erste SLAM-Karte')
        gate = ['--ros-args', '-p', 'require_localization:=false', '-p', 'require_hwt601_fusion:=false',
                '-p', 'hwt601_active_drive:=true', '-p', 'hwt_development_contract:=false',
                '-p', 'allow_localization_search:=false', '-p', 'allow_explore_mission:=true',
                '-p', 'allow_stage3_motion_diagnostic:=false']
        starte('fahrtor', [exe('robot_navigation', 'cmd_vel_mission_gate'), *gate])
        for paket, name, remap in (
                ('nav2_planner', 'planner_server', []),
                ('nav2_controller', 'controller_server', ['-r', 'cmd_vel:=cmd_vel_nav_raw']),
                ('nav2_behaviors', 'behavior_server', ['-r', 'cmd_vel:=cmd_vel_nav_raw']),
                ('nav2_bt_navigator', 'bt_navigator', []),
                ('nav2_velocity_smoother', 'velocity_smoother',
                 ['-r', 'cmd_vel:=cmd_vel_nav', '-r', 'cmd_vel_smoothed:=cmd_vel_smoothed']),
                ('nav2_collision_monitor', 'collision_monitor', [])):
            starte(name, [exe(paket, name), *p, *remap])
        for name in ('lifecycle_manager_navigation', 'lifecycle_manager_collision'):
            starte(name, [exe('nav2_lifecycle_manager', 'lifecycle_manager'), *p,
                          '-r', f'__node:={name}'])
        warte(lambda: all(beobachter.lifecycle(n) == 'active' for n in (*NAV2, 'collision_monitor')),
              manifest['budgets']['start_s'], 'Nav2 und Kollisionswächter aktiv')
        starte('explorer', [exe('explore', 'explore'), '--ros-args',
               '--params-file', str(REPO/'src/explore/config/explore_params.yaml'),
               '--params-file', str(REPO/'src/explore/config/self_healing_params.yaml'),
               '-p', f'behavior_tree:={explorer_bt}',
               '-p', 'require_hwt601_fusion:=false', '-p', 'hwt601_active_drive:=true',
               '-p', 'hwt_development_contract:=false',
               '-p', f'overall_timeout_s:={float(manifest["budgets"]["mission_s"])}'])
        starte('bt_orchestrator', [exe('bt_orchestrator', 'bt_orchestrator'), '--ros-args',
               '--params-file', str(REPO/'src/bt_orchestrator/config/bt_params.yaml'),
               '-p', f'explore_xml:={REPO}/src/bt_orchestrator/bt_xml/explore.xml'])
        starte('mission_manager', [exe('mission_manager', 'mission_manager'), '--ros-args',
               '--params-file', str(REPO/'src/mission_manager/config/mission_catalog.yaml'),
               '-p', 'enable_real_explore:=true'])
        warte(lambda: (beobachter.explore or {}).get('backend_ready') is True
              and beobachter.mission is not None, manifest['budgets']['start_s'],
              'Explorer und Missionsmanager bereit')
        time.sleep(3.)
        missionsstart = time.monotonic()
        beobachter.befehl.publish(String(data=json.dumps({'type': 'explore'})))
        ergebnis['missionsstart_s'] = round(missionsstart - start, 2)
        art = (szenario.get('stoerung') or {}).get('art')
        stoer = szenario.get('stoerung') or {}
        frist = missionsstart + manifest['budgets']['mission_s'] + manifest['budgets']['ueberzug_s']
        gemeldet = 0
        while time.monotonic() < frist:
            time.sleep(.2)
            jetzt = time.monotonic()
            if int(jetzt - start) != (last_verlauf[-1][0] if last_verlauf else -1):
                last_verlauf.append((int(jetzt - start), os.getloadavg()[0]))
            for e in protokoll.ereignisse[gemeldet:]:
                print('EREIGNIS', json.dumps(e, ensure_ascii=False), flush=True)
            gemeldet = len(protokoll.ereignisse)
            if protokoll.beendet_um is not None and jetzt - protokoll.beendet_um >= manifest['budgets']['nachlauf_s']:
                break
            if (protokoll.gestartet_um is None and jetzt - missionsstart > 30.
                    and (beobachter.mission or {}).get('state') == 'failed'):
                ergebnis['fehler'] = 'Mission vor dem Explorerstart gescheitert'
                break
            if art and stoerung['ausgeloest_s'] is None:
                ziele = (protokoll.self_healing or {}).get('goals_reached') or 0
                if ausloeser_erfuellt(stoer.get('ausloeser'), ziele, welt.pose,
                                      welt.velocity[0], jetzt - missionsstart):
                    ok = True
                    if art == 'vl53_pause':
                        zustand['vl53_pause_bis'] = jetzt + stoer['dauer_s']
                    elif art == 'lidar_pause_und_alte_karte':
                        zustand['lidar_pause_bis'] = jetzt + stoer['dauer_s']
                    elif art == 'cpu_last':
                        last = [subprocess.Popen([sys.executable, '-c', 'while True: pass'])
                                for _ in range(os.cpu_count() or 2)]
                    elif art == 'niedriges_hindernis':
                        x, y, yaw = welt.pose
                        mitte = (x + math.cos(yaw)*stoer['abstand_m'], y + math.sin(yaw)*stoer['abstand_m'])
                        half = stoer['groesse_m']/2
                        box = np.array([(mitte[0]-half, mitte[1]-half), (mitte[0]+half, mitte[1]-half),
                                        (mitte[0]+half, mitte[1]+half), (mitte[0]-half, mitte[1]+half)])
                        ok = welt.frei(box)
                        if ok:
                            welt.setze_niedriges_hindernis(mitte, stoer['groesse_m'], stoer['hoehe_m'])
                            stoerung['position'] = [round(mitte[0], 3), round(mitte[1], 3)]
                    elif art == 'tuer_schliessen':
                        welt.schliesse_tuer(stoer['seite'])
                    if ok:
                        print('STOERUNG', art, json.dumps(stoer.get('ausloeser')), flush=True)
                        stoerung['ausgeloest_s'] = round(jetzt - start, 2)
                        stoerung['ziele_bei_ausloesung'] = ziele
                        stoerung['pose'] = [round(v, 3) for v in welt.pose.tolist()]
            if stoerung['ausgeloest_s'] is not None and stoerung['beendet_s'] is None:
                dauer = stoer.get('dauer_s')
                if dauer is None or jetzt - start - stoerung['ausgeloest_s'] >= dauer:
                    if art == 'lidar_pause_und_alte_karte' and beobachter.erste_karte is not None:
                        alte = beobachter.erste_karte     # ältere Karte nach neuerer
                        beobachter.karten_pub.publish(alte)
                        stoerung['alte_karte_gesendet'] = True
                    for proc in last:
                        proc.terminate()
                    last = []
                    stoerung['beendet_s'] = round(jetzt - start, 2)
        ergebnis['nav2_nach_der_fahrt'] = {n: beobachter.lifecycle(n) for n in (*NAV2, 'collision_monitor')}
        abgestuerzt = [n for n, proc in prozesse if proc.poll() is not None]
        ergebnis['abgestuerzte_prozesse'] = abgestuerzt
        if beobachter.karte is not None:
            k = beobachter.karte
            belegung = np.asarray(k.data, dtype=np.int16).reshape(k.info.height, k.info.width)
            ergebnis['karte'] = welt.map_oracle(
                belegung, k.info.resolution, (k.info.origin.position.x, k.info.origin.position.y))
            ergebnis['abdeckung_erreichbar'] = welt.abdeckung_erreichbar(
                belegung, k.info.resolution, (k.info.origin.position.x, k.info.origin.position.y))
    except Exception as fehler:  # noqa: BLE001 - als Befund festhalten
        ergebnis['fehler'] = f'{type(fehler).__name__}: {fehler}'
        abgestuerzt = [n for n, proc in prozesse if proc.poll() is not None]
        ergebnis['abgestuerzte_prozesse'] = abgestuerzt
    finally:
        for proc in last:
            proc.terminate()
        for name, proc in reversed(prozesse):
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)          # einzeln, nie die Gruppe
        ende = time.monotonic() + 15.
        for name, proc in prozesse:
            try:
                proc.wait(timeout=max(.1, ende - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=5.)
                except subprocess.TimeoutExpired:
                    proc.kill()
        for stream in streams:
            stream.close()
        executor.shutdown()
        rclpy.try_shutdown()

    zusammenfassung = protokoll.zusammenfassung()
    ergebnis['stoerung'] = stoerung
    ergebnis['fahrtprotokoll'] = zusammenfassung
    ergebnis['kollision'] = bool(welt.collision)
    ergebnis['minimaler_abstand_m'] = (None if not math.isfinite(welt.minimum_clearance)
                                       else round(float(welt.minimum_clearance), 3))
    ergebnis['engste_stelle'] = welt.engste_stelle
    ergebnis['mitte_engste_stelle'] = welt.mitte_min
    ergebnis['plan_engste_stelle'] = beobachter.plan
    ergebnis['robot_radius_global_m'] = robot_radius
    ergebnis['strecke_welt_m'] = round(float(welt.travel), 2)
    groesste = sorted(zip(welt.verspaetungen, welt.verspaetungen_zeit), reverse=True)[:5]
    ergebnis['timer_verspaetungen'] = {'anzahl': len(welt.verspaetungen),
                                      'max_s': max(welt.verspaetungen, default=0.),
                                      'groesste': [{'luecke_s': d, 't_s': t} for d, t in groesste]}
    ergebnis['rechnerlast'] = {'kerne': os.cpu_count(),
                               'last_1min_max': max((v for _, v in last_verlauf), default=None),
                               'verlauf_alle_10_s': [(t, round(v, 2)) for t, v in last_verlauf
                                                     if t % 10 == 0]}
    if 'fehler' in ergebnis:
        ergebnis['kriterien'] = {'ablauf_ohne_harnessfehler': False}
    else:
        ergebnis['bestanden'], ergebnis['kriterien'] = bewerte(
            manifest['abnahme'], szenario, zusammenfassung, stoerung,
            welt.collision, ergebnis['abgestuerzte_prozesse'], ergebnis.get('abdeckung_erreichbar'),
            ergebnis.get('karte'))
    (out/'ergebnis.json').write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2, default=str))
    kurz = {k: ergebnis.get(k) for k in ('bestanden', 'kriterien', 'stoerung', 'kollision',
                                         'minimaler_abstand_m', 'fehler')}
    kurz['endzustand'] = zusammenfassung.get('endzustand')
    kurz['dauer_s'] = zusammenfassung.get('dauer_s')
    print(json.dumps(kurz, ensure_ascii=False, indent=2), flush=True)
    return 0 if ergebnis['bestanden'] else 1


if __name__ == '__main__':
    sys.exit(main())
