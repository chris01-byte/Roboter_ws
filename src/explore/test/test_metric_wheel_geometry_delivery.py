"""An actual queued wheel frame can bind geometry; missing data still expires."""
import threading
import time

import pytest
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard
from explore.explore_node import ExploreNode


def test_geometry_receives_actual_current_wheel_after_executor_pause(monkeypatch):
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '220')
    rclpy.init(args=[])
    consumer = Node('geometry_wheel_consumer')
    producer = Node('geometry_wheel_producer')
    guard = Hwt601FusionGuard(consumer, True, prefer_latest_wheel=True)
    pub = producer.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
    halt = threading.Event()
    def publish():
        while not halt.is_set():
            msg = Odometry()
            msg.header.frame_id = 'odom'; msg.child_frame_id = 'base_link'
            msg.header.stamp = producer.get_clock().now().to_msg()
            msg.pose.pose.orientation.w = 1.; msg.twist.covariance[0] = .01
            pub.publish(msg); halt.wait(.03)
    worker = threading.Thread(target=publish, daemon=True)
    node = ExploreNode.__new__(ExploreNode)
    node._hwt_guard = guard; node._metric_start_egress_enabled = True
    node._metric_path_validation = 'rpp_rollout'; node._metric_status = {}
    try:
        until = time.monotonic()+3.
        while not pub.get_subscription_count() and time.monotonic()<until:
            time.sleep(.01)
        assert pub.get_subscription_count()
        worker.start(); time.sleep(.12)
        guard.refresh_current_wheel()
        original = guard.health.samples['wheel']
        # Genuine publisher continues; consumer executor is not serviced.
        time.sleep(.28)
        assert time.monotonic()-original[2] > .18
        motion = node._metric_measured_motion((0.,0.,0.), (0.,0.,0.))
        assert motion[3] > original[0]
        assert all(0 <= time.monotonic()-at < .18 for at in motion[1:3])
        detail = guard.health.sample_details['wheel']
        assert motion[3] == detail['stamp_sec']+detail['stamp_nanosec']/1e9
        assert detail['delivery_path'] == 'explorer_predecision_dds_take'
        halt.set(); worker.join(1.); time.sleep(.03)
        guard.refresh_current_wheel()
        missing = guard.health.samples['wheel']
        time.sleep(.22)
        with pytest.raises(ValueError, match='start_motion_wheel_missing_stale_or_invalid'):
            node._metric_measured_motion((0.,0.,0.), (0.,0.,0.))
        assert guard.health.samples['wheel'] == missing
    finally:
        halt.set()
        if worker.ident is not None: worker.join(1.)
        producer.destroy_node(); consumer.destroy_node(); rclpy.shutdown()
