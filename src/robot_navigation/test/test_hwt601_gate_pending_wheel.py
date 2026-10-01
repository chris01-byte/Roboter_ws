"""Real DDS messages queued before the consumer decision, without executor spin."""
import json
import os
import sys
import time
from pathlib import Path

import pytest
import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from nav_msgs.msg import Odometry

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'robot_state_estimation' / 'test'))
sys.path.insert(0, str(ROOT / 'robot_navigation'))
from test_hwt601_fusion_health import ready_health
from robot_navigation.cmd_vel_mission_gate import CmdVelMissionGate


@pytest.mark.parametrize('sample_kind', ['fresh', 'stale', 'invalid', 'missing'])
def test_decision_takes_real_waiting_wheel_without_executor_callback(sample_kind):
    assert os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    assert 200 <= int(os.environ.get('ROS_DOMAIN_ID', '-1')) <= 230
    rclpy.init(args=['--ros-args', '-p', 'require_hwt601_fusion:=true'])
    gate = CmdVelMissionGate()
    probe = Node('gate_pending_wheel_inputs')
    pub = probe.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
    try:
        deadline = time.monotonic()+2
        while pub.get_subscription_count() == 0 and time.monotonic()<deadline:
            time.sleep(.01)
        assert pub.get_subscription_count() == 1
        now = time.monotonic()
        health = ready_health(False, now=now)
        assert health.source_failure(now) is None
        old_stamp = probe.get_clock().now().nanoseconds*1e-9-.5
        health.samples['wheel'] = (old_stamp, now-.5, now-.5, True)
        gate._hwt_guard.health = health
        original = None
        if sample_kind != 'missing':
            m = Odometry()
            m.header.stamp = (probe.get_clock().now() -
                              Duration(seconds=.4 if sample_kind == 'stale' else 0.)).to_msg()
            m.header.frame_id = 'odom'; m.child_frame_id = 'base_link'
            m.twist.covariance[0] = .01
            if sample_kind == 'invalid':
                m.twist.twist.linear.x = float('nan')
            original = (m.header.stamp.sec, m.header.stamp.nanosec)
            pub.publish(m)
            assert pub.wait_for_all_acked(Duration(seconds=.2))
        # No executor was spun. Only the actual gate decision can consume the
        # real queued measurement; the existing old sample is already stale.
        gate._publish()
        if sample_kind == 'fresh':
            assert health.latched_fault is None
            assert health.last_source_failure is None
        else:
            assert health.latched_fault == 'wheel_missing_stale_or_invalid'
        if original is not None:
            detail = health.sample_details['wheel']
            assert (detail['stamp_sec'], detail['stamp_nanosec']) == original
            assert detail['delivery_path'] == 'gate_predecision_dds_take'
            assert detail['callback_entry_monotonic_s'] is None
            assert detail['consumer_entry_monotonic_s'] >= now
        assert gate._mode == 'blocked'  # no mission or authorized motion
    finally:
        gate.destroy_node(); probe.destroy_node(); rclpy.shutdown()
