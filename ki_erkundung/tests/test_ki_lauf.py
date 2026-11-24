"""Ablaufhilfe ki_lauf.py: Rundblick, Wahl, Frage, Antwort – ohne ROS, mit Attrappen.

Geprüft wird vor allem: Jedes Werkzeug läuft in seiner Umgebung, die Kamera
bekommt nach der Aufnahme genau ein SIGINT, und **nur ein „ja“ zu genau
dieser Wahl** startet das Fahrwerkzeug – mit genau den Argumenten aus KI-F9.
"""
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

import ki_lauf

TESTS = Path(__file__).resolve().parent
ATTRAPPEN = TESTS / 'ki_lauf_attrappen.py'


class Umfeld:
    """Ordner, Umgebungsdateien und Attrappen-Werkzeuge für einen Testlauf."""

    def __init__(self, wurzel: Path, szenario: str = ''):
        self.wurzel = wurzel
        self.werkzeuge = wurzel / 'werkzeuge'
        self.werkzeuge.mkdir(parents=True)
        for name in ('blickrunde_aufnehmen.py', 'ki_tuer_waehlen.py', 'fahrziel_senden.py'):
            shutil.copy(ATTRAPPEN, self.werkzeuge / name)
        self.umgebung = {}
        for rolle in ('kamera', 'stack'):
            datei = wurzel / f'{rolle}.env'
            datei.write_text(f'export KI_TEST_UMG={rolle}\nexport KI_TEST_ORDNER={wurzel}\n'
                             f'export KI_TEST_SZENARIO={szenario}\n', encoding='utf-8')
            self.umgebung[rolle] = datei

    def argumente(self, befehl, lauf='1', *mehr):
        """Angaben für den ganzen Lauf nur bei start (und pruefe-umgebung)."""
        basis = [befehl, '--auftrag', 'kiprobe', '--lauf', lauf,
                 '--basis', str(self.wurzel / 'laeufe')]
        if befehl not in ('start', 'pruefe-umgebung'):
            return basis + ['--warten', '20', *mehr]
        return basis + [
            '--umgebung-kamera', str(self.umgebung['kamera']),
            '--umgebung-stack', str(self.umgebung['stack']),
            '--python', sys.executable, '--runden', str(self.wurzel / 'runden'),
            '--wahl-ordner', str(self.wurzel / 'wahl'),
            # „oak.launch.py“ als Argument: Die Hilfe erkennt die Kamera daran.
            '--kamera-befehl', f'{sys.executable} {ATTRAPPEN} kamera oak.launch.py',
            # Die Attrappe der Kamera braucht unter Last etwas, bis sie Signale fängt.
            '--kamera-vorlauf', '1.0', '--nachlauf', '0.2',
            '--werkzeuge', str(self.werkzeuge),
            '--marke', str(self.wurzel / 'letzter_start.json'), *mehr]

    def protokoll(self):
        datei = self.wurzel / 'protokoll.jsonl'
        if not datei.exists():
            return []
        return [json.loads(z) for z in datei.read_text(encoding='utf-8').splitlines()]

    def eintraege(self, art):
        return [e for e in self.protokoll() if e['art'] == art]

    def lauf_ordner(self, lauf='1'):
        return self.wurzel / 'laeufe' / f'lauf{lauf}'


def warte_auf(bedingung, sekunden=10.0):
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        if bedingung():
            return True
        time.sleep(0.05)
    return bedingung()


def aufraeumen(umfeld):
    """Nach jedem Test: was dieser Test gestartet hat, mit je einem SIGINT beenden."""
    laeufe = umfeld.wurzel / 'laeufe'
    for ordner in (sorted(laeufe.iterdir()) if laeufe.exists() else []):
        ki_lauf.main(umfeld.argumente('aufraeumen', ordner.name[len('lauf'):]))


@pytest.fixture
def neues_umfeld(tmp_path):
    angelegt = []

    def neu(szenario=''):
        umfeld = Umfeld(tmp_path / f'u{len(angelegt)}', szenario)
        angelegt.append(umfeld)
        return umfeld
    yield neu
    for umfeld in angelegt:
        aufraeumen(umfeld)


@pytest.fixture
def umfeld(neues_umfeld):
    return neues_umfeld()


