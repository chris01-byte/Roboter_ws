"""Geometrie der KI-Erkundung: Montage von Kamera und LiDAR, Projektion ins Bild.

Rahmen:

* **Bodenrahmen des Roboters:** Ursprung am Boden unter der Antriebsmitte
  (Drehpunkt), x nach vorn, y nach links, z nach oben.
* **Standpunktrahmen:** der Bodenrahmen zum Zeitpunkt der ersten Aufnahme
  einer Blickrunde. Dreht sich Amadeus auf der Stelle um ``gier``, gilt
  ``p_standpunkt = Rz(gier) · p_roboter``.
* **Kamerarahmen (optisch):** z in Blickrichtung, x nach rechts, y nach unten.

Die Vorgabewerte stammen aus dem Projekt (URDF, gemessen 26./27.07.2026;
LiDAR-Montage, gemessen 11.08.2026). Die Aufnahme speichert die tatsächlich
gelesenen Werte; die Vorgaben gelten nur, wenn keine gelesen werden konnten.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np

BASIS_HOEHE_M = 0.09          # base_link über dem Boden
KAMERA_X_M = 0.150            # vor der Antriebsmitte
KAMERA_HOEHE_M = 1.34         # über dem Boden
KAMERA_NEIGUNG_RAD = 0.3306   # 18,94 Grad nach unten
LIDAR_X_M = 0.245             # vor der Antriebsmitte
LIDAR_HOEHE_M = 0.75          # über dem Boden
LIDAR_GIER_RAD = math.pi / 2.0


def drehung_z(gier_rad: float) -> np.ndarray:
    """3x3-Drehung um die Hochachse."""
    c, s = math.cos(gier_rad), math.sin(gier_rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def kamera_montage(x: float = KAMERA_X_M, y: float = 0.0,
                   hoehe: float = KAMERA_HOEHE_M,
                   neigung_rad: float = KAMERA_NEIGUNG_RAD,
                   gier_rad: float = 0.0) -> np.ndarray:
    """4x4: Punkt im optischen Kamerarahmen -> Punkt im Bodenrahmen."""
    ca, sa = math.cos(neigung_rad), math.sin(neigung_rad)
    rechts = np.array([0.0, -1.0, 0.0])
    unten = np.array([-sa, 0.0, -ca])
    vorn = np.array([ca, 0.0, -sa])
    t = np.eye(4)
    t[:3, :3] = drehung_z(gier_rad) @ np.column_stack([rechts, unten, vorn])
    t[:3, 3] = [x, y, hoehe]
    return t


def lidar_montage(x: float = LIDAR_X_M, y: float = 0.0,
                  hoehe: float = LIDAR_HOEHE_M,
                  gier_rad: float = LIDAR_GIER_RAD) -> np.ndarray:
    """4x4: Punkt im LiDAR-Rahmen -> Punkt im Bodenrahmen."""
    t = np.eye(4)
    t[:3, :3] = drehung_z(gier_rad)
    t[:3, 3] = [x, y, hoehe]
    return t


def aus_tf(verschiebung: Sequence[float], quaternion_xyzw: Sequence[float],
           basis_hoehe: float = BASIS_HOEHE_M) -> np.ndarray:
    """4x4 Bodenrahmen <- Kind aus einem TF ``base_link -> Kind``.

    ``base_link`` liegt ``basis_hoehe`` über dem Boden; der Bodenrahmen liegt
    darunter.
    """
    x, y, z, w = (float(v) for v in quaternion_xyzw)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-9:
        raise ValueError('Quaternion ohne Länge')
    x, y, z, w = x / n, y / n, z / n, w / n
    r = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    t = np.eye(4)
    t[:3, :3] = r
    t[:3, 3] = [float(verschiebung[0]), float(verschiebung[1]),
                float(verschiebung[2]) + basis_hoehe]
    return t


def invertiere(t: np.ndarray) -> np.ndarray:
    """Inverse einer starren 4x4-Transformation."""
    r = t[:3, :3]
    inv = np.eye(4)
    inv[:3, :3] = r.T
    inv[:3, 3] = -r.T @ t[:3, 3]
    return inv


def transformiere(t: np.ndarray, punkte: np.ndarray) -> np.ndarray:
    """Nx3-Punkte mit einer 4x4-Transformation abbilden."""
    punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
    return punkte @ t[:3, :3].T + t[:3, 3]


@dataclass(frozen=True)
class Kamera:
    """Lochkamera mit optionaler Verzeichnung (OpenCV-Reihenfolge)."""

    breite: int
    hoehe: int
    fx: float
    fy: float
    cx: float
    cy: float
    d: Tuple[float, ...] = ()

    @classmethod
    def aus_info(cls, info: dict) -> 'Kamera':
        """Aus ``{"breite", "hoehe", "k": [9 Werte], "d": [...]}``."""
        k = [float(v) for v in info['k']]
        if len(k) != 9 or k[0] <= 0 or k[4] <= 0:
            raise ValueError('Kameramatrix K ist unvollständig')
        return cls(int(info['breite']), int(info['hoehe']), k[0], k[4], k[2],
                   k[5], tuple(float(v) for v in info.get('d') or ()))

    @classmethod
    def aus_oeffnungswinkel(cls, breite: int, hoehe: int,
                            horizontal_grad: float) -> 'Kamera':
        """Ideale Kamera aus dem waagerechten Öffnungswinkel."""
        f = (breite / 2.0) / math.tan(math.radians(horizontal_grad) / 2.0)
        return cls(int(breite), int(hoehe), f, f, (breite - 1) / 2.0,
                   (hoehe - 1) / 2.0)

    def als_info(self) -> dict:
        return {'breite': self.breite, 'hoehe': self.hoehe,
                'k': [self.fx, 0.0, self.cx, 0.0, self.fy, self.cy,
                      0.0, 0.0, 1.0],
                'd': list(self.d)}

    def oeffnungswinkel_grad(self) -> Tuple[float, float]:
        """Waagerechter und senkrechter Öffnungswinkel (ohne Verzeichnung)."""
        return (math.degrees(2 * math.atan(self.breite / (2 * self.fx))),
                math.degrees(2 * math.atan(self.hoehe / (2 * self.fy))))

    def projiziere(self, punkte: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Nx3-Punkte im Kamerarahmen -> (Nx2 Bildpunkte, N ``vorn``).

        ``vorn`` ist falsch für Punkte hinter oder zu dicht vor der Kamera und
        für Punkte weit außerhalb des Bildkegels (dort faltet das
        Verzeichnungspolynom zurück und würde falsche Bildpunkte liefern).
        """
        punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
        z = punkte[:, 2]
        vorn = z > 0.05
        zs = np.where(vorn, z, 1.0)
        x = punkte[:, 0] / zs
        y = punkte[:, 1] / zs
        grenze_x = 1.5 * (self.breite / 2.0) / self.fx
        grenze_y = 1.5 * (self.hoehe / 2.0) / self.fy
        vorn = vorn & (np.abs(x) <= grenze_x) & (np.abs(y) <= grenze_y)
        if self.d:
            d = list(self.d) + [0.0] * (8 - len(self.d))
            k1, k2, p1, p2, k3, k4, k5, k6 = d[:8]
            r2 = x * x + y * y
            radial = ((1 + r2 * (k1 + r2 * (k2 + r2 * k3)))
                      / (1 + r2 * (k4 + r2 * (k5 + r2 * k6))))
            xd = x * radial + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
            yd = y * radial + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
            x, y = xd, yd
        uv = np.column_stack([self.fx * x + self.cx, self.fy * y + self.cy])
        return uv, vorn

    def projiziere_ideal(self, punkte: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Wie ``projiziere``, aber ohne Verzeichnung und ohne Kegelgrenze.

        Für Punkte, die außerhalb des Bildes liegen dürfen (zum Beispiel der
        Boden einer nahen Öffnung unterhalb des Bildrands).
        """
        punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
        z = punkte[:, 2]
        vorn = z > 0.05
        zs = np.where(vorn, z, 1.0)
        uv = np.column_stack([self.fx * punkte[:, 0] / zs + self.cx,
                              self.fy * punkte[:, 1] / zs + self.cy])
        return uv, vorn


def standpunkt_nach_kamera(punkte: np.ndarray, gier_rad: float,
                           boden_kamera: np.ndarray) -> np.ndarray:
    """Nx3-Punkte im Standpunktrahmen -> Kamerarahmen bei Gier ``gier_rad``."""
    punkte = np.asarray(punkte, dtype=float).reshape(-1, 3)
    im_roboter = punkte @ drehung_z(gier_rad)        # = Rz(-gier) · p
    return transformiere(invertiere(boden_kamera), im_roboter)


def winkel_normieren(winkel_rad):
    """Auf [-pi, pi) falten; nimmt Zahlen und Felder."""
    return (np.asarray(winkel_rad) + math.pi) % (2 * math.pi) - math.pi
