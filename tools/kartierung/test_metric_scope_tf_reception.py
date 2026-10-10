"""Real local DDS: map/graph preparation must not hold up TF reception."""
import threading
import time

import pytest

from test_metric_scope_vorbereiten import tool


def test_scope_tf_keeps_original_current_stamps_while_main_collector_is_busy():
    rclpy = pytest.importorskip('rclpy')
    from geometry_msgs.msg import TransformStamped
    from rclpy.time import Time
    from tf2_ros import TransformBroadcaster, TransformException

    rclpy.init(args=[])
    node = rclpy.create_node('scope_reception_regression')
    sender = rclpy.create_node('scope_reception_source')
    broadcaster = TransformBroadcaster(sender)
    receiver = tool.ScopeTfListener(node)
    stop = threading.Event()

    def send():
        while not stop.is_set():
            message = TransformStamped()
            message.header.frame_id = 'synthetic_map'
            message.child_frame_id = 'synthetic_base'
            message.header.stamp = sender.get_clock().now().to_msg()
            message.transform.rotation.w = 1.0
            broadcaster.sendTransform(message)
            stop.wait(.01)

    worker = threading.Thread(target=send)
    worker.start()
    try:
        deadline = time.monotonic() + 4.
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            try:
                receiver.buffer.lookup_transform('synthetic_map', 'synthetic_base', Time())
                break
            except TransformException:
                pass
        else:
            pytest.fail('no original TF received')
        # Model time spent on current map/endpoint validation, without spinning
        # the collector. TF must arrive independently, with its source stamp.
        stop.wait(1.)
        latest = receiver.buffer.lookup_transform('synthetic_map', 'synthetic_base', Time())
        stamp = Time.from_msg(latest.header.stamp).nanoseconds
        assert 0 <= (sender.get_clock().now().nanoseconds - stamp) / 1e9 < .8
        stop.set()
        worker.join(2.)
        time.sleep(.1)  # drain the last real transmission before checking staleness
        last = receiver.buffer.lookup_transform('synthetic_map', 'synthetic_base', Time())
        time.sleep(.85)
        stale = receiver.buffer.lookup_transform('synthetic_map', 'synthetic_base', Time())
        assert stale.header.stamp == last.header.stamp
        assert (sender.get_clock().now().nanoseconds - Time.from_msg(stale.header.stamp).nanoseconds) / 1e9 > .8
    finally:
        stop.set()
        worker.join(2.)
        receiver.close()
        node.destroy_node()
        sender.destroy_node()
        rclpy.shutdown()
