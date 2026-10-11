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
import pytest

from ap06_closed_product import device_parameters, device_process, finite_sensor_process, require_isolation


def block_one_state_publication():
    """An actual native-call pause holds this writer's interpreter lock."""
    from rclpy.publisher import Publisher
    original = Publisher.publish
    library = ctypes.PyDLL(None); library.usleep.argtypes = [ctypes.c_uint]
    count = [0]
    def publish(self, message):
        if self.topic_name == '/base_hardware/state_json':
            count[0] += 1
            if count[0] == 12:
                began = time.monotonic()
                library.usleep(350_000)
                ended = time.monotonic()
                Path(os.environ['AP06_WRITER_PAUSE_EVIDENCE']).write_text(json.dumps(
                    dict(pid=os.getpid(), begin=began, end=ended, duration_s=ended-began)))
        return original(self, message)
    Publisher.publish = publish


def paused_output_worker(*args):
    from base_hardware.encoder_publication import _send
    block_one_state_publication()
    _send(*args)


def paused_publication_device(*args):
    from base_hardware import encoder_publication
    block_one_state_publication()
    encoder_publication._send = paused_output_worker
    device_process(*args)


def test_configured_source_keeps_encoder_acquisition_during_actual_writer_pause(tmp_path, monkeypatch):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '186')
    pause_file = tmp_path/'writer_pause.json'
    monkeypatch.setenv('AP06_WRITER_PAUSE_EVIDENCE', str(pause_file))
    require_isolation()
    root = Path(__file__).resolve().parents[2]
    case = json.loads((root/'tools/simulation/ap06_product_scenarios.json').read_text())['positive'][2]
    device_file = tmp_path/'devices.yaml'
    device_file.write_text(yaml.safe_dump(device_parameters(root)))
    context = multiprocessing.get_context('spawn')
    telemetry = context.Array('d', [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0., 0., 0., 0.])
    ready, halt = context.Event(), context.Event()
    fault_value = context.Value('d', 0.)
    source_cpu = sorted(os.sched_getaffinity(0))[-1]
    source = context.Process(target=paused_publication_device, args=(case, tmp_path,
        device_file, True, 2160, fault_value, telemetry, ready, halt, source_cpu))
    states = []
    rclpy.init(); node = Node('ap06_blocked_writer_regression')
    executor = SingleThreadedExecutor(); executor.add_node(node)
    node.create_subscription(String, '/base_hardware/state_json',
        lambda m: states.append(json.loads(m.data)), 100)
    try:
        source.start(); deadline = time.monotonic()+20.
        while len(states) < 50 and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert ready.is_set() and len(states) >= 50
        assert all(s['encoder_feedback_ok'] for s in states)
        assert all(s['encoder_timing_recovery']['first_timing_rejection'] is None for s in states)
        assert all(s['encoder_sample_dt_s'] is None or s['encoder_sample_dt_s'] <= .18 for s in states)
        assert states[-1]['feedback_output_isolated'] is True
        pause = json.loads(pause_file.read_text())
        assert pause['duration_s'] >= .35 and pause['pid'] != source.pid
        # Delivery may really lose frames while blocked. No false continuity,
        # rewritten measurement stamp or filled-in sample is claimed here.
        assert states[-1]['encoder_position_left_u32'] == states[0]['encoder_position_left_u32']
    finally:
        halt.set()
        if source.pid is not None:
            source.join(5.)
            if source.is_alive(): source.terminate(); source.join(2.)
        executor.shutdown(timeout_sec=1.); node.destroy_node(); rclpy.shutdown()
    assert source.exitcode == 0


def paused_sensor_worker(*args):
    """A real sensor interpreter holds its GIL; never change measurement age."""
    from ap06_closed_product import Sensors
    original = Sensors.publish
    library = ctypes.PyDLL(None); library.usleep.argtypes = [ctypes.c_uint]
    def blocked(node):
        library.usleep(250_000)
        original(node)
    Sensors.publish = blocked
    finite_sensor_process(*args)


