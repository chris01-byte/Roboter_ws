"""AP-01: actual raw poll/error methods, deterministic clocks, no devices."""
from collections import deque
import json
from types import SimpleNamespace

import pytest

pytest.importorskip('rclpy')
from rclpy.clock import Clock, ClockType
from rclpy.time import Time
from robot_state_estimation.hwt601_imu_node import Hwt601ImuNode
from robot_state_estimation import hwt601_imu_node as raw_module


class Sink:
    def __init__(self):
        self.messages = []

    def publish(self, msg):
        self.messages.append(msg)


class Timeline:
    def __init__(self):
        self.mono = 10.0
        self.offset_ns = 1000 * 10**9
        self.pairs = deque()
        self.clock_type = ClockType.SYSTEM_TIME
        self.reads = 0
        self.callback_clock = Clock(clock_type=ClockType.SYSTEM_TIME)
        self.create_jump_callback = self.callback_clock.create_jump_callback

    def now(self):
        before, after = self.pairs.popleft() if self.pairs else (0., 0.)
        self.mono += before
        ns = round(self.mono * 1e9) + self.offset_ns
        self.mono += after
        self.reads += 1
        return Time(nanoseconds=ns)


class Reply:
    is_open = True

    def __init__(self, timeline, timeout):
        self.timeline = timeline
        self.timeout = timeout
        self.processing_s = 0.
        self.receipt = 'current'
        self.last_transaction = {}
        self.last_reply_received_monotonic_s = None
        self.registers = (0, 0, 0, 0, 0, 0)

    def read_motion_registers(self):
        start = self.timeline.mono - .001
        self.last_transaction = dict(started_monotonic_s=start,
            deadline_monotonic_s=start + self.timeout, timeout_s=self.timeout,
            classification='complete_on_time', header_received_bytes=3,
            payload_received_bytes=14, identity_intact=True)
        self.last_reply_received_monotonic_s = (
            self.timeline.mono if self.receipt == 'current' else self.receipt)
        self.timeline.mono += self.processing_s
        return self.registers

    def close(self):
        self.is_open = False


@pytest.fixture
def rig(monkeypatch):
    t = Timeline()
    monkeypatch.setattr(raw_module.time, 'monotonic', lambda: t.mono)
    n = Hwt601ImuNode.__new__(Hwt601ImuNode)
    n.__dict__.update(development_contract=True, response_timeout_s=.05,
        sensor_timeout_s=.30, port='/synthetic/hwt', baud=115200,
        device_address=80, frame_id='hwt601_link', imu_topic='/synthetic/raw',
        _last_received_at=None, _last_measurement_stamp_ns=None,
        _last_transport_diagnostic={}, _terminal_fault=None, _accepted=0,
        _rejected=0, _successful_connections=1, _consecutive_errors=0,
        _last_error='', _sample_times=deque(), errors_before_reconnect=3,
        acceleration_full_scale_g=4., angular_velocity_full_scale_dps=400.,
        saturation_margin_counts=8, angular_velocity_variance=.02,
        linear_acceleration_variance=.25)
    n.get_clock = lambda: t
    n.status_pub = Sink()
    n.imu_pub = Sink()
    n.diagnostics_pub = Sink()
    link = Reply(t, n.response_timeout_s)
    n._transport = link
    n._init_clock_correlation()
    return n, t, link


def stamp(msg):
    return msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec


def test_original_20ms_pause_does_not_latch_and_next_receipt_is_published(rig):
    n, t, link = rig
    n._poll()
    assert stamp(n.imu_pub.messages[-1]) == 1010_000_000_000
    t.mono = 10.010
    t.pairs.append((0., .020))
    n._poll()
    assert n._terminal_fault is None, n._last_error
    assert link.is_open
    if len(n.imu_pub.messages) == 2:
        assert stamp(n.imu_pub.messages[-1]) == 1010_010_000_000
    t.mono = 10.040
    n._poll()
    assert stamp(n.imu_pub.messages[-1]) == 1010_040_000_000
    assert n._accepted >= 2


