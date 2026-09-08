#!/usr/bin/env python3
"""Test the production bias core on live IMU data, without ROS or wheel fiction.

Standstill is declared by the present user, NOT verified by encoders. Compare
fixed initial bias against adaptation; no sensor or production settings change.
"""

import argparse
import csv
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import sys
import time

import yaml

from hwt601_messen import Measurement, ROOT
from hwt601_usb_pruefen import _properties
from hwt601_usb_setup import ID_PATH
from robot_state_estimation.hwt601_protocol import decode_motion_registers
from robot_state_estimation.hwt601_transport import Hwt601SerialTransport
from robot_state_estimation.quality_core import GyroBiasConfig, GyroBiasEstimator


def profile_config():
    path = ROOT / 'src/robot_state_estimation/config/amadeus_hwt601.yaml'
    params = yaml.safe_load(path.read_text())['sensor_adapter']['ros__parameters']
    names = {
        'calibration_duration_s': 'calibration_s',
        'maximum_sample_magnitude_radps': 'maximum_sample_radps',
        'maximum_stationary_residual_radps': 'maximum_stationary_residual_radps',
    }
    values = {}
    for name in GyroBiasConfig.__dataclass_fields__:
        suffix = names.get(name, name)
        if name == 'minimum_samples':
            suffix = 'minimum_samples'
        values[name] = params['gyro_bias_' + suffix]
    return GyroBiasConfig(**values)


class Integral:
    def __init__(self):
        self.previous = None
        self.value = [0.0] * 3
        self.peak = [0.0] * 3

    def add(self, stamp, vector):
        if self.previous is not None:
            old_stamp, old_vector = self.previous
            dt = stamp - old_stamp
            if not 0 < dt <= 0.1:
                raise ValueError('Integration durch Datenluecke ungueltig')
            for i in range(3):
                self.value[i] += math.degrees((old_vector[i] + vector[i]) * 0.5 * dt)
                self.peak[i] = max(self.peak[i], abs(self.value[i]))
        self.previous = (stamp, vector)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stationary-confirmed', action='store_true', required=True)
    parser.add_argument('--seconds', type=float, default=600.0)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 1 <= args.seconds <= 1800:
        parser.error('seconds muss 1..1800 sein')
    port = Path('/dev/ttyUSB_HWT601')
    props = _properties(port)
    if (props.get('ID_VENDOR_ID'), props.get('ID_MODEL_ID'), props.get('ID_PATH')) != (
            '1a86', '7523', ID_PATH + ':1.0'):
        raise ValueError('Unerwarteter USB-Port')
    config = profile_config()
    config.validate()
    adaptive = GyroBiasEstimator(config)
    fixed = GyroBiasEstimator(replace(config, stationary_adaptation_time_constant_s=0.0))
    output = Path.home() / '.local/share/amadeus/hwt601' / time.strftime('bias-%Y%m%d-%H%M%S')
    output.mkdir(parents=True, exist_ok=False)
    integrals = {name: Integral() for name in ('raw', 'fixed', 'adaptive')}
    summary = {
        'complete': False, 'passed': False, 'fusion_ready': False,
        'stationary_source': 'user_declared_not_encoder_verified',
        'config': asdict(config), 'requested_evaluation_s': args.seconds,
        'sensor_scales_validated': False, 'cold_start_verified': False,
    }
    started = None
    measurement = None
    initial_bias = None
    blocked = 0
    test_start = time.monotonic()
    report_at = test_start
    next_poll = test_start
    print(f'Messdaten lokal: {output}', flush=True)
    try:
        with (output / 'samples.csv').open('x', newline='') as logfile, \
                Hwt601SerialTransport(str(port), 115200, 0.03, 80) as link:
            writer = csv.writer(logfile)
            writer.writerow(['elapsed_s', 'evaluation_s', 'ax', 'ay', 'az',
                             'gx', 'gy', 'gz', 'calibrated', 'stable',
                             'bias_x', 'bias_y', 'bias_z'])
            while True:
                sample = decode_motion_registers(link.read_motion_registers())
                now = time.monotonic()
                if started is not None and now >= started + args.seconds:
                    break
                if started is None and now - test_start > 90:
                    raise ValueError('Keine stabile Anfangskalibrierung innerhalb 90 s')
                norm = math.sqrt(sum(v * v for v in sample.linear_acceleration_mps2))
                if sample.saturated() or not 9.3 <= norm <= 10.3:
                    raise ValueError('Beschleunigung unplausibel oder Sensor gesaettigt')
                result = adaptive.update(now, sample.angular_velocity_radps, True)
                fixed_result = fixed.update(now, sample.angular_velocity_radps, True)
                if started is None and result.calibrated and fixed_result.calibrated:
                    started = now
                    measurement = Measurement(now)
                    initial_bias = list(result.bias_radps)
                    print(f'Anfangskalibrierung fertig; jetzt {args.seconds:g} s Auswertung.', flush=True)
                if started is not None:
                    measurement.add(sample, now)
                    for name, vector in (
                            ('raw', sample.angular_velocity_radps),
                            ('fixed', fixed.correct(sample.angular_velocity_radps)),
                            ('adaptive', adaptive.correct(sample.angular_velocity_radps))):
                        integrals[name].add(now, vector)
                    blocked += int(not result.stable)
                writer.writerow([now - test_start, None if started is None else now - started,
                                 *sample.linear_acceleration_mps2,
                                 *sample.angular_velocity_radps,
                                 result.calibrated, result.stable, *result.bias_radps])
                if now >= report_at:
                    logfile.flush()
                    print(json.dumps({'evaluation_s': None if started is None else round(now-started,1),
                                      'state': result.reason, 'blocked_samples': blocked,
                                      'z_integral_deg': {key: round(v.value[2],6) for key,v in integrals.items()}}), flush=True)
                    report_at = now + 30
                next_poll = max(next_poll + 0.01, time.monotonic())
                time.sleep(max(0.0, next_poll - time.monotonic()))
        summary['complete'] = True
    except (Exception, KeyboardInterrupt) as error:
        summary['error'] = f'{type(error).__name__}: {error}'
    finally:
        if measurement is not None:
            summary['raw_measurement'] = measurement.report(time.monotonic())
        summary.update({
            'initial_bias_radps_xyz': initial_bias,
            'final_bias_radps_xyz': list(adaptive.result.bias_radps),
            'blocked_samples': blocked,
            'integral_deg_xyz': {key: value.value for key, value in integrals.items()},
            'peak_absolute_integral_deg_xyz': {key: value.peak for key, value in integrals.items()},
            'duration_total_s': time.monotonic() - test_start,
        })
        summary['passed'] = bool(
            summary['complete'] and args.seconds >= 600 and blocked == 0
            and summary['raw_measurement']['raw_check_passed']
            and integrals['adaptive'].peak[2] < 1.0)
        (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
        print(json.dumps(summary, indent=2, allow_nan=False), flush=True)
    return 0 if summary['passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
