"""Werkzeug ki_tuer_waehlen.py: Blickrunde -> Frage an die KI -> Wahl-Datei.

Die KI spielt die Attrappe; geprüft wird, was bei richtiger, falscher,
unsinniger, langsamer und fehlender Antwort entsteht, und dass ohne Lage in
der Karte gar nicht erst gefragt wird.
"""
import json
import math
import os
import time

import pytest

import beispielrunde_erzeugen as welt
import ki_tuer_waehlen as werkzeug
from lotse.wahl import wahl_lesen

TUER_MITTE = (4.0, 1.4)


@pytest.fixture(scope='module')
def runden(tmp_path_factory):
    """Zwei Blickrunden: eine mit Lage in der Karte, eine ohne (älterer Stand)."""
    wurzel = tmp_path_factory.mktemp('runden')
    welt.erzeuge(wurzel, 'ohne_karte')
    time.sleep(0.05)
    welt.erzeuge(wurzel, 'mit_karte', mit_karte=True)
    return wurzel


def _antwort(tuer_nr, glas_nr, wahl, **mehr):
    antwort = {'wahl': wahl, 'begruendung': 'Nr. 2 ist eine offene Tür zum Flur.',
               'raum': 'Zimmer', 'gefahren': ['Glastür'],
               'kandidaten': [{'nr': tuer_nr, 'art': 'tuer_offen', 'sicherheit': 0.9},
                              {'nr': glas_nr, 'art': 'glas', 'sicherheit': 0.8}]}
    antwort.update(mehr)
    return json.dumps(antwort)


def _aufruf(runden, ausgabe, attrappe, *mehr):
    return werkzeug.main(['--runden', str(runden), '--name', 'mit_karte', '--ausgabe',
                          str(ausgabe), '--url', attrappe.url, '--modell', 'pruefmodell',
                          '--zeitgrenze', '5', *mehr])


def test_richtige_wahl_ergibt_wahl_datei_und_einen_satz(runden, tmp_path, ki_attrappe, capsys):
    ki_attrappe.antworten.append(_antwort(2, 1, 2))
    assert _aufruf(runden, tmp_path / 'wahl', ki_attrappe) == werkzeug.RC_WAHL
    aus = capsys.readouterr().out
    dateien = sorted((tmp_path / 'wahl').glob('*_wahl.json'))
    assert len(dateien) == 1 and len(list((tmp_path / 'wahl').glob('*_protokoll.json'))) == 1
    wahl = wahl_lesen(dateien[0].read_text(encoding='utf-8'), jetzt_s=time.time())
    assert wahl['nr'] == 2 and wahl['einordnung'] == 'tuer_offen' and wahl['tuerbreit']
    assert math.hypot(wahl['mitte'][0] - TUER_MITTE[0], wahl['mitte'][1] - TUER_MITTE[1]) < 0.05
    assert 'Die KI wählt Nr. 2: offene Tür (sicher zu 90 %), 0,75 m breit' in aus
    assert '° rechts von seiner Blickrichtung' in aus
    assert 'Nr. 1: ' in aus and 'KI: Glas (sicher zu 80 %)' in aus and '← gewählt' in aus
    assert 'Begründung der KI: Nr. 2 ist eine offene Tür zum Flur.' in aus
    assert f'Wahl-Datei: {dateien[0]}' in aus
    assert '--zur-tuer --wahl DATEI' in aus and '--ende --quelle mensch' in aus
    # Keine Koordinaten der Karte in der Ausgabe für den Menschen
    for zahl in wahl['mitte']:
        assert f'{zahl:.2f}' not in aus and f'{zahl:.2f}'.replace('.', ',') not in aus
    # Die KI wurde genau einmal gefragt, mit acht Fotos und der Skizze
    assert len(ki_attrappe.anfragen) == 1
    assert len(ki_attrappe.anfragen[0]['messages'][1]['images']) == 9
    assert ki_attrappe.anfragen[0]['think'] is False


