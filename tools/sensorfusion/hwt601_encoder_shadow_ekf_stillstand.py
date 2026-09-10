#!/usr/bin/env python3
"""Observe the isolated HWT601/encoder EKF at proven standstill."""

from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
import csv
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Mapping, Sequence

import hwt601_encoder_shadow_stillstand as direct


EKF_TOPIC = '/shadow/hwt601/odom'
EXPECTED_NODES = frozenset({
    '/hwt601_encoder_shadow_stillstand_observer',
    '/hwt601_encoder_shadow_reader',
    '/hwt601_shadow',
    '/hwt601_shadow_reader',
    '/hwt601_encoder_shadow_ekf',
})
EXPECTED_PUBLISHERS = {
    direct.HWT_RAW_IMU_TOPIC: '/hwt601_shadow_reader',
    direct.IMU_TOPIC: '/hwt601_shadow',
    direct.WHEEL_TOPIC: '/hwt601_encoder_shadow_reader',
    direct.HWT_STATUS_TOPIC: '/hwt601_shadow',
    direct.HWT_RAW_STATUS_TOPIC: '/hwt601_shadow_reader',
    direct.ENCODER_STATUS_TOPIC: '/hwt601_encoder_shadow_reader',
    EKF_TOPIC: '/hwt601_encoder_shadow_ekf',
}
FORBIDDEN_TOPICS = (
    '/odom', '/map', '/tf', '/tf_static', '/cmd_vel',
    '/cmd_vel_smoothed', '/fusion/imu', '/fusion/wheel_odom',
)
MIN_EKF_RATE_HZ = 25.0
MAX_EKF_GAP_S = 0.10
MAX_TRANSLATION_M = 0.001
MAX_ANGLE_DEG = 1.0
MAX_SPEED_MPS = 0.005
MAX_YAW_RATE_RADPS = 0.005
STARTUP_TIMEOUT_S = 60.0
POST_STATUS_TIMEOUT_S = 2.0
TRANSFORM_LISTENER_PREFIX = '/transform_listener_impl_'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _finite(values) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def _qualified(name: str, namespace: str) -> str:
    return f'{namespace.rstrip("/")}/{name}'.replace('//', '/')


def _unexpected_non_cli_nodes(nodes) -> set[str]:
    """Return real nodes outside sources, EKF and its private TF listener."""
    return {
        node for node in set(nodes) - EXPECTED_NODES
        if not node.startswith('/_ros2cli_')
        and not node.startswith(TRANSFORM_LISTENER_PREFIX)
    }


def _complete_expected_node_set(nodes) -> bool:
    meaningful = {
        node for node in nodes if not node.startswith('/_ros2cli_')}
    listeners = {
        node for node in meaningful
        if node.startswith(TRANSFORM_LISTENER_PREFIX)}
    return bool(
        len(listeners) == 1
        and meaningful - listeners == EXPECTED_NODES
    )


