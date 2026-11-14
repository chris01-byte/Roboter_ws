#!/usr/bin/env python3
"""SLAM-Prüfstand: eine aufgezeichnete Fahrt nur in slam_toolbox abspielen und messen.

Arbeitspaket SL-1 (STATUS 02.11.2026). In geschlossenen Simulationsläufen fährt
der Roboter jedes Mal anders; hier bekommt slam_toolbox bei jedem Lauf exakt
dieselben Eingangsdaten, sodass ein einzelner Parameter verglichen werden kann.

Abgespielt werden aus einer rosbag2-Aufnahme (``sh_robustheit.py``-Lauf)
``/scan_normiert``, ``/tf`` ohne ``map``->``odom`` (das stammt vom damaligen
SLAM) und ``/tf_static``, in Echtzeit und mit Zeitstempeln, die um einen festen
Versatz auf jetzt verschoben sind. slam_toolbox läuft mit dem Produktprofil
(``slam_toolbox_amadeus.yaml`` + ``slam_toolbox_self_healing.yaml``) und
optional einer Experimentdatei darüber.

Gemessen:
- CPU von slam_toolbox je 10 s in % eines Kerns (/proc);
- Alter des neuesten ``map``->``odom`` mit 20 Hz (RPP wartet 0,2 s, dann
  bricht er mit "extrapolation into the future" ab);
- verworfene Scans ("queue is full") und Ringschlüsse (Ceres) aus dem Log;
- Endkarte gegen die Welt der Aufnahme (Kriterien wie Manifest v4).

Aufruf::

  python3 tools/simulation/slam_pruefstand.py --aufnahme BAG --lauf SIMLAUF \\
      --ausgabe /pfad [--experiment kandidat.yaml]

Nur Messwerkzeug; keine Abnahme des Produkts.
"""

import argparse
import json
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

ABSPIEL_THEMEN = ('/scan_normiert', '/tf', '/tf_static')
ALTER_GRENZE_S = 0.25


# ---------------------------------------------------------------------------
#  Reine Funktionen (ohne ROS testbar)
# ---------------------------------------------------------------------------

def slam_parameter(repo, experiment=None):
    """Produktprofil von slam_toolbox im Selbstheilungsbetrieb, optional mit Experiment."""
    from sh_robustheit import tief_mischen

    def lade(relativ):
        return yaml.safe_load((repo/relativ).read_text(encoding='utf-8'))['slam_toolbox']
    p = lade('src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml')
    tief_mischen(p, lade('src/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml'))
    p['ros__parameters']['scan_topic'] = '/scan_normiert'
    if experiment:
        tief_mischen(p, experiment.get('slam_toolbox', {}))
    return {'slam_toolbox': p}


def verschiebe(stamp, versatz_ns):
    """Header-Zeitstempel um einen festen Versatz verschieben (in place)."""
    ns = stamp.sec*1_000_000_000 + stamp.nanosec + versatz_ns
    stamp.sec, stamp.nanosec = divmod(ns, 1_000_000_000)


def ohne_map_odom(tf_message):
    """``map``->``odom`` des aufgezeichneten SLAM entfernen; True, wenn noch etwas übrig ist."""
    tf_message.transforms = [t for t in tf_message.transforms
                             if t.header.frame_id.lstrip('/') != 'map']
    return bool(tf_message.transforms)


def cpu_zusammenfassung(reihe, letzte_s=120.):
    """``reihe``: Liste ``(s seit Start, % eines Kerns)``."""
    if not reihe:
        return None
    ende = reihe[-1][0]
    letzte = [w for t, w in reihe if t >= ende - letzte_s]
    return {'proben': len(reihe), 'erste': reihe[0][1], 'max': max(w for _, w in reihe),
            'mittel_letzte_2min': round(float(np.mean(letzte)), 1),
            'reihe': [[round(t), round(w, 1)] for t, w in reihe]}


def alter_zusammenfassung(alter_s, grenze_s=ALTER_GRENZE_S):
    if not alter_s:
        return None
    a = np.asarray(alter_s, dtype=float)
    return {'proben': int(a.size), 'grenze_s': grenze_s,
            'anteil_ueber_grenze': round(float(np.mean(a > grenze_s)), 4),
            'p50_s': round(float(np.percentile(a, 50)), 3),
            'p95_s': round(float(np.percentile(a, 95)), 3),
            'p99_s': round(float(np.percentile(a, 99)), 3),
            'max_s': round(float(a.max()), 3)}


def log_zaehlung(text):
    return {'verworfene_scans': text.count('queue is full'),
            'ringschluss_ceres': text.count('preprocessor.cc')}


# ---------------------------------------------------------------------------
#  ROS-Teil
# ---------------------------------------------------------------------------

