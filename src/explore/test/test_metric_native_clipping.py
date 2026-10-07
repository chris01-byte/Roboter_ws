"""Built clipping matches the complete NumPy oracle, including contact vertices."""
import numpy as np
import pytest
import explore.metric_frontier as geometry
from test_metric_native_sweep import native


def same(polygon, cells):
    actual = geometry._cell_intersections(polygon, cells)
    expected = geometry._cell_intersections_full(polygon, cells)
    for a, b in zip(actual, expected):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize('scale', [.01, 1., 100., 10000.])
@pytest.mark.parametrize('shared', [False, True])
def test_exact_rotated_intersections(native, scale, shared):
    rng = np.random.default_rng(227)
    n = 1200
    angles = rng.uniform(-np.pi, np.pi, n)
    base = np.array([[-.13, -.25], [.33, -.25], [.33, .25], [-.13, .25]]) * scale
    co, si = np.cos(angles), np.sin(angles)
    polygon = np.stack((base[:, 0]*co[:, None]-base[:, 1]*si[:, None],
                       base[:, 0]*si[:, None]+base[:, 1]*co[:, None]), axis=2)
    polygon += rng.uniform(-10000., 10000., (n, 1, 2))
    cells = np.floor(polygon[:, 0, ::-1]).astype(np.int64)
    cells += rng.integers(-3, 4, cells.shape)
    same(polygon[0] if shared else polygon, cells)


@pytest.mark.parametrize('offset', [0., 1., -1., 1e-12, -1e-12])
def test_zero_area_contacts_and_containment(native, offset):
    polygon = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])+offset
    cells = np.array([[r, c] for r in range(-2, 3) for c in range(-2, 3)], dtype=np.int64)
    same(polygon, cells)


@pytest.mark.parametrize('kind', ['strided', 'float32', 'empty', 'missing', 'degenerate'])
def test_fallback_and_empty_inputs(native, monkeypatch, kind):
    polygon = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])
    cells = np.array([[0, 0], [1, 1], [2, 2], [3, 3]], dtype=np.int64)
    if kind == 'strided': cells = cells[::-2]
    if kind == 'float32': polygon = polygon.astype(np.float32)
    if kind == 'empty': cells = cells[:0]
    if kind == 'missing': monkeypatch.setattr(geometry, '_reserved_sweep', None)
    if kind == 'degenerate': polygon[1] = polygon[0]
    same(polygon, cells)


@pytest.mark.parametrize('kind', ['shape', 'dtype', 'strided', 'nonfinite', 'overflow'])
def test_unsupported_native_buffers_are_rejected(native, kind):
    polygon = np.array([[[0., 0.], [1., 0.], [1., 1.], [0., 1.]]])
    cells = np.array([[0, 0]], dtype=np.int64)
    if kind == 'shape': polygon = polygon[0]
    if kind == 'dtype': cells = cells.astype(np.int32)
    if kind == 'strided': polygon = polygon[:, ::-1]
    if kind == 'nonfinite': polygon[0, 0, 0] = np.nan
    if kind == 'overflow': cells[0, 0] = np.iinfo(np.int64).max
    with pytest.raises((TypeError, ValueError)):
        native.cell_intersections(polygon, cells)
