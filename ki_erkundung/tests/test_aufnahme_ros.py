"""Aufnahme einer Blickrunde über echte ROS-Themen (nur wo rclpy vorhanden ist).

Ein Hilfsknoten spielt Kamera-Relay, LiDAR, Odometrie und TF mit Daten der
künstlichen Beispielwelt; das Aufnahmewerkzeug hört wie am Roboter mit.
Aufruf in einer abgeschotteten ROS-Umgebung, zum Beispiel:

    env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \\
        python3 -m pytest -q ki_erkundung/tests/test_aufnahme_ros.py
"""
import math
import threading
import time

import numpy as np
import pytest

rclpy = pytest.importorskip('rclpy')

import beispielrunde_erzeugen as welt  # noqa: E402
from blickrunde_aufnehmen import eingabe, nehme_auf  # noqa: E402
from lotse.ablauf import bereite_vor  # noqa: E402
from lotse.blickrunde import Blickrunde  # noqa: E402
from lotse.geometrie import Kamera, kamera_montage, lidar_montage  # noqa: E402


def test_aufnahme_ueber_ros_ergibt_eine_auswertbare_blickrunde(tmp_path):
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import CameraInfo, CompressedImage, LaserScan
    from tf2_ros import StaticTransformBroadcaster

    kamera = Kamera.aus_oeffnungswinkel(640, 360, 69.0)
    flaechen = welt.welt()
    x, y, gier0 = welt.STANDPUNKT
    rclpy.init()
    quelle = rclpy.create_node('ki_test_quelle')
    try:
        sender = {
            'bild': quelle.create_publisher(CompressedImage, '/kitest/rgb', 5),
            'tiefe': quelle.create_publisher(CompressedImage, '/kitest/tiefe', 5),
            'info': quelle.create_publisher(CameraInfo, '/kitest/info', 5),
            'scan': quelle.create_publisher(LaserScan, '/kitest/scan', 5),
            'odom': quelle.create_publisher(Odometry, '/kitest/odom', 5),
        }
        # TF wie am Roboter: base_link 0,09 m über dem Boden
        tf_sender = StaticTransformBroadcaster(quelle)
        transformationen = []
        for kind, verschiebung, quaternion in (
                ('laser_frame', (0.245, 0.0, 0.66), (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5))),
                ('oak_rgb_camera_optical_frame', (0.15, 0.0, 1.25), None)):
            tf = TransformStamped()
            tf.header.frame_id, tf.child_frame_id = 'base_link', kind
            (tf.transform.translation.x, tf.transform.translation.y,
             tf.transform.translation.z) = verschiebung
            if quaternion is None:              # Kamera: aus der Montagematrix
                r = kamera_montage()[:3, :3]
                w = math.sqrt(1.0 + r[0, 0] + r[1, 1] + r[2, 2]) / 2.0
                quaternion = ((r[2, 1] - r[1, 2]) / (4 * w), (r[0, 2] - r[2, 0]) / (4 * w),
                              (r[1, 0] - r[0, 1]) / (4 * w), w)
            (tf.transform.rotation.x, tf.transform.rotation.y,
             tf.transform.rotation.z, tf.transform.rotation.w) = quaternion
            transformationen.append(tf)
        tf_sender.sendTransform(transformationen)

        fertig = threading.Event()
        schritte = 25                           # 25 Bilder in 15-Grad-Schritten

        def stempel(t):
            nachricht = quelle.get_clock().now().to_msg()
            nachricht.sec, nachricht.nanosec = int(t), int((t % 1.0) * 1e9)
            return nachricht

        def spiele():
            time.sleep(1.0)                     # Abonnements finden lassen
            t0 = time.time()
            for k in range(schritte):
                gier = gier0 + math.radians(15.0 * k)
                t = t0 + 0.4 * k
                info = CameraInfo()
                info.header.frame_id = 'oak_rgb_camera_optical_frame'
                info.width, info.height = kamera.breite, kamera.hoehe
                info.k = [float(v) for v in kamera.als_info()['k']]
                sender['info'].publish(info)
                roh = welt.scan(flaechen, x, y, gier, t)
                scan = LaserScan()
                scan.header.frame_id, scan.header.stamp = 'laser_frame', stempel(t)
                scan.angle_min, scan.angle_increment = roh['winkel_min'], roh['winkel_schritt']
                scan.range_min, scan.range_max = 0.03, 25.0
                werte = np.array([np.nan if v is None else v for v in roh['entfernungen']])
                werte[roh['weit']] = np.inf
                scan.ranges = [float(v) for v in werte]
                sender['scan'].publish(scan)
                odom = Odometry()
                odom.header.stamp = stempel(t)
                odom.pose.pose.orientation.z = math.sin((gier - gier0) / 2.0)
                odom.pose.pose.orientation.w = math.cos((gier - gier0) / 2.0)
                sender['odom'].publish(odom)
                for name, daten, form in (('tiefe', b'\x89PNGtiefe', '16UC1; png'),
                                          ('bild', welt.foto(flaechen, kamera, x, y, gier),
                                           'jpeg; bgr8')):
                    bild = CompressedImage()
                    bild.header.frame_id = 'oak_rgb_camera_optical_frame'
                    bild.header.stamp = stempel(t + 0.01)
                    bild.format, bild.data = form, daten
                    sender[name].publish(bild)
                time.sleep(0.08)
            # ein letzter Scan, damit das letzte Bild abgeschlossen wird
            scan.header.stamp = stempel(t + 1.0)
            sender['scan'].publish(scan)
            time.sleep(0.5)
            fertig.set()

        faden = threading.Thread(target=spiele, daemon=True)
        faden.start()
        wahl = eingabe().parse_args([
            '--name', 'ros_probe', '--ausgabe', str(tmp_path), '--dauer', '30',
            '--bild-topic', '/kitest/rgb', '--tiefe-topic', '/kitest/tiefe',
            '--info-topic', '/kitest/info', '--scan-topic', '/kitest/scan',
            '--odom-topic', '/kitest/odom'])
        ordner = nehme_auf(wahl, halt=fertig.is_set)
        faden.join(timeout=5.0)
    finally:
        quelle.destroy_node()
        rclpy.shutdown()

    assert ordner is not None and ordner.parent == tmp_path
    runde = Blickrunde.lade(ordner)
    assert len(runde.aufnahmen) >= schritte - 2          # Bestes Bemühen: fast alle
    assert runde.kamera() == kamera
    assert runde.meta['quelle']['lidar_rahmen'] == 'laser_frame'
    assert runde.aufnahmen[0]['tiefe'].endswith('.png')
    # Montage wurde aus TF gelesen und stimmt mit dem Roboter überein
    assert runde.meta['montage']['quelle'] == 'tf'
    assert np.allclose(runde.boden_lidar(), lidar_montage(), atol=1e-6)
    assert np.allclose(runde.boden_kamera(), kamera_montage(), atol=1e-6)
    vorbereitung = bereite_vor(runde)
    assert vorbereitung.auswahl['vollstaendig']
    assert len(vorbereitung.oeffnungen) == 2
