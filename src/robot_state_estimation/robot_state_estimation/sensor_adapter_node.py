"""Validate sensor contracts and publish fusion-ready standard messages."""

import copy
import json
import math
import time
from typing import Iterable, Optional

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String

from .quality_core import (
    GyroBiasConfig,
    GyroBiasEstimator,
    MotionConsistencyConfig,
    MotionConsistencyMonitor,
)


def _stamp_seconds(message) -> float:
    return float(message.header.stamp.sec) + 1e-9 * float(
        message.header.stamp.nanosec)


def _finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def _positive_variance(value: float, fallback: float) -> float:
    if math.isfinite(value) and value > 0.0:
        return value
    return fallback


def _json_number(value: float):
    return value if math.isfinite(value) else None


def _set_diagonal(covariance, index: int, fallback: float) -> None:
    covariance[index] = _positive_variance(covariance[index], fallback)


class SensorAdapter(Node):
    """Boundary between hardware-specific drivers and the fusion core.

    The node does not calculate a pose and never publishes a transform or
    actuator command.  It rejects malformed messages, fills only explicitly
    configured fallback covariances and dynamically lowers trust in wheel
    odometry when a separately measured motion source disagrees.
    """

    def __init__(self):
        super().__init__('sensor_adapter')
        self.declare_parameter('wheel_odom_input', '/wheel/odom_raw')
        self.declare_parameter('wheel_odom_output', '/fusion/wheel_odom')
        self.declare_parameter('imu_input', '/oak/imu/data')
        self.declare_parameter('imu_output', '/fusion/imu')
        self.declare_parameter('reference_odom_input', '/fusion/reference_odom')
        self.declare_parameter('status_topic', '/sensor_fusion/status_json')
        self.declare_parameter('diagnostics_topic', '/diagnostics')
        self.declare_parameter('expected_odom_frame', 'odom')
        self.declare_parameter('expected_base_frame', 'base_link')
        self.declare_parameter('expected_imu_frame', '')
        self.declare_parameter('require_imu', True)
        self.declare_parameter('require_reference_odom', False)
        self.declare_parameter('use_imu_orientation', False)
        self.declare_parameter('calibrate_gyro_bias', True)
        self.declare_parameter('gyro_bias_initial_settle_s', 0.0)
        self.declare_parameter('gyro_bias_calibration_s', 2.0)
        self.declare_parameter('gyro_bias_minimum_samples', 300)
        self.declare_parameter('gyro_bias_maximum_stddev_radps', 0.02)
        self.declare_parameter('gyro_bias_maximum_sample_radps', 0.20)
        self.declare_parameter('gyro_bias_maximum_sample_gap_s', 0.25)
        self.declare_parameter(
            'gyro_bias_stationary_linear_threshold_mps', 0.01)
        self.declare_parameter(
            'gyro_bias_stationary_angular_threshold_radps', 0.03)
        self.declare_parameter('gyro_bias_stationary_settle_s', 0.0)
        self.declare_parameter(
            'gyro_bias_stationary_adaptation_time_constant_s', 0.0)
        self.declare_parameter(
            'gyro_bias_stationary_residual_time_constant_s', 1.0)
        self.declare_parameter(
            'gyro_bias_maximum_stationary_residual_radps', 0.001)
        self.declare_parameter('gyro_bias_stationary_recovery_s', 1.0)
        self.declare_parameter('sensor_timeout_s', 0.35)
        self.declare_parameter('wheel_pose_xy_variance', 0.0025)
        self.declare_parameter('wheel_pose_yaw_variance', 0.0076)
        self.declare_parameter('wheel_twist_linear_variance', 0.01)
        self.declare_parameter('wheel_twist_lateral_variance', 0.04)
        self.declare_parameter('wheel_twist_angular_variance', 0.03)
        self.declare_parameter('enforce_nonholonomic_lateral_velocity', True)
        self.declare_parameter('imu_angular_velocity_variance', 0.02)
        self.declare_parameter('imu_linear_acceleration_variance', 0.25)
        self.declare_parameter('reference_max_twist_variance', 0.25)
        self.declare_parameter('maximum_linear_velocity_error_mps', 0.10)
        self.declare_parameter('maximum_angular_velocity_error_radps', 0.22)
        self.declare_parameter('minimum_evaluation_speed_mps', 0.025)
        self.declare_parameter('minimum_evaluation_rate_radps', 0.08)
        self.declare_parameter('maximum_stamp_skew_s', 0.16)
        self.declare_parameter('bad_samples_to_latch', 2)
        self.declare_parameter('good_samples_to_recover', 5)
        self.declare_parameter('suspect_covariance_scale', 10.0)
        self.declare_parameter('slip_covariance_scale', 100.0)

        gp = self.get_parameter
        self.wheel_input = str(gp('wheel_odom_input').value)
        self.wheel_output = str(gp('wheel_odom_output').value)
        self.imu_input = str(gp('imu_input').value)
        self.imu_output = str(gp('imu_output').value)
        self.reference_input = str(gp('reference_odom_input').value)
        self.status_topic = str(gp('status_topic').value)
        self.diagnostics_topic = str(gp('diagnostics_topic').value)
        self.expected_odom_frame = str(gp('expected_odom_frame').value)
        self.expected_base_frame = str(gp('expected_base_frame').value)
        self.expected_imu_frame = str(gp('expected_imu_frame').value)
        self.require_imu = bool(gp('require_imu').value)
        self.require_reference = bool(gp('require_reference_odom').value)
        self.use_imu_orientation = bool(gp('use_imu_orientation').value)
        self.calibrate_gyro_bias = bool(gp('calibrate_gyro_bias').value)
        self.gyro_stationary_linear_threshold = float(
            gp('gyro_bias_stationary_linear_threshold_mps').value)
        self.gyro_stationary_angular_threshold = float(
            gp('gyro_bias_stationary_angular_threshold_radps').value)
        self.sensor_timeout_s = float(gp('sensor_timeout_s').value)
        self.wheel_pose_xy_variance = float(
            gp('wheel_pose_xy_variance').value)
        self.wheel_pose_yaw_variance = float(
            gp('wheel_pose_yaw_variance').value)
        self.wheel_twist_linear_variance = float(
            gp('wheel_twist_linear_variance').value)
        self.wheel_twist_lateral_variance = float(
            gp('wheel_twist_lateral_variance').value)
        self.wheel_twist_angular_variance = float(
            gp('wheel_twist_angular_variance').value)
        self.enforce_nonholonomic_lateral_velocity = bool(
            gp('enforce_nonholonomic_lateral_velocity').value)
        self.imu_angular_variance = float(
            gp('imu_angular_velocity_variance').value)
        self.imu_acceleration_variance = float(
            gp('imu_linear_acceleration_variance').value)
        self.reference_max_twist_variance = float(
            gp('reference_max_twist_variance').value)

        positive = {
            'sensor_timeout_s': self.sensor_timeout_s,
            'wheel_pose_xy_variance': self.wheel_pose_xy_variance,
            'wheel_pose_yaw_variance': self.wheel_pose_yaw_variance,
            'wheel_twist_linear_variance': self.wheel_twist_linear_variance,
            'wheel_twist_lateral_variance': self.wheel_twist_lateral_variance,
            'wheel_twist_angular_variance': self.wheel_twist_angular_variance,
            'imu_angular_velocity_variance': self.imu_angular_variance,
            'imu_linear_acceleration_variance': self.imu_acceleration_variance,
            'reference_max_twist_variance': self.reference_max_twist_variance,
            'gyro_bias_stationary_linear_threshold_mps': (
                self.gyro_stationary_linear_threshold),
            'gyro_bias_stationary_angular_threshold_radps': (
                self.gyro_stationary_angular_threshold),
        }
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{name} muss endlich und positiv sein')
        if not self.expected_odom_frame or not self.expected_base_frame:
            raise ValueError('Odometrie- und Basisframe duerfen nicht leer sein')

        self.consistency = MotionConsistencyMonitor(MotionConsistencyConfig(
            maximum_linear_velocity_error_mps=float(
                gp('maximum_linear_velocity_error_mps').value),
            maximum_angular_velocity_error_radps=float(
                gp('maximum_angular_velocity_error_radps').value),
            minimum_evaluation_speed_mps=float(
                gp('minimum_evaluation_speed_mps').value),
            minimum_evaluation_rate_radps=float(
                gp('minimum_evaluation_rate_radps').value),
            maximum_stamp_skew_s=float(gp('maximum_stamp_skew_s').value),
            bad_samples_to_latch=int(gp('bad_samples_to_latch').value),
            good_samples_to_recover=int(gp('good_samples_to_recover').value),
            suspect_covariance_scale=float(
                gp('suspect_covariance_scale').value),
            slip_covariance_scale=float(gp('slip_covariance_scale').value),
        ))
        self.gyro_bias = GyroBiasEstimator(GyroBiasConfig(
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
            stationary_settle_s=float(
                gp('gyro_bias_stationary_settle_s').value),
            stationary_adaptation_time_constant_s=float(gp(
                'gyro_bias_stationary_adaptation_time_constant_s').value),
            stationary_residual_time_constant_s=float(gp(
                'gyro_bias_stationary_residual_time_constant_s').value),
            maximum_stationary_residual_radps=float(gp(
                'gyro_bias_maximum_stationary_residual_radps').value),
            stationary_recovery_s=float(
                gp('gyro_bias_stationary_recovery_s').value),
        ))

        self._last_wheel: Optional[Odometry] = None
        self._last_wheel_stamp_s: Optional[float] = None
        self._last_imu_stamp_s: Optional[float] = None
        self._last_reference_stamp_s: Optional[float] = None
        self._wheel_received_at: Optional[float] = None
        self._imu_received_at: Optional[float] = None
        self._reference_received_at: Optional[float] = None
        self._accepted_wheel = 0
        self._rejected_wheel = 0
        self._accepted_imu = 0
        self._rejected_imu = 0
        self._raw_imu = 0
        self._accepted_reference = 0
        self._rejected_reference = 0
        self._last_scale = 1.0

        self.wheel_pub = self.create_publisher(
            Odometry, self.wheel_output, qos_profile_sensor_data)
        self.imu_pub = self.create_publisher(
            Imu, self.imu_output, qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray, self.diagnostics_topic, 10)
        self.create_subscription(
            Odometry, self.wheel_input, self._on_wheel,
            qos_profile_sensor_data)
        self.create_subscription(
            Imu, self.imu_input, self._on_imu, qos_profile_sensor_data)
        self.create_subscription(
            Odometry, self.reference_input, self._on_reference,
            qos_profile_sensor_data)
        self.create_timer(0.5, self._publish_status)

        self.get_logger().info(
            'Sensoradapter bereit: '
            f'{self.wheel_input} -> {self.wheel_output}, '
            f'{self.imu_input} -> {self.imu_output}; keine Aktorausgabe')

    def _valid_wheel(self, message: Odometry) -> bool:
        pose = message.pose.pose
        twist = message.twist.twist
        values = (
            pose.position.x, pose.position.y, pose.position.z,
            pose.orientation.x, pose.orientation.y,
            pose.orientation.z, pose.orientation.w,
            twist.linear.x, twist.linear.y, twist.linear.z,
            twist.angular.x, twist.angular.y, twist.angular.z,
            *message.pose.covariance,
            *message.twist.covariance,
        )
        quaternion_norm = math.sqrt(
            pose.orientation.x * pose.orientation.x
            + pose.orientation.y * pose.orientation.y
            + pose.orientation.z * pose.orientation.z
            + pose.orientation.w * pose.orientation.w)
        return (
            message.header.frame_id == self.expected_odom_frame
            and message.child_frame_id == self.expected_base_frame
            and _finite(values)
            and quaternion_norm > 1e-9
            and _stamp_seconds(message) > 0.0)

    def _on_wheel(self, message: Odometry) -> None:
        if not self._valid_wheel(message):
            self._rejected_wheel += 1
            return
        stamp_s = _stamp_seconds(message)
        if (
                self._last_wheel_stamp_s is not None
                and stamp_s <= self._last_wheel_stamp_s):
            self._rejected_wheel += 1
            return
        output = copy.deepcopy(message)
        _set_diagonal(
            output.pose.covariance, 0, self.wheel_pose_xy_variance)
        _set_diagonal(
            output.pose.covariance, 7, self.wheel_pose_xy_variance)
        _set_diagonal(
            output.pose.covariance, 35, self.wheel_pose_yaw_variance)
        _set_diagonal(
            output.twist.covariance, 0, self.wheel_twist_linear_variance)
        if self.enforce_nonholonomic_lateral_velocity:
            output.twist.twist.linear.y = 0.0
            output.twist.covariance[7] = self.wheel_twist_lateral_variance
        _set_diagonal(
            output.twist.covariance, 35, self.wheel_twist_angular_variance)

        scale = self.consistency.last_result.covariance_scale
        for index in (0, 7, 35):
            if output.pose.covariance[index] < 1e5:
                output.pose.covariance[index] *= scale
        for index in (0, 7, 35):
            if output.twist.covariance[index] < 1e5:
                output.twist.covariance[index] *= scale
        self._last_scale = scale
        self._last_wheel = copy.deepcopy(message)
        self._last_wheel_stamp_s = stamp_s
        self._wheel_received_at = time.monotonic()
        self._accepted_wheel += 1
        self.wheel_pub.publish(output)

    def _valid_imu(self, message: Imu) -> bool:
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
        orientation_norm = math.sqrt(
            orientation.x * orientation.x
            + orientation.y * orientation.y
            + orientation.z * orientation.z
            + orientation.w * orientation.w)
        frame_valid = (
            bool(message.header.frame_id)
            and (
                not self.expected_imu_frame
                or message.header.frame_id == self.expected_imu_frame))
        orientation_valid = (
            not self.use_imu_orientation or orientation_norm > 1e-9)
        return (
            frame_valid
            and orientation_valid
            and _finite(values)
            and _stamp_seconds(message) > 0.0)

    def _on_imu(self, message: Imu) -> None:
        if not self._valid_imu(message):
            self._rejected_imu += 1
            return
        stamp_s = _stamp_seconds(message)
        if (
                self._last_imu_stamp_s is not None
                and stamp_s <= self._last_imu_stamp_s):
            self._rejected_imu += 1
            return
        self._last_imu_stamp_s = stamp_s
        self._raw_imu += 1
        raw_angular = (
            message.angular_velocity.x,
            message.angular_velocity.y,
            message.angular_velocity.z,
        )
        wheel_fresh = (
            self._wheel_received_at is not None
            and time.monotonic() - self._wheel_received_at
            <= self.sensor_timeout_s)
        wheel_stationary = (
            wheel_fresh
            and self._last_wheel is not None
            and abs(self._last_wheel.twist.twist.linear.x)
            <= self.gyro_stationary_linear_threshold
            and abs(self._last_wheel.twist.twist.angular.z)
            <= self.gyro_stationary_angular_threshold)
        if self.calibrate_gyro_bias:
            bias = self.gyro_bias.update(
                stamp_s, raw_angular, wheel_stationary)
            if not bias.calibrated or not bias.stable:
                return
            corrected_angular = self.gyro_bias.correct(raw_angular)
        else:
            corrected_angular = raw_angular
        output = copy.deepcopy(message)
        output.angular_velocity.x = corrected_angular[0]
        output.angular_velocity.y = corrected_angular[1]
        output.angular_velocity.z = corrected_angular[2]
        for index in (0, 4, 8):
            _set_diagonal(
                output.angular_velocity_covariance,
                index, self.imu_angular_variance)
            _set_diagonal(
                output.linear_acceleration_covariance,
                index, self.imu_acceleration_variance)
        if not self.use_imu_orientation:
            output.orientation_covariance[0] = -1.0
        self._imu_received_at = time.monotonic()
        self._accepted_imu += 1
        self.imu_pub.publish(output)

    def _on_reference(self, message: Odometry) -> None:
        twist = message.twist.twist
        covariance = message.twist.covariance
        values = (
            twist.linear.x, twist.angular.z,
            covariance[0], covariance[35], _stamp_seconds(message),
        )
        if (
                not message.header.frame_id
                or message.child_frame_id != self.expected_base_frame
                or not _finite(values)
                or _stamp_seconds(message) <= 0.0
                or covariance[0] <= 0.0
                or covariance[35] <= 0.0
                or covariance[0] > self.reference_max_twist_variance
                or covariance[35] > self.reference_max_twist_variance):
            self._rejected_reference += 1
            return
        stamp_s = _stamp_seconds(message)
        if (
                self._last_reference_stamp_s is not None
                and stamp_s <= self._last_reference_stamp_s):
            self._rejected_reference += 1
            return
        self._last_reference_stamp_s = stamp_s
        self._reference_received_at = time.monotonic()
        self._accepted_reference += 1
        if self._last_wheel is None:
            return
        wheel = self._last_wheel
        result = self.consistency.update(
            wheel.twist.twist.linear.x,
            wheel.twist.twist.angular.z,
            twist.linear.x,
            twist.angular.z,
            _stamp_seconds(wheel) - _stamp_seconds(message),
        )
        if result.covariance_scale != self._last_scale:
            self.get_logger().warn(
                'Rad-Odometrie-Vertrauen geaendert: '
                f'{result.state}, Faktor {result.covariance_scale:.1f}, '
                f'Grund={result.reason}')

    def _age(self, received_at: Optional[float], now: float) -> Optional[float]:
        return None if received_at is None else max(0.0, now - received_at)

    def _publish_status(self) -> None:
        now = time.monotonic()
        wheel_age = self._age(self._wheel_received_at, now)
        imu_age = self._age(self._imu_received_at, now)
        reference_age = self._age(self._reference_received_at, now)
        wheel_fresh = wheel_age is not None and wheel_age <= self.sensor_timeout_s
        imu_fresh = imu_age is not None and imu_age <= self.sensor_timeout_s
        reference_fresh = (
            reference_age is not None
            and reference_age <= self.sensor_timeout_s)
        consistency = self.consistency.last_result
        gyro_bias = self.gyro_bias.result
        bias_ready = (
            not self.calibrate_gyro_bias
            or (gyro_bias.calibrated and gyro_bias.stable))
        ready = (
            wheel_fresh
            and (imu_fresh or not self.require_imu)
            and (reference_fresh or not self.require_reference)
            and consistency.state != 'slip'
            and bias_ready)
        degraded = (
            consistency.state in ('suspect', 'slip') or not bias_ready)
        reasons = []
        if not wheel_fresh:
            reasons.append('rad_odom_fehlt_oder_alt')
        if self.require_imu and not imu_fresh:
            reasons.append('imu_fehlt_oder_alt')
        if self.require_reference and not reference_fresh:
            reasons.append('referenz_odom_fehlt_oder_alt')
        if consistency.state in ('suspect', 'slip'):
            reasons.append(consistency.reason)
        if not bias_ready:
            reasons.append(gyro_bias.reason)
        if not reasons:
            reasons.append('bereit')
        payload = {
            'ready': ready,
            'state': (
                consistency.state
                if consistency.state in ('suspect', 'slip')
                else ('nominal' if ready else 'degraded')),
            'reasons': reasons,
            'actuator_output': False,
            'wheel': {
                'topic_in': self.wheel_input,
                'topic_out': self.wheel_output,
                'age_s': wheel_age,
                'accepted': self._accepted_wheel,
                'rejected': self._rejected_wheel,
                'covariance_scale': consistency.covariance_scale,
            },
            'imu': {
                'topic_in': self.imu_input,
                'topic_out': self.imu_output,
                'age_s': imu_age,
                'accepted': self._accepted_imu,
                'rejected': self._rejected_imu,
                'raw_received': self._raw_imu,
                'bias_calibration_enabled': self.calibrate_gyro_bias,
                'bias_calibrated': (
                    gyro_bias.calibrated or not self.calibrate_gyro_bias),
                'bias_stable': (
                    gyro_bias.stable or not self.calibrate_gyro_bias),
                'bias_reason': (
                    gyro_bias.reason if self.calibrate_gyro_bias
                    else 'treiber_bias_wird_vertraut'),
                'bias_samples': gyro_bias.samples,
                'bias_adaptation_samples': gyro_bias.adaptation_samples,
                'bias_radps': list(gyro_bias.bias_radps),
                'bias_stddev_radps': [
                    _json_number(value) for value in gyro_bias.stddev_radps],
                'bias_residual_mean_radps': [
                    _json_number(value)
                    for value in gyro_bias.residual_mean_radps],
                'bias_residual_norm_radps': _json_number(math.sqrt(sum(
                    value * value
                    for value in gyro_bias.residual_mean_radps))),
            },
            'reference_odometry': {
                'required': self.require_reference,
                'topic_in': self.reference_input,
                'age_s': reference_age,
                'accepted': self._accepted_reference,
                'rejected': self._rejected_reference,
                'consistency_state': consistency.state,
                'consistency_reason': consistency.reason,
                'linear_error_mps': _json_number(
                    consistency.linear_velocity_error_mps),
                'angular_error_radps': _json_number(
                    consistency.angular_velocity_error_radps),
            },
        }
        self.status_pub.publish(String(data=json.dumps(payload, allow_nan=False)))

        diagnostic = DiagnosticStatus()
        diagnostic.name = 'robot_state_estimation/sensor_adapter'
        diagnostic.hardware_id = 'sensor_fusion'
        diagnostic.level = (
            DiagnosticStatus.OK
            if ready and not degraded else DiagnosticStatus.WARN)
        diagnostic.message = ','.join(reasons)
        diagnostic.values = [
            KeyValue(key='wheel_fresh', value=str(wheel_fresh).lower()),
            KeyValue(key='imu_fresh', value=str(imu_fresh).lower()),
            KeyValue(key='gyro_bias_ready', value=str(bias_ready).lower()),
            KeyValue(key='gyro_bias_reason', value=gyro_bias.reason),
            KeyValue(
                key='gyro_bias_residual_norm_radps',
                value=str(_json_number(math.sqrt(sum(
                    value * value
                    for value in gyro_bias.residual_mean_radps))))),
            KeyValue(key='reference_fresh', value=str(reference_fresh).lower()),
            KeyValue(
                key='wheel_covariance_scale',
                value=f'{consistency.covariance_scale:.3f}'),
            KeyValue(key='actuator_output', value='false'),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status = [diagnostic]
        self.diagnostics_pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = SensorAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except RuntimeError:
        # Humble can race a subscription take against context shutdown.  Keep
        # genuine runtime failures visible, but do not turn a completed Ctrl-C
        # shutdown into a false node failure.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
