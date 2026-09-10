import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DIRECT_SCRIPT = ROOT / 'hwt601_encoder_shadow_stillstand.py'
DIRECT_SPEC = importlib.util.spec_from_file_location(
    'hwt601_encoder_shadow_stillstand', DIRECT_SCRIPT)
DIRECT_MODULE = importlib.util.module_from_spec(DIRECT_SPEC)
assert DIRECT_SPEC.loader is not None
sys.modules[DIRECT_SPEC.name] = DIRECT_MODULE
DIRECT_SPEC.loader.exec_module(DIRECT_MODULE)

SCRIPT = ROOT / 'hwt601_encoder_shadow_ekf_stillstand.py'
SPEC = importlib.util.spec_from_file_location(
    'hwt601_encoder_shadow_ekf_stillstand', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _passing_summary():
    return {
        'complete': True,
        'requested_duration_s': 120.0,
        'faults': [],
        'ekf': {
            'duration_s': 120.01,
            'rate_hz': 30.0,
            'maximum_stamp_gap_s': 0.04,
            'peak_translation_from_start_m': 0.0,
            'final_yaw_deg': 0.1,
            'peak_absolute_yaw_deg': 0.1,
            'peak_absolute_linear_velocity_mps': 0.0,
            'peak_absolute_yaw_rate_radps': 0.001,
        },
        'direct_comparison': {
            'peak_translation_m': 0.0,
            'hwt_angle_deg': 0.1,
            'encoder_angle_deg': 0.0,
        },
        'sources': {
            'hwt_valid': True,
            'hwt_raw_valid': True,
            'encoder_valid': True,
            'post_window_fresh': True,
        },
        'graph': {
            'valid': True,
            'forbidden_publishers_absent': True,
        },
    }


def test_acceptance_passes_only_complete_bounded_isolated_result():
    summary = _passing_summary()
    assert MODULE._passed(summary)

    failures = (
        (('ekf', 'rate_hz'), 24.9),
        (('ekf', 'maximum_stamp_gap_s'), 0.101),
        (('ekf', 'peak_translation_from_start_m'), 0.001),
        (('ekf', 'final_yaw_deg'), 1.0),
        (('ekf', 'peak_absolute_yaw_deg'), 1.0),
        (('ekf', 'peak_absolute_linear_velocity_mps'), 0.005),
        (('ekf', 'peak_absolute_yaw_rate_radps'), 0.005),
        (('direct_comparison', 'hwt_angle_deg'), 1.0),
        (('sources', 'post_window_fresh'), False),
        (('graph', 'forbidden_publishers_absent'), False),
    )
    for path, value in failures:
        candidate = _passing_summary()
        candidate[path[0]][path[1]] = value
        assert not MODULE._passed(candidate), path


def test_observer_has_no_publisher_hardware_or_control_path():
    source = SCRIPT.read_text(encoding='utf-8')

    assert 'create_publisher' not in source
    assert 'serial.Serial' not in source
    assert 'ModbusSerialClient' not in source
    assert 'subprocess' not in source
    assert 'TransformBroadcaster' not in source
    assert "EKF_TOPIC = '/shadow/hwt601/odom'" in source
    assert "'/odom', '/map', '/tf', '/tf_static', '/cmd_vel'" in source
    assert (
        "super().__init__('hwt601_encoder_shadow_stillstand_observer')"
        in source
    )
    assert 'post_window_fresh' in source
    assert 'samples_sha256' in source


def test_ekf_wrappers_keep_order_domain_and_launch_scope():
    observer = (
        ROOT / 'start_hwt601_encoder_shadow_ekf_observer.sh'
    ).read_text(encoding='utf-8')
    launcher = (
        ROOT / 'start_hwt601_encoder_shadow_ekf.sh'
    ).read_text(encoding='utf-8')

    assert '--duration 120' in observer
    assert 'ros2 node list --no-daemon 2>&1' in observer
    assert 'NetworkInterface name="lo"' in observer
    assert 'Reale Messdaten duerfen nicht im Repository liegen' in observer
    assert 'ros2 launch' not in observer
    assert '/dev/tty' not in observer
    assert 'AMADEUS_HWT_ENCODER_EKF_STILLSTAND=JA fehlt' in launcher
    assert 'hwt601_encoder_shadow_ekf.launch.py' in launcher
    assert 'expected_nodes=' in launcher
    assert 'NetworkInterface name="lo"' in launcher
    assert 'base_hardware.launch.py' not in launcher
    assert 'cmd_vel' not in launcher
