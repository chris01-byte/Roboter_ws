#!/usr/bin/env python3
"""Begrenzter synthetischer Lasttest der passiven WE-M2-Rohkartennaht.

Der Test startet nur einen Explorer und einen eigenen Publisher/Beobachter in
einer isolierten ROS-Domain. Er startet weder Hardware-, Sensor-, SLAM-, Nav2-
noch Missionsknoten, sendet keine Action und publiziert niemals einen Twist.
Alle Karten sind deterministisch synthetisch; reale Karten und Bags werden
nicht gelesen.

Der Kartenfingerprint fuer den synthetischen Managerstatus wird erst aus der
ueber DDS zurueckempfangenen OccupancyGrid-Nachricht gebildet. So gehen die
tatsaechlichen Wire-Typen, insbesondere float32 fuer die Aufloesung, in beide
Seiten des Exaktjoins ein.
"""

import argparse
from array import array
import json
import math
import os
from pathlib import Path
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Iterable, Optional


DEFAULT_DOMAIN_ID = 228
MAXIMUM_DOMAIN_ID = 232
MAXIMUM_CELL_COUNT = 4_000_000
MAXIMUM_CASES = 12
MAXIMUM_CAPACITY = 32
MAXIMUM_REPETITIONS = 20
MAXIMUM_OUTPUT_BYTES = 65_536
DOMAIN_QUIET_SECONDS = 2.0


def early_domain_id(arguments: Iterable[str]) -> int:
    """Read and validate --domaene before importing rclpy."""
    values = list(arguments)
    raw_values = []
    for index, value in enumerate(values):
        if value == '--domaene':
            if index + 1 >= len(values):
                raise ValueError('--domaene braucht einen Wert')
            raw_values.append(values[index + 1])
        elif value.startswith('--domaene='):
            raw_values.append(value.split('=', 1)[1])
    if not raw_values:
        return DEFAULT_DOMAIN_ID
    if len(raw_values) != 1:
        raise ValueError('--domaene darf nur einmal angegeben werden')
    raw = raw_values[0]
    try:
        result = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError('--domaene muss eine Ganzzahl sein') from error
    if not 0 <= result <= MAXIMUM_DOMAIN_ID:
        raise ValueError(
            f'--domaene muss zwischen 0 und {MAXIMUM_DOMAIN_ID} liegen')
    return result


try:
    _DOMAIN_ID = early_domain_id(sys.argv[1:])
except ValueError as _domain_error:
    if __name__ == '__main__':
        print(f'ABBRUCH: {_domain_error}', file=sys.stderr)
        raise SystemExit(2)
    _DOMAIN_ID = DEFAULT_DOMAIN_ID
os.environ['ROS_DOMAIN_ID'] = str(_DOMAIN_ID)

import rclpy  # noqa: E402
from ament_index_python.packages import (  # noqa: E402
    get_package_prefix,
    get_package_share_directory,
)
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import (  # noqa: E402
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import String  # noqa: E402

from explore.portal_source_adapter import (  # noqa: E402
    RawMapPortalSource,
    raw_map_portal_source_from_values,
)


def parse_integer_csv(text: str, *, name: str, minimum: int,
                      maximum: int) -> tuple[int, ...]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f'{name} darf nicht leer sein')
    result = []
    for part in text.split(','):
        clean = part.strip()
        try:
            value = int(clean)
        except ValueError as error:
            raise ValueError(f'{name} enthaelt keine Ganzzahl: {clean!r}') from error
        if not minimum <= value <= maximum:
            raise ValueError(
                f'{name} muss Werte zwischen {minimum} und {maximum} enthalten')
        if value in result:
            raise ValueError(f'{name} enthaelt den Wert {value} mehrfach')
        result.append(value)
    return tuple(result)


