#!/usr/bin/env python3
"""Small dependency-free rosbridge mock for iOS simulator UI tests."""

import argparse
import base64
import hashlib
import json
import math
import re
import socket
import socketserver
import struct
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


ROSBRIDGE_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
MAP_TOPIC = '/map'
MAP_WIDTH = 48
MAP_HEIGHT = 36
MAP_RESOLUTION = 0.10
MAP_ORIGIN = (-2.4, -1.8, 0.0)
MAP_MANAGER_STATUS_TOPIC = '/robot_map_manager/status_json'
MAP_MANAGER_COMMAND_TOPIC = '/robot_map_manager/command_json'
SEMANTIC_STATUS_TOPIC = '/semantic_map/status_json'
SEMANTIC_COMMAND_TOPIC = '/semantic_map/command_json'
REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$')
SAFE_ID_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,63}$')
FINGERPRINT_RE = re.compile(r'^[0-9a-f]{64}$')
COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def _map_fingerprint(snapshot):
    """Match robot_map_manager.MapSnapshot and the native iOS codec."""
    info = snapshot['info']
    origin = info['origin']
    frame = snapshot['header']['frame_id'].encode('utf-8')
    digest = hashlib.sha256()
    digest.update(struct.pack(
        '!IId',
        info['width'],
        info['height'],
        info['resolution'],
    ))
    digest.update(struct.pack('!H', len(frame)))
    digest.update(frame)
    position = origin['position']
    orientation = origin['orientation']
    digest.update(struct.pack(
        '!7d',
        position['x'], position['y'], position['z'],
        orientation['x'], orientation['y'],
        orientation['z'], orientation['w'],
    ))
    digest.update(bytes(255 if value == -1 else value for value in snapshot['data']))
    return digest.hexdigest()


