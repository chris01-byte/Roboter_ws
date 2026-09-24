#!/usr/bin/env python3
"""Fail-closed command gate between Nav2 and the velocity smoother."""

import json
import math
import struct
import time

import rclpy
from rclpy.time import Time
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool, String
from sensor_msgs.msg import LaserScan, PointCloud2
from robot_interfaces.msg import NearFieldStatus
from rclpy.qos import (
    QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy,
    qos_profile_sensor_data,
)
from tf2_ros import Buffer, TransformException, TransformListener


AUTHORIZED_PHASES = {'nav2_ziel_senden', 'fahre_zum_raum'}
AUTHORIZED_EXPLORE_PHASES = {'Explore'}


def room_motion_authorized(status):
    """Return True only for an explicitly running go_to_room mission."""
    if not isinstance(status, dict):
        return False
    command = status.get('active_command')
    return (
        status.get('state') == 'running'
        and status.get('phase') in AUTHORIZED_PHASES
        and isinstance(command, dict)
        and command.get('type') == 'go_to_room'
    )


def explore_motion_authorized(status, enabled):
    """Allow exploration only behind the explicit mapping opt-in."""
    if enabled is not True or not isinstance(status, dict):
        return False
    command = status.get('active_command')
    return (
        status.get('state') == 'running'
        and status.get('phase') in AUTHORIZED_EXPLORE_PHASES
        and isinstance(command, dict)
        and command.get('type') == 'explore'
    )


def explore_health_authorized(
        enabled, map_at, scan_at, left_at, right_at, odom_at, now,
        map_timeout_s, sensor_timeout_s, odom_timeout_s,
        allow_stale_map_for_scan=False):
    """Require fresh mapping, LiDAR, both VL53 streams and odometry."""
    values = (
        map_at, scan_at, left_at, right_at, odom_at, now,
        map_timeout_s, sensor_timeout_s, odom_timeout_s)
    if enabled is not True or not all(
            value is not None and math.isfinite(value) for value in values):
        return False
    if map_timeout_s <= 0.0 or sensor_timeout_s <= 0.0 or odom_timeout_s <= 0.0:
        return False
    return (
        (allow_stale_map_for_scan or 0.0 <= now - map_at <= map_timeout_s)
        and now >= map_at
        and 0.0 <= now - scan_at <= sensor_timeout_s
        and 0.0 <= now - left_at <= sensor_timeout_s
        and 0.0 <= now - right_at <= sensor_timeout_s
        and 0.0 <= now - odom_at <= odom_timeout_s
    )


def explore_scan_values_valid(values, max_angular_speed):
    """Allow only a bounded in-place scan on the dedicated input."""
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        return False
    if not math.isfinite(max_angular_speed) or max_angular_speed <= 0.0:
        return False
    linear_x, linear_y, linear_z, angular_x, angular_y, angular_z = values
    return (
        abs(linear_x) <= 1e-9
        and abs(linear_y) <= 1e-9
        and abs(linear_z) <= 1e-9
        and abs(angular_x) <= 1e-9
        and abs(angular_y) <= 1e-9
        and abs(angular_z) <= max_angular_speed
    )


def explore_direct_values_valid(
        values, max_linear_speed, max_angular_speed):
    """Allow only bounded forward motion with a small steering correction."""
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        return False
    if (
            not math.isfinite(max_linear_speed)
            or max_linear_speed <= 0.0
            or not math.isfinite(max_angular_speed)
            or max_angular_speed <= 0.0):
        return False
    linear_x, linear_y, linear_z, angular_x, angular_y, angular_z = values
    return (
        -1e-9 <= linear_x <= max_linear_speed
        and abs(linear_y) <= 1e-9
        and abs(linear_z) <= 1e-9
        and abs(angular_x) <= 1e-9
        and abs(angular_y) <= 1e-9
        and abs(angular_z) <= max_angular_speed
    )


