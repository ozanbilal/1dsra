import numpy as np
import pytest
from dsra1d.config import load_project_config
from dsra1d.calibration import (
    calibrate_gqh_from_darendeli,
    calibrate_mkz_from_darendeli,
    darendeli_damping_ratio,
    darendeli_modulus_reduction,
    generate_darendeli_curves,
)
from dsra1d.materials import gqh_backbone_stress_from_params, gqh_modulus_reduction_from_params


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


def test_darendeli_damping_ratio_rises_meaningfully_with_strain() -> None:
    strain = np.logspace(-6, -1.3, 60, dtype=np.float64)
    damping = darendeli_damping_ratio(
        strain,
        plasticity_index=30.0,
        ocr=1.0,
        mean_effective_stress_kpa=40.0,
        frequency_hz=1.0,
        num_cycles=10.0,
    )
    assert damping[0] == pytest.approx(0.0158, rel=0.08)
    assert damping[-1] > 0.20
    assert damping[-1] / damping[0] > 10.0


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


def test_calibrate_gqh_from_darendeli_strength_controlled_mode() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=95000.0,
        plasticity_index=8.0,
        ocr=1.0,
        mean_effective_stress_kpa=150.0,
        tau_target_kpa=420.0,
        fit_strain_min=1.0e-6,
        fit_strain_max=5.0e-4,
        target_strength_ratio=0.95,
        target_strength_strain=0.1,
    )
    assert result.material == "gqh"
    assert result.gqh_mode == "strength_controlled"
    assert result.material_params["tau_max"] == pytest.approx(420.0, rel=1.0e-4)
    for key in ("theta1", "theta2", "theta3", "theta4", "theta5"):
        assert key in result.material_params
    for key in ("mrdf_p1", "mrdf_p2", "mrdf_p3"):
        assert key in result.material_params
    tau_strength = gqh_backbone_stress_from_params(
        np.array([0.1], dtype=np.float64),
        result.material_params,
    )[0]
    assert tau_strength / result.material_params["tau_max"] == pytest.approx(0.95, rel=0.03)
    assert result.fitted_damping_ratio.shape == result.strain.shape
    damping_log_rmse = np.sqrt(
        np.mean(
            np.square(
                np.log(np.clip(result.fitted_damping_ratio, 1.0e-8, 0.5))
                - np.log(np.clip(result.target_damping_ratio, 1.0e-8, 0.5))
            )
        )
    )
    assert damping_log_rmse < 0.25


def test_calibrate_gqh_from_darendeli_allows_k0_based_mean_stress_resolution() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=90000.0,
        plasticity_index=15.0,
        ocr=1.2,
        mean_effective_stress_kpa=None,
        sigma_v_eff_mid_kpa=120.0,
        k0=0.5,
    )
    assert result.material == "gqh"
    assert result.gqh_mode == "legacy"
    assert result.material_params["gamma_ref"] > 0.0


def test_calibrate_gqh_strength_control_reports_fit_metrics_and_limits() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=509684.0,
        plasticity_index=15.0,
        ocr=1.0,
        mean_effective_stress_kpa=20.0,
        tau_target_kpa=420.0,
        fit_strain_min=1.0e-6,
        fit_strain_max=5.0e-4,
        target_strength_ratio=0.95,
        target_strength_strain=0.1,
        fit_procedure="MRD",
        fit_limits={
            "mr_min_strain": 1.0e-6,
            "mr_max_strain": 5.0e-4,
            "damping_min_strain": 1.0e-6,
            "damping_max_strain": 1.0e-2,
            "min_strength_pct": 95.0,
        },
    )
    assert result.material == "gqh"
    assert result.gqh_mode == "strength_controlled"
    assert result.fit_procedure == "MRD"
    assert result.modulus_rmse is not None
    assert result.damping_rmse is not None
    assert result.strength_ratio_achieved is not None
    assert result.fit_limits_applied is not None
    assert result.fit_limits_applied["min_strength_pct"] == pytest.approx(95.0)
    assert result.strength_ratio_achieved >= 0.90


