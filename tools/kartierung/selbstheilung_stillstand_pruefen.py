#!/usr/bin/env python3
"""Rein lesende Stillstandspruefung fuer ``self_healing:=true``.

Konzept: docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md (Abschnitt 10/11),
Laborrahmen: docs/LABORMODUS.md (LAB-1 Abschnitt 3).

Voraussetzung: der Stack laeuft bereits motorlos, zum Beispiel

    ros2 launch robot_navigation nav_mapping.launch.py self_healing:=true

(``active_drive`` bleibt false, ``enable_auto_explore`` bleibt false).

Das Skript publiziert nichts, sendet keine Aktion und ruft keinen Dienst
mit Wirkung auf. Es liest nur Parameter (GetParameters/ListParameters),
den ROS-Graphen, ``/cmd_vel`` und optional die VL53-Punktwolken.

Geprueft wird:
  A  Explorer-Profil: jeder Wert aus self_healing_params.yaml ist live
     gesetzt, der Explorer verwendet den Baum mit leichter Recovery.
  B  Overlays: jeder Wert aus nav2_params_self_healing.yaml (Planer,
     Glaetter, Behavior-Server, beide Kostenkarten) und aus
     collision_monitor_self_healing_overlay.yaml ist live
     gesetzt (Planung durch Unbekanntes, -0,05 m/s, simulate_ahead_time).
  C  Verdrahtung: BackUp geht ueber cmd_vel_nav_raw (Fahrtor -> Smoother
     -> collision_monitor), RPP hoert auf das Geschwindigkeitslimit.
  D  Stillstand: base_hardware im Dry-Run ohne RS485-Schreibpfad, auf
     /cmd_vel kein Fahrbefehl ungleich null.
  E  (optional, --vl53-s) Niedrige Hindernisse: wie hoch ueber dem Boden
     liegen die VL53-Treffer, und welche davon verwerfen Kostenkarten und
     collision_monitor wegen min_obstacle_height/min_height?

Exitcode 0 = alle Pflichtpruefungen erfuellt, 1 = mindestens eine nicht
erfuellt, 2 = Explorer nicht erreichbar (Stack laeuft nicht).
"""

import argparse
import json
import math
import sys
import time

import numpy as np


NOT_SET = object()

# Hoehe von base_link ueber dem Boden. Quelle: URDF base_height 0,18 m
# (base_link in der Mitte) und Kommentar in nav2_params_real.yaml
# ("z=0 = base_link = 9 cm ueber Boden").
BASE_LINK_UEBER_BODEN_M = 0.09

SELF_HEALING_BT = 'navigate_to_pose_self_healing.xml'
STEUERPFAD_ROH = '/cmd_vel_nav_raw'
RECOVERY_GESPERRT = '/cmd_vel_recovery_blocked'


# ---------------------------------------------------------------------------
#  Reine Funktionen (ohne ROS testbar)
# ---------------------------------------------------------------------------

def flatten_ros_params(document):
    """``{'/knoten': {'a.b': wert}}`` aus einer ROS-2-Parameterdatei."""
    result = {}

    def walk(tree, path):
        if not isinstance(tree, dict):
            return
        if 'ros__parameters' in tree:
            node = '/' + '/'.join(path)
            params = result.setdefault(node, {})
            _flatten_values(tree['ros__parameters'], '', params)
        for key, value in tree.items():
            if key != 'ros__parameters':
                walk(value, path + [str(key)])

    walk(document or {}, [])
    return result


def _flatten_values(tree, prefix, out):
    for key, value in tree.items():
        name = f'{prefix}{key}'
        if isinstance(value, dict):
            _flatten_values(value, name + '.', out)
        else:
            out[name] = value


def values_match(expected, live, tol=1e-6):
    if live is NOT_SET:
        return False
    if isinstance(expected, bool) or isinstance(live, bool):
        return isinstance(expected, bool) and isinstance(live, bool) and expected == live
    if isinstance(expected, (int, float)) and isinstance(live, (int, float)):
        return math.isclose(float(expected), float(live), rel_tol=0.0, abs_tol=tol)
    if isinstance(expected, (list, tuple)) and isinstance(live, (list, tuple)):
        return (len(expected) == len(live)
                and all(values_match(e, v, tol) for e, v in zip(expected, live)))
    return expected == live


