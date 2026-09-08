"""Publish an HWT601-AGV-485 as a passive, fail-closed ROS 2 IMU source."""

from collections import deque
import json
import math
import os
import time
from typing import Optional

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
from std_msgs.msg import String

from .hwt601_protocol import (
    DEFAULT_DEVICE_ADDRESS,
    Hwt601ProtocolError,
    decode_motion_registers,
)
from .hwt601_transport import Hwt601SerialTransport, Hwt601TransportError


class Hwt601ImuNode(Node):
    """Poll motion registers; never configure the sensor or command a robot."""

    def __init__(self):
        super().__init__('hwt601_imu')
        self.declare_parameter('port', '/dev/ttyUSB_HWT601')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('device_address', DEFAULT_DEVICE_ADDRESS)
        self.declare_parameter('poll_rate_hz', 100.0)
        self.declare_parameter('response_timeout_s', 0.03)
        self.declare_parameter('reconnect_interval_s', 1.0)
        self.declare_parameter('errors_before_reconnect', 3)
        self.declare_parameter('sensor_timeout_s', 0.20)
        self.declare_parameter('frame_id', 'hwt601_link')
        self.declare_parameter('imu_topic', '/hwt601/imu/data_raw')
        self.declare_parameter('status_topic', '/hwt601/status_json')
        self.declare_parameter('diagnostics_topic', '/diagnostics')
        self.declare_parameter('acceleration_full_scale_g', 4.0)
        self.declare_parameter('angular_velocity_full_scale_dps', 400.0)
        self.declare_parameter('angular_velocity_variance', 0.02)
        self.declare_parameter('linear_acceleration_variance', 0.25)
        self.declare_parameter('saturation_margin_counts', 8)

        gp = self.get_parameter
        self.port = str(gp('port').value)
        self.baud = int(gp('baud').value)
        self.device_address = int(gp('device_address').value)
        self.poll_rate_hz = float(gp('poll_rate_hz').value)
        self.response_timeout_s = float(gp('response_timeout_s').value)
        self.reconnect_interval_s = float(gp('reconnect_interval_s').value)
        self.errors_before_reconnect = int(gp('errors_before_reconnect').value)
        self.sensor_timeout_s = float(gp('sensor_timeout_s').value)
        self.frame_id = str(gp('frame_id').value)
        self.imu_topic = str(gp('imu_topic').value)
        self.status_topic = str(gp('status_topic').value)
        self.diagnostics_topic = str(gp('diagnostics_topic').value)
        self.acceleration_full_scale_g = float(
            gp('acceleration_full_scale_g').value)
        self.angular_velocity_full_scale_dps = float(
            gp('angular_velocity_full_scale_dps').value)
        self.angular_velocity_variance = float(
            gp('angular_velocity_variance').value)
        self.linear_acceleration_variance = float(
            gp('linear_acceleration_variance').value)
        self.saturation_margin_counts = int(
            gp('saturation_margin_counts').value)
        self._validate_parameters()

        self.imu_pub = self.create_publisher(
            Imu, self.imu_topic, qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.diagnostics_pub = self.create_publisher(
            DiagnosticArray, self.diagnostics_topic, 10)

        self._transport: Optional[Hwt601SerialTransport] = None
        self._last_connect_attempt = -math.inf
        self._last_received_at: Optional[float] = None
        self._accepted = 0
        self._rejected = 0
        self._successful_connections = 0
        self._consecutive_errors = 0
        self._last_error = 'noch_keine_daten'
        self._sample_times = deque(
            maxlen=max(20, int(self.poll_rate_hz * 2.0)))

        self.create_timer(1.0 / self.poll_rate_hz, self._poll)
        self.create_timer(0.5, self._publish_status)
        self.get_logger().info(
            f'HWT601 passiv vorbereitet: {self.port} bei {self.baud} Baud, '
            f'Adresse {self.device_address}; nur Modbus-Lesefunktion 0x03')

    def _validate_parameters(self) -> None:
        motor_port = '/dev/ttyUSB_BASE'
        same_as_motor_port = (
            os.path.exists(motor_port)
            and os.path.realpath(self.port) == os.path.realpath(motor_port))
        if not self.port or self.port == motor_port or same_as_motor_port:
            raise ValueError(
                'HWT601 braucht einen eigenen, expliziten USB-RS485-Port')
        supported_baud = (
            4800, 9600, 19200, 38400, 57600, 115200, 230400)
        if self.baud not in supported_baud:
            raise ValueError('nicht unterstuetzte HWT601-Baudrate')
        if not 1 <= self.device_address <= 247:
            raise ValueError('device_address muss zwischen 1 und 247 liegen')
        positive = {
            'poll_rate_hz': self.poll_rate_hz,
            'response_timeout_s': self.response_timeout_s,
            'reconnect_interval_s': self.reconnect_interval_s,
            'sensor_timeout_s': self.sensor_timeout_s,
            'acceleration_full_scale_g': self.acceleration_full_scale_g,
            'angular_velocity_full_scale_dps': (
                self.angular_velocity_full_scale_dps),
            'angular_velocity_variance': self.angular_velocity_variance,
            'linear_acceleration_variance': self.linear_acceleration_variance,
        }
        for name, value in positive.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f'{name} muss endlich und positiv sein')
        if self.poll_rate_hz > 200.0:
            raise ValueError(
                'poll_rate_hz darf die interne 200-Hz-Rate nicht uebersteigen')
        if self.errors_before_reconnect < 1:
            raise ValueError('errors_before_reconnect muss mindestens 1 sein')
        if not 1 <= self.saturation_margin_counts <= 1024:
            raise ValueError('saturation_margin_counts ist unplausibel')
        if not self.frame_id or self.frame_id.startswith('/'):
            raise ValueError(
                'frame_id muss ein physischer TF-Frame ohne / sein')

    def _connect(self, now: float) -> bool:
        if now - self._last_connect_attempt < self.reconnect_interval_s:
            return False
        self._last_connect_attempt = now
        transport = Hwt601SerialTransport(
            port=self.port,
            baud=self.baud,
            timeout_s=self.response_timeout_s,
            device_address=self.device_address,
        )
        try:
            transport.open()
        except Hwt601TransportError as error:
            self._last_error = str(error)
            return False
        self._transport = transport
        self._successful_connections += 1
        self._consecutive_errors = 0
        self._last_error = ''
        self.get_logger().info(f'HWT601 verbunden: {self.port}')
        return True

    def _disconnect(self) -> None:
        if self._transport is not None:
            self._transport.close()
        self._transport = None
        self._sample_times.clear()
        self._last_received_at = None

    def _record_error(self, error: Exception) -> None:
        self._rejected += 1
        self._consecutive_errors += 1
        self._last_error = str(error)
        if self._consecutive_errors >= self.errors_before_reconnect:
            self._disconnect()

    def _poll(self) -> None:
        now = time.monotonic()
        if self._transport is None and not self._connect(now):
            return
        try:
            registers = self._transport.read_motion_registers()
            sample = decode_motion_registers(
                registers,
                acceleration_full_scale_g=self.acceleration_full_scale_g,
                angular_velocity_full_scale_dps=(
                    self.angular_velocity_full_scale_dps),
            )
            if sample.saturated(self.saturation_margin_counts):
                raise Hwt601ProtocolError(
                    'Messwert ist am Rohdatenlimit gesaettigt')
        except (Hwt601TransportError, Hwt601ProtocolError, OSError) as error:
            self._record_error(error)
            return

        message = Imu()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self.frame_id
        message.orientation.w = 1.0
        message.orientation_covariance[0] = -1.0
        message.angular_velocity.x = sample.angular_velocity_radps[0]
        message.angular_velocity.y = sample.angular_velocity_radps[1]
        message.angular_velocity.z = sample.angular_velocity_radps[2]
        message.linear_acceleration.x = sample.linear_acceleration_mps2[0]
        message.linear_acceleration.y = sample.linear_acceleration_mps2[1]
        message.linear_acceleration.z = sample.linear_acceleration_mps2[2]
        for index in (0, 4, 8):
            message.angular_velocity_covariance[index] = (
                self.angular_velocity_variance)
            message.linear_acceleration_covariance[index] = (
                self.linear_acceleration_variance)
        self.imu_pub.publish(message)

        received_at = time.monotonic()
        self._last_received_at = received_at
        self._sample_times.append(received_at)
        self._accepted += 1
        self._consecutive_errors = 0
        self._last_error = ''

    def _observed_rate_hz(self) -> Optional[float]:
        if len(self._sample_times) < 2:
            return None
        duration = self._sample_times[-1] - self._sample_times[0]
        if duration <= 0.0:
            return None
        return (len(self._sample_times) - 1) / duration

    def _publish_status(self) -> None:
        now = time.monotonic()
        age_s = (
            None if self._last_received_at is None
            else max(0.0, now - self._last_received_at))
        connected = bool(
            self._transport is not None and self._transport.is_open)
        fresh = age_s is not None and age_s <= self.sensor_timeout_s
        ready = connected and fresh and self._consecutive_errors == 0
        if ready:
            state = 'bereit'
            reason = 'gueltige_rohdaten'
        elif not connected:
            state = 'getrennt'
            reason = self._last_error or 'serielle_verbindung_fehlt'
        else:
            state = 'degradiert'
            reason = self._last_error or 'daten_fehlend_oder_alt'
        rate_hz = self._observed_rate_hz()
        payload = {
            'ready': ready,
            'raw_data_ready': ready,
            'fusion_ready': False,
            'state': state,
            'reason': reason,
            'actuator_output': False,
            'sensor_write_commands': False,
            'port': self.port,
            'baud': self.baud,
            'device_address': self.device_address,
            'frame_id': self.frame_id,
            'topic': self.imu_topic,
            'age_s': age_s,
            'observed_rate_hz': rate_hz,
            'accepted': self._accepted,
            'rejected': self._rejected,
            'successful_connections': self._successful_connections,
            'reconnects': max(0, self._successful_connections - 1),
            'consecutive_errors': self._consecutive_errors,
            'last_error': self._last_error,
            'host_receive_timestamp': True,
            'scale_validation_pending': True,
        }
        self.status_pub.publish(String(
            data=json.dumps(payload, allow_nan=False)))

        diagnostic = DiagnosticStatus()
        diagnostic.name = 'robot_state_estimation/hwt601_imu'
        diagnostic.hardware_id = f'hwt601_modbus_{self.device_address}'
        diagnostic.level = (
            DiagnosticStatus.OK if ready else DiagnosticStatus.WARN)
        diagnostic.message = reason
        diagnostic.values = [
            KeyValue(key='connected', value=str(connected).lower()),
            KeyValue(key='fresh', value=str(fresh).lower()),
            KeyValue(key='accepted', value=str(self._accepted)),
            KeyValue(key='rejected', value=str(self._rejected)),
            KeyValue(key='observed_rate_hz', value=str(rate_hz)),
            KeyValue(key='actuator_output', value='false'),
            KeyValue(key='sensor_write_commands', value='false'),
            KeyValue(key='scale_validation_pending', value='true'),
        ]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status = [diagnostic]
        self.diagnostics_pub.publish(array)

    def destroy_node(self):
        self._disconnect()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Hwt601ImuNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
