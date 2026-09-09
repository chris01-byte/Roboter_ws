import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1] / 'hwt601_shadow_stillstand.py')
SPEC = importlib.util.spec_from_file_location('hwt601_shadow_stillstand', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _summary():
    return {
        'requested_duration_s': 600.0,
        'duration_s': 600.0,
        'samples': 60000,
        'rate_hz': 100.0,
        'maximum_gap_s': 0.02,
        'invalid_messages': 0,
        'integral_deg': 0.1,
        'peak_absolute_integral_deg': 0.2,
        'shadow_status': {
            'ready': True,
            'fusion_ready': False,
            'latched_fault': None,
            'rejected': 0,
            'bias': {'adaptation_samples': 0},
        },
        'raw_status': {
            'ready': True,
            'rejected': 0,
            'reconnects': 0,
        },
    }


def test_acceptance_requires_all_shadow_and_raw_health_signals():
    summary = _summary()
    assert MODULE._passed(summary)

    for path, bad_value in (
            (('shadow_status', 'latched_fault'), 'imu_datenluecke'),
            (('shadow_status', 'bias', 'adaptation_samples'), 1),
            (('raw_status', 'reconnects'), 1),
            (('maximum_gap_s',), 0.11),
            (('integral_deg',), 1.01),
            (('peak_absolute_integral_deg',), 1.01),
            (('shadow_status', 'rejected'), 1)):
        changed = _summary()
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = bad_value
        assert not MODULE._passed(changed)