def _start_und_wahl(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    aus = capsys.readouterr().out
    assert 'Jetzt genau einmal die Mission starten.' in aus
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_OK
    return capsys.readouterr().out


def test_ganzer_lauf_mit_ja_faehrt_genau_mit_den_argumenten_aus_kif9(umfeld, capsys):
    aus = _start_und_wahl(umfeld, capsys)
    # Kamera und Aufnahme in der Umgebung der Kamera; Aufnahme endet selbst
    (aufnahme,) = umfeld.eintraege('aufnahme_start')
    assert aufnahme['umg'] == 'kamera'
    assert aufnahme['argv'][aufnahme['argv'].index('--bis-wartephase') + 1] == '0.2'
    assert aufnahme['argv'][aufnahme['argv'].index('--name') + 1] == 'kiprobe_lauf1'
    # die Kamera bekam nach dem Ende der Aufnahme genau ein SIGINT
    (kamera_ende,) = umfeld.eintraege('kamera_ende')
    assert kamera_ende['signale'] == ['SIGINT'] and kamera_ende['umg'] == 'kamera'
    assert kamera_ende['zeit'] >= umfeld.eintraege('aufnahme_ende')[0]['zeit']
    # die KI wurde für genau diese Runde gefragt, in der Umgebung der Kamera
    (waehlen,) = umfeld.eintraege('waehlen')
    assert waehlen['umg'] == 'kamera' and '--ueber-ros' in waehlen['argv']
    runde = waehlen['argv'][waehlen['argv'].index('--runde') + 1]
    assert runde == str(umfeld.wurzel / 'runden' / 'kiprobe_lauf1_20261124_000000')
    # Frage an den Menschen, ohne Pfade, mit Begründung (einzeilig), Gefahren und Minuten
    assert 'FRAGE AN CHRISTOPHER' in aus and '„Die KI hat gewählt. Die KI wählt Nr. 2' in aus
    assert 'Begründung der KI: Nr. 2 ist eine offene Tür.' in aus
    assert 'Gefahren laut KI: Kabel am Boden.' in aus and 'Minuten.)“' in aus
    assert 'Wahl-Datei' not in aus and '_wahl.json' not in aus
    assert 'Kamera und Aufnahme beendet. (Kamera rc=0' in aus
    kennung = json.loads((umfeld.lauf_ordner() / 'zustand.json').read_text())['wahl']['kennung']
    assert f'--kennung {kennung}' in aus
    # „Ja.“ fährt: genau --zur-tuer --wahl DATEI --hinter 0.45 --warten 60 --beobachten 600,
    # eingetragen mit genau der ausgegebenen Befehlszeile (auch mit eigenem --basis)
    zeile = next(z for z in aus.splitlines() if ' antwort --auftrag ' in z)
    befehl = shlex.split(zeile.replace('<seine Antwort>', 'Ja.'))
    assert befehl[0] == 'python3' and Path(befehl[1]).resolve() == Path(ki_lauf.__file__).resolve()
    rc = ki_lauf.main(befehl[2:])
    aus = capsys.readouterr().out
    assert rc == ki_lauf.RC_OK, aus
    (fahren,) = umfeld.eintraege('fahren')
    datei = umfeld.lauf_ordner() / 'wahl_gefahren.json'     # Kopie der geprüften Bytes
    assert fahren['umg'] == 'stack'
    assert fahren['argv'] == ['--zur-tuer', '--wahl', str(datei), '--hinter', '0.45', '--warten',
                              '60', '--beobachten', '600']
    assert datei.read_bytes() == (umfeld.wurzel / 'wahl' /
                                  'kiprobe_lauf1_20261124_000000_wahl.json').read_bytes()
    assert 'Durchfahrt abgeschlossen.' in aus and 'LAUF ergebnis=durchfahrt werkzeug_rc=0' in aus
    # eine zweite Antwort wird nicht mehr angenommen, der interne Fahrbefehl auch nicht
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert ki_lauf.main(['_fahrt', '--ordner', str(umfeld.lauf_ordner())]) == ki_lauf.RC_NEIN
    assert len(umfeld.eintraege('fahren')) == 1
    # ein zweiter Aufruf von wahl fragt die KI nicht noch einmal
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_OK
    assert len(umfeld.eintraege('waehlen')) == 1


@pytest.mark.parametrize('wortlaut', ['nein es ist ein Fensterrollo', 'ja, aber langsam', '',
                                      'jawohl', 'nein'])
def test_jede_andere_antwort_beendet_ohne_fahrt(umfeld, capsys, wortlaut):
    _start_und_wahl(umfeld, capsys)
    kennung = json.loads((umfeld.lauf_ordner() / 'zustand.json').read_text())['wahl']['kennung']
    rc = ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                       '--wortlaut', wortlaut))
    aus = capsys.readouterr().out
    assert rc == ki_lauf.RC_OK
    (fahren,) = umfeld.eintraege('fahren')
    assert fahren['umg'] == 'stack'
    assert fahren['argv'] == ['--ende', '--quelle', 'mensch', '--warten', '60']
    assert 'LAUF ergebnis=nicht_gefahren grund=kein_ja' in aus
    christopher = (umfeld.lauf_ordner() / 'christopher.txt').read_text(encoding='utf-8')
    assert christopher.rstrip('\n').endswith(wortlaut)


def test_falsche_kennung_oder_geaenderte_wahl_ruft_nichts_auf(umfeld, capsys):
    _start_und_wahl(umfeld, capsys)
    zustand = json.loads((umfeld.lauf_ordner() / 'zustand.json').read_text())
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', '000000',
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert 'passt nicht' in capsys.readouterr().out
    Path(zustand['wahl']['datei']).write_text('{"nr": 1}', encoding='utf-8')   # verändert
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', zustand['wahl']['kennung'],
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert 'geändert' in capsys.readouterr().out
    assert umfeld.eintraege('fahren') == []


def test_ohne_wahl_der_ki_keine_frage_aber_ende_an_den_erkunder(neues_umfeld, capsys):
    umfeld = neues_umfeld('keine_wahl')
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'FRAGE' not in aus and 'LAUF ergebnis=nicht_gefahren grund=keine_wahl' in aus
    (fahren,) = umfeld.eintraege('fahren')
    assert fahren['umg'] == 'stack' and fahren['argv'] == ['--ende', '--quelle', 'ki',
                                                           '--warten', '60']
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', 'abcdef',
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert len(umfeld.eintraege('fahren')) == 1


