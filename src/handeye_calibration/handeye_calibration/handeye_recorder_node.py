#!/usr/bin/env python3
# ============================================================================
#  handeye_recorder_node.py  -  Messpaare fuer die Hand-Auge-Kalibrierung
#  (Stufe D aus KONZEPT_KALIBRIERUNG_OAK_ARM.md, Variante Eye-to-Hand)
#  ---------------------------------------------------------------------------
#  ZWECK:
#    Sammelt Paare aus
#      (1) Armpose      T(base_link -> tool0)             aus TF, und
#      (2) Boardpose    T(camera -> charuco_board)        aus dem Kamerabild
#    bei STEHENDEM Arm. Die Paare landen fortlaufend (absturzsicher) in einer
#    YAML-Datei, die anschliessend handeye_solve loest (Stufe E).
#
#  BEDIENUNG (Terminal, Node laeuft im Vordergrund):
#      ENTER oder s   = Paar aufnehmen (mittelt mehrere Frames)
#      u              = letztes Paar verwerfen
#      d              = Vielfalts-/Qualitaetsbericht anzeigen
#      q              = Bericht + beenden (Datei ist bereits gespeichert)
#
#  KONTROLLBILD:
#    Publiziert ein annotiertes Bild auf <debug_image_topic> (Standard
#    /handeye/debug_image) -> im Browser via rosbridge, rqt_image_view oder
#    RViz ansehen. Optional lokales Fenster mit show_window:=true (Desktop).
#
#  VORAUSSETZUNGEN (Stufen A-C des Konzepts):
#    - /joint_states + robot_state_publisher liefern TF base_frame -> tool_frame
#      (echtes Armmodell! Der Arm ist das Messgerät.)
#    - Kameratreiber publiziert Bild + CameraInfo (gleiche Aufloesung wie
#      spaeter im Betrieb).
#    - ChArUco-Board STARR am Flansch, Feldmass nachgemessen (-> YAML).
#
#  ALLE PARAMETER -> config/handeye_params.yaml (nur dort aendern!).
#
#  HINWEIS: Wie die uebrigen Pakete noch nicht in einer ROS-Umgebung
#  kompiliert/getestet (py_compile bestanden). OpenCV-Ziel: 4.5.x (Ubuntu
#  22.04 apt); fuer OpenCV >= 4.7 sind Kompatibilitaetspfade eingebaut.
# ============================================================================

import os
import queue
import sys
import threading
import time
from datetime import datetime

import numpy as np
import yaml

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image, CameraInfo

import tf2_ros
from cv_bridge import CvBridge

import cv2

from . import se3

ARUCO = cv2.aruco


