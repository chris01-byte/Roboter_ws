#!/usr/bin/env python3
"""Small dependency-free rosbridge mock for iOS simulator UI tests."""

import argparse
import base64
import hashlib
import json
import socket
import socketserver
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


ROSBRIDGE_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
MAP_TOPIC = '/map'
MAP_WIDTH = 48
MAP_HEIGHT = 36
MAP_RESOLUTION = 0.10
MAP_ORIGIN = (-2.4, -1.8, 0.0)


def _fill_rectangle(cells, x_min, y_min, x_max, y_max, value):
    """Fill an inclusive rectangle in the row-major OccupancyGrid."""
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                cells[y * MAP_WIDTH + x] = value


def _build_test_apartment(revision):
    """Return a deterministic, visibly room-shaped OccupancyGrid payload."""
    cells = [-1] * (MAP_WIDTH * MAP_HEIGHT)

    # Known floor area and exterior walls.
    _fill_rectangle(cells, 3, 3, 44, 32, 0)
    _fill_rectangle(cells, 3, 3, 44, 3, 100)
    _fill_rectangle(cells, 3, 32, 44, 32, 100)
    _fill_rectangle(cells, 3, 3, 3, 32, 100)
    _fill_rectangle(cells, 44, 3, 44, 32, 100)

    # Interior walls with deliberate door openings.
    _fill_rectangle(cells, 25, 4, 25, 31, 100)
    _fill_rectangle(cells, 25, 11, 25, 14, 0)
    _fill_rectangle(cells, 25, 25, 25, 27, 0)
    _fill_rectangle(cells, 4, 21, 24, 21, 100)
    _fill_rectangle(cells, 12, 21, 15, 21, 0)
    _fill_rectangle(cells, 26, 17, 43, 17, 100)
    _fill_rectangle(cells, 34, 17, 37, 17, 0)

    # Furniture makes the mock map easy to recognise in visual UI tests.
    _fill_rectangle(cells, 6, 26, 17, 28, 100)   # Sofa
    _fill_rectangle(cells, 8, 8, 14, 10, 100)    # Dining table
    _fill_rectangle(cells, 29, 27, 41, 29, 100)  # Bed
    _fill_rectangle(cells, 39, 5, 42, 14, 100)   # Kitchen counter
    _fill_rectangle(cells, 29, 6, 31, 11, 100)   # Kitchen island

    # A small obstacle moves only when /map-update is requested. This gives
    # refresh tests a deterministic pixel-level change without a noisy stream.
    obstacle_x = (18, 20, 22, 20)[revision % 4]
    obstacle_y = (7, 8, 7, 6)[revision % 4]
    _fill_rectangle(
        cells,
        obstacle_x,
        obstacle_y,
        obstacle_x + 1,
        obstacle_y + 1,
        100,
    )
    return cells


def _ros_time(timestamp):
    seconds = int(timestamp)
    return {
        'sec': seconds,
        'nanosec': int((timestamp - seconds) * 1_000_000_000),
    }