def test_calibrate_gqh_strength_control_mrd_refines_final_damping_curve() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=509684.0,
        plasticity_index=0.0,
        ocr=1.0,
        mean_effective_stress_kpa=40.0,
        tau_target_kpa=419.514,
        fit_procedure="MRD",
        fit_strain_min=1.0e-6,
        fit_strain_max=5.0e-2,
        target_strength_ratio=0.95,
        target_strength_strain=0.1,
        fit_limits={
            "mr_min_strain": 1.0e-6,
            "mr_max_strain": 5.0e-2,
            "damping_min_strain": 1.0e-6,
            "damping_max_strain": 5.0e-2,
            "min_strength_pct": 95.0,
        },
    )
    assert result.material == "gqh"
    assert result.fit_procedure == "MRD"
    assert result.modulus_rmse is not None and result.modulus_rmse < 0.18
    assert result.damping_rmse is not None and result.damping_rmse < 0.05
    assert result.strength_ratio_achieved is not None and result.strength_ratio_achieved > 0.84


def test_calibrate_gqh_strength_control_supports_dc_and_fixed_theta3() -> None:
    result = calibrate_gqh_from_darendeli(
        gmax=509684.0,
        plasticity_index=15.0,
        ocr=1.0,
        mean_effective_stress_kpa=20.0,
        tau_target_kpa=420.0,
        fit_procedure="DC",
        fit_limits={
            "fix_theta3": 1.0,
            "min_strength_pct": 95.0,
        },
    )
    assert result.material == "gqh"
    assert result.gqh_mode == "strength_controlled"
    assert result.fit_procedure == "DC"
    assert result.material_params["theta3"] == pytest.approx(1.0, rel=1.0e-6)


def test_fitted_baseline_matches_darendeli_target_better_than_literal_theta_fixture() -> None:
    fitted_cfg = load_project_config("examples/native/deepsoil_gqh_5layer_baseline.yml")
    literal_cfg = load_project_config("examples/native/deepsoil_gqh_5layer_literal.yml")
    fitted_layer = fitted_cfg.profile.layers[0]
    literal_layer = literal_cfg.profile.layers[0]
    assert fitted_layer.calibration is not None
    calibration = fitted_layer.calibration

    curves = generate_darendeli_curves(
        plasticity_index=calibration.plasticity_index,
        ocr=calibration.ocr,
        mean_effective_stress_kpa=calibration.mean_effective_stress_kpa,
        frequency_hz=calibration.frequency_hz,
        num_cycles=calibration.num_cycles,
        strain_min=calibration.strain_min,
        strain_max=calibration.strain_max,
        n_points=calibration.n_points,
    )
    fit_mask = (
        (curves.strain >= calibration.fit_strain_min)
        & (curves.strain <= calibration.fit_strain_max)
    )

    fitted_reduction = gqh_modulus_reduction_from_params(curves.strain, fitted_layer.material_params)
    literal_reduction = gqh_modulus_reduction_from_params(curves.strain, literal_layer.material_params)

    fitted_rmse = float(
        np.sqrt(
            np.mean(
                np.square(
                    np.log(np.clip(fitted_reduction[fit_mask], 1.0e-8, 1.0))
                    - np.log(np.clip(curves.modulus_reduction[fit_mask], 1.0e-8, 1.0))
                )
            )
        )
    )
    literal_rmse = float(
        np.sqrt(
            np.mean(
                np.square(
                    np.log(np.clip(literal_reduction[fit_mask], 1.0e-8, 1.0))
                    - np.log(np.clip(curves.modulus_reduction[fit_mask], 1.0e-8, 1.0))
                )
            )
        )
    )

    assert fitted_rmse < 0.02
    assert literal_rmse > 0.08
    assert fitted_rmse < literal_rmse
