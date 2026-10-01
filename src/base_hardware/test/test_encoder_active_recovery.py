"""Active HWT adapter uses production Core; no ROS executor or serial access."""
import pytest

# The offline encoder workflow intentionally has no ROS runtime. HWT CI and
# target-system regressions execute this adapter test with actual ROS imports.
pytest.importorskip('rclpy', reason='active base adapter requires ROS 2')

from base_hardware.base_hardware_node import BaseHardware
from base_hardware.encoder_odometry import EncoderOdometry, MotorFeedback
from base_hardware.encoder_shadow_reader import EncoderShadowCore, EncoderPair


def active():
    n=BaseHardware.__new__(BaseHardware)
    tracker=EncoderOdometry(wheel_radius_m=.0624,wheel_separation_m=.3845,
        gear_ratio=10.,counts_per_motor_revolution=1000.,invert_left=False,
        invert_right=True,max_motor_rpm=700.,max_delta_factor=1.5,max_recovery_gap_s=.18)
    n.encoder_tracker=tracker;n.encoder_timing_core=EncoderShadowCore(tracker,max_pair_read_duration_s=.12)
    n.encoder_failure_stop_count=5;n.encoder_last_pair_duration_s=.014
    n.stops=[];n._send_stop_if_needed=lambda:n.stops.append(True)
    for i in range(21):n._accept_encoder_pair((MotorFeedback(0,0.),MotorFeedback(0,0.)),1+i*.02)
    assert n.encoder_feedback_ok
    return n


def test_active_hold_retains_connection_baseline_and_republishes_only_real_pairs():
    n=active();t=n.encoder_timing_core.last_sample_time_s
    n.encoder_last_pair_duration_s=.125
    n._accept_encoder_pair((MotorFeedback(10,0.),MotorFeedback(-10 & 0xffffffff,0.)),t+.065)
    assert not n.encoder_feedback_ok and not n.encoder_new_measurement and n.stops
    assert n.encoder_connection_initialized  # no configuration/rebaseline loop
    assert n.encoder_timing_core.last_sample_time_s==t
    n.encoder_last_pair_duration_s=.014
    for stamp,count in ((t+.15,20),(t+.20,30)):
        n._accept_encoder_pair((MotorFeedback(count,0.),MotorFeedback(-count & 0xffffffff,0.)),stamp)
        assert n.encoder_new_measurement
    assert n.encoder_feedback_ok and n.encoder_timing_core.tracker.rebase_count==0
    assert n.encoder_timing_core.last_update.left_delta_counts==10


def test_active_true_gap_never_publishes_or_silently_reinitializes():
    n=active();core=n.encoder_timing_core;t=core.last_sample_time_s
    n.encoder_last_pair_duration_s=.12087426500147558
    n._accept_encoder_pair((MotorFeedback(0,0.),MotorFeedback(0,0.)),t+.1294033375015715)
    n.encoder_last_pair_duration_s=.014
    before=core.tracker.__dict__.copy()
    for stamp in (t+.212127149,t+.27,t+.32,core.timing_recovery_deadline_s):
        n._accept_encoder_pair((MotorFeedback(0,0.),MotorFeedback(0,0.)),stamp)
        assert not n.encoder_new_measurement and not n.encoder_feedback_ok
        assert n.encoder_connection_initialized
        assert core.tracker.__dict__==before
    assert core.fault_reason=='encoder_timing_continuity_unproven'
