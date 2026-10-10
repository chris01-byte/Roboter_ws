"""Actual DDS take returns a fresh frame; missing producer cannot be rejuvenated."""
import threading
import time
import pytest
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard


@pytest.mark.parametrize('active', [False, True])
def test_metric_status_uses_latest_actual_dds_message_and_missing_status_ages(monkeypatch, active):
    import json
    from std_msgs.msg import String
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '224')
    rclpy.init(args=[])
    consumer, producer = Node('metric_status_consumer'), Node('metric_status_producer')
    guard = Hwt601FusionGuard(consumer, active, prefer_latest_wheel=True)
    pubs = [producer.create_publisher(String, sub.topic_name, 10)
            for sub in guard.subscriptions[3:6]]
    halt = threading.Event()
    def publish():
        while not halt.is_set():
            payload = json.dumps({'actual_publication_ns': time.time_ns(), 'ready': True})
            for pub in pubs:
                pub.publish(String(data=payload))
            halt.wait(.05)
    worker = threading.Thread(target=publish, daemon=True)
    try:
        deadline = time.monotonic()+3.
        while not all(p.get_subscription_count() for p in pubs) and time.monotonic()<deadline:
            time.sleep(.01)
        assert all(p.get_subscription_count() for p in pubs)
        assert all(s.qos_profile.depth == 1 for s in guard.subscriptions[3:6])
        assert all(s.callback_group is not consumer.default_callback_group
                   for s in guard.subscriptions[3:6])
        worker.start()
        time.sleep(1.2)  # actual producer continues during withheld executor
        guard.refresh_current_imu()
        for name in ('raw', 'yaw', 'wheel'):
            payload, received = guard.health.statuses[name]
            assert 0 <= (time.time_ns()-payload['actual_publication_ns'])/1e9 < .3
            assert 0 <= time.monotonic()-received < .3
        halt.set(); worker.join(1.)
        guard.refresh_current_status()
        original = dict(guard.health.statuses)
        time.sleep(1.1); guard.refresh_current_status()
        assert guard.health.statuses == original
        assert all(time.monotonic()-entry[1] > 1. for entry in original.values())
        pubs[0].publish(String(data='invalid JSON'))
        time.sleep(.1); guard.refresh_current_status()
        assert guard.health.statuses['raw'][0] == {}
    finally:
        halt.set()
        if worker.ident is not None: worker.join(1.)
        producer.destroy_node(); consumer.destroy_node(); rclpy.shutdown()


def test_metric_predecision_reads_original_current_wheel_and_preserves_missing_age(monkeypatch):
    monkeypatch.setenv('ROS_LOCALHOST_ONLY','1');monkeypatch.setenv('ROS_DOMAIN_ID','220')
    rclpy.init(args=[])
    consumer=Node('metric_latest_wheel_consumer'); producer=Node('metric_latest_wheel_producer')
    guard=Hwt601FusionGuard(consumer,True,prefer_latest_wheel=True)
    pub=producer.create_publisher(Odometry,'/fusion/hwt601/wheel_odom_raw',10)
    halt=threading.Event()
    def publish():
        while not halt.is_set():
            msg=Odometry();msg.header.frame_id='odom';msg.child_frame_id='base_link'
            msg.header.stamp=producer.get_clock().now().to_msg()
            msg.twist.covariance[0]=.01;msg.pose.pose.orientation.w=1.
            pub.publish(msg);halt.wait(.05)
    worker=threading.Thread(target=publish,daemon=True)
    try:
        deadline=time.monotonic()+3.
        while not pub.get_subscription_count() and time.monotonic()<deadline:time.sleep(.01)
        assert pub.get_subscription_count()
        worker.start()
        # No executor service during the actual backlog. The original
        # current DDS message, not cached status, must supply its old stamp.
        time.sleep(.4)
        guard.refresh_current_wheel()
        sample=guard.health.samples['wheel'];details=guard.health.sample_details['wheel']
        assert sample[3] and 0<=time.monotonic()-sample[2]<.18
        assert details['delivery_path']=='explorer_predecision_dds_take'
        assert details['frame_id']=='odom' and details['child_frame_id']=='base_link'
        halt.set();worker.join(1.)
        guard.refresh_current_wheel();original=guard.health.samples['wheel']
        time.sleep(.2);guard.refresh_current_wheel()
        assert guard.health.samples['wheel']==original
        assert time.monotonic()-original[2]>.18
    finally:
        halt.set()
        if worker.ident is not None:worker.join(1.)
        producer.destroy_node();consumer.destroy_node();rclpy.shutdown()


@pytest.mark.parametrize('active', [False, True])
def test_metric_predecision_takes_latest_imu_without_executor_and_never_restamps(monkeypatch, active):
    from sensor_msgs.msg import Imu
    monkeypatch.setenv('ROS_LOCALHOST_ONLY', '1')
    monkeypatch.setenv('ROS_DOMAIN_ID', '220')
    rclpy.init(args=[])
    consumer = Node('metric_latest_imu_consumer')
    producer = Node('metric_latest_imu_producer')
    guard = Hwt601FusionGuard(consumer, active, prefer_latest_wheel=True)
    pubs = [producer.create_publisher(Imu, sub.topic_name, 10)
            for sub in guard.subscriptions[:2]]
    halt = threading.Event()
    def publish():
        while not halt.is_set():
            for name, pub in zip(('raw', 'yaw'), pubs):
                msg = Imu()
                msg.header.frame_id = 'hwt601_link' if name == 'raw' else 'base_link'
                msg.header.stamp = producer.get_clock().now().to_msg()
                msg.angular_velocity_covariance[8] = .01
                pub.publish(msg)
            halt.wait(.02)
    worker = threading.Thread(target=publish, daemon=True)
    try:
        deadline = time.monotonic()+3.
        while not all(p.get_subscription_count() for p in pubs) and time.monotonic()<deadline:
            time.sleep(.01)
        assert all(p.get_subscription_count() for p in pubs)
        assert all(s.qos_profile.depth == 1 for s in guard.subscriptions[:2])
        assert all(s.callback_group is not consumer.default_callback_group
                   for s in guard.subscriptions[:2])
        worker.start()
        time.sleep(.45)  # producer runs, consumer executor intentionally withheld
        guard.refresh_current_imu()
        for name in ('raw', 'yaw'):
            sample = guard.health.samples[name]
            assert sample[3] and 0 <= time.monotonic()-sample[2] < .18
            detail = guard.health.sample_details[name]
            assert detail['delivery_path'] == 'imu_predecision_dds_take'
            assert sample[0] == detail['stamp_sec']+detail['stamp_nanosec']/1e9
        halt.set(); worker.join(1.)
        guard.refresh_current_imu()
        original = dict(guard.health.samples)
        time.sleep(.4)
        guard.refresh_current_imu()
        assert guard.health.samples == original
        assert all(time.monotonic()-original[n][2] > .35 for n in ('raw', 'yaw'))
    finally:
        halt.set()
        if worker.ident is not None: worker.join(1.)
        producer.destroy_node(); consumer.destroy_node(); rclpy.shutdown()