# ======================= ChArUco-Kompatibilitaetsschicht ====================
class CharucoDetector:
    """Kapselt die API-Unterschiede zwischen OpenCV <=4.6 und >=4.7.

    Liefert fuer ein Graubild: (rvec, tvec, n_ecken, reproj_rms_px) oder None.
    """

    def __init__(self, squares_x, squares_y, square_len_m, marker_len_m,
                 dict_name, min_corners):
        dict_id = getattr(ARUCO, dict_name)
        if hasattr(ARUCO, 'getPredefinedDictionary'):
            self.dictionary = ARUCO.getPredefinedDictionary(dict_id)
        else:  # sehr alte API
            self.dictionary = ARUCO.Dictionary_get(dict_id)

        if hasattr(ARUCO, 'CharucoBoard_create'):      # OpenCV <= 4.6 (22.04)
            self.board = ARUCO.CharucoBoard_create(
                squares_x, squares_y, square_len_m, marker_len_m, self.dictionary)
            self._new_api = False
        else:                                          # OpenCV >= 4.7
            self.board = ARUCO.CharucoBoard(
                (squares_x, squares_y), square_len_m, marker_len_m, self.dictionary)
            self._charuco_detector = ARUCO.CharucoDetector(self.board)
            self._new_api = True

        self.min_corners = int(min_corners)

    # ------------------------------------------------------------------
    def detect(self, gray, K, D, draw_on=None):
        if self._new_api:
            ch_corners, ch_ids, mk_corners, mk_ids = \
                self._charuco_detector.detectBoard(gray)
        else:
            mk_corners, mk_ids, _ = ARUCO.detectMarkers(gray, self.dictionary)
            ch_corners, ch_ids = None, None
            if mk_ids is not None and len(mk_ids) > 0:
                _, ch_corners, ch_ids = ARUCO.interpolateCornersCharuco(
                    mk_corners, mk_ids, gray, self.board)

        if draw_on is not None and mk_ids is not None and len(mk_ids) > 0:
            ARUCO.drawDetectedMarkers(draw_on, mk_corners, mk_ids)

        if ch_ids is None or len(ch_ids) < self.min_corners:
            return None

        # --- Pose bestimmen -------------------------------------------------
        if not self._new_api and hasattr(ARUCO, 'estimatePoseCharucoBoard'):
            ok, rvec, tvec = ARUCO.estimatePoseCharucoBoard(
                ch_corners, ch_ids, self.board, K, D, None, None)
            if not ok:
                return None
            obj = self.board.chessboardCorners[ch_ids.flatten()]
            img = ch_corners.reshape(-1, 2)
        else:
            obj, img = self.board.matchImagePoints(ch_corners, ch_ids)
            if obj is None or len(obj) < self.min_corners:
                return None
            ok, rvec, tvec = cv2.solvePnP(obj, img, K, D)
            if not ok:
                return None
            obj = obj.reshape(-1, 3)
            img = img.reshape(-1, 2)

        # --- Reprojektionsfehler (Qualitaetsmass) ---------------------------
        proj, _ = cv2.projectPoints(obj.reshape(-1, 1, 3), rvec, tvec, K, D)
        err = np.linalg.norm(proj.reshape(-1, 2) - img.reshape(-1, 2), axis=1)
        rms = float(np.sqrt(np.mean(err ** 2)))

        if draw_on is not None:
            cv2.drawFrameAxes(draw_on, K, D, rvec, tvec, 0.05)

        return rvec, tvec, int(len(ch_ids)), rms


