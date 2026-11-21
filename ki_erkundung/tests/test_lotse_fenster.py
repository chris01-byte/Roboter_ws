"""Lotsen-Fenster: Programm für den Bildschirm des KI-Rechners.

Ohne ROS und ohne KI-Rechner: Den Lotsen-Dienst spielt ein kleines Skript,
das wie der echte seinen Zustand ablegt und auf SIGINT endet.
"""
import json
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import lotse_fenster
from lotse_fenster import ADRESSE, KOPFZEILE, Fenster, baue_bearbeiter, gegenstellen

GESPIELTER_DIENST = textwrap.dedent('''
    import json, os, signal, sys, time
    ordner = sys.argv[1]
    print('gespielter Dienst gestartet', flush=True)
    os.makedirs(os.path.join(ordner, 'letzte_frage'), exist_ok=True)
    with open(os.path.join(ordner, 'letzte_frage', 'bild_1.jpg'), 'wb') as datei:
        datei.write(b'\\xff\\xd8bild')
    beginn = time.time()
    try:
        while True:
            zustand = {'pid': os.getpid(), 'zeit_unix': time.time(), 'gestartet_unix': beginn,
                       'modell': 'pruefmodell', 'bereit': True, 'beschaeftigt': False,
                       'fragen_beantwortet': 1, 'fragen_abgelehnt': 0,
                       'ros_andere_knoten': 3, 'ros_fragende': 1,
                       'verlauf': [{'zeit_unix': beginn, 'frage_id': 'a', 'ergebnis': 'zeitgrenze'},
                                   {'zeit_unix': beginn + 1, 'frage_id': 'b', 'ergebnis': 'antwort',
                                    'wahl': 2, 'gueltig': True}],
                       'letzte_frage': {'frage_id': 'b', 'zeit_unix': beginn + 1, 'bilder': 1,
                                        'ergebnis': 'antwort', 'wahl': 2}}
            with open(os.path.join(ordner, 'zustand.json'), 'w') as datei:
                json.dump(zustand, datei)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('gespielter Dienst beendet', flush=True)
''')


@pytest.fixture
def fenster(tmp_path, ki_attrappe):
    skript = tmp_path / 'gespielter_dienst.py'
    skript.write_text(GESPIELTER_DIENST, encoding='utf-8')
    ordner = tmp_path / 'lotse'
    eines = Fenster(ordner, 'pruefmodell', ki_attrappe.url,
                    dienst_befehl=[sys.executable, str(skript), str(ordner)],
                    dds_uri='', pruefe_alle_s=0.2)
    yield eines
    eines.schliesse()


@pytest.fixture
def seite(fenster):
    """Die Anzeige auf einem freien Anschluss; liefert eine Abruf-Funktion."""
    beendet = threading.Event()
    server = ThreadingHTTPServer((ADRESSE, 0), baue_bearbeiter(fenster, beendet.set))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    wurzel = f'http://{ADRESSE}:{server.server_address[1]}'
    ohne_umweg = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def rufe(pfad, senden=False, kopf=None):
        anfrage = urllib.request.Request(wurzel + pfad, data=b'' if senden else None,
                                         headers=kopf or {})
        try:
            with ohne_umweg.open(anfrage, timeout=15) as antwort:
                return antwort.status, antwort.read()
        except urllib.error.HTTPError as fehler:
            return fehler.code, fehler.read()

    rufe.beendet = beendet
    yield rufe
    server.shutdown()
    server.server_close()


def warte(bedingung, geduld_s=8.0):
    ende = time.monotonic() + geduld_s
    while time.monotonic() < ende:
        if bedingung():
            return True
        time.sleep(0.05)
    return False


