from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from scipy.optimize import least_squares

FloatArray = npt.NDArray[np.float64]

DEFAULT_ATMOSPHERIC_PRESSURE_KPA = 101.3


def _to_float_array(values: npt.ArrayLike) -> FloatArray:
    return np.asarray(values, dtype=np.float64)


def _check_positive(name: str, value: float) -> float:
    scalar = float(value)
    if not math.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be > 0.")
    return scalar


def _check_nonnegative(name: str, value: float) -> float:
    scalar = float(value)
    if not math.isfinite(scalar) or scalar < 0.0:
        raise ValueError(f"{name} must be >= 0.")
    return scalar


def _strain_grid(
    *,
    strain_min: float,
    strain_max: float,
    n_points: int,
) -> FloatArray:
    lo = _check_positive("strain_min", strain_min)
    hi = _check_positive("strain_max", strain_max)
    if hi <= lo:
        raise ValueError("strain_max must be greater than strain_min.")
    if n_points < 8:
        raise ValueError("n_points must be >= 8.")
    return np.logspace(np.log10(lo), np.log10(hi), int(n_points), dtype=np.float64)


def modified_hyperbolic_modulus_reduction(
    strain: npt.ArrayLike,
    *,
    strain_ref: float,
    curvature: float,
) -> FloatArray:
    gamma = np.maximum(np.abs(_to_float_array(strain)), 1.0e-12)
    gamma_ref = _check_positive("strain_ref", strain_ref)
    exponent = _check_positive("curvature", curvature)
    return np.asarray(1.0 / (1.0 + np.power(gamma / gamma_ref, exponent)), dtype=np.float64)


def modified_hyperbolic_masing_damping(
    strain: npt.ArrayLike,
    *,
    strain_ref: float,
    curvature: float,
    masing_scaling: npt.ArrayLike,
) -> FloatArray:
    gamma = np.maximum(np.abs(_to_float_array(strain)), 1.0e-12)
    gamma_ref = _check_positive("strain_ref", strain_ref)
    exponent = _check_positive("curvature", curvature)
    scaling = _to_float_array(masing_scaling)

    strain_pct = gamma * 100.0
    strain_ref_pct = gamma_ref * 100.0
    with np.errstate(divide="ignore", invalid="ignore"):
        damping_masing_a1 = (100.0 / np.pi) * (
            4.0
            * (
                strain_pct
                - strain_ref_pct * np.log((strain_pct + strain_ref_pct) / strain_ref_pct)
            )
            / (np.square(strain_pct) / (strain_pct + strain_ref_pct))
            - 2.0
        )

    c1 = (-1.1143 * exponent * exponent) + (1.8618 * exponent) + 0.2523
    c2 = (0.0805 * exponent * exponent) - (0.0710 * exponent) - 0.0095
    c3 = (-0.0005 * exponent * exponent) + (0.0002 * exponent) + 0.0003
    damping_masing = (
        (c1 * damping_masing_a1)
        + (c2 * np.square(damping_masing_a1))
        + (c3 * np.power(damping_masing_a1, 3.0))
    )
    modulus_reduction = modified_hyperbolic_modulus_reduction(
        gamma,
        strain_ref=gamma_ref,
        curvature=exponent,
    )
    damping = (scaling * damping_masing * np.power(modulus_reduction, 0.1)) / 100.0
    damping = np.where(np.isfinite(damping), damping, 0.0)
    return np.maximum.accumulate(np.clip(damping, 0.0, 0.5))


def darendeli_reference_strain(
    *,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
) -> float:
    pi = _check_nonnegative("plasticity_index", plasticity_index)
    ocr_value = _check_positive("ocr", ocr)
    sigma_m = _check_positive("mean_effective_stress_kpa", mean_effective_stress_kpa)
    p_atm = _check_positive("atmospheric_pressure_kpa", atmospheric_pressure_kpa)
    strain_pct = (
        (0.0352 + (0.0010 * pi * np.power(ocr_value, 0.3246)))
        * np.power(sigma_m / p_atm, 0.3483)
    )
    return float(strain_pct / 100.0)


def darendeli_minimum_damping(
    *,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    frequency_hz: float = 1.0,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
) -> float:
    pi = _check_nonnegative("plasticity_index", plasticity_index)
    ocr_value = _check_positive("ocr", ocr)
    sigma_m = _check_positive("mean_effective_stress_kpa", mean_effective_stress_kpa)
    freq = _check_positive("frequency_hz", frequency_hz)
    p_atm = _check_positive("atmospheric_pressure_kpa", atmospheric_pressure_kpa)
    damping_pct = (
        (0.8005 + (0.0129 * pi * np.power(ocr_value, -0.1069)))
        * np.power(sigma_m / p_atm, -0.2889)
        * (1.0 + (0.2919 * np.log(freq)))
    )
    return float(np.clip(damping_pct / 100.0, 0.0, 0.5))


def darendeli_curvature() -> float:
    return 0.9190


def darendeli_modulus_reduction(
    strain: npt.ArrayLike,
    *,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
) -> FloatArray:
    strain_ref = darendeli_reference_strain(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
    )
    return modified_hyperbolic_modulus_reduction(
        strain,
        strain_ref=strain_ref,
        curvature=darendeli_curvature(),
    )


