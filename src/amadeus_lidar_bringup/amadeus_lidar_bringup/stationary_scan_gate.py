#!/usr/bin/env python3
"""Gibt LiDAR-Scans nur in kurzen, nachgewiesenen Stillstandsfenstern frei."""

from __future__ import annotations

import json
import math
import time

from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String

from .stationary_scan_gate_core import GateParameters, StationaryScanGate


def quaternion_yaw(x: float, y: float, z: float, w: float) -> float:
    """Yaw aus einer normierten oder nahezu normierten Quaternion."""
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )


class StationaryScanGateNode(Node):
    def __init__(self) -> None:
        super().__init__('stationary_scan_gate')
        self.declare_parameter('input_scan_topic', '/scan_normiert')
        self.declare_parameter('output_scan_topic', '/scan_stillstand')
        self.declare_parameter('imu_topic', '/oak/imu/data')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter(
            'status_topic', '/stationary_scan_gate/status_json')
        defaults = GateParameters()
        for name, value in defaults.__dict__.items():
            self.declare_parameter(name, value)

        parameters = GateParameters(**{
            name: float(self.get_parameter(name).value)
            for name in defaults.__dict__
        })
        self._gate = StationaryScanGate(parameters)
        self._last_state = None
        self._last_capture_index = 0

        input_scan_topic = self._topic_parameter('input_scan_topic')
        output_scan_topic = self._topic_parameter('output_scan_topic')
        imu_topic = self._topic_parameter('imu_topic')
        odom_topic = self._topic_parameter('odom_topic')
        status_topic = self._topic_parameter('status_topic')

        self._scan_publisher = self.create_publisher(
            LaserScan, output_scan_topic, qos_profile_sensor_data)
        status_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._status_publisher = self.create_publisher(
            String, status_topic, status_qos)
        self.create_subscription(
            LaserScan, input_scan_topic, self._on_scan,
            qos_profile_sensor_data)
        self.create_subscription(
            Imu, imu_topic, self._on_imu, qos_profile_sensor_data)
        self.create_subscription(
            Odometry, odom_topic, self._on_odom, qos_profile_sensor_data)
        self.create_timer(0.2, self._publish_status)

        self.get_logger().info(
            'Stillstands-Scan-Gate fail-closed bereit: '
            f'{input_scan_topic} -> {output_scan_topic}; '
            f'{parameters.settle_duration_s:.2f} s beruhigen, '
            f'{parameters.capture_duration_s:.2f} s aufnehmen.')

    def _topic_parameter(self, name: str) -> str:
        value = str(self.get_parameter(name).value).strip()
        if not value or not value.startswith('/'):
            raise ValueError(f'{name} muss ein absolutes ROS-Topic sein')
        return value

    def _on_imu(self, message: Imu) -> None:
        self._gate.update_imu(
            time.monotonic(),
            (
                message.angular_velocity.x,
                message.angular_velocity.y,
                message.angular_velocity.z,
            ),
            (
                message.linear_acceleration.x,
                message.linear_acceleration.y,
                message.linear_acceleration.z,
            ),
        )

    def _on_odom(self, message: Odometry) -> None:
        orientation = message.pose.pose.orientation
        self._gate.update_odom(
            time.monotonic(),
            (
                message.twist.twist.linear.x,
                message.twist.twist.linear.y,
            ),
            message.twist.twist.angular.z,
            (
                message.pose.pose.position.x,
                message.pose.pose.position.y,
                quaternion_yaw(
                    orientation.x,
                    orientation.y,
                    orientation.z,
                    orientation.w,
                ),
            ),
        )

    def _on_scan(self, message: LaserScan) -> None:
        decision = self._gate.process_scan(time.monotonic())
        if decision.forward_scan:
            self._scan_publisher.publish(message)
        if decision.capture_index > self._last_capture_index:
            self.get_logger().info(
                f'Stillstandsaufnahme P{decision.capture_index} gestartet.')
            self._last_capture_index = decision.capture_index
        if decision.state != self._last_state:
            self.get_logger().info(
                f'Scan-Gate Zustand={decision.state.value}, '
                f'Grund={decision.reason}.')
            self._last_state = decision.state

    def _publish_status(self) -> None:
        status = self._gate.snapshot(time.monotonic())
        status.update({
            'schema_version': 1,
            'time': self.get_clock().now().nanoseconds / 1e9,
        })
        self._status_publisher.publish(String(
            data=json.dumps(status, ensure_ascii=False, sort_keys=True)))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StationaryScanGateNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        # ros2 launch beendet den Context bei SIGINT bereits selbst. Ein
        # zweites shutdown() wuerde dann faelschlich mit RCLError enden.
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
