#!/usr/bin/env python3
"""DEVICE-FREE: historical bias adapter + real EKF + production raw-source guard.

All measurements here are synthetic, never a real standstill/drive acceptance.
No driver, serial port, robot launch, mission or velocity command is started.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

# Dedicated loopback domain, never inherit a robot production domain.
os.environ['ROS_DOMAIN_ID'] = '220'
os.environ['ROS_LOCALHOST_ONLY'] = '1'
os.environ['CYCLONEDDS_URI'] = (
    '<CycloneDDS><Domain><General>'
    '<AllowMulticast>false</AllowMulticast></General><Discovery>'
    '<ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>40</MaxAutoParticipantIndex>'
    '<Peers><Peer Address="127.0.0.1"/></Peers></Discovery></Domain></CycloneDDS>')

import rclpy
from ament_index_python.packages import get_package_share_directory, get_package_prefix
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
from robot_state_estimation.hwt601_fusion_guard import Hwt601FusionGuard


class Fixture(Node):
    def __init__(self):
        super().__init__('we_hwt601_synthetic_fixture')
        self.guard = Hwt601FusionGuard(self, True)
        self.raw = self.create_publisher(Imu, '/shadow/hwt601/imu/data_raw', qos_profile_sensor_data)
        self.wheel = self.create_publisher(Odometry, '/fusion/hwt601/wheel_odom_raw', 10)
        self.raw_status = self.create_publisher(String, '/shadow/hwt601/raw_status_json', 10)
        self.wheel_status = self.create_publisher(String, '/base_hardware/state_json', 10)
        self.odom = []
        self.edges = set()
        self.bias_status = None
        self.create_subscription(Odometry, '/odom', lambda msg: self.odom.append(msg), 100)
        self.create_subscription(TFMessage, '/tf', self.on_tf, qos_profile_sensor_data)
        self.create_subscription(String, '/shadow/hwt601/status_json', self.on_bias, 10)
        self.v = self.w = 0.0
        self.drop = None
        self.create_timer(0.01, self.publish_raw)
        self.create_timer(0.05, self.publish_wheel)

    def on_tf(self, msg):
        self.edges.update((t.header.frame_id, t.child_frame_id) for t in msg.transforms)

    def on_bias(self, msg):
        self.bias_status = json.loads(msg.data)

    def publish_raw(self):
        if self.drop == 'raw':
            return
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'hwt601_link'
        msg.orientation.w = 1.0
        msg.orientation_covariance[0] = -1.0
        msg.angular_velocity.z = 0.01 + self.w
        msg.linear_acceleration.z = 9.80665
        for i in (0, 4, 8):
            msg.angular_velocity_covariance[i] = 5e-7
            msg.linear_acceleration_covariance[i] = 0.25
        self.raw.publish(msg)
        self.raw_status.publish(String(data=json.dumps({
            'ready': True, 'raw_data_ready': True, 'port': '/dev/ttyUSB_HWT601',
            'sensor_write_commands': False, 'consecutive_errors': 0, 'age_s': 0.0,
        })))

    def publish_wheel(self):
        if self.drop == 'wheel':
            return
        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'odom'
        msg.child_frame_id = 'base_link'
        msg.pose.pose.orientation.w = 1.0
        msg.twist.twist.linear.x = self.v
        # Deliberately disagree with HWT to prove encoder yaw is NOT fused.
        msg.twist.twist.angular.z = -0.30 if self.w else 0.0
        msg.twist.covariance[0] = 0.01
        msg.twist.covariance[35] = 0.03
        self.wheel.publish(msg)
        self.wheel_status.publish(String(data=json.dumps({
            'dry_run': False, 'allow_rs485': True, 'rs485_ready': True,
            'odometry_source': 'encoder_position', 'encoder_feedback_ok': True,
            'encoder_stale': False, 'encoder_config_fault_latched': False,
            'encoder_feedback_age_s': 0.0,
        })))

    def spin_until(self, predicate, timeout):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            rclpy.spin_once(self, timeout_sec=0.005)
            if predicate():
                return
        raise AssertionError('process timeout: ' + str(self.guard.failure()))

    def spin_for(self, duration):
        until = time.monotonic() + duration
        self.spin_until(lambda: time.monotonic() >= until, duration + 1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--drop', choices=('raw', 'wheel'), required=True)
    args = parser.parse_args()
    directory = Path(tempfile.mkdtemp(prefix='we-hwt601-process-'))
    share = Path(get_package_share_directory('robot_state_estimation'))
    children, logs = [], []
    rclpy.init()
    node = Fixture()
    result = {'synthetic': True, 'hardware_access': False, 'drop': args.drop}
    try:
        node.spin_for(1.0)
        assert set(node.get_node_names()) == {node.get_name()}, 'DDS domain not empty'
        commands = [
            [str(Path(get_package_prefix('robot_state_estimation')) /
                 'lib/robot_state_estimation/hwt601_shadow'), '--ros-args',
             '--params-file', str(share / 'config/hwt601_shadow.yaml'),
             '-p', 'operator_stationary_confirmed:=true'],
            [str(Path(get_package_prefix('robot_localization')) /
                 'lib/robot_localization/ekf_node'), '--ros-args',
             '-r', '__node:=hwt601_mapping_ekf',
             '--params-file', str(share / 'config/ekf_hwt601_mapping.yaml'),
             '-r', 'odometry/filtered:=/odom'],
        ]
        for i, command in enumerate(commands):
            log = (directory / f'process-{i}.log').open('w')
            logs.append(log)
            children.append(subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT))
        # These are separate subscribers; consume the calibrated status on
        # both before asserting it, not whichever callback ran first.
        node.spin_until(lambda: node.guard.failure() is None
                        and node.bias_status is not None
                        and node.bias_status['bias']['calibrated'] is True, 35.0)
        assert node.bias_status['bias']['calibrated'] is True
        assert node.bias_status['bias']['adaptation_samples'] == 0
        assert abs(node.bias_status['bias']['radps_xyz'][2] - 0.01) < 1e-7
        node.v, node.w = 0.04, 0.06
        node.spin_for(2.0)
        assert node.guard.failure() is None
        measured = node.odom[-1].twist.twist
        assert abs(measured.linear.x - 0.04) < 0.005
        assert abs(measured.angular.z - 0.06) < 0.005
        owners = [p.node_name for p in node.get_publishers_info_by_topic('/odom')]
        assert owners == ['hwt601_mapping_ekf'], owners
        assert node.edges == {('odom', 'base_link')}, node.edges
        result.update(bias_calibrated=True, sole_odom_owner=owners,
                      tf_edges=sorted(node.edges), fused_v=measured.linear.x,
                      fused_w=measured.angular.z, encoder_w_excluded=-0.30)
        node.v = node.w = 0.0
        node.spin_for(1.0)
        node.drop = args.drop
        before = len(node.odom)
        node.spin_until(lambda: node.guard.failure() is not None, 1.0)
        node.spin_for(0.5)
        assert len(node.odom) > before, 'EKF must still publish for this counterexample'
        assert args.drop in node.guard.failure()
        result.update(ekf_outputs_after_loss=len(node.odom) - before,
                      blocked_reason=node.guard.failure())
        node.drop = None
        node.spin_for(0.5)
        assert node.guard.failure() is not None, 'no silent mid-mission fallback/rearm'
        result['passed'] = True
    finally:
        # Signal exact parent PIDs, never the process group.
        for child in children:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)
        exits = [child.wait(timeout=15.0) for child in children]
        for log in logs:
            log.close()
        node.destroy_node()
        rclpy.shutdown()
        result['process_exit_codes'] = exits
        result['evidence'] = str(directory)
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    assert exits == [0, 0], exits
    assert all('Traceback' not in path.read_text() for path in directory.glob('process-*.log'))


if __name__ == '__main__':
    main()
