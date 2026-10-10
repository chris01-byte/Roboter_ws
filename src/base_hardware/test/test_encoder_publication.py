"""Blocking publication must not block acquisition or restamp a sample."""
import multiprocessing
import time
from types import SimpleNamespace

from nav_msgs.msg import Odometry
from rclpy.serialization import deserialize_message
from base_hardware.encoder_publication import _Publisher


def _blocked_receiver(slot, entered, release, result):
    entered.set()
    release.wait(5.)
    result.put(slot.get(timeout=2.))


def test_full_interprocess_output_is_bounded_and_preserves_original_stamp():
    ctx = multiprocessing.get_context('spawn')
    slot, result = ctx.Queue(maxsize=1), ctx.Queue()
    entered, release = ctx.Event(), ctx.Event()
    child = ctx.Process(target=_blocked_receiver, args=(slot, entered, release, result))
    child.start()
    try:
        assert entered.wait(3.)
        publisher = _Publisher(slot)
        message = Odometry()
        message.header.stamp.sec = 12
        message.header.stamp.nanosec = 345
        message.pose.pose.position.x = 1.25
        for _ in range(200):
            publisher.publish(message)
        # All submissions returned while delivery was still blocked.
        assert child.is_alive() and not release.is_set()
        release.set()
        data, queued = result.get(timeout=3.)
        received = deserialize_message(data, Odometry)
        assert received == message
        assert queued <= time.monotonic()
    finally:
        release.set()
        child.join(3.)
        if child.is_alive():
            child.terminate(); child.join(2.)
        slot.cancel_join_thread(); slot.close()
        result.close()


def test_lost_output_process_latches_reader_and_closes_transport():
    from base_hardware.encoder_shadow_node import EncoderShadowNode
    from test_encoder_shadow_reader import healthy_core
    node = EncoderShadowNode.__new__(EncoderShadowNode)
    node.core = healthy_core()
    node.output = SimpleNamespace(alive=False)
    closed = []
    statuses = []
    node._close_transport = lambda: closed.append(True)
    node._publish_status_and_diagnostics = lambda **_: statuses.append(node.core.fault_reason)
    node._poll()
    assert closed and statuses == ['encoder_output_process_lost']
    assert not node.core.ready


def test_active_output_loss_stops_motor_owner_and_cannot_restore_motion():
    from base_hardware.base_hardware_node import BaseHardware, WheelCommand
    from test_encoder_shadow_reader import healthy_core
    node = BaseHardware.__new__(BaseHardware)
    node.feedback_output = SimpleNamespace(alive=False)
    node.feedback_output_fault_latched = False
    node.encoder_timing_core = healthy_core()
    node.active_wheel_cmd = WheelCommand(rpm_left=12., rpm_right=12.)
    node.dry_run, node.allow_rs485 = False, True
    stopped, logged = [], []
    node._send_stop_if_needed = lambda: stopped.append(True)
    node.get_logger = lambda: SimpleNamespace(error=lambda message: logged.append(message))
    node._check_feedback_output()
    assert stopped and logged
    assert node.active_wheel_cmd.rpm_left == node.active_wheel_cmd.rpm_right == 0.
    assert node.encoder_timing_core.fault_reason == 'encoder_output_process_lost'
    assert not node._encoder_motion_allowed()
    # A replaced publisher must never erase the physical owner's fault history.
    node.feedback_output.alive = True
    node._check_feedback_output()
    assert node.feedback_output_fault_latched
    assert not node._encoder_motion_allowed()


def test_live_output_does_not_change_motor_commands_or_touch_bus():
    from base_hardware.base_hardware_node import BaseHardware, WheelCommand
    node = BaseHardware.__new__(BaseHardware)
    node.feedback_output = SimpleNamespace(alive=True)
    node.feedback_output_fault_latched = False
    command = WheelCommand(rpm_left=12., rpm_right=-12.)
    node.active_wheel_cmd = command
    node._send_stop_if_needed = lambda: (_ for _ in ()).throw(AssertionError('unexpected motor write'))
    node._check_feedback_output()
    assert node.active_wheel_cmd is command
    assert not node.feedback_output_fault_latched


def test_motorless_base_output_has_single_owner_and_original_stamp():
    import rclpy
    from rclpy.parameter import Parameter
    from base_hardware.base_hardware_node import BaseHardware
    rclpy.init(args=['--ros-args', '-p', 'isolate_feedback_output:=true',
                     '-p', 'odom_topic:=/unit/base_output/odom',
                     '-p', 'state_topic:=/unit/base_output/state'])
    node = observer = None
    try:
        node = BaseHardware()
        node.timer.cancel()
        assert node.dry_run and not node.allow_rs485
        assert node.modbus_client is None
        observer = rclpy.create_node('base_output_test_observer')
        received = []
        subscription = observer.create_subscription(
            Odometry, '/unit/base_output/odom', received.append, 10)
        message = Odometry()
        message.header.stamp.sec, message.header.stamp.nanosec = 12, 345
        message.pose.pose.position.x = 1.25
        deadline = time.monotonic() + 5.
        while not received and time.monotonic() < deadline:
            node.odom_pub.publish(message)
            rclpy.spin_once(observer, timeout_sec=.02)
        assert received and received[-1] == message
        owners = observer.get_publishers_info_by_topic('/unit/base_output/odom')
        # DDS can deliver data before its node-name graph association arrives.
        while (len(owners) != 1 or owners[0].node_name == '_NODE_NAME_UNKNOWN_') and time.monotonic() < deadline:
            rclpy.spin_once(observer, timeout_sec=.02)
            owners = observer.get_publishers_info_by_topic('/unit/base_output/odom')
        assert len(owners) == 1
        assert owners[0].node_name == 'base_hardware_feedback_output'
        assert not node.set_parameters([
            Parameter('isolate_feedback_output', value=False)])[0].successful
        assert node.modbus_client is None
    finally:
        if node is not None:
            node.destroy_node()
        if observer is not None:
            observer.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
