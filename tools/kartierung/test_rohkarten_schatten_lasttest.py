#!/usr/bin/env python3
"""Offline-Vertragstests fuer den passiven WE-M2-Rohkartenlasttest."""

import json
from pathlib import Path
import signal
import subprocess
import sys

import pytest
from rclpy.serialization import deserialize_message, serialize_message


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src' / 'amadeus_map_identity'))
sys.path.insert(0, str(ROOT / 'src' / 'explore'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rohkarten_schatten_lasttest import (  # noqa: E402
    MAXIMUM_OUTPUT_BYTES,
    bounded_json,
    duration_summary_ns,
    early_domain_id,
    explorer_command,
    manager_status_json,
    parse_integer_csv,
    parse_vm_rss_bytes,
    source_from_grid,
    stop_process,
    synthetic_grid,
    validate_diagnostics,
    validate_matrix,
)
from nav_msgs.msg import OccupancyGrid  # noqa: E402


def test_early_domain_is_validated_before_ros_import():
    assert early_domain_id([]) == 228
    assert early_domain_id(['--domaene', '17']) == 17
    assert early_domain_id(['--domaene=232']) == 232
    for arguments in (['--domaene'], ['--domaene', '-1'],
                      ['--domaene=233'], ['--domaene=x'],
                      ['--domaene=1', '--domaene', '2']):
        with pytest.raises(ValueError):
            early_domain_id(arguments)


def test_csv_and_matrix_limits_are_explicit():
    assert parse_integer_csv(
        '64, 256', name='sizes', minimum=1, maximum=2000) == (64, 256)
    for value in ('', '1,1', '0', '2001', 'a'):
        with pytest.raises(ValueError):
            parse_integer_csv(value, name='sizes', minimum=1, maximum=2000)
    validate_matrix((64, 2000), (1, 4), 3)
    with pytest.raises(ValueError):
        validate_matrix((2001,), (1,), 1)
    with pytest.raises(ValueError):
        validate_matrix((1, 2, 3, 4), (1, 2, 3, 4), 1)
    with pytest.raises(ValueError):
        validate_matrix((64,), (1,), 21)


def test_duration_summary_is_bounded_and_deterministic():
    assert duration_summary_ns([4, 1, 3, 2, 100]) == {
        'minimum_ns': 1,
        'median_ns': 3,
        'p95_ns': 100,
        'maximum_ns': 100,
        'samples': 5,
    }
    with pytest.raises(ValueError):
        duration_summary_ns([])


def test_rss_parser_accepts_only_linux_vmrss_line():
    assert parse_vm_rss_bytes('Name:\tpython\nVmRSS:\t123 kB\n') == 125_952
    with pytest.raises(ValueError):
        parse_vm_rss_bytes('VmSize:\t123 kB\n')


def test_wire_roundtrip_controls_fingerprint_fields():
    original = synthetic_grid(4, 3, 1_800_000_000_123_456_789)
    received = deserialize_message(
        serialize_message(original), OccupancyGrid)
    source = source_from_grid(received)
    payload = json.loads(manager_status_json(source, 7))

    assert received.info.resolution != 0.05
    assert payload['map']['summary'] == {
        'fingerprint': source.fingerprint,
        'frame_id': 'map',
        'source_stamp_ns': 1_800_000_000_123_456_789,
    }
    assert payload['counters']['accepted_maps'] == 7


def test_diagnostics_require_capacity_and_counter_conservation():
    payload = {
        'mode': 'shadow',
        'passive': True,
        'raw_map_correlation': {
            'enabled': True,
            'capacity': 2,
            'source_observations': 6,
            'unique_sources': 4,
            'duplicate_sources': 2,
            'pending_sources': 2,
            'evicted_sources': 1,
            'emitted_correlations': 1,
        },
    }
    assert validate_diagnostics(
        payload, capacity=2, expected_observations=6,
        expected_unique=4, expected_duplicates=2,
        minimum_emitted=1)['evicted_sources'] == 1
    payload['raw_map_correlation']['pending_sources'] = 3
    with pytest.raises(ValueError):
        validate_diagnostics(
            payload, capacity=2, expected_observations=6,
            expected_unique=4, expected_duplicates=2,
            minimum_emitted=1)


def test_explorer_command_remaps_every_potentially_active_interface():
    command = explorer_command(
        executable='/tmp/explore', explorer_name='probe_explorer',
        prefix='/probe', capacity=3,
        behavior_tree='/tmp/no-recovery.xml')
    text = ' '.join(command)
    assert text.startswith('/tmp/explore --ros-args')
    for fragment in (
            '__node:=probe_explorer',
            '/explore_area:=/probe/unused_explore_area',
            'map_topic:=/probe/map',
            'scan_command_topic:=/probe/unused_scan_cmd',
            'door_command_topic:=/probe/unused_door_cmd',
            'nav_action_name:=/probe/unused_navigate_to_pose',
            'behavior_tree:=/tmp/no-recovery.xml',
            'region_graph_shadow_raw_map_capacity:=3'):
        assert fragment in text
    assert 'active_drive' not in text


def test_bounded_output_rejects_unbounded_payload():
    text = bounded_json({'schema_version': 1, 'cases': []})
    assert len(text.encode('utf-8')) < MAXIMUM_OUTPUT_BYTES
    with pytest.raises(ValueError):
        bounded_json({'value': 'x' * MAXIMUM_OUTPUT_BYTES})


class FakeProcess:
    def __init__(self, timeouts=0):
        self.returncode = None
        self.timeouts = timeouts
        self.signals = []

    def poll(self):
        return self.returncode

    def send_signal(self, value):
        self.signals.append(value)

    def wait(self, timeout):
        if self.timeouts:
            self.timeouts -= 1
            raise subprocess.TimeoutExpired('fake', timeout)
        self.returncode = 0

    def terminate(self):
        self.signals.append(signal.SIGTERM)

    def kill(self):
        self.signals.append(signal.SIGKILL)


def test_process_cleanup_signals_only_the_child_in_order():
    graceful = FakeProcess()
    stop_process(graceful)
    assert graceful.signals == [signal.SIGINT]

    forced = FakeProcess(timeouts=2)
    stop_process(forced)
    assert forced.signals == [signal.SIGINT, signal.SIGTERM, signal.SIGKILL]
