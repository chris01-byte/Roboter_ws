#!/usr/bin/env python3
"""Regressionstest fuer die Knotenzaehlung aus graph_visualization."""

from types import SimpleNamespace
import unittest

from slam_graph_marker import MARKER_ADD, MARKER_SPHERE, zaehle_knoten_marker


MARKER_DELETEALL = 3
MARKER_LINE_LIST = 5


def marker(namespace, marker_type, action=MARKER_ADD):
    return SimpleNamespace(ns=namespace, type=marker_type, action=action)


class MarkerZaehlerTests(unittest.TestCase):
    def test_zaehlt_nur_posegraph_knoten(self):
        markers = [
            marker('', MARKER_SPHERE, MARKER_DELETEALL),
            marker('slam_toolbox', MARKER_SPHERE),
            marker('slam_toolbox', MARKER_SPHERE),
            marker('slam_toolbox_edges', MARKER_LINE_LIST),
            marker('slam_toolbox_edges', MARKER_LINE_LIST),
        ]

        self.assertEqual(zaehle_knoten_marker(markers), 2)

    def test_fremde_kugel_ist_kein_slam_knoten(self):
        markers = [marker('anderer_node', MARKER_SPHERE)]
        self.assertEqual(zaehle_knoten_marker(markers), 0)


if __name__ == '__main__':
    unittest.main()
