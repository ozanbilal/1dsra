from __future__ import annotations

import numpy as np
import pytest
from dsra1d.config import MaterialType
from dsra1d.materials import mkz_backbone_stress
from dsra1d.materials.mrdf import mrdf_coefficients_from_params
from dsra1d.nonlinear import _ElementConstitutiveState, simulate_hysteretic_stress_path


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


def test_mrdf_uiuc_factor_depends_on_historical_max_strain() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    low_history = np.array([0.0, 0.0020, 0.0010], dtype=np.float64)
    high_history = np.array([0.0, 0.0040, 0.0030], dtype=np.float64)
    tau_low = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        low_history,
        gmax_fallback=70000.0,
    )
    tau_high = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        high_history,
        gmax_fallback=70000.0,
    )
    assert abs(tau_high[-1] - tau_low[-1]) > 1.0e-6


def test_mrdf_secant_reference_blend_uses_reversal_secant_branch() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
        "reload_reference_blend": 1.0,
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
    g_sec_hist = float(
        mkz_backbone_stress(
            np.array([0.0040], dtype=np.float64),
            gmax=70000.0,
            gamma_ref=0.0010,
        )[0]
    ) / 0.0040
    expected = tau_rev + (g_sec_hist * (0.0020 - 0.0040))
    assert tau[2] == pytest.approx(expected, rel=1.0e-8, abs=1.0e-10)


def test_mrdf_secant_reference_blend_stiffens_unload_branch_relative_to_local_anchor() -> None:
    params_local = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 2.0,
        "mrdf_p1": 0.0,
        "mrdf_p2": 0.0,
        "mrdf_p3": 1.0,
        "reload_reference_blend": 0.0,
    }
    params_global = dict(params_local)
    params_global["reload_reference_blend"] = 1.0
    strain = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)
    tau_local = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_local,
        strain,
        gmax_fallback=70000.0,
    )
    tau_global = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_global,
        strain,
        gmax_fallback=70000.0,
    )
    assert tau_global[2] > tau_local[2]


def test_reload_branch_latches_to_backbone_after_true_intersection() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.4,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    strain = np.array(
        [0.0, 0.0020, -0.0005, -0.00025, 0.0, 0.0005, 0.0010, 0.0015, 0.0020, 0.0025],
        dtype=np.float64,
    )
    tau = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params,
        strain,
        gmax_fallback=70000.0,
    )
    tau_backbone = mkz_backbone_stress(
        strain,
        gmax=70000.0,
        gamma_ref=0.0010,
    )
    assert tau[-2] == pytest.approx(float(tau_backbone[-2]), rel=1.0e-8, abs=1.0e-10)
    assert tau[-1] == pytest.approx(float(tau_backbone[-1]), rel=1.0e-8, abs=1.0e-10)


def test_adaptive_reload_rule_changes_hysteretic_response() -> None:
    params_fixed = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    params_adaptive = dict(params_fixed)
    params_adaptive["adaptive_reload_mode_code"] = 1.0
    params_adaptive["adaptive_reload_exponent"] = 0.5
    strain = _closed_strain_cycle(0.0045, n=100)
    tau_fixed = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_fixed,
        strain,
        gmax_fallback=70000.0,
    )
    tau_adaptive = simulate_hysteretic_stress_path(
        MaterialType.MKZ,
        params_adaptive,
        strain,
        gmax_fallback=70000.0,
    )
    assert not np.allclose(tau_fixed, tau_adaptive)


def test_adaptive_tangent_floor_stiffens_branch_tangent_without_changing_backbone() -> None:
    params = {
        "gmax": 70000.0,
        "gamma_ref": 0.0010,
        "reload_factor": 1.1,
        "mrdf_p1": 0.82,
        "mrdf_p2": 0.55,
        "mrdf_p3": 20.0,
    }
    strain_path = np.array([0.0, 0.0040, 0.0020], dtype=np.float64)

    fixed = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params=dict(params),
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    adaptive = _ElementConstitutiveState(
        material=MaterialType.MKZ,
        params={
            **params,
            "adaptive_tangent_mode_code": 1.0,
            "adaptive_tangent_strength": 0.4,
            "adaptive_tangent_exponent": 1.0,
        },
        gmax_fallback=70000.0,
        reload_factor=1.1,
        mrdf_coeffs=mrdf_coefficients_from_params(
            {
                **params,
                "adaptive_tangent_mode_code": 1.0,
                "adaptive_tangent_strength": 0.4,
                "adaptive_tangent_exponent": 1.0,
            }
        ),
    )

    for gamma in strain_path:
        fixed.update_stress(float(gamma))
        adaptive.update_stress(float(gamma))

    tangent_fixed = fixed.tangent_modulus(float(strain_path[-1]))
    tangent_adaptive = adaptive.tangent_modulus(float(strain_path[-1]))
    assert tangent_adaptive >= tangent_fixed


def test_elastic_path_reduces_to_linear_stress() -> None:
    strain = np.array([0.0, 1.0e-4, 2.0e-4, -1.0e-4, 3.0e-4], dtype=np.float64)
    tau = simulate_hysteretic_stress_path(
        MaterialType.ELASTIC,
        {},
        strain,
        gmax_fallback=12345.0,
    )
    assert np.allclose(tau, 12345.0 * strain, rtol=0.0, atol=1.0e-12)
