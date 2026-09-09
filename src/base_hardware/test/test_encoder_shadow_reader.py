#!/usr/bin/env python3
"""ROS- und hardwarefreie Tests des strikt lesenden Encoder-Shadow-Pfads."""

import math
from pathlib import Path
import sys

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from base_hardware.encoder_odometry import EncoderOdometry  # noqa: E402
from base_hardware.encoder_shadow_reader import (  # noqa: E402
    BASE_ALIAS,
    HWT601_ALIAS,
    EncoderPair,
    EncoderPairReader,
    EncoderShadowCore,
    EncoderShadowError,
    ReadOnlyModbusTransport,
    shadow_status_payload,
    validate_base_alias,
)
from base_hardware.encoder_odometry import MotorFeedback  # noqa: E402


class FakeResponse:
    def __init__(self, registers=(), *, error=False):
        self.registers = list(registers)
        self.error = error

    def isError(self):
        return self.error


class FakeSocket:
    def __init__(self, *, exclusive=True, is_open=True):
        self.exclusive = exclusive
        self.is_open = is_open


class FakeClient:
    def __init__(
        self,
        *,
        responses=None,
        accepted_keyword='device_id',
        connect_result=True,
        exclusive=True,
        **kwargs,
    ):
        self.kwargs = kwargs
        self.responses = responses or {}
        self.accepted_keyword = accepted_keyword
        self.connect_result = connect_result
        self.socket = None
        self.socket_exclusive = exclusive
        self.closed = False
        self.calls = []

    def connect(self):
        if self.connect_result:
            self.socket = FakeSocket(exclusive=self.socket_exclusive)
        return self.connect_result

    def close(self):
        self.closed = True
        self.socket = None

    def read_holding_registers(self, address, count=1, **kwargs):
        keyword = next(iter(kwargs), None)
        if keyword != self.accepted_keyword:
            raise TypeError(keyword)
        motor_id = kwargs[keyword]
        self.calls.append((motor_id, address, count, keyword))
        response = self.responses.get((motor_id, address, count))
        if isinstance(response, Exception):
            raise response
        return response if response is not None else FakeResponse([0] * count)


class FakeFactory:
    def __init__(self, **client_kwargs):
        self.client_kwargs = client_kwargs
        self.instances = []
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        client = FakeClient(**self.client_kwargs, **kwargs)
        self.instances.append(client)
        return client


def fake_paths(*, conflict=False):
    targets = {
        BASE_ALIAS: '/dev/ttyUSB0',
        HWT601_ALIAS: '/dev/ttyUSB0' if conflict else '/dev/ttyUSB1',
        '/dev/ttyUSB0': '/dev/ttyUSB0',
        '/dev/ttyUSB1': '/dev/ttyUSB1',
    }
    return (
        lambda path: path in targets,
        lambda path: targets.get(path, path),
    )


def transport(*, factory=None, conflict=False):
    exists, realpath = fake_paths(conflict=conflict)
    return ReadOnlyModbusTransport(
        port=BASE_ALIAS,
        baudrate=115200,
        timeout_s=0.1,
        retries=0,
        client_factory=factory or FakeFactory(),
        exists=exists,
        realpath=realpath,
        identity_validator=lambda _port: None,
    )


def tracker(max_gap=0.10):
    return EncoderOdometry(
        wheel_radius_m=0.0624,
        wheel_separation_m=0.3845,
        gear_ratio=10.0,
        counts_per_motor_revolution=1000.0,
        invert_left=False,
        invert_right=True,
        max_motor_rpm=700.0,
        max_delta_factor=1.5,
        max_recovery_gap_s=max_gap,
    )


def pair(left, right, left_rpm=0.0, right_rpm=0.0):
    return EncoderPair(
        left=MotorFeedback(left, left_rpm),
        right=MotorFeedback(right, right_rpm),
    )


