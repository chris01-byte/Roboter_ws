"""Geometry-only qualification: no ROS nodes, devices or motion commands."""
import math

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from explore.metric_start_sweep import (
    PADDED_BOUNDS, check_straight_start, enclosing_bounds)


def fixture():
    return dict(occupancy=np.zeros((200, 200), dtype=np.int8),
                initial_unknown=np.zeros((200, 200), dtype=bool),
                resolution_m=.01, origin=(-1., -1., 0.),
                scope_vertices=[(-.8, -.8), (.8, -.8), (.8, .8), (-.8, .8)],
                pose=(0., 0., 0.), distance_m=.25,
                position_error_m=.02, heading_error_rad=.05)


def test_full_straight_sweep_known_free_has_no_motion_authority():
    result = check_straight_start(**fixture())
    assert result.geometry_admissible
    assert result.report()['motion_authorized'] is False


def test_fixed_initial_rear_unknown_can_be_left_without_map_whitening():
    args = fixture()
    args['occupancy'][82:118, 88:92] = -1
    args['initial_unknown'][82:118, 88:92] = True
    original = args['occupancy'].copy()
    result = check_straight_start(**args)
    assert result.geometry_admissible
    assert result.initial_unknown_area_m2 > 0
    np.testing.assert_array_equal(args['occupancy'], original)


def test_unknown_cells_are_not_automatically_added_to_initial_inventory():
    args = fixture()
    args['occupancy'][99:101, 90:92] = -1
    assert check_straight_start(**args).reason == 'straight_sweep_new_unknown'


@pytest.mark.parametrize('value', [-1, 1, 100])
def test_middle_of_sweep_is_checked_even_if_endpoints_are_free(value):
    args = fixture()
    args['bounds'] = (-.02, .02, -.02, .02)
    args['occupancy'][100, 112] = value
    result = check_straight_start(**args)
    assert result.reason == ('straight_sweep_new_unknown' if value < 0
                             else 'straight_sweep_occupied')


def test_old_unknown_cell_becoming_occupied_cannot_be_excused():
    args = fixture()
    args['occupancy'][100, 90] = 100
    args['initial_unknown'][100, 90] = True
    assert check_straight_start(**args).reason == 'straight_sweep_occupied'


def test_declaring_whole_map_initial_unknown_does_not_excuse_external_area():
    args = fixture()
    args['occupancy'][100, 140] = -1
    args['initial_unknown'][:] = True
    assert check_straight_start(**args).reason == 'straight_sweep_new_unknown'


def test_partial_unknown_cell_not_wholly_excused_by_initial_body_overlap():
    args = fixture()
    args['pose'] = (.003, 0., 0.)
    args['occupancy'][100, 133] = -1
    args['initial_unknown'][100, 133] = True
    result = check_straight_start(**args)
    assert result.reason == 'straight_sweep_new_unknown'
    assert 0 < result.initial_unknown_area_m2 < .0001


def test_unknown_in_tracking_band_is_not_excused_by_nominal_body():
    args = fixture()
    args['occupancy'][100, 84] = -1
    args['initial_unknown'][100, 84] = True
    assert check_straight_start(**args).reason == 'straight_sweep_new_unknown'


def test_geometric_boundary_has_no_raster_half_diagonal_false_rejection():
    args = fixture()
    args.update(position_error_m=0., heading_error_rad=0.)
    args['scope_vertices'] = [(-.13, -.25), (.58, -.25), (.58, .25), (-.13, .25)]
    assert check_straight_start(**args).geometry_admissible
    # A zero-error ideal result must not become a positive real-error result.
    args['position_error_m'] = .001
    assert check_straight_start(**args).reason == 'straight_sweep_outside_scope'


def test_concave_scope_hole_between_endpoints_is_rejected():
    args = fixture()
    args['bounds'] = (-.02, .02, -.02, .02)
    args['scope_vertices'] = [(-.8, -.8), (.8, -.8), (.8, .8),
                              (.18, .8), (.18, -.1), (.12, -.1),
                              (.12, .8), (-.8, .8)]
    assert check_straight_start(**args).reason == 'straight_sweep_outside_scope'


def test_map_boundary_cannot_be_excused():
    args = fixture()
    args.update(origin=(0., -1., 0.))
    assert check_straight_start(**args).reason == 'straight_sweep_outside_grid'


@pytest.mark.parametrize('yaw', [.27, -1.17, math.pi/2])
def test_global_rigid_transform_preserves_all_areas(yaw):
    args = fixture()
    args['occupancy'][100, 140] = -1
    original = check_straight_start(**args)
    c, s = math.cos(yaw), math.sin(yaw)
    def point(x, y):
        return (2+c*x-s*y, -3+s*x+c*y)
    args['origin'] = (*point(*args['origin'][:2]), yaw)
    args['pose'] = (*point(0., 0.), yaw)
    args['scope_vertices'] = [point(x, y) for x, y in args['scope_vertices']]
    transformed = check_straight_start(**args)
    assert transformed.reason == original.reason
    assert transformed.new_unknown_area_m2 == pytest.approx(original.new_unknown_area_m2)