# ======================= Recorder-Node ======================================
class HandeyeRecorder(Node):
    def __init__(self):
        super().__init__('handeye_recorder')

        # -------------------------------------------------------------------
        #  Parameter (Defaults; Override via config/handeye_params.yaml)
        # -------------------------------------------------------------------
        gp = lambda n, d: self.declare_parameter(n, d).value
        self.image_topic  = str(gp('image_topic', '/oak/rgb/image_raw'))
        self.info_topic   = str(gp('camera_info_topic', '/oak/rgb/camera_info'))
        self.base_frame   = str(gp('base_frame', 'base_link'))
        self.tool_frame   = str(gp('tool_frame', 'tool0'))

        squares_x   = int(gp('board.squares_x', 7))
        squares_y   = int(gp('board.squares_y', 5))
        square_len  = float(gp('board.square_len_m', 0.030))
        marker_len  = float(gp('board.marker_len_m', 0.022))
        dict_name   = str(gp('board.aruco_dict', 'DICT_5X5_250'))
        min_corners = int(gp('board.min_corners', 12))

        self.frames_per_capture = int(gp('capture.frames_per_capture', 8))
        self.capture_timeout_s  = float(gp('capture.timeout_s', 6.0))
        self.max_board_spread_m   = float(gp('capture.max_board_spread_m', 0.002))
        self.max_board_spread_deg = float(gp('capture.max_board_spread_deg', 0.4))
        self.max_tool_spread_m    = float(gp('capture.max_tool_spread_m', 0.001))
        self.max_tool_spread_deg  = float(gp('capture.max_tool_spread_deg', 0.2))
        self.sim_warn_rot_deg   = float(gp('quality.similarity_warn_rot_deg', 5.0))
        self.sim_warn_trans_m   = float(gp('quality.similarity_warn_trans_m', 0.05))
        self.target_spread_deg  = float(gp('quality.target_rotation_spread_deg', 30.0))

        self.process_every_n = max(1, int(gp('process_every_n_frames', 2)))
        self.show_window     = bool(gp('show_window', False))
        debug_topic          = str(gp('debug_image_topic', '/handeye/debug_image'))

        out_dir = os.path.expanduser(str(gp('output_dir', '~/handeye_data')))
        session = str(gp('session_name', '')) or datetime.now().strftime('%Y%m%d_%H%M%S')
        os.makedirs(out_dir, exist_ok=True)
        self.out_file = os.path.join(out_dir, f'handeye_pairs_{session}.yaml')

        # -------------------------------------------------------------------
        #  Zustand
        # -------------------------------------------------------------------
        self.bridge = CvBridge()
        self.detector = CharucoDetector(squares_x, squares_y, square_len,
                                        marker_len, dict_name, min_corners)
        self.board_meta = dict(squares_x=squares_x, squares_y=squares_y,
                               square_len_m=square_len, marker_len_m=marker_len,
                               aruco_dict=dict_name)
        self.K = None                # 3x3 Kameramatrix (aus CameraInfo)
        self.D = None                # Verzeichnung
        self.cam_meta = {}
        self.pairs = []              # gespeicherte Messpaare (dict)
        self.frame_count = 0
        self.last_status = 'warte auf Bilder ...'

        # Aufnahme-Zustandsmaschine (wird im Bild-Callback abgearbeitet)
        self.collecting = False
        self.collect_deadline = 0.0
        self.buf_board = []          # 4x4 cam_T_board je Frame
        self.buf_tool = []           # 4x4 base_T_tool je Frame
        self.buf_corners = []
        self.buf_rms = []

        # -------------------------------------------------------------------
        #  ROS-Schnittstellen
        # -------------------------------------------------------------------
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.create_subscription(Image, self.image_topic, self._on_image,
                                 qos_profile_sensor_data)
        self.create_subscription(CameraInfo, self.info_topic, self._on_info,
                                 qos_profile_sensor_data)
        self.debug_pub = self.create_publisher(Image, debug_topic, 1)

        # Tastatur (stdin) in eigenem Thread -> Kommando-Queue
        self.cmds = queue.Queue()
        threading.Thread(target=self._stdin_loop, daemon=True).start()
        self.create_timer(0.1, self._process_commands)

        self._print_help()
        self.get_logger().info(
            f"handeye_recorder bereit. Bild='{self.image_topic}', "
            f"TF {self.base_frame} -> {self.tool_frame}, Ausgabe: {self.out_file}")

    # ======================= Eingaenge ==================================
    def _on_info(self, msg: CameraInfo):
        if self.K is None:
            self.K = np.array(msg.k, dtype=float).reshape(3, 3)
            self.D = np.array(msg.d, dtype=float)
            self.cam_meta = dict(width=int(msg.width), height=int(msg.height),
                                 distortion_model=msg.distortion_model,
                                 k=[float(v) for v in msg.k],
                                 d=[float(v) for v in msg.d])
            self.get_logger().info(
                f"CameraInfo empfangen ({msg.width}x{msg.height}, "
                f"Modell '{msg.distortion_model}').")

    def _on_image(self, msg: Image):
        self.frame_count += 1
        if self.frame_count % self.process_every_n != 0:
            return
        if self.K is None:
            return

        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        det = self.detector.detect(gray, self.K, self.D, draw_on=frame)

        if det is None:
            self.last_status = 'Board NICHT (vollstaendig) erkannt'
        else:
            rvec, tvec, n, rms = det
            self.last_status = (f'Board ok: {n} Ecken, RMS {rms:.2f} px, '
                                f'Abstand {float(np.linalg.norm(tvec)):.2f} m')
            if self.collecting:
                self._collect_frame(rvec, tvec, n, rms)

        self._publish_debug(frame)
        if self.show_window:
            cv2.imshow('handeye_recorder', frame)
            cv2.waitKey(1)

    # ======================= Aufnahme-Logik =============================
    def _collect_frame(self, rvec, tvec, n_corners, rms):
        # Armpose zum (nahezu) gleichen Zeitpunkt holen; Arm steht ohnehin.
        T_tool = self._lookup_tool()
        if T_tool is None:
            return
        R, _ = cv2.Rodrigues(rvec)
        self.buf_board.append(se3.T_from_rt(R, tvec.reshape(3)))
        self.buf_tool.append(T_tool)
        self.buf_corners.append(n_corners)
        self.buf_rms.append(rms)

        if len(self.buf_board) >= self.frames_per_capture:
            self._finish_capture()
        elif time.monotonic() > self.collect_deadline:
            print(f'[Aufnahme] Zeitueberschreitung: nur {len(self.buf_board)} '
                  f'gueltige Frames — Paar verworfen. Licht/Sicht pruefen.')
            self._reset_capture()

    def _finish_capture(self):
        self.collecting = False
        board_dt, board_dr = se3.spread_of_Ts(self.buf_board)
        tool_dt, tool_dr = se3.spread_of_Ts(self.buf_tool)

        # Stillstand pruefen: wackelt Board ODER Arm, ist das Paar wertlos.
        if board_dt > self.max_board_spread_m or board_dr > self.max_board_spread_deg:
            print(f'[Aufnahme] Board wackelt (Streuung {board_dt*1000:.1f} mm / '
                  f'{board_dr:.2f} deg) — Paar verworfen. Stillstand abwarten.')
            self._reset_capture()
            return
        if tool_dt > self.max_tool_spread_m or tool_dr > self.max_tool_spread_deg:
            print(f'[Aufnahme] Arm-TF nicht stabil (Streuung {tool_dt*1000:.1f} mm / '
                  f'{tool_dr:.2f} deg) — Paar verworfen.')
            self._reset_capture()
            return

        pair = dict(
            id=len(self.pairs) + 1,
            base_T_tool=self._T_to_yaml(se3.average_T(self.buf_tool)),
            cam_T_board=self._T_to_yaml(se3.average_T(self.buf_board)),
            quality=dict(frames=len(self.buf_board),
                         corners_mean=float(np.mean(self.buf_corners)),
                         reproj_rms_px=float(np.mean(self.buf_rms)),
                         board_spread_mm=round(board_dt * 1000.0, 3),
                         board_spread_deg=round(board_dr, 3)),
        )
        self.pairs.append(pair)
        self._save()
        print(f'[OK] Paar #{pair["id"]} gespeichert '
              f'({pair["quality"]["frames"]} Frames, '
              f'RMS {pair["quality"]["reproj_rms_px"]:.2f} px).')
        self._warn_if_similar()
        self._reset_capture()

    def _reset_capture(self):
        self.collecting = False
        self.buf_board, self.buf_tool = [], []
        self.buf_corners, self.buf_rms = [], []

    def _lookup_tool(self):
        try:
            tr = self.tf_buffer.lookup_transform(
                self.base_frame, self.tool_frame, rclpy.time.Time())
        except Exception as exc:
            print(f'[TF] {self.base_frame} -> {self.tool_frame} fehlt: {exc}')
            return None
        t = tr.transform.translation
        q = tr.transform.rotation
        return se3.T_from_xyz_quat([t.x, t.y, t.z], [q.x, q.y, q.z, q.w])

    # ======================= Qualitaet / Vielfalt =======================
    def _warn_if_similar(self):
        """Warnt, wenn das neue Paar einem vorhandenen fast gleicht."""
        if len(self.pairs) < 2:
            return
        Tn = self._T_from_yaml(self.pairs[-1]['base_T_tool'])
        for p in self.pairs[:-1]:
            Tj = self._T_from_yaml(p['base_T_tool'])
            if (se3.rel_rot_deg(Tn, Tj) < self.sim_warn_rot_deg and
                    se3.rel_trans_m(Tn, Tj) < self.sim_warn_trans_m):
                print(f'[WARNUNG] Paar #{self.pairs[-1]["id"]} ist fast identisch '
                      f'mit Paar #{p["id"]} — bringt der Loesung nichts. '
                      f'Naechste Pose deutlich anders waehlen (kippen!).')
                return

    def _diversity_report(self):
        n = len(self.pairs)
        print(f'--- Bericht: {n} Paare, Datei {self.out_file} ---')
        if n < 2:
            print('Noch zu wenige Paare fuer eine Bewertung (Ziel: 15-25).')
            return
        Ts = [self._T_from_yaml(p['base_T_tool']) for p in self.pairs]
        rots, dists = [], []
        for i in range(n):
            for j in range(i + 1, n):
                rots.append(se3.rel_rot_deg(Ts[i], Ts[j]))
                dists.append(se3.rel_trans_m(Ts[i], Ts[j]))
        pos = np.array([T[:3, 3] for T in Ts])
        bbox = (pos.max(axis=0) - pos.min(axis=0)) * 1000.0
        rms = [p['quality']['reproj_rms_px'] for p in self.pairs]
        print(f'Rotations-Spannweite : max {max(rots):.1f} deg '
              f'(Ziel >= {self.target_spread_deg:.0f} deg um zwei Achsen)')
        print(f'Positions-Streuung   : {bbox[0]:.0f} x {bbox[1]:.0f} x {bbox[2]:.0f} mm')
        print(f'Reprojektions-RMS    : Mittel {np.mean(rms):.2f} px, max {max(rms):.2f} px')
        if max(rots) < self.target_spread_deg:
            print('[WARNUNG] Zu wenig Rotationsvielfalt — Board staerker kippen, '
                  'sonst wird die Loesung schlecht konditioniert.')
        if n < 15:
            print(f'[Hinweis] Erst {n} Paare — Ziel sind 15-25.')

    # ======================= Ausgabe ====================================
    @staticmethod
    def _T_to_yaml(T):
        q = se3.mat_to_quat(T[:3, :3])
        return dict(xyz=[round(float(v), 6) for v in T[:3, 3]],
                    quat_xyzw=[round(float(v), 8) for v in q])

    @staticmethod
    def _T_from_yaml(d):
        return se3.T_from_xyz_quat(d['xyz'], d['quat_xyzw'])

    def _save(self):
        data = dict(
            meta=dict(created=datetime.now().isoformat(timespec='seconds'),
                      setup='eye_to_hand (Kamera fest an base, Board am Flansch)',
                      base_frame=self.base_frame, tool_frame=self.tool_frame,
                      image_topic=self.image_topic, board=self.board_meta,
                      camera=self.cam_meta),
            pairs=self.pairs,
        )
        with open(self.out_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def _publish_debug(self, frame):
        cv2.putText(frame, f'Paare: {len(self.pairs)}  |  {self.last_status}',
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if self.collecting:
            cv2.putText(frame, f'AUFNAHME {len(self.buf_board)}/{self.frames_per_capture}',
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        try:
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
        except Exception:
            pass

    # ======================= Bedienung ==================================
    def _stdin_loop(self):
        for line in sys.stdin:
            self.cmds.put(line.strip().lower())

    def _process_commands(self):
        try:
            cmd = self.cmds.get_nowait()
        except queue.Empty:
            return
        if cmd in ('', 's'):
            if self.K is None:
                print('[Aufnahme] Noch keine CameraInfo empfangen.')
                return
            if self.collecting:
                print('[Aufnahme] Laeuft bereits ...')
                return
            print(f'[Aufnahme] Sammle {self.frames_per_capture} Frames — '
                  'Arm und Board ruhig halten ...')
            self._reset_capture()
            self.collecting = True
            self.collect_deadline = time.monotonic() + self.capture_timeout_s
        elif cmd == 'u':
            if self.pairs:
                dropped = self.pairs.pop()
                self._save()
                print(f'[Rueckgaengig] Paar #{dropped["id"]} verworfen.')
            else:
                print('[Rueckgaengig] Keine Paare vorhanden.')
        elif cmd == 'd':
            self._diversity_report()
        elif cmd == 'q':
            self._diversity_report()
            print(f'Fertig. Naechster Schritt (Stufe E):\n'
                  f'  handeye_solve {self.out_file}')
            rclpy.shutdown()
        else:
            self._print_help()

    @staticmethod
    def _print_help():
        print('--------------------------------------------------------')
        print(' handeye_recorder — Tasten (mit ENTER bestaetigen):')
        print('   ENTER / s : Paar aufnehmen (Arm vorher stillhalten!)')
        print('   u         : letztes Paar verwerfen')
        print('   d         : Vielfalts-/Qualitaetsbericht')
        print('   q         : Bericht anzeigen und beenden')
        print(' Empfehlung: 15-25 Posen, Board um >=30 deg um zwei')
        print(' Achsen kippen, jede Pose aus derselben Richtung anfahren.')
        print('--------------------------------------------------------')


def main(args=None):
    rclpy.init(args=args)
    node = HandeyeRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