def test_two_precise_receipts_10ms_apart(rig):
    n, t, _ = rig
    n._poll()
    t.mono += .01
    n._poll()
    assert [stamp(m) for m in n.imu_pub.messages] == [1010_000_000_000, 1010_010_000_000]
    assert n._last_received_at == pytest.approx(10.01)


@pytest.mark.parametrize('offset_ns', [10**12, 10**15])
def test_changing_small_brackets_form_a_valid_conservative_stream(rig, offset_ns):
    n, t, _ = rig
    t.offset_ns = offset_ns
    expected = []
    for i, (before, after) in enumerate(((.0001,.0005), (.0004,.0001),
                                        (.0002,.0006), (.00005,.00003)) * 3):
        t.mono = 10. + i * .01
        expected.append(round(t.mono*1e9) + offset_ns)
        t.pairs.append((before, after))
        n._poll()
    assert n._accepted == len(expected) and n._rejected == 0
    stamps = [stamp(m) for m in n.imu_pub.messages]
    assert all(0 <= true - actual <= 1_000_001 for true, actual in zip(expected, stamps))
    assert all(b > a for a, b in zip(stamps, stamps[1:]))


@pytest.mark.parametrize('phase', ['before', 'inside_before_read', 'inside_after_read', 'after'])
def test_processing_delays_keep_actual_receipt_not_merely_monotone_stamps(rig, monkeypatch, phase):
    n, t, link = rig
    n._poll()  # Precise retained offset, so later uncertainty cannot move it.
    for i, delay in enumerate((.020, .007, .020)):
        t.mono = 10.050 + i * .050
        receipt = round(t.mono * 1e9) + t.offset_ns
        link.processing_s = delay if phase == 'before' else 0.
        if phase.startswith('inside_'):
            t.pairs.append((delay, 0.) if phase.endswith('before_read') else (0., delay))
        original_decode = raw_module.decode_motion_registers
        if phase == 'after':
            def delayed_decode(*args, **kwargs):
                result = original_decode(*args, **kwargs)
                t.mono += delay
                return result
            with monkeypatch.context() as patch:
                patch.setattr(raw_module, 'decode_motion_registers', delayed_decode)
                n._poll()
        else:
            n._poll()
        assert n._terminal_fault is None
        assert stamp(n.imu_pub.messages[-1]) == receipt
    assert n._accepted == 4


def test_persistent_wide_brackets_discard_then_precise_sample_resumes(rig):
    n, t, _ = rig
    t.pairs.extend([(.003, .003)] * 3)
    n._poll()
    assert not n.imu_pub.messages and n._last_received_at is None
    assert n._last_measurement_stamp_ns is None and n._terminal_fault is None
    d = json.loads(n.status_pub.messages[-1].data)
    assert d['clock_correlation']['classification'] == 'clock_pair_uncertain'
    assert d['clock_correlation']['attempts'] == 3
    t.mono = 10.030
    n._poll()
    assert [stamp(m) for m in n.imu_pub.messages] == [1010_030_000_000]
    assert n._accepted == 1 and n._rejected == 1


def test_repeated_uncertainty_does_not_refresh_last_valid_data(rig):
    n, t, link = rig
    n._poll()
    initial = (n._last_received_at, n._last_measurement_stamp_ns)
    for elapsed in (.02, .1, .2, .31):
        t.mono = 10. + elapsed
        t.pairs.extend([(0., .003)] * 3)
        n._poll()
        assert (n._last_received_at, n._last_measurement_stamp_ns) == initial
    d = json.loads(n.status_pub.messages[-1].data)
    assert n._accepted == 1 and n._rejected == 4 and link.is_open
    assert not d['ready'] and not d['data_fresh'] and d['hold_required']
    assert d['data_valid'] and d['terminal_fault'] is None


