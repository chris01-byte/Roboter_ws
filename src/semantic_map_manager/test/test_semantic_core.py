import errno
import json
import math
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

from semantic_map_manager.semantic_core import (
    _json_bytes,
    activate_map_observation,
    CommandValidationError,
    MapMismatchError,
    MapReference,
    MAXIMUM_DOCUMENT_BYTES,
    MAXIMUM_POLYGON_POINTS,
    MAXIMUM_TOTAL_POLYGON_POINTS,
    RequestIDConflict,
    RequestSignatureCache,
    RevisionConflictError,
    Room,
    SemanticDocument,
    SemanticMapRepository,
    SemanticStorageError,
    SemanticValidationError,
    command_signature,
    default_storage_root,
    json_message,
    map_status_is_fresh,
    parse_command_json,
    parse_map_manager_status,
    point_strictly_inside_polygon,
)


FINGERPRINT = "a" * 64
VERSION = "20260814T120000000000Z-abcdef123456"


def valid_map_ref(**overrides):
    payload = {
        "name": "wohnung",
        "version": VERSION,
        "fingerprint": FINGERPRINT,
        "frame_id": "map",
        "width": 100,
        "height": 80,
        "resolution": 0.1,
        "origin": {
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
            "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            "yaw": 0.0,
        },
    }
    payload.update(overrides)
    return MapReference.from_dict(payload)


def valid_room(**overrides):
    payload = {
        "id": "wohnzimmer",
        "name": "Wohnzimmer",
        "color": "#31A8FF",
        "polygon": [
            {"x": 1.0, "y": 1.0},
            {"x": 4.0, "y": 1.0},
            {"x": 4.0, "y": 3.0},
            {"x": 1.0, "y": 3.0},
        ],
        "navigation_goal": {"x": 2.0, "y": 2.0, "yaw": 0.5},
    }
    payload.update(overrides)
    return payload


def regular_polygon(point_count):
    return [
        {
            "x": 5.0 + math.cos(2.0 * math.pi * index / point_count),
            "y": 4.0 + math.sin(2.0 * math.pi * index / point_count),
        }
        for index in range(point_count)
    ]


def room_set(room_count, *, points_per_room=MAXIMUM_POLYGON_POINTS):
    polygon = regular_polygon(points_per_room)
    return [
        valid_room(
            id=f"raum-{index:03d}",
            name=f"Raum {index:03d}",
            polygon=polygon,
            navigation_goal={"x": 5.0, "y": 4.0, "yaw": 0.0},
        )
        for index in range(room_count)
    ]


def semantic_document_payload(rooms):
    return {
        "schema_version": 1,
        "map_ref": valid_map_ref().as_dict(),
        "revision": 0,
        "rooms": rooms,
        "updated_at": "2026-08-14T12:00:00Z",
        "request_log": [],
    }


def map_status(*, fingerprint=FINGERPRINT, saved=True, maps=None, origin=None):
    origin = origin or valid_map_ref().origin
    payload = {
        "schema_version": 1,
        "event": "status",
        "ok": True,
        "map": {
            "available": True,
            "snapshot_available": True,
            "summary": {
                "fingerprint": fingerprint,
                "frame_id": "map",
                "width": 100,
                "height": 80,
                "resolution": 0.1,
                "origin": origin,
                "source_stamp_ns": 123,
            },
        },
        "storage": {"last_saved": None},
    }
    record = {
        "name": "wohnung",
        "version": VERSION,
        "fingerprint": fingerprint,
        "frame_id": "map",
        "width": 100,
        "height": 80,
        "resolution": 0.1,
    }
    if saved:
        payload["storage"]["last_saved"] = record
    if maps is not None:
        payload["maps"] = maps
    return json.dumps(payload)


