#!/usr/bin/env python3
"""Motorloser globaler Vollscan-Abgleich als AMCL-Initialisierungsstufe."""

import json
import math
import time

from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid
import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from robot_navigation.global_scan_matcher import (
    MapScorer,
    result_is_accepted,
    scan_candidates_consistent,
    search_global_pose,
)
from robot_navigation.localization_contract import (
    decode_global_initialization_target,
)


def yaw_from_quaternion(quaternion) -> float:
    return math.atan2(
        2.0 * (
            quaternion.w * quaternion.z
            + quaternion.x * quaternion.y),
        1.0 - 2.0 * (
            quaternion.y * quaternion.y
            + quaternion.z * quaternion.z))


def scan_points(message: LaserScan) -> np.ndarray:
    ranges = np.asarray(message.ranges, dtype=np.float64)
    angles = (
        float(message.angle_min)
        + np.arange(ranges.size, dtype=np.float64)
        * float(message.angle_increment))
    valid = (
        np.isfinite(ranges)
        & (ranges >= float(message.range_min))
        & (ranges <= float(message.range_max)))
    return np.column_stack((
        ranges[valid] * np.cos(angles[valid]),
        ranges[valid] * np.sin(angles[valid])))


class GlobalScanLocalizer(Node):
    """Setzt ``/initialpose`` nur nach einem eindeutigen Kartenabgleich."""

    def __init__(self):
        super().__init__('global_scan_localizer')
        self.declare_parameter('map_topic', '/map')
        self.declare_parameter('scan_topic', '/scan_normiert')
        self.declare_parameter(
            'guard_status_topic', '/localization/status_json')
        self.declare_parameter(
            'match_status_topic', '/localization/global_scan_match_json')
        self.declare_parameter('initialpose_topic', '/initialpose')
        self.declare_parameter('scan_timeout_s', 0.75)
        self.declare_parameter('minimum_scan_points', 400)
        self.declare_parameter('minimum_score', 0.85)
        self.declare_parameter('minimum_endpoint_ratio', 0.85)
        self.declare_parameter('minimum_score_ratio', 1.15)
        self.declare_parameter('initial_position_stddev_m', 0.15)
        self.declare_parameter('initial_yaw_stddev_deg', 5.0)
        self.declare_parameter('required_consistent_matches', 2)
        self.declare_parameter('consensus_maximum_position_error_m', 0.20)
        self.declare_parameter('consensus_maximum_yaw_error_deg', 8.0)
        self.declare_parameter('maximum_attempts_per_reset', 5)
        self.declare_parameter('retry_interval_s', 2.0)
        self.declare_parameter('publish_rate_hz', 5.0)

        map_topic = self._string_parameter('map_topic')
        scan_topic = self._string_parameter('scan_topic')
        guard_topic = self._string_parameter('guard_status_topic')
        status_topic = self._string_parameter('match_status_topic')
        initialpose_topic = self._string_parameter('initialpose_topic')
        self._scan_timeout = self._positive_parameter('scan_timeout_s')
        self._minimum_scan_points = int(
            self.get_parameter('minimum_scan_points').value)
        if self._minimum_scan_points < 50:
            raise ValueError('minimum_scan_points muss mindestens 50 sein')
        self._minimum_score = self._ratio_parameter('minimum_score')
        self._minimum_endpoint_ratio = self._ratio_parameter(
            'minimum_endpoint_ratio')
        self._minimum_score_ratio = self._positive_parameter(
            'minimum_score_ratio')
        if self._minimum_score_ratio <= 1.0:
            raise ValueError('minimum_score_ratio muss groesser als 1 sein')
        self._position_stddev = self._positive_parameter(
            'initial_position_stddev_m')
        self._yaw_stddev = math.radians(
            self._positive_parameter('initial_yaw_stddev_deg'))
        self._required_consistent_matches = int(
            self.get_parameter('required_consistent_matches').value)
        if self._required_consistent_matches < 2:
            raise ValueError('required_consistent_matches muss mindestens 2 sein')
        self._consensus_maximum_position_error = self._positive_parameter(
            'consensus_maximum_position_error_m')
        self._consensus_maximum_yaw_error = math.radians(
            self._positive_parameter('consensus_maximum_yaw_error_deg'))
        self._maximum_attempts = int(
            self.get_parameter('maximum_attempts_per_reset').value)
        if (
                self._maximum_attempts < self._required_consistent_matches
                or self._maximum_attempts > 10):
            raise ValueError(
                'maximum_attempts_per_reset muss mindestens so gross wie '
                'required_consistent_matches und hoechstens 10 sein')
        self._retry_interval = self._positive_parameter('retry_interval_s')
        publish_rate = self._positive_parameter('publish_rate_hz')

        transient_qos = QoSProfile(depth=1)
        transient_qos.reliability = ReliabilityPolicy.RELIABLE
        transient_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._status_publisher = self.create_publisher(
            String, status_topic, transient_qos)
        self._initialpose_publisher = self.create_publisher(
            PoseWithCovarianceStamped, initialpose_topic, 10)
        self.create_subscription(
            OccupancyGrid, map_topic, self._on_map, transient_qos)
        self.create_subscription(
            LaserScan, scan_topic, self._on_scan, qos_profile_sensor_data)
        self.create_subscription(
            String, guard_topic, self._on_guard_status, transient_qos)

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._map_message = None
        self._scan_message = None
        self._scan_received = None
        self._target = None
        self._attempted_scan_stamp = None
        self._attempts = 0
        self._last_attempt = None
        self._state = 'waiting'
        self._reason = 'Warte auf kartenfesten Vollscan-Auftrag'
        self._accepted_payload = None
        self._latest_result = None
        self._consensus_candidate = None
        self._consistent_matches = 0
        self.create_timer(1.0 / publish_rate, self._tick)
        self.get_logger().warn(
            'Globaler Vollscan-Abgleich aktiv: keine Fahrbefehle, '
            'AMCL-Freigabe nur nach eindeutigem Kartentreffer.')

    def _string_parameter(self, name):
        value = self.get_parameter(name).value
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{name} muss eine nichtleere Zeichenkette sein')
        return value.strip()

    def _positive_parameter(self, name):
        value = self.get_parameter(name).value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} muss eine Zahl sein')
        value = float(value)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f'{name} muss endlich und > 0 sein')
        return value

    def _ratio_parameter(self, name):
        value = self._positive_parameter(name)
        if value > 1.0:
            raise ValueError(f'{name} darf hoechstens 1 sein')
        return value

    def _on_map(self, message):
        self._map_message = message

    def _on_scan(self, message):
        self._scan_message = message
        self._scan_received = time.monotonic()

    def _on_guard_status(self, message):
        decoded, _ = decode_global_initialization_target(message.data)
        target = None if decoded is None else (
            decoded.fingerprint,
            decoded.generation,
            decoded.initialization_id)
        if target == self._target:
            return
        self._target = target
        self._attempted_scan_stamp = None
        self._attempts = 0
        self._last_attempt = None
        self._accepted_payload = None
        self._latest_result = None
        self._consensus_candidate = None
        self._consistent_matches = 0
        self._state = 'waiting'
        self._reason = (
            'Warte auf kartenfesten Vollscan-Auftrag'
            if target is None else 'Warte auf frischen Vollscan')

    def _scan_stamp(self):
        if self._scan_message is None:
            return None
        stamp = self._scan_message.header.stamp
        return (int(stamp.sec), int(stamp.nanosec))

    def _map_scorer(self):
        message = self._map_message
        if message is None or message.header.frame_id != 'map':
            raise RuntimeError('Gueltige Karte im map-Frame fehlt')
        width = int(message.info.width)
        height = int(message.info.height)
        if width <= 0 or height <= 0 or len(message.data) != width * height:
            raise RuntimeError('Kartenabmessungen oder Kartendaten sind ungueltig')
        grid = np.asarray(message.data, dtype=np.int16).reshape(height, width)
        origin = message.info.origin
        return MapScorer(
            grid,
            float(message.info.resolution),
            float(origin.position.x),
            float(origin.position.y),
            yaw_from_quaternion(origin.orientation))

    def _attempt_match(self, now):
        if self._target is None or self._accepted_payload is not None:
            return
        if self._attempts >= self._maximum_attempts:
            self._state = 'rejected'
            self._reason = (
                f'Kein eindeutiger Treffer nach {self._attempts} Versuchen')
            return
        if (
                self._last_attempt is not None
                and now - self._last_attempt < self._retry_interval):
            return
        if (
                self._scan_received is None
                or now - self._scan_received > self._scan_timeout):
            self._state = 'waiting'
            self._reason = 'Frischer normalisierter LiDAR-Scan fehlt'
            return
        if self._map_message is None:
            self._state = 'waiting'
            self._reason = 'Geladene Karte fehlt noch'
            return
        stamp = self._scan_stamp()
        if stamp == self._attempted_scan_stamp:
            return
        self._attempted_scan_stamp = stamp
        self._attempts += 1
        self._last_attempt = now
        self._state = 'searching'
        self._reason = f'Bewerte Vollscan, Versuch {self._attempts}'
        self._publish_status()
        started = time.monotonic()
        try:
            points = scan_points(self._scan_message)
            if points.shape[0] < self._minimum_scan_points:
                raise RuntimeError(
                    f'Nur {points.shape[0]} gueltige Scanpunkte; '
                    f'mindestens {self._minimum_scan_points} erforderlich')
            transform = self._tf_buffer.lookup_transform(
                'base_link', self._scan_message.header.frame_id, Time(),
                timeout=Duration(seconds=0.5))
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            scorer = self._map_scorer()
            result = search_global_pose(
                scorer, points,
                laser_translation_x=float(translation.x),
                laser_translation_y=float(translation.y),
                laser_yaw_rad=yaw_from_quaternion(rotation))
        except (RuntimeError, ValueError, TransformException) as error:
            self._state = 'rejected'
            self._reason = str(error)
            self.get_logger().error(
                f'Globaler Vollscan-Abgleich fehlgeschlagen: {error}')
            return

        elapsed = time.monotonic() - started
        self._latest_result = result
        accepted, reasons = result_is_accepted(
            result,
            minimum_score=self._minimum_score,
            minimum_endpoint_ratio=self._minimum_endpoint_ratio,
            minimum_score_ratio=self._minimum_score_ratio)
        if not accepted:
            self._state = 'rejected'
            self._reason = '; '.join(reasons)
            self.get_logger().warn(
                'Globaler Vollscan-Treffer abgelehnt: ' + self._reason)
            return

        best = result.best
        if self._consensus_candidate is None:
            self._consensus_candidate = best
            self._consistent_matches = 1
            self._state = 'waiting'
            self._reason = (
                'Erster gueltiger Treffer; warte auf unabhaengige '
                'Vollscan-Bestaetigung')
            self.get_logger().warn(
                'Erster Vollscan-Treffer noch nicht freigegeben: '
                f'x={best.x_m:.3f} m, y={best.y_m:.3f} m, '
                f'yaw={math.degrees(best.yaw_rad):.1f} Grad. Warte auf '
                'zweiten konsistenten Scan.')
            return
        if not scan_candidates_consistent(
                self._consensus_candidate, best,
                maximum_position_error_m=(
                    self._consensus_maximum_position_error),
                maximum_yaw_error_rad=self._consensus_maximum_yaw_error):
            previous = self._consensus_candidate
            self._consensus_candidate = best
            self._consistent_matches = 1
            self._state = 'waiting'
            self._reason = (
                'Vollscan-Hypothesen widersprechen sich; neuer '
                'Konsensversuch erforderlich')
            self.get_logger().warn(
                'Vollscan-Konsens verworfen: vorher '
                f'({previous.x_m:.3f}, {previous.y_m:.3f}, '
                f'{math.degrees(previous.yaw_rad):.1f} Grad), jetzt '
                f'({best.x_m:.3f}, {best.y_m:.3f}, '
                f'{math.degrees(best.yaw_rad):.1f} Grad).')
            return
        self._consistent_matches += 1
        self._consensus_candidate = best
        if self._consistent_matches < self._required_consistent_matches:
            self._state = 'waiting'
            self._reason = (
                f'{self._consistent_matches}/'
                f'{self._required_consistent_matches} konsistente Treffer')
            return

        pose = PoseWithCovarianceStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = 'map'
        pose.pose.pose.position.x = best.x_m
        pose.pose.pose.position.y = best.y_m
        pose.pose.pose.orientation.z = math.sin(best.yaw_rad / 2.0)
        pose.pose.pose.orientation.w = math.cos(best.yaw_rad / 2.0)
        pose.pose.covariance[0] = self._position_stddev ** 2
        pose.pose.covariance[7] = self._position_stddev ** 2
        pose.pose.covariance[35] = self._yaw_stddev ** 2
        self._initialpose_publisher.publish(pose)

        fingerprint, generation, request_id = self._target
        self._accepted_payload = {
            'schema_version': 1,
            'ok': True,
            'state': 'accepted',
            'map_fingerprint': fingerprint,
            'global_initialization_generation': generation,
            'global_initialization_id': request_id,
            'pose': {
                'x_m': best.x_m,
                'y_m': best.y_m,
                'yaw_rad': best.yaw_rad,
            },
            'score': best.score,
            'endpoint_within_0_15_m_ratio': (
                best.endpoint_within_0_15_m_ratio),
            'score_ratio': result.score_ratio,
            'valid_scan_points': result.valid_scan_points,
            'search_seconds': elapsed,
            'attempt': self._attempts,
            'consistent_matches': self._consistent_matches,
        }
        self._state = 'accepted'
        self._reason = 'Eindeutiger globaler Vollscan-Treffer'
        self.get_logger().warn(
            'Globaler Vollscan-Treffer akzeptiert und an AMCL uebergeben: '
            f'x={best.x_m:.3f} m, y={best.y_m:.3f} m, '
            f'yaw={math.degrees(best.yaw_rad):.1f} Grad, '
            f'Score={best.score:.3f}, Abstand={result.score_ratio:.3f}.')

    def _publish_status(self):
        if self._accepted_payload is not None:
            payload = dict(self._accepted_payload)
        else:
            payload = {
                'schema_version': 1,
                'ok': False,
                'state': self._state,
                'reason': self._reason,
                'attempt': self._attempts,
                'consistent_matches': self._consistent_matches,
            }
            if self._target is not None:
                payload.update({
                    'map_fingerprint': self._target[0],
                    'global_initialization_generation': self._target[1],
                    'global_initialization_id': self._target[2],
                })
            if self._latest_result is not None:
                payload.update({
                    'score': self._latest_result.best.score,
                    'endpoint_within_0_15_m_ratio': (
                        self._latest_result.best.endpoint_within_0_15_m_ratio),
                    'score_ratio': self._latest_result.score_ratio,
                })
        payload['time'] = time.time()
        self._status_publisher.publish(
            String(data=json.dumps(payload, ensure_ascii=False)))

    def _tick(self):
        now = time.monotonic()
        self._attempt_match(now)
        self._publish_status()


def main(args=None):
    rclpy.init(args=args)
    node = GlobalScanLocalizer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
