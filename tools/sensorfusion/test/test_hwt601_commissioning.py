import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hwt601_usb_setup as setup  # noqa: E402
from hwt601_messen import Measurement  # noqa: E402
from robot_state_estimation.hwt601_protocol import decode_motion_registers  # noqa: E402


def test_brltty_override_keeps_all_original_rules_and_is_exact():
    original = 'SOME_ORIGINAL_RULE\nLABEL="brltty_device_end"\n'
    result = setup.brltty_rules(original)
    assert result.endswith(original)
    guard = result.splitlines()[2]
    assert '1a86' in guard and '7523' in guard
    assert setup.DEV_PATH in guard
    assert 'ENV{SYSTEMD_WANTS}=""' in result
    assert 'ENV{BRLTTY_BRAILLE_DRIVER}=""' in result
    assert 'BG03R8RZ' not in result
    assert '10c4' not in result
    with pytest.raises(ValueError):
        setup.brltty_rules('LABEL="new_upstream_label"')


def test_alias_never_matches_all_ch340s_or_vl53_i2c():
    lines = setup.alias_rules().splitlines()
    tty = next(line for line in lines if line.startswith('SUBSYSTEM=="tty"'))
    assert f'ENV{{ID_PATH}}=="{setup.ID_PATH}:1.0"' in tty
    assert '7523' in tty and '5512' not in tty
    assert 'ttyUSB_HWT601' in tty and 'ttyUSB_BASE' not in tty
    assert 'MODE="0660"' in tty


def test_stationary_report_is_not_a_fusion_clearance():
    measurement = Measurement(0.0)
    sample = decode_motion_registers((0, 0, 8192, 0, 0, 0))
    for i in range(1, 1001):
        measurement.add(sample, i / 100.0)
    report = measurement.report(10.0)
    assert report['raw_check_passed'] is True
    assert report['rate_hz'] == 100
    assert report['fusion_ready'] is False
    assert report['gyro_scale_validated'] is False
    assert report['mount_tf_validated'] is False
    assert report['raw_gyro_integral_deg_xyz'] == [0, 0, 0]
    json.dumps(report, allow_nan=False)


def test_missing_data_start_and_end_gaps_and_wrong_scale_fail():
    sample = decode_motion_registers((0, 0, 8192, 0, 0, 1))
    empty = Measurement(0.0).report(1.0)
    assert empty['raw_check_passed'] is False
    json.dumps(empty, allow_nan=False)
    m = Measurement(0.0)
    for i in range(50, 151):
        m.add(sample, i / 100.0)
    report = m.report(2.0)
    assert report['maximum_gap_s'] == 0.5
    assert report['integral_complete'] is False
    assert report['raw_check_passed'] is False
    m = Measurement(0.0)
    for i in range(1, 101):
        m.add(decode_motion_registers((0, 0, 2048, 0, 0, 0)), i / 100.0)
    assert m.report(1.0)['raw_check_passed'] is False


def test_install_refuses_unprivileged_execution(monkeypatch):
    monkeypatch.setattr(setup.os, 'geteuid', lambda: 1000)
    with pytest.raises(ValueError, match='sudo'):
        setup.install()


def test_foreign_kernel_is_rejected_before_build(monkeypatch):
    monkeypatch.setattr(setup.platform, 'release', lambda: 'other-kernel')
    with pytest.raises(ValueError, match='Jetson'):
        setup.check_host()


@pytest.fixture
def installation(tmp_path, monkeypatch):
    build = tmp_path / 'build'
    build.mkdir()
    vendor = tmp_path / 'vendor.rules'
    vendor.write_text('LABEL="brltty_device_end"\n')
    monkeypatch.setattr(setup, 'BUILD', build)
    monkeypatch.setattr(setup, 'VENDOR_RULE', vendor)
    monkeypatch.setattr(setup, 'STATE', tmp_path / 'state')
    targets = {}
    for name, attribute in [('ch341.ko', 'MODULE'),
                            ('85-brltty.rules', 'BRLTTY_RULE'),
                            ('83-hwt601.rules', 'ALIAS_RULE')]:
        (build / name).write_text('synthetic ' + name)
        targets[name] = tmp_path / 'system' / name
        monkeypatch.setattr(setup, attribute, targets[name])
    manifest = {
        'kernel': setup.RELEASE, 'source_sha256': setup.SOURCE_SHA,
        'vendor_rule_sha256': setup.sha(vendor.read_bytes()),
        'files': {name: setup.sha((build / name).read_bytes()) for name in targets},
    }
    (build / 'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setattr(setup.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(setup, 'check_host', lambda: None)
    monkeypatch.setattr(setup, 'check_device', lambda: None)
    calls = []
    monkeypatch.setattr(setup, 'run', lambda *args: calls.append(args))
    return targets, calls


def test_install_is_idempotent_and_rollback_is_recoverable(installation):
    targets, calls = installation
    setup.install()
    setup.install()
    assert all(path.exists() for path in targets.values())
    assert ('systemctl', 'stop', 'brltty-udev.service') in calls
    assert not any('disable' in call or 'mask' in call for call in calls)
    setup.rollback()
    assert not any(path.exists() for path in targets.values())
    backups = list(setup.STATE.glob('rollback-*'))
    assert len(backups) == 1
    assert all((backups[0] / name).is_file() for name in targets)


def test_unknown_rule_is_never_overwritten(installation):
    targets, calls = installation
    setup.BRLTTY_RULE.parent.mkdir()
    setup.BRLTTY_RULE.write_text('user-owned-rule')
    with pytest.raises(ValueError, match='Unbekannte Zieldatei'):
        setup.install()
    assert setup.BRLTTY_RULE.read_text() == 'user-owned-rule'
    assert not setup.MODULE.exists()
    assert calls == []


def test_changed_vendor_rule_or_module_is_not_installed(installation):
    targets, calls = installation
    setup.VENDOR_RULE.write_text('updated package')
    with pytest.raises(ValueError, match='aktualisiert'):
        setup.install()
    assert not any(path.exists() for path in targets.values())
    assert calls == []


def test_modified_installed_rule_is_not_removed(installation):
    targets, calls = installation
    setup.install()
    setup.ALIAS_RULE.write_text('new user change')
    calls.clear()
    with pytest.raises(ValueError, match='veraendert'):
        setup.rollback()
    assert setup.ALIAS_RULE.read_text() == 'new user change'
    assert calls == []
