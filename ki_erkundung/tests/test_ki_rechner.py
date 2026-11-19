"""Verbindung zum KI-Rechner (hier: zur Attrappe auf 127.0.0.1)."""
import base64
import socket
import time

import pytest

from lotse.frage import baue_frage
from lotse.ki_rechner import Rohantwort, frage_stellen, modelle, umgebung
from lotse.kandidaten import Oeffnung

OEFFNUNG = Oeffnung(nr=1, breite_m=0.8, mitte=(2.0, 0.0), pfosten=((2.0, -0.4), (2.0, 0.4)),
                    richtung_grad=0.0, entfernung_m=2.0, tiefe_m=1.0, befahrbar=True)
FRAGE = baue_frage([OEFFNUNG], 8, {1: [1]})
BILDER = [b'\xff\xd8erstes', b'\xff\xd8zweites']


def test_frage_geht_mit_bildern_und_schema_hinaus_und_antwort_kommt_zurueck(ki_attrappe):
    ki_attrappe.antworten.append('{"wahl": 1}')
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url,
                        optionen={'num_ctx': 4096})
    assert roh.fehler is None and roh.text == '{"wahl": 1}' and roh.mit_schema
    assert roh.meta == {'total_s': 2.5, 'load_s': 0.1, 'eval_s': 1.2,
                        'prompt_eval_count': 2100, 'eval_count': 90}
    anfrage = ki_attrappe.anfragen[0]
    assert anfrage['model'] == 'pruefmodell' and anfrage['stream'] is False
    assert anfrage['format'] == FRAGE.schema
    assert anfrage['options'] == {'temperature': 0.0, 'seed': 1, 'num_ctx': 4096}
    system, nutzer = anfrage['messages']
    assert system == {'role': 'system', 'content': FRAGE.system}
    assert nutzer['content'] == FRAGE.text
    assert [base64.b64decode(b) for b in nutzer['images']] == BILDER
    assert roh.als_dict()['fehler'] is None and 'text' not in roh.als_dict()


def test_aelterer_dienst_ohne_schema_wird_einmal_mit_json_zwang_gefragt(ki_attrappe):
    ki_attrappe.schema_ablehnen = True
    ki_attrappe.antworten.append('{"wahl": null}')
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url)
    assert roh.fehler is None and not roh.mit_schema and roh.text == '{"wahl": null}'
    assert [a['format'] for a in ki_attrappe.anfragen] == [FRAGE.schema, 'json']


def test_zu_langsame_antwort_endet_an_der_zeitgrenze(ki_attrappe):
    ki_attrappe.antworten.append({'warten_s': 2.0, 'text': '{"wahl": 1}'})
    beginn = time.monotonic()
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, zeitgrenze_s=0.4)
    assert roh.fehler == 'zeitgrenze' and roh.text is None
    assert time.monotonic() - beginn < 1.5


def test_nicht_erreichbarer_ki_rechner_ist_ein_ergebnis_keine_ausnahme():
    with socket.socket() as frei:                      # ein sicher unbenutzter Port
        frei.bind(('127.0.0.1', 0))
        port = frei.getsockname()[1]
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=f'http://127.0.0.1:{port}',
                        zeitgrenze_s=2.0)
    assert roh.fehler == 'nicht_erreichbar' and roh.text is None
    assert modelle(f'http://127.0.0.1:{port}', zeitgrenze_s=1.0) is None


@pytest.mark.parametrize('antwort,fehler', [
    ({'roh': b'kein json'}, 'antwort_unlesbar'),
    ({'roh': b'{"done": true}'}, 'antwort_unlesbar'),
    ({'status': 404}, 'http_404'),
])
def test_unbrauchbare_antworten_des_dienstes(ki_attrappe, antwort, fehler):
    ki_attrappe.antworten.append(antwort)
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url)
    assert roh.fehler == fehler and roh.text is None


