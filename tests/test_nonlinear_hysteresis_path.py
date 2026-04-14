from __future__ import annotations

import numpy as np
import pytest
from dsra1d.config import MaterialType
from dsra1d.materials import mkz_backbone_stress
from dsra1d.nonlinear import simulate_hysteretic_stress_path


def _closed_strain_cycle(gamma_amp: float, n: int = 120) -> np.ndarray:
    up = np.linspace(0.0, gamma_amp, n, dtype=np.float64)
    down = np.linspace(gamma_amp, -gamma_amp, 2 * n, dtype=np.float64)[1:]
    back = np.linspace(-gamma_amp, gamma_amp, 2 * n, dtype=np.float64)[1:]
    return np.concatenate([up, down, back])


def test_mkz_monotonic_loading_matches_backbone() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0012,
        "reload_factor": 2.0,
    }
    strain = np.linspace(0.0, 0.004, 200, dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_expected = mkz_backbone_stress(
        strain,
        gmax=70000.0,
        gamma_ref=0.0012,
    )
    assert np.allclose(tau, tau_expected, rtol=1.0e-6, atol=1.0e-9)


def test_hysteretic_cycle_has_positive_energy_dissipation() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
    }
    strain = _closed_strain_cycle(0.005, n=120)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    energy = float(abs(np.trapezoid(tau, strain)))
    assert energy > 1.0e-6


def test_reload_factor_changes_hysteretic_response() -> None:
    params_masing = {
        "gmax": 90000.0,
        "gamma_ref": 0.0011,
        "a1": 1.0,
        "a2": 0.3,
        "m": 2.0,
        "reload_factor": 2.0,
    }
    params_non_masing = dict(params_masing)
    params_non_masing["reload_factor"] = 1.0
    strain = _closed_strain_cycle(0.0045, n=100)
    tau_masing = simulate_hysteretic_stress_path(
        MaterialType.GQH,
        params_masing,
        strain,
        gmax_fallback=90000.0,
    )
    tau_non_masing = simulate_hysteretic_stress_path(
        MaterialType.GQH,
        params_non_masing,
        strain,
        gmax_fallback=90000.0,
    )
    assert not np.allclose(tau_masing, tau_non_masing)
    energy_masing = float(abs(np.trapezoid(tau_masing, strain)))
    energy_non_masing = float(abs(np.trapezoid(tau_non_masing, strain)))
    assert abs(energy_masing - energy_non_masing) > 1.0e-6


def test_mrdf_zero_factor_uses_local_translated_reference_branch() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
    }
    strain = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_rev = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    tau_delta = float(
        mkz_backbone_stress(
            np.array([0.0020], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    )
    expected = tau_rev - tau_delta
    assert tau[2] == pytest.approx(expected, rel=1.0e-8, abs=1.0e-10)


def test_elastic_path_reduces_to_linear_stress() -> None:
    strain = np.array([0.0, 1.0e-4, 2.0e-4, -1.0e-4, 3.0e-4], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.ELASTIC,
        {},
        strain,
        gmax_fallback=12345.0,
    )
    assert np.allclose(tau, 12345.0 * strain, rtol=0.0, atol=1.0e-12)