@pytest.mark.parametrize('development,timeout,freshness', [(True,.05,.30),(False,.03,.20)])
@pytest.mark.parametrize('phase', ['processing', 'retry', 'after_decode', 'message_construction'])
def test_total_deadline_covers_processing_pair_retries_and_message_construction(
        rig, monkeypatch, development, timeout, freshness, phase):
    n, t, link = rig
    n.development_contract = development
    n.response_timeout_s = link.timeout = timeout
    n.sensor_timeout_s = freshness
    if phase == 'processing':
        link.processing_s = timeout + .001
    elif phase == 'retry':
        t.pairs.extend([(0., timeout*.6)] * 3)
    elif phase == 'after_decode':
        original_decode = raw_module.decode_motion_registers
        def late(*args, **kwargs):
            result = original_decode(*args, **kwargs)
            t.mono += timeout + .001
            return result
        monkeypatch.setattr(raw_module, 'decode_motion_registers', late)
    else:
        actual_imu = raw_module.Imu
        def late_message():
            t.mono += timeout + .001
            return actual_imu()
        monkeypatch.setattr(raw_module, 'Imu', late_message)
    n._poll()
    assert not n.imu_pub.messages and n._last_received_at is None
    assert n._terminal_fault is None
    assert 'Gesamtfrist' in n._last_error
    if development:
        d = json.loads(n.status_pub.messages[-1].data)
        assert d['last_transport_diagnostic']['classification'] == 'processing_after_deadline'


@pytest.mark.parametrize('receipt', [None, float('nan'), float('inf'), -float('inf'), 10.001, 9.9])
def test_invalid_receive_evidence_never_uses_publish_time(rig, receipt):
    n, _, link = rig
    link.receipt = receipt
    n._poll()
    assert not n.imu_pub.messages and n._terminal_fault
    assert not link.is_open


@pytest.mark.parametrize('receipt', [10., 9.9999])
def test_repeated_or_regressed_receipt_is_hard(rig, receipt):
    n, t, link = rig
    n._poll()
    t.mono = 10.0001
    link.receipt = receipt
    n._poll()
    assert len(n.imu_pub.messages) == 1 and n._terminal_fault


@pytest.mark.parametrize('delta_ns', [-2_000_000, 2_000_000, -20_000_000, 20_000_000])
def test_independent_ros_jump_is_hard_even_when_headers_would_still_increase(rig, delta_ns):
    n, t, link = rig
    t.pairs.append((.0001, .0001))
    n._poll()
    last = stamp(n.imu_pub.messages[-1])
    t.mono = 10.01
    t.offset_ns += delta_ns
    t.pairs.append((.0001, .0001))
    n._poll()
    assert 'Zeitbasis' in n._terminal_fault
    assert len(n.imu_pub.messages) == 1 and not link.is_open
    t.offset_ns -= delta_ns
    t.mono += .01
    n._poll()
    assert len(n.imu_pub.messages) == 1  # Recognized change never rebases away.
    if abs(delta_ns) == 2_000_000:
        assert last < 1010_010_000_000 + delta_ns


def test_wide_bracket_can_still_prove_a_hard_jump(rig):
    n, t, _ = rig
    n._poll()
    t.mono += .01
    t.offset_ns += 30_000_000
    t.pairs.extend([(0., .003)] * 3)
    n._poll()
    assert 'Zeitbasis' in n._terminal_fault
    assert n._receipt_clock.diagnostic['classification'] == 'clock_basis_changed'


@pytest.mark.parametrize('source_change', ['object', 'steady'])
def test_clock_source_replacement_is_never_silently_rebased(rig, source_change):
    n, t, _ = rig
    n._poll()
    if source_change == 'object':
        n.get_clock = lambda: Timeline()
    else:
        t.clock_type = ClockType.STEADY_TIME
    n._poll()
    assert n._terminal_fault and len(n.imu_pub.messages) == 1


