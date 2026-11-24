#!/usr/bin/env python3
"""Ablaufhilfe für einen Lauf der KI-Linie am Jetson: Rundblick, Wahl, Frage, Antwort.

Ersetzt die Handschritte in zwei Shells aus KI-F9 (Bewertung nach KI-F9,
§5): Jeder Schritt lädt seine Umgebung selbst, der Zustand eines Laufs liegt
in einer Datei, und kein Schritt baut auf Variablen eines früheren auf.

    ki_lauf.py pruefe-umgebung
    ki_lauf.py start   --auftrag kif10 --lauf 1      # Kamera, Aufnahme
                       [--tuer "die Labortür" --frist 420 …]  # nur hier
    (Missionsstart von Hand, genau einmal)
    ki_lauf.py wahl    --auftrag kif10 --lauf 1      # Wahl der KI, Frage
    ki_lauf.py antwort --auftrag kif10 --lauf 1 --kennung abc123 --wortlaut "ja"
    ki_lauf.py verfolgen  --auftrag kif10 --lauf 1   # Fahrt weiter zeigen
    ki_lauf.py aufraeumen --auftrag kif10 --lauf 1

``start`` startet losgelöst einen Begleiter. Er startet die Kamera und die
Aufnahme (``--bis-wartephase``: sie endet 5 s nach dem Rundblick von selbst),
beendet danach die Kamera mit genau einem SIGINT und fragt die KI
(``ki_tuer_waehlen.py --ueber-ros --runde …``). ``wahl`` wartet darauf und
baut die Frage an den Menschen aus der Wahl-Datei selbst (Kennung geprüft);
gefragt wird erst, wenn keine Kamera mehr läuft. Ohne gültige Wahl sendet es
dem wartenden Erkunder das „Ende“. Nach ``antwort``: Nur ein „ja“ zu genau
dieser Wahl (Kennung) startet ``fahrziel_senden.py --zur-tuer --wahl …``, und
nur, wenn weder eine Kamera noch eine andere Fahrt läuft; jede andere Antwort
sendet ``--ende --quelle mensch``. Eine Antwort gilt nur, solange der Erkunder
dieses Laufs wartet (Frist ab der Wartephase) und kein späterer Lauf begonnen
hat; danach ruft sie nichts auf, auch kein „Ende“. Angaben für den ganzen Lauf
(Umgebungen, Tür, Frist …) gibt es nur bei ``start``; die späteren Schritte
lesen sie aus dem gespeicherten Zustand.

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
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    # Jeder Start schreibt sich hier ein, über Aufträge und Basis-Ordner hinweg.
    'marke': '~/.local/share/amadeus/ki_erkundung/letzter_start.json',
}
# So endet in der Befehlszeile, was die Hilfe selbst gestartet hat.
MERKMAL = {'begleiter': '_rundblick', 'fahrt_begleiter': '_fahrt', 'kamera': 'oak.launch.py',
           'aufnahme': 'blickrunde_aufnehmen.py', 'werkzeug': 'fahrziel_senden.py'}
ANFUEHRUNG = ' \t\r\n"\'„“”‚‘’»«'
# Mit weniger Restzeit des wartenden Erkunders wird nicht mehr gefragt und
# ihm nichts mehr gesagt (er schließt die Mission nach seiner Frist selbst).
SPAETESTENS_S = 5.0


# ---- kleine Bausteine --------------------------------------------------------

def ist_ja(wortlaut: str) -> bool:
    """Nur ein klares „ja“ gibt die Fahrt frei: „ja“, „Ja.“ oder „ja!“.

    Alles andere ist kein Ja, auch „ja?“ (eine Rückfrage), „ja…“ oder
    „ja, aber …“ (Gegenprüfung 24.11.2026).
    """
    return wortlaut.strip(ANFUEHRUNG).lower() in ('ja', 'ja.', 'ja!')


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
    while pid >= 1 and pid not in pids:
        pids.add(pid)                    # auch PID 1 (eigener Namensraum, Init)
        if pid == 1:
            break
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


def ein_sigint(pid: Optional[int], merkmal: str, lauf: Optional['Lauf'] = None) -> bool:
    """Genau ein SIGINT an genau diesen Prozess, nur wenn er der erwartete ist.

    Mit ``lauf``: nur, wenn die PID in diesem Lauf noch keines bekommen hat (auch
    nicht von einem Begleiter); vermerkt wird vor dem Senden.
    """
    if not pid or int(pid) <= 0 or not laeuft(pid, merkmal):
        return False
    if lauf is not None:
        if int(pid) in lauf.signalisiert():
            return False
        lauf.vermerke_sigint(int(pid))
    try:
        os.kill(int(pid), signal.SIGINT)
    except ProcessLookupError:
        return False
    return True


def zahl(wert) -> Optional[float]:
    """Eine endliche Zahl oder None („nan“, „inf“, „-“, fehlt)."""
    try:
        ergebnis = float(wert)
    except (TypeError, ValueError):
        return None
    return ergebnis if math.isfinite(ergebnis) else None


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
    """Erst in eine eigene Nebendatei, dann umbenennen: Leser sehen nie eine halbe
    Datei, und zwei Schreiber kommen sich nicht in die Quere (Gegenprüfung 24.11.2026)."""
    pfad = Path(pfad)
    nummer, neu = tempfile.mkstemp(dir=pfad.parent, prefix=pfad.name + '.', suffix='.neu')
    try:
        with os.fdopen(nummer, 'w', encoding='utf-8') as datei:
            json.dump(daten, datei, indent=1, ensure_ascii=False)
        os.replace(neu, pfad)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(neu)
        raise


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


def _wahl_werkzeuge():
    """``wahl_satz`` und ``einzeilig`` aus dem Lotsen, erst bei Bedarf geladen
    (numpy): ``aufraeumen`` und ``verfolgen`` gehen auch ohne."""
    if str(WERKZEUGE.parent) not in sys.path:
        sys.path.insert(0, str(WERKZEUGE.parent))
    from lotse.wahl import einzeilig, wahl_satz
    return wahl_satz, einzeilig


def wahl_aus_datei(pfad, kennung: str) -> Tuple[Optional[dict], str]:
    """Die Wahl-Datei, nur wenn genau diese Bytes zur Kennung passen; sonst Grund.

    Die Frage an den Menschen entsteht aus dieser Datei, nicht aus Textzeilen,
    die zu einer anderen Wahl gehören könnten (Gegenprüfung 24.11.2026).
    """
    try:
        roh = Path(pfad).read_bytes()
    except (OSError, TypeError):
        return None, 'Wahl-Datei fehlt'
    if hashlib.sha256(roh).hexdigest()[:6] != kennung:
        return None, 'Wahl-Datei passt nicht zur Kennung'
    try:
        daten = json.loads(roh.decode('utf-8'))
    except ValueError:
        return None, 'Wahl-Datei ist kein JSON'
    if not isinstance(daten, dict) or daten.get('art') != 'ki_wahl' or daten.get('quelle') != 'ki':
        return None, 'keine Wahl der KI'
    if isinstance(daten.get('nr'), bool) or not isinstance(daten.get('nr'), int):
        return None, 'Nummer fehlt'
    try:
        wahl_satz, _ = _wahl_werkzeuge()
        wahl_satz(daten)
    except ImportError as fehler:
        return None, f'Lotse nicht ladbar ({fehler})'
    except (KeyError, TypeError, ValueError):
        return None, 'Maße der Wahl fehlen'
    return daten, ''


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

    @contextlib.contextmanager
    def sperre(self, name: str):
        """Exklusive Sperre dieses Laufs (flock auf ``.<name>.sperre``); je Name eigene."""
        with open(self.ordner / f'.{name}.sperre', 'a', encoding='utf-8') as datei:
            fcntl.flock(datei, fcntl.LOCK_EX)
            yield

    def merke(self, **teile) -> dict:
        """Lesen, ändern, schreiben unter einer Sperre: Zwei Befehle desselben Laufs
        (etwa zweimal „verfolgen“) verlieren sonst gegenseitig ihre Einträge."""
        with self.sperre('zustand'):
            zustand = self.zustand()
            zustand.update(teile)
            schreibe_json(self.zustand_datei, zustand)
        return zustand

    def signalisiert(self) -> set:
        """PIDs, die in diesem Lauf schon ein SIGINT bekommen haben."""
        return {int(p) for p in lies_json(self.ordner / 'signale.json').get('pids', [])
                if str(p).isdigit()}

    def vermerke_sigint(self, pid: int) -> None:
        with self.sperre('signale'):
            pids = self.signalisiert() | {int(pid)}
            schreibe_json(self.ordner / 'signale.json', {'pids': sorted(pids)})

    def protokoll(self, text: str) -> None:
        with open(self.ordner / 'ablauf.log', 'a', encoding='utf-8') as datei:
            datei.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {text}\n')


def starte_losgeloest(befehl: List[str], ausgabe: Path) -> subprocess.Popen:
    """Losgelöst starten (eigene Sitzung): lebt weiter, wenn dieser Aufruf endet."""
    with open(ausgabe, 'ab') as datei:
        return subprocess.Popen(befehl, stdout=datei, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)


def sigint_an(lauf: Lauf, prozess: subprocess.Popen) -> None:
    """Genau ein SIGINT an ein eigenes Kind; vermerkt, damit niemand (auch nicht
    ``aufraeumen``) ein zweites schickt."""
    lauf.vermerke_sigint(prozess.pid)
    prozess.send_signal(signal.SIGINT)


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


def ende_senden(lauf: Lauf, z: dict, quelle: str, wartephase_unix) -> int:
    """Dem wartenden Erkunder „Ende“ sagen. Das fährt nie."""
    befehl = in_umgebung(z['umgebung_stack'], [
        z['python'], Path(z['werkzeuge']) / 'fahrziel_senden.py', '--ende', '--quelle', quelle,
        '--warten', warten_auf_den_erkunder(z, wartephase_unix)])
    lauf.protokoll('ende ' + ' '.join(shlex.quote(t) for t in befehl[5:]))
    rc = fuehre_aus(befehl, lauf.werkzeug, 120)
    for zeile in zeilen(lauf.werkzeug)[-4:]:
        print('  ' + zeile)
    print(f'Ende an den Erkunder (Quelle {quelle}): rc={rc}. Amadeus fährt nicht.')
    return rc


def ende_wenn_er_wartet(lauf: Lauf, z: dict, wartephase_unix, quelle: str) -> Optional[int]:
    """„Ende“ nur an den Erkunder, der zu diesem Lauf wartet, sonst nichts senden."""
    grund = nicht_mehr_dran(lauf, z, wartephase_unix)
    if grund:
        print(f'Kein Ende gesendet: {grund}. Amadeus fährt nicht.')
        lauf.protokoll(f'kein Ende (Quelle {quelle}): {grund}')
        return None
    return ende_senden(lauf, z, quelle, wartephase_unix)


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
                     '--dauer', str(z['dauer']), '--bereit-nach', str(z['bereit_nach'])]
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
                sigint_an(lauf, aufnahme)                  # genau eines: sie schreibt
                weitergegeben = True
            time.sleep(0.2)
        melde(aufnahme_rc=aufnahme.returncode)
    # Die Kamera läuft nur während des Rundblicks: genau ein SIGINT, dann warten.
    if kamera.poll() is None:
        sigint_an(lauf, kamera)
        try:
            kamera.wait(timeout=30)
        except subprocess.TimeoutExpired:
            lauf.protokoll('Kamera nach 30 s noch nicht beendet')
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


def fahrt_erlaubt(lauf: Lauf, z: dict) -> Optional[str]:
    """Grund, warum nicht gefahren werden darf; None, wenn alles passt.

    Dieselben Bedingungen wie in ``antwort``, hier ein zweites Mal geprüft: Der
    interne Befehl ``_fahrt`` darf ohne ein „ja“ zu genau dieser Wahl, an den
    Erkunder genau dieses Laufs, nichts tun.
    """
    w, antwort = z.get('wahl') or {}, z.get('antwort') or {}
    if z.get('nur_stand'):
        return 'Vorlauf im Stand'
    if antwort.get('ja') is not True or not ist_ja(str(antwort.get('wortlaut', ''))):
        return 'kein Ja eingetragen'
    if w.get('rc') != 0 or not w.get('kennung') or not w.get('datei'):
        return 'keine Wahl der KI'
    if antwort.get('kennung') != w['kennung']:
        return 'das Ja gilt einer anderen Wahl'
    datei = Path(w['datei'])
    if not datei.is_file() or kennung_der_datei(datei) != w['kennung']:
        return 'Wahl-Datei fehlt oder ist verändert'
    kamera = laufende(MERKMAL['kamera'], MERKMAL['aufnahme'])
    if kamera:
        return f'Kamera oder Aufnahme laufen noch (PID {kamera})'
    fahrt = laufende(MERKMAL['fahrt_begleiter'], MERKMAL['werkzeug'])
    if fahrt:
        return f'eine andere Fahrt läuft (PID {fahrt})'
    return nicht_mehr_dran(lauf, z, w.get('wartephase_unix'))


def begleiter_fahrt(ordner: Path) -> int:
    lauf = Lauf(ordner)
    z = lauf.zustand()
    stand = {'phase': 'faehrt', 'pid': os.getpid(), 'start_unix': round(time.time(), 1)}
    try:                                 # nur einmal je Lauf: die Datei darf es noch nicht geben
        os.close(os.open(lauf.fahrt_datei, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
    except FileExistsError:
        lauf.protokoll('_fahrt abgelehnt: es gab schon eine Fahrt')
        return RC_NEIN
    grund = fahrt_erlaubt(lauf, z)
    if grund is None:
        # Das Werkzeug bekommt eine Kopie genau der geprüften Bytes; die Wahl-Datei
        # selbst könnte sich bis zu seinem Lesen noch ändern (Gegenprüfung 24.11.2026).
        try:
            roh = Path(z['wahl']['datei']).read_bytes()
        except OSError:
            roh = b''
        if hashlib.sha256(roh).hexdigest()[:6] != z['wahl']['kennung']:
            grund = 'Wahl-Datei fehlt oder ist verändert'
        else:
            (lauf.ordner / 'wahl_gefahren.json').write_bytes(roh)
    if grund is not None:
        stand.update(phase='abgelehnt', grund=grund)
        schreibe_json(lauf.fahrt_datei, stand)
        lauf.protokoll(f'_fahrt abgelehnt: {grund}')
        return RC_NEIN
    marke = Ende().anmelden()            # ab hier setzt ein Signal nur die Marke
    try:
        if marke.gesetzt():
            stand.update(phase='abgelehnt', grund='Signal vor dem Start')
            schreibe_json(lauf.fahrt_datei, stand)
            return RC_NEIN
        schreibe_json(lauf.fahrt_datei, stand)
        befehl = in_umgebung(z['umgebung_stack'], [
            z['python'], Path(z['werkzeuge']) / 'fahrziel_senden.py', '--zur-tuer', '--wahl',
            lauf.ordner / 'wahl_gefahren.json', '--hinter', '0.45',
            '--warten', warten_auf_den_erkunder(z, z['wahl'].get('wartephase_unix')),
            '--beobachten', '600'])
        lauf.protokoll('fahrt ' + ' '.join(shlex.quote(str(t)) for t in befehl[5:]))
        with open(lauf.werkzeug, 'ab') as datei:
            werkzeug = subprocess.Popen(befehl, stdout=datei, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL)
        stand['werkzeug_pid'] = werkzeug.pid
        schreibe_json(lauf.fahrt_datei, stand)
        weitergegeben = False
        while werkzeug.poll() is None:
            if marke.gesetzt() and not weitergegeben:
                sigint_an(lauf, werkzeug)  # genau eines; es sendet danach nichts mehr
                weitergegeben = True
            time.sleep(0.2)
        stand.update(phase='fertig', rc=werkzeug.returncode, ende_unix=round(time.time(), 1))
        schreibe_json(lauf.fahrt_datei, stand)
    finally:
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
            'bereit_nach': a.bereit_nach,
            'dauer': a.dauer, 'nachlauf': a.nachlauf, 'frist': a.frist,
            'hoechstens': 300.0 if a.hoechstens is None else a.hoechstens, 'tuer': a.tuer,
            'nur_stand': bool(getattr(a, 'nur_stand', False)),
            'marke': str(Path(a.marke).expanduser()),
            'werkzeuge': str(Path(a.werkzeuge).expanduser().resolve()) if a.werkzeuge
            else str(WERKZEUGE)}


def befehl_start(a) -> int:
    lauf = Lauf.aus(a)
    z = konfiguration(a)
    if a.nur_stand:
        z['dauer'] = a.dauer_stand
    if zahl(z['frist']) is None or not 0.0 < z['frist'] <= 1800.0:
        print('--frist muss zwischen 0 und 1800 s liegen (so lange wartet der Erkunder). '
              'Nichts gestartet.')
        return RC_NEIN
    fehlen = umgebungen_fehlen(z)
    if fehlen:
        print('Umgebungsdatei fehlt: ' + '; '.join(fehlen) + '. Nichts gestartet.')
        return RC_NEIN
    marke = Path(z['marke'])
    marke.parent.mkdir(parents=True, exist_ok=True)
    # Prüfen und Starten am Stück: Zwei gleichzeitige Starts ergäben zwei Kameras.
    with open(marke.parent / '.start.sperre', 'a', encoding='utf-8') as sperre:
        fcntl.flock(sperre, fcntl.LOCK_EX)
        if lauf.ordner.exists():
            # Auch ohne zustand.json: Alte Ausgaben im Ordner würden sonst mit
            # neuen vermischt (Gegenprüfung 24.11.2026).
            print(f'Lauf {a.lauf} von {a.auftrag} gibt es schon ({lauf.ordner}); für eine '
                  'Wiederholung eine neue Laufkennung nehmen (zum Beispiel 1w).')
            return RC_NEIN
        schon = laufende(MERKMAL['kamera'], MERKMAL['aufnahme'], MERKMAL['begleiter'])
        if schon:
            print(f'Kamera, Aufnahme oder Begleiter laufen schon (PID {schon}). '
                  'Nichts gestartet.')
            return RC_NEIN
        fahrt = laufende(MERKMAL['fahrt_begleiter'], MERKMAL['werkzeug'])
        if fahrt:
            print(f'Eine Fahrt läuft noch (PID {fahrt}); erst „verfolgen“, bis sie fertig '
                  'ist. Nichts gestartet.')
            return RC_NEIN
        lauf.ordner.mkdir(parents=True, exist_ok=True)
        z['start_unix'] = round(time.time(), 3)
        schreibe_json(lauf.zustand_datei, z)
        # Ab jetzt gilt keine Antwort eines früheren Laufs mehr, auch nicht aus einem
        # anderen Auftrag oder Basis-Ordner (Gegenprüfung 24.11.2026).
        schreibe_json(marke, {'ordner': str(lauf.ordner), 'start_unix': z['start_unix']})
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
        print(f'{kamera_zustand(lauf)} Keine Mission starten.')
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
        print('Nicht bereit: ' + '; '.join(gruende) + f'. {kamera_zustand(lauf)} '
              'Keine Mission starten.')
        return RC_NEIN
    if z['nur_stand']:
        print(f'Aufnahme im Stand läuft ({z["dauer"]:.0f} s). Keine Mission starten; danach: '
              'wahl.')
    else:
        print('Aufnahme läuft und endet von selbst 5 s nach dem Rundblick. Jetzt genau einmal '
              'die Mission starten.')
    return RC_OK


def kamera_laeuft(lauf: Lauf) -> List[str]:
    """Was von Kamera und Aufnahme dieses Laufs noch läuft (Argumente geprüft)."""
    b = lies_json(lauf.begleiter_datei)
    return [name for name in ('kamera', 'aufnahme') if laeuft(b.get(f'{name}_pid'), MERKMAL[name])]


def kamera_zustand(lauf: Lauf) -> str:
    noch = kamera_laeuft(lauf)
    return ('Kamera und Aufnahme beendet.' if not noch
            else f'NOCH NICHT BEENDET: {", ".join(noch)}.')


def stoppe_begleiter(lauf: Lauf) -> None:
    z = lauf.zustand()
    if ein_sigint(z.get('begleiter_pid'), MERKMAL['begleiter'], lauf):
        lauf.protokoll('Begleiter: ein SIGINT')
        warte_bis_beendet(z.get('begleiter_pid'), MERKMAL['begleiter'], 40)


def restzeit_s(z: dict, wartephase_unix) -> Optional[float]:
    """So lange wartet der Erkunder dieses Laufs noch auf ein Fahrziel; None: unbekannt
    (keine endliche Zahl, oder die Wartephase läge in der Zukunft)."""
    frist, beginn = zahl(z.get('frist')), zahl(wartephase_unix)
    if frist is None or beginn is None or beginn > time.time() + SPAETESTENS_S:
        return None
    return frist - (time.time() - beginn)


def warten_auf_den_erkunder(z: dict, wartephase_unix) -> str:
    """``--warten`` des Fahrwerkzeugs: höchstens 60 s und nie über die Frist hinaus;
    sonst bediente es einen Erkunder, der erst später zu warten beginnt."""
    rest = restzeit_s(z, wartephase_unix)
    return str(int(max(1.0, min(60.0, (rest if rest is not None else 0.0) - SPAETESTENS_S))))


def spaeterer_lauf(lauf: Lauf, z: dict) -> Optional[str]:
    """Ein Lauf, der nach diesem gestartet wurde: im selben Ordner oder laut der
    Marke, die jeder Start schreibt (auch mit anderem Auftrag oder anderer Basis)."""
    eigener = zahl(z.get('start_unix'))
    if eigener is None:
        return None
    andere = [(ordner, lies_json(ordner / 'zustand.json').get('start_unix'))
              for ordner in sorted(lauf.ordner.parent.glob('lauf*')) if ordner != lauf.ordner]
    marke = lies_json(Path(z['marke'])) if z.get('marke') else {}
    if marke.get('ordner') and Path(marke['ordner']) != lauf.ordner:
        andere.append((Path(marke['ordner']), marke.get('start_unix')))
    for ordner, start in andere:
        if (zahl(start) or 0.0) > eigener:
            return ordner.name if ordner.parent == lauf.ordner.parent else str(ordner)
    return None


def nicht_mehr_dran(lauf: Lauf, z: dict, wartephase_unix) -> Optional[str]:
    """Warum dieser Lauf dem Erkunder nichts mehr sagen darf; None, solange er wartet.

    Ein Ja (oder Ende) gilt nur für den Erkunder, der zu genau dieser Frage
    wartet: nicht nach seiner Frist und nicht, wenn danach ein neuer Lauf
    begonnen hat. Sonst träfe das Fahrwerkzeug den Erkunder des neuen Laufs
    (Gegenprüfung 24.11.2026).
    """
    if zahl(z.get('start_unix')) is None:
        return 'Startzeit dieses Laufs unbekannt'
    spaeter = spaeterer_lauf(lauf, z)
    if spaeter:
        return f'danach wurde {spaeter} gestartet'
    rest = restzeit_s(z, wartephase_unix)
    if rest is None:
        return 'Beginn der Wartephase unbekannt'
    if not rest >= SPAETESTENS_S:
        return 'die Frist des Erkunders ist abgelaufen, er wartet nicht mehr'
    return None


def zeit_satz(rest_s: Optional[float]) -> str:
    if rest_s is None or not math.isfinite(rest_s):
        return ''
    if rest_s >= 120.0:
        return f'(Der Erkunder wartet noch etwa {math.floor(rest_s / 60.0)} Minuten.)'
    if rest_s >= 60.0:
        return '(Der Erkunder wartet noch etwa eine Minute.)'
    return '(Der Erkunder wartet noch weniger als eine Minute.)'


def mit_restzeit(frage: str, rest_s: Optional[float]) -> str:
    """Die gespeicherte Frage mit der Restzeit von jetzt (nie die vom ersten Aufruf)."""
    satz = zeit_satz(rest_s)
    if not satz or not frage.endswith('“'):
        return frage
    return frage[:-1] + ' ' + satz + '“'


def _mit_punkt(satz: str) -> str:
    satz = satz.strip()
    return satz if satz.endswith(('.', '!', '?', '“', '"')) else satz + '.'


def baue_frage(daten: dict, wahl_zeilen: List[str], tuer: str) -> str:
    """Die Frage an den Menschen, ohne Restzeit (die kommt bei jeder Ausgabe mit
    ``mit_restzeit`` neu dazu). Wahl, Begründung und Gefahren kommen aus der
    geprüften Wahl-Datei (``daten``); aus dem Wahl-Text nur die Übersicht, was
    die KI in jeder Nummer sieht."""
    wahl_satz, einzeilig = _wahl_werkzeuge()
    begruendung = einzeilig(daten.get('begruendung') or '')
    gefahren = daten.get('gefahren') or []
    gefahren = einzeilig(', '.join(map(str, gefahren if isinstance(gefahren, list)
                                       else [gefahren])))
    nummern = [einzeilig(z) for z in wahl_zeilen if z.startswith('  Nr. ')]
    teile = ['Die KI hat gewählt.', _mit_punkt(wahl_satz(daten))]
    if begruendung:
        teile.append(_mit_punkt(f'Begründung der KI: {begruendung}'))
    if nummern:
        teile.append('Was sie in jeder Nummer sieht: ' + ' / '.join(nummern) + '.')
    if gefahren:
        teile.append(_mit_punkt(f'Gefahren laut KI: {gefahren}'))
    teile.append('Die Bilder mit den Nummern zeigt das Lotsen-Fenster auf dem KI-Rechner. '
                 f'Ist die gewählte Öffnung {tuer}, und soll Amadeus hindurchfahren? '
                 "Schreib ‚ja' oder ‚nein'.")
    return '„' + ' '.join(teile) + '“'


def befehl_wahl(a) -> int:
    lauf = Lauf.aus(a)
    z = lauf.zustand()
    if not z:
        print(f'Zu Lauf {a.lauf} gibt es keinen Start ({lauf.zustand_datei}).')
        return RC_NEIN
    if 'wahl' in z:                                   # nie zweimal fragen
        w = z['wahl']
        print(f'Die Wahl zu Lauf {a.lauf} steht schon fest (rc={w.get("rc")}).')
        if 'antwort' in z:
            print(f'Antwort schon eingetragen: {z["antwort"].get("wortlaut")!r}.')
        elif w.get('frage'):
            grund = nicht_mehr_dran(lauf, z, w.get('wartephase_unix'))
            if grund:
                print(f'Nicht mehr fragen: {grund}.')
                return RC_NEIN
            print(mit_restzeit(w['frage'], restzeit_s(z, w.get('wartephase_unix'))))
        return RC_OK if w.get('rc') == 0 else RC_NEIN
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
    print(f'Aufnahme: {letzte_zeile(lauf.aufnahme, "ERGEBNIS") or "kein Ergebnis"}; '
          f'{kamera_zustand(lauf)} (Kamera rc={b.get("kamera_rc")}, Fehlerzeilen im Log: '
          f'{b.get("kamera_fehlerzeilen", "-")})')
    if b.get('wahl_rc') is None:
        grund = ('Aufnahme abgebrochen' if b.get('abgebrochen')
                 else 'keine Runde' if erg.get('runde') in (None, '-')
                 else 'Lage in der Karte fehlt' if erg.get('lage') != 'ja'
                 else f'kein Rundblick bis zur Wartephase (Ende: {erg.get("grund")})')
        print(f'Die KI wird nicht gefragt: {grund}.')
        lauf.merke(wahl={'rc': RC_KEINE_RUNDE, 'grund': grund})
        if not z['nur_stand'] and erg.get('grund') == 'wartephase':
            ende_wenn_er_wartet(lauf, z, erg.get('wartephase_unix'), 'ki')
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
            ende_wenn_er_wartet(lauf, z, wahl['wartephase_unix'], 'ki')
        print('LAUF ergebnis=nicht_gefahren grund=keine_wahl')
        return RC_NEIN
    daten, grund = wahl_aus_datei(wahl['datei'], wahl['kennung'])
    if daten is None:
        lauf.merke(wahl={**wahl, 'rc': RC_NEIN, 'grund': grund})
        print(f'Die Wahl lässt sich nicht prüfen ({grund}). Keine Frage an den Menschen.')
        if not z['nur_stand']:
            ende_wenn_er_wartet(lauf, z, wahl['wartephase_unix'], 'ki')
        print('LAUF ergebnis=nicht_gefahren grund=keine_wahl')
        return RC_NEIN
    if z['nur_stand']:
        lauf.merke(wahl=wahl)
        print(f'Vorlauf im Stand: Wahl der KI mit Kennung {wahl["kennung"]}; keine Frage, '
              'nichts gesendet. Weiter mit: messen.')
        return RC_OK
    kamera = laufende(MERKMAL['kamera'], MERKMAL['aufnahme'])
    if kamera:
        # Die Kamera läuft nie während der Fahrt; erst fragen, wenn sie aus ist.
        print(f'Kamera oder Aufnahme laufen noch (PID {kamera}). Noch keine Frage. In einigen '
              'Sekunden „wahl“ erneut aufrufen; enden sie nicht: „aufraeumen“, nicht fahren, '
              'berichten.')
        return RC_LAEUFT
    grund = nicht_mehr_dran(lauf, z, wahl['wartephase_unix'])
    if grund:
        # Ein Ja könnte nichts mehr bewirken: nicht fragen (der Erkunder schließt selbst).
        lauf.merke(wahl={**wahl, 'rc': RC_NEIN, 'grund': grund})
        print(f'Keine Frage an den Menschen: {grund}. Nichts gesendet.')
        print('LAUF ergebnis=nicht_gefahren grund=zu_spaet')
        return RC_NEIN
    frage = baue_frage(daten, text, z['tuer'])
    wahl['frage'] = frage
    lauf.merke(wahl=wahl)
    (lauf.ordner / 'frage.txt').write_text(frage + '\n', encoding='utf-8')
    print('FRAGE AN CHRISTOPHER (wörtlich weitergeben):')
    print(mit_restzeit(frage, restzeit_s(z, wahl['wartephase_unix'])))
    print('Seine Antwort danach eintragen (Kennung der Wahl: ' + wahl['kennung'] + '):')
    print(f'  python3 {Path(__file__).resolve()} antwort --auftrag {a.auftrag} '
          f'--basis {shlex.quote(str(lauf.ordner.parent))} --lauf {a.lauf} '
          f'--kennung {wahl["kennung"]} --wortlaut "<seine Antwort>"')
    return RC_OK


def befehl_antwort(a) -> int:
    lauf = Lauf.aus(a)
    if not lauf.zustand_datei.is_file():
        print(f'Zu Lauf {a.lauf} gibt es keinen Start ({lauf.ordner}). Nichts aufgerufen.')
        return RC_NEIN
    # Prüfen und Eintragen am Stück: Zwei gleichzeitige Antworten ergaben sonst eine
    # Fahrt und ein Ende (Gegenprüfung 24.11.2026). Langsames (Ende, Verfolgen) danach.
    with lauf.sperre('antwort'):
        rc, z, ja = antwort_pruefen_und_eintragen(lauf, a)
    if rc is not None:
        return rc
    if not ja:
        print('Kein Ja: Amadeus fährt nicht.')
        ende_wenn_er_wartet(lauf, z, (z.get('wahl') or {}).get('wartephase_unix'), 'mensch')
        print('LAUF ergebnis=nicht_gefahren grund=kein_ja')
        return RC_OK
    print('Ja: Das Werkzeug misst neu und gibt dem Erkunder das Fahrziel (Anfahrt und '
          'Durchfahrt in einer Mission).')
    return verfolge(lauf, a.warten)


def antwort_pruefen_und_eintragen(lauf: Lauf, a) -> Tuple[Optional[int], dict, bool]:
    """(Rückgabe bei Ablehnung oder None, Zustand, ja). Bei „ja“ ist ``_fahrt`` gestartet."""
    z = lauf.zustand()
    if 'antwort' in z:
        print(f'Zu Lauf {a.lauf} ist schon eine Antwort eingetragen: {z["antwort"]["wortlaut"]!r}. '
              'Nichts aufgerufen.')
        return RC_NEIN, z, False
    w = z.get('wahl') or {}
    if w.get('rc') != 0 or not w.get('kennung') or z.get('nur_stand'):
        print('Zu diesem Lauf gibt es keine Wahl, zu der eine Antwort passen könnte. '
              'Nichts aufgerufen.')
        return RC_NEIN, z, False
    if a.kennung != w['kennung']:
        print(f'Die Kennung {a.kennung!r} passt nicht zur Wahl dieses Laufs. Nichts aufgerufen.')
        return RC_NEIN, z, False
    datei = Path(w['datei'])
    if not datei.is_file() or kennung_der_datei(datei) != w['kennung']:
        print('Die Wahl-Datei fehlt oder hat sich seit der Frage geändert. Nichts aufgerufen.')
        return RC_NEIN, z, False
    grund = nicht_mehr_dran(lauf, z, w.get('wartephase_unix'))
    if grund:
        # Auch kein Ende: Es träfe womöglich den Erkunder eines neuen Laufs.
        lauf.protokoll(f'antwort {a.wortlaut!r} zu spät: {grund}')
        print(f'Zu spät für Lauf {a.lauf}: {grund}. Antwort nicht eingetragen, nichts '
              'aufgerufen, auch kein Ende. Bei einer Wiederholung gilt nur die Frage des '
              'neuen Laufs.')
        return RC_NEIN, z, False
    fahrt = laufende(MERKMAL['fahrt_begleiter'], MERKMAL['werkzeug'])
    if fahrt:
        print(f'Eine Fahrt läuft noch (PID {fahrt}). Antwort nicht eingetragen, nichts '
              'aufgerufen.')
        return RC_NEIN, z, False
    if lauf.fahrt_datei.exists():
        print('Zu diesem Lauf gab es schon einen Fahrversuch (fahrt.json). Antwort nicht '
              'eingetragen, nichts aufgerufen.')
        return RC_NEIN, z, False
    stoppe_begleiter(lauf)                    # läuft der Begleiter noch: zuerst beenden
    ja = ist_ja(a.wortlaut)
    kamera = laufende(MERKMAL['kamera'], MERKMAL['aufnahme']) if ja else []
    if kamera:
        # Die Kamera läuft nie während der Fahrt (KI-F9-Regel); ein Nein geht immer.
        lauf.protokoll(f'antwort {a.wortlaut!r} zurückgestellt: Kamera/Aufnahme PID {kamera}')
        print(f'Kamera oder Aufnahme laufen noch (PID {kamera}). Antwort nicht eingetragen, '
              'nichts gesendet. Gehören sie zu diesem Lauf: „aufraeumen“, dann dieselbe '
              'Antwort noch einmal eintragen; sonst nicht fahren und berichten.')
        return RC_NEIN, z, False
    with open(lauf.ordner / 'christopher.txt', 'a', encoding='utf-8') as datei_c:
        datei_c.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {a.wortlaut}\n')
    z = lauf.merke(antwort={'wortlaut': a.wortlaut, 'ja': ja, 'kennung': a.kennung,
                            'unix': round(time.time(), 1)})
    lauf.protokoll(f'antwort {a.wortlaut!r} -> {"ja" if ja else "kein ja"}')
    if ja:
        begleiter = starte_losgeloest([sys.executable, str(Path(__file__).resolve()), '_fahrt',
                                       '--ordner', str(lauf.ordner)], lauf.ordner / 'fahrt.log')
        z = lauf.merke(fahrt_begleiter_pid=begleiter.pid)
    return None, z, ja


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
        if f.get('phase') in ('fertig', 'abgelehnt') or not laeuft(
                z.get('fahrt_begleiter_pid'), MERKMAL['fahrt_begleiter']):
            f = lies_json(lauf.fahrt_datei)
            if f.get('phase') == 'abgelehnt':
                print(f'Fahrt abgelehnt: {f.get("grund")}. Nichts gesendet.')
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
    """Alles dieses Laufs beenden; jede PID bekommt im ganzen Lauf höchstens ein SIGINT.

    Zuerst die Begleiter: Sie geben genau ein Signal an ihre Kinder weiter und warten
    auf sie (die Kamera bis 30 s). Ein Kind bekommt hier nur dann eines, wenn sein
    Begleiter nicht mehr läuft und es noch keines hatte. Vorher bekam die Kamera
    nach 15 s ein zweites (Gegenprüfung 24.11.2026).
    """
    lauf = Lauf.aus(a)
    z = lauf.zustand()
    begleiter = {'begleiter': z.get('begleiter_pid'),
                 'fahrt_begleiter': z.get('fahrt_begleiter_pid')}
    for name, pid in begleiter.items():
        if ein_sigint(pid, MERKMAL[name], lauf):
            print(f'{name}: ein SIGINT an PID {pid}')
            lauf.protokoll(f'aufraeumen: SIGINT an {name} {pid}')
        warte_bis_beendet(pid, MERKMAL[name], 45)
    b, f = lies_json(lauf.begleiter_datei), lies_json(lauf.fahrt_datei)
    kinder = [('aufnahme', b.get('aufnahme_pid'), 'begleiter'),
              ('kamera', b.get('kamera_pid'), 'begleiter'),
              ('werkzeug', f.get('werkzeug_pid'), 'fahrt_begleiter')]
    for name, pid, eltern in kinder:
        if laeuft(begleiter[eltern], MERKMAL[eltern]):
            continue                                   # sein Begleiter kümmert sich noch
        if ein_sigint(pid, MERKMAL[name], lauf):
            print(f'{name}: ein SIGINT an PID {pid}')
            lauf.protokoll(f'aufraeumen: SIGINT an {name} {pid}')
            warte_bis_beendet(pid, MERKMAL[name], 15)
    alle = list(begleiter.items()) + [(name, pid) for name, pid, _ in kinder]
    schon = lauf.signalisiert()
    uebrig = [f'{name} {pid}' + (' (hatte schon ein SIGINT)' if int(pid) in schon else '')
              for name, pid in alle if laeuft(pid, MERKMAL[name])]
    print('Alles beendet.' if not uebrig else
          'Noch nicht beendet: ' + ', '.join(uebrig) + '. Kein zweites Signal; berichten.')
    return RC_OK if not uebrig else RC_NEIN


def eingabe() -> argparse.ArgumentParser:
    e = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    # Die internen Befehle der Begleiter (_rundblick, _fahrt) stehen nicht in der Hilfe.
    unter = e.add_subparsers(
        dest='befehl', required=True,
        metavar='{pruefe-umgebung,start,wahl,antwort,verfolgen,messen,aufraeumen}')

    def welcher_lauf(p, lauf=True):
        p.add_argument('--auftrag', default='kif10',
                       help='Kennung des Auftrags (Ordner ~/ki_trockenlauf_<auftrag>)')
        if lauf:
            p.add_argument('--lauf', required=True, help='Kennung des Laufs, zum Beispiel 1, 2w')
        p.add_argument('--basis', help='Ordner der Läufe (Vorgabe ~/ki_trockenlauf_<auftrag>)')

    def warten(p):
        p.add_argument('--warten', type=float, default=100.0,
                       help='so lange wartet ein Aufruf, dann rc 10 (erneut aufrufen), s')

    def hoechstens(p):
        p.add_argument('--hoechstens', type=float, default=None,
                       help='kommt bis dahin (ab start) keine Wartephase: Abbruch, s '
                            '(Vorgabe 300; bei wahl gilt, was hier steht, sonst der Wert '
                            'vom Start)')

    def fuer_den_ganzen_lauf(p):
        """Gilt für den ganzen Lauf und wird beim Start gespeichert. Die späteren
        Schritte nehmen nur den gespeicherten Wert und bieten diese Angaben nicht an:
        Ein „wahl --tuer …“ wurde vorher still übergangen (Gegenprüfung 24.11.2026)."""
        p.add_argument('--umgebung-kamera', default=VORGABE['umgebung_kamera'])
        p.add_argument('--umgebung-stack', default=VORGABE['umgebung_stack'])
        p.add_argument('--python', default='python3',
                       help='Python mit rclpy in beiden Umgebungen')
        p.add_argument('--runden', default=VORGABE['runden'])
        p.add_argument('--wahl-ordner', default=VORGABE['wahl_ordner'])
        p.add_argument('--kamera-befehl', default=VORGABE['kamera_befehl'])
        p.add_argument('--kamera-vorlauf', type=float, default=20.0)
        p.add_argument('--bereit-nach', type=float, default=8.0,
                       help='so lange misst die Aufnahme die Raten bis zur Zeile BEREIT, s')
        p.add_argument('--dauer', type=float, default=420.0, help='höchste Aufnahmedauer, s')
        p.add_argument('--nachlauf', type=float, default=5.0,
                       help='so lange nimmt die Aufnahme nach dem Rundblick noch auf, s')
        p.add_argument('--frist', type=float, default=420.0,
                       help='so lange wartet der Erkunder auf ein Fahrziel, s')
        hoechstens(p)
        p.add_argument('--tuer', default='die Labortür',
                       help='so heißt die erwartete Tür in der Frage an den Menschen')
        p.add_argument('--werkzeuge', help=argparse.SUPPRESS)       # nur für Tests
        p.add_argument('--marke', default=VORGABE['marke'], help=argparse.SUPPRESS)

    p = unter.add_parser('pruefe-umgebung', help='beide Umgebungen prüfen')
    welcher_lauf(p, lauf=False)
    fuer_den_ganzen_lauf(p)
    p = unter.add_parser('start', help='Kamera und Aufnahme starten (losgelöst)')
    welcher_lauf(p)
    fuer_den_ganzen_lauf(p)
    p.add_argument('--nur-stand', action='store_true',
                   help='Vorlauf ohne Mission: Aufnahme im Stand, keine Frage, nichts senden')
    p.add_argument('--dauer-stand', type=float, default=10.0)
    p.add_argument('--mindestrate', type=float, default=1.8, help='Bilder je Sekunde')
    p.add_argument('--bereit-warten', type=float, default=60.0)
    p = unter.add_parser('wahl', help='Wahl der KI abwarten, Frage bauen')
    welcher_lauf(p)
    warten(p)
    hoechstens(p)
    p = unter.add_parser('antwort', help='Antwort des Menschen eintragen')
    welcher_lauf(p)
    warten(p)
    p.add_argument('--kennung', required=True)
    p.add_argument('--wortlaut', required=True)
    for name, hilfe in (('verfolgen', 'die Fahrt weiter zeigen'),
                        ('messen', 'nur messen, nichts senden (Vorlauf)'),
                        ('aufraeumen', 'alles dieses Laufs mit je einem SIGINT beenden')):
        p = unter.add_parser(name, help=hilfe)
        welcher_lauf(p)
        warten(p)
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
