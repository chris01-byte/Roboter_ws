"""The output worker preserves source bytes/QoS and cannot own a bus."""
import json
import time
from types import SimpleNamespace

import rclpy
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, ReliabilityPolicy
from sensor_msgs.msg import Imu

from robot_state_estimation.hwt601_imu_node import Hwt601ImuNode


def test_isolated_imu_preserves_original_message_qos_and_single_owner(monkeypatch, tmp_path):
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '219')
    monkeypatch.setenv('AP06_OUTPUT_TRACE_DIR', str(tmp_path))
    rclpy.init(args=['--ros-args', '-p', 'isolate_sensor_output:=true',
        '-p', 'imu_topic:=/unit/isolated_imu/raw',
        '-p', 'status_topic:=/unit/isolated_imu/status',
        '-p', 'diagnostics_topic:=/unit/isolated_imu/diagnostics'])
    node = observer = None
    try:
        node = Hwt601ImuNode()
        for timer in node.timers:
            timer.cancel()
        assert node._transport is None  # no serial connection for this test
        observer = rclpy.create_node('isolated_imu_observer')
        received = []
        observer.create_subscription(Imu, node.imu_topic, received.append,
                                     qos_profile_sensor_data)
        msg = Imu()
        msg.header.stamp.sec, msg.header.stamp.nanosec = 12, 345
        msg.header.frame_id = 'hwt601_link'
        msg.angular_velocity.z = .123
        msg.linear_acceleration.z = 9.81
        deadline = time.monotonic()+5.
        while not received and time.monotonic() < deadline:
            node.imu_pub.publish(msg)
            rclpy.spin_once(observer, timeout_sec=.02)
        assert received and received[-1] == msg
        owners = observer.get_publishers_info_by_topic(node.imu_topic)
        while (len(owners) != 1 or owners[0].node_name == '_NODE_NAME_UNKNOWN_') and time.monotonic() < deadline:
            rclpy.spin_once(observer, timeout_sec=.02)
            owners = observer.get_publishers_info_by_topic(node.imu_topic)
        assert len(owners) == 1 and owners[0].node_name == 'hwt601_imu_output'
        assert owners[0].qos_profile.reliability == ReliabilityPolicy.BEST_EFFORT
        # FastDDS endpoint discovery reports history depth as unknown (0).
        # Check the actual created Publisher in its private timing receipt.
        for topic in (node.status_topic, node.diagnostics_topic):
            endpoints = observer.get_publishers_info_by_topic(topic)
            assert len(endpoints) == 1
            assert endpoints[0].qos_profile.reliability == ReliabilityPolicy.RELIABLE
        assert not node.set_parameters([Parameter('isolate_sensor_output', value=False)])[0].successful
        assert node._transport is None
    finally:
        if node is not None:
            node.destroy_node()
        if observer is not None:
            observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    receipt = json.loads(next(tmp_path.glob('hwt601_imu_output-*-timing.json')).read_text())
    assert receipt['/unit/isolated_imu/raw']['qos_depth'] == qos_profile_sensor_data.depth
    assert receipt['/unit/isolated_imu/raw']['qos_reliability'] == int(ReliabilityPolicy.BEST_EFFORT)
    for topic in ('/unit/isolated_imu/status', '/unit/isolated_imu/diagnostics'):
        assert receipt[topic]['qos_depth'] == 10
        assert receipt[topic]['qos_reliability'] == int(ReliabilityPolicy.RELIABLE)


def test_output_loss_latches_poll_and_never_reopens_transport():
    node = Hwt601ImuNode.__new__(Hwt601ImuNode)
    node._sensor_output = SimpleNamespace(alive=False)
    node._terminal_fault = None
    closed = []
    node._disconnect = lambda: closed.append(True)
    node._check_clock_source = lambda: (_ for _ in ()).throw(AssertionError('poll after output loss'))
    node._poll()
    assert closed and node._terminal_fault == 'hwt_sensor_output_process_lost'
    node._sensor_output.alive = True
    node._poll()
    assert node._terminal_fault == 'hwt_sensor_output_process_lost'
