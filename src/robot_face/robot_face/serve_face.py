#!/usr/bin/env python3
# ============================================================================
#  serve_face.py - Kleiner HTTP-Server fuer die Gesichts-Anzeige
#  ---------------------------------------------------------------------------
#  Dient nur die statischen Dateien aus web/ aus (gleiches Muster wie
#  smartphone_gui/serve_gui.py). Standard-Port 8081, damit die Smartphone-GUI
#  (8080) parallel laufen kann. Anzeige am Roboter-Display:
#      http://localhost:8081   (Chromium im Kiosk-Modus, siehe README)
# ============================================================================

import argparse
import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from ament_index_python.packages import get_package_share_directory


def main():
    parser = argparse.ArgumentParser(description='Serve robot face web app')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8081)
    # parse_known_args: als ROS-Node gestartet haengt launch '--ros-args ...' an;
    # diese ignorieren, statt mit argparse-Fehler abzustuerzen.
    args, _ = parser.parse_known_args()

    web_dir = get_package_share_directory('robot_face') + '/web'
    handler = functools.partial(SimpleHTTPRequestHandler, directory=web_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f'robot_face online: http://{args.host}:{args.port}')
    print(f'web_dir: {web_dir}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