def _passed(summary: Mapping[str, object]) -> bool:
    ekf = summary.get('ekf')
    sources = summary.get('sources')
    graph = summary.get('graph')
    direct_result = summary.get('direct_comparison')
    if not all(isinstance(value, Mapping) for value in (
        ekf, sources, graph, direct_result,
    )):
        return False
    assert isinstance(ekf, Mapping)
    assert isinstance(sources, Mapping)
    assert isinstance(graph, Mapping)
    assert isinstance(direct_result, Mapping)
    return bool(
        summary.get('complete') is True
        and not summary.get('faults')
        and float(ekf.get('duration_s', 0.0))
        >= float(summary.get('requested_duration_s', math.inf))
        and float(ekf.get('rate_hz', 0.0)) >= MIN_EKF_RATE_HZ
        and float(ekf.get('maximum_stamp_gap_s', math.inf))
        <= MAX_EKF_GAP_S
        and float(ekf.get('peak_translation_from_start_m', math.inf))
        < MAX_TRANSLATION_M
        and abs(float(ekf.get('final_yaw_deg', math.inf))) < MAX_ANGLE_DEG
        and float(ekf.get('peak_absolute_yaw_deg', math.inf)) < MAX_ANGLE_DEG
        and float(ekf.get('peak_absolute_linear_velocity_mps', math.inf))
        < MAX_SPEED_MPS
        and float(ekf.get('peak_absolute_yaw_rate_radps', math.inf))
        < MAX_YAW_RATE_RADPS
        and float(direct_result.get('peak_translation_m', math.inf))
        < MAX_TRANSLATION_M
        and abs(float(direct_result.get('hwt_angle_deg', math.inf)))
        < MAX_ANGLE_DEG
        and abs(float(direct_result.get('encoder_angle_deg', math.inf)))
        < MAX_ANGLE_DEG
        and all(sources.get(key) is True for key in (
            'hwt_valid', 'hwt_raw_valid', 'encoder_valid',
            'post_window_fresh',
        ))
        and graph.get('valid') is True
        and graph.get('forbidden_publishers_absent') is True
    )