def test_vorhandene_modelle_werden_gelistet(ki_attrappe):
    ki_attrappe.modelle = ['zweites:7b', 'erstes']
    assert modelle(ki_attrappe.url) == ['erstes', 'zweites:7b']


def test_ein_eingestellter_proxy_wird_fuer_den_ki_rechner_nicht_benutzt(ki_attrappe, monkeypatch):
    """Bilder gehen nur an die angegebene Adresse im Haus."""
    for name in ('http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'all_proxy'):
        monkeypatch.setenv(name, 'http://127.0.0.1:9')      # dort lauscht nichts
    monkeypatch.delenv('no_proxy', raising=False)
    monkeypatch.delenv('NO_PROXY', raising=False)
    ki_attrappe.antworten.append('{"wahl": 1}')
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, zeitgrenze_s=3.0)
    assert roh.fehler is None
    assert modelle(ki_attrappe.url) == ['pruefmodell']


def test_denkschalter_wird_nur_gesendet_wenn_er_gesetzt_ist(ki_attrappe):
    ki_attrappe.antworten += ['{"wahl": 1}'] * 3
    assert frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url).denken is None
    aus = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, denken=False)
    an = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, denken=True)
    assert 'think' not in ki_attrappe.anfragen[0]
    assert ki_attrappe.anfragen[1]['think'] is False and aus.denken is False
    assert ki_attrappe.anfragen[2]['think'] is True and an.als_dict()['denken'] is True


def test_dienst_ohne_denkschalter_wird_ohne_ihn_erneut_gefragt(ki_attrappe):
    ki_attrappe.denkschalter_ablehnen = True
    ki_attrappe.antworten.append('{"wahl": 1}')
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, denken=False)
    assert roh.fehler is None and roh.denken is None and roh.mit_schema
    assert ['think' in a for a in ki_attrappe.anfragen] == [True, False]
    # lehnt er auch das Schema ab, folgt der einfache JSON-Zwang
    ki_attrappe.anfragen.clear()
    ki_attrappe.schema_ablehnen = True
    ki_attrappe.antworten.append('{"wahl": null}')
    roh = frage_stellen(FRAGE, BILDER, 'pruefmodell', url=ki_attrappe.url, denken=True)
    assert roh.fehler is None and not roh.mit_schema and roh.denken is None
    assert [a['format'] == 'json' for a in ki_attrappe.anfragen] == [False, False, True]


def test_umgebung_nennt_fassung_des_dienstes_und_kennung_des_modells(ki_attrappe):
    assert umgebung('pruefmodell', url=ki_attrappe.url) == {
        'modell': 'pruefmodell', 'dienst_fassung': '0.99.1',
        'modell_kennung': 'kennung-pruefmodell', 'quantisierung': 'Q4_K_M',
        'parameter': '9B', 'groesse_gb': 6.6}
    fremd = umgebung('gibt_es_nicht', url=ki_attrappe.url)
    assert fremd['dienst_fassung'] == '0.99.1' and fremd['modell_kennung'] is None
    ki_attrappe.schliessen()
    assert umgebung('pruefmodell', url=ki_attrappe.url, zeitgrenze_s=1.0)['dienst_fassung'] is None


def test_rohantwort_uebersteht_die_uebertragung_als_nachricht():
    roh = Rohantwort('{"wahl": 1}', 3.21, None, True, {'load_s': 0.1}, False)
    zurueck = Rohantwort.aus_nachricht(roh.als_nachricht())
    assert zurueck == Rohantwort('{"wahl": 1}', 3.21, None, True, {'load_s': 0.1}, False)
    assert 'text' not in roh.als_dict()
    assert Rohantwort.aus_nachricht({'fehler': 'zeitgrenze', 'dauer_s': 60}).fehler == 'zeitgrenze'
    assert Rohantwort.aus_nachricht({'dauer_s': 1}).fehler == 'antwort_unlesbar'
