from __future__ import annotations

import math
from dataclasses import dataclass

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
    modulus_reduction = modified_hyperbolic_modulus_reduction(
        strain,
        strain_ref=strain_ref,
        curvature=darendeli_curvature(),
    )
    masing_scaling = (
        0.6329
        - (0.00566 * log_cycles)
        + (-1.1143 + (0.0557 * log_cycles))
        * np.power(1.0 - modulus_reduction, 0.2010 + (0.0405 * log_cycles))
    )
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
    material_params: dict[str, float]
    fit_rmse: float


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
    fit_rmse = float(
        np.sqrt(np.mean(np.square(_log_residual(fitted_reduction, curves.modulus_reduction))))
    )
    return HystereticCalibrationResult(
        material="mkz",
        source="darendeli",
        strain=curves.strain,
        target_modulus_reduction=curves.modulus_reduction,
        target_damping_ratio=curves.damping_ratio,
        fitted_modulus_reduction=fitted_reduction,
        material_params=material_params,
        fit_rmse=fit_rmse,
    )


def calibrate_gqh_from_darendeli(
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
    reload_factor: float = 1.6,
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
    fit_rmse = float(
        np.sqrt(np.mean(np.square(_log_residual(fitted_reduction, curves.modulus_reduction))))
    )
    return HystereticCalibrationResult(
        material="gqh",
        source="darendeli",
        strain=curves.strain,
        target_modulus_reduction=curves.modulus_reduction,
        target_damping_ratio=curves.damping_ratio,
        fitted_modulus_reduction=fitted_reduction,
        material_params=material_params,
        fit_rmse=fit_rmse,
    )
