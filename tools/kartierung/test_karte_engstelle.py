"""Engstelle an einem Punkt: Türbreite, Streifen für den Planer, Lage der Kontur (ohne ROS)."""
import math
import re
from pathlib import Path

import pytest

import karte_engstelle as ke

RES, N = 0.05, 80                       # 4 m x 4 m, Ursprung (-2, -2)
URSPRUNG = (-2.0, -2.0)
WAND_I = 40                             # Wand entlang y bei x = 0,025 m
TUER_J = range(32, 48)                  # 16 freie Zellen = 0,80 m, Mitte bei y = 0
TUERMITTE = (0.025, 0.0)


def _belegt(i, j):
    return i == WAND_I and j not in TUER_J


def _karte(tmp_path, unbekannt=()):
    """Karte wie von map_saver: 0 belegt, 254 frei, 205 unbekannt; Zeile 0 ist oben."""
    pixel = bytearray()
    for zeile in range(N):
        j = N - 1 - zeile
        for i in range(N):
            pixel.append(0 if _belegt(i, j) else 205 if (i, j) in unbekannt else 254)
    (tmp_path/'karte.pgm').write_bytes(b'P5\n%d %d\n255\n' % (N, N) + bytes(pixel))
    (tmp_path/'karte.yaml').write_text(
        'image: karte.pgm\nmode: trinary\nresolution: 0.05\norigin: [-2.0, -2.0, 0]\n'
        'negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n', encoding='utf-8')
    return tmp_path/'karte.yaml'


def _kosten(i, j, radius=0.28):
    if _belegt(i, j):
        return 100
    if abs(i - WAND_I)*RES > radius + RES:
        return 0
    nah = min(math.hypot((i - WAND_I)*RES, (j - jj)*RES) for jj in range(N) if jj not in TUER_J)
    return 99 if nah <= radius else max(0, int(98*math.exp(-2.5*(nah - radius))))


def _kostenkarte(fluss=False, gekuerzt=False):
    werte = [_kosten(i, j) for j in range(N) for i in range(N)]
    kopf = ('header:\n  stamp:\n    sec: 1794765880\n    nanosec: 12\n  frame_id: map\ninfo:\n'
            '  map_load_time:\n    sec: 0\n    nanosec: 0\n  resolution: 0.05000000074505806\n'
            f'  width: {N}\n  height: {N}\n  origin:\n    position:\n      x: -2.0\n      y: -2.0\n'
            '      z: 0.0\n    orientation:\n      x: 0.0\n      y: 0.0\n      z: 0.0\n      w: 1.0\n')
    if gekuerzt:
        return kopf + "data:\n- 0\n- 0\n- '...'\n---\n"
    if fluss:
        return kopf + 'data: [' + ', '.join(str(w) for w in werte) + ']\n---\n'
    return kopf + 'data:\n' + ''.join(f'- {w}\n' for w in werte) + '---\n'


def test_door_width_and_planner_strip_from_a_saved_map(tmp_path):
    gitter = ke.karte_laden(_karte(tmp_path))
    e = ke.auswerten(gitter, TUERMITTE)
    g = e['engstelle']
    assert g['lichte_weite_m'] == 0.8 and g['zellmitten_m'] == 0.85
    assert g['punkt_neben_der_mitte_m'] == 0.0 and g['punkt_neben_der_linie_m'] == 0.0
    # Sechs Zellen liegen weiter als 0,28 m von beiden Pfosten: 0,30 m; rechnerisch 0,85 - 0,56.
    assert g['frei_m'] == pytest.approx(0.30, abs=0.02) and g['rechnerisch_frei_m'] == 0.29
    assert e['punkt'] == dict(klasse='frei', kostenwert=None, naechste_belegte_zelle_m=0.42,
                              fuer_planer_gesperrt=False, naechste_fuer_planer_freie_zelle_m=0.0)
    assert sorted(e['gruppen']) == sorted([len([j for j in range(N) if j < 32 and
                                                math.dist(gitter.mitte(WAND_I, j), TUERMITTE) <= 1.2]),
                                           len([j for j in range(N) if j > 47 and
                                                math.dist(gitter.mitte(WAND_I, j), TUERMITTE) <= 1.2])])


def test_a_point_close_to_one_post_is_blocked_for_the_planner(tmp_path):
    gitter = ke.karte_laden(_karte(tmp_path))
    e = ke.auswerten(gitter, (0.025, -0.17))                    # Zellmitte 0,25 m vom Pfosten
    assert e['punkt']['fuer_planer_gesperrt'] is True
    assert e['punkt']['naechste_belegte_zelle_m'] == pytest.approx(0.255, abs=0.006)
    assert e['punkt']['naechste_fuer_planer_freie_zelle_m'] == pytest.approx(0.045, abs=0.006)
    assert e['engstelle']['punkt_neben_der_mitte_m'] == 0.17
    # Ein größerer Planungsradius schließt die Tür: 0,85 m Zellmitten, zweimal 0,43 m.
    zu = ke.auswerten(gitter, TUERMITTE, radius_m=0.43)
    assert zu['engstelle']['frei_m'] == 0.0 and zu['engstelle']['rechnerisch_frei_m'] == 0.0
    assert zu['punkt']['fuer_planer_gesperrt'] is True


