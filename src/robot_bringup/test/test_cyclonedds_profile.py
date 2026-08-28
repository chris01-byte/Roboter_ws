from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROFILE = PACKAGE_ROOT / 'config' / 'cyclonedds_profile.xml'


class CycloneDDSProfileTests(unittest.TestCase):
    def test_auto_participant_search_covers_full_robot_stack(self):
        root = ET.parse(PROFILE).getroot()
        discovery = next(
            element for element in root.iter()
            if element.tag.rsplit('}', 1)[-1] == 'Discovery')
        values = {
            element.tag.rsplit('}', 1)[-1]: (element.text or '').strip()
            for element in discovery
        }

        self.assertEqual(values.get('ParticipantIndex'), 'auto')
        self.assertGreaterEqual(
            int(values['MaxAutoParticipantIndex']),
            64,
            'Der Nav2-/AMCL-Gesamtstart braucht deutlich mehr als zehn '
            'CycloneDDS-Teilnehmer.',
        )


if __name__ == '__main__':
    unittest.main()