def test_zu_wenige_bilder_beendet_kamera_und_aufnahme_vor_der_mission(neues_umfeld, capsys):
    # wie am Roboter: ohne Mission kommt keine Wartephase, die Aufnahme liefe weiter
    umfeld = neues_umfeld('langsam_ohne_wartephase')
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'Keine Mission starten' in aus and 'Bildrate 0.4 Hz' in aus
    assert warte_auf(lambda: umfeld.eintraege('kamera_ende'))
    assert umfeld.eintraege('aufnahme_ende')[0]['signale'] == ['SIGINT']
    assert umfeld.eintraege('kamera_ende')[0]['signale'] == ['SIGINT']
    assert umfeld.eintraege('waehlen') == []                 # nach Abbruch keine Frage an die KI


def test_ohne_wartephase_wird_nach_der_frist_abgebrochen(neues_umfeld, capsys):
    umfeld = neues_umfeld('ohne_wartephase')
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    rc = ki_lauf.main(umfeld.argumente('wahl', '1', '--hoechstens', '1.5'))
    aus = capsys.readouterr().out
    assert rc == ki_lauf.RC_KEINE_RUNDE and 'noch keine Wartephase' in aus
    assert umfeld.eintraege('waehlen') == [] and umfeld.eintraege('fahren') == []
    assert warte_auf(lambda: umfeld.eintraege('kamera_ende'))


def test_vorlauf_im_stand_fragt_die_ki_aber_niemanden_und_misst_nur(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start', 'v', '--nur-stand', '--dauer-stand',
                                         '1')) == ki_lauf.RC_OK
    (aufnahme,) = umfeld.eintraege('aufnahme_start')
    assert '--bis-wartephase' not in aufnahme['argv']
    assert aufnahme['argv'][aufnahme['argv'].index('--dauer') + 1] == '1.0'
    assert ki_lauf.main(umfeld.argumente('wahl', 'v')) == ki_lauf.RC_OK
    aus = capsys.readouterr().out
    assert 'Vorlauf im Stand' in aus and 'FRAGE' not in aus
    zustand = json.loads((umfeld.lauf_ordner('v') / 'zustand.json').read_text())
    assert ki_lauf.main(umfeld.argumente('antwort', 'v', '--kennung', zustand['wahl']['kennung'],
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert ki_lauf.main(umfeld.argumente('messen', 'v')) == 0
    (fahren,) = umfeld.eintraege('fahren')
    assert '--nur-messen' in fahren['argv'] and fahren['umg'] == 'stack'
    # auch der interne Fahrbefehl fährt im Vorlauf nicht
    assert ki_lauf.main(['_fahrt', '--ordner', str(umfeld.lauf_ordner('v'))]) == ki_lauf.RC_NEIN
    assert ki_lauf.lies_json(umfeld.lauf_ordner('v') / 'fahrt.json')['grund'] == \
        'Vorlauf im Stand'
    assert len(umfeld.eintraege('fahren')) == 1


def test_derselbe_lauf_startet_nicht_zweimal(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_NEIN
    assert 'gibt es schon' in capsys.readouterr().out
    ki_lauf.main(umfeld.argumente('wahl'))
    # auch ein Ordner ohne Zustand (alte Ausgaben) wird nicht wiederverwendet
    umfeld.lauf_ordner('7').mkdir(parents=True)
    assert ki_lauf.main(umfeld.argumente('start', '7')) == ki_lauf.RC_NEIN
    assert 'gibt es schon' in capsys.readouterr().out
    assert len(umfeld.eintraege('kamera_start')) == 1


def test_aufraeumen_beendet_eine_laufende_fahrt_mit_genau_einem_sigint(neues_umfeld, capsys):
    umfeld = neues_umfeld('lange_fahrt')
    _start_und_wahl(umfeld, capsys)
    kennung = json.loads((umfeld.lauf_ordner() / 'zustand.json').read_text())['wahl']['kennung']
    rc = ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung, '--wortlaut', 'ja',
                                       '--warten', '1'))
    assert rc == ki_lauf.RC_LAEUFT and 'weiter mit: verfolgen' in capsys.readouterr().out
    assert ki_lauf.main(umfeld.argumente('aufraeumen')) == ki_lauf.RC_OK
    assert warte_auf(lambda: umfeld.eintraege('fahren_abgebrochen'))
    assert umfeld.eintraege('fahren_abgebrochen')[0]['signale'] == ['SIGINT']
    assert ki_lauf.main(umfeld.argumente('verfolgen')) == ki_lauf.RC_NEIN
    assert 'werkzeug_rc=130' in capsys.readouterr().out


def test_nur_ein_klares_ja():
    for ja in ('ja', 'Ja', 'JA', 'Ja.', ' ja! ', '„ja“', "'ja'"):
        assert ki_lauf.ist_ja(ja), ja
    for nein in ('nein', 'ja, aber', 'ja aber', 'jawohl', 'ok', '', 'ja ja', 'naja',
                 'ja?', 'Ja?', 'ja...', 'ja…', 'ja!?', 'ja?!', 'ja-'):
        assert not ki_lauf.ist_ja(nein), nein


def test_fremde_pid_bekommt_nie_ein_signal(tmp_path):
    fremd = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        assert not ki_lauf.ein_sigint(fremd.pid, 'fahrziel_senden.py')
        assert not ki_lauf.ein_sigint(0, 'x') and not ki_lauf.ein_sigint(None, 'x')
        assert fremd.poll() is None
    finally:
        fremd.send_signal(signal.SIGTERM)
        fremd.wait(timeout=5)


def test_umgebungen_werden_verglichen(umfeld, capsys):
    umfeld.umgebung['stack'].write_text('export ROS_DOMAIN_ID=11\n', encoding='utf-8')
    umfeld.umgebung['kamera'].write_text('export ROS_DOMAIN_ID=12\n', encoding='utf-8')
    argumente = [a for a in umfeld.argumente('pruefe-umgebung') if a not in ('--lauf', '1')]
    assert ki_lauf.main(argumente) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'ROS_DOMAIN_ID ist in beiden Umgebungen verschieden' in aus
    assert 'passen NICHT' in aus
    umfeld.umgebung['stack'].unlink()
    assert ki_lauf.main(argumente) == ki_lauf.RC_NEIN
    assert 'Umgebungsdatei fehlt' in capsys.readouterr().out


def test_statisch_keine_gruppen_signale_kein_ros_und_nichts_gesendet():
    text = (Path(ki_lauf.__file__)).read_text(encoding='utf-8')
    for verboten in ('killpg', 'os.kill(-', 'pkill', 'killall', 'SIGKILL', 'kill -9',
                     'ros2 topic pub', 'import rclpy', 'create_publisher', 'mission_manager'):
        assert verboten not in text, verboten
    assert 'start_new_session=True' in text and "os.kill(int(pid), signal.SIGINT)" in text
    assert os.access(ki_lauf.__file__, os.R_OK)


def test_eine_shell_mit_dem_namen_im_befehl_gilt_nicht_als_kamera():
    """AGENTS.md: „pgrep -f trifft die eigene Shell“ – nur ganze Argumente zählen."""
    text = subprocess.Popen(['bash', '-c', 'sleep 20 # oak.launch.py _rundblick '
                             'blickrunde_aufnehmen.py'])
    echt = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)',
                             'oak.launch.py'])
    try:
        assert warte_auf(lambda: ki_lauf.argumente(echt.pid) is not None
                         and 'oak.launch.py' in ki_lauf.argumente(echt.pid))
        gefunden = ki_lauf.laufende('oak.launch.py', '_rundblick', 'blickrunde_aufnehmen.py')
        assert echt.pid in gefunden and text.pid not in gefunden
        assert ki_lauf.passt(['python3', '/a/b/blickrunde_aufnehmen.py', '--x'],
                             'blickrunde_aufnehmen.py')
        assert not ki_lauf.passt(['bash', '-c', 'echo blickrunde_aufnehmen.py'],
                                 'blickrunde_aufnehmen.py')
        # (Elternprozess 0: Test als PID 1 in eigenem PID-Namensraum, unshare --pid)
        assert os.getpid() in ki_lauf.vorfahren()
        assert os.getppid() in ki_lauf.vorfahren() or os.getppid() == 0
    finally:
        for prozess in (text, echt):
            prozess.send_signal(signal.SIGTERM)
            prozess.wait(timeout=5)