class TestAliasAndTransport:

    def test_fixed_alias_is_required_and_separate(self):
        exists, realpath = fake_paths()
        assert validate_base_alias(
            BASE_ALIAS, exists=exists, realpath=realpath) == '/dev/ttyUSB0'
        with pytest.raises(EncoderShadowError, match='feste Basisalias'):
            validate_base_alias(
                '/dev/ttyUSB0', exists=exists, realpath=realpath)

        exists, realpath = fake_paths(conflict=True)
        with pytest.raises(EncoderShadowError, match='dasselbe Geraet'):
            validate_base_alias(
                BASE_ALIAS, exists=exists, realpath=realpath)

    def test_missing_alias_is_rejected_before_client_creation(self):
        factory = FakeFactory()
        reader = ReadOnlyModbusTransport(
            port=BASE_ALIAS,
            baudrate=115200,
            timeout_s=0.1,
            retries=0,
            client_factory=factory,
            exists=lambda _path: False,
            realpath=lambda path: path,
        )
        with pytest.raises(EncoderShadowError, match='Basisalias fehlt'):
            reader.connect()
        assert factory.instances == []

    def test_missing_hwt_alias_is_rejected_before_client_creation(self):
        factory = FakeFactory()
        existing = {BASE_ALIAS, '/dev/ttyUSB0'}
        reader = ReadOnlyModbusTransport(
            port=BASE_ALIAS,
            baudrate=115200,
            timeout_s=0.1,
            retries=0,
            client_factory=factory,
            exists=lambda path: path in existing,
            realpath=lambda path: (
                '/dev/ttyUSB0' if path == BASE_ALIAS else path),
            identity_validator=lambda _port: None,
        )
        with pytest.raises(EncoderShadowError, match='HWT601-Alias fehlt'):
            reader.connect()
        assert factory.instances == []

    @pytest.mark.parametrize('keyword', ['device_id', 'slave', 'unit'])
    def test_fc03_adapter_supports_pinned_and_legacy_keywords(self, keyword):
        factory = FakeFactory(accepted_keyword=keyword)
        reader = transport(factory=factory)
        assert reader.connect() == '/dev/ttyUSB0'
        assert reader.successful_connections == 1
        assert reader.reconnects == 0
        assert reader.read_holding_registers(2, 0x000A, 3) == (0, 0, 0)
        assert factory.instances[0].calls[-1] == (2, 0x000A, 3, keyword)
        assert factory.calls[0] == {
            'port': BASE_ALIAS,
            'baudrate': 115200,
            'bytesize': 8,
            'parity': 'N',
            'stopbits': 1,
            'timeout': 0.1,
            'retries': 0,
        }

    def test_nonexclusive_serial_connection_is_closed_and_rejected(self):
        factory = FakeFactory(exclusive=False)
        reader = transport(factory=factory)
        with pytest.raises(EncoderShadowError, match='exklusiv'):
            reader.connect()
        assert factory.instances[0].closed
        assert not reader.connected
        assert reader.successful_connections == 0

    def test_alias_is_rechecked_after_open_and_change_closes_client(self):
        calls = {'base': 0}

        def exists(path):
            return path in {
                BASE_ALIAS, HWT601_ALIAS, '/dev/ttyUSB0', '/dev/ttyUSB1',
                '/dev/ttyUSB2'}

        def realpath(path):
            if path == BASE_ALIAS:
                calls['base'] += 1
                return '/dev/ttyUSB0' if calls['base'] == 1 else '/dev/ttyUSB2'
            return '/dev/ttyUSB1' if path == HWT601_ALIAS else path

        factory = FakeFactory()
        reader = ReadOnlyModbusTransport(
            port=BASE_ALIAS,
            baudrate=115200,
            timeout_s=0.1,
            retries=0,
            client_factory=factory,
            exists=exists,
            realpath=realpath,
            identity_validator=lambda _port: None,
        )
        with pytest.raises(EncoderShadowError, match='wechselte'):
            reader.connect()
        assert factory.instances[0].closed
        assert reader.successful_connections == 0

    def test_only_four_whitelisted_fc03_ranges_are_readable(self):
        factory = FakeFactory()
        reader = transport(factory=factory)
        reader.connect()
        allowed = ((0x000A, 3), (0x0011, 1), (0x0019, 1), (0x0101, 1))
        for address, count in allowed:
            words = reader.read_holding_registers(1, address, count)
            assert len(words) == count
        before = len(factory.instances[0].calls)
        for address, count in ((0x001D, 1), (0x0027, 1), (0x000A, 2)):
            with pytest.raises(EncoderShadowError, match='nicht freigegeben'):
                reader.read_holding_registers(1, address, count)
        assert len(factory.instances[0].calls) == before

    @pytest.mark.parametrize('response,match', [
        (FakeResponse([1, 2]), 'Unvollstaendige'),
        (FakeResponse([1, 2, 3], error=True), 'Fehlerhafte'),
        (FakeResponse([1, True, 3]), 'Ungueltiges'),
        (FakeResponse([1, -1, 3]), 'Ungueltiges'),
        (FakeResponse([1, 0x10000, 3]), 'Ungueltiges'),
        (RuntimeError('bus fault'), 'FC03-Leseexception'),
    ])
    def test_malformed_reads_fail_closed(self, response, match):
        responses = {(1, 0x000A, 3): response}
        factory = FakeFactory(responses=responses)
        reader = transport(factory=factory)
        reader.connect()
        with pytest.raises(EncoderShadowError, match=match):
            reader.read_holding_registers(1, 0x000A, 3)

    def test_broken_response_api_is_normalized_to_shadow_error(self):
        class BrokenResponse:
            def isError(self):
                raise AttributeError('broken response')

        factory = FakeFactory(
            responses={(1, 0x000A, 3): BrokenResponse()})
        reader = transport(factory=factory)
        reader.connect()

        with pytest.raises(EncoderShadowError, match='Antwortstruktur'):
            reader.read_holding_registers(1, 0x000A, 3)

    def test_connection_counters_distinguish_first_open_and_reconnect(self):
        factory = FakeFactory()
        reader = transport(factory=factory)
        reader.connect()
        reader.close()
        reader.connect()
        assert reader.successful_connections == 2
        assert reader.reconnects == 1

    def test_lost_socket_cannot_trigger_pymodbus_implicit_reconnect(self):
        factory = FakeFactory()
        reader = transport(factory=factory)
        reader.connect()
        client = factory.instances[0]
        client.socket.is_open = False

        assert not reader.connected
        with pytest.raises(EncoderShadowError, match='nicht mehr sicher offen'):
            reader.connect()
        with pytest.raises(EncoderShadowError, match='nicht verbunden'):
            reader.read_holding_registers(1, 0x000A, 3)
        assert client.calls == []
        assert len(factory.instances) == 1

    def test_sysfs_identity_requires_exact_commissioned_ftdi(
        self, tmp_path,
    ):
        from base_hardware.encoder_shadow_reader import (
            validate_base_usb_identity,
        )

        usb_device = tmp_path / 'devices' / '1-1'
        interface = usb_device / '1-1:1.0'
        interface.mkdir(parents=True)
        (usb_device / 'idVendor').write_text('0403\n', encoding='ascii')
        (usb_device / 'idProduct').write_text('6001\n', encoding='ascii')
        (usb_device / 'serial').write_text('BG03R8RZ\n', encoding='ascii')
        tty = tmp_path / 'class' / 'tty' / 'ttyUSB0'
        tty.mkdir(parents=True)
        (tty / 'device').symlink_to(interface, target_is_directory=True)

        validate_base_usb_identity(
            '/dev/ttyUSB0', sysfs_tty_root=str(tmp_path / 'class' / 'tty'))
        (usb_device / 'serial').write_text('WRONG\n', encoding='ascii')
        with pytest.raises(EncoderShadowError, match='abgenommene FTDI'):
            validate_base_usb_identity(
                '/dev/ttyUSB0',
                sysfs_tty_root=str(tmp_path / 'class' / 'tty'),
            )


class StubTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def read_holding_registers(self, motor_id, address, count):
        self.calls.append((motor_id, address, count))
        value = self.responses[(motor_id, address, count)]
        if isinstance(value, Exception):
            raise value
        return tuple(value)


def configured_pair_reader(*, word_order_left=0, word_order_right=0):
    responses = {}
    for motor_id, order in ((1, word_order_left), (2, word_order_right)):
        responses[(motor_id, 0x0011, 1)] = (1000,)
        responses[(motor_id, 0x0019, 1)] = (order,)
        responses[(motor_id, 0x0101, 1)] = (4000,)
    transport_stub = StubTransport(responses)
    reader = EncoderPairReader(
        transport_stub,
        left_motor_id=1,
        right_motor_id=2,
        position_register=0x000A,
        segment_register=0x0011,
        word_order_register=0x0019,
        resolution_register=0x0101,
        rpm_scale=1.0,
    )
    return reader, transport_stub


class TestPairReader:

    def test_configuration_and_pair_use_only_measured_read_addresses(self):
        reader, transport_stub = configured_pair_reader()
        left, right = reader.read_and_validate_configuration(
            expected_segment=1000,
            expected_word_order=0,
            expected_resolution=4000,
        )
        assert left == right
        transport_stub.responses[(1, 0x000A, 3)] = (0x0001, 0x0002, 10)
        transport_stub.responses[(2, 0x000A, 3)] = (0xFFFF, 0xFFFE, 0xFFF6)
        sample = reader.read_complete_pair()
        assert sample.left.position_u32 == 0x00010002
        assert sample.left.speed_rpm == 10.0
        assert sample.right.position_u32 == 0xFFFFFFFE
        assert sample.right.speed_rpm == -10.0
        assert {address for _, address, _ in transport_stub.calls} == {
            0x000A, 0x0011, 0x0019, 0x0101}

    def test_left_right_word_order_disagreement_is_rejected(self):
        reader, _transport = configured_pair_reader(word_order_right=1)
        with pytest.raises(EncoderShadowError, match='links/rechts'):
            reader.read_and_validate_configuration(
                expected_segment=1000,
                expected_word_order=0,
                expected_resolution=4000,
            )

    def test_word_order_must_match_read_only_h1_measurement(self):
        reader, _transport = configured_pair_reader(
            word_order_left=1, word_order_right=1)
        with pytest.raises(EncoderShadowError, match='H1-Abnahme'):
            reader.read_and_validate_configuration(
                expected_segment=1000,
                expected_word_order=0,
                expected_resolution=4000,
            )

    def test_partial_pair_raises_and_never_returns_one_motor(self):
        reader, transport_stub = configured_pair_reader()
        reader.read_and_validate_configuration(
            expected_segment=1000,
            expected_word_order=0,
            expected_resolution=4000,
        )
        transport_stub.responses[(1, 0x000A, 3)] = (0, 10, 0)
        transport_stub.responses[(2, 0x000A, 3)] = EncoderShadowError(
            'timeout')
        with pytest.raises(EncoderShadowError, match='timeout'):
            reader.read_complete_pair()