def validate_matrix(edges: tuple[int, ...], capacities: tuple[int, ...],
                    repetitions: int) -> None:
    if not edges or not capacities:
        raise ValueError('Raster- und Kapazitaetsmatrix duerfen nicht leer sein')
    if len(edges) * len(capacities) > MAXIMUM_CASES:
        raise ValueError(f'Matrix darf hoechstens {MAXIMUM_CASES} Faelle haben')
    if any(edge * edge > MAXIMUM_CELL_COUNT for edge in edges):
        raise ValueError(
            f'Raster darf hoechstens {MAXIMUM_CELL_COUNT} Zellen enthalten')
    if (
            isinstance(repetitions, bool)
            or not isinstance(repetitions, int)
            or not 1 <= repetitions <= MAXIMUM_REPETITIONS):
        raise ValueError(
            f'Wiederholungen muessen zwischen 1 und {MAXIMUM_REPETITIONS} liegen')


def percentile(values: list[int], fraction: float) -> int:
    """Return a deterministic nearest-rank percentile for bounded samples."""
    if not values:
        raise ValueError('Perzentil braucht mindestens einen Wert')
    if not 0.0 <= fraction <= 1.0:
        raise ValueError('Perzentilanteil muss zwischen 0 und 1 liegen')
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def duration_summary_ns(values: list[int]) -> dict[str, int]:
    if not values or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in values):
        raise ValueError('Zeitmessungen muessen nichtnegative Ganzzahlen sein')
    return {
        'minimum_ns': min(values),
        'median_ns': int(statistics.median(values)),
        'p95_ns': percentile(values, 0.95),
        'maximum_ns': max(values),
        'samples': len(values),
    }


def parse_vm_rss_bytes(status_text: str) -> int:
    match = re.search(r'^VmRSS:\s+(\d+)\s+kB$', status_text, re.MULTILINE)
    if match is None:
        raise ValueError('VmRSS fehlt in /proc-Status')
    return int(match.group(1)) * 1024


def process_rss_bytes(pid: int) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError('Prozess-ID muss positiv sein')
    try:
        text = Path(f'/proc/{pid}/status').read_text(encoding='ascii')
    except (OSError, UnicodeError) as error:
        raise RuntimeError('Explorer-RSS ist nicht mehr lesbar') from error
    return parse_vm_rss_bytes(text)


def source_from_grid(message: OccupancyGrid) -> RawMapPortalSource:
    origin = message.info.origin
    return raw_map_portal_source_from_values(
        width=int(message.info.width),
        height=int(message.info.height),
        resolution=float(message.info.resolution),
        frame_id=str(message.header.frame_id).strip(),
        origin=(
            float(origin.position.x),
            float(origin.position.y),
            float(origin.position.z),
            float(origin.orientation.x),
            float(origin.orientation.y),
            float(origin.orientation.z),
            float(origin.orientation.w),
        ),
        cells=message.data,
        source_stamp_ns=(
            int(message.header.stamp.sec) * 1_000_000_000
            + int(message.header.stamp.nanosec)
        ),
    )


def synthetic_grid(edge: int, sequence: int, stamp_ns: int) -> OccupancyGrid:
    if edge <= 0 or edge * edge > MAXIMUM_CELL_COUNT:
        raise ValueError('Synthetisches Raster verletzt die Zellgrenze')
    if sequence < 0 or stamp_ns < 0:
        raise ValueError('Sequenz und Quellstempel muessen nichtnegativ sein')
    message = OccupancyGrid()
    message.header.frame_id = 'map'
    message.header.stamp.sec = stamp_ns // 1_000_000_000
    message.header.stamp.nanosec = stamp_ns % 1_000_000_000
    message.info.width = edge
    message.info.height = edge
    message.info.resolution = 0.05
    message.info.origin.position.x = -0.15
    message.info.origin.position.y = 0.25
    message.info.origin.orientation.z = 0.01
    message.info.origin.orientation.w = math.sqrt(1.0 - 0.01 ** 2)
    cells = array('b', [-1]) * (edge * edge)
    cells[sequence % len(cells)] = sequence % 101
    message.data = cells
    return message


