"""Pure self-healing decisions: taxonomy, ladder, own-track reversal, frontiers."""
import math

import numpy as np
import pytest

from explore.self_healing import (
    FATAL, HEAL, WAIT, classify,
    HealingLadder, RETRY, DEFER, LOOK_AROUND, TRACK_BACK, REQUEST_HELP,
    TrackRecorder, frontier_goals, frontier_cells_remaining, obstacle_clearance,
    reachable_goal_mask, rotation_clear)


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


def test_blocked_turn_backs_out_at_once_at_most_twice_per_progress():
    """DR-1 (Simulation 03.11.2026): Drehsperre am Ort, nicht am Ziel."""
    ladder = HealingLadder(goal_retries=1, look_around_after=3, track_back_after=5, help_after=8)
    ladder.start(0.)
    assert ladder.failure(1., 'nav_aborted', 1, True, False, turn_blocked=True) == TRACK_BACK
    # Entscheidung 03.11.2026: höchstens zwei Rückfahrten je Stillstand.
    assert ladder.failure(2., 'nav_aborted', 1, True, False, turn_blocked=True) == TRACK_BACK
    assert ladder.failure(3., 'nav_aborted', 1, True, False, turn_blocked=True) == RETRY
    assert ladder.snapshot()['track_backs_in_streak'] == 2
    ladder.progress(4.)
    assert ladder.track_backs_in_streak == 0
    assert ladder.failure(5., 'nav_aborted', 2, True, False, turn_blocked=True) == TRACK_BACK
    # Ohne Rückfahrt oder mit freiem Drehkreis bleibt alles wie bisher.
    fresh = HealingLadder()
    fresh.start(0.)
    assert fresh.failure(1., 'nav_aborted', 1, False, False, turn_blocked=True) == RETRY
    assert fresh.failure(2., 'nav_aborted', 1, True, True) == RETRY
    # Globale Grenzen gehen vor.
    limited = HealingLadder(max_heals=1)
    limited.start(0.)
    limited.failure(1., 'x', 2, False, False)
    assert limited.failure(2., 'x', 1, True, False, turn_blocked=True) == REQUEST_HELP

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


def test_turn_on_the_spot_since_the_track_can_be_undone():
    track = TrackRecorder()
    _straight_track(track, .6)
    x, y, yaw = track.points[-1]
    turned = (x, y, yaw - .4)
    assert track.straight_back_distance(turned, .4) == 0.
    turn = track.turn_since_track(turned, .8)
    assert turn == pytest.approx(-.4)
    undone = (x, y, turned[2] - turn)
    assert track.straight_back_distance(undone, .4) == pytest.approx(.4)
    # Weggefahren, zu weit gedreht oder ohne Spur: keine Aussage.
    assert track.turn_since_track((x+.05, y, yaw-.4), .8) is None
    assert track.turn_since_track((x, y, yaw-1.), .8) is None
    assert track.turn_since_track((x, y, float('nan')), .8) is None
    assert track.turn_since_track((x, y, yaw), math.pi) is None
    assert TrackRecorder().turn_since_track((0., 0., 0.), .8) is None
    # Winkel über die Sprungstelle +-pi hinweg.
    back = TrackRecorder()
    _straight_track(back, .3, yaw=math.pi-.1)
    bx, by, byaw = back.points[-1]
    assert back.turn_since_track((bx, by, -math.pi+.1), .8) == pytest.approx(.2)

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


