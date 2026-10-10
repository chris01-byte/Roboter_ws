import math
from pathlib import Path
import sys

import pytest
from shapely.affinity import affine_transform
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robot_navigation.lab_motion_geometry import (
    fixed_sequence_in_scope, stop_sweep_in_scope, wheel_pose_in_bound_scope)
from robot_navigation.stage3_motion_diagnostic import disk_in_polygon

LAB = ((-.13, -.9), (2., -.9), (2., .7), (-.13, .7))


def test_complete_fixed_sequence_fits_reviewed_lab_where_circle_does_not():
    assert not disk_in_polygon(0., 0., .414, LAB)
    assert fixed_sequence_in_scope((0., 0., 0.), LAB)
    assert stop_sweep_in_scope((0., 0., 0.), .08, 0., LAB)
    # A real requested in-place turn at the boundary still fails.
    assert not stop_sweep_in_scope((0., 0., 0.), 0., .1, LAB)


def test_scope_must_cover_interior_not_only_start_and_endpoint():
    notch = ((-.13, -.9), (2., -.9), (2., .7), (.5, .7),
             (.5, .2), (.4, .2), (.4, .7), (-.13, .7))
    assert stop_sweep_in_scope((0., 0., 0.), 0., 0., notch)
    assert not fixed_sequence_in_scope((0., 0., 0.), notch)


def test_brake_travel_is_checked_beyond_current_contour():
    short = ((-.13, -.9), (.34, -.9), (.34, .7), (-.13, .7))
    assert stop_sweep_in_scope((0., 0., 0.), 0., 0., short)
    assert not stop_sweep_in_scope((0., 0., 0.), .08, 0., short)
    assert not fixed_sequence_in_scope((0., 0., 0.), short)


@pytest.mark.parametrize('angle', [-2.9, -.4, .73, 2.7])
def test_world_frame_rotation_does_not_change_result(angle):
    c, s = math.cos(angle), math.sin(angle)
    transformed = affine_transform(Polygon(LAB), [c, -s, s, c, 5., -3.])
    assert fixed_sequence_in_scope((5., -3., angle), tuple(transformed.exterior.coords))
    assert stop_sweep_in_scope((5., -3., angle), .08, 0., tuple(transformed.exterior.coords))


@pytest.mark.parametrize('vx,wz', [(-.01, 0.), (.081, 0.), (0., .101),
                                  (float('nan'), 0.), (0., float('inf'))])
def test_invalid_or_unbounded_motion_is_never_covered(vx, wz):
    assert not stop_sweep_in_scope((0., 0., 0.), vx, wz, LAB)


def test_continuous_rotation_checks_intermediate_corner_extremum():
    # Heading endpoints can both fit while an intermediate corner protrudes.
    generous = ((-1., -1.), (2., -1.), (2., 1.), (-1., 1.))
    assert stop_sweep_in_scope((.25, 0., .4), 0., .1, generous)
    radius = math.hypot(.33, .25)
    narrow = ((-1., -1.), (2., -1.), (2., radius-.0001), (-1., radius-.0001))
    heading = math.atan2(.33, .25)-.08
    assert not stop_sweep_in_scope((.25, 0., heading), 0., .1, narrow)


def test_wheel_bound_pose_uses_actual_displacement_in_immutable_start_frame():
    origin_wheel = (3., -2., .4)
    origin_map = (5., 7., .4+math.pi/2)
    assert wheel_pose_in_bound_scope(origin_wheel, origin_wheel, origin_map) == pytest.approx(origin_map)
    moved = wheel_pose_in_bound_scope((3.1, -2., .45), origin_wheel, origin_map)
    assert moved == pytest.approx((5., 7.1, origin_map[2]+.05))
    with pytest.raises(ValueError):
        wheel_pose_in_bound_scope((float('nan'), 0., 0.), origin_wheel, origin_map)


def test_signed_measured_residual_keeps_padding_and_never_authorizes_reverse_command():
    # One count of left/right sampling skew can produce signed mean vx in
    # a real in-place turn; the measured stop envelope, not a command clamp,
    # owns its containment decision. All requested commands stay unchanged.
    assert not stop_sweep_in_scope((.27,0.,0.), -.0004,.103,LAB)
    assert stop_sweep_in_scope((.27,0.,0.), -.0004,.103,LAB,observed_motion=True)
    assert not stop_sweep_in_scope((0.,0.,0.), -.01,0.,LAB,observed_motion=True)
    assert not stop_sweep_in_scope((.27,0.,0.), .31,0.,LAB,observed_motion=True)
    assert not stop_sweep_in_scope((.27,0.,0.), 0.,.81,LAB,observed_motion=True)
