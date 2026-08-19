#!/usr/bin/env python3
"""Begrenzte, beaufsichtigte AMCL-Suche ueber die Sicherheitskette."""

import argparse
import json
import math
import os
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Bool, String
from std_srvs.srv import Empty


ANGULAR_SPEED = 0.15
LINEAR_SPEED = 0.04
MOTION_TIMEOUT = 100.0
FORWARD_COMPLETION_TOLERANCE_M = 0.01
NOMOTION_UPDATE_INTERVAL_S = 0.45


def yaw_from_odom(message):
    q = message.pose.pose.orientation
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class LocalizationTurn(Node):
    def __init__(self):
        super().__init__('amcl_lokalisierungsdrehung')
        # Das Missions-Gate begrenzt diese Ausnahme auf langsame Drehung und
        # Vorwaertsfahrt; danach folgen velocity_smoother und
        # collision_monitor.
        self.publisher = self.create_publisher(
            Twist, '/cmd_vel_localization_raw', 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 20)
        self.create_subscription(
            String, '/base_hardware/state_json', self.on_base, 10)
        self.create_subscription(
            String, '/localization/status_json', self.on_localization, 10)
        self.create_subscription(Bool, '/localization/ready', self.on_ready, 10)
        self.nomotion_client = self.create_client(
            Empty, '/request_nomotion_update')
        self.yaw = None
        self.position = None
        self.base = None
        self.localization = None
        self.ready = False
        self.base_received = 0.0

    def on_odom(self, message):
        self.yaw = yaw_from_odom(message)
        self.position = (
            message.pose.pose.position.x, message.pose.pose.position.y)

    def on_base(self, message):
        try:
            self.base = json.loads(message.data)
            self.base_received = time.monotonic()
        except (TypeError, ValueError):
            self.base = None

    def on_localization(self, message):
        try:
            self.localization = json.loads(message.data)
        except (TypeError, ValueError):
            self.localization = None

    def on_ready(self, message):
        self.ready = bool(message.data)

    def base_is_safe(self):
        state = self.base or {}
        return (
            state.get('dry_run') is False
            and state.get('allow_rs485') is True
            and state.get('rs485_ready') is True
            and state.get('encoder_initialized') is True
            and state.get('encoder_feedback_ok') is True
            and abs(float(state.get('motor_rpm_left') or 0.0)) <= 1.0
            and abs(float(state.get('motor_rpm_right') or 0.0)) <= 1.0
        )

    def feedback_is_healthy(self):
        state = self.base or {}
        return (
            time.monotonic() - self.base_received <= 1.0
            and state.get('rs485_ready') is True
            and state.get('encoder_feedback_ok') is True
            and state.get('encoder_config_fault_latched') is False
        )

    def publish_for(self, command, seconds):
        end = time.monotonic() + seconds
        while rclpy.ok() and time.monotonic() < end:
            self.publisher.publish(command)
            rclpy.spin_once(self, timeout_sec=0.05)


def wait_for_preflight(node):
    end = time.monotonic() + 20.0
    while rclpy.ok() and time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.yaw is not None and node.localization and node.base_is_safe():
            return True
    return False


def print_localization(node):
    status = node.localization or {}
    covariance = status.get('covariance') or {}
    print(
        f"Lokalisierung: ready={status.get('ready')}, "
        f"x/y={covariance.get('x_stddev_m')}/"
        f"{covariance.get('y_stddev_m')} m, "
        f"yaw={covariance.get('yaw_stddev_deg')} Grad, "
        f"Gruende={status.get('reasons')}",
        flush=True)


def observe(node, seconds):
    end = time.monotonic() + seconds
    while rclpy.ok() and time.monotonic() < end and not node.ready:
        rclpy.spin_once(node, timeout_sec=0.1)


def turn(node, target_degrees):
    command = Twist()
    command.angular.z = ANGULAR_SPEED
    last_yaw = node.yaw
    turned = 0.0
    start = time.monotonic()
    progress_time = start
    progress_angle = 0.0
    target_angle = math.radians(target_degrees)
    while (rclpy.ok() and turned < target_angle
           and time.monotonic() - start < MOTION_TIMEOUT):
        node.publisher.publish(command)
        rclpy.spin_once(node, timeout_sec=0.05)
        if not node.feedback_is_healthy():
            print('ABBRUCH: Encoder-/RS485-Rueckmeldung verloren.', flush=True)
            return None
        delta = node.yaw - last_yaw
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        if abs(delta) < 0.2:
            turned += abs(delta)
            last_yaw = node.yaw
        if node.ready:
            print('AMCL-Freigabe erreicht; Suche wird beendet.', flush=True)
            break
        if time.monotonic() - progress_time >= 12.0:
            if turned - progress_angle < math.radians(10.0):
                print(
                    'ABBRUCH: Drehung wird blockiert oder bewegt sich nicht; '
                    f'bislang {math.degrees(turned):.1f} Grad.', flush=True)
                return None
            progress_time = time.monotonic()
            progress_angle = turned
    print(f'Begrenzte Drehung: {math.degrees(turned):.1f} Grad', flush=True)
    return turned


