import numpy as np
from dsra1d.post.spectra import compute_spectra


def test_compute_spectra_shape() -> None:
    signal = np.sin(np.linspace(0, 2 * np.pi, 200))
    spec = compute_spectra(signal, dt=0.01)
    assert spec.periods.shape == spec.psa.shape
    assert spec.periods.size == 80
