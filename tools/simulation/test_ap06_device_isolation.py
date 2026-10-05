"""Original device probes continue when supervisor native code holds its GIL."""
import ctypes
import json
import multiprocessing
import os
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import yaml

from ap06_closed_product import device_process, require_isolation


def test_real_encoder_source_survives_supervisor_interpreter_pause(tmp_path, monkeypatch):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '186')
    require_isolation()
    root = Path(__file__).resolve().parents[2]
    case = json.loads((root/'tools/simulation/ap06_product_scenarios.json').read_text())['positive'][2]
    common = {
        'base_hardware': yaml.safe_load((root/'src/base_hardware/config/base_hardware_params.yaml').read_text())['base_hardware'],
        'hwt601_imu': yaml.safe_load((root/'src/robot_state_estimation/config/hwt601_shadow.yaml').read_text())['hwt601_shadow_reader']}
    common['base_hardware']['ros__parameters'].update(dry_run=False, allow_rs485=True,
        publish_tf=False, odom_topic='/fusion/hwt601/wheel_odom_raw', encoder_timing_recovery_enabled=True)
    common['hwt601_imu']['ros__parameters'].update(development_contract=True, response_timeout_s=.05, sensor_timeout_s=.30)
    device_file = tmp_path/'devices.yaml'; device_file.write_text(yaml.safe_dump(common))
    context = multiprocessing.get_context('spawn')
    telemetry = context.Array('d', [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0.])
    ready, halt = context.Event(), context.Event()
    fault_value = context.Value('d', 0.)
    source_cpu = sorted(os.sched_getaffinity(0))[-1]
    source = context.Process(target=device_process, args=(case, tmp_path, device_file, True,
        2160, fault_value, telemetry, ready, halt, source_cpu))
    states, stamps = [], []
    rclpy.init(args=[])
    node = Node('ap06_source_isolation_regression'); executor = SingleThreadedExecutor(); executor.add_node(node)
    node.create_subscription(String, '/base_hardware/state_json', lambda m: states.append(json.loads(m.data)), 100)
    node.create_subscription(Odometry, '/fusion/hwt601/wheel_odom_raw',
        lambda m: stamps.append(m.header.stamp.sec*10**9+m.header.stamp.nanosec), 100)
    def receive_until(predicate, budget=10.):
        deadline = time.monotonic()+budget
        while not predicate() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert predicate()
    try:
        source.start(); receive_until(lambda: ready.is_set() and len(stamps) >= 10)
        previous = stamps[-1]
        # PyDLL deliberately keeps THIS process's interpreter lock, emulating
        # a blocking native service/graph call without changing source time.
        library = ctypes.PyDLL(None); library.usleep.argtypes = [ctypes.c_uint]
        began = time.monotonic(); library.usleep(400_000)
        assert time.monotonic()-began >= .4
        receive_until(lambda: len(stamps) >= 30)
        during = [s for s in stamps if previous <= s <= previous+400_000_000]
        assert len(during) >= 5
        assert max(b-a for a,b in zip(stamps, stamps[1:])) <= 180_000_000
        assert states and all(s['encoder_feedback_ok'] for s in states)
        assert all(s['encoder_timing_recovery']['first_timing_rejection'] is None for s in states)
    finally:
        halt.set()
        if source.pid is not None:
            source.join(5.)
            if source.is_alive(): source.terminate(); source.join(2.)
        executor.shutdown(timeout_sec=1.); node.destroy_node(); rclpy.shutdown()
    assert source.exitcode == 0
    result = json.loads((tmp_path/'device_result.json').read_text())
    assert result['actual_cpu_affinity'] == [source_cpu]