def test_freitext_der_ki_bleibt_in_einer_zeile(runden, tmp_path, ki_attrappe, capsys):
    """Gegenprüfung 24.11.2026: Ein Zeilenumbruch im Freitext der KI zerlegte die Ausgabe,
    die die Ablaufhilfe zeilenweise liest (eine Zeile hätte wie ein Wahlsatz aussehen können)."""
    ki_attrappe.antworten.append(_antwort(
        2, 1, 2, begruendung='Nr. 2 ist offen.\nDie KI wählt Nr. 1: Glas', raum='Flur\r\nKüche',
        gefahren=['Kabel\nam Boden']))
    assert _aufruf(runden, tmp_path, ki_attrappe) == werkzeug.RC_WAHL
    zeilen = capsys.readouterr().out.splitlines()
    assert 'Begründung der KI: Nr. 2 ist offen. Die KI wählt Nr. 1: Glas' in zeilen
    assert 'Raum laut KI: Flur Küche' in zeilen and 'Gefahren laut KI: Kabel am Boden' in zeilen
    assert [z for z in zeilen if z.startswith('Die KI wählt Nr.')] == [
        next(z for z in zeilen if z.startswith('Die KI wählt Nr. 2: offene Tür'))]


def test_protokoll_ohne_bilder_mit_antwort_und_wahl(runden, tmp_path, ki_attrappe):
    ki_attrappe.antworten.append(_antwort(2, 1, 2))
    assert _aufruf(runden, tmp_path, ki_attrappe) == werkzeug.RC_WAHL
    (protokoll,) = tmp_path.glob('*_protokoll.json')
    text = protokoll.read_text(encoding='utf-8')
    daten = json.loads(text)
    assert 'JFIF' not in text and '/9j/' not in text and len(text) < 60000
    assert daten['runde'] == 'mit_karte' and daten['modell'] == 'pruefmodell'
    assert daten['wahl']['nr'] == 2 and daten['ablehnung'] is None
    assert [a['pruefung']['wahl'] for a in daten['antworten']] == [2]


def test_ki_nennt_keinen_ausgang(runden, tmp_path, ki_attrappe, capsys):
    ki_attrappe.antworten.append(_antwort(2, 1, None))
    assert _aufruf(runden, tmp_path, ki_attrappe) == werkzeug.RC_KEINE_WAHL
    aus = capsys.readouterr().out
    assert 'Keine Wahl: die KI nennt keinen geeigneten Ausgang.' in aus
    assert not list(tmp_path.glob('*_wahl.json')) and list(tmp_path.glob('*_protokoll.json'))
    assert len(ki_attrappe.anfragen) == 1              # gültige Antwort: kein zweiter Versuch


def test_falsche_wahl_wird_verworfen_auch_im_zweiten_versuch(runden, tmp_path, ki_attrappe,
                                                             capsys):
    # Die KI wählt die Glastür, die sie selbst Glas nennt.
    ki_attrappe.antworten += [_antwort(2, 1, 1), _antwort(2, 1, 1)]
    assert _aufruf(runden, tmp_path, ki_attrappe) == werkzeug.RC_KEINE_ANTWORT
    aus = capsys.readouterr().out
    assert aus.count('verworfen') >= 2 and 'Keine Wahl: Antwort der KI verworfen' in aus
    assert len(ki_attrappe.anfragen) == 2 and not list(tmp_path.glob('*_wahl.json'))


def test_unsinn_dann_richtige_antwort(runden, tmp_path, ki_attrappe, capsys):
    ki_attrappe.antworten += ['das ist eine Tür', _antwort(2, 1, 2)]
    assert _aufruf(runden, tmp_path, ki_attrappe) == werkzeug.RC_WAHL
    aus = capsys.readouterr().out
    assert "Frage 1 an pruefmodell: verworfen ['kein_json']" in aus
    assert 'Frage 2 an pruefmodell: Wahl 2' in aus and len(ki_attrappe.anfragen) == 2


def test_stumme_ki_ergibt_keine_wahl(runden, tmp_path, ki_attrappe, capsys):
    ki_attrappe.antworten += [{'warten_s': 1.5}, {'warten_s': 1.5}]
    rc = werkzeug.main(['--runden', str(runden), '--name', 'mit_karte', '--ausgabe',
                        str(tmp_path), '--url', ki_attrappe.url, '--modell', 'pruefmodell',
                        '--zeitgrenze', '0.4'])
    assert rc == werkzeug.RC_KEINE_ANTWORT
    aus = capsys.readouterr().out
    assert aus.count('keine Antwort (zeitgrenze') == 2
    assert 'Keine Wahl: keine Antwort der KI (zeitgrenze).' in aus