def cpu_ticks(pid):
    teile = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return int(teile[11]) + int(teile[12])       # utime + stime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--aufnahme', type=Path, required=True, help='rosbag2-Ordner (mcap)')
    parser.add_argument('--lauf', type=Path, required=True,
                        help='Ordner des aufgezeichneten sh_robustheit-Laufs (Welt aus manifest.json)')
    parser.add_argument('--ausgabe', type=Path, required=True)
    parser.add_argument('--experiment', type=Path, default=None)
    parser.add_argument('--domain', type=int, default=132)
    parser.add_argument('--max-s', type=float, default=0.,
                        help='> 0: nur die ersten Sekunden abspielen (Rauchtest)')
    args = parser.parse_args(argv)
    out = args.ausgabe
    out.mkdir(parents=True, exist_ok=False)
    os.environ['ROS_DOMAIN_ID'] = str(args.domain)
    os.environ['ROS_LOCALHOST_ONLY'] = '1'
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'
    os.environ.pop('CYCLONEDDS_URI', None)

    experiment = (yaml.safe_load(args.experiment.read_text(encoding='utf-8'))
                  if args.experiment else None)
    params = slam_parameter(REPO, experiment)
    (out/'slam_params.yaml').write_text(yaml.safe_dump(params, sort_keys=False), encoding='utf-8')

    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from rclpy.serialization import deserialize_message
    from ament_index_python.packages import get_package_prefix
    from lifecycle_msgs.srv import ChangeState
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import LaserScan
    from tf2_msgs.msg import TFMessage
    import rosbag2_py
    from sh_robustheit_welt import RobustheitsWelt

    rclpy.init()
    knoten = rclpy.create_node('slam_pruefstand')
    statisch = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                          reliability=ReliabilityPolicy.RELIABLE)
    pub = {'/scan_normiert': knoten.create_publisher(LaserScan, '/scan_normiert', 10),
           '/tf': knoten.create_publisher(TFMessage, '/tf', 100),
           '/tf_static': knoten.create_publisher(TFMessage, '/tf_static', statisch)}
    zustand = {'map_odom_ns': None, 'karte': None, 'map_odom_n': 0}

    def auf_tf(msg):
        for t in msg.transforms:
            if t.header.frame_id.lstrip('/') == 'map':
                ns = t.header.stamp.sec*1_000_000_000 + t.header.stamp.nanosec
                if zustand['map_odom_ns'] is None or ns > zustand['map_odom_ns']:
                    zustand['map_odom_ns'] = ns
                    zustand['map_odom_n'] += 1

    knoten.create_subscription(TFMessage, '/tf', auf_tf, 100)
    knoten.create_subscription(OccupancyGrid, '/map', lambda m: zustand.__setitem__('karte', m), statisch)
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(knoten)
    threading.Thread(target=executor.spin, daemon=True).start()

    exe = str(Path(get_package_prefix('slam_toolbox'))/'lib/slam_toolbox/async_slam_toolbox_node')
    log = (out/'slam_toolbox.log').open('w')
    slam = subprocess.Popen([exe, '--ros-args', '--params-file', str(out/'slam_params.yaml')],
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    ergebnis = {'aufnahme': str(args.aufnahme.name), 'lauf': str(args.lauf.name),
                'experiment': None if experiment is None else
                {'datei': args.experiment.name, 'parameter': experiment},
                'fehler': None}
    cpu, alter, alter_t = [], [], []
    fertig = threading.Event()
    try:
        # Jazzy: slam_toolbox ist ein Lifecycle-Knoten (configure, activate).
        for uebergang in (1, 3):
            client = knoten.create_client(ChangeState, '/slam_toolbox/change_state')
            if not client.wait_for_service(timeout_sec=20.):
                raise TimeoutError('slam_toolbox/change_state')
            req = ChangeState.Request()
            req.transition.id = uebergang
            fut = client.call_async(req)
            ende = time.monotonic() + 20.
            while not fut.done() and time.monotonic() < ende:
                time.sleep(.02)
            if not fut.done() or not fut.result().success:
                raise RuntimeError(f'slam_toolbox: Übergang {uebergang} abgelehnt')

        hz = os.sysconf('SC_CLK_TCK')
        start_mono = time.monotonic()

        def messe_cpu():
            vorher, t_vorher = cpu_ticks(slam.pid), time.monotonic()
            while not fertig.wait(10.):
                try:
                    jetzt, t_jetzt = cpu_ticks(slam.pid), time.monotonic()
                except (FileNotFoundError, ProcessLookupError):
                    return
                cpu.append((t_jetzt - start_mono, 100.*(jetzt - vorher)/hz/(t_jetzt - t_vorher)))
                vorher, t_vorher = jetzt, t_jetzt

        def messe_alter():
            while not fertig.wait(.05):
                ns = zustand['map_odom_ns']
                if ns is not None:
                    alter.append(time.time() - ns/1e9)
                    alter_t.append(time.monotonic() - start_mono)

        threading.Thread(target=messe_cpu, daemon=True).start()
        threading.Thread(target=messe_alter, daemon=True).start()

        reader = rosbag2_py.SequentialReader()
        reader.open(rosbag2_py.StorageOptions(uri=str(args.aufnahme), storage_id='mcap'),
                    rosbag2_py.ConverterOptions('', ''))
        typen = {'/scan_normiert': LaserScan, '/tf': TFMessage, '/tf_static': TFMessage}
        reader.set_filter(rosbag2_py.StorageFilter(topics=list(ABSPIEL_THEMEN)))
        t0_bag = versatz = start_wall = None
        zaehler = {t: 0 for t in ABSPIEL_THEMEN}
        while reader.has_next():
            thema, daten, t_ns = reader.read_next()
            if args.max_s > 0 and t0_bag is not None and (t_ns - t0_bag)/1e9 > args.max_s:
                break
            msg = deserialize_message(daten, typen[thema])
            if t0_bag is None:
                t0_bag, start_wall = t_ns, time.time_ns()
                versatz = start_wall - t0_bag
            if thema in ('/tf', '/tf_static'):
                if thema == '/tf' and not ohne_map_odom(msg):
                    continue
                for t in msg.transforms:
                    verschiebe(t.header.stamp, versatz)
            else:
                verschiebe(msg.header.stamp, versatz)
            warten = (start_wall + (t_ns - t0_bag) - time.time_ns())/1e9
            if warten > 0:
                time.sleep(warten)
            pub[thema].publish(msg)
            zaehler[thema] += 1
        ergebnis['abgespielt'] = zaehler
        ergebnis['dauer_s'] = round(time.monotonic() - start_mono, 1)
        # Messung endet mit den Daten: danach wächst das Alter von map->odom nur,
        # weil nichts mehr kommt (früher 5 s Artefakt in jeder Altersstatistik).
        fertig.set()
        time.sleep(5.)                       # letzte Kartenaktualisierung abwarten
    except Exception as fehler:  # noqa: BLE001 - als Befund festhalten
        ergebnis['fehler'] = f'{type(fehler).__name__}: {fehler}'
    finally:
        fertig.set()
        if slam.poll() is None:
            slam.send_signal(signal.SIGINT)   # nur dieser Prozess, nie die Gruppe
            try:
                slam.wait(timeout=15.)
            except subprocess.TimeoutExpired:
                slam.terminate()
        log.close()

    ergebnis['slam_beendet_code'] = slam.returncode
    ergebnis['cpu_prozent_kern'] = cpu_zusammenfassung(cpu)
    ergebnis['map_odom_alter'] = alter_zusammenfassung(alter)
    ergebnis['map_odom_aktualisierungen'] = zustand['map_odom_n']
    np.savez_compressed(out/'map_odom_alter.npz', t_s=np.asarray(alter_t[:len(alter)]),
                        alter_s=np.asarray(alter[:len(alter_t)]))
    ergebnis.update(log_zaehlung((out/'slam_toolbox.log').read_text(errors='ignore')))
    karte = zustand['karte']
    if karte is not None:
        manifest = json.loads((args.lauf/'manifest.json').read_text(encoding='utf-8'))
        welt_def = manifest['welt']
        welt = RobustheitsWelt(welt_def['door_m'], welt_def['start'],
                               welt_def.get('zusatz_hindernisse', ()))
        belegung = np.asarray(karte.data, dtype=np.int16).reshape(karte.info.height, karte.info.width)
        ursprung = (karte.info.origin.position.x, karte.info.origin.position.y)
        ergebnis['karte'] = welt.map_oracle(belegung, karte.info.resolution, ursprung)
        ergebnis['abdeckung_erreichbar'] = welt.abdeckung_erreichbar(
            belegung, karte.info.resolution, ursprung)
        ergebnis['kartenfehler_orte'] = welt.kartenfehler_orte(
            belegung, karte.info.resolution, ursprung)
        np.savez_compressed(out/'endkarte.npz', belegung=belegung.astype(np.int8),
                            aufloesung=karte.info.resolution, ursprung=list(ursprung))
    (out/'ergebnis.json').write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1),
                                     encoding='utf-8')
    knoten.destroy_node()
    rclpy.try_shutdown()
    print(json.dumps({k: ergebnis.get(k) for k in (
        'fehler', 'dauer_s', 'verworfene_scans', 'ringschluss_ceres')}, ensure_ascii=False))
    print('CPU', {k: v for k, v in (ergebnis['cpu_prozent_kern'] or {}).items() if k != 'reihe'})
    print('ALTER', ergebnis['map_odom_alter'])
    print('KARTE', ergebnis.get('karte'), ergebnis.get('abdeckung_erreichbar'))
    return 0 if ergebnis['fehler'] is None else 1


if __name__ == '__main__':
    sys.exit(main())