def compare_params(expected, live):
    """Liste ``(name, erwartet, live, ok)`` fuer jeden erwarteten Wert."""
    rows = []
    for name in sorted(expected):
        value = live.get(name, NOT_SET)
        rows.append((name, expected[name], value, values_match(expected[name], value)))
    return rows


def normalize_topic(name):
    name = str(name or '').strip()
    return name if name.startswith('/') else '/' + name


def full_node_name(namespace, name):
    namespace = (namespace or '/').rstrip('/')
    return f'{namespace}/{name}'


def quaternion_matrix(x, y, z, w):
    n = math.sqrt(x*x + y*y + z*z + w*w)
    if n == 0.0:
        raise ValueError('Quaternion der Laenge null')
    x, y, z, w = x/n, y/n, z/n, w/n
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
        [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)],
    ])


def transform_points(points, translation, rotation_xyzw):
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    return points @ quaternion_matrix(*rotation_xyzw).T + np.asarray(translation, dtype=float)


def near_field_filters(params):
    """Hoehenfilter aller Quellen, deren Topic ``near_field`` enthaelt.

    ``params`` ist die flache Parameterliste eines Kostenkarten- oder
    collision_monitor-Knotens. Rueckgabe ``{quelle: {topic, min, max, marking}}``.
    Kostenkarten heissen ``min_obstacle_height``, der collision_monitor
    ``min_height``; reine Raeumquellen (marking=false) markieren nie.
    """
    sources = {}
    for name, value in params.items():
        if not name.endswith('.topic') or 'near_field' not in str(value):
            continue
        base = name[:-len('.topic')]
        low = params.get(f'{base}.min_obstacle_height', params.get(f'{base}.min_height'))
        high = params.get(f'{base}.max_obstacle_height', params.get(f'{base}.max_height'))
        sources[base] = {
            'topic': normalize_topic(value),
            'min': None if low is None else float(low),
            'max': None if high is None else float(high),
            'marking': bool(params.get(f'{base}.marking', True)),
        }
    return sources


def height_report(points_base_link, sensor_points, min_height, base_link_above_floor,
                  row_elevations_rad=None):
    """Hoehenauswertung von VL53-Treffern gegen den wirksamen Hoehenfilter.

    ``min_height`` ist im base_link-Rahmen angegeben wie in den Parametern.
    Hoehen im Bericht sind ueber dem Boden, damit Testobjekte direkt
    vergleichbar sind.
    """
    pts = np.asarray(points_base_link, dtype=float).reshape(-1, 3)
    floor = pts[:, 2] + base_link_above_floor
    threshold_floor = min_height + base_link_above_floor
    dropped = floor < threshold_floor
    report = {
        'punkte': int(len(pts)),
        'filter_ueber_boden_m': round(threshold_floor, 3),
        'verworfen': int(np.count_nonzero(dropped)),
        'behalten': int(np.count_nonzero(~dropped)),
        # Feste Baender, unabhaengig vom Filter, damit Messreihen mit
        # verschiedenen Grenzen vergleichbar bleiben (0,14 m = bisherige Grenze).
        'baender_ueber_boden': {
            '<0,05 m': int(np.count_nonzero(floor < 0.05)),
            '0,05-0,10 m': int(np.count_nonzero((floor >= 0.05) & (floor < 0.10))),
            '0,10-0,14 m': int(np.count_nonzero((floor >= 0.10) & (floor < 0.14))),
            '>=0,14 m': int(np.count_nonzero(floor >= 0.14)),
        },
    }
    if len(pts):
        report['hoehe_ueber_boden_min_m'] = round(float(floor.min()), 3)
        report['hoehe_ueber_boden_max_m'] = round(float(floor.max()), 3)
    if np.any(dropped):
        report['naechster_verworfener_x_base_link_m'] = round(float(pts[dropped, 0].min()), 3)
    if np.any(~dropped):
        report['naechster_behaltener_x_base_link_m'] = round(float(pts[~dropped, 0].min()), 3)
    if row_elevations_rad is not None and len(pts):
        sensor = np.asarray(sensor_points, dtype=float).reshape(-1, 3)
        elevation = np.arctan2(sensor[:, 2], np.hypot(sensor[:, 0], sensor[:, 1]))
        rows = np.asarray(row_elevations_rad, dtype=float)
        nearest_row = np.argmin(np.abs(elevation[:, None] - rows[None, :]), axis=1)
        report['zeilen'] = []
        for row, angle in enumerate(rows):
            mask = nearest_row == row
            if not np.any(mask):
                continue
            report['zeilen'].append({
                'zeile': row,
                'elevation_grad': round(math.degrees(angle), 2),
                'treffer': int(np.count_nonzero(mask)),
                'median_abstand_m': round(float(np.median(np.linalg.norm(sensor[mask], axis=1))), 3),
                'median_hoehe_ueber_boden_m': round(float(np.median(floor[mask])), 3),
                'verworfen': int(np.count_nonzero(dropped & mask)),
            })
    return report


