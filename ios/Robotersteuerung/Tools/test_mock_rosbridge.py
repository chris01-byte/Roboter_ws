#!/usr/bin/env python3
"""Offline contract checks for the semantic rosbridge simulator mock."""

import re
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mock_rosbridge as mock


class SemanticMockTests(unittest.TestCase):
    def setUp(self):
        self.state = mock.RobotState()

    def test_mock_map_fingerprint_is_stable_and_content_sensitive(self):
        initial = self.state.map_summary()['fingerprint']
        self.assertEqual(
            initial,
            '80c5498f9a8241fee01141dc04189ad814451d284a2f9c8aeaf597e94af9fa55',
        )
        self.state.advance_map()
        self.assertNotEqual(self.state.map_summary()['fingerprint'], initial)

    def test_save_creates_exact_persisted_semantic_reference(self):
        initial = self.state.semantic_status()
        self.assertFalse(initial['ok'])
        self.assertIsNone(initial['semantic_map']['map_ref'])
        response = self.state.save_map_for_rooms({
            'command': 'save',
            'name': 'wohnung',
            'request_id': 'ios-map-1',
        })
        self.assertTrue(response['ok'])
        self.assertEqual(response['event'], 'save_result')
        saved = self.state.last_saved_map
        semantic_reference = self.state.semantic_map['map_ref']
        self.assertEqual(saved['fingerprint'], semantic_reference['fingerprint'])
        self.assertEqual(saved['name'], semantic_reference['name'])
        self.assertEqual(saved['version'], semantic_reference['version'])
        self.assertRegex(
            saved['version'],
            re.compile(
                r'^[0-9]{8}T[0-9]{12}Z-[0-9a-f]{12}(?:-[0-9]{2})?$'
            ),
        )
        self.assertTrue(saved['version'].endswith(saved['fingerprint'][:12]))
        self.assertTrue(self.state.semantic_map['editable'])

    def test_save_request_is_idempotent_but_reuse_conflicts(self):
        command = {
            'command': 'save',
            'name': 'wohnung',
            'request_id': 'ios-map-1',
        }
        first = self.state.save_map_for_rooms(command)
        cached_signature, cached_outcome = self.state.map_request_cache['ios-map-1']
        self.assertRegex(cached_signature, r'^[0-9a-f]{64}$')
        self.assertEqual(set(cached_outcome), {'event', 'ok', 'message'})
        saved_fingerprint = first['storage']['last_saved']['fingerprint']
        self.state.advance_map()
        second = self.state.save_map_for_rooms(dict(command))
        current_fingerprint = self.state.map_summary()['fingerprint']
        self.assertNotEqual(current_fingerprint, saved_fingerprint)
        self.assertEqual(second['event'], first['event'])
        self.assertEqual(second['ok'], first['ok'])
        self.assertEqual(second['message'], first['message'])
        self.assertEqual(second['map']['summary']['fingerprint'], current_fingerprint)
        self.assertEqual(
            second['storage']['last_saved']['fingerprint'],
            saved_fingerprint,
        )
        self.assertNotEqual(second, first)
        conflict = self.state.save_map_for_rooms({
            'command': 'save',
            'name': 'falsch',
            'request_id': 'ios-map-1',
        })
        self.assertFalse(conflict['ok'])

    def test_room_upsert_silent_revision_conflict_and_delete(self):
        self.state.save_map_for_rooms({
            'command': 'save',
            'name': 'wohnung',
            'request_id': 'ios-map-1',
        })
        fingerprint = self.state.semantic_map['map_ref']['fingerprint']
        room = {
            'id': 'room-1',
            'name': 'Wohnzimmer',
            'color': '#4FB3A5',
            'polygon': [
                {'x': -2.0, 'y': -1.0},
                {'x': 0.0, 'y': -1.0},
                {'x': 0.0, 'y': 1.0},
            ],
            'navigation_goal': {'x': -1.0, 'y': -0.5, 'yaw': 0.0},
        }
        upsert_command = {
            'command': 'upsert_room',
            'request_id': 'ios-room-1',
            'map_fingerprint': fingerprint,
            'base_revision': 0,
            'room': room,
        }
        upsert = self.state.apply_semantic_command(upsert_command)
        cached_signature, cached_outcome = self.state.semantic_request_cache['ios-room-1']
        self.assertRegex(cached_signature, r'^[0-9a-f]{64}$')
        self.assertEqual(set(cached_outcome), {'event', 'ok', 'message'})
        self.assertTrue(upsert['ok'])
        self.assertEqual(upsert['event'], 'room_created')
        self.assertEqual(self.state.semantic_map['revision'], 1)
        self.assertEqual(self.state.semantic_map['rooms'], [room])
        self.assertEqual(self.state.status['rooms'], ['Wohnzimmer'])

        # The HTTP endpoint /semantic-bump-silent performs the same state
        # transition without a status push. The client still believes the
        # acknowledged revision is 1 while the mock has advanced to 2.
        self.assertEqual(self.state.bump_semantic_revision(), 2)
        replay = self.state.apply_semantic_command(dict(upsert_command))
        self.assertEqual(replay['event'], upsert['event'])
        self.assertEqual(replay['ok'], upsert['ok'])
        self.assertEqual(replay['message'], upsert['message'])
        self.assertEqual(replay['semantic_map']['revision'], 2)
        self.assertNotEqual(replay, upsert)

        changed_payload = dict(upsert_command)
        changed_payload['room'] = dict(room, name='Anderer Name')
        conflict = self.state.apply_semantic_command(changed_payload)
        self.assertFalse(conflict['ok'])
        self.assertEqual(conflict['event'], 'request_id_conflict')
        self.assertEqual(conflict['semantic_map']['revision'], 2)

        stale = self.state.apply_semantic_command({
            'command': 'delete_room',
            'request_id': 'ios-room-stale',
            'map_fingerprint': fingerprint,
            'base_revision': 1,
            'room_id': 'room-1',
        })
        self.assertFalse(stale['ok'])
        self.assertEqual(stale['event'], 'revision_conflict')

        deleted = self.state.apply_semantic_command({
            'command': 'delete_room',
            'request_id': 'ios-room-2',
            'map_fingerprint': fingerprint,
            'base_revision': 2,
            'room_id': 'room-1',
        })
        self.assertTrue(deleted['ok'])
        self.assertEqual(deleted['event'], 'room_deleted')
        self.assertEqual(self.state.semantic_map['revision'], 3)
        self.assertEqual(self.state.semantic_map['rooms'], [])
        self.assertEqual(
            self.state.status['rooms'], list(self.state.DEFAULT_ROOMS))

        invalid = self.state.apply_semantic_command({
            'command': 'delete_room',
            'request_id': '../unsafe',
            'map_fingerprint': fingerprint,
            'base_revision': 3,
            'room_id': 'room-1',
        })
        self.assertFalse(invalid['ok'])
        self.assertEqual(invalid['event'], 'validation_error')

    def test_polygon_complexity_matches_backend_contract(self):
        self.state.save_map_for_rooms({
            'command': 'save',
            'name': 'wohnung',
            'request_id': 'ios-map-complexity',
        })
        fingerprint = self.state.semantic_map['map_ref']['fingerprint']

        def room(room_id, points):
            return {
                'id': room_id,
                'name': room_id,
                'color': '#4FB3A5',
                'polygon': [
                    {
                        'x': -0.5 + 0.4 * math.cos(2 * math.pi * index / points),
                        'y': -0.2 + 0.4 * math.sin(2 * math.pi * index / points),
                    }
                    for index in range(points)
                ],
                'navigation_goal': {'x': -0.5, 'y': -0.2, 'yaw': 0.0},
            }

        too_complex = self.state.apply_semantic_command({
            'command': 'upsert_room',
            'request_id': 'ios-room-65-points',
            'map_fingerprint': fingerprint,
            'base_revision': 0,
            'room': room('room-65-points', 65),
        })
        self.assertFalse(too_complex['ok'])

        self.state.semantic_map['rooms'] = [
            room(f'room-existing-{index}', 17) for index in range(240)
        ]
        total_too_complex = self.state.apply_semantic_command({
            'command': 'upsert_room',
            'request_id': 'ios-room-total-complexity',
            'map_fingerprint': fingerprint,
            'base_revision': 0,
            'room': room('room-new', 17),
        })
        self.assertFalse(total_too_complex['ok'])
        self.assertIn('4096', total_too_complex['message'])


if __name__ == '__main__':
    unittest.main()