def darendeli_damping_ratio(
    strain: npt.ArrayLike,
    *,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    frequency_hz: float = 1.0,
    num_cycles: float = 10.0,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
) -> FloatArray:
    strain_ref = darendeli_reference_strain(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
    )
    damping_min = darendeli_minimum_damping(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        frequency_hz=frequency_hz,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
    )
    cycles = _check_positive("num_cycles", num_cycles)
    log_cycles = np.log(cycles)
    # Darendeli uses a cycle-dependent Masing scaling term. Making this
    # strain-dependent collapses the damping curve into an unrealistically
    # flat low plateau, which is what the UI screenshots were showing.
    masing_scaling = 0.6329 - (0.00566 * log_cycles)
    damping_corr = modified_hyperbolic_masing_damping(
        strain,
        strain_ref=strain_ref,
        curvature=darendeli_curvature(),
        masing_scaling=masing_scaling,
    )
    damping = damping_min + damping_corr
    return np.maximum.accumulate(np.clip(damping, damping_min, 0.5))


@dataclass(slots=True, frozen=True)
class DarendeliCurves:
    strain: FloatArray
    modulus_reduction: FloatArray
    damping_ratio: FloatArray
    strain_ref: float
    damping_min: float
    curvature: float


@dataclass(slots=True, frozen=True)
class HystereticCalibrationResult:
    material: str
    source: str
    strain: FloatArray
    target_modulus_reduction: FloatArray
    target_damping_ratio: FloatArray
    fitted_modulus_reduction: FloatArray
    fitted_damping_ratio: FloatArray
    material_params: dict[str, float]
    fit_rmse: float
    gqh_mode: str | None = None
    modulus_rmse: float | None = None
    damping_rmse: float | None = None
    strength_ratio_achieved: float | None = None
    fit_procedure: str | None = None
    fit_limits_applied: dict[str, float | bool | str] | None = None


def generate_darendeli_curves(
    *,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    frequency_hz: float = 1.0,
    num_cycles: float = 10.0,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
) -> DarendeliCurves:
    strain = _strain_grid(strain_min=strain_min, strain_max=strain_max, n_points=n_points)
    strain_ref = darendeli_reference_strain(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
    )
    damping_min = darendeli_minimum_damping(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        frequency_hz=frequency_hz,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
    )
    return DarendeliCurves(
        strain=strain,
        modulus_reduction=darendeli_modulus_reduction(
            strain,
            plasticity_index=plasticity_index,
            ocr=ocr,
            mean_effective_stress_kpa=mean_effective_stress_kpa,
            atmospheric_pressure_kpa=atmospheric_pressure_kpa,
        ),
        damping_ratio=darendeli_damping_ratio(
            strain,
            plasticity_index=plasticity_index,
            ocr=ocr,
            mean_effective_stress_kpa=mean_effective_stress_kpa,
            frequency_hz=frequency_hz,
            num_cycles=num_cycles,
            atmospheric_pressure_kpa=atmospheric_pressure_kpa,
        ),
        strain_ref=strain_ref,
        damping_min=damping_min,
        curvature=darendeli_curvature(),
    )


def _log_residual(predicted: FloatArray, target: FloatArray) -> FloatArray:
    pred = np.clip(predicted, 1.0e-6, 1.0)
    obs = np.clip(target, 1.0e-6, 1.0)
    return np.asarray(np.log(pred) - np.log(obs), dtype=np.float64)


def _window_mask(
    strain: FloatArray,
    lo: float,
    hi: float,
) -> FloatArray:
    return np.asarray((strain >= lo) & (strain <= hi), dtype=bool)


def _log_rmse(
    predicted: FloatArray,
    target: FloatArray,
) -> float:
    if predicted.size == 0 or target.size == 0:
        return float("nan")
    residual = _log_residual(predicted, target)
    return float(np.sqrt(np.mean(np.square(residual))))


def _fit_damping_max(
    reduction: FloatArray,
    damping_target: FloatArray,
    damping_min: float,
) -> float:
    x = np.clip(1.0 - reduction, 0.0, 1.0)
    y = np.maximum(_to_float_array(damping_target) - damping_min, 0.0)
    denom = float(np.dot(x, x))
    if denom <= 1.0e-14:
        return float(np.clip(damping_min, 0.0, 0.5))
    slope = float(np.dot(x, y) / denom)
    return float(np.clip(damping_min + max(slope, 0.0), damping_min, 0.5))


def _resolve_mean_effective_stress_kpa(
    *,
    mean_effective_stress_kpa: float | None,
    sigma_v_eff_mid_kpa: float | None,
    k0: float | None,
) -> float:
    if mean_effective_stress_kpa is not None:
        return _check_positive("mean_effective_stress_kpa", mean_effective_stress_kpa)
    if sigma_v_eff_mid_kpa is None or k0 is None:
        raise ValueError(
            "Provide mean_effective_stress_kpa or both sigma_v_eff_mid_kpa and k0."
        )
    sigma_eff = _check_positive("sigma_v_eff_mid_kpa", sigma_v_eff_mid_kpa)
    k0_value = _check_nonnegative("k0", k0)
    return float(sigma_eff * (1.0 + (2.0 * k0_value)) / 3.0)


