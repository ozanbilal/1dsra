import numpy as np
from dsra1d.post.spectra import compute_spectra, compute_transfer_function


def test_compute_spectra_shape() -> None:
    signal = np.sin(np.linspace(0, 2 * np.pi, 200))
    spec = compute_spectra(signal, dt=0.01)
    assert spec.periods.shape == spec.psa.shape
    assert spec.periods.size == 80


def test_compute_spectra_zero_input_is_zero() -> None:
    signal = np.zeros(1200, dtype=np.float64)
    spec = compute_spectra(signal, dt=0.005, damping=0.05)
    assert np.allclose(spec.psa, 0.0)


def test_compute_spectra_harmonic_peak_near_input_period() -> None:
    dt = 0.002
    t = np.arange(0.0, 40.0, dt)
    f_in = 2.0
    signal = np.sin(2.0 * np.pi * f_in * t)
    periods = np.linspace(0.2, 0.8, 121)
    spec = compute_spectra(signal, dt=dt, damping=0.05, periods=periods)
    idx_peak = int(np.argmax(spec.psa))
    t_peak = float(spec.periods[idx_peak])
    assert abs(t_peak - (1.0 / f_in)) < 0.08
    assert float(spec.psa[idx_peak]) > 4.0


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


def test_compute_transfer_function_masks_low_energy_bands() -> None:
    dt = 0.005
    t = np.arange(0.0, 20.0, dt)
    inp = np.sin(2.0 * np.pi * 2.0 * t)
    out = 1.5 * inp + 0.6 * np.sin(2.0 * np.pi * 40.0 * t)
    freq, h_abs = compute_transfer_function(inp, out, dt)

    idx_2hz = int(np.argmin(np.abs(freq - 2.0)))
    idx_40hz = int(np.argmin(np.abs(freq - 40.0)))
    assert h_abs[idx_2hz] > 1.0
    assert h_abs[idx_40hz] < 0.2


def test_compute_transfer_function_invalid_floor_ratio_raises() -> None:
    with np.testing.assert_raises(ValueError):
        compute_transfer_function(
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
            0.01,
            amplitude_floor_ratio=0.0,
        )
