"""MRDF + G/Gmax floor scenario tests per decision matrix.

Scenario 1: Strong motion, sand (PI=0) — floor only, no MRDF
Scenario 2: Medium motion, clay (PI>15) — MRDF only, no floor
Scenario 3: Strong motion, clay — both combined
Scenario 4: Weak motion — neither needed
"""
from __future__ import annotations

import numpy as np
import pytest

from dsra1d.materials.hysteretic import (
    generate_masing_loop,
    mkz_modulus_reduction,
)
from dsra1d.materials.mrdf import (
    compute_masing_damping_ratio,
    compute_mrdf_correction_table,
    evaluate_mrdf_factor,
    fit_mrdf_coefficients,
)

# Common MKZ params
SAND_PARAMS: dict[str, float] = {
    "gmax": 127420.0,
    "gamma_ref": 0.00089,
    "damping_min": 0.01,
    "damping_max": 0.15,
    "reload_factor": 1.45,
}

CLAY_PARAMS: dict[str, float] = {
    "gmax": 80000.0,
    "gamma_ref": 0.002,
    "damping_min": 0.02,
    "damping_max": 0.20,
    "reload_factor": 1.6,
}


def _mrdf_f_at_strain(params: dict[str, float], strain: float) -> float:
    """Compute MRDF F factor at a given strain amplitude."""
    from dsra1d.materials.hysteretic import bounded_damping_from_reduction

    strains = np.logspace(-6, -1, 40)
    g_floor = params.get("g_reduction_min", 0.0)
    mod_red = mkz_modulus_reduction(strains, float(params["gamma_ref"]), g_reduction_min=g_floor)
    target = bounded_damping_from_reduction(
        mod_red, float(params["damping_min"]), float(params["damping_max"]),
    )
    _, f_raw = compute_mrdf_correction_table("mkz", params, target, strains, n_points=40)
    coeffs = fit_mrdf_coefficients(np.logspace(-6, -1, 40), f_raw, float(params["gamma_ref"]))
    return evaluate_mrdf_factor(coeffs, strain)


def test_scenario1_sand_floor_only() -> None:
    """Sand (PI=0), strong motion: floor alone stiffens backbone at large strain."""
    params = {**SAND_PARAMS, "g_reduction_min": 0.047}
    # At 5% strain, G/Gmax=0.017 < floor=0.047 so floor activates
    loop_floor = generate_masing_loop("mkz", params, strain_amplitude=0.05)
    loop_no_floor = generate_masing_loop("mkz", {**SAND_PARAMS, "g_reduction_min": 0.0}, strain_amplitude=0.05)
    # Floor backbone is stiffer, so loop peak stress should be higher
    assert float(np.max(loop_floor.stress)) > float(np.max(loop_no_floor.stress))


def test_scenario2_clay_mrdf_only() -> None:
    """Clay (PI>15), medium motion: MRDF F is between 0 and 1.5."""
    params = {**CLAY_PARAMS, "g_reduction_min": 0.0}
    f_val = _mrdf_f_at_strain(params, 0.001)
    assert 0.0 < f_val < 1.5, f"MRDF F={f_val:.3f} out of [0, 1.5] range"


def test_scenario3_combined_floor_and_mrdf() -> None:
    """Strong motion, clay: floor + MRDF combined, F should still be bounded."""
    params = {**CLAY_PARAMS, "g_reduction_min": 0.025}
    f_val = _mrdf_f_at_strain(params, 0.01)
    # With floor-aware Masing damping, F should be reasonable (not >1.5)
    assert 0.0 < f_val <= 1.5, f"Combined F={f_val:.3f} exceeds 1.5 red line"


def test_scenario4_weak_motion_no_effect() -> None:
    """Weak motion: G/Gmax near 1.0, floor has no effect."""
    params = {**SAND_PARAMS, "g_reduction_min": 0.047}
    strain_small = 1.0e-5
    mod_red = mkz_modulus_reduction(
        np.array([strain_small]),
        float(params["gamma_ref"]),
        g_reduction_min=0.047,
    )
    mod_red_no_floor = mkz_modulus_reduction(
        np.array([strain_small]),
        float(params["gamma_ref"]),
        g_reduction_min=0.0,
    )
    # At small strain, floor should have zero effect
    assert abs(float(mod_red[0]) - float(mod_red_no_floor[0])) < 1.0e-6


def test_floor_propagates_to_masing_loop() -> None:
    """g_reduction_min in material_params propagates through generate_masing_loop."""
    params_floor = {**SAND_PARAMS, "g_reduction_min": 0.05}
    params_no_floor = {**SAND_PARAMS, "g_reduction_min": 0.0}

    strains = np.logspace(-4, -1, 20)
    d_floor = compute_masing_damping_ratio("mkz", params_floor, strains)
    d_no_floor = compute_masing_damping_ratio("mkz", params_no_floor, strains)

    # At 5% strain (G/Gmax=0.017 < floor=0.05), floor-aware damping should differ
    large_strain_idx = np.argmin(np.abs(strains - 0.05))
    assert d_floor[large_strain_idx] != d_no_floor[large_strain_idx], (
        "Floor should affect Masing damping at large strains"
    )