def manager_status_json(source: RawMapPortalSource, accepted_maps: int) -> str:
    if accepted_maps <= 0:
        raise ValueError('accepted_maps muss positiv sein')
    status_time = max(time.time(), source.source_stamp_ns / 1_000_000_000.0)
    age_seconds = max(
        0.0, status_time - source.source_stamp_ns / 1_000_000_000.0)
    return json.dumps({
        'schema_version': 1,
        'time': status_time,
        'map': {
            'available': True,
            'snapshot_available': True,
            'age_seconds': age_seconds,
            'summary': {
                'fingerprint': source.fingerprint,
                'frame_id': source.frame_id,
                'source_stamp_ns': source.source_stamp_ns,
            },
        },
        'counters': {'accepted_maps': accepted_maps},
    }, separators=(',', ':'), sort_keys=True)


def validate_diagnostics(payload: object, *, capacity: int,
                         expected_observations: int,
                         expected_unique: int,
                         expected_duplicates: int,
                         minimum_emitted: int) -> dict:
    if not isinstance(payload, dict):
        raise ValueError('Schattenstatus muss ein JSON-Objekt sein')
    if payload.get('mode') != 'shadow' or payload.get('passive') is not True:
        raise ValueError('Status ist kein passiver Schattenstatus')
    diagnostics = payload.get('raw_map_correlation')
    if not isinstance(diagnostics, dict):
        raise ValueError('Rohkartenkorrelationsdiagnose fehlt')
    expected = {
        'enabled': True,
        'capacity': capacity,
        'source_observations': expected_observations,
        'unique_sources': expected_unique,
        'duplicate_sources': expected_duplicates,
        'emitted_correlations': minimum_emitted,
    }
    for key, value in expected.items():
        if diagnostics.get(key) != value:
            raise ValueError(
                f'Rohkartendiagnose {key}={diagnostics.get(key)!r}, '
                f'erwartet {value!r}')
    pending = diagnostics.get('pending_sources')
    evicted = diagnostics.get('evicted_sources')
    if (
            isinstance(pending, bool) or not isinstance(pending, int)
            or isinstance(evicted, bool) or not isinstance(evicted, int)
            or not 0 <= pending <= capacity or evicted < 0):
        raise ValueError('Warte-/Verdraengungszaehler sind ungueltig')
    if expected_unique != pending + evicted + minimum_emitted:
        raise ValueError('Rohkartendiagnose verletzt die Zaehlererhaltung')
    return diagnostics


def bounded_json(payload: dict) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'),
                      sort_keys=True)
    if len(text.encode('utf-8')) > MAXIMUM_OUTPUT_BYTES:
        raise ValueError('Ergebnis ueberschreitet die feste Ausgabegrenze')
    return text


def stop_process(process, *, interrupt_timeout: float = 10.0,
                 terminate_timeout: float = 5.0) -> None:
    """Stop exactly one child; never signal its process group."""
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=interrupt_timeout)
        return
    except subprocess.TimeoutExpired:
        process.terminate()
    try:
        process.wait(timeout=terminate_timeout)
        return
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=terminate_timeout)


