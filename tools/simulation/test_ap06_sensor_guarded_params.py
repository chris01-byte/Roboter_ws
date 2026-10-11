"""New product policy preserves actual VL53 layer and original criteria."""
from pathlib import Path

import pytest
import yaml

from ap06_closed_product import params


REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('policy', ['observed_only', 'sensor_guarded'])
def test_generated_closed_product_parameters_match_motion_policy(tmp_path, policy):
    manifest = REPO/'tools/simulation/ap06_product_scenarios.json'
    unchanged = manifest.read_bytes()
    actual = yaml.safe_load(params(REPO, tmp_path, policy).read_text())
    original = yaml.safe_load((REPO/'src/robot_navigation/config/nav2_params_real.yaml').read_text())
    assert actual['planner_server']['ros__parameters']['GridBased']['allow_unknown'] is (policy == 'sensor_guarded')
    for name in ('local_costmap', 'global_costmap'):
        costmap = actual[name][name]['ros__parameters']
        assert costmap['obstacle_layer'] == original[name][name]['ros__parameters']['obstacle_layer']
        assert ('lidar_obstacle_layer' in costmap['plugins']) is (policy == 'sensor_guarded')
    for name in ('velocity_smoother', 'controller_server'):
        assert actual[name] == original[name]
    monitor = actual['collision_monitor']['ros__parameters']
    assert ('lidar' in monitor['observation_sources']) is (policy == 'sensor_guarded')
    assert monitor['FootprintApproach']['time_before_collision'] == 2.
    assert manifest.read_bytes() == unchanged
