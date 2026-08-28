import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name('oak_static_acceptance.py')
SPEC = importlib.util.spec_from_file_location('oak_static_acceptance', MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AcceptanceEvaluationTests(unittest.TestCase):
    def test_stable_confident_3d_samples_pass(self):
        samples = [
            {
                'confidence': 0.7,
                'camera_point': [0.1, 0.0, 1.2],
                'base_point': [1.1 + offset, 0.1, 0.8],
            }
            for offset in (-0.01, 0.0, 0.01)
        ]

        result = MODULE.evaluate_samples(
            samples, minimum_samples=3, minimum_confidence=0.35,
            maximum_spread_m=0.20)

        self.assertTrue(result['passed'])
        self.assertEqual(result['valid_3d_count'], 3)

    def test_missing_or_unstable_samples_fail(self):
        samples = [
            {
                'confidence': 0.2,
                'camera_point': [0.0, 0.0, 1.0],
                'base_point': [0.0, 0.0, 0.0],
            },
            {
                'confidence': 0.8,
                'camera_point': [0.0, 0.0, 1.0],
                'base_point': [1.0, 0.0, 0.0],
            },
        ]

        result = MODULE.evaluate_samples(
            samples, minimum_samples=3, minimum_confidence=0.35,
            maximum_spread_m=0.20)

        self.assertFalse(result['passed'])
        self.assertGreaterEqual(len(result['reasons']), 2)

    def test_stream_requires_fresh_progressing_expected_profile(self):
        statuses = [
            {
                'schema_version': 1,
                'ready': True,
                'profile_name': 'standard',
                'pairs_published': 10,
                'last_rgb_shape': [360, 640, 3],
                'last_depth_shape': [360, 640],
            },
            {
                'schema_version': 1,
                'ready': True,
                'profile_name': 'standard',
                'pairs_published': 12,
                'last_rgb_shape': [360, 640, 3],
                'last_depth_shape': [360, 640],
            },
        ]
        result = MODULE.evaluate_stream_statuses(
            statuses, expected_profile='standard', expected_width=640,
            expected_height=360, last_status_age_s=0.2)
        self.assertTrue(result['passed'])

        rejected = MODULE.evaluate_stream_statuses(
            statuses, expected_profile='detail_hd', expected_width=1280,
            expected_height=720, last_status_age_s=2.1)
        self.assertFalse(rejected['passed'])
        self.assertGreaterEqual(len(rejected['reasons']), 3)


if __name__ == '__main__':
    unittest.main()