def _two_rooms(door_m, res=.05):
    """Links bekannter Raum, rechts durch die Tür teilweise gesehen (Frontier)."""
    n = int(round(3./res))
    occupancy = np.full((n, 2*n), -1, dtype=int)
    occupancy[:, :n] = 0                                  # linker Raum bekannt frei
    occupancy[:, n:n+n//2] = 0                            # rechter Raum halb gesehen
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = 100
    occupancy[:, n] = 100                                 # Trennwand bei x = 3 m
    if door_m:
        half = int(round(door_m/2/res))
        occupancy[n//2-half:n//2+half, n] = 0
    return occupancy


def test_closed_door_makes_the_far_frontier_unreachable_but_an_open_door_does_not():
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    robot = (30, 30)                                      # (Zeile, Spalte) = (1,5 m / 1,5 m)
    for door_m, erreichbar in ((0., False), (.30, False), (.68, True), (.8, True)):
        occupancy = _two_rooms(door_m)
        allowed = reachable_goal_mask(occupancy, .05, robot)
        goals = frontier_goals(occupancy, .05, to_world, (1.5, 1.5), allowed=allowed)
        assert bool(goals) is erreichbar, door_m
        assert frontier_goals(occupancy, .05, to_world, (1.5, 1.5))   # ohne Prüfung immer da


def test_reachability_tolerates_a_start_next_to_a_post_and_crosses_unknown():
    occupancy = _two_rooms(.8)
    n = 60
    # Roboter 0,15 m neben dem Türpfosten: innerhalb des Sperrsaums, aber frei.
    robot = (n//2+8+3, n-3)
    allowed = reachable_goal_mask(occupancy, .05, robot)
    assert allowed[n//2, n+20]                            # rechter Raum erreichbar
    # Unbekanntes ist passierbar wie mit Nav2 allow_unknown.
    unknown = np.full((40, 40), -1, dtype=int)
    unknown[:, :10] = 0
    assert reachable_goal_mask(unknown, .05, (20, 5))[20, 35]
    # Außerhalb der Karte keine Aussage.
    assert reachable_goal_mask(unknown, .05, (50, 5)) is None


def test_reachability_on_a_fine_slam_grid_matches_the_coarse_result():
    coarse = _two_rooms(0.)
    fine = np.repeat(np.repeat(coarse, 5, axis=0), 5, axis=1)   # 1-cm-Karte wie am Roboter
    allowed = reachable_goal_mask(fine, .01, (150, 150))
    assert allowed.shape == fine.shape
    assert allowed[150, 100] and not allowed[150, 400]


def _door_frontier(door_m, res=.05):
    """Bekannter Raum links, Tür bei x = 1,5 m, dahinter unbekannt (Frontier quer zur Tür)."""
    occupancy = np.full((60, 60), -1, dtype=int)
    occupancy[:, :30] = 0
    occupancy[0, :30] = occupancy[-1, :30] = occupancy[:, 0] = 100
    occupancy[:, 30] = 100
    half = int(round(door_m/2/res))
    occupancy[30-half:30+half, 30] = 0                  # Türöffnung, Pfosten bei y = 1,5 ± door/2
    occupancy[30-half:30+half, 31] = 0                  # erste Zelle hinter der Tür gesehen
    return occupancy


def test_door_frontier_goal_moves_from_the_post_corner_to_the_door_middle():
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    robot = (1.2, 1.0)                                  # schräg vor dem unteren Pfosten
    occupancy = _door_frontier(.8)
    plain = frontier_goals(occupancy, .05, to_world, robot, min_size_cells=3)
    room = obstacle_clearance(occupancy, .05)
    wide = frontier_goals(occupancy, .05, to_world, robot, min_size_cells=3,
                          clearance=room, goal_clearance_m=.45)
    assert len(plain) == len(wide) == 1                 # kein Cluster fällt weg
    pfosten_y = 1.5 - .4
    assert abs(plain[0].y - pfosten_y) < .1             # bisher: direkt an der Pfostenecke
    assert abs(wide[0].y - 1.5) <= .1                   # jetzt: Türmitte
    # 0,68-m-Tür: keine Zelle hat 0,35 m, dann die geräumigste (Mitte).
    narrow = _door_frontier(.68)
    goal = frontier_goals(narrow, .05, to_world, robot, min_size_cells=3,
                          clearance=obstacle_clearance(narrow, .05), goal_clearance_m=.45)[0]
    assert abs(goal.y - 1.5) <= .1


def test_obstacle_clearance_never_overestimates_on_a_fine_grid():
    from scipy.ndimage import distance_transform_edt
    fine = np.repeat(np.repeat(_door_frontier(.8), 5, axis=0), 5, axis=1)   # 1-cm-Karte
    grob = obstacle_clearance(fine, .01)
    genau = distance_transform_edt(fine < 65)*.01
    assert grob.shape == fine.shape
    assert np.all(grob <= genau + 1e-9)
    assert np.max(genau - grob) <= 2*.05*math.sqrt(2) + .01


def test_wall_hugging_frontier_goal_moves_to_a_standable_cell():
    """Frontier nur entlang einer Wand (Simulation: Ziel 6 cm vor der Wand)."""
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((40, 60), 0, dtype=int)
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = occupancy[:, -1] = 100
    occupancy[1:3, 20:30] = -1                      # ungesehener Wandfuß unten
    room = obstacle_clearance(occupancy, .05)
    plain = frontier_goals(occupancy, .05, to_world, (1.0, 1.0), min_size_cells=3,
                           clearance=room, goal_clearance_m=.45)[0]
    shifted = frontier_goals(occupancy, .05, to_world, (1.0, 1.0), min_size_cells=3,
                             clearance=room, goal_clearance_m=.45, goal_shift_max_m=.5)[0]
    assert plain.y < .25                            # ohne Verschieben dicht an der Wand
    assert room[int(shifted.y/.05), int(shifted.x/.05)] >= .45
    assert math.dist((plain.x, plain.y), (shifted.x, shifted.y)) <= .5
    # Zurückgestellt wird die Frontier-Stelle, nicht der verschobene Fahrpunkt.
    assert math.dist(shifted.frontier_xy, (plain.x, plain.y)) < 1e-9
    again = frontier_goals(occupancy, .05, to_world, (1.0, 1.0), min_size_cells=3,
                           clearance=room, goal_clearance_m=.45, goal_shift_max_m=.5,
                           blacklist=[shifted.frontier_xy], blacklist_radius_m=.2)
    assert all(math.dist(g.frontier_xy, shifted.frontier_xy) > .2 for g in again)


def test_corner_goal_moves_to_the_most_spacious_nearby_cell_if_none_is_wide_enough():
    """Simulation v3: Ziel blieb an der Pfostenecke, weil im Umkreis keine Zelle 0,45 m hatte."""
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((24, 40), 0, dtype=int)             # schmaler Raum, 1,2 m breit
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = occupancy[:, -1] = 100
    occupancy[1:3, 30:38] = -1                              # ungesehener Wandfuß unten rechts
    room = obstacle_clearance(occupancy, .05)
    goal = frontier_goals(occupancy, .05, to_world, (.5, .6), min_size_cells=3,
                          clearance=room, goal_clearance_m=.8, goal_shift_max_m=.5)[0]
    frontier_room = room[2, 30:38].max()
    assert room[int(goal.y/.05), int(goal.x/.05)] > frontier_room   # geräumiger als am Wandfuß
    assert goal.y > .25                                       # weg von der Wand


def _sees(occupancy, a, b, res=.05):
    """Prüfhilfe: freie Sicht zwischen zwei Weltpunkten über bekannt freie Zellen."""
    n = int(math.dist(a, b)/res*4)+2
    return all(occupancy[int((a[1]+(b[1]-a[1])*t)/res), int((a[0]+(b[0]-a[0])*t)/res)] == 0
               for t in np.linspace(0, 1, n))


def test_goal_at_a_too_narrow_gap_moves_where_the_robot_can_turn_and_still_sees_it():
    """DR-1 (Simulation 03.11.2026): Ziel in der Mündung einer 0,42-m-Lücke,
    0,25 m vor der Blockecke; dort war keine Drehung frei, der Roboter blieb
    stehen bis „Hilfe benötigt“. Im Umkreis von 1 m gab es Stellen mit 0,5 m."""
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((60, 80), 0, dtype=int)
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = occupancy[:, -1] = 100
    occupancy[1:22, 50:56] = 100                 # Insel bis y = 1,10 m
    occupancy[30:59, 50:56] = 100                # Block ab y = 1,50 m: Lücke 0,40 m
    occupancy[22:30, 51:79] = -1                 # in die Lücke noch nicht hineingesehen
    room = obstacle_clearance(occupancy, .05, unknown_blocks=True)
    robot = (1.0, 1.3)
    near = frontier_goals(occupancy, .05, to_world, robot, min_size_cells=3,
                          clearance=room, goal_clearance_m=.45, goal_shift_max_m=.5)[0]
    far = frontier_goals(occupancy, .05, to_world, robot, min_size_cells=3,
                         clearance=room, goal_clearance_m=.45, goal_shift_max_m=1.0)[0]
    at = lambda g: room[int(g.y/.05), int(g.x/.05)]
    assert at(near) < .45                        # bisher: eng, keine Drehung möglich
    assert at(far) >= .45                        # jetzt: Drehraum
    assert math.dist((far.x, far.y), far.frontier_xy) <= 1.0
    assert _sees(occupancy, (far.x, far.y), far.frontier_xy)


def test_frontier_seen_only_from_a_cramped_strip_gets_no_goal_with_a_minimum():
    """DR-1 (Simulation 03.11.2026): Notziel 0,36 m vor der Insel im 0,91-m-
    Streifen hinter der 0,68-m-Tür; dort keine Drehung frei, „Hilfe benötigt“.

    Mit Mindestabstand bekommt eine Frontier, die nur aus einem engen Streifen
    sichtbar ist, kein Ziel; ohne Mindestabstand bleibt das alte Notziel.
    """
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((40, 60), 100, dtype=int)
    occupancy[5:35, 2:20] = 0                    # Raum links, geräumig
    occupancy[18:22, 20:40] = 0                  # 0,2 m schmaler Gang nach rechts
    occupancy[18:22, 40:44] = -1                 # am Gangende ungesehen
    room = obstacle_clearance(occupancy, .05, unknown_blocks=True)
    common = dict(min_size_cells=2, clearance=room, goal_clearance_m=.45, goal_shift_max_m=1.0)
    old = frontier_goals(occupancy, .05, to_world, (.5, 1.0), **common)
    assert len(old) == 1 and room[int(old[0].y/.05), int(old[0].x/.05)] < .45
    known = obstacle_clearance(occupancy, .05)
    new = frontier_goals(occupancy, .05, to_world, (.5, 1.0), goal_min_clearance_m=.45,
                         min_clearance=known, **common)
    assert new == []
    # Mit Drehraum in Sichtweite bleibt das Ziel erhalten.
    wide = occupancy.copy()
    wide[5:35, 20:40] = 0                        # Gang zur Halle geöffnet
    roomy = obstacle_clearance(wide, .05, unknown_blocks=True)
    kept = frontier_goals(wide, .05, to_world, (.5, 1.0), goal_min_clearance_m=.45,
                          min_clearance=obstacle_clearance(wide, .05),
                          **dict(common, clearance=roomy))
    assert kept and all(obstacle_clearance(wide, .05)[int(g.y/.05), int(g.x/.05)] >= .45
                        for g in kept)


def test_scattered_unseen_cells_do_not_block_every_goal_at_the_start():
    """Simulation 03.11.2026 (e41507b): Auf der Startkarte liegen zwischen den
    Strahlen einzelne unbekannte Zellen; als Hindernis gezählt hatte kein Punkt
    mehr als 0,31 m, 0 Ziele, Mission sofort zu Ende."""
    to_world = lambda rows, cols: ((cols+.5)*.01, (rows+.5)*.01)
    occupancy = np.full((300, 300), -1, dtype=int)
    occupancy[20:280, 20:200] = 0                # gesehener Raum, 1-cm-Raster
    occupancy[20:280, 20] = occupancy[20, 20:200] = occupancy[279, 20:200] = 100
    rng = np.random.default_rng(3)
    holes = rng.random((260, 180)) < .02         # Strahllücken mitten im Raum
    occupancy[20:280, 20:200][holes & (occupancy[20:280, 20:200] == 0)] = -1
    unknown = obstacle_clearance(occupancy, .01, unknown_blocks=True)
    known = obstacle_clearance(occupancy, .01)
    common = dict(min_size_cells=20, clearance=unknown, goal_clearance_m=.45,
                  goal_shift_max_m=1.0, goal_min_clearance_m=.45)
    assert frontier_goals(occupancy, .01, to_world, (1.0, 1.5), **common) == []   # Fehler
    goals = frontier_goals(occupancy, .01, to_world, (1.0, 1.5), min_clearance=known, **common)
    assert goals and all(known[int(g.y/.01), int(g.x/.01)] >= .45 for g in goals)


def test_shifted_goal_never_jumps_behind_a_wall_it_cannot_see_through():
    """Frontier in einem schmalen Streifen; geräumig ist es nur hinter der Wand.

    Ohne Sichtprüfung lag das verschobene Ziel auf der anderen Seite (offline
    nachgerechnet: 0,78 m hinter der Insel); der Roboter hätte die Frontier
    von dort nie gesehen.
    """
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((60, 80), 0, dtype=int)
    occupancy[0, :] = occupancy[-1, :] = occupancy[:, 0] = occupancy[:, -1] = 100
    occupancy[0:41, 30] = 100                    # Wand A, unten offen
    occupancy[:, 40] = 100                       # Wand B trennt die rechte Halle ganz ab
    occupancy[5:9, 32:39] = -1                   # ungesehen oben im 0,45-m-Streifen
    room = obstacle_clearance(occupancy, .05, unknown_blocks=True)
    goal = frontier_goals(occupancy, .05, to_world, (1.0, 2.5), min_size_cells=3,
                          clearance=room, goal_clearance_m=.45, goal_shift_max_m=1.0)[0]
    assert goal.x < 40*.05                       # diesseits von Wand B
    assert _sees(occupancy, (goal.x, goal.y), goal.frontier_xy)
    assert room[int(goal.y/.05), int(goal.x/.05)] >= room[int(goal.frontier_y/.05),
                                                          int(goal.frontier_x/.05)]

def test_unseen_wall_base_does_not_count_as_turning_room():
    """Simulation (X9, v3): Wandfuß der Verbindung noch unbekannt, Ziel 6 cm davor."""
    to_world = lambda rows, cols: ((cols+.5)*.05, (rows+.5)*.05)
    occupancy = np.full((40, 60), -1, dtype=int)
    occupancy[12:29, :] = 0                          # 0,84-m-Verbindung bekannt frei
    occupancy[29, :] = 100                           # obere Wand gesehen
    occupancy[11, :] = -1                            # unterer Wandfuß noch unbekannt
    alt = obstacle_clearance(occupancy, .05)
    neu = obstacle_clearance(occupancy, .05, unknown_blocks=True)
    assert alt[12, 30] > .4                          # bisher: am ungesehenen Fuß "geräumig"
    assert neu[12, 30] == 0.                         # jetzt: kein Drehraum
    goal = frontier_goals(occupancy, .05, to_world, (.5, 1.0), min_size_cells=3,
                          clearance=neu, goal_clearance_m=.45, goal_shift_max_m=.5)[0]
    assert .2 < goal.y - 12*.05                      # mindestens 0,2 m vom unbekannten Fuß