WAHL_BEISPIEL = {
    'schema': 1, 'art': 'ki_wahl', 'runde': 'probe', 'erzeugt_s': 1.0, 'quelle': 'ki',
    'nr': 2, 'einordnung': 'tuer_offen', 'sicherheit': None,
    'begruendung': 'Simulation: gespielte KI\nwählt Nr. 2', 'gefahren': [],
    'breite_m': 0.83, 'tuerbreit': True, 'entfernung_m': 2.8, 'richtung_ende_grad': 9.0,
    'rahmen': 'map', 'mitte': [1.0, 2.0]}


def test_frage_setzt_satzzeichen_wo_sie_fehlen():
    zeilen = ['Die KI wählt Nr. 1: Durchgang.',                 # Text zählt nicht, nur die Datei
              '  Nr. 2: 0,83 m breit; KI: offene Tür  ← gewählt']
    frage = ki_lauf.baue_frage(WAHL_BEISPIEL, zeilen, 'die Labortür')
    assert frage.startswith('„Die KI hat gewählt. Die KI wählt Nr. 2: offene Tür, 0,83 m breit')
    assert 'wählt Nr. 2. Was sie in jeder Nummer sieht' in frage
    assert 'Blickrichtung. Begründung der KI: Simulation: gespielte KI wählt' in frage
    assert 'Blickrichtung..' not in frage and 'Nr. 1' not in frage and 'Gefahren' not in frage
    assert frage.endswith("Schreib ‚ja' oder ‚nein'.“") and 'Minute' not in frage
    assert ki_lauf.mit_restzeit(frage, 370.0).endswith(
        "‚nein'. (Der Erkunder wartet noch etwa 6 Minuten.)“")


def test_restzeit_in_worten():
    assert ki_lauf.zeit_satz(None) == ''
    assert ki_lauf.zeit_satz(125.0) == '(Der Erkunder wartet noch etwa 2 Minuten.)'
    assert ki_lauf.zeit_satz(119.0) == '(Der Erkunder wartet noch etwa eine Minute.)'
    assert ki_lauf.zeit_satz(30.0) == '(Der Erkunder wartet noch weniger als eine Minute.)'


