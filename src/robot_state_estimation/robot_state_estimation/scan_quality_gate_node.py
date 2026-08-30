"""Pass planar scans only while the IMU indicates a stable scan plane."""

import json
import math
import time
from typing import Optional, Tuple

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from .quality_core import (
    ImuStabilityConfig,
    ImuStabilityMonitor,
    rotate_vector_by_quaternion,
)


class ScanQualityGate(Node):
    """Reject only transient non-planar scans, not ordinary planar motion."""

    def __init__(self):
        super().__init__('scan_quality_gate')
        self.declare_parameter('scan_input', '/scan_normiert')
        self.declare_parameter('scan_output', '/scan_qualitaet')
        self.declare_parameter('imu_input', '/fusion/imu')
        self.declare_parameter(
            'status_topic', '/sensor_fusion/scan_quality_json')
        self.declare_parameter('diagnostics_topic', '/diagnostics')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('fail_closed', True)
        self.declare_parameter('imu_timeout_s', 0.35)
        self.declare_parameter('gravity_mps2', 9.80665)
        self.declare_parameter('minimum_acceleration_mps2', 7.0)
        self.declare_parameter('maximum_acceleration_mps2', 12.5)
        self.declare_parameter(
            'maximum_gravity_direction_change_rad', math.radians(3.0))
        self.declare_parameter(
            'maximum_roll_pitch_rate_radps', math.radians(14.0))
        self.declare_parameter('baseline_time_constant_s', 4.0)
        self.declare_parameter('warmup_s', 0.6)
        self.declare_parameter('settle_s', 0.45)

        gp = self.get_parameter
        self.scan_input = str(gp('scan_input').value)
        self.scan_output = str(gp('scan_output').value)
        self.imu_input = str(gp('imu_input').value)
        self.status_topic = str(gp('status_topic').value)
        self.diagnostics_topic = str(gp('diagnostics_topic').value)
        self.base_frame = str(gp('base_frame').value)
        self.fail_closed = bool(gp('fail_closed').value)
        self.imu_timeout_s = float(gp('imu_timeout_s').value)
        if not self.base_frame:
            raise ValueError('base_frame darf nicht leer sein')
        if not math.isfinite(self.imu_timeout_s) or self.imu_timeout_s <= 0.0:
            raise ValueError('imu_timeout_s muss endlich und positiv sein')

        self.monitor = ImuStabilityMonitor(ImuStabilityConfig(
            gravity_mps2=float(gp('gravity_mps2').value),
            minimum_acceleration_mps2=float(
                gp('minimum_acceleration_mps2').value),
            maximum_acceleration_mps2=float(
                gp('maximum_acceleration_mps2').value),
            maximum_gravity_direction_change_rad=float(
                gp('maximum_gravity_direction_change_rad').value),
            maximum_roll_pitch_rate_radps=float(
                gp('maximum_roll_pitch_rate_radps').value),
            baseline_time_constant_s=float(
                gp('baseline_time_constant_s').value),
            warmup_s=float(gp('warmup_s').value),
            settle_s=float(gp('settle_s').value),
        ))
        self.tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self._imu_received_at: Optional[float] = None
        self._imu_stamp_s: Optional[float] = None
        self._last_reason = 'imu_noch_nicht_empfangen'
        self._accepted_scans = 0
        self._rejected_scans = 0
        self._imu_transform_failures = 0

        self.scan_pub = self.create_publisher(
            LaserScan, self.scan_output, qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray, self.diagnostics_topic, 10)
        self.create_subscription(
            Imu, self.imu_input, self._on_imu, qos_profile_sensor_data)
        self.create_subscription(
            LaserScan, self.scan_input, self._on_scan,
            qos_profile_sensor_data)
        self.create_timer(0.5, self._publish_status)

        self.get_logger().info(
            f'Scanqualitaets-Gate bereit: {self.scan_input} -> '
            f'{self.scan_output}, fail_closed={self.fail_closed}')

    def _rotation_to_base(
        self, source_frame: str
    ) -> Optional[Tuple[float, float, float, float]]:
        if source_frame == self.base_frame:
            return (0.0, 0.0, 0.0, 1.0)
        try:
            transform = self.tf_buffer.lookup_transform(
                self.base_frame, source_frame, Time(),
                timeout=Duration(seconds=0.05))
        except TransformException:
            self._imu_transform_failures += 1
            self._last_reason = 'imu_tf_fehlt'
            return None
        rotation = transform.transform.rotation
        return (rotation.x, rotation.y, rotation.z, rotation.w)

    def _on_imu(self, message: Imu) -> None:
        values = (
            message.angular_velocity.x,
            message.angular_velocity.y,
            message.angular_velocity.z,
            message.linear_acceleration.x,
            message.linear_acceleration.y,
            message.linear_acceleration.z,
        )
        if not message.header.frame_id or not all(
                math.isfinite(value) for value in values):
            self._last_reason = 'imu_ungueltige_werte'
            return
        rotation = self._rotation_to_base(message.header.frame_id)
        if rotation is None:
            return
        angular = rotate_vector_by_quaternion(
            (message.angular_velocity.x,
             message.angular_velocity.y,
             message.angular_velocity.z), rotation)
        acceleration = rotate_vector_by_quaternion(
            (message.linear_acceleration.x,
             message.linear_acceleration.y,
             message.linear_acceleration.z), rotation)
        stamp_s = (
            float(message.header.stamp.sec)
            + 1e-9 * float(message.header.stamp.nanosec))
        result = self.monitor.update(stamp_s, angular, acceleration)
        self._imu_stamp_s = stamp_s
        self._imu_received_at = time.monotonic()
        self._last_reason = result.reason

    def _imu_fresh(self) -> bool:
        return (
            self._imu_received_at is not None
            and time.monotonic() - self._imu_received_at <= self.imu_timeout_s)

    def _on_scan(self, message: LaserScan) -> None:
        result = self.monitor.last_result
        accepted = self._imu_fresh() and result.ready and result.stable
        if accepted or not self.fail_closed:
            self.scan_pub.publish(message)
            self._accepted_scans += 1
            return
        self._rejected_scans += 1
        if not self._imu_fresh():
            self._last_reason = 'imu_fehlt_oder_alt'

    def _publish_status(self) -> None:
        result = self.monitor.last_result
        imu_age = (
            None if self._imu_received_at is None
            else max(0.0, time.monotonic() - self._imu_received_at))
        ready = self._imu_fresh() and result.ready and result.stable
        payload = {
            'ready': ready,
            'reason': self._last_reason,
            'fail_closed': self.fail_closed,
            'actuator_output': False,
            'scan_input': self.scan_input,
            'scan_output': self.scan_output,
            'imu_input': self.imu_input,
            'imu_age_s': imu_age,
            'accepted_scans': self._accepted_scans,
            'rejected_scans': self._rejected_scans,
            'imu_transform_failures': self._imu_transform_failures,
            'gravity_direction_change_rad': (
                result.gravity_direction_change_rad
                if math.isfinite(result.gravity_direction_change_rad)
                else None),
            'roll_pitch_rate_radps': (
                result.roll_pitch_rate_radps
                if math.isfinite(result.roll_pitch_rate_radps)
                else None),
            'acceleration_norm_mps2': (
                result.acceleration_norm_mps2
                if math.isfinite(result.acceleration_norm_mps2)
                else None),
        }
        self.status_pub.publish(String(data=json.dumps(payload)))

        diagnostic = DiagnosticStatus()
        diagnostic.name = 'robot_state_estimation/scan_quality_gate'
        diagnostic.hardware_id = 'planar_lidar'
        diagnostic.level = (
            DiagnosticStatus.OK if ready else DiagnosticStatus.WARN)
        diagnostic.message = self._last_reason
        diagnostic.values = [
            KeyValue(key='ready', value=str(ready).lower()),
            KeyValue(
                key='accepted_scans', value=str(self._accepted_scans)),
            KeyValue(
                key='rejected_scans', value=str(self._rejected_scans)),
            KeyValue(key='actuator_output', value='false'),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status = [diagnostic]
        self.diagnostics_pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = ScanQualityGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
