"""Attrappen für die Tests der Ablaufhilfe (ki_lauf.py): Kamera und drei Werkzeuge.

Jede Attrappe schreibt in ``protokoll.jsonl`` (Ordner aus ``KI_TEST_ORDNER``),
mit welchen Argumenten, in welcher Umgebung (``KI_TEST_UMG``) sie lief und
welche Signale sie bekam. Das Verhalten steuert ``KI_TEST_SZENARIO`` aus der
Umgebungsdatei. Kein ROS, keine Bilder.
"""
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

ORDNER = Path(os.environ.get('KI_TEST_ORDNER', '.'))
SZENARIO = os.environ.get('KI_TEST_SZENARIO', '')
signale = []


def protokolliere(art, **mehr):
    with open(ORDNER / 'protokoll.jsonl', 'a', encoding='utf-8') as datei:
        datei.write(json.dumps({'art': art, 'umg': os.environ.get('KI_TEST_UMG'),
                                'argv': sys.argv[1:], 'pid': os.getpid(),
                                'zeit': time.time(), **mehr}) + '\n')


def auf_signal(nummer, _rahmen):
    signale.append(signal.Signals(nummer).name)


def wert(name, standard=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else standard


def kamera():
    signal.signal(signal.SIGINT, auf_signal)
    protokolliere('kamera_start')
    while not signale:
        time.sleep(0.05)
    protokolliere('kamera_ende', signale=list(signale))


def aufnahme():
    signal.signal(signal.SIGINT, auf_signal)
    signal.signal(signal.SIGTERM, auf_signal)
    protokolliere('aufnahme_start')
    rate = '0.4' if 'langsam' in SZENARIO else '2.0'
    print(f'BEREIT bilder_hz={rate} scan_hz=10.0 kamera_info=ja erkunder=ja', flush=True)
    name, dauer = wert('--name'), float(wert('--dauer', '30'))
    nachlauf = wert('--bis-wartephase')
    beginn = time.monotonic()
    grund, wartephase = 'dauer', None
    while time.monotonic() - beginn < dauer:
        if signale:
            grund = 'signal'
            break
        if (nachlauf is not None and 'ohne_wartephase' not in SZENARIO
                and wartephase is None and time.monotonic() - beginn > 0.5):
            wartephase = time.time()
            print('Erkunder: Wartephase seit 00:00:00, Aufnahme endet in 0 s.', flush=True)
        if wartephase is not None and time.time() - wartephase >= float(nachlauf):
            grund = 'wartephase'
            break
        time.sleep(0.05)
    runde = f'{name}_20261124_000000'
    print(f'Blickrunde geschrieben: {runde}', flush=True)
    print(f'ERGEBNIS grund={grund} runde={runde} aufnahmen=200 verworfen=0 gedreht=363 '
          f'lage=ja wartephase_unix={wartephase if wartephase else "-"}', flush=True)
    protokolliere('aufnahme_ende', signale=list(signale), grund=grund)


def waehlen():
    protokolliere('waehlen')
    if 'keine_wahl' in SZENARIO:
        print('Frage 1 an pruefmodell: Wahl None, 2,0 s')
        print('Keine Wahl: die KI nennt keinen geeigneten Ausgang.')
        sys.exit(2)
    ausgabe = Path(wert('--ausgabe'))
    ausgabe.mkdir(parents=True, exist_ok=True)
    runde = Path(wert('--runde')).name
    datei = ausgabe / f'{runde}_wahl.json'
    # wie lotse.wahl.wahl_aufschreiben, mit erfundenen Maßen (keine Wohnung)
    datei.write_text(json.dumps({
        'schema': 1, 'art': 'ki_wahl', 'runde': runde, 'erzeugt_s': round(time.time(), 1),
        'quelle': 'ki', 'modell': 'pruefmodell', 'dauer_s': 2.0, 'nr': 2,
        'einordnung': 'tuer_offen', 'sicherheit': 0.9,
        'begruendung': 'Nr. 2 ist eine\noffene Tür.', 'raum': 'Labor',
        'gefahren': ['Kabel am Boden'], 'breite_m': 0.83, 'tuerbreit': True,
        'entfernung_m': 2.4, 'richtung_ende_grad': 25.0, 'rahmen': 'map',
        'mitte': [1.0, 2.0], 'pfosten': [[0.6, 2.0], [1.4, 2.0]]}, ensure_ascii=False),
        encoding='utf-8')
    print('Frage 1 an pruefmodell: Wahl 2, 2,0 s')
    print('Was die KI in den Nummern sieht (Richtung von seiner jetzigen Blickrichtung):')
    print('  Nr. 1: 0,82 m breit, 2,6 m entfernt, 176° rechts; KI: Lücke an Möbeln')
    print('  Nr. 2: 0,83 m breit, 2,4 m entfernt, 25° links; KI: offene Tür  ← gewählt')
    if 'falscher_text' in SZENARIO:       # Text einer anderen Wahl: die Frage nimmt die Datei
        print('Begründung der KI: Nr. 1 ist ein Durchgang.')
        print('Die KI wählt Nr. 1: Durchgang, 0,82 m breit, 2,6 m entfernt.')
    else:
        print('Begründung der KI: Nr. 2 ist eine offene Tür.')
        print('Gefahren laut KI: Kabel am Boden')
        print('Die KI wählt Nr. 2: offene Tür (sicher zu 90 %), 0,83 m breit, 2,4 m '
              'entfernt, 25° links von seiner Blickrichtung.')
    print(f'Wahl-Datei: {datei}')
    print(f'Kennung der Wahl: {hashlib.sha256(datei.read_bytes()).hexdigest()[:6]}')


def fahren():
    signal.signal(signal.SIGINT, auf_signal)
    protokolliere('fahren')
    if '--ende' in sys.argv:
        print('Kein Fahrziel: Ende auf Wunsch.', flush=True)
        return
    if '--nur-messen' in sys.argv:
        print('Zur Wahl der KI passt Öffnung 1 (die Mitten liegen 0.02 m auseinander).')
        return
    print('Fahrziel gesendet: 3 Punkt(e)', flush=True)
    bis = time.monotonic() + (30.0 if 'lange_fahrt' in SZENARIO else 0.5)
    while time.monotonic() < bis and not signale:
        time.sleep(0.05)
    if signale:
        print('Abgebrochen (SIGINT).', flush=True)
        protokolliere('fahren_abgebrochen', signale=list(signale))
        sys.exit(130)
    print('Anfahrt abgeschlossen. Jetzt misst er neu und fährt in derselben Mission hindurch.')
    print('Durchfahrt abgeschlossen.', flush=True)


if __name__ == '__main__':
    NAME = Path(sys.argv[0]).name           # als Kopie unter dem Namen des Werkzeugs
    if NAME == 'ki_lauf_attrappen.py':
        NAME = sys.argv.pop(1)              # oder mit der Rolle als erstem Argument
    {'kamera': kamera, 'blickrunde_aufnehmen.py': aufnahme, 'ki_tuer_waehlen.py': waehlen,
     'fahrziel_senden.py': fahren}[NAME]()
