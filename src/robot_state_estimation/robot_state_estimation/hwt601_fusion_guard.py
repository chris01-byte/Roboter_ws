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
    def __init__(self, node, active_drive, callback_group=None,
                 wheel_callback_group=None):
        self.node = node
        self.health = Hwt601FusionHealth(active_drive, observer=node.get_name())
        self.subscriptions = []
        self.active_drive = bool(active_drive)
        self.wheel_subscription = None
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
                callback_group=(wheel_callback_group if name == 'wheel'
                                and wheel_callback_group is not None
                                else callback_group)))
        self.wheel_subscription = self.subscriptions[2]
        for name, topic in (
                ('raw', '/shadow/hwt601/raw_status_json'),
                ('yaw', '/shadow/hwt601/status_json'),
                ('wheel', '/base_hardware/state_json' if active_drive else
                 '/shadow/hwt601/wheel_status_json')):
            self.subscriptions.append(node.create_subscription(
                String, topic, lambda msg, key=name: self._status(key, msg),
                10, callback_group=callback_group))

    def refresh_passive_wheel(self):
        """Nonblocking receive from the same depth-one DDS subscription.

        The passive executor can schedule the decision timer before a waiting
        wheel callback even with separate groups. Use rclpy's existing take
        operation under that subscription's group: no second subscriber,
        publisher, clock change or wait. An already executing callback owns
        the group and is left alone; the decision still checks actual age.
        """
        if self.active_drive:
            return
        sub = self.wheel_subscription
        group = sub.callback_group
        if not group.beginning_execution(sub):
            return
        try:
            before = time.monotonic()
            with sub.handle:
                info = sub.handle.take_message(sub.msg_type, sub.raw)
            after = time.monotonic()
            if info is not None:
                self._sample('wheel', info[0], delivery={
                    'delivery_path': 'gate_predecision_dds_take',
                    'take_before_monotonic_s': before,
                    'take_after_monotonic_s': after})
        except Exception as exc:
            # A receive exception must never keep a previously healthy wheel
            # sample eligible. Preserve its original times/message for diagnosis.
            with self.health.lock:
                previous = self.health.samples.get('wheel')
                if previous is not None:
                    self.health.samples['wheel'] = (*previous[:3], False)
                    self.health.sample_validation['wheel'] = {
                        **self.health.sample_validation.get('wheel', {}),
                        'content_valid': False, 'receive_exception': type(exc).__name__}
                self.health.sample_details['wheel'] = {
                    **self.health.sample_details.get('wheel', {}),
                    'delivery_path': 'gate_predecision_dds_take',
                    'receive_exception': type(exc).__name__}
        finally:
            group.ending_execution(sub)

    def _status(self, name, msg):
        received = time.monotonic()
        try:
            payload = json.loads(msg.data)
        except (ValueError, TypeError):
            payload = {}
        self.health.status(name, payload, received)

    def _sample(self, name, msg, delivery=None):
        received = time.monotonic()
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        clock_before = time.monotonic()
        clock_ros_ns = self.node.get_clock().now().nanoseconds
        clock_after = time.monotonic()
        age = (clock_ros_ns-(msg.header.stamp.sec*1000000000 +
                             msg.header.stamp.nanosec))*1e-9
        details = {'stamp_sec': msg.header.stamp.sec,
                   'stamp_nanosec': msg.header.stamp.nanosec,
                   'frame_id': msg.header.frame_id,
                   'callback_entry_monotonic_s': received if delivery is None else None,
                   'consumer_entry_monotonic_s': received,
                   'delivery_path': 'executor_callback',
                   'ros_clock_ns': clock_ros_ns,
                   'clock_read_before_monotonic_s': clock_before,
                   'clock_read_after_monotonic_s': clock_after,
                   'stamp_age_at_ros_clock_s': age,
                   'conversion_reference': 'clock_read_before_monotonic_s',
                   'conversion_uncertainty_s': clock_after-clock_before,
                   'ros_clock_type': str(self.node.get_clock().clock_type)}
        if delivery is not None:
            details.update(delivery)
        if name == 'wheel':
            twist = msg.twist.twist
            values = (twist.linear.x, twist.linear.y, twist.linear.z,
                      twist.angular.x, twist.angular.y, twist.angular.z,
                      *msg.twist.covariance)
            details.update(child_frame_id=msg.child_frame_id,
                           twist=list(values[:6]), twist_covariance=[float(v) for v in msg.twist.covariance],
                           position=[msg.pose.pose.position.x, msg.pose.pose.position.y,
                                     msg.pose.pose.position.z],
                           orientation=[msg.pose.pose.orientation.x, msg.pose.pose.orientation.y,
                                        msg.pose.pose.orientation.z, msg.pose.pose.orientation.w],
                           pose_covariance=[float(v) for v in msg.pose.covariance])
            valid = (msg.header.frame_id == 'odom'  and msg.child_frame_id == 'base_link'
                     and msg.twist.covariance[0] > 0.0)
        else:
            angular = msg.angular_velocity
            values = (angular.x, angular.y, angular.z, *msg.angular_velocity_covariance)
            valid = (msg.header.frame_id == ('hwt601_link' if name == 'raw' else 'base_link')
                     and msg.angular_velocity_covariance[8] > 0.0)
        finite = all(math.isfinite(v) for v in values)
        details['content_valid'] = bool(valid and finite)
        details['content_rejection'] = (None if valid and finite else
                                        'frame_or_covariance' if not valid else 'nonfinite_twist')
        self.health.sample(name, stamp, received, clock_before - age,
                           valid and finite, details=details)

    def failure(self):
        return self.decision()[0]

    def decision(self):
        """Return one atomic reason/state pair; log outside the sample lock."""
        with self.health.lock:
            failure = self.health.motion_failure()
            state = self.health.recovery_state
        # Existing status publishers expose immutable transition snapshots.
        # No synchronous ROS logging or JSON formatting in the stop decision.
        return failure, state


class DeferredJsonPublisher:
    """Bounded latest status delivery, never JSON/I/O on the decision thread.

    Payloads contain an immutable bounded transition journal, so replacement
    of queued repeated statuses retains all relevant lifetime fault events.
    This helper publishes diagnostic String messages only.
    """
    def __init__(self, publisher):
        import queue
        import threading
        self._queue = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._publisher = publisher
        self.last_error = None
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name='hwt_diagnostic_status')
        self._thread.start()

    def submit(self, payload):
        import queue
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(payload)
            except queue.Full:
                pass

    def _run(self):
        import queue
        while not self._stop.is_set():
            try:
                payload = self._queue.get(timeout=.1)
            except queue.Empty:
                continue
            try:
                self._publisher.publish(String(data=json.dumps(payload)))
            except Exception as exc:
                self.last_error = type(exc).__name__

    def close(self):
        self._stop.set()
        self._thread.join(timeout=.2)
