from array import array
from datetime import datetime, timezone
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from robot_map_manager.map_core import (
    BoundedRequestCache,
    CachedCommandResponse,
    CommandValidationError,
    MapOrigin,
    MapRepository,
    MapSnapshot,
    MapStorageError,
    MapValidationError,
    MinimumIntervalGuard,
    RawDuplicateGuard,
    RequestIDConflict,
    SaveProtectionError,
    StoragePolicy,
    default_storage_root,
    json_message,
    parse_cached_command_response,
    parse_command_json,
    raw_cell_digest,
    validate_grid_shape_and_length,
    validate_map_name,
    validate_quaternion,
    validate_transform_timestamp,
)


def valid_origin() -> MapOrigin:
    return MapOrigin(1.25, -2.5, 0.0, 0.0, 0.0, 0.0, 1.0)


def valid_snapshot(
    *,
    cells=(0, 100, -1, 50),
    stamp=123,
) -> MapSnapshot:
    return MapSnapshot.from_values(
        width=2,
        height=2,
        resolution=0.05,
        frame_id="map",
        origin=valid_origin(),
        cells=cells,
        source_stamp_ns=stamp,
    )


def permissive_policy(**overrides) -> StoragePolicy:
    values = {
        "minimum_save_interval_s": 0.0,
        "minimum_free_space_bytes": 0,
        "maximum_versions_per_map": 1000,
        "maximum_total_storage_bytes": 10 * 1024 * 1024 * 1024,
        "maximum_map_names": 100,
        "staging_cleanup_min_age_s": 3600.0,
        "staging_cleanup_max_entries": 0,
    }
    values.update(overrides)
    return StoragePolicy(**values)


class SnapshotValidationTests(unittest.TestCase):
    def test_accepts_valid_map_and_fingerprint_ignores_stamp(self):
        first = valid_snapshot(stamp=1)
        second = valid_snapshot(stamp=999)
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertEqual(first.summary()["width"], 2)
        self.assertIsInstance(first.cells, bytes)
        self.assertEqual(first.cells, bytes((0, 100, 255, 50)))

    def test_rejects_invalid_dimensions_and_cell_limit(self):
        with self.assertRaises(MapValidationError):
            MapSnapshot.from_values(
                width=0,
                height=2,
                resolution=0.1,
                frame_id="map",
                origin=valid_origin(),
                cells=(),
            )
        with self.assertRaises(MapValidationError):
            MapSnapshot.from_values(
                width=4_000_001,
                height=1,
                resolution=0.1,
                frame_id="map",
                origin=valid_origin(),
                cells=(),
            )

    def test_rejects_wrong_data_length_and_cell_values(self):
        with self.assertRaises(MapValidationError):
            valid_snapshot(cells=(0, 1, 2))
        for invalid in (-2, 101, True, 1.5):
            with self.subTest(invalid=invalid):
                with self.assertRaises(MapValidationError):
                    valid_snapshot(cells=(0, 1, 2, invalid))

    def test_rejects_invalid_resolution_frame_and_stamp(self):
        common = {
            "width": 1,
            "height": 1,
            "origin": valid_origin(),
            "cells": (0,),
        }
        for resolution in (0, -0.1, float("nan"), float("inf"), True):
            with self.subTest(resolution=resolution):
                with self.assertRaises(MapValidationError):
                    MapSnapshot.from_values(
                        **common,
                        resolution=resolution,
                        frame_id="map",
                    )
        for frame in ("", "   ", "map\nchild"):
            with self.subTest(frame=frame):
                with self.assertRaises(MapValidationError):
                    MapSnapshot.from_values(
                        **common,
                        resolution=0.1,
                        frame_id=frame,
                    )
        with self.assertRaises(MapValidationError):
            MapSnapshot.from_values(
                **common,
                resolution=0.1,
                frame_id="map",
                source_stamp_ns=-1,
            )

    def test_rejects_zero_nonfinite_and_nonunit_quaternions(self):
        invalid_values = (
            (0.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 2.0),
            (0.0, 0.0, float("nan"), 1.0),
            (0.0, 0.0, float("inf"), 1.0),
        )
        for quaternion in invalid_values:
            with self.subTest(quaternion=quaternion):
                with self.assertRaises(MapValidationError):
                    validate_quaternion(quaternion)
        self.assertEqual(
            validate_quaternion((0.0, 0.0, 0.0, 1.0)),
            (0.0, 0.0, 0.0, 1.0),
        )

    def test_direct_snapshot_construction_cannot_bypass_compact_validation(self):
        with self.assertRaises(MapValidationError):
            MapSnapshot(
                width=1,
                height=1,
                resolution=0.1,
                frame_id="map",
                origin=valid_origin(),
                cells=bytes((254,)),
            )

    def test_maximum_map_uses_compact_cell_storage(self):
        cell_count = 4_000_000
        snapshot = MapSnapshot.from_values(
            width=2000,
            height=2000,
            resolution=0.05,
            frame_id="map",
            origin=valid_origin(),
            cells=itertools.repeat(-1, cell_count),
        )
        self.assertEqual(len(snapshot.cells), cell_count)
        self.assertLessEqual(sys.getsizeof(snapshot.cells), cell_count + 64)
        self.assertIs(snapshot.fingerprint, snapshot.fingerprint)

    def test_signed_byte_buffer_fast_path_is_strict_and_lossless(self):
        cells = array("b", [0, 100, -1, 50])
        count, digest, fallback = raw_cell_digest(cells)
        self.assertEqual(count, 4)
        self.assertEqual(len(digest), 64)
        self.assertIsNone(fallback)
        self.assertEqual(valid_snapshot(cells=cells).cells, bytes((0, 100, 255, 50)))
        with self.assertRaises(MapValidationError):
            valid_snapshot(cells=array("b", [0, 100, -2, 50]))

    def test_generic_raw_digest_returns_reusable_validated_fallback(self):
        count, digest, fallback = raw_cell_digest([0, 100, -1, 50])
        self.assertEqual(count, 4)
        self.assertEqual(len(digest), 64)
        self.assertEqual(fallback, bytes((0, 100, 255, 50)))

    def test_raw_digest_rejects_oversize_before_iterating(self):
        class OversizeCells:
            def __len__(self):
                return 4_000_001

            def __iter__(self):
                raise AssertionError("darf bei Übergröße nicht iterieren")

        with self.assertRaises(MapValidationError):
            raw_cell_digest(OversizeCells())

    def test_cheap_shape_check_rejects_before_digest_stage(self):
        self.assertEqual(validate_grid_shape_and_length(2, 2, 4), 4)
        for width, height, length in (
            (0, 2, 0),
            (100_001, 1, 100_001),
            (2001, 2000, 4_002_000),
            (2, 2, 3),
        ):
            with self.subTest(
                width=width,
                height=height,
                length=length,
            ):
                with self.assertRaises(MapValidationError):
                    validate_grid_shape_and_length(width, height, length)


