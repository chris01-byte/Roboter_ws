#!/usr/bin/env python3
"""Record one bounded, motorless HWT diagnostic bag without reading a live DB.

Start this process before the sensor stack. It starts only ros2 bag record and
subscribes to ROS status topics; it never opens a serial port or starts motors.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from std_msgs.msg import String
import yaml


TOPICS = (
    '/shadow/hwt601/imu/data_raw',
    '/shadow/hwt601/imu/yaw_rate',
    '/shadow/hwt601/raw_status_json',
    '/shadow/hwt601/status_json',
    '/fusion/hwt601/wheel_odom_raw',
    '/shadow/hwt601/wheel_status_json',
    '/fusion/hwt601/status_json',
)
STATUS_TOPICS = (
    '/shadow/hwt601/raw_status_json',
    '/shadow/hwt601/status_json',
    '/shadow/hwt601/wheel_status_json',
    '/fusion/hwt601/status_json',
)
REPO = Path(__file__).resolve().parents[2]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--output', required=True, type=Path,
                        help='new bag directory outside the repository')
    result.add_argument('--warmup-limit-s', type=float, default=120.0,
                        help='maximum time from recorder start to bias readiness')
    result.add_argument('--window-s', type=float, default=120.0,
                        help='recording window after bias readiness')
    return result


def main():
    args = parser().parse_args()
    output = args.output.expanduser().resolve()
    if output == REPO or REPO in output.parents:
        parser().error('output must remain outside the repository')
    if output.exists():
        parser().error(f'bag output already exists: {output}')
    if args.warmup_limit_s <= 0 or args.window_s <= 0:
        parser().error('time limits must be positive')
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = output.with_name(output.name + '-recorder.log')
    summary_path = output.with_name(output.name + '-summary.json')
    info_path = output.with_name(output.name + '-info.txt')
    for path in (log_path, summary_path, info_path):
        if path.exists():
            parser().error(f'output already exists: {path}')

    summary = {
        'started_utc': utc_now(),
        'bag': str(output),
        'topics': list(TOPICS),
        'warmup_limit_s': args.warmup_limit_s,
        'window_s': args.window_s,
        'result': 'incomplete',
        'bias_ready_utc': None,
        'first_fault_observed': None,
        'recorder_exit_code': None,
    }
    node = None
    recorder = None
    ready_at = None
    recorder_subscribed = False
    reason = 'unknown'
    try:
        rclpy.init()
        node = rclpy.create_node('hwt_diagnostic_record_monitor')

        def on_yaw_status(message):
            nonlocal ready_at
            try:
                status = json.loads(message.data)
            except (TypeError, ValueError):
                return
            bias = status.get('bias') or {}
            if (ready_at is None and recorder_subscribed and
                    status.get('ready') is True and
                    status.get('operator_stationary_confirmed') is True and
                    bias.get('calibrated') is True):
                ready_at = time.monotonic()
                summary['bias_ready_utc'] = utc_now()

        def on_fusion_status(message):
            try:
                status = json.loads(message.data)
            except (TypeError, ValueError):
                return
            if summary['first_fault_observed'] is None and status.get('first_fault'):
                summary['first_fault_observed'] = status['first_fault']

        node.create_subscription(String, '/shadow/hwt601/status_json',
                                 on_yaw_status, 10)
        node.create_subscription(String, '/fusion/hwt601/status_json',
                                 on_fusion_status, 10)

        with log_path.open('x', encoding='utf-8') as recorder_log:
            recorder = subprocess.Popen(
                ['ros2', 'bag', 'record', '-o', str(output),
                 '--storage-preset-profile', 'resilient', *TOPICS],
                stdout=recorder_log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, env=os.environ.copy(),
            )
            summary['recorder_pid'] = recorder.pid
            started_at = time.monotonic()
            while True:
                rclpy.spin_once(node, timeout_sec=0.2)
                if recorder.poll() is not None:
                    reason = 'recorder_exited_early'
                    break
                # The text log is safe to read while rosbag owns its database.
                if not recorder_subscribed:
                    recorder_subscribed = 'All requested topics are subscribed' in log_path.read_text(
                        encoding='utf-8', errors='replace')
                now = time.monotonic()
                if ready_at is None and now - started_at >= args.warmup_limit_s:
                    reason = 'bias_readiness_timeout'
                    break
                if ready_at is not None and now - ready_at >= args.window_s:
                    reason = 'window_complete'
                    break

            if recorder.poll() is None:
                recorder.send_signal(signal.SIGINT)  # Direct child only; no process group.
            try:
                summary['recorder_exit_code'] = recorder.wait(timeout=30)
            except subprocess.TimeoutExpired:
                recorder.terminate()
                summary['recorder_exit_code'] = recorder.wait(timeout=10)
                reason = 'recorder_shutdown_timeout'
    except KeyboardInterrupt:
        reason = 'operator_interrupt'
    finally:
        if recorder is not None and recorder.poll() is None:
            recorder.send_signal(signal.SIGINT)
            try:
                summary['recorder_exit_code'] = recorder.wait(timeout=30)
            except subprocess.TimeoutExpired:
                recorder.terminate()
                summary['recorder_exit_code'] = recorder.wait(timeout=10)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        summary['ended_utc'] = utc_now()
        summary['stop_reason'] = reason
        summary['all_topics_subscribed'] = recorder_subscribed
        metadata_path = output / 'metadata.yaml'
        if metadata_path.is_file():
            metadata = yaml.safe_load(metadata_path.read_text(encoding='utf-8'))
            bag_info = metadata['rosbag2_bagfile_information']
            summary['message_counts'] = {
                item['topic_metadata']['name']: item['message_count']
                for item in bag_info['topics_with_message_count']
            }
            info = subprocess.run(['ros2', 'bag', 'info', str(output)],
                                  text=True, capture_output=True, check=False)
            info_path.write_text(info.stdout + info.stderr, encoding='utf-8')
            summary['bag_info_exit_code'] = info.returncode
        else:
            summary['message_counts'] = None
            summary['bag_info_exit_code'] = None
        summary['result'] = (
            'complete' if reason == 'window_complete'
            and summary['recorder_exit_code'] == 0
            and summary['bag_info_exit_code'] == 0
            and set(TOPICS) <= set(summary['message_counts'])
            and all(summary['message_counts'][topic] > 0 for topic in STATUS_TOPICS)
            else 'incomplete'
        )
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False)
                                + '\n', encoding='utf-8')
        print(summary_path)
    return 0 if summary['result'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
