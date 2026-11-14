import copy
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation
import yaml

from robot_state_estimation.hwt601_mount import mount_pose

ROOT = Path(__file__).resolve().parents[1]
CONFIG = yaml.safe_load((ROOT / 'config/hwt601_mount.yaml').read_text())


def test_user_measurements_have_ground_to_base_conversion():
    translation, quaternion = mount_pose(CONFIG)
    assert translation == pytest.approx((0.084, 0.0, -0.056))
    assert np.linalg.norm(quaternion) == pytest.approx(1.0)
    assert CONFIG['position_uncertainty_m'] is None
    assert CONFIG['sensor_origin_offset_mount_m'] is None


@pytest.mark.parametrize('sensor,base', [
    ((1, 0, 0), (0, -1, 0)), ((0, 1, 0), (1, 0, 0)),
    ((0, 0, 1), (0, 0, 1)), ((1, 2, 3), (2, -1, 3)),
])
def test_all_axes_and_yaw_sign(sensor, base):
    _, quaternion = mount_pose(CONFIG)
    rotation = Rotation.from_quat(quaternion)
    assert rotation.apply(sensor) == pytest.approx(base)
    assert np.linalg.det(rotation.as_matrix()) == pytest.approx(1.0)


@pytest.mark.parametrize('key,value', [
    ('housing_center_forward_of_axle_m', 84),
    ('footplate_height_above_ground_m', float('nan')),
    ('mount_frame', 'hwt601_link'), ('sensor_x_direction', 'left'),
    ('fusion_approved', True),
])
def test_bad_units_axes_and_false_sensor_origin_are_refused(key, value):
    config = copy.deepcopy(CONFIG)
    config[key] = value
    with pytest.raises(ValueError):
        mount_pose(config)


def test_reference_is_not_started_by_any_existing_launch():
    for launch in (ROOT / 'launch').glob('*.launch.py'):
        if launch.name != 'hwt601_mount.launch.py':
            assert 'hwt601_mount' not in launch.read_text()
    text = (ROOT / 'launch/hwt601_mount.launch.py').read_text()
    assert "executable='static_transform_publisher'" in text
    assert "executable='hwt601_imu'" not in text
    assert "package='base_hardware'" not in text
