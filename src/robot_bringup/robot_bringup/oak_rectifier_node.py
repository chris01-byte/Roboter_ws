#!/usr/bin/env python3
"""Rectify OAK RGB without coupling image delivery to CameraInfo timestamps."""

from __future__ import annotations

import json
import math
import time

from cv_bridge import CvBridge
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String


def sensor_input_qos() -> QoSProfile:
    """Drop old camera input instead of applying backpressure to DepthAI."""
    return QoSProfile(
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        durability=QoSDurabilityPolicy.VOLATILE,
    )


def image_output_qos() -> QoSProfile:
    """Keep the reliable image contract expected by the existing SLAM stack."""
    return QoSProfile(
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
        reliability=QoSReliabilityPolicy.RELIABLE,
        durability=QoSDurabilityPolicy.VOLATILE,
    )


def input_is_stalled(
        *, now_s: float, started_s: float, last_received_s: float,
        startup_grace_s: float, timeout_s: float) -> bool:
    """Report a local DDS endpoint that never started or became silent."""
    if now_s - started_s < startup_grace_s:
        return False
    return last_received_s <= 0.0 or now_s - last_received_s > timeout_s


def rectification_key(info: CameraInfo, width: int, height: int) -> tuple:
    """Validate calibration and return a hashable map-cache key."""
    if width <= 0 or height <= 0:
        raise ValueError('Bildgroesse ist ungueltig')
    if int(info.width) != width or int(info.height) != height:
        raise ValueError(
            f'CameraInfo {info.width}x{info.height} passt nicht zu '
            f'RGB {width}x{height}')
    if len(info.k) != 9 or len(info.r) != 9 or len(info.p) != 12:
        raise ValueError('CameraInfo enthaelt keine vollstaendige K/R/P-Matrix')
    values = tuple(info.k) + tuple(info.d) + tuple(info.r) + tuple(info.p)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError('CameraInfo enthaelt nicht-endliche Kalibrierwerte')
    if info.k[0] <= 0.0 or info.k[4] <= 0.0:
        raise ValueError('CameraInfo enthaelt ungueltige Brennweiten')
    return (width, height, info.distortion_model, values)


def build_rectification_maps(
        info: CameraInfo, width: int, height: int):
    """Build OpenCV remap tables equivalent to pinhole image rectification."""
    key = rectification_key(info, width, height)
    camera_matrix = np.asarray(info.k, dtype=np.float64).reshape(3, 3)
    distortion = np.asarray(info.d, dtype=np.float64)
    if distortion.size == 0:
        distortion = np.zeros(5, dtype=np.float64)
    rectification = np.asarray(info.r, dtype=np.float64).reshape(3, 3)
    projection = np.asarray(info.p, dtype=np.float64).reshape(3, 4)
    map_x, map_y = cv2.initUndistortRectifyMap(
        camera_matrix,
        distortion,
        rectification,
        projection[:, :3],
        (width, height),
        # Fixed-point maps are mathematically equivalent for cv2.remap and
        # measured 21 % faster than float maps on this Jetson (640x360).
        cv2.CV_16SC2,
    )
    return key, map_x, map_y


