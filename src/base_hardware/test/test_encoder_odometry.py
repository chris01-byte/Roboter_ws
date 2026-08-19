#!/usr/bin/env python3
"""Offline-Regressionstests fuer die absolute ESS-RS-Encoderodometrie.

Die Tests importieren weder ROS noch pymodbus. Sie bilden insbesondere das
reale Fehlerbild nach: Bewegung waehrend Bremsphasen muss aus den absoluten
Zaehlern kommen und darf nicht je Stop/Start verloren gehen.
"""

import math
import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from base_hardware.encoder_odometry import (  # noqa: E402
    UINT32_MODULUS,
    EncoderOdometry,
    decode_i16,
    decode_position_words,
    modular_delta_u32,
    u32_to_i32,
)


def u32(value):
    """Vorzeichenbehafteten Testwert als umlaufenden uint32 darstellen."""
    return value % UINT32_MODULUS


def odometry(**overrides):
    """Gut lesbare Testgeometrie: ein Count entspricht exakt einem Zentimeter."""
    values = {
        'wheel_radius_m': 1.0 / (2.0 * math.pi),  # Umfang genau 1 m
        'wheel_separation_m': 0.5,
        'gear_ratio': 1.0,
        'counts_per_motor_revolution': 100.0,
        'max_motor_rpm': 6000.0,
        'max_delta_factor': 1.5,
        'quantization_margin_counts': 8,
        'max_recovery_gap_s': 5.0,
    }
    values.update(overrides)
    return EncoderOdometry(**values)


class RegisterDecoderTests(unittest.TestCase):

    def test_position_words_high_word_first(self):
        self.assertEqual(
            decode_position_words((0x1234, 0xABCD), high_word_first=True),
            0x1234ABCD,
        )
        self.assertEqual(
            decode_position_words((0xFFFF, 0xFFFF), high_word_first=True),
            0xFFFFFFFF,
        )

    def test_position_words_low_word_first(self):
        self.assertEqual(
            decode_position_words((0xABCD, 0x1234), high_word_first=False),
            0x1234ABCD,
        )
        self.assertEqual(
            decode_position_words((0x0001, 0x0000), high_word_first=False),
            1,
        )

    def test_position_decoder_rejects_malformed_register_response(self):
        for words in ((), (1,), (1, 2, 3)):
            with self.subTest(words=words):
                with self.assertRaises(ValueError):
                    decode_position_words(words, high_word_first=True)

        for words, error in (
            ((-1, 0), ValueError),
            ((0x10000, 0), ValueError),
            ((True, 0), TypeError),
            ((1.5, 0), TypeError),
        ):
            with self.subTest(words=words):
                with self.assertRaises(error):
                    decode_position_words(words, high_word_first=True)

    def test_u32_to_i32_boundaries(self):
        cases = {
            0x00000000: 0,
            0x00000001: 1,
            0x7FFFFFFF: 2147483647,
            0x80000000: -2147483648,
            0xFFFFFF9C: -100,
            0xFFFFFFFF: -1,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=hex(raw)):
                self.assertEqual(u32_to_i32(raw), expected)

    def test_signed_speed_decoder_boundaries(self):
        cases = {
            0x0000: 0,
            0x0001: 1,
            0x7FFF: 32767,
            0x8000: -32768,
            0xFF9C: -100,
            0xFFFF: -1,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=hex(raw)):
                self.assertEqual(decode_i16(raw), expected)


class ModularDeltaTests(unittest.TestCase):

    def test_wraparound_in_both_directions(self):
        self.assertEqual(modular_delta_u32(0xFFFFFFFF, 0x00000000), 1)
        self.assertEqual(modular_delta_u32(0x00000000, 0xFFFFFFFF), -1)
        self.assertEqual(modular_delta_u32(0x7FFFFFFA, 0x80000005), 11)
        self.assertEqual(modular_delta_u32(0x80000005, 0x7FFFFFFA), -11)

    def test_exact_half_range_is_rejected_as_ambiguous(self):
        with self.assertRaisesRegex(ValueError, 'richtungsmehrdeutig'):
            modular_delta_u32(0, 0x80000000)
        with self.assertRaisesRegex(ValueError, 'richtungsmehrdeutig'):
            modular_delta_u32(0x80000000, 0)

    def test_bounded_deltas_survive_wrap_for_many_start_values(self):
        starts = (0, 1, 0x7FFFFFF0, 0xFFFFFFF0, 0xFFFFFFFF)
        for start in starts:
            for expected in (-1000, -11, -1, 0, 1, 11, 1000):
                current = u32(start + expected)
                with self.subTest(start=hex(start), expected=expected):
                    self.assertEqual(
                        modular_delta_u32(start, current), expected)