def row_elevations(fov_deg, rows=8):
    """Zeilenmitten wie im vl53_near_field-Knoten (Konvention z oben +)."""
    return np.radians([(-fov_deg/2.0 + (r + 0.5)/rows*fov_deg) for r in range(rows)])


class Ergebnis:
    def __init__(self):
        self.zeilen = []

    def add(self, bereich, name, ok, detail=''):
        """``ok``: True erfuellt, False nicht erfuellt, None nur Hinweis."""
        self.zeilen.append({'bereich': bereich, 'pruefung': name, 'ok': ok, 'detail': detail})

    @property
    def bestanden(self):
        return all(z['ok'] is not False for z in self.zeilen)

    def drucken(self, stream=sys.stdout):
        marke = {True: 'OK  ', False: 'FEHL', None: 'INFO'}
        for z in self.zeilen:
            detail = f' - {z["detail"]}' if z['detail'] else ''
            print(f'[{marke[z["ok"]]}] {z["bereich"]}: {z["pruefung"]}{detail}', file=stream)


# ---------------------------------------------------------------------------
#  ROS-Teil (nur lesend)
# ---------------------------------------------------------------------------

def _param_to_python(value):
    from rcl_interfaces.msg import ParameterType as T
    kind = value.type
    if kind == T.PARAMETER_BOOL:
        return bool(value.bool_value)
    if kind == T.PARAMETER_INTEGER:
        return int(value.integer_value)
    if kind == T.PARAMETER_DOUBLE:
        return float(value.double_value)
    if kind == T.PARAMETER_STRING:
        return str(value.string_value)
    if kind == T.PARAMETER_BYTE_ARRAY:
        return list(value.byte_array_value)
    if kind == T.PARAMETER_BOOL_ARRAY:
        return [bool(v) for v in value.bool_array_value]
    if kind == T.PARAMETER_INTEGER_ARRAY:
        return [int(v) for v in value.integer_array_value]
    if kind == T.PARAMETER_DOUBLE_ARRAY:
        return [float(v) for v in value.double_array_value]
    if kind == T.PARAMETER_STRING_ARRAY:
        return [str(v) for v in value.string_array_value]
    return NOT_SET


