#!/usr/bin/env python3
# ============================================================================
#  vl53_near_field_node.py  -  WP-1b
#  ROS-2-Wrapper um den GETESTETEN Dual-VL53L7CX-Code (Heatmap-Logik, ohne GUI).
#  ---------------------------------------------------------------------------
#  Publiziert:
#    near_field/left/points    (sensor_msgs/PointCloud2, frame = frame_left)
#    near_field/right/points   (sensor_msgs/PointCloud2, frame = frame_right)
#    near_field/status         (robot_interfaces/NearFieldStatus, frame base_link)
#
#  Die Punktwolken speisen nav2_collision_monitor (+ local costmap),
#  der Status speist safety_monitor + Behavior-Tree.
#
#  WICHTIG - KALIBRIERUNG:
#    Die gesamte Mess-/Validitaets-/Orientierungslogik (FLIPX, Statusfilter,
#    sigma/nb_target-Filter, M[::-1,::-1], Zonen) ist 1:1 aus dem getesteten
#    Skript vl53_dual_heatmap.py uebernommen. NICHT im Code aendern!
#    Alle Werte sind ROS-Parameter -> in config/vl53_params.yaml anpassen
#    (dort steht oben ein Zeilen-Index zum schnellen Finden).
#
#  HARDWARE-TREIBER (via pip, wie in deinem Setup):
#    smbus2, numpy, und vl53l5cx ODER vl53l7cx
# ============================================================================

import math
import os
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from std_msgs.msg import Header
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from robot_interfaces.msg import NearFieldStatus

from smbus2 import SMBus

# Treiber-Import exakt wie im getesteten Skript (vl53l5cx ODER vl53l7cx).
try:
    from vl53l5cx.vl53l5cx import VL53L5CX as DRV
    # CH341A-USB-I2C uebertraegt nur ~32 Byte pro I2C-Transaktion. Sonst wird die
    # VL53-Firmware in einem 4096-Byte-Block geschrieben -> OSError(5)/EIO im init().
    import vl53l5cx.vl53l5cx as _vl53mod
    _vl53mod.VL53L5CX_COMMS_CHUNK_SIZE = 32
except Exception:  # pragma: no cover
    from vl53l7cx import VL53L7CX as DRV


