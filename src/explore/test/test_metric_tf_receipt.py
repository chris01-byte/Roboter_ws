"""Actual DDS reception after processing, retaining TF/wheel source checks."""
import threading
import time

import pytest
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener

from explore.explore_node import ExploreNode
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard


@pytest.fixture
def actual_pair():
    rclpy.init(args=[])
    producer = Node('metric_tf_actual_producer')
    consumer = Node('metric_tf_actual_consumer')
    buffer = Buffer()
    listener = TransformListener(buffer, consumer)
    guard = Hwt601FusionGuard(consumer, True, prefer_latest_wheel=True)
    executor = SingleThreadedExecutor()
    executor.add_node(consumer)
    tf_pub = producer.create_publisher(TFMessage, '/tf', 100)
    wheel_pub = producer.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
    halt = threading.Event()
    origin = time.monotonic()
    sent = []
    errors = []

    def publish():
        try:
            while not halt.is_set():
                x = .1 * (time.monotonic() - origin)
                stamp = producer.get_clock().now().to_msg()
                transforms = []
                for parent, child, value in (('map', 'odom', 0.), ('odom', 'base_link', x)):
                    t = TransformStamped()
                    t.header.frame_id, t.child_frame_id = parent, child
                    t.header.stamp = stamp
                    t.transform.translation.x = value
                    t.transform.rotation.w = 1.
                    transforms.append(t)
                tf_pub.publish(TFMessage(transforms=transforms))
                wheel = Odometry()
                wheel.header.frame_id, wheel.child_frame_id = 'odom', 'base_link'
                wheel.header.stamp = stamp
                wheel.pose.pose.position.x = x
                wheel.pose.pose.orientation.w = 1.
                wheel.twist.covariance[0] = .01
                wheel_pub.publish(wheel)
                sent.append((stamp.sec, stamp.nanosec, x))
                halt.wait(.02)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=publish, daemon=True)
    node = ExploreNode.__new__(ExploreNode)
    node._tf_buffer, node._tf_listener, node._hwt_guard = buffer, listener, guard
    node._global_frame, node._robot_base_frame = 'map', 'base_link'
    node._door_pose_timeout = .5
    node._metric_start_egress_enabled = True
    node._metric_path_validation = 'rpp_rollout'
    node._metric_status = {}
    node.get_clock = consumer.get_clock
    worker.start()
    try:
        deadline = time.monotonic() + 5.
        while time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.01)
            if (buffer.can_transform('map', 'base_link', rclpy.time.Time())
                    and guard.health.samples.get('wheel')):
                break
        else:
            pytest.fail('actual TF/wheel DDS discovery')
        yield node, consumer, executor, halt, worker, sent
        assert not errors
    finally:
        halt.set()
        worker.join(1.)
        executor.shutdown(timeout_sec=1.)
        listener.unregister()
        consumer.destroy_node()
        producer.destroy_node()
        rclpy.shutdown()


def test_pending_original_tf_fixes_false_wheel_disagreement_without_restamping(actual_pair):
    node, consumer, executor, halt, worker, sent = actual_pair
    subscriptions = tuple(consumer.subscriptions)
    before = node._metric_pose_and_reference()
    # Actual producers continue while no consumer callback is dispatched.
    time.sleep(.3)
    halt.set()
    worker.join(1.)
    listener = node._tf_listener
    node._tf_listener = None
    old = node._metric_pose_and_reference()
    assert old[0] == before[0]
    with pytest.raises(ValueError, match='start_motion_wheel_tf_disagreement'):
        node._metric_measured_motion(old[0], old[2])
    assert node._metric_status['motion_binding_rejection']['position_error_m'] > .02
    node._tf_listener = listener
    after = node._metric_pose_and_reference()
    motion = node._metric_measured_motion(after[0], after[2])
    assert after[0][0] > old[0][0] + .02
    assert motion[0] == pytest.approx(after[0])
    assert tuple(consumer.subscriptions) == subscriptions
    latest = node._tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
    source_stamp = (latest.header.stamp.sec, latest.header.stamp.nanosec)
    assert source_stamp == sent[-1][:2]
    assert latest.transform.translation.x == sent[-1][2]
    # Empty reception does not create coverage or refresh the source timestamp.
    time.sleep(.55)
    with pytest.raises(ValueError, match='self_body_anchor_reference_invalid'):
        node._metric_pose_and_reference()
    final = node._tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
    assert (final.header.stamp.sec, final.header.stamp.nanosec) == source_stamp


def test_destroyed_tf_receive_handle_cannot_reuse_fresh_buffer(actual_pair):
    node, consumer, *_ = actual_pair
    assert node._metric_pose_and_reference()[1] < .5
    consumer.destroy_subscription(node._tf_listener.tf_sub)
    with pytest.raises(ValueError, match='self_body_anchor_tf_receive_failed'):
        node._metric_pose_and_reference()


def test_pending_receive_coexists_with_actual_parallel_listener_callbacks(actual_pair):
    node, consumer, single, halt, worker, sent = actual_pair
    single.remove_node(consumer)
    parallel = MultiThreadedExecutor(num_threads=3)
    parallel.add_node(consumer)
    errors = []

    def spin():
        try:
            parallel.spin()
        except Exception as exc:
            errors.append(exc)

    dispatcher = threading.Thread(target=spin, daemon=True)
    dispatcher.start()
    stamps = []
    try:
        for _ in range(80):
            pose, age, reference = node._metric_pose_and_reference()
            assert 0 <= age < .5
            motion = node._metric_measured_motion(pose, reference)
            assert abs(pose[0] - motion[0][0]) <= .02
            tf = node._tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            stamps.append((tf.header.stamp.sec, tf.header.stamp.nanosec))
            time.sleep(.01)
        assert stamps == sorted(stamps)
        assert set(stamps).issubset({row[:2] for row in sent})
    finally:
        parallel.shutdown(timeout_sec=1.)
        dispatcher.join(1.)
        parallel.remove_node(consumer)
    assert not errors
