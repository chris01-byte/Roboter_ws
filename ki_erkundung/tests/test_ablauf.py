"""Der ganze Trockenlauf an der künstlichen Blickrunde, mit gespieltem KI-Rechner."""
import io
import json

import numpy as np
import pytest
from PIL import Image

import beispielrunde_erzeugen as welt
import trockenlauf
import trockenlauf_auswerten
from lotse.ablauf import befrage, bereite_vor
from lotse.blickrunde import Blickrunde, schreibe_runde
from lotse.geometrie import Kamera


def nummern(vorbereitung):
    """Welche Nummer die Tür und welche die Glastür bekommen hat."""
    tuer, _, glas = welt.tuer_im_standpunktrahmen()

    def naechste(ziel):
        return min(vorbereitung.oeffnungen,
                   key=lambda o: np.hypot(o.mitte[0] - ziel[0], o.mitte[1] - ziel[1]))
    return naechste(tuer), naechste(glas)


@pytest.fixture(scope='module')
def vorbereitung(beispielrunde):
    return bereite_vor(beispielrunde)


def test_tuer_und_glastuer_werden_vermessen_die_schranknische_nicht(vorbereitung):
    assert vorbereitung.auswahl['vollstaendig']
    assert len(vorbereitung.auswahl['bilder']) == 8
    assert vorbereitung.guete_min > 0.9
    assert len(vorbereitung.oeffnungen) == 2
    tuer_wahr, _, glas_wahr = welt.tuer_im_standpunktrahmen()
    tuer, glas = nummern(vorbereitung)
    assert tuer.nr != glas.nr
    assert np.hypot(tuer.mitte[0] - tuer_wahr[0], tuer.mitte[1] - tuer_wahr[1]) < 0.10
    assert np.hypot(glas.mitte[0] - glas_wahr[0], glas.mitte[1] - glas_wahr[1]) < 0.10
    # In der Beispielwelt misst die Vermessung einige Zentimeter zu schmal.
    assert tuer.breite_m == pytest.approx(0.80, abs=0.08)
    assert glas.breite_m == pytest.approx(0.90, abs=0.08)
    assert tuer.befahrbar and glas.befahrbar


def test_jede_nummer_steht_in_mindestens_einem_foto_und_in_der_frage(vorbereitung):
    assert vorbereitung.frage.angeboten == [1, 2]
    assert set(vorbereitung.sichtbar) == {1, 2}
    for nr, bilder in vorbereitung.sichtbar.items():
        assert bilder and all(1 <= b <= 8 for b in bilder)
        assert f'\n{nr} | ' in vorbereitung.frage.text
    assert all(f.size == (640, 360) for f in vorbereitung.fotos)
    assert vorbereitung.kamera_winkel_grad[0] == pytest.approx(69.0)


def test_bilder_fuer_die_ki_einzeln_oder_als_ein_blatt(vorbereitung):
    einzeln = vorbereitung.bilder_fuer_ki()
    assert len(einzeln) == 9                              # acht Fotos und die Skizze
    assert all(Image.open(io.BytesIO(b)).format == 'JPEG' for b in einzeln)
    blatt = vorbereitung.bilder_fuer_ki(mosaik=True)
    assert len(blatt) == 1
    assert Image.open(io.BytesIO(blatt[0])).size == (3 * 640, 3 * 360)


def test_ergebniseintrag_enthaelt_zahlen_aber_keine_bilddaten(vorbereitung):
    eintrag = vorbereitung.als_dict()
    text = json.dumps(eintrag)
    assert eintrag['vollstaendig'] and len(eintrag['oeffnungen']) == 2
    assert eintrag['vermessen_von'] == 'antriebsmitte'          # es wurde gedreht
    assert [z['nr'] for z in eintrag['protokoll'] if z['ergebnis'] == 'angeboten'] == [1, 2]
    ohne_protokoll = json.dumps({k: v for k, v in eintrag.items() if k != 'protokoll'})
    assert 'JFIF' not in text and len(ohne_protokoll) < 4000 and len(text) < 40000


def test_richtige_wahl_wird_angenommen_und_nachgemessen(vorbereitung, ki_attrappe):
    tuer, glas = nummern(vorbereitung)
    ki_attrappe.antworten.append(json.dumps({
        'wahl': tuer.nr, 'begruendung': 'offene Tür',
        'kandidaten': [{'nr': tuer.nr, 'art': 'tuer_offen'}, {'nr': glas.nr, 'art': 'glas'}],
        'raum': 'Arbeitszimmer', 'gefahren': ['Glas']}))
    eintrag = befrage(vorbereitung, 'pruefmodell', url=ki_attrappe.url)
    assert eintrag['fehler'] is None
    assert eintrag['pruefung']['gueltig'] and eintrag['pruefung']['wahl'] == tuer.nr
    assert eintrag['nachmessen'] is None
    assert len(ki_attrappe.anfragen[0]['messages'][1]['images']) == 9
    assert ki_attrappe.anfragen[0]['format']['properties']['wahl'] == {'enum': [1, 2, None]}


