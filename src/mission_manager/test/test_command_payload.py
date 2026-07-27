import unittest

from mission_manager.command_payload import decode_command_payload


class CommandPayloadTests(unittest.TestCase):
    def test_decodes_json_object(self):
        command, error = decode_command_payload(
            '{"type":"go_to_room","room":"Kueche"}'
        )
        self.assertIsNone(error)
        self.assertEqual(command['type'], 'go_to_room')

    def test_rejects_valid_non_object_json(self):
        for payload in ('[]', 'null', '42', '"cancel"'):
            with self.subTest(payload=payload):
                command, error = decode_command_payload(payload)
                self.assertIsNone(command)
                self.assertEqual(error, 'JSON-Auftrag muss ein Objekt sein')

    def test_rejects_malformed_json(self):
        command, error = decode_command_payload('{')
        self.assertIsNone(command)
        self.assertTrue(error.startswith('Ungueltiges JSON:'))


if __name__ == '__main__':
    unittest.main()
