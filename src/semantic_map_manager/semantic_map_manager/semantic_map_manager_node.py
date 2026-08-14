#!/usr/bin/env python3
"""ROS-2-Humble-Node für manuell deklarierte semantische Räume.

Der Node publiziert ausschließlich Metadaten. Er besitzt weder ``cmd_vel``-
noch Nav2-/Action-Schnittstellen und kann daher keine Bewegung auslösen.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from std_msgs.msg import String

from semantic_map_manager.semantic_core import (
    activate_map_observation,
    CommandValidationError,
    DEFAULT_MAXIMUM_REVISIONS_PER_MAP,
    DEFAULT_MAXIMUM_STORAGE_BYTES,
    DEFAULT_MINIMUM_FREE_SPACE_BYTES,
    DEFAULT_REQUEST_CACHE_BYTES,
    DEFAULT_REQUEST_CACHE_ENTRIES,
    MapManagerObservation,
    MapMismatchError,
    MutationResult,
    RequestIDConflict,
    RequestSignatureCache,
    RevisionConflictError,
    SemanticCommand,
    SemanticDocument,
    SemanticMapRepository,
    SemanticStorageError,
    SemanticValidationError,
    command_signature,
    json_message,
    map_status_is_fresh,
    parse_command_json,
    parse_map_manager_status,
)


class SemanticMapManager(Node):
    """Bindet semantische Overlays fail-closed an eine gespeicherte Karte."""

    def __init__(self) -> None:
        super().__init__("semantic_map_manager")

        self.declare_parameter("command_topic", "/semantic_map/command_json")
        self.declare_parameter("status_topic", "/semantic_map/status_json")
        self.declare_parameter("catalog_topic", "/semantic/catalog_json")
        self.declare_parameter(
            "map_manager_status_topic",
            "/robot_map_manager/status_json",
        )
        self.declare_parameter(
            "storage_directory",
            "~/.local/share/amadeus/semantic_maps",
        )
        self.declare_parameter("status_publish_period_s", 2.0)
        self.declare_parameter("map_status_stale_timeout_s", 6.0)
        self.declare_parameter(
            "max_revisions_per_map", DEFAULT_MAXIMUM_REVISIONS_PER_MAP
        )
        self.declare_parameter("max_storage_bytes", DEFAULT_MAXIMUM_STORAGE_BYTES)
        self.declare_parameter(
            "min_free_space_bytes", DEFAULT_MINIMUM_FREE_SPACE_BYTES
        )
        self.declare_parameter("request_cache_size", DEFAULT_REQUEST_CACHE_ENTRIES)
        self.declare_parameter("request_cache_max_bytes", DEFAULT_REQUEST_CACHE_BYTES)

        self.command_topic = self._nonempty_parameter("command_topic")
        self.status_topic = self._nonempty_parameter("status_topic")
        self.catalog_topic = self._nonempty_parameter("catalog_topic")
        self.map_manager_status_topic = self._nonempty_parameter(
            "map_manager_status_topic"
        )
        storage_value = self._nonempty_parameter("storage_directory")
        storage_root = Path(storage_value).expanduser()
        if not storage_root.is_absolute():
            raise RuntimeError(
                "Parameter storage_directory muss nach '~'-Expansion absolut sein."
            )
        self.max_revisions_per_map = self._integer_parameter(
            "max_revisions_per_map", minimum=1, maximum=100_000
        )
        self.max_storage_bytes = self._integer_parameter(
            "max_storage_bytes", minimum=16 * 1024 * 1024, maximum=8 * 1024**3
        )
        self.min_free_space_bytes = self._integer_parameter(
            "min_free_space_bytes", minimum=16 * 1024 * 1024, maximum=64 * 1024**3
        )
        self.repository = SemanticMapRepository(
            storage_root,
            max_revisions_per_map=self.max_revisions_per_map,
            max_storage_bytes=self.max_storage_bytes,
            min_free_space_bytes=self.min_free_space_bytes,
        )
        self.status_publish_period_s = self._positive_float_parameter(
            "status_publish_period_s"
        )
        self.map_status_stale_timeout_s = self._positive_float_parameter(
            "map_status_stale_timeout_s"
        )
        if self.map_status_stale_timeout_s <= self.status_publish_period_s:
            raise RuntimeError(
                "map_status_stale_timeout_s muss größer als "
                "status_publish_period_s sein."
            )
        self.request_cache_size = self._integer_parameter(
            "request_cache_size", minimum=1, maximum=1_024
        )
        self.request_cache_max_bytes = self._integer_parameter(
            "request_cache_max_bytes", minimum=1_024, maximum=4 * 1024 * 1024
        )

        self._observation: Optional[MapManagerObservation] = None
        self._document: Optional[SemanticDocument] = None
        self._editable = False
        self._edit_block_reason: Optional[str] = (
            "Noch kein gültiger Status des metrischen Kartenmanagers empfangen."
        )
        self._last_error: Optional[str] = None
        self._last_operation = "startup"
        self._last_map_status_time: Optional[float] = None
        self._last_map_status_monotonic: Optional[float] = None
        self._request_cache = RequestSignatureCache(
            max_entries=self.request_cache_size,
            max_bytes=self.request_cache_max_bytes,
        )
        self._counters = {
            "map_status_accepted": 0,
            "map_status_rejected": 0,
            "commands_accepted": 0,
            "commands_rejected": 0,
            "idempotent_replays": 0,
        }

        latched_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        command_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.status_publisher = self.create_publisher(
            String, self.status_topic, latched_qos
        )
        self.catalog_publisher = self.create_publisher(
            String, self.catalog_topic, latched_qos
        )
        self.command_subscription = self.create_subscription(
            String, self.command_topic, self._on_command, command_qos
        )
        self.map_status_subscription = self.create_subscription(
            String,
            self.map_manager_status_topic,
            self._on_map_manager_status,
            latched_qos,
        )
        self.status_timer = self.create_timer(
            self.status_publish_period_s,
            self._publish_periodic_status,
        )
        self._publish_status(
            event="startup",
            ok=False,
            message="Semantischer Kartenmanager gestartet; warte auf Kartenbindung.",
        )

    def _on_map_manager_status(self, message: String) -> None:
        try:
            observation = parse_map_manager_status(message.data)
        except (SemanticValidationError, TypeError, ValueError) as error:
            self._counters["map_status_rejected"] += 1
            self._observation = None
            self._editable = False
            self._edit_block_reason = f"Ungültiger Kartenmanager-Status: {error}"
            self._last_error = self._edit_block_reason
            self._last_operation = "map_status_rejected"
            self.get_logger().warning(self._edit_block_reason)
            self._publish_status(
                event="map_binding_invalid",
                ok=False,
                message=self._edit_block_reason,
            )
            return

        self._last_map_status_time = time.time()
        self._last_map_status_monotonic = time.monotonic()
        if observation is None:
            self._counters["map_status_accepted"] += 1
            self._observation = None
            self._editable = False
            self._edit_block_reason = (
                "Der metrische Kartenmanager besitzt keinen gültigen Kartensnapshot."
            )
            self._last_error = self._edit_block_reason
            self._last_operation = "map_unavailable"
            self._publish_status(
                event="map_binding_invalid",
                ok=False,
                message=self._edit_block_reason,
            )
            return

        self._observation = observation
        self._counters["map_status_accepted"] += 1
        try:
            document = self._activate_observation(observation)
        except (SemanticStorageError, SemanticValidationError) as error:
            self._document = None
            self._editable = False
            self._edit_block_reason = f"Kartenbindung fehlgeschlagen: {error}"
            self._last_error = self._edit_block_reason
            self._last_operation = "map_binding_failed"
            self.get_logger().warning(self._edit_block_reason)
            self._publish_status(
                event="map_binding_invalid",
                ok=False,
                message=self._edit_block_reason,
            )
            return

        if document is None:
            self._document = None
            self._editable = False
            self._edit_block_reason = (
                "Die aktuelle metrische Karte wurde noch nicht als gespeicherte "
                "Version bestätigt. Zuerst im robot_map_manager speichern oder "
                "auflisten."
            )
            self._last_error = None
            self._last_operation = "map_unconfirmed"
            self._publish_status(
                event="map_binding_required",
                ok=False,
                message=self._edit_block_reason,
            )
            return

        changed = (
            self._document is None
            or self._document.map_ref.fingerprint != document.map_ref.fingerprint
            or self._document.revision != document.revision
        )
        self._document = document
        self._editable = True
        self._edit_block_reason = None
        self._last_error = None
        self._last_operation = "map_bound"
        if changed:
            self._publish_status(
                event="map_bound",
                ok=True,
                message=(
                    f"Semantische Karte an '{document.map_ref.name}' "
                    f"Revision {document.revision} gebunden."
                ),
            )
        else:
            self._publish_catalog()

    def _activate_observation(
        self, observation: MapManagerObservation
    ) -> Optional[SemanticDocument]:
        return activate_map_observation(self.repository, observation)

    def _on_command(self, message: String) -> None:
        try:
            command = parse_command_json(message.data)
            signature = command_signature(command)
            replayed = self._lookup_cached_request(command.request_id, signature)
            if replayed:
                self._counters["idempotent_replays"] += 1
        except (CommandValidationError, SemanticStorageError) as error:
            self._counters["commands_rejected"] += 1
            self._last_error = str(error)
            self._last_operation = "command_rejected"
            self._publish_status(
                event="command_result",
                ok=False,
                message=str(error),
            )
            return

        try:
            if command.command in {"get", "status"}:
                self._publish_status(
                    event="status" if command.command == "status" else "get_result",
                    ok=self._editable,
                    command=command.command,
                    request_id=command.request_id,
                    message="Aktueller semantischer Kartenstand.",
                )
            elif command.command == "bind_map":
                self._handle_bind(command)
            elif command.command == "upsert_room":
                self._handle_upsert(command, signature)
            else:
                self._handle_delete(command, signature)
            self._counters["commands_accepted"] += 1
            self._store_cached_request(command.request_id, signature)
        except (
            MapMismatchError,
            RevisionConflictError,
            RequestIDConflict,
            SemanticStorageError,
            SemanticValidationError,
        ) as error:
            self._counters["commands_rejected"] += 1
            self._last_error = str(error)
            self._last_operation = "command_failed"
            self._publish_status(
                event="command_result",
                ok=False,
                command=command.command,
                request_id=command.request_id,
                message=str(error),
            )
            self._store_cached_request(command.request_id, signature)

    def _handle_bind(self, command: SemanticCommand) -> str:
        observation = self._require_fresh_observation()
        selector = command.map_ref_selector
        if selector is None:
            raise MapMismatchError("Keine aktuelle metrische Karte verfügbar.")
        match = next(
            (
                reference
                for reference in observation.confirmed_references
                if reference.name == selector["name"]
                and reference.version == selector["version"]
                and reference.fingerprint == selector["fingerprint"]
            ),
            None,
        )
        if match is None:
            raise MapMismatchError(
                "bind_map verweigert: Die angegebene Version wurde vom aktuellen "
                "robot_map_manager-Status nicht bestätigt."
            )
        # Die Auswahl kann bei langsamer I/O genau an der Timeout-Grenze
        # erfolgen. Unmittelbar vor der persistenten Erstbindung erneut prüfen.
        self._require_fresh_observation()
        document = self.repository.bind_map(match)
        self._document = document
        self._editable = True
        self._edit_block_reason = None
        self._last_error = None
        self._last_operation = "map_bound"
        return self._publish_status(
            event="map_bound",
            ok=True,
            command="bind_map",
            request_id=command.request_id,
            message=f"Karte '{document.map_ref.name}' gebunden.",
        )

    def _require_fresh_observation(self) -> MapManagerObservation:
        try:
            fresh = map_status_is_fresh(
                last_received_monotonic=self._last_map_status_monotonic,
                now_monotonic=time.monotonic(),
                timeout_s=self.map_status_stale_timeout_s,
            )
        except SemanticValidationError:
            fresh = False
        if not fresh:
            self._mark_map_status_stale()
            raise MapMismatchError(self._edit_block_reason)
        if self._observation is None:
            raise MapMismatchError("Keine aktuelle metrische Karte verfügbar.")
        return self._observation

    def _require_editable(self, fingerprint: Optional[str]) -> SemanticDocument:
        self._apply_stale_guard()
        if not self._editable or self._document is None or self._observation is None:
            raise MapMismatchError(
                self._edit_block_reason
                or "Semantische Karte ist nicht zur Bearbeitung freigegeben."
            )
        if (
            fingerprint != self._document.map_ref.fingerprint
            or fingerprint != self._observation.fingerprint
        ):
            raise MapMismatchError(
                "map_fingerprint stimmt nicht mit der aktuell sichtbaren und "
                "gebundenen Karte überein."
            )
        return self._document

    def _handle_upsert(self, command: SemanticCommand, signature: str) -> str:
        self._require_editable(command.map_fingerprint)
        assert command.map_fingerprint is not None
        assert command.base_revision is not None
        assert command.room is not None
        assert command.request_id is not None
        result = self.repository.upsert_room(
            map_fingerprint=command.map_fingerprint,
            base_revision=command.base_revision,
            room_payload=command.room,
            request_id=command.request_id,
            signature=signature,
        )
        return self._accept_mutation(command, result)

    def _handle_delete(self, command: SemanticCommand, signature: str) -> str:
        self._require_editable(command.map_fingerprint)
        assert command.map_fingerprint is not None
        assert command.base_revision is not None
        assert command.room_id is not None
        assert command.request_id is not None
        result = self.repository.delete_room(
            map_fingerprint=command.map_fingerprint,
            base_revision=command.base_revision,
            room_id=command.room_id,
            request_id=command.request_id,
            signature=signature,
        )
        return self._accept_mutation(command, result)

    def _accept_mutation(
        self, command: SemanticCommand, result: MutationResult
    ) -> str:
        self._document = result.document
        self._last_error = None
        self._last_operation = result.event
        message = result.message
        extra: dict[str, Any] = {"idempotent_replay": result.replayed}
        if result.original_revision is not None:
            extra["original_revision"] = result.original_revision
        return self._publish_status(
            event=result.event,
            ok=True,
            command=command.command,
            request_id=command.request_id,
            message=message,
            extra=extra,
        )

    def _publish_periodic_status(self) -> None:
        self._apply_stale_guard()
        self._publish_status(
            event="status",
            # last_error bleibt als Diagnose des letzten Kommandos erhalten.
            # Readiness hängt dagegen ausschließlich an der aktuellen,
            # frischen Kartenbindung und erholt sich ohne ein weiteres
            # Schreibkommando nach einem harmlosen Revisionskonflikt.
            ok=self._editable,
            message="Periodischer semantischer Kartenstatus.",
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
        # Auch ein direktes get/status zwischen zwei Timer-Ticks darf niemals
        # eine abgelaufene Schreibfreigabe als editable=true darstellen.
        self._apply_stale_guard()
        # Der Aufrufer kann ``ok`` noch vor dem Stale-Check ausgewertet haben.
        # Deshalb hier nach der Zustandsaktualisierung erneut fail-closed mit
        # der tatsächlichen Kartenbindung verknüpfen.
        ok = bool(ok and self._editable)
        document = self._document
        now_monotonic = time.monotonic()
        map_status_age = (
            None
            if self._last_map_status_monotonic is None
            else max(0.0, now_monotonic - self._last_map_status_monotonic)
        )
        semantic_map: dict[str, Any] = {
            "map_ref": None if document is None else document.map_ref.as_dict(),
            "revision": None if document is None else document.revision,
            "rooms": [] if document is None else [room.as_dict() for room in document.rooms],
            "editable": self._editable,
            "edit_block_reason": self._edit_block_reason,
            "updated_at": None if document is None else document.updated_at,
        }
        payload: dict[str, Any] = {
            "schema_version": 1,
            "event": event,
            "ok": ok,
            "command": command,
            "request_id": request_id,
            "message": message,
            "time": time.time(),
            "last_operation": self._last_operation,
            "last_error": self._last_error,
            "semantic_map": semantic_map,
            "map_manager": {
                "status_topic": self.map_manager_status_topic,
                "last_status_time": self._last_map_status_time,
                "status_age_seconds": map_status_age,
                "stale_timeout_seconds": self.map_status_stale_timeout_s,
                "observed_fingerprint": (
                    None if self._observation is None else self._observation.fingerprint
                ),
                "confirmed_versions": (
                    []
                    if self._observation is None
                    else [
                        {
                            "name": reference.name,
                            "version": reference.version,
                            "fingerprint": reference.fingerprint,
                        }
                        for reference in self._observation.confirmed_references
                    ]
                ),
            },
            "storage": {"root": str(self.repository.root)},
            "counters": dict(self._counters),
        }
        if extra:
            payload.update(extra)
        serialized = json_message(payload)
        self.status_publisher.publish(String(data=serialized))
        self._publish_catalog()
        return serialized

    def _publish_catalog(self) -> None:
        document = self._document
        room_entities = (
            []
            if document is None or not self._editable
            else [
                {
                    "id": room.id,
                    "name": room.name,
                    "navigation_goal": room.navigation_goal.as_dict(),
                }
                for room in document.rooms
            ]
        )
        payload = {
            "schema_version": 1,
            "ok": self._editable,
            "source": "semantic_map_manager",
            # Bestehende mission_manager/llm_planner erwarten Namen statt
            # Objektstrukturen in genau diesem Feld.
            "rooms": [entity["name"] for entity in room_entities],
            "room_entities": room_entities,
            "map_fingerprint": (
                None if document is None else document.map_ref.fingerprint
            ),
            "revision": None if document is None else document.revision,
            "editable": self._editable,
        }
        self.catalog_publisher.publish(String(data=json_message(payload)))

    def _apply_stale_guard(self) -> None:
        if not self._editable:
            return
        try:
            fresh = map_status_is_fresh(
                last_received_monotonic=self._last_map_status_monotonic,
                now_monotonic=time.monotonic(),
                timeout_s=self.map_status_stale_timeout_s,
            )
        except SemanticValidationError:
            fresh = False
        if fresh:
            return
        self._mark_map_status_stale()

    def _mark_map_status_stale(self) -> None:
        self._editable = False
        self._edit_block_reason = (
            "Status des metrischen Kartenmanagers ist veraltet; "
            "Schreibzugriffe bleiben bis zum nächsten gültigen Status gesperrt."
        )
        self._last_error = self._edit_block_reason
        self._last_operation = "map_status_stale"

    def _lookup_cached_request(
        self, request_id: Optional[str], signature: str
    ) -> bool:
        return self._request_cache.check(request_id, signature)

    def _store_cached_request(
        self, request_id: Optional[str], signature: str
    ) -> None:
        self._request_cache.remember(request_id, signature)

    def _nonempty_parameter(self, name: str) -> str:
        value = self.get_parameter(name).value
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"Parameter {name} muss eine nichtleere Zeichenkette sein.")
        return value.strip()

    def _positive_float_parameter(self, name: str) -> float:
        value = self.get_parameter(name).value
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math_isfinite(value)
            or float(value) <= 0.0
        ):
            raise RuntimeError(f"Parameter {name} muss eine positive endliche Zahl sein.")
        return float(value)

    def _integer_parameter(self, name: str, *, minimum: int, maximum: int) -> int:
        value = self.get_parameter(name).value
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
            or value > maximum
        ):
            raise RuntimeError(
                f"Parameter {name} muss zwischen {minimum} und {maximum} liegen."
            )
        return value


def math_isfinite(value: Any) -> bool:
    # Lokaler Helper hält den ROS-Einstieg übersichtlich und akzeptiert keine
    # Decimal-/String-Sonderfälle aus Parameter-Overrides.
    try:
        return float("-inf") < float(value) < float("inf")
    except (TypeError, ValueError, OverflowError):
        return False


def main(args: Optional[list[str]] = None) -> None:
    rclpy.init(args=args)
    node: Optional[SemanticMapManager] = None
    try:
        node = SemanticMapManager()
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
