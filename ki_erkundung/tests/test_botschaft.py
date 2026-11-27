"""Frage und Antwort für die Übertragung zwischen Roboter und KI-Rechner."""
import base64
import json

import pytest

from lotse.botschaft import (MAX_BILDER, entpacke_antwort, entpacke_frage,
                             packe_antwort, packe_frage)
from lotse.frage import Frage, antwortschema
from lotse.ki_rechner import Rohantwort

FRAGE = Frage('System', 'Text mit Umlaut ä', antwortschema([1, 2]), [1, 2])
BILDER = [b'\xff\xd8eins', b'\xff\xd8zwei']


def test_frage_uebersteht_die_uebertragung_unveraendert():
    text = packe_frage('abc123', FRAGE, BILDER, 45.0, {'num_ctx': 4096}, False)
    frage_id, frage, bilder, grenze, optionen, denken = entpacke_frage(text)
    assert frage_id == 'abc123' and frage == FRAGE and bilder == BILDER
    assert grenze == 45.0 and optionen == {'num_ctx': 4096} and denken is False
    assert entpacke_frage(packe_frage('x', FRAGE, []))[5] is None


def test_zeitgrenze_wird_begrenzt():
    assert entpacke_frage(packe_frage('x', FRAGE, [], 99999.0))[3] == 300.0
    assert entpacke_frage(packe_frage('x', FRAGE, [], 0.0))[3] == 1.0


def geaendert(**aenderung):
    daten = json.loads(packe_frage('abc', FRAGE, BILDER))
    daten.update(aenderung)
    return json.dumps(daten)


@pytest.mark.parametrize('text', [
    'kein json', '[]', geaendert(schema_version=99), geaendert(frage_id=''),
    geaendert(frage_id=7), geaendert(text=None), geaendert(system='x' * 30000),
    geaendert(schema='keins'), geaendert(bilder_b64='keine'),
    geaendert(bilder_b64=['###']), geaendert(bilder_b64=['']),
    geaendert(bilder_b64=[base64.b64encode(b'x').decode()] * (MAX_BILDER + 1)),
    geaendert(bilder_b64=[base64.b64encode(b'x' * 3_000_001).decode()]),
    geaendert(zeitgrenze_s='lang'), geaendert(zeitgrenze_s=True),
    geaendert(optionen=[1]), geaendert(denken='ja'),
])
def test_unbrauchbare_frage_wird_abgelehnt(text):
    with pytest.raises(ValueError):
        entpacke_frage(text)


def test_antwort_uebersteht_die_uebertragung_mit_text_und_fehlern():
    roh = Rohantwort('{"wahl": 2}', 7.5, None, True, {'load_s': 0.2}, False)
    frage_id, modell, zurueck = entpacke_antwort(packe_antwort('abc', 'qwen3.5:9b', roh))
    assert (frage_id, modell, zurueck) == ('abc', 'qwen3.5:9b', roh)
    _, _, fehler = entpacke_antwort(
        packe_antwort('abc', 'm', Rohantwort(None, 0.0, 'beschaeftigt')))
    assert fehler.fehler == 'beschaeftigt' and fehler.text is None
    for text in ('x', '{}', json.dumps({'schema_version': 1})):
        with pytest.raises(ValueError):
            entpacke_antwort(text)