class MapReferenceTests(unittest.TestCase):
    def test_accepts_complete_reference_and_rotated_bounds(self):
        quarter_turn = {
            "position": {"x": 5.0, "y": 6.0, "z": 0.0},
            "orientation": {
                "x": 0.0,
                "y": 0.0,
                "z": math.sqrt(0.5),
                "w": math.sqrt(0.5),
            },
            "yaw": math.pi / 2.0,
        }
        reference = valid_map_ref(origin=quarter_turn)
        from semantic_map_manager.semantic_core import Point2D

        self.assertTrue(reference.contains_map_point(Point2D(4.0, 7.0)))
        self.assertFalse(reference.contains_map_point(Point2D(6.0, 7.0)))
        self.assertEqual(reference.fingerprint, FINGERPRINT)

    def test_rejects_bad_identity_geometry_origin_and_unknown_fields(self):
        invalid = [
            {"fingerprint": "A" * 64},
            {"fingerprint": "a" * 63},
            {"name": "../wohnung"},
            {"version": "latest"},
            {"width": True},
            {"resolution": float("nan")},
            {"frame_id": "map\nbase"},
            {"extra": 1},
        ]
        for override in invalid:
            with self.subTest(override=override):
                with self.assertRaises(SemanticValidationError):
                    valid_map_ref(**override)

        origin = valid_map_ref().origin
        origin["orientation"] = {"x": 0.0, "y": 0.0, "z": 0.0, "w": 2.0}
        with self.assertRaises(SemanticValidationError):
            valid_map_ref(origin=origin)

    def test_yaw_must_match_quaternion(self):
        origin = valid_map_ref().origin
        origin["yaw"] = 1.0
        with self.assertRaisesRegex(SemanticValidationError, "widerspricht"):
            valid_map_ref(origin=origin)


class RoomValidationTests(unittest.TestCase):
    def test_accepts_room_and_normalizes_color(self):
        room = Room.from_dict(valid_room(color="#aabbcc"), map_ref=valid_map_ref())
        self.assertEqual(room.id, "wohnzimmer")
        self.assertEqual(room.color, "#AABBCC")
        self.assertEqual(room.as_dict()["polygon"][0], {"x": 1.0, "y": 1.0})

    def test_rejects_too_few_duplicate_collinear_or_self_intersecting_points(self):
        invalid_polygons = [
            [{"x": 1.0, "y": 1.0}, {"x": 2.0, "y": 1.0}],
            [
                {"x": 1.0, "y": 1.0},
                {"x": 2.0, "y": 1.0},
                {"x": 2.0, "y": 1.0},
                {"x": 1.0, "y": 2.0},
            ],
            [
                {"x": 1.0, "y": 1.0},
                {"x": 2.0, "y": 1.0},
                {"x": 3.0, "y": 1.0},
            ],
            [
                {"x": 1.0, "y": 1.0},
                {"x": 4.0, "y": 3.0},
                {"x": 1.0, "y": 3.0},
                {"x": 4.0, "y": 1.0},
            ],
        ]
        for polygon in invalid_polygons:
            with self.subTest(polygon=polygon):
                with self.assertRaises(SemanticValidationError):
                    Room.from_dict(
                        valid_room(polygon=polygon), map_ref=valid_map_ref()
                    )

    def test_rejects_polygon_outside_map_and_goal_outside_or_on_boundary(self):
        with self.assertRaisesRegex(SemanticValidationError, "außerhalb"):
            Room.from_dict(
                valid_room(
                    polygon=[
                        {"x": -1.0, "y": 1.0},
                        {"x": 2.0, "y": 1.0},
                        {"x": 2.0, "y": 2.0},
                    ]
                ),
                map_ref=valid_map_ref(),
            )
        for goal in (
            {"x": 8.0, "y": 7.0, "yaw": 0.0},
            {"x": 1.0, "y": 2.0, "yaw": 0.0},
        ):
            with self.subTest(goal=goal):
                with self.assertRaisesRegex(SemanticValidationError, "strikt"):
                    Room.from_dict(
                        valid_room(navigation_goal=goal), map_ref=valid_map_ref()
                    )

    def test_rejects_invalid_id_name_color_yaw_and_extra_fields(self):
        invalid = [
            {"id": "Wohn Zimmer"},
            {"name": "\n"},
            {"color": "blue"},
            {"navigation_goal": {"x": 2.0, "y": 2.0, "yaw": 4.0}},
            {"unknown": True},
        ]
        for override in invalid:
            with self.subTest(override=override):
                with self.assertRaises(SemanticValidationError):
                    Room.from_dict(valid_room(**override), map_ref=valid_map_ref())

    def test_point_inside_helper_excludes_edge(self):
        room = Room.from_dict(valid_room(), map_ref=valid_map_ref())
        from semantic_map_manager.semantic_core import Point2D

        self.assertTrue(point_strictly_inside_polygon(Point2D(2.0, 2.0), room.polygon))
        self.assertFalse(point_strictly_inside_polygon(Point2D(1.0, 2.0), room.polygon))

    def test_polygon_complexity_accepts_64_and_rejects_65_points(self):
        accepted = Room.from_dict(
            valid_room(
                polygon=regular_polygon(MAXIMUM_POLYGON_POINTS),
                navigation_goal={"x": 5.0, "y": 4.0, "yaw": 0.0},
            ),
            map_ref=valid_map_ref(),
        )
        self.assertEqual(len(accepted.polygon), 64)
        with self.assertRaisesRegex(SemanticValidationError, "3 bis 64"):
            Room.from_dict(
                valid_room(
                    polygon=regular_polygon(MAXIMUM_POLYGON_POINTS + 1),
                    navigation_goal={"x": 5.0, "y": 4.0, "yaw": 0.0},
                ),
                map_ref=valid_map_ref(),
            )


