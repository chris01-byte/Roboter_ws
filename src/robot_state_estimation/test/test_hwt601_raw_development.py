"""Production poll/status methods with synthetic serial/time, no executor/device."""
from collections import deque
import json
from types import SimpleNamespace
import pytest

pytest.importorskip('rclpy')
from rclpy.time import Time
from robot_state_estimation.hwt601_imu_node import Hwt601ImuNode
from robot_state_estimation.hwt601_transport import Hwt601TransportError
from robot_state_estimation.hwt601_protocol import Hwt601ProtocolError


class Sink:
    def __init__(self): self.messages=[]
    def publish(self,msg): self.messages.append(msg)


@pytest.fixture
def reader(monkeypatch):
    from robot_state_estimation import hwt601_imu_node as module
    now=[10.];monkeypatch.setattr(module.time,'monotonic',lambda:now[0])
    n=Hwt601ImuNode.__new__(Hwt601ImuNode)
    n.__dict__.update(development_contract=True,response_timeout_s=.05,sensor_timeout_s=.30,
        port='/dev/ttyUSB_HWT601',baud=115200,device_address=80,frame_id='hwt601_link',
        imu_topic='/shadow/hwt601/imu/data_raw',_last_received_at=10.,
        _last_measurement_stamp_ns=10**10,_last_transport_diagnostic={},
        _terminal_fault=None,_accepted=1,_rejected=0,_successful_connections=1,
        _consecutive_errors=0,_last_error='',_sample_times=deque([9.99,10.]),
        errors_before_reconnect=3,acceleration_full_scale_g=4.,angular_velocity_full_scale_dps=400.,
        saturation_margin_counts=8,angular_velocity_variance=.02,linear_acceleration_variance=.25)
    n.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=round(now[0]*1e9)))
    n.status_pub=Sink();n.imu_pub=Sink();n.diagnostics_pub=Sink()
    n._transport=SimpleNamespace(is_open=True,close=lambda:None,
        read_motion_registers=lambda:(0,0,0,0,0,0),
        last_reply_received_monotonic_s=10.048,last_transaction={})
    return n,now


def status(n):return json.loads(n.status_pub.messages[-1].data)


def test_one_payload_timeout_is_transport_degraded_with_original_fresh_data(reader):
    n,now=reader;now[0]=10.037327
    n._record_error(Hwt601TransportError('Zeitueberschreitung nach 0/14 Bytes',
        kind='response_deadline',diagnostic={'phase':'payload','header_received_bytes':3,
        'phase_received_bytes':0,'classification':'payload_missing'}))
    d=status(n)
    assert d['ready'] and d['data_valid'] and d['data_fresh'] and d['transport_degraded']
    assert not d['transport_ok'] and not d['hold_required'] and d['terminal_fault'] is None
    assert d['last_measurement_stamp_ns']==10**10 and not n.imu_pub.messages
    assert d['last_transport_diagnostic']['header_received_bytes']==3


def test_repeated_timeouts_only_make_data_unusable_at_actual_freshness_limit(reader):
    n,now=reader
    for t in (10.05,10.1,10.15,10.2,10.25,10.31):
        now[0]=t;n._record_error(Hwt601TransportError('timeout',kind='response_deadline'))
    d=status(n)
    assert n._transport is not None and d['data_valid'] and not d['data_fresh']
    assert d['hold_required'] and not d['ready'] and d['terminal_fault'] is None
    assert d['consecutive_errors']==6 and not n.imu_pub.messages


@pytest.mark.parametrize('error',[Hwt601TransportError('port lost'),Hwt601ProtocolError('CRC')])
def test_port_protocol_failures_latch_even_while_last_sample_was_recent(reader,error):
    n,now=reader;now[0]=10.01;n._record_error(error)
    assert status(n)['terminal_fault'] and not status(n)['ready']
    n._poll();assert not n.imu_pub.messages


def test_good_pair_uses_reply_receipt_stamp_not_later_processing_or_publish_time(reader):
    n,now=reader;now[0]=10.05;n._poll()
    m=n.imu_pub.messages[-1]
    assert m.header.stamp.sec*10**9+m.header.stamp.nanosec==10_048_000_000
    assert n._last_received_at==10.048


def test_ros_clock_regression_is_hard_and_never_published(reader):
    n,now=reader;now[0]=9.99;n._transport.last_reply_received_monotonic_s=9.989
    n._poll();assert n._terminal_fault and not n.imu_pub.messages
