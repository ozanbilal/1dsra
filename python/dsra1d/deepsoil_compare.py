from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from dsra1d.config import MaterialType, ProjectConfig, load_project_config
from dsra1d.deepsoil_excel import import_deepsoil_excel_bundle
from dsra1d.materials import generate_masing_loop
from dsra1d.motion import effective_input_acceleration
from dsra1d.motion.io import load_motion_series
from dsra1d.post import compute_spectra
from dsra1d.profile_diagnostics import compute_profile_diagnostics
from dsra1d.store import ResultStore, load_result


@dataclass(slots=True)
class DeepsoilComparisonArtifacts:
    output_dir: Path
    json_path: Path
    markdown_path: Path


@dataclass(slots=True)
class DeepsoilProfileComparison:
    depth_points: int
    compared_metrics: list[str]
    gamma_max_nrmse: float | None = None
    ru_max_nrmse: float | None = None
    sigma_v_eff_min_nrmse: float | None = None
    effective_stress_kpa_nrmse: float | None = None
    pga_g_nrmse: float | None = None
    max_displacement_m_nrmse: float | None = None
    max_strain_pct_nrmse: float | None = None
    max_stress_ratio_nrmse: float | None = None
    vs_m_s_nrmse: float | None = None
    implied_strength_kpa_nrmse: float | None = None
    normalized_implied_strength_nrmse: float | None = None
    implied_friction_angle_deg_nrmse: float | None = None
    mobilized_strength_nrmse: float | None = None
    mobilized_friction_angle_deg_nrmse: float | None = None


@dataclass(slots=True)
class DeepsoilHysteresisComparison:
    layer_index: int
    point_count: int
    gamma_peak_pct_diff: float
    tau_peak_pct_diff: float
    loop_energy_pct_diff: float
    stress_path_nrmse: float


@dataclass(slots=True)
class DeepsoilComparisonResult:
    run_id: str
    run_dir: Path
    stratawave_dt_s: float
    deepsoil_dt_s: float
    overlap_duration_s: float
    overlap_samples: int
    stratawave_pga_m_s2: float
    deepsoil_pga_m_s2: float
    pga_ratio: float
    pga_pct_diff: float
    surface_rmse_m_s2: float
    surface_nrmse: float
    surface_corrcoef: float
    psa_point_count: int
    psa_rmse_m_s2: float
    psa_nrmse: float
    psa_max_abs_diff_m_s2: float
    psa_pct_diff_at_peak: float
    psa_peak_period_s: float
    used_reference_psa_csv: bool
    surface_psa_peak_period_diff_pct: float | None = None
    # Anderson (2004) GoF metrics
    arias_intensity_sw: float = 0.0
    arias_intensity_ref: float = 0.0
    arias_intensity_ratio: float = 0.0
    xcorr_lag_samples: int = 0
    xcorr_lag_s: float = 0.0
    xcorr_peak_coeff: float = 0.0
    input_history_nrmse: float | None = None
    input_psa_nrmse: float | None = None
    applied_input_history_nrmse: float | None = None
    applied_input_psa_nrmse: float | None = None
    input_dt_used_s: float | None = None
    input_pga_loaded_m_s2: float | None = None
    applied_input_pga_loaded_m_s2: float | None = None
    boundary_condition: str = ""
    motion_input_type: str = ""
    damping_mode: str = ""
    base_motion_semantics_ok: bool | None = None
    reference_kind: str = ""
    warnings: list[str] = field(default_factory=list)
    profile: DeepsoilProfileComparison | None = None
    hysteresis: DeepsoilHysteresisComparison | None = None
    artifacts: DeepsoilComparisonArtifacts | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        artifacts = payload.get("artifacts")
        if isinstance(artifacts, dict):
            payload["artifacts"] = {
                key: str(value) if isinstance(value, Path) else value
                for key, value in artifacts.items()
            }
        payload["run_dir"] = str(self.run_dir)
        return payload


@dataclass(slots=True)
class DeepsoilComparisonTolerancePolicy:
    surface_corrcoef_min: float = 0.95
    surface_nrmse_max: float = 0.20
    psa_nrmse_max: float = 0.20
    pga_pct_diff_abs_max: float = 20.0
    profile_nrmse_max: float | None = None
    hysteresis_stress_nrmse_max: float | None = None
    hysteresis_energy_pct_diff_abs_max: float | None = None


@dataclass(slots=True)
class DeepsoilComparisonBatchArtifacts:
    output_dir: Path
    json_path: Path
    markdown_path: Path


@dataclass(slots=True)
class DeepsoilComparisonBatchResult:
    manifest_path: Path
    total_cases: int
    passed_cases: int
    failed_cases: int
    policy: DeepsoilComparisonTolerancePolicy
    cases: list[dict[str, object]]
    artifacts: DeepsoilComparisonBatchArtifacts | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        artifacts = payload.get("artifacts")
        if isinstance(artifacts, dict):
            payload["artifacts"] = {
                key: str(value) if isinstance(value, Path) else value
                for key, value in artifacts.items()
            }
        payload["manifest_path"] = str(self.manifest_path)
        return payload


def _load_numeric_table(path: Path) -> np.ndarray:
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        normalized = text.replace(";", ",")
        tokens = (
            [token.strip() for token in normalized.split(",")]
            if "," in normalized
            else text.split()
        )
        values: list[float] = []
        failed = False
        for token in tokens:
            if not token:
                continue
            try:
                values.append(float(token))
            except ValueError:
                failed = True
                break
        if failed or not values:
            continue
        rows.append(values)

    if not rows:
        raise ValueError(f"No numeric rows found in reference table: {path}")

    width = max(len(row) for row in rows)
    consistent = [row for row in rows if len(row) == width]
    if not consistent:
        raise ValueError(f"No consistent numeric rows found in reference table: {path}")

    return np.asarray(consistent, dtype=np.float64)


def _load_reference_psa(path: Path) -> tuple[np.ndarray, np.ndarray]:
    table = _load_numeric_table(path)
    if table.ndim == 1 or table.shape[1] < 2:
        raise ValueError(
            f"Reference PSA table must include at least two numeric columns: {path}"
        )

    periods = np.asarray(table[:, 0], dtype=np.float64)
    psa = np.asarray(table[:, -1], dtype=np.float64)
    valid = np.isfinite(periods) & np.isfinite(psa) & (periods > 0.0)
    periods = periods[valid]
    psa = psa[valid]
    if periods.size < 3:
        raise ValueError(f"Reference PSA table has insufficient valid rows: {path}")

    order = np.argsort(periods)
    periods = periods[order]
    psa = psa[order]

    unique_periods, unique_indices = np.unique(periods, return_index=True)
    return unique_periods.astype(np.float64), psa[unique_indices].astype(np.float64)


def _interpolate_series(
    time: np.ndarray,
    values: np.ndarray,
    target_time: np.ndarray,
) -> np.ndarray:
    return np.asarray(np.interp(target_time, time, values), dtype=np.float64)


def _time_history_metrics(
    sw_time: np.ndarray,
    sw_acc: np.ndarray,
    ref_time: np.ndarray,
    ref_acc: np.ndarray,
    sw_dt: float,
    ref_dt: float,
) -> tuple[float, int, float, float, float, list[str]]:
    warnings: list[str] = []
    if sw_time.size < 2 or ref_time.size < 2:
        raise ValueError("Surface acceleration series must contain at least 2 samples.")

    start = max(float(sw_time[0]), float(ref_time[0]))
    end = min(float(sw_time[-1]), float(ref_time[-1]))
    if end <= start:
        raise ValueError("GeoWave and DEEPSOIL time histories do not overlap.")

    compare_dt = min(float(sw_dt), float(ref_dt))
    if not np.isfinite(compare_dt) or compare_dt <= 0.0:
        raise ValueError("Non-positive time step encountered in comparison inputs.")

    common_time = np.arange(start, end + 0.5 * compare_dt, compare_dt, dtype=np.float64)
    if common_time.size < 2:
        raise ValueError("Common comparison time axis is too short.")

    sw_interp = _interpolate_series(sw_time, sw_acc, common_time)
    ref_interp = _interpolate_series(ref_time, ref_acc, common_time)
    diff = sw_interp - ref_interp
    rmse = float(np.sqrt(np.mean(diff**2)))
    ref_peak = float(np.max(np.abs(ref_interp))) if ref_interp.size > 0 else 0.0
    nrmse = float(rmse / ref_peak) if ref_peak > 0.0 else float("nan")

    if ref_interp.size > 1 and np.std(sw_interp) > 0.0 and np.std(ref_interp) > 0.0:
        corr = float(np.corrcoef(sw_interp, ref_interp)[0, 1])
    else:
        corr = float("nan")

    dt_ratio = max(float(sw_dt), float(ref_dt)) / min(float(sw_dt), float(ref_dt))
    if dt_ratio > 1.05:
        warnings.append(
            f"Time-step mismatch detected (GeoWave={sw_dt:.6g}s, DEEPSOIL={ref_dt:.6g}s)."
        )

    overlap_duration = float(common_time[-1] - common_time[0]) if common_time.size > 1 else 0.0
    return overlap_duration, int(common_time.size), rmse, nrmse, corr, warnings


def _arias_intensity(acc: np.ndarray, dt: float) -> float:
    """Arias intensity: Ia = (pi / 2g) * integral(a^2 dt)."""
    return float(np.pi / (2.0 * 9.81) * np.sum(acc**2) * dt)


def _xcorr_metrics(
    sw_acc: np.ndarray,
    ref_acc: np.ndarray,
    dt: float,
) -> tuple[int, float, float]:
    """Cross-correlation lag (samples, seconds) and peak coefficient."""
    from scipy.signal import correlate

    n = max(len(sw_acc), len(ref_acc))
    corr = correlate(sw_acc[:n], ref_acc[:n], mode="full")
    norm = float(np.sqrt(np.sum(sw_acc[:n] ** 2) * np.sum(ref_acc[:n] ** 2)))
    if norm < 1.0e-20:
        return 0, 0.0, 0.0
    corr_norm = corr / norm
    peak_idx = int(np.argmax(corr_norm))
    lag_samples = peak_idx - (n - 1)
    lag_s = float(lag_samples) * dt
    peak_coeff = float(corr_norm[peak_idx])
    return lag_samples, lag_s, peak_coeff


