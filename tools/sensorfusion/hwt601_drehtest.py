#!/usr/bin/env python3
"""Manual marked-angle test. Default: USB metadata only, no serial open.

No ROS, actuators, sensor configuration writes or bias adaptation during motion.
Ground markings, not the IMU display, define the reference angle.
"""

import argparse
import csv
from dataclasses import replace
import json
import math
from pathlib import Path
import select
import sys
import time

from hwt601_bias_stillstand import Integral, profile_config
from hwt601_usb_pruefen import _properties
from hwt601_usb_setup import ID_PATH
from robot_state_estimation.hwt601_protocol import decode_motion_registers
from robot_state_estimation.hwt601_transport import Hwt601SerialTransport
from robot_state_estimation.quality_core import GyroBiasEstimator


class TurnMeasurement:
    """Frozen bias, physical signed target, and explicit quality accounting."""

    def __init__(self, bias, target_deg, tolerance_deg=5.0):
        if (len(bias) != 3 or not all(math.isfinite(v) for v in bias)
                or target_deg not in (-90.0, 90.0)
                or not math.isfinite(tolerance_deg) or not 0 < tolerance_deg <= 10):
            raise ValueError('Invalid fixed bias or reference angle')
        self.bias = tuple(bias)
        self.target = target_deg
        self.tolerance = tolerance_deg
        self.integral = Integral()
        self.start = None
        self.last = None
        self.count = 0
        self.max_gap = 0.0

    def add(self, stamp, raw_gyro):
        if (not math.isfinite(stamp) or len(raw_gyro) != 3
                or not all(math.isfinite(v) for v in raw_gyro)):
            raise ValueError('Invalid gyro sample')
        if self.start is None:
            self.start = stamp
        if self.last is not None:
            self.max_gap = max(self.max_gap, stamp - self.last)
        corrected = tuple(v - b for v, b in zip(raw_gyro, self.bias))
        self.integral.add(stamp, corrected)
        self.last = stamp
        self.count += 1
        return corrected

    def report(self):
        duration = 0.0 if self.start is None else self.last - self.start
        rate = (self.count - 1) / duration if duration > 0 else 0.0
        angle = self.integral.value[2]
        error = angle - self.target
        planar = max(self.integral.peak[:2]) <= 5.0
        return {
            'target_angle_deg': self.target, 'tolerance_deg': self.tolerance,
            'measured_angle_deg_xyz': self.integral.value,
            'peak_absolute_angle_deg_xyz': self.integral.peak,
            'error_deg': error, 'observed_scale_ratio': angle / self.target,
            'sign_ok': angle * self.target > 0,
            'fixed_bias_radps_xyz': self.bias,
            'duration_s': duration, 'samples': self.count,
            'observed_rate_hz': rate, 'maximum_gap_s': self.max_gap,
            'planar_check_passed': planar,
            'coarse_angle_check_passed': (
                self.count >= 100 and duration >= 2 and rate >= 80
                and self.max_gap <= .1 and planar
                and angle * self.target > 0 and abs(error) <= self.tolerance),
            'reference': 'operator_ground_marking_not_imu_display',
            'bias_adaptation_during_turn': False,
            'fusion_ready': False, 'actuator_output': False,
        }


def check_usb():
    port = Path('/dev/ttyUSB_HWT601')
    props = _properties(port)
    if (props.get('ID_VENDOR_ID'), props.get('ID_MODEL_ID'), props.get('ID_PATH')) != (
            '1a86', '7523', ID_PATH + ':1.0'):
        raise ValueError('Alias entspricht nicht dem vermessenen HWT-Adapter')
    return str(port)


def operator_line():
    if select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if line == '':
            raise EOFError('Eingabeterminal geschlossen')
        return line.strip().lower()
    return None


