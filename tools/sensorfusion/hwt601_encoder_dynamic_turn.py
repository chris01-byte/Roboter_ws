#!/usr/bin/env python3
"""Supervised, bounded HWT601/encoder/EKF turn in one direction.

The separately started validation stack owns both serial ports.  This tool
only observes its isolated topics and publishes a bounded yaw command.  The
default invocation is a passive preflight; --execute requires the explicit
environment gate and a TTY.
"""

import argparse
import json
import math
import os
from pathlib import Path
import select
import sys
import time


COMMAND = '/hwt_dynamic/cmd_vel'
BASE_STATE = '/hwt_dynamic/base_state'
WHEEL_ODOM = '/shadow/hwt601/wheel_odom_raw'
IMU = '/shadow/hwt601/imu/yaw_rate'
EKF_ODOM = '/shadow/hwt601/odom'
HWT_STATUS = '/shadow/hwt601/status_json'
RAW_STATUS = '/shadow/hwt601/raw_status_json'
FORBIDDEN_PRODUCTION_TOPICS = (
    '/cmd_vel', '/cmd_vel_smoothed', '/map', '/odom', '/scan',
    '/scan_normiert', '/scan_qualitaet', '/tf', '/tf_static')
TARGET_STOP_DEG = 17.0
HARD_ANGLE_DEG = 30.0
COMMAND_RADPS = 0.08
MAX_TURN_S = 10.0


def angle_delta(current, start):
    return math.atan2(math.sin(current - start), math.cos(current - start))


def yaw_from_quaternion(q):
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def base_healthy(state, age_s):
    return (
        age_s <= 0.3
        and state.get('dry_run') is False
        and state.get('allow_rs485') is True
        and state.get('rs485_ready') is True
        and state.get('odometry_source') == 'encoder_position'
        and state.get('encoder_feedback_ok') is True
        and state.get('encoder_initialized') is True
        and state.get('encoder_stale') is False
        and state.get('encoder_config_fault_latched') is False
        and state.get('encoder_consecutive_failures') == 0
        and state.get('modbus_read_failures') == 0
        and isinstance(state.get('encoder_pair_read_duration_s'), (int, float))
        and 0.0 <= state['encoder_pair_read_duration_s'] <= 0.05)


def stationary(state):
    return all(
        isinstance(state.get(key), (int, float))
        and math.isfinite(state[key])
        and abs(state[key]) <= 0.01
        for key in ('meas_v_mps', 'meas_w_radps'))


def turn_command(elapsed_s, encoder_deg, imu_deg, ekf_deg,
                 displacement_m, direction):
    signed = tuple(direction * value for value in
                   (encoder_deg, imu_deg, ekf_deg))
    values = (elapsed_s, displacement_m, *signed)
    if direction not in (-1, 1) or not all(math.isfinite(v) for v in values):
        raise ValueError('ungueltige Bewegungswerte')
    if elapsed_s > MAX_TURN_S:
        raise ValueError('Zeitlimit')
    if displacement_m > 0.03:
        raise ValueError('Translationsgrenze')
    if min(signed) < -2.0 or max(signed) > HARD_ANGLE_DEG:
        raise ValueError('Richtung/Winkelgrenze')
    if elapsed_s > 6.0 and min(signed) < 2.0:
        raise ValueError('kein bestaetigter Drehfortschritt')
    if signed[0] >= 3.0:
        if abs(encoder_deg - imu_deg) > 5.0:
            raise ValueError('HWT und Encoder widersprechen sich')
        if abs(ekf_deg - imu_deg) > 5.0:
            raise ValueError('EKF und HWT widersprechen sich')
    return 0.0 if signed[0] >= TARGET_STOP_DEG else direction * COMMAND_RADPS


