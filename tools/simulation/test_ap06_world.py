import importlib.util
from pathlib import Path
import math
import ast
import json
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('world', Path(__file__).with_name('ap06_world.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_first_return_occludes_room_behind_closed_door_edge():
    world = module.World(.68, [-1.9, -.45, 0.])
    distance = world.raycast([-1., .5], np.array([0.]))[0]
    assert distance == pytest.approx(.36)
    assert world.raycast([-1., 0.], np.array([0.]))[0] == pytest.approx(2.55)


def test_parallel_wall_ray_has_finite_return_and_side_clearance():
    world = module.World(.8, [0., 0., 0.])
    assert world.raycast([0., 0.], np.array([math.pi/2]))[0] == pytest.approx(.42)
    assert module.polygon_distance(module.chassis([0., 0., 0.]), world.obstacles[10]) == pytest.approx(.17)
    assert module.polygon_distance(module.chassis([0., 0., math.pi/2]), world.obstacles[10]) == pytest.approx(.29)


def test_encoder_measures_ramp_and_tail_after_zero_command():
    world = module.World(.8, [-1.9, -.45, 0.])
    for _ in range(10):
        world.integrate([.1, 0.], .01)
    before = world.motor_positions.copy()
    world.integrate([0., 0.], .01)
    assert world.motor_positions[0] > before[0]
    assert world.motor_positions[1] < before[1]
    assert world.travel < .011
    with pytest.raises(ValueError):
        world.integrate([.1, 0.], .04)


@pytest.mark.parametrize('beams', (720, 2160))
def test_native_mast_mask_is_nan_in_sensor_frame(beams):
    world = module.World(.8, [-1.9, -.45, 0.])
    angles, values = world.laser(beams=beams)
    assert len(values) == beams
    hidden = (angles >= math.radians(56)) & (angles <= math.radians(124))
    assert np.isnan(values[hidden]).all()
    assert np.isfinite(values[~hidden]).all()
    assert np.isfinite(world.laser(mask=False)[1]).all()


def test_native_manifest_preserves_scenarios_and_matches_product_beam_count():
    directory = Path(__file__).parent
    original = json.loads((directory/'ap06_scenarios.json').read_text())
    native = json.loads((directory/'ap06_native_scenarios.json').read_text())
    product = json.loads((directory/'ap06_product_scenarios.json').read_text())
    for key in ('plant', 'budgets', 'positive', 'negative', 'acceptance'):
        assert native[key] == original[key]
        assert product[key] == original[key]
    source = directory.parents[1]/'src/amadeus_lidar_bringup/amadeus_lidar_bringup/scan_vereinheitlichen.py'
    tree = ast.parse(source.read_text())
    declared = [node.args[1].value for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'declare_parameter' and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'strahlen']
    assert declared == [native['sensor']['lidar_beams']]
    assert original['sensor']['lidar_beams'] == 720
    assert {key: value for key, value in native['sensor'].items() if key != 'lidar_beams'} == {
        key: value for key, value in original['sensor'].items() if key != 'lidar_beams'}


def test_rear_clearance_requires_whole_chassis_beyond_door():
    world = module.World(.8, [.72, 0., 0.])
    world.integrate([0., 0.], .01)
    assert not world.rear_cleared
    world.pose[0] = .78
    world.integrate([0., 0.], .01)
    assert world.rear_cleared


def test_large_free_count_cannot_hide_false_wall_in_reference_comparison():
    world = module.World(.8, [-1.9, -.45, 0.])
    grid = np.zeros((94, 187), dtype=np.int8)
    grid[70, 43] = 100  # invented wall in the open left room
    oracle = world.map_oracle(grid, .03, (-.9, -.95))
    assert oracle['reference_observed_fraction'] > .99
    assert oracle['maximum_occupied_wall_error_m'] > .1


def test_depth_cone_returns_stop_at_wall_and_floor_without_inventing_far_points():
    world = module.World(.8, [-1.6, 0., 0.])
    ray = np.array([[1., 0., 0.], [math.sqrt(.5), 0., -math.sqrt(.5)]])
    returns = world.cone_returns((.15, 0., 1.25), ray)
    assert returns[0] == pytest.approx(3.)  # first central pillar, no far wall
    assert returns[1] == pytest.approx(1.34/math.sqrt(.5))  # floor occludes pillar
    assert np.isnan(world.cone_returns((.15,0.,1.25), ray, maximum=1.)).all()
