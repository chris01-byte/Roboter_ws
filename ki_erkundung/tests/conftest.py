"""Gemeinsame Vorbereitung der Tests der KI-Erkundung.

Die Tests brauchen weder Roboter noch KI-Rechner noch echte Wohnungsdaten.
Blickrunden kommen aus der künstlichen Beispielwelt.
"""
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
for pfad in (WURZEL, WURZEL / 'werkzeuge', WURZEL / 'tests'):
    if str(pfad) not in sys.path:
        sys.path.insert(0, str(pfad))


@pytest.fixture(scope='session')
def beispielordner(tmp_path_factory):
    """Ordner mit einer künstlichen Blickrunde (einmal je Testlauf erzeugt)."""
    import beispielrunde_erzeugen
    wurzel = tmp_path_factory.mktemp('blickrunden')
    beispielrunde_erzeugen.erzeuge(wurzel, 'beispiel_zimmer')
    return wurzel


@pytest.fixture(scope='session')
def beispielrunde(beispielordner):
    from lotse.blickrunde import Blickrunde
    return Blickrunde.lade(beispielordner / 'beispiel_zimmer')


@pytest.fixture
def ki_attrappe():
    """Gespielter KI-Rechner auf 127.0.0.1 (siehe ki_attrappe.py)."""
    from ki_attrappe import Attrappe
    attrappe = Attrappe()
    yield attrappe
    attrappe.schliessen()
