import tempfile
import unittest
from pathlib import Path

from karte_fuer_nav2_pruefen import MapCheckError, check_map


def write_map(directory: Path, free_thresh: float, pixels: bytes) -> Path:
    width = 100
    height = len(pixels) // width
    (directory / 'map.pgm').write_bytes(
        f'P5\n# test\n{width} {height}\n255\n'.encode() + pixels)
    yaml_path = directory / 'map.yaml'
    yaml_path.write_text(
        'image: map.pgm\n'
        'mode: trinary\n'
        'resolution: 0.03\n'
        'origin: [0, 0, 0]\n'
        'negate: 0\n'
        'occupied_thresh: 0.65\n'
        f'free_thresh: {free_thresh}\n',
        encoding='utf-8')
    return yaml_path


class Nav2MapCheckTest(unittest.TestCase):
    def test_rejects_unknown_cells_that_threshold_turns_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_map(
                Path(tmp), 0.25,
                bytes([205] * 2000 + [254] * 7000 + [0] * 1000))
            with self.assertRaisesRegex(MapCheckError, 'KARTENVERLUST'):
                check_map(path)

    def test_preserves_unknown_cells_with_corrected_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_map(
                Path(tmp), 0.196,
                bytes([205] * 2000 + [254] * 7000 + [0] * 1000))
            stats = check_map(path)
            self.assertEqual(stats.unknown, 2000)
            self.assertEqual(stats.free, 7000)
            self.assertEqual(stats.occupied, 1000)
            self.assertAlmostEqual(stats.free_area_m2, 6.3)

    def test_binary_map_without_unknown_region_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_map(
                Path(tmp), 0.25, bytes([254] * 9000 + [0] * 1000))
            stats = check_map(path)
            self.assertEqual(stats.unknown, 0)
            self.assertEqual(stats.source_unknown_marker, 0)

    def test_rejects_non_trinary_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_map(Path(tmp), 0.196, bytes([254] * 10000))
            path.write_text(
                path.read_text(encoding='utf-8').replace(
                    'mode: trinary', 'mode: scale'),
                encoding='utf-8')
            with self.assertRaisesRegex(MapCheckError, 'trinary'):
                check_map(path)


if __name__ == '__main__':
    unittest.main()