class RawMapProbeNode(Node):
    def __init__(self, *, node_name: str, map_topic: str,
                 manager_topic: str, shadow_topic: str):
        super().__init__(node_name)
        map_qos = QoSProfile(depth=1)
        shadow_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.map_publisher = self.create_publisher(
            OccupancyGrid, map_topic, map_qos)
        self.manager_publisher = self.create_publisher(
            String, manager_topic, shadow_qos)
        self.create_subscription(
            OccupancyGrid, map_topic, self._on_wire_map, map_qos)
        self.create_subscription(
            String, shadow_topic, self._on_shadow_status, shadow_qos)
        self.wire_sources: dict[int, RawMapPortalSource] = {}
        self.factory_durations_ns: list[int] = []
        self.wire_observations = 0
        self.latest_shadow_payload: Optional[dict] = None
        self.maximum_pending_sources = 0

    def _on_wire_map(self, message: OccupancyGrid) -> None:
        started = time.perf_counter_ns()
        source = source_from_grid(message)
        self.factory_durations_ns.append(time.perf_counter_ns() - started)
        self.wire_sources[source.source_stamp_ns] = source
        self.wire_observations += 1

    def _on_shadow_status(self, message: String) -> None:
        if len(message.data.encode('utf-8')) > MAXIMUM_OUTPUT_BYTES:
            raise RuntimeError('Schattenstatus ueberschreitet die Testgrenze')
        payload = json.loads(message.data)
        if not isinstance(payload, dict):
            raise RuntimeError('Schattenstatus ist kein Objekt')
        diagnostics = payload.get('raw_map_correlation')
        if isinstance(diagnostics, dict):
            pending = diagnostics.get('pending_sources')
            if isinstance(pending, int) and not isinstance(pending, bool):
                self.maximum_pending_sources = max(
                    self.maximum_pending_sources, pending)
        self.latest_shadow_payload = payload

    def publish_map(self, message: OccupancyGrid) -> None:
        self.map_publisher.publish(message)

    def publish_manager_status(self, source: RawMapPortalSource,
                               accepted_maps: int) -> None:
        self.manager_publisher.publish(String(
            data=manager_status_json(source, accepted_maps)))


def full_node_names(node: Node) -> set[str]:
    result = set()
    for name, namespace in node.get_node_names_and_namespaces():
        prefix = namespace.rstrip('/')
        result.add(f'{prefix}/{name}' if prefix else f'/{name}')
    return result


def assert_isolated_domain(node: Node, *, own_name: str,
                           deadline: float) -> None:
    """Require a continuously quiet discovery window before any child start."""
    quiet_since = None
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        names = full_node_names(node)
        unexpected = names - {own_name}
        if unexpected:
            raise RuntimeError(
                'Testdomain enthaelt fremde ROS-Knoten: '
                + ', '.join(sorted(unexpected)))
        if names == {own_name}:
            if quiet_since is None:
                quiet_since = time.monotonic()
            elif time.monotonic() - quiet_since >= DOMAIN_QUIET_SECONDS:
                return
        else:
            quiet_since = None
    raise TimeoutError('Testdomain wurde nicht dauerhaft leer beobachtet')


def explorer_program() -> str:
    """Resolve the sourced Explorer and reject an overlay without WE-M2/AE."""
    prefix = Path(get_package_prefix('explore'))
    program = prefix / 'lib' / 'explore' / 'explore'
    parameter_file = (
        Path(get_package_share_directory('explore'))
        / 'config' / 'explore_params.yaml')
    if not program.is_file():
        raise RuntimeError(f'Explorerprogramm fehlt unter {program}')
    try:
        parameters = parameter_file.read_text(encoding='utf-8')
    except OSError as error:
        raise RuntimeError('Installierte Explorerparameter sind nicht lesbar') from error
    for contract in (
            'region_graph_shadow_raw_map_enabled: false',
            'region_graph_shadow_raw_map_capacity: 0'):
        if contract not in parameters:
            raise RuntimeError(
                'Gesourcter Explorer enthaelt den WE-M2/AE-Vertrag nicht')
    return str(program)


def explorer_command(*, executable: str, explorer_name: str, prefix: str,
                     capacity: int, behavior_tree: str) -> list[str]:
    parameter_values = {
        'map_topic': f'{prefix}/map',
        'global_costmap_topic': f'{prefix}/unused_global_costmap',
        'odom_topic': f'{prefix}/unused_odom',
        'door_lidar_scan_topic': f'{prefix}/unused_scan',
        'scan_command_topic': f'{prefix}/unused_scan_cmd',
        'door_command_topic': f'{prefix}/unused_door_cmd',
        'nav_action_name': f'{prefix}/unused_navigate_to_pose',
        'status_topic': f'{prefix}/explore_status',
        'visualize': 'false',
        'behavior_tree': behavior_tree,
        'region_graph_shadow_enabled': 'true',
        'region_graph_shadow_raw_map_enabled': 'true',
        'region_graph_shadow_raw_map_capacity': str(capacity),
        'region_graph_shadow_session_id': f'we-m2ag-session-{capacity}',
        'region_graph_shadow_start_observation_id': 'we-m2ag-start',
        'region_graph_shadow_map_status_topic': f'{prefix}/manager_status',
        'region_graph_shadow_status_topic': f'{prefix}/shadow_status',
    }
    command = [executable, '--ros-args',
               '-r', f'__node:={explorer_name}',
               '-r', f'/explore_area:={prefix}/unused_explore_area']
    for name, value in parameter_values.items():
        command.extend(['-p', f'{name}:={value}'])
    return command