def _material_fitted_damping_ratio(
    *,
    material: str,
    params: dict[str, float],
    strain: FloatArray,
) -> FloatArray:
    from dsra1d.config import MaterialType
    from dsra1d.materials import (
        bounded_damping_from_reduction,
        compute_masing_damping_ratio,
        evaluate_mrdf_factor,
        gqh_modulus_reduction_from_params,
        mkz_modulus_reduction,
        mrdf_coefficients_from_params,
    )

    damping_min = float(params.get("damping_min", 0.0))
    damping_max = float(params.get("damping_max", max(damping_min, 0.15)))
    mat = MaterialType(material)
    if mat == MaterialType.MKZ:
        reduction = mkz_modulus_reduction(
            strain,
            gamma_ref=float(params.get("gamma_ref", 1.0e-3)),
            g_reduction_min=float(params.get("g_reduction_min", 0.0)),
        )
    else:
        reduction = gqh_modulus_reduction_from_params(strain, params)

    coeffs = mrdf_coefficients_from_params(params)
    if coeffs is None:
        return bounded_damping_from_reduction(
            reduction,
            damping_min=damping_min,
            damping_max=damping_max,
        )

    masing = compute_masing_damping_ratio(mat, params, strain)
    factors = np.asarray(
        [
            evaluate_mrdf_factor(coeffs, float(s), g_over_gmax=float(r))
            for s, r in zip(strain, reduction, strict=False)
        ],
        dtype=np.float64,
    )
    damping = np.maximum(damping_min, masing * factors)
    return np.maximum.accumulate(np.clip(damping, damping_min, 0.5))


def _fit_uiuc_mrdf_parameters(
    *,
    reduction: FloatArray,
    masing_damping: FloatArray,
    target_damping: FloatArray,
    damping_min: float,
) -> tuple[float, float, float]:
    red = np.clip(_to_float_array(reduction), 0.0, 1.0)
    masing = np.clip(_to_float_array(masing_damping), 1.0e-12, 0.5)
    target = np.clip(_to_float_array(target_damping), max(float(damping_min), 1.0e-12), 0.5)
    if red.shape != masing.shape or red.shape != target.shape:
        raise ValueError("reduction, masing_damping, and target_damping must share the same shape.")

    mask = np.isfinite(red) & np.isfinite(masing) & np.isfinite(target)
    if int(np.count_nonzero(mask)) < 8:
        return (1.0, 0.0, 20.0)

    red_fit = red[mask]
    masing_fit = masing[mask]
    target_fit = target[mask]
    one_minus_red = np.clip(1.0 - red_fit, 0.0, 1.0)
    damping_floor = max(float(damping_min), 1.0e-12)

    lower = np.array([0.0, -1.5, 0.1], dtype=np.float64)
    upper = np.array([1.5, 1.5, 40.0], dtype=np.float64)
    seeds = (
        np.array([1.0, 0.0, 20.0], dtype=np.float64),
        np.array([0.9, 0.2, 15.0], dtype=np.float64),
        np.array([1.1, -0.2, 8.0], dtype=np.float64),
        np.array([0.8, 0.5, 25.0], dtype=np.float64),
    )

    def residual(x: FloatArray) -> FloatArray:
        p1, p2, p3 = (float(v) for v in x)
        f = np.clip(p1 - (p2 * np.power(one_minus_red, p3)), 0.0, 1.5)
        predicted = np.maximum(damping_floor, masing_fit * f)
        predicted = np.clip(predicted, damping_floor, 0.5)
        return np.log(predicted) - np.log(target_fit)

    best_result = None
    best_cost = float("inf")
    for seed in seeds:
        result = least_squares(residual, x0=seed, bounds=(lower, upper), max_nfev=1200)
        cost = float(np.sum(np.square(result.fun)))
        if cost < best_cost:
            best_cost = cost
            best_result = result

    if best_result is None:
        return (1.0, 0.0, 20.0)
    p1, p2, p3 = (float(v) for v in best_result.x)
    return (p1, p2, p3)