def _gof_metrics(
    sw_time: np.ndarray,
    sw_acc: np.ndarray,
    ref_time: np.ndarray,
    ref_acc: np.ndarray,
    sw_dt: float,
    ref_dt: float,
) -> tuple[float, float, float, int, float, float]:
    """Compute Anderson (2004) GoF-inspired metrics.

    Returns (ia_sw, ia_ref, ia_ratio, xcorr_lag_samples, xcorr_lag_s, xcorr_peak).
    """
    compare_dt = min(float(sw_dt), float(ref_dt))
    if compare_dt <= 0.0:
        return 0.0, 0.0, 0.0, 0, 0.0, 0.0
    start = max(float(sw_time[0]), float(ref_time[0]))
    end = min(float(sw_time[-1]), float(ref_time[-1]))
    if end <= start:
        return 0.0, 0.0, 0.0, 0, 0.0, 0.0
    common_time = np.arange(start, end + 0.5 * compare_dt, compare_dt, dtype=np.float64)
    if common_time.size < 2:
        return 0.0, 0.0, 0.0, 0, 0.0, 0.0
    sw_interp = _interpolate_series(sw_time, sw_acc, common_time)
    ref_interp = _interpolate_series(ref_time, ref_acc, common_time)

    ia_sw = _arias_intensity(sw_interp, compare_dt)
    ia_ref = _arias_intensity(ref_interp, compare_dt)
    ia_ratio = ia_sw / ia_ref if ia_ref > 1.0e-20 else 0.0

    lag_samples, lag_s, peak_coeff = _xcorr_metrics(sw_interp, ref_interp, compare_dt)

    return ia_sw, ia_ref, ia_ratio, lag_samples, lag_s, peak_coeff


def _psa_metrics_from_arrays(
    sw_periods: np.ndarray,
    sw_psa: np.ndarray,
    ref_time: np.ndarray,
    ref_acc: np.ndarray,
    ref_dt: float,
    *,
    damping: float,
    ref_psa_path: Path | None,
) -> tuple[int, float, float, float, float, float, float, bool, list[str]]:
    warnings: list[str] = []
    if ref_psa_path is None:
        ref_spectra = compute_spectra(ref_acc, ref_dt, damping=damping, periods=sw_periods)
        common_periods = sw_periods
        ref_psa = ref_spectra.psa
        sw_common = sw_psa
        used_reference_psa_csv = False
    else:
        ref_periods, ref_psa_raw = _load_reference_psa(ref_psa_path)
        lo = max(float(np.min(sw_periods)), float(np.min(ref_periods)))
        hi = min(float(np.max(sw_periods)), float(np.max(ref_periods)))
        mask = (sw_periods >= lo) & (sw_periods <= hi)
        common_periods = sw_periods[mask]
        if common_periods.size < 3:
            raise ValueError(
                "Insufficient overlapping PSA periods between GeoWave and DEEPSOIL."
            )
        sw_common = sw_psa[mask]
        ref_psa = np.interp(common_periods, ref_periods, ref_psa_raw).astype(np.float64)
        used_reference_psa_csv = True

    diff = sw_common - ref_psa
    rmse = float(np.sqrt(np.mean(diff**2)))
    ref_peak = float(np.max(np.abs(ref_psa))) if ref_psa.size > 0 else 0.0
    nrmse = float(rmse / ref_peak) if ref_peak > 0.0 else float("nan")
    max_abs_diff = float(np.max(np.abs(diff))) if diff.size > 0 else float("nan")
    peak_idx = int(np.argmax(np.abs(ref_psa))) if ref_psa.size > 0 else 0
    peak_period = float(common_periods[peak_idx]) if common_periods.size > 0 else float("nan")
    peak_ref = float(ref_psa[peak_idx]) if ref_psa.size > 0 else 0.0
    sw_peak_idx = int(np.argmax(np.abs(sw_common))) if sw_common.size > 0 else 0
    sw_peak_period = (
        float(common_periods[sw_peak_idx]) if common_periods.size > 0 else float("nan")
    )
    peak_pct_diff = (
        float(100.0 * diff[peak_idx] / peak_ref)
        if peak_ref != 0.0 and diff.size > 0
        else float("nan")
    )
    peak_period_diff_pct = (
        float(100.0 * (sw_peak_period - peak_period) / peak_period)
        if peak_period > 0.0 and np.isfinite(sw_peak_period)
        else float("nan")
    )

    return (
        int(common_periods.size),
        rmse,
        nrmse,
        max_abs_diff,
        peak_pct_diff,
        peak_period,
        peak_period_diff_pct,
        used_reference_psa_csv,
        warnings,
    )


def _psa_metrics(
    store: ResultStore,
    ref_time: np.ndarray,
    ref_acc: np.ndarray,
    ref_dt: float,
    *,
    damping: float,
    ref_psa_path: Path | None,
) -> tuple[int, float, float, float, float, float, float, bool, list[str]]:
    warnings: list[str] = []
    if store.spectra_periods.size >= 3 and store.spectra_psa.size == store.spectra_periods.size:
        sw_periods = np.asarray(store.spectra_periods, dtype=np.float64)
        sw_psa = np.asarray(store.spectra_psa, dtype=np.float64)
    else:
        spectra = compute_spectra(store.acc_surface, store.dt_s, damping=damping)
        sw_periods = spectra.periods
        sw_psa = spectra.psa
        warnings.append("Run did not contain stored spectra; recomputed GeoWave PSA.")

    (
        point_count,
        rmse,
        nrmse,
        max_abs_diff,
        peak_pct_diff,
        peak_period,
        peak_period_diff_pct,
        used_reference_psa_csv,
        psa_warnings,
    ) = _psa_metrics_from_arrays(
        sw_periods,
        sw_psa,
        ref_time,
        ref_acc,
        ref_dt,
        damping=damping,
        ref_psa_path=ref_psa_path,
    )
    warnings.extend(psa_warnings)

    if ref_time.size > 0 and store.time.size > 0:
        if abs(float(store.time[-1]) - float(ref_time[-1])) > max(store.dt_s, ref_dt) * 2.0:
            warnings.append("Surface records have different end times; check truncation/windowing.")

    return (
        point_count,
        rmse,
        nrmse,
        max_abs_diff,
        peak_pct_diff,
        peak_period,
        peak_period_diff_pct,
        used_reference_psa_csv,
        warnings,
    )


def _pga_metrics(sw_acc: np.ndarray, ref_acc: np.ndarray) -> tuple[float, float, float, float]:
    sw_pga = float(np.max(np.abs(sw_acc))) if sw_acc.size > 0 else 0.0
    ref_pga = float(np.max(np.abs(ref_acc))) if ref_acc.size > 0 else 0.0
    ratio = float(sw_pga / ref_pga) if ref_pga > 0.0 else float("nan")
    pct_diff = float(100.0 * (sw_pga - ref_pga) / ref_pga) if ref_pga > 0.0 else float("nan")
    return sw_pga, ref_pga, ratio, pct_diff


