#!/usr/bin/env python3
"""Regressionstests fuer die fail-closed Stillstands-Scanfreigabe."""

import math
import os
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from amadeus_lidar_bringup.stationary_scan_gate_core import (  # noqa: E402
    GateParameters,
    GateState,
    StationaryScanGate,
    angular_distance,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def stable_inputs(gate, now_s, *, x_m=0.0, yaw_rad=0.0):
    gate.update_imu(
        now_s, (0.002, -0.003, 0.001), (0.0, 0.0, 9.75))
    gate.update_odom(
        now_s, (0.0, 0.0), 0.0, (x_m, 0.0, yaw_rad))


class StationaryScanGateTests(unittest.TestCase):
    def setUp(self):
        self.params = GateParameters(
            settle_duration_s=1.0,
            capture_duration_s=2.0,
            sensor_max_age_s=0.5,
            maximum_linear_speed_m_s=0.01,
            maximum_angular_speed_rad_s=0.02,
            maximum_imu_angular_speed_rad_s=0.08,
            gravity_m_s2=9.80665,
            maximum_acceleration_deviation_m_s2=0.8,
            rearm_motion_duration_s=0.1,
            rearm_translation_m=0.08,
            rearm_rotation_rad=0.08,
        )
        self.gate = StationaryScanGate(self.params)

    def _scan_with_fresh_stable_inputs(self, now_s, **kwargs):
        stable_inputs(self.gate, now_s, **kwargs)
        return self.gate.process_scan(now_s)

    def test_missing_sensors_keep_gate_closed(self):
        decision = self.gate.process_scan(0.0)
        self.assertFalse(decision.forward_scan)
        self.assertEqual(decision.reason, 'missing_imu')
        self.assertEqual(self.gate.state, GateState.WAIT_STABLE)

    def test_opens_only_after_continuous_settle_time(self):
        first = self._scan_with_fresh_stable_inputs(0.0)
        second = self._scan_with_fresh_stable_inputs(0.9)
        opened = self._scan_with_fresh_stable_inputs(1.0)

        self.assertFalse(first.forward_scan)
        self.assertFalse(second.forward_scan)
        self.assertTrue(opened.forward_scan)
        self.assertEqual(opened.capture_index, 1)
        self.assertEqual(self.gate.state, GateState.CAPTURING)

    def test_capture_closes_and_does_not_repeat_without_movement(self):
        self._scan_with_fresh_stable_inputs(0.0)
        self.assertTrue(self._scan_with_fresh_stable_inputs(1.0).forward_scan)
        self.assertTrue(self._scan_with_fresh_stable_inputs(2.9).forward_scan)
        completed = self._scan_with_fresh_stable_inputs(3.0)
        still_waiting = self._scan_with_fresh_stable_inputs(8.0)

        self.assertFalse(completed.forward_scan)
        self.assertEqual(completed.reason, 'capture_complete')
        self.assertEqual(self.gate.state, GateState.WAIT_MOVEMENT)
        self.assertFalse(still_waiting.forward_scan)
        self.assertEqual(still_waiting.reason, 'wait_movement')
        self.assertEqual(self.gate.capture_index, 1)

    def test_motion_interrupts_capture_immediately(self):
        self._scan_with_fresh_stable_inputs(0.0)
        self.assertTrue(self._scan_with_fresh_stable_inputs(1.0).forward_scan)
        self.gate.update_imu(
            1.1, (0.2, 0.0, 0.0), (0.0, 0.0, 9.8))
        self.gate.update_odom(
            1.1, (0.2, 0.0), 0.0, (0.01, 0.0, 0.0))

        interrupted = self.gate.process_scan(1.1)

        self.assertFalse(interrupted.forward_scan)
        self.assertEqual(self.gate.state, GateState.WAIT_STABLE)
        self.assertEqual(self.gate.interrupted_captures, 1)

    def test_new_capture_requires_motion_then_new_settle(self):
        self._scan_with_fresh_stable_inputs(0.0)
        self._scan_with_fresh_stable_inputs(1.0)
        self._scan_with_fresh_stable_inputs(3.0)

        self.gate.update_imu(
            3.1, (0.01, 0.0, 0.0), (0.0, 0.0, 9.8))
        self.gate.update_odom(
            3.1, (0.2, 0.0), 0.0, (0.02, 0.0, 0.0))
        self.assertFalse(self.gate.process_scan(3.1).forward_scan)
        self.gate.update_imu(
            3.25, (0.01, 0.0, 0.0), (0.0, 0.0, 9.8))
        self.gate.update_odom(
            3.25, (0.2, 0.0), 0.0, (0.10, 0.0, 0.0))
        self.assertFalse(self.gate.process_scan(3.25).forward_scan)

        self.assertFalse(
            self._scan_with_fresh_stable_inputs(3.4, x_m=0.10).forward_scan)
        reopened = self._scan_with_fresh_stable_inputs(4.4, x_m=0.10)

        self.assertTrue(reopened.forward_scan)
        self.assertEqual(reopened.capture_index, 2)

    def test_stale_or_nonfinite_inputs_fail_closed(self):
        stable_inputs(self.gate, 0.0)
        stale = self.gate.process_scan(0.6)
        self.assertFalse(stale.forward_scan)
        self.assertEqual(stale.reason, 'stale_imu')

        self.gate.update_imu(
            1.0, (math.nan, 0.0, 0.0), (0.0, 0.0, 9.8))
        self.gate.update_odom(1.0, (0.0, 0.0), 0.0, (0.0, 0.0, 0.0))
        invalid = self.gate.process_scan(1.0)
        self.assertFalse(invalid.forward_scan)
        self.assertEqual(invalid.reason, 'invalid_imu')

    def test_imu_mast_motion_delays_settle(self):
        stable_inputs(self.gate, 0.0)
        self.gate.process_scan(0.0)
        self.gate.update_imu(
            0.8, (0.1, 0.0, 0.0), (0.0, 0.0, 9.8))
        self.gate.update_odom(0.8, (0.0, 0.0), 0.0, (0.0, 0.0, 0.0))
        unstable = self.gate.process_scan(0.8)
        self.assertFalse(unstable.forward_scan)
        self.assertEqual(unstable.reason, 'imu_angular_motion')

        self.assertFalse(self._scan_with_fresh_stable_inputs(1.0).forward_scan)
        self.assertTrue(self._scan_with_fresh_stable_inputs(2.0).forward_scan)

    def test_angle_distance_wraps_at_pi(self):
        self.assertAlmostEqual(
            angular_distance(math.radians(179), math.radians(-179)),
            math.radians(2), places=12)


class StationaryScanGateContractTests(unittest.TestCase):
    def test_profile_matches_verified_fail_closed_contract(self):
        profile = yaml.safe_load(
            (PACKAGE_ROOT / 'config' / 'stationary_scan_gate.yaml')
            .read_text(encoding='utf-8'))
        params = profile['stationary_scan_gate']['ros__parameters']

        self.assertEqual(params['input_scan_topic'], '/scan_normiert')
        self.assertEqual(params['output_scan_topic'], '/scan_stillstand')
        self.assertEqual(params['imu_topic'], '/oak/imu/data')
        self.assertEqual(params['odom_topic'], '/odom')
        self.assertGreaterEqual(params['settle_duration_s'], 1.0)
        self.assertLessEqual(params['capture_duration_s'], 3.0)
        self.assertLessEqual(params['sensor_max_age_s'], 0.5)

    def test_dedicated_launch_gates_only_slam_input(self):
        launch = (
            PACKAGE_ROOT / 'launch' / 'stationary_slam_lidar.launch.py'
        ).read_text(encoding='utf-8')

        self.assertIn("executable='stationary_scan_gate'", launch)
        self.assertIn("'output_scan_topic': '/scan_stillstand'", launch)
        self.assertIn("{'scan_topic': '/scan_stillstand'}", launch)
        self.assertIn("'map_file_name': map_file_name", launch)
        self.assertIn("'map_start_pose': start_pose", launch)
        self.assertIn("package='joy'", launch)
        self.assertIn("remappings=[('/cmd_vel', '/cmd_vel')]", launch)

        standard_launch = (
            PACKAGE_ROOT / 'launch' / 'slam_lidar.launch.py'
        ).read_text(encoding='utf-8')
        self.assertNotIn('stationary_scan_gate', standard_launch)
        self.assertNotIn('/scan_stillstand', standard_launch)

    def test_manual_start_requires_fresh_motor_authorization(self):
        script = (
            PACKAGE_ROOT.parents[1] / 'tools' / 'kartierung' /
            'start_stationaere_kartierung.sh'
        ).read_text(encoding='utf-8')

        self.assertIn('stationary_slam_lidar.launch.py', script)
        self.assertIn('AMADEUS_FAHRFREIGABE', script)
        self.assertIn('oak_imu_check --duration 3', script)
        self.assertIn('AMADEUS_OHNE_NAHBEREICH', script)

    def test_stationary_workflow_uses_local_dds_only(self):
        tools = PACKAGE_ROOT.parents[1] / 'tools' / 'kartierung'
        profile = tools / 'cyclonedds_stationaer_lokal.xml'
        root = ET.parse(profile).getroot()

        interfaces = [
            element for element in root.iter()
            if element.tag.rsplit('}', 1)[-1] == 'NetworkInterface'
        ]
        peers = [
            element for element in root.iter()
            if element.tag.rsplit('}', 1)[-1] == 'Peer'
        ]
        values = {
            element.tag.rsplit('}', 1)[-1]: (element.text or '').strip()
            for element in root.iter()
        }

        self.assertEqual(len(interfaces), 1)
        self.assertEqual(interfaces[0].attrib.get('name'), 'lo')
        self.assertEqual(peers, [])
        self.assertEqual(values.get('ParticipantIndex'), 'auto')
        self.assertGreaterEqual(int(values['MaxAutoParticipantIndex']), 64)

        environment = (
            tools / 'stationaere_ros_umgebung.sh'
        ).read_text(encoding='utf-8')
        self.assertIn('RMW_IMPLEMENTATION=rmw_cyclonedds_cpp', environment)
        self.assertIn('cyclonedds_stationaer_lokal.xml', environment)

        for script_name in (
                'start_stationaere_oak.sh',
                'start_stationaere_kartierung.sh',
                'save_stationaere_kartierung.sh',
                'record_stationary_mapping_bag.sh'):
            script = (tools / script_name).read_text(encoding='utf-8')
            self.assertIn(
                'source "$SCRIPT_DIR/stationaere_ros_umgebung.sh"', script)

        oak_start = (
            tools / 'start_stationaere_oak.sh'
        ).read_text(encoding='utf-8')
        self.assertIn('oak.launch.py pointcloud:=false', oak_start)
        self.assertIn('ros2 node list --no-daemon', oak_start)

        mapping_start = (
            tools / 'start_stationaere_kartierung.sh'
        ).read_text(encoding='utf-8')
        self.assertIn('ros2 node list --no-daemon', mapping_start)

        save = (
            tools / 'save_stationaere_kartierung.sh'
        ).read_text(encoding='utf-8')
        self.assertIn('ros2 service list --no-daemon', save)

    def test_local_save_keeps_raster_and_posegraph(self):
        script = (
            PACKAGE_ROOT.parents[1] / 'tools' / 'kartierung' /
            'save_stationaere_kartierung.sh'
        ).read_text(encoding='utf-8')

        self.assertIn('/slam_toolbox/save_map', script)
        self.assertIn('/slam_toolbox/serialize_map', script)
        self.assertIn('.posegraph', script)
        self.assertIn('.data', script)


if __name__ == '__main__':
    unittest.main(verbosity=2)
