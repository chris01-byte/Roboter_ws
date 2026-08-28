from types import SimpleNamespace
import json
import unittest

from semantic_perception.semantic_state import (
    SemanticStateError,
    bounded_object_status,
    localization_is_live,
    parse_localization_status,
)


def _status(**overrides):
    value = {
        'schema_version': 1,
        'ready': True,
        'state': 'localized',
        'reasons': [],
        'map_fingerprint': 'a' * 64,
        'global_initialization': 'completed',
        'time': 123.5,
    }
    value.update(overrides)
    return json.dumps(value)


class SemanticStateTests(unittest.TestCase):
    def test_ready_localization_requires_complete_map_binding(self):
        parsed = parse_localization_status(_status())

        self.assertTrue(parsed.ready)
        self.assertEqual(parsed.map_fingerprint, 'a' * 64)
        with self.assertRaises(SemanticStateError):
            parse_localization_status(_status(map_fingerprint=None))
        with self.assertRaises(SemanticStateError):
            parse_localization_status(_status(global_initialization='searching'))

    def test_localization_liveness_requires_two_fresh_advancing_messages(self):
        parsed = parse_localization_status(_status())

        self.assertFalse(localization_is_live(
            parsed, received_s=10.0, now_s=10.2,
            progress_count=1, maximum_age_s=1.0))
        self.assertTrue(localization_is_live(
            parsed, received_s=10.0, now_s=10.2,
            progress_count=2, maximum_age_s=1.0))
        self.assertFalse(localization_is_live(
            parsed, received_s=10.0, now_s=11.1,
            progress_count=2, maximum_age_s=1.0))

    def test_malformed_or_unbounded_status_is_rejected(self):
        for value in ('not-json', json.dumps([]), _status(reasons=['x' * 513])):
            with self.subTest(value=value[:20]):
                with self.assertRaises(SemanticStateError):
                    parse_localization_status(value)

    def test_object_status_keeps_only_current_finite_map_binding(self):
        pose = SimpleNamespace(pose=SimpleNamespace(position=SimpleNamespace(
            x=1.0, y=-0.5, z=0.8)))
        memory = {
            'cup': {
                'name': 'Tasse', 'pose': pose, 'conf': 0.7,
                'last_seen_time': 100.0, 'map_fingerprint': 'a' * 64,
            },
            'old': {
                'name': 'Flasche', 'pose': pose, 'conf': 0.9,
                'last_seen_time': 100.0, 'map_fingerprint': 'b' * 64,
            },
        }

        payload = bounded_object_status(
            frame_id='map', map_fingerprint='a' * 64, now=102.0,
            ready=True, memory=memory, maximum_objects=10,
            memory_ttl_s=5.0)

        self.assertEqual([item['name'] for item in payload['objects']], ['Tasse'])
        self.assertEqual(payload['objects'][0]['position']['x'], 1.0)
        self.assertEqual(payload['objects'][0]['age_s'], 2.0)


if __name__ == '__main__':
    unittest.main()
