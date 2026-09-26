"""Single-use, fixed HWT601 movement diagnostic behind the mission gate.

The node is only launched by an explicit opt-in. It never publishes to
``/cmd_vel`` and exposes no target/velocity arguments: one Trigger request
can run only 0.25 m forward, +15 degrees, then -15 degrees, with verified
stops between phases. Commands enter the existing command gate.
"""

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu, LaserScan, PointCloud2
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
from tf2_msgs.msg import TFMessage
from robot_interfaces.msg import NearFieldStatus
from tf2_ros import Buffer, TransformException, TransformListener


PHASES = ('forward', 'stop_after_forward', 'turn_positive',
          'stop_after_positive', 'turn_negative', 'stop_final')
LAB_MODE = 'stage3_bounded_motion_test'
LINEAR_MPS = 0.08  # existing Explore-direct gate limit; no product limit change
ANGULAR_RADPS = 0.10  # existing Explore-direct gate limit; no product limit change
TEST_DISTANCE_M = 0.25
TEST_TURN_RAD = math.radians(15.0)
SOURCE_TIMEOUT_S = 0.8
TF_TIMEOUT_S = 0.8
STOP_CONFIRM_S = 0.5
STOP_TIMEOUT_S = 8.0
PHASE_TIMEOUT_S = 45.0
FOOTPRINT_RADIUS_M = 0.414  # existing padded local footprint circumscribed radius


