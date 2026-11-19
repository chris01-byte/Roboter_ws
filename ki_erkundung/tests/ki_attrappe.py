"""Attrappe des KI-Rechners für Tests: ein kleiner Ollama-ähnlicher Dienst.

Läuft nur auf 127.0.0.1 und nur während eines Tests. Die Antworten werden
vom Test vorgegeben; so lässt sich prüfen, was bei richtiger, falscher,
langsamer und fehlender Antwort geschieht.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Attrappe:
    def __init__(self, modelle=('pruefmodell',)):
        self.modelle = list(modelle)
        self.antworten = []          # je Anfrage: Text, dict mit Sonderfall, oder Funktion
        self.anfragen = []
        self.schema_ablehnen = False
        attrappe = self

        class Bearbeiter(BaseHTTPRequestHandler):
            def log_message(self, *args):          # keine Ausgabe im Testlauf
                pass

            def _sende(self, status, inhalt: bytes):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(inhalt)))
                self.end_headers()
                try:
                    self.wfile.write(inhalt)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                if self.path == '/api/tags':
                    self._sende(200, json.dumps(
                        {'models': [{'name': m} for m in attrappe.modelle]}).encode())
                else:
                    self._sende(404, b'{}')

            def do_POST(self):
                laenge = int(self.headers.get('Content-Length', 0))
                anfrage = json.loads(self.rfile.read(laenge).decode('utf-8'))
                attrappe.anfragen.append(anfrage)
                if attrappe.schema_ablehnen and isinstance(anfrage.get('format'), dict):
                    self._sende(400, b'{"error": "format wird nicht unterstuetzt"}')
                    return
                antwort = attrappe.antworten.pop(0) if attrappe.antworten else '{}'
                if callable(antwort):
                    antwort = antwort(anfrage)
                if isinstance(antwort, dict):
                    if 'warten_s' in antwort:
                        time.sleep(antwort['warten_s'])
                    if 'status' in antwort:
                        self._sende(antwort['status'], b'{"error": "x"}')
                        return
                    if 'roh' in antwort:
                        self._sende(200, antwort['roh'])
                        return
                    antwort = antwort.get('text', '{}')
                self._sende(200, json.dumps({
                    'model': anfrage.get('model'),
                    'message': {'role': 'assistant', 'content': antwort},
                    'total_duration': 2_500_000_000, 'load_duration': 100_000_000,
                    'prompt_eval_count': 2100, 'eval_count': 90,
                    'eval_duration': 1_200_000_000}).encode())

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Bearbeiter)
        self.server.daemon_threads = True
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self._faden = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._faden.start()

    def schliessen(self):
        self.server.shutdown()
        self.server.server_close()
