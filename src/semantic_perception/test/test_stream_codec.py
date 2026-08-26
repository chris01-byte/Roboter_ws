from types import SimpleNamespace
import unittest

import numpy as np

from semantic_perception.stream_codec import (
    StreamCodecError,
    decode_depth_png,
    decode_rgb_jpeg,
    encode_depth_png,
    encode_rgb_jpeg,
    pair_is_publishable,
    pair_rejection_reason,
    select_freshest_pair,
    stamp_seconds,
)
from semantic_perception.semantic_stream_relay_node import input_is_stalled


class StreamCodecTests(unittest.TestCase):
    def test_depth_png_roundtrip_is_lossless(self):
        depth = np.arange(48, dtype=np.uint16).reshape(6, 8) * 37

        decoded = decode_depth_png(encode_depth_png(depth, compression=1))

        np.testing.assert_array_equal(decoded, depth)

    def test_rgb_jpeg_keeps_shape_and_reasonable_error(self):
        image = np.zeros((32, 48, 3), dtype=np.uint8)
        image[:, :24] = (20, 80, 220)
        image[:, 24:] = (200, 160, 30)

        decoded = decode_rgb_jpeg(encode_rgb_jpeg(image, quality=90))

        self.assertEqual(decoded.shape, image.shape)
        self.assertEqual(decoded.dtype, np.uint8)
        self.assertLess(float(np.abs(decoded.astype(int) - image).mean()), 8.0)

    def test_depth_codec_rejects_non_16_bit_input(self):
        with self.assertRaises(StreamCodecError):
            encode_depth_png(np.zeros((4, 4), dtype=np.uint8))
        with self.assertRaises(StreamCodecError):
            decode_depth_png(b'not a png')

    def test_pair_contract_rejects_stale_or_skewed_frames(self):
        good = dict(
            now_s=10.0,
            rgb_received_s=9.8,
            depth_received_s=9.9,
            rgb_stamp_s=100.00,
            depth_stamp_s=100.05,
            max_age_s=1.0,
            max_skew_s=0.20,
        )
        self.assertTrue(pair_is_publishable(**good))

        stale = dict(good, rgb_received_s=8.0)
        skewed = dict(good, depth_stamp_s=100.50)
        self.assertFalse(pair_is_publishable(**stale))
        self.assertFalse(pair_is_publishable(**skewed))
        self.assertEqual(pair_rejection_reason(**stale), 'stale_rgb')
        self.assertEqual(pair_rejection_reason(**skewed), 'timestamp_skew')

    def test_stamp_conversion(self):
        stamp = SimpleNamespace(sec=12, nanosec=250_000_000)
        self.assertEqual(stamp_seconds(stamp), 12.25)

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

    def test_freshest_pair_matches_delayed_depth_to_buffered_rgb(self):
        rgb = [
            ('rgb-old', 9.1, 100.0),
            ('rgb-match', 9.4, 100.5),
            ('rgb-new', 9.9, 101.0),
        ]
        depth = [('depth-match', 9.9, 100.5)]

        pair = select_freshest_pair(
            rgb, depth, now_s=10.0, max_age_s=1.0, max_skew_s=0.05)

        self.assertEqual(pair[0][0], 'rgb-match')
        self.assertEqual(pair[1][0], 'depth-match')

    def test_pair_selector_rejects_stale_and_already_published_rgb(self):
        rgb = [('rgb', 9.5, 100.0)]
        depth = [('depth', 9.5, 100.0)]

        stale = select_freshest_pair(
            rgb, depth, now_s=11.0, max_age_s=1.0, max_skew_s=0.05)
        duplicate = select_freshest_pair(
            rgb, depth, now_s=10.0, max_age_s=1.0, max_skew_s=0.05,
            last_rgb_stamp_s=100.0)

        self.assertIsNone(stale)
        self.assertIsNone(duplicate)


if __name__ == '__main__':
    unittest.main()