def localization_motion_authorized(
        required, ready, received_at, now, timeout_s):
    """Fail closed when a required localization signal is false or stale."""
    if not required:
        return True
    return (
        ready is True
        and received_at is not None
        and math.isfinite(received_at)
        and math.isfinite(now)
        and math.isfinite(timeout_s)
        and timeout_s > 0.0
        and 0.0 <= now - received_at <= timeout_s
    )


def estop_motion_authorized(clear, received_at, now, timeout_s):
    """Require a fresh explicit clear signal for every gate output."""
    return (
        clear is True
        and received_at is not None
        and all(math.isfinite(value) for value in (
            received_at, now, timeout_s))
        and timeout_s > 0.0
        and 0.0 <= now - received_at <= timeout_s
    )


def transform_motion_authorized(stamp_ns, now_ns, timeout_s):
    """A connected map-to-base transform must describe a recent pose."""
    return (
        isinstance(stamp_ns, int)
        and stamp_ns > 0
        and isinstance(now_ns, int)
        and math.isfinite(timeout_s)
        and timeout_s > 0.0
        and 0 <= now_ns - stamp_ns <= int(timeout_s * 1_000_000_000)
    )


def localization_search_authorized(
        enabled, ready, ever_ready, localization_received_at,
        command_received_at, search_started_at, odom_received_at,
        distance_m, now, localization_timeout_s, command_timeout_s,
        odom_timeout_s, max_duration_s, max_distance_m):
    """Allow only a fresh, explicitly enabled, pre-fix search window."""
    times = (localization_received_at, command_received_at,
             search_started_at, odom_received_at, distance_m, now)
    return (
        enabled is True
        and ready is False
        and ever_ready is False
        and all(value is not None and math.isfinite(value) for value in times)
        and math.isfinite(localization_timeout_s)
        and math.isfinite(command_timeout_s)
        and math.isfinite(odom_timeout_s)
        and math.isfinite(max_duration_s)
        and math.isfinite(max_distance_m)
        and localization_timeout_s > 0.0
        and command_timeout_s > 0.0
        and odom_timeout_s > 0.0
        and max_duration_s > 0.0
        and max_distance_m > 0.0
        and 0.0 <= now - localization_received_at <= localization_timeout_s
        and 0.0 <= now - command_received_at <= command_timeout_s
        and 0.0 <= now - odom_received_at <= odom_timeout_s
        and 0.0 <= now - search_started_at <= max_duration_s
        and 0.0 <= distance_m <= max_distance_m
    )


def localization_search_values_valid(
        values, max_linear_speed, max_angular_speed):
    """Search commands are finite, forward-only and conservatively bounded."""
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        return False
    if (not math.isfinite(max_linear_speed) or max_linear_speed <= 0.0
            or not math.isfinite(max_angular_speed)
            or max_angular_speed <= 0.0):
        return False
    linear_x, linear_y, linear_z, angular_x, angular_y, angular_z = values
    return (
        -1e-9 <= linear_x <= max_linear_speed
        and abs(linear_y) <= 1e-9
        and abs(linear_z) <= 1e-9
        and abs(angular_x) <= 1e-9
        and abs(angular_y) <= 1e-9
        and abs(angular_z) <= max_angular_speed
    )