class DocumentComplexityTests(unittest.TestCase):
    def test_document_accepts_4096_and_rejects_4160_points(self):
        exact_room_count = (
            MAXIMUM_TOTAL_POLYGON_POINTS // MAXIMUM_POLYGON_POINTS
        )
        accepted = SemanticDocument.from_dict(
            semantic_document_payload(room_set(exact_room_count))
        )
        self.assertEqual(
            sum(len(room.polygon) for room in accepted.rooms),
            MAXIMUM_TOTAL_POLYGON_POINTS,
        )
        with self.assertRaisesRegex(SemanticValidationError, "Gesamtlimit"):
            SemanticDocument.from_dict(
                semantic_document_payload(room_set(exact_room_count + 1))
            )


class CommandTests(unittest.TestCase):
    def test_accepts_all_commands(self):
        self.assertEqual(parse_command_json('{"command":"get"}').command, "get")
        self.assertEqual(parse_command_json('{"command":"status"}').command, "status")
        bind = parse_command_json(
            json.dumps(
                {
                    "command": "bind_map",
                    "request_id": "ios:1",
                    "map_ref": {
                        "name": "wohnung",
                        "version": VERSION,
                        "fingerprint": FINGERPRINT,
                    },
                }
            )
        )
        self.assertEqual(bind.map_ref_selector["name"], "wohnung")
        upsert = parse_command_json(
            json.dumps(
                {
                    "command": "upsert_room",
                    "request_id": "ios:2",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": 0,
                    "room": valid_room(),
                }
            )
        )
        self.assertEqual(upsert.base_revision, 0)
        delete = parse_command_json(
            json.dumps(
                {
                    "command": "delete_room",
                    "request_id": "ios:3",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": 1,
                    "room_id": "wohnzimmer",
                }
            )
        )
        self.assertEqual(delete.room_id, "wohnzimmer")

    def test_rejects_unknown_fields_missing_request_and_nonfinite_revision(self):
        invalid = [
            "[]",
            '{"command":"drive"}',
            '{"command":"get","extra":1}',
            json.dumps(
                {
                    "command": "upsert_room",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": 0,
                    "room": valid_room(),
                }
            ),
            json.dumps(
                {
                    "command": "delete_room",
                    "request_id": "../bad",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": -1,
                    "room_id": "wohnzimmer",
                }
            ),
        ]
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(CommandValidationError):
                    parse_command_json(payload)

    def test_rejects_oversize_before_json_parse(self):
        with self.assertRaises(CommandValidationError):
            parse_command_json("{" + "x" * (64 * 1024) + "}")

    def test_deep_json_and_invalid_unicode_fail_closed(self):
        deeply_nested = "[" * 2_000 + "0" + "]" * 2_000
        with self.assertRaises(CommandValidationError):
            parse_command_json(deeply_nested)
        with self.assertRaises(CommandValidationError):
            parse_command_json('{"command":"get","request_id":"\ud800"}')

    def test_upsert_rejects_65_points_during_command_preflight(self):
        payload = {
            "command": "upsert_room",
            "request_id": "ios:too-complex",
            "map_fingerprint": FINGERPRINT,
            "base_revision": 0,
            "room": valid_room(
                polygon=regular_polygon(MAXIMUM_POLYGON_POINTS + 1),
                navigation_goal={"x": 5.0, "y": 4.0, "yaw": 0.0},
            ),
        }
        with self.assertRaisesRegex(CommandValidationError, "3 bis 64"):
            parse_command_json(json.dumps(payload))

    def test_signature_ignores_request_id_but_covers_payload(self):
        first = parse_command_json(
            json.dumps(
                {
                    "command": "upsert_room",
                    "request_id": "one",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": 0,
                    "room": valid_room(),
                }
            )
        )
        second_payload = json.loads(json.dumps({
            "command": "upsert_room",
            "request_id": "two",
            "map_fingerprint": FINGERPRINT,
            "base_revision": 0,
            "room": valid_room(),
        }))
        second = parse_command_json(json.dumps(second_payload))
        self.assertEqual(command_signature(first), command_signature(second))
        second_payload["room"]["name"] = "Küche"
        changed = parse_command_json(json.dumps(second_payload))
        self.assertNotEqual(command_signature(first), command_signature(changed))


