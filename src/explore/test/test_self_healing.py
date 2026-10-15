"""Pure self-healing decisions: taxonomy, ladder, own-track reversal, frontiers."""
import math

import numpy as np
import pytest

from explore.self_healing import (
    FATAL, HEAL, WAIT, classify,
    HealingLadder, RETRY, DEFER, LOOK_AROUND, TRACK_BACK, REQUEST_HELP,
    TrackRecorder, frontier_goals, frontier_cells_remaining, rotation_clear)


@pytest.mark.parametrize('reason,expected', [
    ('estop_active', FATAL), ('hwt601_terminal_fault', FATAL),
    ('child_cancel_failed', FATAL), ('second_child_forbidden', FATAL),
    ('actuator_or_encoder_state_invalid', FATAL),
    ('estop_missing_stale_or_active', WAIT), ('lidar_missing_stale_or_invalid', WAIT),
    ('vl53_status_missing_stale_or_invalid', WAIT), ('localization_missing_or_stale', WAIT),
    ('odometry_missing_stale_or_invalid age_s=1.2', WAIT), ('hwt_hold', WAIT),
    ('nav_aborted', HEAL), ('nav_timeout', HEAL), ('nav_rejected', HEAL),
    ('frontier_candidate_processing_budget_exhausted', HEAL),
    ('map_status_join_pending', HEAL), ('start_egress_new_unknown_or_obstacle', HEAL),
    (None, HEAL), ('', HEAL),
])
def test_only_genuine_exceptions_are_fatal(reason, expected):
    assert classify(reason) == expected


def test_ladder_escalates_retry_defer_look_track_help_and_resets_on_progress():
    ladder = HealingLadder(goal_retries=1, look_around_after=3, track_back_after=5, help_after=8)
    ladder.start(0.)
    actions = [ladder.failure(1.+i, 'nav_aborted', goal_attempts=1 if i == 0 else 2,
                              track_back_available=True, look_around_available=True)
               for i in range(8)]
    assert actions == [RETRY, DEFER, LOOK_AROUND, DEFER, TRACK_BACK, DEFER, DEFER, REQUEST_HELP]
    ladder.progress(20.)
    assert ladder.streak == 0 and not ladder.looked_around and not ladder.tracked_back
    assert ladder.failure(21., 'nav_aborted', 2, True, True) == DEFER


def test_ladder_skips_unavailable_steps_and_respects_global_limits():
    ladder = HealingLadder(look_around_after=1, track_back_after=1, help_after=5, max_heals=3)
    ladder.start(0.)
    assert ladder.failure(1., 'x', 5, False, False) == DEFER
    assert ladder.failure(2., 'x', 5, False, False) == DEFER
    assert ladder.failure(3., 'x', 5, False, False) == DEFER
    assert ladder.failure(4., 'x', 5, False, False) == REQUEST_HELP  # max_heals
    stalled = HealingLadder(no_progress_timeout_s=10.)
    stalled.start(0.)
    assert stalled.failure(11., 'x', 1, True, True) == REQUEST_HELP
    with pytest.raises(ValueError):
        HealingLadder(look_around_after=5, track_back_after=2)


def _straight_track(recorder, length, yaw=0.):
    for i in range(int(length/0.02)+1):
        d = i*0.02
        recorder.add((d*math.cos(yaw), d*math.sin(yaw), yaw))


def test_track_back_follows_only_the_straight_recent_own_track():
    track = TrackRecorder()
    _straight_track(track, 1.0)
    pose = track.points[-1]
    assert track.straight_back_distance(pose, .4) == pytest.approx(.4)
    assert track.straight_back_distance(pose, 2.) == pytest.approx(1.0, abs=.021)
    # After an in-place turn the old track is no longer straight behind.
    turned = (pose[0], pose[1], math.pi/2)
    assert track.straight_back_distance(turned, .4) == 0.
    # A curve limits the distance to the straight recent segment.
    curve = TrackRecorder()
    for i in range(30):
        a = i*0.05
        curve.add((math.sin(a), 1-math.cos(a), a))
    end = curve.points[-1]
    assert 0. < curve.straight_back_distance(end, .4) < .4
    # No recorded motion -> no reversal authority.
    assert TrackRecorder().straight_back_distance((0., 0., 0.), .4) == 0.


