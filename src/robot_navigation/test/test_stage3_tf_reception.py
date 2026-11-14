"""Original TF reaches the diagnostic buffer before a queued executor callback."""
import threading
import time
import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from tf2_msgs.msg import TFMessage
from geometry_msgs.msg import TransformStamped
from robot_navigation.stage3_motion_diagnostic import Stage3MotionDiagnostic
from robot_navigation.tf_reception import receive_latest_sources
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from geometry_msgs.msg import PoseStamped


def test_current_tf_received_without_executor_and_missing_tf_never_restamped():
    rclpy.init(args=[])
    consumer, producer = Node('stage3_tf_test_consumer'), Node('stage3_tf_test_producer')
    buffer = Buffer()
    listener = TransformListener(buffer, consumer)
    node = Stage3MotionDiagnostic.__new__(Stage3MotionDiagnostic)
    node._tf_buffer, node._tf_listener = buffer, listener
    node.get_clock = consumer.get_clock
    pub = producer.create_publisher(TFMessage, '/tf', 100)
    halt = threading.Event()
    def publish():
        while not halt.is_set():
            transforms = []
            for parent, child in [('map','odom'),('odom','base_link')]:
                t = TransformStamped()
                t.header.frame_id, t.child_frame_id = parent, child
                t.header.stamp = producer.get_clock().now().to_msg()
                t.transform.rotation.w = 1.
                transforms.append(t)
            pub.publish(TFMessage(transforms=transforms))
            halt.wait(.02)
    worker = threading.Thread(target=publish,daemon=True)
    try:
        deadline = time.monotonic()+3.
        while not pub.get_subscription_count() and time.monotonic()<deadline:time.sleep(.01)
        assert pub.get_subscription_count()
        worker.start()
        time.sleep(.35)  # actual publisher runs, listener executor withheld
        assert Stage3MotionDiagnostic._motion_tf_authorized(node)
        original = buffer.lookup_transform('odom','base_link',rclpy.time.Time()).header.stamp
        assert 0 <= (consumer.get_clock().now().nanoseconds-original.sec*10**9-original.nanosec)/1e9 < .2
        halt.set();worker.join(1.)
        node._refresh_current_tf()
        final = buffer.lookup_transform('odom','base_link',rclpy.time.Time()).header.stamp
        time.sleep(.25)
        assert not Stage3MotionDiagnostic._motion_tf_authorized(node)
        assert buffer.lookup_transform('odom','base_link',rclpy.time.Time()).header.stamp == final
    finally:
        halt.set()
        if worker.ident is not None:worker.join(1.)
        listener.unregister()
        consumer.destroy_node();producer.destroy_node()
        if rclpy.ok():rclpy.shutdown()


def test_latest_actual_source_before_decision_preserves_stamp_and_missing_age():
    rclpy.init(args=[])
    consumer, producer = Node('stage3_source_consumer'), Node('stage3_source_producer')
    values = []
    source_group = MutuallyExclusiveCallbackGroup()
    def callback(message):
        values.append((message, time.monotonic()))
    sub = consumer.create_subscription(PoseStamped, '/stage3_test_actual_pose', callback,
                                       10, callback_group=source_group)
    pub = producer.create_publisher(PoseStamped, '/stage3_test_actual_pose', 10)
    halt = threading.Event()
    original_stamps = set()
    def publish():
        sequence = 0
        while not halt.is_set():
            message = PoseStamped()
            message.header.stamp = producer.get_clock().now().to_msg()
            original_stamps.add((message.header.stamp.sec, message.header.stamp.nanosec))
            message.pose.position.x = float(sequence)
            pub.publish(message)
            sequence += 1
            halt.wait(.02)
    worker = threading.Thread(target=publish, daemon=True)
    try:
        deadline = time.monotonic()+3.
        while not pub.get_subscription_count() and time.monotonic()<deadline:time.sleep(.01)
        assert pub.get_subscription_count()
        worker.start()
        time.sleep(1.)  # exceeds existing .8 s source timeout; publisher remains real
        assert not values
        assert receive_latest_sources([(sub, callback)])
        assert len(values) == 1
        message, _ = values[-1]
        stamp = message.header.stamp
        assert (stamp.sec, stamp.nanosec) in original_stamps
        assert message.pose.position.x > 30
        assert 0 <= (consumer.get_clock().now().nanoseconds-stamp.sec*10**9-stamp.nanosec)/1e9 < .2
        halt.set();worker.join(1.)
        time.sleep(.05)
        assert receive_latest_sources([(sub, callback)])
        final_count, final_value = len(values), values[-1]
        time.sleep(.85)
        assert receive_latest_sources([(sub, callback)])
        assert len(values) == final_count and values[-1] == final_value
        stamp = values[-1][0].header.stamp
        assert (consumer.get_clock().now().nanoseconds-stamp.sec*10**9-stamp.nanosec)/1e9 > .8
    finally:
        halt.set()
        if worker.ident is not None:worker.join(1.)
        consumer.destroy_node();producer.destroy_node()
        if rclpy.ok():rclpy.shutdown()
