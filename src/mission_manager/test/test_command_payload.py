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

    def test_rejects_deep_oversized_and_invalid_unicode_payloads(self):
        payloads = (
            '{"type":"go_to_room","junk":' + '[' * 2_000 +
            '0' + ']' * 2_000 + '}',
            '{"type":"go_to_room","junk":"' + ('x' * (65 * 1024)) + '"}',
            '\ud800',
        )
        for payload in payloads:
            with self.subTest(size=len(payload)):
                command, error = decode_command_payload(payload)
                self.assertIsNone(command)
                self.assertTrue(error)


if __name__ == '__main__':
    unittest.main()
