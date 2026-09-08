import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hwt601_drehtest as module  # noqa: E402


def simulate(angle, target=90, roll=0):
    bias = (.001, .006, .0001)
    test = module.TurnMeasurement(bias, target)
    gyro = tuple(v+b for v,b in zip(
        (math.radians(roll)/10, 0, math.radians(angle)/10), bias))
    for i in range(1001):
        test.add(i*.01, gyro)
    return test.report()


@pytest.mark.parametrize('target', [90, -90])
def test_both_directions_with_bias_are_integrated_correctly(target):
    report = simulate(target, target)
    assert report['coarse_angle_check_passed']
    assert report['measured_angle_deg_xyz'][2] == pytest.approx(target)
    assert report['observed_scale_ratio'] == pytest.approx(1)
    assert not report['bias_adaptation_during_turn']
    assert not report['fusion_ready']


@pytest.mark.parametrize('angle', [-90, 0, 45, 180, 84, 96])
def test_sign_missing_motion_wrong_scale_and_excess_error_fail(angle):
    assert not simulate(angle)['coarse_angle_check_passed']


def test_tilt_fails_even_if_yaw_matches():
    report = simulate(90, roll=6)
    assert not report['planar_check_passed']
    assert not report['coarse_angle_check_passed']


def test_external_bias_input_cannot_change_frozen_reference():
    original = [0, 0, .01]
    test = module.TurnMeasurement(original, 90)
    original[2] = 9
    assert test.bias == (0, 0, .01)
    assert not test.report()['coarse_angle_check_passed']


@pytest.mark.parametrize('stamp,vector', [
    (.2, (0,0,0)), (-.01, (0,0,0)), (float('nan'), (0,0,0)),
    (.01, (0,0,float('nan'))), (.01, (0,0)),
])
def test_gaps_bad_clock_and_invalid_data_are_not_integrated(stamp, vector):
    test = module.TurnMeasurement((0,0,0), 90)
    test.add(0, (0,0,0))
    with pytest.raises(ValueError):
        test.add(stamp, vector)


def test_default_preflight_never_opens_serial(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['hwt601_drehtest.py'])
    monkeypatch.setattr(module, 'check_usb', lambda: '/dev/ttyUSB_HWT601')
    def forbidden(*args, **kwargs):
        raise AssertionError('No port may open during preparation')
    monkeypatch.setattr(module, 'Hwt601SerialTransport', forbidden)
    assert module.main() == 0


def test_run_requires_explicit_declarations(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['hwt601_drehtest.py', '--run'])
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2


def test_full_operator_flow_with_synthetic_serial_only(tmp_path, monkeypatch):
    from robot_state_estimation.hwt601_protocol import Hwt601Sample
    clock = [0.0]
    commands = {'s': False, 'e': False}
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(module.time, 'sleep', lambda seconds: clock.__setitem__(0, clock[0]+seconds))
    monkeypatch.setattr(module.Path, 'home', lambda: tmp_path)

    class Link:
        def __init__(self, *args):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read_motion_registers(self):
            clock[0] += .002
            return ()

    def sample(_):
        rate = math.radians(9) if 25.1 <= clock[0] < 35.1 else 0
        return Hwt601Sample((0,0,8192), (0,0,0), (0,0,9.80665), (.001,.006,.0001+rate))

    def command():
        for key, stamp in [('s', 25.08), ('e', 35.2)]:
            if clock[0] >= stamp and not commands[key]:
                commands[key] = True
                return key
        return None

    monkeypatch.setattr(module, 'Hwt601SerialTransport', Link)
    monkeypatch.setattr(module, 'decode_motion_registers', sample)
    monkeypatch.setattr(module, 'operator_line', command)
    assert module.run_test('/dev/NOT_REAL', 'left') == 0
    import json
    report_path = next(tmp_path.glob('.local/share/amadeus/hwt601/turn-*/summary.json'))
    report = json.loads(report_path.read_text())
    assert report['complete'] and report['passed']
    assert report['measurement']['fixed_bias_radps_xyz'] == pytest.approx([.001,.006,.0001])
