from __future__ import annotations

import numpy as np
import pytest

from dsra1d.profile_diagnostics import (
    compute_profile_diagnostics,
    mean_effective_stress_from_k0,
)


def test_mean_effective_stress_from_k0_matches_manual_expression() -> None:
    sigma_eff = 120.0
    k0 = 0.5
    sigma_m = mean_effective_stress_from_k0(sigma_eff, k0)
    assert sigma_m == pytest.approx(80.0)


def test_profile_diagnostics_implied_strength_for_elastic_layer() -> None:
    layers = [
        {
            "name": "L1",
            "thickness_m": 5.0,
            "unit_weight_kN_m3": 20.0,
            "vs_m_s": 500.0,
            "material": "elastic",
            "material_params": {},
        }
    ]
    strain = np.array([1.0e-4, 1.0e-3, 1.0e-2], dtype=np.float64)
    rows = compute_profile_diagnostics(layers, water_table_depth_m=None, strain=strain)
    assert len(rows) == 1
    row = rows[0]
    rho = 20.0 / 9.81
    gmax = rho * 500.0 * 500.0
    assert row.implied_strength_kpa == pytest.approx(gmax * 1.0e-2, rel=1.0e-6)
    expected_norm = (gmax * 1.0e-2) / row.sigma_v_eff_mid_kpa
    assert row.normalized_implied_strength == pytest.approx(expected_norm, rel=1.0e-6)


def test_profile_diagnostics_effective_stress_with_water_table() -> None:
    layers = [
        {
            "name": "L1",
            "thickness_m": 4.0,
            "unit_weight_kN_m3": 20.0,
            "vs_m_s": 250.0,
            "material": "elastic",
            "material_params": {},
        },
        {
            "name": "L2",
            "thickness_m": 4.0,
            "unit_weight_kN_m3": 20.0,
            "vs_m_s": 250.0,
            "material": "elastic",
            "material_params": {},
        },
    ]
    rows = compute_profile_diagnostics(layers, water_table_depth_m=1.0)
    assert len(rows) == 2
    assert rows[0].sigma_v_eff_mid_kpa < rows[0].sigma_v0_mid_kpa
    assert rows[1].sigma_v_eff_mid_kpa < rows[1].sigma_v0_mid_kpa
    assert rows[1].pore_water_pressure_kpa > rows[0].pore_water_pressure_kpa