class MapStatusTests(unittest.TestCase):
    def test_extracts_matching_last_saved_reference(self):
        observation = parse_map_manager_status(map_status())
        self.assertIsNotNone(observation)
        self.assertEqual(observation.fingerprint, FINGERPRINT)
        self.assertEqual(len(observation.confirmed_references), 1)
        self.assertEqual(observation.confirmed_references[0].name, "wohnung")

    def test_live_snapshot_without_saved_reference_is_unconfirmed(self):
        observation = parse_map_manager_status(map_status(saved=False))
        self.assertIsNotNone(observation)
        self.assertEqual(observation.confirmed_references, ())

    def test_list_result_is_accepted_and_mismatch_or_geometry_lie_ignored(self):
        valid_record = {
            "name": "wohnung",
            "version": VERSION,
            "fingerprint": FINGERPRINT,
            "frame_id": "map",
            "width": 100,
            "height": 80,
            "resolution": 0.1,
        }
        wrong_fingerprint = dict(valid_record, fingerprint="b" * 64)
        wrong_geometry = dict(valid_record, width=101)
        observation = parse_map_manager_status(
            map_status(
                saved=False,
                maps=[wrong_fingerprint, wrong_geometry, valid_record],
            )
        )
        self.assertEqual(len(observation.confirmed_references), 1)

    def test_unavailable_returns_none_and_bad_summary_fails(self):
        payload = json.loads(map_status())
        payload["map"]["snapshot_available"] = False
        self.assertIsNone(parse_map_manager_status(json.dumps(payload)))
        payload = json.loads(map_status())
        del payload["map"]["summary"]["origin"]
        with self.assertRaises(SemanticValidationError):
            parse_map_manager_status(json.dumps(payload))

    def test_error_status_never_confirms_old_snapshot(self):
        payload = json.loads(map_status())
        payload["ok"] = False
        payload["message"] = "alter Snapshot nach internem Fehler"
        with self.assertRaisesRegex(SemanticValidationError, "ok=true"):
            parse_map_manager_status(json.dumps(payload))

    def test_deep_status_json_fails_closed(self):
        deeply_nested = "[" * 2_000 + "0" + "]" * 2_000
        with self.assertRaises(SemanticValidationError):
            parse_map_manager_status(deeply_nested)

    def test_status_freshness_is_monotonic_and_fail_closed(self):
        self.assertFalse(
            map_status_is_fresh(
                last_received_monotonic=None,
                now_monotonic=10.0,
                timeout_s=6.0,
            )
        )
        # monotonic ist System-Uptime und auf einem dauerhaft laufenden Jetson
        # regelmäßig viel größer als Kartenkoordinaten.
        self.assertTrue(
            map_status_is_fresh(
                last_received_monotonic=1_000_000.0,
                now_monotonic=1_000_001.0,
                timeout_s=6.0,
            )
        )
        self.assertTrue(
            map_status_is_fresh(
                last_received_monotonic=10.0,
                now_monotonic=16.0,
                timeout_s=6.0,
            )
        )
        self.assertFalse(
            map_status_is_fresh(
                last_received_monotonic=10.0,
                now_monotonic=16.0001,
                timeout_s=6.0,
            )
        )
        self.assertFalse(
            map_status_is_fresh(
                last_received_monotonic=10.0,
                now_monotonic=9.0,
                timeout_s=6.0,
            )
        )


