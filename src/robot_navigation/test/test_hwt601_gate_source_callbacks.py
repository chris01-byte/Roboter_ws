"""Actual DDS callbacks: a busy ordinary gate callback must not age sources."""
import json
import multiprocessing
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from std_msgs.msg import String

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'robot_state_estimation' / 'test'))
sys.path.insert(0, str(ROOT / 'robot_navigation'))
from test_hwt601_fusion_health import ready_health
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate, spin_passive_gate


def _source_process(stopped, wheel_enabled, ready):
    """Actual fresh DDS messages from a separate producer, like base/HWT."""
    rclpy.init(args=[])
    node = Node('gate_source_callback_test_inputs')
    raw = node.create_publisher(Imu, '/shadow/hwt601/imu/data_raw', 10)
    yaw = node.create_publisher(Imu, '/shadow/hwt601/imu/yaw_rate', 10)
    wheel = node.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
    template = ready_health(False, now=time.monotonic())
    statuses = {key: node.create_publisher(String, topic, 10) for key, topic in [
        ('raw', '/shadow/hwt601/raw_status_json'),
        ('yaw', '/shadow/hwt601/status_json'),
        ('wheel', '/shadow/hwt601/wheel_status_json')]}
    try:
        ready.set()
        while not stopped.is_set():
            stamp = node.get_clock().now().to_msg()
            for pub, frame in [(raw, 'hwt601_link'), (yaw, 'base_link')]:
                m = Imu(); m.header.stamp = stamp; m.header.frame_id = frame
                m.angular_velocity_covariance[8] = .01; pub.publish(m)
            if wheel_enabled.is_set():
                m = Odometry(); m.header.stamp = stamp; m.header.frame_id = 'odom'
                m.child_frame_id = 'base_link'; m.twist.covariance[0] = .01
                wheel.publish(m)
            for key, pub in statuses.items():
                pub.publish(String(data=json.dumps(template.statuses[key][0])))
            stopped.wait(.01)
    finally:
        node.destroy_node(); rclpy.shutdown()


@pytest.mark.parametrize('stop_wheel', [False, True])
@pytest.mark.parametrize('busy_group', ['default', 'imu_status'])
def test_passive_wheel_continues_during_busy_callback(stop_wheel, busy_group):
    # A real gate starts in its own process. Reusing rclpy's global context
    # after other DDS tests left Humble executor wait-set threads racing the
    # next context (including a NoneType.handle teardown exception). Keep the
    # original real subscriptions, executor and freshness assertions inside
    # a fresh process, rather than forgiving a delayed measurement.
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
        busy_group, 'stop' if stop_wheel else 'continue'],
        capture_output=True, text=True, timeout=20.)
    assert result.returncode == 0, result.stdout + result.stderr


