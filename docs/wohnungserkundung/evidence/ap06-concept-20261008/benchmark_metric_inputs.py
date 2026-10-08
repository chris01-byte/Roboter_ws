#!/usr/bin/env python3
"""Offline cost profile of the unchanged installed metric input pipeline.

Uses saved synthetic joined-a CDR maps/scan and its recorded TF chain. The
existing test fixture supplies a non-Node instance and fixed evaluation clocks;
this is NOT a replay of DDS delays, a sensor-freshness receipt, or a mission.
No ROS nodes, publishers, actuator endpoints or product files are created.
"""
import argparse
from collections import defaultdict, deque
import cProfile
import gzip
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import pstats
import statistics
import sys
import threading
import time
from types import SimpleNamespace


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(message):
    return message.header.stamp.sec*10**9+message.header.stamp.nanosec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/evidence/ap06-concept-20261008/joined-a/door68_start_a'))
    parser.add_argument('--repo', type=Path, default=Path('/evidence/ap06-repo'))
    parser.add_argument('--install-root', type=Path, default=Path('/evidence/ap06-old-product-install'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert Path('/.dockerenv').exists() and os.environ.get('AP06_SIMULATION') == '1'
    assert not any(Path(p).exists() for p in ('/dev/ttyUSB_BASE', '/dev/ttyUSB_HWT601', '/etc/nv_tegra_release'))
    args.output.mkdir(parents=True, exist_ok=False)

    import numpy as np
    import pytest
    import rclpy
    from rclpy.serialization import deserialize_message
    from rclpy.time import Time
    from tf2_ros import Buffer
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import OccupancyGrid
    from sensor_msgs.msg import LaserScan
    from explore.explore_node import ExploreNode
    from explore.exploration_scope import AuthorizedExplorationScope
    from explore.portal_memory import PortalMapContext, Point2D
    from explore.portal_source_adapter import PortalSourceCorrelation, raw_map_portal_source_from_values
    from explore.metric_egress_reference import ReferencedStartEgress

    sys.path.insert(0, str(args.repo/'src/explore/test'))
    from test_metric_frontier import body_input_fixture
    module_names = ('explore.explore_node', 'explore.metric_frontier_runtime', 'explore.metric_frontier',
        'explore.metric_egress_reference', 'explore.frontier_task_evidence', 'explore.exploration_scope',
        'amadeus_map_identity.fingerprint')
    modules = {}
    for name in module_names:
        path = Path(importlib.import_module(name).__file__).resolve()
        assert args.install_root.resolve() in path.parents, (name, path)
        modules[name] = dict(path=str(path), sha256=sha(path))
    inputs = {name: dict(path=str(args.source/name), sha256=sha(args.source/name)) for name in (
        'result.json', 'final_raw_map.cdr', 'final_costmap.cdr', 'final_scan.cdr', 'events.jsonl.gz')}
    result = json.loads((args.source/'result.json').read_text())
    assert result['metric']['reason'] == 'self_body_scan_stale_after_processing'
    assert result['metric']['start_reference']['retained'] == [0, 0]
    assert result['metric']['start_reference']['retained_area_m2'] == [0., 0.]
    assert result['metric']['start_reference']['projected'] == [0, 0]
    raw = deserialize_message((args.source/'final_raw_map.cdr').read_bytes(), OccupancyGrid)
    cost = deserialize_message((args.source/'final_costmap.cdr').read_bytes(), OccupancyGrid)
    scan = deserialize_message((args.source/'final_scan.cdr').read_bytes(), LaserScan)
    transforms = defaultdict(lambda: deque(maxlen=256))
    wheel = None
    with gzip.open(args.source/'events.jsonl.gz', 'rt') as stream:
        for line in stream:
            event = json.loads(line)
            if event['topic'] == '/tf':
                value = event['transform']
                transforms[value['parent'], value['child']].append(value)
            elif event['topic'] == '/base_hardware/state_json':
                wheel = event['data']
    rclpy.init(args=[])
    try:
        buffer = Buffer()
        for values in transforms.values():
            for value in values:
                transform = TransformStamped()
                transform.header.frame_id, transform.child_frame_id = value['parent'], value['child']
                transform.header.stamp.sec, transform.header.stamp.nanosec = value['stamp']
                t, q = transform.transform.translation, transform.transform.rotation
                t.x, t.y, t.z = value['translation']
                q.x, q.y, q.z, q.w = value['rotation']
                buffer.set_transform(transform, 'recorded_synthetic_joined_a')
        # Same declared static transform as the original AP06 SensorProcess.
        transform = TransformStamped()
        transform.header.frame_id, transform.child_frame_id = 'base_link', 'laser_frame'
        transform.transform.translation.x, transform.transform.translation.z = .245, .660
        transform.transform.rotation.z = math.sin(math.pi/4)
        transform.transform.rotation.w = math.cos(math.pi/4)
        buffer.set_transform_static(transform, 'original_harness_static_mount')
        actual = buffer.lookup_transform('map', 'base_link', Time())
        fixture_ros_now = max(stamp(raw), stamp(cost), stamp(actual))+1_000_000
        source = raw_map_portal_source_from_values(**ExploreNode._metric_grid_values(raw))
        context = PortalMapContext('ap06-door68_start_a', 'map-'+result['initial_map']['fingerprint'], 'map')
        correlation = PortalSourceCorrelation(context, 1, source.fingerprint, source.source_stamp_ns)
        start = result['case']['start']
        polygon = np.asarray([[-2.8, -1.4], [2.8, -1.4], [2.8, 1.4], [-2.8, 1.4]])-start[:2]
        ca, sa = math.cos(start[2]), math.sin(start[2])
        polygon = polygon@np.array([[ca, -sa], [sa, ca]])
        scope = AuthorizedExplorationScope('ap06-two-rooms', context, tuple(Point2D(*p) for p in polygon))
        report = dict(schema=1, diagnostic_only=True, hardware_qualified=False, mission_qualified=False,
            source_reason=result['metric']['reason'], original_inputs=inputs, installed_modules=modules,
            benchmark=dict(path=str(Path(__file__).resolve()), sha256=sha(__file__)),
            evaluation_clock='Existing test fixture: fixed monotonic 10.0; ROS time max original stamps + 1ms. No stamps modified.',
            fixture_ros_now_ns=fixture_ros_now, affinity=sorted(os.sched_getaffinity(0)),
            limitations=['No concurrent ROS/DDS/process load: compute microbenchmark only.',
                'Exact saved final CDR grids; final composed common-time TF pose, not the discarded failing input object.',
                'Original start ledger was not captured: reconstruct and assert the reported empty private inventory.',
                'Steady case keeps real geometry memo; cold case invalidates only its projection memo, not evidence.',
                'cProfile overhead changes wall time; use unprofiled values for elapsed-cost comparisons.'],
            raw_shape=[raw.info.height, raw.info.width], cost_shape=[cost.info.height, cost.info.width],
            original_stamps_ns=dict(raw=stamp(raw), cost=stamp(cost), tf=stamp(actual), scan=stamp(scan)),
            scope_vertices=polygon.tolist(), timings={}, profiles={})
        with pytest.MonkeyPatch.context() as patch:
            node = body_input_fixture(patch, 10.)
            del node._metric_matches_status
            del node._robot_pose_sample
            del node._door_lidar_mount
            del node._door_lidar_scan_snapshot
            node._metric_raw = (raw, source, 10.)
            node._metric_correlation, node._metric_scope = correlation, scope
            node._metric_status_at = 10.
            node._metric_status = {}
            node._global_costmap, node._global_costmap_received_at = cost, 10.
            node._wohnungserkundung_evidence_max_cells = 262144
            node._metric_start_egress_enabled = True
            node._metric_egress = node._metric_egress_identity = None
            node._metric_egress_expired = node._metric_body_anchor_expired = False
            node._metric_bounds = (-.13, .33, -.25, .25)
            node._metric_path_validation = 'rpp_rollout'
            node._robot_base_frame = 'base_link'
            node._tf_buffer = buffer
            node.get_clock = lambda: SimpleNamespace(now=lambda: Time(nanoseconds=fixture_ros_now))
            node._door_scan_lock = threading.Lock()
            node._on_door_lidar_scan(scan)
            # Recorded wheel pose; fixed offline sample times are fixture values,
            # not a new or restamped measurement. Original binding still checks it.
            node._hwt_guard = SimpleNamespace(health=SimpleNamespace(lock=threading.RLock(),
                samples={'wheel': ((1, 0), 10., 10., True)}, sample_details={'wheel': dict(
                    frame_id='odom', child_frame_id='base_link', position=[wheel['x'], wheel['y'], 0.],
                    orientation=[0., 0., math.sin(wheel['yaw']/2), math.cos(wheel['yaw']/2)])}))
            # Two complete original calls initialize the existing empty ledger.
            for _ in range(2):
                values = node._metric_inputs_locked(active=True)
                assert len(values) == 7
            assert all(isinstance(e, ReferencedStartEgress) and e.valid and not e.unknown.any()
                and not e.fixed.unknown.any() and e.retained_region.is_empty for e in node._metric_egress)
            report['pose'] = list(values[2])
            report['reference'] = list(values.map_odom_reference)
            report['bound_physical_motion'] = values.physical_motion
            report['mask_cells'] = dict(known=int(values[3].sum()), safe=int(values[4].sum()), cost_known=int(values[6].sum()))
            report['steady_state'] = dict(retained=[int(e.fixed.unknown.sum()) for e in node._metric_egress],
                projected=[int(e.unknown.sum()) for e in node._metric_egress], valid=[e.valid for e in node._metric_egress])
            for mode in ('steady', 'cold_projection'):
                timings = []
                for _ in range(5):
                    if mode == 'cold_projection':
                        for evidence in node._metric_egress:
                            evidence._projection_key = None
                    begin = time.perf_counter()
                    values = node._metric_inputs_locked(active=True)
                    timings.append(time.perf_counter()-begin)
                report['timings'][mode] = dict(seconds=timings, mean_s=statistics.mean(timings),
                    median_s=statistics.median(timings), maximum_s=max(timings), minimum_s=min(timings))
                profile = cProfile.Profile()
                begin = time.perf_counter()
                for _ in range(4):
                    if mode == 'cold_projection':
                        for evidence in node._metric_egress:
                            evidence._projection_key = None
                    values = profile.runcall(node._metric_inputs_locked, active=True)
                elapsed = time.perf_counter()-begin
                profile.dump_stats(str(args.output/(mode+'.prof')))
                stream = io.StringIO()
                stats = pstats.Stats(profile, stream=stream).sort_stats('cumulative')
                stats.print_stats(50)
                (args.output/(mode+'.txt')).write_text(stream.getvalue())
                stages = []
                names = {'_metric_inputs_locked', '_validated_snapshot', 'compact_occupancy_cells',
                    'map_snapshot_fingerprint', 'rasterize_scope', 'known_safe_mask', '_metric_prepare_egress',
                    '_metric_motion_binding_for_geometry', 'self_body_unknown_mask', 'footprint_clear',
                    'footprint_cells', 'refresh', 'check_trajectory'}
                for (filename, line, name), (primitive, total, own, cumulative, callers) in stats.stats.items():
                    if name in names:
                        stages.append(dict(file=filename, line=line, function=name, calls=total,
                            own_s=own, cumulative_s=cumulative, cumulative_fraction=cumulative/stats.total_tt))
                report['profiles'][mode] = dict(iterations=4, wall_s=elapsed, profile_total_s=stats.total_tt,
                    stages=sorted(stages, key=lambda x: -x['cumulative_s']),
                    note='Nested cumulative times overlap and must not be added.')
            report['call_count'] = dict(warmup=2, unprofiled=10, profiled=8, total=20)
        (args.output/'result.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        print(json.dumps(dict(output=str(args.output), timings=report['timings'],
            profiles={k:v['stages'] for k,v in report['profiles'].items()}), indent=2))
    finally:
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