def run_test(port, direction):
    target = 90.0 if direction == 'left' else -90.0
    config = replace(profile_config(), stationary_adaptation_time_constant_s=0.0)
    estimator = GyroBiasEstimator(config)
    output = Path.home() / '.local/share/amadeus/hwt601' / time.strftime(
        f'turn-{direction}-%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=False)
    summary = {'complete': False, 'passed': False, 'fusion_ready': False,
               'motor_power_off': 'operator_declared_not_measured',
               'initial_standstill': 'operator_declared_not_encoder_verified',
               'direction': direction}
    phase = 'calibrating'
    phase_start = time.monotonic()
    next_poll = phase_start
    last_print = phase_start
    turn = None
    end_still_since = None
    print(f'Aufzeichnung: {output}', flush=True)
    print('Roboter ruhig halten: ca. 25 s Einlauf/Anfangskalibrierung. q + Enter bricht ab.', flush=True)
    try:
        with (output / 'samples.csv').open('x', newline='') as file, \
                Hwt601SerialTransport(port, 115200, .03, 80) as link:
            writer = csv.writer(file)
            writer.writerow(['monotonic_s', 'phase', 'ax', 'ay', 'az',
                             'gx', 'gy', 'gz', 'fixed_bx', 'fixed_by', 'fixed_bz'])
            while True:
                sample = decode_motion_registers(link.read_motion_registers())
                now = time.monotonic()
                if sample.saturated():
                    raise ValueError('Rohwertsaettigung')
                gravity = math.sqrt(sum(v*v for v in sample.linear_acceleration_mps2))
                if not 7.0 <= gravity <= 12.5:
                    raise ValueError('Unplausible Beschleunigung; Messung abbrechen')
                command = operator_line()
                if command == 'q':
                    raise KeyboardInterrupt('Bedienerabbruch')
                if now - phase_start > (90 if phase == 'calibrating' else 120):
                    raise TimeoutError(f'Zeitlimit in Phase {phase}')
                if phase == 'calibrating':
                    if not 9.3 <= gravity <= 10.3:
                        raise ValueError('Anfangsruhe/Beschleunigung unplausibel')
                    result = estimator.update(now, sample.angular_velocity_radps, True)
                    if result.calibrated:
                        turn = TurnMeasurement(result.bias_radps, target)
                        phase, phase_start = 'armed', now
                        print(f'Bias eingefroren. Ziel {target:+.0f} Grad anhand Bodenmarkierung. '
                              'Noch ruhig halten; s + Enter startet die Aufzeichnung.', flush=True)
                elif phase == 'armed':
                    residual = [v-b for v,b in zip(sample.angular_velocity_radps, turn.bias)]
                    if math.sqrt(sum(v*v for v in residual)) > .03:
                        raise ValueError('Bewegung vor Messstart: Startposition erneut ausrichten')
                    if command == 's':
                        turn.add(now, sample.angular_velocity_radps)
                        phase, phase_start = 'turning', now
                        print('Messfenster aktiv. Langsam zur Bodenmarkierung drehen; '
                              'danach ruhig abstellen und e + Enter. Nicht nach IMU-Anzeige ausrichten.', flush=True)
                else:
                    corrected = turn.add(now, sample.angular_velocity_radps)
                    if max(abs(v) for v in corrected) > math.radians(90):
                        raise ValueError('Drehung fuer diesen manuellen Test zu schnell')
                    if phase == 'turning' and command == 'e':
                        phase, phase_start = 'end_still', now
                        print('Endkontrolle: drei Sekunden ruhig halten.', flush=True)
                    if phase == 'end_still':
                        if math.sqrt(sum(v*v for v in corrected)) <= .005:
                            if end_still_since is None:
                                end_still_since = now
                        else:
                            end_still_since = None
                writer.writerow([now, phase, *sample.linear_acceleration_mps2,
                                 *sample.angular_velocity_radps,
                                 *(turn.bias if turn is not None else (None,)*3)])
                if end_still_since is not None and now - end_still_since >= 3:
                    summary['complete'] = True
                    break
                if now - last_print >= 5:
                    # Do not display an angle that could become the reference.
                    print(f'Phase: {phase} — Datenempfang aktiv.', flush=True)
                    file.flush()
                    last_print = now
                next_poll = max(next_poll + .01, time.monotonic())
                time.sleep(max(0, next_poll - time.monotonic()))
    except (Exception, KeyboardInterrupt) as error:
        summary['error'] = f'{type(error).__name__}: {error}'
    finally:
        if turn is not None:
            summary['measurement'] = turn.report()
        summary['passed'] = bool(summary['complete'] and
                                 summary['measurement']['coarse_angle_check_passed'])
        (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
        print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
        print('Messung beendet, Port geschlossen. Keine Motoren angesteuert.', flush=True)
    return 0 if summary['passed'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--direction', choices=('left', 'right'), default='left')
    parser.add_argument('--motor-power-off', action='store_true')
    parser.add_argument('--stationary-confirmed', action='store_true')
    args = parser.parse_args()
    if args.run and not (args.motor_power_off and args.stationary_confirmed):
        parser.error('--run braucht --motor-power-off und --stationary-confirmed')
    if args.run and not sys.stdin.isatty():
        parser.error('Interaktives Terminal erforderlich; keine gepipten Startbefehle')
    try:
        port = check_usb()
    except Exception as error:
        print(f'USB-Pruefung fehlgeschlagen: {error}', file=sys.stderr)
        return 2
    if not args.run:
        print(f'USB-Metadaten passen: {port}. Kein Port geoeffnet, keine Messung gestartet.')
        print('Bodenreferenz und stromlose mechanische Beweglichkeit zuerst pruefen.')
        return 0
    return run_test(port, args.direction)


if __name__ == '__main__':
    raise SystemExit(main())