def test_dienst_starten_zustand_lesen_und_mit_einem_sigint_beenden(fenster):
    vorher = fenster.zustand()
    assert not vorher['dienst']['laeuft'] and vorher['verlauf'] == []
    assert fenster.starte_dienst() == 'gestartet'
    assert fenster.starte_dienst() == 'laeuft_schon'
    assert warte(lambda: fenster.zustand()['dienst']['meldet_sich'])
    assert warte(lambda: fenster.zustand()['ollama']['geprueft'])
    z = fenster.zustand()
    assert z['dienst']['bereit'] and z['dienst']['beantwortet'] == 1
    assert z['ollama'] == {'geprueft': True, 'erreichbar': True, 'fassung': '0.99.1',
                           'modell_vorhanden': True, 'groesse_gb': 6.6, 'parameter': '9B'}
    assert z['roboter'] == {'gegenstellen': 0, 'im_netz': None, 'ros_andere_knoten': 3,
                            'ros_fragende': 1}
    assert [e['frage_id'] for e in z['verlauf']] == ['b', 'a']          # neueste zuerst
    assert z['letzte_frage']['wahl'] == 2 and fenster.bild(1) == b'\xff\xd8bild'
    assert fenster.bild(2) is None
    assert any('gespielter Dienst gestartet' in zeile for zeile in z['log'])
    assert fenster.stoppe_dienst() == 'beendet'
    assert fenster.stoppe_dienst() == 'lief_nicht'
    nachher = fenster.zustand()
    assert not nachher['dienst']['laeuft'] and not nachher['dienst']['meldet_sich']
    log = fenster.logdatei.read_text(encoding='utf-8')
    assert 'gespielter Dienst beendet' in log          # er hat das SIGINT selbst behandelt
    assert '--- Start' in log and '--- Ende' in log


def test_fehlendes_modell_und_abgestuerzter_dienst_werden_gezeigt(tmp_path, ki_attrappe):
    kaputt = [sys.executable, '-c', 'import sys; print("kaputt"); sys.exit(3)']
    eines = Fenster(tmp_path / 'lotse', 'gibt_es_nicht', ki_attrappe.url,
                    dienst_befehl=kaputt, dds_uri='', pruefe_alle_s=0.2)
    try:
        assert eines.starte_dienst() == 'gestartet'
        assert warte(lambda: eines.zustand()['dienst']['ende_code'] == 3)
        assert warte(lambda: eines.zustand()['ollama']['geprueft'])
        z = eines.zustand()
        assert z['ollama']['erreichbar'] and not z['ollama']['modell_vorhanden']
        assert not z['dienst']['laeuft'] and 'kaputt' in z['log'][-1]
    finally:
        eines.schliesse()


def test_ein_dienst_ausserhalb_des_programms_wird_erkannt_und_kein_zweiter_gestartet(
        fenster, tmp_path):
    import subprocess
    fremd_skript = tmp_path / 'lotse_dienst.py'          # so heißt der echte Dienst
    fremd_skript.write_text('import time\ntime.sleep(60)\n', encoding='utf-8')
    fremder = subprocess.Popen([sys.executable, str(fremd_skript)])
    try:
        assert warte(lambda: fremder.pid in fenster.fremde_dienste())
        assert fenster.starte_dienst() == 'fremder_dienst'
        assert not fenster.dienst_laeuft()
        assert fenster.stoppe_fremden(1) == 'unbekannt'       # nur erkannte Lotsen-Dienste
        assert fenster.stoppe_fremden(fremder.pid) == 'beendet'
        assert fremder.wait(timeout=5) != 0
        assert warte(lambda: fenster.fremde_dienste() == [])
        assert fenster.starte_dienst() == 'gestartet'
    finally:
        if fremder.poll() is None:
            fremder.kill()


def test_seite_zustand_und_bild_nur_von_diesem_rechner(fenster, seite):
    assert fenster.starte_dienst() == 'gestartet'
    assert warte(lambda: fenster.zustand()['dienst']['meldet_sich'])
    status, inhalt = seite('/')
    assert status == 200 and b'Amadeus' in inhalt and b'<script>' in inhalt
    status, inhalt = seite('/api/zustand')
    zustand = json.loads(inhalt)
    assert status == 200 and zustand['dienst']['laeuft'] and zustand['modell'] == 'pruefmodell'
    assert seite('/bild/1') == (200, b'\xff\xd8bild')
    assert seite('/bild/9')[0] == 404 and seite('/bild/../zustand.json')[0] == 404
    assert seite('/etwas')[0] == 404
    # Unter fremdem Namen angesprochen (eine Webseite, die hierher zeigt): abgelehnt.
    assert seite('/api/zustand', kopf={'Host': 'boese.example'})[0] == 403
    assert seite('/', kopf={'Host': 'boese.example'})[0] == 403


