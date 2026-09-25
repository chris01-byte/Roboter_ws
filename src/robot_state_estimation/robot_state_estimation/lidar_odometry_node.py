"""Publish optional wheel-independent short-term LiDAR odometry."""

import json
import math
import time
from typing import Optional, Tuple

from nav_msgs.msg import Odometry
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from .planar_scan_matcher import (
    LidarReferenceMatcher,
    compose_pose,
    conservative_motion_variances,
    motion_estimate_is_reliable,
    relative_pose,
    scan_points_in_base,
)


def _quaternion_to_rpy(quaternion) -> Tuple[float, float, float]:
    x, y, z, w = (
        quaternion.x, quaternion.y, quaternion.z, quaternion.w)
    magnitude = math.sqrt(x * x + y * y + z * z + w * w)
    if not math.isfinite(magnitude) or magnitude <= 1e-9:
        raise ValueError('Ungueltige TF-Quaternion')
    x, y, z, w = (value / magnitude for value in (x, y, z, w))
    roll = math.atan2(
        2.0 * (w * x + y * z),
        1.0 - 2.0 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))
    yaw = math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


class LidarOdometry(Node):
    """Local scan-to-scan odometry used as a quality reference only.

    The node does not consume wheel odometry, does not publish TF and stops
    publishing whenever geometry is weak or ambiguous.  This preserves its
    independence for symmetric wheel-spin detection.
    """

    def __init__(self):
        super().__init__('lidar_odometry')
        self.declare_parameter('scan_input', '/scan_qualitaet')
        self.declare_parameter('odom_output', '/fusion/reference_odom')
        self.declare_parameter(
            'status_topic', '/sensor_fusion/lidar_odometry_json')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('odom_frame', 'lidar_odom')
        self.declare_parameter('minimum_update_interval_s', 0.18)
        self.declare_parameter('maximum_range_m', 6.0)
        self.declare_parameter('minimum_points', 200)
        self.declare_parameter('resolution_m', 0.015)
        self.declare_parameter('field_margin_m', 0.90)
        self.declare_parameter('maximum_points', 600)
        self.declare_parameter('maximum_cost_m', 0.08)
        self.declare_parameter('minimum_support_ratio', 0.45)
        self.declare_parameter('minimum_distinct_gap_m', 0.0005)
        self.declare_parameter('rebase_translation_m', 0.35)
        self.declare_parameter(
            'rebase_yaw_rad', math.radians(15.0))
        self.declare_parameter(
            'maximum_static_lidar_tilt_rad', math.radians(3.0))
        self.declare_parameter('minimum_position_variance_m2', 0.0004)
        self.declare_parameter('minimum_yaw_variance_rad2', 0.0025)
        self.declare_parameter(
            'minimum_linear_velocity_variance_m2ps2', 0.0025)
        self.declare_parameter(
            'minimum_angular_velocity_variance_rad2ps2', 0.01)

        gp = self.get_parameter
        self.scan_input = str(gp('scan_input').value)
        self.odom_output = str(gp('odom_output').value)
        self.status_topic = str(gp('status_topic').value)
        self.base_frame = str(gp('base_frame').value)
        self.odom_frame = str(gp('odom_frame').value)
        self.minimum_interval = float(
            gp('minimum_update_interval_s').value)
        self.maximum_range = float(gp('maximum_range_m').value)
        self.minimum_points = int(gp('minimum_points').value)
        self.resolution = float(gp('resolution_m').value)
        self.field_margin = float(gp('field_margin_m').value)
        self.maximum_points = int(gp('maximum_points').value)
        self.maximum_cost = float(gp('maximum_cost_m').value)
        self.minimum_support = float(gp('minimum_support_ratio').value)
        self.minimum_gap = float(gp('minimum_distinct_gap_m').value)
        self.rebase_translation = float(gp('rebase_translation_m').value)
        self.rebase_yaw = float(gp('rebase_yaw_rad').value)
        self.maximum_static_tilt = float(
            gp('maximum_static_lidar_tilt_rad').value)
        self.minimum_position_variance = float(
            gp('minimum_position_variance_m2').value)
        self.minimum_yaw_variance = float(
            gp('minimum_yaw_variance_rad2').value)
        self.minimum_linear_velocity_variance = float(
            gp('minimum_linear_velocity_variance_m2ps2').value)
        self.minimum_angular_velocity_variance = float(
            gp('minimum_angular_velocity_variance_rad2ps2').value)
        positive = (
            self.minimum_interval, self.maximum_range, self.resolution,
            self.field_margin, self.maximum_cost, self.minimum_support,
            self.minimum_gap, self.rebase_translation, self.rebase_yaw,
            self.maximum_static_tilt, self.minimum_position_variance,
            self.minimum_yaw_variance,
            self.minimum_linear_velocity_variance,
            self.minimum_angular_velocity_variance,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in positive):
            raise ValueError('LiDAR-Odometriegrenzen muessen positiv sein')
        if self.minimum_points < 200 or self.maximum_points < self.minimum_points:
            raise ValueError('LiDAR-Odometrie braucht mindestens 200 Punkte')
        if not 0.0 < self.minimum_support <= 1.0:
            raise ValueError('minimum_support_ratio muss in (0, 1] liegen')
        if not self.base_frame or not self.odom_frame:
            raise ValueError('LiDAR-Odometrieframes duerfen nicht leer sein')

        self.tf_buffer = Buffer(cache_time=Duration(seconds=10.0))
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.matcher: Optional[LidarReferenceMatcher] = None
        self.reference_global = (0.0, 0.0, 0.0)
        self.local_pose = (0.0, 0.0, 0.0)
        self.last_global_pose = (0.0, 0.0, 0.0)
        self.last_scan_stamp_s: Optional[float] = None
        self.last_processed_stamp_s: Optional[float] = None
        self.accepted = 0
        self.rejected = 0
        self.rebased = 0
        self.last_reason = 'referenz_noch_nicht_initialisiert'
        self.last_cost_m: Optional[float] = None
        self.last_support: Optional[float] = None

        self.odom_pub = self.create_publisher(
            Odometry, self.odom_output, qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.create_subscription(
            LaserScan, self.scan_input, self._on_scan,
            qos_profile_sensor_data)
        self.create_timer(0.5, self._publish_status)
        self.get_logger().info(
            f'Radunabhaengige LiDAR-Odometrie bereit: {self.scan_input} -> '
            f'{self.odom_output}; kein TF, keine Aktorausgabe')

    def _laser_geometry(
        self, scan: LaserScan
    ) -> Optional[Tuple[float, float, float]]:
        if scan.header.frame_id == self.base_frame:
            return 0.0, 0.0, 0.0
        try:
            transform = self.tf_buffer.lookup_transform(
                self.base_frame, scan.header.frame_id, Time(),
                timeout=Duration(seconds=0.05))
            roll, pitch, yaw = _quaternion_to_rpy(transform.transform.rotation)
        except (TransformException, ValueError):
            self.last_reason = 'lidar_tf_fehlt_oder_ungueltig'
            return None
        if abs(roll) > self.maximum_static_tilt or abs(pitch) > self.maximum_static_tilt:
            self.last_reason = 'lidar_statisch_nicht_planar'
            return None
        return (
            transform.transform.translation.x,
            transform.transform.translation.y,
            yaw,
        )

    def _points(self, scan: LaserScan):
        geometry = self._laser_geometry(scan)
        if geometry is None:
            return None
        try:
            points = scan_points_in_base(
                scan.ranges, scan.angle_min, scan.angle_increment,
                scan.range_min, scan.range_max,
                laser_x_m=geometry[0], laser_y_m=geometry[1],
                laser_yaw_rad=geometry[2],
                maximum_range_m=self.maximum_range)
        except ValueError:
            self.last_reason = 'scan_geometrie_ungueltig'
            return None
        if points.shape[0] < self.minimum_points:
            self.last_reason = 'zu_wenige_scanpunkte'
            return None
        return points

    def _new_matcher(self, points) -> LidarReferenceMatcher:
        return LidarReferenceMatcher(
            points,
            resolution_m=self.resolution,
            field_margin_m=self.field_margin,
            maximum_points=self.maximum_points)

    def _on_scan(self, scan: LaserScan) -> None:
        stamp_s = (
            float(scan.header.stamp.sec)
            + 1e-9 * float(scan.header.stamp.nanosec))
        if not math.isfinite(stamp_s) or stamp_s <= 0.0:
            self.rejected += 1
            self.last_reason = 'scan_zeit_ungueltig'
            return
        if (
                self.last_processed_stamp_s is not None
                and stamp_s - self.last_processed_stamp_s < self.minimum_interval):
            return
        self.last_processed_stamp_s = stamp_s
        points = self._points(scan)
        if points is None:
            self.rejected += 1
            return
        if self.matcher is None:
            self.matcher = self._new_matcher(points)
            self.last_scan_stamp_s = stamp_s
            self.last_reason = 'referenz_initialisiert'
            return
        assert self.last_scan_stamp_s is not None
        dt = stamp_s - self.last_scan_stamp_s
        if dt <= 0.0:
            self.rejected += 1
            self.last_reason = 'scan_zeit_nicht_monoton'
            return
        try:
            estimate = self.matcher.estimate(points, self.local_pose)
        except ValueError:
            self.rejected += 1
            self.last_reason = 'scanmatch_nicht_berechenbar'
            return
        reliable = motion_estimate_is_reliable(
            estimate,
            max_cost_m=self.maximum_cost,
            min_support_ratio=self.minimum_support,
            min_distinct_gap_m=self.minimum_gap)
        self.last_cost_m = estimate.cost_m
        self.last_support = estimate.support_ratio
        if not reliable:
            self.rejected += 1
            self.last_reason = 'scanmatch_schwach_oder_mehrdeutig'
            return

        self.local_pose = (
            estimate.x_m, estimate.y_m, estimate.yaw_rad)
        global_pose = compose_pose(self.reference_global, self.local_pose)
        delta = relative_pose(self.last_global_pose, global_pose)
        linear_velocity = delta[0] / dt
        angular_velocity = delta[2] / dt
        variances = conservative_motion_variances(
            estimate, dt,
            minimum_position_m2=self.minimum_position_variance,
            minimum_yaw_rad2=self.minimum_yaw_variance,
            minimum_linear_velocity_m2ps2=(
                self.minimum_linear_velocity_variance),
            minimum_angular_velocity_rad2ps2=(
                self.minimum_angular_velocity_variance))
        self._publish_odometry(
            scan, global_pose, linear_velocity, angular_velocity,
            variances.position_m2, variances.yaw_rad2,
            variances.linear_velocity_m2ps2,
            variances.angular_velocity_rad2ps2)
        self.accepted += 1
        self.last_reason = 'scanmatch_gueltig'
        self.last_scan_stamp_s = stamp_s
        self.last_global_pose = global_pose

        if (
                math.hypot(self.local_pose[0], self.local_pose[1])
                >= self.rebase_translation
                or abs(self.local_pose[2]) >= self.rebase_yaw):
            self.matcher = self._new_matcher(points)
            self.reference_global = global_pose
            self.local_pose = (0.0, 0.0, 0.0)
            self.rebased += 1

    def _publish_odometry(
            self, scan: LaserScan, pose, linear_velocity: float,
            angular_velocity: float, position_variance: float,
            yaw_variance: float, linear_velocity_variance: float,
            angular_velocity_variance: float) -> None:
        message = Odometry()
        message.header.stamp = scan.header.stamp
        message.header.frame_id = self.odom_frame
        message.child_frame_id = self.base_frame
        message.pose.pose.position.x = pose[0]
        message.pose.pose.position.y = pose[1]
        message.pose.pose.orientation.z = math.sin(pose[2] / 2.0)
        message.pose.pose.orientation.w = math.cos(pose[2] / 2.0)
        message.twist.twist.linear.x = linear_velocity
        message.twist.twist.angular.z = angular_velocity
        message.pose.covariance[0] = position_variance
        message.pose.covariance[7] = position_variance
        message.pose.covariance[14] = 1e6
        message.pose.covariance[21] = 1e6
        message.pose.covariance[28] = 1e6
        message.pose.covariance[35] = yaw_variance
        message.twist.covariance[0] = linear_velocity_variance
        message.twist.covariance[7] = 1e6
        message.twist.covariance[14] = 1e6
        message.twist.covariance[21] = 1e6
        message.twist.covariance[28] = 1e6
        message.twist.covariance[35] = angular_velocity_variance
        self.odom_pub.publish(message)

    def _publish_status(self) -> None:
        payload = {
            'ready': self.matcher is not None and self.accepted > 0,
            'reason': self.last_reason,
            'actuator_output': False,
            'publishes_tf': False,
            'scan_input': self.scan_input,
            'odom_output': self.odom_output,
            'accepted': self.accepted,
            'rejected': self.rejected,
            'rebased': self.rebased,
            'last_cost_m': self.last_cost_m,
            'last_support_ratio': self.last_support,
            'stamp_monotonic_s': time.monotonic(),
        }
        self.status_pub.publish(String(data=json.dumps(payload)))


def main(args=None):
    rclpy.init(args=args)
    node = LidarOdometry()
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
