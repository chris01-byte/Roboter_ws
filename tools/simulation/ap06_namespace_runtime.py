#!/usr/bin/env python3
"""Run the unchanged AP06 cases in real, device-free namespaces on ARM hosts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from ap06_isolation import namespace_ids


def command(repo, runtime, underlay, output, case, verify_only=False):
    repo, runtime, underlay, output = map(lambda p: Path(p).resolve(),
                                         (repo, runtime, underlay, output))
    if (not runtime.is_file() or not underlay.is_dir() or not repo.is_dir()
            or not output.parent.is_dir() or output.exists()
            or any((p/'.git').exists() for p in (output.parent, *output.parents))):
        raise ValueError('existing sources/runtime and new private output outside Git required')
    binary = shutil.which('bwrap')
    if not binary:
        raise RuntimeError('bubblewrap is unavailable; no host simulation fallback')
    argv = [binary, '--unshare-user', '--unshare-pid', '--unshare-net',
            '--unshare-ipc', '--unshare-uts', '--uid', '0', '--gid', '0',
            '--cap-add', 'CAP_NET_ADMIN', '--die-with-parent', '--new-session',
            '--clearenv', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/dev/shm',
            '--tmpfs', '/tmp', '--tmpfs', '/run', '--dir', '/etc']
    # No host root, /dev, /sys, /run, home or existing robot install is mounted.
    # Only declared executables, libraries, source and candidate are visible.
    for path in ('/usr', '/lib', '/lib64', '/bin', '/sbin', '/opt/ros',
                 str(repo), str(underlay), str(runtime.parent)):
        if Path(path).exists():
            argv += ['--ro-bind', path, path]
    for name in ('ld.so.cache', 'hosts', 'nsswitch.conf', 'passwd', 'group', 'os-release'):
        path = '/etc/'+name
        if Path(path).exists():
            argv += ['--ro-bind', path, path]
    argv += ['--bind', str(output.parent), str(output.parent),
             '--chdir', str(repo), '--setenv', 'HOME', '/tmp/ap06-home',
             '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',
             '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'AP06_SIMULATION', '1',
             '--setenv', 'AP06_NAMESPACE_PARENT', json.dumps(namespace_ids())]
    if verify_only:
        inner = ['python3', '-c',
                 'import json; from ap06_isolation import require_isolation; print(json.dumps(require_isolation()))']
        argv += ['--setenv', 'PYTHONPATH', str(repo/'tools/simulation')]
    else:
        inner = ['python3', str(repo/'tools/simulation/ap06_closed_product.py'),
                 '--repo', str(repo), '--output', str(output), '--case', case,
                 '--tf-probe', str(underlay/'tf-probe-build/tf_ownership_probe')]
    # All paths/case names are positional arguments; no shell interpolation.
    script = ('set -eo pipefail; ip link set lo up; mkdir -p "$HOME"; '
              'source "$1"; shift; export ROS_DOMAIN_ID=186; exec "$@"')
    return argv+['--', '/bin/bash', '--noprofile', '--norc', '-c', script,
                 'ap06-namespace', str(runtime), *inner]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--underlay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', choices=('door68_start_a', 'door68_start_b', 'door80_start_c'))
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if not args.verify_only and not args.case:
        parser.error('--case required for a full run')
    argv = command(args.repo, args.runtime, args.underlay, args.output,
                   args.case, args.verify_only)
    return subprocess.call(argv)


if __name__ == '__main__':
    raise SystemExit(main())
