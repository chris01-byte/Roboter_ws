"""Actual TF2 time coverage for the SLAM start-body anchor, AP-06."""
from types import SimpleNamespace
import pytest
import rclpy
from rclpy.time import Time
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformException
from explore.metric_frontier_runtime import MetricFrontierRuntime


def relation(buffer, stamp_ns, x=0., roll_component=0.):
    t = TransformStamped()
    t.header.stamp = Time(nanoseconds=stamp_ns).to_msg()
    t.header.frame_id, t.child_frame_id = 'map', 'odom'
    t.transform.translation.x = x
    t.transform.rotation.x = roll_component
    t.transform.rotation.w = (1.-roll_component**2)**.5
    buffer.set_transform(t, 'actual_slam_profile')


@pytest.fixture
def anchor():
    rclpy.init(args=[])
    now = Time(nanoseconds=100_100_000_000)
    buffer = Buffer()
    runtime = SimpleNamespace(_tf_buffer=buffer, _global_frame='map',
        get_clock=lambda: SimpleNamespace(now=lambda: now), _door_pose_timeout=1.)
    yield runtime, buffer
    rclpy.shutdown()


def test_forward_dated_slam_interpolates_actual_current_relation(anchor):
    runtime, buffer = anchor
    relation(buffer, 100_000_000_000, x=.01)
    relation(buffer, 100_200_000_000, x=.03)
    # Counterexample: old latest lookup selects the future .03 endpoint.
    latest = buffer.lookup_transform('map', 'odom', Time())
    assert latest.header.stamp == Time(nanoseconds=100_200_000_000).to_msg()
    assert MetricFrontierRuntime._metric_body_reference(runtime) == pytest.approx((.02, 0., 0.))


@pytest.mark.parametrize('stamp', [99_000_000_000, 100_200_000_000])
def test_stale_or_future_only_relation_has_no_current_tf_coverage(anchor, stamp):
    runtime, buffer = anchor
    relation(buffer, stamp)
    with pytest.raises(TransformException):
        MetricFrontierRuntime._metric_body_reference(runtime)


def test_current_nonplanar_relation_remains_rejected(anchor):
    runtime, buffer = anchor
    relation(buffer, 100_000_000_000, roll_component=.1)
    relation(buffer, 100_200_000_000, roll_component=.1)
    with pytest.raises(ValueError, match='self_body_anchor_reference_invalid'):
        MetricFrontierRuntime._metric_body_reference(runtime)


def test_pose_and_reference_use_same_actual_common_tf_time(anchor):
    runtime, buffer = anchor
    relation(buffer, 100_000_000_000, x=.01)
    relation(buffer, 100_200_000_000, x=.03)
    base = TransformStamped()
    base.header.stamp = Time(nanoseconds=100_050_000_000).to_msg()
    base.header.frame_id, base.child_frame_id = 'odom', 'base_link'
    base.transform.translation.x = .5
    base.transform.rotation.w = 1.
    buffer.set_transform(base, 'actual_ekf')
    runtime._robot_base_frame = 'base_link'
    runtime._metric_body_reference = lambda stamp: MetricFrontierRuntime._metric_body_reference(runtime, stamp)
    pose, age, reference = MetricFrontierRuntime._metric_pose_and_reference(runtime)
    assert pose == pytest.approx((.515,0.,0.))
    assert reference == pytest.approx((.015,0.,0.))
    assert age == pytest.approx(.05)