@pytest.mark.parametrize('toggle_back', [False, True])
def test_actual_rosclock_timesource_activation_and_deactivation_latch(rig, toggle_back):
    from rclpy.clock import ROSClock
    from rclpy.time_source import TimeSource
    n, t, link = rig
    actual_clock = ROSClock()
    source = TimeSource()
    source.attach_clock(actual_clock)
    n.get_clock = lambda: actual_clock
    n._init_clock_correlation()
    n._poll()  # Inactive real ROSClock uses host time, within a real bracket.
    assert n._accepted == 1
    source.ros_time_is_active = True
    actual_clock.set_ros_time_override(Time(seconds=1010.))
    unchanged_monotonic = t.mono
    actual_clock.set_ros_time_override(Time(seconds=1009.998))
    assert actual_clock.now().nanoseconds == 1009_998_000_000
    assert t.mono == unchanged_monotonic
    if toggle_back:
        source.ros_time_is_active = False
    n._poll()
    assert 'Clockquelle' in n._terminal_fault
    assert len(n.imu_pub.messages) == 1 and not link.is_open
    n._clock_jump_handle.unregister()


def test_actual_rosclock_simulation_active_at_start_is_rejected_before_read(rig):
    from rclpy.clock import ROSClock
    from rclpy.time_source import TimeSource
    n, _, link = rig
    clock, source = ROSClock(), TimeSource()
    source.attach_clock(clock)
    source.ros_time_is_active = True
    n.get_clock = lambda: clock
    n._init_clock_correlation()
    n._poll()
    assert n._terminal_fault and not n.imu_pub.messages and not link.last_transaction
    n._clock_jump_handle.unregister()


def test_saturation_remains_hard_with_valid_time(rig):
    n, _, link = rig
    link.registers = (32767, 0, 0, 0, 0, 0)
    n._poll()
    assert 'gesaettigt' in n._terminal_fault and not n.imu_pub.messages


def connected_guard(n, t):
    from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard
    from test_hwt601_fusion_health import ready_health
    n.port = '/dev/ttyUSB_HWT601'  # Advertised fixture identity, no device open.
    guard = Hwt601FusionGuard.__new__(Hwt601FusionGuard)
    guard.health = ready_health(False, now=t.mono, development=True)
    guard.node = SimpleNamespace(get_clock=lambda: t)
    return guard


def other_inputs_current(guard, t):
    for key in ('yaw', 'wheel'):
        guard.health.sample(key, t.mono+1000., t.mono, t.mono)
        guard.health.status(key, guard.health.statuses[key][0], t.mono)


@pytest.mark.parametrize('delivery_s', [0., .00005, .002])
@pytest.mark.parametrize('bracket', [(0.,0.), (.0003,.0005), (.0007,.0001)])
def test_generated_headers_pass_actual_guard_and_health_without_future_fault(rig, delivery_s, bracket):
    n, t, _ = rig
    guard = connected_guard(n, t)
    t.pairs.append(bracket)
    n._poll()
    n._publish_status()
    t.mono += delivery_s
    guard._sample('raw', n.imu_pub.messages[-1])
    guard._status('raw', n.status_pub.messages[-1])
    other_inputs_current(guard, t)
    assert guard.health.source_failure(t.mono) is None
    assert guard.health.recovery_state == 'HEALTHY'
    assert guard.health.samples['raw'][2] <= t.mono
    assert 0 <= 10. - guard.health.samples['raw'][2] <= .001000001


def test_existing_guard_still_rejects_a_slightly_future_header(rig):
    n, t, _ = rig
    guard = connected_guard(n, t)
    n._poll()
    n._publish_status()
    guard._sample('raw', n.imu_pub.messages[-1])
    guard._status('raw', n.status_pub.messages[-1])
    assert guard.health.source_failure(t.mono) is None
    future = raw_module.Imu()
    future.header = n.imu_pub.messages[-1].header
    future.header.stamp.nanosec += 1_000_000
    future.angular_velocity_covariance[8] = .02
    t.mono += .0001  # Future by only 0.9 ms at delivery.
    guard._sample('raw', future)
    other_inputs_current(guard, t)
    assert guard.health.source_failure(t.mono) == 'raw_missing_stale_or_invalid'
    assert guard.health.recovery_state == 'TERMINAL_FAULT'