def calibrate_gqh_strength_control_from_reference(
    *,
    gmax: float,
    tau_target_kpa: float,
    strain: FloatArray,
    target_modulus_reduction: FloatArray,
    target_damping_ratio: FloatArray,
    fit_strain_min: float = 1.0e-6,
    fit_strain_max: float = 5.0e-4,
    target_strength_ratio: float = 0.95,
    target_strength_strain: float = 1.0e-1,
    reload_factor: float = 1.6,
    damping_min: float | None = None,
    fit_procedure: str = "MR",
    fit_limits: dict[str, Any] | None = None,
) -> HystereticCalibrationResult:
    from dsra1d.materials import (
        bounded_damping_from_reduction,
        gqh_backbone_stress,
        gqh_backbone_stress_from_params,
        gqh_modulus_reduction,
        gqh_modulus_reduction_from_params,
    )

    gmax_value = _check_positive("gmax", gmax)
    tau_target = _check_positive("tau_target_kpa", tau_target_kpa)
    fit_lo = _check_positive("fit_strain_min", fit_strain_min)
    fit_hi = _check_positive("fit_strain_max", fit_strain_max)
    if fit_hi <= fit_lo:
        raise ValueError("fit_strain_max must be greater than fit_strain_min.")
    target_ratio = _check_positive("target_strength_ratio", target_strength_ratio)
    if target_ratio > 1.0:
        raise ValueError("target_strength_ratio must be <= 1.")
    target_strength_gamma = _check_positive("target_strength_strain", target_strength_strain)
    fit_proc = str(fit_procedure or "MR").strip().upper()
    if fit_proc not in {"MR", "MRD", "DC"}:
        raise ValueError("fit_procedure must be one of: MR, MRD, DC.")

    strain_arr = _to_float_array(strain)
    target_reduction = _to_float_array(target_modulus_reduction)
    target_damping = _to_float_array(target_damping_ratio)
    if strain_arr.shape != target_reduction.shape or strain_arr.shape != target_damping.shape:
        raise ValueError("strain, target_modulus_reduction, and target_damping_ratio must match.")

    limits = dict(fit_limits or {})
    mr_lo = float(limits.get("mr_min_strain", fit_lo))
    mr_hi = float(limits.get("mr_max_strain", fit_hi))
    damping_lo = float(limits.get("damping_min_strain", fit_lo))
    damping_hi = float(limits.get("damping_max_strain", fit_hi))
    min_strength_pct_raw = limits.get("min_strength_pct")
    min_strength_ratio = (
        float(min_strength_pct_raw) / 100.0 if min_strength_pct_raw is not None else target_ratio
    )
    min_strength_ratio = float(np.clip(min_strength_ratio, 0.0, 1.0))
    target_ratio_effective = max(target_ratio, min_strength_ratio)

    if mr_lo <= 0.0 or mr_hi <= mr_lo:
        raise ValueError("MR fit limits require 0 < mr_min_strain < mr_max_strain.")
    if damping_lo <= 0.0 or damping_hi <= damping_lo:
        raise ValueError(
            "Damping fit limits require 0 < damping_min_strain < damping_max_strain."
        )

    mr_mask = _window_mask(strain_arr, mr_lo, mr_hi)
    if int(np.count_nonzero(mr_mask)) < 8:
        raise ValueError("At least 8 reference-curve points must lie within the fit strain range.")
    damping_mask = _window_mask(strain_arr, damping_lo, damping_hi)
    if int(np.count_nonzero(damping_mask)) < 8:
        raise ValueError(
            "At least 8 reference-curve points must lie within the damping fit strain range."
        )

    strain_fit = strain_arr[mr_mask]
    target_fit = target_reduction[mr_mask]
    strain_damping_fit = strain_arr[damping_mask]
    target_damping_fit = target_damping[damping_mask]
    damping_floor = float(
        damping_min if damping_min is not None else max(float(np.min(target_damping)), 0.0)
    )

    fix_theta3 = limits.get("fix_theta3")
    if fix_theta3 is not None:
        fix_theta3 = _check_positive("fit_limits.fix_theta3", float(fix_theta3))

    seeds = [
        np.array([-2.5, 3.0, 5.0, 1.0, 1.0], dtype=np.float64),
        np.array([-5.0, 5.0, 15.0, 1.0, 1.0], dtype=np.float64),
        np.array([-1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64),
        np.array([-8.0, 2.0, 20.0, 1.0, 0.99], dtype=np.float64),
    ]
    lower = np.array([-25.0, -25.0, 0.05, 0.05, 0.2], dtype=np.float64)
    upper = np.array([25.0, 25.0, 150.0, 10.0, 4.0], dtype=np.float64)

    if fix_theta3 is not None:
        seeds = [np.array([s[0], s[1], s[3], s[4]], dtype=np.float64) for s in seeds]
        lower = np.array([lower[0], lower[1], lower[3], lower[4]], dtype=np.float64)
        upper = np.array([upper[0], upper[1], upper[3], upper[4]], dtype=np.float64)

    def unpack_theta(x: FloatArray) -> tuple[float, float, float, float, float]:
        if fix_theta3 is None:
            return (float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        return (float(x[0]), float(x[1]), float(fix_theta3), float(x[2]), float(x[3]))

    best_result = None
    best_cost = float("inf")

    def residual(x: FloatArray) -> FloatArray:
        theta1, theta2, theta3, theta4, theta5 = unpack_theta(x)
        predicted = gqh_modulus_reduction(
            strain_fit,
            gmax=gmax_value,
            tau_max=tau_target,
            theta1=theta1,
            theta2=theta2,
            theta3=theta3,
            theta4=theta4,
            theta5=theta5,
        )
        predicted_damp_red = gqh_modulus_reduction(
            strain_damping_fit,
            gmax=gmax_value,
            tau_max=tau_target,
            theta1=theta1,
            theta2=theta2,
            theta3=theta3,
            theta4=theta4,
            theta5=theta5,
        )
        damping_max_fit = _fit_damping_max(
            predicted_damp_red,
            target_damping_fit,
            damping_min=damping_floor,
        )
        predicted_damping = bounded_damping_from_reduction(
            predicted_damp_red,
            damping_min=damping_floor,
            damping_max=damping_max_fit,
        )
        tau_strength = float(
            gqh_backbone_stress(
                np.array([target_strength_gamma], dtype=np.float64),
                gmax=gmax_value,
                tau_max=tau_target,
                theta1=theta1,
                theta2=theta2,
                theta3=theta3,
                theta4=theta4,
                theta5=theta5,
            )[0]
        )
        strength_residual = (tau_strength / tau_target) - target_ratio_effective
        regularization_terms = [
            0.02 * (theta4 - 1.0),
            0.02 * (theta5 - 1.0),
        ]
        if fix_theta3 is None:
            regularization_terms.append(0.01 * max(theta3 - 80.0, 0.0))
        regularization = np.asarray(regularization_terms, dtype=np.float64)
        modulus_residual = _log_residual(predicted, target_fit)
        damping_residual = _log_residual(predicted_damping, target_damping_fit)
        if fit_proc == "MR":
            mixed = np.concatenate(
                [
                    modulus_residual,
                    0.35 * damping_residual,
                ]
            )
        elif fit_proc == "MRD":
            mixed = np.concatenate([modulus_residual, damping_residual])
        else:
            mixed = np.concatenate([0.20 * modulus_residual, damping_residual])
        return np.concatenate(
            [
                mixed,
                np.array([6.0 * strength_residual], dtype=np.float64),
                regularization,
            ]
        )

    for seed in seeds:
        result = least_squares(residual, x0=seed, bounds=(lower, upper), max_nfev=4000)
        cost = float(np.sum(np.square(result.fun)))
        if cost < best_cost:
            best_cost = cost
            best_result = result

    assert best_result is not None
    theta1, theta2, theta3, theta4, theta5 = unpack_theta(best_result.x)
    damping_cap = float(np.max(target_damping_fit))
    material_params = {
        "gmax": gmax_value,
        "gamma_ref": tau_target / gmax_value,
        "tau_max": tau_target,
        "theta1": theta1,
        "theta2": theta2,
        "theta3": theta3,
        "theta4": theta4,
        "theta5": theta5,
        "damping_min": damping_floor,
        "damping_max": damping_cap,
        "reload_factor": float(max(reload_factor, 1.0e-6)),
    }
    from dsra1d.config import MaterialType
    from dsra1d.materials import compute_masing_damping_ratio

    fitted_reduction = gqh_modulus_reduction_from_params(strain_arr, material_params)
    masing_damping = compute_masing_damping_ratio(
        MaterialType.GQH,
        material_params,
        strain_arr,
    )
    mrdf_p1, mrdf_p2, mrdf_p3 = _fit_uiuc_mrdf_parameters(
        reduction=fitted_reduction[damping_mask],
        masing_damping=masing_damping[damping_mask],
        target_damping=target_damping[damping_mask],
        damping_min=damping_floor,
    )
    material_params["mrdf_p1"] = mrdf_p1
    material_params["mrdf_p2"] = mrdf_p2
    material_params["mrdf_p3"] = mrdf_p3

    def _pack_joint_params(params: dict[str, float]) -> FloatArray:
        if fix_theta3 is None:
            return np.array(
                [
                    params["theta1"],
                    params["theta2"],
                    params["theta3"],
                    params["theta4"],
                    params["theta5"],
                    params["mrdf_p1"],
                    params["mrdf_p2"],
                    params["mrdf_p3"],
                ],
                dtype=np.float64,
            )
        return np.array(
            [
                params["theta1"],
                params["theta2"],
                params["theta4"],
                params["theta5"],
                params["mrdf_p1"],
                params["mrdf_p2"],
                params["mrdf_p3"],
            ],
            dtype=np.float64,
        )

    def _unpack_joint_params(x: FloatArray) -> dict[str, float]:
        if fix_theta3 is None:
            theta1_v, theta2_v, theta3_v, theta4_v, theta5_v, p1_v, p2_v, p3_v = (
                float(v) for v in x
            )
        else:
            theta1_v, theta2_v, theta4_v, theta5_v, p1_v, p2_v, p3_v = (
                float(v) for v in x
            )
            theta3_v = float(fix_theta3)
        return {
            "gmax": gmax_value,
            "gamma_ref": tau_target / gmax_value,
            "tau_max": tau_target,
            "theta1": theta1_v,
            "theta2": theta2_v,
            "theta3": theta3_v,
            "theta4": theta4_v,
            "theta5": theta5_v,
            "damping_min": damping_floor,
            "damping_max": damping_cap,
            "reload_factor": float(max(reload_factor, 1.0e-6)),
            "mrdf_p1": p1_v,
            "mrdf_p2": p2_v,
            "mrdf_p3": p3_v,
        }

    joint_lower = np.concatenate(
        [
            lower,
            np.array([0.0, -1.5, 0.1], dtype=np.float64),
        ]
    )
    joint_upper = np.concatenate(
        [
            upper,
            np.array([1.5, 1.5, 40.0], dtype=np.float64),
        ]
    )
    if fix_theta3 is not None:
        joint_lower = np.concatenate(
            [
                lower,
                np.array([0.0, -1.5, 0.1], dtype=np.float64),
            ]
        )
        joint_upper = np.concatenate(
            [
                upper,
                np.array([1.5, 1.5, 40.0], dtype=np.float64),
            ]
        )

    def _joint_residual(params: dict[str, float]) -> FloatArray:
        predicted = gqh_modulus_reduction_from_params(strain_arr, params)
        predicted_damping = _material_fitted_damping_ratio(
            material="gqh",
            params=params,
            strain=strain_arr,
        )
        strength_ratio = float(
            gqh_backbone_stress_from_params(
                np.array([target_strength_gamma], dtype=np.float64),
                params,
            )[0]
            / tau_target
        )
        modulus_residual = _log_residual(predicted[mr_mask], target_reduction[mr_mask])
        damping_residual = _log_residual(
            predicted_damping[damping_mask],
            target_damping[damping_mask],
        )
        if fit_proc == "MR":
            mixed = np.concatenate([modulus_residual, 0.35 * damping_residual])
        elif fit_proc == "MRD":
            mixed = np.concatenate([modulus_residual, damping_residual])
        else:
            mixed = np.concatenate([0.20 * modulus_residual, damping_residual])
        strength_shortfall = max(target_ratio_effective - strength_ratio, 0.0)
        regularization_terms = [
            0.02 * (params["theta4"] - 1.0),
            0.02 * (params["theta5"] - 1.0),
        ]
        if fix_theta3 is None:
            regularization_terms.append(0.01 * max(params["theta3"] - 80.0, 0.0))
        return np.concatenate(
            [
                mixed,
                np.array(
                    [
                        6.0 * (strength_ratio - target_ratio_effective),
                        8.0 * strength_shortfall,
                    ],
                    dtype=np.float64,
                ),
                np.asarray(regularization_terms, dtype=np.float64),
            ]
        )

    def _joint_cost(params: dict[str, float]) -> float:
        vec = _joint_residual(params)
        return float(np.sum(np.square(vec)))

    if fit_proc in {"MRD", "DC"}:
        initial_params = dict(material_params)
        joint_x0 = _pack_joint_params(initial_params)
        joint_result = least_squares(
            lambda x: _joint_residual(_unpack_joint_params(x)),
            x0=joint_x0,
            bounds=(joint_lower, joint_upper),
            max_nfev=2200,
        )
        refined_params = _unpack_joint_params(joint_result.x)
        if _joint_cost(refined_params) <= _joint_cost(initial_params):
            material_params = refined_params

    fitted_reduction = gqh_modulus_reduction_from_params(strain_arr, material_params)
    fitted_damping = _material_fitted_damping_ratio(
        material="gqh",
        params=material_params,
        strain=strain_arr,
    )
    tau_strength_achieved = float(
        gqh_backbone_stress_from_params(
            np.array([target_strength_gamma], dtype=np.float64),
            material_params,
        )[0]
    )
    strength_ratio_achieved = float(tau_strength_achieved / tau_target)
    modulus_rmse = _log_rmse(fitted_reduction[mr_mask], target_reduction[mr_mask])
    damping_rmse = _log_rmse(fitted_damping[damping_mask], target_damping[damping_mask])
    fit_limits_applied: dict[str, float | bool | str] = {
        "mr_min_strain": float(mr_lo),
        "mr_max_strain": float(mr_hi),
        "damping_min_strain": float(damping_lo),
        "damping_max_strain": float(damping_hi),
        "min_strength_pct": float(target_ratio_effective * 100.0),
        "fix_theta3": float(fix_theta3) if fix_theta3 is not None else False,
    }

    return HystereticCalibrationResult(
        material="gqh",
        source="darendeli",
        strain=strain_arr,
        target_modulus_reduction=target_reduction,
        target_damping_ratio=target_damping,
        fitted_modulus_reduction=fitted_reduction,
        fitted_damping_ratio=fitted_damping,
        material_params=material_params,
        fit_rmse=modulus_rmse,
        gqh_mode="strength_controlled",
        modulus_rmse=modulus_rmse,
        damping_rmse=damping_rmse,
        strength_ratio_achieved=strength_ratio_achieved,
        fit_procedure=fit_proc,
        fit_limits_applied=fit_limits_applied,
    )


def calibrate_mkz_from_darendeli(
    *,
    gmax: float,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float,
    frequency_hz: float = 1.0,
    num_cycles: float = 10.0,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
    reload_factor: float = 2.0,
) -> HystereticCalibrationResult:
    gmax_value = _check_positive("gmax", gmax)
    curves = generate_darendeli_curves(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        frequency_hz=frequency_hz,
        num_cycles=num_cycles,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
        strain_min=strain_min,
        strain_max=strain_max,
        n_points=n_points,
    )

    def residual(x: FloatArray) -> FloatArray:
        gamma_ref = float(x[0])
        predicted = 1.0 / (1.0 + (curves.strain / gamma_ref))
        return _log_residual(predicted, curves.modulus_reduction)

    x0 = np.array([curves.strain_ref], dtype=np.float64)
    bounds = (
        np.array([min(curves.strain) * 0.25], dtype=np.float64),
        np.array([max(curves.strain) * 4.0], dtype=np.float64),
    )
    result = least_squares(residual, x0=x0, bounds=bounds, max_nfev=200)
    gamma_ref = float(result.x[0])
    fitted_reduction = 1.0 / (1.0 + (curves.strain / gamma_ref))
    damping_max = _fit_damping_max(
        fitted_reduction,
        curves.damping_ratio,
        damping_min=curves.damping_min,
    )
    material_params = {
        "gmax": gmax_value,
        "gamma_ref": gamma_ref,
        "damping_min": curves.damping_min,
        "damping_max": damping_max,
        "reload_factor": float(max(reload_factor, 1.0e-6)),
    }
    fitted_damping = _material_fitted_damping_ratio(
        material="mkz",
        params=material_params,
        strain=curves.strain,
    )
    fit_rmse = _log_rmse(fitted_reduction, curves.modulus_reduction)
    damping_rmse = _log_rmse(fitted_damping, curves.damping_ratio)
    return HystereticCalibrationResult(
        material="mkz",
        source="darendeli",
        strain=curves.strain,
        target_modulus_reduction=curves.modulus_reduction,
        target_damping_ratio=curves.damping_ratio,
        fitted_modulus_reduction=fitted_reduction,
        fitted_damping_ratio=fitted_damping,
        material_params=material_params,
        fit_rmse=fit_rmse,
        modulus_rmse=fit_rmse,
        damping_rmse=damping_rmse,
        fit_procedure="MR",
    )


def calibrate_gqh_from_darendeli(
    *,
    gmax: float,
    plasticity_index: float,
    ocr: float,
    mean_effective_stress_kpa: float | None = None,
    sigma_v_eff_mid_kpa: float | None = None,
    k0: float | None = None,
    frequency_hz: float = 1.0,
    num_cycles: float = 10.0,
    atmospheric_pressure_kpa: float = DEFAULT_ATMOSPHERIC_PRESSURE_KPA,
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
    tau_target_kpa: float | None = None,
    fit_strain_min: float = 1.0e-6,
    fit_strain_max: float = 5.0e-4,
    target_strength_ratio: float = 0.95,
    target_strength_strain: float = 1.0e-1,
    reload_factor: float = 1.6,
    fit_procedure: str = "MR",
    fit_limits: dict[str, Any] | None = None,
) -> HystereticCalibrationResult:
    gmax_value = _check_positive("gmax", gmax)
    sigma_m = _resolve_mean_effective_stress_kpa(
        mean_effective_stress_kpa=mean_effective_stress_kpa,
        sigma_v_eff_mid_kpa=sigma_v_eff_mid_kpa,
        k0=k0,
    )
    curves = generate_darendeli_curves(
        plasticity_index=plasticity_index,
        ocr=ocr,
        mean_effective_stress_kpa=sigma_m,
        frequency_hz=frequency_hz,
        num_cycles=num_cycles,
        atmospheric_pressure_kpa=atmospheric_pressure_kpa,
        strain_min=strain_min,
        strain_max=strain_max,
        n_points=n_points,
    )
    tau_target = tau_target_kpa
    if tau_target is not None:
        return calibrate_gqh_strength_control_from_reference(
            gmax=gmax_value,
            tau_target_kpa=tau_target,
            strain=curves.strain,
            target_modulus_reduction=curves.modulus_reduction,
            target_damping_ratio=curves.damping_ratio,
            fit_strain_min=fit_strain_min,
            fit_strain_max=fit_strain_max,
            target_strength_ratio=target_strength_ratio,
            target_strength_strain=target_strength_strain,
            reload_factor=reload_factor,
            damping_min=curves.damping_min,
            fit_procedure=fit_procedure,
            fit_limits=fit_limits,
        )

    def residual(x: FloatArray) -> FloatArray:
        gamma_ref, a1, a2, exponent = (float(v) for v in x)
        ratio = curves.strain / gamma_ref
        predicted = 1.0 / (1.0 + (a1 * ratio) + (a2 * np.power(ratio, exponent)))
        return _log_residual(predicted, curves.modulus_reduction)

    x0 = np.array([curves.strain_ref, 0.8, 0.2, curves.curvature], dtype=np.float64)
    lower = np.array([min(curves.strain) * 0.2, 1.0e-3, 0.0, 0.5], dtype=np.float64)
    upper = np.array([max(curves.strain) * 4.0, 5.0, 5.0, 4.0], dtype=np.float64)
    result = least_squares(residual, x0=x0, bounds=(lower, upper), max_nfev=1200)
    gamma_ref, a1, a2, exponent = (float(v) for v in result.x)
    ratio = curves.strain / gamma_ref
    fitted_reduction = 1.0 / (1.0 + (a1 * ratio) + (a2 * np.power(ratio, exponent)))
    damping_max = _fit_damping_max(
        fitted_reduction,
        curves.damping_ratio,
        damping_min=curves.damping_min,
    )
    material_params = {
        "gmax": gmax_value,
        "gamma_ref": gamma_ref,
        "a1": a1,
        "a2": a2,
        "m": exponent,
        "damping_min": curves.damping_min,
        "damping_max": damping_max,
        "reload_factor": float(max(reload_factor, 1.0e-6)),
    }
    fitted_damping = _material_fitted_damping_ratio(
        material="gqh",
        params=material_params,
        strain=curves.strain,
    )
    fit_rmse = _log_rmse(fitted_reduction, curves.modulus_reduction)
    damping_rmse = _log_rmse(fitted_damping, curves.damping_ratio)
    return HystereticCalibrationResult(
        material="gqh",
        source="darendeli",
        strain=curves.strain,
        target_modulus_reduction=curves.modulus_reduction,
        target_damping_ratio=curves.damping_ratio,
        fitted_modulus_reduction=fitted_reduction,
        fitted_damping_ratio=fitted_damping,
        material_params=material_params,
        fit_rmse=fit_rmse,
        gqh_mode="legacy",
        modulus_rmse=fit_rmse,
        damping_rmse=damping_rmse,
        fit_procedure="MR",
    )


# ---------------------------------------------------------------------------
# Reference curve library (Seed-Idriss 1970, Vucetic-Dobry 1991)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReferenceCurveSet:
    """Container for empirical G/Gmax and damping reference curves."""
    name: str
    source: str
    strain: FloatArray
    modulus_reduction: FloatArray
    damping_ratio: FloatArray


def seed_idriss_sand_upper(
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
) -> ReferenceCurveSet:
    """Seed & Idriss (1970) upper range for sand."""
    anchor_strain = np.array([
        1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4,
        1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
    ])
    anchor_gg = np.array([
        1.000, 1.000, 0.995, 0.980, 0.940, 0.830,
        0.600, 0.350, 0.170, 0.070, 0.030,
    ])
    anchor_damping = np.array([
        0.002, 0.003, 0.005, 0.008, 0.013, 0.020,
        0.035, 0.065, 0.105, 0.155, 0.210,
    ])
    strains = np.logspace(np.log10(strain_min), np.log10(strain_max), n_points)
    gg = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), anchor_gg), 0.0, 1.0)
    damping = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), anchor_damping), 0.0, 0.5)
    return ReferenceCurveSet(
        name="Seed-Idriss Sand (Upper)", source="Seed & Idriss (1970)",
        strain=strains, modulus_reduction=gg, damping_ratio=damping,
    )


