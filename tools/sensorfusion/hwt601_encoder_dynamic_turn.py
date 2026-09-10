#!/usr/bin/env python3
"""Supervised, bounded HWT601/encoder/EKF turn or straight segment.

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
RAW_IMU = '/shadow/hwt601/imu/data_raw'
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
TARGET_STRAIGHT_STOP_M = 0.12
STRAIGHT_COMMAND_MPS = 0.05
MAX_STRAIGHT_TARGET_M = 1.0
MIN_ACCEL_MPS2 = 7.0
MAX_ACCEL_MPS2 = 12.5
MAX_ROLL_PITCH_RATE_RADPS = math.radians(14.0)
MAX_GRAVITY_STEP_RAD = math.radians(3.0)


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


def straight_command(elapsed_s, forward_m, lateral_m, encoder_deg, imu_deg,
                     ekf_deg, direction,
                     target_stop_m=TARGET_STRAIGHT_STOP_M):
    if (not math.isfinite(target_stop_m)
            or not 0.10 <= target_stop_m <= MAX_STRAIGHT_TARGET_M):
        raise ValueError('ungueltiges Geradeausziel')
    hard_distance_m = target_stop_m + 0.12
    maximum_time_s = target_stop_m / STRAIGHT_COMMAND_MPS + 10.0
    lateral_limit_m = 0.02 if target_stop_m <= 0.20 else 0.04
    signed_forward = direction * forward_m
    values = (
        elapsed_s, signed_forward, lateral_m, encoder_deg, imu_deg, ekf_deg)
    if direction not in (-1, 1) or not all(math.isfinite(v) for v in values):
        raise ValueError('ungueltige Geradeauswerte')
    if elapsed_s > maximum_time_s:
        raise ValueError('Geradeaus-Zeitlimit')
    if signed_forward < -0.02 or signed_forward > hard_distance_m:
        raise ValueError('Geradeaus-Richtung/Streckengrenze')
    if abs(lateral_m) > lateral_limit_m:
        raise ValueError('Seitwaertsgrenze')
    if max(abs(encoder_deg), abs(imu_deg), abs(ekf_deg)) > 5.0:
        raise ValueError('Geradeaus-Winkelgrenze')
    if elapsed_s > 7.0 and signed_forward < 0.02:
        raise ValueError('kein bestaetigter Geradeausfortschritt')
    if signed_forward >= 0.03:
        if abs(encoder_deg - imu_deg) > 3.0:
            raise ValueError('HWT und Encoder widersprechen sich')
        if abs(ekf_deg - imu_deg) > 3.0:
            raise ValueError('EKF und HWT widersprechen sich')
    return 0.0 if signed_forward >= target_stop_m \
        else direction * STRAIGHT_COMMAND_MPS


def _percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        raise ValueError('keine Vibrationsproben')
    index = int(round((len(ordered) - 1) * fraction))
    return ordered[index]


def vibration_metrics(samples):
    """Evaluate raw acceleration and non-yaw rate against scan-gate limits."""
    if len(samples) < 2:
        raise ValueError('zu wenige Vibrationsproben')
    accel_norms = []
    roll_pitch_rates = []
    gravity_steps = []
    previous_accel = None
    for sample in samples:
        accel = tuple(float(value) for value in sample['accel'])
        gyro = tuple(float(value) for value in sample['gyro'])
        if not all(math.isfinite(value) for value in (*accel, *gyro)):
            raise ValueError('nicht-endliche Vibrationsprobe')
        norm = math.sqrt(sum(value * value for value in accel))
        accel_norms.append(norm)
        # A pure yaw mounting rotation preserves the X/Y norm.  Thus this is
        # the base-frame roll/pitch-rate magnitude without inventing a chip
        # lever arm or orientation measurement.
        roll_pitch_rates.append(math.hypot(gyro[0], gyro[1]))
        if previous_accel is not None:
            previous_norm = math.sqrt(
                sum(value * value for value in previous_accel))
            if norm > 0.0 and previous_norm > 0.0:
                cosine = sum(a * b for a, b in zip(accel, previous_accel)) / (
                    norm * previous_norm)
                gravity_steps.append(math.acos(max(-1.0, min(1.0, cosine))))
        previous_accel = accel
    return {
        'samples': len(samples),
        'acceleration_norm_mean_mps2': sum(accel_norms) / len(accel_norms),
        'acceleration_norm_min_mps2': min(accel_norms),
        'acceleration_norm_max_mps2': max(accel_norms),
        'roll_pitch_rate_p95_radps': _percentile(roll_pitch_rates, 0.95),
        'roll_pitch_rate_peak_radps': max(roll_pitch_rates),
        'gravity_direction_step_peak_rad': max(gravity_steps),
        'within_scan_gate_envelope': (
            min(accel_norms) >= MIN_ACCEL_MPS2
            and max(accel_norms) <= MAX_ACCEL_MPS2
            and max(roll_pitch_rates) <= MAX_ROLL_PITCH_RATE_RADPS
            and max(gravity_steps) <= MAX_GRAVITY_STEP_RAD),
    }


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
    parser.add_argument('--motion', choices=('turn', 'straight'), default='turn')
    parser.add_argument(
        '--direction', choices=('left', 'right', 'forward', 'reverse'),
        default='left')
    parser.add_argument(
        '--target-distance-m', type=float, default=TARGET_STRAIGHT_STOP_M,
        help='Geradeausziel 0,10..1,00 m; fuer Drehungen unzulaessig.')
    args = parser.parse_args()
    if ((args.motion == 'turn' and args.direction not in ('left', 'right')) or
            (args.motion == 'straight' and
             args.direction not in ('forward', 'reverse'))):
        parser.error('Richtung passt nicht zur Bewegungsart')
    if args.motion == 'turn' and args.target_distance_m != TARGET_STRAIGHT_STOP_M:
        parser.error('--target-distance-m gilt nur fuer Geradeausfahrt')
    if (not math.isfinite(args.target_distance_m)
            or not 0.10 <= args.target_distance_m <= MAX_STRAIGHT_TARGET_M):
        parser.error('--target-distance-m muss zwischen 0,10 und 1,00 liegen')
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

    direction = 1 if args.direction in ('left', 'forward') else -1
    is_turn = args.motion == 'turn'
    motion_label = 'Drehung' if is_turn else 'Geradeausfahrt'
    rclpy.init()
    node = rclpy.create_node('hwt601_encoder_dynamic_turn')
    output = (Path.home() / '.local/share/amadeus/hwt601' /
              time.strftime(
                  f'dynamic-{args.motion}-{args.direction}-%Y%m%d-%H%M%S'))
    output.mkdir(parents=True, exist_ok=False)
    samples = (output / 'samples.jsonl').open('x')
    data = {}
    phase = 'preflight'
    integral = ScalarIntegral()
    raw_motion = []
    publisher = None
    summary = {
        'complete': False, 'passed': False, 'execute': args.execute,
        'motion': args.motion, 'direction': args.direction,
        'target_stop_deg': TARGET_STOP_DEG if is_turn else None,
        'target_straight_stop_m': (
            args.target_distance_m if not is_turn else None),
        'command_radps': COMMAND_RADPS if is_turn else None,
        'command_mps': STRAIGHT_COMMAND_MPS if not is_turn else None,
        'output': str(output),
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

    def on_raw_imu(message):
        value = {
            'stamp': message.header.stamp.sec + message.header.stamp.nanosec * 1e-9,
            'gyro': [
                float(message.angular_velocity.x),
                float(message.angular_velocity.y),
                float(message.angular_velocity.z)],
            'accel': [
                float(message.linear_acceleration.x),
                float(message.linear_acceleration.y),
                float(message.linear_acceleration.z)],
        }
        receive('raw_imu', value)
        if phase in ('turning', 'stopping'):
            raw_motion.append(value)

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
        Imu, RAW_IMU, on_raw_imu, qos_profile_sensor_data)
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
            'imu': 0.15, 'raw_imu': 0.15, 'wheel': 0.20, 'ekf': 0.20,
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
                print(
                    f'{motion_label} startet in {remaining} s; '
                    'Enter bricht ab.', flush=True)
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
                dx = wheel['x'] - start_wheel['x']
                dy = wheel['y'] - start_wheel['y']
                forward = (math.cos(start_wheel['yaw']) * dx +
                           math.sin(start_wheel['yaw']) * dy)
                lateral = (-math.sin(start_wheel['yaw']) * dx +
                           math.cos(start_wheel['yaw']) * dy)
                if is_turn:
                    command = turn_command(
                        time.monotonic() - started, encoder_deg, imu_deg,
                        ekf_deg, displacement, direction)
                else:
                    command = straight_command(
                        time.monotonic() - started, forward, lateral,
                        encoder_deg, imu_deg, ekf_deg, direction,
                        args.target_distance_m)
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
                    if is_turn:
                        message.angular.z = command
                    else:
                        message.linear.x = command
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
            dx = wheel['x'] - start_wheel['x']
            dy = wheel['y'] - start_wheel['y']
            forward = (math.cos(start_wheel['yaw']) * dx +
                       math.sin(start_wheel['yaw']) * dy)
            lateral = (-math.sin(start_wheel['yaw']) * dx +
                       math.cos(start_wheel['yaw']) * dy)
            vibration = vibration_metrics(raw_motion)
            counters_unchanged = all(
                base.get(key) == start_base.get(key)
                for key in ('encoder_rejected_updates', 'encoder_rebases'))
            if is_turn:
                passed = (
                    15.0 <= direction * encoder_deg <= 25.0
                    and abs(imu_deg - encoder_deg) <= 3.0
                    and abs(ekf_deg - imu_deg) <= 2.0
                    and displacement <= 0.03)
            else:
                passed = (
                    args.target_distance_m - 0.02
                    <= direction * forward
                    <= args.target_distance_m + 0.10
                    and abs(lateral) <= 0.03
                    and max(abs(encoder_deg), abs(imu_deg), abs(ekf_deg)) <= 3.0
                    and abs(imu_deg - encoder_deg) <= 2.0)
            passed = (
                passed and vibration['within_scan_gate_envelope']
                and counters_unchanged
                and base.get('modbus_read_failures') == 0)
            summary.update(
                complete=True, passed=passed,
                encoder_deg=encoder_deg, imu_deg=imu_deg, ekf_deg=ekf_deg,
                imu_minus_encoder_deg=imu_deg - encoder_deg,
                ekf_minus_imu_deg=ekf_deg - imu_deg,
                encoder_translation_m=displacement,
                encoder_forward_m=forward,
                encoder_lateral_m=lateral,
                encoder_pair_read_duration_s=base.get(
                    'encoder_pair_read_duration_s'),
                encoder_maximum_pair_read_duration_s=base.get(
                    'encoder_maximum_pair_read_duration_s'),
                encoder_pair_left_first=base.get('encoder_pair_left_first'),
                encoder_counters_unchanged=counters_unchanged,
                modbus_read_failures=base.get('modbus_read_failures'),
                vibration=vibration)
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