def _passive_wheel_case(stop_wheel, busy_group):
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID', '-1')) <= 230
    rclpy.init(args=['--ros-args', '-p', 'require_hwt601_fusion:=true'])
    gate = CmdVelMissionGate()
    probe = Node('gate_source_callback_test_control')
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(gate)
    executor_stop = threading.Event()
    thread = threading.Thread(target=spin_passive_gate,
        args=(executor, executor_stop.is_set), daemon=True)
    entered, exited = threading.Event(), threading.Event()
    release = threading.Event()
    def busy(_msg):
        entered.set()
        # Explicit barrier keeps the intended callback busy while the probe
        # evaluates source freshness. Scheduling delay before acquiring the
        # health lock must not accidentally end the simulated blocking work.
        release.wait(timeout=2.)
        exited.set()
    gate.create_subscription(String, '/test/gate_busy_callback', busy, 10,
                             callback_group=(gate._hwt_source_cb
                                             if busy_group == 'imu_status' else None))
    trigger = probe.create_publisher(String, '/test/gate_busy_callback', 10)
    context = multiprocessing.get_context('spawn')
    source_stop, wheel_enabled, source_ready = (context.Event() for _ in range(3))
    wheel_enabled.set()
    sources = context.Process(target=_source_process,
        args=(source_stop, wheel_enabled, source_ready))
    def publish(include_wheel=True):
        # Only control the independent producer. A busy gate's Python GIL
        # must not prevent the test from PRODUCING fresh wheel measurements.
        (wheel_enabled.set if include_wheel else wheel_enabled.clear)()
        time.sleep(.01)
    try:
        sources.start()
        assert source_ready.wait(3.)
        thread.start()
        end = time.monotonic()+3
        while time.monotonic()<end:
            publish()
            with gate._hwt_guard.health.lock:
                if gate._hwt_guard.health.was_ready:
                    break
        assert gate._hwt_guard.health.was_ready
        trigger.publish(String(data='block ordinary callback'))
        end = time.monotonic()+2
        while not entered.is_set() and time.monotonic()<end:
            publish()
        assert entered.is_set()
        with gate._hwt_guard.health.lock:
            before = gate._hwt_guard.health.samples['wheel'][0]
        # At .25 s the ordinary callback is still blocked. Actual source
        # callbacks must have progressed independently, without restamping.
        end = time.monotonic()+.25
        while time.monotonic()<end:
            publish(not stop_wheel)
        assert not exited.is_set()
        with gate._hwt_guard.health.lock:
            after = gate._hwt_guard.health.samples['wheel'][0]
            if not stop_wheel:
                assert after > before
                assert time.monotonic()-gate._hwt_guard.health.samples['wheel'][2] < .18
                # Fresh IMU callbacks now progress independently of a busy
                # status callback. Its still-fresh status must not cause HOLD.
                assert gate._hwt_guard.health.source_failure() is None
        if busy_group == 'imu_status' and not stop_wheel:
            # A genuinely missing status is still a fault after its existing
            # deadline, even while original raw/yaw measurements stay fresh.
            end = time.monotonic()+1.05
            while time.monotonic()<end:
                publish()
            assert not exited.is_set()
            with gate._hwt_guard.health.lock:
                assert all(time.monotonic()-gate._hwt_guard.health.samples[n][2] < .18
                           for n in ('raw', 'yaw', 'wheel'))
                assert gate._hwt_guard.health.source_failure() is not None
                assert gate._hwt_guard.health.recovery_state == 'TERMINAL_FAULT'
                assert gate._hwt_guard.health.latched_fault.endswith('_status_missing_or_stale')
        release.set()
        end = time.monotonic()+1
        while not exited.is_set() and time.monotonic()<end:
            publish(not stop_wheel)
        assert exited.is_set()
        end = time.monotonic()+(1.3 if busy_group == 'imu_status' else .15)
        while time.monotonic()<end:
            publish(not stop_wheel)
        if stop_wheel:
            assert gate._hwt_guard.health.latched_fault == 'wheel_missing_stale_or_invalid'
        elif busy_group == 'imu_status':
            # A later status must not silently clear a genuine hard loss.
            assert gate._hwt_guard.health.latched_fault.endswith('_status_missing_or_stale')
        else:
            assert gate._hwt_guard.health.latched_fault is None
            assert gate._hwt_guard.health.source_failure() is None
        assert gate._mode == 'blocked'  # no mission, even with healthy inputs
    finally:
        release.set()
        source_stop.set(); sources.join(timeout=3.)
        if sources.is_alive():
            sources.terminate(); sources.join(timeout=2.)
        executor_stop.set(); thread.join(timeout=2.)
        executor.shutdown(timeout_sec=2)
        thread.join(timeout=2)
        gate.destroy_node(); probe.destroy_node(); rclpy.shutdown()


def test_active_gate_keeps_its_existing_serial_source_group():
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID', '-1')) <= 230
    rclpy.init(args=['--ros-args', '-p', 'require_hwt601_fusion:=true',
                    '-p', 'hwt601_active_drive:=true'])
    gate = CmdVelMissionGate()
    try:
        assert gate._hwt_source_cb is None
        assert gate._hwt_wheel_cb is None
        assert all(s.callback_group is gate.default_callback_group
                   for s in gate._hwt_guard.subscriptions)
        wheel = gate._hwt_guard.subscriptions[2]
        assert wheel.qos_profile.depth == 5
    finally:
        gate.destroy_node(); rclpy.shutdown()


def test_active_diagnostic_selects_current_measurements_without_explore_opt_in():
    rclpy.init(args=['--ros-args', '-p', 'require_hwt601_fusion:=true',
                    '-p', 'hwt601_active_drive:=true',
                    '-p', 'allow_explore_mission:=false',
                    '-p', 'allow_stage3_motion_diagnostic:=true'])
    gate = CmdVelMissionGate()
    try:
        assert gate._hwt_guard.prefer_latest_wheel is True
        assert all(s.qos_profile.depth == 1 for s in gate._hwt_guard.subscriptions[:3])
        assert len({id(s.callback_group) for s in gate._hwt_guard.subscriptions[:3]}) == 3
        # Selecting current DDS does not invent measurements or readiness.
        gate._hwt_guard.refresh_current_wheel()
        gate._hwt_guard.refresh_current_imu()
        assert gate._hwt_guard.health.was_ready is False
        assert gate._hwt_guard.health.source_failure() is not None
        assert gate._mode == 'blocked'
    finally:
        gate.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    assert len(sys.argv) == 3 and sys.argv[1] in ('default', 'imu_status')
    assert sys.argv[2] in ('stop', 'continue')
    _passive_wheel_case(sys.argv[2] == 'stop', sys.argv[1])
