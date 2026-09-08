#!/usr/bin/env python3
"""Bounded, motorless HWT601 commissioning; no ROS/OAK/TF or sensor writes."""

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time

# Runs from this checkout without requiring an already installed ROS overlay.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/robot_state_estimation'))
from robot_state_estimation.hwt601_protocol import (  # noqa: E402
    Hwt601ProtocolError, decode_motion_registers)
from robot_state_estimation.hwt601_transport import (  # noqa: E402
    Hwt601SerialTransport, Hwt601TransportError, check_not_motor_port)
from hwt601_usb_pruefen import _properties  # noqa: E402
from hwt601_usb_setup import ID_PATH  # noqa: E402


class Measurement:
    """Online statistics, with missing start/end and intersample time included."""

    def __init__(self, started):
        self.started = started
        self.last_time = started
        self.last_gyro = None
        self.count = 0
        self.errors = 0
        self.max_gap = 0.0
        self.mean = [0.0] * 7
        self.m2 = [0.0] * 7
        self.norm_min = math.inf
        self.norm_max = -math.inf
        self.integral = [0.0] * 3
        self.integral_complete = True

    def add(self, sample, now):
        norm = math.sqrt(sum(v * v for v in sample.linear_acceleration_mps2))
        values = (*sample.linear_acceleration_mps2,
                  *sample.angular_velocity_radps, norm)
        self.count += 1
        for i, value in enumerate(values):
            delta = value - self.mean[i]
            self.mean[i] += delta / self.count
            self.m2[i] += delta * (value - self.mean[i])
        gap = now - self.last_time
        self.max_gap = max(self.max_gap, gap)
        if self.last_gyro is not None and gap <= 0.2:
            for i in range(3):
                self.integral[i] += 0.5 * (
                    self.last_gyro[i] + sample.angular_velocity_radps[i]) * gap
        elif gap > 0.2:
            self.integral_complete = False
        self.last_time = now
        self.last_gyro = sample.angular_velocity_radps
        self.norm_min = min(self.norm_min, norm)
        self.norm_max = max(self.norm_max, norm)

    def report(self, ended):
        duration = ended - self.started
        gap = max(self.max_gap, ended - self.last_time)
        rate = self.count / duration if duration > 0.0 else 0.0
        valid = self.count > 1
        std = [math.sqrt(max(0.0, v / (self.count - 1)))
               for v in self.m2] if valid else None
        return {
            'samples': self.count, 'rejected': self.errors,
            'duration_s': duration, 'rate_hz': rate, 'maximum_gap_s': gap,
            'acceleration_mean_mps2_xyz': self.mean[:3] if valid else None,
            'acceleration_std_mps2_xyz': std[:3] if valid else None,
            'gyro_mean_radps_xyz': self.mean[3:6] if valid else None,
            'gyro_std_radps_xyz': std[3:6] if valid else None,
            'acceleration_norm_mps2': {
                'mean': self.mean[6], 'min': self.norm_min, 'max': self.norm_max,
            } if valid else None,
            'raw_gyro_integral_deg_xyz': [math.degrees(v) for v in self.integral],
            'integral_complete': valid and self.integral_complete and gap <= 0.2,
            'raw_check_passed': (valid and rate >= 80.0 and gap <= 0.2
                                 and self.errors == 0
                                 and 9.3 <= self.norm_min <= self.norm_max <= 10.3),
            'gyro_scale_validated': False, 'mount_tf_validated': False,
            'fusion_ready': False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modbus', action='store_true',
                        help='Nach RS485-Pruefung nur FC03 lesen; sonst nur lauschen')
    parser.add_argument('--seconds', type=float, default=30.0)
    parser.add_argument('--settle', type=float, default=15.0)
    parser.add_argument('--baud', type=int, default=115200,
                        choices=(4800, 9600, 19200, 38400, 57600, 115200, 230400))
    args = parser.parse_args()
    if (not math.isfinite(args.seconds) or not 1 <= args.seconds <= 1800
            or not math.isfinite(args.settle) or not 0 <= args.settle <= 1800):
        parser.error('seconds: 1..1800, settle: 0..1800 Sekunden')
    port = Path('/dev/ttyUSB_HWT601')
    try:
        check_not_motor_port(str(port))
        if not port.exists():
            raise ValueError(
                '/dev/ttyUSB_HWT601 fehlt: zuerst USB-Treiber/udev installieren')
        props = _properties(port)
        if (props.get('ID_VENDOR_ID'), props.get('ID_MODEL_ID'),
                props.get('ID_PATH')) != ('1a86', '7523', ID_PATH + ':1.0'):
            raise ValueError('Alias zeigt nicht auf den vermessenen HWT-USB-Port')
        import serial
        # Never transmit into an unsolicited UART stream. No baud search and
        # no configuration commands: every experiment has explicit settings.
        with serial.Serial(str(port), args.baud, timeout=0.1,
                           write_timeout=0.03, exclusive=True) as link:
            end = time.monotonic() + 2.0
            incoming = bytearray()
            while time.monotonic() < end:
                incoming.extend(link.read(256))
                if len(incoming) > 4096:
                    break
        if incoming or not args.modbus:
            print(json.dumps({
                'listen_only': True, 'received_bytes': len(incoming),
                'first_bytes_hex': incoming[:64].hex(),
                'modbus_confirmed': False, 'fusion_ready': False,
                'next': ('Unaufgeforderte Daten: Protokoll vor Abfragen klaeren'
                         if incoming else 'RS485 pruefen; dann --modbus verwenden'),
            }, indent=2))
            return 2 if args.modbus else 0

        with Hwt601SerialTransport(str(port), args.baud, 0.03, 0x50) as link:
            started = time.monotonic() + args.settle
            ended = started + args.seconds
            measurement = Measurement(started)
            last_error = ''
            next_poll = time.monotonic()
            while time.monotonic() < ended:
                try:
                    sample = decode_motion_registers(link.read_motion_registers())
                    if sample.saturated():
                        raise Hwt601ProtocolError('Rohwertsaettigung')
                    now = time.monotonic()
                    if started <= now <= ended:
                        measurement.add(sample, now)
                except (Hwt601ProtocolError, Hwt601TransportError, OSError) as error:
                    if time.monotonic() >= started:
                        measurement.errors += 1
                    last_error = str(error)
                now = time.monotonic()
                next_poll = max(next_poll + 0.01, now)
                time.sleep(max(0.0, min(next_poll, ended) - now))
            report = measurement.report(time.monotonic())
            report.update({'port': str(port), 'baud': args.baud,
                           'settle_s': args.settle, 'last_error': last_error,
                           'scale_assumption_g': 4.0,
                           'scale_assumption_dps': 400.0,
                           'sensor_write_commands': False, 'actuator_output': False})
            print(json.dumps(report, indent=2, allow_nan=False))
            return 0 if report['raw_check_passed'] else 2
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Abbruch: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