def test_wahl_aus_datei_prueft_kennung_und_inhalt(tmp_path):
    datei = tmp_path / 'w.json'
    datei.write_text(json.dumps(WAHL_BEISPIEL), encoding='utf-8')
    kennung = ki_lauf.kennung_der_datei(datei)
    daten, grund = ki_lauf.wahl_aus_datei(datei, kennung)
    assert daten == WAHL_BEISPIEL and grund == ''
    assert ki_lauf.wahl_aus_datei(datei, '000000') == (None, 'Wahl-Datei passt nicht zur Kennung')
    assert ki_lauf.wahl_aus_datei(tmp_path / 'fehlt.json', kennung) == (None, 'Wahl-Datei fehlt')
    ohne_breite = {k: v for k, v in WAHL_BEISPIEL.items() if k != 'breite_m'}
    for inhalt, grund in ((b'kein json', 'Wahl-Datei ist kein JSON'),
                          (b'\xff\xfe', 'Wahl-Datei ist kein JSON'),
                          (json.dumps([1, 2]).encode(), 'keine Wahl der KI'),
                          (json.dumps({**WAHL_BEISPIEL, 'quelle': 'mensch'}).encode(),
                           'keine Wahl der KI'),
                          (json.dumps({**WAHL_BEISPIEL, 'nr': True}).encode(), 'Nummer fehlt'),
                          (json.dumps(ohne_breite).encode(), 'Maße der Wahl fehlen')):
        datei.write_bytes(inhalt)
        assert ki_lauf.wahl_aus_datei(datei, ki_lauf.kennung_der_datei(datei)) == (None, grund)


def test_frage_kommt_aus_der_wahl_datei_nicht_aus_dem_text(neues_umfeld, capsys):
    umfeld = neues_umfeld('falscher_text')
    _start_und_wahl(umfeld, capsys)
    frage = (umfeld.lauf_ordner() / 'frage.txt').read_text(encoding='utf-8').rstrip('\n')
    assert 'Die KI wählt Nr. 2: offene Tür, 0,83 m breit, 2,4 m' in frage
    assert 'Begründung der KI: Nr. 2 ist eine offene Tür.' in frage
    assert 'Gefahren laut KI: Kabel am Boden.' in frage
    assert 'Durchgang' not in frage and 'Die KI wählt Nr. 1' not in frage and '\n' not in frage


def test_wahl_datei_nach_der_ki_geaendert_keine_frage_und_ende(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    begleiter = umfeld.lauf_ordner() / 'begleiter.json'
    assert warte_auf(lambda: ki_lauf.lies_json(begleiter).get('phase') == 'fertig', 30)
    datei = Path(ki_lauf.lies_json(begleiter)['wahl_datei'])
    datei.write_text(datei.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'passt nicht zur Kennung' in aus and 'FRAGE' not in aus
    (fahren,) = umfeld.eintraege('fahren')
    assert fahren['argv'] == ['--ende', '--quelle', 'ki', '--warten', '60']
    kennung = ki_lauf.lies_json(begleiter)['kennung']
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert len(umfeld.eintraege('fahren')) == 1


def _fremde_kamera():
    """Ein Prozess, der wie eine Kamera aussieht (ganzes Argument oak.launch.py)."""
    kamera = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)',
                               'oak.launch.py'])
    assert warte_auf(lambda: kamera.pid in ki_lauf.laufende('oak.launch.py'))
    return kamera


def _beende(prozess):
    prozess.send_signal(signal.SIGTERM)
    prozess.wait(timeout=5)


def test_keine_frage_und_keine_fahrt_solange_eine_kamera_laeuft(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start')) == ki_lauf.RC_OK
    kamera = _fremde_kamera()
    try:
        assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_LAEUFT
        aus = capsys.readouterr().out
        assert 'Noch keine Frage' in aus and 'FRAGE' not in aus
    finally:
        _beende(kamera)
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_OK
    assert 'FRAGE AN CHRISTOPHER' in capsys.readouterr().out
    kennung = json.loads((umfeld.lauf_ordner() / 'zustand.json').read_text())['wahl']['kennung']
    kamera = _fremde_kamera()
    try:
        assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                             '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
        assert 'Antwort nicht eingetragen' in capsys.readouterr().out
        assert umfeld.eintraege('fahren') == []
        assert not (umfeld.lauf_ordner() / 'christopher.txt').exists()
    finally:
        _beende(kamera)
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_OK
    (fahren,) = umfeld.eintraege('fahren')
    assert fahren['argv'][0] == '--zur-tuer'


def _zustand(umfeld, lauf='1'):
    return json.loads((umfeld.lauf_ordner(lauf) / 'zustand.json').read_text(encoding='utf-8'))


def _wartephase_verschieben(umfeld, sekunden, lauf='1'):
    """Als wartete der Erkunder schon so viel länger auf ein Fahrziel."""
    zustand = ki_lauf.Lauf(umfeld.lauf_ordner(lauf))
    wahl = zustand.zustand()['wahl']
    wahl['wartephase_unix'] = str(float(wahl['wartephase_unix']) - sekunden)
    zustand.merke(wahl=wahl)


def test_waehrend_einer_fahrt_kein_neuer_start(neues_umfeld, capsys):
    umfeld = neues_umfeld('lange_fahrt')
    _start_und_wahl(umfeld, capsys)
    kennung = _zustand(umfeld)['wahl']['kennung']
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung, '--wortlaut', 'ja',
                                         '--warten', '1')) == ki_lauf.RC_LAEUFT
    capsys.readouterr()
    assert ki_lauf.main(umfeld.argumente('start', '2')) == ki_lauf.RC_NEIN
    assert 'Eine Fahrt läuft noch' in capsys.readouterr().out
    assert not umfeld.lauf_ordner('2').exists()
    assert len(umfeld.eintraege('fahren')) == 1


