"""Analytical validation of frequency-domain 1D SH solver against Kramer (1996) Ch.7.

Single uniform damped layer on rigid rock:
    |H(f)| = 1 / |cos(k* h)|
    k* = omega / Vs*
    Vs* = Vs * sqrt(1 + 2i xi)
    f_n = Vs / (4H) for undamped fundamental frequency
"""
from __future__ import annotations

import numpy as np
import pytest

from dsra1d.linear import solve_frequency_domain_sh
from dsra1d.config import (
    AnalysisControl,
    BoundaryCondition,
    Layer,
    MotionConfig,
    OutputConfig,
    ProjectConfig,
    SoilProfile,
)
from dsra1d.types import Motion


def _single_layer_config(
    thickness: float,
    vs: float,
    rho_kn_m3: float,
    damping: float,
    boundary: BoundaryCondition,
) -> ProjectConfig:
    layer = Layer(
        name="single",
        thickness_m=thickness,
        unit_weight_kn_m3=rho_kn_m3,
        vs_m_s=vs,
        material="elastic",
        material_params={"nu": 0.3},
    )
    return ProjectConfig(
        project_name="analytical_test",
        profile=SoilProfile(layers=[layer]),
        analysis=AnalysisControl(
            solver_backend="linear",
            dt=0.005,
            f_max=50.0,
        ),
        motion=MotionConfig(path="synthetic", units="m/s2"),
        output=OutputConfig(),
        boundary_condition=boundary,
    )


def _analytical_tf_single_layer_rigid(
    freq: np.ndarray,
    h: float,
    vs: float,
    rho: float,
    xi: float,
) -> np.ndarray:
    """Kramer (1996) eq. 7.6: H(f) = 1/cos(k*h) for single layer on rigid base."""
    g = rho * vs**2
    g_star = g * (1.0 + 2.0j * xi)
    vs_star = np.sqrt(g_star / rho)
    result = np.ones(len(freq), dtype=np.complex128)
    for i, f in enumerate(freq):
        omega = 2.0 * np.pi * f
        if omega < 1e-12:
            result[i] = 1.0
            continue
        k_star = omega / vs_star
        result[i] = 1.0 / np.cos(k_star * h)
    return result


def test_single_layer_rigid_transfer_function() -> None:
    """Single damped layer on rigid base: numerical H(f) matches analytical."""
    h, vs, rho_kn = 10.0, 100.0, 17.658  # rho = 1.8 t/m3
    rho = rho_kn / 9.81
    xi = 0.02

    cfg = _single_layer_config(h, vs, rho_kn, xi, BoundaryCondition.RIGID)
    dt = 0.005
    t = np.arange(0, 10.0, dt)
    acc = 0.1 * np.sin(2 * np.pi * 2.0 * t) * np.exp(-t / 3.0)
    motion = Motion(acc=acc, dt=dt)

    result = solve_frequency_domain_sh(
        cfg, motion, layer_damping={1: xi},
    )

    # Analytical
    mask = (result.freq_hz > 0.5) & (result.freq_hz < 40.0)
    h_analytical = _analytical_tf_single_layer_rigid(
        result.freq_hz[mask], h, vs, rho, xi,
    )
    h_numerical = result.transfer_function[mask]

    # Compare magnitudes
    ratio = np.abs(h_numerical) / np.maximum(np.abs(h_analytical), 1e-10)
    assert np.all(np.abs(ratio - 1.0) < 0.02), (
        f"Transfer function mismatch > 2%: max ratio deviation = {np.max(np.abs(ratio - 1.0)):.4f}"
    )


def test_single_layer_rigid_fundamental_frequency() -> None:
    """Fundamental frequency f_n = Vs/(4H) for undamped single layer on rigid base."""
    h, vs = 10.0, 100.0
    f_n_expected = vs / (4.0 * h)  # 2.5 Hz

    cfg = _single_layer_config(h, vs, 17.658, 0.005, BoundaryCondition.RIGID)
    dt = 0.002
    t = np.arange(0, 10.0, dt)
    # Broadband input to excite all frequencies
    rng = np.random.default_rng(42)
    acc = 0.05 * rng.standard_normal(len(t))
    motion = Motion(acc=acc, dt=dt)

    result = solve_frequency_domain_sh(cfg, motion, layer_damping={1: 0.005})

    # Find peak of transfer function
    mask = (result.freq_hz > 1.0) & (result.freq_hz < 10.0)
    peak_idx = np.argmax(np.abs(result.transfer_function[mask]))
    f_peak = result.freq_hz[mask][peak_idx]

    assert abs(f_peak - f_n_expected) < 0.3, (
        f"Fundamental frequency {f_peak:.2f} Hz != expected {f_n_expected:.2f} Hz"
    )


def test_single_layer_rigid_amplification_at_resonance() -> None:
    """At resonance, amplification ~ 1/(2*xi) for lightly damped layer."""
    h, vs, xi = 10.0, 100.0, 0.02
    rho_kn = 17.658
    rho = rho_kn / 9.81
    f_n = vs / (4.0 * h)  # 2.5 Hz
    expected_amp = 1.0 / (2.0 * xi)  # 25.0

    cfg = _single_layer_config(h, vs, rho_kn, xi, BoundaryCondition.RIGID)
    dt = 0.002
    t = np.arange(0, 10.0, dt)
    rng = np.random.default_rng(42)
    acc = 0.05 * rng.standard_normal(len(t))
    motion = Motion(acc=acc, dt=dt)

    result = solve_frequency_domain_sh(cfg, motion, layer_damping={1: xi})

    # Find amplitude at fundamental frequency
    idx_fn = np.argmin(np.abs(result.freq_hz - f_n))
    amp_at_fn = float(np.abs(result.transfer_function[idx_fn]))

    # Analytical: |H(f_n)| = 1/|cos(k*h)| ≈ 1/(2*xi) for small xi
    h_analytical = _analytical_tf_single_layer_rigid(
        np.array([f_n]), h, vs, rho, xi,
    )
    amp_analytical = float(np.abs(h_analytical[0]))

    # Allow 10% tolerance (frequency discretization)
    assert abs(amp_at_fn - amp_analytical) / amp_analytical < 0.10, (
        f"Amplification at resonance: numerical={amp_at_fn:.2f}, analytical={amp_analytical:.2f}"
    )


def test_low_frequency_unity_amplification() -> None:
    """At very low frequencies, H(f) -> 1 for rigid base."""
    cfg = _single_layer_config(10.0, 100.0, 17.658, 0.02, BoundaryCondition.RIGID)
    dt = 0.005
    t = np.arange(0, 5.0, dt)
    acc = 0.1 * np.sin(2 * np.pi * 0.1 * t)
    motion = Motion(acc=acc, dt=dt)

    result = solve_frequency_domain_sh(cfg, motion, layer_damping={1: 0.02})

    # H(f) at f < 0.5 Hz should be ~1.0
    mask = (result.freq_hz > 0.05) & (result.freq_hz < 0.5)
    if np.sum(mask) > 0:
        h_low = np.abs(result.transfer_function[mask])
        assert np.all(np.abs(h_low - 1.0) < 0.05), (
            f"Low-frequency H(f) deviates from 1.0: range [{h_low.min():.4f}, {h_low.max():.4f}]"
        )
