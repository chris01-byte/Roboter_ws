"""Read-only subscriptions shared by the existing command gate and Explorer."""

import json
import math
import time

from nav_msgs.msg import Odometry
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String

from .hwt601_fusion_health import Hwt601FusionHealth


class Hwt601FusionGuard:
    def __init__(self, node, active_drive, callback_group=None):
        self.node = node
        self.health = Hwt601FusionHealth(active_drive, observer=node.get_name())
        self._logged_recovery_events = 0
        self._logged_first_fault = False
        self.subscriptions = []
        # Passive readiness needs the newest actual measurement, not a queue
        # of old sensor frames. No restamping or extra freshness is permitted.
        latest_sensor = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        latest_wheel = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        for name, topic, msg_type in (
                ('raw', '/shadow/hwt601/imu/data_raw', Imu),
                ('yaw', '/shadow/hwt601/imu/yaw_rate', Imu),
                ('wheel', '/fusion/hwt601/wheel_odom_raw', Odometry)):
            self.subscriptions.append(node.create_subscription(
                msg_type, topic, lambda msg, key=name: self._sample(key, msg),
                (qos_profile_sensor_data if active_drive else
                 latest_wheel if name == 'wheel' else latest_sensor),
                callback_group=callback_group))
        for name, topic in (
                ('raw', '/shadow/hwt601/raw_status_json'),
                ('yaw', '/shadow/hwt601/status_json'),
                ('wheel', '/base_hardware/state_json' if active_drive else
                 '/shadow/hwt601/wheel_status_json')):
            self.subscriptions.append(node.create_subscription(
                String, topic, lambda msg, key=name: self._status(key, msg),
                10, callback_group=callback_group))

    def _status(self, name, msg):
        try:
            payload = json.loads(msg.data)
        except (ValueError, TypeError):
            payload = {}
        self.health.status(name, payload, time.monotonic())

    def _sample(self, name, msg):
        received = time.monotonic()
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        age = self.node.get_clock().now().nanoseconds * 1e-9 - stamp
        if name == 'wheel':
            twist = msg.twist.twist
            values = (twist.linear.x, twist.linear.y, twist.linear.z,
                      twist.angular.x, twist.angular.y, twist.angular.z,
                      *msg.twist.covariance)
            valid = (msg.header.frame_id == 'odom' and msg.child_frame_id == 'base_link'
                     and msg.twist.covariance[0] > 0.0)
        else:
            angular = msg.angular_velocity
            values = (angular.x, angular.y, angular.z, *msg.angular_velocity_covariance)
            valid = (msg.header.frame_id == ('hwt601_link' if name == 'raw' else 'base_link')
                     and msg.angular_velocity_covariance[8] > 0.0)
        self.health.sample(name, stamp, received, received - age,
                           valid and all(math.isfinite(v) for v in values))

    def failure(self):
        return self.decision()[0]

    def decision(self):
        """Return one atomic reason/state pair; log outside the sample lock."""
        with self.health.lock:
            failure = self.health.motion_failure()
            state = self.health.recovery_state
        snapshot = self.health.first_fault_snapshot()
        if snapshot is not None and not self._logged_first_fault:
            try:
                self.node.get_logger().warn(
                    'HWT first_fault: ' + json.dumps(snapshot, sort_keys=True))
                self._logged_first_fault = True
            except Exception:
                pass  # Diagnostics must never suppress the stop decision.
        events = self.health.recovery_events
        for event in events[self._logged_recovery_events:]:
            try:
                self.node.get_logger().warn(
                    'HWT-Recovery %s: %s (monotonic %.6f)' % (
                        event['state'], event['reason'], event['monotonic_s']))
            except Exception:
                # A logging failure must not interfere with the stop signal.
                pass
        self._logged_recovery_events = len(events)
        return failure, state