def test_analytic_heading_envelope_contains_independent_sampled_corners():
    # Include extrema strictly between both endpoint headings.
    for half_angle in (0., .001, .05, .6, 1.8, math.pi):
        left, right, bottom, top = enclosing_bounds(PADDED_BOUNDS, .02, half_angle)
        for yaw in np.linspace(-half_angle, half_angle, 301):
            for x in PADDED_BOUNDS[:2]:
                for y in PADDED_BOUNDS[2:]:
                    px = math.cos(yaw)*x-math.sin(yaw)*y
                    py = math.sin(yaw)*x+math.cos(yaw)*y
                    assert left-1e-14 <= px-.02 <= px+.02 <= right+1e-14
                    assert bottom-1e-14 <= py-.02 <= py+.02 <= top+1e-14


def test_angular_interior_extremum_is_larger_than_endpoint_only_bound():
    bounds = enclosing_bounds(PADDED_BOUNDS, 0., .9)
    assert bounds[1] == pytest.approx(math.hypot(.33, .25))
    endpoint_max = max(math.cos(t)*x-math.sin(t)*y for t in (-.9, .9)
                       for x in PADDED_BOUNDS[:2] for y in PADDED_BOUNDS[2:])
    assert bounds[1] > endpoint_max


def test_independent_dense_trajectory_samples_stay_within_accepted_free_region():
    args = fixture()
    args['occupancy'][82:118, 88:92] = -1
    args['initial_unknown'][82:118, 88:92] = True
    assert check_straight_start(**args).geometry_admissible
    scope = Polygon(args['scope_vertices'])
    initial = box(-.13, -.25, .33, .25)
    unknown = box(-.12, -.18, -.08, .18)
    # Independent physical corner formula, including tracking envelope edges.
    for distance in np.linspace(0., .25, 17):
        for yaw in (-.05, -.017, 0., .023, .05):
            for dx, dy in ((.02, 0.), (-.02, 0.), (0., .02), (0., -.02)):
                corners = [(distance+dx+math.cos(yaw)*x-math.sin(yaw)*y,
                            dy+math.sin(yaw)*x+math.cos(yaw)*y)
                           for x, y in [(-.13,-.25),(.33,-.25),(.33,.25),(-.13,.25)]]
                footprint = Polygon(corners)
                assert scope.covers(footprint)
                assert footprint.difference(initial).intersection(unknown).area < 1e-12


def test_tracking_sweep_detects_obstacle_missed_by_ideal_straight_motion():
    args = fixture()
    args['occupancy'][125, 115] = 100  # just outside the nominal left side
    robust = check_straight_start(**args)
    assert robust.reason == 'straight_sweep_occupied'
    args.update(position_error_m=0., heading_error_rad=0.)
    assert check_straight_start(**args).geometry_admissible


def test_tiny_real_unknown_sliver_is_not_rounded_to_a_free_cell():
    args = fixture()
    args.update(position_error_m=0., heading_error_rad=0., distance_m=.0001)
    args['occupancy'][100, 133] = -1
    assert check_straight_start(**args).new_unknown_area_m2 == pytest.approx(1e-6)


def test_new_snapshot_is_evaluated_again_without_cached_free_space():
    args = fixture()
    assert check_straight_start(**args).geometry_admissible
    args['occupancy'][100, 145] = 100
    assert check_straight_start(**args).reason == 'straight_sweep_occupied'


@pytest.mark.parametrize('key,value', [
    ('distance_m', -.01), ('distance_m', .51), ('distance_m', float('nan')),
    ('position_error_m', -.01), ('heading_error_rad', float('inf')),
    ('heading_error_rad', math.pi+.01), ('resolution_m', 0.),
    ('free_max_value', 100), ('free_max_value', True),
    ('pose', (0., 0., float('nan'))),
    ('scope_vertices', [(0., 0.), (1., 1.), (0., 1.), (1., 0.)]),
])
def test_invalid_inputs_fail_closed(key, value):
    args = fixture()
    args[key] = value
    with pytest.raises(ValueError):
        check_straight_start(**args)


@pytest.mark.parametrize('kind', ['shape', 'dtype', 'occupancy', 'float_raster'])
def test_invalid_rasters_fail_closed(kind):
    args = fixture()
    if kind == 'shape':
        args['initial_unknown'] = np.zeros((2, 2), dtype=bool)
    elif kind == 'dtype':
        args['initial_unknown'] = np.zeros((200, 200), dtype=np.uint8)
    elif kind == 'occupancy':
        args['occupancy'][0, 0] = -2
    else:
        args['occupancy'] = args['occupancy'].astype(float)
    with pytest.raises(ValueError):
        check_straight_start(**args)


def test_costmap_threshold_does_not_apply_to_raw_map_or_lethal_cells():
    args = fixture()
    args['occupancy'][100, 140] = 50
    assert not check_straight_start(**args).geometry_admissible
    assert check_straight_start(**args, free_max_value=90).geometry_admissible
    args['occupancy'][100, 140] = 100
    assert not check_straight_start(**args, free_max_value=90).geometry_admissible
