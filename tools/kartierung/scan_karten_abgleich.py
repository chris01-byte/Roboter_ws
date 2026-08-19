#!/usr/bin/env python3
"""Legt den aktuellen LiDAR-Scan rein lesend ueber die geladene Nav2-Karte.

Das Diagnosebild bleibt lokal ausserhalb des Repositories. Das Werkzeug
abonniert nur ``/map`` und ``/scan_normiert`` und liest TF; es besitzt bewusst
keinen Publisher und kann den Roboter nicht bewegen.
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
import rclpy  # noqa: E402
from matplotlib.transforms import Affine2D  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.duration import Duration  # noqa: E402
from rclpy.node import Node  # noqa: E402
from rclpy.qos import (  # noqa: E402
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.time import Time  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from sensor_msgs.msg import LaserScan  # noqa: E402
from tf2_ros import Buffer, TransformException, TransformListener  # noqa: E402


def yaw_from_quaternion(quaternion):
    return math.atan2(
        2.0 * (quaternion.w * quaternion.z
               + quaternion.x * quaternion.y),
        1.0 - 2.0 * (quaternion.y * quaternion.y
                     + quaternion.z * quaternion.z))


class ScanMapCapture(Node):
    def __init__(self):
        super().__init__('scan_karten_abgleich')
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


def wait_for_capture(node, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_transform_error = None
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.map_message is None or node.scan_message is None:
            continue
        try:
            map_to_laser = node.tf_buffer.lookup_transform(
                node.map_message.header.frame_id,
                node.scan_message.header.frame_id,
                Time(), timeout=Duration(seconds=0.5))
            map_to_base = node.tf_buffer.lookup_transform(
                node.map_message.header.frame_id, 'base_link', Time(),
                timeout=Duration(seconds=0.5))
            return map_to_laser, map_to_base
        except TransformException as error:
            last_transform_error = str(error)
    raise RuntimeError(
        'Diagnosedaten unvollstaendig: '
        f'Karte={node.map_message is not None}, '
        f'Scan={node.scan_message is not None}, '
        f'TF-Fehler={last_transform_error!r}.')


def scan_points(scan):
    ranges = np.asarray(scan.ranges, dtype=np.float64)
    angles = scan.angle_min + np.arange(ranges.size) * scan.angle_increment
    valid = (
        np.isfinite(ranges)
        & (ranges >= max(float(scan.range_min), 0.02))
        & (ranges <= float(scan.range_max)))
    ranges = ranges[valid]
    angles = angles[valid]
    return np.column_stack((ranges * np.cos(angles), ranges * np.sin(angles)))


def transform_points(points, transform):
    translation = transform.transform.translation
    yaw = yaw_from_quaternion(transform.transform.rotation)
    cosine, sine = math.cos(yaw), math.sin(yaw)
    x = translation.x + cosine * points[:, 0] - sine * points[:, 1]
    y = translation.y + sine * points[:, 0] + cosine * points[:, 1]
    return np.column_stack((x, y))


def world_to_grid(points, map_message):
    origin = map_message.info.origin
    origin_yaw = yaw_from_quaternion(origin.orientation)
    delta_x = points[:, 0] - origin.position.x
    delta_y = points[:, 1] - origin.position.y
    cosine, sine = math.cos(origin_yaw), math.sin(origin_yaw)
    local_x = cosine * delta_x + sine * delta_y
    local_y = -sine * delta_x + cosine * delta_y
    resolution = float(map_message.info.resolution)
    columns = np.floor(local_x / resolution).astype(np.int64)
    rows = np.floor(local_y / resolution).astype(np.int64)
    inside = (
        (columns >= 0) & (columns < int(map_message.info.width))
        & (rows >= 0) & (rows < int(map_message.info.height)))
    return rows, columns, inside


def alignment_metrics(map_message, points):
    height = int(map_message.info.height)
    width = int(map_message.info.width)
    grid = np.asarray(map_message.data, dtype=np.int16).reshape(height, width)
    occupied = grid >= 65
    if not occupied.any():
        raise RuntimeError('Die geladene Karte enthaelt keine belegten Zellen.')
    distances = distance_transform_edt(~occupied) * map_message.info.resolution
    rows, columns, inside = world_to_grid(points, map_message)
    endpoint_distances = np.full(points.shape[0], np.nan, dtype=np.float64)
    endpoint_distances[inside] = distances[rows[inside], columns[inside]]
    usable = endpoint_distances[np.isfinite(endpoint_distances)]
    if usable.size == 0:
        raise RuntimeError('Kein LiDAR-Endpunkt liegt innerhalb der Karte.')
    metrics = {
        'valid_scan_points': int(points.shape[0]),
        'points_inside_map': int(usable.size),
        'inside_map_ratio': float(usable.size / points.shape[0]),
        'within_0_09_m_ratio': float(np.mean(usable <= 0.09)),
        'within_0_15_m_ratio': float(np.mean(usable <= 0.15)),
        'within_0_30_m_ratio': float(np.mean(usable <= 0.30)),
        'median_wall_distance_m': float(np.median(usable)),
        'p90_wall_distance_m': float(np.quantile(usable, 0.90)),
    }
    return grid, endpoint_distances, metrics


def render(output_path, map_message, grid, points, endpoint_distances,
           map_to_base, metrics):
    display = np.empty((*grid.shape, 3), dtype=np.float32)
    display[grid < 0] = (0.72, 0.72, 0.72)
    display[(grid >= 0) & (grid < 65)] = (1.0, 1.0, 1.0)
    display[grid >= 65] = (0.08, 0.08, 0.08)

    origin = map_message.info.origin
    resolution = float(map_message.info.resolution)
    width_m = map_message.info.width * resolution
    height_m = map_message.info.height * resolution
    origin_yaw = yaw_from_quaternion(origin.orientation)

    figure, axis = plt.subplots(figsize=(8, 9), constrained_layout=True)
    image = axis.imshow(
        display, origin='lower', interpolation='nearest',
        extent=(origin.position.x, origin.position.x + width_m,
                origin.position.y, origin.position.y + height_m))
    if abs(origin_yaw) > 1e-9:
        image.set_transform(
            Affine2D().rotate_around(
                origin.position.x, origin.position.y, origin_yaw)
            + axis.transData)

    near = np.isfinite(endpoint_distances) & (endpoint_distances <= 0.15)
    far = np.isfinite(endpoint_distances) & ~near
    outside = ~np.isfinite(endpoint_distances)
    axis.scatter(points[outside, 0], points[outside, 1], s=2,
                 color='#7b61ff', alpha=0.28, label='Scan ausserhalb Karte')
    axis.scatter(points[far, 0], points[far, 1], s=3,
                 color='#f28e2b', alpha=0.55, label='Scan > 15 cm zur Wand')
    axis.scatter(points[near, 0], points[near, 1], s=4,
                 color='#1f9d55', alpha=0.75, label='Scan <= 15 cm zur Wand')

    base = map_to_base.transform.translation
    base_yaw = yaw_from_quaternion(map_to_base.transform.rotation)
    axis.scatter([base.x], [base.y], s=90, color='#d62728', zorder=5,
                 label='AMCL-Roboterpose')
    axis.arrow(base.x, base.y, 0.45 * math.cos(base_yaw),
               0.45 * math.sin(base_yaw), width=0.025,
               head_width=0.14, head_length=0.16,
               color='#d62728', length_includes_head=True, zorder=5)

    axis.set_aspect('equal', adjustable='box')
    axis.set_xlabel('Karten-x [m]')
    axis.set_ylabel('Karten-y [m]')
    axis.set_title(
        'LiDAR/Karten-Abgleich (rein lesend)\n'
        f"innerhalb 15 cm: {metrics['within_0_15_m_ratio'] * 100:.1f} %, "
        f"Median: {metrics['median_wall_distance_m']:.3f} m")
    axis.grid(True, linewidth=0.3, alpha=0.35)
    axis.legend(loc='upper right', fontsize=8)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=10.0)
    parser.add_argument(
        '--output-dir',
        default=str(Path.home() / '.local/share/amadeus/diagnostics'))
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0.0:
        parser.error('--timeout muss positiv und endlich sein.')

    rclpy.init()
    node = ScanMapCapture()
    try:
        map_to_laser, map_to_base = wait_for_capture(node, args.timeout)
        points = transform_points(scan_points(node.scan_message), map_to_laser)
        grid, endpoint_distances, metrics = alignment_metrics(
            node.map_message, points)
        base = map_to_base.transform.translation
        metrics['robot_pose'] = {
            'x_m': float(base.x),
            'y_m': float(base.y),
            'yaw_deg': math.degrees(
                yaw_from_quaternion(map_to_base.transform.rotation)),
        }
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / (
            time.strftime('scan_map_%Y%m%dT%H%M%S') + '.png')
        render(output_path, node.map_message, grid, points,
               endpoint_distances, map_to_base, metrics)
        metrics['output_path'] = str(output_path)
        print(json.dumps(metrics, indent=2, sort_keys=True))
        return 0
    except RuntimeError as error:
        print(f'ABBRUCH: {error}')
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