def test_repeated_discard_ages_original_sample_into_actual_health_hold(rig):
    n, t, _ = rig
    guard = connected_guard(n, t)
    n._poll()
    n._publish_status()
    guard._sample('raw', n.imu_pub.messages[-1])
    guard._status('raw', n.status_pub.messages[-1])
    assert guard.health.source_failure(t.mono) is None
    original = guard.health.samples['raw']
    for elapsed in (.02, .1, .2, .31):
        t.mono = 10. + elapsed
        t.pairs.extend([(0., .003)] * 3)
        n._poll()
        guard._status('raw', n.status_pub.messages[-1])
        other_inputs_current(guard, t)
        assert guard.health.samples['raw'] == original
        failure = guard.health.source_failure(t.mono)
        if elapsed < .3:
            assert failure is None
        else:
            assert failure == 'raw_missing_stale_or_invalid'
            assert guard.health.recovery_state == 'HOLD'
            assert guard.health.latched_fault is None
    assert len(n.imu_pub.messages) == 1 and n._terminal_fault is None


@pytest.mark.parametrize('fragmented', [False, True])
def test_real_transport_receipt_survives_decode_delay_and_reaches_poll(rig, monkeypatch, fragmented):
    from robot_state_estimation.hwt601_transport import Hwt601SerialTransport
    from robot_state_estimation import hwt601_transport as transport_module
    from test_hwt601_transport import FakeSerial
    n, t, _ = rig
    transport = Hwt601SerialTransport('/synthetic/serial', 115200, .05, 80,
                                     serial_factory=FakeSerial)
    transport.open()
    read = transport._serial.read
    def advancing_read(length):
        result = read(min(length, 1) if fragmented else length)
        t.mono += .0001
        return result
    transport._serial.read = advancing_read
    parse = transport_module.parse_read_holding_response
    def delayed_decode(*args):
        result = parse(*args)
        t.mono += .007
        return result
    monkeypatch.setattr(transport_module, 'parse_read_holding_response', delayed_decode)
    n._transport = transport
    n._poll()
    receipt = transport.last_reply_received_monotonic_s
    assert n._accepted == 1
    assert 0 <= round(receipt*1e9) + t.offset_ns - stamp(n.imu_pub.messages[-1]) <= 2
    assert n._last_received_at == receipt
    assert t.mono - receipt == pytest.approx(.007)
    assert transport.last_transaction['deadline_monotonic_s'] == pytest.approx(10.05)
    assert transport.last_transaction['classification'] == 'complete_on_time'
    transport.close()


@pytest.mark.parametrize('delta_ns', [-2_000_000, 2_000_000])
def test_real_rosclock_independent_override_change_disagrees_with_correlation(delta_ns):
    """Real ROSClock API changes only ROS; no physical host clock change.

    Active simulation is rejected by the raw driver (tested above). Here its
    override API supplies an independently stepped clock to the actual private
    correlation method, in addition to the end-to-end synthetic poll cases.
    """
    from rclpy.clock import ROSClock
    from rclpy.time_source import TimeSource
    from robot_state_estimation._hwt601_clock import ReceiptClockCorrelation
    from robot_state_estimation.hwt601_protocol import Hwt601ProtocolError
    clock, source = ROSClock(), TimeSource()
    source.attach_clock(clock)
    source.ros_time_is_active = True
    correlation = ReceiptClockCorrelation()
    clock.set_ros_time_override(Time(nanoseconds=1010_000_000_000))
    correlation.project(10., 10., clock.now().nanoseconds, 10.0002)
    clock.set_ros_time_override(Time(nanoseconds=1010_010_000_000 + delta_ns))
    with pytest.raises(Hwt601ProtocolError, match='Zeitbasis'):
        correlation.project(10.01, 10.01, clock.now().nanoseconds, 10.0102)
