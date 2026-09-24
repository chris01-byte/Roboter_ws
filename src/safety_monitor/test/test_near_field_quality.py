"""The optional VL53 hard-stop may not clear on missing/invalid frames."""

import time
from types import SimpleNamespace

from robot_interfaces.msg import NearFieldStatus
from safety_monitor.safety_monitor_node import SafetyMonitor


def _monitor():
    node = SafetyMonitor.__new__(SafetyMonitor)
    output = []
    node._use_near_field = True
    node._nf_timeout = 0.8
    node._nf_estop_dist = 0.08
    node._request_estop = False
    node._near_estop = True
    node._near_last_valid_at = None
    node._last_published = None
    node._estop_pub = SimpleNamespace(
        publish=lambda message: output.append(message.data))
    node.get_logger = lambda: SimpleNamespace(
        warn=lambda *_args: None, info=lambda *_args: None)
    node.get_clock = lambda: SimpleNamespace(
        now=lambda: SimpleNamespace(nanoseconds=10_000_000_000))
    return node, output


def _status(quality=NearFieldStatus.QUALITY_VALID_FAR, second=10):
    status = NearFieldStatus()
    status.header.frame_id = 'base_link'
    status.header.stamp.sec = second
    status.left_quality = quality
    status.right_quality = quality
    status.left_observed_columns = status.right_observed_columns = 255
    status.min_dist_left = -1.0
    status.min_dist_right = -1.0
    status.min_dist_middle = -1.0
    return status


def test_valid_empty_far_can_clear_but_unknown_and_partial_cannot():
    node, output = _monitor()
    node._on_near_field(_status())
    assert node._near_estop is False and output[-1] is False
    node._on_near_field(_status(NearFieldStatus.QUALITY_UNKNOWN))
    assert node._near_estop is True and output[-1] is True
    node._on_near_field(_status(NearFieldStatus.QUALITY_PARTIAL))
    assert node._near_estop is True


def test_near_obstacle_and_stale_or_future_status_stay_stopped():
    node, output = _monitor()
    near = _status(NearFieldStatus.QUALITY_VALID_NEAR)
    near.min_dist_left = 0.05
    node._on_near_field(near)
    assert node._near_estop is True
    node._on_near_field(_status(second=9))
    assert node._near_estop is True
    node._on_near_field(_status(second=11))
    assert node._near_estop is True
    node._on_near_field(_status())
    assert node._near_estop is False
    node._near_last_valid_at = time.monotonic() - 1.0
    node._tick()
    assert node._near_estop is True and output[-1] is True