def test_track_back_rejects_track_ahead_and_consumes_used_segment():
    track = TrackRecorder()
    _straight_track(track, .6)
    # Robot facing backwards along its track: the track lies AHEAD.
    pose = (track.points[-1][0], track.points[-1][1], math.pi)
    assert track.straight_back_distance(pose, .4) == 0.
    pose = track.points[-1]
    track.consume(.3)
    assert track.points[-1][0] == pytest.approx(.3, abs=.021)


def test_track_recorder_ignores_invalid_and_tiny_motion():
    track = TrackRecorder(spacing_m=.02)
    track.add(None); track.add((float('nan'), 0., 0.)); track.add((0., 0., 0.))
    track.add((0.005, 0., 0.))
    assert len(track.points) == 1


def _grid():
    occupancy = np.full((60, 80), -1, dtype=int)
    occupancy[10:50, 10:40] = 0       # known room
    occupancy[10:50, 10] = 100        # wall
    return occupancy


def _cell_to_world(rows, cols):
    return (cols+.5)*.05, (rows+.5)*.05


def test_frontier_goals_pick_nearest_cell_of_each_cluster_and_honour_blacklist():
    occupancy = _grid()
    goals = frontier_goals(occupancy, .05, _cell_to_world, (1.0, 1.5), min_size_cells=5)
    assert goals and all(occupancy[int(g.y/.05), int(g.x/.05)] == 0 for g in goals)
    first = goals[0]
    again = frontier_goals(occupancy, .05, _cell_to_world, (1.0, 1.5), min_size_cells=5,
                           blacklist=[(first.x, first.y)], blacklist_radius_m=.3)
    assert all(math.dist((g.x, g.y), (first.x, first.y)) > .3 for g in again)
    assert frontier_cells_remaining(occupancy) >= 1


def test_closed_room_has_no_frontiers():
    occupancy = np.full((20, 20), 100, dtype=int)
    occupancy[1:-1, 1:-1] = 0
    assert frontier_goals(occupancy, .05, _cell_to_world, (.5, .5)) == []
    assert frontier_cells_remaining(occupancy) == 0


def test_rotation_blocked_only_by_measured_obstacles_not_unknown():
    costs = np.full((40, 40), -1, dtype=int)
    def to_cell(x, y):
        return int(x/.05), int(y/.05)
    assert rotation_clear(costs, to_cell, .05, (1., 1.), .45)       # unknown is fine
    costs[20, 26] = 100                                             # 0.3 m away
    assert not rotation_clear(costs, to_cell, .05, (1., 1.), .45)
    costs[20, 26] = 99                                              # inflation only
    assert rotation_clear(costs, to_cell, .05, (1., 1.), .45)


def test_unknown_ahead_fraction_looks_only_at_the_corridor_in_front():
    from explore.self_healing import unknown_ahead_fraction
    occupancy = np.zeros((100, 100), dtype=int)          # 5 m x 5 m known
    def to_cell(x, y):
        return np.floor(np.asarray(x)/.05).astype(int), np.floor(np.asarray(y)/.05).astype(int)
    pose = (1.0, 2.5, 0.)                                  # facing +x
    assert unknown_ahead_fraction(occupancy, to_cell, .05, pose) == 0.
    occupancy[:, 30:40] = -1                               # unknown 1.5..2.0 m
    assert unknown_ahead_fraction(occupancy, to_cell, .05, pose) == pytest.approx(.5)
    behind = (1.0, 2.5, math.pi)                           # facing away
    assert unknown_ahead_fraction(occupancy, to_cell, .05, behind) == 0.
    edge = (4.8, 2.5, 0.)                                  # corridor leaves the map
    assert unknown_ahead_fraction(np.zeros((100, 100)), to_cell, .05, edge) > .5
    assert unknown_ahead_fraction(occupancy, to_cell, .05, None) == 1.
