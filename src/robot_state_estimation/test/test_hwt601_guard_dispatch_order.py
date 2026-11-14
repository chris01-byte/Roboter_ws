"""Real DDS callbacks: dispatch preemption is not sensor time regression."""
import threading
import time

import pytest
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.context import Context
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from nav_msgs.msg import Odometry

from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard


def wait(predicate, timeout=3.):
    until = time.monotonic()+timeout
    while not predicate():
        assert time.monotonic() < until, 'DDS test barrier expired'
        time.sleep(.005)


def message(node, name, stamp_ns):
    msg = Odometry() if name == 'wheel' else Imu()
    msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp_ns, 1000000000)
    msg.header.frame_id = {'raw': 'hwt601_link', 'yaw': 'base_link', 'wheel': 'odom'}[name]
    if name == 'wheel':
        msg.child_frame_id = 'base_link'
        msg.twist.covariance[0] = .01
    else:
        msg.angular_velocity_covariance[8] = .01
    return msg


@pytest.mark.parametrize('name', ['raw', 'yaw', 'wheel'])
@pytest.mark.parametrize('preempt_first', [True, False], ids=['dispatch-preemption', 'real-regression'])
def test_native_source_dispatch_order_and_real_stamp_regression(name, preempt_first):
    context = Context(); rclpy.init(context=context)
    node = Node('ap06_guard_order', context=context)
    executor = MultiThreadedExecutor(num_threads=3, context=context)
    guard = Hwt601FusionGuard(node, True, callback_group=ReentrantCallbackGroup())
    index = {'raw': 0, 'yaw': 1, 'wheel': 2}[name]
    subscription = guard.subscriptions[index]
    pub = node.create_publisher(subscription.msg_type, subscription.topic_name,
                                qos_profile_sensor_data)
    other_name = 'yaw' if name == 'raw' else 'raw'
    other = guard.subscriptions[{'raw': 0, 'yaw': 1}[other_name]]
    other_pub = node.create_publisher(other.msg_type, other.topic_name, qos_profile_sensor_data)
    other_processed = threading.Event()
    entered = threading.Event(); release = threading.Event()
    processed = []; sample = guard._sample
    stamp = node.get_clock().now().nanoseconds
    first = message(node, name, stamp-20000000)
    second = message(node, name, stamp-(10000000 if preempt_first else 30000000))
    def paused(key, msg, delivery=None):
        if key == name and msg.header.stamp == first.header.stamp:
            entered.set()
            if preempt_first:
                assert release.wait(3.), 'test callback release missing'
        sample(key, msg, delivery)
        if key == name:
            processed.append(msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec)
        elif key == other_name:
            other_processed.set()
    guard._sample = paused
    executor.add_node(node)
    spin = threading.Thread(target=executor.spin, daemon=True); spin.start()
    try:
        wait(lambda: pub.get_subscription_count() == 1)
        wait(lambda: other_pub.get_subscription_count() == 1)
        pub.publish(first); assert entered.wait(3.)
        if not preempt_first:
            wait(lambda: len(processed) == 1)
        pub.publish(second)
        if preempt_first:
            other_pub.publish(message(node, other_name, stamp-10000000))
            assert other_processed.wait(.2), 'one held source blocked another source'
            # Older dispatch is paused BEFORE Guard entry, reproducing B67.
            # A reentrant group lets the newer sample overtake it; a per-source
            # exclusive group queues it without blocking other sources.
            time.sleep(.12)
            release.set()
        wait(lambda: len(processed) == 2)
        value = guard.health.samples[name]
        if preempt_first:
            assert processed == [stamp-20000000, stamp-10000000]
            assert value[0] == pytest.approx((stamp-10000000)*1e-9, abs=1e-6)
            assert value[3] is True
            detail = guard.health.sample_details[name]
            assert detail['stamp_sec']*1000000000+detail['stamp_nanosec'] == stamp-10000000
        else:
            assert value[3] is False
            assert guard.health.sample_validation[name]['strictly_newer_stamp'] is False
    finally:
        release.set()
        executor.shutdown(timeout_sec=3.)
        spin.join(3.); node.destroy_node(); context.shutdown()
