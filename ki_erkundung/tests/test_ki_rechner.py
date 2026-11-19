"""Verbindung zum KI-Rechner (hier: zur Attrappe auf 127.0.0.1)."""
import base64
import socket
import time

import pytest

from lotse.frage import baue_frage
from lotse.ki_rechner import frage_stellen, modelle
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
