#!/usr/bin/env python3
# ============================================================================
#  base_hardware_node.py  -  Differentialantrieb Basis (Bus B)
#  ---------------------------------------------------------------------------
#  Zweck v1:
#    - /cmd_vel empfangen (geometry_msgs/Twist)
#    - linke/rechte Radgeschwindigkeit berechnen
#    - daraus Motor-RPM berechnen
#    - Dry-run: nur loggen und simulierte /odom publizieren
#    - RS485-Modus: Modbus-Register fuer linkes/rechtes Rad schreiben
#    - Watchdog: bei ausbleibendem /cmd_vel automatisch stoppen
#
#  Warum zuerst dry_run?
#    Ein falsches Vorzeichen, ein falscher Radabstand oder eine falsche
#    Skalierung kann echte Motoren sofort gefaehrlich bewegen. Dieser Node
#    beweist zuerst die komplette Softwarekette, ohne RS485-Kommandos zu senden.
#
#  TOPICS:
#    Eingang : /cmd_vel             (geometry_msgs/Twist)
#    Ausgang : /odom                (nav_msgs/Odometry)
#    Ausgang : /base_hardware/state_json (std_msgs/String, Diagnose fuer GUI/Log)
#
#  PARAMETER-INDEX (Defaults; echte Werte in config/base_hardware_params.yaml)
#    cmd_vel_topic / odom_topic ................ Zeile  68 / 69
#    wheel_radius / wheel_separation ........... Zeile  75 / 76
#    max_linear_speed / max_angular_speed ...... Zeile  77 / 78
#    cmd_timeout_s / update_rate_hz ............ Zeile  83 / 84
#    dry_run / allow_rs485 ..................... Zeile  89 / 90
#    RS485-Port / Baudrate / Motor-IDs ......... Zeile  95-100
#    Modbus-Register ........................... Zeile 110-118
#    publish_tf ................................ Zeile 126
# ============================================================================

import json
import math
import time
from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster

try:
    from pymodbus.client import ModbusSerialClient
except Exception:  # pragma: no cover - auf Entwicklungs-PC evtl. nicht installiert
    ModbusSerialClient = None


@dataclass
class WheelCommand:
    v_left_mps: float = 0.0
    v_right_mps: float = 0.0
    rpm_left: float = 0.0
    rpm_right: float = 0.0


