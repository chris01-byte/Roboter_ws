#!/usr/bin/env python3
"""Sucher: das Kamerabild live ansehen, um Amadeus für eine Ansicht hinzustellen.

Zeigt das laufende Bild der Kamera in einem gewöhnlichen Fenster des
Browsers auf dem Bildschirm des Jetson. Das Fenster lässt sich schließen wie
jedes andere; ein Vollbild gibt es nicht. (Am 21.11.2026 ließ sich ein
behelfsmäßiges Vollbild nicht schließen, und der Jetson musste
heruntergefahren werden.)

Der Sucher liest nur mit: keine Fahrbefehle, keine Dienstaufrufe. Er
speichert kein Bild; das jeweils letzte liegt nur im Arbeitsspeicher. Die
Anzeige ist nur von diesem Rechner aus erreichbar (127.0.0.1). Nach
``--dauer`` Sekunden endet er von selbst.

Aufruf (Kamera läuft, ROS-Umgebung gesetzt):
    python3 sucher.py            # öffnet das Fenster; Ende mit Strg+C oder „Beenden“
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ros_ende import Ende, ros_beenden, ros_starten  # noqa: E402

# Die Seite ist nur von diesem Rechner aus erreichbar.
ADRESSE = '127.0.0.1'
VORGABE_PORT = 8766
KOPFZEILE = 'X-Sucher'

SEITE = '''<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Amadeus · Sucher</title>
<style>
  body { margin: 0; background: #14181d; color: #e8ecf1;
         font: 15px/1.45 system-ui, "Segoe UI", Roboto, "Noto Sans", sans-serif; }
  main { max-width: 1000px; margin: 0 auto; padding: 16px; }
  header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
  h1 { font-size: 20px; margin: 0; }
  #lage { padding: 5px 13px; border-radius: 999px; background: #262d35; color: #9aa5b1; }
  #lage.gut { background: #173524; color: #4cc47f; }
  #lage.schlecht { background: #3d1c1a; color: #f0776f; }
  button { margin-left: auto; font: inherit; padding: 6px 13px; border-radius: 8px;
           border: 1px solid #2f3741; background: #1d232a; color: #e8ecf1; cursor: pointer; }
  .rahmen { position: relative; background: #000; border-radius: 10px; overflow: hidden;
            border: 1px solid #2f3741; }
  img { width: 100%; display: block; image-rendering: auto; min-height: 120px; }
  .mitte { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px;
           background: rgba(255, 255, 255, .45); }
  p { color: #9aa5b1; font-size: 13.5px; }
</style></head>
<body><main>
  <header><h1>Amadeus · Sucher</h1><span id="lage">warte auf das erste Bild …</span>
    <button id="ende">Beenden</button></header>
  <div class="rahmen"><img id="bild" alt="Kamerabild"><div class="mitte"></div></div>
  <p>Der Strich zeigt geradeaus. Das Bild wird nicht gespeichert und verlässt diesen
     Rechner nicht. Dieses Fenster kann einfach geschlossen werden.</p>
</main>
<script>
'use strict';
let fertig = false;
async function hole() {
  if (fertig) return;
  const lage = document.getElementById('lage');
  try {
    const z = await (await fetch('/api/zustand', {cache: 'no-store'})).json();
    if (z.bilder > 0) document.getElementById('bild').src = '/bild?n=' + z.bilder;
    if (z.bilder === 0) { lage.className = ''; lage.textContent = 'warte auf das erste Bild …'; }
    else if (z.alter_s > 3) { lage.className = 'schlecht';
      lage.textContent = 'kein neues Bild seit ' + Math.round(z.alter_s) + ' s'; }
    else { lage.className = 'gut';
      lage.textContent = 'live, ' + z.breite + ' × ' + z.hoehe + ', '
        + String(z.rate_hz).replace('.', ',') + ' Bilder je Sekunde'; }
  } catch (fehler) { lage.className = 'schlecht'; lage.textContent = 'Sucher beendet'; }
}
document.getElementById('ende').onclick = async () => {
  fertig = true;
  try {
    await fetch('/api/beenden', {method: 'POST', headers: {'X-Sucher': '1'}});
  } catch (fehler) { /* schon weg */ }
  const lage = document.getElementById('lage');
  lage.className = ''; lage.textContent = 'beendet – dieses Fenster kann geschlossen werden';
};
hole(); setInterval(hole, 400);
</script></body></html>
'''


def bildgroesse(jpeg: bytes):
    """Breite und Höhe aus den Kopfdaten eines JPEG (ohne es zu entpacken)."""
    i = 2
    while i + 9 < len(jpeg):
        if jpeg[i] != 0xFF:
            i += 1
            continue
        kennung = jpeg[i + 1]
        if kennung in (0xC0, 0xC1, 0xC2):
            return (int.from_bytes(jpeg[i + 7:i + 9], 'big'),
                    int.from_bytes(jpeg[i + 5:i + 7], 'big'))
        if kennung in (0xD8, 0x01) or 0xD0 <= kennung <= 0xD7:
            i += 2
            continue
        i += 2 + int.from_bytes(jpeg[i + 2:i + 4], 'big')
    return None, None


class Sucher:
    """Hält das letzte Kamerabild im Arbeitsspeicher."""

    def __init__(self):
        self._sperre = threading.Lock()
        self._bild: Optional[bytes] = None
        self._zeiten = []
        self.bilder = 0

    def nimm(self, jpeg: bytes) -> None:
        jetzt = time.monotonic()
        with self._sperre:
            self._bild = bytes(jpeg)
            self.bilder += 1
            self._zeiten = [t for t in self._zeiten if jetzt - t < 5.0] + [jetzt]

    def bild(self) -> Optional[bytes]:
        with self._sperre:
            return self._bild

    def zustand(self) -> dict:
        jetzt = time.monotonic()
        with self._sperre:
            zeiten = list(self._zeiten)
            bild = self._bild
        breite, hoehe = bildgroesse(bild) if bild else (None, None)
        rate = (len(zeiten) - 1) / (zeiten[-1] - zeiten[0]) if len(zeiten) >= 2 else 0.0
        return {'bilder': self.bilder, 'breite': breite, 'hoehe': hoehe,
                'alter_s': round(jetzt - zeiten[-1], 1) if zeiten else None,
                'rate_hz': round(rate, 1)}


def baue_bearbeiter(sucher: Sucher, beenden):
    class Bearbeiter(BaseHTTPRequestHandler):
        server_version = 'Sucher'

        def log_message(self, *args):
            pass

        def _von_hier(self) -> bool:
            return (self.headers.get('Host') or '').split(':')[0] in (ADRESSE, 'localhost')

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

        def do_GET(self):
            if not self._von_hier():
                return self._sende(403, b'{}')
            pfad = self.path.split('?')[0]
            if pfad == '/':
                return self._sende(200, SEITE.encode('utf-8'), 'text/html; charset=utf-8')
            if pfad == '/api/zustand':
                return self._sende(200, json.dumps(sucher.zustand()).encode('utf-8'))
            if pfad == '/bild' and sucher.bild() is not None:
                return self._sende(200, sucher.bild(), 'image/jpeg')
            return self._sende(404, b'{}')

        def do_POST(self):
            if not self._von_hier() or self.headers.get(KOPFZEILE) != '1':
                return self._sende(403, b'{}')
            if self.path.split('?')[0] == '/api/beenden':
                self._sende(200, b'{"ergebnis": "wird beendet"}')
                threading.Thread(target=beenden, daemon=True).start()
                return None
            return self._sende(404, b'{}')

    return Bearbeiter


def main(argv=None) -> int:
    eingabe = argparse.ArgumentParser(
        description='Sucher: das Kamerabild live in einem gewöhnlichen Fenster zeigen.')
    eingabe.add_argument('--bild-topic', default='/oak/semantic/rgb/compressed')
    eingabe.add_argument('--port', type=int, default=VORGABE_PORT)
    eingabe.add_argument('--dauer', type=float, default=1800.0,
                         help='nach so vielen Sekunden endet der Sucher von selbst')
    eingabe.add_argument('--kein-browser', action='store_true')
    wahl = eingabe.parse_args(argv)

    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CompressedImage

    sucher = Sucher()
    adresse = f'http://{ADRESSE}:{wahl.port}/'
    ende = threading.Event()
    try:
        server = ThreadingHTTPServer((ADRESSE, wahl.port), baue_bearbeiter(sucher, ende.set))
    except OSError:
        print(f'Der Sucher läuft bereits: {adresse}')
        if not wahl.kein_browser:
            webbrowser.open(adresse)
        return 0
    # Zuerst die Marke, dann rclpy ohne eigene Handler (ros_ende).
    marke = Ende().anmelden()
    eigener_kontext = ros_starten()
    knoten = rclpy.create_node('ki_sucher')
    knoten.create_subscription(CompressedImage, wahl.bild_topic,
                               lambda nachricht: sucher.nimm(bytes(nachricht.data)),
                               qos_profile_sensor_data)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f'Sucher: {adresse} (nur von diesem Rechner aus erreichbar; Ende mit Strg+C)')
    if not wahl.kein_browser:
        webbrowser.open(adresse)
    beginn = time.monotonic()
    try:
        while (rclpy.ok() and not ende.is_set() and not marke.gesetzt()
               and time.monotonic() - beginn < wahl.dauer):
            rclpy.spin_once(knoten, timeout_sec=0.1)
    finally:
        server.shutdown()
        server.server_close()
        ros_beenden([knoten], eigener_kontext=eigener_kontext)
        marke.abmelden()
    print(f'Sucher beendet ({sucher.bilder} Bilder gezeigt, keines gespeichert).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