class ScalarIntegral:
    def __init__(self):
        self.last_stamp = None
        self.last_value = None
        self.value = 0.0

    def add(self, stamp, value):
        if self.last_stamp is not None:
            dt = stamp - self.last_stamp
            if not 0.0 < dt <= 0.10:
                raise ValueError('IMU-Zeitluecke')
            self.value += 0.5 * (self.last_value + value) * dt
        self.last_stamp = stamp
        self.last_value = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--direction', choices=('left', 'right'), default='left')
    args = parser.parse_args()
    if args.execute and (
            os.environ.get('AMADEUS_DYNAMISCHE_FAHRFREIGABE') != 'JA'
            or not sys.stdin.isatty()):
        parser.error(
            'Echter Lauf braucht TTY und AMADEUS_DYNAMISCHE_FAHRFREIGABE=JA')

    import rclpy
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu
    from std_msgs.msg import String
    from rclpy.qos import qos_profile_sensor_data

    direction = 1 if args.direction == 'left' else -1
    rclpy.init()
    node = rclpy.create_node('hwt601_encoder_dynamic_turn')
    output = (Path.home() / '.local/share/amadeus/hwt601' /
              time.strftime(f'dynamic-{args.direction}-%Y%m%d-%H%M%S'))
    output.mkdir(parents=True, exist_ok=False)
    samples = (output / 'samples.jsonl').open('x')
    data = {}
    phase = 'preflight'
    integral = ScalarIntegral()
    publisher = None
    summary = {
        'complete': False, 'passed': False, 'execute': args.execute,
        'direction': args.direction, 'target_stop_deg': TARGET_STOP_DEG,
        'command_radps': COMMAND_RADPS, 'output': str(output),
        'forbidden_production_publishers_checked': list(
            FORBIDDEN_PRODUCTION_TOPICS),
    }

    def receive(kind, value):
        now = time.monotonic()
        data[kind] = (now, value)
        samples.write(json.dumps({
            'received_monotonic_s': now, 'phase': phase,
            'kind': kind, 'value': value}, allow_nan=False) + '\n')

    def on_imu(message):
        stamp = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
        value = float(message.angular_velocity.z)
        receive('imu', {'stamp': stamp, 'wz': value})
        if phase in ('turning', 'stopping'):
            integral.add(stamp, value)

    def on_odom(kind, message):
        receive(kind, {
            'stamp': message.header.stamp.sec + message.header.stamp.nanosec * 1e-9,
            'x': float(message.pose.pose.position.x),
            'y': float(message.pose.pose.position.y),
            'yaw': yaw_from_quaternion(message.pose.pose.orientation),
            'v': float(message.twist.twist.linear.x),
            'w': float(message.twist.twist.angular.z),
        })

    node.create_subscription(Imu, IMU, on_imu, qos_profile_sensor_data)
    node.create_subscription(
        Odometry, WHEEL_ODOM, lambda m: on_odom('wheel', m), 10)
    node.create_subscription(
        Odometry, EKF_ODOM, lambda m: on_odom('ekf', m), 10)
    node.create_subscription(
        String, BASE_STATE, lambda m: receive('base', json.loads(m.data)), 10)
    node.create_subscription(
        String, HWT_STATUS, lambda m: receive('hwt_status', json.loads(m.data)), 10)
    node.create_subscription(
        String, RAW_STATUS, lambda m: receive('raw_status', json.loads(m.data)), 10)

    def ready(require_still=False):
        now = time.monotonic()
        limits = {
            'imu': 0.15, 'wheel': 0.20, 'ekf': 0.20,
            'base': 0.30, 'hwt_status': 1.0, 'raw_status': 1.0,
        }
        for key, limit in limits.items():
            if key not in data or now - data[key][0] > limit:
                raise ValueError(f'Daten fehlen/veraltet: {key}')
        base = data['base'][1]
        if not base_healthy(base, now - data['base'][0]):
            raise ValueError('Encoder/Antrieb nicht gesund')
        if not data['hwt_status'][1].get('ready'):
            raise ValueError('HWT-Shadow nicht bereit')
        if not data['raw_status'][1].get('ready'):
            raise ValueError('HWT-Rohquelle nicht bereit')
        for kind in ('imu', 'wheel', 'ekf'):
            if abs(time.time() - data[kind][1]['stamp']) > 0.4:
                raise ValueError(f'Quellzeit veraltet: {kind}')
        for topic in FORBIDDEN_PRODUCTION_TOPICS:
            if node.count_publishers(topic) != 0:
                raise ValueError(f'Produktivpublisher vorhanden: {topic}')
        if require_still and (
                not stationary(base)
                or abs(data['wheel'][1]['v']) > 0.005
                or abs(data['wheel'][1]['w']) > 0.005
                or abs(data['ekf'][1]['v']) > 0.005
                or abs(data['ekf'][1]['w']) > 0.005):
            raise ValueError('gemessener Stillstand fehlt')

    def zero():
        if publisher is not None:
            publisher.publish(Twist())

    try:
        print(f'Lokal: {output}; execute={args.execute}', flush=True)
        until = time.monotonic() + 8.0
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=0.02)
        ready(True)
        if node.count_publishers(COMMAND) != 0:
            raise ValueError('fremder Befehlspublisher vorhanden')
        if node.count_subscribers(COMMAND) != 1:
            raise ValueError('Befehlskanal nicht exklusiv')
        if not args.execute:
            summary.update(complete=True, passed=True)
            print('PASSIVER PREFLIGHT OK; kein Publisher erstellt.', flush=True)
        else:
            publisher = node.create_publisher(Twist, COMMAND, 1)
            for remaining in (3, 2, 1):
                print(f'Drehung startet in {remaining} s; Enter bricht ab.', flush=True)
                deadline = time.monotonic() + 1.0
                while time.monotonic() < deadline:
                    zero()
                    rclpy.spin_once(node, timeout_sec=0.02)
                    ready(True)
                    if select.select([sys.stdin], [], [], 0)[0]:
                        sys.stdin.readline()
                        raise ValueError('Bedienerabbruch')
            # Anchor all relative measurements after the warning period.  No
            # IMU timestamp from before that pause may enter the dynamic
            # integral, otherwise the deliberate countdown looks like loss.
            start_wheel = data['wheel'][1].copy()
            start_ekf = data['ekf'][1].copy()
            start_base = data['base'][1].copy()
            integral.add(data['imu'][1]['stamp'], data['imu'][1]['wz'])
            phase = 'turning'
            started = time.monotonic()
            next_command = started
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.01)
                ready(False)
                wheel = data['wheel'][1]
                ekf = data['ekf'][1]
                encoder_deg = math.degrees(angle_delta(
                    wheel['yaw'], start_wheel['yaw']))
                imu_deg = math.degrees(integral.value)
                ekf_deg = math.degrees(angle_delta(
                    ekf['yaw'], start_ekf['yaw']))
                displacement = math.hypot(
                    wheel['x'] - start_wheel['x'],
                    wheel['y'] - start_wheel['y'])
                command = turn_command(
                    time.monotonic() - started, encoder_deg, imu_deg,
                    ekf_deg, displacement, direction)
                if command == 0.0:
                    break
                if (node.count_publishers(COMMAND) != 1 or
                        node.count_subscribers(COMMAND) != 1):
                    raise ValueError('Befehlskanal nicht mehr exklusiv')
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    raise ValueError('Bedienerabbruch')
                if time.monotonic() >= next_command:
                    message = Twist()
                    message.angular.z = command
                    publisher.publish(message)
                    next_command = time.monotonic() + 0.05

            phase = 'stopping'
            until = time.monotonic() + 3.0
            while time.monotonic() < until:
                zero()
                rclpy.spin_once(node, timeout_sec=0.01)
                ready(False)
            ready(True)
            wheel = data['wheel'][1]
            ekf = data['ekf'][1]
            base = data['base'][1]
            encoder_deg = math.degrees(angle_delta(
                wheel['yaw'], start_wheel['yaw']))
            imu_deg = math.degrees(integral.value)
            ekf_deg = math.degrees(angle_delta(
                ekf['yaw'], start_ekf['yaw']))
            displacement = math.hypot(
                wheel['x'] - start_wheel['x'],
                wheel['y'] - start_wheel['y'])
            signed_encoder = direction * encoder_deg
            counters_unchanged = all(
                base.get(key) == start_base.get(key)
                for key in ('encoder_rejected_updates', 'encoder_rebases'))
            passed = (
                15.0 <= signed_encoder <= 25.0
                and abs(imu_deg - encoder_deg) <= 3.0
                and abs(ekf_deg - imu_deg) <= 2.0
                and displacement <= 0.03
                and counters_unchanged
                and base.get('modbus_read_failures') == 0)
            summary.update(
                complete=True, passed=passed,
                encoder_deg=encoder_deg, imu_deg=imu_deg, ekf_deg=ekf_deg,
                imu_minus_encoder_deg=imu_deg - encoder_deg,
                ekf_minus_imu_deg=ekf_deg - imu_deg,
                encoder_translation_m=displacement,
                encoder_pair_read_duration_s=base.get(
                    'encoder_pair_read_duration_s'),
                encoder_maximum_pair_read_duration_s=base.get(
                    'encoder_maximum_pair_read_duration_s'),
                encoder_pair_left_first=base.get('encoder_pair_left_first'),
                encoder_counters_unchanged=counters_unchanged,
                modbus_read_failures=base.get('modbus_read_failures'))
    except (Exception, KeyboardInterrupt) as exc:
        summary['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        phase = 'cleanup'
        until = time.monotonic() + 2.0
        while publisher is not None and rclpy.ok() and time.monotonic() < until:
            zero()
            try:
                rclpy.spin_once(node, timeout_sec=0.02)
            except Exception:
                pass
        summary['stopped_feedback_confirmed'] = bool(
            'base' in data and time.monotonic() - data['base'][0] < 0.3
            and stationary(data['base'][1]))
        summary['passed'] = bool(
            summary['complete'] and summary['passed']
            and summary['stopped_feedback_confirmed'])
        samples.close()
        (output / 'summary.json').write_text(
            json.dumps(summary, indent=2, allow_nan=False) + '\n')
        print(json.dumps(summary, indent=2), flush=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0 if summary['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