class OakRectifier(Node):
    """Rectify every fresh RGB frame using the latest valid calibration."""

    def __init__(self):
        super().__init__('oak_rectifier')
        self._image_input = self.declare_parameter(
            'image_input', '/oak/rgb/image_raw').value
        self._camera_info_input = self.declare_parameter(
            'camera_info_input', '/oak/rgb/camera_info').value
        self._image_output = self.declare_parameter(
            'image_output', '/oak/rgb/image_rect').value
        self._status_topic = self.declare_parameter(
            'status_topic', '/oak/rgb/rectifier_status_json').value
        self._ready_timeout_s = float(self.declare_parameter(
            'ready_timeout_s', 2.0).value)
        self._interpolation = int(self.declare_parameter(
            'interpolation', int(cv2.INTER_LINEAR)).value)
        self._input_stall_timeout_s = float(self.declare_parameter(
            'input_stall_timeout_s', 3.0).value)
        self._subscription_restart_cooldown_s = float(self.declare_parameter(
            'subscription_restart_cooldown_s', 5.0).value)
        self._startup_grace_s = float(self.declare_parameter(
            'startup_grace_s', 10.0).value)
        if self._ready_timeout_s <= 0.0:
            raise ValueError('ready_timeout_s muss positiv sein')
        if self._interpolation not in (
                cv2.INTER_NEAREST, cv2.INTER_LINEAR, cv2.INTER_CUBIC,
                cv2.INTER_AREA, cv2.INTER_LANCZOS4):
            raise ValueError('interpolation ist ungueltig')
        if (
                self._input_stall_timeout_s <= 0.0 or
                self._subscription_restart_cooldown_s <= 0.0 or
                self._startup_grace_s < self._input_stall_timeout_s):
            raise ValueError('Subscription-Watchdog-Parameter sind ungueltig')

        self._bridge = CvBridge()
        self._started_s = time.monotonic()
        self._last_image_received_s = 0.0
        self._last_camera_info_received_s = 0.0
        self._last_subscription_restart_s = {'image': 0.0, 'camera_info': 0.0}
        self._subscription_restarts = {'image': 0, 'camera_info': 0}
        self._camera_info = None
        self._maps_key = None
        self._map_x = None
        self._map_y = None
        self._received = 0
        self._published = 0
        self._dropped = 0
        self._map_updates = 0
        self._last_publish_s = 0.0
        self._last_warning_s = 0.0
        self._last_shape = None

        qos = sensor_input_qos()
        self._camera_info_subscription = self.create_subscription(
            CameraInfo, self._camera_info_input, self._on_camera_info, qos)
        self._image_subscription = self.create_subscription(
            Image, self._image_input, self._on_image, qos)
        self._image_pub = self.create_publisher(
            Image, self._image_output, image_output_qos())
        self._status_pub = self.create_publisher(
            String, self._status_topic, 1)
        self.create_timer(1.0, self._publish_status)
        self.create_timer(1.0, self._watch_inputs)
        self.get_logger().info(
            'OAK-RGB-Entzerrer bereit: getrennte Best-Effort-Eingaenge, '
            'keine Image/CameraInfo-Zeitstempelsynchronisierung.')

    def _on_camera_info(self, message: CameraInfo):
        self._last_camera_info_received_s = time.monotonic()
        self._camera_info = message

    def _warn_throttled(self, message: str):
        now_s = time.monotonic()
        if now_s - self._last_warning_s >= 5.0:
            self.get_logger().warn(message)
            self._last_warning_s = now_s

    def _on_image(self, message: Image):
        self._last_image_received_s = time.monotonic()
        self._received += 1
        if self._camera_info is None:
            self._dropped += 1
            self._warn_throttled(
                'Noch keine CameraInfo; RGB-Entzerrung bleibt fail-closed.')
            return
        try:
            image = self._bridge.imgmsg_to_cv2(
                message, desired_encoding='passthrough')
            if image.ndim not in (2, 3):
                raise ValueError(f'RGB-Bilddimension {image.shape} ist ungueltig')
            height, width = image.shape[:2]
            key = rectification_key(self._camera_info, width, height)
            if key != self._maps_key:
                key, self._map_x, self._map_y = build_rectification_maps(
                    self._camera_info, width, height)
                self._maps_key = key
                self._map_updates += 1
            rectified = cv2.remap(
                image,
                self._map_x,
                self._map_y,
                interpolation=self._interpolation,
                borderMode=cv2.BORDER_CONSTANT,
            )
            output = self._bridge.cv2_to_imgmsg(
                rectified, encoding=message.encoding)
            output.header = message.header
        except Exception as exc:
            self._dropped += 1
            self._warn_throttled(f'RGB-Entzerrung verworfen ({exc}).')
            return

        self._image_pub.publish(output)
        self._published += 1
        self._last_publish_s = time.monotonic()
        self._last_shape = [height, width]

    def _watch_inputs(self):
        now_s = time.monotonic()
        if input_is_stalled(
                now_s=now_s,
                started_s=self._started_s,
                last_received_s=self._last_image_received_s,
                startup_grace_s=self._startup_grace_s,
                timeout_s=self._input_stall_timeout_s):
            self._restart_subscription('image', now_s)
        if self._camera_info is None and input_is_stalled(
                now_s=now_s,
                started_s=self._started_s,
                last_received_s=self._last_camera_info_received_s,
                startup_grace_s=self._startup_grace_s,
                timeout_s=self._input_stall_timeout_s):
            self._restart_subscription('camera_info', now_s)

    def _restart_subscription(self, stream: str, now_s: float):
        if (
                now_s - self._last_subscription_restart_s[stream] <
                self._subscription_restart_cooldown_s):
            return
        qos = sensor_input_qos()
        if stream == 'image':
            self.destroy_subscription(self._image_subscription)
            self._image_subscription = self.create_subscription(
                Image, self._image_input, self._on_image, qos)
            self._last_image_received_s = 0.0
        elif stream == 'camera_info':
            self.destroy_subscription(self._camera_info_subscription)
            self._camera_info_subscription = self.create_subscription(
                CameraInfo, self._camera_info_input,
                self._on_camera_info, qos)
            self._last_camera_info_received_s = 0.0
        else:
            raise ValueError(f'Unbekannter Entzerrer-Eingang: {stream}')
        self._last_subscription_restart_s[stream] = now_s
        self._subscription_restarts[stream] += 1
        self.get_logger().warn(
            f'{stream}-Eingang seit mehr als '
            f'{self._input_stall_timeout_s:.1f} s still; lokale '
            'Best-Effort-Subscription wird neu aufgebaut.')

    def _publish_status(self):
        now_s = time.monotonic()
        age = None
        if self._last_publish_s > 0.0:
            age = max(0.0, now_s - self._last_publish_s)
        image_input_age = None
        if self._last_image_received_s > 0.0:
            image_input_age = max(0.0, now_s - self._last_image_received_s)
        camera_info_age = None
        if self._last_camera_info_received_s > 0.0:
            camera_info_age = max(
                0.0, now_s - self._last_camera_info_received_s)
        payload = {
            'ready': age is not None and age <= self._ready_timeout_s,
            'last_publish_age_s': age,
            'frames_received': self._received,
            'frames_published': self._published,
            'frames_dropped': self._dropped,
            'map_updates': self._map_updates,
            'last_shape': self._last_shape,
            'image_input_age_s': image_input_age,
            'camera_info_age_s': camera_info_age,
            'subscription_restarts': self._subscription_restarts,
            'synchronization': 'latest_valid_camera_info',
        }
        self._status_pub.publish(String(data=json.dumps(payload)))


def main(args=None):
    from rclpy.executors import ExternalShutdownException

    rclpy.init(args=args)
    node = OakRectifier()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
