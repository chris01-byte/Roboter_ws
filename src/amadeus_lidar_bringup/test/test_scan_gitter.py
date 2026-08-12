#!/usr/bin/env python3
"""Regressionstest fuer die Winkelabbildung - laeuft ohne ROS.

Aufruf:  python3 src/amadeus_lidar_bringup/test/test_scan_gitter.py
"""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from amadeus_lidar_bringup.scan_gitter import auf_gitter, gitter_indizes  # noqa: E402

VOLLKREIS = 2.0 * math.pi


def inkrement(anzahl):
    """So rechnet der Treiber: (N-1) * increment ergibt genau 360 Grad."""
    return VOLLKREIS / (anzahl - 1)


class WinkeltreueTest(unittest.TestCase):

    def test_gleiche_groesse_ist_identitaet(self):
        n = 2160
        idx = gitter_indizes(n, 0.0, inkrement(n), n, 0.0, inkrement(n))
        np.testing.assert_array_equal(idx, np.arange(n))

    def test_winkelfehler_bleibt_unter_halbem_inkrement(self):
        """Der Kern: jeder Ausgabestrahl trifft den winkelnaechsten Eingang."""
        for anzahl_ein in (2146, 2159, 2172, 2176):
            inc_ein = inkrement(anzahl_ein)
            anzahl_aus = 2160
            inc_aus = inkrement(anzahl_aus)
            idx = gitter_indizes(anzahl_ein, 0.0, inc_ein,
                                 anzahl_aus, 0.0, inc_aus)
            winkel_aus = np.arange(anzahl_aus) * inc_aus
            winkel_getroffen = idx * inc_ein
            fehler = np.abs(winkel_aus - winkel_getroffen)
            self.assertLessEqual(
                float(fehler.max()), inc_ein / 2.0 + 1e-12,
                f'Bei {anzahl_ein} Eingabestrahlen wurde ein Strahl weiter '
                f'als ein halbes Inkrement daneben zugeordnet.')

    def test_indizes_bleiben_im_gueltigen_bereich(self):
        for anzahl_ein in (2, 100, 2146, 2176):
            idx = gitter_indizes(anzahl_ein, 0.0, inkrement(anzahl_ein),
                                 2160, 0.0, inkrement(2160))
            self.assertGreaterEqual(int(idx.min()), 0)
            self.assertLess(int(idx.max()), anzahl_ein)

    def test_maskierte_strahlen_bleiben_ungueltig(self):
        """NaN aus der Mastmaske darf nie zu einer Messung werden."""
        anzahl_ein = 2172
        werte = np.full(anzahl_ein, 2.5, dtype=np.float32)
        # Mastsektor 236..304 Grad wie in stl27l.yaml
        inc_grad = 360.0 / (anzahl_ein - 1)
        von, bis = int(236.0 / inc_grad), int(304.0 / inc_grad)
        werte[von:bis + 1] = np.nan

        idx = gitter_indizes(anzahl_ein, 0.0, inkrement(anzahl_ein),
                             2160, 0.0, inkrement(2160))
        raus = auf_gitter(werte, idx)

        self.assertTrue(np.isnan(raus).any(), 'Maske komplett verschwunden.')
        anteil_ein = float(np.isnan(werte).mean())
        anteil_aus = float(np.isnan(raus).mean())
        self.assertAlmostEqual(anteil_ein, anteil_aus, delta=0.005)

    def test_keine_interpolation_nur_vorhandene_werte(self):
        """Ausgabewerte muessen echte Eingabewerte sein, keine Mischungen."""
        anzahl_ein = 2176
        werte = np.arange(anzahl_ein, dtype=np.float32)
        idx = gitter_indizes(anzahl_ein, 0.0, inkrement(anzahl_ein),
                             2160, 0.0, inkrement(2160))
        raus = auf_gitter(werte, idx)
        self.assertTrue(np.all(np.isin(raus, werte)))

    def test_leere_eingabe_wird_abgelehnt(self):
        with self.assertRaises(ValueError):
            gitter_indizes(0, 0.0, 0.001, 2160, 0.0, 0.001)
        with self.assertRaises(ValueError):
            gitter_indizes(2160, 0.0, 0.0, 2160, 0.0, 0.001)


if __name__ == '__main__':
    unittest.main(verbosity=2)
