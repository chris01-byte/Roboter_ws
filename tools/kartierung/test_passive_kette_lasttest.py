#!/usr/bin/env python3
"""Offline-Vertragstests fuer den passiven WE-M2-Kettenlanglauf."""

from array import array
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'amadeus_map_identity'))
sys.path.insert(0, str(ROOT / 'src' / 'explore'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from passive_kette_lasttest import (  # noqa: E402
    capacity_probe,
    duration_summary_ns,
    run_probe,
    synthetic_apartment_grid,
    validate_arguments,
)


def test_synthetic_growth_preserves_metric_apartment_origin():
    first = synthetic_apartment_grid(
        1, growth_interval=2, maximum_padding=2, base_stamp_ns=1000)
    grown = synthetic_apartment_grid(
        5, growth_interval=2, maximum_padding=2, base_stamp_ns=1000)

    assert (first.info.width, first.info.height) == (100, 60)
    assert (grown.info.width, grown.info.height) == (104, 64)
    assert grown.info.origin.position.x == pytest.approx(-0.10)
    assert grown.info.origin.position.y == pytest.approx(-0.10)
    assert first.header.stamp.nanosec != grown.header.stamp.nanosec
    assert array('b', first.data).tobytes() != array('b', grown.data).tobytes()


def test_short_probe_runs_exact_chain_without_task_growth():
    result = run_probe(
        revisions=4,
        growth_interval=2,
        maximum_padding=2,
        base_stamp_ns=1_800_000_000_000_000_000,
    )

    assert result['passive'] is True
    assert result['hardware_access'] is False
    assert result['actions_sent'] == 0
    assert result['commands_published'] == 0
    assert result['observed']['capacity_rejected_atomically'] is True
    assert result['observed']['confirmed_portal_count'] == 1
    assert result['observed']['connection_count'] == 1
    assert result['observed']['region_count'] == 2
    assert result['observed']['frontier_task_count'] >= 1
    assert result['observed']['maximum_task_count'] == (
        result['observed']['frontier_task_count'] + 2)
    assert result['processing_duration']['samples'] == 4
    assert result['rss_bytes']['peak'] >= result['rss_bytes']['start']


def test_capacity_probe_is_atomic():
    assert capacity_probe() is True


def test_argument_and_duration_bounds_fail_closed():
    validate_arguments(2, 1, 0)
    for values in ((1, 1, 0), (513, 1, 0), (2, 0, 0), (2, 1, 25)):
        with pytest.raises(ValueError):
            validate_arguments(*values)
    assert duration_summary_ns([4, 1, 3, 2, 100]) == {
        'minimum_ns': 1,
        'median_ns': 3,
        'p95_ns': 100,
        'maximum_ns': 100,
        'samples': 5,
    }
    with pytest.raises(ValueError):
        duration_summary_ns([])


def test_probe_source_contains_no_runtime_or_drive_start():
    source = (Path(__file__).with_name(
        'passive_kette_lasttest.py').read_text(encoding='utf-8'))

    assert 'subprocess' not in source
    assert 'Popen(' not in source
    assert 'create_publisher' not in source
    assert 'create_subscription' not in source
    assert 'ActionClient' not in source
    assert 'Twist' not in source
