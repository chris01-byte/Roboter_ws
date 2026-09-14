#!/usr/bin/env python3
"""Gerätefreier Langlauf der passiven WE-M2-Daten- und Aufgabenkette.

Der Prüfer startet keine ROS-Knoten, liest keine realen Karten und greift auf
keine Geräte zu. Deterministische synthetische OccupancyGrids laufen durch
Rohkartenfingerprint/Exaktjoin, ungefilterte Frontierbildung, topologische
Portalbeobachtung und die passive Regions-/Aufgabenverwaltung. Eingangsraster
werden vor und nach jeder Verarbeitung bytegleich verglichen.
"""

import argparse
from array import array
import json
import math
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Optional

from nav_msgs.msg import OccupancyGrid


ROOT = Path(__file__).resolve().parents[2]
for source_path in (
        ROOT / 'src' / 'amadeus_map_identity', ROOT / 'src' / 'explore'):
    if str(source_path) not in sys.path:
        sys.path.insert(0, str(source_path))

from explore.explore_node import ExploreNode  # noqa: E402
from explore.frontier_task_feed import (  # noqa: E402
    FrontierTaskFeedCapacityError,
    FrontierTaskPolicy,
    FrontierTaskTracker,
    frontier_inventory_from_clusters,
)
from explore.portal_memory import PortalMapContext  # noqa: E402
from explore.portal_source_adapter import (  # noqa: E402
    PortalSourceCorrelation,
    raw_map_portal_source_from_values,
)
from explore.raw_map_portal_adapter import (  # noqa: E402
    correlated_connected_portal_observations,
)
from explore.region_graph_shadow_lifecycle import (  # noqa: E402
    RegionGraphShadowLifecycle,
)


DEFAULT_REVISIONS = 60
MAXIMUM_REVISIONS = 512
MAXIMUM_PADDING_CELLS = 24
MAXIMUM_OUTPUT_BYTES = 65_536
RESOLUTION_M = 0.05
BASE_WIDTH = 100
BASE_HEIGHT = 60


def parse_vm_rss_bytes(status_text: str) -> int:
    match = re.search(r'^VmRSS:\s+(\d+)\s+kB$', status_text, re.MULTILINE)
    if match is None:
        raise ValueError('VmRSS fehlt in /proc-Status')
    return int(match.group(1)) * 1024


def current_rss_bytes() -> int:
    return parse_vm_rss_bytes(
        Path('/proc/self/status').read_text(encoding='ascii'))


def percentile(values: list[int], fraction: float) -> int:
    if not values or not 0.0 <= fraction <= 1.0:
        raise ValueError('Perzentilparameter sind ungueltig')
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def duration_summary_ns(values: list[int]) -> dict[str, int]:
    if not values or any(value < 0 for value in values):
        raise ValueError('Zeitmessungen muessen nichtnegative Werte enthalten')
    return {
        'minimum_ns': min(values),
        'median_ns': int(statistics.median(values)),
        'p95_ns': percentile(values, 0.95),
        'maximum_ns': max(values),
        'samples': len(values),
    }


def validate_arguments(revisions: int, growth_interval: int,
                       maximum_padding: int) -> None:
    for value, name, minimum, maximum in (
            (revisions, 'revisions', 2, MAXIMUM_REVISIONS),
            (growth_interval, 'growth_interval', 1, MAXIMUM_REVISIONS),
            (maximum_padding, 'maximum_padding', 0,
             MAXIMUM_PADDING_CELLS)):
        if (
                isinstance(value, bool) or not isinstance(value, int)
                or not minimum <= value <= maximum):
            raise ValueError(
                f'{name} muss zwischen {minimum} und {maximum} liegen')


