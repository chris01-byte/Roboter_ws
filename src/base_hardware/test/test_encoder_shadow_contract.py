#!/usr/bin/env python3
"""Quell-/Konfigurationsvertrag des isolierten Encoder-Shadow-Nodes."""

import ast
from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
READER_PATH = PACKAGE_ROOT / 'base_hardware' / 'encoder_shadow_reader.py'
NODE_PATH = PACKAGE_ROOT / 'base_hardware' / 'encoder_shadow_node.py'
CONFIG_PATH = PACKAGE_ROOT / 'config' / 'encoder_shadow.yaml'
LAUNCH_PATH = PACKAGE_ROOT / 'launch' / 'encoder_shadow.launch.py'
SETUP_PATH = PACKAGE_ROOT / 'setup.py'


def call_attributes(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_new_sources_are_valid_python():
    for path in (READER_PATH, NODE_PATH, LAUNCH_PATH, SETUP_PATH):
        ast.parse(path.read_text(encoding='utf-8'))


def test_productive_transport_exposes_only_fc03_modbus_operation():
    calls = call_attributes(READER_PATH)
    assert 'read_holding_registers' in calls
    assert not any(name.startswith('write') for name in calls)
    source = READER_PATH.read_text(encoding='utf-8')
    assert 'FC03_READ_WHITELIST' in source
    for address in ('0x000A', '0x0011', '0x0019', '0x0101'):
        assert address in source


def test_node_has_no_command_subscription_write_or_tf_surface():
    calls = call_attributes(NODE_PATH)
    assert 'create_subscription' not in calls
    assert not any(name.startswith('write') for name in calls)
    source = NODE_PATH.read_text(encoding='utf-8')
    assert 'TransformBroadcaster' not in source
    assert 'sendTransform' not in source
    assert "'/cmd_vel'" not in source
    assert "'/tf'" not in source
    assert "'output_qos': 'reliable_keep_last_10'" in source


def test_config_uses_measured_geometry_and_strict_shadow_contract():
    params = yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8'))[
        'hwt601_encoder_shadow_reader']['ros__parameters']
    assert params['odom_topic'] == '/shadow/hwt601/wheel_odom_raw'
    assert params['status_topic'] == '/shadow/hwt601/wheel_status_json'
    assert params['diagnostics_topic'].startswith('/shadow/hwt601/')
    assert params['port'] == '/dev/ttyUSB_BASE'
    assert params['forbidden_port_alias'] == '/dev/ttyUSB_HWT601'
    assert params['left_motor_id'] == 1
    assert params['right_motor_id'] == 2
    assert params['position_register'] == 0x000A
    assert params['segment_register'] == 0x0011
    assert params['word_order_register'] == 0x0019
    assert params['resolution_register'] == 0x0101
    assert params['expected_segment'] == 1000
    assert params['expected_word_order'] == 0
    assert params['expected_resolution'] == 4000
    assert params['counts_per_motor_revolution'] == 1000.0
    assert params['wheel_radius_m'] == 0.0624
    assert params['wheel_separation_m'] == 0.3845
    assert params['gear_ratio'] == 10.0
    assert params['max_pair_read_duration_s'] == 0.05
    assert params['max_sample_gap_s'] == 0.10
    assert params['read_only'] is True
    assert params['sensor_write_commands'] is False
    assert params['actuator_output'] is False
    assert params['publish_tf'] is False
    assert params['use_sim_time'] is False


def test_launch_starts_exactly_one_reader_and_never_main_base_node():
    source = LAUNCH_PATH.read_text(encoding='utf-8')
    assert source.count('Node(') == 1
    assert "executable='encoder_shadow_reader'" in source
    assert "executable='base_hardware'" not in source
    assert "'encoder_shadow.yaml'" in source
    assert 'IncludeLaunchDescription' not in source


def test_setup_registers_dedicated_entry_point():
    source = SETUP_PATH.read_text(encoding='utf-8')
    assert (
        'encoder_shadow_reader = base_hardware.encoder_shadow_node:main'
        in source
    )


def test_node_uses_pair_midpoint_for_ros_header_stamp():
    source = NODE_PATH.read_text(encoding='utf-8')
    assert 'ros_read_started = self.get_clock().now()' in source
    assert 'ros_read_finished = self.get_clock().now()' in source
    assert (
        'ros_read_started.nanoseconds + ros_read_finished.nanoseconds'
        in source
    )
    assert "self.core.latch_fault('ros_zeit_nicht_monoton')" in source


def test_node_latches_and_closes_before_any_possible_reconnect():
    source = NODE_PATH.read_text(encoding='utf-8')
    poll_start = source.index('    def _poll(self)')
    poll_end = source.index('    def _publish_odometry', poll_start)
    poll = source[poll_start:poll_end]
    assert poll.index('if self.core.fault_reason is not None:') < poll.index(
        'self.transport.connect()')
    assert "self.core.latch_fault('basisport_nicht_sicher')" in poll
    assert poll.index('self._close_transport()') < poll.rindex('return')