def _resolve_manifest_path(base_dir: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Manifest case paths must be non-empty strings.")
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _as_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _normalize_header(text: str) -> str:
    normalized = text.strip().lower()
    for old, new in ((" ", "_"), ("-", "_"), ("/", "_"), ("(", ""), (")", "")):
        normalized = normalized.replace(old, new)
    return normalized


def _load_header_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Expected header row in reference CSV: {path}")
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append(
                {
                    _normalize_header(str(k)): str(v)
                    for k, v in row.items()
                    if k is not None
                }
            )
    if not rows:
        raise ValueError(f"No data rows found in reference CSV: {path}")
    return rows


def _optional_float_from_mapping(row: dict[str, str], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        raw = row.get(key)
        if raw is None:
            continue
        text = raw.strip()
        if not text:
            continue
        try:
            value = float(text)
        except ValueError:
            continue
        if np.isfinite(value):
            return float(value)
    return None


def _estimate_gmax_kpa(vs_m_s: float, unit_weight_kn_m3: float) -> float:
    if vs_m_s <= 0.0:
        return 1.0
    unit_weight = unit_weight_kn_m3 if unit_weight_kn_m3 > 0.0 else 18.0
    rho_kg_m3 = (unit_weight * 1000.0) / 9.81
    return float(max((rho_kg_m3 * vs_m_s * vs_m_s) / 1000.0, 1.0))


def _load_profile_reference(path: Path) -> dict[str, np.ndarray]:
    rows = _load_header_rows(path)
    depth: list[float] = []
    gamma_max: list[float] = []
    ru_max: list[float] = []
    sigma_v_eff_min: list[float] = []
    effective_stress_kpa: list[float] = []
    pga_g: list[float] = []
    max_displacement_m: list[float] = []
    max_strain_pct: list[float] = []
    max_stress_ratio: list[float] = []
    vs_m_s: list[float] = []
    implied_strength_kpa: list[float] = []
    normalized_implied_strength: list[float] = []
    implied_friction_angle_deg: list[float] = []
    keep_mask: list[bool] = []

    for row in rows:
        z_mid = _optional_float_from_mapping(row, ("z_mid_m", "depth_m", "depth", "z_m", "z"))
        if z_mid is None:
            z_top = _optional_float_from_mapping(row, ("z_top_m", "top_m"))
            z_bot = _optional_float_from_mapping(row, ("z_bottom_m", "z_bot_m", "bottom_m"))
            if z_top is not None and z_bot is not None:
                z_mid = 0.5 * (z_top + z_bot)
        if z_mid is None:
            continue
        depth.append(float(z_mid))
        gamma_max.append(
            _optional_float_from_mapping(row, ("gamma_max", "gamma", "max_gamma")) or float("nan")
        )
        ru_max.append(_optional_float_from_mapping(row, ("ru_max", "ru")) or float("nan"))
        sigma_v_eff_min.append(
            _optional_float_from_mapping(
                row,
                ("sigma_v_eff_min", "sigma_v_eff", "sigma_v_eff_min_kpa", "sigma_v_eff_kpa"),
            )
            or float("nan")
        )
        effective_stress_kpa.append(
            _optional_float_from_mapping(
                row,
                ("effective_stress_kpa", "effective_stress", "stress_kpa", "stress"),
            )
            or float("nan")
        )
        pga_g.append(_optional_float_from_mapping(row, ("pga_g", "pga")) or float("nan"))
        max_displacement_m.append(
            _optional_float_from_mapping(
                row,
                ("max_displacement_m", "maximum_displacement", "displacement_m"),
            )
            or float("nan")
        )
        max_strain_pct.append(
            _optional_float_from_mapping(
                row,
                ("max_strain_pct", "max_strain", "strain_pct", "strain"),
            )
            or float("nan")
        )
        max_stress_ratio.append(
            _optional_float_from_mapping(
                row,
                ("max_stress_ratio", "stress_ratio", "shear_stress_ratio"),
            )
            or float("nan")
        )
        vs_m_s.append(_optional_float_from_mapping(row, ("vs_m_s", "vs")) or float("nan"))
        implied_strength_kpa.append(
            _optional_float_from_mapping(
                row,
                ("implied_strength_kpa", "implied_strength", "imp_strength_kpa"),
            )
            or float("nan")
        )
        normalized_implied_strength.append(
            _optional_float_from_mapping(
                row,
                (
                    "normalized_implied_strength",
                    "normalized_strength",
                    "normalized_imp_strength",
                ),
            )
            or float("nan")
        )
        implied_friction_angle_deg.append(
            _optional_float_from_mapping(
                row,
                (
                    "implied_friction_angle_deg",
                    "implied_friction_angle",
                    "imp_friction_angle_deg",
                    "phi_deg",
                ),
            )
            or float("nan")
        )
        keep_mask.append(True)

    if not keep_mask:
        raise ValueError(f"Profile reference CSV must include depth headers: {path}")

    order = np.argsort(np.asarray(depth, dtype=np.float64))
    return {
        "depth_m": np.asarray(depth, dtype=np.float64)[order],
        "gamma_max": np.asarray(gamma_max, dtype=np.float64)[order],
        "ru_max": np.asarray(ru_max, dtype=np.float64)[order],
        "sigma_v_eff_min": np.asarray(sigma_v_eff_min, dtype=np.float64)[order],
        "effective_stress_kpa": np.asarray(effective_stress_kpa, dtype=np.float64)[order],
        "pga_g": np.asarray(pga_g, dtype=np.float64)[order],
        "max_displacement_m": np.asarray(max_displacement_m, dtype=np.float64)[order],
        "max_strain_pct": np.asarray(max_strain_pct, dtype=np.float64)[order],
        "max_stress_ratio": np.asarray(max_stress_ratio, dtype=np.float64)[order],
        "vs_m_s": np.asarray(vs_m_s, dtype=np.float64)[order],
        "implied_strength_kpa": np.asarray(implied_strength_kpa, dtype=np.float64)[order],
        "normalized_implied_strength": np.asarray(
            normalized_implied_strength,
            dtype=np.float64,
        )[order],
        "implied_friction_angle_deg": np.asarray(
            implied_friction_angle_deg,
            dtype=np.float64,
        )[order],
    }


def _load_matrix_safe(path: Path) -> np.ndarray | None:
    if not path.exists() or path.stat().st_size <= 0:
        return None
    try:
        arr = np.loadtxt(path, ndmin=2)
    except Exception:
        return None
    matrix = np.asarray(arr, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 4:
        return None
    return matrix


def _looks_like_time_axis(values: np.ndarray) -> bool:
    if values.size < 3 or not np.all(np.isfinite(values)):
        return False
    diffs = np.diff(values)
    if diffs.size == 0 or not np.all(diffs >= -1.0e-12):
        return False
    return float(np.median(diffs)) > 0.0


def _extract_recorder_component(matrix: np.ndarray) -> np.ndarray:
    if matrix.shape[1] <= 1:
        return np.asarray(matrix[:, 0], dtype=np.float64)
    start = 1 if _looks_like_time_axis(matrix[:, 0]) else 0
    values = matrix[:, start:]
    if values.size == 0:
        values = matrix
    return np.asarray(values[:, -1], dtype=np.float64)


def _read_layer_pwp_profile_stats(
    run_dir: Path,
    *,
    layer_idx: int,
    sigma_v0_mid_kpa: float,
) -> tuple[float | None, float | None, float | None]:
    if sigma_v0_mid_kpa <= 0.0:
        return None, None, None
    candidates = [
        run_dir / f"layer_{layer_idx}_pwp_raw.out",
        run_dir / f"layer_{layer_idx + 1}_pwp_raw.out",
        run_dir / f"layer_{max(layer_idx - 1, 0)}_pwp_raw.out",
    ]
    pwp_path = next((path for path in candidates if path.exists()), None)
    if pwp_path is None:
        return None, None, None

    matrix = _load_matrix_safe(pwp_path)
    if matrix is None:
        return None, None, None
    pwp = _extract_recorder_component(matrix)
    if pwp.size == 0:
        return None, None, None
    delta_u = np.maximum(-pwp, 0.0)
    delta_u_max = float(np.max(delta_u)) if delta_u.size > 0 else None
    if delta_u_max is None:
        return None, None, None
    ru_max = float(np.clip(delta_u_max / sigma_v0_mid_kpa, 0.0, 1.5))
    sigma_v_eff_min = float(max(sigma_v0_mid_kpa - delta_u_max, 0.0))
    return ru_max, delta_u_max, sigma_v_eff_min


def _load_layer_response_summary(run_dir: Path) -> dict[int, dict[str, float]]:
    summary_path = run_dir / "layer_response_summary.csv"
    if not summary_path.exists():
        return {}
    rows: dict[int, dict[str, float]] = {}
    with summary_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                idx = int(float(row.get("layer_index", "")))
            except (TypeError, ValueError):
                continue
            payload: dict[str, float] = {}
            for field in ("gamma_max", "tau_peak_kpa", "secant_g_pa", "secant_g_over_gmax", "z_mid_m"):
                raw = row.get(field)
                try:
                    payload[field] = float(raw) if raw not in (None, "") else float("nan")
                except (TypeError, ValueError):
                    payload[field] = float("nan")
            rows[idx] = payload
    return rows


def _load_layer_calibration_stress_by_index(cfg: ProjectConfig | None) -> dict[int, float]:
    if cfg is None:
        return {}
    stresses: dict[int, float] = {}
    for idx, layer in enumerate(cfg.profile.layers):
        calibration = getattr(layer, "calibration", None)
        if calibration is None:
            continue
        mean_stress = getattr(calibration, "mean_effective_stress_kpa", None)
        if mean_stress is None:
            continue
        try:
            value = float(mean_stress)
        except (TypeError, ValueError):
            continue
        if np.isfinite(value) and value > 0.0:
            stresses[int(idx)] = value
    return stresses


def _load_profile_from_run(run_dir: Path) -> dict[str, np.ndarray]:
    sqlite_path = run_dir / "results.sqlite"
    if not sqlite_path.exists():
        raise ValueError(f"Profile comparison requires results.sqlite: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    try:
        layer_rows = conn.execute(
            "SELECT idx, name, thickness_m, unit_weight_kN_m3, vs_m_s, material "
            "FROM layers ORDER BY idx ASC"
        ).fetchall()
        mesh_by_name: dict[str, tuple[float, float, int]] = {}
        try:
            mesh_rows = conn.execute(
                "SELECT layer_name, MIN(z_top), MAX(z_bot), SUM(n_sub) "
                "FROM mesh_slices GROUP BY layer_name"
            ).fetchall()
            for name, z_top, z_bot, n_sub in mesh_rows:
                mesh_by_name[str(name)] = (
                    float(z_top),
                    float(z_bot),
                    max(1, int(float(n_sub))),
                )
        except sqlite3.Error:
            pass

        gamma_by_idx: dict[int, float] = {}
        try:
            eql_rows = conn.execute(
                "SELECT layer_idx, gamma_max FROM eql_layers ORDER BY layer_idx ASC"
            ).fetchall()
            for idx, gamma in eql_rows:
                try:
                    gamma_by_idx[int(idx)] = float(gamma)
                except (TypeError, ValueError):
                    continue
        except sqlite3.Error:
            pass
    finally:
        conn.close()

    z_mid: list[float] = []
    gamma_max: list[float] = []
    ru_max: list[float] = []
    sigma_v_eff_min: list[float] = []
    effective_stress_kpa: list[float] = []
    pga_g: list[float] = []
    max_displacement_m: list[float] = []
    max_strain_pct: list[float] = []
    max_stress_ratio: list[float] = []
    mobilized_strength_kpa: list[float] = []
    mobilized_friction_angle_deg: list[float] = []
    vs_values: list[float] = []
    implied_strength_kpa: list[float] = []
    normalized_implied_strength: list[float] = []
    implied_friction_angle_deg: list[float] = []
    layer_index_values: list[float] = []
    diagnostics_by_idx: dict[int, object] = {}
    layer_response_summary = _load_layer_response_summary(run_dir)
    store = load_result(run_dir)
    calibration_stress_by_idx: dict[int, float] = {}
    node_pga_g = np.array([], dtype=np.float64)
    node_max_disp = np.array([], dtype=np.float64)
    if store.node_depth_m.size > 0 and store.nodal_displacement_m.ndim == 2:
        node_depth = np.asarray(store.node_depth_m, dtype=np.float64).reshape(-1)
        disp = np.asarray(store.nodal_displacement_m, dtype=np.float64)
        if disp.shape[0] == node_depth.size and disp.shape[1] > 1 and store.dt_s > 0.0:
            node_max_disp = np.max(np.abs(disp), axis=1)
            vel = np.gradient(disp, store.dt_s, axis=1)
            acc = np.gradient(vel, store.dt_s, axis=1)
            node_pga_g = np.max(np.abs(acc), axis=1) / 9.81

    cfg = _load_run_config_snapshot(run_dir)
    if cfg is not None:
        calibration_stress_by_idx = _load_layer_calibration_stress_by_index(cfg)
        try:
            diagnostics = compute_profile_diagnostics(
                list(cfg.profile.layers),
                water_table_depth_m=cfg.profile.water_table_depth_m,
            )
            diagnostics_by_idx = {int(row.index): row for row in diagnostics}
        except Exception:
            diagnostics_by_idx = {}

    cum_depth = 0.0
    for idx, name, thickness, unit_weight, vs, _material in layer_rows:
        layer_idx = int(idx)
        layer_name = str(name)
        t_m = float(thickness)
        default_top = float(cum_depth)
        default_bot = float(cum_depth + t_m)
        cum_depth = default_bot
        z_top_m, z_bottom_m, _n_sub = mesh_by_name.get(
            layer_name,
            (default_top, default_bot, 1),
        )
        z_mid_m = 0.5 * (float(z_top_m) + float(z_bottom_m))
        sigma_v0_mid_kpa = z_mid_m * float(unit_weight)
        ru_i, _delta_u_i, sigma_eff_i = _read_layer_pwp_profile_stats(
            run_dir,
            layer_idx=layer_idx,
            sigma_v0_mid_kpa=sigma_v0_mid_kpa,
        )
        response_row = layer_response_summary.get(layer_idx, {})
        gamma_val = response_row.get("gamma_max")
        if gamma_val is None or not np.isfinite(gamma_val):
            gamma_val = gamma_by_idx.get(layer_idx)
        if gamma_val is None or not np.isfinite(gamma_val):
            gamma_val = gamma_by_idx.get(layer_idx + 1)

        z_mid.append(z_mid_m)
        layer_index_values.append(float(layer_idx))
        gamma_max.append(float(gamma_val) if gamma_val is not None else float("nan"))
        ru_max.append(float(ru_i) if ru_i is not None else float("nan"))
        sigma_v_eff_min.append(float(sigma_eff_i) if sigma_eff_i is not None else float("nan"))
        vs_values.append(float(vs))
        diag = diagnostics_by_idx.get(layer_idx)
        if diag is None:
            diag = diagnostics_by_idx.get(layer_idx - 1)
        sigma_mid_eff_from_calibration = calibration_stress_by_idx.get(layer_idx)
        if sigma_mid_eff_from_calibration is None:
            sigma_mid_eff_from_calibration = calibration_stress_by_idx.get(layer_idx - 1)
        sigma_mid_eff = (
            float(sigma_mid_eff_from_calibration)
            if sigma_mid_eff_from_calibration is not None
            else (
                float(getattr(diag, "sigma_v_eff_mid_kpa"))
                if diag is not None and getattr(diag, "sigma_v_eff_mid_kpa", None) is not None
                else (float(sigma_eff_i) if sigma_eff_i is not None else float("nan"))
            )
        )
        effective_stress_kpa.append(sigma_mid_eff)
        if node_max_disp.size == store.node_depth_m.size and node_max_disp.size > 0:
            max_displacement_m.append(
                float(np.interp(z_mid_m, store.node_depth_m, node_max_disp))
            )
        else:
            max_displacement_m.append(float("nan"))
        if node_pga_g.size == store.node_depth_m.size and node_pga_g.size > 0:
            pga_g.append(float(np.interp(z_mid_m, store.node_depth_m, node_pga_g)))
        else:
            pga_g.append(float("nan"))
        max_strain_pct.append(
            float(gamma_val * 100.0) if gamma_val is not None and np.isfinite(gamma_val) else float("nan")
        )
        tau_peak_kpa = response_row.get("tau_peak_kpa")
        if tau_peak_kpa is not None and np.isfinite(tau_peak_kpa) and sigma_mid_eff > 0.0:
            max_stress_ratio.append(float(tau_peak_kpa / sigma_mid_eff))
            mobilized_strength_kpa.append(float(tau_peak_kpa))
            mobilized_friction_angle_deg.append(
                float(np.degrees(np.arctan(float(tau_peak_kpa) / sigma_mid_eff)))
            )
        else:
            max_stress_ratio.append(float("nan"))
            mobilized_strength_kpa.append(float("nan"))
            mobilized_friction_angle_deg.append(float("nan"))
        implied_strength_kpa.append(
            float(getattr(diag, "implied_strength_kpa"))
            if diag is not None and getattr(diag, "implied_strength_kpa") is not None
            else float("nan")
        )
        normalized_implied_strength.append(
            float(getattr(diag, "normalized_implied_strength"))
            if diag is not None and getattr(diag, "normalized_implied_strength") is not None
            else float("nan")
        )
        implied_friction_angle_deg.append(
            float(getattr(diag, "implied_friction_angle_deg"))
            if diag is not None and getattr(diag, "implied_friction_angle_deg") is not None
            else float("nan")
        )

    if not z_mid:
        raise ValueError(f"No layer profile data found in run sqlite: {sqlite_path}")

    return {
        "layer_index": np.asarray(layer_index_values, dtype=np.float64),
        "depth_m": np.asarray(z_mid, dtype=np.float64),
        "gamma_max": np.asarray(gamma_max, dtype=np.float64),
        "ru_max": np.asarray(ru_max, dtype=np.float64),
        "sigma_v_eff_min": np.asarray(sigma_v_eff_min, dtype=np.float64),
        "effective_stress_kpa": np.asarray(effective_stress_kpa, dtype=np.float64),
        "pga_g": np.asarray(pga_g, dtype=np.float64),
        "max_displacement_m": np.asarray(max_displacement_m, dtype=np.float64),
        "max_strain_pct": np.asarray(max_strain_pct, dtype=np.float64),
        "max_stress_ratio": np.asarray(max_stress_ratio, dtype=np.float64),
        "mobilized_strength_kpa": np.asarray(mobilized_strength_kpa, dtype=np.float64),
        "mobilized_friction_angle_deg": np.asarray(
            mobilized_friction_angle_deg,
            dtype=np.float64,
        ),
        "vs_m_s": np.asarray(vs_values, dtype=np.float64),
        "implied_strength_kpa": np.asarray(implied_strength_kpa, dtype=np.float64),
        "normalized_implied_strength": np.asarray(
            normalized_implied_strength,
            dtype=np.float64,
        ),
        "implied_friction_angle_deg": np.asarray(
            implied_friction_angle_deg,
            dtype=np.float64,
        ),
    }


def _profile_metric_nrmse(
    sw_depth: np.ndarray,
    sw_values: np.ndarray,
    ref_depth: np.ndarray,
    ref_values: np.ndarray,
) -> tuple[int, float] | None:
    sw_mask = np.isfinite(sw_depth) & np.isfinite(sw_values)
    ref_mask = np.isfinite(ref_depth) & np.isfinite(ref_values)
    if int(np.count_nonzero(sw_mask)) < 1 or int(np.count_nonzero(ref_mask)) < 1:
        return None
    sw_d = sw_depth[sw_mask]
    sw_v = sw_values[sw_mask]
    ref_d = ref_depth[ref_mask]
    ref_v = ref_values[ref_mask]
    start = max(float(np.min(sw_d)), float(np.min(ref_d)))
    end = min(float(np.max(sw_d)), float(np.max(ref_d)))
    if end < start:
        return None
    if np.isclose(end, start):
        common_depth = np.asarray([start], dtype=np.float64)
    else:
        n = max(int(min(sw_d.size, ref_d.size)), 3)
        common_depth = np.linspace(start, end, n, dtype=np.float64)
    sw_i = np.interp(common_depth, sw_d, sw_v)
    ref_i = np.interp(common_depth, ref_d, ref_v)
    diff = sw_i - ref_i
    rmse = float(np.sqrt(np.mean(diff**2)))
    ref_peak = float(np.max(np.abs(ref_i))) if ref_i.size > 0 else 0.0
    nrmse = float(rmse / ref_peak) if ref_peak > 0.0 else float("nan")
    return int(common_depth.size), nrmse


def _layer_metric_nrmse(
    sw_idx: np.ndarray,
    sw_values: np.ndarray,
    ref_idx: np.ndarray,
    ref_values: np.ndarray,
) -> tuple[int, float] | None:
    sw_mask = np.isfinite(sw_idx) & np.isfinite(sw_values)
    ref_mask = np.isfinite(ref_idx) & np.isfinite(ref_values)
    if int(np.count_nonzero(sw_mask)) < 1 or int(np.count_nonzero(ref_mask)) < 1:
        return None
    sw_map = {int(round(idx)): float(val) for idx, val in zip(sw_idx[sw_mask], sw_values[sw_mask], strict=False)}
    ref_map = {int(round(idx)): float(val) for idx, val in zip(ref_idx[ref_mask], ref_values[ref_mask], strict=False)}
    common = sorted(set(sw_map) & set(ref_map))
    if not common:
        return None
    sw_arr = np.asarray([sw_map[idx] for idx in common], dtype=np.float64)
    ref_arr = np.asarray([ref_map[idx] for idx in common], dtype=np.float64)
    diff = sw_arr - ref_arr
    rmse = float(np.sqrt(np.mean(diff**2)))
    ref_peak = float(np.max(np.abs(ref_arr))) if ref_arr.size > 0 else 0.0
    nrmse = float(rmse / ref_peak) if ref_peak > 0.0 else float("nan")
    return int(len(common)), nrmse


def _load_mobilized_strength_reference(path: Path) -> dict[str, np.ndarray]:
    rows = _load_header_rows(path)
    layer_idx: list[float] = []
    shear_strength: list[float] = []
    friction_angle: list[float] = []
    for row in rows:
        layer = _optional_float_from_mapping(row, ("layer", "layer_idx", "layer_index"))
        strength = _optional_float_from_mapping(
            row,
            ("shear_strength_kpa", "shear_strength", "strength_kpa"),
        )
        friction = _optional_float_from_mapping(
            row,
            ("friction_angle_deg", "friction_angle", "phi_deg"),
        )
        if layer is None:
            continue
        # DeepSoil workbook uses 1-based layer numbering.
        layer_idx.append(float(layer) - 1.0)
        shear_strength.append(float(strength) if strength is not None else float("nan"))
        friction_angle.append(float(friction) if friction is not None else float("nan"))
    if not layer_idx:
        raise ValueError(f"Mobilized strength CSV requires layer rows: {path}")
    order = np.argsort(np.asarray(layer_idx, dtype=np.float64))
    return {
        "layer_index": np.asarray(layer_idx, dtype=np.float64)[order],
        "mobilized_strength_kpa": np.asarray(shear_strength, dtype=np.float64)[order],
        "mobilized_friction_angle_deg": np.asarray(friction_angle, dtype=np.float64)[order],
    }


def _compare_profile_metrics(
    run_dir: Path,
    profile_csv: Path,
    mobilized_strength_csv: Path | None = None,
) -> DeepsoilProfileComparison:
    sw_profile = _load_profile_from_run(run_dir)
    ref_profile = _load_profile_reference(profile_csv)
    compared_metrics: list[str] = []
    depth_points = 0
    metric_results: dict[str, float | None] = {
        "gamma_max_nrmse": None,
        "ru_max_nrmse": None,
        "sigma_v_eff_min_nrmse": None,
        "effective_stress_kpa_nrmse": None,
        "pga_g_nrmse": None,
        "max_displacement_m_nrmse": None,
        "max_strain_pct_nrmse": None,
        "max_stress_ratio_nrmse": None,
        "vs_m_s_nrmse": None,
        "implied_strength_kpa_nrmse": None,
        "normalized_implied_strength_nrmse": None,
        "implied_friction_angle_deg_nrmse": None,
        "mobilized_strength_nrmse": None,
        "mobilized_friction_angle_deg_nrmse": None,
    }
    for source_key, result_key in (
        ("gamma_max", "gamma_max_nrmse"),
        ("ru_max", "ru_max_nrmse"),
        ("sigma_v_eff_min", "sigma_v_eff_min_nrmse"),
        ("effective_stress_kpa", "effective_stress_kpa_nrmse"),
        ("pga_g", "pga_g_nrmse"),
        ("max_displacement_m", "max_displacement_m_nrmse"),
        ("max_strain_pct", "max_strain_pct_nrmse"),
        ("max_stress_ratio", "max_stress_ratio_nrmse"),
        ("vs_m_s", "vs_m_s_nrmse"),
        ("implied_strength_kpa", "implied_strength_kpa_nrmse"),
        ("normalized_implied_strength", "normalized_implied_strength_nrmse"),
        ("implied_friction_angle_deg", "implied_friction_angle_deg_nrmse"),
    ):
        compared = _profile_metric_nrmse(
            sw_profile["depth_m"],
            sw_profile[source_key],
            ref_profile["depth_m"],
            ref_profile[source_key],
        )
        if compared is None:
            continue
        n_points, nrmse = compared
        depth_points = max(depth_points, n_points)
        compared_metrics.append(source_key)
        metric_results[result_key] = nrmse
    if mobilized_strength_csv is not None:
        ref_mobilized = _load_mobilized_strength_reference(mobilized_strength_csv)
        for source_key, result_key in (
            ("mobilized_strength_kpa", "mobilized_strength_nrmse"),
            ("mobilized_friction_angle_deg", "mobilized_friction_angle_deg_nrmse"),
        ):
            compared = _layer_metric_nrmse(
                sw_profile["layer_index"],
                sw_profile[source_key],
                ref_mobilized["layer_index"],
                ref_mobilized[source_key],
            )
            if compared is None:
                continue
            n_points, nrmse = compared
            depth_points = max(depth_points, n_points)
            compared_metrics.append(source_key)
            metric_results[result_key] = nrmse
    if not compared_metrics:
        raise ValueError(f"No overlapping profile metrics found in reference CSV: {profile_csv}")
    return DeepsoilProfileComparison(
        depth_points=depth_points,
        compared_metrics=compared_metrics,
        gamma_max_nrmse=metric_results["gamma_max_nrmse"],
        ru_max_nrmse=metric_results["ru_max_nrmse"],
        sigma_v_eff_min_nrmse=metric_results["sigma_v_eff_min_nrmse"],
        effective_stress_kpa_nrmse=metric_results["effective_stress_kpa_nrmse"],
        pga_g_nrmse=metric_results["pga_g_nrmse"],
        max_displacement_m_nrmse=metric_results["max_displacement_m_nrmse"],
        max_strain_pct_nrmse=metric_results["max_strain_pct_nrmse"],
        max_stress_ratio_nrmse=metric_results["max_stress_ratio_nrmse"],
        vs_m_s_nrmse=metric_results["vs_m_s_nrmse"],
        implied_strength_kpa_nrmse=metric_results["implied_strength_kpa_nrmse"],
        normalized_implied_strength_nrmse=metric_results["normalized_implied_strength_nrmse"],
        implied_friction_angle_deg_nrmse=metric_results["implied_friction_angle_deg_nrmse"],
        mobilized_strength_nrmse=metric_results["mobilized_strength_nrmse"],
        mobilized_friction_angle_deg_nrmse=metric_results["mobilized_friction_angle_deg_nrmse"],
    )


def _load_reference_hysteresis(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rows = _load_header_rows(path)
    strain: list[float] = []
    stress: list[float] = []
    for row in rows:
        gamma = _optional_float_from_mapping(row, ("strain", "gamma", "shear_strain"))
        tau = _optional_float_from_mapping(row, ("stress", "tau", "shear_stress"))
        if gamma is None or tau is None:
            continue
        strain.append(float(gamma))
        stress.append(float(tau))
    if len(strain) < 8:
        table = _load_numeric_table(path)
        if table.ndim == 2 and table.shape[1] >= 2:
            return (
                np.asarray(table[:, 0], dtype=np.float64),
                np.asarray(table[:, -1], dtype=np.float64),
            )
        raise ValueError(f"Hysteresis reference CSV requires strain/stress columns: {path}")
    return np.asarray(strain, dtype=np.float64), np.asarray(stress, dtype=np.float64)


def _load_run_config_snapshot(run_dir: Path) -> ProjectConfig | None:
    candidates = [run_dir / "config_snapshot.json"]
    meta_path = run_dir / "run_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if isinstance(meta, dict):
            meta_snapshot = meta.get("config_snapshot")
            if isinstance(meta_snapshot, str) and meta_snapshot.strip():
                candidates.append(Path(meta_snapshot).expanduser())
    for path in candidates:
        if not path.exists():
            continue
        try:
            return load_project_config(path)
        except (OSError, ValueError):
            continue
    return None


def _layer_loop_profile(
    material: MaterialType,
    material_params: dict[str, float],
    vs_m_s: float,
    unit_weight_kn_m3: float,
) -> tuple[MaterialType, dict[str, float]]:
    params = dict(material_params)
    if material == MaterialType.MKZ:
        params.setdefault("gmax", _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3))
        params.setdefault("gamma_ref", 0.001)
        params.setdefault("damping_min", 0.01)
        params.setdefault("damping_max", 0.12)
        return MaterialType.MKZ, params
    if material == MaterialType.GQH:
        params.setdefault("gmax", _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3))
        params.setdefault("gamma_ref", 0.001)
        params.setdefault("a1", 1.0)
        params.setdefault("a2", 0.35)
        params.setdefault("m", 2.0)
        params.setdefault("damping_min", 0.01)
        params.setdefault("damping_max", 0.12)
        return MaterialType.GQH, params
    proxy_gamma_ref = 0.0012 if material == MaterialType.PM4SAND else 0.0018
    if material == MaterialType.ELASTIC:
        proxy_gamma_ref = 0.0005
    return MaterialType.MKZ, {
        "gmax": _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3),
        "gamma_ref": proxy_gamma_ref,
        "damping_min": 0.01,
        "damping_max": 0.10,
    }


def _load_layer_recorded_hysteresis(
    run_dir: Path,
    *,
    layer_index_zero_based: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    tag_candidates = [
        layer_index_zero_based + 1,
        layer_index_zero_based,
        max(layer_index_zero_based - 1, 0),
    ]
    seen: set[int] = set()
    for tag in tag_candidates:
        if tag in seen:
            continue
        seen.add(tag)
        strain_path = run_dir / f"layer_{tag}_strain.out"
        stress_path = run_dir / f"layer_{tag}_stress.out"
        strain_raw = _load_matrix_safe(strain_path)
        stress_raw = _load_matrix_safe(stress_path)
        if strain_raw is None or stress_raw is None:
            continue
        strain = _extract_recorder_component(strain_raw)
        stress = _extract_recorder_component(stress_raw)
        n = int(min(strain.size, stress.size))
        if n < 8:
            continue
        finite = np.isfinite(strain[:n]) & np.isfinite(stress[:n])
        if int(np.count_nonzero(finite)) < 8:
            continue
        return (
            np.asarray(strain[:n][finite], dtype=np.float64),
            np.asarray(stress[:n][finite], dtype=np.float64),
        )
    return None


def _load_layer_material_context(
    run_dir: Path,
    layer_index_zero_based: int,
) -> tuple[MaterialType, dict[str, float], float, float]:
    cfg = _load_run_config_snapshot(run_dir)
    if cfg is not None and 0 <= layer_index_zero_based < len(cfg.profile.layers):
        layer = cfg.profile.layers[layer_index_zero_based]
        params = {k: float(v) for k, v in layer.material_params.items()}
        return layer.material, params, float(layer.vs_m_s), float(layer.unit_weight_kn_m3)

    sqlite_path = run_dir / "results.sqlite"
    if not sqlite_path.exists():
        raise ValueError(f"Hysteresis compare requires config snapshot or sqlite layers: {run_dir}")
    conn = sqlite3.connect(sqlite_path)
    try:
        row = conn.execute(
            "SELECT material, vs_m_s, unit_weight_kN_m3 FROM layers WHERE idx = ?",
            (layer_index_zero_based,),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT material, vs_m_s, unit_weight_kN_m3 "
                "FROM layers ORDER BY idx ASC LIMIT 1 OFFSET ?",
                (layer_index_zero_based,),
            ).fetchone()
        if row is None:
            raise ValueError(
                f"Layer index not found for hysteresis compare: {layer_index_zero_based}"
            )
        material = MaterialType(str(row[0]))
        return material, {}, float(row[1]), float(row[2])
    finally:
        conn.close()


def _load_run_hysteresis(
    run_dir: Path,
    *,
    layer_index: int,
) -> tuple[np.ndarray, np.ndarray]:
    recorded = _load_layer_recorded_hysteresis(run_dir, layer_index_zero_based=layer_index)
    if recorded is not None:
        return recorded

    material, params, vs_m_s, unit_weight = _load_layer_material_context(run_dir, layer_index)
    loop_material, loop_params = _layer_loop_profile(material, params, vs_m_s, unit_weight)
    store = load_result(run_dir)
    pga = float(np.max(np.abs(store.acc_surface))) if store.acc_surface.size > 0 else 0.0
    pga_g = max(pga / 9.81, 0.0)
    ru_max = float(np.max(store.ru)) if store.ru.size > 0 else 0.0
    gamma_ref = float(loop_params.get("gamma_ref", 0.001))
    gamma_a = float(
        np.clip(
            5.0 * gamma_ref * (1.0 + (1.2 * pga_g) + (0.6 * ru_max)),
            2.5e-4,
            2.0e-2,
        )
    )
    loop = generate_masing_loop(
        material=loop_material,
        material_params=loop_params,
        strain_amplitude=gamma_a,
        n_points_per_branch=140,
    )
    return np.asarray(loop.strain, dtype=np.float64), np.asarray(loop.stress, dtype=np.float64)


def _rotate_loop_to_anchor(strain: np.ndarray, stress: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if strain.size == 0:
        return strain, stress
    idx = int(np.argmin(strain))
    return np.roll(strain, -idx), np.roll(stress, -idx)


def _resample_loop_by_arclength(
    strain: np.ndarray,
    stress: np.ndarray,
    n_points: int = 240,
) -> tuple[np.ndarray, np.ndarray]:
    if strain.size != stress.size or strain.size < 4:
        raise ValueError("Loop compare requires matching strain/stress vectors.")
    ds = np.sqrt(np.diff(strain) ** 2 + np.diff(stress) ** 2)
    s = np.concatenate(([0.0], np.cumsum(ds)))
    if float(s[-1]) <= 0.0:
        raise ValueError("Loop arc length is zero.")
    s_norm = s / float(s[-1])
    target = np.linspace(0.0, 1.0, n_points, dtype=np.float64)
    return (
        np.interp(target, s_norm, strain).astype(np.float64),
        np.interp(target, s_norm, stress).astype(np.float64),
    )


def _compare_hysteresis_metrics(
    run_dir: Path,
    hysteresis_csv: Path,
    *,
    layer_index: int,
) -> DeepsoilHysteresisComparison:
    sw_strain, sw_stress = _load_run_hysteresis(run_dir, layer_index=layer_index)
    ref_strain, ref_stress = _load_reference_hysteresis(hysteresis_csv)
    sw_strain, sw_stress = _rotate_loop_to_anchor(sw_strain, sw_stress)
    ref_strain, ref_stress = _rotate_loop_to_anchor(ref_strain, ref_stress)
    sw_strain_r, sw_stress_r = _resample_loop_by_arclength(sw_strain, sw_stress)
    ref_strain_r, ref_stress_r = _resample_loop_by_arclength(ref_strain, ref_stress)

    stress_diff = sw_stress_r - ref_stress_r
    ref_stress_peak = float(np.max(np.abs(ref_stress_r))) if ref_stress_r.size > 0 else 0.0
    stress_rmse = float(np.sqrt(np.mean(stress_diff**2)))
    stress_nrmse = float(stress_rmse / ref_stress_peak) if ref_stress_peak > 0.0 else float("nan")

    sw_gamma_peak = float(np.max(np.abs(sw_strain_r))) if sw_strain_r.size > 0 else 0.0
    ref_gamma_peak = float(np.max(np.abs(ref_strain_r))) if ref_strain_r.size > 0 else 0.0
    sw_tau_peak = float(np.max(np.abs(sw_stress_r))) if sw_stress_r.size > 0 else 0.0
    ref_tau_peak = float(np.max(np.abs(ref_stress_r))) if ref_stress_r.size > 0 else 0.0
    sw_energy = float(abs(np.trapezoid(sw_stress_r, sw_strain_r)))
    ref_energy = float(abs(np.trapezoid(ref_stress_r, ref_strain_r)))

    gamma_peak_pct_diff = (
        float(100.0 * (sw_gamma_peak - ref_gamma_peak) / ref_gamma_peak)
        if ref_gamma_peak > 0.0
        else float("nan")
    )
    tau_peak_pct_diff = (
        float(100.0 * (sw_tau_peak - ref_tau_peak) / ref_tau_peak)
        if ref_tau_peak > 0.0
        else float("nan")
    )
    loop_energy_pct_diff = (
        float(100.0 * (sw_energy - ref_energy) / ref_energy)
        if ref_energy > 0.0
        else float("nan")
    )

    return DeepsoilHysteresisComparison(
        layer_index=layer_index,
        point_count=int(sw_strain_r.size),
        gamma_peak_pct_diff=gamma_peak_pct_diff,
        tau_peak_pct_diff=tau_peak_pct_diff,
        loop_energy_pct_diff=loop_energy_pct_diff,
        stress_path_nrmse=stress_nrmse,
    )


def _merge_tolerance_policy(
    base: DeepsoilComparisonTolerancePolicy,
    overrides: object,
) -> DeepsoilComparisonTolerancePolicy:
    if not isinstance(overrides, dict):
        return base
    return DeepsoilComparisonTolerancePolicy(
        surface_corrcoef_min=_as_float(
            overrides.get("surface_corrcoef_min"),
            base.surface_corrcoef_min,
        ),
        surface_nrmse_max=_as_float(
            overrides.get("surface_nrmse_max"),
            base.surface_nrmse_max,
        ),
        psa_nrmse_max=_as_float(
            overrides.get("psa_nrmse_max"),
            base.psa_nrmse_max,
        ),
        pga_pct_diff_abs_max=_as_float(
            overrides.get("pga_pct_diff_abs_max"),
            base.pga_pct_diff_abs_max,
        ),
        profile_nrmse_max=(
            _as_float(overrides.get("profile_nrmse_max"), 0.0)
            if overrides.get("profile_nrmse_max") is not None
            else base.profile_nrmse_max
        ),
        hysteresis_stress_nrmse_max=(
            _as_float(overrides.get("hysteresis_stress_nrmse_max"), 0.0)
            if overrides.get("hysteresis_stress_nrmse_max") is not None
            else base.hysteresis_stress_nrmse_max
        ),
        hysteresis_energy_pct_diff_abs_max=(
            _as_float(overrides.get("hysteresis_energy_pct_diff_abs_max"), 0.0)
            if overrides.get("hysteresis_energy_pct_diff_abs_max") is not None
            else base.hysteresis_energy_pct_diff_abs_max
        ),
    )


def _evaluate_case_policy(
    result: DeepsoilComparisonResult,
    policy: DeepsoilComparisonTolerancePolicy,
) -> dict[str, object]:
    checks = {
        "surface_corrcoef_min": bool(
            np.isfinite(result.surface_corrcoef)
            and result.surface_corrcoef >= policy.surface_corrcoef_min
        ),
        "surface_nrmse_max": bool(
            np.isfinite(result.surface_nrmse)
            and result.surface_nrmse <= policy.surface_nrmse_max
        ),
        "psa_nrmse_max": bool(
            np.isfinite(result.psa_nrmse) and result.psa_nrmse <= policy.psa_nrmse_max
        ),
        "pga_pct_diff_abs_max": bool(
            np.isfinite(result.pga_pct_diff)
            and abs(result.pga_pct_diff) <= policy.pga_pct_diff_abs_max
        ),
    }
    if result.profile is not None and policy.profile_nrmse_max is not None:
        profile_values = [
            value
            for value in (
                result.profile.gamma_max_nrmse,
                result.profile.ru_max_nrmse,
                result.profile.sigma_v_eff_min_nrmse,
                result.profile.vs_m_s_nrmse,
                result.profile.implied_strength_kpa_nrmse,
                result.profile.normalized_implied_strength_nrmse,
                result.profile.implied_friction_angle_deg_nrmse,
            )
            if value is not None and np.isfinite(value)
        ]
        checks["profile_nrmse_max"] = bool(profile_values) and (
            max(profile_values) <= policy.profile_nrmse_max
        )
    if result.hysteresis is not None and policy.hysteresis_stress_nrmse_max is not None:
        checks["hysteresis_stress_nrmse_max"] = bool(
            np.isfinite(result.hysteresis.stress_path_nrmse)
            and result.hysteresis.stress_path_nrmse <= policy.hysteresis_stress_nrmse_max
        )
    if result.hysteresis is not None and policy.hysteresis_energy_pct_diff_abs_max is not None:
        checks["hysteresis_energy_pct_diff_abs_max"] = bool(
            np.isfinite(result.hysteresis.loop_energy_pct_diff)
            and abs(result.hysteresis.loop_energy_pct_diff)
            <= policy.hysteresis_energy_pct_diff_abs_max
        )
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "policy": asdict(policy),
    }


def render_deepsoil_comparison_markdown(
    result: DeepsoilComparisonResult,
    *,
    surface_csv: Path | None,
    psa_csv: Path | None,
    profile_csv: Path | None,
    hysteresis_csv: Path | None,
    input_motion_csv: Path | None = None,
    input_psa_csv: Path | None = None,
    mobilized_strength_csv: Path | None = None,
    deepsoil_excel: Path | None = None,
) -> str:
    warnings_block = (
        "\n".join(f"- {warning}" for warning in result.warnings)
        if result.warnings
        else "- None"
    )
    psa_source = (
        str(psa_csv)
        if psa_csv is not None
        else "computed from DEEPSOIL surface acceleration"
    )
    input_psa_source = (
        str(input_psa_csv)
        if input_psa_csv is not None
        else "computed from DEEPSOIL input acceleration"
    )
    profile_source = str(profile_csv) if profile_csv is not None else "not provided"
    hysteresis_source = str(hysteresis_csv) if hysteresis_csv is not None else "not provided"
    input_motion_source = str(input_motion_csv) if input_motion_csv is not None else "not provided"
    mobilized_source = (
        str(mobilized_strength_csv) if mobilized_strength_csv is not None else "not provided"
    )
    workbook_source = str(deepsoil_excel) if deepsoil_excel is not None else "not provided"
    profile_block: list[str] = []
    if result.profile is not None:
        profile_block.extend(
            [
                "## Profile",
                f"- Profile CSV: `{profile_source}`",
                f"- Mobilized strength CSV: `{mobilized_source}`",
                f"- Depth points compared: `{result.profile.depth_points}`",
                f"- Compared metrics: `{', '.join(result.profile.compared_metrics)}`",
                f"- gamma_max NRMSE: `{result.profile.gamma_max_nrmse}`",
                f"- ru_max NRMSE: `{result.profile.ru_max_nrmse}`",
                f"- sigma'_v,min NRMSE: `{result.profile.sigma_v_eff_min_nrmse}`",
                f"- Effective stress NRMSE: `{result.profile.effective_stress_kpa_nrmse}`",
                f"- PGA-vs-depth NRMSE: `{result.profile.pga_g_nrmse}`",
                f"- Max displacement NRMSE: `{result.profile.max_displacement_m_nrmse}`",
                f"- Max strain NRMSE: `{result.profile.max_strain_pct_nrmse}`",
                f"- Max stress ratio NRMSE: `{result.profile.max_stress_ratio_nrmse}`",
                f"- Vs NRMSE: `{result.profile.vs_m_s_nrmse}`",
                f"- Implied strength NRMSE: `{result.profile.implied_strength_kpa_nrmse}`",
                f"- Normalized implied strength NRMSE: `{result.profile.normalized_implied_strength_nrmse}`",
                f"- Implied friction angle NRMSE: `{result.profile.implied_friction_angle_deg_nrmse}`",
                f"- Mobilized strength NRMSE: `{result.profile.mobilized_strength_nrmse}`",
                f"- Mobilized friction angle NRMSE: `{result.profile.mobilized_friction_angle_deg_nrmse}`",
                "",
            ]
        )
    hysteresis_block: list[str] = []
    if result.hysteresis is not None:
        hysteresis_block.extend(
            [
                "## Hysteresis",
                f"- Hysteresis CSV: `{hysteresis_source}`",
                f"- Layer index: `{result.hysteresis.layer_index}`",
                f"- Resampled points: `{result.hysteresis.point_count}`",
                f"- Stress-path NRMSE: `{result.hysteresis.stress_path_nrmse:.6f}`",
                f"- Loop energy diff: `{result.hysteresis.loop_energy_pct_diff:.3f}` %",
                f"- tau_peak diff: `{result.hysteresis.tau_peak_pct_diff:.3f}` %",
                f"- gamma_peak diff: `{result.hysteresis.gamma_peak_pct_diff:.3f}` %",
                "",
            ]
        )
    return "\n".join(
        [
            f"# DEEPSOIL Comparison: {result.run_id}",
            "",
            "## Inputs",
            f"- GeoWave run: `{result.run_dir}`",
            f"- DEEPSOIL workbook: `{workbook_source}`",
            f"- DEEPSOIL surface CSV: `{surface_csv if surface_csv is not None else 'not provided'}`",
            f"- DEEPSOIL input motion CSV: `{input_motion_source}`",
            f"- DEEPSOIL PSA source: `{psa_source}`",
            f"- DEEPSOIL input PSA source: `{input_psa_source}`",
            f"- Reference kind: `{result.reference_kind}`",
            "",
            "## Semantics",
            f"- Boundary condition: `{result.boundary_condition}`",
            f"- Motion input type: `{result.motion_input_type}`",
            f"- Damping mode: `{result.damping_mode}`",
            f"- Input dt used: `{result.input_dt_used_s}` s",
            f"- Input PGA as loaded: `{result.input_pga_loaded_m_s2}` m/s^2",
            f"- Applied input PGA: `{result.applied_input_pga_loaded_m_s2}` m/s^2",
            f"- Base motion semantics ok: `{result.base_motion_semantics_ok}`",
            "",
            "## Surface Acceleration",
            f"- GeoWave dt: `{result.stratawave_dt_s:.8f}` s",
            f"- DEEPSOIL dt: `{result.deepsoil_dt_s:.8f}` s",
            f"- Overlap duration: `{result.overlap_duration_s:.4f}` s",
            f"- Overlap samples: `{result.overlap_samples}`",
            f"- PGA (GeoWave): `{result.stratawave_pga_m_s2:.6f}` m/s^2",
            f"- PGA (DEEPSOIL): `{result.deepsoil_pga_m_s2:.6f}` m/s^2",
            f"- PGA ratio: `{result.pga_ratio:.6f}`",
            f"- PGA diff: `{result.pga_pct_diff:.3f}` %",
            f"- Surface RMSE: `{result.surface_rmse_m_s2:.6f}` m/s^2",
            f"- Surface NRMSE: `{result.surface_nrmse:.6f}`",
            f"- Surface correlation: `{result.surface_corrcoef:.6f}`",
            "",
            "## PSA",
            f"- PSA points compared: `{result.psa_point_count}`",
            f"- PSA RMSE: `{result.psa_rmse_m_s2:.6f}` m/s^2",
            f"- PSA NRMSE: `{result.psa_nrmse:.6f}`",
            f"- PSA max abs diff: `{result.psa_max_abs_diff_m_s2:.6f}` m/s^2",
            f"- PSA diff at reference peak: `{result.psa_pct_diff_at_peak:.3f}` %",
            f"- Reference peak period: `{result.psa_peak_period_s:.4f}` s",
            f"- Surface PSA peak-period diff: `{result.surface_psa_peak_period_diff_pct}` %",
            "",
            "## Input Motion",
            f"- Input history NRMSE: `{result.input_history_nrmse}`",
            f"- Input PSA NRMSE: `{result.input_psa_nrmse}`",
            f"- Applied input history NRMSE: `{result.applied_input_history_nrmse}`",
            f"- Applied input PSA NRMSE: `{result.applied_input_psa_nrmse}`",
            "",
            *profile_block,
            *hysteresis_block,
            "## Warnings",
            warnings_block,
            "",
        ]
    )


def render_deepsoil_comparison_batch_markdown(
    result: DeepsoilComparisonBatchResult,
) -> str:
    lines = [
        "# DEEPSOIL Comparison Batch",
        "",
        f"- Manifest: `{result.manifest_path}`",
        f"- Total cases: `{result.total_cases}`",
        f"- Passed: `{result.passed_cases}`",
        f"- Failed: `{result.failed_cases}`",
        "",
        "## Policy",
        f"- surface_corrcoef_min: `{result.policy.surface_corrcoef_min:.4f}`",
        f"- surface_nrmse_max: `{result.policy.surface_nrmse_max:.4f}`",
        f"- psa_nrmse_max: `{result.policy.psa_nrmse_max:.4f}`",
        f"- pga_pct_diff_abs_max: `{result.policy.pga_pct_diff_abs_max:.4f}`",
        f"- profile_nrmse_max: `{result.policy.profile_nrmse_max}`",
        f"- hysteresis_stress_nrmse_max: `{result.policy.hysteresis_stress_nrmse_max}`",
        (
            "- hysteresis_energy_pct_diff_abs_max: "
            f"`{result.policy.hysteresis_energy_pct_diff_abs_max}`"
        ),
        "",
        "## Cases",
    ]
    for case in result.cases:
        metrics_raw = case.get("metrics", {})
        metrics = metrics_raw if isinstance(metrics_raw, dict) else {}
        checks_raw = case.get("checks", {})
        checks = checks_raw if isinstance(checks_raw, dict) else {}
        lines.extend(
            [
                f"### {case.get('name', 'unnamed')}",
                f"- Passed: `{case.get('passed', False)}`",
                f"- Run: `{case.get('run_dir', '')}`",
                f"- Surface CSV: `{case.get('surface_csv', '')}`",
                f"- PSA CSV: `{case.get('psa_csv', '')}`",
                f"- Profile CSV: `{case.get('profile_csv', '')}`",
                f"- Hysteresis CSV: `{case.get('hysteresis_csv', '')}`",
                f"- PGA diff (%): `{metrics.get('pga_pct_diff', float('nan')):.3f}`",
                f"- Surface corr: `{metrics.get('surface_corrcoef', float('nan')):.6f}`",
                f"- Surface NRMSE: `{metrics.get('surface_nrmse', float('nan')):.6f}`",
                f"- PSA NRMSE: `{metrics.get('psa_nrmse', float('nan')):.6f}`",
                f"- Profile metrics: `{metrics.get('profile', {})}`",
                f"- Hysteresis metrics: `{metrics.get('hysteresis', {})}`",
                f"- Checks: `{checks}`",
                "",
            ]
        )
    return "\n".join(lines)


def compare_deepsoil_run(
    run_dir: str | Path,
    *,
    surface_csv: str | Path | None = None,
    input_motion_csv: str | Path | None = None,
    psa_csv: str | Path | None = None,
    input_psa_csv: str | Path | None = None,
    profile_csv: str | Path | None = None,
    mobilized_strength_csv: str | Path | None = None,
    hysteresis_csv: str | Path | None = None,
    deepsoil_excel: str | Path | None = None,
    hysteresis_layer: int = 0,
    out_dir: str | Path | None = None,
    surface_dt_override: float | None = None,
    damping: float = 0.05,
) -> DeepsoilComparisonResult:
    run_path = Path(run_dir)
    store = load_result(run_path)
    output_dir = Path(out_dir) if out_dir is not None else None
    imported_bundle = None
    if deepsoil_excel is not None:
        bundle_dir = (
            output_dir / "_deepsoil_bundle"
            if output_dir is not None
            else run_path / "_deepsoil_bundle"
        )
        imported_bundle = import_deepsoil_excel_bundle(deepsoil_excel, bundle_dir)
        surface_csv = surface_csv or imported_bundle.surface_csv
        input_motion_csv = input_motion_csv or imported_bundle.input_motion_csv
        psa_csv = psa_csv or imported_bundle.psa_surface_csv
        input_psa_csv = input_psa_csv or imported_bundle.psa_input_csv
        profile_csv = profile_csv or imported_bundle.profile_csv
        mobilized_strength_csv = mobilized_strength_csv or imported_bundle.mobilized_strength_csv
        hysteresis_csv = hysteresis_csv or imported_bundle.hysteresis_csv
    if surface_csv is None:
        raise ValueError("compare_deepsoil_run requires surface_csv or deepsoil_excel.")

    surface_path = Path(surface_csv)
    input_motion_path = Path(input_motion_csv) if input_motion_csv is not None else None
    ref_psa_path = Path(psa_csv) if psa_csv is not None else None
    ref_input_psa_path = Path(input_psa_csv) if input_psa_csv is not None else None
    ref_profile_path = Path(profile_csv) if profile_csv is not None else None
    ref_mobilized_path = (
        Path(mobilized_strength_csv) if mobilized_strength_csv is not None else None
    )
    ref_hysteresis_path = Path(hysteresis_csv) if hysteresis_csv is not None else None

    ref_time, ref_acc = load_motion_series(
        surface_path,
        dt_override=surface_dt_override,
        fallback_dt=store.dt_s,
    )
    ref_dt = float(np.median(np.diff(ref_time))) if ref_time.size > 1 else float(store.dt_s)
    warnings = list(imported_bundle.warnings) if imported_bundle is not None else []

    sw_pga, ref_pga, pga_ratio, pga_pct_diff = _pga_metrics(store.acc_surface, ref_acc)
    overlap_duration, overlap_samples, rmse, nrmse, corr, surface_warnings = _time_history_metrics(
        store.time,
        store.acc_surface,
        ref_time,
        ref_acc,
        store.dt_s,
        ref_dt,
    )
    warnings.extend(surface_warnings)
    ia_sw, ia_ref, ia_ratio, xcorr_lag, xcorr_lag_s, xcorr_peak = _gof_metrics(
        store.time,
        store.acc_surface,
        ref_time,
        ref_acc,
        store.dt_s,
        ref_dt,
    )
    (
        psa_point_count,
        psa_rmse,
        psa_nrmse,
        psa_max_abs_diff,
        psa_peak_pct_diff,
        psa_peak_period,
        surface_psa_peak_period_diff_pct,
        used_reference_psa_csv,
        psa_warnings,
    ) = _psa_metrics(
        store,
        ref_time,
        ref_acc,
        ref_dt,
        damping=damping,
        ref_psa_path=ref_psa_path,
    )
    warnings.extend(psa_warnings)
    cfg = _load_run_config_snapshot(run_path)
    input_history_nrmse: float | None = None
    input_psa_nrmse: float | None = None
    applied_input_history_nrmse: float | None = None
    applied_input_psa_nrmse: float | None = None
    if input_motion_path is not None and store.input_time.size > 1 and store.acc_input.size > 1:
        ref_input_time, ref_input_acc = load_motion_series(
            input_motion_path,
            dt_override=None,
            fallback_dt=store.input_dt_s if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0 else store.dt_s,
        )
        ref_input_dt = (
            float(np.median(np.diff(ref_input_time)))
            if ref_input_time.size > 1
            else (
                float(store.input_dt_s)
                if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0
                else float(store.dt_s)
            )
        )
        (
            _input_overlap_duration,
            _input_overlap_samples,
            _input_rmse,
            input_history_nrmse,
            _input_corr,
            input_warnings,
        ) = _time_history_metrics(
            store.input_time,
            store.acc_input,
            ref_input_time,
            ref_input_acc,
            float(store.input_dt_s) if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0 else float(store.dt_s),
            ref_input_dt,
        )
        warnings.extend(f"Input motion: {message}" for message in input_warnings)
        input_spectra = compute_spectra(
            store.acc_input,
            float(store.input_dt_s) if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0 else float(store.dt_s),
            damping=damping,
        )
        (
            _input_psa_points,
            _input_psa_rmse,
            input_psa_nrmse,
            _input_psa_max_abs_diff,
            _input_psa_peak_pct_diff,
            _input_psa_peak_period,
            _input_psa_peak_period_diff_pct,
            _used_ref_input_psa_csv,
            input_psa_warnings,
        ) = _psa_metrics_from_arrays(
            np.asarray(input_spectra.periods, dtype=np.float64),
            np.asarray(input_spectra.psa, dtype=np.float64),
            ref_input_time,
            ref_input_acc,
            ref_input_dt,
            damping=damping,
            ref_psa_path=ref_input_psa_path,
        )
        warnings.extend(f"Input PSA: {message}" for message in input_psa_warnings)
        sw_applied_acc = np.asarray(store.acc_applied_input, dtype=np.float64)
        if sw_applied_acc.size <= 1 and cfg is not None:
            sw_applied_acc = effective_input_acceleration(cfg, store.acc_input)
        ref_applied_input_acc = (
            effective_input_acceleration(cfg, ref_input_acc)
            if cfg is not None
            else np.asarray(ref_input_acc, dtype=np.float64)
        )
        if sw_applied_acc.size > 1:
            (
                _applied_overlap_duration,
                _applied_overlap_samples,
                _applied_rmse,
                applied_input_history_nrmse,
                _applied_corr,
                applied_input_warnings,
            ) = _time_history_metrics(
                store.input_time,
                sw_applied_acc,
                ref_input_time,
                ref_applied_input_acc,
                float(store.input_dt_s)
                if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0
                else float(store.dt_s),
                ref_input_dt,
            )
            warnings.extend(
                f"Applied input: {message}" for message in applied_input_warnings
            )
            applied_input_spectra = compute_spectra(
                sw_applied_acc,
                float(store.input_dt_s)
                if np.isfinite(store.input_dt_s) and store.input_dt_s > 0.0
                else float(store.dt_s),
                damping=damping,
            )
            (
                _applied_input_psa_points,
                _applied_input_psa_rmse,
                applied_input_psa_nrmse,
                _applied_input_psa_max_abs_diff,
                _applied_input_psa_peak_pct_diff,
                _applied_input_psa_peak_period,
                _applied_input_psa_peak_period_diff_pct,
                _used_ref_applied_input_psa_csv,
                applied_input_psa_warnings,
            ) = _psa_metrics_from_arrays(
                np.asarray(applied_input_spectra.periods, dtype=np.float64),
                np.asarray(applied_input_spectra.psa, dtype=np.float64),
                ref_input_time,
                ref_applied_input_acc,
                ref_input_dt,
                damping=damping,
                ref_psa_path=None,
            )
            warnings.extend(
                f"Applied input PSA: {message}"
                for message in applied_input_psa_warnings
            )
    profile_result: DeepsoilProfileComparison | None = None
    if ref_profile_path is not None:
        profile_result = _compare_profile_metrics(
            run_path,
            ref_profile_path,
            mobilized_strength_csv=ref_mobilized_path,
        )
    hysteresis_result: DeepsoilHysteresisComparison | None = None
    if ref_hysteresis_path is not None:
        hysteresis_result = _compare_hysteresis_metrics(
            run_path,
            ref_hysteresis_path,
            layer_index=hysteresis_layer,
        )
    boundary_condition = cfg.boundary_condition.value if cfg is not None else ""
    motion_input_type = cfg.motion.input_type if cfg is not None else ""
    damping_mode = cfg.analysis.damping_mode if cfg is not None else ""
    base_motion_semantics_ok = None
    if cfg is not None:
        base_motion_semantics_ok = (
            boundary_condition == "rigid"
            and motion_input_type == "outcrop"
            and damping_mode == "frequency_independent"
            and not bool(cfg.analysis.viscous_damping_update)
        )

    result = DeepsoilComparisonResult(
        run_id=store.run_id,
        run_dir=run_path,
        stratawave_dt_s=float(store.dt_s),
        deepsoil_dt_s=ref_dt,
        overlap_duration_s=overlap_duration,
        overlap_samples=overlap_samples,
        stratawave_pga_m_s2=sw_pga,
        deepsoil_pga_m_s2=ref_pga,
        pga_ratio=pga_ratio,
        pga_pct_diff=pga_pct_diff,
        surface_rmse_m_s2=rmse,
        surface_nrmse=nrmse,
        surface_corrcoef=corr,
        psa_point_count=psa_point_count,
        psa_rmse_m_s2=psa_rmse,
        psa_nrmse=psa_nrmse,
        psa_max_abs_diff_m_s2=psa_max_abs_diff,
        psa_pct_diff_at_peak=psa_peak_pct_diff,
        psa_peak_period_s=psa_peak_period,
        used_reference_psa_csv=used_reference_psa_csv,
        surface_psa_peak_period_diff_pct=surface_psa_peak_period_diff_pct,
        arias_intensity_sw=ia_sw,
        arias_intensity_ref=ia_ref,
        arias_intensity_ratio=ia_ratio,
        xcorr_lag_samples=xcorr_lag,
        xcorr_lag_s=xcorr_lag_s,
        xcorr_peak_coeff=xcorr_peak,
        input_history_nrmse=input_history_nrmse,
        input_psa_nrmse=input_psa_nrmse,
        applied_input_history_nrmse=applied_input_history_nrmse,
        applied_input_psa_nrmse=applied_input_psa_nrmse,
        input_dt_used_s=float(store.input_dt_s) if np.isfinite(store.input_dt_s) else None,
        input_pga_loaded_m_s2=(
            float(np.max(np.abs(store.acc_input))) if store.acc_input.size > 0 else None
        ),
        applied_input_pga_loaded_m_s2=(
            float(np.max(np.abs(store.acc_applied_input)))
            if store.acc_applied_input.size > 0
            else (
                float(np.max(np.abs(effective_input_acceleration(cfg, store.acc_input))))
                if cfg is not None and store.acc_input.size > 0
                else None
            )
        ),
        boundary_condition=boundary_condition,
        motion_input_type=motion_input_type,
        damping_mode=damping_mode,
        base_motion_semantics_ok=base_motion_semantics_ok,
        reference_kind=imported_bundle.case_kind if imported_bundle is not None else "",
        profile=profile_result,
        hysteresis=hysteresis_result,
        warnings=warnings,
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "deepsoil_compare.json"
        markdown_path = output_dir / "deepsoil_compare.md"
        json_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        markdown = render_deepsoil_comparison_markdown(
            result,
            surface_csv=surface_path,
            psa_csv=ref_psa_path,
            profile_csv=ref_profile_path,
            hysteresis_csv=ref_hysteresis_path,
            input_motion_csv=input_motion_path,
            input_psa_csv=ref_input_psa_path,
            mobilized_strength_csv=ref_mobilized_path,
            deepsoil_excel=Path(deepsoil_excel) if deepsoil_excel is not None else None,
        )
        markdown_path.write_text(markdown, encoding="utf-8")
        result.artifacts = DeepsoilComparisonArtifacts(
            output_dir=output_dir,
            json_path=json_path,
            markdown_path=markdown_path,
        )

    return result


def compare_deepsoil_manifest(
    manifest_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    damping: float = 0.05,
) -> DeepsoilComparisonBatchResult:
    manifest = Path(manifest_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("DEEPSOIL comparison manifest root must be a JSON object.")

    cases_raw = raw.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise ValueError("DEEPSOIL comparison manifest must include a non-empty 'cases' list.")

    base_dir = manifest.parent
    default_policy = _merge_tolerance_policy(
        DeepsoilComparisonTolerancePolicy(),
        raw.get("defaults"),
    )
    case_results: list[dict[str, object]] = []
    passed_cases = 0

    for idx, case_raw in enumerate(cases_raw, start=1):
        if not isinstance(case_raw, dict):
            raise ValueError(f"Manifest case #{idx} must be an object.")
        name = str(case_raw.get("name", f"case-{idx:02d}"))
        run_dir = _resolve_manifest_path(base_dir, case_raw.get("run"))
        deepsoil_excel_value = case_raw.get("deepsoil_excel")
        deepsoil_excel = (
            _resolve_manifest_path(base_dir, deepsoil_excel_value) if deepsoil_excel_value else None
        )
        surface_value = case_raw.get("surface_csv")
        surface_csv = _resolve_manifest_path(base_dir, surface_value) if surface_value else None
        input_motion_value = case_raw.get("input_motion_csv")
        input_motion_csv = (
            _resolve_manifest_path(base_dir, input_motion_value) if input_motion_value else None
        )
        psa_value = case_raw.get("psa_csv")
        psa_csv = _resolve_manifest_path(base_dir, psa_value) if psa_value else None
        input_psa_value = case_raw.get("input_psa_csv")
        input_psa_csv = (
            _resolve_manifest_path(base_dir, input_psa_value) if input_psa_value else None
        )
        profile_value = case_raw.get("profile_csv")
        profile_csv = _resolve_manifest_path(base_dir, profile_value) if profile_value else None
        mobilized_value = case_raw.get("mobilized_strength_csv")
        mobilized_strength_csv = (
            _resolve_manifest_path(base_dir, mobilized_value) if mobilized_value else None
        )
        hysteresis_value = case_raw.get("hysteresis_csv")
        hysteresis_csv = (
            _resolve_manifest_path(base_dir, hysteresis_value) if hysteresis_value else None
        )
        hysteresis_layer = int(_as_float(case_raw.get("hysteresis_layer", 0), 0.0))
        surface_dt_override_raw = case_raw.get("surface_dt_override")
        surface_dt_override = (
            _as_float(surface_dt_override_raw, float("nan"))
            if surface_dt_override_raw is not None
            else None
        )
        if surface_dt_override is not None and not np.isfinite(surface_dt_override):
            surface_dt_override = None

        case_policy = _merge_tolerance_policy(default_policy, case_raw.get("tolerances"))
        result = compare_deepsoil_run(
            run_dir,
            surface_csv=surface_csv,
            input_motion_csv=input_motion_csv,
            psa_csv=psa_csv,
            input_psa_csv=input_psa_csv,
            profile_csv=profile_csv,
            mobilized_strength_csv=mobilized_strength_csv,
            hysteresis_csv=hysteresis_csv,
            deepsoil_excel=deepsoil_excel,
            hysteresis_layer=hysteresis_layer,
            out_dir=None,
            surface_dt_override=surface_dt_override,
            damping=damping,
        )
        verdict = _evaluate_case_policy(result, case_policy)
        passed = bool(verdict["passed"])
        if passed:
            passed_cases += 1
        case_results.append(
            {
                "name": name,
                "run_dir": str(run_dir),
                "deepsoil_excel": str(deepsoil_excel) if deepsoil_excel is not None else "",
                "surface_csv": str(surface_csv) if surface_csv is not None else "",
                "input_motion_csv": str(input_motion_csv) if input_motion_csv is not None else "",
                "psa_csv": str(psa_csv) if psa_csv is not None else "",
                "input_psa_csv": str(input_psa_csv) if input_psa_csv is not None else "",
                "profile_csv": str(profile_csv) if profile_csv is not None else "",
                "mobilized_strength_csv": (
                    str(mobilized_strength_csv) if mobilized_strength_csv is not None else ""
                ),
                "hysteresis_csv": str(hysteresis_csv) if hysteresis_csv is not None else "",
                "metrics": {
                    "pga_pct_diff": result.pga_pct_diff,
                    "surface_corrcoef": result.surface_corrcoef,
                    "surface_nrmse": result.surface_nrmse,
                    "psa_nrmse": result.psa_nrmse,
                    "input_history_nrmse": result.input_history_nrmse,
                    "input_psa_nrmse": result.input_psa_nrmse,
                    "applied_input_history_nrmse": result.applied_input_history_nrmse,
                    "applied_input_psa_nrmse": result.applied_input_psa_nrmse,
                    "profile": asdict(result.profile) if result.profile is not None else {},
                    "hysteresis": (
                        asdict(result.hysteresis) if result.hysteresis is not None else {}
                    ),
                },
                "checks": verdict["checks"],
                "passed": passed,
                "warnings": list(result.warnings),
                "comparison": result.to_dict(),
            }
        )

    batch_result = DeepsoilComparisonBatchResult(
        manifest_path=manifest.resolve(),
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=len(case_results) - passed_cases,
        policy=default_policy,
        cases=case_results,
    )

    if out_dir is not None:
        output_dir = Path(out_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "deepsoil_compare_batch.json"
        markdown_path = output_dir / "deepsoil_compare_batch.md"
        json_path.write_text(json.dumps(batch_result.to_dict(), indent=2), encoding="utf-8")
        markdown_path.write_text(
            render_deepsoil_comparison_batch_markdown(batch_result),
            encoding="utf-8",
        )
        batch_result.artifacts = DeepsoilComparisonBatchArtifacts(
            output_dir=output_dir,
            json_path=json_path,
            markdown_path=markdown_path,
        )

    return batch_result