class RobotState:
    def __init__(self):
        self.lock = threading.RLock()
        self.clients = set()
        self.events = []
        self.generation = 0
        self.pause_status_until = 0.0
        self.pause_estop_until = 0.0
        self.estop = False
        self.reset()

    def reset(self):
        with self.lock:
            self.generation += 1
            self.map_revision = 0
            self.map_load_time = time.time()
            self.map_available = True
            self.status = {
                'state': 'idle',
                'phase': 'bereit',
                'message': 'Bereit (Simulator-Mock)',
                'progress': 0.0,
                'active_command': {},
                'rooms': ['Wohnzimmer', 'Kueche', 'Werkstatt'],
                'targets': ['Tisch', 'Regal', 'Arbeitsplatte'],
                'objects': ['Tasse', 'Flasche', 'Fernbedienung'],
                'offboard_available': True,
                'cancel_pending': False,
                'last_rejection': '',
            }
            self.estop = False

    def advance_map(self):
        with self.lock:
            self.map_revision += 1
            return self.map_revision

    def reset_map(self):
        with self.lock:
            self.map_revision = 0
            self.map_load_time = time.time()
            return self.map_revision

    def set_map_available(self, available):
        with self.lock:
            self.map_available = available
            return self.map_available

    def is_map_available(self):
        with self.lock:
            return self.map_available

    def map_snapshot(self):
        now = time.time()
        with self.lock:
            revision = self.map_revision
            load_time = self.map_load_time
        return {
            'header': {
                'stamp': _ros_time(now),
                'frame_id': 'map',
            },
            'info': {
                'map_load_time': _ros_time(load_time),
                'resolution': MAP_RESOLUTION,
                'width': MAP_WIDTH,
                'height': MAP_HEIGHT,
                'origin': {
                    'position': {
                        'x': MAP_ORIGIN[0],
                        'y': MAP_ORIGIN[1],
                        'z': MAP_ORIGIN[2],
                    },
                    'orientation': {
                        'x': 0.0,
                        'y': 0.0,
                        'z': 0.0,
                        'w': 1.0,
                    },
                },
            },
            'data': _build_test_apartment(revision),
        }

    def snapshot(self):
        with self.lock:
            payload = dict(self.status)
            payload['time'] = time.time()
            return payload

    def record(self, kind, payload):
        entry = {'kind': kind, 'payload': payload, 'time': time.time()}
        with self.lock:
            self.events.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)

    def start_mission(self, command):
        with self.lock:
            if self.status['state'] == 'running':
                self.status['last_rejection'] = 'Es laeuft bereits eine Mission'
                self.record('rejected', command)
                return
            self.generation += 1
            generation = self.generation
            self.status.update({
                'state': 'running',
                'phase': 'gestartet',
                'message': f"Mission gestartet: {command.get('type', '?')}",
                'progress': 0.05,
                'active_command': dict(command),
                'cancel_pending': False,
                'last_rejection': '',
            })
        self.record('command', command)

        # Exploration deliberately stays active long enough for interactive
        # Simulator tests of cancel and emergency-stop controls.
        duration = 20.0 if command.get('type') == 'explore' else 2.0
        threading.Thread(
            target=self._complete_mission,
            args=(generation, duration),
            daemon=True,
        ).start()

    def _complete_mission(self, generation, duration):
        steps = (
            (0.25, 'Planung'),
            (0.55, 'Navigation'),
            (0.82, 'Ausfuehrung'),
        )
        interval = duration / (len(steps) + 1)
        for progress, phase in steps:
            time.sleep(interval)
            with self.lock:
                if generation != self.generation or self.status['state'] != 'running':
                    return
                self.status['phase'] = phase
                self.status['message'] = f'Phase: {phase}'
                self.status['progress'] = progress
        time.sleep(interval)
        with self.lock:
            if generation != self.generation or self.status['state'] != 'running':
                return
            self.status.update({
                'state': 'success',
                'phase': 'fertig',
                'message': 'Mission erfolgreich abgeschlossen',
                'progress': 1.0,
                'cancel_pending': False,
            })

    def cancel_mission(self):
        with self.lock:
            self.record('cancel', {'type': 'cancel'})
            if self.status['state'] != 'running':
                self.status['last_rejection'] = 'Keine laufende Mission'
                return
            self.generation += 1
            generation = self.generation
            self.status.update({
                'phase': 'abbruch_angefordert',
                'message': 'Abbruch angenommen; warte auf Action-Ergebnis ...',
                'cancel_pending': True,
            })
        threading.Thread(
            target=self._complete_cancel,
            args=(generation,),
            daemon=True,
        ).start()

    def _complete_cancel(self, generation):
        time.sleep(0.8)
        with self.lock:
            if generation != self.generation:
                return
            self.status.update({
                'state': 'canceled',
                'phase': 'abgebrochen',
                'message': 'Mission vom Simulator-Mock abgebrochen',
                'cancel_pending': False,
            })

    def request_estop(self, active):
        self.record('estop', active)

        def acknowledge():
            time.sleep(0.25)
            with self.lock:
                self.estop = active

        threading.Thread(target=acknowledge, daemon=True).start()

    def close_clients(self):
        with self.lock:
            clients = list(self.clients)
        for client in clients:
            client.close()


STATE = RobotState()


def ros_publish(topic, value):
    return json.dumps({
        'op': 'publish',
        'topic': topic,
        'msg': {'data': value},
    }, ensure_ascii=False, separators=(',', ':'))


def ros_map_publish(message):
    return json.dumps({
        'op': 'publish',
        'topic': MAP_TOPIC,
        'msg': message,
    }, ensure_ascii=False, separators=(',', ':'))


class WebSocketHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.send_lock = threading.Lock()
        self.closed = False
        self.status_subscribed = False
        self.estop_subscribed = False
        self.map_subscription_ids = set()

    @property
    def map_subscribed(self):
        return bool(self.map_subscription_ids)

    def handle(self):
        if not self._handshake():
            return
        with STATE.lock:
            STATE.clients.add(self)
        STATE.record('connection', self.client_address[0])
        try:
            while not self.closed:
                opcode, payload = self._read_frame()
                if opcode is None or opcode == 0x8:
                    return
                if opcode == 0x9:
                    self._send_frame(0xA, payload)
                elif opcode == 0x1:
                    self._handle_text(payload.decode('utf-8'))
        except (ConnectionError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        finally:
            with STATE.lock:
                STATE.clients.discard(self)
            self.close()

    def _handshake(self):
        request = b''
        while b'\r\n\r\n' not in request and len(request) < 65536:
            chunk = self.request.recv(4096)
            if not chunk:
                return False
            request += chunk
        headers = {}
        for line in request.decode('latin1').split('\r\n')[1:]:
            if ':' in line:
                name, value = line.split(':', 1)
                headers[name.strip().lower()] = value.strip()
        key = headers.get('sec-websocket-key')
        if not key:
            return False
        accept = base64.b64encode(
            hashlib.sha1((key + ROSBRIDGE_GUID).encode('ascii')).digest()
        ).decode('ascii')
        response = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n\r\n'
        )
        self.request.sendall(response.encode('ascii'))
        return True

    def _read_exact(self, size):
        result = b''
        while len(result) < size:
            chunk = self.request.recv(size - len(result))
            if not chunk:
                raise ConnectionError('socket closed')
            result += chunk
        return result

    def _read_frame(self):
        first = self.request.recv(2)
        if not first:
            return None, b''
        if len(first) < 2:
            first += self._read_exact(2 - len(first))
        opcode = first[0] & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = struct.unpack('!H', self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack('!Q', self._read_exact(8))[0]
        mask = self._read_exact(4) if masked else None
        payload = self._read_exact(length)
        if mask:
            payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        return opcode, payload

    def _send_frame(self, opcode, payload):
        if self.closed:
            return
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        length = len(payload)
        header = bytes([0x80 | opcode])
        if length < 126:
            header += bytes([length])
        elif length <= 0xFFFF:
            header += bytes([126]) + struct.pack('!H', length)
        else:
            header += bytes([127]) + struct.pack('!Q', length)
        with self.send_lock:
            self.request.sendall(header + payload)

    def send_text(self, text):
        try:
            self._send_frame(0x1, text)
        except OSError:
            self.close()

    def _handle_text(self, text):
        frame = json.loads(text)
        STATE.record('frame', frame)
        if frame.get('op') == 'subscribe':
            topic = frame.get('topic')
            self.status_subscribed |= topic == '/mission_manager/status_json'
            self.estop_subscribed |= topic == '/safety/estop'
            if topic == MAP_TOPIC:
                subscription_id = frame.get('id') or MAP_TOPIC
                if STATE.is_map_available():
                    self.map_subscription_ids.add(subscription_id)
                    self.send_text(ros_map_publish(STATE.map_snapshot()))
                else:
                    STATE.record(
                        'map_waiting_for_publisher',
                        {'subscription_id': subscription_id},
                    )
            return
        if frame.get('op') == 'unsubscribe':
            topic = frame.get('topic')
            subscription_id = frame.get('id')
            if topic == '/mission_manager/status_json':
                self.status_subscribed = False
            if topic == '/safety/estop':
                self.estop_subscribed = False
            if topic == MAP_TOPIC and subscription_id is None:
                self.map_subscription_ids.clear()
            elif subscription_id in self.map_subscription_ids:
                self.map_subscription_ids.discard(subscription_id)
            return
        if frame.get('op') != 'publish':
            return
        topic = frame.get('topic')
        data = (frame.get('msg') or {}).get('data')
        if topic == '/mission_manager/command_json' and isinstance(data, str):
            command = json.loads(data)
            if command.get('type') == 'cancel':
                STATE.cancel_mission()
            else:
                STATE.start_mission(command)
        elif topic == '/safety/estop_request' and isinstance(data, bool):
            STATE.request_estop(data)

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.request.close()


class WebSocketServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ControlHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == '/events':
            with STATE.lock:
                self._json(STATE.events)
            return
        if parsed.path == '/clear-events':
            with STATE.lock:
                STATE.events.clear()
            self._json({'ok': True})
            return
        if parsed.path == '/reset':
            STATE.reset()
            broadcast_map()
            self._json({'ok': True})
            return
        if parsed.path == '/map-update':
            revision = STATE.advance_map()
            broadcast_map()
            self._json({'ok': True, 'map_revision': revision})
            return
        if parsed.path == '/map-reset':
            revision = STATE.reset_map()
            broadcast_map()
            self._json({'ok': True, 'map_revision': revision})
            return
        if parsed.path == '/map-disable':
            available = STATE.set_map_available(False)
            self._json({'ok': True, 'map_available': available})
            return
        if parsed.path == '/map-enable':
            available = STATE.set_map_available(True)
            self._json({'ok': True, 'map_available': available})
            return
        if parsed.path == '/pause':
            seconds = float(query.get('seconds', ['4'])[0])
            stream = query.get('stream', ['all'])[0]
            with STATE.lock:
                if stream in ('status', 'all'):
                    STATE.pause_status_until = time.monotonic() + seconds
                if stream in ('estop', 'all'):
                    STATE.pause_estop_until = time.monotonic() + seconds
            self._json({'ok': True, 'stream': stream, 'seconds': seconds})
            return
        if parsed.path in ('/malformed', '/partial', '/unknown'):
            with STATE.lock:
                STATE.pause_status_until = time.monotonic() + 3.5
            if parsed.path == '/malformed':
                data = '{kaputt'
            elif parsed.path == '/partial':
                data = '{}'
            else:
                invalid = STATE.snapshot()
                invalid['state'] = 'mystery'
                data = json.dumps(invalid, ensure_ascii=False)
            broadcast_raw_status(data)
            self._json({'ok': True})
            return
        if parsed.path == '/close':
            STATE.close_clients()
            self._json({'ok': True})
            return
        self._json({
            'endpoints': [
                '/events',
                '/clear-events',
                '/reset',
                '/map-update',
                '/map-reset',
                '/map-disable',
                '/map-enable',
                '/pause?stream=status|estop|all&seconds=4',
                '/malformed',
                '/partial',
                '/unknown',
                '/close',
            ]
        })

    def log_message(self, _format, *_args):
        return

    def _json(self, value):
        body = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def broadcast_raw_status(data):
    text = ros_publish('/mission_manager/status_json', data)
    with STATE.lock:
        clients = list(STATE.clients)
    for client in clients:
        if client.status_subscribed:
            client.send_text(text)


def broadcast_map():
    if not STATE.is_map_available():
        return
    text = ros_map_publish(STATE.map_snapshot())
    with STATE.lock:
        clients = list(STATE.clients)
    for client in clients:
        if client.map_subscribed:
            client.send_text(text)


def telemetry_loop():
    while True:
        now = time.monotonic()
        status_text = ros_publish(
            '/mission_manager/status_json',
            json.dumps(STATE.snapshot(), ensure_ascii=False, separators=(',', ':')),
        )
        with STATE.lock:
            clients = list(STATE.clients)
            estop = STATE.estop
            status_paused = now < STATE.pause_status_until
            estop_paused = now < STATE.pause_estop_until
        estop_text = ros_publish('/safety/estop', estop)
        for client in clients:
            if client.status_subscribed and not status_paused:
                client.send_text(status_text)
            if client.estop_subscribed and not estop_paused:
                client.send_text(estop_text)
        time.sleep(0.35)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Map test controls:\n'
            '  GET /map-update  publish the next deterministic map revision\n'
            '  GET /map-reset   restore and publish the initial test apartment\n'
            '  GET /map-disable simulate /map missing at subscribe time\n'
            '  GET /map-enable  make /map available without broadcasting'
        ),
    )
    parser.add_argument('--host', default='127.0.0.1', help='listen address')
    parser.add_argument('--port', type=int, default=9090, help='WebSocket port')
    parser.add_argument(
        '--control-port',
        type=int,
        default=9091,
        help='HTTP control and event port',
    )
    args = parser.parse_args()

    websocket_server = WebSocketServer((args.host, args.port), WebSocketHandler)
    control_server = ThreadingHTTPServer((args.host, args.control_port), ControlHandler)
    threading.Thread(target=telemetry_loop, daemon=True).start()
    threading.Thread(target=control_server.serve_forever, daemon=True).start()
    print(
        f'Mock rosbridge: ws://{args.host}:{args.port}/ '
        f'control: http://{args.host}:{args.control_port}/\n'
        f'Map controls: http://{args.host}:{args.control_port}/map-update '
        f'/map-reset /map-disable /map-enable',
        flush=True,
    )
    try:
        websocket_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        websocket_server.shutdown()
        control_server.shutdown()


if __name__ == '__main__':
    main()
