"""EK-1 Teil B (14.11.2026): nur Lücken, in die der Roboter passt.

Eigene Datei, damit die gezielte Testliste des laufenden Auftrags SH-8b
(197 Tests) unverändert bleibt.
"""
import numpy as np

from explore.self_healing import (
    deep_unknown_mask, frontier_cells_remaining, frontier_goals)

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
