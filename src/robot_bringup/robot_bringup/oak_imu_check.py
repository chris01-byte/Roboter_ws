#!/usr/bin/env python3
"""Motorloser Akzeptanztest fuer den OAK-IMU-Datenstrom."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
import statistics
import sys
import time
from typing import Iterable

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Imu


@dataclass(frozen=True)
class ImuSample:
    received_s: float
    stamp_ns: int
    frame_id: str
    acceleration: tuple[float, float, float]
    angular_velocity: tuple[float, float, float]


def _rate(count: int, span_s: float) -> float:
    return (count - 1) / span_s if count > 1 and span_s > 0.0 else 0.0


def evaluate_samples(
    samples: Iterable[ImuSample],
    *,
    min_rate_hz: float,
    max_rate_hz: float,
    expected_frame: str,
) -> tuple[dict[str, object], list[str]]:
    """Wertet echte Daten aus; ein vorhandener Publisher allein reicht nicht."""
    values = list(samples)
    errors: list[str] = []
    result: dict[str, object] = {'messages': len(values)}
    if len(values) < 2:
        return result, ['weniger als zwei IMU-Nachrichten empfangen']

    receipt_span_s = values[-1].received_s - values[0].received_s
    stamp_span_s = (values[-1].stamp_ns - values[0].stamp_ns) / 1e9
    receipt_rate_hz = _rate(len(values), receipt_span_s)
    stamp_rate_hz = _rate(len(values), stamp_span_s)
    result.update({
        'receipt_rate_hz': round(receipt_rate_hz, 3),
        'stamp_rate_hz': round(stamp_rate_hz, 3),
        'receipt_span_s': round(receipt_span_s, 3),
        'stamp_span_s': round(stamp_span_s, 3),
    })

    for label, rate in (
        ('Empfangsrate', receipt_rate_hz),
        ('Zeitstempelrate', stamp_rate_hz),
    ):
        if not min_rate_hz <= rate <= max_rate_hz:
            errors.append(
                f'{label} {rate:.1f} Hz ausserhalb '
                f'{min_rate_hz:.1f}..{max_rate_hz:.1f} Hz')

    non_increasing = sum(
        current.stamp_ns <= previous.stamp_ns
        for previous, current in zip(values, values[1:])
    )
    result['non_increasing_stamps'] = non_increasing
    if non_increasing:
        errors.append(f'{non_increasing} nicht steigende Sensorzeitstempel')

    frames = sorted({sample.frame_id for sample in values})
    result['frames'] = frames
    if frames != [expected_frame]:
        errors.append(
            f'Frame(s) {frames!r} statt ausschliesslich {expected_frame!r}')

    vectors = [
        component
        for sample in values
        for vector in (sample.acceleration, sample.angular_velocity)
        for component in vector
    ]
    if not all(math.isfinite(component) for component in vectors):
        errors.append('NaN oder unendlicher IMU-Messwert')

    acceleration_norms = [
        math.sqrt(sum(component * component for component in sample.acceleration))
        for sample in values
    ]
    median_acceleration = statistics.median(acceleration_norms)
    result['median_acceleration_m_s2'] = round(median_acceleration, 3)
    if not 5.0 <= median_acceleration <= 15.0:
        errors.append(
            f'unplausible mittlere Beschleunigung {median_acceleration:.2f} m/s^2')

    return result, errors


class ImuCollector(Node):
    def __init__(self, topic: str) -> None:
        super().__init__('oak_imu_acceptance')
        self.samples: list[ImuSample] = []
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=500,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.create_subscription(Imu, topic, self._on_imu, qos)

    def _on_imu(self, message: Imu) -> None:
        self.samples.append(ImuSample(
            received_s=time.monotonic(),
            stamp_ns=(message.header.stamp.sec * 1_000_000_000
                      + message.header.stamp.nanosec),
            frame_id=message.header.frame_id,
            acceleration=(
                message.linear_acceleration.x,
                message.linear_acceleration.y,
                message.linear_acceleration.z,
            ),
            angular_velocity=(
                message.angular_velocity.x,
                message.angular_velocity.y,
                message.angular_velocity.z,
            ),
        ))


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Prueft echte /oak/imu/data-Nachrichten, ohne Aktoren.')
    parser.add_argument('--topic', default='/oak/imu/data')
    parser.add_argument('--duration', type=float, default=5.0)
    parser.add_argument('--min-rate', type=float, default=80.0)
    parser.add_argument('--max-rate', type=float, default=130.0)
    parser.add_argument('--frame', default='oak_imu_frame')
    args = parser.parse_args(argv)
    if args.duration <= 0.0:
        parser.error('--duration muss groesser als null sein')
    if args.min_rate <= 0.0 or args.max_rate <= args.min_rate:
        parser.error('ungueltiger Frequenzbereich')
    return args


def main() -> None:
    args = _arguments(sys.argv[1:])
    # Der Checker braucht keine ROS-Remappings; eigene Optionen nicht an
    # rclpy weiterreichen.
    rclpy.init(args=[sys.argv[0]])
    node = ImuCollector(args.topic)
    deadline = time.monotonic() + args.duration
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        result, errors = evaluate_samples(
            node.samples,
            min_rate_hz=args.min_rate,
            max_rate_hz=args.max_rate,
            expected_frame=args.frame,
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()

    result['ok'] = not errors
    result['errors'] = errors
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == '__main__':
    main()