def test_wahl_der_glastuer_wird_verworfen_wenn_die_ki_sie_selbst_glas_nennt(
        vorbereitung, ki_attrappe):
    tuer, glas = nummern(vorbereitung)
    ki_attrappe.antworten.append(json.dumps({
        'wahl': glas.nr, 'begruendung': '', 'raum': '', 'gefahren': [],
        'kandidaten': [{'nr': tuer.nr, 'art': 'tuer_offen'}, {'nr': glas.nr, 'art': 'glas'}]}))
    eintrag = befrage(vorbereitung, 'pruefmodell', url=ki_attrappe.url)
    assert not eintrag['pruefung']['gueltig'] and eintrag['pruefung']['wahl'] is None
    assert eintrag['nachmessen'] is None


def test_stummer_ki_rechner_ergibt_einen_eintrag_ohne_pruefung(vorbereitung, ki_attrappe):
    ki_attrappe.antworten.append({'warten_s': 2.0})
    eintrag = befrage(vorbereitung, 'pruefmodell', url=ki_attrappe.url, zeitgrenze_s=0.3)
    assert eintrag['fehler'] == 'zeitgrenze' and 'pruefung' not in eintrag


def test_blickrunde_ohne_scans_wird_mit_klarem_grund_abgelehnt(tmp_path):
    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    ordner = schreibe_runde(tmp_path / 'r', 'ohne_scan', kamera, [b'a'], [None], [0.0])
    with pytest.raises(ValueError, match='ohne LiDAR-Scans'):
        bereite_vor(Blickrunde.lade(ordner))


def test_werkzeuge_von_der_aufnahme_bis_zum_bericht(beispielordner, tmp_path, ki_attrappe,
                                                    capsys):
    aus = tmp_path / 'aus'
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe', str(aus),
                             '--nur-markieren']) == 0
    ansicht = aus / 'beispiel_zimmer'
    assert sorted(p.name for p in ansicht.iterdir()) == sorted(
        [f'B{i}.jpg' for i in range(1, 9)] + ['frage.txt', 'skizze.png', 'uebersicht.jpg'])
    ohne_ki = json.loads((aus / 'ergebnis.json').read_text(encoding='utf-8'))
    assert ohne_ki['runden'][0]['antworten'] == []

    vorbereitung = bereite_vor(Blickrunde.lade(beispielordner / 'beispiel_zimmer'))
    tuer, glas = nummern(vorbereitung)

    def waehle_tuer(anfrage):
        return json.dumps({'wahl': tuer.nr, 'begruendung': 'Tür', 'raum': 'Zimmer',
                           'gefahren': [],
                           'kandidaten': [{'nr': tuer.nr, 'art': 'tuer_offen'},
                                          {'nr': glas.nr, 'art': 'glas'}]})
    ki_attrappe.antworten += [waehle_tuer, waehle_tuer]
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe', str(aus),
                             '--modell', 'pruefmodell', '--wiederholungen', '2',
                             '--url', ki_attrappe.url, '--kontext', '4096']) == 0
    ergebnis = json.loads((aus / 'ergebnis.json').read_text(encoding='utf-8'))
    antworten = ergebnis['runden'][0]['antworten']
    assert [a['pruefung']['wahl'] for a in antworten] == [tuer.nr, tuer.nr]
    assert ki_attrappe.anfragen[0]['options']['num_ctx'] == 4096
    assert 'think' not in ki_attrappe.anfragen[0]
    # womit geantwortet wurde, steht nachvollziehbar in der Ergebnisdatei
    assert ergebnis['einstellungen']['umgebung']['pruefmodell'] == {
        'modell': 'pruefmodell', 'dienst_fassung': '0.99.1',
        'modell_kennung': 'kennung-pruefmodell', 'quantisierung': 'Q4_K_M',
        'parameter': '9B', 'groesse_gb': 6.6}

    (beispielordner / 'beispiel_zimmer' / 'wahrheit.json').write_text(json.dumps({
        'ausgaenge': [tuer.nr], 'ausgang_sichtbar': True,
        'arten': {str(tuer.nr): 'tuer_offen', str(glas.nr): 'glas'}}), encoding='utf-8')
    try:
        capsys.readouterr()
        assert trockenlauf_auswerten.main([
            '--ergebnis', str(aus / 'ergebnis.json'), '--runden', str(beispielordner),
            '--bericht', str(tmp_path / 'bericht.md'),
            '--json', str(tmp_path / 'auswertung.json')]) == 0
        text = capsys.readouterr().out
        assert 'richtig 1 von 1 (100 %)' in text
        assert '0 Wahlen auf Glas, Spiegel oder Fenster' in text
        assert (tmp_path / 'bericht.md').read_text(encoding='utf-8').startswith('# Trockenlauf')
        kennzahlen = json.loads((tmp_path / 'auswertung.json').read_text(encoding='utf-8'))
        assert kennzahlen['modelle']['pruefmodell']['einordnung_richtig'] == 4
    finally:
        (beispielordner / 'beispiel_zimmer' / 'wahrheit.json').unlink()


