"""A slow native timeout-timer allocation must not interrupt live sources."""
import ctypes
import json
import multiprocessing
import os
from pathlib import Path
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import yaml

from ap06_closed_product import device_parameters, device_process, require_isolation


def delayed_timeout_allocation_device(*args):
    """Keep actual ROS timers; expose the measured slow allocation boundary."""
    import rclpy.executors as executors
    original = executors.Timer
    library = ctypes.PyDLL(None)
    library.usleep.argtypes = [ctypes.c_uint]
    evidence = dict(timeout_allocations=0, pause=None)
    first = None

    def timer(callback, callback_group, period_ns, clock, **kwargs):
        nonlocal first
        if callback is None and callback_group is None and period_ns == 50_000_000:
            evidence['timeout_allocations'] += 1
            now = time.monotonic()
            if first is None:
                first = now
            if now-first >= 1.5 and evidence['pause'] is None:
                library.usleep(300_000)
                evidence['pause'] = dict(begin=now, end=time.monotonic())
        return original(callback, callback_group, period_ns, clock, **kwargs)

    executors.Timer = timer
    try:
        device_process(*args)
    finally:
        executors.Timer = original
        Path(args[1], 'timeout-allocation.json').write_text(json.dumps(evidence))


def test_native_timeout_allocation_cannot_interrupt_live_encoder_source(tmp_path, monkeypatch):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '186')
    require_isolation()
    repo = Path(__file__).resolve().parents[2]
    case = json.loads((repo/'tools/simulation/ap06_product_scenarios.json').read_text())['positive'][2]
    parameters = tmp_path/'devices.yaml'
    parameters.write_text(yaml.safe_dump(device_parameters(repo)))
    context = multiprocessing.get_context('spawn')
    telemetry = context.Array('d', [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0., 0., 0., 0.])
    ready, halt = context.Event(), context.Event()
    fault = context.Value('d', 0.)
    source = context.Process(target=delayed_timeout_allocation_device,
        args=(case, tmp_path, parameters, True, 2160, fault,
              telemetry, ready, halt, sorted(os.sched_getaffinity(0))[-1]))
    states, stamps = [], []
    rclpy.init()
    node = Node('ap06_timeout_allocation_regression')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    node.create_subscription(String, '/base_hardware/state_json',
        lambda message: states.append(json.loads(message.data)), 100)
    node.create_subscription(Odometry, '/fusion/hwt601/wheel_odom_raw',
        lambda message: stamps.append(message.header.stamp.sec*10**9+
                                      message.header.stamp.nanosec), 100)
    try:
        source.start()
        deadline = time.monotonic()+20.
        while len(stamps) < 70 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert ready.is_set() and len(stamps) >= 70
        assert states and all(s['encoder_feedback_ok'] for s in states)
        assert max(b-a for a, b in zip(stamps, stamps[1:])) <= 180_000_000
        assert all(s['encoder_sample_dt_s'] is None or
                   s['encoder_sample_dt_s'] <= .18 for s in states)
    finally:
        (tmp_path/'received_base_states.json').write_text(json.dumps(states))
        (tmp_path/'received_wheel_stamps.json').write_text(json.dumps(stamps))
        halt.set()
        if source.pid is not None:
            source.join(5.)
            if source.is_alive():
                source.terminate()
                source.join(2.)
        executor.shutdown(timeout_sec=1.)
        node.destroy_node()
        rclpy.shutdown()
    assert source.exitcode == 0
    proof = json.loads((tmp_path/'timeout-allocation.json').read_text())
    # Actual node timers continue to produce the measured samples. A polling
    # timeout needs no freshly allocated ROS timer in this periodic source loop.
    assert proof['timeout_allocations'] == 0 and proof['pause'] is None
