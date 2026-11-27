"""Hilfe für Tests mit echtem ROS: spielt Sensoren der künstlichen Beispielwelt.

Ein eigener Knoten veröffentlicht in einem Faden Kamerabild, Tiefe,
camera_info, LiDAR-Scan, Odometrie, TF (Montage und Lage in der Karte) und
wahlweise den Status eines gespielten Erkunders – so, wie die Aufnahme sie am
Roboter liest. Der Roboter der Beispielwelt dreht sich dabei langsam.
Nur in abgeschotteter ROS-Umgebung benutzen (siehe test_aufnahme_ros.py).
"""
import json
import math
import threading
import time

import numpy as np

import beispielrunde_erzeugen as welt
from lotse.geometrie import Kamera, kamera_montage

KAMERA = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
THEMEN = {'bild': '/kitest/rgb', 'tiefe': '/kitest/tiefe', 'info': '/kitest/info',
          'scan': '/kitest/scan', 'odom': '/kitest/odom', 'status': '/kitest/status'}


def aufnahme_argumente(ausgabe, name='ros_probe', dauer=30.0):
    """Argumente für blickrunde_aufnehmen.py, passend zu den Themen hier."""
    return ['--name', name, '--ausgabe', str(ausgabe), '--dauer', str(dauer),
            '--bild-topic', THEMEN['bild'], '--tiefe-topic', THEMEN['tiefe'],
            '--info-topic', THEMEN['info'], '--scan-topic', THEMEN['scan'],
            '--odom-topic', THEMEN['odom'], '--status-topic', THEMEN['status']]


def _quaternion_der_kamera():
    r = kamera_montage()[:3, :3]
    w = math.sqrt(1.0 + r[0, 0] + r[1, 1] + r[2, 2]) / 2.0
    return ((r[2, 1] - r[1, 2]) / (4 * w), (r[0, 2] - r[2, 0]) / (4 * w),
            (r[1, 0] - r[0, 1]) / (4 * w), w)


