#!/usr/bin/env python3
"""Lotsen-Fenster: das Programm für den Bildschirm des KI-Rechners.

Startet den Lotsen-Dienst (``lotse_dienst.py``) und zeigt in einem Fenster
des Browsers, was er tut: ob das KI-Programm (Ollama) läuft, ob der Dienst
bereit ist, ob der Roboter im Netz ist, die letzten Fragen des Roboters mit
Bildern und Antwort, und das Log.

Die Anzeige ist eine Seite, die dieses Programm selbst ausliefert. Sie ist
**nur von diesem Rechner aus erreichbar** (Adresse 127.0.0.1); ins Netz
geht davon nichts. Die Bilder der letzten Frage liegen im Ordner des
Programms auf dem KI-Rechner und verlassen ihn nicht.

Start (in der ROS-Umgebung des KI-Rechners, gleiche ``ROS_DOMAIN_ID`` und
DDS-Einstellung wie für den Dienst):

    python3 lotse_fenster.py --modell qwen3.5:9b

Das Fenster zu schließen beendet den Dienst nicht; dafür gibt es auf der
Seite „Programm beenden“. Ein zweiter Start öffnet nur das Fenster wieder.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lotse.ki_rechner import STANDARD_URL, umgebung  # noqa: E402

# Die Seite ist nur von diesem Rechner aus erreichbar.
ADRESSE = '127.0.0.1'
VORGABE_PORT = 8765
VORGABE_ORDNER = Path.home() / '.local/share/amadeus/ki_erkundung/lotse'
SEITE = Path(__file__).resolve().with_name('lotse_fenster_seite.html')
DIENST = Path(__file__).resolve().with_name('lotse_dienst.py')
KOPFZEILE = 'X-Lotse-Fenster'          # nur die eigene Seite sendet sie mit


def _in_arbeitskopie(ordner: Path) -> bool:
    """Liegt der Ordner in einer Git-Arbeitskopie? Dort gehören keine Bilder hin."""
    ordner = ordner.resolve()
    return any((eltern / '.git').exists() for eltern in (ordner, *ordner.parents))


def gegenstellen(dds_uri: Optional[str]) -> List[str]:
    """Die festen Gegenstellen aus der DDS-Einstellung (für die Erreichbarkeit)."""
    if not dds_uri or not dds_uri.startswith('file://'):
        return []
    try:
        wurzel = ET.parse(dds_uri[len('file://'):]).getroot()
    except (OSError, ET.ParseError):
        return []
    adressen = []
    for element in wurzel.iter():
        if element.tag.split('}')[-1].lower() != 'peer':
            continue
        adresse = element.get('address') or element.get('Address') or ''
        adresse = adresse.split(':')[0].strip()
        if adresse and adresse not in adressen:
            adressen.append(adresse)
    return adressen


def eigene_adressen() -> List[str]:
    try:
        ausgabe = subprocess.run(['hostname', '-I'], capture_output=True, text=True,
                                 timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return ausgabe.split()


def erreichbar(adresse: str) -> bool:
    """Antwortet die Gegenstelle auf einen Ping (eine Sekunde Geduld)?"""
    try:
        return subprocess.run(['ping', '-c', '1', '-W', '1', adresse],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=4).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class Fenster:
    """Hält den Dienst am Laufen und sammelt, was die Seite zeigt."""

    def __init__(self, ordner, modell: str, url: str = STANDARD_URL,
                 dienst_befehl: Optional[List[str]] = None,
                 dds_uri: Optional[str] = None, pruefe_alle_s: float = 5.0):
        self.ordner = Path(ordner)
        self.modell, self.url = modell, url
        self.ordner.mkdir(parents=True, exist_ok=True)
        self.logdatei = self.ordner / 'lotse_dienst.log'
        self.befehl = dienst_befehl or [sys.executable, str(DIENST), '--modell', modell,
                                        '--url', url, '--zustand', str(self.ordner)]
        self._kind: Optional[subprocess.Popen] = None
        self._log = None
        self._sperre = threading.Lock()
        self._ollama = {'geprueft_unix': None, 'umgebung': None}
        self._netz = {'gegenstellen': 0, 'erreichbar': None, 'geprueft_unix': None}
        eigene = set(eigene_adressen())
        self._gegenstellen = [a for a in gegenstellen(
            dds_uri if dds_uri is not None else os.environ.get('CYCLONEDDS_URI'))
            if a not in eigene]
        self._ende = threading.Event()
        self._pruefe_alle_s = pruefe_alle_s
        self._faden = threading.Thread(target=self._pruefe_dauernd, daemon=True)
        self._faden.start()

    # ------------------------------------------------------------- Dienst

    def dienst_laeuft(self) -> bool:
        return self._kind is not None and self._kind.poll() is None

    def fremde_dienste(self) -> List[int]:
        """Lotsen-Dienste, die nicht von diesem Programm gestartet wurden."""
        eigener = self._kind.pid if self.dienst_laeuft() else None
        gefunden = []
        for eintrag in Path('/proc').iterdir():
            if not eintrag.name.isdigit():
                continue
            pid = int(eintrag.name)
            if pid in (os.getpid(), eigener):
                continue
            try:
                teile = (eintrag / 'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            if any(teil.endswith(b'lotse_dienst.py') for teil in teile):
                gefunden.append(pid)
        return sorted(gefunden)

    def starte_dienst(self) -> str:
        with self._sperre:
            if self.dienst_laeuft():
                return 'laeuft_schon'
            if self.fremde_dienste():
                return 'fremder_dienst'
            if self.logdatei.exists() and self.logdatei.stat().st_size > 5_000_000:
                os.replace(self.logdatei, self.logdatei.with_suffix('.log.1'))
            (self.ordner / 'zustand.json').unlink(missing_ok=True)
            self._log = open(self.logdatei, 'ab')
            self._log.write(f'\n--- Start {time.strftime("%d.%m.%Y %H:%M:%S")} ---\n'.encode())
            self._log.flush()
            umgebungsvariablen = dict(os.environ, PYTHONUNBUFFERED='1')
            self._kind = subprocess.Popen(self.befehl, stdout=self._log,
                                          stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                          env=umgebungsvariablen)
            return 'gestartet'

    def stoppe_dienst(self, geduld_s: float = 8.0) -> str:
        """Den eigenen Dienst beenden: ein SIGINT an genau diesen Prozess."""
        with self._sperre:
            kind = self._kind
            if kind is None or kind.poll() is not None:
                return 'lief_nicht'
            kind.send_signal(signal.SIGINT)
            try:
                kind.wait(timeout=geduld_s)
            except subprocess.TimeoutExpired:
                kind.terminate()
                try:
                    kind.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    kind.kill()
                    kind.wait(timeout=3.0)
            if self._log is not None:
                self._log.write(f'--- Ende {time.strftime("%d.%m.%Y %H:%M:%S")} ---\n'.encode())
                self._log.close()
                self._log = None
            return 'beendet'

    def stoppe_fremden(self, pid: int) -> str:
        """Einen ohne dieses Programm gestarteten Lotsen-Dienst beenden (ein SIGINT)."""
        if pid not in self.fremde_dienste():
            return 'unbekannt'
        try:
            os.kill(pid, signal.SIGINT)
        except OSError as fehler:
            return f'fehler: {fehler}'
        return 'beendet'

    def schliesse(self) -> None:
        self._ende.set()
        self.stoppe_dienst()

    # ------------------------------------------------------------ Prüfungen

    def _pruefe_dauernd(self) -> None:
        while not self._ende.is_set():
            bekannt = umgebung(self.modell, self.url, zeitgrenze_s=2.0)
            self._ollama = {'geprueft_unix': round(time.time(), 1), 'umgebung': bekannt}
            if self._gegenstellen:
                anzahl = sum(1 for adresse in self._gegenstellen if erreichbar(adresse))
                self._netz = {'gegenstellen': len(self._gegenstellen), 'erreichbar': anzahl,
                              'geprueft_unix': round(time.time(), 1)}
            self._ende.wait(self._pruefe_alle_s)

    def _log_ende(self, zeilen: int = 200) -> List[str]:
        try:
            with open(self.logdatei, 'rb') as datei:
                datei.seek(0, os.SEEK_END)
                datei.seek(max(0, datei.tell() - 60_000))
                text = datei.read().decode('utf-8', errors='replace')
        except OSError:
            return []
        return text.splitlines()[-zeilen:]

    def zustand(self) -> dict:
        """Alles, was die Seite anzeigt."""
        jetzt = time.time()
        gemeldet = None
        try:
            gemeldet = json.loads((self.ordner / 'zustand.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        if not isinstance(gemeldet, dict):
            gemeldet = None
        frisch = bool(gemeldet and jetzt - float(gemeldet.get('zeit_unix') or 0.0) < 5.0)
        laeuft = self.dienst_laeuft()
        ende_code = None if self._kind is None or laeuft else self._kind.returncode
        bekannt = self._ollama['umgebung'] or {}
        return {
            'zeit_unix': round(jetzt, 1), 'modell': self.modell,
            'logdatei': str(self.logdatei),
            'ollama': {
                'geprueft': self._ollama['geprueft_unix'] is not None,
                'erreichbar': bekannt.get('dienst_fassung') is not None,
                'fassung': bekannt.get('dienst_fassung'),
                'modell_vorhanden': bekannt.get('modell_kennung') is not None,
                'groesse_gb': bekannt.get('groesse_gb'),
                'parameter': bekannt.get('parameter'),
            },
            'dienst': {
                'laeuft': laeuft, 'pid': self._kind.pid if laeuft else None,
                'ende_code': ende_code,
                # läuft, meldet sich aber nicht: hängt oder startet noch
                'meldet_sich': bool(laeuft and frisch),
                'gestartet_unix': gemeldet.get('gestartet_unix') if frisch else None,
                'bereit': bool(frisch and gemeldet.get('bereit')),
                'beschaeftigt': bool(frisch and gemeldet.get('beschaeftigt')),
                'beantwortet': gemeldet.get('fragen_beantwortet', 0) if gemeldet else 0,
                'abgelehnt': gemeldet.get('fragen_abgelehnt', 0) if gemeldet else 0,
            },
            'fremde_dienste': self.fremde_dienste(),
            'roboter': {
                'gegenstellen': self._netz['gegenstellen'],
                'im_netz': (None if self._netz['erreichbar'] is None
                            else self._netz['erreichbar'] > 0),
                'ros_andere_knoten': gemeldet.get('ros_andere_knoten') if frisch else None,
                'ros_fragende': gemeldet.get('ros_fragende') if frisch else None,
            },
            'verlauf': (gemeldet.get('verlauf') or [])[::-1] if gemeldet else [],
            'letzte_frage': gemeldet.get('letzte_frage') if gemeldet else None,
            'log': self._log_ende(),
        }

    def bild(self, nummer: int) -> Optional[bytes]:
        datei = self.ordner / 'letzte_frage' / f'bild_{int(nummer)}.jpg'
        try:
            return datei.read_bytes()
        except OSError:
            return None


def baue_bearbeiter(fenster: Fenster, beenden):
    """Die Seite und ihre wenigen Anfragen; nur für Aufrufe von diesem Rechner."""

    class Bearbeiter(BaseHTTPRequestHandler):
        server_version = 'LotsenFenster'

        def log_message(self, *args):          # kein Protokoll je Seitenabruf
            pass

        def _von_hier(self) -> bool:
            # Der Name der Gegenseite muss dieser Rechner sein: Eine fremde
            # Webseite kann die Anzeige so nicht unter anderem Namen ansprechen.
            host = (self.headers.get('Host') or '').split(':')[0]
            return host in (ADRESSE, 'localhost')

        def _sende(self, status: int, inhalt: bytes, art: str = 'application/json') -> None:
            self.send_response(status)
            self.send_header('Content-Type', art)
            self.send_header('Content-Length', str(len(inhalt)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            try:
                self.wfile.write(inhalt)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _json(self, status: int, wert) -> None:
            self._sende(status, json.dumps(wert, ensure_ascii=False).encode('utf-8'))

        def do_GET(self):
            if not self._von_hier():
                return self._json(403, {'fehler': 'nur von diesem Rechner'})
            pfad = self.path.split('?')[0]
            if pfad in ('/', '/index.html'):
                return self._sende(200, SEITE.read_bytes(), 'text/html; charset=utf-8')
            if pfad == '/api/zustand':
                return self._json(200, fenster.zustand())
            if pfad.startswith('/bild/') and pfad[6:].isdigit():
                bild = fenster.bild(int(pfad[6:]))
                if bild is not None:
                    return self._sende(200, bild, 'image/jpeg')
            return self._json(404, {'fehler': 'unbekannt'})

        def do_POST(self):
            # Nur die eigene Seite schickt diese Kopfzeile mit.
            if not self._von_hier() or self.headers.get(KOPFZEILE) != '1':
                return self._json(403, {'fehler': 'nur von der eigenen Seite'})
            pfad = self.path.split('?')[0]
            if pfad == '/api/dienst/start':
                return self._json(200, {'ergebnis': fenster.starte_dienst()})
            if pfad == '/api/dienst/stopp':
                return self._json(200, {'ergebnis': fenster.stoppe_dienst()})
            if pfad.startswith('/api/fremd/stopp/') and pfad[17:].isdigit():
                return self._json(200, {'ergebnis': fenster.stoppe_fremden(int(pfad[17:]))})
            if pfad == '/api/beenden':
                self._json(200, {'ergebnis': 'wird beendet'})
                threading.Thread(target=beenden, daemon=True).start()
                return None
            return self._json(404, {'fehler': 'unbekannt'})

    return Bearbeiter


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Lotsen-Fenster: Lotsen-Dienst starten und am Bildschirm zeigen.')
    eingabe.add_argument('--modell', default='qwen3.5:9b',
                         help='Name des Bild-Sprach-Modells in Ollama')
    eingabe.add_argument('--url', default=STANDARD_URL,
                         help='Adresse von Ollama auf diesem Rechner')
    eingabe.add_argument('--ordner', default=str(VORGABE_ORDNER),
                         help='Ordner für Zustand, Log und die Bilder der letzten Frage '
                              '(auf diesem Rechner, außerhalb des Repositorys)')
    eingabe.add_argument('--port', type=int, default=VORGABE_PORT)
    eingabe.add_argument('--kein-browser', action='store_true',
                         help='das Fenster nicht selbst öffnen')
    eingabe.add_argument('--nicht-starten', action='store_true',
                         help='den Lotsen-Dienst nicht gleich starten')
    wahl = eingabe.parse_args(argv)

    ordner = Path(wahl.ordner).expanduser()
    if _in_arbeitskopie(ordner):
        print(f'{ordner} liegt in einer Git-Arbeitskopie. Bilder der Wohnung gehören '
              'nicht dorthin; bitte einen Ordner außerhalb wählen.', file=sys.stderr)
        return 2
    adresse = f'http://{ADRESSE}:{wahl.port}/'
    halter = {}

    def beenden():
        if 'server' in halter:
            halter['server'].shutdown()

    class Spaeter:
        """Reicht Aufrufe an das Fenster weiter, das erst nach dem Server entsteht."""

        def __getattr__(self, name):
            return getattr(halter['fenster'], name)

    try:
        server = ThreadingHTTPServer((ADRESSE, wahl.port), baue_bearbeiter(Spaeter(), beenden))
    except OSError:
        # Das Programm läuft schon: nur das Fenster wieder öffnen.
        print(f'Das Lotsen-Fenster läuft bereits: {adresse}')
        if not wahl.kein_browser:
            webbrowser.open(adresse)
        return 0
    halter['server'] = server
    fenster = halter['fenster'] = Fenster(ordner, wahl.modell, wahl.url)
    for zeichen in (signal.SIGINT, signal.SIGTERM):
        signal.signal(zeichen, lambda *_: threading.Thread(target=beenden, daemon=True).start())
    if not wahl.nicht_starten:
        ergebnis = fenster.starte_dienst()
        print(f'Lotsen-Dienst: {ergebnis}')
    print(f'Lotsen-Fenster: {adresse} (nur von diesem Rechner aus erreichbar)')
    if not wahl.kein_browser:
        webbrowser.open(adresse)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        fenster.schliesse()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