def spin_until(node: RawMapProbeNode, predicate, *, deadline: float,
               operation: str, process=None,
               rss_samples: Optional[list[int]] = None) -> None:
    while time.monotonic() < deadline:
        if process is not None:
            if process.poll() is not None:
                raise RuntimeError(
                    f'Explorerprozess endete vorzeitig mit Code '
                    f'{process.returncode}')
            if rss_samples is not None:
                rss_samples.append(process_rss_bytes(process.pid))
        rclpy.spin_once(node, timeout_sec=0.02)
        if predicate():
            return
    raise TimeoutError(f'Begrenzte Wartefrist abgelaufen: {operation}')


def run_case(*, edge: int, capacity: int, repetitions: int,
             interval_seconds: float, timeout_seconds: float,
             case_index: int, global_deadline: float) -> dict:
    token = f'we_m2ag_{os.getpid()}_{case_index}'
    prefix = f'/{token}'
    probe_name = f'{token}_probe'
    explorer_name = f'{token}_explorer'
    node = RawMapProbeNode(
        node_name=probe_name,
        map_topic=f'{prefix}/map',
        manager_topic=f'{prefix}/manager_status',
        shadow_topic=f'{prefix}/shadow_status',
    )
    log = tempfile.NamedTemporaryFile(
        prefix='we_m2ag_explorer_', suffix='.log', mode='w+', delete=False)
    process = None
    started = time.perf_counter_ns()
    rss_samples: list[int] = []
    case_deadline = min(global_deadline, time.monotonic() + timeout_seconds)
    try:
        assert_isolated_domain(
            node,
            own_name=f'/{probe_name}',
            deadline=min(
                case_deadline,
                time.monotonic() + DOMAIN_QUIET_SECONDS + 2.0),
        )
        process = subprocess.Popen(
            explorer_command(
                executable=explorer_program(),
                explorer_name=explorer_name, prefix=prefix,
                capacity=capacity,
                behavior_tree=str(
                    Path(get_package_share_directory('explore'))
                    / 'behavior_trees'
                    / 'navigate_to_pose_no_recovery.xml'),
            ),
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        expected_nodes = {f'/{probe_name}', f'/{explorer_name}'}
        spin_until(
            node,
            lambda: (
                full_node_names(node) == expected_nodes
                and node.map_publisher.get_subscription_count() >= 2
                and node.manager_publisher.get_subscription_count() >= 1
            ),
            deadline=case_deadline,
            operation='Explorer und private Endpunkte bereit',
            process=process,
            rss_samples=rss_samples,
        )
        start_rss = process_rss_bytes(process.pid)
        rss_samples.append(start_rss)

        base_stamp_ns = time.time_ns()
        anchor_grid = synthetic_grid(1, 0, base_stamp_ns)
        anchor_source = source_from_grid(anchor_grid)
        node.publish_manager_status(anchor_source, 1)
        spin_until(
            node,
            lambda: (
                isinstance(node.latest_shadow_payload, dict)
                and isinstance(
                    node.latest_shadow_payload.get('raw_map_correlation'), dict)
            ),
            deadline=case_deadline,
            operation='erster Schattenstatus nach Ankerstatus',
            process=process,
            rss_samples=rss_samples,
        )

        matched_stamp = base_stamp_ns + 1_000_000
        matched_grid = synthetic_grid(edge, 1, matched_stamp)
        before = node.wire_observations
        node.publish_map(matched_grid)
        spin_until(
            node,
            lambda: node.wire_observations > before,
            deadline=case_deadline,
            operation='Wire-Roundtrip der Joinquelle',
            process=process,
            rss_samples=rss_samples,
        )
        matched_source = node.wire_sources[matched_stamp]
        spin_until(
            node,
            lambda: (
                node.latest_shadow_payload['raw_map_correlation'][
                    'source_observations'] >= 1
            ),
            deadline=case_deadline,
            operation='Explorer beobachtet Joinquelle',
            process=process,
            rss_samples=rss_samples,
        )
        join_started = time.perf_counter_ns()
        node.publish_manager_status(matched_source, 2)
        spin_until(
            node,
            lambda: (
                node.latest_shadow_payload['raw_map_correlation'][
                    'emitted_correlations'] >= 1
            ),
            deadline=case_deadline,
            operation='exakter Join im Schattenstatus',
            process=process,
            rss_samples=rss_samples,
        )
        join_latency_ns = time.perf_counter_ns() - join_started

        latest_grid = None
        unique_after_join = capacity + 2
        for offset in range(unique_after_join):
            sequence = offset + 2
            stamp_ns = base_stamp_ns + sequence * 1_000_000
            latest_grid = synthetic_grid(edge, sequence, stamp_ns)
            before = node.wire_observations
            node.publish_map(latest_grid)
            spin_until(
                node,
                lambda: node.wire_observations > before,
                deadline=case_deadline,
                operation='Wire-Roundtrip einer eindeutigen Lastkarte',
                process=process,
                rss_samples=rss_samples,
            )
            until = min(case_deadline, time.monotonic() + interval_seconds)
            while time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=0.01)
                rss_samples.append(process_rss_bytes(process.pid))

        if latest_grid is None:
            raise RuntimeError('Interner Testfehler: letzte Karte fehlt')
        for _ in range(repetitions):
            before = node.wire_observations
            node.publish_map(latest_grid)
            spin_until(
                node,
                lambda: node.wire_observations > before,
                deadline=case_deadline,
                operation='Wire-Roundtrip einer Duplikatkarte',
                process=process,
                rss_samples=rss_samples,
            )
            until = min(case_deadline, time.monotonic() + interval_seconds)
            while time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=0.01)
                rss_samples.append(process_rss_bytes(process.pid))

        expected_unique = 1 + unique_after_join
        expected_observations = expected_unique + repetitions
        spin_until(
            node,
            lambda: (
                node.latest_shadow_payload['raw_map_correlation'][
                    'source_observations'] >= expected_observations
            ),
            deadline=case_deadline,
            operation='finale begrenzte Joinerdiagnose',
            process=process,
            rss_samples=rss_samples,
        )
        diagnostics = validate_diagnostics(
            node.latest_shadow_payload,
            capacity=capacity,
            expected_observations=expected_observations,
            expected_unique=expected_unique,
            expected_duplicates=repetitions,
            minimum_emitted=1,
        )
        if diagnostics['pending_sources'] != capacity:
            raise RuntimeError('Finale Warteschlange erreicht Kapazitaet nicht')
        if diagnostics['evicted_sources'] != 2:
            raise RuntimeError('Verdraengungsfall wurde nicht exakt beobachtet')
        end_rss = process_rss_bytes(process.pid)
        rss_samples.append(end_rss)
        return {
            'capacity': capacity,
            'cell_count': edge * edge,
            'edge_cells': edge,
            'factory_duration': duration_summary_ns(
                node.factory_durations_ns),
            'join_status_latency_ns': join_latency_ns,
            'maximum_pending_sources': node.maximum_pending_sources,
            'observed': {
                'duplicate_sources': diagnostics['duplicate_sources'],
                'emitted_correlations': diagnostics['emitted_correlations'],
                'evicted_sources': diagnostics['evicted_sources'],
                'source_observations': diagnostics['source_observations'],
                'unique_sources': diagnostics['unique_sources'],
            },
            'repetitions': repetitions,
            'rss_bytes': {
                'start': start_rss,
                'peak': max(rss_samples),
                'end': end_rss,
            },
            'runtime_ns': time.perf_counter_ns() - started,
        }
    finally:
        if process is not None:
            stop_process(process)
        node.destroy_node()
        log.close()
        try:
            os.unlink(log.name)
        except OSError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domaene', type=int, default=_DOMAIN_ID)
    parser.add_argument('--raster-kanten', default='64,256,512')
    parser.add_argument('--kapazitaeten', default='1,4')
    parser.add_argument('--wiederholungen', type=int, default=3)
    parser.add_argument('--intervall-sekunden', type=float, default=0.05)
    parser.add_argument('--fall-timeout-sekunden', type=float, default=15.0)
    parser.add_argument('--gesamt-timeout-sekunden', type=float, default=120.0)
    return parser