def move_forward(node, target_meters):
    command = Twist()
    command.linear.x = LINEAR_SPEED
    start_position = node.position
    start = time.monotonic()
    progress_time = start
    progress_distance = 0.0
    distance = 0.0
    while (rclpy.ok() and distance < target_meters
           and time.monotonic() - start < 30.0):
        node.publisher.publish(command)
        rclpy.spin_once(node, timeout_sec=0.05)
        if not node.feedback_is_healthy():
            print('ABBRUCH: Encoder-/RS485-Rueckmeldung verloren.', flush=True)
            return None
        distance = math.dist(start_position, node.position)
        if node.ready:
            print('AMCL-Freigabe erreicht; Suche wird beendet.', flush=True)
            break
        if time.monotonic() - progress_time >= 10.0:
            if distance - progress_distance < 0.03:
                if distance >= (
                        target_meters - FORWARD_COMPLETION_TOLERANCE_M):
                    print(
                        'Vorwaertsziel innerhalb der 1-cm-Toleranz erreicht: '
                        f'{distance:.3f} m.', flush=True)
                    return distance
                print(
                    'ABBRUCH: Vorwaertsfahrt wird blockiert oder bewegt sich '
                    f'nicht; bislang {distance:.3f} m.', flush=True)
                return None
            progress_time = time.monotonic()
            progress_distance = distance
    if (not node.ready
            and distance < target_meters - FORWARD_COMPLETION_TOLERANCE_M):
        print(
            'ABBRUCH: Vorwaertsziel vor Ablauf der Zeit nicht erreicht; '
            f'bislang {distance:.3f} m.', flush=True)
        return None
    print(f'Begrenzte Vorwaertsfahrt: {distance:.3f} m', flush=True)
    return distance


def request_nomotion_updates(node, maximum_updates):
    """Verarbeite im sicheren Stillstand weitere Scans bis zur Freigabe."""
    if maximum_updates <= 0 or node.ready:
        return True
    if not node.nomotion_client.wait_for_service(timeout_sec=5.0):
        print(
            'ABBRUCH: AMCL-Dienst /request_nomotion_update fehlt.',
            flush=True)
        return False
    print(
        'Stationaere AMCL-Nachmessung: bis zu '
        f'{maximum_updates} Updates.', flush=True)
    for number in range(1, maximum_updates + 1):
        future = node.nomotion_client.call_async(Empty.Request())
        response_deadline = time.monotonic() + 2.0
        while (rclpy.ok() and not future.done()
               and time.monotonic() < response_deadline):
            rclpy.spin_once(node, timeout_sec=0.05)
        if not future.done() or future.result() is None:
            print(
                'ABBRUCH: Keine Antwort auf stationaeres AMCL-Update '
                f'{number}.', flush=True)
            return False
        observation_deadline = time.monotonic() + NOMOTION_UPDATE_INTERVAL_S
        while (rclpy.ok() and not node.ready
               and time.monotonic() < observation_deadline):
            rclpy.spin_once(node, timeout_sec=0.05)
        if node.ready:
            print(
                'AMCL-Freigabe nach stationaerem Update '
                f'{number}/{maximum_updates} erreicht.', flush=True)
            return True
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--degrees', type=float, default=360.0,
        help='Erster begrenzter Drehwinkel, 30..360 Grad (Default: 360).')
    parser.add_argument(
        '--forward-meters', type=float, default=0.0,
        help='Danach 0..0.30 m gerade vorwaerts (Default: 0).')
    parser.add_argument(
        '--after-degrees', type=float, default=0.0,
        help='Danach weitere 0 oder 30..360 Grad drehen (Default: 0).')
    parser.add_argument(
        '--nomotion-updates', type=int, default=20,
        help='Zum Abschluss 0..50 stationaere AMCL-Updates (Default: 20).')
    args = parser.parse_args()
    if not math.isfinite(args.degrees) or not 30.0 <= args.degrees <= 360.0:
        parser.error('--degrees muss endlich und zwischen 30 und 360 liegen.')
    if (not math.isfinite(args.forward_meters)
            or not 0.0 <= args.forward_meters <= 0.30):
        parser.error('--forward-meters muss zwischen 0 und 0.30 liegen.')
    if (not math.isfinite(args.after_degrees)
            or not (args.after_degrees == 0.0
                    or 30.0 <= args.after_degrees <= 360.0)):
        parser.error('--after-degrees muss 0 oder 30..360 sein.')
    if not 0 <= args.nomotion_updates <= 50:
        parser.error('--nomotion-updates muss zwischen 0 und 50 liegen.')
    if os.environ.get('AMADEUS_FAHRFREIGABE') != 'JA':
        print('ABBRUCH: AMADEUS_FAHRFREIGABE=JA fehlt.', flush=True)
        return 1
    rclpy.init()
    node = LocalizationTurn()
    stop = Twist()
    try:
        if not wait_for_preflight(node):
            print('ABBRUCH: scharfe Basis, Encoder oder Status nicht bereit.')
            print(f'Basisstatus: {node.base}', flush=True)
            return 1
        print('Preflight bestanden: Encoder/RS485 bereit, Motoren bei 0 rpm.')
        print_localization(node)

        if turn(node, args.degrees) is None:
            return 1
        node.publish_for(stop, 2.0)
        observe(node, 3.0)
        if not node.ready and args.forward_meters > 0.0:
            if move_forward(node, args.forward_meters) is None:
                return 1
            node.publish_for(stop, 2.0)
            observe(node, 3.0)
        if not node.ready and args.after_degrees > 0.0:
            if turn(node, args.after_degrees) is None:
                return 1
            node.publish_for(stop, 2.0)
        # AMCL verarbeitet neue Scans normalerweise erst nach einer
        # Odometrieaenderung. Die standardisierte No-motion-Anforderung nutzt
        # den nun garantierten Stillstand, um die nach der Suchbewegung noch
        # vorhandenen Winkelhypothesen ohne weitere Fahrt zu trennen.
        node.publish_for(stop, 2.0)
        if not request_nomotion_updates(node, args.nomotion_updates):
            return 1
        observe(node, 3.0)
        print_localization(node)
        return 0 if node.ready else 2
    finally:
        node.publish_for(stop, 2.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
