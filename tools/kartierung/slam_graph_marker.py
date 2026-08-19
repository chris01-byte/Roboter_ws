#!/usr/bin/env python3
"""Kleine, ROS-unabhaengig testbare Helfer fuer slam_toolbox-Marker."""


# visualization_msgs/msg/Marker-Konstanten. Bewusst lokal gespiegelt, damit die
# Filterlogik auch auf einem Entwicklungsrechner ohne ROS getestet werden kann.
MARKER_ADD = 0
MARKER_SPHERE = 2


def zaehle_knoten_marker(markers):
    """Zaehlt nur Posegraph-Knoten, nicht Verwaltungs- oder Kantenmarker."""
    return sum(
        marker.ns == 'slam_toolbox'
        and marker.type == MARKER_SPHERE
        and marker.action == MARKER_ADD
        for marker in markers
    )
