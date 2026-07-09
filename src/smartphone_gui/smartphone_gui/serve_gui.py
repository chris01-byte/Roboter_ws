#!/usr/bin/env python3
# ============================================================================
#  serve_gui.py - Kleiner HTTP-Server fuer die Smartphone-PWA
#  ---------------------------------------------------------------------------
#  Dient nur statische Dateien aus dem installierten Paket aus.
#  Keine Robotik-Logik, keine Hardware-Befehle.
# ============================================================================

import argparse
import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from ament_index_python.packages import get_package_share_directory


def main():
    parser = argparse.ArgumentParser(description='Serve smartphone GUI web app')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    # parse_known_args: als ROS-Node gestartet haengt launch '--ros-args ...' an;
    # diese ignorieren, statt mit argparse-Fehler abzustuerzen.
    args, _ = parser.parse_known_args()

    web_dir = get_package_share_directory('smartphone_gui') + '/web'
    handler = functools.partial(SimpleHTTPRequestHandler, directory=web_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f'smartphone_gui online: http://{args.host}:{args.port}')
    print(f'web_dir: {web_dir}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