class Leser:
    """Passiver Knoten: keine Publisher, keine Aktionen, keine Schreibdienste."""

    def __init__(self, timeout_s):
        import rclpy
        self.rclpy = rclpy
        self.node = rclpy.create_node('selbstheilung_stillstand_pruefer')
        self.timeout_s = timeout_s

    def spin_for(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.rclpy.spin_once(self.node, timeout_sec=0.05)

    def _call(self, srv_type, name, request):
        client = self.node.create_client(srv_type, name)
        try:
            if not client.wait_for_service(timeout_sec=self.timeout_s):
                return None
            future = client.call_async(request)
            self.rclpy.spin_until_future_complete(self.node, future, timeout_sec=self.timeout_s)
            return future.result() if future.done() else None
        finally:
            self.node.destroy_client(client)

    def get_params(self, node, names):
        """``{name: wert}`` oder ``None``, wenn der Knoten nicht antwortet."""
        from rcl_interfaces.srv import GetParameters
        names = list(names)
        if not names:
            return {}
        request = GetParameters.Request()
        request.names = names
        response = self._call(GetParameters, f'{node}/get_parameters', request)
        if response is None:
            return None
        return {n: _param_to_python(v) for n, v in zip(names, response.values)}

    def all_params(self, node):
        from rcl_interfaces.srv import ListParameters
        request = ListParameters.Request()
        request.depth = 0  # rekursiv
        response = self._call(ListParameters, f'{node}/list_parameters', request)
        if response is None:
            return None
        return self.get_params(node, response.result.names)

    def publishers(self, topic):
        return {full_node_name(i.node_namespace, i.node_name)
                for i in self.node.get_publishers_info_by_topic(topic)}

    def subscribers(self, topic):
        return {full_node_name(i.node_namespace, i.node_name)
                for i in self.node.get_subscriptions_info_by_topic(topic)}

    def action_servers(self, node_name, namespace='/'):
        from rclpy.action import get_action_server_names_and_types_by_node
        return {name for name, _ in get_action_server_names_and_types_by_node(
            self.node, node_name, namespace)}

    def close(self):
        self.node.destroy_node()


def _load_yaml(path):
    import yaml
    with open(path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)


def _share(package, *parts):
    import os
    from ament_index_python.packages import get_package_share_directory
    return os.path.join(get_package_share_directory(package), *parts)


def pruefe_profile(leser, ergebnis, explore_profil, overlays):
    explore_expected = flatten_ros_params(_load_yaml(explore_profil)).get('/explore_node', {})
    live = leser.get_params('/explore_node', list(explore_expected) + [
        'behavior_tree', 'self_healing_speed_limit_topic'])
    if live is None:
        ergebnis.add('A Explorer', '/explore_node erreichbar', False,
                     'keine Parameterantwort; Stack mit self_healing:=true starten')
        return None
    falsch = [(n, e, v) for n, e, v, ok in compare_params(explore_expected, live) if not ok]
    ergebnis.add('A Explorer', f'{len(explore_expected)} Profilwerte live gesetzt', not falsch,
                 '; '.join(f'{n}: erwartet {e!r}, live '
                           f'{"nicht deklariert" if v is NOT_SET else repr(v)}'
                           for n, e, v in falsch[:6]))
    tree = live.get('behavior_tree')
    ergebnis.add('A Explorer', 'Nav2-Baum mit leichter Recovery',
                 isinstance(tree, str) and tree.endswith(SELF_HEALING_BT), repr(tree))

    for bereich, overlay in overlays:
        for node, expected in sorted(flatten_ros_params(_load_yaml(overlay)).items()):
            values = leser.get_params(node, expected)
            if values is None:
                ergebnis.add(bereich, f'{node} erreichbar', False, 'keine Parameterantwort')
                continue
            for name, e, v, ok in compare_params(expected, values):
                ergebnis.add(bereich, f'{node} {name}', ok,
                             f'erwartet {e!r}, live '
                             f'{"nicht deklariert" if v is NOT_SET else repr(v)}')
    return live


def pruefe_verdrahtung(leser, ergebnis, explore_live):
    raw_pubs = leser.publishers(STEUERPFAD_ROH)
    for node in ('/controller_server', '/behavior_server'):
        ergebnis.add('C Verdrahtung', f'{node} publiziert auf {STEUERPFAD_ROH}',
                     node in raw_pubs, ', '.join(sorted(raw_pubs)) or 'keine Publisher')
    raw_subs = leser.subscribers(STEUERPFAD_ROH)
    ergebnis.add('C Verdrahtung', f'Fahrtor liest {STEUERPFAD_ROH}',
                 '/cmd_vel_mission_gate' in raw_subs, ', '.join(sorted(raw_subs)) or 'keine Leser')
    blocked = leser.publishers(RECOVERY_GESPERRT)
    ergebnis.add('C Verdrahtung', f'behavior_server nicht mehr auf {RECOVERY_GESPERRT}',
                 '/behavior_server' not in blocked, ', '.join(sorted(blocked)) or 'leer')
    actions = leser.action_servers('behavior_server')
    ergebnis.add('C Verdrahtung', 'BackUp-Aktion /backup angeboten', '/backup' in actions,
                 ', '.join(sorted(actions)) or 'keine Aktionsserver')

    topic = normalize_topic((explore_live or {}).get('self_healing_speed_limit_topic', '/speed_limit'))
    controller = leser.get_params('/controller_server', ['speed_limit_topic'])
    configured = None if controller is None else controller.get('speed_limit_topic')
    ergebnis.add('C Verdrahtung', 'controller_server speed_limit_topic passt zum Explorer',
                 configured is not NOT_SET and configured is not None
                 and normalize_topic(configured) == topic,
                 f'Explorer {topic}, Controller '
                 f'{"nicht deklariert" if configured is NOT_SET else repr(configured)}')
    subs = leser.subscribers(topic)
    ergebnis.add('C Verdrahtung', f'controller_server abonniert {topic}',
                 '/controller_server' in subs, ', '.join(sorted(subs)) or 'keine Leser')
    pubs = leser.publishers(topic)
    ergebnis.add('C Verdrahtung', f'Publisher auf {topic}', None,
                 (', '.join(sorted(pubs)) or 'keine') +
                 ' (der Explorer publiziert erst waehrend einer Mission)')
    cmd_pubs = leser.publishers('/cmd_vel')
    andere = sorted(cmd_pubs - {'/collision_monitor'})
    ergebnis.add('C Verdrahtung', '/cmd_vel kommt vom collision_monitor',
                 '/collision_monitor' in cmd_pubs,
                 ', '.join(sorted(cmd_pubs)) or 'keine Publisher')
    if andere:
        ergebnis.add('C Verdrahtung', 'weitere /cmd_vel-Publisher', None, ', '.join(andere))


def pruefe_stillstand(leser, ergebnis, beobachten_s):
    base = leser.get_params('/base_hardware', ['dry_run', 'allow_rs485'])
    if base is None:
        ergebnis.add('D Stillstand', '/base_hardware erreichbar', False, 'keine Parameterantwort')
    else:
        ergebnis.add('D Stillstand', 'base_hardware im Dry-Run', base.get('dry_run') is True,
                     f'dry_run={base.get("dry_run")!r}')
        ergebnis.add('D Stillstand', 'kein RS485-Schreibpfad', base.get('allow_rs485') is False,
                     f'allow_rs485={base.get("allow_rs485")!r}')
    from geometry_msgs.msg import Twist
    seen = {'n': 0, 'max_lin': 0.0, 'max_ang': 0.0}

    def on_twist(msg):
        seen['n'] += 1
        seen['max_lin'] = max(seen['max_lin'], abs(msg.linear.x), abs(msg.linear.y))
        seen['max_ang'] = max(seen['max_ang'], abs(msg.angular.z))

    sub = leser.node.create_subscription(Twist, '/cmd_vel', on_twist, 10)
    leser.spin_for(beobachten_s)
    leser.node.destroy_subscription(sub)
    ergebnis.add('D Stillstand', f'/cmd_vel {beobachten_s:.0f} s ohne Fahrbefehl',
                 seen['max_lin'] == 0.0 and seen['max_ang'] == 0.0,
                 f'{seen["n"]} Nachrichten, max |v|={seen["max_lin"]:.3f} m/s, '
                 f'max |w|={seen["max_ang"]:.3f} rad/s')


def pruefe_vl53(leser, ergebnis, sekunden, base_link_above_floor):
    from rclpy.qos import qos_profile_sensor_data
    from rclpy.time import Time
    from sensor_msgs.msg import PointCloud2
    from sensor_msgs_py.point_cloud2 import read_points
    from tf2_ros import Buffer, TransformListener

    filters = {}
    for node in ('/collision_monitor', '/local_costmap/local_costmap',
                 '/global_costmap/global_costmap'):
        params = leser.all_params(node)
        if params is None:
            ergebnis.add('E VL53', f'{node} erreichbar', None, 'keine Parameterantwort')
            continue
        for source, info in near_field_filters(params).items():
            filters[f'{node} {source}'] = info
    marking = {k: v for k, v in filters.items() if v['marking'] and v['min'] is not None}
    for key, info in sorted(filters.items()):
        ergebnis.add('E VL53', f'Filter {key}', None,
                     f'{info["topic"]} min={info["min"]} max={info["max"]} '
                     f'marking={info["marking"]}')
    if not marking:
        ergebnis.add('E VL53', 'Hoehenfilter gefunden', False, 'keine markierende near_field-Quelle')
        return {}
    min_height = max(info['min'] for info in marking.values())

    vl53 = leser.get_params('/vl53_near_field', ['fov_deg', 'z_max'])
    fov = (vl53 or {}).get('fov_deg', 60.0)
    if fov is NOT_SET:
        fov = 60.0
    rows = row_elevations(fov)

    tf_buffer = Buffer()
    TransformListener(tf_buffer, leser.node)
    clouds = {'left': [], 'right': []}

    def collect(side):
        def callback(msg):
            pts = [(float(p[0]), float(p[1]), float(p[2]))
                   for p in read_points(msg, field_names=('x', 'y', 'z'), skip_nans=True)]
            clouds[side].append((msg.header.frame_id, np.array(pts, dtype=float).reshape(-1, 3)))
        return callback

    subs = [leser.node.create_subscription(
                PointCloud2, f'/near_field/{side}/points', collect(side), qos_profile_sensor_data)
            for side in clouds]
    leser.spin_for(sekunden)
    for sub in subs:
        leser.node.destroy_subscription(sub)

    berichte = {}
    for side, frames in clouds.items():
        if not frames:
            ergebnis.add('E VL53', f'{side}: Punktwolken empfangen', False, 'keine Nachricht')
            continue
        frame_id = frames[0][0]
        try:
            tf = tf_buffer.lookup_transform('base_link', frame_id, Time())
        except Exception as error:  # noqa: BLE001 - Diagnose ausgeben
            ergebnis.add('E VL53', f'{side}: TF {frame_id} -> base_link', False, str(error))
            continue
        t, q = tf.transform.translation, tf.transform.rotation
        sensor = np.vstack([pts for _, pts in frames]) if frames else np.zeros((0, 3))
        base = transform_points(sensor, (t.x, t.y, t.z), (q.x, q.y, q.z, q.w))
        report = height_report(base, sensor, min_height, base_link_above_floor, rows)
        report['frames'] = len(frames)
        report['sensor_ueber_boden_m'] = round(t.z + base_link_above_floor, 3)
        berichte[side] = report
        ergebnis.add('E VL53', f'{side}: {len(frames)} Frames, {report["punkte"]} Treffer', None,
                     f'{report["verworfen"]} unter dem Filter '
                     f'({report["filter_ueber_boden_m"]:.2f} m ueber Boden), '
                     f'Baender {report["baender_ueber_boden"]}')
    return berichte


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--explore-profil', help='Default: installiertes self_healing_params.yaml')
    parser.add_argument('--nav-overlay', help='Default: installiertes nav2_params_self_healing.yaml')
    parser.add_argument('--collision-overlay',
                        help='Default: installiertes collision_monitor_self_healing_overlay.yaml')
    parser.add_argument('--timeout-s', type=float, default=3.0)
    parser.add_argument('--entdeckung-s', type=float, default=2.0,
                        help='Wartezeit fuer die DDS-Entdeckung vor den Graphabfragen')
    parser.add_argument('--beobachten-s', type=float, default=3.0,
                        help='So lange wird /cmd_vel beobachtet')
    parser.add_argument('--vl53-s', type=float, default=0.0,
                        help='> 0: VL53-Hoehenmessung ueber diese Dauer (Testobjekt vor dem Roboter)')
    parser.add_argument('--base-link-ueber-boden', type=float, default=BASE_LINK_UEBER_BODEN_M)
    parser.add_argument('--notiz', default='', help='z. B. "Klotz 5 cm, 0,35 m mittig"')
    parser.add_argument('--json', help='Ergebnis zusaetzlich als JSON (lokal, nicht ins Repo)')
    args = parser.parse_args(argv)

    explore_profil = args.explore_profil or _share('explore', 'config', 'self_healing_params.yaml')
    nav_overlay = args.nav_overlay or _share(
        'robot_navigation', 'config', 'nav2_params_self_healing.yaml')
    collision_overlay = args.collision_overlay or _share(
        'vl53_near_field', 'config', 'collision_monitor_self_healing_overlay.yaml')
    overlays = (('B Nav2-Overlay', nav_overlay), ('B Kollisionswaechter', collision_overlay))

    import rclpy
    rclpy.init()
    leser = Leser(args.timeout_s)
    ergebnis = Ergebnis()
    vl53 = {}
    try:
        leser.spin_for(args.entdeckung_s)
        explore_live = pruefe_profile(leser, ergebnis, explore_profil, overlays)
        if explore_live is None:
            ergebnis.drucken()
            return 2
        pruefe_verdrahtung(leser, ergebnis, explore_live)
        pruefe_stillstand(leser, ergebnis, args.beobachten_s)
        if args.vl53_s > 0:
            vl53 = pruefe_vl53(leser, ergebnis, args.vl53_s, args.base_link_ueber_boden)
    finally:
        leser.close()
        rclpy.try_shutdown()

    ergebnis.drucken()
    if vl53:
        print(json.dumps({'notiz': args.notiz, 'vl53': vl53}, ensure_ascii=False, indent=2))
    print('ERGEBNIS:', 'bestanden' if ergebnis.bestanden else 'NICHT bestanden')
    if args.json:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump({'zeit': time.strftime('%Y-%m-%dT%H:%M:%S'), 'notiz': args.notiz,
                       'bestanden': ergebnis.bestanden, 'pruefungen': ergebnis.zeilen,
                       'vl53': vl53}, handle, ensure_ascii=False, indent=2, default=str)
    return 0 if ergebnis.bestanden else 1


if __name__ == '__main__':
    sys.exit(main())
