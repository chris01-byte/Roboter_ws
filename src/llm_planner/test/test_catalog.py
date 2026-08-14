import json
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

from llm_planner.catalog import CatalogValidationError, merge_catalog_json


class CatalogTests(unittest.TestCase):
    def merge(self, payload):
        if isinstance(payload, dict):
            payload = {
                "schema_version": 1,
                "source": "semantic_map_manager",
                **payload,
            }
        return merge_catalog_json(
            json.dumps(payload),
            rooms=["Alt"],
            targets=["Tisch"],
            objects=["Tasse"],
        )

    def test_partial_room_catalog_preserves_objects_and_targets(self):
        result = self.merge({"rooms": ["Wohnzimmer", "Kueche"]})
        self.assertEqual(result.rooms, ("Wohnzimmer", "Kueche"))
        self.assertEqual(result.targets, ("Tisch",))
        self.assertEqual(result.objects, ("Tasse",))

    def test_dynamic_objects_and_targets_are_rejected(self):
        for field in ("objects", "targets"):
            with self.subTest(field=field):
                with self.assertRaises(CatalogValidationError):
                    self.merge({"rooms": ["Flur"], field: ["Fremd"]})

    def test_node_keeps_real_pick_and_place_rooms_static(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "llm_planner" / "llm_planner_node.py"
        ).read_text(encoding="utf-8")
        self.assertIn("self._static_rooms = tuple(self._rooms)", source)
        self.assertIn("cmd.get('room') not in self._static_rooms", source)
        self.assertIn("rooms=self._static_rooms", source)

    def test_room_entities_are_normalized_for_compatibility(self):
        result = self.merge({"rooms": [{"id": "room-1", "name": "Buero"}]})
        self.assertEqual(result.rooms, ("Buero",))

    def test_empty_or_invalid_update_never_erases_fallback(self):
        result = self.merge({"rooms": []})
        self.assertEqual(result.rooms, ("Alt",))
        for payload in ({"rooms": [3]}, []):
            with self.subTest(payload=payload):
                with self.assertRaises(CatalogValidationError):
                    self.merge(payload)

    def test_names_are_trimmed_and_casefold_duplicates_removed(self):
        result = self.merge({"rooms": ["  Flur ", "flur", "Kueche"]})
        self.assertEqual(result.rooms, ("Flur", "Kueche"))

    def test_oversized_payload_is_rejected(self):
        text = '{"rooms":["' + ("x" * (513 * 1024)) + '"]}'
        with self.assertRaises(CatalogValidationError):
            merge_catalog_json(
                text,
                rooms=["Alt"],
                targets=["Tisch"],
                objects=["Tasse"],
            )

    def test_not_ok_catalog_cannot_replace_fallback(self):
        with self.assertRaises(CatalogValidationError):
            self.merge({"ok": False, "rooms": ["Fremder Raum"]})

    def test_wrong_schema_or_source_is_rejected(self):
        base = {
            "schema_version": 1,
            "source": "semantic_map_manager",
            "rooms": ["Flur"],
        }
        for mutation in (
            {**base, "schema_version": 2},
            {**base, "source": "fremd"},
            {key: value for key, value in base.items() if key != "source"},
        ):
            with self.subTest(payload=mutation):
                with self.assertRaises(CatalogValidationError):
                    merge_catalog_json(
                        json.dumps(mutation),
                        rooms=["Alt"],
                        targets=["Tisch"],
                        objects=["Tasse"],
                    )

    def test_accepts_full_backend_room_count_and_name_limit(self):
        rooms = [f"Raum-{index}" for index in range(255)] + ["R" * 80]
        result = self.merge({"rooms": rooms})
        self.assertEqual(len(result.rooms), 256)
        self.assertEqual(result.rooms[-1], "R" * 80)

        with self.assertRaises(CatalogValidationError):
            self.merge({"rooms": rooms + ["Zu-viel"]})

    def test_accepts_backend_catalog_above_legacy_64k_limit(self):
        rooms = [f"{index:03d}-" + ("🏠" * 76) for index in range(256)]
        payload = {
            "schema_version": 1,
            "source": "semantic_map_manager",
            "ok": True,
            "rooms": rooms,
            "room_entities": [
                {
                    "id": f"room-{index}",
                    "name": name,
                    "navigation_goal": {
                        "x": index / 10,
                        "y": 1.0,
                        "yaw": 0.0,
                    },
                }
                for index, name in enumerate(rooms)
            ],
        }
        text = json.dumps(payload, ensure_ascii=False)
        self.assertGreater(len(text.encode("utf-8")), 64 * 1024)
        result = merge_catalog_json(
            text,
            rooms=["Alt"],
            targets=["Tisch"],
            objects=["Tasse"],
        )
        self.assertEqual(len(result.rooms), 256)

    def test_deep_json_and_invalid_unicode_fail_closed(self):
        for text in ('[' * 1_100 + '0' + ']' * 1_100, '\ud800'):
            with self.subTest(kind='unicode' if text == '\ud800' else 'deep'):
                with self.assertRaises(CatalogValidationError):
                    merge_catalog_json(
                        text,
                        rooms=["Alt"],
                        targets=["Tisch"],
                        objects=["Tasse"],
                    )


class LlmResponseParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy = types.ModuleType("rclpy")
        rclpy_node = types.ModuleType("rclpy.node")
        rclpy_qos = types.ModuleType("rclpy.qos")
        std_msgs = types.ModuleType("std_msgs")
        std_msgs_msg = types.ModuleType("std_msgs.msg")
        rclpy_node.Node = object
        rclpy_qos.QoSProfile = object
        rclpy_qos.QoSDurabilityPolicy = object
        rclpy_qos.QoSReliabilityPolicy = object
        std_msgs_msg.String = object
        module_path = (
            Path(__file__).resolve().parents[1]
            / "llm_planner" / "llm_planner_node.py"
        )
        spec = importlib.util.spec_from_file_location(
            "llm_planner_node_parser_test", module_path
        )
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {
            "rclpy": rclpy,
            "rclpy.node": rclpy_node,
            "rclpy.qos": rclpy_qos,
            "std_msgs": std_msgs,
            "std_msgs.msg": std_msgs_msg,
        }):
            spec.loader.exec_module(module)
        cls.extract_json = staticmethod(module.LlmPlanner._extract_json)
        cls.maximum_bytes = module.MAXIMUM_LLM_RESPONSE_BYTES

    def test_extracts_valid_json_object(self):
        self.assertEqual(
            self.extract_json('Antwort: {"type":"go_to_room","room":"Flur"}'),
            {"type": "go_to_room", "room": "Flur"},
        )

    def test_oversized_response_fails_closed(self):
        response = "x" * self.maximum_bytes + '{"type":"explore"}'
        self.assertIsNone(self.extract_json(response))

    def test_deep_json_and_invalid_unicode_fail_closed(self):
        responses = (
            '{"type":"explore","nested":' + '[' * 1_500
            + '0' + ']' * 1_500 + '}',
            '{"type":"go_to_room","room":"\ud800"}',
        )
        for response in responses:
            with self.subTest(kind="unicode" if "\ud800" in response else "deep"):
                self.assertIsNone(self.extract_json(response))


if __name__ == "__main__":
    unittest.main()
