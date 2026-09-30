"""Actual DDS callbacks: a busy ordinary gate callback must not age sources."""
import json
import os
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
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate


@pytest.mark.parametrize('stop_wheel', [False, True])
def test_passive_sources_continue_during_busy_default_callback(stop_wheel):
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID', '-1')) <= 230
    rclpy.init(args=['--ros-args', '-p', 'require_hwt601_fusion:=true'])
    gate = CmdVelMissionGate()
    probe = Node('gate_source_callback_test_inputs')
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(gate)
    thread = threading.Thread(target=executor.spin, daemon=True)
    entered, exited = threading.Event(), threading.Event()
    def busy(_msg):
        entered.set()
        time.sleep(.35)
        exited.set()
    gate.create_subscription(String, '/test/gate_busy_callback', busy, 10)
    trigger = probe.create_publisher(String, '/test/gate_busy_callback', 10)
    raw = probe.create_publisher(Imu, '/shadow/hwt601/imu/data_raw', 10)
    yaw = probe.create_publisher(Imu, '/shadow/hwt601/imu/yaw_rate', 10)
    wheel = probe.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
    template = ready_health(False, now=time.monotonic())
    statuses = {
        key: probe.create_publisher(String, topic, 10)
        for key, topic in [('raw', '/shadow/hwt601/raw_status_json'),
                           ('yaw', '/shadow/hwt601/status_json'),
                           ('wheel', '/shadow/hwt601/wheel_status_json')]}
    def publish(include_wheel=True):
        stamp = probe.get_clock().now().to_msg()
        for pub, frame in [(raw, 'hwt601_link'), (yaw, 'base_link')]:
            m = Imu(); m.header.stamp = stamp; m.header.frame_id = frame
            m.angular_velocity_covariance[8] = .01; pub.publish(m)
        if include_wheel:
            m = Odometry(); m.header.stamp = stamp; m.header.frame_id = 'odom'
            m.child_frame_id = 'base_link'; m.twist.covariance[0] = .01
            wheel.publish(m)
        for key, pub in statuses.items():
            pub.publish(String(data=json.dumps(template.statuses[key][0])))
        time.sleep(.01)
    try:
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
                assert gate._hwt_guard.health.source_failure() is None
        end = time.monotonic()+1
        while not exited.is_set() and time.monotonic()<end:
            publish(not stop_wheel)
        assert exited.is_set()
        end = time.monotonic()+.15
        while time.monotonic()<end:
            publish(not stop_wheel)
        if stop_wheel:
            assert gate._hwt_guard.health.latched_fault == 'wheel_missing_stale_or_invalid'
        else:
            assert gate._hwt_guard.health.latched_fault is None
            assert gate._hwt_guard.health.source_failure() is None
        assert gate._mode == 'blocked'  # no mission, even with healthy inputs
    finally:
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
        assert all(s.callback_group is gate.default_callback_group
                   for s in gate._hwt_guard.subscriptions)
        wheel = gate._hwt_guard.subscriptions[2]
        assert wheel.qos_profile.depth == 5
    finally:
        gate.destroy_node(); rclpy.shutdown()