@pytest.mark.parametrize('sensor_pause', (False, True))
def test_real_encoder_source_survives_supervisor_interpreter_pause(tmp_path, monkeypatch, sensor_pause):
    monkeypatch.setenv('AP06_SIMULATION', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '186')
    require_isolation()
    root = Path(__file__).resolve().parents[2]
    case = json.loads((root/'tools/simulation/ap06_product_scenarios.json').read_text())['positive'][2]
    common = device_parameters(root)
    device_file = tmp_path/'devices.yaml'; device_file.write_text(yaml.safe_dump(common))
    context = multiprocessing.get_context('spawn')
    telemetry = context.Array('d', [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0., 0., 0., 0.])
    ready, halt = context.Event(), context.Event()
    fault_value = context.Value('d', 0.)
    source_cpu = sorted(os.sched_getaffinity(0))[-1]
    source = context.Process(target=device_process, args=(case, tmp_path, device_file, True,
        2160, fault_value, telemetry, ready, halt, source_cpu),
        kwargs={'sensor_worker': paused_sensor_worker} if sensor_pause else {})
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
    assert result['separate_finite_sensor_process']
    assert result['finite_sensor_process_exitcode'] == 0
    sensor = json.loads((tmp_path/'sensor_result.json').read_text())
    assert sensor['published'] > 0 and sensor['separate_process']
    assert not sensor['plant_integration'] and not sensor['writes_registers']


def test_finite_frames_keep_plant_acquisition_stamp_and_withhold_stale_input(tmp_path, monkeypatch):
    from sensor_msgs.msg import LaserScan
    from robot_interfaces.msg import NearFieldStatus
    from rclpy.qos import qos_profile_sensor_data
    monkeypatch.setenv('AP06_SIMULATION', '1'); monkeypatch.setenv('ROS_DOMAIN_ID', '185')
    require_isolation()
    case = dict(door_m=.8, start=[-1.6, 0., 0.])
    context = multiprocessing.get_context('spawn')
    telemetry = context.Array('d', [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0., 0., 0., 0.])
    ready, halt = context.Event(), context.Event()
    worker = context.Process(target=finite_sensor_process,
        args=(case, tmp_path, True, 2160, telemetry, ready, halt))
    rclpy.init(); node = Node('ap06_sensor_acquisition_regression')
    executor = SingleThreadedExecutor(); executor.add_node(node)
    received, supplied = [], set()
    def sample(message):
        received.append(message.header.stamp.sec*10**9+message.header.stamp.nanosec)
    node.create_subscription(LaserScan, '/scan', sample, qos_profile_sensor_data)
    node.create_subscription(NearFieldStatus, '/near_field/status', sample, 10)
    def feed():
        stamp = node.get_clock().now().to_msg()
        supplied.add(stamp.sec*10**9+stamp.nanosec)
        telemetry[:] = [*case['start'], 0., 0., 0., float('inf'), 0., 0., 0.,
                        time.monotonic(), float(stamp.sec), float(stamp.nanosec)]
    try:
        worker.start(); deadline = time.monotonic()+10.
        while len(received) < 6 and time.monotonic() < deadline:
            feed(); executor.spin_once(timeout_sec=.01)
        assert ready.is_set() and len(received) >= 6
        assert set(received) <= supplied  # original acquisitions, no later restamp
        frozen_stamp = int(telemetry[11])*10**9+int(telemetry[12])
        deadline = time.monotonic()+.7
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.02)
        assert set(received) <= supplied and max(received) <= frozen_stamp
        before = len(received); deadline = time.monotonic()+3.
        while len(received) < before+4 and time.monotonic() < deadline:
            feed(); executor.spin_once(timeout_sec=.01)
        assert len(received) >= before+4 and max(received) > frozen_stamp
        assert set(received) <= supplied
    finally:
        halt.set(); worker.join(3.)
        if worker.is_alive():
            worker.terminate(); worker.join(2.)
        executor.shutdown(timeout_sec=1.); node.destroy_node(); rclpy.shutdown()
    assert worker.exitcode == 0
    result = json.loads((tmp_path/'sensor_result.json').read_text())
    assert result['withheld_stale_plant'] >= 3
