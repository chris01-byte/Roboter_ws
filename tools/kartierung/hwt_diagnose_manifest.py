#!/usr/bin/env python3
"""Record resolved HWT diagnostic software inputs; do not start ROS nodes."""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys

from ament_index_python.packages import get_package_prefix, PackageNotFoundError


PACKAGES = (
    'robot_state_estimation', 'robot_navigation', 'base_hardware',
    'vl53_near_field', 'explore', 'mission_manager', 'bt_orchestrator',
    'robot_bringup', 'behaviortree_ros2', 'behaviortree_cpp',
    'robot_localization', 'slam_toolbox',
)
PYTHON_DISTS = ('pyserial', 'smbus2', 'vl53l5cx', 'numpy')
MODULES = {
    'robot_state_estimation': (
        'hwt601_imu_node.py', 'hwt601_transport.py',
        'hwt601_fusion_health.py', 'hwt601_fusion_guard.py'),
    'robot_navigation': ('cmd_vel_mission_gate.py',),
    'vl53_near_field': ('vl53_near_field_node.py',),
}
REPO = Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def command(*args):
    try:
        result = subprocess.run(args, cwd=REPO, text=True, capture_output=True,
                                check=False)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def package_record(name):
    try:
        prefix = Path(get_package_prefix(name))
    except PackageNotFoundError:
        return {'resolved': False}
    manifest = prefix / 'share' / name / 'package.xml'
    modules = {}
    for filename in MODULES.get(name, ()):
        matches = sorted(prefix.glob(
            f'lib/python*/site-packages/{name}/{filename}'))
        modules[filename] = [
            {'path': str(path), 'sha256': sha256(path)} for path in matches
            if path.is_file()]
    executable_dir = prefix / 'lib' / name
    executables = (
        {path.name: sha256(path) for path in sorted(executable_dir.iterdir())
         if path.is_file()}
        if executable_dir.is_dir() else {})
    return {
        'resolved': True,
        'prefix': str(prefix),
        'installed_package_xml_sha256': sha256(manifest) if manifest.is_file() else None,
        'installed_modules': modules,
        'installed_executables_sha256': executables,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path,
                        help='local JSON path outside the repository')
    parser.add_argument('--profile', required=True, type=Path,
                        help='exact Explorer parameter overlay for the planned run')
    parser.add_argument('--launch-file', required=True,
                        help='package and launch file, e.g. robot_bringup/app_mapping.launch.py')
    parser.add_argument('--launch-arg', action='append', default=[], metavar='KEY=VALUE')
    parser.add_argument('--sourced-setup', action='append', default=[],
                        help='setup script sourced in this shell, in source order')
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    profile = args.profile.expanduser().resolve()
    if not profile.is_file():
        parser.error(f'profile not found: {profile}')
    if output == REPO or REPO in output.parents:
        parser.error('output must remain outside the repository')
    if not args.sourced_setup:
        parser.error('at least one --sourced-setup is required')
    launch_args = {}
    for item in args.launch_arg:
        if '=' not in item:
            parser.error(f'launch argument must be KEY=VALUE: {item}')
        key, value = item.split('=', 1)
        if not key or key in launch_args:
            parser.error(f'empty or duplicate launch argument: {key}')
        launch_args[key] = value

    packages = {name: package_record(name) for name in PACKAGES}
    dists = {}
    for name in PYTHON_DISTS:
        try:
            dists[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            dists[name] = None
    bt_prefix = packages['bt_orchestrator'].get('prefix')
    bt_exe = (Path(bt_prefix) / 'lib/bt_orchestrator/bt_orchestrator'
              if bt_prefix else None)
    bt_link_map = command('ldd', str(bt_exe)) if bt_exe and bt_exe.is_file() else None
    bt_library_lines = [line.strip() for line in (bt_link_map or '').splitlines()
                        if 'libbehaviortree_cpp' in line]
    dkms_status = command('dkms', 'status')
    vendor_pin = REPO / 'vendor_ch34x_mphsi.repos'
    manifest = {
        'captured_utc': datetime.now(timezone.utc).isoformat(),
        'purpose': 'motorless HWT first-fault diagnosis; no device opened by manifest',
        'source_root': str(REPO),
        'source_commit': command('git', 'rev-parse', 'HEAD'),
        'source_branch': command('git', 'branch', '--show-current'),
        'source_dirty': bool(command('git', 'status', '--porcelain')),
        'bt_submodule': command('git', 'rev-parse', 'HEAD:src/behaviortree_ros2'),
        'sourced_setup_scripts_declared': args.sourced_setup,
        'effective_ament_prefix_order':
            os.environ.get('AMENT_PREFIX_PATH', '').split(os.pathsep),
        'effective_cmake_prefix_order':
            os.environ.get('CMAKE_PREFIX_PATH', '').split(os.pathsep),
        'effective_library_search_order':
            os.environ.get('LD_LIBRARY_PATH', '').split(os.pathsep),
        'packages': packages,
        'python_distributions': dists,
        'ch341_vendor_repos_sha256': sha256(vendor_pin) if vendor_pin.is_file() else None,
        'ch341_dkms_status': [line for line in (dkms_status or '').splitlines()
                              if 'ch34' in line.lower()],
        'ros_behaviortree_cpp_apt_version': command(
            'dpkg-query', '-W', '-f=${Version}', 'ros-humble-behaviortree-cpp'),
        'bt_library_link_map': bt_library_lines,
        'profile': {'path': str(profile), 'sha256': sha256(profile)},
        'launch_file': args.launch_file,
        'launch_arguments': launch_args,
        'python_executable': sys.executable,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as target:
        json.dump(manifest, target, indent=2, ensure_ascii=False, allow_nan=False)
        target.write('\n')
    print(output)


if __name__ == '__main__':
    main()
