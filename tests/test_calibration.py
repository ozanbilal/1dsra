import numpy as np
from dsra1d.calibration import (
    calibrate_gqh_from_darendeli,
    calibrate_mkz_from_darendeli,
    darendeli_damping_ratio,
    darendeli_modulus_reduction,
    generate_darendeli_curves,
)


def test_darendeli_curves_are_monotonic() -> None:
    curves = generate_darendeli_curves(
        plasticity_index=20.0,
        ocr=1.5,
        mean_effective_stress_kpa=80.0,
    )
    assert np.all(np.diff(curves.strain) > 0.0)
    assert np.all(np.diff(curves.modulus_reduction) < 0.0)
    assert np.all(np.diff(curves.damping_ratio) >= 0.0)
    assert 0.0 < curves.strain_ref < 0.1
    assert 0.0 < curves.damping_min < 0.1


def test_darendeli_modulus_and_damping_return_finite_arrays() -> None:
    strain = np.logspace(-6, -2, 20, dtype=np.float64)
    reduction = darendeli_modulus_reduction(
        strain,
        plasticity_index=10.0,
        ocr=1.0,
        mean_effective_stress_kpa=120.0,
    )
    damping = darendeli_damping_ratio(
        strain,
        plasticity_index=10.0,
        ocr=1.0,
        mean_effective_stress_kpa=120.0,
    )
    assert reduction.shape == strain.shape
    assert damping.shape == strain.shape
    assert np.all(np.isfinite(reduction))
    assert np.all(np.isfinite(damping))
    assert np.all((reduction > 0.0) & (reduction <= 1.0))
    assert np.all((damping >= 0.0) & (damping <= 0.5))


def test_calibrate_mkz_from_darendeli_produces_usable_parameters() -> None:
    result = calibrate_mkz_from_darendeli(
        gmax=70000.0,
        plasticity_index=25.0,
        ocr=1.8,
        mean_effective_stress_kpa=90.0,
    )
    assert result.material == "mkz"
    assert result.material_params["gmax"] == 70000.0
    assert result.material_params["gamma_ref"] > 0.0
    assert result.material_params["damping_max"] >= result.material_params["damping_min"]
    assert result.fit_rmse < 0.30


def test_calibrate_gqh_from_darendeli_produces_usable_parameters() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=95000.0,
        plasticity_index=8.0,
        ocr=1.0,
        mean_effective_stress_kpa=150.0,
    )
    assert result.material == "gqh"
    assert result.material_params["gmax"] == 95000.0
    assert result.material_params["gamma_ref"] > 0.0
    assert result.material_params["a1"] > 0.0
    assert result.material_params["a2"] >= 0.0
    assert result.material_params["m"] > 0.0
    assert result.material_params["damping_max"] >= result.material_params["damping_min"]
    assert result.fit_rmse < 0.20
