from types import SimpleNamespace
import unittest

import cv2
import numpy as np

from robot_bringup.oak_rectifier_node import (
    build_rectification_maps,
    input_is_stalled,
    rectification_key,
)


def _camera_info(width=8, height=6):
    return SimpleNamespace(
        width=width,
        height=height,
        distortion_model='plumb_bob',
        d=[0.0, 0.0, 0.0, 0.0, 0.0],
        k=[4.0, 0.0, 3.5, 0.0, 4.0, 2.5, 0.0, 0.0, 1.0],
        r=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        p=[4.0, 0.0, 3.5, 0.0, 0.0, 4.0, 2.5, 0.0,
           0.0, 0.0, 1.0, 0.0],
    )


class OakRectifierTests(unittest.TestCase):
    def test_zero_distortion_builds_identity_remap(self):
        info = _camera_info()

        key, map_x, map_y = build_rectification_maps(info, 8, 6)

        self.assertEqual(key, rectification_key(info, 8, 6))
        self.assertEqual(map_x.shape, (6, 8, 2))
        self.assertEqual(map_y.shape, (6, 8))

        image = np.arange(48, dtype=np.uint8).reshape(6, 8)
        rectified = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)
        np.testing.assert_array_equal(rectified, image)

    def test_resolution_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'passt nicht'):
            rectification_key(_camera_info(width=640, height=360), 1280, 720)

    def test_invalid_focal_length_is_rejected(self):
        info = _camera_info()
        info.k[0] = 0.0

        with self.assertRaisesRegex(ValueError, 'Brennweiten'):
            rectification_key(info, 8, 6)

    def test_subscription_stall_watchdog_respects_startup_and_timeout(self):
        common = dict(
            started_s=100.0,
            startup_grace_s=10.0,
            timeout_s=3.0,
        )
        self.assertFalse(input_is_stalled(
            now_s=105.0, last_received_s=0.0, **common))
        self.assertTrue(input_is_stalled(
            now_s=111.0, last_received_s=0.0, **common))
        self.assertFalse(input_is_stalled(
            now_s=111.0, last_received_s=109.0, **common))
        self.assertTrue(input_is_stalled(
            now_s=113.1, last_received_s=110.0, **common))


if __name__ == '__main__':
    unittest.main()
