"""Publish a strictly isolated, bias-corrected HWT601 yaw-rate shadow."""

import copy
import json
import math
import time
from typing import Optional

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import Imu
from std_msgs.msg import String

from .hwt601_shadow_core import (
    Hwt601YawShadowCore,
    valid_hwt601_shadow_input,
)
from .quality_core import GyroBiasConfig


SHADOW_OUTPUT_QOS_DEPTH = 200


def _stamp_seconds(message: Imu) -> float:
    return float(message.header.stamp.sec) + 1e-9 * float(
        message.header.stamp.nanosec)


def _json_number(value: float):
    return value if math.isfinite(value) else None


class Hwt601ShadowNode(Node):
    """Derive only base-frame yaw rate; never publish pose, TF or commands."""

    def __init__(self):
        super().__init__('hwt601_shadow')
        self.declare_parameter(
            'imu_input', '/shadow/hwt601/imu/data_raw')
        self.declare_parameter(
            'imu_output', '/shadow/hwt601/imu/yaw_rate')
        self.declare_parameter(
            'status_topic', '/shadow/hwt601/status_json')
        self.declare_parameter(
            'diagnostics_topic', '/shadow/hwt601/diagnostics')
        self.declare_parameter('expected_input_frame', 'hwt601_link')
        self.declare_parameter('output_frame', 'base_link')
        self.declare_parameter('operator_stationary_confirmed', False)
        self.declare_parameter('gyro_bias_initial_settle_s', 15.0)
        self.declare_parameter('gyro_bias_calibration_s', 10.0)
        self.declare_parameter('gyro_bias_minimum_samples', 800)
        self.declare_parameter('gyro_bias_maximum_stddev_radps', 0.005)
        self.declare_parameter('gyro_bias_maximum_sample_radps', 0.03)
        self.declare_parameter('gyro_bias_maximum_sample_gap_s', 0.10)
        self.declare_parameter('sensor_timeout_s', 0.35)
        self.declare_parameter('angular_velocity_z_variance', 5.0e-7)
        self.declare_parameter('unobserved_axis_variance', 1.0e6)

        gp = self.get_parameter
        self.imu_input = str(gp('imu_input').value)
        self.imu_output = str(gp('imu_output').value)
        self.status_topic = str(gp('status_topic').value)
        self.diagnostics_topic = str(gp('diagnostics_topic').value)
        self.expected_input_frame = str(gp('expected_input_frame').value)
        self.output_frame = str(gp('output_frame').value)
        self.operator_stationary_confirmed = bool(
            gp('operator_stationary_confirmed').value)
        self.sensor_timeout_s = float(gp('sensor_timeout_s').value)
        self.angular_velocity_z_variance = float(
            gp('angular_velocity_z_variance').value)
        self.unobserved_axis_variance = float(
            gp('unobserved_axis_variance').value)

        for topic in (
                self.imu_input, self.imu_output, self.status_topic,
                self.diagnostics_topic):
            if not topic.startswith('/shadow/hwt601/'):
                raise ValueError(
                    'HWT-Schattenpfad darf nur /shadow/hwt601/* verwenden')
        if self.expected_input_frame != 'hwt601_link':
            raise ValueError('HWT-Rohdaten muessen im hwt601_link bleiben')
        if self.output_frame != 'base_link':
            raise ValueError('abgeleitete Giergeschwindigkeit braucht base_link')
        for name, value in (
                ('sensor_timeout_s', self.sensor_timeout_s),
                ('angular_velocity_z_variance',
                 self.angular_velocity_z_variance),
                ('unobserved_axis_variance', self.unobserved_axis_variance)):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{name} muss endlich und positiv sein')

        bias_config = GyroBiasConfig(
            initial_settle_s=float(
                gp('gyro_bias_initial_settle_s').value),
            calibration_duration_s=float(
                gp('gyro_bias_calibration_s').value),
            minimum_samples=int(gp('gyro_bias_minimum_samples').value),
            maximum_stddev_radps=float(
                gp('gyro_bias_maximum_stddev_radps').value),
            maximum_sample_magnitude_radps=float(
                gp('gyro_bias_maximum_sample_radps').value),
            maximum_sample_gap_s=float(
                gp('gyro_bias_maximum_sample_gap_s').value),
            # This shadow path calibrates once and never adapts in motion.
            stationary_adaptation_time_constant_s=0.0,
        )
        self.core = Hwt601YawShadowCore(
            bias_config, self.operator_stationary_confirmed)

        self._raw_received = 0
        self._published = 0
        self._blocked = 0
        self._rejected = 0
        self._last_reason = 'noch_keine_daten'
        self._last_output_at: Optional[float] = None

        shadow_output_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=SHADOW_OUTPUT_QOS_DEPTH,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.imu_pub = self.create_publisher(
            Imu, self.imu_output, shadow_output_qos)
        self.status_pub = self.create_publisher(
            String, self.status_topic, 10)
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray, self.diagnostics_topic, 10)
        self.create_subscription(
            Imu, self.imu_input, self._on_imu, qos_profile_sensor_data)
        self.create_timer(0.5, self._publish_status)

        confirmation = (
            'bestaetigt' if self.operator_stationary_confirmed
            else 'NICHT bestaetigt; keine Ausgabe')
        self.get_logger().warn(
            'HWT601-Schattenpfad: nur Gyro-Z, kein TF/keine Pose/keine '
            f'Aktorausgabe; Startstillstand {confirmation}')

    def _valid_input(self, message: Imu) -> bool:
        angular = message.angular_velocity
        acceleration = message.linear_acceleration
        orientation = message.orientation
        values = (
            angular.x, angular.y, angular.z,
            acceleration.x, acceleration.y, acceleration.z,
            orientation.x, orientation.y, orientation.z, orientation.w,
            *message.orientation_covariance,
            *message.angular_velocity_covariance,
            *message.linear_acceleration_covariance,
        )
        return valid_hwt601_shadow_input(
            message.header.frame_id,
            _stamp_seconds(message),
            values,
            self.expected_input_frame,
        ) and message.angular_velocity_covariance[8] > 0.0

    def _on_imu(self, message: Imu) -> None:
        self._raw_received += 1
        if not self._valid_input(message):
            self._rejected += 1
            self._last_reason = self.core.reject_invalid_message()
            return
        angular = (
            message.angular_velocity.x,
            message.angular_velocity.y,
            message.angular_velocity.z,
        )
        result = self.core.update(_stamp_seconds(message), angular)
        self._last_reason = result.reason
        if not result.publish:
            if result.reason in (
                    'imu_probe_ungueltig', 'imu_zeit_nicht_monoton',
                    'imu_datenluecke',
                    'imu_probe_ungueltig_neustart_noetig',
                    'imu_zeitfehler_neustart_noetig',
                    'imu_datenluecke_neustart_noetig'):
                self._rejected += 1
            else:
                self._blocked += 1
            return

        output = Imu()
        output.header = copy.deepcopy(message.header)
        output.header.frame_id = self.output_frame
        output.orientation.w = 1.0
        output.orientation_covariance[0] = -1.0
        output.angular_velocity.z = result.yaw_rate_radps
        output.angular_velocity_covariance[0] = self.unobserved_axis_variance
        output.angular_velocity_covariance[4] = self.unobserved_axis_variance
        output.angular_velocity_covariance[8] = (
            self.angular_velocity_z_variance)
        output.linear_acceleration_covariance[0] = -1.0
        self.imu_pub.publish(output)
        self._published += 1
        self._last_output_at = time.monotonic()

    def _publish_status(self) -> None:
        age_s = (
            None if self._last_output_at is None
            else max(0.0, time.monotonic() - self._last_output_at))
        fresh = age_s is not None and age_s <= self.sensor_timeout_s
        bias = self.core.bias
        ready = bool(
            fresh
            and bias.calibrated
            and bias.stable
            and self.core.fault_reason is None)
        if ready:
            reason = 'shadow_yaw_bereit'
        elif not self.operator_stationary_confirmed:
            reason = 'operator_stillstand_nicht_bestaetigt'
        elif self.core.fault_reason is not None:
            reason = self.core.fault_reason
        elif self._last_output_at is not None and not fresh:
            reason = 'shadow_yaw_daten_alt'
        else:
            reason = self._last_reason

        payload = {
            'ready': ready,
            'fusion_ready': False,
            'shadow_only': True,
            'reason': reason,
            'actuator_output': False,
            'publishes_tf': False,
            'operator_stationary_confirmed': (
                self.operator_stationary_confirmed),
            'stationary_source': 'operator_declared_startup_only',
            'bias_frozen_after_startup': True,
            'latched_fault': self.core.fault_reason,
            'scale_validation': 'external_180_observer_confirmed',
            'sensor_to_base_axes': 'x_b=y_s,y_b=-x_s,z_b=z_s',
            'input_topic': self.imu_input,
            'input_frame': self.expected_input_frame,
            'output_topic': self.imu_output,
            'output_frame': self.output_frame,
            'output_qos': 'reliable_keep_last_200',
            'age_s': age_s,
            'raw_received': self._raw_received,
            'published': self._published,
            'blocked': self._blocked,
            'rejected': self._rejected,
            'angular_velocity_z_variance': (
                self.angular_velocity_z_variance),
            'bias': {
                'calibrated': bias.calibrated,
                'stable': bias.stable,
                'reason': (
                    'gyro_bias_eingefroren'
                    if bias.calibrated and bias.stable
                    else bias.reason),
                'samples': bias.samples,
                'adaptation_samples': bias.adaptation_samples,
                'radps_xyz': list(bias.bias_radps),
                'stddev_radps_xyz': [
                    _json_number(value) for value in bias.stddev_radps],
            },
        }
        self.status_pub.publish(String(
            data=json.dumps(payload, allow_nan=False)))

        diagnostic = DiagnosticStatus()
        diagnostic.name = 'robot_state_estimation/hwt601_shadow'
        diagnostic.hardware_id = 'hwt601_shadow_yaw'
        diagnostic.level = (
            DiagnosticStatus.OK if ready else DiagnosticStatus.WARN)
        diagnostic.message = reason
        diagnostic.values = [
            KeyValue(key='ready', value=str(ready).lower()),
            KeyValue(key='shadow_only', value='true'),
            KeyValue(key='fusion_ready', value='false'),
            KeyValue(key='actuator_output', value='false'),
            KeyValue(key='publishes_tf', value='false'),
            KeyValue(
                key='bias_calibrated', value=str(bias.calibrated).lower()),
            KeyValue(
                key='bias_adaptation_samples',
                value=str(bias.adaptation_samples)),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status = [diagnostic]
        self.diagnostics_pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = Hwt601ShadowNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
