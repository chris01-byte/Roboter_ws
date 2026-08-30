#!/usr/bin/env python3
"""Inspect one USB-RS485 adapter and print a safe, exact udev rule."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


SAFE_VALUE = re.compile(r'^[A-Za-z0-9._:+-]+$')


def _properties(device: Path):
    result = subprocess.run(
        ['udevadm', 'info', '--query=property', f'--name={device}'],
        check=True, capture_output=True, text=True)
    properties = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            properties[key] = value
    return properties


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Liest nur USB-Merkmale. Es wird keine Regel installiert und '
            'kein serielles Geraet geoeffnet.'))
    parser.add_argument('device', help='z.B. /dev/ttyUSB2')
    args = parser.parse_args()
    device = Path(args.device)
    if not str(device).startswith('/dev/') or not device.exists():
        parser.error('ein vorhandenes Geraet unter /dev/ ist erforderlich')

    base_alias = Path('/dev/ttyUSB_BASE')
    if (
            base_alias.exists()
            and os.path.realpath(device) == os.path.realpath(base_alias)):
        parser.error(
            'das ist der Motor-RS485-Adapter; nicht fuer die IMU verwenden')

    try:
        properties = _properties(device)
    except (OSError, subprocess.CalledProcessError) as error:
        print(
            f'USB-Merkmale konnten nicht gelesen werden: {error}',
            file=sys.stderr)
        return 2

    vendor = properties.get('ID_VENDOR_ID', '')
    product = properties.get('ID_MODEL_ID', '')
    serial = properties.get('ID_SERIAL_SHORT', '')
    print(f'Geraet: {device.resolve()}')
    print(f'VID: {vendor or "fehlt"}')
    print(f'PID: {product or "fehlt"}')
    print(f'Seriennummer: {serial or "fehlt"}')
    if not all(
            value and SAFE_VALUE.fullmatch(value)
            for value in (vendor, product, serial)):
        print(
            'Keine eindeutige Regel erzeugt. Einen Adapter mit eindeutiger '
            'Seriennummer verwenden; VID/PID allein koennte den Motoradapter '
            'treffen.')
        return 1

    print('\nVorschlag fuer /etc/udev/rules.d/83-hwt601.rules:')
    print(
        f'SUBSYSTEM=="tty", ATTRS{{idVendor}}=="{vendor}", '
        f'ATTRS{{idProduct}}=="{product}", ATTRS{{serial}}=="{serial}", '
        'SYMLINK+="ttyUSB_HWT601", GROUP="dialout", MODE="0660"')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
