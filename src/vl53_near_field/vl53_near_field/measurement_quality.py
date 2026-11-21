"""VL53 frame quality before the near-range display filter.

The status is deliberately stricter than obstacle detection: a column may
clear a costmap ray only when every zone in that column has a valid return.
"""

import numpy as np


UNKNOWN = 0
VALID_NEAR = 1
VALID_FAR = 2
PARTIAL = 3
INVALID = 4
MAX_MEASURED_DISTANCE_M = 4.0  # VL53L5CX/L7CX specified ranging envelope


def assess_frame(data, rows, cols, valid_statuses, require_nb,
                 min_signal_per_spad, max_sigma_mm, z_min, z_max):
    """Return distances, valid zones, full-column mask, and frame quality.

    Missing quality fields are UNKNOWN. Rejected readings are INVALID or
    PARTIAL; a valid return beyond z_max is not a near obstacle, but still
    proves that direction was measured up to its actual returned distance.
    """
    shape = (rows, cols)
    empty = np.full(shape, np.nan, dtype=np.float32)
    none = np.zeros(shape, dtype=bool)
    if not isinstance(data, dict) or rows <= 0 or cols <= 0 or cols > 8:
        return empty, none, 0, UNKNOWN

    def array(name, dtype):
        value = data.get(name)
        try:
            if value is None or len(value) != rows * cols:
                return None
            return np.asarray(value, dtype=dtype).reshape(shape)[::-1, ::-1]
        except (TypeError, ValueError, OverflowError):
            return None

    distances = array('distance_mm', np.float32)
    statuses = array('target_status', np.int16)
    counts = array('nb_target_detected', np.int16) if require_nb else None
    signal = (array('signal_per_spad', np.float32)
              if min_signal_per_spad > 0 else None)
    sigma = array('sigma_mm', np.float32) if max_sigma_mm > 0 else None
    if (distances is None or statuses is None
            or (require_nb and counts is None)
            or (min_signal_per_spad > 0 and signal is None)
            or (max_sigma_mm > 0 and sigma is None)):
        return empty, none, 0, UNKNOWN

    distances *= 0.001
    valid = (np.isfinite(distances) & (distances >= z_min)
             & (distances <= MAX_MEASURED_DISTANCE_M)
             & np.isin(statuses, valid_statuses))
    if counts is not None:
        valid &= counts > 0
    if signal is not None:
        valid &= np.isfinite(signal) & (signal >= min_signal_per_spad)
    if sigma is not None:
        valid &= np.isfinite(sigma) & (sigma >= 0) & (sigma <= max_sigma_mm)
    observed = np.where(valid, distances, np.nan)
    full_columns = np.all(valid, axis=0)
    column_mask = sum(1 << col for col, full in enumerate(full_columns) if full)
    if np.all(valid):
        quality = VALID_NEAR if np.any(observed <= z_max) else VALID_FAR
    elif np.any(valid):
        quality = PARTIAL
    else:
        quality = INVALID
    return observed, valid, column_mask, quality