def validated_arguments(arguments=None):
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        if not 0 <= args.domaene <= MAXIMUM_DOMAIN_ID:
            raise ValueError(
                f'--domaene muss zwischen 0 und {MAXIMUM_DOMAIN_ID} liegen')
        edges = parse_integer_csv(
            args.raster_kanten, name='--raster-kanten', minimum=1,
            maximum=int(math.sqrt(MAXIMUM_CELL_COUNT)))
        capacities = parse_integer_csv(
            args.kapazitaeten, name='--kapazitaeten', minimum=1,
            maximum=MAXIMUM_CAPACITY)
        validate_matrix(edges, capacities, args.wiederholungen)
        for name, value, minimum, maximum in (
                ('--intervall-sekunden', args.intervall_sekunden, 0.01, 1.0),
                ('--fall-timeout-sekunden', args.fall_timeout_sekunden, 3.0, 60.0),
                ('--gesamt-timeout-sekunden', args.gesamt_timeout_sekunden, 3.0, 600.0)):
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError(
                    f'{name} muss endlich zwischen {minimum} und {maximum} liegen')
        if args.gesamt_timeout_sekunden < args.fall_timeout_sekunden:
            raise ValueError(
                '--gesamt-timeout-sekunden darf nicht kleiner als '
                '--fall-timeout-sekunden sein')
    except ValueError as error:
        parser.error(str(error))
    args.edges = edges
    args.capacities = capacities
    return args