class Vl53NearField(Node):
    def __init__(self):
        super().__init__('vl53_near_field')

        # -------------------------------------------------------------------
        #  Parameter deklarieren (Defaults = GETESTETE Werte).
        #  Ueberschreibbar via config/vl53_params.yaml.
        # -------------------------------------------------------------------
        self.declare_parameter('i2c_bus_num', 1)
        self.declare_parameter('mux_addr', 0x70)
        self.declare_parameter('sensor_addr', 0x29)
        self.declare_parameter('left_channel', 0)
        self.declare_parameter('right_channel', 1)
        self.declare_parameter('rate_hz', 10.0)
        self.declare_parameter('grid_r', 8)
        self.declare_parameter('grid_c', 8)
        self.declare_parameter('fov_deg', 60.0)
        self.declare_parameter('z_min', 0.01)
        self.declare_parameter('z_max', 0.50)
        self.declare_parameter('thresh_m', 0.25)
        self.declare_parameter('inner_cols', 4)
        self.declare_parameter('max_bad_frames', 3)
        self.declare_parameter('require_nb_target', True)
        self.declare_parameter('valid_statuses', [5])
        self.declare_parameter('min_signal_per_spad', 0.0)
        self.declare_parameter('max_sigma_mm', 50.0)
        self.declare_parameter('flipx_left', True)
        self.declare_parameter('flipx_right', False)
        self.declare_parameter('frame_left', 'vl53_left_link')
        self.declare_parameter('frame_right', 'vl53_right_link')

        gp = self.get_parameter
        self.bus_num = int(gp('i2c_bus_num').value)
        if self.bus_num < 0:                     # -1 = CH341-USB-I2C-Bus automatisch suchen
            self.bus_num = self._find_ch341_bus()
            self.get_logger().info(f'CH341-I2C-Bus automatisch erkannt: i2c-{self.bus_num}')
        self.mux_addr = int(gp('mux_addr').value)
        self.sensor_addr = int(gp('sensor_addr').value)
        self.ch_left = int(gp('left_channel').value)
        self.ch_right = int(gp('right_channel').value)
        self.rate_hz = float(gp('rate_hz').value)
        self.GR = int(gp('grid_r').value)
        self.GC = int(gp('grid_c').value)
        self.fov = float(gp('fov_deg').value)
        self.z_min = float(gp('z_min').value)
        self.z_max = float(gp('z_max').value)
        self.thresh = float(gp('thresh_m').value)
        self.inner = int(gp('inner_cols').value)
        self.max_bad = int(gp('max_bad_frames').value)
        self.require_nb = bool(gp('require_nb_target').value)
        self.valid_statuses = list(gp('valid_statuses').value)
        self.min_sps = float(gp('min_signal_per_spad').value)
        self.max_sigma = float(gp('max_sigma_mm').value)
        self.flipx_left = bool(gp('flipx_left').value)
        self.flipx_right = bool(gp('flipx_right').value)
        self.frame_left = str(gp('frame_left').value)
        self.frame_right = str(gp('frame_right').value)

        # -------------------------------------------------------------------
        #  I2C-Bus oeffnen + beide Sensoren starten
        # -------------------------------------------------------------------
        self.bus = SMBus(self.bus_num)
        self.bad = {self.ch_left: 0, self.ch_right: 0}
        self.get_logger().info('Starte VL53-Sensoren (links/rechts) ...')
        self.sL = self._sensor_start(self.ch_left)
        self.sR = self._sensor_start(self.ch_right)

        # -------------------------------------------------------------------
        #  Publisher
        # -------------------------------------------------------------------
        self.pub_left = self.create_publisher(
            PointCloud2, 'near_field/left/points', qos_profile_sensor_data)
        self.pub_right = self.create_publisher(
            PointCloud2, 'near_field/right/points', qos_profile_sensor_data)
        self.pub_status = self.create_publisher(
            NearFieldStatus, 'near_field/status', 10)

        # -------------------------------------------------------------------
        #  Winkel je Spalte (Azimut) / Zeile (Elevation) vorberechnen.
        #  Konvention (ROS REP-103): x=vorne, y=links(+), z=oben(+).
        #  plot_x: -FOV/2 (links) .. +FOV/2 (rechts)  ->  ROS-Azimut = -plot_x
        #  (passt zur Heatmap-Orientierung nach den FLIPX-Korrekturen).
        # -------------------------------------------------------------------
        self.col_az = np.radians(np.array(
            [-(-self.fov / 2.0 + (c + 0.5) / self.GC * self.fov) for c in range(self.GC)],
            dtype=np.float64))
        self.row_el = np.radians(np.array(
            [(-self.fov / 2.0 + (r + 0.5) / self.GR * self.fov) for r in range(self.GR)],
            dtype=np.float64))

        # -------------------------------------------------------------------
        #  Taktgeber (gleiche Rate wie die Sensoren)
        # -------------------------------------------------------------------
        self.timer = self.create_timer(1.0 / self.rate_hz, self._tick)
        self.get_logger().info('vl53_near_field laeuft.')

    # ======================= CH341-USB-I2C-Bus automatisch finden =======
    @staticmethod
    def _find_ch341_bus():
        import glob
        for d in sorted(glob.glob('/sys/class/i2c-adapter/i2c-*')):
            try:
                with open(os.path.join(d, 'name')) as f:
                    if any(x in f.read().lower() for x in ('ch34', 'mphsi')):
                        return int(os.path.basename(d).split('-')[1])
            except Exception:
                pass
        raise RuntimeError('Kein CH341/CH34x-I2C-Bus gefunden (WCH-Treiber geladen? lsmod | grep ch34x)')

    # ======================= MUX (TCA9548A) =============================
    def _mux_select(self, ch):
        # Genau EINEN Kanal durchschalten (beide Sensoren haben 0x29!).
        self.bus.write_byte(self.mux_addr, 1 << ch)
        time.sleep(0.001)

    def _mux_disable_all(self):
        self.bus.write_byte(self.mux_addr, 0x00)

    # ======================= Sensor-Start (faithful) ====================
    def _sensor_start(self, ch):
        self._mux_select(ch)
        # Konstruktor-Signatur je nach Treiber: Abstract-Horizon-VL53L5CX nimmt
        # bus_id=<Nummer>; andere Varianten i2c_bus/i2c_address. Reihenfolge = Praeferenz.
        s = None
        for kwargs in (dict(bus_id=self.bus_num),
                       dict(i2c_bus=self.bus_num, i2c_address=self.sensor_addr),
                       dict()):
            try:
                s = DRV(**kwargs)
                break
            except TypeError:
                continue
        if s is None:
            raise RuntimeError('VL53-Treiber liess sich nicht instanziieren')
        if hasattr(s, 'init'):
            s.init()
        elif hasattr(s, 'begin') and not s.begin():
            raise RuntimeError('begin() failed')
        for fn, arg in (('set_resolution', self.GR * self.GC),
                        ('set_ranging_frequency_hz', int(self.rate_hz))):
            if hasattr(s, fn):
                try:
                    getattr(s, fn)(arg)
                except Exception:
                    pass
        for fn in ('start_ranging', 'start'):
            if hasattr(s, fn):
                try:
                    getattr(s, fn)()
                except Exception:
                    pass
        return s

    def _stop_sensor(self, s, ch):
        self._mux_select(ch)
        for fn in ('stop_ranging', 'stop'):
            if hasattr(s, fn):
                try:
                    getattr(s, fn)()
                except Exception:
                    pass

    # ======================= Daten lesen (faithful) =====================
    def _get_data_safe(self, s, ch):
        self._mux_select(ch)
        for fn in ('check_data_ready', 'data_ready'):
            if hasattr(s, fn):
                try:
                    if not getattr(s, fn)():
                        return None
                except Exception:
                    pass
        try:
            if hasattr(s, 'get_ranging_data'):
                d = s.get_ranging_data()
                if d is None:
                    raise RuntimeError('get_ranging_data()->None')
                if not isinstance(d, dict):
                    d = {
                        'distance_mm': getattr(d, 'distance_mm', None),
                        'nb_target_detected': getattr(d, 'nb_target_detected', None),
                        'target_status': getattr(d, 'target_status', None),
                        'signal_per_spad': getattr(d, 'signal_per_spad', None),
                        'sigma_mm': getattr(d, 'sigma_mm', None),
                    }
            elif hasattr(s, 'get_data'):
                if not s.get_data():
                    return None
                d = {'distance_mm': getattr(s, 'distance_mm', None)}
            else:
                return None
            dist = d.get('distance_mm')
            if not dist or len(dist) != self.GR * self.GC:
                raise RuntimeError('unvollstaendiges Frame')
            self.bad[ch] = 0
            return d
        except Exception as e:
            # Fehlerbehandlung wie im Skript: nach MAX_BAD_FRAMES neu starten.
            self.bad[ch] += 1
            if self.bad[ch] >= self.max_bad:
                self.get_logger().warn(f'ch{ch}: {e} - Ranging neu starten ...')
                self._stop_sensor(s, ch)
                time.sleep(0.03)
                self._mux_select(ch)
                for fn in ('start_ranging', 'start'):
                    if hasattr(s, fn):
                        try:
                            getattr(s, fn)()
                        except Exception:
                            pass
                self.bad[ch] = 0
            return None

    # ======================= Matrix bauen (faithful) ====================
    def _build_matrix(self, d):
        M = np.array(d['distance_mm'], dtype=np.float32).reshape(self.GR, self.GC) * 1e-3
        M = M[::-1, ::-1]
        valid = (M >= self.z_min) & (M <= self.z_max)

        def ok(x):
            return (x is not None) and (len(x) == self.GR * self.GC)

        if self.require_nb and ok(d.get('nb_target_detected')):
            nbA = np.array(d['nb_target_detected'], dtype=np.int16).reshape(self.GR, self.GC)[::-1, ::-1]
            valid &= (nbA > 0)
        if ok(d.get('target_status')):
            stA = np.array(d['target_status'], dtype=np.int16).reshape(self.GR, self.GC)[::-1, ::-1]
            valid &= np.isin(stA, self.valid_statuses)
        if self.min_sps > 0 and ok(d.get('signal_per_spad')):
            spA = np.array(d['signal_per_spad'], dtype=np.float32).reshape(self.GR, self.GC)[::-1, ::-1]
            valid &= (spA >= self.min_sps)
        if self.max_sigma > 0 and ok(d.get('sigma_mm')):
            sgA = np.array(d['sigma_mm'], dtype=np.float32).reshape(self.GR, self.GC)[::-1, ::-1]
            valid &= (sgA <= self.max_sigma)
        M[~valid] = np.nan
        return M

    # ======================= Matrix -> PointCloud2 ======================
    def _matrix_to_cloud(self, M, frame_id, stamp):
        # Jede gueltige Zelle -> 3D-Punkt (Kugelkoordinaten aus Azimut/Elevation).
        pts = []
        for r in range(self.GR):
            el = self.row_el[r]
            cos_el = math.cos(el)
            sin_el = math.sin(el)
            for c in range(self.GC):
                dist = M[r, c]
                if not np.isfinite(dist):
                    continue
                az = self.col_az[c]
                x = dist * cos_el * math.cos(az)   # vorne
                y = dist * cos_el * math.sin(az)   # links +
                z = dist * sin_el                  # oben +
                pts.append((float(x), float(y), float(z)))
        header = Header()
        header.stamp = stamp
        header.frame_id = frame_id
        return point_cloud2.create_cloud_xyz32(header, pts)

    @staticmethod
    def _nanmin(A):
        # inf zurueckgeben, wenn die Zone leer/komplett ungueltig ist
        # (vermeidet die "All-NaN slice"-Warnung von np.nanmin).
        if A.size == 0 or not np.any(np.isfinite(A)):
            return np.inf
        return float(np.nanmin(A))

    # ======================= Haupttakt ==================================
    def _tick(self):
        dL = self._get_data_safe(self.sL, self.ch_left)
        dR = self._get_data_safe(self.sR, self.ch_right)
        if dL is None or dR is None:
            return

        ML = self._build_matrix(dL)
        MR = self._build_matrix(dR)
        # FLIPX wie im getesteten Skript (Orientierung links/rechts korrekt).
        if self.flipx_left:
            ML = ML[:, ::-1]
        if self.flipx_right:
            MR = MR[:, ::-1]

        # Zonen-Logik exakt wie im Skript.
        n = self.inner
        GC = self.GC
        left_zone = ML[:, :GC // 2]
        right_zone = MR[:, GC // 2:]
        mid_left = ML[:, GC - n:]
        mid_right = MR[:, :n]

        mL = self._nanmin(left_zone)
        mR = self._nanmin(right_zone)
        mML = self._nanmin(mid_left)
        mMR = self._nanmin(mid_right)

        stamp = self.get_clock().now().to_msg()

        # --- Status publizieren ---
        st = NearFieldStatus()
        st.header.stamp = stamp
        st.header.frame_id = 'base_link'
        st.left = bool(mL < self.thresh)
        st.right = bool(mR < self.thresh)
        st.middle = bool((mML < self.thresh) and (mMR < self.thresh))
        st.min_dist_left = float(mL) if np.isfinite(mL) else -1.0
        st.min_dist_right = float(mR) if np.isfinite(mR) else -1.0
        mmid = min(mML, mMR)
        st.min_dist_middle = float(mmid) if np.isfinite(mmid) else -1.0
        self.pub_status.publish(st)

        # --- Punktwolken publizieren (geflippte Matrizen -> Orientierung wie Status) ---
        self.pub_left.publish(self._matrix_to_cloud(ML, self.frame_left, stamp))
        self.pub_right.publish(self._matrix_to_cloud(MR, self.frame_right, stamp))

    # ======================= Aufraeumen =================================
    def destroy_node(self):
        try:
            self._stop_sensor(self.sL, self.ch_left)
            self._stop_sensor(self.sR, self.ch_right)
            self._mux_disable_all()
            self.bus.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Vl53NearField()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
