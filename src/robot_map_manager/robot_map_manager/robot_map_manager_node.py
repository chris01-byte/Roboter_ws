#!/usr/bin/env python3
"""ROS-2-Humble-Node für robuste Kartenaufnahme und sichere Speicherung."""

from __future__ import annotations

from pathlib import Path
import math
import time
from typing import Any, Optional

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from rclpy.time import Time
from std_msgs.msg import String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformException, TransformListener

from robot_map_manager.map_core import (
    BoundedRequestCache,
    CommandValidationError,
    MapCommand,
    MapOrigin,
    MapRepository,
    MapSnapshot,
    MapStorageError,
    MapValidationError,
    MinimumIntervalGuard,
    RawDuplicateGuard,
    RequestIDConflict,
    StoragePolicy,
    json_message,
    parse_cached_command_response,
    parse_command_json,
    raw_cell_digest,
    validate_grid_shape_and_length,
    validate_map_name,
    validate_quaternion,
    validate_transform_timestamp,
)


class RobotMapManager(Node):
    """Hält die jüngste gültige Karte und speichert nur auf expliziten Befehl."""

    def __init__(self) -> None:
        super().__init__("robot_map_manager")

        self.declare_parameter("map_topic", "/map")
        self.declare_parameter("command_topic", "/robot_map_manager/command_json")
        self.declare_parameter("status_topic", "/robot_map_manager/status_json")
        self.declare_parameter("save_service", "/robot_map_manager/save_map")
        self.declare_parameter("pose_topic", "/robot_map_manager/robot_pose")
        self.declare_parameter(
            "storage_directory",
            "~/.local/share/amadeus/maps",
        )
        self.declare_parameter("default_map_name", "amadeus")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("pose_publish_rate_hz", 5.0)
        self.declare_parameter("maximum_dynamic_tf_age_s", 1.0)
        self.declare_parameter("status_publish_period_s", 2.0)
        self.declare_parameter("maximum_list_entries", 20)
        self.declare_parameter("minimum_list_interval_s", 10.0)
        self.declare_parameter("maximum_list_verify_bytes", 134_217_728)
        self.declare_parameter("minimum_save_interval_s", 5.0)
        self.declare_parameter("minimum_free_space_bytes", 536_870_912)
        self.declare_parameter("maximum_versions_per_map", 100)
        self.declare_parameter("maximum_total_storage_bytes", 2_147_483_648)
        self.declare_parameter("maximum_map_names", 16)
        self.declare_parameter("staging_cleanup_min_age_s", 3600.0)
        self.declare_parameter("staging_cleanup_max_entries", 32)
        self.declare_parameter("request_cache_size", 128)
        self.declare_parameter("raw_duplicate_window_s", 1.0)

        self.map_topic = self._nonempty_parameter("map_topic")
        self.command_topic = self._nonempty_parameter("command_topic")
        self.status_topic = self._nonempty_parameter("status_topic")
        self.save_service_name = self._nonempty_parameter("save_service")
        self.pose_topic = self._nonempty_parameter("pose_topic")
        self.base_frame = self._frame_parameter("base_frame")

        try:
            self.default_map_name = validate_map_name(
                self.get_parameter("default_map_name").value
            )
        except MapValidationError as error:
            raise RuntimeError(f"Ungültiger Parameter default_map_name: {error}") from error

        self.pose_publish_rate_hz = self._positive_float_parameter(
            "pose_publish_rate_hz"
        )
        self.maximum_dynamic_tf_age_s = self._positive_float_parameter(
            "maximum_dynamic_tf_age_s"
        )
        self.status_publish_period_s = self._positive_float_parameter(
            "status_publish_period_s"
        )
        self.maximum_list_entries = self._integer_parameter(
            "maximum_list_entries",
            minimum=1,
            maximum=100,
        )
        request_cache_size = self._integer_parameter(
            "request_cache_size",
            minimum=1,
            maximum=10_000,
        )
        raw_duplicate_window_s = self._nonnegative_float_parameter(
            "raw_duplicate_window_s"
        )
        storage_policy = StoragePolicy(
            minimum_save_interval_s=self._nonnegative_float_parameter(
                "minimum_save_interval_s"
            ),
            minimum_list_interval_s=self._nonnegative_float_parameter(
                "minimum_list_interval_s"
            ),
            maximum_list_verify_bytes=self._integer_parameter(
                "maximum_list_verify_bytes",
                minimum=1,
                maximum=2_147_483_648,
            ),
            minimum_free_space_bytes=self._integer_parameter(
                "minimum_free_space_bytes",
                minimum=0,
            ),
            maximum_versions_per_map=self._integer_parameter(
                "maximum_versions_per_map",
                minimum=1,
            ),
            maximum_total_storage_bytes=self._integer_parameter(
                "maximum_total_storage_bytes",
                minimum=1,
            ),
            maximum_map_names=self._integer_parameter(
                "maximum_map_names",
                minimum=1,
                maximum=10_000,
            ),
            staging_cleanup_min_age_s=self._nonnegative_float_parameter(
                "staging_cleanup_min_age_s"
            ),
            staging_cleanup_max_entries=self._integer_parameter(
                "staging_cleanup_max_entries",
                minimum=0,
                maximum=1000,
            ),
        ).validated()

        storage_value = self._nonempty_parameter("storage_directory")
        storage_root = Path(storage_value).expanduser()
        if not storage_root.is_absolute():
            raise RuntimeError(
                "Parameter storage_directory muss nach '~'-Expansion absolut sein."
            )
        self.repository = MapRepository(
            storage_root,
            default_name=self.default_map_name,
            policy=storage_policy,
        )
        self.request_cache = BoundedRequestCache(request_cache_size)
        self.raw_duplicate_guard = RawDuplicateGuard(raw_duplicate_window_s)
        self.list_interval_guard = MinimumIntervalGuard(
            storage_policy.minimum_list_interval_s
        )

        self._latest_map: Optional[MapSnapshot] = None
        self._latest_fingerprint: Optional[str] = None
        self._latest_source: Optional[str] = None
        self._last_map_received_wall: Optional[float] = None
        self._last_map_received_iso: Optional[str] = None
        self._last_saved: Optional[dict[str, Any]] = None
        self._last_operation = "startup"
        self._last_error: Optional[str] = None
        self._last_validation_error: Optional[str] = None
        self._last_status_json: Optional[str] = None
        self._accepted_maps = 0
        self._duplicate_maps = 0
        self._early_duplicate_maps = 0
        self._rejected_maps = 0
        self._idempotent_replays = 0
        self._list_rate_limited = 0
        self._pose_available = False
        self._pose_error: Optional[str] = "Noch keine Transformation empfangen."
        self._last_pose_iso: Optional[str] = None
        self._pose_target_frame: Optional[str] = None
        self._pose_zero_stamp_static_assumption: Optional[bool] = None
        self._pose_tf_age_s: Optional[float] = None
        self._pose_tf_stamp_ns: Optional[int] = None
        self._last_tf_warning_wall = 0.0

        transient_map_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        volatile_map_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        status_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self.status_publisher = self.create_publisher(
            String,
            self.status_topic,
            status_qos,
        )
        self.pose_publisher = self.create_publisher(
            PoseStamped,
            self.pose_topic,
            QoSProfile(depth=1),
        )
        self.transient_map_subscription = self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            lambda message: self._on_map(message, "transient_reliable"),
            transient_map_qos,
        )
        self.volatile_map_subscription = self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            lambda message: self._on_map(message, "volatile_best_effort"),
            volatile_map_qos,
        )
        self.command_subscription = self.create_subscription(
            String,
            self.command_topic,
            self._on_command,
            QoSProfile(depth=10),
        )
        self.save_service = self.create_service(
            Trigger,
            self.save_service_name,
            self._on_save_trigger,
        )

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pose_timer = self.create_timer(
            1.0 / self.pose_publish_rate_hz,
            self._publish_robot_pose,
        )
        self.status_timer = self.create_timer(
            self.status_publish_period_s,
            self._publish_periodic_status,
        )

        self._publish_status(
            event="status",
            ok=True,
            message="robot_map_manager bereit; warte auf eine gültige /map.",
        )
        self.get_logger().info(
            "robot_map_manager bereit: "
            f"{self.map_topic} -> {self.repository.root}; "
            f"Pose <aktueller Kartenframe>->{self.base_frame} "
            f"auf {self.pose_topic}."
        )

    def _on_map(self, message: OccupancyGrid, source: str) -> None:
        raw_seen = time.monotonic()
        try:
            (
                raw_signature,
                has_ros_identity,
                compact_fallback,
            ) = self._raw_map_signature(message)
            if self.raw_duplicate_guard.is_duplicate(
                raw_signature,
                source=source,
                now=raw_seen,
                has_ros_identity=has_ros_identity,
            ):
                now = time.time()
                self._last_map_received_wall = now
                self._last_map_received_iso = self._iso_time(now)
                self._last_error = None
                self._duplicate_maps += 1
                self._early_duplicate_maps += 1
                self._last_operation = "map_duplicate"
                return

            stamp_ns = (
                int(message.header.stamp.sec) * 1_000_000_000
                + int(message.header.stamp.nanosec)
            )
            origin = message.info.origin
            snapshot = MapSnapshot.from_values(
                width=message.info.width,
                height=message.info.height,
                resolution=message.info.resolution,
                frame_id=message.header.frame_id,
                origin=MapOrigin(
                    position_x=origin.position.x,
                    position_y=origin.position.y,
                    position_z=origin.position.z,
                    orientation_x=origin.orientation.x,
                    orientation_y=origin.orientation.y,
                    orientation_z=origin.orientation.z,
                    orientation_w=origin.orientation.w,
                ),
                cells=(
                    message.data
                    if compact_fallback is None
                    else compact_fallback
                ),
                source_stamp_ns=stamp_ns,
            )
        except (MapValidationError, TypeError, ValueError, OverflowError) as error:
            self._rejected_maps += 1
            self._last_validation_error = f"Ungültige Karte verworfen: {error}"
            self._last_error = self._last_validation_error
            self._last_operation = "map_rejected"
            self.get_logger().warning(self._last_error)
            self._publish_status(
                event="map_rejected",
                ok=False,
                message=self._last_error,
            )
            return

        self.raw_duplicate_guard.mark_valid(
            raw_signature,
            source=source,
            now=raw_seen,
        )
        now = time.time()
        self._last_map_received_wall = now
        self._last_map_received_iso = self._iso_time(now)
        self._last_error = None
        if snapshot.fingerprint == self._latest_fingerprint:
            self._duplicate_maps += 1
            self._last_operation = "map_duplicate"
            return

        self._latest_map = snapshot
        self._latest_fingerprint = snapshot.fingerprint
        self._latest_source = source
        self._pose_available = False
        self._pose_target_frame = snapshot.frame_id
        self._pose_zero_stamp_static_assumption = None
        self._pose_tf_age_s = None
        self._pose_tf_stamp_ns = None
        self._pose_error = (
            "Warte auf die Pose im Frame des aktuellen Kartensnapshots."
        )
        self._accepted_maps += 1
        self._last_error = None
        self._last_operation = "map_received"
        self._publish_status(
            event="map_received",
            ok=True,
            message=(
                f"Gültige Karte empfangen: {snapshot.width} × {snapshot.height} "
                f"über {source}."
            ),
        )

    @staticmethod
    def _raw_map_signature(
        message: OccupancyGrid,
    ) -> tuple[tuple[Any, ...], bool, Optional[bytes]]:
        stamp_sec = int(message.header.stamp.sec)
        stamp_nanosec = int(message.header.stamp.nanosec)
        load_sec = int(message.info.map_load_time.sec)
        load_nanosec = int(message.info.map_load_time.nanosec)
        stamp_ns = stamp_sec * 1_000_000_000 + stamp_nanosec
        load_ns = load_sec * 1_000_000_000 + load_nanosec
        width = message.info.width
        height = message.info.height
        try:
            raw_length = len(message.data)
        except (TypeError, OverflowError) as error:
            raise MapValidationError(
                "Kartendaten müssen eine bekannte Länge besitzen."
            ) from error
        validate_grid_shape_and_length(width, height, raw_length)
        cell_count, cell_digest, compact_fallback = raw_cell_digest(message.data)
        origin = message.info.origin
        signature = (
            stamp_sec,
            stamp_nanosec,
            load_sec,
            load_nanosec,
            message.header.frame_id,
            width,
            height,
            message.info.resolution,
            origin.position.x,
            origin.position.y,
            origin.position.z,
            origin.orientation.x,
            origin.orientation.y,
            origin.orientation.z,
            origin.orientation.w,
            cell_count,
            cell_digest,
        )
        return signature, bool(stamp_ns or load_ns), compact_fallback

    def _on_command(self, message: String) -> None:
        try:
            command = parse_command_json(message.data)
        except CommandValidationError as error:
            self._last_error = str(error)
            self._last_operation = "command_rejected"
            self._publish_status(
                event="command_result",
                ok=False,
                message=str(error),
            )
            return

        signature = self._command_signature(command)
        if command.request_id is not None:
            try:
                cached_response = self.request_cache.lookup(
                    command.request_id,
                    signature,
                )
            except RequestIDConflict as error:
                self._last_error = str(error)
                self._last_operation = "command_rejected"
                self._publish_status(
                    event="command_result",
                    ok=False,
                    command=command.command,
                    request_id=command.request_id,
                    message=str(error),
                )
                return
            if cached_response is not None:
                try:
                    cached_result = parse_cached_command_response(
                        cached_response,
                        expected_request_id=command.request_id,
                        expected_command=command.command,
                    )
                except MapStorageError as error:
                    self._last_error = str(error)
                    self._last_operation = "command_replay_rejected"
                    self._publish_status(
                        event="command_result",
                        ok=False,
                        command=command.command,
                        request_id=command.request_id,
                        message=str(error),
                    )
                    return
                self._idempotent_replays += 1
                replay = cached_result.publish_kwargs(
                    current_status_ok=self._last_error is None
                )
                # Das Kommandoergebnis bleibt idempotent. Der globale Zustand
                # (map/storage/pose/time/counters) wird dagegen immer frisch in
                # _publish_status aufgebaut und niemals aus dem Cache replayt.
                self._publish_status(**replay)
                return

        if command.command == "save":
            self._save_map(
                name=command.name or self.default_map_name,
                request_id=command.request_id,
                origin="command",
            )
        elif command.command == "list":
            allowed, remaining = self.list_interval_guard.acquire(
                now=time.monotonic()
            )
            if allowed:
                self._list_maps(command)
            else:
                self._list_rate_limited += 1
                self._last_error = (
                    "Globale Listen-Abkühlzeit aktiv; "
                    f"{remaining:.3f} s verbleibend."
                )
                self._last_operation = "list_rate_limited"
                self._publish_status(
                    event="list_result",
                    ok=False,
                    command="list",
                    request_id=command.request_id,
                    message=self._last_error,
                    extra={
                        "list_policy": {
                            "minimum_list_interval_s": (
                                self.repository.policy.minimum_list_interval_s
                            ),
                            "retry_after_seconds": remaining,
                        }
                    },
                )
        else:
            self._last_operation = "status"
            self._publish_status(
                event="status",
                ok=self._last_error is None,
                command="status",
                request_id=command.request_id,
                message="Aktueller Kartenstatus.",
            )

        if command.request_id is not None and self._last_status_json is not None:
            cached_result = parse_cached_command_response(
                self._last_status_json,
                expected_request_id=command.request_id,
                expected_command=command.command,
            )
            self.request_cache.store(
                command.request_id,
                signature,
                cached_result.as_cache_json(),
            )

    def _command_signature(self, command: MapCommand) -> tuple[Any, ...]:
        if command.command == "save":
            return ("save", command.name or self.default_map_name)
        if command.command == "list":
            return ("list", command.name)
        return ("status",)

    def _on_save_trigger(
        self,
        _request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        saved, message = self._save_map(
            name=self.default_map_name,
            request_id=None,
            origin="trigger_service",
        )
        response.success = saved
        response.message = message
        return response

    def _save_map(
        self,
        *,
        name: str,
        request_id: Optional[str],
        origin: str,
    ) -> tuple[bool, str]:
        snapshot = self._latest_map
        if snapshot is None:
            message = "Keine gültige Karte empfangen; Speicherung nicht möglich."
            self._last_error = message
            self._last_operation = "save_failed"
            self._publish_status(
                event="save_result",
                ok=False,
                command="save",
                request_id=request_id,
                message=message,
                extra={"requested_name": name, "origin": origin},
            )
            return False, message

        try:
            saved = self.repository.save(snapshot, name=name)
        except (MapStorageError, MapValidationError) as error:
            message = f"Karte konnte nicht gespeichert werden: {error}"
            self._last_error = message
            self._last_operation = "save_failed"
            self._publish_status(
                event="save_result",
                ok=False,
                command="save",
                request_id=request_id,
                message=message,
                extra={"requested_name": name, "origin": origin},
            )
            return False, message

        self._last_saved = saved.as_dict()
        self._last_error = None
        self._last_operation = "save"
        message = f"Karte '{saved.name}' als Version {saved.version} gespeichert."
        self._publish_status(
            event="save_result",
            ok=True,
            command="save",
            request_id=request_id,
            message=message,
            extra={"saved": saved.as_dict(), "origin": origin},
        )
        return True, message

    def _list_maps(self, command: MapCommand) -> None:
        try:
            report = self.repository.list_versions_with_report(
                name=command.name,
                limit=self.maximum_list_entries,
            )
        except (MapStorageError, MapValidationError) as error:
            self._last_error = str(error)
            self._last_operation = "list_failed"
            self._publish_status(
                event="list_result",
                ok=False,
                command="list",
                request_id=command.request_id,
                message=f"Kartenliste konnte nicht gelesen werden: {error}",
            )
            return

        self._last_error = None
        self._last_operation = "list"
        truncation_note = (
            " Ergebnis wurde durch Schutzlimits gekürzt."
            if report.truncated
            else ""
        )
        self._publish_status(
            event="list_result",
            ok=True,
            command="list",
            request_id=command.request_id,
            message=(
                f"{len(report.records)} gespeicherte Kartenversionen gefunden."
                f"{truncation_note}"
            ),
            extra={
                "maps": [record.as_dict() for record in report.records],
                "limit": self.maximum_list_entries,
                "name_filter": command.name,
                "list_policy": report.policy_dict(),
            },
        )

    def _publish_robot_pose(self) -> None:
        snapshot = self._latest_map
        if snapshot is None:
            self._pose_available = False
            self._pose_target_frame = None
            self._pose_zero_stamp_static_assumption = None
            self._pose_tf_age_s = None
            self._pose_tf_stamp_ns = None
            self._pose_error = (
                "Keine gültige Karte; Ziel-Frame für die Pose ist unbekannt."
            )
            return

        target_frame = snapshot.frame_id
        self._pose_target_frame = target_frame
        self._pose_zero_stamp_static_assumption = None
        self._pose_tf_age_s = None
        self._pose_tf_stamp_ns = None
        try:
            transform = self.tf_buffer.lookup_transform(
                target_frame,
                self.base_frame,
                Time(),
            )
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            position = (
                float(translation.x),
                float(translation.y),
                float(translation.z),
            )
            if not all(math.isfinite(value) for value in position):
                raise MapValidationError("Transformation enthält ungültige Koordinaten.")
            quaternion = validate_quaternion(
                (rotation.x, rotation.y, rotation.z, rotation.w)
            )
            stamp_ns = (
                int(transform.header.stamp.sec) * 1_000_000_000
                + int(transform.header.stamp.nanosec)
            )
            now_ns = self.get_clock().now().nanoseconds
            self._pose_tf_stamp_ns = stamp_ns
            if stamp_ns != 0:
                self._pose_tf_age_s = (
                    now_ns - stamp_ns
                ) / 1_000_000_000.0
            uses_zero_stamp_convention, dynamic_age = validate_transform_timestamp(
                stamp_ns=stamp_ns,
                now_ns=now_ns,
                maximum_age_s=self.maximum_dynamic_tf_age_s,
            )
            self._pose_zero_stamp_static_assumption = (
                uses_zero_stamp_convention
            )
            self._pose_tf_age_s = dynamic_age

            pose = PoseStamped()
            pose.header.stamp = transform.header.stamp
            pose.header.frame_id = target_frame
            pose.pose.position.x = position[0]
            pose.pose.position.y = position[1]
            pose.pose.position.z = position[2]
            pose.pose.orientation.x = quaternion[0]
            pose.pose.orientation.y = quaternion[1]
            pose.pose.orientation.z = quaternion[2]
            pose.pose.orientation.w = quaternion[3]
            self.pose_publisher.publish(pose)

            self._pose_available = True
            self._pose_error = None
            self._last_pose_iso = self._iso_time(time.time())
        except (
            TransformException,
            MapValidationError,
            TypeError,
            ValueError,
            OverflowError,
        ) as error:
            self._pose_available = False
            self._pose_error = str(error)
            now = time.monotonic()
            if now - self._last_tf_warning_wall >= 10.0:
                self.get_logger().warning(
                    f"Pose {target_frame}->{self.base_frame} "
                    f"nicht verfügbar: {error}"
                )
                self._last_tf_warning_wall = now

    def _publish_periodic_status(self) -> None:
        self._publish_status(
            event="status",
            ok=self._last_error is None,
            message="Periodischer Kartenstatus.",
        )

    def _publish_status(
        self,
        *,
        event: str,
        ok: bool,
        message: str,
        command: Optional[str] = None,
        request_id: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> str:
        now = time.time()
        age = (
            None
            if self._last_map_received_wall is None
            else max(0.0, now - self._last_map_received_wall)
        )
        payload: dict[str, Any] = {
            "schema_version": 1,
            "event": event,
            "ok": ok,
            "command": command,
            "request_id": request_id,
            "message": message,
            "time": now,
            "last_operation": self._last_operation,
            "last_error": self._last_error,
            "map": {
                "available": self._latest_map is not None,
                "snapshot_available": self._latest_map is not None,
                "publisher_count": self.count_publishers(self.map_topic),
                "last_received": self._last_map_received_iso,
                "age_seconds": age,
                "source": self._latest_source,
                "summary": (
                    None if self._latest_map is None else self._latest_map.summary()
                ),
                "last_validation_error": self._last_validation_error,
            },
            "pose": {
                "available": self._pose_available,
                "topic": self.pose_topic,
                "target_frame": self._pose_target_frame,
                "snapshot_frame": (
                    None
                    if self._latest_map is None
                    else self._latest_map.frame_id
                ),
                "base_frame": self.base_frame,
                "last_published": self._last_pose_iso,
                "zero_stamp_static_assumption": (
                    self._pose_zero_stamp_static_assumption
                ),
                "tf_stamp_ns": self._pose_tf_stamp_ns,
                "tf_age_seconds": self._pose_tf_age_s,
                "maximum_dynamic_tf_age_s": self.maximum_dynamic_tf_age_s,
                "error": self._pose_error,
            },
            "storage": {
                "root": str(self.repository.root),
                "default_name": self.default_map_name,
                "last_saved": self._last_saved,
                "policy": {
                    "minimum_save_interval_s": (
                        self.repository.policy.minimum_save_interval_s
                    ),
                    "minimum_list_interval_s": (
                        self.repository.policy.minimum_list_interval_s
                    ),
                    "maximum_list_verify_bytes": (
                        self.repository.policy.maximum_list_verify_bytes
                    ),
                    "maximum_list_entries": self.maximum_list_entries,
                    "minimum_free_space_bytes": (
                        self.repository.policy.minimum_free_space_bytes
                    ),
                    "maximum_versions_per_map": (
                        self.repository.policy.maximum_versions_per_map
                    ),
                    "maximum_total_storage_bytes": (
                        self.repository.policy.maximum_total_storage_bytes
                    ),
                    "maximum_map_names": (
                        self.repository.policy.maximum_map_names
                    ),
                },
                "startup_staging_cleanup": {
                    "removed": self.repository.cleanup_removed,
                    "errors": self.repository.cleanup_errors,
                },
            },
            "counters": {
                "accepted_maps": self._accepted_maps,
                "duplicate_maps": self._duplicate_maps,
                "early_qos_duplicates": self._early_duplicate_maps,
                "rejected_maps": self._rejected_maps,
                "idempotent_replays": self._idempotent_replays,
                "list_rate_limited": self._list_rate_limited,
                "request_cache_entries": len(self.request_cache),
            },
        }
        if extra:
            payload.update(extra)
        serialized = json_message(payload)
        self._last_status_json = serialized
        self.status_publisher.publish(String(data=serialized))
        return serialized

    def _nonempty_parameter(self, name: str) -> str:
        value = self.get_parameter(name).value
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Parameter {name} muss eine nichtleere Zeichenkette sein.")
        return value.strip()

    def _frame_parameter(self, name: str) -> str:
        value = self._nonempty_parameter(name)
        if len(value) > 128 or any(ord(character) < 0x20 for character in value):
            raise RuntimeError(f"Parameter {name} enthält eine ungültige Frame-ID.")
        return value

    def _positive_float_parameter(self, name: str) -> float:
        value = self.get_parameter(name).value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"Parameter {name} muss eine positive Zahl sein.")
        result = float(value)
        if not (result > 0.0 and result < float("inf")):
            raise RuntimeError(f"Parameter {name} muss eine positive endliche Zahl sein.")
        return result

    def _nonnegative_float_parameter(self, name: str) -> float:
        value = self.get_parameter(name).value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"Parameter {name} muss eine nichtnegative Zahl sein.")
        result = float(value)
        if not (result >= 0.0 and result < float("inf")):
            raise RuntimeError(
                f"Parameter {name} muss eine nichtnegative endliche Zahl sein."
            )
        return result

    def _integer_parameter(
        self,
        name: str,
        *,
        minimum: int,
        maximum: Optional[int] = None,
    ) -> int:
        value = self.get_parameter(name).value
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
            or (maximum is not None and value > maximum)
        ):
            range_description = (
                f"mindestens {minimum}"
                if maximum is None
                else f"zwischen {minimum} und {maximum}"
            )
            raise RuntimeError(
                f"Parameter {name} muss eine Ganzzahl "
                f"{range_description} sein."
            )
        return value

    @staticmethod
    def _iso_time(value: float) -> str:
        from datetime import datetime, timezone

        return (
            datetime.fromtimestamp(value, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node: Optional[RobotMapManager] = None
    try:
        node = RobotMapManager()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
