"""Clearing-ray limits are not measured obstacles; retain measured marking."""
from pathlib import Path
import pytest
import yaml


@pytest.mark.parametrize('costmap', ('local_costmap', 'global_costmap'))
def test_vl53_clearing_endpoints_cannot_mark_but_measurements_still_can(costmap):
    source = Path(__file__).resolve().parents[1]/'config/nav2_params_real.yaml'
    layer = yaml.safe_load(source.read_text())[costmap][costmap]['ros__parameters']['obstacle_layer']
    for side in ('left', 'right'):
        clear = layer['vl53_'+side]
        measured = layer['vl53_'+side+'_mark']
        assert clear['topic'] == '/near_field/'+side+'/points_costmap'
        assert clear['clearing'] is True and clear['marking'] is False
        assert measured['topic'] == '/near_field/'+side+'/points'
        assert measured['marking'] is True and measured['clearing'] is False
        assert measured['obstacle_max_range'] == .55
        assert clear['raytrace_max_range'] == .7