def test_eine_andere_fahrt_sperrt_die_antwort(umfeld, capsys):
    _start_und_wahl(umfeld, capsys)
    kennung = _zustand(umfeld)['wahl']['kennung']
    fahrt = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)',
                              'fahrziel_senden.py'])         # sieht aus wie das Fahrwerkzeug
    try:
        assert warte_auf(lambda: fahrt.pid in ki_lauf.laufende('fahrziel_senden.py'))
        assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                             '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
        assert 'Eine Fahrt läuft noch' in capsys.readouterr().out
    finally:
        _beende(fahrt)
    assert umfeld.eintraege('fahren') == [] and 'antwort' not in _zustand(umfeld)


def test_zu_spaete_antwort_ruft_nichts_auf_auch_kein_ende(umfeld, capsys):
    """Gegenprüfung 24.11.2026: Ein Ja nach der Frist hätte den Erkunder eines neuen Laufs
    treffen können, ein Nein ihm ein Ende geschickt."""
    _start_und_wahl(umfeld, capsys)
    kennung = _zustand(umfeld)['wahl']['kennung']
    _wartephase_verschieben(umfeld, 500)
    for wortlaut in ('ja', 'nein'):
        assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                             '--wortlaut', wortlaut)) == ki_lauf.RC_NEIN
        assert 'Zu spät für Lauf 1: die Frist des Erkunders ist abgelaufen' in \
            capsys.readouterr().out
    assert umfeld.eintraege('fahren') == [] and 'antwort' not in _zustand(umfeld)
    assert not (umfeld.lauf_ordner() / 'christopher.txt').exists()
    # die zweite Prüfung im internen Fahrbefehl greift ebenso
    lauf = ki_lauf.Lauf(umfeld.lauf_ordner())
    zustand = {**lauf.zustand(), 'antwort': {'ja': True, 'wortlaut': 'ja', 'kennung': kennung}}
    assert 'Frist' in ki_lauf.fahrt_erlaubt(lauf, zustand)


