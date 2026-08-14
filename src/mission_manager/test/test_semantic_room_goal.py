import json
import math
import unittest

from mission_manager.semantic_room_goal import (
    decode_semantic_map_status,
    point_in_polygon,
    resolve_room_goal,
    semantic_snapshot_is_fresh,
)


def valid_status():
    return {
        'schema_version': 1,
        'ok': True,
        'semantic_map': {
            'map_ref': {
                'fingerprint': 'a' * 64,
                'frame_id': 'map',
            },
            'revision': 7,
            'rooms': [{
                'id': 'room-wohnzimmer',
                'name': 'Wohnzimmer',
                'polygon': [
                    {'x': 0.0, 'y': 0.0},
                    {'x': 4.0, 'y': 0.0},
                    {'x': 4.0, 'y': 3.0},
                    {'x': 0.0, 'y': 3.0},
                ],
                'navigation_goal': {'x': 2.0, 'y': 1.5, 'yaw': 1.57},
            }],
            'editable': True,
        },
    }


class SemanticRoomGoalTests(unittest.TestCase):
    def decode(self, payload=None, **kwargs):
        return decode_semantic_map_status(json.dumps(payload or valid_status()), **kwargs)

    def test_valid_snapshot_resolves_name_and_map_binding(self):
        snapshot, error = self.decode()
        self.assertIsNone(error)
        goal, error = resolve_room_goal(snapshot, room_name=' wohnzimmer ')
        self.assertIsNone(error)
        self.assertEqual(goal.room_id, 'room-wohnzimmer')
        self.assertEqual(goal.map_fingerprint, 'a' * 64)
        self.assertEqual(goal.map_revision, 7)
        self.assertEqual(goal.frame_id, 'map')
        self.assertEqual(goal.as_dict()['pose'], {'x': 2.0, 'y': 1.5, 'yaw': 1.57})

    def test_room_id_and_name_must_describe_same_room(self):
        payload = valid_status()
        payload['semantic_map']['rooms'].append({
            'id': 'room-kueche',
            'name': 'Kueche',
            'polygon': [[5, 0], [8, 0], [8, 3], [5, 3]],
            'navigation_goal': {'x': 6, 'y': 1, 'yaw': 0},
        })
        snapshot, error = self.decode(payload)
        self.assertIsNone(error)
        goal, error = resolve_room_goal(
            snapshot, room_name='Wohnzimmer', room_id='room-kueche')
        self.assertIsNone(goal)
        self.assertIn('unbekannt', error)

    def test_missing_goal_keeps_map_readable_but_room_fails_closed(self):
        payload = valid_status()
        del payload['semantic_map']['rooms'][0]['navigation_goal']
        snapshot, error = self.decode(payload)
        self.assertIsNone(error)
        goal, error = resolve_room_goal(snapshot, room_name='Wohnzimmer')
        self.assertIsNone(goal)
        self.assertIn('noch kein Navigationsziel', error)

    def test_rejects_not_ok_wrong_fingerprint_frame_and_revision(self):
        mutations = [
            (lambda p: p.update(ok=False), {}, 'ok != true'),
            (lambda p: p['semantic_map']['map_ref'].update(fingerprint='not-a-hash'),
             {}, '64 kleinen Hexzeichen'),
            (lambda p: None, {'expected_fingerprint': 'b' * 64}, 'Fingerprint'),
            (lambda p: p['semantic_map']['map_ref'].update(frame_id='odom'), {}, 'Frame'),
            (lambda p: p['semantic_map'].update(revision=True), {}, 'Ganzzahl'),
            (lambda p: p['semantic_map'].update(revision=-1), {}, 'Ganzzahl'),
        ]
        for mutate, kwargs, expected in mutations:
            with self.subTest(expected=expected):
                payload = valid_status()
                mutate(payload)
                snapshot, error = self.decode(payload, **kwargs)
                self.assertIsNone(snapshot)
                self.assertIn(expected, error)

    def test_rejects_wrong_schema_or_noneditable_snapshot(self):
        payload = valid_status()
        payload['schema_version'] = 2
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('schema_version', error)

        payload = valid_status()
        payload['semantic_map']['editable'] = False
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('nicht editierbar', error)

    def test_rejects_non_finite_goal_and_goal_outside_room(self):
        for value in (math.nan, math.inf, True, '1.0'):
            with self.subTest(value=value):
                payload = valid_status()
                payload['semantic_map']['rooms'][0]['navigation_goal']['x'] = value
                snapshot, error = self.decode(payload)
                self.assertIsNone(snapshot)
                self.assertIn('endliche Zielpose', error)
        payload = valid_status()
        payload['semantic_map']['rooms'][0]['navigation_goal']['x'] = 10.0
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('nicht strikt', error)

        payload = valid_status()
        payload['semantic_map']['rooms'][0]['navigation_goal']['x'] = 0.0
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('nicht strikt', error)

    def test_rejects_duplicate_identity_and_degenerate_polygon(self):
        payload = valid_status()
        duplicate = dict(payload['semantic_map']['rooms'][0])
        duplicate['id'] = 'room-wohnzimmer'
        duplicate['name'] = 'Anderer Name'
        payload['semantic_map']['rooms'].append(duplicate)
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('Doppelte Raum-ID', error)

        payload = valid_status()
        duplicate = dict(payload['semantic_map']['rooms'][0])
        duplicate['id'] = 'room-zwei'
        duplicate['name'] = 'WOHNZIMMER'
        payload['semantic_map']['rooms'].append(duplicate)
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('Doppelter Raumname', error)

        payload = valid_status()
        payload['semantic_map']['rooms'][0]['polygon'] = [[0, 0], [1, 1], [2, 2]]
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('ohne nutzbare Flaeche', error)

    def test_polygon_boundary_is_accepted(self):
        polygon = ((0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0))
        self.assertTrue(point_in_polygon((0.0, 1.0), polygon))
        self.assertTrue(point_in_polygon((1.0, 1.0), polygon))
        self.assertFalse(point_in_polygon((3.0, 1.0), polygon))

    def test_legacy_two_number_polygon_points_remain_readable(self):
        payload = valid_status()
        payload['semantic_map']['rooms'][0]['polygon'] = [
            [0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0],
        ]
        snapshot, error = self.decode(payload)
        self.assertIsNone(error)
        self.assertEqual(snapshot.rooms[0].polygon[2], (4.0, 3.0))

    def test_deep_json_and_invalid_unicode_fail_closed(self):
        for payload in ('[' * 1_100 + '0' + ']' * 1_100, '\ud800'):
            with self.subTest(kind='unicode' if payload == '\ud800' else 'deep'):
                snapshot, error = decode_semantic_map_status(payload)
                self.assertIsNone(snapshot)
                self.assertTrue(error)

    def test_snapshot_freshness_uses_bounded_monotonic_age(self):
        self.assertTrue(semantic_snapshot_is_fresh(10.0, 15.9, 6.0))
        self.assertTrue(semantic_snapshot_is_fresh(10.0, 16.0, 6.0))
        for values in (
                (10.0, 16.001, 6.0),
                (10.0, 9.0, 6.0),
                (None, 11.0, 6.0),
                (10.0, math.nan, 6.0),
                (10.0, 11.0, 0.0)):
            with self.subTest(values=values):
                self.assertFalse(semantic_snapshot_is_fresh(*values))

    def test_accepts_backend_maximum_total_polygon_complexity(self):
        polygon = [
            {
                'x': 10.0 + 2.0 * math.cos(2.0 * math.pi * index / 16.0),
                'y': 10.0 + 2.0 * math.sin(2.0 * math.pi * index / 16.0),
            }
            for index in range(16)
        ]
        payload = valid_status()
        payload['semantic_map']['rooms'] = [
            {
                'id': f'room-{index}',
                'name': f'{index:03d}-' + ('R' * 76),
                'polygon': polygon,
                'navigation_goal': {'x': 10.0, 'y': 10.0, 'yaw': 0.0},
            }
            for index in range(256)
        ]
        text = json.dumps(payload, ensure_ascii=False)
        snapshot, error = decode_semantic_map_status(text)
        self.assertIsNone(error)
        self.assertEqual(len(snapshot.rooms), 256)
        self.assertEqual(sum(len(room.polygon) for room in snapshot.rooms), 4096)

    def test_polygon_complexity_limits_fail_before_quadratic_work(self):
        payload = valid_status()
        payload['semantic_map']['rooms'][0]['polygon'] = [
            {
                'x': 10.0 + 2.0 * math.cos(2.0 * math.pi * index / 65.0),
                'y': 10.0 + 2.0 * math.sin(2.0 * math.pi * index / 65.0),
            }
            for index in range(65)
        ]
        payload['semantic_map']['rooms'][0]['navigation_goal'] = {
            'x': 10.0, 'y': 10.0, 'yaw': 0.0,
        }
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('3 bis 64', error)

        polygon = [
            {
                'x': 10.0 + 2.0 * math.cos(2.0 * math.pi * index / 17.0),
                'y': 10.0 + 2.0 * math.sin(2.0 * math.pi * index / 17.0),
            }
            for index in range(17)
        ]
        payload = valid_status()
        payload['semantic_map']['rooms'] = [
            {
                'id': f'room-{index}',
                'name': f'Raum {index}',
                'polygon': polygon,
                'navigation_goal': {'x': 10.0, 'y': 10.0, 'yaw': 0.0},
            }
            for index in range(242)
        ]
        snapshot, error = self.decode(payload)
        self.assertIsNone(snapshot)
        self.assertIn('4096 Polygonpunkte', error)


if __name__ == '__main__':
    unittest.main()
