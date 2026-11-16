"""EK-1 Teil B (14.11.2026): nur Lücken, in die der Roboter passt.

Eigene Datei, damit die gezielte Testliste des laufenden Auftrags SH-8b
(197 Tests) unverändert bleibt.
"""
import numpy as np

from explore.self_healing import (
    deep_reach_mask, deep_unknown_mask, frontier_cells_remaining, frontier_goals)

RES = 0.01


def _welt(rows, cols):
    return (cols+.5)*RES, (rows+.5)*RES


def _raum():
    """4 x 3 m bekannt frei, 2-cm-Wand ringsum, außen unbekannt."""
    grid = np.full((340, 440), -1, dtype=np.int16)
    grid[20:320, 20:420] = 0
    grid[18:20, 18:422] = 100
    grid[320:322, 18:422] = 100
    grid[18:322, 18:20] = 100
    grid[18:322, 420:422] = 100
    return grid


def test_off_by_default_returns_none_and_keeps_selection_unchanged():
    grid = _raum()
    grid[150:152, 420:422] = -1                       # Loch in der Wand
    assert deep_unknown_mask(grid, RES, 0.0) is None
    ohne = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=1)
    mit_none = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=1, deep=None)
    assert [(g.x, g.y, g.cost) for g in ohne] == [(g.x, g.y, g.cost) for g in mit_none]


def test_door_counts_wall_hole_thin_wedge_and_strip_do_not():
    grid = _raum()
    grid[110:190, 420:422] = -1                       # Tür 0,80 m in der rechten Wand
    grid[60:62, 18:20] = -1                           # 2-cm-Loch in der linken Wand
    grid[200:204, 100:300] = -1                       # 4 cm breiter Schattenkeil, 2 m lang
    grid[20:22, 150:300] = -1                         # 2-cm-Streifen vor der unteren Wand
    deep = deep_unknown_mask(grid, RES, 0.25)
    assert deep is not None and deep.dtype == bool and deep.shape == grid.shape
    # Das Unbekannte hinter der Tür ist tief, Keil und Streifen sind es nicht.
    assert deep[150, 430] and not deep[202, 200] and not deep[21, 200]
    alle = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30)
    tiefe = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30, deep=deep)
    assert len(alle) >= 3                              # Keil und Streifen zählen bisher mit
    assert len(tiefe) == 1
    ziel = tiefe[0]
    assert abs(ziel.frontier_xy[0] - 4.195) < 0.02 and 1.1 <= ziel.frontier_xy[1] <= 1.9
    # Die Kosten rechnen nur die tiefe Länge an (Türbreite), nicht den Keil.
    assert 0.6 <= ziel.size_cells*RES <= 0.85
    assert frontier_cells_remaining(grid, 30) >= 3
    assert frontier_cells_remaining(grid, 30, deep=deep) == 1


def test_gap_narrower_than_the_robot_is_ignored_wider_one_counts():
    for breite_cm, erwartet in ((30, 0), (60, 1)):
        grid = _raum()
        # Nische in der oberen Wand: breite_cm breit, dahinter 1 m unbekannt
        # zwischen zwei bekannten Wänden (z. B. Spalt zwischen Schränken).
        links = 200 - breite_cm//2
        grid[320:322, links:links+breite_cm] = -1
        grid[322:340, 18:links] = 100
        grid[322:340, links+breite_cm:422] = 100
        deep = deep_unknown_mask(grid, RES, 0.25)
        assert frontier_cells_remaining(grid, 20, deep=deep) == erwartet, breite_cm


def test_unknown_at_the_map_border_counts_as_deep():
    grid = np.zeros((200, 200), dtype=np.int16)        # ganz frei bis zum Kartenrand
    grid[:, 190:] = -1                                 # 10 cm unbekannt am Rand
    deep = deep_unknown_mask(grid, RES, 0.25)
    assert deep[100, 195]                              # außerhalb geht es unbekannt weiter
    assert frontier_cells_remaining(grid, 30, deep=deep) == 1


def test_fully_known_or_tiny_maps_do_not_crash():
    assert not deep_unknown_mask(np.zeros((5, 5), dtype=np.int16), RES, 0.25).any()
    assert deep_unknown_mask(np.zeros((0, 0), dtype=np.int16), RES, 0.25) is None
    assert deep_unknown_mask(np.full((3, 3), -1, dtype=np.int16), RES, 0.25).all()


def _raum_mit_ausgefranster_tuer():
    """Tür 0,80 m in der rechten Wand; dahinter ein ausgefranster Strahlenkamm.

    Wie in der echten 1-cm-Karte am Rand eines Sichtschattens: Hinter der
    Öffnung liegen einzelne Strahlen frei (jede zweite Zeile), unterschiedlich
    weit (2 bis 10 cm), dazwischen bleibt es unbekannt. Nur wenige Strahlen
    reichen bis an das tiefe Unbekannte.
    """
    grid = _raum()
    grid[110:190, 420:422] = 0                        # Türöffnung, frei gesehen
    for nummer, zeile in enumerate(range(110, 190, 2)):
        grid[zeile, 422:422 + 2 + (nummer*7) % 9] = 0  # Strahl, 2 bis 10 cm lang
    return grid