def main(arguments=None) -> int:
    args = validated_arguments(arguments)
    if args.domaene != _DOMAIN_ID:
        print(
            'ABBRUCH: --domaene wurde nach dem ROS-Import veraendert.',
            file=sys.stderr,
        )
        return 2
    rclpy.init()
    started = time.perf_counter_ns()
    deadline = time.monotonic() + args.gesamt_timeout_sekunden
    cases = []
    try:
        index = 0
        for capacity in args.capacities:
            for edge in args.edges:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Gesamtfrist vor Matrixende abgelaufen')
                cases.append(run_case(
                    edge=edge,
                    capacity=capacity,
                    repetitions=args.wiederholungen,
                    interval_seconds=args.intervall_sekunden,
                    timeout_seconds=args.fall_timeout_sekunden,
                    case_index=index,
                    global_deadline=deadline,
                ))
                index += 1
        payload = {
            'actions_sent': 0,
            'cases': cases,
            'commands_published': 0,
            'domain_id': args.domaene,
            'hardware_access': False,
            'kind': 'we_m2_raw_map_shadow_load_probe',
            'passive': True,
            'runtime_ns': time.perf_counter_ns() - started,
            'schema_version': 1,
        }
        print(bounded_json(payload))
        return 0
    except (OSError, RuntimeError, TimeoutError, ValueError) as error:
        print(f'ABBRUCH: {error}', file=sys.stderr)
        return 1
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
