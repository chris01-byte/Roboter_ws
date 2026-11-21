#!/usr/bin/env python3
"""Device-free SIGINT/save regression for the installed map manager.

Run after sourcing the intended overlay. Both rounds use a private DDS domain,
temporary maps, and no launch file, device driver, or motor process.
"""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

os.environ['ROS_DOMAIN_ID'] = '220'

import rclpy  # noqa: E402
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from rclpy.qos import (  # noqa: E402
    DurabilityPolicy, QoSProfile, ReliabilityPolicy,
)
from std_msgs.msg import String  # noqa: E402
from std_srvs.srv import Trigger  # noqa: E402


CHILD = '''
from pathlib import Path
import sys
import time
from robot_map_manager.map_core import MapRepository
from robot_map_manager.robot_map_manager_node import main

marker = Path(sys.argv[1])
storage = sys.argv[2]
original = MapRepository.save
def slow_save(self, snapshot, *, name=None, now=None):
    marker.write_text('save entered')
    time.sleep(0.35)
    return original(self, snapshot, name=name, now=now)
MapRepository.save = slow_save
main(args=['--ros-args', '-p', f'storage_directory:={storage}',
           '-p', 'minimum_free_space_bytes:=0',
           '-p', 'minimum_save_interval_s:=0.0'])
'''


def _until(predicate, timeout, message, node=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        if node is not None:
            rclpy.spin_once(node, timeout_sec=0.05)
        else:
            time.sleep(0.05)
    raise AssertionError(message)


def main():
    directory = Path(tempfile.mkdtemp(prefix='we-mapmanager-shutdown-'))
    print(f'EVIDENCE_DIRECTORY={directory}', flush=True)
    rclpy.init()
    node = rclpy.create_node('we_mapmanager_shutdown_smoke')
    qos = QoSProfile(depth=1)
    qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
    qos.reliability = ReliabilityPolicy.RELIABLE
    publisher = node.create_publisher(OccupancyGrid, '/map', qos)
    events = []
    node.create_subscription(
        String, '/robot_map_manager/status_json',
        lambda message: events.append(json.loads(message.data)), 10)
    client = node.create_client(Trigger, '/robot_map_manager/save_map')
    results = []
    try:
        for index in (1, 2):
            marker = directory / f'save-entered-{index}'
            storage = directory / f'maps-{index}'
            log_path = directory / f'node-{index}.log'
            baseline = len(events)
            with log_path.open('w', encoding='utf-8') as log:
                process = subprocess.Popen(
                    [sys.executable, '-c', CHILD, str(marker), str(storage)],
                    stdout=log, stderr=subprocess.STDOUT,
                    env=os.environ.copy())
                try:
                    _until(lambda: client.wait_for_service(timeout_sec=0.05),
                           8.0, 'Mapmanager-Dienst nicht gestartet', node)
                    grid = OccupancyGrid()
                    grid.header.frame_id = 'map'
                    grid.header.stamp = node.get_clock().now().to_msg()
                    grid.info.resolution = 0.05
                    grid.info.width = grid.info.height = 2
                    grid.info.origin.orientation.w = 1.0
                    grid.data = [0, 0, 0, 100]
                    _until(
                        lambda: (
                            publisher.publish(grid) is None
                            and any(event.get('event') in (
                                'map_received', 'map_observed')
                                    for event in events[baseline:])),
                        8.0, 'Mapmanager nahm Rohkarte nicht an', node)
                    response = client.call_async(Trigger.Request())
                    _until(marker.exists, 6.0,
                           'Save-Callback wurde nicht erreicht', node)
                    process.send_signal(signal.SIGINT)
                    _until(lambda: process.poll() is not None, 8.0,
                           'Mapmanager haengt nach SIGINT', node)
                    _until(response.done, 2.0,
                           'Save-Dienst lieferte keine Antwort', node)
                    assert response.result().success, response.result().message
                    assert process.returncode == 0, process.returncode
                    assert list(storage.rglob('map.yaml')), 'Save ging verloren'
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5.0)
            log_text = log_path.read_text(encoding='utf-8')
            assert 'Traceback' not in log_text, 'Unerklaerter Traceback'
            results.append({'round': index, 'exit': process.returncode,
                            'save_present': True, 'traceback': False})
    finally:
        node.destroy_node()
        rclpy.shutdown()
    (directory / 'result.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    main()
