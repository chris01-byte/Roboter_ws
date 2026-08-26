#!/usr/bin/env python3
"""Onboard OAK relay: throttled compressed RGB-D for offboard semantics."""

from collections import deque
from copy import deepcopy
import json
import time

from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
)
from sensor_msgs.msg import CameraInfo, CompressedImage, Image
from std_msgs.msg import String

from .stream_codec import (
    StreamCodecError,
    encode_depth_png,
    encode_rgb_jpeg,
    pair_rejection_reason,
    select_freshest_pair,
    stamp_seconds,
)


def sensor_qos() -> QoSProfile:
    """Best-effort depth-one QoS: stale frames are dropped, never queued."""
    return QoSProfile(
        history=QoSHistoryPolicy.KEEP_LAST,
        depth=1,
        reliability=QoSReliabilityPolicy.BEST_EFFORT,
        durability=QoSDurabilityPolicy.VOLATILE,
    )


def input_is_stalled(
        *, now_s: float, started_s: float, last_received_s: float,
        startup_grace_s: float, timeout_s: float) -> bool:
    """Report a missing local subscription after startup or a live stall."""
    if now_s - started_s < startup_grace_s:
        return False
    return last_received_s <= 0.0 or now_s - last_received_s > timeout_s


class SemanticStreamRelay(Node):
    def __init__(self):
        super().__init__('semantic_stream_relay')

        self._rgb_input = self.declare_parameter(
            'rgb_input', '/oak/rgb/image_raw').value
        self._depth_input = self.declare_parameter(
            'depth_input', '/oak/stereo/image_raw').value
        self._camera_info_input = self.declare_parameter(
            'camera_info_input', '/oak/rgb/camera_info').value
        self._rgb_output = self.declare_parameter(
            'rgb_output', '/oak/semantic/rgb/compressed').value
        self._depth_output = self.declare_parameter(
            'depth_output', '/oak/semantic/depth/compressed').value
        self._camera_info_output = self.declare_parameter(
            'camera_info_output', '/oak/semantic/camera_info').value
        self._status_topic = self.declare_parameter(
            'status_topic', '/oak/semantic/stream_status_json').value
        self._rate_hz = float(self.declare_parameter(
            'publish_rate_hz', 2.0).value)
        self._jpeg_quality = int(self.declare_parameter(
            'jpeg_quality', 80).value)
        self._png_compression = int(self.declare_parameter(
            'png_compression', 1).value)
        self._max_age_s = float(self.declare_parameter(
            'max_input_age_s', 1.0).value)
        self._max_skew_s = float(self.declare_parameter(
            'max_rgb_depth_skew_s', 0.20).value)
        self._queue_size = int(self.declare_parameter(
            'frame_queue_size', 40).value)
        self._input_stall_timeout_s = float(self.declare_parameter(
            'input_stall_timeout_s', 3.0).value)
        self._subscription_restart_cooldown_s = float(self.declare_parameter(
            'subscription_restart_cooldown_s', 5.0).value)
        self._startup_grace_s = float(self.declare_parameter(
            'startup_grace_s', 10.0).value)
        self._validate_parameters()

        self._bridge = CvBridge()
        self._started_s = time.monotonic()
        self._last_rgb_received_s = 0.0
        self._last_depth_received_s = 0.0
        self._last_subscription_restart_s = {'rgb': 0.0, 'depth': 0.0}
        self._subscription_restarts = {'rgb': 0, 'depth': 0}
        self._rgb_frames = deque(maxlen=self._queue_size)
        self._depth_frames = deque(maxlen=self._queue_size)
        self._camera_info = None
        self._last_published_rgb_stamp_s = None
        self._last_publish_s = 0.0
        self._published = 0
        self._rejected = 0
        self._rejection_reasons = {
            'missing_input': 0,
            'stale_rgb': 0,
            'stale_depth': 0,
            'timestamp_skew': 0,
            'duplicate_rgb': 0,
        }
        self._codec_errors = 0
        self._last_rgb_bytes = 0
        self._last_depth_bytes = 0
        self._last_source_skew_s = None
        self._last_rgb_shape = None
        self._last_depth_shape = None

        qos = sensor_qos()
        self._rgb_subscription = self.create_subscription(
            Image, self._rgb_input, self._on_rgb, qos)
        self._depth_subscription = self.create_subscription(
            Image, self._depth_input, self._on_depth, qos)
        self._camera_info_subscription = self.create_subscription(
            CameraInfo, self._camera_info_input, self._on_camera_info, qos)
        self._rgb_pub = self.create_publisher(
            CompressedImage, self._rgb_output, qos)
        self._depth_pub = self.create_publisher(
            CompressedImage, self._depth_output, qos)
        self._camera_info_pub = self.create_publisher(
            CameraInfo, self._camera_info_output, qos)
        self._status_pub = self.create_publisher(String, self._status_topic, 1)

        self.create_timer(1.0 / self._rate_hz, self._publish_pair)
        self.create_timer(1.0, self._publish_status)
        self.create_timer(1.0, self._watch_inputs)
        self.get_logger().info(
            f'Semantik-Relay bereit: {self._rate_hz:.2f} Hz, '
            f'JPEG {self._jpeg_quality}, PNG {self._png_compression}; '
            'Best-Effort, Queue-Tiefe 1.')

    def _validate_parameters(self):
        if not 0.1 <= self._rate_hz <= 10.0:
            raise ValueError('publish_rate_hz muss zwischen 0.1 und 10 liegen')
        if not 1 <= self._jpeg_quality <= 100:
            raise ValueError('jpeg_quality muss zwischen 1 und 100 liegen')
        if not 0 <= self._png_compression <= 9:
            raise ValueError('png_compression muss zwischen 0 und 9 liegen')
        if self._max_age_s <= 0.0 or self._max_skew_s < 0.0:
            raise ValueError('Zeitgrenzen des Semantik-Relays sind ungueltig')
        if not 2 <= self._queue_size <= 120:
            raise ValueError('frame_queue_size muss zwischen 2 und 120 liegen')
        if (
                self._input_stall_timeout_s <= 0.0 or
                self._subscription_restart_cooldown_s <= 0.0 or
                self._startup_grace_s < self._input_stall_timeout_s):
            raise ValueError('Subscription-Watchdog-Parameter sind ungueltig')

    def _on_rgb(self, message: Image):
        self._last_rgb_received_s = time.monotonic()
        self._rgb_frames.append((
            message, self._last_rgb_received_s,
            stamp_seconds(message.header.stamp)))

    def _on_depth(self, message: Image):
        self._last_depth_received_s = time.monotonic()
        self._depth_frames.append((
            message, self._last_depth_received_s,
            stamp_seconds(message.header.stamp)))

    def _on_camera_info(self, message: CameraInfo):
        self._camera_info = message

    def _watch_inputs(self):
        now_s = time.monotonic()
        streams = (
            ('rgb', self._last_rgb_received_s),
            ('depth', self._last_depth_received_s),
        )
        for stream, last_received_s in streams:
            if not input_is_stalled(
                    now_s=now_s,
                    started_s=self._started_s,
                    last_received_s=last_received_s,
                    startup_grace_s=self._startup_grace_s,
                    timeout_s=self._input_stall_timeout_s):
                continue
            if (
                    now_s - self._last_subscription_restart_s[stream] <
                    self._subscription_restart_cooldown_s):
                continue
            self._restart_subscription(stream, now_s)

    def _restart_subscription(self, stream: str, now_s: float):
        qos = sensor_qos()
        if stream == 'rgb':
            self.destroy_subscription(self._rgb_subscription)
            self._rgb_subscription = self.create_subscription(
                Image, self._rgb_input, self._on_rgb, qos)
            self._rgb_frames.clear()
            self._last_rgb_received_s = 0.0
        elif stream == 'depth':
            self.destroy_subscription(self._depth_subscription)
            self._depth_subscription = self.create_subscription(
                Image, self._depth_input, self._on_depth, qos)
            self._depth_frames.clear()
            self._last_depth_received_s = 0.0
        else:
            raise ValueError(f'Unbekannter Relay-Eingang: {stream}')
        self._last_subscription_restart_s[stream] = now_s
        self._subscription_restarts[stream] += 1
        self.get_logger().warn(
            f'{stream}-Eingang seit mehr als '
            f'{self._input_stall_timeout_s:.1f} s still; lokale '
            'Best-Effort-Subscription wird neu aufgebaut.')

    def _publish_pair(self):
        if (
                not self._rgb_frames or not self._depth_frames or
                self._camera_info is None):
            self._reject('missing_input')
            return
        now_s = time.monotonic()
        try:
            pair = select_freshest_pair(
                self._rgb_frames,
                self._depth_frames,
                now_s=now_s,
                max_age_s=self._max_age_s,
                max_skew_s=self._max_skew_s,
                last_rgb_stamp_s=self._last_published_rgb_stamp_s,
            )
        except StreamCodecError:
            self._reject('timestamp_skew')
            return
        if pair is None:
            rgb_latest = self._rgb_frames[-1]
            depth_latest = self._depth_frames[-1]
            self._last_source_skew_s = abs(rgb_latest[2] - depth_latest[2])
            try:
                reason = pair_rejection_reason(
                    now_s=now_s,
                    rgb_received_s=rgb_latest[1],
                    depth_received_s=depth_latest[1],
                    rgb_stamp_s=rgb_latest[2],
                    depth_stamp_s=depth_latest[2],
                    max_age_s=self._max_age_s,
                    max_skew_s=self._max_skew_s,
                )
            except StreamCodecError:
                reason = 'timestamp_skew'
            self._reject(reason or 'duplicate_rgb')
            return

        rgb_sample, depth_sample = pair
        rgb_message_raw, _, rgb_stamp = rgb_sample
        depth_message_raw, _, depth_stamp = depth_sample
        self._last_source_skew_s = abs(rgb_stamp - depth_stamp)
        try:
            reason = pair_rejection_reason(
                now_s=now_s,
                rgb_received_s=rgb_sample[1],
                depth_received_s=depth_sample[1],
                rgb_stamp_s=rgb_stamp,
                depth_stamp_s=depth_stamp,
                max_age_s=self._max_age_s,
                max_skew_s=self._max_skew_s,
            )
        except StreamCodecError:
            self._reject('timestamp_skew')
            return
        if reason is not None:
            self._reject(reason)
            return

        try:
            rgb = self._bridge.imgmsg_to_cv2(
                rgb_message_raw, desired_encoding='bgr8')
            depth = self._bridge.imgmsg_to_cv2(
                depth_message_raw, desired_encoding='passthrough')
            self._last_rgb_shape = list(rgb.shape)
            self._last_depth_shape = list(depth.shape)
            if rgb.shape[:2] != depth.shape[:2]:
                raise StreamCodecError(
                    'RGB und Tiefe haben verschiedene Groessen')
            rgb_payload = encode_rgb_jpeg(rgb, self._jpeg_quality)
            depth_payload = encode_depth_png(depth, self._png_compression)
        except Exception as exc:
            self._codec_errors += 1
            self.get_logger().warn(
                f'Semantik-Bildpaar nicht komprimierbar ({exc}).')
            return

        rgb_message = CompressedImage()
        rgb_message.header = rgb_message_raw.header
        rgb_message.format = 'jpeg; bgr8'
        rgb_message.data = rgb_payload
        depth_message = CompressedImage()
        depth_message.header = depth_message_raw.header
        depth_message.format = '16UC1; png'
        depth_message.data = depth_payload
        camera_info = deepcopy(self._camera_info)
        camera_info.header = rgb_message_raw.header

        self._rgb_pub.publish(rgb_message)
        self._depth_pub.publish(depth_message)
        self._camera_info_pub.publish(camera_info)
        self._last_published_rgb_stamp_s = rgb_stamp
        self._last_publish_s = now_s
        self._published += 1
        self._last_rgb_bytes = len(rgb_payload)
        self._last_depth_bytes = len(depth_payload)
        self._discard_through(self._rgb_frames, rgb_stamp)
        self._discard_through(self._depth_frames, depth_stamp)

    @staticmethod
    def _discard_through(frames, source_stamp_s: float):
        while frames and frames[0][2] <= source_stamp_s:
            frames.popleft()

    def _reject(self, reason: str):
        self._rejected += 1
        self._rejection_reasons[reason] += 1

    def _publish_status(self):
        now_s = time.monotonic()
        age = None
        if self._last_publish_s > 0.0:
            age = max(0.0, now_s - self._last_publish_s)
        rgb_input_age = None
        if self._last_rgb_received_s > 0.0:
            rgb_input_age = max(0.0, now_s - self._last_rgb_received_s)
        depth_input_age = None
        if self._last_depth_received_s > 0.0:
            depth_input_age = max(0.0, now_s - self._last_depth_received_s)
        payload = {
            'ready': age is not None and age <= self._max_age_s,
            'publish_rate_hz': self._rate_hz,
            'pairs_published': self._published,
            'pairs_rejected': self._rejected,
            'rejection_reasons': self._rejection_reasons,
            'codec_errors': self._codec_errors,
            'last_publish_age_s': age,
            'last_source_skew_s': self._last_source_skew_s,
            'last_rgb_shape': self._last_rgb_shape,
            'last_depth_shape': self._last_depth_shape,
            'rgb_queue_size': len(self._rgb_frames),
            'depth_queue_size': len(self._depth_frames),
            'rgb_input_age_s': rgb_input_age,
            'depth_input_age_s': depth_input_age,
            'subscription_restarts': self._subscription_restarts,
            'last_rgb_bytes': self._last_rgb_bytes,
            'last_depth_bytes': self._last_depth_bytes,
            'transport': 'compressed_best_effort_depth_1',
        }
        self._status_pub.publish(String(data=json.dumps(payload)))


def main(args=None):
    from rclpy.executors import ExternalShutdownException

    rclpy.init(args=args)
    node = SemanticStreamRelay()
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