def _yaw(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                      1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def _wrap(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def directed_turn_progress(origin, yaw, direction):
    """Return degrees-in-radians progressed in the requested turn direction."""
    return direction * _wrap(yaw - origin)


def point_in_polygon(x, y, polygon):
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        crosses = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if crosses:
            inside = not inside
        j = i
    return inside


def disk_in_polygon(x, y, radius, polygon):
    """Conservatively require the padded footprint disk inside the scope."""
    if not point_in_polygon(x, y, polygon):
        return False
    for index in range(32):
        angle = 2.0 * math.pi * index / 32.0
        if not point_in_polygon(
                x + radius * math.cos(angle),
                y + radius * math.sin(angle), polygon):
            return False
    return True


class Stage3MotionDiagnostic(Node):
    def __init__(self):
        super().__init__('stage3_motion_diagnostic')
        self.declare_parameter('enabled', False)
        self.declare_parameter('scope_profile_path', '')
        self.declare_parameter(
            'required_scope_id', 'stage3-local-scope-20260925-after-r2')
        self.declare_parameter('lab_external_hardware_halt_attested', False)
        if not bool(self.get_parameter('enabled').value):
            raise RuntimeError('Stage-3-Diagnosemodus ist nicht aktiviert')
        self.external_hardware_halt_attested = bool(
            self.get_parameter('lab_external_hardware_halt_attested').value)

        profile_path = Path(str(
            self.get_parameter('scope_profile_path').value)).expanduser()
        if not profile_path.is_file():
            raise RuntimeError('Verifiziertes WE-Scope-Profil fehlt')
        with profile_path.open('r', encoding='utf-8') as stream:
            profile = yaml.safe_load(stream)
        params = profile.get('explore_node', {}).get('ros__parameters', {})
        self.scope_id = str(params.get('wohnungserkundung_scope_id', '')).strip()
        self.session_id = str(
            params.get('region_graph_shadow_session_id', '')).strip()
        values = params.get('wohnungserkundung_scope_polygon_xy', [])
        self.scope_polygon = tuple(
            (float(values[i]), float(values[i + 1]))
            for i in range(0, len(values), 2)) if len(values) % 2 == 0 else ()
        if (self.scope_id != str(self.get_parameter('required_scope_id').value)
                or not params.get('wohnungserkundung_accessible_scope_verified')
                or not self.session_id or len(self.scope_polygon) < 3):
            raise RuntimeError('Scope-Profil/ID ist nicht exakt verifiziert')

        self._latest = {}
        self._received = {}
        self._stamps = {}
        self._state = 'idle'
        self._phase_started = None
        self._stop_stable_since = None
        self._start_pose = None
        self._start_yaw = None
        self._turn_negative_origin = None
        self._bound_fingerprint = None
        self._bound_frame = None
        self._bound_session = None
        self._result_message = ''
        self._last_nonzero_requested = False
        self._last_collision_zero_since = None
        self._log_stream = None
        self._test_started_once = False
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._command_pub = self.create_publisher(
            Twist, '/cmd_vel_stage3_diagnostic_raw', 10)
        self._active_pub = self.create_publisher(
            Bool, '/stage3_motion_test/active', 10)
        self._status_pub = self.create_publisher(
            String, '/stage3_motion_test/status_json', 10)
        self._start_srv = self.create_service(
            Trigger, '/stage3_motion_test/start', self._start)

        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT)
        self.create_subscription(PoseStamped, '/robot_map_manager/robot_pose',
                                 self._pose, 10)
        self.create_subscription(String, '/robot_map_manager/status_json',
                                 self._map_status, 10)
        self.create_subscription(String, '/explore/region_graph/status_json',
                                 self._region_status, 10)
        self.create_subscription(String, '/fusion/hwt601/status_json',
                                 self._json_topic('fusion'), 10)
        self.create_subscription(String, '/base_hardware/state_json',
                                 self._json_topic('base'), 10)
        self.create_subscription(String, '/shadow/hwt601/raw_status_json',
                                 self._json_topic('hwt_raw'), 10)
        self.create_subscription(String, '/shadow/hwt601/status_json',
                                 self._json_topic('hwt_yaw_status'), 10)
        self.create_subscription(NearFieldStatus, '/near_field/status',
                                 self._near_status, 10)
        estop_qos = QoSProfile(depth=1)
        estop_qos.reliability = ReliabilityPolicy.RELIABLE
        from rclpy.qos import DurabilityPolicy
        estop_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(Bool, '/safety/estop',
                                 self._bool_topic('estop'), estop_qos)
        self.create_subscription(LaserScan, '/scan_normiert',
                                 self._scan, sensor_qos)
        self.create_subscription(Odometry, '/odom',
                                 self._odom, sensor_qos)
        self.create_subscription(Odometry, '/fusion/hwt601/wheel_odom_raw',
                                 self._odom_topic('wheel_odom'), sensor_qos)
        self.create_subscription(Odometry, '/fusion/reference_odom',
                                 self._odom_topic('lidar_odom'), sensor_qos)
        self.create_subscription(String, '/sensor_fusion/lidar_odometry_json',
                                 self._json_topic('lidar_observer_status'), 10)
        self.create_subscription(Imu, '/shadow/hwt601/imu/yaw_rate',
                                 self._imu, sensor_qos)
        self.create_subscription(PointCloud2, '/near_field/left/points',
                                 self._cloud('vl53_left'), sensor_qos)
        self.create_subscription(PointCloud2, '/near_field/right/points',
                                 self._cloud('vl53_right'), sensor_qos)
        for topic, name in (
                ('/cmd_vel_stage3_diagnostic_raw', 'command_in'),
                ('/cmd_vel_nav', 'gate_out'),
                ('/cmd_vel_smoothed', 'smoother_out'),
                ('/cmd_vel', 'collision_monitor_out')):
            self.create_subscription(Twist, topic, self._twist_topic(name), 10)
        self.create_subscription(TFMessage, '/tf', self._tf_event, sensor_qos)
        self.create_timer(0.05, self._tick)
        self.get_logger().warning(
            f'LABORMODUS {LAB_MODE} aktiv (explizites Diagnose-Opt-in); '
            f'externer Hardware-Halt manuell bestaetigt='
            f'{self.external_hardware_halt_attested}; Scope {self.scope_id}; '
            'ein einziger Trigger erlaubt nur 0,25 m / +15 Grad / -15 Grad.')

    def _record(self, topic, payload, stamp_ns=None):
        received = time.monotonic()
        self._latest[topic] = payload
        self._received[topic] = received
        if stamp_ns is not None:
            self._stamps[topic] = stamp_ns
        if self._log_stream is not None:
            self._log_stream.write(json.dumps({
                'received_monotonic_s': received,
                'stamp_ns': stamp_ns,
                'topic': topic,
                'payload': payload,
            }, separators=(',', ':'), allow_nan=False) + '\n')
            self._log_stream.flush()

    def _json_topic(self, name):
        def callback(msg):
            try:
                value = json.loads(msg.data)
            except (ValueError, TypeError):
                value = None
            self._record(name, value)
        return callback

    def _bool_topic(self, name):
        return lambda msg: self._record(name, bool(msg.data))

    def _pose(self, msg):
        p = msg.pose.position
        q = msg.pose.orientation
        self._record('map_pose', {'frame_id': msg.header.frame_id,
                                  'x': p.x, 'y': p.y, 'yaw': _yaw(q)},
                     _stamp(msg))

    def _map_status(self, msg):
        try:
            value = json.loads(msg.data)
        except (ValueError, TypeError):
            value = None
        self._record('map_status', value)

    def _region_status(self, msg):
        try:
            value = json.loads(msg.data)
        except (ValueError, TypeError):
            value = None
        self._record('region_status', value)

    def _near_status(self, msg):
        self._record('near_status', {
            'frame_id': msg.header.frame_id,
            'left_frame_healthy': msg.left_frame_healthy,
            'right_frame_healthy': msg.right_frame_healthy,
            'left_quality': msg.left_quality,
            'right_quality': msg.right_quality,
        }, _stamp(msg))

    def _scan(self, msg):
        valid = [value for value in msg.ranges
                 if math.isfinite(value) and msg.range_min <= value <= msg.range_max]
        self._record('scan', {'frame_id': msg.header.frame_id,
                              'valid_ranges': len(valid),
                              'minimum_range_m': min(valid) if valid else None},
                     _stamp(msg))

    def _odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        tw = msg.twist.twist
        self._record('odom', {'frame_id': msg.header.frame_id,
                              'child_frame_id': msg.child_frame_id,
                              'x': p.x, 'y': p.y, 'yaw': _yaw(q),
                              'vx': tw.linear.x, 'wz': tw.angular.z},
                     _stamp(msg))

    def _odom_topic(self, name):
        def callback(msg):
            p = msg.pose.pose.position
            q = msg.pose.pose.orientation
            tw = msg.twist.twist
            self._record(name, {'frame_id': msg.header.frame_id,
                                'child_frame_id': msg.child_frame_id,
                                'x': p.x, 'y': p.y, 'yaw': _yaw(q),
                                'vx': tw.linear.x, 'wz': tw.angular.z},
                         _stamp(msg))
        return callback

    def _imu(self, msg):
        self._record('hwt_gyro', {
            'frame_id': msg.header.frame_id,
            'gyro_x': msg.angular_velocity.x,
            'gyro_y': msg.angular_velocity.y,
            'gyro_z': msg.angular_velocity.z,
        }, _stamp(msg))

    def _cloud(self, name):
        return lambda msg: self._record(
            name, {'frame_id': msg.header.frame_id, 'width': msg.width,
                   'height': msg.height}, _stamp(msg))

    def _twist_topic(self, name):
        def callback(msg):
            self._record(name, {'vx': msg.linear.x, 'wz': msg.angular.z})
        return callback

    def _tf_event(self, msg):
        records = []
        for item in msg.transforms:
            if ((item.header.frame_id, item.child_frame_id) not in (
                    ('map', 'odom'), ('odom', 'base_link'))):
                continue
            records.append({
                'parent': item.header.frame_id,
                'child': item.child_frame_id,
                'stamp_ns': _stamp(item),
                'x': item.transform.translation.x,
                'y': item.transform.translation.y,
                'yaw': _yaw(item.transform.rotation),
            })
        if records:
            self._record('tf', records, max(item['stamp_ns'] for item in records))

    def _fresh(self, name, timeout=SOURCE_TIMEOUT_S):
        if timeout is None:
            timeout = SOURCE_TIMEOUT_S
        received = self._received.get(name)
        if received is None or not 0.0 <= time.monotonic() - received <= timeout:
            return False
        stamp_ns = self._stamps.get(name)
        if stamp_ns is not None:
            age = self.get_clock().now().nanoseconds - stamp_ns
            if age < 0 or age > int(timeout * 1e9):
                return False
        return True

    def _scope_map_binding(self, require_exact_map=True):
        map_status = self._latest.get('map_status')
        region = self._latest.get('region_status')
        if not isinstance(map_status, dict) or map_status.get('ok') is not True:
            return None
        map_info = map_status.get('map')
        summary = map_info.get('summary') if isinstance(map_info, dict) else None
        if (not isinstance(summary, dict) or summary.get('available') is False
                or summary.get('frame_id') != 'map'
                or not isinstance(map_info.get('age_seconds'), (int, float))
                or not 0.0 <= map_info['age_seconds'] <= 5.0):
            return None
        fingerprint = summary.get('fingerprint')
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            return None
        if not isinstance(region, dict) or region.get('source', {}).get('stale') is not False:
            return None
        context = region.get('context', {})
        if (context.get('session_id') != self.session_id
                or not str(context.get('map_id', '')).startswith('map-')
                or context.get('frame_id') != 'map'
                or (require_exact_map
                    and context.get('map_id') != f'map-{fingerprint}')):
            return None
        return fingerprint

    def _health_failure(self):
        required = ('fusion', 'base', 'hwt_raw', 'hwt_yaw_status',
                    'near_status', 'estop', 'scan', 'odom', 'wheel_odom',
                    'hwt_gyro', 'vl53_left', 'vl53_right',
                    'map_status', 'region_status', 'map_pose')
        stale = [name for name in required if not self._fresh(
            name, 2.0 if name in ('map_status', 'region_status') else None)]
        if stale:
            return f'veraltete Quellen: {",".join(stale)}'
        fusion = self._latest.get('fusion')
        base = self._latest.get('base')
        raw = self._latest.get('hwt_raw')
        yaw_status = self._latest.get('hwt_yaw_status')
        near = self._latest.get('near_status')
        if (not isinstance(fusion, dict) or fusion.get('sources_ready') is not True
                or fusion.get('hwt_motion_ready') is not True
                or fusion.get('latched_fault')):
            return 'HWT-Fusion nicht fahrbereit'
        if (not isinstance(base, dict) or base.get('dry_run') is not False
                or base.get('allow_rs485') is not True
                or base.get('encoder_feedback_ok') is not True
                or base.get('encoder_stale') is not False
                or base.get('encoder_config_fault_latched') is True
                or base.get('meas_motor_rpm_left') is None
                or base.get('meas_motor_rpm_right') is None):
            return 'Base-/Encoder-Rueckmeldung nicht fahrbereit'
        if not isinstance(raw, dict) or raw.get('ready') is not True or raw.get('reconnects') != 0:
            return 'HWT-Rohquelle nicht gueltig'
        if not isinstance(yaw_status, dict) or yaw_status.get('ready') is not True:
            return 'HWT-Gierquelle nicht gueltig'
        if not isinstance(near, dict) or (
                near.get('frame_id') != 'base_link'
                or near.get('left_frame_healthy') is not True
                or near.get('right_frame_healthy') is not True):
            return 'VL53-Frame-Health nicht gueltig'
        if self._latest.get('estop') is not False:
            return 'Safety/E-Stop nicht freigegeben'
        scan = self._latest.get('scan')
        if not isinstance(scan, dict) or scan.get('valid_ranges', 0) <= 0:
            return 'LiDAR-Scan ungueltig'
        if self._scope_map_binding(
                require_exact_map=(self._state == 'idle')) is None:
            return 'Scope nicht an aktuelle Karte/SLAM-Session gebunden'
        pose = self._latest.get('map_pose')
        if not isinstance(pose, dict) or pose.get('frame_id') != 'map':
            return 'aktuelle Pose fehlt oder ist nicht im Map-Frame'
        if not disk_in_polygon(
                pose['x'], pose['y'], FOOTPRINT_RADIUS_M, self.scope_polygon):
            return 'gepaddeter Footprint liegt ausserhalb des WE-Scopes'
        if not self._motion_tf_authorized():
            return 'TF map/base_link oder odom/base_link nicht frisch'
        return None

    def _motion_tf_authorized(self):
        try:
            for target, source, max_age in (
                    ('map', 'base_link', TF_TIMEOUT_S),
                    ('odom', 'base_link', 0.2)):
                transform = self._tf_buffer.lookup_transform(
                    target, source, rclpy.time.Time())
                stamp = transform.header.stamp.sec + transform.header.stamp.nanosec * 1e-9
                if not 0.0 <= self.get_clock().now().nanoseconds * 1e-9 - stamp <= max_age:
                    return False
        except TransformException:
            return False
        return True

    def _start(self, _request, response):
        if self._test_started_once or self._state != 'idle':
            response.success = False
            response.message = 'Dieser Prozess erlaubt genau einen Diagnoselauf.'
            return response
        if not self.external_hardware_halt_attested:
            response.success = False
            response.message = (
                'Labormodus gesperrt: unabhaengigen Hardware-Halt vor Ort '
                'manuell bestaetigen.')
            return response
        failure = self._health_failure()
        if failure:
            response.success = False
            response.message = failure
            return response
        pose = self._latest['map_pose']
        if not disk_in_polygon(
                pose['x'] + TEST_DISTANCE_M * math.cos(pose['yaw']),
                pose['y'] + TEST_DISTANCE_M * math.sin(pose['yaw']),
                FOOTPRINT_RADIUS_M, self.scope_polygon):
            response.success = False
            response.message = '0,25-m-Testsegment verlaesst den verifizierten Scope.'
            return response
        steps = max(1, math.ceil(TEST_DISTANCE_M / 0.025))
        if any(not disk_in_polygon(
                pose['x'] + TEST_DISTANCE_M * step / steps * math.cos(pose['yaw']),
                pose['y'] + TEST_DISTANCE_M * step / steps * math.sin(pose['yaw']),
                FOOTPRINT_RADIUS_M, self.scope_polygon)
                for step in range(steps + 1)):
            response.success = False
            response.message = 'Gepaddeter Footprint verlaesst waehrend der Fahrt den Scope.'
            return response
        self._bound_fingerprint = self._scope_map_binding()
        self._bound_frame = 'map'
        self._bound_session = self.session_id
        self._start_pose = (pose['x'], pose['y'])
        self._start_yaw = pose['yaw']
        self._state = PHASES[0]
        self._phase_started = time.monotonic()
        self._test_started_once = True
        log_dir = Path.home() / '.local' / 'share' / 'amadeus' / 'tests'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / (
            'stage3-hwt601-motion-' + datetime.now(timezone.utc).strftime(
                '%Y%m%dT%H%M%SZ') + '.jsonl')
        self._log_stream = log_path.open('x', encoding='utf-8', buffering=1)
        self._record('binding', {
            'scope_id': self.scope_id,
            'session_id': self._bound_session,
            'map_frame': self._bound_frame,
            'map_fingerprint_at_start': self._bound_fingerprint,
            'start_x': pose['x'], 'start_y': pose['y'],
            'start_yaw': pose['yaw'],
            'sequence': list(PHASES),
        })
        response.success = True
        response.message = f'Diagnose gestartet; Evidenz: {log_path}'
        self.get_logger().warning(response.message)
        return response

    def _enter(self, state):
        self._state = state
        self._phase_started = time.monotonic()
        self._stop_stable_since = None
        self._record('phase', {'state': state})

    def _publish_command(self, vx=0.0, wz=0.0):
        command = Twist()
        command.linear.x = vx
        command.angular.z = wz
        self._active_pub.publish(Bool(data=True))
        self._command_pub.publish(command)
        self._last_nonzero_requested = abs(vx) > 1e-6 or abs(wz) > 1e-6

    def _finish(self, state, message):
        self._publish_command()
        self._active_pub.publish(Bool(data=False))
        self._state = state
        self._result_message = message
        self._status_pub.publish(String(data=json.dumps({
            'state': state, 'phase': state, 'scope_id': self.scope_id,
            'lab_mode': LAB_MODE,
            'external_hardware_halt_attested': (
                self.external_hardware_halt_attested),
            'session_id': self._bound_session,
            'map_fingerprint': self._bound_fingerprint,
            'message': message,
            'log_path': self._log_stream.name if self._log_stream else None,
        }, separators=(',', ':'))))
        self._record('result', {'state': state, 'message': message,
                                'log_path': self._log_stream.name
                                if self._log_stream else None})
        if self._log_stream is not None:
            self._log_stream.close()
            self._log_stream = None
        self.get_logger().warning(f'Stage-3-Bewegungstest {state}: {message}')

    def _stationary(self):
        base = self._latest.get('base')
        odom = self._latest.get('odom')
        commands = [self._latest.get(name) for name in (
            'gate_out', 'smoother_out', 'collision_monitor_out')]
        if (not isinstance(base, dict) or not isinstance(odom, dict)
                or any(not self._fresh(name, 0.5) for name in (
                    'gate_out', 'smoother_out', 'collision_monitor_out'))):
            return False
        rpms = (base.get('meas_motor_rpm_left'), base.get('meas_motor_rpm_right'))
        return (
            all(value is not None and abs(float(value)) <= 1.0 for value in rpms)
            and abs(float(odom.get('vx', math.inf))) <= 0.01
            and abs(float(odom.get('wz', math.inf))) <= 0.02
            and all(isinstance(item, dict)
                    and abs(float(item.get('vx', math.inf))) <= 1e-4
                    and abs(float(item.get('wz', math.inf))) <= 1e-4
                    for item in commands)
        )

    def _tick(self):
        now = time.monotonic()
        if self._state in ('idle', 'complete', 'aborted'):
            self._active_pub.publish(Bool(data=False))
            return
        failure = self._health_failure()
        if failure:
            self._finish('aborted', failure)
            return
        cm = self._latest.get('collision_monitor_out')
        if self._last_nonzero_requested and isinstance(cm, dict):
            cm_zero = (abs(float(cm.get('vx', math.inf))) <= 1e-4
                       and abs(float(cm.get('wz', math.inf))) <= 1e-4)
            if cm_zero:
                self._last_collision_zero_since = (
                    self._last_collision_zero_since or now)
                if now - self._last_collision_zero_since >= 0.6:
                    self._finish(
                        'aborted',
                        'Collision Monitor/Fahrtor begrenzt den Bewegungswunsch auf Null')
                    return
            else:
                self._last_collision_zero_since = None
        if now - self._phase_started > PHASE_TIMEOUT_S:
            self._finish('aborted', f'Phase {self._state} abgelaufen')
            return
        pose = self._latest['map_pose']
        x, y, yaw = pose['x'], pose['y'], pose['yaw']
        if self._scope_map_binding(require_exact_map=False) is None:
            self._finish('aborted', 'Karte/Scope-Bindung verloren')
            return

        if self._state == 'forward':
            dx, dy = x - self._start_pose[0], y - self._start_pose[1]
            progress = dx * math.cos(self._start_yaw) + dy * math.sin(self._start_yaw)
            lateral = -dx * math.sin(self._start_yaw) + dy * math.cos(self._start_yaw)
            if progress >= TEST_DISTANCE_M:
                self._enter('stop_after_forward')
                self._publish_command()
            elif progress < -0.02 or abs(lateral) > 0.05:
                self._finish('aborted', 'Translation verlaesst Vorwaerts-Testachse')
            else:
                self._publish_command(LINEAR_MPS, 0.0)
        elif self._state in ('stop_after_forward', 'stop_after_positive', 'stop_final'):
            self._publish_command()
            if self._stationary():
                self._stop_stable_since = self._stop_stable_since or now
                if now - self._stop_stable_since >= STOP_CONFIRM_S:
                    if self._state == 'stop_after_forward':
                        self._turn_origin = yaw
                        self._enter('turn_positive')
                    elif self._state == 'stop_after_positive':
                        self._turn_negative_origin = yaw
                        self._enter('turn_negative')
                    else:
                        self._finish('complete', 'Feste Sequenz und drei Stillstaende bestaetigt')
            else:
                self._stop_stable_since = None
                if now - self._phase_started > STOP_TIMEOUT_S:
                    self._finish('aborted', 'Stillstand nicht vollstaendig bestaetigt')
        elif self._state == 'turn_positive':
            progress = directed_turn_progress(self._turn_origin, yaw, 1.0)
            if progress < -math.radians(3.0):
                self._finish('aborted', 'Drehung entgegen der Sollrichtung')
            elif progress > TEST_TURN_RAD + math.radians(5.0):
                self._finish('aborted', 'Drehung ueberschreitet Testumfang')
            elif progress >= TEST_TURN_RAD:
                self._enter('stop_after_positive')
                self._publish_command()
            else:
                self._publish_command(0.0, ANGULAR_RADPS)
        elif self._state == 'turn_negative':
            progress = directed_turn_progress(
                self._turn_negative_origin, yaw, -1.0)
            if progress < -math.radians(3.0):
                self._finish('aborted', 'Rueckdrehung entgegen der Sollrichtung')
            elif progress > TEST_TURN_RAD + math.radians(5.0):
                self._finish('aborted', 'Rueckdrehung ueberschreitet Testumfang')
            elif progress >= TEST_TURN_RAD:
                self._enter('stop_final')
                self._publish_command()
            else:
                self._publish_command(0.0, -ANGULAR_RADPS)
        self._status_pub.publish(String(data=json.dumps({
            'state': self._state,
            'lab_mode': LAB_MODE,
            'external_hardware_halt_attested': (
                self.external_hardware_halt_attested),
            'scope_id': self.scope_id,
            'session_id': self._bound_session,
            'map_fingerprint': self._bound_fingerprint,
            'phase': self._state,
            'message': self._result_message,
        }, separators=(',', ':'))))


def _stamp(msg):
    stamp = msg.header.stamp
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = Stage3MotionDiagnostic()
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if node is not None:
            if node._state not in ('idle', 'complete', 'aborted'):
                node._finish('aborted', 'Prozess-Shutdown waehrend Bewegungstest')
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