class RequestSignatureCacheTests(unittest.TestCase):
    def test_replay_keeps_only_signature_and_conflicts_fail_closed(self):
        cache = RequestSignatureCache(max_entries=4, max_bytes=4_096)
        self.assertFalse(cache.check("ios:1", "a" * 64))
        cache.remember("ios:1", "a" * 64)
        self.assertTrue(cache.check("ios:1", "a" * 64))
        self.assertLessEqual(cache.bytes_used, cache.max_bytes)
        with self.assertRaises(RequestIDConflict):
            cache.check("ios:1", "b" * 64)

    def test_entry_and_byte_limits_evict_oldest(self):
        cache = RequestSignatureCache(max_entries=10, max_bytes=700)
        cache.remember("ios:1", "a" * 64)
        cache.remember("ios:2", "b" * 64)
        cache.remember("ios:3", "c" * 64)
        self.assertLessEqual(cache.bytes_used, 700)
        self.assertLessEqual(len(cache), 10)
        self.assertFalse(cache.check("ios:1", "a" * 64))
        self.assertTrue(cache.check("ios:3", "c" * 64))


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "semantic_maps"
        self.repository = SemanticMapRepository(self.root)
        self.reference = valid_map_ref()

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *, request_id="ios:1", revision=0, room=None):
        return parse_command_json(
            json.dumps(
                {
                    "command": "upsert_room",
                    "request_id": request_id,
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": revision,
                    "room": room or valid_room(),
                }
            )
        )

    def upsert(self, command):
        return self.repository.upsert_room(
            map_fingerprint=command.map_fingerprint,
            base_revision=command.base_revision,
            room_payload=command.room,
            request_id=command.request_id,
            signature=command_signature(command),
        )

    def test_bind_creates_revision_zero_outside_workspace_and_reloads(self):
        document = self.repository.bind_map(self.reference)
        self.assertEqual(document.revision, 0)
        directory = self.root / FINGERPRINT
        self.assertTrue((directory / "current.json").is_file())
        self.assertTrue((directory / "revisions" / "00000000000000000000.json").is_file())
        self.assertEqual(self.repository.load(FINGERPRINT), document)
        self.assertEqual(
            default_storage_root(Path("/home/test")),
            Path("/home/test/.local/share/amadeus/semantic_maps"),
        )

    def test_activation_requires_saved_first_time_but_not_after_restart(self):
        unconfirmed = parse_map_manager_status(map_status(saved=False))
        self.assertIsNone(activate_map_observation(self.repository, unconfirmed))

        confirmed = parse_map_manager_status(map_status(saved=True))
        first = activate_map_observation(self.repository, confirmed)
        self.assertIsNotNone(first)
        self.assertEqual(first.revision, 0)

        restarted = SemanticMapRepository(self.root)
        restored = activate_map_observation(restarted, unconfirmed)
        self.assertEqual(restored.map_ref, first.map_ref)

    def test_restart_activation_still_rejects_live_geometry_mismatch(self):
        self.repository.bind_map(self.reference)
        payload = json.loads(map_status(saved=False))
        payload["map"]["summary"]["width"] = 99
        observation = parse_map_manager_status(json.dumps(payload))
        with self.assertRaises(MapMismatchError):
            activate_map_observation(self.repository, observation)

    def test_same_fingerprint_new_saved_version_reuses_canonical_overlay(self):
        first = self.repository.bind_map(self.reference)
        newer = valid_map_ref(version="20260814T130000000000Z-fedcba654321")
        loaded = self.repository.bind_map(newer)
        self.assertEqual(loaded.map_ref.version, first.map_ref.version)

    def test_geometry_mismatch_same_fingerprint_fails_closed(self):
        self.repository.bind_map(self.reference)
        with self.assertRaises(MapMismatchError):
            self.repository.bind_map(valid_map_ref(width=99))

    def test_upsert_update_delete_revision_history(self):
        self.repository.bind_map(self.reference)
        created = self.upsert(self.command())
        self.assertEqual(created.event, "room_created")
        self.assertEqual(created.document.revision, 1)
        updated_command = self.command(
            request_id="ios:2",
            revision=1,
            room=valid_room(name="Großes Wohnzimmer"),
        )
        updated = self.upsert(updated_command)
        self.assertEqual(updated.event, "room_updated")
        self.assertEqual(updated.document.rooms[0].name, "Großes Wohnzimmer")
        delete_command = parse_command_json(
            json.dumps(
                {
                    "command": "delete_room",
                    "request_id": "ios:3",
                    "map_fingerprint": FINGERPRINT,
                    "base_revision": 2,
                    "room_id": "wohnzimmer",
                }
            )
        )
        deleted = self.repository.delete_room(
            map_fingerprint=FINGERPRINT,
            base_revision=2,
            room_id="wohnzimmer",
            request_id="ios:3",
            signature=command_signature(delete_command),
        )
        self.assertEqual(deleted.document.revision, 3)
        self.assertEqual(deleted.document.rooms, ())
        revisions = sorted((self.root / FINGERPRINT / "revisions").iterdir())
        self.assertEqual(len(revisions), 4)

    def test_stale_revision_rejected_without_file_change(self):
        self.repository.bind_map(self.reference)
        self.upsert(self.command())
        current = (self.root / FINGERPRINT / "current.json").read_bytes()
        with self.assertRaises(RevisionConflictError):
            self.upsert(self.command(request_id="ios:2", revision=0))
        self.assertEqual((self.root / FINGERPRINT / "current.json").read_bytes(), current)

    def test_request_replay_persists_across_repository_restart_and_precedes_revision(self):
        self.repository.bind_map(self.reference)
        command = self.command()
        first = self.upsert(command)
        restarted = SemanticMapRepository(self.root)
        replay = restarted.upsert_room(
            map_fingerprint=FINGERPRINT,
            base_revision=0,
            room_payload=command.room,
            request_id=command.request_id,
            signature=command_signature(command),
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.original_revision, 1)
        self.assertEqual(replay.document.revision, first.document.revision)

    def test_reused_request_id_with_other_payload_is_conflict(self):
        self.repository.bind_map(self.reference)
        self.upsert(self.command())
        conflicting = self.command(
            revision=1,
            room=valid_room(name="Anderer Name"),
        )
        with self.assertRaises(RequestIDConflict):
            self.upsert(conflicting)

    def test_duplicate_room_names_and_missing_delete_are_rejected(self):
        self.repository.bind_map(self.reference)
        self.upsert(self.command())
        with self.assertRaisesRegex(SemanticValidationError, "bereits vergeben"):
            self.upsert(
                self.command(
                    request_id="ios:2",
                    revision=1,
                    room=valid_room(id="wohnzimmer-zwei", polygon=[
                        {"x": 5.0, "y": 1.0},
                        {"x": 7.0, "y": 1.0},
                        {"x": 7.0, "y": 3.0},
                        {"x": 5.0, "y": 3.0},
                    ], navigation_goal={"x": 6.0, "y": 2.0, "yaw": 0.0}),
                )
            )
        with self.assertRaisesRegex(SemanticValidationError, "existiert nicht"):
            self.repository.delete_room(
                map_fingerprint=FINGERPRINT,
                base_revision=1,
                room_id="kueche",
                request_id="ios:3",
                signature="b" * 64,
            )

    def test_recovers_complete_orphan_revision_when_current_is_missing(self):
        self.repository.bind_map(self.reference)
        self.upsert(self.command())
        current = self.root / FINGERPRINT / "current.json"
        current.unlink()
        recovered = SemanticMapRepository(self.root).load(FINGERPRINT)
        self.assertEqual(recovered.revision, 1)
        self.assertTrue(current.is_file())

    def test_corrupt_current_and_symlink_root_fail(self):
        self.repository.bind_map(self.reference)
        (self.root / FINGERPRINT / "current.json").write_text("not-json")
        with self.assertRaises(SemanticStorageError):
            self.repository.load(FINGERPRINT)
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            target.mkdir()
            link = Path(temporary) / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(SemanticStorageError):
                SemanticMapRepository(link)

    def test_deep_persisted_json_fails_closed(self):
        self.repository.bind_map(self.reference)
        current = self.root / FINGERPRINT / "current.json"
        current.write_text("[" * 2_000 + "0" + "]" * 2_000, encoding="utf-8")
        with self.assertRaises(SemanticStorageError):
            self.repository.load(FINGERPRINT)

    def test_partial_revision_write_never_publishes_final_file_and_retry_works(self):
        real_write = os.write
        write_calls = 0

        def fail_after_partial_write(descriptor, data):
            nonlocal write_calls
            write_calls += 1
            if write_calls == 1:
                return real_write(descriptor, bytes(data[:7]))
            raise OSError(errno.ENOSPC, "synthetisch voll")

        revision = self.root / FINGERPRINT / "revisions" / "00000000000000000000.json"
        with mock.patch(
            "semantic_map_manager.semantic_core.os.write",
            side_effect=fail_after_partial_write,
        ):
            with self.assertRaisesRegex(SemanticStorageError, "geschrieben"):
                self.repository.bind_map(self.reference)
        self.assertFalse(revision.exists())
        revisions = revision.parent
        self.assertEqual(list(revisions.glob(".tmp-revision-*")), [])

        document = self.repository.bind_map(self.reference)
        self.assertEqual(document.revision, 0)
        self.assertTrue(revision.is_file())

    def test_retry_recovers_revision_published_before_current_replace_failed(self):
        initial = self.repository.bind_map(self.reference)
        self.assertEqual(initial.revision, 0)
        command = self.command(request_id="ios:orphan-current", revision=0)
        real_replace = os.replace

        def fail_current_replace(source, destination):
            if Path(destination).name == "current.json":
                revision = (
                    self.root
                    / FINGERPRINT
                    / "revisions"
                    / "00000000000000000001.json"
                )
                self.assertTrue(revision.is_file())
                raise OSError(errno.EIO, "synthetischer current-Replace-Fehler")
            return real_replace(source, destination)

        with mock.patch(
            "semantic_map_manager.semantic_core.os.replace",
            side_effect=fail_current_replace,
        ):
            with self.assertRaises(SemanticStorageError):
                self.upsert(command)

        current_path = self.root / FINGERPRINT / "current.json"
        orphan_path = (
            self.root
            / FINGERPRINT
            / "revisions"
            / "00000000000000000001.json"
        )
        self.assertEqual(json.loads(current_path.read_text())["revision"], 0)
        orphan_payload = json.loads(orphan_path.read_text())
        orphan_updated_at = orphan_payload["updated_at"]

        # Derselbe Retry lädt zuerst den lückenlosen orphan Commit. Dadurch
        # greift dessen persistente request_id, statt Revision 1 mit einem
        # neuen updated_at erneut schreiben und daran dauerhaft zu scheitern.
        replay = self.upsert(command)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.document.revision, 1)
        self.assertEqual(replay.document.updated_at, orphan_updated_at)
        self.assertEqual(current_path.read_bytes(), orphan_path.read_bytes())
        self.assertEqual(
            len(list((self.root / FINGERPRINT / "revisions").glob("*.json"))),
            2,
        )

    def test_orphan_recovery_rejects_revision_gap(self):
        current = self.repository.bind_map(self.reference)
        forged = current.as_dict()
        forged["revision"] = 2
        forged["updated_at"] = "2026-08-14T12:00:02Z"
        forged["request_log"] = [
            {
                "request_id": "ios:gapped",
                "signature": "d" * 64,
                "revision": 2,
                "event": "room_created",
                "message": "synthetischer Sprung",
            }
        ]
        gap_path = (
            self.root
            / FINGERPRINT
            / "revisions"
            / "00000000000000000002.json"
        )
        gap_path.write_text(json.dumps(forged), encoding="utf-8")
        with self.assertRaisesRegex(SemanticStorageError, "lückenlose"):
            self.repository.load(FINGERPRINT)
        self.assertEqual(
            json.loads((self.root / FINGERPRINT / "current.json").read_text())[
                "revision"
            ],
            0,
        )

    def test_revision_limit_blocks_before_new_revision_is_published(self):
        limited = SemanticMapRepository(self.root, max_revisions_per_map=2)
        limited.bind_map(self.reference)
        command = self.command()
        first = limited.upsert_room(
            map_fingerprint=command.map_fingerprint,
            base_revision=command.base_revision,
            room_payload=command.room,
            request_id=command.request_id,
            signature=command_signature(command),
        )
        second = self.command(
            request_id="ios:2",
            revision=first.document.revision,
            room=valid_room(name="Aktualisiert"),
        )
        with self.assertRaisesRegex(SemanticStorageError, "Revisionen"):
            limited.upsert_room(
                map_fingerprint=second.map_fingerprint,
                base_revision=second.base_revision,
                room_payload=second.room,
                request_id=second.request_id,
                signature=command_signature(second),
            )
        self.assertFalse(
            (
                self.root
                / FINGERPRINT
                / "revisions"
                / "00000000000000000002.json"
            ).exists()
        )
        self.assertEqual(limited.load(FINGERPRINT).revision, 1)

    def test_storage_and_free_space_budgets_fail_before_publish(self):
        tiny = SemanticMapRepository(
            self.root,
            max_storage_bytes=1,
            min_free_space_bytes=1,
        )
        with self.assertRaisesRegex(SemanticStorageError, "Größenlimit"):
            tiny.bind_map(self.reference)

        other_root = Path(self.temporary.name) / "free_space_test"
        reserve = SemanticMapRepository(other_root, min_free_space_bytes=1_024)
        with mock.patch(
            "semantic_map_manager.semantic_core.shutil.disk_usage",
            return_value=SimpleNamespace(free=1_024),
        ):
            with self.assertRaisesRegex(SemanticStorageError, "Freispeicherreserve"):
                reserve.bind_map(self.reference)
        self.assertFalse(
            (
                other_root
                / FINGERPRINT
                / "revisions"
                / "00000000000000000000.json"
            ).exists()
        )

    def test_upsert_rejects_projected_total_before_new_room_validation(self):
        exact_room_count = (
            MAXIMUM_TOTAL_POLYGON_POINTS // MAXIMUM_POLYGON_POINTS
        )
        document = SemanticDocument.from_dict(
            semantic_document_payload(room_set(exact_room_count))
        )
        with self.repository._lock():
            self.repository._commit_unlocked(document)

        incoming = valid_room(
            id="zusatzraum",
            name="Zusatzraum",
            polygon=regular_polygon(MAXIMUM_POLYGON_POINTS),
            navigation_goal={"x": 5.0, "y": 4.0, "yaw": 0.0},
        )
        with self.assertRaisesRegex(SemanticValidationError, "Mutation.*Gesamtlimit"):
            self.repository.upsert_room(
                map_fingerprint=FINGERPRINT,
                base_revision=0,
                room_payload=incoming,
                request_id="ios:complexity-limit",
                signature="c" * 64,
            )
        self.assertEqual(self.repository.load(FINGERPRINT).revision, 0)
        self.assertFalse(
            (
                self.root
                / FINGERPRINT
                / "revisions"
                / "00000000000000000001.json"
            ).exists()
        )

    def test_concurrent_same_base_allows_exactly_one_writer(self):
        self.repository.bind_map(self.reference)
        barrier = threading.Barrier(2)
        outcomes = []

        def worker(request_id, room_payload):
            repo = SemanticMapRepository(self.root)
            command = self.command(request_id=request_id, room=room_payload)
            barrier.wait()
            try:
                repo.upsert_room(
                    map_fingerprint=FINGERPRINT,
                    base_revision=0,
                    room_payload=command.room,
                    request_id=request_id,
                    signature=command_signature(command),
                )
                outcomes.append("ok")
            except RevisionConflictError:
                outcomes.append("conflict")

        first = threading.Thread(target=worker, args=("ios:a", valid_room()))
        second = threading.Thread(
            target=worker,
            args=(
                "ios:b",
                valid_room(
                    id="kueche",
                    name="Küche",
                    polygon=[
                        {"x": 5.0, "y": 1.0},
                        {"x": 7.0, "y": 1.0},
                        {"x": 7.0, "y": 3.0},
                        {"x": 5.0, "y": 3.0},
                    ],
                    navigation_goal={"x": 6.0, "y": 2.0, "yaw": 0.0},
                ),
            ),
        )
        first.start()
        second.start()
        first.join()
        second.join()
        self.assertCountEqual(outcomes, ["ok", "conflict"])
        self.assertEqual(self.repository.load(FINGERPRINT).revision, 1)


