#!/usr/bin/env python3
"""Globale AMCL-Initialisierung und fail-closed Lokalisierungsfreigabe."""

from collections import deque
import json
import math
import time

from geometry_msgs.msg import PoseWithCovarianceStamped
import rclpy
from rclpy._rclpy_pybind11 import RCLError
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
from std_msgs.msg import Bool, String
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformException, TransformListener

from robot_navigation.localization_contract import (
    covariance_hysteresis_limits,
    covariance_quality,
    decode_map_manager_binding,
    decode_semantic_binding,
    initialization_matches_bindings,
    matching_bindings,
    transform_stability_hysteresis_limits,
    transform_window_motion,
    transform_window_stable,
)


class LocalizationGuard(Node):
    def __init__(self):
        super().__init__('localization_guard')
        self.declare_parameter('amcl_pose_topic', '/amcl_pose')
        self.declare_parameter('scan_topic', '/scan_normiert')
        self.declare_parameter(
            'map_manager_status_topic', '/robot_map_manager/status_json')
        self.declare_parameter(
            'semantic_map_status_topic', '/semantic_map/status_json')
        self.declare_parameter('ready_topic', '/localization/ready')
        self.declare_parameter('status_topic', '/localization/status_json')
        self.declare_parameter(
            'global_localization_service', '/reinitialize_global_localization')
        self.declare_parameter('auto_global_localization', True)
        self.declare_parameter('status_timeout_s', 5.0)
        self.declare_parameter('scan_timeout_s', 0.75)
        self.declare_parameter('tf_timeout_s', 1.5)
        self.declare_parameter('maximum_position_stddev_m', 0.20)
        self.declare_parameter('maximum_yaw_stddev_deg', 10.0)
        self.declare_parameter('release_position_stddev_m', 0.30)
        self.declare_parameter('release_yaw_stddev_deg', 15.0)
        self.declare_parameter('stability_window_s', 3.0)
        self.declare_parameter('stability_minimum_samples', 10)
        self.declare_parameter('stability_maximum_translation_m', 0.08)
        self.declare_parameter('stability_maximum_yaw_deg', 5.0)
        self.declare_parameter(
            'stability_release_maximum_translation_m', 0.20)
        self.declare_parameter('stability_release_maximum_yaw_deg', 12.0)
        self.declare_parameter('publish_rate_hz', 5.0)

        self._pose_topic = self._string_parameter('amcl_pose_topic')
        scan_topic = self._string_parameter('scan_topic')
        map_status_topic = self._string_parameter('map_manager_status_topic')
        semantic_status_topic = self._string_parameter(
            'semantic_map_status_topic')
        ready_topic = self._string_parameter('ready_topic')
        status_topic = self._string_parameter('status_topic')
        global_service = self._string_parameter('global_localization_service')
        self._auto_global = bool(
            self.get_parameter('auto_global_localization').value)

        self._status_timeout = self._positive_parameter('status_timeout_s')
        self._scan_timeout = self._positive_parameter('scan_timeout_s')
        self._tf_timeout = self._positive_parameter('tf_timeout_s')
        self._maximum_position_stddev = self._positive_parameter(
            'maximum_position_stddev_m')
        self._maximum_yaw_stddev = math.radians(
            self._positive_parameter('maximum_yaw_stddev_deg'))
        self._release_position_stddev = self._positive_parameter(
            'release_position_stddev_m')
        self._release_yaw_stddev = math.radians(
            self._positive_parameter('release_yaw_stddev_deg'))
        # Konfigurationsfehler schon beim Start erkennen, nicht erst nach der
        # ersten AMCL-Pose.
        covariance_hysteresis_limits(
            False,
            acquire_position_stddev_m=self._maximum_position_stddev,
            acquire_yaw_stddev_rad=self._maximum_yaw_stddev,
            release_position_stddev_m=self._release_position_stddev,
            release_yaw_stddev_rad=self._release_yaw_stddev)
        self._stability_window = self._positive_parameter('stability_window_s')
        self._stability_minimum_samples = int(
            self.get_parameter('stability_minimum_samples').value)
        if self._stability_minimum_samples < 2:
            raise ValueError('stability_minimum_samples muss mindestens 2 sein')
        self._stability_maximum_translation = self._positive_parameter(
            'stability_maximum_translation_m')
        self._stability_maximum_yaw = math.radians(
            self._positive_parameter('stability_maximum_yaw_deg'))
        self._stability_release_maximum_translation = self._positive_parameter(
            'stability_release_maximum_translation_m')
        self._stability_release_maximum_yaw = math.radians(
            self._positive_parameter('stability_release_maximum_yaw_deg'))
        transform_stability_hysteresis_limits(
            False,
            acquire_translation_m=self._stability_maximum_translation,
            acquire_yaw_rad=self._stability_maximum_yaw,
            release_translation_m=self._stability_release_maximum_translation,
            release_yaw_rad=self._stability_release_maximum_yaw)
        publish_rate = self._positive_parameter('publish_rate_hz')

        transient_qos = QoSProfile(depth=1)
        transient_qos.reliability = ReliabilityPolicy.RELIABLE
        transient_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self._ready_publisher = self.create_publisher(Bool, ready_topic, 1)
        self._status_publisher = self.create_publisher(
            String, status_topic, transient_qos)
        self.create_subscription(
            PoseWithCovarianceStamped, self._pose_topic, self._on_pose, 10)
        self.create_subscription(
            LaserScan, scan_topic, self._on_scan, qos_profile_sensor_data)
        self.create_subscription(
            String, map_status_topic, self._on_map_status, transient_qos)
        self.create_subscription(
            String, semantic_status_topic, self._on_semantic_status,
            transient_qos)

        self._global_client = self.create_client(Empty, global_service)
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._map_binding = None
        self._map_error = 'Noch kein Kartenmanager-Status empfangen'
        self._map_received = None
        self._semantic_binding = None
        self._semantic_error = 'Noch kein Semantik-Status empfangen'
        self._semantic_received = None
        self._scan_received = None
        self._scan_valid_rays = 0
        self._pose_received = None
        self._pose_quality = None
        self._pose_error = 'Noch keine AMCL-Pose empfangen'
        self._pose_limit_mode = 'acquire'
        self._pose_position_limit = self._maximum_position_stddev
        self._pose_yaw_limit = self._maximum_yaw_stddev
        self._global_state = 'waiting'
        self._global_generation = 0
        self._global_fingerprint = None
        self._global_request_time = None
        self._tf_samples = deque()
        self._tf_error = 'Noch kein map->odom nach globaler Initialisierung'
        self._tf_stamp_age = None
        self._stability_limit_mode = 'acquire'
        self._stability_translation_limit = self._stability_maximum_translation
        self._stability_yaw_limit = self._stability_maximum_yaw
        self._tf_window_duration = 0.0
        self._tf_window_translation = 0.0
        self._tf_window_yaw = 0.0
        self._last_ready = False

        self.create_timer(1.0 / publish_rate, self._tick)
        self.get_logger().warn(
            'Lokalisierungswaechter aktiv: Fahrt bleibt bis zur globalen '
            'AMCL-Konvergenz gesperrt.')

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

    def _on_map_status(self, message):
        self._map_binding, self._map_error = decode_map_manager_binding(
            message.data)
        self._map_received = time.monotonic()
        self._reset_global_initialization_for_binding_change()

    def _on_semantic_status(self, message):
        self._semantic_binding, self._semantic_error = decode_semantic_binding(
            message.data)
        self._semantic_received = time.monotonic()
        self._reset_global_initialization_for_binding_change()

    def _on_scan(self, message):
        valid = sum(
            1 for value in message.ranges
            if math.isfinite(value)
            and value >= message.range_min
            and value <= message.range_max
        )
        if valid >= 50:
            self._scan_received = time.monotonic()
            self._scan_valid_rays = valid

    def _on_pose(self, message):
        pose = message.pose.pose
        values = (
            pose.position.x, pose.position.y, pose.position.z,
            pose.orientation.x, pose.orientation.y,
            pose.orientation.z, pose.orientation.w,
        )
        if message.header.frame_id != 'map' or not all(
                math.isfinite(value) for value in values):
            self._pose_quality = None
            self._pose_error = 'AMCL-Pose ist ungueltig oder nicht im map-Frame'
            return
        maintaining = self._last_ready is True
        position_limit, yaw_limit = covariance_hysteresis_limits(
            maintaining,
            acquire_position_stddev_m=self._maximum_position_stddev,
            acquire_yaw_stddev_rad=self._maximum_yaw_stddev,
            release_position_stddev_m=self._release_position_stddev,
            release_yaw_stddev_rad=self._release_yaw_stddev)
        self._pose_limit_mode = 'maintain' if maintaining else 'acquire'
        self._pose_position_limit = position_limit
        self._pose_yaw_limit = yaw_limit
        self._pose_quality, self._pose_error = covariance_quality(
            message.pose.covariance,
            maximum_position_stddev_m=position_limit,
            maximum_yaw_stddev_rad=yaw_limit)
        self._pose_received = time.monotonic()

    def _fresh(self, received, timeout, now):
        return (
            received is not None
            and 0.0 <= now - received <= timeout
        )

    def _reset_global_initialization_for_binding_change(self):
        if self._global_fingerprint is None:
            return
        current_fingerprints = {
            binding.fingerprint
            for binding in (self._map_binding, self._semantic_binding)
            if binding is not None
        }
        if not any(
                fingerprint != self._global_fingerprint
                for fingerprint in current_fingerprints):
            return
        self._global_generation += 1
        self._global_state = 'waiting'
        self._global_fingerprint = None
        self._global_request_time = None
        self._pose_received = None
        self._pose_quality = None
        self._pose_error = 'Kartenwechsel verlangt einen neuen Global-Reset'
        self._tf_samples.clear()
        self._tf_error = 'Kartenwechsel verlangt einen neuen Global-Reset'
        self._tf_stamp_age = None
        self._ready_publisher.publish(Bool(data=False))
        self._last_ready = False
        self.get_logger().warn(
            'Kartenfingerabdruck geaendert: globale AMCL-Initialisierung '
            'wird fail-closed wiederholt.')

    def _maybe_request_global_localization(self, now):
        if not self._auto_global or self._global_state != 'waiting':
            return
        prerequisites = (
            self._fresh(self._map_received, self._status_timeout, now)
            and self._fresh(self._semantic_received, self._status_timeout, now)
            and matching_bindings(self._map_binding, self._semantic_binding)
            and self._fresh(self._scan_received, self._scan_timeout, now)
            and self.count_publishers(self._pose_topic) == 1
            and self._global_client.service_is_ready()
        )
        if not prerequisites:
            return
        self._global_state = 'requested'
        self._global_generation += 1
        request_generation = self._global_generation
        self._global_fingerprint = self._map_binding.fingerprint
        request_fingerprint = self._global_fingerprint
        self._global_request_time = now
        self._pose_received = None
        self._pose_quality = None
        self._pose_error = 'Warte auf eine neue AMCL-Pose nach Global-Reset'
        self._tf_samples.clear()
        future = self._global_client.call_async(Empty.Request())
        future.add_done_callback(
            lambda completed: self._on_global_response(
                completed, request_generation, request_fingerprint))
        self.get_logger().warn(
            'AMCL-Partikel wurden global ueber die bestaetigte Karte verteilt.')

    def _on_global_response(self, future, request_generation, fingerprint):
        try:
            future.result()
        except Exception as error:  # pragma: no cover - ROS-Transportfehler
            if (
                    request_generation != self._global_generation
                    or fingerprint != self._global_fingerprint):
                return
            self._global_state = 'failed'
            self._tf_error = f'Global-Lokalisierungsdienst fehlgeschlagen: {error}'
            self.get_logger().error(self._tf_error)
            return
        if (
                request_generation != self._global_generation
                or fingerprint != self._global_fingerprint):
            return
        self._global_state = 'completed'

    def _sample_map_to_odom(self, now):
        if (
                self._global_state != 'completed'
                or self._pose_received is None
                or self._global_request_time is None
                or self._pose_received < self._global_request_time):
            return
        try:
            transform = self._tf_buffer.lookup_transform('map', 'odom', Time())
        except TransformException as error:
            self._tf_error = f'map->odom nicht verfuegbar: {error}'
            return
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        values = (
            translation.x, translation.y,
            rotation.x, rotation.y, rotation.z, rotation.w)
        if not all(math.isfinite(value) for value in values):
            self._tf_error = 'map->odom enthaelt nicht-endliche Werte'
            return
        stamp_ns = (
            int(transform.header.stamp.sec) * 1_000_000_000
            + int(transform.header.stamp.nanosec)
        )
        if stamp_ns <= 0:
            self._tf_error = (
                'map->odom hat keinen dynamischen Zeitstempel; statischer '
                'Platzhalter oder ungueltiger Transform')
            self._tf_stamp_age = None
            return
        ros_now_ns = self.get_clock().now().nanoseconds
        stamp_age = (ros_now_ns - stamp_ns) / 1_000_000_000.0
        # AMCL datiert den Transform um transform_tolerance in die Zukunft.
        # Ein alter Cache oder ein statischer Nullstempel darf aber nie als
        # laufende Lokalisierung gelten.
        if stamp_age > self._tf_timeout or stamp_age < -self._tf_timeout:
            self._tf_error = (
                f'map->odom-Zeitstempel ist unplausibel ({stamp_age:.2f} s)')
            self._tf_stamp_age = stamp_age
            return
        self._tf_stamp_age = stamp_age
        yaw = math.atan2(
            2.0 * (rotation.w * rotation.z + rotation.x * rotation.y),
            1.0 - 2.0 * (rotation.y * rotation.y + rotation.z * rotation.z))
        self._tf_samples.append((now, translation.x, translation.y, yaw))
        cutoff = now - self._stability_window
        while self._tf_samples and self._tf_samples[0][0] < cutoff:
            self._tf_samples.popleft()
        self._tf_error = ''

    def _evaluate(self, now):
        reasons = []
        if not self._fresh(self._map_received, self._status_timeout, now):
            reasons.append('Kartenmanager-Status fehlt oder ist veraltet')
        elif self._map_binding is None:
            reasons.append(self._map_error)
        if not self._fresh(self._semantic_received, self._status_timeout, now):
            reasons.append('Semantik-Status fehlt oder ist veraltet')
        elif self._semantic_binding is None:
            reasons.append(self._semantic_error)
        if not matching_bindings(self._map_binding, self._semantic_binding):
            reasons.append('Metrische und semantische Karte stimmen nicht ueberein')
        if not self._fresh(self._scan_received, self._scan_timeout, now):
            reasons.append('Normalisierter LiDAR-Scan fehlt oder ist veraltet')
        pose_publishers = self.count_publishers(self._pose_topic)
        if pose_publishers != 1:
            reasons.append(
                f'AMCL braucht genau einen Pose-Publisher; gefunden: {pose_publishers}')
        if self._global_state != 'completed':
            reasons.append(
                f'Globale AMCL-Initialisierung ist nicht abgeschlossen '
                f'({self._global_state})')
        elif not initialization_matches_bindings(
                self._map_binding,
                self._semantic_binding,
                self._global_fingerprint):
            reasons.append(
                'Globale AMCL-Initialisierung gehoert nicht zur aktuellen Karte')
        if (
                self._pose_received is None
                or self._global_request_time is None
                or self._pose_received < self._global_request_time):
            reasons.append('AMCL-Pose nach Global-Reset fehlt')
        elif self._pose_error:
            reasons.append(self._pose_error)
        maintaining = self._last_ready is True
        (
            self._stability_translation_limit,
            self._stability_yaw_limit,
        ) = transform_stability_hysteresis_limits(
            maintaining,
            acquire_translation_m=self._stability_maximum_translation,
            acquire_yaw_rad=self._stability_maximum_yaw,
            release_translation_m=self._stability_release_maximum_translation,
            release_yaw_rad=self._stability_release_maximum_yaw)
        self._stability_limit_mode = 'maintain' if maintaining else 'acquire'
        (
            self._tf_window_duration,
            self._tf_window_translation,
            self._tf_window_yaw,
        ) = transform_window_motion(tuple(self._tf_samples))
        stable, stability_reason = transform_window_stable(
            tuple(self._tf_samples),
            minimum_duration_s=self._stability_window * 0.8,
            minimum_samples=self._stability_minimum_samples,
            maximum_translation_m=self._stability_translation_limit,
            maximum_yaw_rad=self._stability_yaw_limit)
        if not stable:
            reasons.append(self._tf_error or stability_reason)
        return not reasons, reasons, pose_publishers

    def _tick(self):
        now = time.monotonic()
        self._maybe_request_global_localization(now)
        self._sample_map_to_odom(now)
        ready, reasons, pose_publishers = self._evaluate(now)
        self._ready_publisher.publish(Bool(data=ready))

        quality = None
        if self._pose_quality is not None:
            quality = {
                'x_stddev_m': self._pose_quality.x_stddev_m,
                'y_stddev_m': self._pose_quality.y_stddev_m,
                'yaw_stddev_deg': math.degrees(
                    self._pose_quality.yaw_stddev_rad),
            }
        payload = {
            'schema_version': 1,
            'ready': ready,
            'state': 'localized' if ready else 'converging',
            'reasons': reasons,
            'map_fingerprint': (
                None if self._map_binding is None
                else self._map_binding.fingerprint),
            'global_initialization': self._global_state,
            'global_initialization_fingerprint': self._global_fingerprint,
            'scan_valid_rays': self._scan_valid_rays,
            'amcl_pose_publishers': pose_publishers,
            'covariance': quality,
            'amcl_pose_age_seconds': (
                None if self._pose_received is None
                else max(0.0, now - self._pose_received)),
            'covariance_limits': {
                'mode': self._pose_limit_mode,
                'position_stddev_m': self._pose_position_limit,
                'yaw_stddev_deg': math.degrees(self._pose_yaw_limit),
            },
            'map_to_odom_samples': len(self._tf_samples),
            'map_to_odom_stamp_age_seconds': self._tf_stamp_age,
            'map_to_odom_window': {
                'duration_seconds': self._tf_window_duration,
                'translation_m': self._tf_window_translation,
                'yaw_deg': math.degrees(self._tf_window_yaw),
            },
            'transform_stability_limits': {
                'mode': self._stability_limit_mode,
                'translation_m': self._stability_translation_limit,
                'yaw_deg': math.degrees(self._stability_yaw_limit),
            },
            'time': time.time(),
        }
        self._status_publisher.publish(
            String(data=json.dumps(payload, ensure_ascii=False)))
        if ready != self._last_ready:
            self.get_logger().warn(
                'Lokalisierung FREIGEGEBEN'
                if ready else (
                    'Lokalisierung GESPERRT: '
                    + '; '.join(reasons)))
            self._last_ready = ready


def main(args=None):
    rclpy.init(args=args)
    node = LocalizationGuard()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            try:
                node._ready_publisher.publish(Bool(data=False))
            except RCLError:
                pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