class CommandValidationTests(unittest.TestCase):
    def test_accepts_all_supported_commands(self):
        self.assertEqual(parse_command_json('{"command":"save"}').command, "save")
        listed = parse_command_json(
            '{"command":"list","name":"wohnung_1","request_id":"ios:42"}'
        )
        self.assertEqual(listed.name, "wohnung_1")
        self.assertEqual(listed.request_id, "ios:42")
        self.assertEqual(
            parse_command_json('{"command":"status"}').command,
            "status",
        )

    def test_rejects_malformed_unknown_and_extra_commands(self):
        invalid_payloads = (
            "",
            "[]",
            '{"command":"delete"}',
            '{"command":"save","extra":true}',
            '{"command":"status","name":"wohnung"}',
            '{"command":"save","request_id":"../bad"}',
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(CommandValidationError):
                    parse_command_json(payload)

    def test_deep_and_invalid_unicode_commands_fail_closed(self):
        payloads = (
            '{"command":"status","x":' + '[' * 1_500 +
            '0' + ']' * 1_500 + '}',
            '{"command":"status","request_id":"bad\ud800"}',
        )
        for payload in payloads:
            with self.subTest(size=len(payload)):
                with self.assertRaises(CommandValidationError):
                    parse_command_json(payload)

    def test_path_names_are_strict(self):
        self.assertEqual(validate_map_name("wohnung_2-alt"), "wohnung_2-alt")
        for value in (
            "",
            ".",
            "..",
            "../wohnung",
            "wohnung/keller",
            "Wohnung",
            "wohn ung",
            ".hidden",
            "a" * 65,
            42,
        ):
            with self.subTest(value=value):
                with self.assertRaises(MapValidationError):
                    validate_map_name(value)

    def test_json_message_rejects_nonfinite_numbers(self):
        self.assertEqual(json.loads(json_message({"ok": True})), {"ok": True})
        with self.assertRaises(ValueError):
            json_message({"bad": float("nan")})


class RuntimeGuardTests(unittest.TestCase):
    def test_global_minimum_interval_rejects_rotating_callers(self):
        guard = MinimumIntervalGuard(10.0)
        self.assertEqual(guard.acquire(now=100.0), (True, 0.0))
        allowed, remaining = guard.acquire(now=101.5)
        self.assertFalse(allowed)
        self.assertAlmostEqual(remaining, 8.5)
        # Abgelehnte Aufrufe verschieben das globale Fenster nicht.
        self.assertEqual(guard.acquire(now=110.0), (True, 0.0))

    def test_request_cache_replays_conflicts_and_evicts_oldest(self):
        cache = BoundedRequestCache(2)
        cache.store("one", ("save", "a"), '{"ok":true}')
        self.assertEqual(
            cache.lookup("one", ("save", "a")),
            '{"ok":true}',
        )
        with self.assertRaises(RequestIDConflict):
            cache.lookup("one", ("save", "b"))
        cache.store("two", ("status",), '{"ok":true}')
        # Zugriff auf "one" macht diesen Eintrag zum jüngsten.
        cache.lookup("one", ("save", "a"))
        cache.store("three", ("list", None), '{"ok":true}')
        self.assertIsNone(cache.lookup("two", ("status",)))
        self.assertEqual(len(cache), 2)

    def test_old_full_status_replay_keeps_result_but_drops_runtime_state(self):
        old_fingerprint = "a" * 64
        cached = json_message({
            "schema_version": 1,
            "event": "save_result",
            "ok": True,
            "command": "save",
            "request_id": "ios-map-old",
            "message": "Karte A gespeichert.",
            "time": 10.0,
            "last_operation": "save",
            "last_error": None,
            "map": {"summary": {"fingerprint": old_fingerprint}},
            "pose": {"available": True},
            "storage": {"last_saved": {"fingerprint": old_fingerprint}},
            "counters": {"idempotent_replays": 0},
            "saved": {"fingerprint": old_fingerprint, "name": "wohnung"},
            "origin": "command",
        })

        result = parse_cached_command_response(
            cached,
            expected_request_id="ios-map-old",
            expected_command="save",
        )

        self.assertIsInstance(result, CachedCommandResponse)
        compact = json.loads(result.as_cache_json())
        self.assertNotIn("map", compact)
        self.assertNotIn("pose", compact)
        self.assertNotIn("storage", compact)
        self.assertNotIn("time", compact)
        self.assertNotIn("counters", compact)
        self.assertEqual(compact["saved"]["fingerprint"], old_fingerprint)

    def test_late_replay_after_map_change_uses_fresh_status_factory(self):
        old_fingerprint = "a" * 64
        current_fingerprint = "b" * 64
        old_status = json_message({
            "schema_version": 1,
            "event": "save_result",
            "ok": True,
            "command": "save",
            "request_id": "ios-map-late",
            "message": "Alte Karte gespeichert.",
            "time": 10.0,
            "map": {"summary": {"fingerprint": old_fingerprint}},
            "storage": {"last_saved": {"fingerprint": old_fingerprint}},
            "saved": {"fingerprint": old_fingerprint, "name": "wohnung"},
        })
        result = parse_cached_command_response(
            old_status,
            expected_request_id="ios-map-late",
            expected_command="save",
        )

        # Entspricht dem Produktionspfad: publish_kwargs liefert ausschliesslich
        # das alte Kommandoergebnis; der Status-Builder setzt aktuelle Felder.
        fresh_runtime_state = {
            "time": 20.0,
            "map": {"summary": {"fingerprint": current_fingerprint}},
            "storage": {"last_saved": {"fingerprint": current_fingerprint}},
        }
        replayed = {**result.publish_kwargs(), **fresh_runtime_state}

        self.assertEqual(
            replayed["map"]["summary"]["fingerprint"],
            current_fingerprint,
        )
        self.assertEqual(
            replayed["storage"]["last_saved"]["fingerprint"],
            current_fingerprint,
        )
        self.assertEqual(replayed["time"], 20.0)
        self.assertTrue(replayed["extra"]["idempotent_replay"])
        self.assertEqual(
            replayed["extra"]["saved"]["fingerprint"],
            old_fingerprint,
        )
        self.assertFalse(result.publish_kwargs(current_status_ok=False)["ok"])
        with self.assertRaises(MapStorageError):
            result.publish_kwargs(current_status_ok=1)

    def test_cached_response_identity_and_schema_mismatch_fail_closed(self):
        valid = json_message({
            "schema_version": 1,
            "event": "status",
            "ok": True,
            "command": "status",
            "request_id": "ios-status-1",
            "message": "Bereit.",
        })
        with self.assertRaises(MapStorageError):
            parse_cached_command_response(
                valid,
                expected_request_id="ios-status-2",
                expected_command="status",
            )
        with self.assertRaises(MapStorageError):
            parse_cached_command_response(
                valid,
                expected_request_id="ios-status-1",
                expected_command="save",
            )
        with self.assertRaises(MapStorageError):
            parse_cached_command_response('{"schema_version":2}')

    def test_node_replay_path_rebuilds_instead_of_raw_publishing(self):
        node_source = (
            Path(__file__).parents[1]
            / "robot_map_manager"
            / "robot_map_manager_node.py"
        ).read_text(encoding="utf-8")
        replay_start = node_source.index("            if cached_response is not None:")
        replay_end = node_source.index(
            '        if command.command == "save":',
            replay_start,
        )
        replay_block = node_source[replay_start:replay_end]
        self.assertIn("parse_cached_command_response(", replay_block)
        self.assertIn("self._publish_status(**replay)", replay_block)
        self.assertNotIn("self.status_publisher.publish", replay_block)

    def test_raw_duplicate_guard_skips_only_valid_cross_qos_delivery(self):
        guard = RawDuplicateGuard(1.0)
        signature = ("metadata", "complete-digest")
        self.assertFalse(
            guard.is_duplicate(
                signature,
                source="transient",
                now=10.0,
                has_ros_identity=True,
            )
        )
        # Eine noch nicht validierte Erstlieferung darf nichts überspringen.
        self.assertFalse(
            guard.is_duplicate(
                signature,
                source="volatile",
                now=10.1,
                has_ros_identity=True,
            )
        )
        guard.mark_valid(signature, source="volatile", now=10.1)
        self.assertTrue(
            guard.is_duplicate(
                signature,
                source="transient",
                now=10.2,
                has_ros_identity=True,
            )
        )
        self.assertFalse(
            guard.is_duplicate(
                signature,
                source="volatile",
                now=10.3,
                has_ros_identity=True,
            )
        )

    def test_raw_duplicate_guard_requires_ros_identity_and_window(self):
        signature = ("same",)
        guard = RawDuplicateGuard(0.5)
        guard.is_duplicate(
            signature,
            source="transient",
            now=1.0,
            has_ros_identity=True,
        )
        guard.mark_valid(signature, source="transient", now=1.0)
        self.assertFalse(
            guard.is_duplicate(
                signature,
                source="volatile",
                now=2.0,
                has_ros_identity=True,
            )
        )
        guard.mark_valid(signature, source="transient", now=3.0)
        self.assertFalse(
            guard.is_duplicate(
                signature,
                source="volatile",
                now=3.1,
                has_ros_identity=False,
            )
        )

    def test_tf_timestamp_uses_zero_stamp_convention_and_reports_age(self):
        self.assertEqual(
            validate_transform_timestamp(
                stamp_ns=0,
                now_ns=100_000_000_000,
                maximum_age_s=1.0,
            ),
            (True, None),
        )
        uses_zero_stamp_convention, age = validate_transform_timestamp(
            stamp_ns=99_500_000_000,
            now_ns=100_000_000_000,
            maximum_age_s=1.0,
        )
        self.assertFalse(uses_zero_stamp_convention)
        self.assertAlmostEqual(age, 0.5)
        with self.assertRaises(MapValidationError):
            validate_transform_timestamp(
                stamp_ns=98_000_000_000,
                now_ns=100_000_000_000,
                maximum_age_s=1.0,
            )
        _uses_zero_stamp_convention, future_age = validate_transform_timestamp(
            stamp_ns=100_100_000_000,
            now_ns=100_000_000_000,
            maximum_age_s=1.0,
        )
        self.assertAlmostEqual(future_age, -0.1)


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "maps"
        self.repository = MapRepository(
            self.root,
            default_name="amadeus",
            policy=permissive_policy(),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_storage_path_is_outside_workspace_convention(self):
        self.assertEqual(
            default_storage_root(Path("/home/robot")),
            Path("/home/robot/.local/share/amadeus/maps"),
        )

    def test_root_must_be_absolute(self):
        with self.assertRaises(MapStorageError):
            MapRepository(Path("relative/maps"), policy=permissive_policy())

    def test_storage_chain_fsyncs_to_same_device_mount_root(self):
        existing = Path(self.temporary.name) / "existing"
        existing.mkdir()
        root = existing / "level-one" / "level-two" / "maps"
        with mock.patch.object(
            MapRepository,
            "_sync_directory",
            wraps=MapRepository._sync_directory,
        ) as sync_directory:
            repository = MapRepository(
                root,
                policy=permissive_policy(),
            )
        self.assertEqual(repository.root, root.resolve())
        synced = [call.args[0] for call in sync_directory.call_args_list]
        expected = []
        root_device = repository.root.stat().st_dev
        parent = repository.root.parent
        while parent.stat().st_dev == root_device:
            expected.append(parent)
            if parent.parent == parent:
                break
            parent = parent.parent
        if not expected:
            expected.append(repository.root)
        self.assertEqual(synced, expected)
        mount_root = expected[-1]
        if mount_root.parent != mount_root:
            self.assertNotEqual(
                mount_root.parent.stat().st_dev,
                root_device,
            )

    def test_storage_chain_fsync_failure_prevents_first_and_retry_start(self):
        existing = Path(self.temporary.name) / "existing-failure"
        existing.mkdir()
        root = existing / "new-parent" / "maps"
        with mock.patch.object(
            MapRepository,
            "_sync_directory",
            side_effect=OSError("simulierter Eltern-fsync-Fehler"),
        ) as sync_directory:
            for _attempt in range(2):
                with self.assertRaisesRegex(
                    MapStorageError,
                    "Eltern-fsync",
                ):
                    MapRepository(root, policy=permissive_policy())
        self.assertEqual(sync_directory.call_count, 2)
        self.assertTrue(root.is_dir())

    def test_save_creates_complete_version_and_exact_binary_data(self):
        now = datetime(2026, 7, 26, 12, 34, 56, 123456, tzinfo=timezone.utc)
        saved = self.repository.save(valid_snapshot(), name="wohnung", now=now)

        self.assertEqual(saved.path.parent, self.root.resolve() / "wohnung")
        self.assertRegex(
            saved.version,
            r"^20260726T123456123456Z-[0-9a-f]{12}$",
        )
        self.assertEqual(
            {item.name for item in saved.path.iterdir()},
            {"map.pgm", "map.yaml", "occupancy.bin", "metadata.json"},
        )
        self.assertEqual(
            (saved.path / "occupancy.bin").read_bytes(),
            bytes((0, 100, 255, 50)),
        )
        metadata = json.loads(
            (saved.path / "metadata.json").read_text(encoding="utf-8")
        )
        self.assertEqual(metadata["name"], "wohnung")
        self.assertEqual(metadata["width"], 2)
        self.assertEqual(metadata["files"]["occupancy.bin"]["bytes"], 4)
        self.assertEqual(len(metadata["files"]["map.pgm"]["sha256"]), 64)

    def test_pgm_flips_ros_rows_and_uses_expected_grays(self):
        saved = self.repository.save(valid_snapshot())
        pgm = (saved.path / "map.pgm").read_bytes()
        raster = pgm.split(b"\n", 4)[4]
        self.assertEqual(raster, bytes((205, 127, 254, 0)))
        yaml = (saved.path / "map.yaml").read_text(encoding="utf-8")
        self.assertIn("image: map.pgm", yaml)
        self.assertIn("resolution: 0.050000000000000003", yaml)

    def test_repeated_save_is_versioned_without_overwrite(self):
        now = datetime(2026, 7, 26, tzinfo=timezone.utc)
        first = self.repository.save(valid_snapshot(), now=now)
        second = self.repository.save(valid_snapshot(), now=now)
        self.assertNotEqual(first.version, second.version)
        self.assertTrue(first.path.is_dir())
        self.assertTrue(second.path.is_dir())
        self.assertTrue(second.version.endswith("-01"))

    def test_list_filters_and_orders_versions(self):
        old = datetime(2026, 7, 25, tzinfo=timezone.utc)
        new = datetime(2026, 7, 26, tzinfo=timezone.utc)
        self.repository.save(valid_snapshot(), name="wohnung", now=old)
        latest = self.repository.save(valid_snapshot(), name="wohnung", now=new)
        self.repository.save(valid_snapshot(), name="werkstatt", now=new)

        all_records = self.repository.list_versions()
        self.assertEqual(len(all_records), 3)
        filtered = self.repository.list_versions(name="wohnung")
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].version, latest.version)
        self.assertEqual(len(self.repository.list_versions(limit=1)), 1)

    @unittest.skipUnless(hasattr(os, "symlink"), "Symlinks nicht verfügbar")
    def test_list_ignores_symlinked_map_directory(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        os.symlink(outside, self.root / "escape")
        self.assertEqual(self.repository.list_versions(), [])
        with self.assertRaises(MapStorageError):
            self.repository.save(valid_snapshot(), name="escape")

    def test_corrupt_metadata_is_ignored(self):
        saved = self.repository.save(valid_snapshot())
        (saved.path / "metadata.json").write_text("{broken", encoding="utf-8")
        self.assertEqual(self.repository.list_versions(), [])

    def test_modified_pgm_is_rejected_by_checksum_verification(self):
        saved = self.repository.save(valid_snapshot())
        pgm_path = saved.path / "map.pgm"
        content = bytearray(pgm_path.read_bytes())
        content[-1] ^= 0x01
        pgm_path.write_bytes(content)
        self.assertEqual(self.repository.list_versions(), [])

    def test_failed_write_leaves_no_visible_or_staging_version(self):
        class FailingRepository(MapRepository):
            def _write_bytes(self, path, content):
                super()._write_bytes(path, content)
                if path.name == "map.pgm":
                    raise MapStorageError("simulierter Schreibfehler")

        broken_root = Path(self.temporary.name) / "broken"
        repository = FailingRepository(
            broken_root,
            policy=permissive_policy(),
        )
        with self.assertRaises(MapStorageError):
            repository.save(valid_snapshot())
        name_directory = broken_root / "amadeus"
        self.assertTrue(name_directory.is_dir())
        self.assertEqual(list(name_directory.iterdir()), [])

    def test_save_interval_is_global_across_map_names_and_deletes_nothing(self):
        repository = MapRepository(
            Path(self.temporary.name) / "global-interval",
            policy=permissive_policy(minimum_save_interval_s=10.0),
        )
        first_time = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
        first = repository.save(
            valid_snapshot(),
            name="wohnung",
            now=first_time,
        )
        too_soon = datetime(2026, 7, 26, 12, 0, 5, tzinfo=timezone.utc)
        with self.assertRaises(SaveProtectionError):
            repository.save(
                valid_snapshot(),
                name="werkstatt",
                now=too_soon,
            )
        self.assertTrue(first.path.is_dir())
        self.assertFalse((repository.root / "werkstatt").exists())

    def test_version_limit_rejects_without_deleting_existing_version(self):
        repository = MapRepository(
            Path(self.temporary.name) / "version-limit",
            policy=permissive_policy(maximum_versions_per_map=1),
        )
        first = repository.save(
            valid_snapshot(),
            now=datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        with self.assertRaises(SaveProtectionError):
            repository.save(
                valid_snapshot(),
                now=datetime(2026, 7, 27, tzinfo=timezone.utc),
            )
        self.assertTrue(first.path.is_dir())
        self.assertEqual(
            [child for child in first.path.parent.iterdir() if child.is_dir()],
            [first.path],
        )

    def test_map_name_limit_rejects_new_name_but_allows_existing_name(self):
        repository = MapRepository(
            Path(self.temporary.name) / "name-limit",
            policy=permissive_policy(maximum_map_names=1),
        )
        repository.save(
            valid_snapshot(),
            name="wohnung",
            now=datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        repository.save(
            valid_snapshot(cells=(1, 2, 3, 4)),
            name="wohnung",
            now=datetime(2026, 7, 27, tzinfo=timezone.utc),
        )
        with self.assertRaises(SaveProtectionError):
            repository.save(
                valid_snapshot(),
                name="werkstatt",
                now=datetime(2026, 7, 28, tzinfo=timezone.utc),
            )
        self.assertEqual(repository._map_names(), ["wohnung"])

    def test_total_storage_limit_rejects_before_creating_map_directory(self):
        repository = MapRepository(
            Path(self.temporary.name) / "total-limit",
            policy=permissive_policy(maximum_total_storage_bytes=1),
        )
        with self.assertRaises(SaveProtectionError):
            repository.save(valid_snapshot(), name="wohnung")
        self.assertFalse((repository.root / "wohnung").exists())

    def test_minimum_free_space_rejects_conservatively(self):
        repository = MapRepository(
            Path(self.temporary.name) / "free-limit",
            policy=permissive_policy(minimum_free_space_bytes=10_000),
        )
        fake_usage = type(
            "DiskUsage",
            (),
            {"total": 20_000, "used": 10_000, "free": 10_000},
        )()
        with mock.patch(
            "robot_map_manager.map_core.shutil.disk_usage",
            return_value=fake_usage,
        ):
            with self.assertRaises(SaveProtectionError):
                repository.save(valid_snapshot(), name="wohnung")
        self.assertFalse((repository.root / "wohnung").exists())

    def test_post_commit_directory_fsync_error_is_success_with_warning(self):
        class PostCommitFsyncFailure(MapRepository):
            def _sync_directory(self, path):
                if path.name == "amadeus":
                    raise OSError("simulierter Verzeichnis-fsync-Fehler")
                return super()._sync_directory(path)

        repository = PostCommitFsyncFailure(
            Path(self.temporary.name) / "post-commit",
            policy=permissive_policy(),
        )
        saved = repository.save(valid_snapshot())
        self.assertTrue(saved.path.is_dir())
        self.assertIsNotNone(saved.durability_warning)
        self.assertIn("atomar sichtbar", saved.durability_warning)
        self.assertEqual(len(repository.list_versions()), 1)

    def test_new_map_name_syncs_root_and_root_error_is_only_warning(self):
        class RootFsyncFailure(MapRepository):
            def __init__(self, *args, **kwargs):
                self.synced_paths = []
                super().__init__(*args, **kwargs)

            def _sync_directory(self, path):
                self.synced_paths.append(path)
                if path == getattr(self, "root", None):
                    raise OSError("simulierter Root-fsync-Fehler")
                return super()._sync_directory(path)

        repository = RootFsyncFailure(
            Path(self.temporary.name) / "root-fsync",
            policy=permissive_policy(),
        )
        saved = repository.save(valid_snapshot(), name="wohnung")
        self.assertTrue(saved.path.is_dir())
        self.assertIn(repository.root, repository.synced_paths)
        self.assertIsNotNone(saved.durability_warning)
        self.assertIn("Speicherwurzel", saved.durability_warning)
        self.assertEqual(len(repository.list_versions(name="wohnung")), 1)

    def test_repository_lock_serializes_concurrent_policy_and_commit(self):
        state_lock = threading.Lock()
        state = {"active": 0, "maximum": 0}

        class ObservedRepository(MapRepository):
            def _save_locked(self, *args, **kwargs):
                with state_lock:
                    state["active"] += 1
                    state["maximum"] = max(
                        state["maximum"],
                        state["active"],
                    )
                try:
                    time.sleep(0.05)
                    return super()._save_locked(*args, **kwargs)
                finally:
                    with state_lock:
                        state["active"] -= 1

        root = Path(self.temporary.name) / "locked"
        first_repository = ObservedRepository(
            root,
            policy=permissive_policy(minimum_save_interval_s=10.0),
        )
        second_repository = ObservedRepository(
            root,
            policy=permissive_policy(minimum_save_interval_s=10.0),
        )
        start = threading.Barrier(3)
        results = []
        errors = []
        fixed_time = datetime(2026, 7, 26, tzinfo=timezone.utc)

        def worker(repository, name):
            start.wait()
            try:
                results.append(
                    repository.save(
                        valid_snapshot(),
                        name=name,
                        now=fixed_time,
                    )
                )
            except Exception as error:
                errors.append(error)

        threads = [
            threading.Thread(
                target=worker,
                args=(first_repository, "wohnung"),
            ),
            threading.Thread(
                target=worker,
                args=(second_repository, "werkstatt"),
            ),
        ]
        for thread in threads:
            thread.start()
        start.wait()
        for thread in threads:
            thread.join(timeout=5.0)
            self.assertFalse(thread.is_alive())

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], SaveProtectionError)
        self.assertEqual(len(results), 1)
        self.assertEqual(state["maximum"], 1)
        self.assertEqual(len(first_repository.list_versions()), 1)

    def test_startup_cleanup_is_old_bounded_and_never_removes_versions(self):
        root = Path(self.temporary.name) / "cleanup"
        name_directory = root / "amadeus"
        name_directory.mkdir(parents=True)
        old_a = name_directory / (".tmp-" + "a" * 32)
        old_b = name_directory / (".tmp-" + "b" * 32)
        recent = name_directory / (".tmp-" + "c" * 32)
        visible_version = (
            name_directory
            / "20260726T120000000000Z-123456789abc"
        )
        for directory in (old_a, old_b, recent, visible_version):
            directory.mkdir()
        now = time.time()
        os.utime(old_a, (now - 7200, now - 7200))
        os.utime(old_b, (now - 7100, now - 7100))
        os.utime(recent, (now, now))

        repository = MapRepository(
            root,
            policy=permissive_policy(
                staging_cleanup_min_age_s=3600.0,
                staging_cleanup_max_entries=1,
            ),
        )
        self.assertEqual(repository.cleanup_removed, 1)
        self.assertEqual(sum(path.exists() for path in (old_a, old_b)), 1)
        self.assertTrue(recent.is_dir())
        self.assertTrue(visible_version.is_dir())

    def test_startup_cleanup_refuses_unexpected_staging_contents(self):
        root = Path(self.temporary.name) / "unsafe-cleanup"
        staging = root / "amadeus" / (".tmp-" + "d" * 32)
        staging.mkdir(parents=True)
        (staging / "foreign.txt").write_text("nicht vom Manager")
        old = time.time() - 7200
        os.utime(staging, (old, old))
        repository = MapRepository(
            root,
            policy=permissive_policy(
                staging_cleanup_min_age_s=3600.0,
                staging_cleanup_max_entries=1,
            ),
        )
        self.assertEqual(repository.cleanup_removed, 0)
        self.assertEqual(repository.cleanup_errors, 1)
        self.assertTrue((staging / "foreign.txt").is_file())

    def test_list_verifies_only_bounded_newest_candidates(self):
        repository = MapRepository(
            Path(self.temporary.name) / "bounded-list",
            policy=permissive_policy(),
        )
        saved = []
        for day in range(1, 7):
            saved.append(
                repository.save(
                    valid_snapshot(cells=(day, day, day, day)),
                    now=datetime(
                        2026,
                        7,
                        day,
                        tzinfo=timezone.utc,
                    ),
                )
            )
        for record in saved[-2:]:
            (record.path / "metadata.json").write_text(
                "{broken",
                encoding="utf-8",
            )
        with mock.patch.object(
            repository,
            "_read_record",
            wraps=repository._read_record,
        ) as read_record:
            self.assertEqual(repository.list_versions(limit=1), [])
            self.assertEqual(read_record.call_count, 2)

    def test_list_hash_io_stops_before_configured_byte_budget(self):
        root = Path(self.temporary.name) / "list-byte-budget"
        writer = MapRepository(root, policy=permissive_policy())
        first = writer.save(
            valid_snapshot(),
            now=datetime(2026, 7, 25, tzinfo=timezone.utc),
        )
        writer.save(
            valid_snapshot(cells=(1, 2, 3, 4)),
            now=datetime(2026, 7, 26, tzinfo=timezone.utc),
        )
        metadata = json.loads(
            (first.path / "metadata.json").read_text(encoding="utf-8")
        )
        one_candidate_bytes = sum(
            descriptor["bytes"]
            for descriptor in metadata["files"].values()
        )
        reader = MapRepository(
            root,
            policy=permissive_policy(
                maximum_list_verify_bytes=one_candidate_bytes,
            ),
        )
        report = reader.list_versions_with_report(limit=2)
        self.assertEqual(len(report.records), 1)
        self.assertTrue(report.truncated)
        self.assertIn(
            "verification_byte_budget",
            report.truncation_reasons,
        )
        self.assertEqual(
            report.artifact_verification_bytes_reserved,
            one_candidate_bytes,
        )
        self.assertLessEqual(
            report.artifact_verification_bytes_reserved,
            report.maximum_list_verify_bytes,
        )
        policy_payload = report.policy_dict()
        self.assertTrue(policy_payload["truncated"])
        self.assertEqual(
            policy_payload["maximum_list_verify_bytes"],
            one_candidate_bytes,
        )

    def test_large_declared_artifacts_are_not_hashed_past_budget(self):
        root = Path(self.temporary.name) / "declared-byte-budget"
        version = "20260726T120000000000Z-123456789abc"
        version_directory = root / "amadeus" / version
        version_directory.mkdir(parents=True)
        huge_files = {
            "occupancy.bin": {
                "bytes": 4_000_000,
                "sha256": "0" * 64,
            },
            "map.pgm": {
                "bytes": 4_004_096,
                "sha256": "1" * 64,
            },
            "map.yaml": {
                "bytes": 65_536,
                "sha256": "2" * 64,
            },
        }
        metadata = {
            "schema_version": 1,
            "name": "amadeus",
            "version": version,
            "saved_at": "2026-07-26T12:00:00Z",
            "width": 2000,
            "height": 2000,
            "resolution": 0.05,
            "frame_id": "map",
            "fingerprint": "3" * 64,
            "files": huge_files,
        }
        (version_directory / "metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )
        repository = MapRepository(
            root,
            policy=permissive_policy(maximum_list_verify_bytes=1024),
        )
        with mock.patch.object(
            repository,
            "_verify_artifact",
            return_value=True,
        ) as verify_artifact:
            report = repository.list_versions_with_report(limit=1)
        self.assertEqual(report.records, ())
        self.assertEqual(verify_artifact.call_count, 0)
        self.assertEqual(
            report.truncation_reasons,
            ("verification_byte_budget",),
        )
        self.assertEqual(report.artifact_verification_bytes_reserved, 0)

    def test_storage_policy_rejects_zero_hard_limits(self):
        with self.assertRaises(MapStorageError):
            StoragePolicy(maximum_versions_per_map=0).validated()
        with self.assertRaises(MapStorageError):
            StoragePolicy(maximum_total_storage_bytes=0).validated()
        with self.assertRaises(MapStorageError):
            StoragePolicy(maximum_map_names=0).validated()
        with self.assertRaises(MapStorageError):
            StoragePolicy(maximum_list_verify_bytes=0).validated()


if __name__ == "__main__":
    unittest.main()
