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
