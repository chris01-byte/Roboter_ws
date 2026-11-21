"""Sucher: das Kamerabild live in einem gewöhnlichen Fenster (Jetson)."""
import io
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from PIL import Image

from sucher import ADRESSE, KOPFZEILE, Sucher, baue_bearbeiter, bildgroesse


def jpeg(breite=320, hoehe=180, farbe=(10, 120, 40)) -> bytes:
    puffer = io.BytesIO()
    Image.new('RGB', (breite, hoehe), farbe).save(puffer, format='JPEG')
    return puffer.getvalue()


@pytest.fixture
def seite():
    sucher = Sucher()
    beendet = threading.Event()
    server = ThreadingHTTPServer((ADRESSE, 0), baue_bearbeiter(sucher, beendet.set))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    wurzel = f'http://{ADRESSE}:{server.server_address[1]}'
    ohne_umweg = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def rufe(pfad, senden=False, kopf=None):
        anfrage = urllib.request.Request(wurzel + pfad, data=b'' if senden else None,
                                         headers=kopf or {})
        try:
            with ohne_umweg.open(anfrage, timeout=10) as antwort:
                return antwort.status, antwort.read()
        except urllib.error.HTTPError as fehler:
            return fehler.code, fehler.read()

    rufe.sucher, rufe.beendet = sucher, beendet
    yield rufe
    server.shutdown()
    server.server_close()


def test_bildgroesse_aus_den_kopfdaten():
    assert bildgroesse(jpeg(320, 180)) == (320, 180)
    assert bildgroesse(jpeg(640, 360)) == (640, 360)
    assert bildgroesse(b'kein bild') == (None, None)


def test_letztes_bild_wird_gezeigt_und_nicht_gespeichert(seite, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert json.loads(seite('/api/zustand')[1]) == {
        'bilder': 0, 'breite': None, 'hoehe': None, 'alter_s': None, 'rate_hz': 0.0}
    assert seite('/bild')[0] == 404                       # noch kein Bild
    erstes, zweites = jpeg(farbe=(200, 0, 0)), jpeg(farbe=(0, 0, 200))
    seite.sucher.nimm(erstes)
    seite.sucher.nimm(zweites)
    zustand = json.loads(seite('/api/zustand')[1])
    assert zustand['bilder'] == 2 and (zustand['breite'], zustand['hoehe']) == (320, 180)
    assert zustand['alter_s'] < 2.0
    assert seite('/bild') == (200, zweites)               # immer nur das letzte
    status, inhalt = seite('/')
    assert status == 200 and 'Sucher'.encode() in inhalt
    assert b'requestFullscreen' not in inhalt and b'fullscreen' not in inhalt.lower()
    assert list(tmp_path.iterdir()) == []                 # nichts auf die Platte


def test_nur_von_diesem_rechner_und_beenden_nur_von_der_eigenen_seite(seite):
    assert seite('/', kopf={'Host': 'boese.example'})[0] == 403
    assert seite('/api/beenden', senden=True)[0] == 403
    assert seite('/api/beenden', senden=True, kopf={KOPFZEILE: '1', 'Host': 'x.example'}
                 )[0] == 403
    assert not seite.beendet.is_set()
    assert seite('/api/anderes', senden=True, kopf={KOPFZEILE: '1'})[0] == 404
    assert seite('/api/beenden', senden=True, kopf={KOPFZEILE: '1'})[0] == 200
    assert seite.beendet.wait(timeout=3.0)
