#!/usr/bin/env python3
# ============================================================================
#  handeye_solve.py  -  Hand-Auge-Loesung rechnen + URDF-Werte ausgeben
#  (Stufen E und F aus KONZEPT_KALIBRIERUNG_OAK_ARM.md, Eye-to-Hand)
#  ---------------------------------------------------------------------------
#  Laeuft OHNE ROS (nur OpenCV + numpy + yaml) — also auch offline am PC.
#
#  EINGABE : die YAML aus handeye_recorder (Paare base_T_tool / cam_T_board)
#  AUSGABE :
#    1) T(base_link -> camera_rgb_optical_frame)  — das Kalibrierergebnis
#    2) Residuen je Paar + Ausreisserfilter (> sigma) mit zweiter Loesung
#    3) T(tool0 -> board) als Nebenprodukt (Plausibilitaet der Halterung)
#    4) fertige URDF-/Xacro-Werte fuer den Kamera-Joint (base -> camera_link),
#       inkl. Rueckrechnung ueber die feste optische Drehung (rpy -90,0,-90)
#
#  MATHE-REZEPT (dokumentiert im OpenCV-Handbuch):
#    cv2.calibrateHandEye erwartet fuer Eye-in-Hand die Paare
#    (gripper2base, target2cam). Fuer EYE-TO-HAND uebergibt man stattdessen
#    die INVERTIERTEN Armposen (base2gripper) — das Ergebnis "cam2gripper"
#    ist dann cam2base, in ROS-Sprech: T(base_link -> camera_optical).
#
#  AUFRUF:
#    handeye_solve pfad/zu/handeye_pairs_XXXX.yaml
#    handeye_solve pairs.yaml --method park --outlier-sigma 3.0
# ============================================================================

import argparse
import math
import sys

import numpy as np
import yaml

import cv2

try:                                    # Paketkontext (ros2 run / installiert)
    from . import se3
except ImportError:                     # direkter Skriptaufruf
    import se3  # type: ignore

# Feste optische Drehung aus der URDF (camera_link -> camera_rgb_optical_frame)
OPTICAL_RPY = (-math.pi / 2.0, 0.0, -math.pi / 2.0)

METHODS = {
    'tsai':       cv2.CALIB_HAND_EYE_TSAI,
    'park':       cv2.CALIB_HAND_EYE_PARK,
    'horaud':     cv2.CALIB_HAND_EYE_HORAUD,
    'andreff':    cv2.CALIB_HAND_EYE_ANDREFF,
    'daniilidis': cv2.CALIB_HAND_EYE_DANIILIDIS,
}


