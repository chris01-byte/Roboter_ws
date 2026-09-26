#!/usr/bin/env python3
"""ROS-Node fuer strikt lesende ESS-RS-Encoder-Schattenodometrie."""

from __future__ import annotations

import json
import math
import time
from typing import Any

import rclpy
from rclpy.executors import ExternalShutdownException
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String

from .encoder_odometry import EncoderOdometry
from .encoder_shadow_reader import (
    BASE_ALIAS,
    HWT601_ALIAS,
    EncoderPairReader,
    EncoderShadowCore,
    EncoderShadowError,
    ReadOnlyModbusTransport,
    shadow_status_payload,
)


ModbusSerialClient: Any
try:
    from pymodbus.client import ModbusSerialClient as _ModbusSerialClient
except Exception:  # pragma: no cover - System ohne Laufzeitabhaengigkeit
    ModbusSerialClient = None
else:
    ModbusSerialClient = _ModbusSerialClient


class EncoderShadowNode(Node):
    """Publiziert nur vollstaendige Encoderpaare im Shadow-Namensraum."""

    def __init__(self) -> None:
        super().__init__('hwt601_encoder_shadow_reader')

        self.declare_parameter(
            'odom_topic', '/shadow/hwt601/wheel_odom_raw')
        self.declare_parameter(
            'status_topic', '/shadow/hwt601/wheel_status_json')
        self.declare_parameter(
            'diagnostics_topic', '/shadow/hwt601/wheel_diagnostics_json')
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')

        self.declare_parameter('port', BASE_ALIAS)
        self.declare_parameter('forbidden_port_alias', HWT601_ALIAS)
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('left_motor_id', 1)
        self.declare_parameter('right_motor_id', 2)
        self.declare_parameter('modbus_timeout_s', 0.1)
        self.declare_parameter('modbus_retries', 0)
        self.declare_parameter('poll_rate_hz', 20.0)
        self.declare_parameter('max_pair_read_duration_s', 0.05)
        self.declare_parameter('max_sample_gap_s', 0.10)

        self.declare_parameter('position_register', 0x000A)
        self.declare_parameter('segment_register', 0x0011)
        self.declare_parameter('word_order_register', 0x0019)
        self.declare_parameter('resolution_register', 0x0101)
        self.declare_parameter('expected_segment', 1000)
        self.declare_parameter('expected_word_order', 0)
        self.declare_parameter('expected_resolution', 4000)
        self.declare_parameter('counts_per_motor_revolution', 1000.0)
        self.declare_parameter('rpm_scale', 1.0)

        self.declare_parameter('wheel_radius_m', 0.0624)
        self.declare_parameter('wheel_separation_m', 0.3845)
        self.declare_parameter('gear_ratio', 10.0)
        self.declare_parameter('invert_left', False)
        self.declare_parameter('invert_right', True)
        self.declare_parameter('max_motor_rpm', 700.0)
        self.declare_parameter('max_delta_factor', 1.5)

        self.declare_parameter('pose_xy_variance', 0.0025)
        self.declare_parameter('yaw_variance', 0.0076)
        self.declare_parameter('twist_linear_variance', 0.01)
        self.declare_parameter('twist_angular_variance', 0.03)

        # Diese vier Werte sind Teil des maschinenlesbaren Sicherheitsvertrags.
        # Der Node besitzt trotzdem keinerlei Schreib- oder TF-Implementierung.
        self.declare_parameter('read_only', True)
        self.declare_parameter('sensor_write_commands', False)
        self.declare_parameter('actuator_output', False)
        self.declare_parameter('publish_tf', False)

        gp = self.get_parameter
        self.odom_topic = str(gp('odom_topic').value)
        self.status_topic = str(gp('status_topic').value)
        self.diagnostics_topic = str(gp('diagnostics_topic').value)
        self.odom_frame_id = str(gp('odom_frame_id').value)
        self.base_frame_id = str(gp('base_frame_id').value)
        self.port = str(gp('port').value)
        self.forbidden_port_alias = str(gp('forbidden_port_alias').value)
        self.baudrate = int(gp('baudrate').value)
        self.left_motor_id = int(gp('left_motor_id').value)
        self.right_motor_id = int(gp('right_motor_id').value)
        self.modbus_timeout_s = float(gp('modbus_timeout_s').value)
        self.modbus_retries = int(gp('modbus_retries').value)
        self.poll_rate_hz = float(gp('poll_rate_hz').value)
        self.max_pair_read_duration_s = float(
            gp('max_pair_read_duration_s').value)
        self.max_sample_gap_s = float(gp('max_sample_gap_s').value)
        self.position_register = int(gp('position_register').value)
        self.segment_register = int(gp('segment_register').value)
        self.word_order_register = int(gp('word_order_register').value)
        self.resolution_register = int(gp('resolution_register').value)
        self.expected_segment = int(gp('expected_segment').value)
        self.expected_word_order = int(gp('expected_word_order').value)
        self.expected_resolution = int(gp('expected_resolution').value)
        self.counts_per_motor_revolution = float(
            gp('counts_per_motor_revolution').value)
        self.rpm_scale = float(gp('rpm_scale').value)
        self.wheel_radius_m = float(gp('wheel_radius_m').value)
        self.wheel_separation_m = float(gp('wheel_separation_m').value)
        self.gear_ratio = float(gp('gear_ratio').value)
        self.invert_left = bool(gp('invert_left').value)
        self.invert_right = bool(gp('invert_right').value)
        self.max_motor_rpm = float(gp('max_motor_rpm').value)
        self.max_delta_factor = float(gp('max_delta_factor').value)
        self.pose_xy_variance = float(gp('pose_xy_variance').value)
        self.yaw_variance = float(gp('yaw_variance').value)
        self.twist_linear_variance = float(
            gp('twist_linear_variance').value)
        self.twist_angular_variance = float(
            gp('twist_angular_variance').value)
        self.read_only = bool(gp('read_only').value)
        self.sensor_write_commands = bool(
            gp('sensor_write_commands').value)
        self.actuator_output = bool(gp('actuator_output').value)
        self.publish_tf = bool(gp('publish_tf').value)
        self.use_sim_time = bool(gp('use_sim_time').value)
        self._validate_parameters()

        tracker = EncoderOdometry(
            wheel_radius_m=self.wheel_radius_m,
            wheel_separation_m=self.wheel_separation_m,
            gear_ratio=self.gear_ratio,
            counts_per_motor_revolution=self.counts_per_motor_revolution,
            invert_left=self.invert_left,
            invert_right=self.invert_right,
            max_motor_rpm=self.max_motor_rpm,
            max_delta_factor=self.max_delta_factor,
            max_recovery_gap_s=self.max_sample_gap_s,
        )
        self.core = EncoderShadowCore(
            tracker,
            max_pair_read_duration_s=self.max_pair_read_duration_s,
        )
        self.transport: ReadOnlyModbusTransport | None = None
        self.reader: EncoderPairReader | None = None
        if ModbusSerialClient is None:
            self.core.latch_fault('pymodbus_fehlt')
        else:
            self.transport = ReadOnlyModbusTransport(
                port=self.port,
                baudrate=self.baudrate,
                timeout_s=self.modbus_timeout_s,
                retries=self.modbus_retries,
                client_factory=ModbusSerialClient,
                required_alias=BASE_ALIAS,
                forbidden_alias=self.forbidden_port_alias,
            )
            self.reader = EncoderPairReader(
                self.transport,
                left_motor_id=self.left_motor_id,
                right_motor_id=self.right_motor_id,
                position_register=self.position_register,
                segment_register=self.segment_register,
                word_order_register=self.word_order_register,
                resolution_register=self.resolution_register,
                rpm_scale=self.rpm_scale,
            )

        self.configuration_valid = False
        self.last_feedback_monotonic: float | None = None
        self.last_ros_stamp_ns: int | None = None
        self.last_error_detail: str | None = None
        self.last_diagnostics_publish = 0.0

        self.odom_pub = self.create_publisher(
            Odometry, self.odom_topic, 10)
        self.status_pub = self.create_publisher(
            String, self.status_topic, 10)
        self.diagnostics_pub = self.create_publisher(
            String, self.diagnostics_topic, 10)
        self.parameter_callback = self.add_on_set_parameters_callback(
            self._reject_runtime_parameter_changes)
        self.timer = self.create_timer(1.0 / self.poll_rate_hz, self._poll)

        self.get_logger().warn(
            'Encoder-Shadow gestartet: nur FC03, keine Schreibkommandos, '
            'keine Aktorausgabe, kein cmd_vel und kein TF.')

    def _validate_parameters(self) -> None:
        shadow_topics = (
            self.odom_topic, self.status_topic, self.diagnostics_topic)
        if any(
            not topic.startswith('/shadow/hwt601/')
            for topic in shadow_topics
        ):
            raise ValueError(
                'Alle Encoder-Shadow-Topics muessen /shadow/hwt601/* sein')
        if len(set(shadow_topics)) != len(shadow_topics):
            raise ValueError('Encoder-Shadow-Topics muessen verschieden sein')
        if self.port != BASE_ALIAS:
            raise ValueError(
                f'port muss der feste Basisalias {BASE_ALIAS} sein')
        if self.forbidden_port_alias != HWT601_ALIAS:
            raise ValueError(
                f'forbidden_port_alias muss {HWT601_ALIAS} bleiben')
        if not self.odom_frame_id or not self.base_frame_id:
            raise ValueError('Odometrieframes duerfen nicht leer sein')
        if self.odom_frame_id == self.base_frame_id:
            raise ValueError(
                'Odometrie- und Basisframe muessen verschieden sein')
        if self.use_sim_time:
            raise ValueError(
                'use_sim_time ist fuer den realen Encoderleser verboten')
        if (not self.read_only or self.sensor_write_commands
                or self.actuator_output or self.publish_tf):
            raise ValueError(
                'Encoder-Shadow muss read_only=true und alle Ausgaben '
                'false halten')
        if self.left_motor_id == self.right_motor_id:
            raise ValueError('Motor-IDs muessen verschieden sein')
        if not all(
            1 <= value <= 247
            for value in (self.left_motor_id, self.right_motor_id)
        ):
            raise ValueError('Motor-IDs muessen 1..247 sein')
        if self.baudrate <= 0 or self.modbus_retries != 0:
            raise ValueError(
                'Baudrate muss positiv und Modbus-Retries muessen 0 sein')
        if self.expected_segment <= 0 or self.expected_resolution <= 0:
            raise ValueError(
                'Abgenommene Encoderregister muessen positiv sein')
        if self.expected_word_order not in (0, 1):
            raise ValueError('expected_word_order muss 0 oder 1 sein')
        for name, value in (
            ('position_register', self.position_register),
            ('segment_register', self.segment_register),
            ('word_order_register', self.word_order_register),
            ('resolution_register', self.resolution_register),
        ):
            if not 0 <= value <= 0xFFFF:
                raise ValueError(f'{name} muss uint16 sein')
        for name, value in (
            ('modbus_timeout_s', self.modbus_timeout_s),
            ('poll_rate_hz', self.poll_rate_hz),
            ('max_pair_read_duration_s', self.max_pair_read_duration_s),
            ('max_sample_gap_s', self.max_sample_gap_s),
            ('counts_per_motor_revolution', self.counts_per_motor_revolution),
            ('rpm_scale', self.rpm_scale),
            ('wheel_radius_m', self.wheel_radius_m),
            ('wheel_separation_m', self.wheel_separation_m),
            ('gear_ratio', self.gear_ratio),
            ('max_motor_rpm', self.max_motor_rpm),
            ('max_delta_factor', self.max_delta_factor),
            ('pose_xy_variance', self.pose_xy_variance),
            ('yaw_variance', self.yaw_variance),
            ('twist_linear_variance', self.twist_linear_variance),
            ('twist_angular_variance', self.twist_angular_variance),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{name} muss endlich und > 0 sein')
        if self.max_pair_read_duration_s >= self.max_sample_gap_s:
            raise ValueError(
                'max_pair_read_duration_s muss kleiner als '
                'max_sample_gap_s sein')

    @staticmethod
    def _reject_runtime_parameter_changes(parameters) -> SetParametersResult:
        if parameters:
            return SetParametersResult(
                successful=False,
                reason=(
                    'Encoder-Shadow-Parameter sind nur beim Neustart '
                    'aenderbar'),
            )
        return SetParametersResult(successful=True)

    def _poll(self) -> None:
        if self.core.fault_reason is not None:
            self._publish_status_and_diagnostics(force_diagnostics=True)
            return
        assert self.transport is not None
        assert self.reader is not None

        try:
            if not self.transport.connected:
                self.transport.connect()
            if not self.configuration_valid:
                self.reader.read_and_validate_configuration(
                    expected_segment=self.expected_segment,
                    expected_word_order=self.expected_word_order,
                    expected_resolution=self.expected_resolution,
                )
                self.configuration_valid = True

            read_started = time.monotonic()
            ros_read_started = self.get_clock().now()
            pair = self.reader.read_complete_pair()
            read_finished = time.monotonic()
            ros_read_finished = self.get_clock().now()
            sample_time = (read_started + read_finished) / 2.0
            result = self.core.accept_pair(
                pair,
                sample_time_s=sample_time,
                pair_read_duration_s=read_finished - read_started,
            )
        except EncoderShadowError as exc:
            self.last_error_detail = str(exc)
            read_finished = time.monotonic()
            read_started = locals().get('read_started', read_finished)
            sample_time = (read_started + read_finished) / 2.0
            if not self.transport.connected:
                self.core.latch_fault('basisport_nicht_sicher')
                result = self.core.accept_pair(
                    None,
                    sample_time_s=sample_time,
                    pair_read_duration_s=read_finished - read_started,
                )
            elif not self.configuration_valid:
                self.core.latch_fault('encoderkonfiguration_ungueltig')
                result = self.core.accept_pair(
                    None,
                    sample_time_s=sample_time,
                    pair_read_duration_s=read_finished - read_started,
                )
            else:
                result = self.core.accept_pair(
                    None,
                    sample_time_s=sample_time,
                    pair_read_duration_s=read_finished - read_started,
                )

        if self.core.fault_reason is not None:
            self._close_transport()
            self._publish_status_and_diagnostics(force_diagnostics=True)
            duration = self.core.last_rejected_pair_duration_s
            if duration is not None:
                self.last_error_detail = (
                    f'FC03-Paar {duration:.6f}s, Grenze '
                    f'{self.max_pair_read_duration_s:.6f}s; '
                    f'Einzelreads {self.reader.last_read_durations_s}')
            self.get_logger().error(
                'Encoder-Shadow dauerhaft gesperrt: '
                f'{self.core.fault_reason}; '
                f'Detail: {self.last_error_detail or result.reason}')
            return

        self.last_feedback_monotonic = sample_time
        if ros_read_finished.nanoseconds <= ros_read_started.nanoseconds:
            self.core.latch_fault('ros_zeit_im_encoderpaar_nicht_monoton')
            self.last_error_detail = (
                'ROS-Zeit ging innerhalb der Encoderpaarprobe nicht vorwaerts')
            self._close_transport()
            self._publish_status_and_diagnostics(force_diagnostics=True)
            return
        stamp = Time(
            nanoseconds=(
                ros_read_started.nanoseconds + ros_read_finished.nanoseconds
            ) // 2,
            clock_type=ros_read_finished.clock_type,
        )
        stamp_ns = stamp.nanoseconds
        if (self.last_ros_stamp_ns is not None
                and stamp_ns <= self.last_ros_stamp_ns):
            self.core.latch_fault('ros_zeit_nicht_monoton')
            self.last_error_detail = 'ROS-Zeitstempel ging nicht vorwaerts'
            self._close_transport()
            self._publish_status_and_diagnostics(force_diagnostics=True)
            return
        self.last_ros_stamp_ns = stamp_ns

        if result.publish:
            self._publish_odometry(stamp, result.update)
        self._publish_status_and_diagnostics()

    def _publish_odometry(self, stamp, update) -> None:
        msg = Odometry()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = self.odom_frame_id
        msg.child_frame_id = self.base_frame_id
        msg.pose.pose.position.x = self.core.tracker.x_m
        msg.pose.pose.position.y = self.core.tracker.y_m
        msg.pose.pose.orientation.z = math.sin(self.core.tracker.yaw_rad / 2.0)
        msg.pose.pose.orientation.w = math.cos(self.core.tracker.yaw_rad / 2.0)
        msg.twist.twist.linear.x = update.linear_velocity_mps
        msg.twist.twist.angular.z = update.angular_velocity_radps

        msg.pose.covariance[0] = self.pose_xy_variance
        msg.pose.covariance[7] = self.pose_xy_variance
        msg.pose.covariance[14] = 1e6
        msg.pose.covariance[21] = 1e6
        msg.pose.covariance[28] = 1e6
        msg.pose.covariance[35] = self.yaw_variance
        msg.twist.covariance[0] = self.twist_linear_variance
        msg.twist.covariance[7] = 1e6
        msg.twist.covariance[14] = 1e6
        msg.twist.covariance[21] = 1e6
        msg.twist.covariance[28] = 1e6
        msg.twist.covariance[35] = self.twist_angular_variance
        self.odom_pub.publish(msg)

    def _feedback_age(self) -> float | None:
        if self.last_feedback_monotonic is None:
            return None
        return max(0.0, time.monotonic() - self.last_feedback_monotonic)

    def _publish_status_and_diagnostics(
        self, *, force_diagnostics: bool = False,
    ) -> None:
        connected = bool(self.transport and self.transport.connected)
        resolved = self.transport.resolved_port if self.transport else None
        payload = shadow_status_payload(
            self.core,
            connected=connected,
            configuration_valid=self.configuration_valid,
            port=self.port,
            resolved_port=resolved,
            left_motor_id=self.left_motor_id,
            right_motor_id=self.right_motor_id,
            last_feedback_age_s=self._feedback_age(),
            max_feedback_age_s=self.max_sample_gap_s,
            successful_connections=(
                self.transport.successful_connections
                if self.transport else 0),
            reconnects=self.transport.reconnects if self.transport else 0,
        )
        payload.update({
            'topic': self.odom_topic,
            'output_qos': 'reliable_keep_last_10',
            'odom_frame_id': self.odom_frame_id,
            'base_frame_id': self.base_frame_id,
            'wheel_radius_m': self.wheel_radius_m,
            'wheel_separation_m': self.wheel_separation_m,
            'gear_ratio': self.gear_ratio,
            'counts_per_motor_revolution': self.counts_per_motor_revolution,
            'invert_left': self.invert_left,
            'invert_right': self.invert_right,
            'position_register': self.position_register,
            'segment_register': self.segment_register,
            'word_order_register': self.word_order_register,
            'resolution_register': self.resolution_register,
            'expected_segment': self.expected_segment,
            'expected_word_order': self.expected_word_order,
            'expected_resolution': self.expected_resolution,
            'rpm_scale': self.rpm_scale,
            'poll_rate_hz': self.poll_rate_hz,
            'max_pair_read_duration_s': self.max_pair_read_duration_s,
            'max_sample_gap_s': self.max_sample_gap_s,
            'last_read_order': self.reader.last_read_order if self.reader else [],
            'last_read_durations_s': (
                self.reader.last_read_durations_s if self.reader else {}),
        })
        self.status_pub.publish(String(
            data=json.dumps(payload, sort_keys=True)))

        now = time.monotonic()
        if force_diagnostics or now - self.last_diagnostics_publish >= 1.0:
            level = 'ERROR' if self.core.fault_reason else (
                'OK' if payload['ready'] else 'WARN')
            diagnostics = {
                'level': level,
                'message': self.core.fault_reason or payload['state'],
                'detail': self.last_error_detail,
                'ready': payload['ready'],
                'sensor_write_commands': False,
                'actuator_output': False,
                'publishes_tf': False,
            }
            self.diagnostics_pub.publish(String(
                data=json.dumps(diagnostics, sort_keys=True)))
            self.last_diagnostics_publish = now

    def _close_transport(self) -> None:
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception as exc:  # pragma: no cover - nur Aufraeumdiagnose
                self.get_logger().warn(
                    f'Encoder-Shadow-Port nicht sauber schliessbar: {exc}')

    def destroy_node(self) -> None:
        self._close_transport()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = EncoderShadowNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
