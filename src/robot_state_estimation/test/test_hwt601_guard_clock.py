"""Clock-pair regression: callback preemption must not count age twice."""
from types import SimpleNamespace
import pytest
from nav_msgs.msg import Odometry
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard
import robot_state_estimation.hwt601_fusion_guard as module
from test_hwt601_fusion_health import ready_health


@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('stale', [False, True])
def test_callback_work_before_clock_read_has_one_age_and_true_stale_still_stops(monkeypatch, active, stale):
    h=ready_health(active);assert h.source_failure(10.) is None
    guard=Hwt601FusionGuard.__new__(Hwt601FusionGuard);guard.health=h
    clock=SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=1000120000000),clock_type='ROS_TIME')
    guard.node=SimpleNamespace(get_clock=lambda:clock)
    # A real measurement at mono 10.010 / ROS 1000.010. Callback enters at
    # 10.020 but is preempted for 100 ms before pairing the two clocks.
    times=iter((10.020,10.120,10.120001))
    monkeypatch.setattr(module.time,'monotonic',lambda:next(times))
    msg=Odometry();msg.header.stamp.sec=1000;msg.header.stamp.nanosec=10000000
    msg.header.frame_id='odom';msg.child_frame_id='base_link';msg.twist.covariance[0]=.01
    guard._sample('wheel',msg)
    limit=.30 if active else .18;now=10.010+limit+(.001 if stale else -.01)
    for key in ('raw','yaw'):
        h.sample(key,now,now,now);h.status(key,h.statuses[key][0],now)
    h.status('wheel',h.statuses['wheel'][0],now)
    assert h.samples['wheel'][2] == pytest.approx(10.010)
    assert h.sample_details['wheel']['callback_entry_monotonic_s']==10.020
    assert h.sample_details['wheel']['twist_covariance']==[.01]+[0.]*35
    assert h.sample_details['wheel']['stamp_sec']==1000
    assert h.sample_details['wheel']['stamp_nanosec']==10000000
    assert h.source_failure(now)==('wheel_missing_stale_or_invalid' if stale else None)
    if stale:
        assert h.recovery_state=='TERMINAL_FAULT'


def test_receive_exception_preserves_original_sample_and_stops():
    guard = Hwt601FusionGuard.__new__(Hwt601FusionGuard)
    guard.active_drive = False
    guard.health = ready_health(False)
    assert guard.health.source_failure(10.) is None
    original = guard.health.samples['wheel']
    guard.health.sample_details['wheel'] = {'stamp_sec': 10, 'stamp_nanosec': 0}
    ended = []
    def broken_take(*_):
        raise RuntimeError('DDS receive failure')
    class BrokenHandle:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        take_message = staticmethod(broken_take)
    handle = BrokenHandle()
    guard.wheel_subscription = SimpleNamespace(
        callback_group=SimpleNamespace(beginning_execution=lambda _: True,
                                       ending_execution=lambda _: ended.append(True)),
        handle=handle, msg_type=Odometry, raw=False)
    guard.refresh_passive_wheel()
    assert ended == [True]
    assert guard.health.samples['wheel'][:3] == original[:3]
    assert guard.health.sample_details['wheel']['stamp_sec'] == 10
    assert guard.health.sample_details['wheel']['receive_exception'] == 'RuntimeError'
    assert guard.health.source_failure(10.01) == 'wheel_missing_stale_or_invalid'
    assert guard.health.last_fault['source_checks'][2]['original_message_and_clock_pair']['receive_exception'] == 'RuntimeError'


@pytest.mark.parametrize('active', [False, True])
def test_predecision_take_never_waits_for_an_owned_group_or_touches_active_source(active):
    guard = Hwt601FusionGuard.__new__(Hwt601FusionGuard)
    guard.active_drive = active
    guard.health = ready_health(active)
    touched = []
    guard.wheel_subscription = SimpleNamespace(
        callback_group=SimpleNamespace(beginning_execution=lambda _: touched.append(True) or False))
    original = dict(guard.health.samples)
    guard.refresh_passive_wheel()
    assert touched == ([] if active else [True])
    assert guard.health.samples == original