class TestShadowCore:

    def test_baseline_then_complete_pair_publishes_real_encoder_odometry(self):
        core = EncoderShadowCore(tracker(), max_pair_read_duration_s=0.05)
        baseline = core.accept_pair(
            pair(100, 200), sample_time_s=1.0, pair_read_duration_s=0.01)
        result = core.accept_pair(
            pair(110, 190), sample_time_s=1.05, pair_read_duration_s=0.012)
        assert not baseline.publish
        assert baseline.reason == 'baseline_initialisiert'
        assert result.publish
        assert result.update.left_delta_counts == 10
        assert result.update.right_delta_counts == 10
        expected = 10 * 2.0 * math.pi * 0.0624 / (1000.0 * 10.0)
        assert core.tracker.x_m == pytest.approx(expected)
        assert core.tracker.y_m == pytest.approx(0.0)
        assert core.tracker.yaw_rad == pytest.approx(0.0)
        assert core.maximum_pair_duration_s == pytest.approx(0.012)

    @pytest.mark.parametrize(
        'second_time,duration,expected_reason', [
            (1.0, 0.01, 'nicht_monotoner_zeitstempel'),
            (1.11, 0.01, 'luecke_zu_lang_rebaseline'),
            (1.05, 0.051, 'encoderpaar_zeitfenster_ueberschritten'),
        ])
    def test_time_and_gap_faults_latch_until_restart(
        self, second_time, duration, expected_reason,
    ):
        core = EncoderShadowCore(tracker(), max_pair_read_duration_s=0.05)
        core.accept_pair(
            pair(100, 200), sample_time_s=1.0, pair_read_duration_s=0.01)
        failed = core.accept_pair(
            pair(110, 190),
            sample_time_s=second_time,
            pair_read_duration_s=duration,
        )
        assert not failed.publish
        assert core.fault_reason == expected_reason
        later = core.accept_pair(
            pair(120, 180), sample_time_s=1.06, pair_read_duration_s=0.01)
        assert not later.publish
        assert later.reason == expected_reason

    def test_incomplete_pair_latches_without_changing_baseline(self):
        core = EncoderShadowCore(tracker(), max_pair_read_duration_s=0.05)
        core.accept_pair(
            pair(100, 200), sample_time_s=1.0, pair_read_duration_s=0.01)
        failed = core.accept_pair(
            None, sample_time_s=1.05, pair_read_duration_s=0.01)
        assert not failed.publish
        assert core.fault_reason == 'encoderpaar_unvollstaendig'
        assert core.tracker.accepted_update_count == 0

    def test_status_contract_is_explicitly_nonsynthetic_and_nonactuating(self):
        core = EncoderShadowCore(tracker(), max_pair_read_duration_s=0.05)
        core.accept_pair(
            pair(100, 200), sample_time_s=1.0, pair_read_duration_s=0.01)
        status = shadow_status_payload(
            core,
            connected=True,
            configuration_valid=True,
            port=BASE_ALIAS,
            resolved_port='/dev/ttyUSB0',
            left_motor_id=1,
            right_motor_id=2,
            last_feedback_age_s=0.001,
            max_feedback_age_s=0.10,
            successful_connections=1,
            reconnects=0,
        )
        assert status['ready'] is True
        assert status['source'] == 'ess23_absolute_fc03'
        assert status['synthetic'] is False
        assert status['command_derived'] is False
        assert status['sensor_write_commands'] is False
        assert status['actuator_output'] is False
        assert status['publishes_tf'] is False
        assert status['rejected'] == 0
        assert status['reconnects'] == 0
        assert status['rebases'] == 0
        assert status['fault_latched'] is False
        assert status['fault_reason'] is None
        assert status['last_pair_duration_s'] == pytest.approx(0.01)
        assert status['maximum_pair_duration_s'] == pytest.approx(0.01)