class Spieler:
    """Spielt Sensoren (und wahlweise einen Erkunder) bis ``stopp()``.

    ``status``: Liste von (Sekunden ab Start, dict) – der gespielte Erkunder
    meldet ab diesem Zeitpunkt diesen Status (einmal je Sekunde wiederholt).
    """

    def __init__(self, rclpy, *, scan_hz=10.0, bild_hz=2.0, tf_hz=50.0, status=None,
                 grad_je_s=10.0):
        from geometry_msgs.msg import TransformStamped
        from nav_msgs.msg import Odometry
        from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
        from sensor_msgs.msg import CameraInfo, CompressedImage, LaserScan
        from std_msgs.msg import String
        from tf2_msgs.msg import TFMessage
        from tf2_ros import StaticTransformBroadcaster

        self._rclpy = rclpy
        self._typen = {'TransformStamped': TransformStamped, 'Odometry': Odometry,
                       'CameraInfo': CameraInfo, 'CompressedImage': CompressedImage,
                       'LaserScan': LaserScan, 'String': String, 'TFMessage': TFMessage}
        self.knoten = rclpy.create_node('ki_test_spieler')
        letzter = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self._sender = {
            'bild': self.knoten.create_publisher(CompressedImage, THEMEN['bild'], 5),
            'tiefe': self.knoten.create_publisher(CompressedImage, THEMEN['tiefe'], 5),
            'info': self.knoten.create_publisher(CameraInfo, THEMEN['info'], 5),
            'scan': self.knoten.create_publisher(LaserScan, THEMEN['scan'], 5),
            'odom': self.knoten.create_publisher(Odometry, THEMEN['odom'], 5),
            'status': self.knoten.create_publisher(String, THEMEN['status'], letzter),
            'tf': self.knoten.create_publisher(TFMessage, '/tf', 10),
        }
        self._statisch = StaticTransformBroadcaster(self.knoten)
        self.scan_hz, self.bild_hz, self.tf_hz = scan_hz, bild_hz, tf_hz
        self.grad_je_s = grad_je_s
        self.status = sorted(status or [], key=lambda eintrag: eintrag[0])
        self.flaechen = welt.welt()
        self.x, self.y, self.gier0 = welt.STANDPUNKT
        self._foto = welt.foto(self.flaechen, KAMERA, self.x, self.y, self.gier0)
        self._halt = threading.Event()
        self._faden = None
        self.beginn = None

    # -- Nachrichten --------------------------------------------------------
    def _stempel(self, t):
        nachricht = self.knoten.get_clock().now().to_msg()
        nachricht.sec, nachricht.nanosec = int(t), int((t % 1.0) * 1e9)
        return nachricht

    def _tf(self, eltern, kind, verschiebung, quaternion, t=None):
        tf = self._typen['TransformStamped']()
        tf.header.frame_id, tf.child_frame_id = eltern, kind
        if t is not None:
            tf.header.stamp = self._stempel(t)
        (tf.transform.translation.x, tf.transform.translation.y,
         tf.transform.translation.z) = verschiebung
        (tf.transform.rotation.x, tf.transform.rotation.y,
         tf.transform.rotation.z, tf.transform.rotation.w) = quaternion
        return tf

    def gier(self, t):
        return self.gier0 + math.radians(self.grad_je_s * (t - self.beginn))

    def _sende_scan(self, t):
        roh = welt.scan(self.flaechen, self.x, self.y, self.gier(t), t)
        scan = self._typen['LaserScan']()
        scan.header.frame_id, scan.header.stamp = 'laser_frame', self._stempel(t)
        scan.angle_min, scan.angle_increment = roh['winkel_min'], roh['winkel_schritt']
        scan.range_min, scan.range_max = 0.03, 25.0
        werte = np.array([np.nan if v is None else v for v in roh['entfernungen']])
        werte[roh['weit']] = np.inf
        scan.ranges = [float(v) for v in werte]
        self._sender['scan'].publish(scan)
        odom = self._typen['Odometry']()
        odom.header.stamp = self._stempel(t)
        halb = (self.gier(t) - self.gier0) / 2.0
        odom.pose.pose.orientation.z, odom.pose.pose.orientation.w = math.sin(halb), math.cos(halb)
        self._sender['odom'].publish(odom)

    def _sende_bild(self, t):
        info = self._typen['CameraInfo']()
        info.header.frame_id = 'oak_rgb_camera_optical_frame'
        info.width, info.height = KAMERA.breite, KAMERA.hoehe
        info.k = [float(v) for v in KAMERA.als_info()['k']]
        self._sender['info'].publish(info)
        for name, daten, form in (('tiefe', b'\x89PNGtiefe', '16UC1; png'),
                                  ('bild', self._foto, 'jpeg; bgr8')):
            bild = self._typen['CompressedImage']()
            bild.header.frame_id = 'oak_rgb_camera_optical_frame'
            bild.header.stamp = self._stempel(t + 0.01)
            bild.format, bild.data = form, daten
            self._sender[name].publish(bild)

    def _sende_lage(self, t):
        halb = self.gier(t) / 2.0
        nachricht = self._typen['TFMessage']()
        nachricht.transforms = [self._tf('map', 'base_link', (self.x, self.y, 0.0),
                                         (0.0, 0.0, math.sin(halb), math.cos(halb)), t)]
        self._sender['tf'].publish(nachricht)

    def _sende_status(self, seit):
        aktuell = None
        for ab, status in self.status:
            if seit >= ab:
                aktuell = status
        if aktuell is not None:
            self._sender['status'].publish(self._typen['String'](data=json.dumps(aktuell)))

    # -- Ablauf -------------------------------------------------------------
    def _spiele(self):
        naechst = {'scan': 0.0, 'bild': 0.0, 'tf': 0.0, 'status': 0.0}
        takt = {'scan': 1.0 / self.scan_hz, 'bild': 1.0 / self.bild_hz,
                'tf': 1.0 / self.tf_hz, 'status': 1.0}
        letzter_status = None
        while not self._halt.is_set():
            jetzt = time.time()
            seit = jetzt - self.beginn
            try:
                if seit >= naechst['scan']:
                    naechst['scan'] = seit + takt['scan']
                    self._sende_scan(jetzt)
                if seit >= naechst['bild']:
                    naechst['bild'] = seit + takt['bild']
                    self._sende_bild(jetzt)
                if seit >= naechst['tf']:
                    naechst['tf'] = seit + takt['tf']
                    self._sende_lage(jetzt)
                stufe = sum(1 for ab, _ in self.status if seit >= ab)
                if seit >= naechst['status'] or stufe != letzter_status:
                    naechst['status'] = seit + takt['status']
                    letzter_status = stufe
                    self._sende_status(seit)
            except Exception:                   # noqa: BLE001 (Kontext beim Ende weg)
                if not self._rclpy.ok():
                    return
                raise
            self._halt.wait(0.002)

    def start(self):
        self._statisch.sendTransform([
            self._tf('base_link', 'laser_frame', (0.245, 0.0, 0.66),
                     (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5))),
            self._tf('base_link', 'oak_rgb_camera_optical_frame', (0.15, 0.0, 1.25),
                     _quaternion_der_kamera())])
        self.beginn = time.time()
        self._faden = threading.Thread(target=self._spiele, daemon=True)
        self._faden.start()
        return self

    def stopp(self):
        self._halt.set()
        if self._faden is not None:
            self._faden.join(timeout=5.0)
        self.knoten.destroy_node()