def test_schalter_nur_von_der_eigenen_seite(fenster, seite):
    assert fenster.starte_dienst() == 'gestartet'
    assert seite('/api/dienst/stopp', senden=True)[0] == 403          # ohne Kopfzeile
    assert seite('/api/beenden', senden=True)[0] == 403
    assert fenster.dienst_laeuft() and not seite.beendet.is_set()
    eigene = {KOPFZEILE: '1'}
    assert seite('/api/dienst/stopp', senden=True, kopf={KOPFZEILE: '1', 'Host': 'x.example'}
                 )[0] == 403
    status, inhalt = seite('/api/dienst/stopp', senden=True, kopf=eigene)
    assert status == 200 and json.loads(inhalt) == {'ergebnis': 'beendet'}
    assert not fenster.dienst_laeuft()
    assert json.loads(seite('/api/dienst/start', senden=True, kopf=eigene)[1]) == {
        'ergebnis': 'gestartet'}
    assert json.loads(seite('/api/fremd/stopp/1', senden=True, kopf=eigene)[1]) == {
        'ergebnis': 'unbekannt'}
    assert seite('/api/gibt_es_nicht', senden=True, kopf=eigene)[0] == 404
    assert seite('/api/beenden', senden=True, kopf=eigene)[0] == 200
    assert seite.beendet.wait(timeout=3.0)


def test_gegenstellen_aus_der_dds_einstellung(tmp_path):
    datei = tmp_path / 'dds.xml'
    datei.write_text(
        '<CycloneDDS xmlns="https://cdds.io/config"><Domain Id="any"><Discovery><Peers>'
        '<Peer Address="198.51.100.7"/><Peer address="198.51.100.8:7400"/>'
        '<Peer Address="198.51.100.7"/></Peers></Discovery></Domain></CycloneDDS>',
        encoding='utf-8')
    assert gegenstellen(f'file://{datei}') == ['198.51.100.7', '198.51.100.8']
    assert gegenstellen(None) == [] and gegenstellen('') == []
    assert gegenstellen(f'file://{tmp_path}/fehlt.xml') == []
    datei.write_text('kein xml', encoding='utf-8')
    assert gegenstellen(f'file://{datei}') == []


def test_erreichbarkeit_der_gegenstelle_wird_angezeigt(tmp_path, ki_attrappe, monkeypatch):
    datei = tmp_path / 'dds.xml'
    datei.write_text('<CycloneDDS><Domain><Discovery><Peers><Peer Address="198.51.100.7"/>'
                     '<Peer Address="198.51.100.9"/></Peers></Discovery></Domain></CycloneDDS>',
                     encoding='utf-8')
    monkeypatch.setattr(lotse_fenster, 'eigene_adressen', lambda: ['198.51.100.9'])
    antwortet = {'wert': False}
    monkeypatch.setattr(lotse_fenster, 'erreichbar', lambda adresse: antwortet['wert'])
    eines = Fenster(tmp_path / 'lotse', 'pruefmodell', ki_attrappe.url,
                    dienst_befehl=[sys.executable, '-c', 'pass'], dds_uri=f'file://{datei}',
                    pruefe_alle_s=0.1)
    try:
        assert warte(lambda: eines.zustand()['roboter']['im_netz'] is False)
        assert eines.zustand()['roboter']['gegenstellen'] == 1       # die eigene zählt nicht
        antwortet['wert'] = True
        assert warte(lambda: eines.zustand()['roboter']['im_netz'] is True)
        # Adressen stehen nirgends im Zustand, den die Seite bekommt.
        assert '198.51.100' not in json.dumps(eines.zustand())
    finally:
        eines.schliesse()


def test_programm_lehnt_einen_ordner_in_der_arbeitskopie_ab_und_laeuft_nur_einmal(
        tmp_path, ki_attrappe, capsys, monkeypatch):
    from conftest import WURZEL
    assert lotse_fenster.main(['--ordner', str(WURZEL / 'tests' / 'gibt_es_nicht'),
                               '--kein-browser']) == 2
    assert 'Git-Arbeitskopie' in capsys.readouterr().err
    assert not (WURZEL / 'tests' / 'gibt_es_nicht').exists()
    # Der Anschluss ist belegt (das Programm läuft schon): nur das Fenster öffnen.
    belegt = ThreadingHTTPServer((ADRESSE, 0), baue_bearbeiter(None, lambda: None))
    geoeffnet = []
    monkeypatch.setattr(lotse_fenster.webbrowser, 'open', geoeffnet.append)
    try:
        port = belegt.server_address[1]
        assert lotse_fenster.main(['--ordner', str(tmp_path / 'lotse'), '--url', ki_attrappe.url,
                                   '--port', str(port)]) == 0
    finally:
        belegt.server_close()
    assert geoeffnet == [f'http://{ADRESSE}:{port}/']
    assert 'läuft bereits' in capsys.readouterr().out
