"""Actual DDS take returns a fresh frame; missing producer cannot be rejuvenated."""
import threading
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard


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
