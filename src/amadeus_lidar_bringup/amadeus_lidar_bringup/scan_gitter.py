"""Winkelgitter fuer LaserScan-Vereinheitlichung - bewusst ohne ROS-Import.

Der STL-27L liefert je Umdrehung unterschiedlich viele Strahlen. Karto merkt
sich die Strahlenzahl des ERSTEN verarbeiteten Scans und verwirft danach jeden
Scan mit abweichender Zahl (``LaserRangeFinder::Validate`` gibt false zurueck,
``Mapper::Process`` bricht daraufhin sofort ab). Deshalb wird jeder Scan vor
slam_toolbox auf ein festes Winkelgitter umgesetzt.
"""
import numpy as np


def gitter_indizes(anzahl_ein, winkel_min_ein, inkrement_ein,
                   anzahl_aus, winkel_min_aus, inkrement_aus):
    """Zu jedem Ausgabestrahl den Index des winkelnaechsten Eingabestrahls.

    Bewusst naechster Nachbar und KEINE Interpolation: Zwischen zwei
    benachbarten Strahlen kann eine Tiefenkante liegen (Tuerkante, Moebelrand).
    Ein interpolierter Wert erfindet dort eine Flaeche, die es nicht gibt, und
    genau solche Phantomflaechen sollen nicht in die Karte.

    Der Winkelfehler bleibt dabei unter einem halben Eingabeinkrement, beim
    STL-27L also unter rund 0.083 Grad - deutlich feiner als seine eigene
    Aufloesung von 0.167 Grad.
    """
    if anzahl_ein < 1:
        raise ValueError('Eingabescan ohne Strahlen.')
    if inkrement_ein == 0.0:
        raise ValueError('angle_increment ist 0 - Winkel nicht bestimmbar.')
    if anzahl_aus < 1:
        raise ValueError('Ausgabegitter ohne Strahlen.')

    winkel_aus = winkel_min_aus + np.arange(anzahl_aus) * inkrement_aus
    roh = (winkel_aus - winkel_min_ein) / inkrement_ein
    return np.clip(np.rint(roh).astype(np.int64), 0, anzahl_ein - 1)


def auf_gitter(werte, indizes, fuellwert=float('nan')):
    """Werte per Index umsortieren; leere Eingabe ergibt lauter Fuellwerte."""
    if werte is None or len(werte) == 0:
        return np.full(len(indizes), fuellwert, dtype=np.float32)
    feld = np.asarray(werte, dtype=np.float32)
    sicher = np.clip(indizes, 0, len(feld) - 1)
    return feld[sicher]