class CmdVelMissionGate(Node):
    def __init__(self):
        super().__init__('cmd_vel_mission_gate')
        self.declare_parameter('input_topic', '/cmd_vel_nav_raw')
        self.declare_parameter('output_topic', '/cmd_vel_nav')
        self.declare_parameter(
            'mission_status_topic', '/mission_manager/status_json')
        self.declare_parameter('status_timeout_s', 1.0)
        self.declare_parameter('command_timeout_s', 0.25)
        self.declare_parameter('require_localization', True)
        self.declare_parameter('allow_explore_mission', False)
        self.declare_parameter(
            'explore_scan_command_topic', '/cmd_vel_explore_scan_raw')
        self.declare_parameter('explore_scan_max_angular', 0.15)
        self.declare_parameter(
            'explore_direct_command_topic', '/cmd_vel_explore_direct_raw')
        self.declare_parameter('explore_direct_max_linear', 0.08)
        # Der reale Schwellenlauf benoetigt bis 0.10 rad/s Gegenlenkung. Bei
        # 0.08 m/s bleiben damit beide Antriebsraeder vorwaerts gerichtet.
        self.declare_parameter('explore_direct_max_angular', 0.10)
        self.declare_parameter('explore_map_topic', '/map')
        self.declare_parameter('explore_scan_topic', '/scan_normiert')
        self.declare_parameter(
            'explore_vl53_left_topic', '/near_field/left/points')
        self.declare_parameter(
            'explore_vl53_right_topic', '/near_field/right/points')
        self.declare_parameter(
            'near_field_status_topic', '/near_field/status')
        self.declare_parameter('explore_map_timeout_s', 5.0)
        self.declare_parameter('explore_sensor_timeout_s', 0.8)
        self.declare_parameter('explore_odom_timeout_s', 0.8)
        self.declare_parameter(
            'localization_ready_topic', '/localization/ready')
        self.declare_parameter('localization_timeout_s', 1.0)
        self.declare_parameter('allow_localization_search', False)
        self.declare_parameter(
            'localization_search_input_topic', '/cmd_vel_localization_raw')
        self.declare_parameter('localization_search_max_angular', 0.15)
        self.declare_parameter('localization_search_max_linear', 0.04)
        self.declare_parameter('localization_search_max_duration_s', 110.0)
        self.declare_parameter('localization_search_max_distance_m', 0.35)
        self.declare_parameter('localization_search_odom_topic', '/odom')
        self.declare_parameter('localization_search_odom_timeout_s', 0.5)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('estop_topic', '/safety/estop')
        self.declare_parameter('estop_timeout_s', 1.0)
        self.declare_parameter('global_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('motion_map_tf_timeout_s', 0.8)
        self.declare_parameter('motion_base_tf_timeout_s', 0.2)

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        status_topic = self.get_parameter('mission_status_topic').value
        localization_topic = self.get_parameter(
            'localization_ready_topic').value
        search_topic = self.get_parameter(
            'localization_search_input_topic').value
        search_odom_topic = self.get_parameter(
            'localization_search_odom_topic').value
        self._require_localization = bool(
            self.get_parameter('require_localization').value)
        self._allow_explore = bool(
            self.get_parameter('allow_explore_mission').value)
        self._explore_scan_max_angular = float(
            self.get_parameter('explore_scan_max_angular').value)
        self._explore_direct_max_linear = float(
            self.get_parameter('explore_direct_max_linear').value)
        self._explore_direct_max_angular = float(
            self.get_parameter('explore_direct_max_angular').value)
        self._allow_localization_search = bool(
            self.get_parameter('allow_localization_search').value)
        rate_hz = float(self.get_parameter('publish_rate_hz').value)
        if not math.isfinite(rate_hz) or rate_hz <= 0.0:
            raise ValueError('publish_rate_hz muss endlich und > 0 sein')

        self._status_timeout = float(
            self.get_parameter('status_timeout_s').value)
        self._command_timeout = float(
            self.get_parameter('command_timeout_s').value)
        self._localization_timeout = float(
            self.get_parameter('localization_timeout_s').value)
        self._explore_map_timeout = float(
            self.get_parameter('explore_map_timeout_s').value)
        self._explore_sensor_timeout = float(
            self.get_parameter('explore_sensor_timeout_s').value)
        self._explore_odom_timeout = float(
            self.get_parameter('explore_odom_timeout_s').value)
        self._search_max_angular = float(
            self.get_parameter('localization_search_max_angular').value)
        self._search_max_linear = float(
            self.get_parameter('localization_search_max_linear').value)
        self._search_max_duration = float(
            self.get_parameter('localization_search_max_duration_s').value)
        self._search_max_distance = float(
            self.get_parameter('localization_search_max_distance_m').value)
        self._search_odom_timeout = float(
            self.get_parameter('localization_search_odom_timeout_s').value)
        self._estop_timeout = float(
            self.get_parameter('estop_timeout_s').value)
        self._motion_map_tf_timeout = float(
            self.get_parameter('motion_map_tf_timeout_s').value)
        self._motion_base_tf_timeout = float(
            self.get_parameter('motion_base_tf_timeout_s').value)
        self._global_frame = str(self.get_parameter('global_frame').value)
        self._odom_frame = str(self.get_parameter('odom_frame').value)
        self._base_frame = str(self.get_parameter('base_frame').value)
        if (
                self._status_timeout <= 0.0
                or self._command_timeout <= 0.0
                or self._localization_timeout <= 0.0
                or self._search_max_angular <= 0.0
                or self._search_max_linear <= 0.0
                or self._search_max_duration <= 0.0
                or self._search_max_distance <= 0.0
                or self._search_odom_timeout <= 0.0
                or self._explore_map_timeout <= 0.0
                or self._explore_sensor_timeout <= 0.0
                or self._explore_odom_timeout <= 0.0
                or self._explore_scan_max_angular <= 0.0
                or self._explore_direct_max_linear <= 0.0
                or self._explore_direct_max_angular <= 0.0):
            raise ValueError('Gate-Timeouts muessen > 0 sein')
        if not math.isfinite(self._estop_timeout) or self._estop_timeout <= 0.0:
            raise ValueError('estop_timeout_s muss endlich und > 0 sein')
        if (not math.isfinite(self._motion_map_tf_timeout)
                or self._motion_map_tf_timeout <= 0.0
                or not math.isfinite(self._motion_base_tf_timeout)
                or self._motion_base_tf_timeout <= 0.0
                or not self._global_frame or not self._odom_frame
                or not self._base_frame):
            raise ValueError('Missions-TF braucht Frames und positives Zeitlimit')

        self._status = None
        self._status_time = 0.0
        self._command = Twist()
        self._command_time = 0.0
        self._command_source = 'none'
        self._localization_ready = False
        self._localization_time = None
        self._ever_localized = False
        self._search_command = Twist()
        self._search_command_time = None
        self._search_started_at = None
        self._odom_xy = None
        self._odom_time = None
        self._search_last_odom_xy = None
        self._search_distance = 0.0
        self._explore_map_time = None
        self._explore_scan_time = None
        self._explore_left_time = None
        self._explore_right_time = None
        self._near_clouds = {'left': {}, 'right': {}}
        self._near_statuses = {}
        self._estop_clear = None
        self._estop_time = None
        self._mode = 'blocked'

        self._publisher = self.create_publisher(Twist, output_topic, 10)
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self.create_subscription(Twist, input_topic, self._on_command, 10)
        self.create_subscription(
            Twist,
            self.get_parameter('explore_scan_command_topic').value,
            self._on_explore_scan_command,
            10)
        self.create_subscription(
            Twist,
            self.get_parameter('explore_direct_command_topic').value,
            self._on_explore_direct_command,
            10)
        self.create_subscription(String, status_topic, self._on_status, 10)
        self.create_subscription(
            Bool, localization_topic, self._on_localization, 10)
        self.create_subscription(
            Twist, search_topic, self._on_search_command, 10)
        self.create_subscription(
            Odometry, search_odom_topic, self._on_odom, 20)
        self.create_subscription(
            OccupancyGrid, self.get_parameter('explore_map_topic').value,
            self._on_explore_map, 1)
        self.create_subscription(
            LaserScan, self.get_parameter('explore_scan_topic').value,
            self._on_explore_scan, qos_profile_sensor_data)
        self.create_subscription(
            PointCloud2, self.get_parameter('explore_vl53_left_topic').value,
            self._on_explore_left, qos_profile_sensor_data)
        self.create_subscription(
            PointCloud2, self.get_parameter('explore_vl53_right_topic').value,
            self._on_explore_right, qos_profile_sensor_data)
        self.create_subscription(
            NearFieldStatus, self.get_parameter('near_field_status_topic').value,
            self._on_near_status, 10)
        latched = QoSProfile(depth=1)
        latched.reliability = QoSReliabilityPolicy.RELIABLE
        latched.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(
            Bool, self.get_parameter('estop_topic').value,
            self._on_estop, latched)
        self.create_timer(1.0 / rate_hz, self._publish)
        self.get_logger().warn(
            'Nav2-Fahrtor aktiv: Befehle nur bei explizit freigegebener Mission'
            + (' und belastbarer Lokalisierung.'
               if self._require_localization else '.'))
        if self._allow_explore:
            self.get_logger().warn(
                'AUTOMATISCHE ERKUNDUNG im Fahrtor freigegeben; Karte, LiDAR, '
                'Odometrie und beide VL53 muessen fortlaufend frisch bleiben.')
        if self._allow_localization_search:
            self.get_logger().warn(
                'Lokalisierungssuche freigegeben: vorwaerts bis '
                f'{self._search_max_linear:.2f} m/s, Drehung bis '
                f'{self._search_max_angular:.2f} rad/s, maximal '
                f'{self._search_max_distance:.2f} m / '
                f'{self._search_max_duration:.0f} s und nur vor AMCL-Freigabe.')

    def _on_command(self, message):
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if not all(math.isfinite(value) for value in values):
            self._command = Twist()
            self._command_time = 0.0
            self.get_logger().error('Nicht-endlicher Nav2-Befehl verworfen.')
            return
        self._command = message
        self._command_time = time.monotonic()
        self._command_source = 'nav'

    def _on_explore_scan_command(self, message):
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if not explore_scan_values_valid(
                values, self._explore_scan_max_angular):
            self._command = Twist()
            self._command_time = time.monotonic()
            self._command_source = 'explore_scan'
            self._publisher.publish(Twist())
            self.get_logger().error(
                'Explore-Rundblickbefehl verworfen: nur begrenzte Drehung '
                'auf der Stelle ist erlaubt.')
            return
        self._command = message
        self._command_time = time.monotonic()
        self._command_source = 'explore_scan'

    def _on_explore_direct_command(self, message):
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if not explore_direct_values_valid(
                values, self._explore_direct_max_linear,
                self._explore_direct_max_angular):
            self._command = Twist()
            self._command_time = time.monotonic()
            self._command_source = 'explore_direct'
            self._publisher.publish(Twist())
            self.get_logger().error(
                'Direkter Explore-Befehl verworfen: nur begrenzte '
                'Vorwaertsfahrt mit kleiner Lenkkorrektur ist erlaubt.')
            return
        self._command = message
        self._command_time = time.monotonic()
        self._command_source = 'explore_direct'

    def _on_status(self, message):
        try:
            status = json.loads(message.data)
        except (json.JSONDecodeError, TypeError):
            self._status = None
            self._status_time = 0.0
            if not self._search_authorized(time.monotonic()):
                self._publisher.publish(Twist())
            return
        self._status = status
        self._status_time = time.monotonic()
        if not self._mission_authorized(status, time.monotonic()):
            # Nicht erst auf den naechsten Timer-Tick warten.
            if not self._search_authorized(time.monotonic()):
                self._publisher.publish(Twist())

    def _on_search_command(self, message):
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if not localization_search_values_valid(
                values, self._search_max_linear, self._search_max_angular):
            self._search_command = Twist()
            self._search_command_time = None
            self._publisher.publish(Twist())
            self.get_logger().error(
                'Lokalisierungsbefehl verworfen: Suchgrenzen verletzt.')
            return
        now = time.monotonic()
        self._search_command = message
        self._search_command_time = now
        if abs(message.angular.z) > 1e-9 and self._search_started_at is None:
            self._search_started_at = now
            self._search_last_odom_xy = self._odom_xy
        elif message.linear.x > 1e-9 and self._search_started_at is None:
            self._search_started_at = now
            self._search_last_odom_xy = self._odom_xy

    def _on_odom(self, message):
        now = time.monotonic()
        xy = (message.pose.pose.position.x, message.pose.pose.position.y)
        if not all(math.isfinite(value) for value in xy):
            self._odom_xy = None
            self._odom_time = None
            self._publisher.publish(Twist())
            return
        self._odom_xy = xy
        self._odom_time = now
        if self._search_started_at is not None:
            if self._search_last_odom_xy is not None:
                self._search_distance += math.dist(
                    self._search_last_odom_xy, xy)
            self._search_last_odom_xy = xy
            if self._search_distance > self._search_max_distance:
                self._publisher.publish(Twist())

    def _on_explore_map(self, _message):
        self._explore_map_time = time.monotonic()

    def _on_explore_scan(self, _message):
        self._explore_scan_time = time.monotonic()

    def _near_cloud(self, side, message):
        now = time.monotonic()
        stamp = (int(message.header.stamp.sec) * 1_000_000_000
                 + int(message.header.stamp.nanosec))
        age_ns = self.get_clock().now().nanoseconds - stamp
        fields = {field.name: field for field in message.fields}
        valid = (
            bool(message.header.frame_id)
            and message.height > 0 and message.point_step >= 12
            and message.row_step >= message.width * message.point_step
            and len(message.data) == message.height * message.row_step
            and all(name in fields and fields[name].datatype == 7
                    and fields[name].count == 1
                    and 0 <= fields[name].offset <= message.point_step - 4
                    for name in ('x', 'y', 'z'))
            and age_ns >= 0)
        if valid and message.width:
            endian = '>' if message.is_bigendian else '<'
            for row in range(message.height):
                for col in range(message.width):
                    offset = row * message.row_step + col * message.point_step
                    point = tuple(struct.unpack_from(
                        endian + 'f', message.data,
                        offset + fields[name].offset)[0]
                        for name in ('x', 'y', 'z'))
                    if (not all(math.isfinite(value) for value in point)
                            or sum(value * value for value in point) == 0.0):
                        valid = False
                        break
                if not valid:
                    break
        if valid:
            clouds = self._near_clouds[side]
            clouds[stamp] = (now, now - age_ns / 1_000_000_000)
            for older in sorted(clouds)[:-3]:
                del clouds[older]
        else:
            self._near_clouds[side].clear()
        if side == 'left':
            self._explore_left_time = now if valid else None
        else:
            self._explore_right_time = now if valid else None

    def _on_explore_left(self, message):
        self._near_cloud('left', message)

    def _on_explore_right(self, message):
        self._near_cloud('right', message)

    def _on_near_status(self, message):
        now = time.monotonic()
        stamp = (int(message.header.stamp.sec) * 1_000_000_000
                 + int(message.header.stamp.nanosec))
        age_ns = self.get_clock().now().nanoseconds - stamp
        observed = (
            now - age_ns / 1_000_000_000
            if message.header.frame_id == 'base_link' and age_ns >= 0
            else None)
        self._near_statuses[stamp] = (message, now, observed)
        for older in sorted(self._near_statuses)[:-3]:
            del self._near_statuses[older]

    def _near_quality_authorized(self, now):
        if not self._near_statuses:
            return False
        latest, latest_received, latest_observed = self._near_statuses[
            max(self._near_statuses)]
        # A newly reported failure stops immediately, even while a previous
        # complete triplet is still inside its normal freshness window.
        if (any(value is None or not 0 <= now - value <=
                self._explore_sensor_timeout
                for value in (latest_received, latest_observed))
                or any(getattr(latest, f'{side}_quality') not in (
                NearFieldStatus.QUALITY_VALID_NEAR,
                NearFieldStatus.QUALITY_VALID_FAR)
                or getattr(latest, f'{side}_observed_columns') != 255
               for side in ('left', 'right'))):
            return False
        for stamp in sorted(self._near_statuses, reverse=True):
            status, received, observed = self._near_statuses[stamp]
            if (any(value is None or not 0 <= now - value <=
                    self._explore_sensor_timeout
                    for value in (received, observed))
                    or any(getattr(status, f'{side}_quality') not in (
                        NearFieldStatus.QUALITY_VALID_NEAR,
                        NearFieldStatus.QUALITY_VALID_FAR)
                        or getattr(status, f'{side}_observed_columns') != 255
                        for side in ('left', 'right'))):
                continue
            paired = True
            for side in ('left', 'right'):
                cloud = self._near_clouds[side].get(stamp)
                if (cloud is None or any(
                        not 0 <= now - value <= self._explore_sensor_timeout
                        for value in cloud)):
                    paired = False
                    break
            if paired:
                return True
        return False

    def _explore_health_authorized(self, now):
        return self._near_quality_authorized(now) and explore_health_authorized(
            self._allow_explore,
            self._explore_map_time,
            self._explore_scan_time,
            self._explore_left_time,
            self._explore_right_time,
            self._odom_time,
            now,
            self._explore_map_timeout,
            self._explore_sensor_timeout,
            self._explore_odom_timeout,
            allow_stale_map_for_scan=(
                self._command_source == 'explore_scan'))

    def _mission_authorized(self, status, now):
        return (
            (room_motion_authorized(status)
             and self._near_quality_authorized(now))
            or (
                explore_motion_authorized(status, self._allow_explore)
                and self._explore_health_authorized(now)
            )
        )

    def _on_localization(self, message):
        was_ready = self._localization_ready
        self._localization_ready = message.data is True
        self._localization_time = time.monotonic()
        if self._localization_ready:
            self._ever_localized = True
            self._publisher.publish(Twist())
        elif self._require_localization and (
                was_ready or not self._allow_localization_search):
            # Lokalisierungsverlust ist ein unmittelbarer, harter Gate-Stopp.
            self._publisher.publish(Twist())

    def _on_estop(self, message):
        self._estop_clear = message.data is False
        self._estop_time = time.monotonic()
        if not self._estop_clear:
            self._publisher.publish(Twist())

    def _search_authorized(self, now):
        return localization_search_authorized(
            self._allow_localization_search,
            self._localization_ready,
            self._ever_localized,
            self._localization_time,
            self._search_command_time,
            self._search_started_at,
            self._odom_time,
            self._search_distance,
            now,
            self._localization_timeout,
            self._command_timeout,
            self._search_odom_timeout,
            self._search_max_duration,
            self._search_max_distance)

    def _motion_tf_authorized(self):
        try:
            map_transform = self._tf_buffer.lookup_transform(
                self._global_frame, self._base_frame, Time())
            base_transform = self._tf_buffer.lookup_transform(
                self._odom_frame, self._base_frame, Time())
        except TransformException:
            return False
        now_ns = self.get_clock().now().nanoseconds
        def stamp_ns(transform):
            stamp = transform.header.stamp
            return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
        return (
            transform_motion_authorized(
                stamp_ns(map_transform), now_ns,
                self._motion_map_tf_timeout)
            and transform_motion_authorized(
                stamp_ns(base_transform), now_ns,
                self._motion_base_tf_timeout)
        )

    def _publish(self):
        now = time.monotonic()
        estop_clear = estop_motion_authorized(
            self._estop_clear, self._estop_time, now, self._estop_timeout)
        mission_authorized = (
            estop_clear
            and self._motion_tf_authorized()
            and self._mission_authorized(self._status, now)
            and now - self._status_time <= self._status_timeout
            and localization_motion_authorized(
                self._require_localization,
                self._localization_ready,
                self._localization_time,
                now,
                self._localization_timeout)
        )
        command_fresh = now - self._command_time <= self._command_timeout
        search_authorized = (estop_clear and self._search_authorized(now)
                             and self._near_quality_authorized(now))
        if search_authorized:
            command = self._search_command
            mode = 'localization_search'
        elif mission_authorized and command_fresh:
            command = self._command
            mode = 'mission'
        else:
            command = Twist()
            mode = 'blocked'
        self._publisher.publish(command)
        if mode != self._mode:
            self.get_logger().warn(f'Fahrtor-Modus: {mode}')
            self._mode = mode


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelMissionGate()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        # Humble kann beim globalen SIGINT waehrend take_message() statt der
        # vorgesehenen ExternalShutdownException einen RuntimeError werfen.
        # Echte RuntimeError im laufenden Kontext bleiben sichtbar.
        if rclpy.ok():
            raise
    finally:
        if rclpy.ok():
            try:
                node._publisher.publish(Twist())
            except RCLError:
                # Bei globalem SIGINT kann rclpy.ok() noch kurz True liefern,
                # obwohl der Publisher-Kontext bereits ungueltig ist.
                pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