def seed_idriss_sand_mean(
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
) -> ReferenceCurveSet:
    """Seed & Idriss (1970) mean curve for sand."""
    anchor_strain = np.array([
        1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4,
        1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
    ])
    anchor_gg = np.array([
        1.000, 1.000, 0.990, 0.960, 0.900, 0.750,
        0.480, 0.240, 0.100, 0.040, 0.015,
    ])
    anchor_damping = np.array([
        0.004, 0.005, 0.008, 0.012, 0.018, 0.030,
        0.055, 0.090, 0.140, 0.195, 0.250,
    ])
    strains = np.logspace(np.log10(strain_min), np.log10(strain_max), n_points)
    gg = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), anchor_gg), 0.0, 1.0)
    damping = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), anchor_damping), 0.0, 0.5)
    return ReferenceCurveSet(
        name="Seed-Idriss Sand (Mean)", source="Seed & Idriss (1970)",
        strain=strains, modulus_reduction=gg, damping_ratio=damping,
    )


def vucetic_dobry(
    plasticity_index: float = 0.0,
    strain_min: float = 1.0e-6,
    strain_max: float = 1.0e-1,
    n_points: int = 60,
) -> ReferenceCurveSet:
    """Vucetic & Dobry (1991) PI-dependent modulus reduction and damping."""
    pi = max(0.0, float(plasticity_index))
    anchor_strain = np.array([
        1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4,
        1e-3, 3e-3, 1e-2, 3e-2, 1e-1,
    ])
    gg_table: dict[float, list[float]] = {
        0:   [1.000, 1.000, 0.990, 0.960, 0.900, 0.750, 0.480, 0.250, 0.100, 0.040, 0.015],
        15:  [1.000, 1.000, 0.995, 0.975, 0.940, 0.830, 0.600, 0.370, 0.170, 0.070, 0.030],
        30:  [1.000, 1.000, 0.997, 0.985, 0.960, 0.880, 0.700, 0.470, 0.250, 0.110, 0.050],
        50:  [1.000, 1.000, 0.998, 0.990, 0.975, 0.920, 0.780, 0.570, 0.330, 0.160, 0.070],
        100: [1.000, 1.000, 0.999, 0.995, 0.985, 0.955, 0.860, 0.680, 0.440, 0.230, 0.110],
        200: [1.000, 1.000, 1.000, 0.998, 0.993, 0.975, 0.920, 0.780, 0.560, 0.330, 0.170],
    }
    d_table: dict[float, list[float]] = {
        0:   [0.004, 0.005, 0.008, 0.012, 0.018, 0.030, 0.055, 0.090, 0.140, 0.195, 0.250],
        15:  [0.003, 0.004, 0.006, 0.009, 0.014, 0.023, 0.040, 0.070, 0.110, 0.160, 0.210],
        30:  [0.002, 0.003, 0.005, 0.007, 0.011, 0.018, 0.032, 0.055, 0.090, 0.130, 0.175],
        50:  [0.002, 0.002, 0.004, 0.006, 0.009, 0.014, 0.025, 0.043, 0.070, 0.105, 0.145],
        100: [0.001, 0.002, 0.003, 0.004, 0.006, 0.010, 0.018, 0.030, 0.050, 0.075, 0.105],
        200: [0.001, 0.001, 0.002, 0.003, 0.005, 0.008, 0.013, 0.022, 0.038, 0.055, 0.080],
    }
    pi_keys = sorted(gg_table.keys())
    if pi <= pi_keys[0]:
        gg_vals, d_vals = np.array(gg_table[pi_keys[0]]), np.array(d_table[pi_keys[0]])
    elif pi >= pi_keys[-1]:
        gg_vals, d_vals = np.array(gg_table[pi_keys[-1]]), np.array(d_table[pi_keys[-1]])
    else:
        lo = max(k for k in pi_keys if k <= pi)
        hi = min(k for k in pi_keys if k > pi)
        frac = (pi - lo) / (hi - lo)
        gg_vals = (1 - frac) * np.array(gg_table[lo]) + frac * np.array(gg_table[hi])
        d_vals = (1 - frac) * np.array(d_table[lo]) + frac * np.array(d_table[hi])
    strains = np.logspace(np.log10(strain_min), np.log10(strain_max), n_points)
    gg = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), gg_vals), 0.0, 1.0)
    damping = np.clip(np.interp(np.log10(strains), np.log10(anchor_strain), d_vals), 0.0, 0.5)
    return ReferenceCurveSet(
        name=f"Vucetic-Dobry (PI={pi:.0f})", source="Vucetic & Dobry (1991)",
        strain=strains, modulus_reduction=gg, damping_ratio=damping,
    )


def get_reference_curves(
    curve_type: str,
    plasticity_index: float = 0.0,
    **kwargs: float,
) -> ReferenceCurveSet:
    """Dispatch to the requested reference curve generator."""
    if curve_type == "seed_idriss_upper":
        return seed_idriss_sand_upper()
    if curve_type == "seed_idriss_mean":
        return seed_idriss_sand_mean()
    if curve_type in ("vucetic_dobry", "vucetic-dobry"):
        return vucetic_dobry(plasticity_index=plasticity_index)
    raise ValueError(f"Unknown reference curve type: {curve_type!r}")