class SerializationTests(unittest.TestCase):
    def test_json_message_rejects_nan(self):
        with self.assertRaises(ValueError):
            json_message({"x": float("nan")})

    def test_document_limit_includes_trailing_newline(self):
        empty_size = len(_json_bytes({"x": ""}))
        exact = _json_bytes({"x": "a" * (MAXIMUM_DOCUMENT_BYTES - empty_size)})
        self.assertEqual(len(exact), MAXIMUM_DOCUMENT_BYTES)
        with self.assertRaisesRegex(SemanticStorageError, "Größenlimit"):
            _json_bytes({"x": "a" * (MAXIMUM_DOCUMENT_BYTES - empty_size + 1)})


class NodeSourceContractTests(unittest.TestCase):
    @staticmethod
    def node_source():
        node_path = (
            Path(__file__).resolve().parents[1]
            / "semantic_map_manager"
            / "semantic_map_manager_node.py"
        )
        return node_path.read_text(encoding="utf-8")

    def test_status_ok_is_rechecked_after_stale_guard(self):
        source = self.node_source()
        function_start = source.index("    def _publish_status(")
        function_end = source.index("    def _publish_catalog(", function_start)
        function_source = source[function_start:function_end]
        stale_check = function_source.index("self._apply_stale_guard()")
        effective_ok = function_source.index("ok = bool(ok and self._editable)")
        payload_ok = function_source.index('"ok": ok')
        self.assertLess(stale_check, effective_ok)
        self.assertLess(effective_ok, payload_ok)

    def test_runtime_replay_never_publishes_cached_status_payload(self):
        source = self.node_source()
        function_start = source.index("    def _on_command(")
        function_end = source.index("    def _handle_bind(", function_start)
        function_source = source[function_start:function_end]
        self.assertIn("_lookup_cached_request", function_source)
        self.assertNotIn("status_publisher.publish", function_source)
        self.assertNotIn("return\n", function_source.split("if replayed:", 1)[1].split(
            "except", 1
        )[0])

    def test_bind_requires_fresh_status_immediately_before_persistence(self):
        source = self.node_source()
        function_start = source.index("    def _handle_bind(")
        function_end = source.index("    def _require_fresh_observation(", function_start)
        function_source = source[function_start:function_end]
        persistence = function_source.index("self.repository.bind_map(match)")
        self.assertGreaterEqual(
            function_source[:persistence].count("self._require_fresh_observation()"),
            2,
        )


if __name__ == "__main__":
    unittest.main()
