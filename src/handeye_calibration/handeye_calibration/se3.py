# ============================================================================
#  se3.py  -  kleine SE(3)-Helfer fuer die Hand-Auge-Kalibrierung
#  ---------------------------------------------------------------------------
#  Nur numpy, keine ROS-/scipy-Abhaengigkeit: wird vom Recorder-Node UND vom
#  Offline-Loeser (handeye_solve) benutzt.
#
#  Konventionen:
#    T           = homogene 4x4-Matrix, "parent_T_child" wie in ROS-TF
#                  (bildet Kind-Koordinaten in den Eltern-Frame ab)
#    Quaternion  = (x, y, z, w)  wie geometry_msgs
#    rpy         = fixed-axis Roll/Pitch/Yaw wie in der URDF:
#                  R = Rz(yaw) @ Ry(pitch) @ Rx(roll)
# ============================================================================

import math

import numpy as np


# ======================= Quaternion <-> Matrix ==============================
def quat_to_mat(q):
    """(x, y, z, w) -> 3x3-Rotationsmatrix."""
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        return np.eye(3)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)],
    ])


def mat_to_quat(R):
    """3x3-Rotationsmatrix -> (x, y, z, w). Numerisch robuste Standardform."""
    R = np.asarray(R, dtype=float)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


# ======================= rpy (URDF, fixed-axis) =============================
def rpy_to_mat(roll, pitch, yaw):
    """URDF-Konvention: R = Rz(yaw) @ Ry(pitch) @ Rx(roll)."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def mat_to_rpy(R):
    """Rotationsmatrix -> (roll, pitch, yaw) in URDF-Konvention."""
    R = np.asarray(R, dtype=float)
    sp = -R[2, 0]
    sp = max(-1.0, min(1.0, sp))
    pitch = math.asin(sp)
    if abs(sp) > 0.999999:          # Gimbal-Naehe: yaw und roll entarten
        roll = math.atan2(-R[1, 2], R[1, 1])
        yaw = 0.0
    else:
        roll = math.atan2(R[2, 1], R[2, 2])
        yaw = math.atan2(R[1, 0], R[0, 0])
    return roll, pitch, yaw


# ======================= 4x4-Transformationen ===============================
def T_from_rt(R, t):
    T = np.eye(4)
    T[:3, :3] = np.asarray(R, dtype=float)
    T[:3, 3] = np.asarray(t, dtype=float).reshape(3)
    return T


def T_from_xyz_quat(xyz, quat_xyzw):
    return T_from_rt(quat_to_mat(quat_xyzw), xyz)


def invert_T(T):
    R = T[:3, :3]
    t = T[:3, 3]
    Ti = np.eye(4)
    Ti[:3, :3] = R.T
    Ti[:3, 3] = -R.T @ t
    return Ti


def rot_angle_deg(R):
    """Drehwinkel einer Rotationsmatrix in Grad (0..180)."""
    c = (np.trace(R) - 1.0) / 2.0
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def rel_rot_deg(Ta, Tb):
    """Relativer Drehwinkel zwischen zwei Posen in Grad."""
    return rot_angle_deg(Ta[:3, :3].T @ Tb[:3, :3])


def rel_trans_m(Ta, Tb):
    """Abstand der Positionen zweier Posen in Metern."""
    return float(np.linalg.norm(Ta[:3, 3] - Tb[:3, 3]))


# ======================= Mittelung ==========================================
def average_quaternions(quats):
    """Mittelt Quaternionen (x,y,z,w) ueber den groessten Eigenvektor von
    M = sum(q q^T). Vorzeichen werden am ersten Quaternion ausgerichtet."""
    A = np.zeros((4, 4))
    q0 = np.asarray(quats[0], dtype=float)
    for q in quats:
        q = np.asarray(q, dtype=float)
        if np.dot(q, q0) < 0.0:
            q = -q
        q = q / np.linalg.norm(q)
        A += np.outer(q, q)
    vals, vecs = np.linalg.eigh(A)
    q_mean = vecs[:, np.argmax(vals)]
    if np.dot(q_mean, q0) < 0.0:
        q_mean = -q_mean
    return q_mean / np.linalg.norm(q_mean)


def average_T(Ts):
    """Mittelt eine Liste von 4x4-Posen (Translation arithmetisch,
    Rotation ueber Quaternion-Mittel)."""
    ts = np.array([T[:3, 3] for T in Ts])
    qs = [mat_to_quat(T[:3, :3]) for T in Ts]
    return T_from_rt(quat_to_mat(average_quaternions(qs)), ts.mean(axis=0))


def spread_of_Ts(Ts):
    """(max. Translationsabstand [m], max. Drehwinkel [deg]) aller Posen
    gegenueber dem Mittel — Mass fuer 'steht wirklich still?'."""
    if len(Ts) < 2:
        return 0.0, 0.0
    Tm = average_T(Ts)
    dt = max(rel_trans_m(T, Tm) for T in Ts)
    dr = max(rel_rot_deg(T, Tm) for T in Ts)
    return dt, dr