def test_werkzeug_meldet_fehlende_runden_fehlenden_ki_rechner_und_fehlendes_modell(
        beispielordner, tmp_path, ki_attrappe, capsys):
    leer = tmp_path / 'leer'
    leer.mkdir()
    assert trockenlauf.main(['--runden', str(leer), '--ausgabe', str(tmp_path / 'a'),
                             '--nur-markieren']) == 2
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe', str(tmp_path / 'a'),
                             '--modell', 'gibt_es_nicht', '--url', ki_attrappe.url]) == 3
    assert 'nicht vorhanden' in capsys.readouterr().err
    ki_attrappe.schliessen()
    assert trockenlauf.main(['--runden', str(beispielordner), '--ausgabe', str(tmp_path / 'a'),
                             '--modell', 'pruefmodell', '--url', ki_attrappe.url]) == 3
    assert 'antwortet nicht' in capsys.readouterr().err


def test_wahrheit_mit_falscher_form_wird_abgelehnt(beispielordner, tmp_path, capsys):
    datei = beispielordner / 'beispiel_zimmer' / 'wahrheit.json'
    ergebnis = tmp_path / 'ergebnis.json'
    ergebnis.write_text(json.dumps({'runden': []}), encoding='utf-8')
    try:
        for inhalt in ({'ausgaenge': '2'}, {'ausgaenge': [True]},
                       {'ausgaenge': [1], 'arten': {'1': 'vorhang'}}):
            datei.write_text(json.dumps(inhalt), encoding='utf-8')
            assert trockenlauf_auswerten.main(['--ergebnis', str(ergebnis),
                                               '--runden', str(beispielordner)]) == 2
            assert 'wahrheit.json' in capsys.readouterr().err
    finally:
        datei.unlink()


def test_blickrunde_im_stand_ergibt_ein_bild_und_die_tuer_davor(tmp_path):
    """Ohne Drehung: Amadeus steht und schaut zur Tür (erstes Sehen, KI-0a)."""
    import math
    welt.erzeuge(tmp_path, 'im_stand', schritt_grad=0.01, gesamt_grad=0.12,
                 standpunkt=(1.8, 1.4, 0.0))
    vorbereitung = bereite_vor(Blickrunde.lade(tmp_path / 'im_stand'))
    assert not vorbereitung.auswahl['vollstaendig']
    assert [b['bild'] for b in vorbereitung.auswahl['bilder']] == [1]
    vorn = [o for o in vorbereitung.oeffnungen if abs(o.richtung_grad) < 10.0]
    assert len(vorn) == 1 and vorn[0].breite_m == pytest.approx(0.80, abs=0.08)
    assert vorbereitung.sichtbar[vorn[0].nr] == [1]
    assert 'schaut in eine Richtung' in vorbereitung.frage.text
    assert len(vorbereitung.bilder_fuer_ki()) == 2          # ein Foto und die Skizze
    assert math.isclose(vorbereitung.auswahl['gedreht_grad'], 0.0, abs_tol=1.0)
    # Im Stand wird vom Ort des LiDAR aus vermessen (24,5 cm vor der Antriebsmitte).
    assert vorbereitung.als_dict()['vermessen_von'] == 'lidar'
    assert vorbereitung.ursprung == pytest.approx((0.245, 0.0), abs=0.005)
    assert vorn[0].entfernung_m == pytest.approx(2.2, abs=0.06)   # ab Antriebsmitte


def test_im_stand_mit_offenem_tuerblatt_wird_die_tuer_und_nicht_die_blattspitze_vermessen(
        tmp_path):
    """Befund KI-0 vom 21.11.2026, nachgestellt: Blick von der Scharnierseite."""
    import math
    stand = (2.0, 2.2, math.radians(-20.0))
    welt.erzeuge(tmp_path, 'blatt', schritt_grad=0.01, gesamt_grad=0.15, standpunkt=stand,
                 tuerblatt_grad=90.0)
    vorbereitung = bereite_vor(Blickrunde.lade(tmp_path / 'blatt'))
    tuer, _, _ = welt.tuer_im_standpunktrahmen(stand)
    nah = [o for o in vorbereitung.oeffnungen
           if math.hypot(o.mitte[0] - tuer[0], o.mitte[1] - tuer[1]) < 0.15]
    assert len(nah) == 1, [o.als_dict() for o in vorbereitung.oeffnungen]
    assert nah[0].schluss == 'blatt'
    assert nah[0].breite_m == pytest.approx(0.80, abs=0.08)
    # Die Nummer steht auf dem sichtbaren Stück der Schwelle und damit im Foto.
    assert nah[0].marke is not None and vorbereitung.sichtbar[nah[0].nr] == [1]
    assert any(z['ergebnis'] == 'angeboten' and z['schluss'] == 'blatt'
               for z in vorbereitung.protokoll)