def test_ragged_edge_in_front_of_deep_unknown_still_counts_as_a_door():
    """Simulation 16.11.2026: Fahrt „vollständig“ mit halbem Flur, weil die Tür durchfiel."""
    grid = _raum_mit_ausgefranster_tuer()
    deep = deep_unknown_mask(grid, RES, 0.25)
    # Streng: Nur die längsten Strahlen berühren das tiefe Unbekannte; das reicht nicht.
    assert frontier_cells_remaining(grid, 30, deep=deep) == 0
    assert frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30, deep=deep) == []
    # Mit Rand 5 cm durch Unbekanntes: Die Tür zählt wieder.
    nah = deep_reach_mask(grid, deep, RES, 0.05)
    assert nah.dtype == bool and nah.shape == grid.shape and (nah | ~deep).all()
    assert not nah[grid >= 0].any()                   # wächst nur durch unbekannte Zellen
    assert nah[151, 430] and not nah[151, 423]        # nur die letzten 5 cm vor dem Tiefen
    assert frontier_cells_remaining(grid, 30, deep=nah) == 1
    (ziel,) = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30, deep=nah)
    assert ziel.frontier_xy[0] > 4.2 and 1.1 <= ziel.frontier_xy[1] <= 1.9
    # Eine durchgehend frei gesehene Linie trennt: Dahinter beginnt eine neue Frontier,
    # der Rand davor zählt nicht mehr zum tiefen Unbekannten.
    getrennt = _raum_mit_ausgefranster_tuer()
    getrennt[:, 436] = 0
    tief = deep_unknown_mask(getrennt, RES, 0.25)
    nah = deep_reach_mask(getrennt, tief, RES, 0.05)
    assert tief[150, 438] and nah[150, 438] and not nah[150, 434]


def test_reach_does_not_bring_back_strips_wedges_or_wall_holes():
    grid = _raum()
    grid[110:190, 420:422] = -1                       # Tür 0,80 m in der rechten Wand
    grid[60:62, 18:20] = -1                           # 2-cm-Loch in der linken Wand
    grid[200:204, 100:300] = -1                       # 4 cm breiter Schattenkeil, 2 m lang
    grid[20:22, 150:300] = -1                         # 2-cm-Streifen vor der unteren Wand
    deep = deep_unknown_mask(grid, RES, 0.25)
    nah = deep_reach_mask(grid, deep, RES, 0.05)
    # Der Streifen liegt 2 cm vor der Wand, das Unbekannte 2 cm dahinter: durch die
    # belegte Wand wächst die Maske nicht.
    assert not nah[21, 200] and not nah[202, 200]
    tiefe = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30, deep=nah)
    assert len(tiefe) == 1 and abs(tiefe[0].frontier_xy[0] - 4.195) < 0.02
    assert frontier_cells_remaining(grid, 30, deep=nah) == 1
    # Das Loch in der 2 cm dicken Wand zählt gar nicht: dicht an Belegtem wächst nichts.
    assert frontier_cells_remaining(grid, 3, deep=nah) == 1
    assert frontier_cells_remaining(grid, 2, deep=nah) == 1
    assert frontier_cells_remaining(grid, 2, deep=deep_reach_mask(grid, deep, RES, 0.05,
                                                                  wall_guard_m=0.0)) == 2


def test_ragged_furniture_front_with_unknown_behind_is_not_an_opening():
    """Simulation 16.11.2026: Lücken einer Regalfront zählten als Öffnung, Amadeus saß fest."""
    grid = _raum()
    # Regal an der linken Wand, 0,4 m tief und 1,6 m lang: Der LiDAR sieht nur die Front
    # (2 cm dick, jede dritte Zelle fehlt), dahinter ist alles unbekannt bis nach draußen.
    grid[60:220, 18:60] = -1
    grid[60:220, 58:60] = 100
    grid[58:60, 18:60] = 100                           # Seitenwände des Regals
    grid[220:222, 18:60] = 100
    grid[63:218:3, 58:60] = -1
    grid[63:218:3, 60:62] = -1                         # und davor je ein unbekannter Fleck
    deep = deep_unknown_mask(grid, RES, 0.25)
    assert deep[140, 40]                               # hinter der Front ist es tief
    assert frontier_cells_remaining(grid, 30, deep=deep) == 0      # streng: keine Öffnung
    ohne_wandabstand = deep_reach_mask(grid, deep, RES, 0.05, wall_guard_m=0.0)
    mit_wandabstand = deep_reach_mask(grid, deep, RES, 0.05)
    assert frontier_cells_remaining(grid, 30, deep=ohne_wandabstand) >= 1
    assert frontier_cells_remaining(grid, 30, deep=mit_wandabstand) == 0
    assert frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30,
                          deep=mit_wandabstand) == []
    # Die Tür daneben zählt weiter.
    grid[110:190, 420:422] = -1
    tief = deep_unknown_mask(grid, RES, 0.25)
    (ziel,) = frontier_goals(grid, RES, _welt, (1.0, 1.5), min_size_cells=30,
                             deep=deep_reach_mask(grid, tief, RES, 0.05))
    assert abs(ziel.frontier_xy[0] - 4.195) < 0.02


def test_reach_zero_or_missing_mask_changes_nothing():
    grid = _raum_mit_ausgefranster_tuer()
    deep = deep_unknown_mask(grid, RES, 0.25)
    assert deep_reach_mask(grid, deep, RES, 0.0) is deep
    assert deep_reach_mask(grid, deep, RES, 0.004) is deep       # unter einer halben Zelle
    assert deep_reach_mask(grid, None, RES, 0.05) is None
