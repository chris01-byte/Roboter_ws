"""Compression helpers and timing checks for the OAK semantic stream."""

from __future__ import annotations

from typing import Any, Iterable

import cv2
import numpy as np


class StreamCodecError(ValueError):
    """Raised when a frame cannot satisfy the semantic stream contract."""


def encode_rgb_jpeg(image: np.ndarray, quality: int = 80) -> bytes:
    """Encode a BGR uint8 image as JPEG."""
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise StreamCodecError('RGB muss ein HxWx3-uint8-Bild sein')
    if not 1 <= quality <= 100:
        raise StreamCodecError('jpeg_quality muss zwischen 1 und 100 liegen')
    ok, encoded = cv2.imencode(
        '.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise StreamCodecError('JPEG-Kompression fehlgeschlagen')
    return encoded.tobytes()


def decode_rgb_jpeg(payload: Any) -> np.ndarray:
    """Decode a JPEG payload into a BGR uint8 image."""
    encoded = np.frombuffer(bytes(payload), dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3:
        raise StreamCodecError('Ungueltiges JPEG-RGB-Bild')
    return image


def encode_depth_png(depth: np.ndarray, compression: int = 1) -> bytes:
    """Losslessly encode an aligned 16-bit depth image as PNG."""
    if depth.ndim != 2 or depth.dtype != np.uint16:
        raise StreamCodecError('Tiefe muss ein HxW-uint16-Bild sein')
    if not 0 <= compression <= 9:
        raise StreamCodecError('png_compression muss zwischen 0 und 9 liegen')
    ok, encoded = cv2.imencode(
        '.png', depth, [cv2.IMWRITE_PNG_COMPRESSION, int(compression)])
    if not ok:
        raise StreamCodecError('PNG-Tiefenkompression fehlgeschlagen')
    return encoded.tobytes()


def decode_depth_png(payload: Any) -> np.ndarray:
    """Decode a PNG payload and require lossless 16-bit depth."""
    encoded = np.frombuffer(bytes(payload), dtype=np.uint8)
    depth = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    if depth is None or depth.ndim != 2 or depth.dtype != np.uint16:
        raise StreamCodecError('Ungueltiges 16UC1-PNG-Tiefenbild')
    return depth


def stamp_seconds(stamp) -> float:
    """Convert a ROS builtin_interfaces/Time-like value to seconds."""
    return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def pair_is_publishable(
        *, now_s: float, rgb_received_s: float, depth_received_s: float,
        rgb_stamp_s: float, depth_stamp_s: float, max_age_s: float,
        max_skew_s: float) -> bool:
    """Accept only fresh RGB/depth pairs captured close enough together."""
    return pair_rejection_reason(
        now_s=now_s,
        rgb_received_s=rgb_received_s,
        depth_received_s=depth_received_s,
        rgb_stamp_s=rgb_stamp_s,
        depth_stamp_s=depth_stamp_s,
        max_age_s=max_age_s,
        max_skew_s=max_skew_s,
    ) is None


def pair_rejection_reason(
        *, now_s: float, rgb_received_s: float, depth_received_s: float,
        rgb_stamp_s: float, depth_stamp_s: float, max_age_s: float,
        max_skew_s: float) -> str | None:
    """Return a diagnostic reason, or ``None`` for an acceptable pair."""
    if max_age_s <= 0.0 or max_skew_s < 0.0:
        raise StreamCodecError('Zeitgrenzen sind ungueltig')
    if now_s - rgb_received_s > max_age_s:
        return 'stale_rgb'
    if now_s - depth_received_s > max_age_s:
        return 'stale_depth'
    if abs(rgb_stamp_s - depth_stamp_s) > max_skew_s:
        return 'timestamp_skew'
    return None


def select_freshest_pair(
        rgb_samples: Iterable[tuple[Any, float, float]],
        depth_samples: Iterable[tuple[Any, float, float]], *,
        now_s: float, max_age_s: float, max_skew_s: float,
        last_rgb_stamp_s: float | None = None):
    """Select the newest fresh RGB-D pair from bounded local sample queues.

    Each sample contains message, monotonic receive time and source stamp.
    A newer capture time wins; source skew is the tie breaker. DDS itself
    still uses depth-one Best-Effort queues, so this cannot create network
    backpressure.
    """
    if max_age_s <= 0.0 or max_skew_s < 0.0:
        raise StreamCodecError('Zeitgrenzen sind ungueltig')
    candidates = []
    for rgb in rgb_samples:
        if now_s - rgb[1] > max_age_s:
            continue
        if last_rgb_stamp_s is not None and rgb[2] == last_rgb_stamp_s:
            continue
        for depth in depth_samples:
            if now_s - depth[1] > max_age_s:
                continue
            skew = abs(rgb[2] - depth[2])
            if skew <= max_skew_s:
                capture_stamp = min(rgb[2], depth[2])
                candidates.append((capture_stamp, -skew, rgb, depth))
    if not candidates:
        return None
    _, _, rgb, depth = max(candidates, key=lambda item: (item[0], item[1]))
    return rgb, depth
