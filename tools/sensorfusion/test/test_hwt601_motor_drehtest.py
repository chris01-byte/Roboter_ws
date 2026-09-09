import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hwt601_motor_drehtest import angle_delta, base_healthy, stationary, drive_decision


def test_wrapping():
    assert math.degrees(angle_delta(math.radians(-179),math.radians(179))) == pytest.approx(2)


def test_target_stops_and_speed_is_bounded():
    for angle in range(88):
        assert drive_decision(angle/6,angle,angle,0,angle)==.10
    assert drive_decision(16,88,89,.01,90)==0


def test_right_target_and_wrong_direction():
    for angle in range(88):
        assert drive_decision(angle/6,-angle,-angle,0,-angle,-1)==-.10
    assert drive_decision(16,-88,-89,.01,-90,-1)==0
    for values in ((1,3,0,0,0),(1,0,3,0,0),(25,-80,-80,0,-80),
                   (15,-80,-106,0,-80),(5,0,0,0,0),(5,-30,-10,0,-30)):
        with pytest.raises(ValueError):drive_decision(*values,direction=-1)
    with pytest.raises(ValueError):drive_decision(0,0,0,0,0,direction=0)


@pytest.mark.parametrize('values',[
    (25,80,80,0,80),(1,-3,0,0,0),(1,0,-3,0,0),
    (15,80,106,0,80),(1,0,0,.13,0),(1,0,0,0,121),
    (5,0,0,0,0),(5,30,10,0,30),(1,float('nan'),0,0,0)])
def test_motion_aborts(values):
    with pytest.raises(ValueError):drive_decision(*values)


def test_base_fails_closed():
    state=dict(dry_run=False,allow_rs485=True,rs485_ready=True,
               encoder_feedback_ok=True,encoder_initialized=True,
               encoder_stale=False,encoder_config_fault_latched=False)
    assert base_healthy(state,.1)
    assert not base_healthy(state,.4)
    for key in state:
        broken=state.copy();del broken[key]
        assert not base_healthy(broken,.1)
        broken=state.copy();broken[key]=not state[key]
        assert not base_healthy(broken,.1)


def test_standstill_requires_real_finite_feedback():
    assert stationary(dict(meas_v_mps=0,meas_w_radps=0))
    for value in (None,float('nan'),.02):
        assert not stationary(dict(meas_v_mps=0,meas_w_radps=value))
    assert not stationary({})
