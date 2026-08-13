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
from typing import Any

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from tf2_ros import TransformBroadcaster

from .encoder_odometry import (
    EncoderOdometry,
    EncoderUpdate,
    MotorFeedback,
    decode_i16,
    decode_position_words,
    u32_to_i32,
)

ModbusSerialClient: Any
try:
    from pymodbus.client import ModbusSerialClient as _ModbusSerialClient
except Exception:  # pragma: no cover - auf Entwicklungs-PC evtl. nicht installiert
    ModbusSerialClient = None
else:
    ModbusSerialClient = _ModbusSerialClient


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
        self.declare_parameter('wheel_radius_m', 0.0625)
        self.declare_parameter('wheel_separation_m', 0.378)
        # Getriebe: Motorumdrehungen je RAD-Umdrehung (z.B. 10:1 -> 10.0).
        self.declare_parameter('gear_ratio', 10.0)
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
        self.declare_parameter('modbus_retries', 0)
        self.declare_parameter('modbus_write_period_s', 0.05)

        # -------------------------------------------------------------------
        # Anfahr- und Bremsrampe (0x001E / 0x001F, Angabe in Millisekunden).
        # Wurden bis 28.07.2026 nie gesetzt -> Werksrampe -> der Roboter nickte
        # beim Anfahren. Das verfaelscht die Karte, weil die Kamera auf 1.34 m
        # sitzt: 2 Grad Nicken = rund 10 cm Bodenversatz auf 3 m Entfernung.
        # Groesser = sanfter.
        # -------------------------------------------------------------------
        self.declare_parameter('accel_register', 0x001E)
        self.declare_parameter('decel_register', 0x001F)
        self.declare_parameter('accel_ms', 800)
        self.declare_parameter('decel_ms', 800)
        # Startgeschwindigkeit: die Drehzahl, mit der der Antrieb SOFORT einsetzt,
        # bevor die Rampe ueberhaupt greift. Stand auf 30 rpm (aus dem
        # Richtungstest vom 24.07.2026 uebriggeblieben) - bei Fahrdrehzahlen um
        # 46 rpm sprang der Motor damit auf 65 % der Zielgeschwindigkeit. Das war
        # der eigentliche Ruck beim Anfahren und Anhalten, nicht die Rampe.
        self.declare_parameter('start_speed_register', 0x0020)
        self.declare_parameter('start_speed_rpm', 5)

        # -------------------------------------------------------------------
        # Drehzahl-Rueckmeldung (GEMESSENE Odometrie statt Sollwert-Integration)
        #   speed_register  = 0x000C, Ist-Drehzahl (read-only, signed int16)
        #   Gelesen wird per FC03 (read_holding_registers); FC04 antwortet NICHT.
        #   Eigene, langsamere Periode: ein Read kostet je nach FTDI-
        #   latency_timer 1-16 ms, das soll den 50-Hz-Schreibtakt nicht bremsen.
        # -------------------------------------------------------------------
        self.declare_parameter('use_speed_feedback', True)
        self.declare_parameter('speed_register', 0x000C)
        self.declare_parameter('feedback_period_s', 0.1)

        # Absolute Position statt Momentaufnahme der Drehzahl. Counts=0 sperrt
        # den Produktionsmodus, bis die Einheit am echten Motor bestimmt ist.
        self.declare_parameter('odometry_source', 'encoder_position')
        self.declare_parameter('encoder_position_register', 0x000A)
        self.declare_parameter('encoder_segment_register', 0x0011)
        self.declare_parameter('encoder_word_order_register', 0x0019)
        self.declare_parameter('encoder_resolution_register', 0x0101)
        self.declare_parameter('encoder_counts_per_motor_revolution', 0.0)
        self.declare_parameter('encoder_expected_segment', 0)
        self.declare_parameter('encoder_expected_resolution', 0)
        self.declare_parameter('encoder_feedback_period_s', 0.05)
        self.declare_parameter('encoder_stale_timeout_s', 0.30)
        self.declare_parameter('encoder_max_recovery_gap_s', 2.0)
        self.declare_parameter('encoder_max_delta_factor', 1.5)
        self.declare_parameter('encoder_failure_stop_count', 5)

        # -------------------------------------------------------------------
        # Frames: Standardentscheidung im Projekt: EKF publiziert spaeter TF.
        # Deshalb publish_tf standardmaessig false.
        # -------------------------------------------------------------------
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('publish_tf', False)
        self.declare_parameter('odom_pose_xy_variance', 0.0025)
        self.declare_parameter('odom_yaw_variance', 0.0076)
        self.declare_parameter('odom_twist_linear_variance', 0.01)
        self.declare_parameter('odom_twist_angular_variance', 0.03)

        gp = self.get_parameter
        self.cmd_vel_topic = str(gp('cmd_vel_topic').value)
        self.odom_topic = str(gp('odom_topic').value)
        self.state_topic = str(gp('state_topic').value)
        self.wheel_radius = float(gp('wheel_radius_m').value)
        self.wheel_separation = float(gp('wheel_separation_m').value)
        self.gear_ratio = float(gp('gear_ratio').value)
        self.max_linear = float(gp('max_linear_speed_mps').value)
        self.max_angular = float(gp('max_angular_speed_radps').value)
        self.cmd_timeout = float(gp('cmd_timeout_s').value)
        self.update_rate = float(gp('update_rate_hz').value)
        self.dry_run = bool(gp('dry_run').value)
        self.allow_rs485 = bool(gp('allow_rs485').value)
        self.use_sim_time = bool(gp('use_sim_time').value)
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
        self.modbus_retries = int(gp('modbus_retries').value)
        self.modbus_write_period_s = float(gp('modbus_write_period_s').value)
        self.accel_register = int(gp('accel_register').value)
        self.decel_register = int(gp('decel_register').value)
        self.accel_ms = int(gp('accel_ms').value)
        self.decel_ms = int(gp('decel_ms').value)
        self.start_speed_register = int(gp('start_speed_register').value)
        self.start_speed_rpm = int(gp('start_speed_rpm').value)
        self.use_speed_feedback = bool(gp('use_speed_feedback').value)
        self.speed_register = int(gp('speed_register').value)
        self.feedback_period_s = float(gp('feedback_period_s').value)
        self.odometry_source = str(gp('odometry_source').value).strip().lower()
        self.encoder_position_register = int(gp('encoder_position_register').value)
        self.encoder_segment_register = int(gp('encoder_segment_register').value)
        self.encoder_word_order_register = int(gp('encoder_word_order_register').value)
        self.encoder_resolution_register = int(gp('encoder_resolution_register').value)
        self.encoder_counts_per_motor_revolution = float(
            gp('encoder_counts_per_motor_revolution').value)
        self.encoder_expected_segment = int(gp('encoder_expected_segment').value)
        self.encoder_expected_resolution = int(
            gp('encoder_expected_resolution').value)
        self.encoder_feedback_period_s = float(gp('encoder_feedback_period_s').value)
        self.encoder_stale_timeout_s = float(gp('encoder_stale_timeout_s').value)
        self.encoder_max_recovery_gap_s = float(gp('encoder_max_recovery_gap_s').value)
        self.encoder_max_delta_factor = float(gp('encoder_max_delta_factor').value)
        self.encoder_failure_stop_count = int(gp('encoder_failure_stop_count').value)
        self.odom_frame_id = str(gp('odom_frame_id').value)
        self.base_frame_id = str(gp('base_frame_id').value)
        self.publish_tf = bool(gp('publish_tf').value)
        self.odom_pose_xy_variance = float(gp('odom_pose_xy_variance').value)
        self.odom_yaw_variance = float(gp('odom_yaw_variance').value)
        self.odom_twist_linear_variance = float(
            gp('odom_twist_linear_variance').value)
        self.odom_twist_angular_variance = float(
            gp('odom_twist_angular_variance').value)

        self._validate_parameters()

        # -------------------------------------------------------------------
        # Interner Zustand fuer simulierte Odometrie
        # -------------------------------------------------------------------
        self.last_cmd_time = self.get_clock().now()
        self.last_cmd_monotonic = time.monotonic()
        self.last_update_time = self.get_clock().now()
        self.last_log_time = 0.0
        self.cmd_v = 0.0
        self.cmd_w = 0.0
        self.active_wheel_cmd = WheelCommand()
        self.invalid_cmd_count = 0
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.modbus_client = None
        self.last_modbus_write = 0.0
        self.last_sent_left_rpm = None
        self.last_sent_right_rpm = None
        self.rs485_ready = False
        # Gemessene Rueckmeldung (None = noch keine gueltige Messung)
        self.last_feedback_read = 0.0
        self.last_reconnect_try = 0.0
        self.reconnect_period_s = 2.0
        self.modbus_read_failures = 0
        self.meas_motor_rpm_left = None
        self.meas_motor_rpm_right = None
        self.meas_v = None
        self.meas_w = None
        self.feedback_ok = False
        self.encoder_tracker = None
        if (self.odometry_source == 'encoder_position' and
                self.encoder_counts_per_motor_revolution > 0.0):
            self.encoder_tracker = EncoderOdometry(
                wheel_radius_m=self.wheel_radius,
                wheel_separation_m=self.wheel_separation,
                gear_ratio=self.gear_ratio,
                counts_per_motor_revolution=self.encoder_counts_per_motor_revolution,
                invert_left=self.invert_left,
                invert_right=self.invert_right,
                max_motor_rpm=self.max_motor_rpm,
                max_delta_factor=self.encoder_max_delta_factor,
                max_recovery_gap_s=self.encoder_max_recovery_gap_s,
            )
        self.encoder_last_poll = 0.0
        self.encoder_last_success = None
        self.encoder_feedback_ok = False
        self.encoder_consecutive_failures = 0
        self.encoder_last_failure_reason = 'noch_keine_probe'
        self.encoder_last_update = EncoderUpdate(False, False, 'noch_keine_probe')
        self.encoder_left_feedback = None
        self.encoder_right_feedback = None
        self.encoder_left_high_word_first = None
        self.encoder_right_high_word_first = None
        self.encoder_segment_left = None
        self.encoder_segment_right = None
        self.encoder_resolution_left = None
        self.encoder_resolution_right = None
        self.encoder_poll_left_first = True
        self.encoder_connection_initialized = False
        self.encoder_new_measurement = False
        self.encoder_config_fault_latched = False

        # -------------------------------------------------------------------
        # Publisher / Subscriber
        # -------------------------------------------------------------------
        self.cmd_sub = self.create_subscription(
            Twist, self.cmd_vel_topic, self._on_cmd_vel, 1)
        self.odom_pub = self.create_publisher(Odometry, self.odom_topic, 10)
        self.state_pub = self.create_publisher(String, self.state_topic, 10)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_tf else None

        self._parameter_callback = self.add_on_set_parameters_callback(
            self._guard_runtime_parameters)
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
        positive_finite = {
            'wheel_radius_m': self.wheel_radius,
            'wheel_separation_m': self.wheel_separation,
            'gear_ratio': self.gear_ratio,
            'max_linear_speed_mps': self.max_linear,
            'max_angular_speed_radps': self.max_angular,
            'update_rate_hz': self.update_rate,
            'cmd_timeout_s': self.cmd_timeout,
            'rpm_scale': self.rpm_scale,
            'max_motor_rpm': self.max_motor_rpm,
            'modbus_timeout_s': self.modbus_timeout_s,
            'modbus_write_period_s': self.modbus_write_period_s,
            'feedback_period_s': self.feedback_period_s,
            'encoder_feedback_period_s': self.encoder_feedback_period_s,
            'encoder_stale_timeout_s': self.encoder_stale_timeout_s,
            'encoder_max_recovery_gap_s': self.encoder_max_recovery_gap_s,
            'encoder_max_delta_factor': self.encoder_max_delta_factor,
            'odom_pose_xy_variance': self.odom_pose_xy_variance,
            'odom_yaw_variance': self.odom_yaw_variance,
            'odom_twist_linear_variance': self.odom_twist_linear_variance,
            'odom_twist_angular_variance': self.odom_twist_angular_variance,
        }
        for name, value in positive_finite.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{name} muss endlich und > 0 sein')
        if self.modbus_retries < 0:
            raise ValueError('modbus_retries muss >= 0 sein')
        if not 1 <= self.left_motor_id <= 247 or not 1 <= self.right_motor_id <= 247:
            raise ValueError('Motor-IDs muessen im Modbus-Bereich 1..247 liegen')
        if self.left_motor_id == self.right_motor_id:
            raise ValueError('left_motor_id und right_motor_id muessen verschieden sein')
        for name, value in (
                ('rpm_register', self.rpm_register),
                ('command_register', self.command_register),
                ('speed_register', self.speed_register),
                ('encoder_position_register', self.encoder_position_register),
                ('encoder_segment_register', self.encoder_segment_register),
                ('encoder_word_order_register', self.encoder_word_order_register),
                ('encoder_resolution_register', self.encoder_resolution_register)):
            if not 0 <= value <= 0xFFFF:
                raise ValueError(f'{name} muss ein uint16-Register sein')
        if self.odometry_source not in ('encoder_position', 'speed'):
            raise ValueError('odometry_source muss encoder_position oder speed sein')
        if self.encoder_failure_stop_count < 1:
            raise ValueError('encoder_failure_stop_count muss >= 1 sein')
        if self.encoder_expected_segment < 0 or self.encoder_expected_resolution < 0:
            raise ValueError('Erwartete Encoderregister muessen >= 0 sein')
        if (not math.isfinite(self.encoder_counts_per_motor_revolution) or
                self.encoder_counts_per_motor_revolution < 0.0):
            raise ValueError(
                'encoder_counts_per_motor_revolution muss endlich und >= 0 sein')
        if not self.dry_run and self.allow_rs485 and self.use_sim_time:
            raise ValueError(
                'use_sim_time=true ist fuer scharfe Motorsteuerung verboten; '
                'der Watchdog braucht eine laufende Echtzeituhr.')
        if not self.dry_run and self.odometry_source == 'encoder_position':
            if self.encoder_counts_per_motor_revolution <= 0.0:
                raise ValueError(
                    'encoder_counts_per_motor_revolution ist unbekannt (0). '
                    'Zuerst encoder_position_pruefen.py read-only ausfuehren.')
            if (self.encoder_expected_segment <= 0 or
                    self.encoder_expected_resolution <= 0):
                raise ValueError(
                    'encoder_expected_segment und encoder_expected_resolution '
                    'muessen nach H2 auf die read-only ausgelesenen Werte gesetzt sein.')

    def _guard_runtime_parameters(self, parameters):
        if not self.dry_run and self.allow_rs485:
            for parameter in parameters:
                if parameter.name == 'use_sim_time' and bool(parameter.value):
                    return SetParametersResult(
                        successful=False,
                        reason='use_sim_time ist bei scharfer Motorsteuerung gesperrt')
        return SetParametersResult(successful=True)

    # ======================= Eingang: /cmd_vel ==========================
    def _on_cmd_vel(self, msg: Twist):
        # NaN/Inf duerfen niemals durch min/max zu Vollgeschwindigkeit werden.
        raw_v = float(msg.linear.x)
        raw_w = float(msg.angular.z)
        if not math.isfinite(raw_v) or not math.isfinite(raw_w):
            self.invalid_cmd_count += 1
            self.cmd_v = 0.0
            self.cmd_w = 0.0
            self.active_wheel_cmd = WheelCommand()
            self.last_cmd_time = self.get_clock().now()
            self.last_cmd_monotonic = time.monotonic()
            self.get_logger().error('Nicht-endlicher /cmd_vel verworfen; Stop angefordert')
            return
        v = self._clamp(raw_v, -self.max_linear, self.max_linear)
        w = self._clamp(raw_w, -self.max_angular, self.max_angular)
        self.cmd_v = v
        self.cmd_w = w
        self.last_cmd_time = self.get_clock().now()
        self.last_cmd_monotonic = time.monotonic()
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
        # Watchdog zuerst und ausschliesslich gegen monotone Echtzeit. Ein
        # stehender/rueckwaerts springender ROS-Clock darf den Motor-Stopp
        # niemals ueberspringen.
        timed_out = self._command_timed_out()
        if timed_out and not self.dry_run and self.allow_rs485:
            self.active_wheel_cmd = WheelCommand()
            self._send_stop_if_needed()

        now = self.get_clock().now()
        dt = (now - self.last_update_time).nanoseconds * 1e-9
        self.last_update_time = now
        if dt <= 0.0:
            return
        if timed_out:
            v = 0.0
            w = 0.0
            self.active_wheel_cmd = WheelCommand()
        else:
            v = self.cmd_v
            w = self.cmd_w

        if not self.dry_run and self.allow_rs485:
            motion_requested = (
                self._quantize_motor_rpm(
                    self.active_wheel_cmd.rpm_left * self.gear_ratio) != 0 or
                self._quantize_motor_rpm(
                    self.active_wheel_cmd.rpm_right * self.gear_ratio) != 0)
            # Ein Nullbefehl ist ein Stop-Ereignis und darf nicht hinter einem
            # potenziell blockierenden Feedback-Read warten.
            if not motion_requested:
                self._send_stop_if_needed()
            self._ensure_rs485()
            encoder_ready = True
            if (self.odometry_source == "encoder_position" and
                    self.rs485_ready and not self.encoder_connection_initialized):
                encoder_ready = self._initialize_encoder_feedback()
            if self.odometry_source == "encoder_position":
                if encoder_ready:
                    self._poll_encoder_feedback()
                motion_allowed = self._encoder_motion_allowed()
            else:
                self._poll_speed_feedback()
                motion_allowed = self.feedback_ok
            # Reconnect, Konfigurations- und Feedbackzugriffe koennen den
            # Single-Thread-Executor laenger als cmd_timeout blockieren. Den
            # Fahrbefehl deshalb direkt vor einem Start erneut altern lassen.
            if self._command_timed_out():
                timed_out = True
                self.active_wheel_cmd = WheelCommand()
            if timed_out or not motion_allowed or not motion_requested:
                self._send_stop_if_needed()
            else:
                self._send_rs485_velocity(self.active_wheel_cmd)

        publish_odom = True
        if self.dry_run:
            odom_v, odom_w = v, w
            self._integrate_odom(odom_v, odom_w, dt)
        elif self.odometry_source == "encoder_position":
            # Eine neue /odom-Messung nur zu einem neuen gueltigen Encoderpaar.
            # Keine identische Pose mit neuem Zeitstempel und altem Twist.
            odom_v, odom_w = self._encoder_twist()
            publish_odom = self.encoder_new_measurement
            self.encoder_new_measurement = False
        elif self.feedback_ok and self.meas_v is not None:
            odom_v, odom_w = self.meas_v, self.meas_w
            self._integrate_odom(odom_v, odom_w, dt)
        else:
            # Im realen Betrieb niemals eine nicht gemessene Sollbewegung erfinden.
            odom_v, odom_w = 0.0, 0.0

        if publish_odom:
            self._publish_odom(now, odom_v, odom_w)
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
        # Encoder erfassen keinen Schlupf und keine Seitwaertsbewegung. Null
        # wuerde in ROS faelschlich perfekte Sicherheit bedeuten.
        msg.pose.covariance[0] = self.odom_pose_xy_variance
        msg.pose.covariance[7] = self.odom_pose_xy_variance
        msg.pose.covariance[14] = 1e6
        msg.pose.covariance[21] = 1e6
        msg.pose.covariance[28] = 1e6
        msg.pose.covariance[35] = self.odom_yaw_variance
        msg.twist.covariance[0] = self.odom_twist_linear_variance
        msg.twist.covariance[7] = 1e6
        msg.twist.covariance[14] = 1e6
        msg.twist.covariance[21] = 1e6
        msg.twist.covariance[28] = 1e6
        msg.twist.covariance[35] = self.odom_twist_angular_variance
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
            'invalid_cmd_count': self.invalid_cmd_count,
            'v_left_mps': self.active_wheel_cmd.v_left_mps,
            'v_right_mps': self.active_wheel_cmd.v_right_mps,
            'rpm_left': self.active_wheel_cmd.rpm_left,        # Rad-Drehzahl
            'rpm_right': self.active_wheel_cmd.rpm_right,
            'motor_rpm_left': self.active_wheel_cmd.rpm_left * self.gear_ratio,
            'motor_rpm_right': self.active_wheel_cmd.rpm_right * self.gear_ratio,
            'gear_ratio': self.gear_ratio,
            'x': self.x,
            'y': self.y,
            'yaw': self.yaw,
            'odometry_source': self.odometry_source,
            'encoder_initialized': bool(self.encoder_tracker and self.encoder_tracker.initialized),
            'encoder_feedback_ok': self.encoder_feedback_ok,
            'encoder_stale': self._encoder_is_stale(),
            'encoder_feedback_age_s': self._encoder_feedback_age(),
            'encoder_counts_per_motor_revolution': self.encoder_counts_per_motor_revolution,
            'encoder_expected_segment': self.encoder_expected_segment,
            'encoder_expected_resolution': self.encoder_expected_resolution,
            'encoder_connection_initialized': self.encoder_connection_initialized,
            'encoder_config_fault_latched': self.encoder_config_fault_latched,
            'encoder_position_left_u32': (self.encoder_left_feedback.position_u32
                                          if self.encoder_left_feedback else None),
            'encoder_position_right_u32': (self.encoder_right_feedback.position_u32
                                           if self.encoder_right_feedback else None),
            'encoder_position_left_i32': (u32_to_i32(self.encoder_left_feedback.position_u32)
                                          if self.encoder_left_feedback else None),
            'encoder_position_right_i32': (u32_to_i32(self.encoder_right_feedback.position_u32)
                                           if self.encoder_right_feedback else None),
            'encoder_delta_left': self.encoder_last_update.left_delta_counts,
            'encoder_delta_right': self.encoder_last_update.right_delta_counts,
            'encoder_sample_dt_s': self.encoder_last_update.sample_dt_s,
            'encoder_last_reason': self.encoder_last_failure_reason,
            'encoder_consecutive_failures': self.encoder_consecutive_failures,
            'modbus_read_failures': self.modbus_read_failures,
            'encoder_rejected_updates': (self.encoder_tracker.rejected_update_count
                                         if self.encoder_tracker else 0),
            'encoder_rebases': (self.encoder_tracker.rebase_count
                                if self.encoder_tracker else 0),
            'encoder_word_order_left': self.encoder_left_high_word_first,
            'encoder_word_order_right': self.encoder_right_high_word_first,
            'encoder_segment_left': self.encoder_segment_left,
            'encoder_segment_right': self.encoder_segment_right,
            'encoder_resolution_left': self.encoder_resolution_left,
            'encoder_resolution_right': self.encoder_resolution_right,
            # GEMESSENE Rueckmeldung (None = keine gueltige Messung)
            'feedback_ok': self.feedback_ok,
            'meas_motor_rpm_left': self.meas_motor_rpm_left,
            'meas_motor_rpm_right': self.meas_motor_rpm_right,
            'meas_v_mps': self.meas_v,
            'meas_w_radps': self.meas_w,
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
            self._mark_bus_fault('pymodbus_fehlt')
            return

        if self.modbus_client is not None:
            try:
                self.modbus_client.close()
            except Exception as exc:
                self.get_logger().warn(f'Alten RS485-Client schliessen fehlgeschlagen: {exc}')
            self.modbus_client = None

        # Jeder neue Client ist eine neue Zaehler-Epoche. Der Motorcontroller
        # koennte zwischenzeitlich neu gestartet und sein Zaehler auf null
        # gesetzt worden sein. Deshalb niemals eine alte Baseline ueber einen
        # echten Reconnect hinweg verwenden.
        self._prepare_encoder_reconnect()
        client = None
        try:
            client = ModbusSerialClient(
                port=self.rs485_port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=self.modbus_timeout_s,
                retries=self.modbus_retries,
            )
            if not client.connect():
                client.close()
                self._mark_bus_fault('rs485_connect_fehlgeschlagen')
                self.get_logger().error(
                    f'RS485-Verbindung fehlgeschlagen: {self.rs485_port}')
                return
            self.modbus_client = client
            self.rs485_ready = True
        except Exception as exc:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            self._mark_bus_fault('rs485_connect_exception')
            self.get_logger().error(
                f'RS485-Verbindungsaufbau fehlgeschlagen: {exc}')
            return

        self.get_logger().warn(
            f'RS485 verbunden auf {self.rs485_port} @ {self.baudrate}; '
            'Fahrfreigabe erst nach bestaetigtem Stop, Rampen und Feedback.')
        if not self._stop_both_motors(force=True):
            return
        if not self._write_ramps():
            self._mark_bus_fault('rampen_nicht_bestaetigt')
            return
        if self.odometry_source == 'encoder_position':
            self.encoder_connection_initialized = self._initialize_encoder_feedback()
            if not self.encoder_connection_initialized:
                if not self.encoder_config_fault_latched:
                    self._mark_bus_fault('encoder_initialisierung_fehlgeschlagen')
                return
        self.get_logger().warn(
            'RS485 Initialisierung vollstaendig bestaetigt. '
            'Raeder muessen frei drehen, Not-Aus bereithalten.')

    def _prepare_encoder_reconnect(self):
        if self.encoder_tracker is not None:
            self.encoder_tracker.reset_baseline()
        self.encoder_connection_initialized = False
        self.encoder_new_measurement = False
        self.encoder_feedback_ok = False
        self.encoder_last_success = None
        self.modbus_read_failures = 0
        self.encoder_last_update = EncoderUpdate(
            False, False, 'client_neu_baseline_noetig')
        self.encoder_last_failure_reason = 'client_neu_baseline_noetig'
        self.encoder_left_high_word_first = None
        self.encoder_right_high_word_first = None
        self.meas_v = None
        self.meas_w = None
        self.feedback_ok = False

    def _handle_bus_read_failure(self, reason):
        if self.modbus_client is not None and self.rs485_ready:
            self._stop_both_motors(force=True)
        self._mark_bus_fault(reason)

    def _note_modbus_read_failure(self, reason):
        self.modbus_read_failures += 1
        if self.modbus_read_failures >= self.encoder_failure_stop_count:
            self._handle_bus_read_failure(reason)

    def _mark_bus_fault(self, reason):
        self.rs485_ready = False
        self.encoder_connection_initialized = False
        self.encoder_new_measurement = False
        self.encoder_feedback_ok = False
        self.feedback_ok = False
        self.meas_v = None
        self.meas_w = None
        self.encoder_last_failure_reason = reason

    def _write_ramps(self):
        """Beschleunigungs- und Bremsrampe in die Motoren schreiben.

        WARUM DAS NOETIG IST (28.07.2026):
        Diese Register wurden bisher NIE gesetzt - die Antriebe liefen mit ihrer
        Werksrampe an, und die ist fuer diesen Aufbau zu hart. Der Roboter NICKT
        beim Anfahren sichtbar. Das ist nicht nur unschoen: Die Kamera sitzt auf
        1.34 m, das ist ein langer Hebel. Schon 2 Grad Nicken verschieben den
        gemessenen Boden auf 3 m Entfernung um rund 10 cm - damit rutscht Boden
        ueber die Hindernisschwelle und wird als Wand in die Karte eingetragen.
        Die Handfahrt vom 28.07. lieferte so eine Karte mit einem 8x8 m grossen
        "belegten" Klumpen in einem 3.8x4.9 m Raum.

        Groessere Werte = sanfter. Die Einheit ist Millisekunden (Zeit fuer die
        volle Drehzahlaenderung) laut "Modbus Series Bus Driver Function Manual".
        """
        if not self.rs485_ready:
            return False
        for motor_id in (self.left_motor_id, self.right_motor_id):
            for register, value in (
                    (self.accel_register, self.accel_ms),
                    (self.decel_register, self.decel_ms),
                    (self.start_speed_register, self.start_speed_rpm)):
                if not self._write_register(motor_id, register, value):
                    self.get_logger().error(
                        f'Anfahrparameter Motor {motor_id}, Reg 0x{register:04X} '
                        'nicht bestaetigt')
                    return False
        self.get_logger().info(
            f'Anfahrverhalten bestaetigt: Beschleunigen {self.accel_ms} ms, '
            f'Bremsen {self.decel_ms} ms, Startdrehzahl {self.start_speed_rpm} rpm.')
        return True

    def _ensure_rs485(self):
        """Verbindung selbstheilend halten.

        Eine einzelne Modbus-Ausnahme setzt rs485_ready auf False. Ohne diese
        Wiederherstellung bliebe der Bus danach dauerhaft tot: die
        Drehzahl-Rueckmeldung versucht von sich aus KEINEN Neuaufbau, und ein
        Neuaufbau ueber _send_rs485_velocity passiert nur, wenn gerade ein
        Fahrbefehl anliegt. Real aufgetreten (27.07.2026): waehrend des
        Startgewitters von OAK, VL53 und RTAB-Map lief eine Transaktion in den
        Timeout; danach meldete der Node dauerhaft rs485_ready=False, obwohl
        die Motoren einwandfrei antworteten.
        """
        if self.encoder_config_fault_latched:
            return
        if self.rs485_ready:
            return
        now = time.monotonic()
        if now - self.last_reconnect_try < self.reconnect_period_s:
            return
        self.last_reconnect_try = now
        self.get_logger().warn('RS485 nicht bereit - versuche Neuaufbau ...',
                               throttle_duration_sec=10.0)
        self._connect_modbus()

    def _send_rs485_velocity(self, wheel_cmd: WheelCommand):
        if not self.rs485_ready:
            return False

        now = time.monotonic()
        if now - self.last_modbus_write < self.modbus_write_period_s:
            return True
        self.last_modbus_write = now

        # Beide Sollwerte muessen bestaetigt sein, bevor auch nur ein Motor den
        # Startbefehl erhaelt. Sonst koennte ein alter Sollwert oder nur eine
        # Seite anlaufen.
        left_rpm = self._clamp(wheel_cmd.rpm_left * self.gear_ratio,
                               -self.max_motor_rpm, self.max_motor_rpm)
        right_rpm = self._clamp(wheel_cmd.rpm_right * self.gear_ratio,
                                -self.max_motor_rpm, self.max_motor_rpm)
        if not self._write_motor_setpoint(self.left_motor_id, left_rpm):
            self._handle_drive_write_failure('sollwert_links')
            return False
        if not self._write_motor_setpoint(self.right_motor_id, right_rpm):
            self._handle_drive_write_failure('sollwert_rechts')
            return False
        # Auch zwei bestaetigte Setpoint-Writes koennen zusammen laenger als
        # der Watchdog dauern. Ein inzwischen alter Befehl darf nie starten.
        if self._command_timed_out():
            self._stop_both_motors(force=True)
            return False
        if not self._write_motor_start(self.left_motor_id):
            self._handle_drive_write_failure('start_links')
            return False
        if self._command_timed_out():
            self._stop_both_motors(force=True)
            return False
        if not self._write_motor_start(self.right_motor_id):
            self._handle_drive_write_failure('start_rechts')
            return False

        self.last_sent_left_rpm = left_rpm
        self.last_sent_right_rpm = right_rpm
        return True

    def _send_stop_if_needed(self):
        return self._stop_both_motors(force=False)

    def _stop_both_motors(self, force=False):
        if (not force and self.last_sent_left_rpm == 0.0 and
                self.last_sent_right_rpm == 0.0):
            return True
        if not self.rs485_ready:
            return False
        left_ok = self._write_motor_stop(self.left_motor_id)
        right_ok = self._write_motor_stop(self.right_motor_id)
        if left_ok and right_ok:
            self.last_sent_left_rpm = 0.0
            self.last_sent_right_rpm = 0.0
            return True
        self.get_logger().error(
            f'Stop nicht von beiden Motoren bestaetigt: '
            f'links={left_ok}, rechts={right_ok}; Reconnect erforderlich')
        self._mark_bus_fault('stop_nicht_bestaetigt')
        return False

    def _handle_drive_write_failure(self, stage):
        self.get_logger().error(
            f'Motorbefehl in Phase {stage} fehlgeschlagen; bestaetigter Stopversuch')
        # _write_register kann den Bus bereits als fehlerhaft markieren. Fuer
        # den bestmoeglichen Stopversuch bleibt derselbe Client noch nutzbar.
        if self.modbus_client is not None:
            self.rs485_ready = True
            self._stop_both_motors(force=True)
        self._mark_bus_fault(f'motorbefehl_{stage}_fehlgeschlagen')

    def _quantize_motor_rpm(self, rpm: float) -> int:
        signed_rpm = int(round(rpm * self.rpm_scale))
        return int(self._clamp(signed_rpm, -32768, 32767))

    def _write_motor_setpoint(self, motor_id: int, rpm: float) -> bool:
        signed_rpm = self._quantize_motor_rpm(rpm)
        return self._write_register(motor_id, self.rpm_register, signed_rpm & 0xFFFF)

    def _write_motor_start(self, motor_id: int) -> bool:
        return self._write_register(
            motor_id, self.command_register, self.velocity_start_value)

    def _write_motor_stop(self, motor_id: int) -> bool:
        return self._write_register(motor_id, self.command_register, self.stop_value)

    def _latch_encoder_config_fault(self, reason):
        """Sperrt Fahrt bis zum Neustart; Reconnect heilt Konfigfehler nicht."""
        self._encoder_failure(reason)
        if self.modbus_client is not None and self.rs485_ready:
            self._stop_both_motors(force=True)
        self.encoder_config_fault_latched = True
        self._mark_bus_fault(reason)
        if self.modbus_client is not None:
            try:
                self.modbus_client.close()
            except Exception as exc:
                self.get_logger().warn(
                    f'RS485-Client nach Encoder-Konfigfehler nicht schliessbar: {exc}')
            self.modbus_client = None
        self.get_logger().error(
            f'Encoder-Konfiguration gesperrt: {reason}. '
            'Treiber/YAML pruefen und Node danach neu starten.')

    # ------------------- Positions-Rueckmeldung (lesend) ----------------
    def _initialize_encoder_feedback(self):
        """Liest Treibereinstellungen und setzt vor jedem Start die Baseline."""
        if not (self.rs485_ready and self.encoder_tracker):
            self.encoder_feedback_ok = False
            self.encoder_last_failure_reason = "encoder_nicht_konfiguriert"
            return False

        config = []
        for motor_id in (self.left_motor_id, self.right_motor_id):
            segment = self._read_register(motor_id, self.encoder_segment_register)
            order = self._read_register(motor_id, self.encoder_word_order_register)
            resolution = self._read_register(motor_id, self.encoder_resolution_register)
            if segment is None or order is None or resolution is None:
                self._encoder_failure("treibereinstellungen_nicht_lesbar")
                return False
            if order not in (0, 1):
                self._latch_encoder_config_fault('ungueltige_encoder_wortfolge')
                return False
            config.append((segment, order == 0, resolution))
        (self.encoder_segment_left, self.encoder_left_high_word_first,
         self.encoder_resolution_left) = config[0]
        (self.encoder_segment_right, self.encoder_right_high_word_first,
         self.encoder_resolution_right) = config[1]
        if self.encoder_segment_left != self.encoder_segment_right:
            self._latch_encoder_config_fault('segmentierung_links_rechts_abweichend')
            return False
        if self.encoder_resolution_left != self.encoder_resolution_right:
            self._latch_encoder_config_fault('encoderaufloesung_links_rechts_abweichend')
            return False
        if (self.encoder_expected_segment and
                self.encoder_segment_left != self.encoder_expected_segment):
            self._latch_encoder_config_fault('segmentierung_abweichend_von_abnahme')
            return False
        if (self.encoder_expected_resolution and
                self.encoder_resolution_left != self.encoder_expected_resolution):
            self._latch_encoder_config_fault('encoderaufloesung_abweichend_von_abnahme')
            return False

        read_started = time.monotonic()
        pair = self._read_encoder_pair()
        sample_time = (read_started + time.monotonic()) / 2.0
        if pair is None:
            self._encoder_failure("baseline_nicht_lesbar")
            return False
        # Beim ersten Start oder nach einem neuen Modbus-Client entsteht nur
        # die Baseline. Kurze Lesefehler innerhalb desselben Clients behalten
        # sie; ein echter Reconnect rebased bewusst gegen Controllerresets.
        self._accept_encoder_pair(pair, sample_time)
        if self.encoder_connection_initialized:
            self.modbus_read_failures = 0
        return self.encoder_connection_initialized

    def _poll_encoder_feedback(self):
        if not (self.rs485_ready and self.encoder_tracker):
            return
        read_started = time.monotonic()
        if read_started - self.encoder_last_poll < self.encoder_feedback_period_s:
            return
        self.encoder_last_poll = read_started
        pair = self._read_encoder_pair()
        sample_time = (read_started + time.monotonic()) / 2.0
        if pair is None:
            self._encoder_failure("encoderpaar_nicht_lesbar")
            return
        self._accept_encoder_pair(pair, sample_time)
        if self.encoder_feedback_ok:
            self.modbus_read_failures = 0

    def _accept_encoder_pair(self, pair, timestamp):
        left, right = pair
        update = self.encoder_tracker.update(
            left.position_u32, right.position_u32, timestamp)
        self.encoder_left_feedback = left
        self.encoder_right_feedback = right
        self.meas_motor_rpm_left = left.speed_rpm
        self.meas_motor_rpm_right = right.speed_rpm
        self.encoder_last_update = update
        self.encoder_last_failure_reason = update.reason
        if update.accepted:
            self.x = self.encoder_tracker.x_m
            self.y = self.encoder_tracker.y_m
            self.yaw = self.encoder_tracker.yaw_rad
            self.meas_v = update.linear_velocity_mps
            self.meas_w = update.angular_velocity_radps
        if update.reason.startswith("unplausibles_delta") or \
                update.reason.startswith("mehrdeutiges_delta"):
            self.get_logger().warn(f"Encoderprobe verworfen: {update.reason}")
        self.encoder_feedback_ok = (update.reason == "ok" or
                                    update.reason == "baseline_initialisiert")
        if self.encoder_feedback_ok:
            self.encoder_last_success = timestamp
            self.encoder_consecutive_failures = 0
            self.encoder_new_measurement = True
        else:
            self.meas_v = None
            self.meas_w = None
            self.encoder_consecutive_failures = self.encoder_failure_stop_count
        self.encoder_connection_initialized = self.encoder_feedback_ok
        self.feedback_ok = self.encoder_feedback_ok

    def _read_encoder_pair(self):
        if self.encoder_left_high_word_first is None or \
                self.encoder_right_high_word_first is None:
            return None
        ids = [(self.left_motor_id, self.encoder_left_high_word_first),
               (self.right_motor_id, self.encoder_right_high_word_first)]
        if not self.encoder_poll_left_first:
            ids.reverse()
        self.encoder_poll_left_first = not self.encoder_poll_left_first
        result = {}
        for motor_id, high_word_first in ids:
            feedback = self._read_motor_feedback(motor_id, high_word_first)
            if feedback is None:
                return None
            result[motor_id] = feedback
        return result[self.left_motor_id], result[self.right_motor_id]

    def _read_motor_feedback(self, motor_id, high_word_first):
        words = self._read_registers(motor_id, self.encoder_position_register, 3)
        if words is None:
            return None
        try:
            return MotorFeedback(
                decode_position_words(words[:2], high_word_first),
                float(decode_i16(words[2])) / self.rpm_scale,
            )
        except (TypeError, ValueError) as exc:
            self.get_logger().warn(f"Ungueltige Encoderantwort Motor {motor_id}: {exc}")
            return None

    def _encoder_failure(self, reason):
        self.encoder_feedback_ok = False
        self.feedback_ok = False
        self.meas_v = None
        self.meas_w = None
        self.encoder_consecutive_failures += 1
        self.encoder_last_failure_reason = reason
        if (self.encoder_consecutive_failures >= self.encoder_failure_stop_count or
                self._encoder_is_stale()):
            self._send_stop_if_needed()

    def _encoder_feedback_age(self):
        if self.encoder_last_success is None:
            return None
        return max(0.0, time.monotonic() - self.encoder_last_success)

    def _encoder_is_stale(self):
        age = self._encoder_feedback_age()
        return age is None or age > self.encoder_stale_timeout_s

    def _encoder_motion_allowed(self):
        return bool(self.encoder_tracker and self.encoder_tracker.initialized and
                    self.encoder_connection_initialized and
                    not self._encoder_is_stale() and
                    self.encoder_consecutive_failures < self.encoder_failure_stop_count)

    def _encoder_twist(self):
        if self._encoder_is_stale() or not self.encoder_connection_initialized:
            return 0.0, 0.0
        return (self.meas_v or 0.0, self.meas_w or 0.0)

    # ------------------- Drehzahl-Rueckmeldung (lesend) -----------------
    def _poll_speed_feedback(self):
        """Liest beide Ist-Drehzahlen und rechnet sie in v/omega um.

        Laeuft in eigener, langsamerer Periode als der Schreibtakt, damit die
        Lesezugriffe die Motorregelung nicht ausbremsen.
        """
        if not (self.use_speed_feedback and self.rs485_ready):
            self.feedback_ok = False
            self.meas_v = None
            self.meas_w = None
            return
        now = time.monotonic()
        if now - self.last_feedback_read < self.feedback_period_s:
            return
        self.last_feedback_read = now

        rpm_l = self._read_motor_speed(self.left_motor_id)
        rpm_r = self._read_motor_speed(self.right_motor_id)
        if rpm_l is None or rpm_r is None:
            self.feedback_ok = False
            self.meas_v = None
            self.meas_w = None
            return

        self.meas_motor_rpm_left = rpm_l
        self.meas_motor_rpm_right = rpm_r

        # Motor-rpm -> Rad-rpm -> Radgeschwindigkeit [m/s]
        circumference = 2.0 * math.pi * self.wheel_radius
        v_left = (rpm_l / self.gear_ratio) / 60.0 * circumference
        v_right = (rpm_r / self.gear_ratio) / 60.0 * circumference

        # Montage-Invertierung zuruecknehmen (Gegenstueck zu _twist_to_wheels),
        # damit wieder Roboter-Koordinaten herauskommen.
        if self.invert_left:
            v_left *= -1.0
        if self.invert_right:
            v_right *= -1.0

        self.meas_v = (v_left + v_right) / 2.0
        self.meas_w = (v_right - v_left) / self.wheel_separation
        self.feedback_ok = True
        self.modbus_read_failures = 0

    def _read_motor_speed(self, motor_id: int):
        """Ist-Drehzahl in MOTOR-rpm (vorzeichenbehaftet) oder None."""
        raw = self._read_register(motor_id, self.speed_register)
        if raw is None:
            return None
        if raw >= 0x8000:          # uint16 -> int16 (Zweierkomplement)
            raw -= 0x10000
        return float(raw) / self.rpm_scale

    def _read_registers(self, motor_id: int, address: int, count: int):
        """Liest FC03-Register atomar; unterstuetzt pymodbus-3.x-Keywords."""
        if self.modbus_client is None or count < 1:
            return None
        try:
            for kw in ("device_id", "slave", "unit"):
                try:
                    result = self.modbus_client.read_holding_registers(
                        address, count=count, **{kw: motor_id})
                except TypeError:
                    continue
                if result is None or result.isError():
                    self._note_modbus_read_failure('modbus_leseantwort_fehlerhaft')
                    return None
                words = [int(word) for word in result.registers]
                if len(words) != count:
                    self._note_modbus_read_failure('modbus_leseantwort_unvollstaendig')
                    return None
                return words
            self._handle_bus_read_failure('pymodbus_api_unbekannt')
            return None
        except Exception as exc:
            self._handle_bus_read_failure('modbus_leseexception')
            self.get_logger().warn(
                f"Modbus-Lesefehler Motor {motor_id}, Reg 0x{address:04X}: {exc}",
                throttle_duration_sec=5.0)
            return None

    def _read_register(self, motor_id: int, address: int):
        words = self._read_registers(motor_id, address, 1)
        return words[0] if words else None

    def _write_register(self, motor_id: int, address: int, value: int) -> bool:
        if self.modbus_client is None:
            return False
        try:
            # Slave-Adressierung je nach pymodbus-Version: 3.7+/3.14 device_id=,
            # 3.0-3.6 slave=, 2.x unit=. Reihenfolge = neueste zuerst.
            try:
                result = self.modbus_client.write_register(address, value, device_id=motor_id)
            except TypeError:
                try:
                    result = self.modbus_client.write_register(address, value, slave=motor_id)
                except TypeError:
                    result = self.modbus_client.write_register(address, value, unit=motor_id)
            if result is None or result.isError():
                self._mark_bus_fault('modbus_schreibantwort_fehlerhaft')
                return False
            return True
        except Exception as exc:
            self._mark_bus_fault('modbus_schreibexception')
            self.get_logger().error(f'Modbus-Fehler Motor {motor_id}, Reg 0x{address:04X}: {exc}')
            return False

    # ======================= Helfer ====================================
    def _command_timed_out(self) -> bool:
        age = max(0.0, time.monotonic() - self.last_cmd_monotonic)
        return age > self.cmd_timeout

    def _throttled_log(self, timed_out: bool):
        now = time.monotonic()
        if now - self.last_log_time < 1.0:
            return
        self.last_log_time = now
        cmd = self.active_wheel_cmd
        mode = 'TIMEOUT-STOP' if timed_out else 'CMD'
        self.get_logger().info(
            f'{mode}: v={self.cmd_v:+.3f} m/s w={self.cmd_w:+.3f} rad/s | '
            f'Rad L={cmd.rpm_left:+.1f} R={cmd.rpm_right:+.1f} rpm | '
            f'Motor L={cmd.rpm_left * self.gear_ratio:+.0f} '
            f'R={cmd.rpm_right * self.gear_ratio:+.0f} rpm')

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