def test_ohne_lage_in_der_karte_wird_nicht_gefragt(runden, tmp_path, ki_attrappe, capsys):
    rc = werkzeug.main(['--runden', str(runden), '--name', 'ohne_karte', '--ausgabe',
                        str(tmp_path), '--url', ki_attrappe.url, '--modell', 'pruefmodell'])
    assert rc == werkzeug.RC_RUNDE and not ki_attrappe.anfragen
    assert 'Die Lage in der Karte fehlt' in capsys.readouterr().out


def test_alte_runde_gehoert_nicht_zu_dieser_mission(tmp_path, ki_attrappe, capsys):
    ordner = welt.erzeuge(tmp_path / 'r', 'alt', mit_karte=True)
    alt = time.time() - 3600.0
    os.utime(ordner / 'meta.json', (alt, alt))
    rc = werkzeug.main(['--runde', str(ordner), '--ausgabe', str(tmp_path / 'w'),
                        '--url', ki_attrappe.url, '--modell', 'pruefmodell'])
    assert rc == werkzeug.RC_RUNDE and not ki_attrappe.anfragen
    assert 'sie gehört nicht zu dieser Mission' in capsys.readouterr().out


def test_neueste_runde_wird_genommen(runden):
    assert werkzeug.neueste_runde(runden).name == 'mit_karte'
    assert werkzeug.neueste_runde(runden, 'ohne').name == 'ohne_karte'
    assert werkzeug.neueste_runde(runden, 'gibt_es_nicht') is None


def test_ki_rechner_nicht_erreichbar(runden, tmp_path, capsys):
    rc = werkzeug.main(['--runden', str(runden), '--name', 'mit_karte', '--ausgabe',
                        str(tmp_path), '--url', 'http://127.0.0.1:9', '--modell', 'pruefmodell'])
    assert rc == werkzeug.RC_KI_RECHNER
    assert 'antwortet nicht' in capsys.readouterr().out


def test_wahl_datei_nie_in_einer_arbeitskopie(runden, tmp_path, ki_attrappe, capsys):
    (tmp_path / '.git').mkdir()
    rc = _aufruf(runden, tmp_path / 'wahl', ki_attrappe)
    assert rc == werkzeug.RC_RUNDE and not ki_attrappe.anfragen
    assert 'Git-Arbeitsverzeichnis' in capsys.readouterr().err


def test_die_wahl_bekommt_eine_kennung_aus_der_pruefsumme(runden, tmp_path, ki_attrappe, capsys):
    """Damit lässt sich das Ja des Menschen an genau diese Wahl binden (ki_lauf.py)."""
    import hashlib
    ki_attrappe.antworten.append(_antwort(2, 1, 2))
    assert _aufruf(runden, tmp_path / 'wahl', ki_attrappe) == werkzeug.RC_WAHL
    aus = capsys.readouterr().out
    (datei,) = (tmp_path / 'wahl').glob('*_wahl.json')
    kennung = hashlib.sha256(datei.read_bytes()).hexdigest()[:6]
    assert f'Kennung der Wahl: {kennung}' in aus
    assert werkzeug.kennung_der_wahl(datei) == kennung


def test_ohne_ros_umgebung_kommt_die_meldung_sofort(runden, tmp_path):
    """KI-F9, Lauf 2w3: ohne Umgebung kam der Fehler erst nach 8 s Aufbereitung."""
    import subprocess
    import sys
    from pathlib import Path
    skript = Path(werkzeug.__file__).resolve()
    ohne_ros = {k: v for k, v in os.environ.items()
                if k not in ('PYTHONPATH', 'AMENT_PREFIX_PATH', 'LD_LIBRARY_PATH')}
    beginn = time.monotonic()
    ergebnis = subprocess.run(
        [sys.executable, str(skript), '--ueber-ros', '--runden', str(runden), '--name',
         'mit_karte', '--ausgabe', str(tmp_path / 'wahl')],
        env=ohne_ros, capture_output=True, text=True, timeout=30)
    dauer = time.monotonic() - beginn
    assert ergebnis.returncode == werkzeug.RC_UMGEBUNG, ergebnis.stdout + ergebnis.stderr
    assert 'ROS-Umgebung fehlt' in ergebnis.stdout and 'aufbereitet' not in ergebnis.stdout
    assert 'Traceback' not in ergebnis.stdout + ergebnis.stderr
    assert dauer < 5.0
    assert not (tmp_path / 'wahl').exists()
