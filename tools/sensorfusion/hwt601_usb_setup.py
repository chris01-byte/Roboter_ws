#!/usr/bin/env python3
"""Prepare/install the missing CH340 driver; never open a robot serial port.

Only for the measured Jetson 5.15.199-tegra and the HWT USB socket observed
2026-09-08. No broad USB rebinding, motor access, service mask or package removal.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / 'build' / 'hwt601_usb'
RELEASE = '5.15.199-tegra'
SOURCE = ('https://raw.githubusercontent.com/gregkh/linux/v5.15.199/'
          'drivers/usb/serial/ch341.c')
SOURCE_SHA = 'f66d070eab6235b8a5c7a06a283d2feecb8fa3d81bc1323c847c2d2cbf7bd410'
USB_PATH = '/sys/bus/usb/devices/1-2.4.4.4'
DEV_PATH = '/devices/platform/bus@0/3610000.usb/usb1/1-2/1-2.4/1-2.4.4/1-2.4.4.4'
ID_PATH = 'platform-3610000.usb-usb-0:2.4.4.4'
VENDOR_RULE = Path('/lib/udev/rules.d/85-brltty.rules')
BRLTTY_RULE = Path('/etc/udev/rules.d/85-brltty.rules')
ALIAS_RULE = Path('/etc/udev/rules.d/83-hwt601.rules')
MODULE = Path(f'/lib/modules/{RELEASE}/updates/amadeus-hwt601/ch341.ko')
STATE = Path('/var/lib/amadeus/hwt601-usb')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(*args):
    return subprocess.run(args, check=True, text=True)


def brltty_rules(original):
    if 'LABEL="brltty_device_end"' not in original:
        raise ValueError('Unbekannte brltty-Regelstruktur; nichts ueberschreiben')
    # GOTO labels are file-local, hence a guarded copy of the packaged file.
    # All original Braille mappings remain untouched after this exact guard.
    match = ('SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", '
             'ATTR{idVendor}=="1a86", ATTR{idProduct}=="7523", '
             f'DEVPATH=="{DEV_PATH}", ')
    return (
        '# Amadeus: only the measured HWT601 USB socket is excluded.\n'
        '# Rebuild this override after a brltty package update.\n'
        # Also clear the exact stale property observed before installation.
        + match + 'ENV{SYSTEMD_WANTS}=="brltty-udev.service", '
        'ENV{SYSTEMD_WANTS}=""\n'
        + match + 'ENV{BRLTTY_BRAILLE_DRIVER}="", '
        'ENV{BRLTTY_BRAILLE_DEVICE}="", ENV{BRLTTY_PID_FILE}="", '
        'GOTO="brltty_device_end"\n'
        + original)


def alias_rules():
    return (
        '# No serial number: keep HWT on this physical USB socket.\n'
        'SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", '
        'ATTR{idVendor}=="1a86", ATTR{idProduct}=="7523", '
        f'DEVPATH=="{DEV_PATH}", ENV{{ID_MM_DEVICE_IGNORE}}="1"\n'
        'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", '
        'ATTRS{idProduct}=="7523", '
        f'ENV{{ID_PATH}}=="{ID_PATH}:1.0", '
        'SYMLINK+="ttyUSB_HWT601", GROUP="dialout", MODE="0660", '
        'ENV{ID_MM_DEVICE_IGNORE}="1"\n')


def check_host():
    if platform.release() != RELEASE or platform.machine() != 'aarch64':
        raise ValueError(f'Nur fuer den vermessenen Jetson-Kernel {RELEASE}')


def check_device():
    path = Path(USB_PATH)
    if ((path / 'idVendor').read_text().strip(),
            (path / 'idProduct').read_text().strip()) != ('1a86', '7523'):
        raise ValueError('Der vermessene HWT-Adapter fehlt am bekannten USB-Port')


def prepare():
    if os.geteuid() == 0:
        raise ValueError('prepare ohne sudo ausfuehren; nur install braucht root')
    check_host()
    check_device()
    BUILD.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(SOURCE, timeout=30) as response:
        source = response.read(100000)
    if sha(source) != SOURCE_SHA:
        raise ValueError('Kernelquellen-Pruefsumme stimmt nicht')
    (BUILD / 'ch341.c').write_bytes(source)
    shutil.copyfile(ROOT / 'tools/sensorfusion/ch341/Makefile', BUILD / 'Makefile')
    run('make', '-C', f'/lib/modules/{RELEASE}/build', f'M={BUILD}',
        '-j2', 'modules')
    vermagic = subprocess.check_output(
        ['modinfo', '-F', 'vermagic', str(BUILD / 'ch341.ko')], text=True)
    if vermagic.split()[0] != RELEASE:
        raise ValueError('Modul passt nicht zum laufenden Kernel')
    original = VENDOR_RULE.read_text()
    (BUILD / '85-brltty.rules').write_text(brltty_rules(original))
    (BUILD / '83-hwt601.rules').write_text(alias_rules())
    (BUILD / 'manifest.json').write_text(json.dumps({
        'kernel': RELEASE, 'source_sha256': SOURCE_SHA,
        'vendor_rule_sha256': sha(original.encode()),
        'files': {name: sha((BUILD / name).read_bytes()) for name in
                  ('ch341.ko', '85-brltty.rules', '83-hwt601.rules')},
    }, indent=2) + '\n')
    print(f'Vorbereitet in {BUILD}; noch NICHT systemweit installiert.')


def install():
    if os.geteuid() != 0:
        raise ValueError('install braucht sudo; Passwort nur im lokalen Terminal')
    check_host()
    check_device()
    manifest = json.loads((BUILD / 'manifest.json').read_text())
    if manifest['vendor_rule_sha256'] != sha(VENDOR_RULE.read_bytes()):
        raise ValueError('brltty wurde aktualisiert; prepare erneut ausfuehren')
    if manifest['source_sha256'] != SOURCE_SHA or manifest['kernel'] != RELEASE:
        raise ValueError('Unpassendes Buildmanifest')
    targets = {'ch341.ko': MODULE, '85-brltty.rules': BRLTTY_RULE,
               '83-hwt601.rules': ALIAS_RULE}
    previous = STATE / 'manifest.json'
    if previous.exists() and json.loads(previous.read_text()) != manifest:
        raise ValueError('Andere Installation vorhanden; erst Rueckfall pruefen')
    # Complete preflight before the first system write. Never overwrite unknowns.
    for name, target in targets.items():
        if sha((BUILD / name).read_bytes()) != manifest['files'][name]:
            raise ValueError(f'Builddatei geaendert: {name}')
        if target.is_symlink() or (target.exists() and (
                not previous.exists()
                or sha(target.read_bytes()) != manifest['files'][name])):
            raise ValueError(f'Unbekannte Zieldatei bleibt unangetastet: {target}')
    STATE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BUILD / 'manifest.json', previous)
    for name, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            with target.open('xb') as output:
                output.write((BUILD / name).read_bytes())
            target.chmod(0o644)
    run('depmod', '-a', RELEASE)
    run('udevadm', 'control', '--reload-rules')
    # Release the falsely claimed USB interfaces once. Do not mask/uninstall
    # accessibility; the separate desktop brltty process is not touched.
    run('systemctl', 'stop', 'brltty-udev.service')
    run('modprobe', 'ch341')
    run('udevadm', 'trigger', '--action=add', USB_PATH)
    # Only HWT tty nodes, never trigger the motor or LiDAR USB interfaces.
    device = Path(USB_PATH).resolve()
    for tty in Path('/sys/class/tty').glob('ttyUSB*'):
        if device in (tty / 'device').resolve().parents:
            run('udevadm', 'trigger', '--action=add', str(tty))
    run('udevadm', 'settle', '--timeout=10')
    if not Path('/dev/ttyUSB_HWT601').exists():
        print('Installiert; HWT-USB kurz abziehen und am GLEICHEN Port einstecken.')
    else:
        print('/dev/ttyUSB_HWT601 vorhanden. Noch keine IMU-Messung/Abnahme.')
    print('Keine seriellen Ports geoeffnet, keine Motor-/Sensorregister geschrieben.')


def rollback():
    if os.geteuid() != 0:
        raise ValueError('rollback braucht sudo')
    check_host()
    manifest = json.loads((STATE / 'manifest.json').read_text())
    targets = {'ch341.ko': MODULE, '85-brltty.rules': BRLTTY_RULE,
               '83-hwt601.rules': ALIAS_RULE}
    for name, target in targets.items():
        if target.is_symlink() or (target.exists() and
                sha(target.read_bytes()) != manifest['files'][name]):
            raise ValueError(f'Seit Installation veraendert; nicht anfassen: {target}')
    if Path('/sys/module/ch341').exists():
        run('modprobe', '-r', 'ch341')  # Fails if in use; never force removal.
    backup = STATE / f'rollback-{time.time_ns()}'
    backup.mkdir()
    for name, target in targets.items():
        if target.exists():
            shutil.move(str(target), str(backup / name))
    shutil.move(str(STATE / 'manifest.json'), str(backup / 'manifest.json'))
    run('depmod', '-a', RELEASE)
    run('udevadm', 'control', '--reload-rules')
    print(f'Unsere Dateien nach {backup} verschoben, wiederherstellbar.')
    print('Urspruengliche brltty-Regeln gelten beim naechsten USB-Ereignis wieder.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install', 'rollback'))
    args = parser.parse_args()
    try:
        {'prepare': prepare, 'install': install, 'rollback': rollback}[args.action]()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Abbruch: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
