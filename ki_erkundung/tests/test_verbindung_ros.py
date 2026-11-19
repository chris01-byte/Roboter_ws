"""Strecke Roboter -> Lotsen-Dienst -> Ollama über echte ROS-Themen.

Nur wo rclpy vorhanden ist. Ollama wird von der Attrappe gespielt. Aufruf in
einer abgeschotteten ROS-Umgebung, zum Beispiel:

    env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \\
        python3 -m pytest -q ki_erkundung/tests/test_verbindung_ros.py
"""
import base64
import json
import threading
import time

import pytest

rclpy = pytest.importorskip('rclpy')

import trockenlauf  # noqa: E402
from ki_verbindung_ros import THEMA_FRAGE, Verbindung, qos_botschaft  # noqa: E402
from lotse.frage import baue_frage  # noqa: E402
from lotse.kandidaten import Oeffnung  # noqa: E402
from lotse_dienst import Dienst  # noqa: E402

OEFFNUNG = Oeffnung(nr=1, breite_m=0.8, mitte=(2.0, 0.0), pfosten=((2.0, -0.4), (2.0, 0.4)),
                    richtung_grad=0.0, entfernung_m=2.0, tiefe_m=1.0, befahrbar=True)
FRAGE = baue_frage([OEFFNUNG], 8, {1: [1]})
BILDER = [b'\xff\xd8erstes', b'\xff\xd8zweites']


@pytest.fixture
def ros():
    rclpy.init()
    yield
    rclpy.shutdown()


@pytest.fixture
def dienst(ros, ki_attrappe):
    """Lotsen-Dienst wie auf dem KI-Rechner, mit der Attrappe als Ollama."""
    from rclpy.executors import SingleThreadedExecutor
    knoten = rclpy.create_node('ki_lotse_dienst_test')
    dienst = Dienst(knoten, 'pruefmodell', ki_attrappe.url, kontext=4096, status_alle_s=0.5)
    ausfuehrer = SingleThreadedExecutor()
    ausfuehrer.add_node(knoten)
    faden = threading.Thread(target=ausfuehrer.spin, daemon=True)
    faden.start()
    yield dienst
    ausfuehrer.shutdown()
    faden.join(timeout=3.0)
    knoten.destroy_node()


def test_frage_des_roboters_kommt_bei_ollama_an_und_die_antwort_zurueck(dienst, ki_attrappe):
    ki_attrappe.antworten.append('{"wahl": 1}')
    verbindung = Verbindung()
    try:
        status = verbindung.status()
        assert status['bereit'] and status['modell'] == 'pruefmodell'
        assert status['umgebung']['modell_kennung'] == 'kennung-pruefmodell'
        roh = verbindung.frage_stellen(FRAGE, BILDER, zeitgrenze_s=10.0, denken=False)
    finally:
        verbindung.schliessen()
    assert roh.fehler is None and roh.text == '{"wahl": 1}' and roh.denken is False
    assert roh.meta['modell_dienst'] == 'pruefmodell' and 'weg_s' in roh.meta
    anfrage = ki_attrappe.anfragen[0]
    assert anfrage['model'] == 'pruefmodell' and anfrage['think'] is False
    assert anfrage['options']['num_ctx'] == 4096
    assert anfrage['format'] == FRAGE.schema
    assert [base64.b64decode(b) for b in anfrage['messages'][1]['images']] == BILDER
    assert anfrage['messages'][1]['content'] == FRAGE.text


def test_zweite_frage_waehrend_der_ersten_bekommt_beschaeftigt(dienst, ki_attrappe):
    ki_attrappe.antworten.append({'warten_s': 1.5, 'text': '{"wahl": 1}'})
    erste, zweite = Verbindung(name='frager_a'), Verbindung(name='frager_b')
    ergebnis = {}
    try:
        assert erste.status() and zweite.status()
        faden = threading.Thread(target=lambda: ergebnis.update(
            a=erste.frage_stellen(FRAGE, BILDER, zeitgrenze_s=10.0)))
        faden.start()
        time.sleep(0.6)
        ergebnis['b'] = zweite.frage_stellen(FRAGE, BILDER, zeitgrenze_s=5.0)
        faden.join(timeout=10.0)
    finally:
        erste.schliessen()
        zweite.schliessen()
    assert ergebnis['b'].fehler == 'beschaeftigt'
    assert ergebnis['a'].fehler is None and ergebnis['a'].text == '{"wahl": 1}'
    assert len(ki_attrappe.anfragen) == 1


