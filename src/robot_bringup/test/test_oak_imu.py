from pathlib import Path
import unittest

import yaml

from robot_bringup.oak_imu_check import ImuSample, evaluate_samples


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class OakImuProfileTests(unittest.TestCase):
    def test_all_oak_profiles_pin_verified_bmi270_parameters(self):
        expected = {
            'i_message_type': 'IMU',
            'i_sync_method': 'COPY',
            'i_enable_acc': True,
            'i_acc_mode': 'ACCELEROMETER_RAW',
            'i_acc_freq': 100,
            'i_enable_gyro': True,
            'i_gyro_mode': 'GYROSCOPE_RAW',
            'i_gyro_freq': 100,
            'i_enable_mag': False,
            'i_enable_rotation': False,
        }
        for name in (
            'oak_params.yaml',
            'oak_params_slam.yaml',
            'oak_params_detail.yaml',
        ):
            with self.subTest(profile=name):
                config = yaml.safe_load(
                    (PACKAGE_ROOT / 'config' / name).read_text(encoding='utf-8'))
                params = config['/oak']['ros__parameters']
                self.assertTrue(params['camera']['i_enable_imu'])
                self.assertEqual(params['imu'], expected)


class OakImuEvaluationTests(unittest.TestCase):
    @staticmethod
    def _samples(count=101, rate=100.0):
        return [
            ImuSample(
                received_s=index / rate,
                stamp_ns=round(index * 1e9 / rate),
                frame_id='oak_imu_frame',
                acceleration=(0.0, 0.0, 9.81),
                angular_velocity=(0.001, -0.002, 0.003),
            )
            for index in range(count)
        ]

    def test_accepts_complete_100_hz_stream(self):
        result, errors = evaluate_samples(
            self._samples(), min_rate_hz=80.0, max_rate_hz=130.0,
            expected_frame='oak_imu_frame')
        self.assertEqual(errors, [])
        self.assertEqual(result['messages'], 101)
        self.assertEqual(result['non_increasing_stamps'], 0)

    def test_rejects_silent_stream(self):
        _, errors = evaluate_samples(
            [], min_rate_hz=80.0, max_rate_hz=130.0,
            expected_frame='oak_imu_frame')
        self.assertIn('weniger als zwei IMU-Nachrichten empfangen', errors)

    def test_rejects_wrong_rate_frame_and_non_finite_value(self):
        samples = self._samples(count=11, rate=10.0)
        broken = list(samples)
        broken[-1] = ImuSample(
            received_s=broken[-1].received_s,
            stamp_ns=broken[-2].stamp_ns,
            frame_id='wrong_frame',
            acceleration=(float('nan'), 0.0, 9.81),
            angular_velocity=broken[-1].angular_velocity,
        )
        _, errors = evaluate_samples(
            broken, min_rate_hz=80.0, max_rate_hz=130.0,
            expected_frame='oak_imu_frame')
        self.assertTrue(any('Empfangsrate' in error for error in errors))
        self.assertTrue(any('nicht steigende' in error for error in errors))
        self.assertTrue(any('Frame(s)' in error for error in errors))
        self.assertIn('NaN oder unendlicher IMU-Messwert', errors)


if __name__ == '__main__':
    unittest.main()