def _run(duration_s: float, output: Path) -> int:
    import rclpy
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from rclpy.qos import (
        DurabilityPolicy,
        HistoryPolicy,
        QoSProfile,
        ReliabilityPolicy,
    )
    from sensor_msgs.msg import Imu
    from std_msgs.msg import String

    output.mkdir(parents=True, exist_ok=False)
    csv_path = output / 'samples.csv'
    summary_path = output / 'summary.json'
    reliable_qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=200,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )

    class Observer(Node):
        def __init__(self, writer: csv.writer) -> None:
            # This established name is the source wrapper's passive-observer
            # gate.  The EKF observer still has no publisher or hardware path.
            super().__init__('hwt601_encoder_shadow_stillstand_observer')
            self.writer = writer
            self.started_at = time.monotonic()
            self.faults: list[str] = []
            self.imu_samples: list[direct.ImuYawSample] = []
            self.wheel_samples: list[direct.WheelPoseSample] = []
            self.ekf_samples: list[dict[str, float]] = []
            self.ekf_received: list[float] = []
            self.statuses: dict[str, dict[str, object]] = {}
            self.status_received: dict[str, float] = {}
            self.graph_valid = False
            self.graph_nodes: list[str] = []
            self.graph_publishers: dict[str, list[str]] = {}
            self.endpoint_baseline: dict[str, list[str]] | None = None
            self.maximum_graph_gap_s = 0.0
            self.last_graph_check_s: float | None = None
            self.measurement_start_index: int | None = None
            self.measurement_end_index: int | None = None
            self.measurement_end_received_s: float | None = None
            self.create_subscription(
                Imu, direct.IMU_TOPIC, self._on_imu, reliable_qos)
            self.create_subscription(
                Odometry, direct.WHEEL_TOPIC, self._on_wheel, reliable_qos)
            self.create_subscription(
                Odometry, EKF_TOPIC, self._on_ekf, reliable_qos)
            self.create_subscription(
                String, direct.HWT_STATUS_TOPIC,
                lambda msg: self._on_status('hwt', msg), 10)
            self.create_subscription(
                String, direct.HWT_RAW_STATUS_TOPIC,
                lambda msg: self._on_status('hwt_raw', msg), 10)
            self.create_subscription(
                String, direct.ENCODER_STATUS_TOPIC,
                lambda msg: self._on_status('encoder', msg), 10)

        def latch(self, reason: str) -> None:
            if reason not in self.faults:
                self.faults.append(reason)

        def _on_status(self, source: str, message: String) -> None:
            try:
                payload = json.loads(message.data)
            except (json.JSONDecodeError, TypeError):
                self.latch(f'{source}_status_json_ungueltig')
                return
            if not isinstance(payload, dict):
                self.latch(f'{source}_status_json_ungueltig')
                return
            validator = {
                'hwt': direct.validate_hwt_status,
                'hwt_raw': direct.validate_raw_hwt_status,
                'encoder': direct.validate_encoder_status,
            }[source]
            violation = validator(payload, require_ready=False)
            if violation is not None:
                self.latch(violation)
            self.statuses[source] = payload
            self.status_received[source] = time.monotonic()

        def _on_imu(self, message: Imu) -> None:
            stamp = float(message.header.stamp.sec) + 1e-9 * float(
                message.header.stamp.nanosec)
            if (
                message.header.frame_id != direct.IMU_FRAME
                or not math.isfinite(stamp)
                or not math.isfinite(message.angular_velocity.z)
            ):
                self.latch('imu_ungueltig')
                return
            self.imu_samples.append(direct.ImuYawSample(
                stamp, float(message.angular_velocity.z)))
            self.writer.writerow((
                'imu', time.monotonic(), stamp, '', '', '',
                message.angular_velocity.z, '', '',
            ))

        def _on_wheel(self, message: Odometry) -> None:
            stamp = float(message.header.stamp.sec) + 1e-9 * float(
                message.header.stamp.nanosec)
            pose = message.pose.pose
            try:
                yaw = direct.quaternion_to_planar_yaw(
                    pose.orientation.x, pose.orientation.y,
                    pose.orientation.z, pose.orientation.w)
            except direct.AnalysisError as error:
                self.latch(str(error))
                return
            values = (
                stamp, pose.position.x, pose.position.y,
                message.twist.twist.linear.x,
                message.twist.twist.angular.z,
            )
            if (
                message.header.frame_id != direct.ODOM_FRAME
                or message.child_frame_id != direct.BASE_FRAME
                or not _finite(values)
            ):
                self.latch('encoder_ungueltig')
                return
            sample = direct.WheelPoseSample(
                stamp, float(pose.position.x), float(pose.position.y), yaw,
                float(message.twist.twist.linear.x),
                float(message.twist.twist.angular.z))
            self.wheel_samples.append(sample)
            self.writer.writerow((
                'encoder', time.monotonic(), stamp, sample.x_m, sample.y_m,
                sample.yaw_rad, '', sample.linear_velocity_mps,
                sample.angular_velocity_radps,
            ))

        def _on_ekf(self, message: Odometry) -> None:
            received = time.monotonic()
            stamp = float(message.header.stamp.sec) + 1e-9 * float(
                message.header.stamp.nanosec)
            pose = message.pose.pose
            twist = message.twist.twist
            try:
                yaw = direct.quaternion_to_planar_yaw(
                    pose.orientation.x, pose.orientation.y,
                    pose.orientation.z, pose.orientation.w,
                    planar_tolerance=1e-5)
            except direct.AnalysisError as error:
                self.latch(f'ekf_{error}')
                return
            values = (
                stamp, pose.position.x, pose.position.y, pose.position.z,
                twist.linear.x, twist.linear.y, twist.linear.z,
                twist.angular.x, twist.angular.y, twist.angular.z,
                *message.pose.covariance, *message.twist.covariance,
            )
            relevant_covariance = (
                message.pose.covariance[0], message.pose.covariance[7],
                message.pose.covariance[35], message.twist.covariance[0],
                message.twist.covariance[35],
            )
            if (
                message.header.frame_id != direct.ODOM_FRAME
                or message.child_frame_id != direct.BASE_FRAME
                or not _finite(values)
                or not all(value >= 0.0 for value in relevant_covariance)
            ):
                self.latch('ekf_frame_wert_oder_kovarianz_ungueltig')
                return
            if self.ekf_samples and stamp <= self.ekf_samples[-1]['stamp_s']:
                self.latch('ekf_zeitstempel_nicht_monoton')
                return
            self.ekf_samples.append({
                'stamp_s': stamp,
                'x_m': float(pose.position.x),
                'y_m': float(pose.position.y),
                'yaw_rad': yaw,
                'vx_mps': float(twist.linear.x),
                'wz_radps': float(twist.angular.z),
            })
            self.ekf_received.append(received)
            self.writer.writerow((
                'ekf', received, stamp, pose.position.x, pose.position.y,
                yaw, '', twist.linear.x, twist.angular.z,
            ))

        @staticmethod
        def _endpoint_token(info) -> str:
            return (
                f'{_qualified(info.node_name, info.node_namespace)}@'
                f'{bytes(info.endpoint_gid).hex()}'
            )

        def check_graph(self) -> None:
            now = time.monotonic()
            if (
                self.last_graph_check_s is not None
                and now - self.last_graph_check_s < 0.5
            ):
                return
            if self.last_graph_check_s is not None:
                self.maximum_graph_gap_s = max(
                    self.maximum_graph_gap_s,
                    now - self.last_graph_check_s)
            self.last_graph_check_s = now
            nodes = sorted(
                _qualified(name, namespace)
                for name, namespace in self.get_node_names_and_namespaces())
            self.graph_nodes = nodes
            unexpected = set(nodes) - EXPECTED_NODES
            if _unexpected_non_cli_nodes(nodes):
                self.latch('ros_graph_nodes_unerwartet')
                return
            listeners = {
                node for node in unexpected
                if node.startswith(TRANSFORM_LISTENER_PREFIX)}
            if len(listeners) > 1:
                self.latch('ros_graph_transform_listener_mehrdeutig')
                return
            if not _complete_expected_node_set(nodes):
                return
            publishers: dict[str, list[str]] = {}
            endpoint_ids: dict[str, list[str]] = {}
            for topic in tuple(EXPECTED_PUBLISHERS) + FORBIDDEN_TOPICS:
                infos = list(self.get_publishers_info_by_topic(topic))
                publishers[topic] = sorted(
                    _qualified(info.node_name, info.node_namespace)
                    for info in infos)
                endpoint_ids[topic] = sorted(
                    self._endpoint_token(info) for info in infos)
            self.graph_publishers = publishers
            for topic, expected in EXPECTED_PUBLISHERS.items():
                if publishers[topic] != [expected]:
                    self.latch(f'ros_graph_publisher_unerwartet:{topic}')
            for topic in FORBIDDEN_TOPICS:
                if publishers[topic]:
                    self.latch(f'ros_graph_verbotener_publisher:{topic}')
            if self.faults:
                return
            if self.endpoint_baseline is None:
                self.endpoint_baseline = endpoint_ids
            elif endpoint_ids != self.endpoint_baseline:
                self.latch('ros_graph_publisher_instanz_gewechselt')
            self.graph_valid = not self.faults

        def sources_ready(self) -> bool:
            if set(self.statuses) != {'hwt', 'hwt_raw', 'encoder'}:
                return False
            validators = (
                direct.validate_hwt_status(
                    self.statuses['hwt'], require_ready=True),
                direct.validate_raw_hwt_status(
                    self.statuses['hwt_raw'], require_ready=True),
                direct.validate_encoder_status(
                    self.statuses['encoder'], require_ready=True),
            )
            return all(value is None for value in validators)

        def update_window(self) -> None:
            if self.measurement_end_index is not None:
                return
            if (
                self.measurement_start_index is None
                and self.graph_valid
                and self.sources_ready()
                and self.ekf_samples
            ):
                self.measurement_start_index = len(self.ekf_samples) - 1
            if self.measurement_start_index is None or not self.ekf_samples:
                return
            start_index = self.measurement_start_index
            latest = len(self.ekf_samples) - 1
            stamp_duration = (
                self.ekf_samples[latest]['stamp_s']
                - self.ekf_samples[start_index]['stamp_s'])
            receive_duration = (
                self.ekf_received[latest] - self.ekf_received[start_index])
            if stamp_duration >= duration_s and receive_duration >= duration_s:
                self.measurement_end_index = latest
                self.measurement_end_received_s = self.ekf_received[latest]

        def post_status_fresh(self) -> bool:
            if self.measurement_end_received_s is None:
                return False
            return all(
                self.status_received.get(source, -math.inf)
                > self.measurement_end_received_s
                for source in ('hwt', 'hwt_raw', 'encoder'))

    rclpy.init()
    node = None
    with csv_path.open('x', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow((
            'kind', 'received_monotonic_s', 'stamp_s', 'x_m', 'y_m',
            'yaw_rad', 'yaw_rate_radps', 'linear_velocity_mps',
            'angular_velocity_radps',
        ))
        node = Observer(writer)
        deadline = time.monotonic() + STARTUP_TIMEOUT_S + duration_s + 5.0
        next_progress = time.monotonic() + 30.0
        while time.monotonic() < deadline and not node.faults:
            rclpy.spin_once(node, timeout_sec=0.05)
            node.check_graph()
            node.update_window()
            if node.measurement_end_index is not None:
                if node.post_status_fresh():
                    break
                assert node.measurement_end_received_s is not None
                if (
                    time.monotonic() - node.measurement_end_received_s
                    > POST_STATUS_TIMEOUT_S
                ):
                    node.latch('abschlussstatus_nach_messende_timeout')
                    break
            if (
                node.measurement_start_index is None
                and time.monotonic() - node.started_at > STARTUP_TIMEOUT_S
            ):
                node.latch('ekf_oder_quellen_nicht_rechtzeitig_bereit')
                break
            if time.monotonic() >= next_progress:
                observed = 0.0
                if node.measurement_start_index is not None:
                    observed = (
                        node.ekf_samples[-1]['stamp_s']
                        - node.ekf_samples[
                            node.measurement_start_index]['stamp_s'])
                print(
                    f'EKF-Fortschritt {observed:.1f}/{duration_s:.1f} s; '
                    f'Proben={len(node.ekf_samples)}',
                    flush=True)
                next_progress += 30.0

    assert node is not None
    if node.measurement_start_index is None:
        node.latch('ekf_messstart_fehlt')
    if node.measurement_end_index is None:
        node.latch('ekf_messende_fehlt')
    ekf_result: dict[str, object] | None = None
    direct_result: dict[str, object] | None = None
    if (
        node.measurement_start_index is not None
        and node.measurement_end_index is not None
    ):
        selected = node.ekf_samples[
            node.measurement_start_index:node.measurement_end_index + 1]
        received = node.ekf_received[
            node.measurement_start_index:node.measurement_end_index + 1]
        yaws = [0.0]
        for before, after in zip(selected, selected[1:]):
            yaws.append(yaws[-1] + direct.normalize_angle(
                after['yaw_rad'] - before['yaw_rad']))
        first = selected[0]
        stamp_gaps = [
            after['stamp_s'] - before['stamp_s']
            for before, after in zip(selected, selected[1:])]
        receive_gaps = [
            after - before for before, after in zip(received, received[1:])]
        duration = selected[-1]['stamp_s'] - first['stamp_s']
        ekf_result = {
            'samples': len(selected),
            'duration_s': duration,
            'monotonic_duration_s': received[-1] - received[0],
            'rate_hz': (len(selected) - 1) / duration,
            'maximum_stamp_gap_s': max(stamp_gaps),
            'maximum_receive_gap_s': max(receive_gaps),
            'initial_x_m': first['x_m'],
            'initial_y_m': first['y_m'],
            'peak_translation_from_start_m': max(
                math.hypot(
                    sample['x_m'] - first['x_m'],
                    sample['y_m'] - first['y_m'])
                for sample in selected),
            'final_yaw_deg': math.degrees(yaws[-1]),
            'peak_absolute_yaw_deg': math.degrees(
                max(abs(value) for value in yaws)),
            'peak_absolute_linear_velocity_mps': max(
                abs(sample['vx_mps']) for sample in selected),
            'peak_absolute_yaw_rate_radps': max(
                abs(sample['wz_radps']) for sample in selected),
        }
        start_stamp = selected[0]['stamp_s']
        end_stamp = selected[-1]['stamp_s']
        imu_stamps = [sample.stamp_s for sample in node.imu_samples]
        wheel_stamps = [sample.stamp_s for sample in node.wheel_samples]
        wheel_start = bisect_left(wheel_stamps, start_stamp)
        wheel_end = bisect_right(wheel_stamps, end_stamp) - 1
        if wheel_start < wheel_end:
            imu_start = max(
                0, bisect_right(
                    imu_stamps, node.wheel_samples[wheel_start].stamp_s) - 1)
            imu_end = bisect_left(
                imu_stamps, node.wheel_samples[wheel_end].stamp_s)
            if imu_end < len(node.imu_samples):
                try:
                    comparison = direct.compare_angles(
                        node.imu_samples[imu_start:imu_end + 1],
                        node.wheel_samples[wheel_start:wheel_end + 1])
                    direct_result = {
                        'duration_s': comparison.duration_s,
                        'hwt_angle_deg': math.degrees(
                            comparison.hwt_angle_rad),
                        'encoder_angle_deg': math.degrees(
                            comparison.encoder_angle_rad),
                        'peak_translation_m': (
                            comparison
                            .peak_translation_from_encoder_baseline_m),
                        'hwt_minus_ekf_deg': (
                            math.degrees(comparison.hwt_angle_rad)
                            - float(ekf_result['final_yaw_deg'])),
                    }
                except direct.AnalysisError as error:
                    node.latch(str(error))
        if direct_result is None:
            node.latch('direktvergleich_fehlt')

    now = time.monotonic()
    source_validity = {
        'hwt_valid': False,
        'hwt_raw_valid': False,
        'encoder_valid': False,
        'post_window_fresh': node.post_status_fresh(),
    }
    validators = {
        'hwt': direct.validate_hwt_status,
        'hwt_raw': direct.validate_raw_hwt_status,
        'encoder': direct.validate_encoder_status,
    }
    for source, validator in validators.items():
        status = node.statuses.get(source)
        fresh = now - node.status_received.get(source, -math.inf) <= 1.0
        key = f'{source}_valid'
        if status is not None and fresh:
            violation = validator(status, require_ready=True)
            if violation is None:
                source_validity[key] = True
            else:
                node.latch(violation)
        else:
            node.latch(f'{source}_status_fehlt_oder_veraltet')
    forbidden_absent = all(
        not node.graph_publishers.get(topic, [])
        for topic in FORBIDDEN_TOPICS)
    summary: dict[str, object] = {
        'complete': ekf_result is not None and direct_result is not None,
        'requested_duration_s': duration_s,
        'observer_only': True,
        'ekf': ekf_result,
        'direct_comparison': direct_result,
        'sources': {
            **source_validity,
            'statuses': node.statuses,
        },
        'graph': {
            'valid': node.graph_valid and node.maximum_graph_gap_s <= 1.0,
            'nodes': node.graph_nodes,
            'publishers': node.graph_publishers,
            'maximum_check_gap_s': node.maximum_graph_gap_s,
            'forbidden_publishers_absent': forbidden_absent,
        },
        'faults': node.faults,
        'samples_sha256': _sha256(csv_path),
    }
    summary['passed'] = _passed(summary)
    summary_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False) + '\n',
        encoding='utf-8')
    print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return 0 if summary['passed'] else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=120.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or args.duration < 30.0:
        parser.error('--duration muss endlich und mindestens 30 s sein')
    return _run(args.duration, args.output)


if __name__ == '__main__':
    raise SystemExit(main())