def test_antwort_auf_einen_aelteren_lauf_faehrt_nicht(umfeld, capsys):
    """Nach dem Start einer Wiederholung (1w) gilt nur noch deren Frage."""
    _start_und_wahl(umfeld, capsys)
    k1 = _zustand(umfeld)['wahl']['kennung']
    assert ki_lauf.main(umfeld.argumente('start', '1w')) == ki_lauf.RC_OK
    assert ki_lauf.main(umfeld.argumente('wahl', '1w')) == ki_lauf.RC_OK
    capsys.readouterr()
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', k1,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert 'danach wurde lauf1w gestartet' in capsys.readouterr().out
    assert umfeld.eintraege('fahren') == []
    k2 = _zustand(umfeld, '1w')['wahl']['kennung']
    assert ki_lauf.main(umfeld.argumente('antwort', '1w', '--kennung', k2,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_OK
    (fahren,) = umfeld.eintraege('fahren')
    assert Path(fahren['argv'][2]).read_bytes() == (
        umfeld.wurzel / 'wahl' / 'kiprobe_lauf1w_20261124_000000_wahl.json').read_bytes()


def test_nach_der_frist_keine_frage_und_kein_ende(neues_umfeld, capsys):
    umfeld = neues_umfeld()
    assert ki_lauf.main(umfeld.argumente('start', '1', '--frist', '1')) == ki_lauf.RC_OK
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'Keine Frage an den Menschen: die Frist des Erkunders ist abgelaufen' in aus
    assert 'FRAGE' not in aus and 'LAUF ergebnis=nicht_gefahren grund=zu_spaet' in aus
    ohne_wahl = neues_umfeld('keine_wahl')
    assert ki_lauf.main(ohne_wahl.argumente('start', '1', '--frist', '1')) == ki_lauf.RC_OK
    assert ki_lauf.main(ohne_wahl.argumente('wahl')) == ki_lauf.RC_NEIN
    assert 'Kein Ende gesendet: die Frist des Erkunders ist abgelaufen' in capsys.readouterr().out
    assert umfeld.eintraege('fahren') == [] and ohne_wahl.eintraege('fahren') == []


def test_frage_nennt_bei_jedem_aufruf_die_restzeit_von_jetzt(umfeld, capsys):
    assert ki_lauf.main(umfeld.argumente('start', '1', '--tuer', 'die Küchentür')) == \
        ki_lauf.RC_OK
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_OK
    aus = capsys.readouterr().out
    assert 'Ist die gewählte Öffnung die Küchentür' in aus and 'etwa 6 Minuten.)“' in aus
    _wartephase_verschieben(umfeld, 300)
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_OK
    aus = capsys.readouterr().out
    assert 'steht schon fest' in aus and 'etwa eine Minute.)“' in aus and 'Minuten' not in aus
    _wartephase_verschieben(umfeld, 100)
    ki_lauf.main(umfeld.argumente('wahl'))
    assert 'weniger als eine Minute.)“' in capsys.readouterr().out
    _wartephase_verschieben(umfeld, 30)
    assert ki_lauf.main(umfeld.argumente('wahl')) == ki_lauf.RC_NEIN
    aus = capsys.readouterr().out
    assert 'Nicht mehr fragen: die Frist des Erkunders ist abgelaufen' in aus and '„' not in aus


def test_angaben_fuer_den_ganzen_lauf_gibt_es_nur_beim_start(capsys):
    """Gegenprüfung 24.11.2026: „wahl --tuer …“ wurde still übergangen."""
    for befehl in ('wahl', 'antwort', 'verfolgen', 'messen', 'aufraeumen'):
        mehr = ['--kennung', 'abcdef', '--wortlaut', 'ja'] if befehl == 'antwort' else []
        with pytest.raises(SystemExit) as ende:
            ki_lauf.main([befehl, '--lauf', '1', *mehr, '--tuer', 'die Küchentür'])
        assert ende.value.code == 2, befehl
        assert '--tuer' in capsys.readouterr().err, befehl


def test_zwei_schreiber_verlieren_nichts(tmp_path):
    """Gegenprüfung 24.11.2026: Mit einer gemeinsamen Nebendatei verlor zustand.json
    Einträge (zweimal „verfolgen“ gleichzeitig)."""
    ordner = tmp_path / 'lauf1'
    ordner.mkdir()
    lauf = ki_lauf.Lauf(ordner)
    ki_lauf.schreibe_json(lauf.zustand_datei, {'wahl': {'rc': 0}, 'start_unix': 1.0})
    code = ('import sys\nsys.path.insert(0, sys.argv[1])\nimport ki_lauf\n'
            'lauf = ki_lauf.Lauf(sys.argv[2])\n'
            'for i in range(300):\n    lauf.merke(**{sys.argv[3]: i})\n')
    werkzeuge = str(Path(ki_lauf.__file__).resolve().parent)
    schreiber = [subprocess.Popen([sys.executable, '-c', code, werkzeuge, str(ordner), name],
                                  stderr=subprocess.PIPE, text=True) for name in ('a', 'b')]
    for prozess in schreiber:
        _, fehler = prozess.communicate(timeout=120)
        assert prozess.returncode == 0, fehler
    zustand = lauf.zustand()
    assert zustand['a'] == 299 and zustand['b'] == 299 and zustand['wahl'] == {'rc': 0}
    assert not list(ordner.glob('*.neu'))


def test_interner_fahrbefehl_ohne_ja_tut_nichts(umfeld, capsys):
    _start_und_wahl(umfeld, capsys)
    ordner = umfeld.lauf_ordner()
    assert ki_lauf.main(['_fahrt', '--ordner', str(ordner)]) == ki_lauf.RC_NEIN
    assert ki_lauf.lies_json(ordner / 'fahrt.json')['grund'] == 'kein Ja eingetragen'
    # danach fährt auch ein Ja zu diesem Lauf nicht mehr: es gab schon einen Fahrversuch
    kennung = json.loads((ordner / 'zustand.json').read_text())['wahl']['kennung']
    assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                         '--wortlaut', 'ja')) == ki_lauf.RC_NEIN
    assert 'schon einen Fahrversuch' in capsys.readouterr().out
    assert umfeld.eintraege('fahren') == []


def test_interne_befehle_stehen_nicht_in_der_hilfe(capsys):
    with pytest.raises(SystemExit):
        ki_lauf.main(['--help'])
    hilfe = capsys.readouterr().out
    assert 'antwort' in hilfe and '_fahrt' not in hilfe and '_rundblick' not in hilfe


def test_antwort_gilt_nicht_nach_einem_start_in_anderem_auftrag_oder_ordner(umfeld, capsys):
    """Gegenprüfung 24.11.2026: Ein späterer Lauf wurde nur im selben Ordner erkannt."""
    _start_und_wahl(umfeld, capsys)
    kennung = _zustand(umfeld)['wahl']['kennung']
    andere = umfeld.argumente('start', '1')
    andere[andere.index('--auftrag') + 1] = 'kiandere'
    andere[andere.index('--basis') + 1] = str(umfeld.wurzel / 'andere_laeufe')
    try:
        assert ki_lauf.main(andere) == ki_lauf.RC_OK
        capsys.readouterr()
        for wortlaut in ('ja', 'nein'):
            assert ki_lauf.main(umfeld.argumente('antwort', '1', '--kennung', kennung,
                                                 '--wortlaut', wortlaut)) == ki_lauf.RC_NEIN
            aus = capsys.readouterr().out
            assert 'danach wurde' in aus and 'andere_laeufe/lauf1 gestartet' in aus
        assert umfeld.eintraege('fahren') == []
    finally:
        ki_lauf.main(['aufraeumen', '--auftrag', 'kiandere', '--lauf', '1',
                      '--basis', str(umfeld.wurzel / 'andere_laeufe')])


