import csv
import importlib.util
import math
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / 'hwt601_ruherauschen_auswerten.py')
SPEC = importlib.util.spec_from_file_location('hwt601_noise', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_nice_ceiling_uses_one_two_five_series():
    assert MODULE._nice_ceiling(4.18e-7) == 5.0e-7
    assert MODULE._nice_ceiling(1.2e-7) == 2.0e-7


def test_analysis_reads_only_evaluation_rows_and_returns_positive_covariance(
        tmp_path):
    path = tmp_path / 'samples.csv'
    with path.open('w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(('evaluation_s', 'gx', 'gy', 'gz'))
        writer.writerow(('', 99.0, 99.0, 99.0))
        for index in range(200):
            writer.writerow((
                0.01 * index,
                0.001 + 0.0001 * math.sin(index),
                -0.002 + 0.0001 * math.cos(index),
                0.0002 + 0.00005 * math.sin(index / 3.0),
            ))

    result = MODULE.analyse(path)

    assert result['samples'] == 200
    assert 99.0 < result['rate_hz'] < 101.0
    assert result['gyro_covariance_rad2ps2'][2][2] > 0.0
    assert result['recommended_shadow_variance_rad2ps2'] > 0.0