def synthetic_apartment_grid(
        revision: int, *, growth_interval: int,
        maximum_padding: int, base_stamp_ns: int) -> OccupancyGrid:
    """Return a growing room-door-room raster with stable world geometry."""
    validate_arguments(max(2, revision), growth_interval, maximum_padding)
    if revision <= 0 or base_stamp_ns < 0:
        raise ValueError('Revision und Basisstempel muessen gueltig sein')
    padding = min(maximum_padding, (revision - 1) // growth_interval)
    width = BASE_WIDTH + 2 * padding
    height = BASE_HEIGHT + 2 * padding
    cells = array('b', [-1]) * (width * height)

    def mark_free(row_start, row_stop, col_start, col_stop):
        for row in range(row_start + padding, row_stop + padding):
            offset = row * width
            for col in range(col_start + padding, col_stop + padding):
                cells[offset + col] = 0

    mark_free(5, 55, 3, 48)
    mark_free(5, 55, 52, 97)
    door_start = 26 if revision % 2 == 0 else 27
    mark_free(door_start, 33, 48, 52)

    # One occupied marker in the synthetic unknown border changes the exact
    # fingerprint without touching the room, door or frontier geometry.
    marker_span = max(1, width - 2)
    marker_col = 1 + ((revision - 1) % marker_span)
    cells[marker_col] = 100

    message = OccupancyGrid()
    message.header.frame_id = 'map'
    stamp_ns = base_stamp_ns + revision * 1_000_000
    message.header.stamp.sec = stamp_ns // 1_000_000_000
    message.header.stamp.nanosec = stamp_ns % 1_000_000_000
    message.info.width = width
    message.info.height = height
    message.info.resolution = RESOLUTION_M
    message.info.origin.position.x = -padding * RESOLUTION_M
    message.info.origin.position.y = -padding * RESOLUTION_M
    message.info.origin.orientation.w = 1.0
    message.data = cells
    return message


def raw_source(message: OccupancyGrid):
    origin = message.info.origin
    return raw_map_portal_source_from_values(
        width=message.info.width,
        height=message.info.height,
        resolution=message.info.resolution,
        frame_id=message.header.frame_id,
        origin=(
            origin.position.x, origin.position.y, origin.position.z,
            origin.orientation.x, origin.orientation.y,
            origin.orientation.z, origin.orientation.w,
        ),
        cells=message.data,
        source_stamp_ns=(
            message.header.stamp.sec * 1_000_000_000
            + message.header.stamp.nanosec),
    )


def manager_status_json(source, revision: int) -> str:
    source_seconds = source.source_stamp_ns / 1_000_000_000.0
    return json.dumps({
        'schema_version': 1,
        'time': source_seconds + 0.1,
        'map': {
            'available': True,
            'snapshot_available': True,
            'age_seconds': 0.1,
            'summary': {
                'fingerprint': source.fingerprint,
                'frame_id': source.frame_id,
                'source_stamp_ns': source.source_stamp_ns,
            },
        },
        'counters': {'accepted_maps': revision},
    }, separators=(',', ':'), sort_keys=True)


def correlation_from_updates(raw_update, status_update):
    correlations = [
        update.raw_map_correlation
        for update in (raw_update, status_update)
        if update.raw_map_correlation is not None]
    if len(correlations) != 1:
        raise RuntimeError('Exaktjoin lieferte nicht genau eine Korrelation')
    return correlations[0]


def grid_signature(message: OccupancyGrid) -> tuple:
    origin = message.info.origin
    return (
        message.info.width, message.info.height, message.info.resolution,
        origin.position.x, origin.position.y, origin.position.z,
        origin.orientation.x, origin.orientation.y,
        origin.orientation.z, origin.orientation.w,
        message.header.frame_id,
        message.header.stamp.sec, message.header.stamp.nanosec,
        array('b', message.data).tobytes(),
    )


def capacity_probe() -> bool:
    context = PortalMapContext('capacity-session', 'capacity-map', 'map')
    tracker = FrontierTaskTracker(
        context, policy=FrontierTaskPolicy(max_frontiers=1))

    def inventory(revision, clusters):
        return frontier_inventory_from_clusters(PortalSourceCorrelation(
            context=context,
            map_revision=revision,
            fingerprint=f'{revision:064x}',
            source_stamp_ns=revision,
        ), clusters)

    tracker.observe(inventory(1, [(0.0, 0.0, 4)]))
    before = tracker.tracks()
    try:
        tracker.observe(inventory(2, [(0.0, 0.0, 4), (2.0, 0.0, 4)]))
    except FrontierTaskFeedCapacityError:
        return tracker.tracks() == before and tracker.latest_revision == 1
    return False


def run_probe(*, revisions: int = DEFAULT_REVISIONS,
              growth_interval: int = 10,
              maximum_padding: int = 6,
              base_stamp_ns: Optional[int] = None) -> dict:
    validate_arguments(revisions, growth_interval, maximum_padding)
    stamp = time.time_ns() if base_stamp_ns is None else base_stamp_ns
    if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp < 0:
        raise ValueError('base_stamp_ns muss eine nichtnegative Ganzzahl sein')

    lifecycle = RegionGraphShadowLifecycle(
        'we-m2at-offline-session', 'map', 'we-m2at-start',
        frontier_policy=FrontierTaskPolicy(association_radius_m=0.60),
        raw_map_capacity=2,
    )
    frontier_detector = ExploreNode.__new__(ExploreNode)
    durations = []
    rss_start = current_rss_bytes()
    rss_samples = [rss_start]
    first_frontier_ids = None
    maximum_task_count = 0
    input_bytes_checked = 0
    portal_observation_count = 0

    for revision in range(1, revisions + 1):
        started = time.perf_counter_ns()
        grid = synthetic_apartment_grid(
            revision,
            growth_interval=growth_interval,
            maximum_padding=maximum_padding,
            base_stamp_ns=stamp,
        )
        signature_before = grid_signature(grid)
        source = raw_source(grid)
        raw_update = lifecycle.accept_raw_map_source(
            source, received_monotonic_seconds=revision * 10.0)
        status_update = lifecycle.accept_map_status_json(
            manager_status_json(source, revision),
            received_monotonic_seconds=revision * 10.0 + 1.0,
        )
        correlation = correlation_from_updates(raw_update, status_update)

        frontiers = ExploreNode._detect_frontiers(
            frontier_detector, grid, 0.30)
        inventory = frontier_inventory_from_clusters(
            correlation,
            ((frontier.cx, frontier.cy, frontier.size)
             for frontier in frontiers),
        )
        lifecycle.observe_frontier_inventory(
            inventory,
            observed_monotonic_seconds=revision * 10.0 + 2.0,
        )

        origin = grid.info.origin
        observations = correlated_connected_portal_observations(
            correlation,
            width=grid.info.width,
            height=grid.info.height,
            resolution=grid.info.resolution,
            frame_id=grid.header.frame_id,
            origin=(
                origin.position.x, origin.position.y, origin.position.z,
                origin.orientation.x, origin.orientation.y,
                origin.orientation.z, origin.orientation.w,
            ),
            cells=grid.data,
            source_stamp_ns=source.source_stamp_ns,
            robot_xy=(1.025, 1.525),
            uncertainty_m=0.02,
            analysis_clearance_m=0.20,
            min_target_area_m2=0.40,
            min_gap_m=0.12,
            max_gap_m=0.80,
            exit_margin_m=0.25,
            max_traverse_distance_m=1.00,
        )
        if len(observations) != 1:
            raise RuntimeError(
                f'Revision {revision}: erwartet ein Portal, erhalten '
                f'{len(observations)}')
        for offset, observation in enumerate(observations):
            lifecycle.observe_structural_portal(
                observation,
                observed_monotonic_seconds=(
                    revision * 10.0 + 3.0 + offset * 0.001),
            )
            portal_observation_count += 1

        payload = json.loads(lifecycle.build_status_json(
            now_monotonic_seconds=revision * 10.0 + 4.0))
        frontier_ids = {
            task['subject_id'] for task in payload['tasks']
            if task['kind'] == 'frontier'}
        if not frontier_ids:
            raise RuntimeError('Ungefilterter Frontierbestand ging verloren')
        if first_frontier_ids is None:
            first_frontier_ids = frontier_ids
        elif frontier_ids != first_frontier_ids:
            raise RuntimeError(
                'Frontieridentitaet wuchs trotz stabiler Weltgeometrie')
        maximum_task_count = max(
            maximum_task_count, len(payload['tasks']))
        if grid_signature(grid) != signature_before:
            raise RuntimeError('Eingangsraster wurde waehrend der Kette mutiert')
        input_bytes_checked += len(signature_before[-1])
        durations.append(time.perf_counter_ns() - started)
        rss_samples.append(current_rss_bytes())

    if not capacity_probe():
        raise RuntimeError('Kapazitaetsfehler war nicht atomar und fail-closed')
    if first_frontier_ids is None:
        raise RuntimeError('Interner Fehler: keine Frontieridentitaet')
    if payload['summary']['confirmed_portal_count'] != 1:
        raise RuntimeError('Portal wurde nicht ueber Revisionen bestaetigt')
    if payload['summary']['region_count'] != 2:
        raise RuntimeError('Passive Gegenregion fehlt')
    if payload['summary']['connection_count'] != 1:
        raise RuntimeError('Passive Portalverbindung fehlt')
    if maximum_task_count != len(first_frontier_ids) + 2:
        raise RuntimeError('Aufgabenbestand ist unerwartet gewachsen')

    rss_end = current_rss_bytes()
    rss_samples.append(rss_end)
    result = {
        'schema_version': 1,
        'passive': True,
        'hardware_access': False,
        'actions_sent': 0,
        'commands_published': 0,
        'configuration': {
            'revisions': revisions,
            'growth_interval': growth_interval,
            'maximum_padding_cells': maximum_padding,
            'maximum_cell_count': (
                (BASE_WIDTH + 2 * maximum_padding)
                * (BASE_HEIGHT + 2 * maximum_padding)),
        },
        'observed': {
            'capacity_rejected_atomically': True,
            'confirmed_portal_count': payload['summary'][
                'confirmed_portal_count'],
            'connection_count': payload['summary']['connection_count'],
            'final_task_count': len(payload['tasks']),
            'frontier_task_count': len(first_frontier_ids),
            'input_bytes_checked': input_bytes_checked,
            'maximum_task_count': maximum_task_count,
            'portal_observation_count': portal_observation_count,
            'region_count': payload['summary']['region_count'],
        },
        'processing_duration': duration_summary_ns(durations),
        'rss_bytes': {
            'start': rss_start,
            'peak': max(rss_samples),
            'end': rss_end,
            'peak_increase': max(rss_samples) - rss_start,
        },
    }
    text = json.dumps(result, sort_keys=True, separators=(',', ':'))
    if len(text.encode('utf-8')) > MAXIMUM_OUTPUT_BYTES:
        raise RuntimeError('Ergebnis ueberschreitet die Ausgabegrenze')
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revisionen', type=int, default=DEFAULT_REVISIONS)
    parser.add_argument('--wachstumsintervall', type=int, default=10)
    parser.add_argument('--max-polsterzellen', type=int, default=6)
    parser.add_argument('--ausgabe', type=Path)
    return parser


def main(arguments=None) -> int:
    options = build_parser().parse_args(arguments)
    try:
        result = run_probe(
            revisions=options.revisionen,
            growth_interval=options.wachstumsintervall,
            maximum_padding=options.max_polsterzellen,
        )
    except Exception as error:
        print(f'ABBRUCH: {type(error).__name__}: {error}', file=sys.stderr)
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if options.ausgabe is not None:
        try:
            with options.ausgabe.open('x', encoding='utf-8') as output:
                output.write(text + '\n')
        except FileExistsError:
            print('ABBRUCH: Ausgabedatei existiert bereits', file=sys.stderr)
            return 1
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