def test_pruefwerkzeug_nennt_angebotene_und_verworfene_luecken_ohne_bilddaten(tmp_path, capsys):
    """vermessung_pruefen.py: nur Maße einzelner Lücken, lesbar ohne Roboter."""
    import math
    import vermessung_pruefen
    welt.erzeuge(tmp_path / 'runden', 'stand_blatt', schritt_grad=0.01, gesamt_grad=0.15,
                 standpunkt=(2.0, 2.2, math.radians(-20.0)), tuerblatt_grad=90.0)
    welt.erzeuge(tmp_path / 'runden', 'gedreht')
    bericht = tmp_path / 'pruefung.md'
    assert vermessung_pruefen.main(['--runden', str(tmp_path / 'runden'),
                                    '--bericht', str(bericht)]) == 0
    text = capsys.readouterr().out
    assert bericht.read_text(encoding='utf-8').strip() == text.strip()
    assert '## stand_blatt' in text and 'vom Ort des LiDAR (im Stand)' in text
    assert '## gedreht' in text and 'von der Antriebsmitte' in text
    blatt = [z for z in text.splitlines() if '| blatt |' in z]
    assert len(blatt) == 1 and '0.8' in blatt[0] and 'blatt_0.' in blatt[0]
    # die Lücke bis zur Blattspitze steht mit Grund unter den verworfenen
    assert 'dahinter zu wenig freie Tiefe' in text
    assert 'bild_' not in text and 'scan_' not in text
    assert vermessung_pruefen.main(['--runden', str(tmp_path / 'leer')]) == 2


def test_wahrheit_eintragen_prueft_nummern_und_bewahrt_fruehere_angaben(beispielordner, tmp_path,
                                                                        capsys):
    import shutil
    import trockenlauf
    import trockenlauf_auswerten
    import wahrheit_eintragen
    runden = tmp_path / 'runden'
    shutil.copytree(beispielordner, runden)
    ausgabe = tmp_path / 'aus'
    assert trockenlauf.main(['--runden', str(runden), '--ausgabe', str(ausgabe),
                             '--nur-markieren']) == 0
    fest = ['--ergebnis', str(ausgabe / 'ergebnis.json'), '--runden', str(runden),
            '--name', 'beispiel_zimmer']
    assert wahrheit_eintragen.main(fest + ['--ausgaenge', '2', '--arten', '1=glas',
                                           '2=tuer_offen', '--raum', 'Zimmer']) == 0
    datei = runden / 'beispiel_zimmer' / 'wahrheit.json'
    erste = json.loads(datei.read_text(encoding='utf-8'))
    assert erste['ausgaenge'] == [2] and erste['ausgang_sichtbar'] is True
    assert erste['arten'] == {'1': 'glas', '2': 'tuer_offen'} and erste['raum'] == 'Zimmer'
    assert set(erste['lage']) == {'1', '2'} and len(erste['lage']['2']['mitte']) == 2
    # zweite Angabe: kein Ausgang unter den Nummern, aber einer ohne Nummer
    assert wahrheit_eintragen.main(fest + ['--arten', '1=moebelspalt',
                                           '--ausgang-ohne-nummer', 'ja',
                                           '--bemerkung', 'Tür weiter links']) == 0
    zweite = json.loads(datei.read_text(encoding='utf-8'))
    assert zweite['ausgaenge'] == [] and zweite['ausgang_sichtbar'] is True
    assert zweite['bemerkung'] == 'Tür weiter links'
    vorher = runden / 'beispiel_zimmer' / 'wahrheit_vorher_1.json'
    assert json.loads(vorher.read_text(encoding='utf-8')) == erste
    assert 'aufbewahrt als wahrheit_vorher_1.json' in capsys.readouterr().out
    # die Auswertung liest die neue Form
    assert trockenlauf_auswerten.lies_wahrheiten(runden)['beispiel_zimmer']['ausgaenge'] == []
    # falsche Angaben werden abgelehnt, die Datei bleibt
    assert wahrheit_eintragen.main(fest + ['--ausgaenge', '7']) == 2
    assert wahrheit_eintragen.main(fest + ['--arten', '1=rollo']) == 2
    assert wahrheit_eintragen.main(fest[:-1] + ['gibt_es_nicht']) == 2
    assert json.loads(datei.read_text(encoding='utf-8')) == zweite
