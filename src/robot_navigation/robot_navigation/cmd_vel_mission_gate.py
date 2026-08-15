#!/usr/bin/env python3
"""Fail-closed command gate between Nav2 and the velocity smoother."""

import json
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


AUTHORIZED_PHASES = {'nav2_ziel_senden', 'fahre_zum_raum'}


def room_motion_authorized(status):
    """Return True only for an explicitly running go_to_room mission."""
    if not isinstance(status, dict):
        return False
    command = status.get('active_command')
    return (
        status.get('state') == 'running'
        and status.get('phase') in AUTHORIZED_PHASES
        and isinstance(command, dict)
        and command.get('type') == 'go_to_room'
    )


class CmdVelMissionGate(Node):
    def __init__(self):
        super().__init__('cmd_vel_mission_gate')
        self.declare_parameter('input_topic', '/cmd_vel_nav_raw')
        self.declare_parameter('output_topic', '/cmd_vel_nav')
        self.declare_parameter(
            'mission_status_topic', '/mission_manager/status_json')
        self.declare_parameter('status_timeout_s', 1.0)
        self.declare_parameter('command_timeout_s', 0.25)
        self.declare_parameter('publish_rate_hz', 20.0)

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        status_topic = self.get_parameter('mission_status_topic').value
        rate_hz = float(self.get_parameter('publish_rate_hz').value)
        if not math.isfinite(rate_hz) or rate_hz <= 0.0:
            raise ValueError('publish_rate_hz muss endlich und > 0 sein')

        self._status_timeout = float(
            self.get_parameter('status_timeout_s').value)
        self._command_timeout = float(
            self.get_parameter('command_timeout_s').value)
        if self._status_timeout <= 0.0 or self._command_timeout <= 0.0:
            raise ValueError('Gate-Timeouts muessen > 0 sein')

        self._status = None
        self._status_time = 0.0
        self._command = Twist()
        self._command_time = 0.0
        self._was_authorized = False

        self._publisher = self.create_publisher(Twist, output_topic, 10)
        self.create_subscription(Twist, input_topic, self._on_command, 10)
        self.create_subscription(String, status_topic, self._on_status, 10)
        self.create_timer(1.0 / rate_hz, self._publish)
        self.get_logger().warn(
            'Nav2-Fahrtor aktiv: Befehle nur bei laufender go_to_room-Mission.')

    def _on_command(self, message):
        values = (message.linear.x, message.linear.y, message.linear.z,
                  message.angular.x, message.angular.y, message.angular.z)
        if not all(math.isfinite(value) for value in values):
            self._command = Twist()
            self._command_time = 0.0
            self.get_logger().error('Nicht-endlicher Nav2-Befehl verworfen.')
            return
        self._command = message
        self._command_time = time.monotonic()

    def _on_status(self, message):
        try:
            status = json.loads(message.data)
        except (json.JSONDecodeError, TypeError):
            self._status = None
            self._status_time = 0.0
            self._publisher.publish(Twist())
            return
        self._status = status
        self._status_time = time.monotonic()
        if not room_motion_authorized(status):
            # Nicht erst auf den naechsten Timer-Tick warten.
            self._publisher.publish(Twist())

    def _publish(self):
        now = time.monotonic()
        authorized = (
            room_motion_authorized(self._status)
            and now - self._status_time <= self._status_timeout
        )
        command_fresh = now - self._command_time <= self._command_timeout
        self._publisher.publish(
            self._command if authorized and command_fresh else Twist())
        if authorized != self._was_authorized:
            message = 'Fahrtor FREI' if authorized else 'Fahrtor GESPERRT'
            self.get_logger().warn(message)
            self._was_authorized = authorized


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelMissionGate()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            try:
                node._publisher.publish(Twist())
            except RCLError:
                # Bei globalem SIGINT kann rclpy.ok() noch kurz True liefern,
                # obwohl der Publisher-Kontext bereits ungueltig ist.
                pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
