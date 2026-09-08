from dataclasses import replace
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hwt601_bias_stillstand import Integral, profile_config  # noqa: E402
from robot_state_estimation.quality_core import GyroBiasEstimator  # noqa: E402


def test_integral_uses_seconds_radians_and_all_three_axes():
    integral = Integral()
    for index in range(101):
        integral.add(index * 0.01, (0.01, -0.02, 0.03))
    assert integral.value == pytest.approx([math.degrees(v) for v in (.01, -.02, .03)])
    assert integral.peak == pytest.approx([math.degrees(v) for v in (.01, .02, .03)])


@pytest.mark.parametrize('stamp', [0.0, -1.0, 0.2])
def test_bad_interval_cannot_be_hidden_in_integrated_angle(stamp):
    integral = Integral()
    integral.add(0.0, (0, 0, 0))
    with pytest.raises(ValueError):
        integral.add(stamp, (0, 0, 0))


def test_fixed_reference_is_not_secretly_adapted():
    config = profile_config()
    fixed = GyroBiasEstimator(replace(config, stationary_adaptation_time_constant_s=0))
    adaptive = GyroBiasEstimator(config)
    for i in range(3001):
        fixed.update(i * .01, (.001, .006, .0001), True)
        adaptive.update(i * .01, (.001, .006, .0001), True)
    initial = fixed.result.bias_radps
    assert fixed.result.calibrated and adaptive.result.calibrated
    for i in range(3001, 6001):
        fixed.update(i * .01, (.001, .006, .0002), True)
        adaptive.update(i * .01, (.001, .006, .0002), True)
    assert fixed.result.bias_radps == initial
    assert adaptive.result.bias_radps[2] > fixed.result.bias_radps[2]
    assert config.stationary_adaptation_time_constant_s == 30.0
