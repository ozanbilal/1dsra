import numpy as np
from dsra1d.post.spectra import compute_spectra, compute_transfer_function


def test_compute_spectra_shape() -> None:
    signal = np.sin(np.linspace(0, 2 * np.pi, 200))
    spec = compute_spectra(signal, dt=0.01)
    assert spec.periods.shape == spec.psa.shape
    assert spec.periods.size == 80


def test_compute_transfer_function_shape_and_finite() -> None:
    dt = 0.01
    t = np.arange(0.0, 5.0, dt)
    inp = np.sin(2.0 * np.pi * 2.0 * t)
    out = 1.5 * inp
    freq, h_abs = compute_transfer_function(inp, out, dt)
    assert freq.shape == h_abs.shape
    assert freq.size > 2
    assert np.all(np.isfinite(h_abs))
    # Dominant frequency amplification should reflect 1.5x scaling.
    idx = int(np.argmin(np.abs(freq - 2.0)))
    assert h_abs[idx] > 1.0
