"""Lotsen-Dienst: Ablage der letzten Fragen mit Bildern für das Fenster.

Ohne ROS: Der Dienst wird ohne Knoten gebaut, nur die Ablage wird geprüft.
"""
import collections
import json
import threading
from pathlib import Path

from lotse.frage import Frage
from lotse_dienst import ABLAGE_MUSTER, FRAGEN_BEHALTEN, Dienst, ablage_name
from lotse_fenster import ABLAGE_MUSTER as ABLAGE_MUSTER_FENSTER
from lotse_fenster import BILD_PFAD


class Protokoll:
    def __init__(self):
        self.warnungen = []

    def warning(self, text):
        self.warnungen.append(text)


class Knoten:
    def __init__(self):
        self.protokoll = Protokoll()

    def get_logger(self):
        return self.protokoll


def dienst_ohne_ros(ordner: Path) -> Dienst:
    dienst = Dienst.__new__(Dienst)
    dienst.knoten = Knoten()
    dienst._sperre = threading.Lock()
    dienst._verlauf = collections.deque(maxlen=30)
    dienst._fragen = collections.deque(maxlen=FRAGEN_BEHALTEN)
    dienst._zustand_ordner = ordner
    dienst.schreibe_zustand = lambda: None
    return dienst


def frage(nr: int) -> Frage:
    return Frage(system='s', text=f'Frage {nr}', schema={}, angeboten=[1, 2])


def test_ablage_name_ist_sicher_und_passt_zum_fenster():
    assert ablage_name(1795275511.8, '5a4fe9ee-1234') == '1795275511800_5a4fe9ee1234'
    assert ablage_name(1.0, '../../etc') == '1000_etc'
    assert ablage_name(1.0, None) == '1000_frage'
    assert ablage_name(1.0, 'ä/ö') == '1000_frage'
    assert ABLAGE_MUSTER.pattern == ABLAGE_MUSTER_FENSTER.pattern
    assert BILD_PFAD.fullmatch('/bild/1795275511800_5a4fe9ee/2').groups() == (
        '1795275511800_5a4fe9ee', '2')
    assert BILD_PFAD.fullmatch('/bild/3').groups() == (None, '3')
    for boese in ('/bild/../zustand.json', '/bild/1_a/../../x/1', '/bild/1_a/x', '/bild/a_1/1'):
        assert BILD_PFAD.fullmatch(boese) is None


def test_die_letzten_zehn_fragen_bleiben_mit_bildern_erhalten(tmp_path):
    ordner = tmp_path / 'lotse'
    # Ablagen aus einem früheren Lauf und fremde Dateien im Ordner
    (ordner / 'fragen' / '5_alt').mkdir(parents=True)
    (ordner / 'fragen' / 'notiz').mkdir()
    dienst = dienst_ohne_ros(ordner)
    for nr in range(1, 13):
        eintrag = {'zeit_unix': 1000.0 + nr, 'frage_id': f'id{nr:02d}', 'bilder': 2,
                   'ergebnis': 'antwort', 'wahl': nr % 3}
        dienst._merke(eintrag, frage(nr), [b'\xff\xd8a%d' % nr, b'\xff\xd8b%d' % nr],
                      json.dumps({'wahl': nr % 3}))
    fragen = list(dienst._fragen)
    assert len(fragen) == FRAGEN_BEHALTEN
    assert [f['frage_id'] for f in fragen] == [f'id{nr:02d}' for nr in range(3, 13)]
    assert len(dienst._verlauf) == 12 and all('ablage' in e for e in dienst._verlauf)
    vorhanden = sorted(p.name for p in (ordner / 'fragen').iterdir())
    assert vorhanden == sorted([f['ablage'] for f in fragen] + ['notiz'])   # Fremdes bleibt
    for nr, f in zip(range(3, 13), fragen):
        abgelegt = ordner / 'fragen' / f['ablage']
        assert (abgelegt / 'bild_1.jpg').read_bytes() == b'\xff\xd8a%d' % nr
        assert (abgelegt / 'bild_2.jpg').read_bytes() == b'\xff\xd8b%d' % nr
        assert (abgelegt / 'frage.txt').read_text(encoding='utf-8') == f'Frage {nr}'
        assert f['bilder'] == 2 and f['angeboten'] == [1, 2] and f['antworttext']
    assert not dienst.knoten.protokoll.warnungen


def test_unbrauchbare_frage_kommt_nur_in_den_verlauf(tmp_path):
    dienst = dienst_ohne_ros(tmp_path / 'lotse')
    dienst._merke({'zeit_unix': 1.0, 'frage_id': None, 'ergebnis': 'unbrauchbare_frage'})
    assert len(dienst._verlauf) == 1 and 'ablage' not in dienst._verlauf[0]
    assert not dienst._fragen and not (tmp_path / 'lotse' / 'fragen').exists()
