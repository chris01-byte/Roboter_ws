#!/usr/bin/env python3
"""Record and evaluate the isolated HWT601 yaw shadow at standstill."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String


IMU_TOPIC = '/shadow/hwt601/imu/yaw_rate'
STATUS_TOPIC = '/shadow/hwt601/status_json'
RAW_STATUS_TOPIC = '/shadow/hwt601/raw_status_json'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class ShadowObserver(Node):
    def __init__(self, writer):
        super().__init__('hwt601_shadow_stillstand_observer')
        self.writer = writer
        self.first_stamp_s = None
        self.last_stamp_s = None
        self.last_z = None
        self.samples = 0
        self.mean_z = 0.0
        self.m2_z = 0.0
        self.integral_rad = 0.0
        self.peak_integral_rad = 0.0
        self.maximum_gap_s = 0.0
        self.invalid_messages = 0
        self.latest_status = None
        self.latest_raw_status = None
        self.create_subscription(
            Imu, IMU_TOPIC, self._on_imu, qos_profile_sensor_data)
        self.create_subscription(String, STATUS_TOPIC, self._on_status, 10)
        self.create_subscription(
            String, RAW_STATUS_TOPIC, self._on_raw_status, 10)

    @staticmethod
    def _decode_status(message):
        try:
            return json.loads(message.data)
        except (json.JSONDecodeError, TypeError):
            return None

    def _on_status(self, message):
        self.latest_status = self._decode_status(message)

    def _on_raw_status(self, message):
        self.latest_raw_status = self._decode_status(message)

    def _on_imu(self, message):
        stamp_s = float(message.header.stamp.sec) + 1e-9 * float(
            message.header.stamp.nanosec)
        z = float(message.angular_velocity.z)
        valid = (
            message.header.frame_id == 'base_link'
            and math.isfinite(stamp_s)
            and stamp_s > 0.0
            and math.isfinite(z)
            and message.orientation_covariance[0] == -1.0
            and message.linear_acceleration_covariance[0] == -1.0
            and math.isclose(
                message.angular_velocity_covariance[8], 5.0e-7,
                rel_tol=0.0, abs_tol=1e-15))
        if not valid:
            self.invalid_messages += 1
            return
        if self.last_stamp_s is not None and stamp_s <= self.last_stamp_s:
            self.invalid_messages += 1
            return
        if self.first_stamp_s is None:
            self.first_stamp_s = stamp_s
        elapsed_s = stamp_s - self.first_stamp_s
        if self.last_stamp_s is not None:
            gap_s = stamp_s - self.last_stamp_s
            self.maximum_gap_s = max(self.maximum_gap_s, gap_s)
            self.integral_rad += 0.5 * (self.last_z + z) * gap_s
            self.peak_integral_rad = max(
                self.peak_integral_rad, abs(self.integral_rad))
        self.last_stamp_s = stamp_s
        self.last_z = z
        self.samples += 1
        delta = z - self.mean_z
        self.mean_z += delta / self.samples
        self.m2_z += delta * (z - self.mean_z)
        self.writer.writerow((elapsed_s, stamp_s, z))


def _passed(summary):
    shadow = summary.get('shadow_status') or {}
    raw = summary.get('raw_status') or {}
    bias = shadow.get('bias') or {}
    return bool(
        summary['samples'] >= 48000
        and summary['duration_s'] >= summary['requested_duration_s'] - 0.05
        and summary['rate_hz'] >= 80.0
        and summary['maximum_gap_s'] <= 0.10
        and summary['invalid_messages'] == 0
        and abs(summary['integral_deg']) < 1.0
        and summary['peak_absolute_integral_deg'] < 1.0
        and shadow.get('ready') is True
        and shadow.get('fusion_ready') is False
        and shadow.get('latched_fault') is None
        and shadow.get('rejected') == 0
        and bias.get('adaptation_samples') == 0
        and raw.get('ready') is True
        and raw.get('rejected') == 0
        and raw.get('reconnects') == 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=600.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration < 10.0:
        raise SystemExit('--duration muss mindestens 10 s sein')
    args.output.mkdir(parents=True, exist_ok=False)
    csv_path = args.output / 'samples.csv'
    summary_path = args.output / 'summary.json'

    rclpy.init()
    with csv_path.open('x', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(('elapsed_s', 'stamp_s', 'yaw_rate_radps'))
        node = ShadowObserver(writer)
        deadline = time.monotonic() + args.duration + 45.0
        next_progress = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if (
                    node.first_stamp_s is not None
                    and node.last_stamp_s - node.first_stamp_s
                    >= args.duration):
                break
            if time.monotonic() >= next_progress:
                observed = (
                    0.0 if node.first_stamp_s is None
                    else node.last_stamp_s - node.first_stamp_s)
                print(
                    f'Fortschritt {observed:.1f}/{args.duration:.1f} s, '
                    f'Proben={node.samples}, '
                    f'Integral={math.degrees(node.integral_rad):+.4f} Grad',
                    flush=True)
                next_progress += 60.0

    duration_s = (
        0.0 if node.first_stamp_s is None
        else node.last_stamp_s - node.first_stamp_s)
    rate_hz = (
        0.0 if duration_s <= 0.0
        else (node.samples - 1) / duration_s)
    stddev_z = (
        0.0 if node.samples < 2
        else math.sqrt(node.m2_z / (node.samples - 1)))
    summary = {
        'complete': duration_s >= args.duration - 0.05,
        'requested_duration_s': args.duration,
        'duration_s': duration_s,
        'samples': node.samples,
        'rate_hz': rate_hz,
        'maximum_gap_s': node.maximum_gap_s,
        'invalid_messages': node.invalid_messages,
        'yaw_rate_mean_radps': node.mean_z,
        'yaw_rate_stddev_radps': stddev_z,
        'integral_deg': math.degrees(node.integral_rad),
        'peak_absolute_integral_deg': math.degrees(node.peak_integral_rad),
        'shadow_status': node.latest_status,
        'raw_status': node.latest_raw_status,
        'samples_sha256': _sha256(csv_path),
    }
    summary['passed'] = _passed(summary)
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    node.destroy_node()
    rclpy.shutdown()
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
