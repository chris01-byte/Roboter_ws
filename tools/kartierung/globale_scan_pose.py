#!/usr/bin/env python3
"""Visualisiert die Kandidaten des rein lesenden globalen Vollscan-Matchers.

Das Werkzeug verwendet denselben Kern wie die automatische Initialisierung,
publiziert aber weder ``/initialpose`` noch Fahrbefehle.
"""

import argparse
import json
import math
import time
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
import rclpy  # noqa: E402
from rclpy.duration import Duration  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import (  # noqa: E402
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.time import Time  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402
from tf2_ros import Buffer, TransformException, TransformListener  # noqa: E402

from robot_navigation.global_scan_localizer import (  # noqa: E402
    scan_points,
    yaw_from_quaternion,
)
from robot_navigation.global_scan_matcher import (  # noqa: E402
    MapScorer,
    search_global_pose,
    select_evenly,
    transform_points,
)


class Capture(Node):
    def __init__(self):
        super().__init__('globale_scan_pose_diagnose')
        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.map_message = None
        self.scan_message = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_subscription(
            OccupancyGrid, '/map', self._on_map, map_qos)
        self.create_subscription(
            LaserScan, '/scan_normiert', self._on_scan,
            qos_profile_sensor_data)

    def _on_map(self, message):
        self.map_message = message

    def _on_scan(self, message):
        self.scan_message = message


def wait_for_data(node, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.map_message is None or node.scan_message is None:
            continue
        try:
            return node.tf_buffer.lookup_transform(
                'base_link', node.scan_message.header.frame_id, Time(),
                timeout=Duration(seconds=0.5))
        except TransformException as error:
            last_error = str(error)
    raise RuntimeError(
        f'Daten unvollstaendig: Karte={node.map_message is not None}, '
        f'Scan={node.scan_message is not None}, TF={last_error!r}.')


def map_scorer(message):
    height, width = int(message.info.height), int(message.info.width)
    if width <= 0 or height <= 0 or len(message.data) != width * height:
        raise RuntimeError('Kartenabmessungen oder Kartendaten sind ungueltig')
    origin = message.info.origin
    return MapScorer(
        np.asarray(message.data, dtype=np.int16).reshape(height, width),
        float(message.info.resolution),
        float(origin.position.x),
        float(origin.position.y),
        yaw_from_quaternion(origin.orientation))


def render(output_path, scorer, result, base_endpoints):
    grid = scorer.grid
    display = np.empty((*grid.shape, 3), dtype=np.float32)
    display[grid < 0] = (0.72, 0.72, 0.72)
    display[(grid >= 0) & (grid < 65)] = (1.0, 1.0, 1.0)
    display[grid >= 65] = (0.08, 0.08, 0.08)
    extent = (
        scorer.origin_x,
        scorer.origin_x + scorer.width * scorer.resolution,
        scorer.origin_y,
        scorer.origin_y + scorer.height * scorer.resolution,
    )
    figure, axis = plt.subplots(figsize=(8, 9), constrained_layout=True)
    axis.imshow(display, origin='lower', interpolation='nearest', extent=extent)
    colors = plt.cm.tab10(np.linspace(0, 1, len(result.candidates)))
    for rank, (candidate, color) in enumerate(
            zip(result.candidates, colors), 1):
        if rank == 1:
            points = transform_points(
                base_endpoints, candidate.x_m, candidate.y_m,
                candidate.yaw_rad)
            axis.scatter(
                points[:, 0], points[:, 1], s=3, color=color, alpha=0.45,
                label='Scan der besten Hypothese')
        axis.scatter(
            [candidate.x_m], [candidate.y_m],
            s=100 if rank == 1 else 50, color=color, zorder=5)
        axis.arrow(
            candidate.x_m, candidate.y_m,
            0.42 * math.cos(candidate.yaw_rad),
            0.42 * math.sin(candidate.yaw_rad),
            width=0.018, head_width=0.12, head_length=0.13,
            color=color, length_includes_head=True, zorder=5)
        axis.text(
            candidate.x_m + 0.08, candidate.y_m + 0.08, str(rank),
            color=color, fontsize=10, weight='bold')
    axis.set_aspect('equal', adjustable='box')
    axis.set_xlabel('Karten-x [m]')
    axis.set_ylabel('Karten-y [m]')
    axis.set_title('Globale Vollscan-Hypothesen (rein lesend)')
    axis.grid(True, linewidth=0.3, alpha=0.35)
    axis.legend(loc='upper right', fontsize=8)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=15.0)
    parser.add_argument(
        '--output-dir',
        default=str(Path.home() / '.local/share/amadeus/diagnostics'))
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0.0:
        parser.error('--timeout muss positiv und endlich sein.')

    rclpy.init()
    node = Capture()
    try:
        base_to_laser = wait_for_data(node, args.timeout)
        points = scan_points(node.scan_message)
        scorer = map_scorer(node.map_message)
        translation = base_to_laser.transform.translation
        rotation = base_to_laser.transform.rotation
        started = time.monotonic()
        result = search_global_pose(
            scorer, points,
            laser_translation_x=float(translation.x),
            laser_translation_y=float(translation.y),
            laser_yaw_rad=yaw_from_quaternion(rotation))
        elapsed = time.monotonic() - started
        base_endpoints = transform_points(
            select_evenly(points, 720),
            float(translation.x), float(translation.y),
            yaw_from_quaternion(rotation))
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (
            time.strftime('global_scan_%Y%m%dT%H%M%S') + '.png')
        render(output_path, scorer, result, base_endpoints)
        payload = {
            'schema_version': 1,
            'read_only': True,
            'valid_scan_points': result.valid_scan_points,
            'search_seconds': elapsed,
            'best_to_second_score_ratio': result.score_ratio,
            'candidates': [{
                'rank': rank,
                'x_m': candidate.x_m,
                'y_m': candidate.y_m,
                'yaw_deg': math.degrees(candidate.yaw_rad),
                'score': candidate.score,
                'endpoint_within_0_15_m_ratio': (
                    candidate.endpoint_within_0_15_m_ratio),
            } for rank, candidate in enumerate(result.candidates, 1)],
            'output_path': str(output_path),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except RuntimeError as error:
        print(f'ABBRUCH: {error}')
        return 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
