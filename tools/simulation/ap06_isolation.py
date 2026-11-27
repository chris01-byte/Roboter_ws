"""Verify a device-free AP06 container without manufacturing Docker markers."""
import json
import os
from pathlib import Path

NAMESPACES = ('user', 'mnt', 'pid', 'net', 'ipc', 'uts')


def namespace_ids():
    return {name: os.readlink('/proc/self/ns/'+name) for name in NAMESPACES}


def require_isolation():
    try:
        domain = int(os.environ.get('ROS_DOMAIN_ID', '-1'))
    except ValueError:
        domain = -1
    devices = ('/dev/ttyUSB_BASE', '/dev/ttyUSB_HWT601', '/etc/nv_tegra_release')
    if (os.environ.get('AP06_SIMULATION') != '1' or not 100 <= domain <= 200
            or any(Path(p).exists() for p in devices)):
        raise RuntimeError('device-free container and dedicated simulation domain required')
    current = namespace_ids()
    if Path('/.dockerenv').exists():
        return {'kind': 'docker', 'namespaces': current, 'domain': domain,
                'hardware_aliases_absent': True}
    try:
        parent = json.loads(os.environ['AP06_NAMESPACE_PARENT'])
        valid = (type(parent) is dict and set(parent) == set(NAMESPACES)
                 and all(type(parent[n]) is str and parent[n].startswith(n+':[')
                         and parent[n].endswith(']') and parent[n] != current[n]
                         for n in NAMESPACES))
    except (KeyError, ValueError, TypeError):
        valid = False
    if not valid:
        raise RuntimeError('verified separate user/mount/PID/network/IPC/UTS namespaces required')
    return {'kind': 'bubblewrap', 'namespaces': current, 'host_namespaces': parent,
            'domain': domain, 'hardware_aliases_absent': True}
