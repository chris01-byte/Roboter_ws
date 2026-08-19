import json
import unittest

from mission_manager.semantic_catalog import decode_catalog_payload


def catalog_payload(**values):
    return {
        'schema_version': 1,
        'source': 'semantic_map_manager',
        **values,
    }


class SemanticCatalogTests(unittest.TestCase):
    def test_accepts_legacy_names_and_structured_room_entries(self):
        update, error = decode_catalog_payload(json.dumps(catalog_payload(
            ok=True,
            rooms=[{'id': 'room-1', 'name': ' Wohnzimmer '}, 'Kueche'],
            room_entities=[{'id': 'room-1', 'name': 'Wohnzimmer'}],
        )))
        self.assertIsNone(error)
        self.assertEqual(update['rooms'], ['Wohnzimmer', 'Kueche'])

    def test_objects_and_targets_cannot_expand_real_allowlists(self):
        for field in ('objects', 'targets'):
            with self.subTest(field=field):
                payload = catalog_payload(rooms=['Flur'], **{field: ['Fremd']})
                update, error = decode_catalog_payload(json.dumps(payload))
                self.assertIsNone(update)
                self.assertIn('nur die Raumliste', error)

    def test_empty_list_does_not_clear_fallback_catalog(self):
        update, error = decode_catalog_payload(json.dumps(catalog_payload(rooms=[])))
        self.assertIsNone(error)
        self.assertEqual(update, {'rooms': []})

    def test_deduplicates_case_insensitively(self):
        update, error = decode_catalog_payload(json.dumps(
            catalog_payload(rooms=['Flur', 'flur'])))
        self.assertIsNone(error)
        self.assertEqual(update['rooms'], ['Flur'])

    def test_invalid_or_not_ok_payload_does_not_produce_update(self):
        for payload in (
                '[]',
                json.dumps(catalog_payload(ok=False, rooms=['Flur'])),
                json.dumps(catalog_payload(rooms=[42])),
                json.dumps(catalog_payload(revision=1)),
                json.dumps({'schema_version': 1, 'source': 'fremd', 'rooms': ['Flur']}),
                json.dumps({'source': 'semantic_map_manager', 'rooms': ['Flur']})):
            with self.subTest(payload=payload):
                update, error = decode_catalog_payload(payload)
                self.assertIsNone(update)
                self.assertTrue(error)

    def test_resource_bounds_and_control_characters_fail_closed(self):
        payloads = (
            json.dumps(catalog_payload(rooms=['x' * 81])),
            json.dumps(catalog_payload(rooms=['Flur\x00'])),
            json.dumps(catalog_payload(
                rooms=[f'Raum-{index}' for index in range(257)])),
            json.dumps(catalog_payload(rooms=['x' * (513 * 1024)])),
        )
        for payload in payloads:
            with self.subTest(size=len(payload)):
                update, error = decode_catalog_payload(payload)
                self.assertIsNone(update)
                self.assertTrue(error)

    def test_accepts_backend_sized_256_room_catalog_above_legacy_limit(self):
        rooms = [f'{index:03d}-' + ('🏠' * 76) for index in range(256)]
        room_entities = [
            {
                'id': f'room-{index}',
                'name': name,
                'navigation_goal': {'x': index / 10, 'y': 1.0, 'yaw': 0.0},
            }
            for index, name in enumerate(rooms)
        ]
        payload = json.dumps(
            catalog_payload(
                ok=True,
                rooms=rooms,
                room_entities=room_entities,
                map_fingerprint='a' * 64,
                revision=1,
                editable=True),
            ensure_ascii=False)
        self.assertGreater(len(payload.encode('utf-8')), 64 * 1024)
        update, error = decode_catalog_payload(payload)
        self.assertIsNone(error)
        self.assertEqual(len(update['rooms']), 256)

    def test_deep_json_and_invalid_unicode_fail_closed(self):
        for payload in ('[' * 1_100 + '0' + ']' * 1_100, '\ud800'):
            with self.subTest(kind='unicode' if payload == '\ud800' else 'deep'):
                update, error = decode_catalog_payload(payload)
                self.assertIsNone(update)
                self.assertTrue(error)


if __name__ == '__main__':
    unittest.main()
