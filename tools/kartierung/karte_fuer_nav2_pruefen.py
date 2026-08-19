#!/usr/bin/env python3
"""Prueft eine ROS-2-Trinary-Karte vor dem Start von Nav2.

Der Nav2-Map-Server interpretiert Pixel anhand der Schwellwerte in map.yaml.
Ein zu hoher free_thresh kann dabei den von map_saver verwendeten
Unbekannt-Wert 205 unbemerkt in freien Raum umwandeln. Das Werkzeug bildet
diese Interpretation fuer die im Projekt verwendeten PGM-Karten nach und
bricht bei genau diesem Informationsverlust ab.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class MapCheckError(ValueError):
    """Die Karte ist fuer einen sicheren Nav2-Start ungeeignet."""


@dataclass(frozen=True)
class MapStatistics:
    width: int
    height: int
    resolution: float
    free: int
    occupied: int
    unknown: int
    source_unknown_marker: int

    @property
    def free_area_m2(self) -> float:
        return self.free * self.resolution * self.resolution

    @property
    def unknown_area_m2(self) -> float:
        return self.unknown * self.resolution * self.resolution


def _next_pgm_token(data: bytes, offset: int) -> tuple[bytes, int]:
    length = len(data)
    while offset < length:
        if data[offset] in b' \t\r\n':
            offset += 1
            continue
        if data[offset] == ord('#'):
            newline = data.find(b'\n', offset)
            if newline < 0:
                raise MapCheckError('Unvollstaendiger Kommentar im PGM-Header.')
            offset = newline + 1
            continue
        break
    start = offset
    while offset < length and data[offset] not in b' \t\r\n#':
        offset += 1
    if start == offset:
        raise MapCheckError('Unvollstaendiger PGM-Header.')
    return data[start:offset], offset


def read_pgm(path: Path) -> tuple[int, int, int, list[int]]:
    data = path.read_bytes()
    magic, offset = _next_pgm_token(data, 0)
    width_raw, offset = _next_pgm_token(data, offset)
    height_raw, offset = _next_pgm_token(data, offset)
    maxval_raw, offset = _next_pgm_token(data, offset)
    try:
        width = int(width_raw)
        height = int(height_raw)
        maxval = int(maxval_raw)
    except ValueError as exc:
        raise MapCheckError('Ungueltige Zahl im PGM-Header.') from exc
    if width <= 0 or height <= 0 or not 1 <= maxval <= 255:
        raise MapCheckError('PGM braucht positive Masse und maxval 1..255.')

    expected = width * height
    if magic == b'P5':
        if offset >= len(data) or data[offset] not in b' \t\r\n':
            raise MapCheckError('Trennzeichen hinter PGM-maxval fehlt.')
        if data[offset] == ord('\r') and offset + 1 < len(data) \
                and data[offset + 1] == ord('\n'):
            offset += 2
        else:
            offset += 1
        pixels = list(data[offset:])
        if len(pixels) != expected:
            raise MapCheckError(
                f'PGM-Pixeldaten: erwartet {expected}, gefunden {len(pixels)}.')
    elif magic == b'P2':
        pixels = []
        for _ in range(expected):
            token, offset = _next_pgm_token(data, offset)
            try:
                pixels.append(int(token))
            except ValueError as exc:
                raise MapCheckError('Ungueltiger Pixel in ASCII-PGM.') from exc
        try:
            _next_pgm_token(data, offset)
        except MapCheckError:
            pass
        else:
            raise MapCheckError('ASCII-PGM enthaelt mehr Pixel als angegeben.')
    else:
        raise MapCheckError('Nur PGM P5/P2 wird fuer den Nav2-Start akzeptiert.')

    if any(pixel < 0 or pixel > maxval for pixel in pixels):
        raise MapCheckError('PGM-Pixel liegt ausserhalb 0..maxval.')
    return width, height, maxval, pixels


def _required_number(config: dict[str, Any], key: str) -> float:
    value = config.get(key)
    if isinstance(value, bool):
        raise MapCheckError(f'{key} muss eine Zahl sein.')
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MapCheckError(f'{key} muss eine Zahl sein.') from exc
    if not math.isfinite(number):
        raise MapCheckError(f'{key} muss endlich sein.')
    return number


def check_map(yaml_path: Path) -> MapStatistics:
    try:
        config = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise MapCheckError(f'map.yaml kann nicht gelesen werden: {exc}') from exc
    if not isinstance(config, dict):
        raise MapCheckError('map.yaml muss ein YAML-Objekt enthalten.')
    if config.get('mode', 'trinary') != 'trinary':
        raise MapCheckError('Nur mode: trinary ist fuer diesen Start freigegeben.')

    image_value = config.get('image')
    if not isinstance(image_value, str) or not image_value.strip():
        raise MapCheckError('image fehlt in map.yaml.')
    image_path = Path(image_value)
    if not image_path.is_absolute():
        image_path = yaml_path.parent / image_path
    try:
        image_path = image_path.resolve(strict=True)
    except OSError as exc:
        raise MapCheckError(f'Kartenbild fehlt: {image_path}') from exc
    if image_path.suffix.lower() != '.pgm':
        raise MapCheckError('Das gepruefte Amadeus-Kartenformat ist PGM.')

    resolution = _required_number(config, 'resolution')
    free_thresh = _required_number(config, 'free_thresh')
    occupied_thresh = _required_number(config, 'occupied_thresh')
    if resolution <= 0.0:
        raise MapCheckError('resolution muss groesser als null sein.')
    if not 0.0 <= free_thresh < occupied_thresh <= 1.0:
        raise MapCheckError(
            'Schwellwerte brauchen 0 <= free_thresh < occupied_thresh <= 1.')
    negate = config.get('negate')
    if negate not in (0, 1, False, True):
        raise MapCheckError('negate muss 0 oder 1 sein.')
    origin = config.get('origin')
    if not isinstance(origin, list) or len(origin) != 3:
        raise MapCheckError('origin muss aus [x, y, yaw] bestehen.')
    for value in origin:
        if isinstance(value, bool):
            raise MapCheckError('origin darf nur endliche Zahlen enthalten.')
        try:
            finite = math.isfinite(float(value))
        except (TypeError, ValueError) as exc:
            raise MapCheckError(
                'origin darf nur endliche Zahlen enthalten.') from exc
        if not finite:
            raise MapCheckError('origin darf nur endliche Zahlen enthalten.')

    width, height, maxval, pixels = read_pgm(image_path)
    free = occupied = unknown = marker = marker_unknown = 0
    marker_value = round(205 * maxval / 255)
    for pixel in pixels:
        occupancy = pixel / maxval if bool(negate) else (maxval - pixel) / maxval
        if occupancy > occupied_thresh:
            occupied += 1
            classification = 'occupied'
        elif occupancy < free_thresh:
            free += 1
            classification = 'free'
        else:
            unknown += 1
            classification = 'unknown'
        if pixel == marker_value:
            marker += 1
            if classification == 'unknown':
                marker_unknown += 1

    # map_saver schreibt unbekannte Zellen als 205. Wenige gleichfarbige
    # Antialiasing-Pixel sind kein belastbarer Herkunftsnachweis; ab 0,1 %
    # bzw. mindestens 100 Zellen handelt es sich bei unseren Karten um eine
    # echte unbekannte Region, die beim Laden erhalten bleiben muss.
    marker_limit = max(100, math.ceil(width * height * 0.001))
    if marker >= marker_limit and marker_unknown == 0:
        raise MapCheckError(
            f'GEFAEHRLICHER KARTENVERLUST: {marker} Quellzellen mit '
            f'Unbekannt-Marker 205 wuerden nicht als unbekannt geladen '
            f'(free_thresh={free_thresh:g}).')

    return MapStatistics(
        width=width,
        height=height,
        resolution=resolution,
        free=free,
        occupied=occupied,
        unknown=unknown,
        source_unknown_marker=marker,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Prueft eine PGM/YAML-Karte vor dem Nav2-Start.')
    parser.add_argument('map_yaml', type=Path)
    args = parser.parse_args()
    try:
        stats = check_map(args.map_yaml.resolve(strict=True))
    except (OSError, MapCheckError) as exc:
        print(f'KARTENPRUEFUNG FEHLGESCHLAGEN: {exc}', file=sys.stderr)
        return 1
    print(
        'Kartenpruefung bestanden: '
        f'{stats.width}x{stats.height}, '
        f'frei={stats.free} ({stats.free_area_m2:.2f} m2), '
        f'belegt={stats.occupied}, '
        f'unbekannt={stats.unknown} ({stats.unknown_area_m2:.2f} m2), '
        f'Quellmarker205={stats.source_unknown_marker}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
