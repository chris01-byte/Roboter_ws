#!/usr/bin/env python3
"""Ablaufhilfe für einen Lauf der KI-Linie am Jetson: Rundblick, Wahl, Frage, Antwort.

Ersetzt die Handschritte in zwei Shells aus KI-F9 (Bewertung nach KI-F9,
§5): Jeder Schritt lädt seine Umgebung selbst, der Zustand eines Laufs liegt
in einer Datei, und kein Schritt baut auf Variablen eines früheren auf.

    ki_lauf.py pruefe-umgebung
    ki_lauf.py start   --auftrag kif10 --lauf 1      # Kamera, Aufnahme
    (Missionsstart von Hand, genau einmal)
    ki_lauf.py wahl    --auftrag kif10 --lauf 1      # Wahl der KI, Frage
    ki_lauf.py antwort --auftrag kif10 --lauf 1 --kennung abc123 --wortlaut "ja"
    ki_lauf.py verfolgen  --auftrag kif10 --lauf 1   # Fahrt weiter zeigen
    ki_lauf.py aufraeumen --auftrag kif10 --lauf 1

``start`` startet losgelöst einen Begleiter. Er startet die Kamera und die
Aufnahme (``--bis-wartephase``: sie endet 5 s nach dem Rundblick von selbst),
beendet danach die Kamera mit genau einem SIGINT und fragt die KI
(``ki_tuer_waehlen.py --ueber-ros --runde …``). ``wahl`` wartet darauf und
baut die Frage an den Menschen; ohne gültige Wahl sendet es dem wartenden
Erkunder das „Ende“. Nach ``antwort``: Nur ein „ja“ zu genau dieser Wahl
(Kennung) startet ``fahrziel_senden.py --zur-tuer --wahl …``; jede andere
Antwort sendet ``--ende --quelle mensch``.

**Kein Navigator, kein Aufseher:** Die Hilfe sendet selbst nichts an ROS,
startet und stoppt keine Mission und plant keinen Weg. Gefahren wird nur
durch den Erkunder mit seiner Schutzkette, und nur nach dem Ja des Menschen.
Signale gehen immer nur als genau ein SIGINT an eine geprüfte einzelne PID
(Befehlszeile passt), nie an eine Gruppe.

Rückgabe: 0 erledigt; 2 abgelehnt oder nicht gefahren; 4 kein Rundblick oder
keine Runde; 10 läuft noch – denselben Befehl noch einmal aufrufen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ros_ende import Ende  # noqa: E402

WERKZEUGE = Path(__file__).resolve().parent
RC_OK, RC_NEIN, RC_KEINE_RUNDE, RC_LAEUFT = 0, 2, 4, 10
VORGABE = {
    'umgebung_kamera': '~/ki_trockenlauf_ki0/umgebung_we1.bash',
    'umgebung_stack': '~/roboter_worktrees/kif8.env',
    'runden': '~/.local/share/amadeus/ki_erkundung/blickrunden',
    'wahl_ordner': '~/.local/share/amadeus/ki_erkundung/wahl',
    'kamera_befehl': 'ros2 launch robot_bringup oak.launch.py pointcloud:=false',
}
# So endet in der Befehlszeile, was die Hilfe selbst gestartet hat.
MERKMAL = {'begleiter': '_rundblick', 'fahrt_begleiter': '_fahrt', 'kamera': 'oak.launch.py',
           'aufnahme': 'blickrunde_aufnehmen.py', 'werkzeug': 'fahrziel_senden.py'}
RAND = ' \t\r\n.,;:!?"\'„“”‚‘’»«()'


# ---- kleine Bausteine --------------------------------------------------------

def ist_ja(wortlaut: str) -> bool:
    """Nur ein klares „ja“ gibt die Fahrt frei („Ja.“ ja, „ja, aber …“ nein)."""
    return wortlaut.strip(RAND).lower() == 'ja'


def kennung_der_datei(pfad: Path) -> str:
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()[:6]


def in_umgebung(umgebung: str, befehl: List[str]) -> List[str]:
    """Befehl, der zuerst die Umgebung lädt und mit Standard-SIGINT läuft."""
    return ['bash', '-c',
            'source "$1" >/dev/null 2>&1; shift; exec env --default-signal=INT "$@"',
            '_', str(Path(umgebung).expanduser())] + [str(teil) for teil in befehl]


def argumente(pid: int) -> Optional[List[str]]:
    """Die Argumente eines Prozesses (``/proc/PID/cmdline``) oder None."""
    try:
        roh = Path(f'/proc/{int(pid)}/cmdline').read_bytes()
    except (OSError, ValueError):
        return None
    return [teil.decode('utf-8', 'replace') for teil in roh.split(b'\0') if teil] or None


def befehlszeile(pid: int) -> Optional[str]:
    teile = argumente(pid)
    return ' '.join(teile) if teile else None


def passt(teile: Optional[List[str]], merkmal: str) -> bool:
    """Ein Argument ist das Merkmal selbst oder ein Pfad, der darauf endet.

    Nur ganze Argumente zählen: Eine Shell, deren Befehl das Merkmal bloß als
    Text enthält (``bash -c "… oak.launch.py …"``), ist keine Kamera (AGENTS.md:
    „pgrep -f trifft die eigene Shell“).
    """
    return bool(teile) and any(t == merkmal or t.endswith('/' + merkmal) for t in teile)


def vorfahren() -> set:
    """Dieser Prozess und alle seine Vorfahren (Shells, die ihn gestartet haben)."""
    pids, pid = set(), os.getpid()
    while pid > 1 and pid not in pids:
        pids.add(pid)
        try:
            status = Path(f'/proc/{pid}/status').read_text(encoding='utf-8', errors='replace')
        except OSError:
            break
        treffer = re.search(r'^PPid:\s+(\d+)', status, re.M)
        if not treffer:
            break
        pid = int(treffer.group(1))
    return pids


def laeuft(pid: Optional[int], merkmal: str) -> bool:
    """Lebt dieser Prozess noch, und ist er der erwartete (Argumente)?"""
    return bool(pid) and passt(argumente(pid), merkmal)


def laufende(*muster: str) -> List[int]:
    """PIDs mit einem passenden Argument; ohne diesen Prozess und seine Vorfahren."""
    eigene = vorfahren()
    treffer = []
    for eintrag in Path('/proc').iterdir():
        if not eintrag.name.isdigit() or int(eintrag.name) in eigene:
            continue
        teile = argumente(int(eintrag.name))
        if any(passt(teile, m) for m in muster):
            treffer.append(int(eintrag.name))
    return sorted(treffer)


def ein_sigint(pid: Optional[int], merkmal: str) -> bool:
    """Genau ein SIGINT an genau diesen Prozess, nur wenn er der erwartete ist."""
    if not pid or int(pid) <= 0 or not laeuft(pid, merkmal):
        return False
    try:
        os.kill(int(pid), signal.SIGINT)
    except ProcessLookupError:
        return False
    return True


def warte_bis_beendet(pid: Optional[int], merkmal: str, sekunden: float) -> bool:
    ende = time.monotonic() + sekunden
    while laeuft(pid, merkmal) and time.monotonic() < ende:
        time.sleep(0.2)
    return not laeuft(pid, merkmal)


def lies_json(pfad: Path) -> dict:
    try:
        return json.loads(Path(pfad).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def schreibe_json(pfad: Path, daten: dict) -> None:
    """Erst in eine Nebendatei, dann umbenennen: Leser sehen nie eine halbe Datei."""
    neu = Path(str(pfad) + '.neu')
    neu.write_text(json.dumps(daten, indent=1, ensure_ascii=False), encoding='utf-8')
    os.replace(neu, pfad)


def zeilen(pfad: Path) -> List[str]:
    try:
        return Path(pfad).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []


def schluesselwerte(zeile: str) -> Dict[str, str]:
    return dict(teil.split('=', 1) for teil in zeile.split()[1:] if '=' in teil)


def letzte_zeile(pfad: Path, anfang: str) -> Optional[str]:
    treffer = [z for z in zeilen(pfad) if z.startswith(anfang)]
    return treffer[-1] if treffer else None


# ---- ein Lauf ----------------------------------------------------------------

class Lauf:
    """Pfade und Zustand eines Laufs (``~/ki_trockenlauf_<auftrag>/lauf<K>``)."""

    def __init__(self, ordner: Path):
        self.ordner = Path(ordner)
        self.zustand_datei = self.ordner / 'zustand.json'
        self.begleiter_datei = self.ordner / 'begleiter.json'
        self.fahrt_datei = self.ordner / 'fahrt.json'
        self.aufnahme = self.ordner / 'aufnahme.txt'
        self.kamera_log = self.ordner / 'oak.log'
        self.wahl_txt = self.ordner / 'wahl.txt'
        self.werkzeug = self.ordner / 'werkzeug.txt'

    @classmethod
    def aus(cls, a) -> 'Lauf':
        basis = Path(a.basis or f'~/ki_trockenlauf_{a.auftrag}').expanduser()
        return cls(basis / f'lauf{a.lauf}')

    def zustand(self) -> dict:
        return lies_json(self.zustand_datei)

    def merke(self, **teile) -> dict:
        zustand = self.zustand()
        zustand.update(teile)
        schreibe_json(self.zustand_datei, zustand)
        return zustand

    def protokoll(self, text: str) -> None:
        with open(self.ordner / 'ablauf.log', 'a', encoding='utf-8') as datei:
            datei.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {text}\n')


def starte_losgeloest(befehl: List[str], ausgabe: Path) -> subprocess.Popen:
    """Losgelöst starten (eigene Sitzung): lebt weiter, wenn dieser Aufruf endet."""
    with open(ausgabe, 'ab') as datei:
        return subprocess.Popen(befehl, stdout=datei, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)


def fuehre_aus(befehl: List[str], ausgabe: Path, zeitgrenze: float, abbruch=None) -> int:
    """Ausführen, Ausgabe in die Datei. Bei Überschreiten der Zeit oder Abbruch genau
    ein SIGINT an diesen einen Prozess, dann höchstens 20 s warten."""
    with open(ausgabe, 'ab') as datei:
        prozess = subprocess.Popen(befehl, stdout=datei, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL)
        bis = time.monotonic() + zeitgrenze
        while prozess.poll() is None:
            if time.monotonic() >= bis or (abbruch is not None and abbruch()):
                prozess.send_signal(signal.SIGINT)
                try:
                    return prozess.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    return 124
            time.sleep(0.2)
        return prozess.returncode


def ende_senden(lauf: Lauf, z: dict, quelle: str) -> int:
    """Dem wartenden Erkunder „Ende“ sagen. Das fährt nie."""
    befehl = in_umgebung(z['umgebung_stack'], [
        z['python'], Path(z['werkzeuge']) / 'fahrziel_senden.py', '--ende', '--quelle', quelle,
        '--warten', '60'])
    lauf.protokoll('ende ' + ' '.join(shlex.quote(t) for t in befehl[5:]))
    rc = fuehre_aus(befehl, lauf.werkzeug, 120)
    for zeile in zeilen(lauf.werkzeug)[-4:]:
        print('  ' + zeile)
    print(f'Ende an den Erkunder (Quelle {quelle}): rc={rc}. Amadeus fährt nicht.')
    return rc


# ---- Begleiter (losgelöst): Kamera, Aufnahme, Wahl der KI ----------------------

def begleiter_rundblick(ordner: Path) -> int:
    lauf = Lauf(ordner)
    z = lauf.zustand()
    marke = Ende().anmelden()            # ein Signal setzt nur die Marke
    stand = {'phase': 'kamera', 'pid': os.getpid(), 'start_unix': round(time.time(), 1)}
    schreibe_json(lauf.begleiter_datei, stand)

    def melde(**teile):
        stand.update(teile)
        schreibe_json(lauf.begleiter_datei, stand)

    with open(lauf.kamera_log, 'ab') as log:
        kamera = subprocess.Popen(in_umgebung(z['umgebung_kamera'],
                                              shlex.split(z['kamera_befehl'])),
                                  stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    melde(kamera_pid=kamera.pid)
    lauf.protokoll(f'Kamera gestartet (PID {kamera.pid})')
    bis = time.monotonic() + float(z['kamera_vorlauf'])
    while time.monotonic() < bis and not marke.gesetzt() and kamera.poll() is None:
        time.sleep(0.2)
    aufnahme = None
    if not marke.gesetzt() and kamera.poll() is None:
        argumente = [z['python'], Path(z['werkzeuge']) / 'blickrunde_aufnehmen.py',
                     '--name', z['name'], '--ausgabe', Path(z['runden']).expanduser(),
                     '--dauer', str(z['dauer'])]
        if not z['nur_stand']:
            argumente += ['--bis-wartephase', str(z['nachlauf'])]
        with open(lauf.aufnahme, 'ab') as datei:
            aufnahme = subprocess.Popen(in_umgebung(z['umgebung_kamera'], argumente),
                                        stdout=datei, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL)
        melde(phase='aufnahme', aufnahme_pid=aufnahme.pid)
        lauf.protokoll(f'Aufnahme gestartet (PID {aufnahme.pid})')
        weitergegeben = False
        while aufnahme.poll() is None:
            if marke.gesetzt() and not weitergegeben:
                aufnahme.send_signal(signal.SIGINT)        # genau eines: sie schreibt
                weitergegeben = True
            time.sleep(0.2)
        melde(aufnahme_rc=aufnahme.returncode)
    # Die Kamera läuft nur während des Rundblicks: genau ein SIGINT, dann warten.
    if kamera.poll() is None:
        kamera.send_signal(signal.SIGINT)
        try:
            kamera.wait(timeout=15)
        except subprocess.TimeoutExpired:
            lauf.protokoll('Kamera nach 15 s noch nicht beendet')
    fehler = sum(1 for zeile in zeilen(lauf.kamera_log) if 'error' in zeile.lower())
    ergebnis_zeile = letzte_zeile(lauf.aufnahme, 'ERGEBNIS')
    ergebnis = schluesselwerte(ergebnis_zeile) if ergebnis_zeile else {}
    melde(phase='runde', kamera_rc=kamera.returncode, kamera_fehlerzeilen=fehler,
          ergebnis=ergebnis, abgebrochen=marke.gesetzt())
    lauf.protokoll(f'Aufnahme beendet: {ergebnis_zeile or "ohne Ergebnis"}')

    runde = ergebnis.get('runde')
    tauglich = (runde not in (None, '-') and ergebnis.get('lage') == 'ja'
                and (z['nur_stand'] or ergebnis.get('grund') == 'wartephase')
                and not marke.gesetzt())
    if tauglich:
        befehl = in_umgebung(z['umgebung_kamera'], [
            z['python'], Path(z['werkzeuge']) / 'ki_tuer_waehlen.py', '--ueber-ros', '--runde',
            Path(z['runden']).expanduser() / runde, '--ausgabe',
            Path(z['wahl_ordner']).expanduser()])
        melde(phase='ki')
        beginn = time.monotonic()
        rc = fuehre_aus(befehl, lauf.wahl_txt, 360, abbruch=marke.gesetzt)
        kennung = letzte_zeile(lauf.wahl_txt, 'Kennung der Wahl: ')
        datei = letzte_zeile(lauf.wahl_txt, 'Wahl-Datei: ')
        melde(wahl_rc=rc, wahl_dauer_s=round(time.monotonic() - beginn, 1),
              kennung=kennung.split(': ', 1)[1].strip() if kennung else None,
              wahl_datei=datei.split(': ', 1)[1].strip() if datei else None)
        lauf.protokoll(f'Wahl der KI: rc={rc}')
    melde(phase='fertig', ende_unix=round(time.time(), 1))
    marke.abmelden()
    return 0


def begleiter_fahrt(ordner: Path) -> int:
    lauf = Lauf(ordner)
    z = lauf.zustand()
    marke = Ende().anmelden()
    stand = {'phase': 'faehrt', 'pid': os.getpid(), 'start_unix': round(time.time(), 1)}
    schreibe_json(lauf.fahrt_datei, stand)
    befehl = in_umgebung(z['umgebung_stack'], [
        z['python'], Path(z['werkzeuge']) / 'fahrziel_senden.py', '--zur-tuer', '--wahl',
        z['wahl']['datei'], '--hinter', '0.45', '--warten', '60', '--beobachten', '600'])
    lauf.protokoll('fahrt ' + ' '.join(shlex.quote(str(t)) for t in befehl[5:]))
    with open(lauf.werkzeug, 'ab') as datei:
        werkzeug = subprocess.Popen(befehl, stdout=datei, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL)
    stand['werkzeug_pid'] = werkzeug.pid
    schreibe_json(lauf.fahrt_datei, stand)
    weitergegeben = False
    while werkzeug.poll() is None:
        if marke.gesetzt() and not weitergegeben:
            werkzeug.send_signal(signal.SIGINT)      # genau eines; es sendet danach nichts mehr
            weitergegeben = True
        time.sleep(0.2)
    stand.update(phase='fertig', rc=werkzeug.returncode, ende_unix=round(time.time(), 1))
    schreibe_json(lauf.fahrt_datei, stand)
    marke.abmelden()
    return 0


# ---- Befehle -------------------------------------------------------------------

def umgebungen_fehlen(z: dict) -> List[str]:
    return [f'{name}: {z[name]}' for name in ('umgebung_kamera', 'umgebung_stack')
            if not Path(z[name]).expanduser().is_file()]


PRUEF_SKRIPT = (
    'import json, os\n'
    'def geht(name):\n'
    '    try:\n'
    '        __import__(name)\n'
    '        return True\n'
    '    except ImportError:\n'
    '        return False\n'
    'print(json.dumps({"rclpy": geht("rclpy"), "std_msgs": geht("std_msgs.msg"),\n'
    '    "domain": os.environ.get("ROS_DOMAIN_ID"), "rmw": os.environ.get("RMW_IMPLEMENTATION"),\n'
    '    "localhost": os.environ.get("ROS_LOCALHOST_ONLY"),\n'
    '    "reichweite": os.environ.get("ROS_AUTOMATIC_DISCOVERY_RANGE"),\n'
    '    "cyclone": os.environ.get("CYCLONEDDS_URI")}))\n')


def befehl_pruefe_umgebung(a) -> int:
    z = konfiguration(a)
    fehlen = umgebungen_fehlen(z)
    if fehlen:
        print('Umgebungsdatei fehlt: ' + '; '.join(fehlen))
        return RC_NEIN
    werte = {}
    for name in ('umgebung_kamera', 'umgebung_stack'):
        ergebnis = subprocess.run(in_umgebung(z[name], [z['python'], '-c', PRUEF_SKRIPT]),
                                  capture_output=True, text=True, timeout=60)
        try:
            werte[name] = json.loads(ergebnis.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            werte[name] = {}
    k, s = werte['umgebung_kamera'], werte['umgebung_stack']
    gut = True
    for name, w in (('Kamera', k), ('Stack', s)):
        geladen = w.get('rclpy') and w.get('std_msgs')
        gut &= bool(geladen)
        print(f'{name}: rclpy {"ja" if w.get("rclpy") else "nein"}, std_msgs '
              f'{"ja" if w.get("std_msgs") else "nein"}, ROS_DOMAIN_ID {w.get("domain")!r}, '
              f'RMW {w.get("rmw")!r}')
    for schluessel, text in (('domain', 'ROS_DOMAIN_ID'), ('rmw', 'RMW_IMPLEMENTATION'),
                             ('localhost', 'ROS_LOCALHOST_ONLY'),
                             ('reichweite', 'ROS_AUTOMATIC_DISCOVERY_RANGE')):
        if k.get(schluessel) != s.get(schluessel):
            gut = False
            print(f'{text} ist in beiden Umgebungen verschieden – sie sähen sich nicht.')
    cyclone = ('in keiner gesetzt' if not k.get('cyclone') and not s.get('cyclone')
               else 'gleich' if k.get('cyclone') == s.get('cyclone') else 'verschieden')
    print(f'CYCLONEDDS_URI: {cyclone} (Inhalt nicht gezeigt).')
    print('Umgebungen passen.' if gut else 'Umgebungen passen NICHT – nichts starten.')
    return RC_OK if gut else RC_NEIN


def konfiguration(a) -> dict:
    lauf = getattr(a, 'lauf', None)
    return {'auftrag': a.auftrag, 'lauf': lauf, 'name': f'{a.auftrag}_lauf{lauf}',
            'umgebung_kamera': a.umgebung_kamera, 'umgebung_stack': a.umgebung_stack,
            'python': a.python, 'runden': a.runden, 'wahl_ordner': a.wahl_ordner,
            'kamera_befehl': a.kamera_befehl, 'kamera_vorlauf': a.kamera_vorlauf,
            'dauer': a.dauer, 'nachlauf': a.nachlauf, 'frist': a.frist,
            'hoechstens': 300.0 if a.hoechstens is None else a.hoechstens, 'tuer': a.tuer,
            'nur_stand': bool(getattr(a, 'nur_stand', False)),
            'werkzeuge': str(Path(a.werkzeuge).expanduser().resolve()) if a.werkzeuge
            else str(WERKZEUGE)}


def befehl_start(a) -> int:
    lauf = Lauf.aus(a)
    if lauf.zustand_datei.exists():
        print(f'Lauf {a.lauf} von {a.auftrag} gibt es schon ({lauf.ordner}); für eine '
              'Wiederholung eine neue Laufkennung nehmen (zum Beispiel 1w).')
        return RC_NEIN
    z = konfiguration(a)
    if a.nur_stand:
        z['dauer'] = a.dauer_stand
    fehlen = umgebungen_fehlen(z)
    if fehlen:
        print('Umgebungsdatei fehlt: ' + '; '.join(fehlen) + '. Nichts gestartet.')
        return RC_NEIN
    schon = laufende(MERKMAL['kamera'], MERKMAL['aufnahme'], MERKMAL['begleiter'])
    if schon:
        print(f'Kamera, Aufnahme oder Begleiter laufen schon (PID {schon}). Nichts gestartet.')
        return RC_NEIN
    lauf.ordner.mkdir(parents=True, exist_ok=True)
    z['start_unix'] = round(time.time(), 1)
    schreibe_json(lauf.zustand_datei, z)
    begleiter = starte_losgeloest([sys.executable, str(Path(__file__).resolve()),
                                   '_rundblick', '--ordner', str(lauf.ordner)],
                                  lauf.ordner / 'begleiter.log')
    lauf.merke(begleiter_pid=begleiter.pid)
    lauf.protokoll(f'start: Begleiter PID {begleiter.pid}')
    print(f'Lauf {a.lauf}: Kamera startet, nach {z["kamera_vorlauf"]:.0f} s die Aufnahme '
          f'(Ablage {lauf.ordner}).')
    bis = time.monotonic() + a.bereit_warten
    bereit = None
    while time.monotonic() < bis and bereit is None:
        bereit = letzte_zeile(lauf.aufnahme, 'BEREIT')
        if bereit is None and begleiter.poll() is not None:
            break
        time.sleep(0.5)
    if bereit is None:
        print('Die Aufnahme meldet sich nicht (keine Zeile BEREIT). Letzte Zeilen:')
        for zeile in (zeilen(lauf.aufnahme) + zeilen(lauf.kamera_log))[-8:]:
            print('  ' + zeile)
        stoppe_begleiter(lauf)
        print('Kamera und Aufnahme beendet. Keine Mission starten.')
        return RC_NEIN
    werte = schluesselwerte(bereit)
    gruende = []
    if float(werte.get('bilder_hz', 0)) < a.mindestrate:
        gruende.append(f'Bildrate {werte.get("bilder_hz")} Hz (mindestens {a.mindestrate} Hz)')
    if float(werte.get('scan_hz', 0)) <= 0.0:
        gruende.append('kein Scan')
    if werte.get('kamera_info') != 'ja':
        gruende.append('keine Kameradaten (camera_info)')
    if not z['nur_stand'] and werte.get('erkunder') != 'ja':
        gruende.append('kein Status des Erkunders')
    print(bereit)
    if gruende:
        stoppe_begleiter(lauf)
        print('Nicht bereit: ' + '; '.join(gruende) + '. Kamera und Aufnahme beendet. '
              'Keine Mission starten.')
        return RC_NEIN
    if z['nur_stand']:
        print(f'Aufnahme im Stand läuft ({z["dauer"]:.0f} s). Keine Mission starten; danach: '
              'wahl.')
    else:
        print('Aufnahme läuft und endet von selbst 5 s nach dem Rundblick. Jetzt genau einmal '
              'die Mission starten.')
    return RC_OK


def stoppe_begleiter(lauf: Lauf) -> None:
    z = lauf.zustand()
    if ein_sigint(z.get('begleiter_pid'), MERKMAL['begleiter']):
        lauf.protokoll('Begleiter: ein SIGINT')
        warte_bis_beendet(z.get('begleiter_pid'), MERKMAL['begleiter'], 40)


def minuten_uebrig(z: dict, wartephase_unix: Optional[str]) -> Optional[int]:
    try:
        seit = time.time() - float(wartephase_unix)
    except (TypeError, ValueError):
        return None
    return max(0, math.floor((float(z['frist']) - seit) / 60.0))


def baue_frage(wahl_zeilen: List[str], minuten: Optional[int], tuer: str) -> Optional[str]:
    satz = next((z for z in wahl_zeilen if z.startswith('Die KI wählt Nr.')), None)
    if satz is None:
        return None
    begruendung = next((z for z in wahl_zeilen if z.startswith('Begründung der KI:')), None)
    gefahren = next((z for z in wahl_zeilen if z.startswith('Gefahren laut KI:')), None)
    nummern = [z.strip() for z in wahl_zeilen if z.startswith('  Nr. ')]
    teile = ['Die KI hat gewählt.', satz]
    if begruendung:
        teile.append(begruendung)
    if nummern:
        teile.append('Was sie in jeder Nummer sieht: ' + ' / '.join(nummern) + '.')
    if gefahren:
        teile.append(gefahren + '.')
    teile.append('Die Bilder mit den Nummern zeigt das Lotsen-Fenster auf dem KI-Rechner. '
                 f'Ist die gewählte Öffnung {tuer}, und soll Amadeus hindurchfahren? '
                 "Schreib ‚ja' oder ‚nein'.")
    if minuten is not None:
        teile.append(f'(Der Erkunder wartet noch etwa {minuten} Minuten.)')
    return '„' + ' '.join(teile) + '“'


def befehl_wahl(a) -> int:
    lauf = Lauf.aus(a)
    z = lauf.zustand()
    if not z:
        print(f'Zu Lauf {a.lauf} gibt es keinen Start ({lauf.zustand_datei}).')
        return RC_NEIN
    if 'wahl' in z:                                   # nie zweimal fragen
        print(f'Die Wahl zu Lauf {a.lauf} steht schon fest (rc={z["wahl"].get("rc")}).')
        if z['wahl'].get('frage'):
            print(z['wahl']['frage'])
        return RC_OK if z['wahl'].get('rc') == 0 else RC_NEIN
    bis = time.monotonic() + a.warten
    hoechstens = float(z['hoechstens'] if a.hoechstens is None else a.hoechstens)
    naechste_meldung = 0.0
    while laeuft(z.get('begleiter_pid'), MERKMAL['begleiter']):
        b = lies_json(lauf.begleiter_datei)
        wartephase = any('Erkunder: Wartephase' in zeile for zeile in zeilen(lauf.aufnahme))
        if (not z['nur_stand'] and not wartephase and b.get('phase') in ('kamera', 'aufnahme')
                and time.time() - float(z['start_unix']) > hoechstens):
            print(f'Nach {hoechstens:.0f} s noch keine Wartephase des Erkunders: Abbruch. '
                  'Aufnahme und Kamera werden beendet; die KI wird nicht gefragt.')
            stoppe_begleiter(lauf)
            lauf.merke(wahl={'rc': RC_KEINE_RUNDE, 'grund': 'keine_wartephase'})
            print('LAUF ergebnis=nicht_gefahren grund=keine_wartephase')
            return RC_KEINE_RUNDE
        if time.monotonic() >= bis:
            fortschritt = [zz for zz in zeilen(lauf.aufnahme) if zz.strip()]
            print(f'Läuft noch (Phase {b.get("phase")!r}); zuletzt: '
                  f'{fortschritt[-1].strip() if fortschritt else "-"}. Bitte „wahl“ erneut '
                  'aufrufen.')
            return RC_LAEUFT
        if time.monotonic() >= naechste_meldung:
            naechste_meldung = time.monotonic() + 20.0
            fortschritt = [zz for zz in zeilen(lauf.aufnahme) if zz.strip()]
            if fortschritt:
                print('  ' + fortschritt[-1].strip())
        time.sleep(1.0)
    b = lies_json(lauf.begleiter_datei)
    erg = b.get('ergebnis') or {}
    print(f'Aufnahme: {letzte_zeile(lauf.aufnahme, "ERGEBNIS") or "kein Ergebnis"}; Kamera '
          f'beendet (Fehlerzeilen im Log: {b.get("kamera_fehlerzeilen", "-")}).')
    if b.get('wahl_rc') is None:
        grund = ('Aufnahme abgebrochen' if b.get('abgebrochen')
                 else 'keine Runde' if erg.get('runde') in (None, '-')
                 else 'Lage in der Karte fehlt' if erg.get('lage') != 'ja'
                 else f'kein Rundblick bis zur Wartephase (Ende: {erg.get("grund")})')
        print(f'Die KI wird nicht gefragt: {grund}.')
        lauf.merke(wahl={'rc': RC_KEINE_RUNDE, 'grund': grund})
        if not z['nur_stand'] and erg.get('grund') == 'wartephase':
            ende_senden(lauf, z, 'ki')
        print('LAUF ergebnis=nicht_gefahren grund=keine_runde')
        return RC_KEINE_RUNDE
    text = [zz for zz in zeilen(lauf.wahl_txt)
            if not zz.startswith(('Wahl-Datei: ', 'Protokoll: ', 'Gefahren wird erst'))]
    for zeile in text:
        print(zeile)
    wahl = {'rc': b['wahl_rc'], 'kennung': b.get('kennung'), 'datei': b.get('wahl_datei'),
            'wartephase_unix': erg.get('wartephase_unix'), 'dauer_s': b.get('wahl_dauer_s')}
    if b['wahl_rc'] != 0 or not wahl['kennung'] or not wahl['datei']:
        lauf.merke(wahl=wahl)
        print(f'Keine Wahl der KI (rc={b["wahl_rc"]}). Keine Frage an den Menschen.')
        if not z['nur_stand']:
            ende_senden(lauf, z, 'ki')
        print('LAUF ergebnis=nicht_gefahren grund=keine_wahl')
        return RC_NEIN
    if z['nur_stand']:
        lauf.merke(wahl=wahl)
        print(f'Vorlauf im Stand: Wahl der KI mit Kennung {wahl["kennung"]}; keine Frage, '
              'nichts gesendet. Weiter mit: messen.')
        return RC_OK
    frage = baue_frage(text, minuten_uebrig(z, wahl['wartephase_unix']), z['tuer'])
    wahl['frage'] = frage
    lauf.merke(wahl=wahl)
    (lauf.ordner / 'frage.txt').write_text((frage or '') + '\n', encoding='utf-8')
    print('FRAGE AN CHRISTOPHER (wörtlich weitergeben):')
    print(frage)
    print('Seine Antwort danach eintragen (Kennung der Wahl: ' + wahl['kennung'] + '):')
    print(f'  python3 {Path(__file__).resolve()} antwort --auftrag {a.auftrag} '
          f'--lauf {a.lauf} --kennung {wahl["kennung"]} --wortlaut "<seine Antwort>"')
    return RC_OK


def befehl_antwort(a) -> int:
    lauf = Lauf.aus(a)
    z = lauf.zustand()
    if 'antwort' in z:
        print(f'Zu Lauf {a.lauf} ist schon eine Antwort eingetragen: {z["antwort"]["wortlaut"]!r}. '
              'Nichts aufgerufen.')
        return RC_NEIN
    w = z.get('wahl') or {}
    if w.get('rc') != 0 or not w.get('kennung') or z.get('nur_stand'):
        print('Zu diesem Lauf gibt es keine Wahl, zu der eine Antwort passen könnte. '
              'Nichts aufgerufen.')
        return RC_NEIN
    if a.kennung != w['kennung']:
        print(f'Die Kennung {a.kennung!r} passt nicht zur Wahl dieses Laufs. Nichts aufgerufen.')
        return RC_NEIN
    datei = Path(w['datei'])
    if not datei.is_file() or kennung_der_datei(datei) != w['kennung']:
        print('Die Wahl-Datei fehlt oder hat sich seit der Frage geändert. Nichts aufgerufen.')
        return RC_NEIN
    stoppe_begleiter(lauf)                    # läuft die Kamera noch: zuerst beenden
    ja = ist_ja(a.wortlaut)
    with open(lauf.ordner / 'christopher.txt', 'a', encoding='utf-8') as datei_c:
        datei_c.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {a.wortlaut}\n')
    lauf.merke(antwort={'wortlaut': a.wortlaut, 'ja': ja, 'unix': round(time.time(), 1)})
    lauf.protokoll(f'antwort {a.wortlaut!r} -> {"ja" if ja else "kein ja"}')
    if not ja:
        print('Kein Ja: Amadeus fährt nicht.')
        ende_senden(lauf, z, 'mensch')
        print('LAUF ergebnis=nicht_gefahren grund=kein_ja')
        return RC_OK
    begleiter = starte_losgeloest([sys.executable, str(Path(__file__).resolve()), '_fahrt',
                                   '--ordner', str(lauf.ordner)], lauf.ordner / 'fahrt.log')
    lauf.merke(fahrt_begleiter_pid=begleiter.pid)
    print('Ja: Das Werkzeug misst neu und gibt dem Erkunder das Fahrziel (Anfahrt und '
          'Durchfahrt in einer Mission).')
    return verfolge(lauf, a.warten)


def ergebnis_der_fahrt(text: List[str]) -> str:
    if any(z.strip() == 'Durchfahrt abgeschlossen.' for z in text):
        return 'durchfahrt'
    if any(z.strip().startswith('Anfahrt abgeschlossen.') for z in text):
        return 'nur_anfahrt'
    return 'nicht_gefahren'


def verfolge(lauf: Lauf, warten: float) -> int:
    z = lauf.zustand()
    gezeigt = int(z.get('gezeigt_bis', 0))
    bis = time.monotonic() + warten
    while True:
        alle = zeilen(lauf.werkzeug)
        neu = alle[gezeigt:]
        for zeile in neu:
            print('  ' + zeile)
        gezeigt = len(alle)
        lauf.merke(gezeigt_bis=gezeigt)
        f = lies_json(lauf.fahrt_datei)
        if f.get('phase') == 'fertig' or not laeuft(z.get('fahrt_begleiter_pid'),
                                                    MERKMAL['fahrt_begleiter']):
            f = lies_json(lauf.fahrt_datei)
            ergebnis = ergebnis_der_fahrt(zeilen(lauf.werkzeug))
            print(f'LAUF ergebnis={ergebnis} werkzeug_rc={f.get("rc")}')
            return RC_OK if ergebnis == 'durchfahrt' else RC_NEIN
        if time.monotonic() >= bis:
            print('Die Fahrt läuft noch; weiter mit: verfolgen.')
            return RC_LAEUFT
        time.sleep(1.0)


def befehl_verfolgen(a) -> int:
    lauf = Lauf.aus(a)
    if not lauf.zustand().get('fahrt_begleiter_pid'):
        print('Zu diesem Lauf gibt es keine Fahrt.')
        return RC_NEIN
    return verfolge(lauf, a.warten)


def befehl_messen(a) -> int:
    """Nur messen (Vorlauf, Diagnose): Was würde das Werkzeug zur Wahl tun? Sendet nichts."""
    lauf = Lauf.aus(a)
    z = lauf.zustand()
    w = z.get('wahl') or {}
    if w.get('rc') != 0 or not w.get('datei'):
        print('Zu diesem Lauf gibt es keine Wahl der KI zum Messen.')
        return RC_NEIN
    befehl = in_umgebung(z['umgebung_stack'], [
        z['python'], Path(z['werkzeuge']) / 'fahrziel_senden.py', '--zur-tuer', '--wahl',
        w['datei'], '--nur-messen', '--hinter', '0.45'])
    rc = fuehre_aus(befehl, lauf.ordner / 'messen.txt', 120)
    for zeile in zeilen(lauf.ordner / 'messen.txt'):
        print(zeile)
    print(f'Nur gemessen, nichts gesendet: rc={rc}.')
    return rc


def befehl_aufraeumen(a) -> int:
    lauf = Lauf.aus(a)
    z, b, f = lauf.zustand(), lies_json(lauf.begleiter_datei), lies_json(lauf.fahrt_datei)
    kandidaten = [('begleiter', z.get('begleiter_pid')), ('aufnahme', b.get('aufnahme_pid')),
                  ('kamera', b.get('kamera_pid')),
                  ('fahrt_begleiter', z.get('fahrt_begleiter_pid')),
                  ('werkzeug', f.get('werkzeug_pid'))]
    for name, pid in kandidaten:
        if ein_sigint(pid, MERKMAL[name]):
            print(f'{name}: ein SIGINT an PID {pid}')
            lauf.protokoll(f'aufraeumen: SIGINT an {name} {pid}')
            warte_bis_beendet(pid, MERKMAL[name], 15)
    uebrig = [f'{name} {pid}' for name, pid in kandidaten if laeuft(pid, MERKMAL[name])]
    print('Alles beendet.' if not uebrig else 'Noch nicht beendet: ' + ', '.join(uebrig))
    return RC_OK if not uebrig else RC_NEIN


def eingabe() -> argparse.ArgumentParser:
    e = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    unter = e.add_subparsers(dest='befehl', required=True)

    def gemeinsam(p, lauf=True):
        p.add_argument('--auftrag', default='kif10',
                       help='Kennung des Auftrags (Ordner ~/ki_trockenlauf_<auftrag>)')
        if lauf:
            p.add_argument('--lauf', required=True, help='Kennung des Laufs, zum Beispiel 1, 2w')
        p.add_argument('--basis', help='Ordner der Läufe (Vorgabe ~/ki_trockenlauf_<auftrag>)')
        p.add_argument('--umgebung-kamera', default=VORGABE['umgebung_kamera'])
        p.add_argument('--umgebung-stack', default=VORGABE['umgebung_stack'])
        p.add_argument('--python', default='python3',
                       help='Python mit rclpy in beiden Umgebungen')
        p.add_argument('--runden', default=VORGABE['runden'])
        p.add_argument('--wahl-ordner', default=VORGABE['wahl_ordner'])
        p.add_argument('--kamera-befehl', default=VORGABE['kamera_befehl'])
        p.add_argument('--kamera-vorlauf', type=float, default=20.0)
        p.add_argument('--dauer', type=float, default=420.0, help='höchste Aufnahmedauer, s')
        p.add_argument('--nachlauf', type=float, default=5.0,
                       help='so lange nimmt die Aufnahme nach dem Rundblick noch auf, s')
        p.add_argument('--frist', type=float, default=420.0,
                       help='so lange wartet der Erkunder auf ein Fahrziel, s')
        p.add_argument('--hoechstens', type=float, default=None,
                       help='kommt bis dahin (ab start) keine Wartephase: Abbruch, s '
                            '(Vorgabe 300; bei wahl gilt, was hier steht, sonst der Wert '
                            'vom Start)')
        p.add_argument('--tuer', default='die Labortür',
                       help='so heißt die erwartete Tür in der Frage an den Menschen')
        p.add_argument('--warten', type=float, default=100.0,
                       help='so lange wartet ein Aufruf, dann rc 10 (erneut aufrufen), s')
        p.add_argument('--werkzeuge', help=argparse.SUPPRESS)       # nur für Tests

    gemeinsam(unter.add_parser('pruefe-umgebung', help='beide Umgebungen prüfen'), lauf=False)
    p = unter.add_parser('start', help='Kamera und Aufnahme starten (losgelöst)')
    gemeinsam(p)
    p.add_argument('--nur-stand', action='store_true',
                   help='Vorlauf ohne Mission: Aufnahme im Stand, keine Frage, nichts senden')
    p.add_argument('--dauer-stand', type=float, default=10.0)
    p.add_argument('--mindestrate', type=float, default=1.8, help='Bilder je Sekunde')
    p.add_argument('--bereit-warten', type=float, default=60.0)
    gemeinsam(unter.add_parser('wahl', help='Wahl der KI abwarten, Frage bauen'))
    p = unter.add_parser('antwort', help='Antwort des Menschen eintragen')
    gemeinsam(p)
    p.add_argument('--kennung', required=True)
    p.add_argument('--wortlaut', required=True)
    gemeinsam(unter.add_parser('verfolgen', help='die Fahrt weiter zeigen'))
    gemeinsam(unter.add_parser('messen', help='nur messen, nichts senden (Vorlauf)'))
    gemeinsam(unter.add_parser('aufraeumen', help='alles dieses Laufs mit je einem SIGINT beenden'))
    for name in ('_rundblick', '_fahrt'):
        p = unter.add_parser(name)
        p.add_argument('--ordner', required=True)
    return e


def main(argv=None) -> int:
    for strom in (sys.stdout, sys.stderr):
        if hasattr(strom, 'reconfigure'):
            strom.reconfigure(line_buffering=True)
    a = eingabe().parse_args(argv)
    if a.befehl == '_rundblick':
        return begleiter_rundblick(Path(a.ordner))
    if a.befehl == '_fahrt':
        return begleiter_fahrt(Path(a.ordner))
    if hasattr(a, 'lauf') and not re.fullmatch(r'[A-Za-z0-9]{1,12}', a.lauf):
        eingabe().error('--lauf: nur Buchstaben und Ziffern')
    if not re.fullmatch(r'[A-Za-z0-9_]{1,24}', a.auftrag):
        eingabe().error('--auftrag: nur Buchstaben, Ziffern und _')
    return {'pruefe-umgebung': befehl_pruefe_umgebung, 'start': befehl_start,
            'wahl': befehl_wahl, 'antwort': befehl_antwort, 'verfolgen': befehl_verfolgen,
            'messen': befehl_messen, 'aufraeumen': befehl_aufraeumen}[a.befehl](a)


if __name__ == '__main__':
    raise SystemExit(main())