def _map_version(fingerprint):
    """Match robot_map_manager's persisted version identifier."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    return f'{timestamp}-{fingerprint[:12]}'


def _valid_request_id(value):
    return isinstance(value, str) and REQUEST_ID_RE.fullmatch(value) is not None


def _command_signature(command):
    canonical = json.dumps(command, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _immutable_outcome(response):
    """Keep the idempotent result, never a stale global status snapshot."""
    return {
        'event': response['event'],
        'ok': response['ok'],
        'message': response['message'],
    }


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _point_inside_polygon(point, polygon):
    """Strict ray casting; points on an edge are deliberately rejected."""
    px, py = point
    inside = False
    previous = polygon[-1]
    for current in polygon:
        ax, ay = previous
        bx, by = current
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if abs(cross) <= 1e-9 and (
            min(ax, bx) - 1e-9 <= px <= max(ax, bx) + 1e-9
            and min(ay, by) - 1e-9 <= py <= max(ay, by) + 1e-9
        ):
            return False
        if (by > py) != (ay > py):
            crossing_x = (ax - bx) * (py - by) / (ay - by) + bx
            if px < crossing_x:
                inside = not inside
        previous = current
    return inside


def _valid_room_payload(room, map_ref):
    if not isinstance(room, dict):
        return False
    required = {'id', 'name', 'polygon', 'navigation_goal'}
    if not required <= set(room) or set(room) - required - {'color'}:
        return False
    room_id = room.get('id')
    name = room.get('name')
    if not isinstance(room_id, str) or SAFE_ID_RE.fullmatch(room_id) is None:
        return False
    if (
        not isinstance(name, str) or not name.strip() or len(name.strip()) > 80
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in name.strip())
    ):
        return False
    color = room.get('color')
    if color is not None and (not isinstance(color, str) or COLOR_RE.fullmatch(color) is None):
        return False
    raw_polygon = room.get('polygon')
    if not isinstance(raw_polygon, list) or not 3 <= len(raw_polygon) <= 64:
        return False
    polygon = []
    for raw_point in raw_polygon:
        if not isinstance(raw_point, dict) or set(raw_point) != {'x', 'y'}:
            return False
        if not _finite_number(raw_point['x']) or not _finite_number(raw_point['y']):
            return False
        polygon.append((float(raw_point['x']), float(raw_point['y'])))
    if len(set(polygon)) != len(polygon):
        return False
    goal = room.get('navigation_goal')
    if not isinstance(goal, dict) or set(goal) != {'x', 'y', 'yaw'}:
        return False
    if not all(_finite_number(goal[key]) for key in ('x', 'y', 'yaw')):
        return False
    if not -math.pi <= goal['yaw'] <= math.pi:
        return False
    origin = map_ref['origin']['position']
    minimum_x = origin['x']
    minimum_y = origin['y']
    maximum_x = minimum_x + map_ref['width'] * map_ref['resolution']
    maximum_y = minimum_y + map_ref['height'] * map_ref['resolution']
    if not all(
        minimum_x - 1e-9 <= x <= maximum_x + 1e-9
        and minimum_y - 1e-9 <= y <= maximum_y + 1e-9
        for x, y in polygon + [(goal['x'], goal['y'])]
    ):
        return False
    return _point_inside_polygon((goal['x'], goal['y']), polygon)


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
    DEFAULT_ROOMS = ('Wohnzimmer', 'Kueche', 'Werkstatt')

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
            self.last_saved_map = None
            self.semantic_map = None
            self.map_request_cache = {}
            self.semantic_request_cache = {}
            self.status = {
                'state': 'idle',
                'phase': 'bereit',
                'message': 'Bereit (Simulator-Mock)',
                'progress': 0.0,
                'active_command': {},
                'rooms': list(self.DEFAULT_ROOMS),
                'pick_and_place_rooms': ['Wohnzimmer', 'Kueche'],
                'targets': ['Tisch', 'Regal', 'Arbeitsplatte'],
                'objects': ['Tasse', 'Flasche', 'Fernbedienung'],
                'offboard_available': True,
                'cancel_pending': False,
                'last_rejection': '',
                'explore_execution': 'bt_explicit_opt_in',
            }
            self.explore_status = {
                'schema_version': 1,
                'backend_ready': True,
                'state': 'idle',
                'phase': 'idle',
                'message': 'Explorer bereit (Simulator-Mock)',
                'strategy': 'frontier_then_adaptive_coverage',
                'coverage_ratio': 0.0,
                'coverage_percent': 0.0,
                'target_coverage_percent': 85.0,
                'reachable_area_m2': 12.0,
                'covered_area_m2': 0.0,
                'frontiers_visited': 0,
                'coverage_goals_visited': 0,
                'frontiers_remaining': 3,
                'map_ready_to_save': False,
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

    def map_summary(self):
        snapshot = self.map_snapshot()
        info = snapshot['info']
        return {
            'width': info['width'],
            'height': info['height'],
            'resolution': info['resolution'],
            'frame_id': snapshot['header']['frame_id'],
            'origin': info['origin'],
            'source_stamp_ns': 0,
            'fingerprint': _map_fingerprint(snapshot),
        }

    def map_manager_status(
        self,
        event='status',
        ok=True,
        request_id=None,
        message='Kartenmanager bereit (Simulator-Mock)',
    ):
        with self.lock:
            summary = self.map_summary() if self.map_available else None
            return {
                'schema_version': 1,
                'event': event,
                'ok': ok,
                'request_id': request_id,
                'message': message,
                'map': {
                    'snapshot_available': summary is not None,
                    'summary': summary,
                },
                'storage': {
                    'last_saved': self.last_saved_map,
                },
            }

    def semantic_status(
        self,
        event='status',
        ok=None,
        request_id=None,
        message='Semantischer Kartenmanager bereit (Simulator-Mock)',
    ):
        with self.lock:
            semantic_map = (
                {
                    'map_ref': None,
                    'revision': None,
                    'rooms': [],
                    'editable': False,
                    'edit_block_reason': 'Zuerst die Karte für Räume speichern',
                    'updated_at': None,
                }
                if self.semantic_map is None
                else json.loads(json.dumps(self.semantic_map))
            )
            if ok is None:
                ok = self.semantic_map is not None
        return {
            'schema_version': 1,
            'event': event,
            'ok': ok,
            'request_id': request_id,
            'message': message,
            'semantic_map': semantic_map,
        }

    def bump_semantic_revision(self):
        """Apply an external revision without broadcasting it to clients."""
        with self.lock:
            if self.semantic_map is None:
                return None
            self.semantic_map['revision'] += 1
            return self.semantic_map['revision']

    def _sync_mission_rooms_from_semantic(self):
        names = (
            []
            if self.semantic_map is None
            else [room['name'] for room in self.semantic_map['rooms']]
        )
        self.status['rooms'] = names or list(self.DEFAULT_ROOMS)

    def save_map_for_rooms(self, command):
        request_id = command.get('request_id')
        signature = _command_signature(command)
        with self.lock:
            cached = self.map_request_cache.get(request_id)
            if cached is not None:
                old_signature, outcome = cached
                if old_signature == signature:
                    return self.map_manager_status(
                        event=outcome['event'],
                        ok=outcome['ok'],
                        request_id=request_id,
                        message=outcome['message'],
                    )
                return self.map_manager_status(
                    event='save_result',
                    ok=False,
                    request_id=request_id,
                    message='request_id wurde bereits für ein anderes Kommando benutzt',
                )

            if (
                set(command) != {'command', 'name', 'request_id'}
                or command.get('command') != 'save'
                or command.get('name') != 'wohnung'
                or not _valid_request_id(request_id)
            ):
                response = self.map_manager_status(
                    event='save_result',
                    ok=False,
                    request_id=request_id,
                    message='Ungültiger Save-Befehl',
                )
            else:
                summary = self.map_summary()
                version = _map_version(summary['fingerprint'])
                self.last_saved_map = {
                    'name': 'wohnung',
                    'version': version,
                    'width': summary['width'],
                    'height': summary['height'],
                    'resolution': summary['resolution'],
                    'frame_id': summary['frame_id'],
                    'fingerprint': summary['fingerprint'],
                }
                self.semantic_map = {
                    'map_ref': {
                        'name': 'wohnung',
                        'version': version,
                        'fingerprint': summary['fingerprint'],
                        'frame_id': summary['frame_id'],
                        'width': summary['width'],
                        'height': summary['height'],
                        'resolution': summary['resolution'],
                        'origin': summary['origin'],
                    },
                    'revision': 0,
                    'rooms': [],
                    'editable': True,
                }
                response = self.map_manager_status(
                    event='save_result',
                    ok=True,
                    request_id=request_id,
                    message='Karte für Räume gespeichert',
                )
            self.map_request_cache[request_id] = (
                signature,
                _immutable_outcome(response),
            )
            return response

    def apply_semantic_command(self, command):
        request_id = command.get('request_id')
        signature = _command_signature(command)
        with self.lock:
            cached = self.semantic_request_cache.get(request_id)
            if cached is not None:
                old_signature, outcome = cached
                if old_signature == signature:
                    return self.semantic_status(
                        event=outcome['event'],
                        ok=outcome['ok'],
                        request_id=request_id,
                        message=outcome['message'],
                    )
                return self.semantic_status(
                    event='request_id_conflict',
                    ok=False,
                    request_id=request_id,
                    message='request_id wurde bereits für ein anderes Kommando benutzt',
                )

            command_name = command.get('command')
            expected_keys = {
                'upsert_room': {
                    'command', 'request_id', 'map_fingerprint', 'base_revision', 'room'
                },
                'delete_room': {
                    'command', 'request_id', 'map_fingerprint', 'base_revision', 'room_id'
                },
            }.get(command_name)
            if (
                expected_keys is None
                or set(command) != expected_keys
                or not _valid_request_id(request_id)
                or not isinstance(command.get('map_fingerprint'), str)
                or FINGERPRINT_RE.fullmatch(command['map_fingerprint']) is None
                or not isinstance(command.get('base_revision'), int)
                or isinstance(command.get('base_revision'), bool)
                or command['base_revision'] < 0
            ):
                response = self.semantic_status(
                    event='validation_error',
                    ok=False,
                    request_id=request_id,
                    message='Ungültiger semantischer Befehl',
                )
            elif self.semantic_map is None:
                response = self.semantic_status(
                    event='not_editable',
                    ok=False,
                    request_id=request_id,
                    message='Zuerst die Karte für Räume speichern',
                )
            elif command.get('map_fingerprint') != self.semantic_map['map_ref']['fingerprint']:
                response = self.semantic_status(
                    event='map_conflict',
                    ok=False,
                    request_id=request_id,
                    message='Kartenfingerabdruck stimmt nicht überein',
                )
            elif command.get('base_revision') != self.semantic_map['revision']:
                response = self.semantic_status(
                    event='revision_conflict',
                    ok=False,
                    request_id=request_id,
                    message='Revision conflict: Kartenstand neu laden',
                )
            elif command_name == 'upsert_room':
                room = command['room']
                room_id = room.get('id')
                if not _valid_room_payload(room, self.semantic_map['map_ref']):
                    response = self.semantic_status(
                        event='validation_error',
                        ok=False,
                        request_id=request_id,
                        message='Ungültige Raumdaten',
                    )
                elif (
                    len(self.semantic_map['rooms']) >= 256
                    and not any(value.get('id') == room_id for value in self.semantic_map['rooms'])
                ):
                    response = self.semantic_status(
                        event='validation_error',
                        ok=False,
                        request_id=request_id,
                        message='Maximal 256 Räume sind erlaubt',
                    )
                elif (
                    sum(
                        len(value.get('polygon', []))
                        for value in self.semantic_map['rooms']
                        if value.get('id') != room_id
                    ) + len(room.get('polygon', [])) > 4096
                ):
                    response = self.semantic_status(
                        event='validation_error',
                        ok=False,
                        request_id=request_id,
                        message='Maximal 4096 Polygonpunkte insgesamt sind erlaubt',
                    )
                else:
                    rooms = self.semantic_map['rooms']
                    event = (
                        'room_updated'
                        if any(value.get('id') == room_id for value in rooms)
                        else 'room_created'
                    )
                    rooms[:] = [value for value in rooms if value.get('id') != room_id]
                    rooms.append(room)
                    self.semantic_map['revision'] += 1
                    response = self.semantic_status(
                        event=event,
                        ok=True,
                        request_id=request_id,
                        message=f"Raum {room.get('name', room_id)} gespeichert",
                    )
            elif (
                command_name == 'delete_room'
                and isinstance(command['room_id'], str)
                and SAFE_ID_RE.fullmatch(command['room_id']) is not None
            ):
                room_id = command['room_id']
                rooms = self.semantic_map['rooms']
                before = len(rooms)
                rooms[:] = [value for value in rooms if value.get('id') != room_id]
                if len(rooms) == before:
                    response = self.semantic_status(
                        event='not_found',
                        ok=False,
                        request_id=request_id,
                        message='Raum nicht gefunden',
                    )
                else:
                    self.semantic_map['revision'] += 1
                    response = self.semantic_status(
                        event='room_deleted',
                        ok=True,
                        request_id=request_id,
                        message='Raum gelöscht',
                    )
            else:
                response = self.semantic_status(
                    event='validation_error',
                    ok=False,
                    request_id=request_id,
                    message='Ungültiger semantischer Befehl',
                )
            if response.get('ok') and response.get('event') in {
                'room_created', 'room_updated', 'room_deleted',
            }:
                self._sync_mission_rooms_from_semantic()
            self.semantic_request_cache[request_id] = (
                signature,
                _immutable_outcome(response),
            )
            return response

    def snapshot(self):
        with self.lock:
            payload = dict(self.status)
            payload['time'] = time.time()
            return payload

    def explore_snapshot(self):
        with self.lock:
            payload = dict(self.explore_status)
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
            if command.get('type') == 'explore':
                self.explore_status.update({
                    'state': 'running',
                    'phase': 'initial_scan',
                    'message': '360-Grad-Rundblick (Simulator-Mock)',
                    'coverage_ratio': 0.08,
                    'coverage_percent': 8.0,
                    'covered_area_m2': 0.96,
                    'frontiers_visited': 0,
                    'coverage_goals_visited': 0,
                    'frontiers_remaining': 3,
                    'map_ready_to_save': False,
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
                if self.status['active_command'].get('type') == 'explore':
                    ratio = min(0.82, progress)
                    self.explore_status.update({
                        'state': 'running',
                        'phase': 'frontier' if progress < 0.55 else 'coverage',
                        'message': f'Explorer-Fortschritt: {round(ratio * 100)} %',
                        'coverage_ratio': ratio,
                        'coverage_percent': ratio * 100.0,
                        'covered_area_m2': ratio * 12.0,
                        'frontiers_visited': 1 if progress < 0.55 else 3,
                        'coverage_goals_visited': 0 if progress < 0.55 else 2,
                        'frontiers_remaining': 2 if progress < 0.55 else 0,
                    })
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
            if self.status['active_command'].get('type') == 'explore':
                self.explore_status.update({
                    'state': 'success',
                    'phase': 'complete',
                    'message': 'Zielabdeckung erreicht (Simulator-Mock)',
                    'coverage_ratio': 0.85,
                    'coverage_percent': 85.0,
                    'covered_area_m2': 10.2,
                    'frontiers_visited': 3,
                    'coverage_goals_visited': 3,
                    'frontiers_remaining': 0,
                    'map_ready_to_save': True,
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
            if self.status['active_command'].get('type') == 'explore':
                self.explore_status.update({
                    'state': 'canceled',
                    'phase': 'canceled',
                    'message': 'Erkundung vom Simulator-Mock abgebrochen',
                    'map_ready_to_save': False,
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
        self.explore_status_subscribed = False
        self.estop_subscribed = False
        self.map_subscription_ids = set()
        self.map_manager_status_subscribed = False
        self.semantic_status_subscribed = False

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
            self.explore_status_subscribed |= topic == '/explore/status_json'
            self.estop_subscribed |= topic == '/safety/estop'
            if topic == MAP_MANAGER_STATUS_TOPIC:
                self.map_manager_status_subscribed = True
                self.send_text(ros_publish(
                    MAP_MANAGER_STATUS_TOPIC,
                    json.dumps(
                        STATE.map_manager_status(),
                        ensure_ascii=False,
                        separators=(',', ':'),
                    ),
                ))
            if topic == SEMANTIC_STATUS_TOPIC:
                self.semantic_status_subscribed = True
                self.send_text(ros_publish(
                    SEMANTIC_STATUS_TOPIC,
                    json.dumps(
                        STATE.semantic_status(),
                        ensure_ascii=False,
                        separators=(',', ':'),
                    ),
                ))
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
            if topic == '/explore/status_json':
                self.explore_status_subscribed = False
            if topic == '/safety/estop':
                self.estop_subscribed = False
            if topic == MAP_MANAGER_STATUS_TOPIC:
                self.map_manager_status_subscribed = False
            if topic == SEMANTIC_STATUS_TOPIC:
                self.semantic_status_subscribed = False
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
        elif topic == MAP_MANAGER_COMMAND_TOPIC and isinstance(data, str):
            command = json.loads(data)
            response = STATE.save_map_for_rooms(command)
            STATE.record('map_manager_command', command)
            broadcast_map_manager_status(response)
            if response.get('ok'):
                broadcast_semantic_status(STATE.semantic_status(
                    event='snapshot',
                    message='Semantische Karte ist bereit',
                ))
        elif topic == SEMANTIC_COMMAND_TOPIC and isinstance(data, str):
            command = json.loads(data)
            response = STATE.apply_semantic_command(command)
            STATE.record('semantic_command', command)
            broadcast_semantic_status(response)

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
            broadcast_map_manager_status(STATE.map_manager_status())
            broadcast_semantic_status(STATE.semantic_status())
            self._json({'ok': True})
            return
        if parsed.path == '/map-update':
            revision = STATE.advance_map()
            broadcast_map()
            broadcast_map_manager_status(STATE.map_manager_status(
                event='map_received',
                message='Geänderte Testkarte empfangen',
            ))
            self._json({'ok': True, 'map_revision': revision})
            return
        if parsed.path == '/map-reset':
            revision = STATE.reset_map()
            broadcast_map()
            broadcast_map_manager_status(STATE.map_manager_status(
                event='map_received',
                message='Testkarte zurückgesetzt',
            ))
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
        if parsed.path in ('/semantic-bump', '/semantic-bump-silent'):
            revision = STATE.bump_semantic_revision()
            if revision is None:
                self._json({'ok': False, 'error': 'semantic map missing'})
                return
            if parsed.path == '/semantic-bump':
                broadcast_semantic_status(STATE.semantic_status(
                    event='snapshot',
                    message='Semantische Revision extern geändert',
                ))
            self._json({'ok': True, 'semantic_revision': revision})
            return
        if parsed.path == '/semantic-reset':
            with STATE.lock:
                STATE.last_saved_map = None
                STATE.semantic_map = None
                STATE._sync_mission_rooms_from_semantic()
                STATE.map_request_cache.clear()
                STATE.semantic_request_cache.clear()
            broadcast_map_manager_status(STATE.map_manager_status())
            broadcast_semantic_status(STATE.semantic_status())
            self._json({'ok': True})
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
                '/semantic-bump',
                '/semantic-bump-silent',
                '/semantic-reset',
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


def broadcast_map_manager_status(payload):
    text = ros_publish(
        MAP_MANAGER_STATUS_TOPIC,
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
    )
    with STATE.lock:
        clients = list(STATE.clients)
    for client in clients:
        if client.map_manager_status_subscribed:
            client.send_text(text)


def broadcast_semantic_status(payload):
    text = ros_publish(
        SEMANTIC_STATUS_TOPIC,
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
    )
    with STATE.lock:
        clients = list(STATE.clients)
    for client in clients:
        if client.semantic_status_subscribed:
            client.send_text(text)


def telemetry_loop():
    while True:
        now = time.monotonic()
        status_text = ros_publish(
            '/mission_manager/status_json',
            json.dumps(STATE.snapshot(), ensure_ascii=False, separators=(',', ':')),
        )
        explore_status_text = ros_publish(
            '/explore/status_json',
            json.dumps(
                STATE.explore_snapshot(),
                ensure_ascii=False,
                separators=(',', ':'),
            ),
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
            if client.explore_status_subscribed and not status_paused:
                client.send_text(explore_status_text)
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
            '  GET /map-enable  make /map available without broadcasting\n'
            '  GET /semantic-reset return to the first-save UI state\n'
            '  GET /semantic-bump-silent provoke a revision conflict'
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
        f'/map-reset /map-disable /map-enable /semantic-reset '
        f'/semantic-bump-silent',
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