# ======================= Laden ==============================================
def load_pairs(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    pairs = data.get('pairs', [])
    if len(pairs) < 5:
        sys.exit(f'FEHLER: nur {len(pairs)} Paare in {path} — '
                 'mindestens 5, empfohlen 15-25.')
    T_base_tool = [se3.T_from_xyz_quat(p['base_T_tool']['xyz'],
                                       p['base_T_tool']['quat_xyzw']) for p in pairs]
    T_cam_board = [se3.T_from_xyz_quat(p['cam_T_board']['xyz'],
                                       p['cam_T_board']['quat_xyzw']) for p in pairs]
    ids = [p.get('id', i + 1) for i, p in enumerate(pairs)]
    return data.get('meta', {}), ids, T_base_tool, T_cam_board


# ======================= Loesen =============================================
def solve(T_base_tool, T_cam_board, method_flag):
    """Eye-to-Hand: invertierte Armposen an calibrateHandEye -> base_T_cam."""
    R_b2g, t_b2g, R_t2c, t_t2c = [], [], [], []
    for Tbt, Tcb in zip(T_base_tool, T_cam_board):
        Tinv = se3.invert_T(Tbt)               # tool_T_base ("base2gripper")
        R_b2g.append(Tinv[:3, :3]); t_b2g.append(Tinv[:3, 3])
        R_t2c.append(Tcb[:3, :3]);  t_t2c.append(Tcb[:3, 3])
    R, t = cv2.calibrateHandEye(R_b2g, t_b2g, R_t2c, t_t2c, method=method_flag)
    return se3.T_from_rt(R, t.reshape(3))      # = base_T_cam_optical


def tool_T_board_per_pair(X, T_base_tool, T_cam_board):
    """Nebenprodukt je Paar: Y_i = inv(base_T_tool_i) @ X @ cam_T_board_i."""
    return [se3.invert_T(Tbt) @ X @ Tcb
            for Tbt, Tcb in zip(T_base_tool, T_cam_board)]


def residuals(X, Y, T_base_tool, T_cam_board):
    """Vergleicht beide Wege zum Board: base_T_tool_i @ Y  vs.  X @ cam_T_board_i.
    Rueckgabe: Liste (trans_mm, rot_deg) je Paar."""
    out = []
    for Tbt, Tcb in zip(T_base_tool, T_cam_board):
        delta = se3.invert_T(Tbt @ Y) @ (X @ Tcb)
        out.append((float(np.linalg.norm(delta[:3, 3])) * 1000.0,
                    se3.rot_angle_deg(delta[:3, :3])))
    return out


def solve_with_report(ids, T_base_tool, T_cam_board, method_name, sigma):
    X = solve(T_base_tool, T_cam_board, METHODS[method_name])
    Y = se3.average_T(tool_T_board_per_pair(X, T_base_tool, T_cam_board))
    res = residuals(X, Y, T_base_tool, T_cam_board)

    trans = np.array([r[0] for r in res])
    keep = list(range(len(res)))
    dropped = []
    if len(res) >= 10 and trans.std() > 1e-9:
        thr = trans.mean() + sigma * trans.std()
        keep = [i for i, v in enumerate(trans) if v <= thr]
        dropped = [i for i in range(len(res)) if i not in keep]
        if dropped:
            X = solve([T_base_tool[i] for i in keep],
                      [T_cam_board[i] for i in keep], METHODS[method_name])
            Y = se3.average_T(tool_T_board_per_pair(
                X, [T_base_tool[i] for i in keep],
                [T_cam_board[i] for i in keep]))
            res = residuals(X, Y, [T_base_tool[i] for i in keep],
                            [T_cam_board[i] for i in keep])
    return X, Y, res, keep, dropped


# ======================= Ausgabe ============================================
def fmt_T(T, label):
    xyz = T[:3, 3]
    r, p, y = se3.mat_to_rpy(T[:3, :3])
    q = se3.mat_to_quat(T[:3, :3])
    print(f'{label}')
    print(f'  xyz  [m]  : {xyz[0]:+.4f}  {xyz[1]:+.4f}  {xyz[2]:+.4f}')
    print(f'  rpy  [rad]: {r:+.5f}  {p:+.5f}  {y:+.5f}'
          f'   ({math.degrees(r):+.2f} / {math.degrees(p):+.2f} / '
          f'{math.degrees(y):+.2f} deg)')
    print(f'  quat xyzw : {q[0]:+.6f}  {q[1]:+.6f}  {q[2]:+.6f}  {q[3]:+.6f}')


def print_report(meta, ids, X, Y, res, keep, dropped, method_name):
    print('=' * 66)
    print('HAND-AUGE-LOESUNG (Eye-to-Hand)   Methode:', method_name)
    print('=' * 66)
    if meta:
        print(f"Datensatz: {meta.get('created', '?')}, "
              f"{meta.get('base_frame', 'base_link')} -> "
              f"{meta.get('tool_frame', 'tool0')}, "
              f"Kamera {meta.get('camera', {}).get('width', '?')}x"
              f"{meta.get('camera', {}).get('height', '?')}")
    print(f'Paare verwendet: {len(keep)}'
          + (f'  (Ausreisser entfernt: {[ids[i] for i in dropped]})' if dropped else ''))
    print()
    fmt_T(X, 'T(base_link -> camera_rgb_optical_frame)   << ERGEBNIS')
    print()
    fmt_T(Y, 'T(tool0 -> board)   (Nebenprodukt, Plausibilitaet der Halterung)')
    print()

    trans = np.array([r[0] for r in res]); rot = np.array([r[1] for r in res])
    print('Residuen (beide Rechenwege zum Board verglichen):')
    print(f'  Translation: RMS {np.sqrt((trans**2).mean()):6.2f} mm | '
          f'Mittel {trans.mean():6.2f} | max {trans.max():6.2f}')
    print(f'  Rotation   : RMS {np.sqrt((rot**2).mean()):6.3f} deg | '
          f'Mittel {rot.mean():6.3f} | max {rot.max():6.3f}')
    ok = np.sqrt((trans**2).mean()) <= 5.0 and np.sqrt((rot**2).mean()) <= 0.5
    print(f'  Abnahme Stufe E (<= 5 mm / <= 0.5 deg RMS): '
          f'{"ERFUELLT" if ok else "NICHT erfuellt — Posenvielfalt/Stufe A pruefen!"}')
    print()

    # ---- Stufe F: Rueckrechnung auf den URDF-Kamera-Joint ------------------
    T_cl_opt = se3.T_from_rt(se3.rpy_to_mat(*OPTICAL_RPY), [0.0, 0.0, 0.0])
    T_base_cl = X @ se3.invert_T(T_cl_opt)     # base -> camera_link (mechanisch)
    xyz = T_base_cl[:3, 3]
    r, p, y = se3.mat_to_rpy(T_base_cl[:3, :3])
    print('URDF-Werte fuer den Joint base_link -> camera_link (Stufe F):')
    print('  (Kamera-Joint in mobile_manipulator_dummy.urdf.xacro auf volle')
    print('   rpy erweitern und diese Werte eintragen — Marker [KALIBRIERT])')
    print(f'    <xacro:property name="oak_x"     value="{xyz[0]:.4f}"/>')
    print(f'    <xacro:property name="oak_y"     value="{xyz[1]:.4f}"/>')
    print(f'    <xacro:property name="oak_z"     value="{xyz[2]:.4f}"/>')
    print(f'    <xacro:property name="oak_roll"  value="{r:.5f}"/>')
    print(f'    <xacro:property name="oak_pitch" value="{p:.5f}"/>')
    print(f'    <xacro:property name="oak_yaw"   value="{y:.5f}"/>')
    print()
    q = se3.mat_to_quat(X[:3, :3]); t = X[:3, 3]
    print('Nur zum schnellen TESTEN (URDF bleibt die einzige Quelle!):')
    print(f'  ros2 run tf2_ros static_transform_publisher '
          f'{t[0]:.4f} {t[1]:.4f} {t[2]:.4f} '
          f'{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f} '
          f'base_link camera_rgb_optical_frame')
    print('=' * 66)


# ======================= main ===============================================
def main():
    ap = argparse.ArgumentParser(
        description='Hand-Auge-Kalibrierung loesen (Eye-to-Hand, Stufe E/F).')
    ap.add_argument('pairs_yaml', help='YAML aus handeye_recorder')
    ap.add_argument('--method', default='park',
                    choices=sorted(METHODS) + ['all'],
                    help='Loeser (Default: park). "all" = Methodenvergleich.')
    ap.add_argument('--outlier-sigma', type=float, default=3.0,
                    help='Ausreisserschwelle in Standardabweichungen (Default 3).')
    args = ap.parse_args()

    meta, ids, T_base_tool, T_cam_board = load_pairs(args.pairs_yaml)

    if args.method == 'all':
        # Methodenvergleich: Streuung der Ergebnisse = Sanity-Indikator.
        print('Methodenvergleich (Translation des Ergebnisses in m):')
        results = {}
        for name in sorted(METHODS):
            try:
                Xm = solve(T_base_tool, T_cam_board, METHODS[name])
                results[name] = Xm
                t = Xm[:3, 3]
                print(f'  {name:10s}: {t[0]:+.4f} {t[1]:+.4f} {t[2]:+.4f}')
            except cv2.error as exc:
                print(f'  {name:10s}: fehlgeschlagen ({exc})')
        if len(results) >= 2:
            pos = np.array([X[:3, 3] for X in results.values()])
            spread = np.linalg.norm(pos.max(axis=0) - pos.min(axis=0)) * 1000.0
            print(f'  Streuung zwischen den Methoden: {spread:.1f} mm '
                  '(gross = Datensatz schlecht konditioniert)')
        print()
        chosen = 'park' if 'park' in results else sorted(results)[0]
    else:
        chosen = args.method

    X, Y, res, keep, dropped = solve_with_report(
        ids, T_base_tool, T_cam_board, chosen, args.outlier_sigma)
    print_report(meta, ids, X, Y, res, keep, dropped, chosen)


if __name__ == '__main__':
    main()
