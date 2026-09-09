#!/usr/bin/env python3
"""Reproduce HWT601 stationary gyro covariance without touching hardware."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def _nice_ceiling(value: float) -> float:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError('Varianz muss endlich und positiv sein')
    exponent = math.floor(math.log10(value))
    scale = 10.0 ** exponent
    normalized = value / scale
    for step in (1.0, 2.0, 5.0, 10.0):
        if normalized <= step:
            return step * scale
    raise AssertionError('unerreichbar')


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def analyse(path: Path) -> dict:
    rows = []
    with path.open(newline='') as file:
        for row in csv.DictReader(file):
            if not row.get('evaluation_s'):
                continue
            rows.append(tuple(
                float(row[key]) for key in ('evaluation_s', 'gx', 'gy', 'gz')))
    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or data.shape[0] < 100 or data.shape[1] != 4:
        raise ValueError('zu wenige gueltige Evaluationsproben')
    if not np.isfinite(data).all():
        raise ValueError('Datensatz enthaelt NaN oder Inf')

    time_s = data[:, 0]
    gyro = data[:, 1:]
    gaps = np.diff(time_s)
    if np.any(gaps <= 0.0):
        raise ValueError('Zeitstempel sind nicht streng monoton')
    duration_s = float(time_s[-1] - time_s[0])
    rate_hz = float((len(time_s) - 1) / duration_s)
    covariance = np.cov(gyro, rowvar=False, ddof=1)

    centered_time = time_s - np.mean(time_s)
    design = np.column_stack((np.ones(len(time_s)), centered_time))
    fit = design @ np.linalg.lstsq(design, gyro[:, 2], rcond=None)[0]
    z_residual = gyro[:, 2] - fit
    z_variance = float(np.mean(z_residual * z_residual))

    autocorrelation = {}
    for lag in (1, 2, 3, 4, 5, 10, 20, 50, 100):
        autocorrelation[str(lag)] = float(np.mean(
            z_residual[:-lag] * z_residual[lag:]) / z_variance)

    nominal_rate_hz = int(round(rate_hz))
    effective_variance = {}
    for horizon_s in (0.1, 1.0, 10.0, 30.0, 60.0, 100.0):
        block_size = max(1, int(round(horizon_s * nominal_rate_hz)))
        blocks = len(z_residual) // block_size
        if blocks < 2:
            continue
        means = z_residual[:blocks * block_size].reshape(
            blocks, block_size).mean(axis=1)
        effective_variance[str(horizon_s)] = float(
            block_size * np.var(means, ddof=1))

    conservative_basis = max(
        float(np.max(np.diag(covariance))),
        max(effective_variance.values()),
    )
    recommendation = _nice_ceiling(conservative_basis)
    return {
        'source': str(path),
        'sha256': _sha256(path),
        'samples': int(len(time_s)),
        'duration_s': duration_s,
        'rate_hz': rate_hz,
        'maximum_gap_s': float(np.max(gaps)),
        'gyro_mean_radps_xyz': gyro.mean(axis=0).tolist(),
        'gyro_stddev_radps_xyz': gyro.std(axis=0, ddof=1).tolist(),
        'gyro_covariance_rad2ps2': covariance.tolist(),
        'z_linear_detrended_variance_rad2ps2': z_variance,
        'z_autocorrelation_by_lag_samples': autocorrelation,
        'z_effective_variance_by_horizon_s': effective_variance,
        'recommended_shadow_variance_rad2ps2': recommendation,
        'scope': (
            'warm_stationary_shadow_only; no temperature, cold-start or '
            'motor-vibration validation'),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='HWT601-Ruherauschen aus bestehender CSV auswerten')
    parser.add_argument('samples_csv', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyse(args.samples_csv), indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