def test_frist_und_zeiten_nur_als_endliche_zahlen(umfeld, capsys):
    """Gegenprüfung 24.11.2026: Mit „nan“ als Frist fuhr ein Ja noch nach drei Stunden."""
    for frist in ('nan', 'inf', '0', '-5', '2000'):
        assert ki_lauf.main(umfeld.argumente('start', '1', '--frist', frist)) == ki_lauf.RC_NEIN
        assert '--frist muss zwischen 0 und 1800 s liegen' in capsys.readouterr().out
    assert not umfeld.lauf_ordner().exists()
    jetzt = time.time()
    assert ki_lauf.restzeit_s({'frist': 420.0}, 'nan') is None
    assert ki_lauf.restzeit_s({'frist': 420.0}, 'inf') is None
    assert ki_lauf.restzeit_s({'frist': 420.0}, str(jetzt + 3600)) is None   # in der Zukunft
    assert ki_lauf.restzeit_s({'frist': float('nan')}, str(jetzt)) is None
    assert ki_lauf.zeit_satz(float('inf')) == ''
    lauf = ki_lauf.Lauf(umfeld.wurzel)
    assert ki_lauf.nicht_mehr_dran(lauf, {'frist': 420.0}, str(jetzt)) == \
        'Startzeit dieses Laufs unbekannt'
    assert ki_lauf.nicht_mehr_dran(lauf, {'frist': 420.0, 'start_unix': jetzt}, 'nan') == \
        'Beginn der Wartephase unbekannt'


def test_warten_des_fahrwerkzeugs_endet_vor_der_frist():
    jetzt = time.time()
    z = {'frist': 420.0}
    assert ki_lauf.warten_auf_den_erkunder(z, str(jetzt - 2)) == '60'
    assert 23 <= int(ki_lauf.warten_auf_den_erkunder(z, str(jetzt - 390))) <= 25
    assert ki_lauf.warten_auf_den_erkunder(z, 'nan') == '1'


def test_interner_fahrbefehl_prueft_dasselbe_wie_antwort(umfeld, capsys):
    """Gegenprüfung 24.11.2026: _fahrt prüfte weder Kamera noch andere Fahrt noch die
    Kennung des Ja."""
    _start_und_wahl(umfeld, capsys)
    lauf = ki_lauf.Lauf(umfeld.lauf_ordner())
    kennung = _zustand(umfeld)['wahl']['kennung']
    zustand = {**lauf.zustand(), 'antwort': {'ja': True, 'wortlaut': 'ja', 'kennung': '000000'}}
    assert ki_lauf.fahrt_erlaubt(lauf, zustand) == 'das Ja gilt einer anderen Wahl'
    zustand['antwort']['kennung'] = kennung
    assert ki_lauf.fahrt_erlaubt(lauf, zustand) is None
    kamera = _fremde_kamera()
    try:
        assert 'Kamera oder Aufnahme laufen noch' in ki_lauf.fahrt_erlaubt(lauf, zustand)
    finally:
        _beende(kamera)
    fahrt = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)',
                              'fahrziel_senden.py'])
    try:
        assert warte_auf(lambda: fahrt.pid in ki_lauf.laufende('fahrziel_senden.py'))
        assert 'eine andere Fahrt läuft' in ki_lauf.fahrt_erlaubt(lauf, zustand)
    finally:
        _beende(fahrt)


def test_antwort_prueft_und_traegt_unter_einer_sperre_ein(umfeld, capsys):
    """Gegenprüfung 24.11.2026: Zwei gleichzeitige Antworten ergaben Fahrt und Ende."""
    _start_und_wahl(umfeld, capsys)
    kennung = _zustand(umfeld)['wahl']['kennung']
    lauf = ki_lauf.Lauf(umfeld.lauf_ordner())
    with lauf.sperre('antwort'):
        zweite = subprocess.Popen(
            [sys.executable, str(Path(ki_lauf.__file__).resolve()),
             *umfeld.argumente('antwort', '1', '--kennung', kennung, '--wortlaut', 'ja')],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        time.sleep(1.5)
        # Sie wartet auf die Sperre: noch nichts eingetragen, nichts gestartet.
        assert zweite.poll() is None
        assert not (umfeld.lauf_ordner() / 'christopher.txt').exists()
        lauf.merke(antwort={'wortlaut': 'nein', 'ja': False, 'kennung': kennung,
                            'unix': time.time()})
    aus, _ = zweite.communicate(timeout=60)
    assert zweite.returncode == ki_lauf.RC_NEIN and 'schon eine Antwort eingetragen' in aus
    assert umfeld.eintraege('fahren') == []


def test_jede_pid_bekommt_im_lauf_hoechstens_ein_sigint(tmp_path):
    """Gegenprüfung 24.11.2026: aufraeumen schickte der Kamera nach 15 s ein zweites."""
    ordner = tmp_path / 'lauf1'
    ordner.mkdir()
    lauf = ki_lauf.Lauf(ordner)
    zaeh = subprocess.Popen(
        [sys.executable, '-c', 'import signal, sys, time\n'
         'signal.signal(signal.SIGINT, signal.SIG_IGN)\nprint("bereit", flush=True)\n'
         'time.sleep(60)', 'oak.launch.py'], stdout=subprocess.PIPE, text=True)
    try:
        assert zaeh.stdout.readline().strip() == 'bereit'
        assert ki_lauf.ein_sigint(zaeh.pid, 'oak.launch.py', lauf)
        assert not ki_lauf.ein_sigint(zaeh.pid, 'oak.launch.py', lauf)      # schon eines
        assert zaeh.pid in lauf.signalisiert() and zaeh.poll() is None
    finally:
        _beende(zaeh)
