import importlib.util
import math
from pathlib import Path
import sys

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / 'hwt601_encoder_shadow_stillstand.py'
)
SPEC = importlib.util.spec_from_file_location(
    'hwt601_encoder_shadow_stillstand', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _wrapped(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def _motion_samples(target_deg, *, start_yaw_deg=170.0):
    """Asynchronous 100-Hz IMU and 20-Hz encoder with real edge brackets."""
    rate = math.copysign(math.radians(20.0), target_deg)
    duration = abs(math.radians(target_deg) / rate)
    encoder_start = 10.025
    imu_start = 10.0
    imu_end = encoder_start + duration + 0.025
    imu_count = int(round((imu_end - imu_start) * 100.0))
    imu = [
        MODULE.ImuYawSample(imu_start + index / 100.0, rate)
        for index in range(imu_count + 1)
    ]
    encoder_count = int(round(duration * 20.0))
    initial_yaw = math.radians(start_yaw_deg)
    encoder = []
    for index in range(encoder_count + 1):
        stamp = encoder_start + index / 20.0
        yaw = _wrapped(initial_yaw + rate * (stamp - encoder_start))
        encoder.append(MODULE.WheelPoseSample(stamp, 0.0, 0.0, yaw))
    return imu, encoder


@pytest.mark.parametrize('target_deg', (45.0, -45.0, 180.0, -180.0))
def test_direct_comparison_handles_async_rates_wrap_and_signed_targets(target_deg):
    imu, encoder = _motion_samples(target_deg)

    result = MODULE.compare_angles(imu, encoder)

    assert math.degrees(result.hwt_angle_rad) == pytest.approx(
        target_deg, abs=1.0e-9)
    assert math.degrees(result.encoder_angle_rad) == pytest.approx(
        target_deg, abs=1.0e-9)
    assert math.degrees(result.difference_rad) == pytest.approx(0.0, abs=1.0e-9)
    assert result.imu_rate_hz == pytest.approx(100.0, rel=2.0e-3)
    assert result.encoder_rate_hz == pytest.approx(20.0, abs=1.0e-8)


def test_encoder_unwrap_crosses_positive_pi_without_losing_rotation():
    angles = (179.0, -179.0, -170.0, -160.0)
    samples = [
        MODULE.WheelPoseSample(
            1.0 + 0.05 * index, 0.0, 0.0, math.radians(angle))
        for index, angle in enumerate(angles)
    ]

    unwrapped = MODULE.unwrap_encoder_yaw(samples)

    assert math.degrees(unwrapped[-1]) == pytest.approx(21.0, abs=1.0e-10)
    assert all(after > before for before, after in zip(unwrapped, unwrapped[1:]))


@pytest.mark.parametrize('missing_side', ('before', 'after'))
def test_direct_comparison_refuses_missing_real_boundary_bracket(missing_side):
    imu, encoder = _motion_samples(45.0)
    if missing_side == 'before':
        imu = [sample for sample in imu if sample.stamp_s >= encoder[0].stamp_s]
    else:
        imu = [sample for sample in imu if sample.stamp_s <= encoder[-1].stamp_s]

    with pytest.raises(
            MODULE.AnalysisError,
            match='imu_randprobe_ohne_echte_klammer'):
        MODULE.compare_angles(imu, encoder)


def test_exact_first_and_last_imu_samples_are_valid_real_boundaries():
    rate = math.radians(10.0)
    imu = [
        MODULE.ImuYawSample(1.0 + index * 0.01, rate)
        for index in range(101)
    ]
    encoder = [
        MODULE.WheelPoseSample(
            1.0 + index * 0.05,
            0.0,
            0.0,
            _wrapped(rate * index * 0.05),
        )
        for index in range(21)
    ]

    result = MODULE.compare_angles(imu, encoder)

    assert math.degrees(result.hwt_angle_rad) == pytest.approx(10.0)
    assert math.degrees(result.encoder_angle_rad) == pytest.approx(10.0)


def _hwt_status(*, calibrated, ready, blocked):
    return {
        'ready': ready,
        'shadow_only': True,
        'fusion_ready': False,
        'actuator_output': False,
        'publishes_tf': False,
        'operator_stationary_confirmed': True,
        'stationary_source': 'operator_declared_startup_only',
        'bias_frozen_after_startup': True,
        'scale_validation': 'external_180_observer_confirmed',
        'sensor_to_base_axes': 'x_b=y_s,y_b=-x_s,z_b=z_s',
        'input_topic': MODULE.HWT_RAW_IMU_TOPIC,
        'input_frame': 'hwt601_link',
        'output_topic': MODULE.IMU_TOPIC,
        'output_frame': MODULE.IMU_FRAME,
        'output_qos': 'reliable_keep_last_200',
        'latched_fault': None,
        'rejected': 0,
        'blocked': blocked,
        'raw_received': blocked,
        'published': 0 if not calibrated else 10,
        'bias': {
            'calibrated': calibrated,
            'stable': calibrated,
            'adaptation_samples': 0,
            'samples': 0 if not calibrated else 1000,
        },
    }


def _stationary_bias_guard():
    guard = MODULE.BiasPhaseGuard()
    guard.observe_hwt_status(
        _hwt_status(calibrated=False, ready=False, blocked=20))
    for index in range(501):
        guard.observe_wheel(MODULE.WheelPoseSample(
            1.0 + index * 0.05, 0.0, 0.0, 0.0))
    guard.observe_hwt_status(
        _hwt_status(calibrated=True, ready=True, blocked=2500))
    return guard


def test_bias_phase_requires_and_accepts_full_real_stationary_history():
    guard = _stationary_bias_guard()

    assert guard.completed
    assert guard.fault_reason is None
    assert guard.observed_duration_s == pytest.approx(25.0)


@pytest.mark.parametrize(
    'sample',
    (
        # A non-zero first pose is movement since the reader's FC03 baseline;
        # the observer must not redefine it as a comparison origin.
        MODULE.WheelPoseSample(1.0, 0.002, 0.0, 0.0),
        MODULE.WheelPoseSample(1.0, 0.0, 0.0, math.radians(0.2)),
        MODULE.WheelPoseSample(1.0, 0.0, 0.0, 0.0, 0.006, 0.0),
        MODULE.WheelPoseSample(1.0, 0.0, 0.0, 0.0, 0.0, 0.006),
    ),
)
def test_bias_phase_rejects_motion_including_moved_first_absolute_pose(sample):
    guard = MODULE.BiasPhaseGuard()
    guard.observe_hwt_status(
        _hwt_status(calibrated=False, ready=False, blocked=20))

    guard.observe_wheel(sample)

    assert not guard.completed
    assert guard.fault_reason == 'bewegung_waehrend_hwt_biasphase'


def test_bias_phase_rejects_late_observer_even_when_current_pose_is_zero():
    guard = MODULE.BiasPhaseGuard()
    guard.observe_wheel(MODULE.WheelPoseSample(25.0, 0.0, 0.0, 0.0))

    guard.observe_hwt_status(
        _hwt_status(calibrated=True, ready=True, blocked=2500))

    assert not guard.completed
    assert guard.fault_reason == 'hwt_biasphase_nicht_vollstaendig_beobachtet'


def _encoder_status():
    return {
        'ready': True,
        'source': 'ess23_absolute_fc03',
        'synthetic': False,
        'command_derived': False,
        'shadow_only': True,
        'fusion_ready': False,
        'read_only': True,
        'modbus_function_code': 3,
        'sensor_write_commands': False,
        'actuator_output': False,
        'cmd_vel_subscription': False,
        'publishes_tf': False,
        'port': '/dev/ttyUSB_BASE',
        'left_motor_id': 1,
        'right_motor_id': 2,
        'topic': MODULE.WHEEL_TOPIC,
        'output_qos': 'reliable_keep_last_10',
        'odom_frame_id': MODULE.ODOM_FRAME,
        'base_frame_id': MODULE.BASE_FRAME,
        'wheel_radius_m': 0.0624,
        'wheel_separation_m': 0.3845,
        'gear_ratio': 10.0,
        'counts_per_motor_revolution': 1000.0,
        'invert_left': False,
        'invert_right': True,
        'position_register': 0x000A,
        'segment_register': 0x0011,
        'word_order_register': 0x0019,
        'resolution_register': 0x0101,
        'expected_segment': 1000,
        'expected_word_order': 0,
        'expected_resolution': 4000,
        'rpm_scale': 1.0,
        'poll_rate_hz': 20.0,
        'max_pair_read_duration_s': MODULE.MAX_PAIR_DURATION_S,
        'max_sample_gap_s': MODULE.ENCODER_SOURCE_MAX_SAMPLE_GAP_S,
        'connected': True,
        'configuration_valid': True,
        'successful_connections': 1,
        'rejected': 0,
        'reconnects': 0,
        'rebases': 0,
        'fault_latched': False,
        'fault_reason': None,
        'maximum_pair_duration_s': 0.012,
        'complete_pair_count': 20,
        'published_count': 19,
        'baseline_count': 1,
    }


def test_encoder_status_proves_real_fc03_source_and_pair_span():
    status = _encoder_status()
    assert MODULE.validate_encoder_status(status, require_ready=True) is None

    for field, value in (
        ('source', 'dry_run'),
        ('synthetic', True),
        ('command_derived', True),
        ('rejected', 1),
        ('reconnects', 1),
        ('successful_connections', 2),
        ('rebases', 1),
        ('fault_latched', True),
        ('maximum_pair_duration_s', 0.051),
    ):
        changed = _encoder_status()
        changed[field] = value
        assert MODULE.validate_encoder_status(
            changed, require_ready=True) is not None


def _raw_hwt_status():
    return {
        'ready': True,
        'raw_data_ready': True,
        'fusion_ready': False,
        'sensor_write_commands': False,
        'actuator_output': False,
        'port': '/dev/ttyUSB_HWT601',
        'baud': 115200,
        'device_address': 80,
        'frame_id': 'hwt601_link',
        'topic': MODULE.HWT_RAW_IMU_TOPIC,
        'host_receive_timestamp': True,
        'scale_validation_pending': True,
        'rejected': 0,
        'successful_connections': 1,
        'reconnects': 0,
        'consecutive_errors': 0,
        'accepted': 100,
    }


def test_raw_hwt_status_requires_one_clean_connection_and_no_reconnect():
    assert MODULE.validate_raw_hwt_status(
        _raw_hwt_status(), require_ready=True) is None

    for field, value in (
        ('ready', False),
        ('raw_data_ready', False),
        ('sensor_write_commands', True),
        ('actuator_output', True),
        ('rejected', 1),
        ('successful_connections', 2),
        ('reconnects', 1),
        ('consecutive_errors', 1),
    ):
        changed = _raw_hwt_status()
        changed[field] = value
        assert MODULE.validate_raw_hwt_status(
            changed, require_ready=True) is not None


def _passing_summary():
    return {
        'complete': True,
        'requested_duration_s': 600.0,
        'faults': [],
        'bias_phase': {
            'complete': True,
            'movement_detected': False,
            'observed_duration_s': 25.0,
        },
        'statuses': {
            'hwt_valid': True,
            'hwt_raw_valid': True,
            'encoder_valid': True,
            'hwt': _hwt_status(
                calibrated=True, ready=True, blocked=2500),
            'hwt_raw': _raw_hwt_status(),
            'encoder': _encoder_status(),
        },
        'graph': {
            'valid': True,
            'first_check_monotonic_s': 99.5,
        },
        'runtime': {
            'measurement_start_received_monotonic_s': 100.0,
            'monotonic_duration_s': 600.0,
            'ros_stamp_duration_s': 600.0,
            'duration_clock_skew_s': 0.0,
        },
        'status_continuity': {
            'valid': True,
            'first_received_s': {
                'hwt': 90.0,
                'hwt_raw': 90.1,
                'encoder': 90.2,
            },
        },
        'post_window_status': {
            'complete': True,
            'fault_reason': None,
            'measurement_end_received_monotonic_s': 700.0,
            'deadline_monotonic_s': 702.0,
            'timeout_s': 2.0,
            'status_received_monotonic_s': {
                'hwt': 700.5,
                'hwt_raw': 700.6,
                'encoder': 700.7,
            },
        },
        'comparison': {
            'duration_s': 600.0,
            'imu_rate_hz': 100.0,
            'encoder_rate_hz': 20.0,
            'maximum_imu_gap_s': 0.02,
            'maximum_encoder_gap_s': 0.06,
            'hwt_angle_deg': 0.1,
            'encoder_angle_deg': 0.05,
            'difference_deg': 0.05,
            'peak_absolute_hwt_angle_deg': 0.2,
            'peak_absolute_encoder_angle_deg': 0.1,
            'peak_absolute_difference_deg': 0.1,
            'peak_translation_from_window_start_m': 0.0001,
            'peak_translation_from_encoder_baseline_m': 0.0001,
            'peak_absolute_linear_velocity_mps': 0.0001,
            'peak_absolute_encoder_angular_velocity_radps': 0.0001,
        },
    }


def test_600_second_acceptance_checks_rates_gaps_final_and_peak_angles():
    assert MODULE._passed(_passing_summary())

    for path, value in (
        (('requested_duration_s',), 599.0),
        (('comparison', 'imu_rate_hz'), 79.9),
        (('comparison', 'encoder_rate_hz'), 9.9),
        (('comparison', 'maximum_imu_gap_s'), 0.101),
        (('comparison', 'maximum_encoder_gap_s'), 0.101),
        (('comparison', 'hwt_angle_deg'), 1.0),
        (('comparison', 'encoder_angle_deg'), -1.0),
        (('comparison', 'difference_deg'), 1.0),
        (('comparison', 'peak_absolute_hwt_angle_deg'), 1.0),
        (('comparison', 'peak_absolute_encoder_angle_deg'), 1.0),
        (('comparison', 'peak_absolute_difference_deg'), 1.0),
        (('comparison', 'peak_translation_from_window_start_m'), 0.001),
        (('comparison', 'peak_translation_from_encoder_baseline_m'), 0.001),
        (('comparison', 'peak_absolute_linear_velocity_mps'), 0.005),
        (('comparison', 'peak_absolute_encoder_angular_velocity_radps'), 0.005),
        (('runtime', 'monotonic_duration_s'), 599.0),
        (('runtime', 'duration_clock_skew_s'), 0.501),
        (('status_continuity', 'first_received_s', 'encoder'), 100.1),
        (('graph', 'first_check_monotonic_s'), 100.1),
        (('status_continuity', 'valid'), False),
        (('post_window_status', 'complete'), False),
        (('post_window_status', 'fault_reason'), 'timeout'),
        (('post_window_status', 'timeout_s'), 3.0),
        (('post_window_status', 'deadline_monotonic_s'), 702.1),
        (('post_window_status', 'status_received_monotonic_s', 'encoder'), 700.0),
        (('post_window_status', 'status_received_monotonic_s', 'encoder'), 702.1),
        (('bias_phase', 'movement_detected'), True),
        (('statuses', 'hwt_raw_valid'), False),
        (('statuses', 'encoder_valid'), False),
    ):
        changed = _passing_summary()
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert not MODULE._passed(changed)


def test_post_window_status_guard_requires_every_status_strictly_after_end():
    guard = MODULE.PostWindowStatusGuard(timeout_s=2.0)
    guard.start(100.0)

    assert not guard.update(100.5, {
        'hwt': 100.1,
        'hwt_raw': 100.2,
        'encoder': 100.0,
    })
    assert guard.fault_reason is None
    assert not guard.completed

    assert guard.update(100.6, {
        'hwt': 100.1,
        'hwt_raw': 100.2,
        'encoder': 100.3,
    })
    assert guard.completed
    assert guard.fault_reason is None
    assert guard.status_received_s == {
        'hwt': 100.1,
        'hwt_raw': 100.2,
        'encoder': 100.3,
    }


def test_post_window_status_guard_times_out_fail_closed():
    guard = MODULE.PostWindowStatusGuard(timeout_s=2.0)
    guard.start(100.0)

    assert not guard.update(101.99, {
        'hwt': 100.1,
        'hwt_raw': None,
        'encoder': 100.2,
    })
    assert guard.fault_reason is None
    assert not guard.update(102.0, {
        'hwt': 100.1,
        'hwt_raw': None,
        'encoder': 100.2,
    })
    assert guard.fault_reason == 'abschlussstatus_nach_messende_timeout'
    assert not guard.completed


def test_post_window_status_guard_rejects_status_after_deadline():
    guard = MODULE.PostWindowStatusGuard(timeout_s=2.0)
    guard.start(100.0)

    assert not guard.update(102.1, {
        'hwt': 100.1,
        'hwt_raw': 100.2,
        'encoder': 102.1,
    })
    assert guard.fault_reason == 'abschlussstatus_nach_messende_timeout'
    assert not guard.completed


def test_observer_source_has_no_output_or_hardware_control_path():
    source = SCRIPT.read_text(encoding='utf-8')

    assert 'create_publisher' not in source
    assert 'TransformBroadcaster' not in source
    assert 'subprocess' not in source
    assert 'serial.Serial' not in source
    assert 'ModbusSerialClient' not in source
    assert 'create_subscription(\n                Twist' not in source
    assert MODULE.IMU_TOPIC == '/shadow/hwt601/imu/yaw_rate'
    assert MODULE.WHEEL_TOPIC == '/shadow/hwt601/wheel_odom_raw'
    assert MODULE.HWT_RAW_STATUS_TOPIC == '/shadow/hwt601/raw_status_json'
    assert MODULE.SENSOR_BUFFER_DEPTH == 200
    assert 'depth=SENSOR_BUFFER_DEPTH' in source
    assert 'reliability=ReliabilityPolicy.RELIABLE' in source
    assert 'self.imu_stamps.append(stamp_s)' in source
    assert 'return _bracketing_indices(self.imu_stamps, stamp_s)' in source
    assert 'index = len(self.wheel_samples) - 1' in source
    assert 'ever-growing history on every' in source
    assert "'gap_fault_detail': node.gap_fault_detail" in source
    assert "'stamp_gap_s': gap" in source
    assert "'receive_gap_s': receive_gap" in source


def test_straight_translation_cannot_pass_as_stationary_yaw_agreement():
    imu = [
        MODULE.ImuYawSample(1.0 + index * 0.01, 0.0)
        for index in range(101)
    ]
    encoder = [
        MODULE.WheelPoseSample(
            1.0 + index * 0.05,
            index * 0.001,
            0.0,
            0.0,
            linear_velocity_mps=0.02,
        )
        for index in range(21)
    ]

    result = MODULE.compare_angles(imu, encoder)

    assert result.hwt_angle_rad == pytest.approx(0.0)
    assert result.encoder_angle_rad == pytest.approx(0.0)
    assert result.peak_translation_from_window_start_m == pytest.approx(0.02)
    assert result.peak_translation_from_encoder_baseline_m == pytest.approx(0.02)
    assert result.peak_absolute_linear_velocity_mps == pytest.approx(0.02)


def test_status_continuity_latches_gaps_and_counter_resets():
    guard = MODULE.StatusContinuityGuard()
    guard.observe('encoder', 10.0, {'published': 10})
    guard.observe('encoder', 10.5, {'published': 20})
    assert guard.fault_reason is None
    assert guard.first_received_s['encoder'] == pytest.approx(10.0)
    assert guard.maximum_gap_s['encoder'] == pytest.approx(0.5)

    guard.observe('encoder', 11.0, {'published': 19})
    assert guard.fault_reason == 'encoder_statuszaehler_published_zurueckgesetzt'

    gap_guard = MODULE.StatusContinuityGuard()
    gap_guard.observe('hwt', 1.0, {'published': 1})
    gap_guard.observe('hwt', 2.01, {'published': 2})
    assert gap_guard.fault_reason == 'hwt_status_datenluecke'


def test_pre_window_coverage_requires_all_statuses_and_graph_before_samples():
    first_status = {
        'hwt': 9.0,
        'hwt_raw': 9.1,
        'encoder': 9.2,
    }
    assert MODULE.validate_pre_window_coverage(
        10.0, first_status, 9.5) is None

    late_status = dict(first_status, encoder=10.1)
    assert MODULE.validate_pre_window_coverage(
        10.0, late_status, 9.5,
    ) == 'encoder_erster_status_nach_messstart'
    assert MODULE.validate_pre_window_coverage(
        10.0, {'hwt': 9.0, 'encoder': 9.2}, 9.5,
    ) == 'hwt_raw_erster_status_fehlt'
    assert MODULE.validate_pre_window_coverage(
        10.0, first_status, 10.1,
    ) == 'ros_graph_erster_check_nach_messstart'
    equal_status = dict(first_status, encoder=10.0)
    assert MODULE.validate_pre_window_coverage(
        10.0, equal_status, 9.5,
    ) == 'encoder_erster_status_nach_messstart'
    assert MODULE.validate_pre_window_coverage(
        10.0, first_status, 10.0,
    ) == 'ros_graph_erster_check_nach_messstart'


def test_graph_contract_requires_exact_sources_and_no_production_publishers():
    nodes = [
        (name.lstrip('/'), '/')
        for name in MODULE.EXPECTED_GRAPH_NODES
    ]
    publishers = {
        topic: list(expected)
        for topic, expected in MODULE.EXPECTED_TOPIC_PUBLISHERS.items()
    }
    publishers.update({topic: [] for topic in MODULE.FORBIDDEN_PUBLISHER_TOPICS})

    assert MODULE.validate_graph_contract(nodes, publishers) == []

    extra_nodes = nodes + [('rogue', '/')]
    assert 'ros_graph_nodes_unerwartet' in MODULE.validate_graph_contract(
        extra_nodes, publishers)
    publishers['/cmd_vel'] = ['/rogue']
    assert 'produktiver_publisher_unerwartet:/cmd_vel' in (
        MODULE.validate_graph_contract(nodes, publishers))
    publishers[MODULE.IMU_TOPIC] = ['/rogue']
    assert f'ros_graph_publisher_unerwartet:{MODULE.IMU_TOPIC}' in (
        MODULE.validate_graph_contract(nodes, publishers))


def test_graph_contract_detects_duplicate_and_changed_publisher_instance():
    nodes = [
        (name.lstrip('/'), '/')
        for name in MODULE.EXPECTED_GRAPH_NODES
    ]
    publishers = {
        topic: list(expected)
        for topic, expected in MODULE.EXPECTED_TOPIC_PUBLISHERS.items()
    }
    publishers.update({topic: [] for topic in MODULE.FORBIDDEN_PUBLISHER_TOPICS})
    endpoints = {
        topic: [f'{next(iter(names))}@gid-{index}']
        for index, (topic, names) in enumerate(
            MODULE.EXPECTED_TOPIC_PUBLISHERS.items())
    }

    guard = MODULE.GraphContinuityGuard()
    guard.observe(1.0, nodes, publishers, endpoints)
    guard.observe(1.5, nodes, publishers, endpoints)
    assert guard.fault_reason is None
    assert guard.first_check_s == pytest.approx(1.0)
    assert guard.maximum_check_gap_s == pytest.approx(0.5)

    changed = {topic: list(values) for topic, values in endpoints.items()}
    changed[MODULE.IMU_TOPIC] = ['/hwt601_shadow@new-gid']
    guard.observe(2.0, nodes, publishers, changed)
    assert guard.fault_reason == 'ros_graph_publisher_instanz_gewechselt'

    duplicate_publishers = {
        topic: list(values) for topic, values in publishers.items()}
    duplicate_publishers[MODULE.IMU_TOPIC].append('/hwt601_shadow')
    assert f'ros_graph_publisher_unerwartet:{MODULE.IMU_TOPIC}' in (
        MODULE.validate_graph_contract(nodes, duplicate_publishers))