class EncoderOdometryTests(unittest.TestCase):

    def assert_pose(self, tracker, x, y, yaw, places=12):
        self.assertAlmostEqual(tracker.x_m, x, places=places)
        self.assertAlmostEqual(tracker.y_m, y, places=places)
        self.assertAlmostEqual(tracker.yaw_rad, yaw, places=places)

    def test_first_sample_only_initializes_baseline(self):
        tracker = odometry()
        result = tracker.update(123, 456, 10.0)

        self.assertFalse(result.accepted)
        self.assertTrue(result.initialized)
        self.assertEqual(result.reason, 'baseline_initialisiert')
        self.assertTrue(tracker.initialized)
        self.assertEqual(tracker.accepted_update_count, 0)
        self.assertEqual(tracker.rejected_update_count, 0)
        self.assert_pose(tracker, 0.0, 0.0, 0.0)

    def test_reset_and_node_restart_do_not_create_phantom_motion(self):
        tracker = odometry()
        tracker.update(100, 100, 0.0)
        tracker.update(110, 110, 1.0)
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

        tracker.reset_baseline()
        baseline = tracker.update(900000, 800000, 2.0)
        self.assertFalse(baseline.accepted)
        self.assertEqual(baseline.reason, 'baseline_initialisiert')
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

        moved = tracker.update(900010, 800010, 3.0)
        self.assertTrue(moved.accepted)
        self.assert_pose(tracker, 0.2, 0.0, 0.0)

    def test_straight_motion_and_velocity(self):
        tracker = odometry()
        tracker.update(100, 200, 3.0)
        result = tracker.update(110, 210, 4.0)

        self.assertTrue(result.accepted)
        self.assertEqual(result.left_delta_counts, 10)
        self.assertEqual(result.right_delta_counts, 10)
        self.assertAlmostEqual(result.left_distance_m, 0.1)
        self.assertAlmostEqual(result.right_distance_m, 0.1)
        self.assertAlmostEqual(result.distance_m, 0.1)
        self.assertAlmostEqual(result.heading_rad, 0.0)
        self.assertAlmostEqual(result.linear_velocity_mps, 0.1)
        self.assertAlmostEqual(result.angular_velocity_radps, 0.0)
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

    def test_reverse_motion(self):
        tracker = odometry()
        tracker.update(100, 200, 0.0)
        result = tracker.update(90, 190, 1.0)

        self.assertTrue(result.accepted)
        self.assertEqual(result.left_delta_counts, -10)
        self.assertEqual(result.right_delta_counts, -10)
        self.assert_pose(tracker, -0.1, 0.0, 0.0)

    def test_pure_rotation(self):
        tracker = odometry()
        tracker.update(100, 100, 0.0)
        result = tracker.update(75, 125, 1.0)

        self.assertTrue(result.accepted)
        self.assertAlmostEqual(result.left_distance_m, -0.25)
        self.assertAlmostEqual(result.right_distance_m, 0.25)
        self.assertAlmostEqual(result.distance_m, 0.0)
        self.assertAlmostEqual(result.heading_rad, 1.0)
        self.assertAlmostEqual(result.angular_velocity_radps, 1.0)
        self.assert_pose(tracker, 0.0, 0.0, 1.0)

    def test_arc_uses_exact_differential_drive_integration(self):
        tracker = odometry()
        tracker.update(0, 0, 0.0)
        result = tracker.update(10, 20, 1.0)

        # dl=0.1, dr=0.2 -> s=0.15, dtheta=0.2, turn radius=0.75.
        expected_x = 0.75 * math.sin(0.2)
        expected_y = 0.75 * (1.0 - math.cos(0.2))
        self.assertTrue(result.accepted)
        self.assertAlmostEqual(result.distance_m, 0.15)
        self.assertAlmostEqual(result.heading_rad, 0.2)
        self.assert_pose(tracker, expected_x, expected_y, 0.2)

    def test_existing_yaw_rotates_body_arc_into_world_frame(self):
        tracker = odometry()
        tracker.set_pose(1.0, 2.0, math.pi / 2.0)
        tracker.update(0, 0, 0.0)
        tracker.update(10, 20, 1.0)

        dx_body = 0.75 * math.sin(0.2)
        dy_body = 0.75 * (1.0 - math.cos(0.2))
        self.assert_pose(
            tracker,
            1.0 - dy_body,
            2.0 + dx_body,
            math.pi / 2.0 + 0.2,
        )

    def test_mirrored_right_motor_is_inverted_exactly_once(self):
        tracker = odometry(invert_right=True)
        tracker.update(100, 100, 0.0)
        result = tracker.update(110, 90, 1.0)

        self.assertTrue(result.accepted)
        self.assertEqual(result.left_delta_counts, 10)
        self.assertEqual(result.right_delta_counts, 10)
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

    def test_both_inversion_flags_are_independent(self):
        tracker = odometry(invert_left=True, invert_right=True)
        tracker.update(100, 100, 0.0)
        result = tracker.update(90, 90, 1.0)

        self.assertTrue(result.accepted)
        self.assertEqual(result.left_delta_counts, 10)
        self.assertEqual(result.right_delta_counts, 10)
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

    def test_segmenting_same_counted_path_does_not_change_end_pose(self):
        continuous = odometry()
        continuous.update(0, 0, 0.0)
        continuous.update(100, 100, 4.0)

        segmented = odometry()
        segmented.update(0, 0, 0.0)
        timestamp = 0.0
        for endpoint in (25, 50, 75, 100):
            timestamp += 1.0
            self.assertTrue(segmented.update(endpoint, endpoint, timestamp).accepted)
            # Ein Stillstandsintervall zwischen zwei Fahrten darf weder Weg
            # hinzufuegen noch die absolute Baseline verwerfen.
            timestamp += 1.0
            stopped = segmented.update(endpoint, endpoint, timestamp)
            self.assertTrue(stopped.accepted)
            self.assertEqual(stopped.distance_m, 0.0)

        self.assert_pose(continuous, 1.0, 0.0, 0.0)
        self.assert_pose(segmented, 1.0, 0.0, 0.0)
        self.assert_pose(
            segmented,
            continuous.x_m,
            continuous.y_m,
            continuous.yaw_rad,
        )

    def test_encoder_motion_during_braking_is_not_lost(self):
        tracker = odometry()
        tracker.update(0, 0, 0.0)
        while_commanded = tracker.update(100, 100, 1.0)
        # Ab hier waere /cmd_vel bereits null. Die Zaehler bewegen sich in der
        # Bremsphase dennoch um weitere 20 Counts.
        during_braking = tracker.update(120, 120, 2.0)

        self.assertTrue(while_commanded.accepted)
        self.assertTrue(during_braking.accepted)
        self.assertAlmostEqual(during_braking.distance_m, 0.2)
        self.assert_pose(tracker, 1.2, 0.0, 0.0)

    def test_manual_push_is_counted_without_command_input(self):
        tracker = odometry()
        tracker.update(500, 700, 0.0)
        pushed = tracker.update(530, 730, 3.0)

        self.assertTrue(pushed.accepted)
        self.assertEqual(pushed.left_delta_counts, 30)
        self.assertEqual(pushed.right_delta_counts, 30)
        self.assertAlmostEqual(pushed.linear_velocity_mps, 0.1)
        self.assert_pose(tracker, 0.3, 0.0, 0.0)

    def test_short_feedback_outage_is_recovered_from_absolute_counts(self):
        tracker = odometry(max_recovery_gap_s=5.0)
        tracker.update(0, 0, 0.0)
        first = tracker.update(10, 10, 1.0)
        # Fuer t=2 und t=3 wird update bewusst nicht aufgerufen: beide Modbus-
        # Paarmessungen seien ausgefallen. Die Baseline muss bei 10 bleiben.
        recovered = tracker.update(40, 40, 4.0)

        self.assertTrue(first.accepted)
        self.assertTrue(recovered.accepted)
        self.assertEqual(recovered.left_delta_counts, 30)
        self.assertEqual(recovered.right_delta_counts, 30)
        self.assertAlmostEqual(recovered.sample_dt_s, 3.0)
        self.assertAlmostEqual(recovered.linear_velocity_mps, 0.1)
        self.assert_pose(tracker, 0.4, 0.0, 0.0)

    def test_long_feedback_outage_rebaselines_without_pose_jump(self):
        tracker = odometry(max_recovery_gap_s=2.0)
        tracker.update(0, 0, 0.0)
        tracker.update(10, 10, 1.0)
        before = (tracker.x_m, tracker.y_m, tracker.yaw_rad)

        gap = tracker.update(1000, 2000, 5.0)
        self.assertFalse(gap.accepted)
        self.assertEqual(gap.reason, 'luecke_zu_lang_rebaseline')
        self.assertEqual((tracker.x_m, tracker.y_m, tracker.yaw_rad), before)
        self.assertEqual(tracker.rebase_count, 1)

        after_rebase = tracker.update(1010, 2010, 6.0)
        self.assertTrue(after_rebase.accepted)
        self.assert_pose(tracker, 0.2, 0.0, 0.0)

    def test_jump_filter_accepts_boundary_and_rejects_one_count_more(self):
        # 60 rpm * 1 s / 60 * 100 Counts = exakt 100 plausible Counts.
        tracker = odometry(
            max_motor_rpm=60.0,
            max_delta_factor=1.0,
            quantization_margin_counts=0,
        )
        tracker.update(0, 0, 0.0)
        boundary = tracker.update(100, 100, 1.0)
        self.assertTrue(boundary.accepted)
        self.assert_pose(tracker, 1.0, 0.0, 0.0)

        jump = tracker.update(201, 200, 2.0)
        self.assertFalse(jump.accepted)
        self.assertTrue(jump.reason.startswith('unplausibles_delta:'))
        self.assertEqual(jump.left_delta_counts, 101)
        self.assertEqual(jump.right_delta_counts, 100)
        self.assertEqual(tracker.rebase_count, 1)
        self.assert_pose(tracker, 1.0, 0.0, 0.0)

        # Das gesamte Paar wurde auf den verworfenen Stand rebaselined. Beim
        # naechsten symmetrischen Delta darf kein alter Rechtsweg nachlaufen.
        resumed = tracker.update(211, 210, 3.0)
        self.assertTrue(resumed.accepted)
        self.assertEqual(resumed.left_delta_counts, 10)
        self.assertEqual(resumed.right_delta_counts, 10)
        self.assert_pose(tracker, 1.1, 0.0, 0.0)

    def test_ambiguous_half_range_rebaselines_without_motion(self):
        tracker = odometry()
        tracker.update(0, 0, 0.0)
        ambiguous = tracker.update(0x80000000, 0, 1.0)

        self.assertFalse(ambiguous.accepted)
        self.assertTrue(ambiguous.reason.startswith('mehrdeutiges_delta:'))
        self.assertEqual(tracker.rebase_count, 1)
        self.assert_pose(tracker, 0.0, 0.0, 0.0)

    def test_repeated_absolute_sample_is_never_double_counted(self):
        tracker = odometry()
        tracker.update(0, 0, 0.0)
        moved = tracker.update(10, 10, 0.1)
        self.assertTrue(moved.accepted)
        self.assert_pose(tracker, 0.1, 0.0, 0.0)

        # Entspricht mehreren 50-Hz-Updates zwischen zwei neuen 10-Hz-
        # Encoderproben: derselbe absolute Stand darf nie erneut Weg erzeugen.
        for timestamp in (0.12, 0.14, 0.16, 0.18):
            duplicate = tracker.update(10, 10, timestamp)
            self.assertTrue(duplicate.accepted)
            self.assertEqual(duplicate.left_delta_counts, 0)
            self.assertEqual(duplicate.right_delta_counts, 0)
            self.assertEqual(duplicate.distance_m, 0.0)
            self.assert_pose(tracker, 0.1, 0.0, 0.0)

        next_sample = tracker.update(20, 20, 0.2)
        self.assertTrue(next_sample.accepted)
        self.assert_pose(tracker, 0.2, 0.0, 0.0)

    def test_non_monotonic_timestamp_is_rejected_without_moving_baseline(self):
        tracker = odometry()
        tracker.update(0, 0, 1.0)
        rejected = tracker.update(10, 10, 1.0)
        self.assertFalse(rejected.accepted)
        self.assertEqual(rejected.reason, 'nicht_monotoner_zeitstempel')

        recovered = tracker.update(20, 20, 2.0)
        self.assertTrue(recovered.accepted)
        self.assertEqual(recovered.left_delta_counts, 20)
        self.assert_pose(tracker, 0.2, 0.0, 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
