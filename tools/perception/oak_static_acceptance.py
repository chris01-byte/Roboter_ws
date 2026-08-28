#!/usr/bin/env python3
"""Motorless OAK object acceptance using semantic diagnostic topics only."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def evaluate_samples(
        samples, *, minimum_samples: int, minimum_confidence: float,
        maximum_spread_m: float):
    reasons = []
    if len(samples) < minimum_samples:
        reasons.append(
            f'nur {len(samples)} statt {minimum_samples} frische Detektionen')
    valid = []
    for sample in samples:
        point = sample.get('base_point')
        confidence = sample.get('confidence')
        camera = sample.get('camera_point')
        if (
                not isinstance(point, list) or len(point) != 3 or
                not isinstance(camera, list) or len(camera) != 3 or
                not isinstance(confidence, (int, float)) or
                not all(isinstance(value, (int, float)) and math.isfinite(value)
                        for value in point + camera) or
                not math.isfinite(float(confidence))):
            reasons.append('mindestens eine Detektion hat keine gueltige 3D-Pose')
            continue
        if float(confidence) < minimum_confidence:
            reasons.append(
                f'Konfidenz {float(confidence):.3f} unter {minimum_confidence:.3f}')
        depth_m = float(camera[2])
        if not 0.15 <= depth_m <= 5.0:
            reasons.append(f'unplausible Kameratiefe {depth_m:.3f} m')
        valid.append((point, float(confidence), depth_m))

    median = None
    maximum_spread = None
    if valid:
        median = [statistics.median(item[0][axis] for item in valid)
                  for axis in range(3)]
        maximum_spread = max(math.dist(item[0], median) for item in valid)
        if maximum_spread > maximum_spread_m:
            reasons.append(
                f'3D-Streuung {maximum_spread:.3f} m ueber {maximum_spread_m:.3f} m')
    return {
        'passed': not reasons,
        'sample_count': len(samples),
        'valid_3d_count': len(valid),
        'median_base_point_m': median,
        'maximum_spread_m': maximum_spread,
        'minimum_confidence': (
            min((item[1] for item in valid), default=None)),
        'median_depth_m': (
            statistics.median(item[2] for item in valid) if valid else None),
        'reasons': sorted(set(reasons)),
    }


def evaluate_stream_statuses(
        statuses, *, expected_profile: str, expected_width: int,
        expected_height: int, last_status_age_s: float):
    reasons = []
    if len(statuses) < 2:
        reasons.append('weniger als zwei frische Stream-Statusmeldungen')
    latest = statuses[-1] if statuses else None
    if latest is None:
        return {'passed': False, 'reasons': reasons, 'latest': None}
    if last_status_age_s > 2.0:
        reasons.append(f'letzter Stream-Status ist {last_status_age_s:.2f} s alt')
    if latest.get('schema_version') != 1 or latest.get('ready') is not True:
        reasons.append('Semantik-RGB-D-Stream ist nicht bereit')
    if latest.get('profile_name') != expected_profile:
        reasons.append(
            f"Profil {latest.get('profile_name')!r} statt {expected_profile!r}")
    expected_rgb = [expected_height, expected_width, 3]
    expected_depth = [expected_height, expected_width]
    if latest.get('last_rgb_shape') != expected_rgb:
        reasons.append(
            f"RGB-Groesse {latest.get('last_rgb_shape')!r} statt {expected_rgb!r}")
    if latest.get('last_depth_shape') != expected_depth:
        reasons.append(
            f"Tiefengroesse {latest.get('last_depth_shape')!r} statt {expected_depth!r}")
    published = [item.get('pairs_published') for item in statuses]
    if (
            any(isinstance(value, bool) or not isinstance(value, int)
                for value in published) or
            published[-1] <= published[0]):
        reasons.append('Bildpaarzaehler ist nicht fortgeschritten')
    return {'passed': not reasons, 'reasons': reasons, 'latest': latest}


class AcceptanceNode(Node):
    def __init__(self, object_name: str):
        super().__init__('oak_static_acceptance')
        self.object_name = object_name.casefold()
        self.samples = []
        self.seen_times = set()
        self.stream_statuses = []
        self.last_stream_status_received_s = 0.0
        self.create_subscription(
            String, '/semantic/observation_status_json',
            self._on_observation, 1)
        self.create_subscription(
            String, '/oak/semantic/stream_status_json',
            self._on_stream, 1)

    def _on_observation(self, message):
        try:
            payload = json.loads(message.data)
        except ValueError:
            return
        if payload.get('schema_version') != 1:
            return
        for entry in payload.get('observations', []):
            if str(entry.get('name', '')).casefold() != self.object_name:
                continue
            seen_time = entry.get('last_seen_time')
            if seen_time in self.seen_times:
                continue
            self.seen_times.add(seen_time)
            self.samples.append(entry)

    def _on_stream(self, message):
        try:
            status = json.loads(message.data)
        except ValueError:
            return
        if not isinstance(status, dict):
            return
        self.stream_statuses.append(status)
        self.last_stream_status_received_s = time.monotonic()


def main():
    parser = argparse.ArgumentParser(
        description='Motorloser OAK-Abnahmetest ohne Bildspeicherung')
    parser.add_argument('--object', default='Tasse')
    parser.add_argument('--position', default='unbenannt')
    parser.add_argument('--duration-s', type=float, default=12.0)
    parser.add_argument('--minimum-samples', type=int, default=3)
    parser.add_argument('--minimum-confidence', type=float, default=0.35)
    parser.add_argument('--maximum-spread-m', type=float, default=0.20)
    parser.add_argument('--expected-profile', default='standard')
    parser.add_argument('--expected-width', type=int, default=320)
    parser.add_argument('--expected-height', type=int, default=180)
    parser.add_argument(
        '--report-directory',
        default='~/.local/share/amadeus/diagnostics/oak-object-acceptance')
    args = parser.parse_args()
    if (
            args.duration_s <= 0.0 or args.minimum_samples < 1 or
            args.expected_width < 1 or args.expected_height < 1):
        parser.error('Dauer, Mindestzahl und Bildgroesse muessen positiv sein')

    rclpy.init()
    node = AcceptanceNode(args.object)
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.duration_s:
            rclpy.spin_once(node, timeout_sec=0.2)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    result = evaluate_samples(
        node.samples,
        minimum_samples=args.minimum_samples,
        minimum_confidence=args.minimum_confidence,
        maximum_spread_m=args.maximum_spread_m,
    )
    last_status_age_s = (
        math.inf if node.last_stream_status_received_s <= 0.0 else
        max(0.0, time.monotonic() - node.last_stream_status_received_s))
    stream_result = evaluate_stream_statuses(
        node.stream_statuses,
        expected_profile=args.expected_profile,
        expected_width=args.expected_width,
        expected_height=args.expected_height,
        last_status_age_s=last_status_age_s,
    )
    if not stream_result['passed']:
        result['passed'] = False
        result['reasons'].extend(stream_result['reasons'])
        result['reasons'] = sorted(set(result['reasons']))
    latest_stream = stream_result['latest']
    result.update({
        'schema_version': 1,
        'object': args.object,
        'position': args.position,
        'duration_s': args.duration_s,
        'stream_ready': stream_result['passed'],
        'expected_stream_profile': args.expected_profile,
        'stream_status_count': len(node.stream_statuses),
        'last_stream_status_age_s': last_status_age_s,
        'stream_shape': (
            None if latest_stream is None
            else latest_stream.get('last_rgb_shape')),
        'time': time.time(),
    })

    directory = Path(args.report_directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / (
        f"{time.strftime('%Y%m%dT%H%M%S')}-{args.position}.json")
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    print(json.dumps({**result, 'report_path': str(report_path)},
                     ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