class BaseHardware(Node):
    def __init__(self):
        super().__init__('base_hardware')

        # -------------------------------------------------------------------
        # ROS-Topic-Parameter
        # -------------------------------------------------------------------
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('state_topic', '/base_hardware/state_json')

        # -------------------------------------------------------------------
        # Geometrie / Limits [ANPASSEN]
        # -------------------------------------------------------------------
        self.declare_parameter('wheel_radius_m', 0.075)
        self.declare_parameter('wheel_separation_m', 0.420)
        self.declare_parameter('max_linear_speed_mps', 0.30)
        self.declare_parameter('max_angular_speed_radps', 0.80)

        # -------------------------------------------------------------------
        # Timing / Watchdog
        # -------------------------------------------------------------------
        self.declare_parameter('cmd_timeout_s', 0.25)
        self.declare_parameter('update_rate_hz', 50.0)

        # -------------------------------------------------------------------
        # Sicherheits-/Modusparameter
        # -------------------------------------------------------------------
        self.declare_parameter('dry_run', True)
        self.declare_parameter('allow_rs485', False)

        # -------------------------------------------------------------------
        # RS485-Platzhalter (werden erst in einer spaeteren Stufe genutzt)
        # -------------------------------------------------------------------
        self.declare_parameter('rs485_port', '/dev/ttyUSB_BASE')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('left_motor_id', 1)
        self.declare_parameter('right_motor_id', 2)
        self.declare_parameter('invert_left', False)
        self.declare_parameter('invert_right', True)

        # -------------------------------------------------------------------
        # Modbus-Register [ANPASSEN]
        # Defaults orientieren sich an einem einfachen Velocity-Modus:
        #   rpm_register       = Zielgeschwindigkeit in rpm (Betrag)
        #   direction_register = 0 vorwaerts / 1 rueckwaerts
        #   command_register   = Start/Stop-Kommando
        # Passe diese Werte an das Manual der NEMA23-RS485-Motoren an.
        # -------------------------------------------------------------------
        self.declare_parameter('rpm_register', 0x001D)
        self.declare_parameter('direction_register', 0x001C)
        self.declare_parameter('command_register', 0x0027)
        self.declare_parameter('velocity_start_value', 0x0002)
        self.declare_parameter('stop_value', 0x0100)
        self.declare_parameter('rpm_scale', 1.0)
        self.declare_parameter('max_motor_rpm', 120.0)
        self.declare_parameter('modbus_timeout_s', 0.05)
        self.declare_parameter('modbus_write_period_s', 0.05)

        # -------------------------------------------------------------------
        # Frames: Standardentscheidung im Projekt: EKF publiziert spaeter TF.
        # Deshalb publish_tf standardmaessig false.
        # -------------------------------------------------------------------
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('publish_tf', False)

        gp = self.get_parameter
        self.cmd_vel_topic = str(gp('cmd_vel_topic').value)
        self.odom_topic = str(gp('odom_topic').value)
        self.state_topic = str(gp('state_topic').value)
        self.wheel_radius = float(gp('wheel_radius_m').value)
        self.wheel_separation = float(gp('wheel_separation_m').value)
        self.max_linear = float(gp('max_linear_speed_mps').value)
        self.max_angular = float(gp('max_angular_speed_radps').value)
        self.cmd_timeout = float(gp('cmd_timeout_s').value)
        self.update_rate = float(gp('update_rate_hz').value)
        self.dry_run = bool(gp('dry_run').value)
        self.allow_rs485 = bool(gp('allow_rs485').value)
        self.rs485_port = str(gp('rs485_port').value)
        self.baudrate = int(gp('baudrate').value)
        self.left_motor_id = int(gp('left_motor_id').value)
        self.right_motor_id = int(gp('right_motor_id').value)
        self.invert_left = bool(gp('invert_left').value)
        self.invert_right = bool(gp('invert_right').value)
        self.rpm_register = int(gp('rpm_register').value)
        self.direction_register = int(gp('direction_register').value)
        self.command_register = int(gp('command_register').value)
        self.velocity_start_value = int(gp('velocity_start_value').value)
        self.stop_value = int(gp('stop_value').value)
        self.rpm_scale = float(gp('rpm_scale').value)
        self.max_motor_rpm = float(gp('max_motor_rpm').value)
        self.modbus_timeout_s = float(gp('modbus_timeout_s').value)
        self.modbus_write_period_s = float(gp('modbus_write_period_s').value)
        self.odom_frame_id = str(gp('odom_frame_id').value)
        self.base_frame_id = str(gp('base_frame_id').value)
        self.publish_tf = bool(gp('publish_tf').value)

        self._validate_parameters()

        # -------------------------------------------------------------------
        # Interner Zustand fuer simulierte Odometrie
        # -------------------------------------------------------------------
        self.last_cmd_time = self.get_clock().now()
        self.last_update_time = self.get_clock().now()
        self.last_log_time = 0.0
        self.cmd_v = 0.0
        self.cmd_w = 0.0
        self.active_wheel_cmd = WheelCommand()
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.modbus_client = None
        self.last_modbus_write = 0.0
        self.last_sent_left_rpm = None
        self.last_sent_right_rpm = None
        self.rs485_ready = False

        # -------------------------------------------------------------------
        # Publisher / Subscriber
        # -------------------------------------------------------------------
        self.cmd_sub = self.create_subscription(Twist, self.cmd_vel_topic, self._on_cmd_vel, 10)
        self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 10)
        self.state_pub = self.create_publisher(String, self.state_topic, 10)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None

        self.timer = self.create_timer(1.0 / self.update_rate, self._update)

        if not self.dry_run and not self.allow_rs485:
            self.get_logger().error(
                'dry_run=false, aber allow_rs485=false. RS485 bleibt blockiert. '
                'Setze allow_rs485=true erst nach aufgebocktem Radtest und Not-Aus-Pruefung.')
        elif not self.dry_run and self.allow_rs485:
            self._connect_modbus()

        self.get_logger().info(
            f'base_hardware bereit: dry_run={self.dry_run}, cmd_vel={self.cmd_vel_topic}, '
            f'wheel_radius={self.wheel_radius:.3f} m, separation={self.wheel_separation:.3f} m')

    # ======================= Parameter / Sicherheit =====================
    def _validate_parameters(self):
        if self.wheel_radius <= 0.0:
            raise ValueError('wheel_radius_m muss > 0 sein')
        if self.wheel_separation <= 0.0:
            raise ValueError('wheel_separation_m muss > 0 sein')
        if self.update_rate <= 0.0:
            raise ValueError('update_rate_hz muss > 0 sein')
        if self.cmd_timeout <= 0.0:
            raise ValueError('cmd_timeout_s muss > 0 sein')
        if self.max_motor_rpm <= 0.0:
            raise ValueError('max_motor_rpm muss > 0 sein')
        if self.modbus_write_period_s <= 0.0:
            raise ValueError('modbus_write_period_s muss > 0 sein')

    # ======================= Eingang: /cmd_vel ==========================
    def _on_cmd_vel(self, msg: Twist):
        # Nur die fuer Differentialantrieb relevanten Komponenten verwenden.
        v = self._clamp(float(msg.linear.x), -self.max_linear, self.max_linear)
        w = self._clamp(float(msg.angular.z), -self.max_angular, self.max_angular)
        self.cmd_v = v
        self.cmd_w = w
        self.last_cmd_time = self.get_clock().now()
        self.active_wheel_cmd = self._twist_to_wheels(v, w)

    # ======================= Kinematik =================================
    def _twist_to_wheels(self, v: float, w: float) -> WheelCommand:
        # Differentialantrieb:
        #   links  = v - omega * spurweite/2
        #   rechts = v + omega * spurweite/2
        v_left = v - (w * self.wheel_separation / 2.0)
        v_right = v + (w * self.wheel_separation / 2.0)

        if self.invert_left:
            v_left *= -1.0
        if self.invert_right:
            v_right *= -1.0

        circumference = 2.0 * math.pi * self.wheel_radius
        rpm_left = (v_left / circumference) * 60.0
        rpm_right = (v_right / circumference) * 60.0
        return WheelCommand(v_left, v_right, rpm_left, rpm_right)

    # ======================= Hauptupdate ===============================
    def _update(self):
        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds * 1e-9
        self.last_update_time = now
        if dt <= 0.0:
            return

        age = (now - self.last_cmd_time).nanoseconds * 1e-9
        timed_out = age > self.cmd_timeout
        if timed_out:
            v = 0.0
            w = 0.0
            self.active_wheel_cmd = WheelCommand()
        else:
            v = self.cmd_v
            w = self.cmd_w

        if not self.dry_run and self.allow_rs485:
            if timed_out:
                self._send_stop_if_needed()
            else:
                self._send_rs485_velocity(self.active_wheel_cmd)

        # Dry-run-Odometrie: wir integrieren die Sollgeschwindigkeit.
        self._integrate_odom(v, w, dt)
        self._publish_odom(now, v, w)
        self._publish_state(now, timed_out)
        self._throttled_log(timed_out)

    def _integrate_odom(self, v: float, w: float, dt: float):
        self.yaw = self._normalize_angle(self.yaw + w * dt)
        self.x += v * math.cos(self.yaw) * dt
        self.y += v * math.sin(self.yaw) * dt

    def _publish_odom(self, stamp, v: float, w: float):
        msg = Odometry()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = self.odom_frame_id
        msg.child_frame_id = self.base_frame_id
        msg.pose.pose.position.x = self.x
        msg.pose.pose.position.y = self.y
        msg.pose.pose.orientation.z = math.sin(self.yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(self.yaw / 2.0)
        msg.twist.twist.linear.x = v
        msg.twist.twist.angular.z = w
        self.odom_pub.publish(msg)

        if self.tf_broadcaster:
            tf = TransformStamped()
            tf.header = msg.header
            tf.child_frame_id = self.base_frame_id
            tf.transform.translation.x = self.x
            tf.transform.translation.y = self.y
            tf.transform.rotation = msg.pose.pose.orientation
            self.tf_broadcaster.sendTransform(tf)

    def _publish_state(self, stamp, timed_out: bool):
        payload = {
            'dry_run': self.dry_run,
            'allow_rs485': self.allow_rs485,
            'timed_out': timed_out,
            'cmd_v_mps': self.cmd_v,
            'cmd_w_radps': self.cmd_w,
            'v_left_mps': self.active_wheel_cmd.v_left_mps,
            'v_right_mps': self.active_wheel_cmd.v_right_mps,
            'rpm_left': self.active_wheel_cmd.rpm_left,
            'rpm_right': self.active_wheel_cmd.rpm_right,
            'x': self.x,
            'y': self.y,
            'yaw': self.yaw,
            'rs485_port': self.rs485_port,
            'rs485_ready': self.rs485_ready,
            'left_motor_id': self.left_motor_id,
            'right_motor_id': self.right_motor_id,
            'stamp_sec': stamp.nanoseconds * 1e-9,
        }
        self.state_pub.publish(String(data=json.dumps(payload)))

    # ======================= RS485 / Modbus ============================
    def _connect_modbus(self):
        if ModbusSerialClient is None:
            self.get_logger().error(
                'pymodbus ist nicht installiert. Installiere auf dem Jetson: pip install pymodbus')
            self.rs485_ready = False
            return

        self.modbus_client = ModbusSerialClient(
            port=self.rs485_port,
            baudrate=self.baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=self.modbus_timeout_s,
        )
        self.rs485_ready = bool(self.modbus_client.connect())
        if self.rs485_ready:
            self.get_logger().warn(
                f'RS485 AKTIV auf {self.rs485_port} @ {self.baudrate}. '
                'Raeder muessen frei drehen, Not-Aus bereithalten.')
            self._write_motor_stop(self.left_motor_id)
            self._write_motor_stop(self.right_motor_id)
        else:
            self.get_logger().error(f'RS485-Verbindung fehlgeschlagen: {self.rs485_port}')

    def _send_rs485_velocity(self, wheel_cmd: WheelCommand):
        if not self.rs485_ready:
            self._connect_modbus()
            if not self.rs485_ready:
                return

        now = time.monotonic()
        if now - self.last_modbus_write < self.modbus_write_period_s:
            return
        self.last_modbus_write = now

        left_rpm = self._clamp(wheel_cmd.rpm_left, -self.max_motor_rpm, self.max_motor_rpm)
        right_rpm = self._clamp(wheel_cmd.rpm_right, -self.max_motor_rpm, self.max_motor_rpm)
        self._write_motor_velocity(self.left_motor_id, left_rpm)
        self._write_motor_velocity(self.right_motor_id, right_rpm)
        self.last_sent_left_rpm = left_rpm
        self.last_sent_right_rpm = right_rpm

    def _send_stop_if_needed(self):
        if self.last_sent_left_rpm == 0.0 and self.last_sent_right_rpm == 0.0:
            return
        if not self.rs485_ready:
            return
        self._write_motor_stop(self.left_motor_id)
        self._write_motor_stop(self.right_motor_id)
        self.last_sent_left_rpm = 0.0
        self.last_sent_right_rpm = 0.0

    def _write_motor_velocity(self, motor_id: int, rpm: float):
        direction = 0 if rpm >= 0.0 else 1
        rpm_value = int(round(abs(rpm) * self.rpm_scale))
        rpm_value = int(self._clamp(rpm_value, 0, 65535))

        ok = True
        ok &= self._write_register(motor_id, self.direction_register, direction)
        ok &= self._write_register(motor_id, self.rpm_register, rpm_value)
        ok &= self._write_register(motor_id, self.command_register, self.velocity_start_value)
        if not ok:
            self.get_logger().error(f'Modbus-Schreiben Motor {motor_id} fehlgeschlagen')

    def _write_motor_stop(self, motor_id: int):
        self._write_register(motor_id, self.command_register, self.stop_value)

    def _write_register(self, motor_id: int, address: int, value: int) -> bool:
        if self.modbus_client is None:
            return False
        try:
            # pymodbus 3.x nutzt slave=, aeltere Versionen unit=.
            try:
                result = self.modbus_client.write_register(address=address, value=value, slave=motor_id)
            except TypeError:
                result = self.modbus_client.write_register(address=address, value=value, unit=motor_id)
            return result is not None and not result.isError()
        except Exception as exc:
            self.rs485_ready = False
            self.get_logger().error(f'Modbus-Fehler Motor {motor_id}, Reg 0x{address:04X}: {exc}')
            return False

    # ======================= Helfer ====================================
    def _throttled_log(self, timed_out: bool):
        now = time.monotonic()
        if now - self.last_log_time < 1.0:
            return
        self.last_log_time = now
        cmd = self.active_wheel_cmd
        mode = 'TIMEOUT-STOP' if timed_out else 'CMD'
        self.get_logger().info(
            f'{mode}: v={self.cmd_v:+.3f} m/s w={self.cmd_w:+.3f} rad/s | '
            f'L={cmd.rpm_left:+.1f} rpm R={cmd.rpm_right:+.1f} rpm')

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def destroy_node(self):
        try:
            if self.rs485_ready:
                self._write_motor_stop(self.left_motor_id)
                self._write_motor_stop(self.right_motor_id)
            if self.modbus_client is not None:
                self.modbus_client.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = BaseHardware()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