def test_unbrauchbare_frage_wird_gezaehlt_und_der_dienst_laeuft_weiter(dienst, ki_attrappe):
    from std_msgs.msg import String
    stoerer = rclpy.create_node('ki_test_stoerer')
    sender = stoerer.create_publisher(String, THEMA_FRAGE, qos_botschaft())
    ende = time.monotonic() + 5.0
    while stoerer.count_subscribers(THEMA_FRAGE) == 0 and time.monotonic() < ende:
        time.sleep(0.05)
    sender.publish(String(data='das ist keine Frage'))
    sender.publish(String(data=json.dumps({'schema_version': 1, 'frage_id': 'x'})))
    ende = time.monotonic() + 5.0
    while dienst._abgelehnt < 2 and time.monotonic() < ende:
        time.sleep(0.05)
    stoerer.destroy_node()
    assert dienst._abgelehnt == 2 and ki_attrappe.anfragen == []
    ki_attrappe.antworten.append('{"wahl": null}')
    verbindung = Verbindung()
    try:
        assert verbindung.frage_stellen(FRAGE, BILDER, zeitgrenze_s=10.0).text == '{"wahl": null}'
    finally:
        verbindung.schliessen()


def test_ohne_dienst_ist_keine_antwort_ein_ergebnis(ros):
    verbindung = Verbindung()
    try:
        assert verbindung.status(warten_s=0.5) is None
        roh = verbindung.frage_stellen(FRAGE, BILDER, zeitgrenze_s=2.0, finden_s=0.5)
    finally:
        verbindung.schliessen()
    assert roh.fehler == 'lotse_nicht_erreichbar' and roh.text is None


def test_langsames_ollama_endet_an_der_zeitgrenze_des_dienstes(dienst, ki_attrappe):
    ki_attrappe.antworten.append({'warten_s': 3.0, 'text': '{"wahl": 1}'})
    verbindung = Verbindung()
    try:
        beginn = time.monotonic()
        roh = verbindung.frage_stellen(FRAGE, BILDER, zeitgrenze_s=1.0)
    finally:
        verbindung.schliessen()
    assert roh.fehler == 'zeitgrenze' and time.monotonic() - beginn < 4.0


def test_trockenlauf_vom_roboter_aus_ueber_den_dienst(dienst, ki_attrappe, beispielordner,
                                                      tmp_path, capsys):
    def keine_wahl(anfrage):
        return json.dumps({'wahl': None, 'begruendung': 'unsicher', 'kandidaten': [],
                           'raum': 'unklar', 'gefahren': []})
    ki_attrappe.antworten.append(keine_wahl)
    aus = tmp_path / 'aus'
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe', str(aus),
                             '--ueber-ros', '--denken', 'aus']) == 0
    ergebnis = json.loads((aus / 'ergebnis.json').read_text(encoding='utf-8'))
    einstellungen = ergebnis['einstellungen']
    assert einstellungen['ueber_ros'] and einstellungen['denken'] == 'aus'
    assert einstellungen['modelle'] == ['pruefmodell']
    assert einstellungen['umgebung']['pruefmodell']['dienst_fassung'] == '0.99.1'
    antwort = ergebnis['runden'][0]['antworten'][0]
    assert antwort['modell'] == 'pruefmodell' and antwort['fehler'] is None
    assert antwort['pruefung']['gueltig'] and antwort['pruefung']['wahl'] is None
    assert len(ki_attrappe.anfragen[0]['messages'][1]['images']) == 9
    assert ki_attrappe.anfragen[0]['think'] is False


def test_trockenlauf_meldet_fehlenden_dienst(ros, beispielordner, tmp_path, capsys):
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe',
                             str(tmp_path / 'a'), '--ueber-ros']) == 3
    assert 'Lotsen-Dienst' in capsys.readouterr().err