def test_slant_and_contour_position_are_measured_relative_to_the_passage(tmp_path):
    gitter = ke.karte_laden(_karte(tmp_path))
    lage = ke.auswerten(gitter, TUERMITTE, gier_grad=43.0)['lage']
    assert lage['schraegstand_grad'] == 43.0
    # (0,31 + 0,11 + 0,04) * sin 43 + 0,50 * cos 43 = 0,68 m; gerade 0,50 m.
    assert lage['gepolsterte_kontur_braucht_m'] == 0.68 and lage['gerade_braucht_m'] == 0.5
    assert lage['rest_bei_diesem_schraegstand_m'] == 0.12
    assert lage['belegte_in_gepolsterter_kontur'] == 0 and lage['belegte_in_kontur'] == 0
    n = lage['naechste_belegte']
    assert n['abstand_zur_gepolsterten_kontur_m'] == pytest.approx(0.06, abs=0.01)
    assert n['seite'] == 'vorn links' and n['vor_dem_roboter_m'] == pytest.approx(0.29, abs=0.01)
    # Dieselbe Richtung um 180 Grad gedreht ergibt denselben Schrägstand.
    assert ke.auswerten(gitter, TUERMITTE, gier_grad=223.0)['lage']['schraegstand_grad'] == 43.0
    # Dicht am Pfosten und schräg: Zellen liegen in der Kontur.
    eng = ke.auswerten(gitter, (0.0, -0.22), gier_grad=43.0)['lage']
    assert eng['belegte_in_gepolsterter_kontur'] >= 1
    assert eng['naechste_belegte']['abstand_zur_gepolsterten_kontur_m'] == 0.0
    assert eng['naechste_belegte']['seite'].endswith('rechts')


@pytest.mark.parametrize('fluss', [False, True])
def test_costmap_text_is_read_in_both_layouts_and_judged_by_cost(fluss):
    gitter = ke.kostenkarte_lesen(_kostenkarte(fluss=fluss))
    assert (gitter.breite, gitter.hoehe, gitter.art) == (N, N, 'kostenkarte')
    e = ke.auswerten(gitter, TUERMITTE)
    g = e['engstelle']
    assert g['lichte_weite_m'] == 0.8
    assert g['frei_m'] == pytest.approx(0.30, abs=0.02) and g['rechnerisch_frei_m'] is None
    assert 0 < g['kleinster_kostenwert'] < 99 and e['planungsradius_m'] is None
    assert e['punkt']['kostenwert'] == g['kleinster_kostenwert'] and not e['punkt']['fuer_planer_gesperrt']
    am_pfosten = ke.auswerten(gitter, (0.025, -0.17))
    assert am_pfosten['punkt']['kostenwert'] == 99 and am_pfosten['punkt']['fuer_planer_gesperrt']
    assert am_pfosten['punkt']['klasse'] == 'gesperrt'


def test_unusable_input_is_reported_not_guessed(tmp_path):
    with pytest.raises(ke.Eingabefehler, match='gekürzt'):
        ke.kostenkarte_lesen(_kostenkarte(gekuerzt=True))
    with pytest.raises(ke.Eingabefehler, match='Kopf unvollständig'):
        ke.kostenkarte_lesen('data:\n- 0\n')
    with pytest.raises(ke.Eingabefehler, match='erwartet 6400 Zellen, gefunden 6399'):
        ke.kostenkarte_lesen(_kostenkarte().replace('data:\n- 0\n', 'data:\n', 1))
    gitter = ke.karte_laden(_karte(tmp_path))
    with pytest.raises(ke.Eingabefehler, match='außerhalb'):
        ke.auswerten(gitter, (9.0, 9.0))
    assert ke.main(['--kostenkarte', str(tmp_path/'fehlt.txt'), '--mitte']) == 2


def test_no_bottleneck_without_two_sides_and_unknown_cells_are_counted(tmp_path):
    gitter = ke.karte_laden(_karte(tmp_path, unbekannt={(WAND_I, 38), (WAND_I, 39)}))
    e = ke.auswerten(gitter, TUERMITTE)
    assert e['engstelle']['unbekannte_zellen'] == 2            # 205 bleibt unbekannt trotz free_thresh
    weit_weg = ke.auswerten(gitter, (-1.5, 0.0), umkreis_m=0.4)
    assert weit_weg['engstelle'] is None and weit_weg['belegte_zellen_im_umkreis'] == 0
    assert 'keine gefunden' in ke.text(weit_weg)


def test_output_has_no_map_coordinates_and_the_tool_only_reads(tmp_path, capsys):
    pfad = _karte(tmp_path)
    assert ke.main(['--karte', str(pfad), '--punkt', '0.0137', '-0.1731', '--gier', '43.3',
                    '--json', str(tmp_path/'e.json')]) == 0
    ausgabe = capsys.readouterr().out
    assert 'lichte Weite 0.8 m' in ausgabe and 'Schrägstand zur Durchfahrtsachse 43.3°' in ausgabe
    assert '0.0137' not in ausgabe and '0.1731' not in ausgabe and '-2.0' not in ausgabe
    assert not re.search(r'\(\s*-?\d+\.\d+,\s*-?\d+\.\d+\s*\)', ausgabe)
    assert (tmp_path/'e.json').exists()
    (tmp_path/'k.txt').write_text(_kostenkarte(), encoding='utf-8')
    assert ke.main(['--kostenkarte', str(tmp_path/'k.txt'), '--mitte']) == 0
    assert 'Quelle: Kostenkarte' in capsys.readouterr().out
    quelle = Path(ke.__file__).read_text(encoding='utf-8')
    for verboten in ('rclpy', 'subprocess', 'socket', 'create_publisher', 'os.remove', 'unlink'):
        assert verboten not in quelle
    assert quelle.count("open(") == 2 and quelle.count("'w'") == 1   # eine Eingabe, ein lokales JSON
