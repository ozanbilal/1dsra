from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path
from typing import Literal, cast

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from dsra1d.calibration import (
    calibrate_gqh_strength_control_from_reference,
    calibrate_gqh_from_darendeli,
    calibrate_mkz_from_darendeli,
    generate_darendeli_curves,
    get_reference_curves,
)
from dsra1d.config import (
    available_config_templates,
    get_config_template_payload,
    load_project_config,
    write_config_template,
)
from dsra1d.config.models import (
    BaselineMode,
    BedrockProperties,
    BoundaryCondition,
    DarendeliCalibration,
    MaterialType,
    MotionConfig,
    MotionProcessingConfig,
    ProjectConfig,
    ScaleMode,
)
from dsra1d.materials import (
    bounded_damping_from_reduction,
    compute_masing_damping_ratio,
    evaluate_mrdf_factor,
    generate_masing_loop,
    gqh_mode_from_params,
    gqh_modulus_reduction_from_params,
    mkz_modulus_reduction,
    mrdf_coefficients_from_params,
)
from dsra1d.motion import (
    import_peer_at2_to_csv,
    load_motion,
    load_motion_series,
    preprocess_motion,
    process_motion_components,
)
from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.post import compute_spectra, compute_transfer_function
from dsra1d.profile_diagnostics import (
    compute_layer_stress_states,
    compute_profile_diagnostics,
    mean_effective_stress_from_k0,
)
from dsra1d.store import ResultStore
from dsra1d.types import Motion
from dsra1d.units import accel_factor_to_si

RunBackendMode = Literal["linear", "eql", "nonlinear"]
ResolvedBackend = Literal["linear", "eql", "nonlinear"]


class RunRequest(BaseModel):
    config_path: str
    motion_path: str = ""
    output_root: str = "out/web"
    backend: RunBackendMode = "nonlinear"


class RunResponse(BaseModel):
    run_id: str
    output_dir: str
    output_root: str
    status: str
    message: str
    backend: str


class RunBatchRequest(BaseModel):
    config_path: str
    motion_paths: list[str] = Field(default_factory=list)
    output_root: str = "out/web"
    backend: RunBackendMode = "nonlinear"
    n_jobs: int = Field(default=1, ge=1, le=256)


class RunBatchResponse(BaseModel):
    output_root: str
    backend: str
    status: str
    message: str
    motion_count: int
    unique_run_count: int
    n_jobs: int
    results: list[RunResponse] = Field(default_factory=list)


class RunSummary(BaseModel):
    run_id: str
    output_dir: str
    timestamp_utc: str = ""
    solver_backend: str = "unknown"
    status: str = "unknown"
    message: str = ""
    project_name: str = ""
    input_motion: str = ""
    motion_name: str = ""
    pga: float | None = None
    ru_max: float | None = None
    delta_u_max: float | None = None
    sigma_v_eff_min: float | None = None
    convergence_mode: str = "none"
    convergence_severity: str = "neutral"
    converged: bool | None = None
    solver_warning_count: int | None = None
    solver_failed_converge_count: int | None = None
    solver_analyze_failed_count: int | None = None
    solver_divide_by_zero_count: int | None = None
    solver_dynamic_fallback_failed_count: int | None = None


class ConfigTemplateRequest(BaseModel):
    template: Literal[
        "linear-3layer-sand",
        "mkz-gqh-eql",
        "mkz-gqh-nonlinear",
        "mkz-gqh-darendeli",
    ] = "mkz-gqh-nonlinear"
    output_dir: str = ""
    file_name: str = ""


class ConfigTemplateResponse(BaseModel):
    template: str
    config_path: str
    status: str
    message: str


class WizardAnalysisStep(BaseModel):
    project_name: str = "wizard-project"
    boundary_condition: BoundaryCondition = BoundaryCondition.RIGID
    solver_backend: RunBackendMode = "nonlinear"


class WizardLayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    thickness_m: float = Field(gt=0.0)
    unit_weight_kn_m3: float = Field(gt=0.0, alias="unit_weight_kN_m3")
    vs_m_s: float = Field(gt=0.0)
    material: MaterialType
    reference_curve: str | None = None
    fit_stale: bool = False
    material_params: dict[str, float] = Field(default_factory=dict)
    material_optional_args: list[float] = Field(default_factory=list)
    calibration: DarendeliCalibration | None = None


class WizardProfileStep(BaseModel):
    water_table_depth_m: float | None = Field(default=None, ge=0.0)
    bedrock: BedrockProperties | None = None
    layers: list[WizardLayer] = Field(default_factory=list)


class WizardMotionStep(BaseModel):
    units: str = "m/s2"
    input_type: Literal["within", "outcrop"] = "outcrop"
    dt_override: float | None = Field(default=None, gt=0.0)
    baseline: BaselineMode = BaselineMode.REMOVE_MEAN
    scale_mode: ScaleMode = ScaleMode.NONE
    scale_factor: float | None = None
    target_pga: float | None = None
    motion_path: str = ""
    processing: MotionProcessingConfig | None = None


class WizardDampingStep(BaseModel):
    mode: Literal["frequency_independent", "rayleigh"] = "frequency_independent"
    update_matrix: bool = False
    mode_1: float | None = None
    mode_2: float | None = None


class WizardControlStep(BaseModel):
    dt: float | None = Field(default=None, gt=0.0)
    f_max: float = Field(default=25.0, gt=0.0)
    timeout_s: int = Field(default=180, ge=1)
    retries: int = Field(default=1, ge=0)
    write_hdf5: bool = True
    write_sqlite: bool = True
    parquet_export: bool = False
    output_dir: str = "out/web"
    config_output_dir: str = ""
    config_file_name: str = ""


class WizardConfigRequest(BaseModel):
    analysis_step: WizardAnalysisStep
    profile_step: WizardProfileStep
    motion_step: WizardMotionStep
    damping_step: WizardDampingStep
    control_step: WizardControlStep


class WizardConfigResponse(BaseModel):
    config_path: str
    config_yaml: str
    warnings: list[str]
    status: str


class LayerCalibrationPreviewRequest(BaseModel):
    layer: WizardLayer
    layers: list[WizardLayer] | None = None
    layer_index: int | None = Field(default=None, ge=0)
    water_table_depth_m: float | None = Field(default=None, ge=0.0)


class LayerCalibrationPreviewResponse(BaseModel):
    available: bool = False
    material: str = ""
    source: str = ""
    target_available: bool = False
    strain: list[float] = Field(default_factory=list)
    target_modulus_reduction: list[float] = Field(default_factory=list)
    fitted_modulus_reduction: list[float] = Field(default_factory=list)
    target_damping_ratio: list[float] = Field(default_factory=list)
    fitted_damping_ratio: list[float] = Field(default_factory=list)
    material_params: dict[str, float] = Field(default_factory=dict)
    calibrated_material_params: dict[str, float] = Field(default_factory=dict)
    fit_rmse: float | None = None
    modulus_rmse: float | None = None
    damping_rmse: float | None = None
    strength_ratio_achieved: float | None = None
    fit_procedure: str | None = None
    fit_limits_applied: dict[str, float | bool | str] | None = None
    fit_stale: bool = False
    gqh_mode: str | None = None
    sigma_v_eff_mid_kpa: float | None = None
    implied_strength_kpa: float | None = None
    normalized_implied_strength: float | None = None
    implied_friction_angle_deg: float | None = None
    loop_strain: list[float] = Field(default_factory=list)
    loop_stress: list[float] = Field(default_factory=list)
    loop_strain_amplitude: float | None = None
    loop_energy: float | None = None
    warnings: list[str] = Field(default_factory=list)


class MotionImportRequest(BaseModel):
    path: str
    units_hint: str = "g"
    dt_override: float | None = Field(default=None, gt=0.0)
    output_dir: str = ""
    output_name: str = ""


class MotionImportResponse(BaseModel):
    converted_csv_path: str
    npts: int
    dt_s: float
    pga_si: float
    status: str


class MotionUploadResponse(BaseModel):
    uploaded_path: str
    file_name: str
    nbytes: int
    status: str


class MotionGeneratedClearResponse(BaseModel):
    status: str
    directory: str
    removed_files: int
    freed_bytes: int


class MotionUploadCsvRequest(BaseModel):
    file_name: str
    content_base64: str
    output_dir: str = ""
    output_name: str = ""


class MotionUploadPeerAT2Request(BaseModel):
    file_name: str
    content_base64: str
    units_hint: str = "g"
    dt_override: float | None = Field(default=None, gt=0.0)
    output_dir: str = ""
    output_name: str = ""


class MotionParseOptionsModel(BaseModel):
    format_hint: Literal["auto", "time_acc", "single", "numeric_stream"] = "auto"
    delimiter: str | None = None
    skip_rows: int = Field(default=0, ge=0, le=5000)
    time_col: int = Field(default=0, ge=0, le=100)
    acc_col: int = Field(default=1, ge=0, le=100)
    has_time: bool = True


class MotionProcessingOptionsModel(BaseModel):
    processing_order: Literal["filter_first", "baseline_first"] = "filter_first"
    baseline_on: bool = False
    baseline_method: str = "poly4"
    baseline_degree: int = Field(default=4, ge=0, le=10)
    filter_on: bool = False
    filter_domain: Literal["time", "frequency"] = "time"
    filter_config: str = "bandpass"
    filter_type: Literal["butter", "cheby", "bessel"] = "butter"
    f_low: float = Field(default=0.1, ge=0.0)
    f_high: float = Field(default=25.0, ge=0.0)
    filter_order: int = Field(default=4, ge=1, le=16)
    acausal: bool = True
    window_on: bool = False
    window_type: str = "hanning"
    window_param: float = Field(default=0.1, ge=0.0)
    window_duration: float | None = Field(default=None, gt=0.0)
    window_apply_to: Literal["start", "end", "both"] = "both"
    trim_start: float = Field(default=0.0, ge=0.0)
    trim_end: float = Field(default=0.0, ge=0.0)
    trim_taper: bool = False
    pad_front: float = Field(default=0.0, ge=0.0)
    pad_end: float = Field(default=0.0, ge=0.0)
    pad_method: str = "zeros"
    pad_method_front: str | None = None
    pad_method_end: str | None = None
    pad_smooth: bool = False
    residual_fix: bool = False
    spectrum_damping_ratio: float = Field(default=0.05, gt=0.0, lt=1.0)
    show_uncorrected_preview: bool = True


class MotionProcessRequest(MotionParseOptionsModel, MotionProcessingOptionsModel):
    motion_path: str
    units_hint: str = "m/s2"
    dt_override: float | None = Field(default=None, gt=0.0)
    fallback_dt: float | None = Field(default=None, gt=0.0)
    baseline_mode: BaselineMode = BaselineMode.REMOVE_MEAN
    scale_mode: ScaleMode = ScaleMode.NONE
    scale_factor: float | None = None
    target_pga: float | None = None
    output_dir: str = ""
    output_name: str = ""


class MotionProcessResponse(BaseModel):
    processed_motion_path: str
    metrics_path: str
    metrics: dict[str, float]
    spectra_preview: dict[str, object]
    status: str


class MotionTimeStepReductionRequest(MotionParseOptionsModel):
    motion_path: str
    units_hint: str = "m/s2"
    dt_override: float | None = Field(default=None, gt=0.0)
    target_dt: float | None = Field(default=None, gt=0.0)
    reduction_factor: int = Field(default=2, ge=2, le=20)
    max_points: int = Field(default=4000, ge=200, le=40000)


class MotionTimeStepReductionResponse(BaseModel):
    dt_original: float
    dt_reduced: float
    reduction_factor: int
    pga_original_m_s2: float
    pga_reduced_m_s2: float
    time_s: list[float] = Field(default_factory=list)
    acc_original_m_s2: list[float] = Field(default_factory=list)
    acc_reduced_m_s2: list[float] = Field(default_factory=list)
    note: str = ""


class MotionKappaRequest(MotionParseOptionsModel):
    motion_path: str
    units_hint: str = "m/s2"
    dt_override: float | None = Field(default=None, gt=0.0)
    freq_min_hz: float = Field(default=10.0, gt=0.0)
    freq_max_hz: float = Field(default=40.0, gt=0.0)
    max_points: int = Field(default=2400, ge=100, le=40000)


class MotionKappaResponse(BaseModel):
    kappa: float | None = None
    kappa_r2: float | None = None
    freq_hz: list[float] = Field(default_factory=list)
    fas_amplitude: list[float] = Field(default_factory=list)
    fit_freq_hz: list[float] = Field(default_factory=list)
    fit_amplitude: list[float] = Field(default_factory=list)
    note: str = ""


class ResultSummaryResponse(BaseModel):
    run_id: str
    status: str
    solver_backend: str
    project_name: str = ""
    input_motion: str = ""
    metrics: dict[str, float]
    convergence: dict[str, object]
    output_layers: list[str]
    artifacts: list[dict[str, str]]
    solver_notes: str


class WizardSanityCheckItem(BaseModel):
    name: str
    status: Literal["ok", "warning", "blocker"]
    message: str


class WizardSanityResponse(BaseModel):
    ok: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: list[WizardSanityCheckItem] = Field(default_factory=list)
    derived: dict[str, object] = Field(default_factory=dict)


class ProfileDiagnosticsRequest(BaseModel):
    profile_step: WizardProfileStep


class ProfileDiagnosticsLayerRow(BaseModel):
    idx: int
    name: str
    material: str
    thickness_m: float
    unit_weight_kn_m3: float = Field(serialization_alias="unit_weight_kN_m3")
    vs_m_s: float
    z_top_m: float
    z_bottom_m: float
    sigma_v0_mid_kpa: float
    sigma_v_eff_mid_kpa: float
    pore_water_pressure_kpa: float
    small_strain_damping_ratio: float | None = None
    max_frequency_hz: float | None = None
    implied_strength_kpa: float | None = None
    normalized_implied_strength: float | None = None
    implied_friction_angle_deg: float | None = None
    gqh_mode: str | None = None


class ProfileDiagnosticsResponse(BaseModel):
    layer_count: int
    total_thickness_m: float
    water_table_depth_m: float | None = None
    layers: list[ProfileDiagnosticsLayerRow] = Field(default_factory=list)


class ResultProfileLayerRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    idx: int
    name: str
    material: str
    thickness_m: float
    unit_weight_kn_m3: float = Field(serialization_alias="unit_weight_kN_m3")
    vs_m_s: float
    z_top_m: float
    z_bottom_m: float
    n_sub: int
    gamma_max: float | None = None
    damping_ratio: float | None = None
    tau_peak_kpa: float | None = None
    secant_g_pa: float | None = None
    secant_g_over_gmax: float | None = None
    sigma_v0_mid_kpa: float | None = None
    sigma_v_eff_mid_kpa: float | None = None
    pore_water_pressure_kpa: float | None = None
    small_strain_damping_ratio: float | None = None
    max_frequency_hz: float | None = None
    implied_strength_kpa: float | None = None
    normalized_implied_strength: float | None = None
    implied_friction_angle_deg: float | None = None
    gqh_mode: str | None = None
    ru_max: float | None = None
    delta_u_max: float | None = None
    sigma_v_eff_min: float | None = None


class ResultProfileSummaryResponse(BaseModel):
    run_id: str
    layer_count: int
    total_thickness_m: float
    ru_max: float | None = None
    delta_u_max: float | None = None
    sigma_v_eff_min: float | None = None
    layers: list[ResultProfileLayerRow] = Field(default_factory=list)


class DisplacementAnimationRequest(BaseModel):
    run_id: str
    output_root: str = "out/web"
    frame_count: int = Field(default=120, ge=20, le=1200)
    max_depth_points: int = Field(default=200, ge=10, le=2000)


class DisplacementAnimationResponse(BaseModel):
    run_id: str
    approximate: bool = True
    depth_m: list[float] = Field(default_factory=list)
    frame_time_s: list[float] = Field(default_factory=list)
    displacement_cm: list[list[float]] = Field(default_factory=list)
    relative_displacement_cm: list[list[float]] = Field(default_factory=list)
    peak_surface_displacement_cm: float | None = None
    peak_profile_displacement_cm: float | None = None
    peak_surface_relative_displacement_cm: float | None = None
    peak_profile_relative_displacement_cm: float | None = None
    note: str = ""


class SpectraSummaryRow(BaseModel):
    period_s: float
    frequency_hz: float
    surface_psa_m_s2: float | None = None
    surface_psa_g: float | None = None
    input_psa_m_s2: float | None = None
    amplification_ratio: float | None = None


class ResponseSpectraSummaryResponse(BaseModel):
    run_id: str
    damping_ratio: float
    row_count: int
    rows: list[SpectraSummaryRow] = Field(default_factory=list)
    max_surface_psa_m_s2: float | None = None
    max_amplification_ratio: float | None = None


SPECTRA_STANDARD_PERIODS: tuple[float, ...] = (
    0.01,
    0.02,
    0.03,
    0.05,
    0.075,
    0.1,
    0.15,
    0.2,
    0.25,
    0.3,
    0.4,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.0,
    4.0,
    5.0,
    7.5,
    10.0,
)

WEB_SPECTRA_MIN_PERIOD_S = 0.05
WEB_SPECTRA_MAX_PERIOD_S = 10.0
WEB_SPECTRA_POINT_COUNT = 120


def _web_spectra_periods() -> np.ndarray:
    return np.logspace(
        np.log10(WEB_SPECTRA_MIN_PERIOD_S),
        np.log10(WEB_SPECTRA_MAX_PERIOD_S),
        WEB_SPECTRA_POINT_COUNT,
        dtype=np.float64,
    )


def _profile_summary_csv_text(summary: ResultProfileSummaryResponse) -> str:
    lines = [
        (
            "idx,name,material,z_top_m,z_bottom_m,thickness_m,vs_m_s,"
            "unit_weight_kN_m3,n_sub,gamma_max,tau_peak_kpa,secant_g_pa,secant_g_over_gmax,"
            "sigma_v0_mid_kpa,sigma_v_eff_mid_kpa,"
            "pore_water_pressure_kpa,small_strain_damping_ratio,max_frequency_hz,"
            "implied_strength_kpa,normalized_implied_strength,implied_friction_angle_deg,"
            "gqh_mode,ru_max,delta_u_max,sigma_v_eff_min"
        )
    ]
    for layer in summary.layers:
        values = [
            layer.idx,
            layer.name,
            layer.material,
            f"{layer.z_top_m:.8f}",
            f"{layer.z_bottom_m:.8f}",
            f"{layer.thickness_m:.8f}",
            f"{layer.vs_m_s:.8f}",
            f"{layer.unit_weight_kn_m3:.8f}",
            layer.n_sub,
            "" if layer.gamma_max is None else f"{layer.gamma_max:.10e}",
            "" if layer.tau_peak_kpa is None else f"{layer.tau_peak_kpa:.10e}",
            "" if layer.secant_g_pa is None else f"{layer.secant_g_pa:.10e}",
            "" if layer.secant_g_over_gmax is None else f"{layer.secant_g_over_gmax:.10e}",
            "" if layer.sigma_v0_mid_kpa is None else f"{layer.sigma_v0_mid_kpa:.10e}",
            "" if layer.sigma_v_eff_mid_kpa is None else f"{layer.sigma_v_eff_mid_kpa:.10e}",
            "" if layer.pore_water_pressure_kpa is None else f"{layer.pore_water_pressure_kpa:.10e}",
            ""
            if layer.small_strain_damping_ratio is None
            else f"{layer.small_strain_damping_ratio:.10e}",
            "" if layer.max_frequency_hz is None else f"{layer.max_frequency_hz:.10e}",
            "" if layer.implied_strength_kpa is None else f"{layer.implied_strength_kpa:.10e}",
            ""
            if layer.normalized_implied_strength is None
            else f"{layer.normalized_implied_strength:.10e}",
            ""
            if layer.implied_friction_angle_deg is None
            else f"{layer.implied_friction_angle_deg:.10e}",
            "" if layer.gqh_mode is None else layer.gqh_mode,
            "" if layer.ru_max is None else f"{layer.ru_max:.10e}",
            "" if layer.delta_u_max is None else f"{layer.delta_u_max:.10e}",
            "" if layer.sigma_v_eff_min is None else f"{layer.sigma_v_eff_min:.10e}",
        ]
        row = ",".join(
            f"\"{str(value).replace('\"', '\"\"')}\"" if isinstance(value, str) else str(value)
            for value in values
        )
        lines.append(row)
    return "\n".join(lines)


class HysteresisLayerResponse(BaseModel):
    layer_index: int
    layer_name: str
    material: str
    model: str
    is_proxy: bool = False
    strain_amplitude: float
    loop_energy: float
    mobilized_strength_ratio: float
    g_over_gmax: float
    damping_proxy: float
    strain: list[float]
    stress: list[float]


class ResultHysteresisResponse(BaseModel):
    run_id: str
    source: str
    note: str = ""
    layers: list[HysteresisLayerResponse] = Field(default_factory=list)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_output_root() -> Path:
    return _repo_root() / "out" / "ui"


def _default_config_root() -> Path:
    return _repo_root() / "out" / "ui" / "configs"


def _safe_real_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _safe_motion_output_dir(raw: str) -> Path:
    if raw.strip():
        out = _safe_real_path(raw)
    else:
        out = _repo_root() / "out" / "ui" / "motions"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _safe_upload_stem(raw: str, fallback: str) -> str:
    name = (raw or "").strip()
    base = Path(name).stem if name else Path(fallback).stem
    base = base.strip() or "uploaded_motion"
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in base)


def _clear_generated_motion_dir() -> MotionGeneratedClearResponse:
    out_dir = _safe_motion_output_dir("")
    removed_files = 0
    freed_bytes = 0
    if out_dir.exists() and out_dir.is_dir():
        for entry in out_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in {".csv", ".txt", ".at2"}:
                continue
            try:
                freed_bytes += int(entry.stat().st_size)
            except OSError:
                pass
            entry.unlink(missing_ok=True)
            removed_files += 1
    return MotionGeneratedClearResponse(
        status="ok",
        directory=str(out_dir),
        removed_files=removed_files,
        freed_bytes=freed_bytes,
    )


def _resolve_input_path(path_value: str, *, label: str) -> Path:
    text = path_value.strip()
    if not text:
        raise ValueError(f"{label} path is empty.")
    raw = Path(text).expanduser()
    candidates: list[Path]
    if raw.is_absolute():
        candidates = [raw]
    else:
        candidates = [Path.cwd() / raw, _repo_root() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"{label} not found: {path_value}")


def _motion_parse_kwargs_from_model(payload: object) -> dict[str, object]:
    def pick(name: str, default: object) -> object:
        if isinstance(payload, dict):
            return payload.get(name, default)
        return getattr(payload, name, default)

    return {
        "format_hint": pick("format_hint", "auto"),
        "delimiter": pick("delimiter", None),
        "skip_rows": pick("skip_rows", 0),
        "time_col": pick("time_col", 0),
        "acc_col": pick("acc_col", 1),
        "has_time": pick("has_time", True),
    }


def _motion_processing_kwargs_from_model(payload: object) -> dict[str, object]:
    def pick(name: str, default: object) -> object:
        if isinstance(payload, dict):
            return payload.get(name, default)
        return getattr(payload, name, default)

    return {
        "processing_order": pick("processing_order", "filter_first"),
        "baseline_on": pick("baseline_on", False),
        "baseline_method": pick("baseline_method", "poly4"),
        "baseline_degree": pick("baseline_degree", 4),
        "filter_on": pick("filter_on", False),
        "filter_domain": pick("filter_domain", "time"),
        "filter_config": pick("filter_config", "bandpass"),
        "filter_type": pick("filter_type", "butter"),
        "f_low": pick("f_low", 0.1),
        "f_high": pick("f_high", 25.0),
        "filter_order": pick("filter_order", 4),
        "acausal": pick("acausal", True),
        "window_on": pick("window_on", False),
        "window_type": pick("window_type", "hanning"),
        "window_param": pick("window_param", 0.1),
        "window_duration": pick("window_duration", None),
        "window_apply_to": pick("window_apply_to", "both"),
        "trim_start": pick("trim_start", 0.0),
        "trim_end": pick("trim_end", 0.0),
        "trim_taper": pick("trim_taper", False),
        "pad_front": pick("pad_front", 0.0),
        "pad_end": pick("pad_end", 0.0),
        "pad_method": pick("pad_method", "zeros"),
        "pad_method_front": pick("pad_method_front", None),
        "pad_method_end": pick("pad_method_end", None),
        "pad_smooth": pick("pad_smooth", False),
        "residual_fix": pick("residual_fix", False),
        "spectrum_damping_ratio": pick("spectrum_damping_ratio", 0.05),
        "show_uncorrected_preview": pick("show_uncorrected_preview", True),
    }


def _motion_config_from_model(
    payload: object,
    *,
    baseline_mode: BaselineMode = BaselineMode.NONE,
    scale_mode: ScaleMode = ScaleMode.NONE,
    scale_factor: float | None = None,
    target_pga: float | None = None,
    force_processing: bool = False,
) -> MotionConfig:
    def pick(name: str, default: object) -> object:
        if isinstance(payload, dict):
            return payload.get(name, default)
        return getattr(payload, name, default)

    processing_kwargs = _motion_processing_kwargs_from_model(payload)
    processing_defaults = MotionProcessingOptionsModel().model_dump(mode="python")
    relevant_keys = tuple(
        key
        for key in processing_defaults.keys()
        if key not in {"show_uncorrected_preview", "spectrum_damping_ratio"}
    )
    has_processing = force_processing or any(
        processing_kwargs[key] != processing_defaults[key]
        for key in relevant_keys
    )
    processing = (
        MotionProcessingConfig.model_validate(processing_kwargs)
        if has_processing
        else None
    )
    return MotionConfig(
        units=cast(str, pick("units_hint", pick("units", "m/s2"))),
        input_type=cast(str, pick("input_type", "within")),
        baseline=baseline_mode,
        scale_mode=scale_mode,
        scale_factor=scale_factor,
        target_pga=target_pga,
        processing=processing,
    )


def _motion_preview_payload(
    *,
    motion_path: Path,
    units_hint: str,
    format_hint: str,
    raw_time_s: np.ndarray,
    raw_acc_si: np.ndarray,
    processed_dt_s: float,
    processed_components: dict[str, np.ndarray],
    spectrum_damping_ratio: float = 0.05,
    show_uncorrected_preview: bool = True,
    max_points: int = 1200,
) -> dict[str, object]:
    factor = accel_factor_to_si(units_hint)
    raw_time = np.asarray(raw_time_s, dtype=np.float64)
    raw_acc_m_s2 = np.asarray(raw_acc_si, dtype=np.float64)
    raw_acc_input = raw_acc_m_s2 / factor if factor != 0.0 else raw_acc_m_s2.copy()

    acc_proc_m_s2 = np.asarray(processed_components["acc_processed"], dtype=np.float64)
    vel_proc_m_s = np.asarray(processed_components["vel_processed"], dtype=np.float64)
    disp_proc_m = np.asarray(processed_components["disp_processed"], dtype=np.float64)
    time_proc = np.arange(acc_proc_m_s2.size, dtype=np.float64) * float(processed_dt_s)
    acc_proc_input = acc_proc_m_s2 / factor if factor != 0.0 else acc_proc_m_s2.copy()

    spectra = compute_spectra(
        acc_proc_m_s2,
        dt=float(processed_dt_s),
        damping=float(spectrum_damping_ratio),
    )
    sv, sd = _spectral_triplet(spectra.psa, spectra.periods)
    sa_input = spectra.psa / factor if factor != 0.0 else spectra.psa.copy()

    time_d, acc_input_d = _downsample_np(time_proc, acc_proc_input, max_points=max_points)
    _, acc_d = _downsample_np(time_proc, acc_proc_m_s2, max_points=max_points)
    _, vel_d = _downsample_np(time_proc, vel_proc_m_s, max_points=max_points)
    _, disp_d = _downsample_np(time_proc, disp_proc_m, max_points=max_points)
    period_d, sa_input_d = _downsample_np(
        spectra.periods,
        sa_input,
        max_points=min(max_points, 800),
    )
    _, sa_m_s2_d = _downsample_np(
        spectra.periods,
        spectra.psa,
        max_points=min(max_points, 800),
    )
    _, sv_d = _downsample_np(spectra.periods, sv, max_points=min(max_points, 800))
    _, sd_d = _downsample_np(spectra.periods, sd, max_points=min(max_points, 800))

    raw_time_d: list[float] = []
    raw_acc_input_d: list[float] = []
    raw_acc_d: list[float] = []
    if show_uncorrected_preview:
        raw_time_ds, raw_acc_input_ds = _downsample_np(raw_time, raw_acc_input, max_points=max_points)
        _, raw_acc_si_ds = _downsample_np(raw_time, raw_acc_m_s2, max_points=max_points)
        raw_time_d = [float(v) for v in raw_time_ds]
        raw_acc_input_d = [float(v) for v in raw_acc_input_ds]
        raw_acc_d = [float(v) for v in raw_acc_si_ds]

    raw_pga_m_s2 = float(np.max(np.abs(raw_acc_m_s2))) if raw_acc_m_s2.size > 0 else 0.0
    pga_m_s2 = float(np.max(np.abs(acc_proc_m_s2))) if acc_proc_m_s2.size > 0 else 0.0
    duration = float(time_proc[-1]) if time_proc.size > 1 else 0.0

    return {
        "path": str(motion_path),
        "name": motion_path.stem,
        "npts": int(acc_proc_m_s2.size),
        "raw_npts": int(raw_acc_m_s2.size),
        "dt": float(processed_dt_s),
        "raw_dt": _estimate_dt(raw_time) if raw_time.size > 1 else float(processed_dt_s),
        "duration": duration,
        "raw_duration": float(raw_time[-1]) if raw_time.size > 1 else 0.0,
        "input_units": units_hint,
        "format_hint": format_hint,
        "show_uncorrected_preview": bool(show_uncorrected_preview),
        "pga_input_units": pga_m_s2 / factor if factor != 0.0 else pga_m_s2,
        "pga_m_s2": pga_m_s2,
        "pga_g": pga_m_s2 / 9.81,
        "pgv_m_s": float(np.max(np.abs(vel_proc_m_s))) if vel_proc_m_s.size > 0 else 0.0,
        "pgd_m": float(np.max(np.abs(disp_proc_m))) if disp_proc_m.size > 0 else 0.0,
        "sa_max_input_units": float(np.max(np.abs(sa_input))) if sa_input.size > 0 else 0.0,
        "peak_sa_m_s2": float(np.max(np.abs(spectra.psa))) if spectra.psa.size > 0 else 0.0,
        "raw_pga_input_units": raw_pga_m_s2 / factor if factor != 0.0 else raw_pga_m_s2,
        "raw_pga_m_s2": raw_pga_m_s2,
        "raw_pga_g": raw_pga_m_s2 / 9.81,
        "raw_time_s": raw_time_d,
        "raw_acc_input_units": raw_acc_input_d,
        "raw_acc_m_s2": raw_acc_d,
        "time_s": [float(v) for v in time_d],
        "acc_input_units": [float(v) for v in acc_input_d],
        "acc_m_s2": [float(v) for v in acc_d],
        "vel_m_s": [float(v) for v in vel_d],
        "disp_m": [float(v) for v in disp_d],
        "period_s": [float(v) for v in period_d],
        "sa_input_units": [float(v) for v in sa_input_d],
        "sa_m_s2": [float(v) for v in sa_m_s2_d],
        "sv_m_s": [float(v) for v in sv_d],
        "sd_m": [float(v) for v in sd_d],
    }


def _resolve_output_root(raw: str) -> Path:
    text = raw.strip()
    if not text:
        return _default_output_root()
    out = Path(text).expanduser()
    if out.is_absolute():
        return out.resolve()
    return (_repo_root() / out).resolve()


def _motion_source_label(path: Path) -> str:
    parent = path.parent.name.strip()
    name = path.name.strip()
    if parent and parent != name:
        return f"{parent} / {name}"
    return str(path)


def _motion_source_group_label(file_path: Path, lib_dir: Path) -> str:
    root_label = _motion_source_label(lib_dir)
    try:
        relative = file_path.resolve().relative_to(lib_dir.resolve())
    except ValueError:
        return root_label
    if len(relative.parts) <= 1:
        return root_label
    top_level = relative.parts[0].strip()
    if not top_level:
        return root_label
    parent = lib_dir.parent.name.strip()
    if parent and parent != top_level:
        return f"{parent} / {top_level}"
    return top_level


def _is_generated_motion_artifact(file_path: Path, lib_dir: Path) -> bool:
    generated_dirs = {"outputs_gui", "testdsout"}
    try:
        relative = file_path.resolve().relative_to(lib_dir.resolve())
    except ValueError:
        return False
    return any(part.strip().lower() in generated_dirs for part in relative.parts[:-1])


def _scan_motion_library(lib_dirs: list[Path]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for lib_dir in lib_dirs:
        if not lib_dir.is_dir():
            continue
        for f in sorted(lib_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in {".csv", ".at2", ".txt"}:
                continue
            if _is_generated_motion_artifact(f, lib_dir):
                continue
            resolved = str(f.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            results.append(
                {
                    "name": f.stem,
                    "file_name": f.name,
                    "path": resolved,
                    "format": f.suffix.lower().lstrip("."),
                    "source": resolved,
                    "source_label": _motion_source_label(lib_dir),
                    "source_group_label": _motion_source_group_label(f, lib_dir),
                }
            )
    results.sort(key=lambda item: (item["name"].lower(), item["file_name"].lower(), item["path"]))
    return results


def _resolve_motion_library_dirs(extra_dirs: list[str] | None) -> list[Path]:
    resolved_dirs: list[Path] = []
    seen: set[str] = set()
    for raw_dir in extra_dirs or []:
        text = (raw_dir or "").strip()
        if not text:
            continue
        try:
            candidate = _resolve_input_path(text, label="Motion library directory")
        except FileNotFoundError:
            continue
        if not candidate.is_dir():
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        resolved_dirs.append(candidate)
    return resolved_dirs


def _collect_runs(output_root: Path) -> list[Path]:
    run_dirs = _scan_run_dirs(output_root)
    unique_by_id: dict[str, Path] = {}
    for run_dir in run_dirs:
        unique_by_id.setdefault(run_dir.name, run_dir)
    return list(unique_by_id.values())


def _looks_like_run_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return (path / "run_meta.json").exists()


def _load_result_or_409(run_dir: Path) -> ResultStore:
    try:
        return load_result(run_dir)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Run artifacts incomplete for {run_dir.name}: {exc}",
        ) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Run artifacts unreadable for {run_dir.name}: {exc}",
        ) from exc


def _path_mtime(path: Path) -> float:
    try:
        return float(path.stat().st_mtime)
    except OSError:
        return 0.0


def _scan_run_dirs(output_root: Path) -> list[Path]:
    if not output_root.exists() or not output_root.is_dir():
        return []
    seen: dict[Path, Path] = {}
    try:
        for meta_path in output_root.rglob("run_meta.json"):
            run_dir = meta_path.parent.resolve()
            if _looks_like_run_dir(run_dir):
                seen[run_dir] = run_dir
    except OSError:
        return []
    return sorted(seen.values(), key=_path_mtime, reverse=True)


def _resolve_run_search_roots(output_root_raw: str) -> list[Path]:
    roots: list[Path] = []
    if output_root_raw.strip():
        roots.append(_safe_real_path(output_root_raw))
    roots.append(_default_output_root())
    roots.append((_repo_root() / "out").resolve())
    dedup: dict[Path, Path] = {}
    for root in roots:
        dedup[root.resolve()] = root.resolve()
    return list(dedup.values())


def _resolve_run_dir(run_id: str, output_root: str) -> Path:
    run_id_text = run_id.strip()
    if not run_id_text:
        raise HTTPException(status_code=404, detail="Run not found: <empty run id>")

    roots = _resolve_run_search_roots(output_root)
    for root in roots:
        direct = (root / run_id_text).resolve()
        if _looks_like_run_dir(direct):
            return direct

    candidates: list[Path] = []
    for root in roots:
        for run_dir in _scan_run_dirs(root):
            if run_dir.name == run_id_text:
                candidates.append(run_dir)
    if candidates:
        candidates.sort(key=_path_mtime, reverse=True)
        return candidates[0]

    raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")


def _read_metrics(sqlite_path: Path) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if not sqlite_path.exists():
        return metrics
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute("SELECT name, value FROM metrics").fetchall()
        for name, value in rows:
            try:
                metrics[str(name)] = float(value)
            except (TypeError, ValueError):
                continue
    finally:
        conn.close()
    return metrics


def _read_run_meta_raw(run_dir: Path) -> dict[str, object]:
    meta_path = run_dir / "run_meta.json"
    if not meta_path.exists():
        return {}
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _read_run_meta(run_dir: Path) -> dict[str, str]:
    raw = _read_run_meta_raw(run_dir)
    out: dict[str, str] = {}
    for key in (
        "timestamp_utc",
        "solver_backend",
        "status",
        "message",
        "input_motion",
        "dt_s",
        "delta_t_s",
        "config_snapshot",
    ):
        value = raw.get(key)
        if isinstance(value, str):
            out[key] = value
        elif isinstance(value, (int, float)):
            out[key] = str(value)
    return out


def _json_mapping(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _as_int(value: object, fallback: int = 0, *, minimum: int | None = None) -> int:
    parsed = fallback
    if isinstance(value, bool):
        parsed = int(value)
    elif isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if np.isfinite(value):
            parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(float(value))
        except ValueError:
            parsed = fallback
    if minimum is not None and parsed < minimum:
        return minimum
    return parsed


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        f = float(value)
        return f if np.isfinite(f) else default
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _read_project_name(sqlite_path: Path) -> str:
    if not sqlite_path.exists():
        return ""
    conn = sqlite3.connect(sqlite_path)
    try:
        row = conn.execute("SELECT project_name FROM runs LIMIT 1").fetchone()
        if row is None or row[0] is None:
            return ""
        return str(row[0])
    finally:
        conn.close()


def _read_artifacts(sqlite_path: Path) -> list[dict[str, str]]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT kind, path FROM artifacts ORDER BY kind ASC, path ASC"
        ).fetchall()
        out: list[dict[str, str]] = []
        for kind, path in rows:
            out.append({"kind": str(kind), "path": str(path)})
        return out
    finally:
        conn.close()


def _read_output_layers(sqlite_path: Path) -> list[str]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT DISTINCT layer_name FROM mesh_slices ORDER BY layer_name ASC"
        ).fetchall()
        return [str(r[0]) for r in rows if r and r[0] is not None]
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


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

    # Read PWP raw data from text file
    try:
        data = np.loadtxt(pwp_path, ndmin=2)
    except Exception:
        return None, None, None
    if data.size == 0:
        return None, None, None
    pwp = data[:, -1] if data.ndim == 2 and data.shape[1] > 1 else data.ravel()
    pwp = np.asarray(pwp, dtype=np.float64)
    if pwp.size == 0:
        return None, None, None

    delta_u = np.maximum(-pwp, 0.0)
    if delta_u.size == 0:
        return None, None, None

    delta_u_max = float(np.max(delta_u))
    ru_max = float(np.clip(delta_u_max / sigma_v0_mid_kpa, 0.0, 1.5))
    sigma_v_eff_min = float(max(sigma_v0_mid_kpa - delta_u_max, 0.0))
    return ru_max, delta_u_max, sigma_v_eff_min


def _read_layer_response_summary(
    run_dir: Path | None,
) -> dict[int, dict[str, float]]:
    if run_dir is None:
        return {}
    summary_path = run_dir / "layer_response_summary.csv"
    if not summary_path.exists():
        return {}
    try:
        rows = summary_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    if not rows:
        return {}

    out: dict[int, dict[str, float]] = {}
    for line in rows[1:]:
        text = line.strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split(",")]
        if len(parts) < 8:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        values: dict[str, float] = {}
        for key, raw in (
            ("gamma_max", parts[4]),
            ("tau_peak_kpa", parts[5]),
            ("secant_g_pa", parts[6]),
            ("secant_g_over_gmax", parts[7]),
        ):
            if not raw:
                continue
            try:
                values[key] = float(raw)
            except ValueError:
                continue
        out[idx] = values
    return out


def _read_profile_layer_summary(
    sqlite_path: Path,
    run_dir: Path | None = None,
) -> list[ResultProfileLayerRow]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    try:
        if not _table_exists(conn, "layers"):
            return []
        layer_rows = conn.execute(
            "SELECT idx, name, thickness_m, unit_weight_kN_m3, vs_m_s, material "
            "FROM layers ORDER BY idx ASC"
        ).fetchall()

        mesh_by_name: dict[str, tuple[float, float, int]] = {}
        if _table_exists(conn, "mesh_slices"):
            mesh_rows = conn.execute(
                "SELECT layer_name, MIN(z_top), MAX(z_bot), SUM(n_sub) "
                "FROM mesh_slices GROUP BY layer_name"
            ).fetchall()
            for name, z_top, z_bot, n_sub in mesh_rows:
                key = str(name)
                mesh_by_name[key] = (
                    float(z_top),
                    float(z_bot),
                    max(1, int(float(n_sub))),
                )

        gamma_by_idx: dict[int, float] = {}
        damping_by_idx: dict[int, float] = {}
        tau_peak_by_idx: dict[int, float] = {}
        secant_g_pa_by_idx: dict[int, float] = {}
        secant_g_over_gmax_by_idx: dict[int, float] = {}
        if _table_exists(conn, "eql_layers"):
            eql_rows = conn.execute(
                "SELECT layer_idx, gamma_max, damping FROM eql_layers ORDER BY layer_idx ASC"
            ).fetchall()
            for idx, gamma, damp in eql_rows:
                try:
                    gamma_by_idx[int(idx)] = float(gamma)
                    damping_by_idx[int(idx)] = float(damp)
                except (TypeError, ValueError):
                    continue

        layer_response_summary = _read_layer_response_summary(run_dir)
        for idx, row in layer_response_summary.items():
            gamma_val = row.get("gamma_max")
            if gamma_val is not None and np.isfinite(gamma_val):
                gamma_by_idx[idx] = float(gamma_val)
            tau_peak_val = row.get("tau_peak_kpa")
            if tau_peak_val is not None and np.isfinite(tau_peak_val):
                tau_peak_by_idx[idx] = float(tau_peak_val)
            secant_g_val = row.get("secant_g_pa")
            if secant_g_val is not None and np.isfinite(secant_g_val):
                secant_g_pa_by_idx[idx] = float(secant_g_val)
            secant_ratio_val = row.get("secant_g_over_gmax")
            if secant_ratio_val is not None and np.isfinite(secant_ratio_val):
                secant_g_over_gmax_by_idx[idx] = float(secant_ratio_val)

        # Fallback for nonlinear: read peak strain/stress from recorded hysteresis files
        if not gamma_by_idx and run_dir is not None:
            for layer_idx_zero in range(len(layer_rows)):
                hyst = _load_layer_recorded_hysteresis(run_dir, layer_index_zero_based=layer_idx_zero)
                if hyst is not None:
                    strain_arr, stress_arr = hyst
                    if strain_arr.size > 0:
                        gamma_by_idx[layer_idx_zero] = float(np.max(np.abs(strain_arr)))
                    if stress_arr.size > 0:
                        tau_peak_by_idx[layer_idx_zero] = float(np.max(np.abs(stress_arr)))

        # Second fallback: use hysteresis proxy builder if still no data
        if not gamma_by_idx and run_dir is not None:
            try:
                hyst_resp = _build_hysteresis_response(
                    run_id=run_dir.name,
                    run_dir=run_dir,
                    sqlite_path=sqlite_path,
                    max_points=50,
                )
                for hl in hyst_resp.layers:
                    gamma_by_idx[hl.layer_index] = hl.strain_amplitude
                    if hl.stress:
                        tau_peak_by_idx[hl.layer_index] = float(max(abs(s) for s in hl.stress))
                    damping_by_idx[hl.layer_index] = hl.damping_proxy
            except Exception:
                pass  # non-critical fallback

        diagnostics_by_idx: dict[int, object] = {}
        diagnostics_by_name: dict[str, object] = {}
        fallback_layers: list[dict[str, object]] = []
        for idx, name, thickness, unit_weight, vs, material in layer_rows:
            fallback_layers.append(
                {
                    "name": str(name),
                    "thickness_m": float(thickness),
                    "unit_weight_kN_m3": float(unit_weight),
                    "vs_m_s": float(vs),
                    "material": str(material),
                    "material_params": {},
                }
            )

        profile_layers_input: list[object] = fallback_layers
        water_table_depth_m: float | None = None
        if run_dir is not None:
            run_meta = _read_run_meta(run_dir)
            snapshot_path = run_meta.get("config_snapshot", "").strip()
            if snapshot_path:
                candidate = Path(snapshot_path)
                if not candidate.is_absolute():
                    candidate = (run_dir / candidate).resolve()
                if candidate.exists():
                    try:
                        cfg = load_project_config(candidate)
                        profile_layers_input = list(cfg.profile.layers)
                        water_table_depth_m = cfg.profile.water_table_depth_m
                    except Exception:
                        profile_layers_input = fallback_layers
                        water_table_depth_m = None

        try:
            diagnostics_rows = compute_profile_diagnostics(
                profile_layers_input,
                water_table_depth_m=water_table_depth_m,
            )
        except Exception:
            diagnostics_rows = []
        for row in diagnostics_rows:
            diagnostics_by_idx[int(row.index)] = row
            diagnostics_by_name[row.name] = row

        layers: list[ResultProfileLayerRow] = []
        cum_depth = 0.0
        for idx, name, thickness, unit_weight, vs, material in layer_rows:
            layer_idx = int(idx)
            layer_name = str(name)
            t_m = float(thickness)
            default_top = float(cum_depth)
            default_bot = float(cum_depth + t_m)
            cum_depth = default_bot

            z_top_m, z_bottom_m, n_sub = mesh_by_name.get(
                layer_name,
                (
                    default_top,
                    default_bot,
                    1,
                ),
            )
            diag = diagnostics_by_idx.get(layer_idx)
            if diag is None:
                diag = diagnostics_by_idx.get(layer_idx - 1)
            if diag is None:
                diag = diagnostics_by_name.get(layer_name)

            gamma_max = gamma_by_idx.get(layer_idx)
            if gamma_max is None:
                gamma_max = gamma_by_idx.get(layer_idx + 1)
            damping_ratio_val = damping_by_idx.get(layer_idx)
            if damping_ratio_val is None:
                damping_ratio_val = damping_by_idx.get(layer_idx + 1)

            tau_peak_kpa_val: float | None = tau_peak_by_idx.get(layer_idx)
            if tau_peak_kpa_val is None and gamma_max is not None and gamma_max > 0:
                tau_peak_kpa_val = _estimate_gmax_kpa(float(vs), float(unit_weight)) * gamma_max
            if tau_peak_kpa_val is None and diag is not None:
                tau_peak_kpa_val = getattr(diag, "implied_strength_kpa", None)
            secant_g_pa_val = secant_g_pa_by_idx.get(layer_idx)
            if secant_g_pa_val is None:
                secant_g_pa_val = secant_g_pa_by_idx.get(layer_idx + 1)
            secant_g_over_gmax_val = secant_g_over_gmax_by_idx.get(layer_idx)
            if secant_g_over_gmax_val is None:
                secant_g_over_gmax_val = secant_g_over_gmax_by_idx.get(layer_idx + 1)

            unit_weight_kn_m3 = float(unit_weight)
            sigma_v0_mid_kpa = (
                float(getattr(diag, "sigma_v0_mid_kpa"))
                if diag is not None
                else (max(default_top, 0.0) + (0.5 * max(t_m, 0.0))) * max(unit_weight_kn_m3, 0.0)
            )
            sigma_v_eff_mid_kpa = (
                float(getattr(diag, "sigma_v_eff_mid_kpa"))
                if diag is not None
                else None
            )
            pore_pressure_kpa = (
                float(getattr(diag, "pore_water_pressure_kpa"))
                if diag is not None
                else None
            )
            small_strain_damping_ratio = (
                float(getattr(diag, "small_strain_damping_ratio"))
                if diag is not None and getattr(diag, "small_strain_damping_ratio") is not None
                else None
            )
            max_frequency_hz = (
                float(getattr(diag, "max_frequency_hz"))
                if diag is not None and getattr(diag, "max_frequency_hz") is not None
                else None
            )
            implied_strength_kpa = (
                float(getattr(diag, "implied_strength_kpa"))
                if diag is not None and getattr(diag, "implied_strength_kpa") is not None
                else None
            )
            normalized_implied_strength = (
                float(getattr(diag, "normalized_implied_strength"))
                if diag is not None and getattr(diag, "normalized_implied_strength") is not None
                else None
            )
            implied_friction_angle_deg = (
                float(getattr(diag, "implied_friction_angle_deg"))
                if diag is not None and getattr(diag, "implied_friction_angle_deg") is not None
                else None
            )
            gqh_mode = (
                str(getattr(diag, "gqh_mode"))
                if diag is not None and getattr(diag, "gqh_mode") is not None
                else None
            )

            ru_max = None
            delta_u_max = None
            sigma_v_eff_min = None
            if run_dir is not None:
                ru_max, delta_u_max, sigma_v_eff_min = _read_layer_pwp_profile_stats(
                    run_dir,
                    layer_idx=layer_idx,
                    sigma_v0_mid_kpa=sigma_v0_mid_kpa,
                )

            layers.append(
                ResultProfileLayerRow(
                    idx=layer_idx,
                    name=layer_name,
                    material=str(material),
                    thickness_m=t_m,
                    unit_weight_kn_m3=unit_weight_kn_m3,
                    vs_m_s=float(vs),
                    z_top_m=float(z_top_m),
                    z_bottom_m=float(z_bottom_m),
                    n_sub=max(1, int(n_sub)),
                    gamma_max=float(gamma_max) if gamma_max is not None else None,
                    damping_ratio=float(damping_ratio_val) if damping_ratio_val is not None else None,
                    tau_peak_kpa=tau_peak_kpa_val,
                    secant_g_pa=secant_g_pa_val,
                    secant_g_over_gmax=secant_g_over_gmax_val,
                    sigma_v0_mid_kpa=sigma_v0_mid_kpa,
                    sigma_v_eff_mid_kpa=sigma_v_eff_mid_kpa,
                    pore_water_pressure_kpa=pore_pressure_kpa,
                    small_strain_damping_ratio=small_strain_damping_ratio,
                    max_frequency_hz=max_frequency_hz,
                    implied_strength_kpa=implied_strength_kpa,
                    normalized_implied_strength=normalized_implied_strength,
                    implied_friction_angle_deg=implied_friction_angle_deg,
                    gqh_mode=gqh_mode,
                    ru_max=ru_max,
                    delta_u_max=delta_u_max,
                    sigma_v_eff_min=sigma_v_eff_min,
                )
            )
        return layers
    finally:
        conn.close()


def _read_convergence(sqlite_path: Path, run_dir: Path | None = None) -> dict[str, object]:
    if not sqlite_path.exists():
        return {"available": False}
    conn = sqlite3.connect(sqlite_path)
    try:
        try:
            row = conn.execute(
                "SELECT iterations, converged, max_change_last, max_change_max "
                "FROM eql_summary LIMIT 1"
            ).fetchone()
        except sqlite3.Error:
            row = None
        if row is None:
            return {"available": False}
        return {
            "available": True,
            "iterations": int(row[0]),
            "converged": bool(int(row[1])),
            "max_change_last": float(row[2]),
            "max_change_max": float(row[3]),
        }
    finally:
        conn.close()


def _optional_int(value: object) -> int | None:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            if np.isfinite(float(value)):
                return int(float(value))
            return None
        text = str(value).strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _optional_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            parsed = float(value)
            return parsed if np.isfinite(parsed) else None
        text = str(value).strip()
        if not text:
            return None
        parsed = float(text)
        return parsed if np.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def _run_health_summary(sqlite_path: Path, run_dir: Path) -> dict[str, object]:
    conv = _read_convergence(sqlite_path, run_dir=run_dir)
    if not bool(conv.get("available", False)):
        return {
            "convergence_mode": "none",
            "convergence_severity": "neutral",
            "converged": None,
            "solver_warning_count": None,
            "solver_failed_converge_count": None,
            "solver_analyze_failed_count": None,
            "solver_divide_by_zero_count": None,
            "solver_dynamic_fallback_failed_count": None,
        }

    if "iterations" in conv or "max_change_last" in conv:
        converged = bool(conv.get("converged", False))
        return {
            "convergence_mode": "eql",
            "convergence_severity": "ok" if converged else "warning",
            "converged": converged,
            "solver_warning_count": None,
            "solver_failed_converge_count": None,
            "solver_analyze_failed_count": None,
            "solver_divide_by_zero_count": None,
            "solver_dynamic_fallback_failed_count": None,
        }

    severity = str(conv.get("severity", "unknown")).strip().lower() or "unknown"
    return {
        "convergence_mode": "solver",
        "convergence_severity": severity,
        "converged": None,
        "solver_warning_count": _optional_int(conv.get("warning_count")),
        "solver_failed_converge_count": _optional_int(conv.get("failed_converge_count")),
        "solver_analyze_failed_count": _optional_int(conv.get("analyze_failed_count")),
        "solver_divide_by_zero_count": _optional_int(conv.get("divide_by_zero_count")),
        "solver_dynamic_fallback_failed_count": _optional_int(conv.get("dynamic_fallback_failed")),
    }


def _read_layer_rows(sqlite_path: Path) -> list[dict[str, object]]:
    if not sqlite_path.exists():
        return []
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT idx, name, thickness_m, unit_weight_kN_m3, vs_m_s, material "
            "FROM layers ORDER BY idx ASC"
        ).fetchall()
        out: list[dict[str, object]] = []
        for idx, name, thickness, unit_weight, vs, material in rows:
            out.append(
                {
                    "idx": int(idx),
                    "name": str(name),
                    "thickness_m": float(thickness),
                    "unit_weight_kN_m3": float(unit_weight),
                    "vs_m_s": float(vs),
                    "material": str(material),
                }
            )
        return out
    finally:
        conn.close()


def _read_eql_gamma_max_map(sqlite_path: Path) -> dict[int, float]:
    if not sqlite_path.exists():
        return {}
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute(
            "SELECT layer_idx, gamma_max FROM eql_layers ORDER BY layer_idx ASC"
        ).fetchall()
        out: dict[int, float] = {}
        for idx, gamma_max in rows:
            try:
                out[int(idx)] = float(gamma_max)
            except (TypeError, ValueError):
                continue
        return out
    finally:
        conn.close()


def _to_material_type(raw: object) -> MaterialType | None:
    if isinstance(raw, MaterialType):
        return raw
    if isinstance(raw, str):
        key = raw.strip().lower()
        for material in MaterialType:
            if material.value == key:
                return material
    return None


def _estimate_gmax_kpa(vs_m_s: float, unit_weight_kn_m3: float) -> float:
    if vs_m_s <= 0.0:
        return 1.0
    if unit_weight_kn_m3 <= 0.0:
        unit_weight_kn_m3 = 18.0
    rho_kg_m3 = (unit_weight_kn_m3 * 1000.0) / 9.81
    gmax_kpa = (rho_kg_m3 * vs_m_s * vs_m_s) / 1000.0
    return float(max(gmax_kpa, 1.0))


def _layer_loop_profile(
    *,
    material: MaterialType,
    material_params: dict[str, float],
    vs_m_s: float,
    unit_weight_kn_m3: float,
) -> tuple[MaterialType, dict[str, float], bool, str]:
    if material == MaterialType.MKZ:
        params = dict(material_params)
        params.setdefault("gmax", _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3))
        params.setdefault("gamma_ref", 0.001)
        params.setdefault("damping_min", 0.01)
        params.setdefault("damping_max", 0.12)
        return MaterialType.MKZ, params, False, "mkz"
    if material == MaterialType.GQH:
        params = dict(material_params)
        params.setdefault("gmax", _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3))
        params.setdefault("gamma_ref", 0.001)
        params.setdefault("a1", 1.0)
        params.setdefault("a2", 0.35)
        params.setdefault("m", 2.0)
        params.setdefault("damping_min", 0.01)
        params.setdefault("damping_max", 0.12)
        return MaterialType.GQH, params, False, "gqh"

    # Elastic layers use MKZ proxy defaults for derived metrics.
    gamma_ref = 0.0005 if material == MaterialType.ELASTIC else 0.0012
    proxy_params = {
        "gmax": _estimate_gmax_kpa(vs_m_s, unit_weight_kn_m3),
        "gamma_ref": gamma_ref,
        "damping_min": 0.01,
        "damping_max": 0.10,
    }
    return MaterialType.MKZ, proxy_params, True, f"{material.value}_mkz_proxy"


def _load_run_config_snapshot(run_dir: Path, meta_raw: dict[str, object]) -> ProjectConfig | None:
    candidates: list[Path] = []
    run_snapshot = run_dir / "config_snapshot.json"
    if run_snapshot.exists():
        candidates.append(run_snapshot)
    meta_snapshot = meta_raw.get("config_snapshot")
    if isinstance(meta_snapshot, str) and meta_snapshot.strip():
        meta_path = Path(meta_snapshot).expanduser()
        if meta_path.exists():
            candidates.append(meta_path)

    for path in candidates:
        try:
            return load_project_config(path)
        except (ValueError, OSError):
            continue
    return None


def _downsample_series(values: np.ndarray, max_points: int) -> list[float]:
    if values.size == 0:
        return []
    if values.size <= max_points:
        return [float(v) for v in values]
    step = max(1, values.size // max_points)
    return [float(v) for v in values[::step]]


def _load_matrix_safe(path: Path) -> np.ndarray | None:
    if not path.exists() or path.stat().st_size <= 0:
        return None
    try:
        arr = np.loadtxt(path, ndmin=2)
    except Exception:
        return None
    matrix = np.asarray(arr, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 8:
        return None
    return matrix


def _looks_like_time_axis(values: np.ndarray) -> bool:
    if values.size < 3:
        return False
    if not np.all(np.isfinite(values)):
        return False
    diffs = np.diff(values)
    if diffs.size == 0:
        return False
    if not np.all(diffs >= -1.0e-12):
        return False
    return float(np.median(diffs)) > 0.0


def _extract_recorder_component(matrix: np.ndarray) -> np.ndarray:
    if matrix.shape[1] <= 1:
        return matrix[:, 0]
    start = 1 if _looks_like_time_axis(matrix[:, 0]) else 0
    values = matrix[:, start:]
    if values.size == 0:
        values = matrix
    return values[:, -1]


def _load_layer_recorded_hysteresis(
    run_dir: Path,
    *,
    layer_index_zero_based: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    if layer_index_zero_based < 0:
        return None
    tag_candidates = [layer_index_zero_based + 1, layer_index_zero_based]
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
        strain = np.asarray(strain[:n], dtype=np.float64)
        stress = np.asarray(stress[:n], dtype=np.float64)
        finite_mask = np.isfinite(strain) & np.isfinite(stress)
        if int(np.count_nonzero(finite_mask)) < 8:
            continue
        return strain[finite_mask], stress[finite_mask]
    return None


def _build_hysteresis_response(
    *,
    run_id: str,
    run_dir: Path,
    sqlite_path: Path,
    max_points: int = 700,
) -> ResultHysteresisResponse:
    rs = load_result(run_dir)
    meta_raw = _read_run_meta_raw(run_dir)
    cfg = _load_run_config_snapshot(run_dir, meta_raw)
    eql_gamma_max_map = _read_eql_gamma_max_map(sqlite_path)

    source = "config_snapshot" if cfg is not None else "sqlite_layers_fallback"
    note_parts: list[str] = []

    pga = float(np.max(np.abs(rs.acc_surface))) if rs.acc_surface.size > 0 else 0.0
    pga_g = max(pga / 9.81, 0.0)
    ru_max = float(np.max(rs.ru)) if rs.ru.size > 0 else 0.0

    layer_items: list[dict[str, object]] = []
    if cfg is not None:
        for idx, layer in enumerate(cfg.profile.layers):
            layer_items.append(
                {
                    "idx": idx,
                    "name": layer.name,
                    "thickness_m": float(layer.thickness_m),
                    "unit_weight_kN_m3": float(layer.unit_weight_kn_m3),
                    "vs_m_s": float(layer.vs_m_s),
                    "material": layer.material,
                    "material_params": dict(layer.material_params),
                }
            )
    else:
        for row in _read_layer_rows(sqlite_path):
            material = _to_material_type(row.get("material"))
            if material is None:
                continue
            layer_items.append(
                {
                    "idx": row["idx"],
                    "name": row["name"],
                    "thickness_m": row["thickness_m"],
                    "unit_weight_kN_m3": row["unit_weight_kN_m3"],
                    "vs_m_s": row["vs_m_s"],
                    "material": material,
                    "material_params": {},
                }
            )

    layers: list[HysteresisLayerResponse] = []
    proxy_used = False
    recorded_layers = 0
    for item in layer_items:
        idx_obj = item.get("idx")
        name_obj = item.get("name")
        material_obj = item.get("material")
        if not isinstance(idx_obj, int) or not isinstance(name_obj, str):
            continue
        if not isinstance(material_obj, MaterialType):
            continue
        vs_raw = item.get("vs_m_s")
        if not isinstance(vs_raw, (int, float)):
            continue
        vs_m_s = float(vs_raw)
        unit_weight_raw = item.get("unit_weight_kN_m3")
        if not isinstance(unit_weight_raw, (int, float)):
            unit_weight = 18.0
        else:
            unit_weight = float(unit_weight_raw)
        params = item.get("material_params", {})
        material_params = params if isinstance(params, dict) else {}
        typed_params: dict[str, float] = {}
        for key, value in material_params.items():
            if isinstance(key, str) and isinstance(value, (int, float)):
                typed_params[key] = float(value)

        loop_material, loop_params, is_proxy, model_name = _layer_loop_profile(
            material=material_obj,
            material_params=typed_params,
            vs_m_s=vs_m_s,
            unit_weight_kn_m3=unit_weight,
        )

        recorded_loop = _load_layer_recorded_hysteresis(
            run_dir,
            layer_index_zero_based=idx_obj,
        )
        gamma_ref = float(loop_params.get("gamma_ref", 0.001))
        if recorded_loop is not None:
            loop_strain, loop_stress = recorded_loop
            gamma_a = float(np.clip(np.max(np.abs(loop_strain)), 1.0e-6, 2.0e-2))
            loop_energy = float(abs(np.trapezoid(loop_stress, loop_strain)))
            tau_peak = float(np.max(np.abs(loop_stress))) if loop_stress.size > 0 else 0.0
            is_proxy = False
            model_name = f"{material_obj.value}_recorded"
            recorded_layers += 1
        else:
            proxy_used = proxy_used or is_proxy
            gamma_hint = eql_gamma_max_map.get(idx_obj)
            if gamma_hint is not None and np.isfinite(gamma_hint) and gamma_hint > 0.0:
                gamma_a = float(np.clip(gamma_hint, 1.0e-5, 2.0e-2))
            else:
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
            loop_strain = loop.strain
            loop_stress = loop.stress
            loop_energy = float(loop.energy_dissipation)
            tau_peak = float(np.max(np.abs(loop_stress))) if loop_stress.size > 0 else 0.0

        tau_cap = loop_params.get("tau_max")
        if tau_cap is not None and tau_cap > 0.0:
            mobilized_ratio = float(np.clip(tau_peak / tau_cap, 0.0, 1.0))
        else:
            tau_ref = float(max(abs(loop_params["gmax"] * gamma_a), 1.0e-9))
            mobilized_ratio = float(np.clip(tau_peak / tau_ref, 0.0, 1.0))

        if loop_material == MaterialType.MKZ:
            g_over_gmax = float(
                mkz_modulus_reduction(np.array([gamma_a], dtype=np.float64), gamma_ref=gamma_ref)[0]
            )
        else:
            g_over_gmax = float(
                gqh_modulus_reduction_from_params(
                    np.array([gamma_a], dtype=np.float64),
                    loop_params,
                )[0]
            )
        damping_proxy = float(
            bounded_damping_from_reduction(
                np.array([g_over_gmax], dtype=np.float64),
                damping_min=float(loop_params.get("damping_min", 0.01)),
                damping_max=float(loop_params.get("damping_max", 0.12)),
            )[0]
        )
        layers.append(
            HysteresisLayerResponse(
                layer_index=idx_obj,
                layer_name=name_obj,
                material=material_obj.value,
                model=model_name,
                is_proxy=is_proxy,
                strain_amplitude=float(gamma_a),
                loop_energy=loop_energy,
                mobilized_strength_ratio=mobilized_ratio,
                g_over_gmax=g_over_gmax,
                damping_proxy=damping_proxy,
                strain=_downsample_series(loop_strain, max_points=max_points),
                stress=_downsample_series(loop_stress, max_points=max_points),
            )
        )

    if cfg is None:
        note_parts.append("Config snapshot not found; using sqlite layer fallback.")
    if recorded_layers > 0:
        if recorded_layers >= len(layers):
            source = "recorders"
        else:
            source = "mixed_recorders_proxy"
            note_parts.append(
                f"Recorder stress-strain available for {recorded_layers}/{len(layers)} layers."
            )
    if proxy_used:
        note_parts.append(
            "Elastic layers shown as MKZ proxies until native recorder channels are added."
        )
    if not layers:
        note_parts.append("No layer data available for hysteresis rendering.")

    return ResultHysteresisResponse(
        run_id=run_id,
        source=source,
        note=" ".join(note_parts).strip(),
        layers=layers,
    )


def _as_positive_float_or_none(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    v = float(value)
    if not np.isfinite(v) or v <= 0.0:
        return None
    return v


def _as_non_negative_float_or_none(value: object) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    v = float(value)
    if not np.isfinite(v) or v < 0.0:
        return None
    return v


def _as_non_negative_float(value: object, fallback: float) -> float:
    if not isinstance(value, (int, float)):
        return fallback
    v = float(value)
    if not np.isfinite(v) or v < 0.0:
        return fallback
    return v


def _numeric_dict(raw: object) -> dict[str, float]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, (int, float)):
            continue
        v = float(value)
        if np.isfinite(v):
            out[key] = v
    return out


def _numeric_list(raw: object) -> list[float]:
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for value in raw:
        if not isinstance(value, (int, float)):
            continue
        v = float(value)
        if np.isfinite(v):
            out.append(v)
    return out


def _darendeli_payload(raw: object) -> dict[str, object] | None:
    if not isinstance(raw, dict):
        return None
    try:
        calibrated = DarendeliCalibration.model_validate(raw)
    except ValidationError:
        return None
    return cast(dict[str, object], calibrated.model_dump(mode="json"))


def _layer_gmax_seed(layer: WizardLayer) -> float:
    density_t_m3 = float(layer.unit_weight_kn_m3) / 9.81
    return density_t_m3 * float(layer.vs_m_s) * float(layer.vs_m_s)


def _material_preview_curves(
    material: MaterialType,
    params: dict[str, float],
    strain: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    damping_min = float(params.get("damping_min", 0.01))
    damping_max = float(params.get("damping_max", 0.12))
    gamma_ref = float(params.get("gamma_ref", 1.0e-3))
    if material == MaterialType.MKZ:
        reduction = mkz_modulus_reduction(
            strain,
            gamma_ref=gamma_ref,
            g_reduction_min=float(params.get("g_reduction_min", 0.0)),
        )
    elif material == MaterialType.GQH:
        reduction = gqh_modulus_reduction_from_params(
            strain,
            params,
        )
    else:
        raise ValueError("Preview curves are available only for MKZ/GQH materials.")
    coeffs = mrdf_coefficients_from_params(params)
    if coeffs is None:
        damping = bounded_damping_from_reduction(
            reduction,
            damping_min=damping_min,
            damping_max=damping_max,
        )
    else:
        masing = compute_masing_damping_ratio(material, params, strain)
        factors = np.asarray(
            [
                evaluate_mrdf_factor(coeffs, float(gamma), g_over_gmax=float(red))
                for gamma, red in zip(strain, reduction, strict=False)
            ],
            dtype=np.float64,
        )
        damping = np.maximum(damping_min, masing * factors)
        damping = np.maximum.accumulate(np.clip(damping, damping_min, 0.5))
    return reduction, damping


def _build_layer_calibration_preview(
    layer: WizardLayer,
    *,
    sigma_v_eff_mid_kpa: float | None = None,
) -> LayerCalibrationPreviewResponse:
    material = layer.material
    warnings: list[str] = []
    if material not in {MaterialType.MKZ, MaterialType.GQH}:
        return LayerCalibrationPreviewResponse(
            available=False,
            material=material.value,
            source="unsupported",
            warnings=["Layer preview is currently available only for MKZ/GQH materials."],
        )

    calibration = layer.calibration
    strain_min = calibration.strain_min if calibration is not None else 1.0e-6
    strain_max = calibration.strain_max if calibration is not None else 1.0e-1
    n_points = calibration.n_points if calibration is not None else 60
    strain = np.logspace(
        np.log10(strain_min),
        np.log10(strain_max),
        int(n_points),
        dtype=np.float64,
    )

    raw_params = dict(layer.material_params)
    gmax_seed = float(raw_params.get("gmax", _layer_gmax_seed(layer)))
    raw_params.setdefault("gmax", gmax_seed)

    target_available = calibration is not None
    target_modulus: np.ndarray = np.asarray([], dtype=np.float64)
    target_damping: np.ndarray = np.asarray([], dtype=np.float64)
    calibrated_params: dict[str, float] = {}
    source = "manual"
    sigma_mid_eff = (
        float(sigma_v_eff_mid_kpa)
        if sigma_v_eff_mid_kpa is not None and np.isfinite(sigma_v_eff_mid_kpa)
        else None
    )
    sigma_mean_eff: float | None = None
    gqh_mode: str | None = None
    modulus_rmse: float | None = None
    damping_rmse: float | None = None
    strength_ratio_achieved: float | None = None
    fit_procedure: str | None = None
    fit_limits_applied: dict[str, float | bool | str] | None = None
    fit_stale = bool(getattr(layer, "fit_stale", False))
    reference_curve = (layer.reference_curve or "darendeli").strip().lower()

    if calibration is not None:
        source = calibration.source
        if reference_curve == "darendeli":
            sigma_mean_eff = calibration.mean_effective_stress_kpa
            if sigma_mean_eff is None:
                if calibration.k0 is None:
                    warnings.append(
                        "Calibration requires mean_effective_stress_kpa or k0 for stress context."
                    )
                    return LayerCalibrationPreviewResponse(
                        available=False,
                        material=material.value,
                        source=source,
                        target_available=target_available,
                        warnings=warnings,
                    )
                sigma_eff_seed = sigma_mid_eff
                if sigma_eff_seed is None or sigma_eff_seed <= 0.0:
                    sigma_eff_seed = max(0.5 * layer.thickness_m * layer.unit_weight_kn_m3, 1.0e-3)
                    warnings.append(
                        "Profile effective stress was not provided for K0-based calibration; "
                        "using layer midpoint stress estimate."
                    )
                sigma_mean_eff = mean_effective_stress_from_k0(sigma_eff_seed, calibration.k0)
            if material == MaterialType.MKZ:
                calibrated = calibrate_mkz_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=calibration.plasticity_index,
                    ocr=calibration.ocr,
                    mean_effective_stress_kpa=sigma_mean_eff,
                    frequency_hz=calibration.frequency_hz,
                    num_cycles=calibration.num_cycles,
                    atmospheric_pressure_kpa=calibration.atmospheric_pressure_kpa,
                    strain_min=calibration.strain_min,
                    strain_max=calibration.strain_max,
                    n_points=calibration.n_points,
                    reload_factor=calibration.reload_factor or 2.0,
                )
            else:
                tau_target = calibration.target_strength_kpa
                if tau_target is None:
                    tau_target = raw_params.get("tau_max")
                calibrated = calibrate_gqh_from_darendeli(
                    gmax=gmax_seed,
                    plasticity_index=calibration.plasticity_index,
                    ocr=calibration.ocr,
                    mean_effective_stress_kpa=sigma_mean_eff,
                    sigma_v_eff_mid_kpa=sigma_mid_eff,
                    k0=calibration.k0,
                    frequency_hz=calibration.frequency_hz,
                    num_cycles=calibration.num_cycles,
                    atmospheric_pressure_kpa=calibration.atmospheric_pressure_kpa,
                    strain_min=calibration.strain_min,
                    strain_max=calibration.strain_max,
                    n_points=calibration.n_points,
                    tau_target_kpa=tau_target,
                    fit_strain_min=calibration.fit_strain_min,
                    fit_strain_max=calibration.fit_strain_max,
                    target_strength_ratio=calibration.target_strength_ratio,
                    target_strength_strain=calibration.target_strength_strain,
                    reload_factor=calibration.reload_factor or 1.6,
                    fit_procedure=calibration.fit_procedure,
                    fit_limits=(
                        calibration.fit_limits.model_dump(exclude_none=True)
                        if calibration.fit_limits is not None
                        else None
                    ),
                )
                gqh_mode = calibrated.gqh_mode
            modulus_rmse = calibrated.modulus_rmse
            damping_rmse = calibrated.damping_rmse
            strength_ratio_achieved = calibrated.strength_ratio_achieved
            fit_procedure = calibrated.fit_procedure
            fit_limits_applied = calibrated.fit_limits_applied
            target_curves = generate_darendeli_curves(
                plasticity_index=calibration.plasticity_index,
                ocr=calibration.ocr,
                mean_effective_stress_kpa=sigma_mean_eff,
                frequency_hz=calibration.frequency_hz,
                num_cycles=calibration.num_cycles,
                atmospheric_pressure_kpa=calibration.atmospheric_pressure_kpa,
                strain_min=calibration.strain_min,
                strain_max=calibration.strain_max,
                n_points=calibration.n_points,
            )
            target_modulus = target_curves.modulus_reduction
            target_damping = target_curves.damping_ratio
            strain = target_curves.strain.astype(np.float64)
            calibrated_params = dict(calibrated.material_params)
        else:
            source = f"reference:{reference_curve}"
            try:
                target_curves = get_reference_curves(
                    reference_curve,
                    plasticity_index=calibration.plasticity_index,
                    strain_min=calibration.strain_min,
                    strain_max=calibration.strain_max,
                    n_points=calibration.n_points,
                )
            except ValueError as exc:
                warnings.append(str(exc))
                return LayerCalibrationPreviewResponse(
                    available=False,
                    material=material.value,
                    source=source,
                    target_available=target_available,
                    warnings=warnings,
                )
            target_modulus = target_curves.modulus_reduction
            target_damping = target_curves.damping_ratio
            strain = target_curves.strain.astype(np.float64)
            if material == MaterialType.MKZ:
                warnings.append(
                    "Reference-curve refit is currently implemented for GQ/H only."
                )
            else:
                tau_target = calibration.target_strength_kpa
                if tau_target is None:
                    tau_target = raw_params.get("tau_max")
                if tau_target is None:
                    warnings.append(
                        "Reference-curve refit requires target_strength_kpa or material_params.tau_max."
                    )
                else:
                    calibrated = calibrate_gqh_strength_control_from_reference(
                        gmax=gmax_seed,
                        tau_target_kpa=float(tau_target),
                        strain=strain,
                        target_modulus_reduction=target_modulus,
                        target_damping_ratio=target_damping,
                        fit_strain_min=calibration.fit_strain_min,
                        fit_strain_max=calibration.fit_strain_max,
                        target_strength_ratio=calibration.target_strength_ratio,
                        target_strength_strain=calibration.target_strength_strain,
                        reload_factor=calibration.reload_factor or 1.6,
                        fit_procedure=calibration.fit_procedure,
                        fit_limits=(
                            calibration.fit_limits.model_dump(exclude_none=True)
                            if calibration.fit_limits is not None
                            else None
                        ),
                    )
                    gqh_mode = calibrated.gqh_mode
                    calibrated_params = dict(calibrated.material_params)
                    modulus_rmse = calibrated.modulus_rmse
                    damping_rmse = calibrated.damping_rmse
                    strength_ratio_achieved = calibrated.strength_ratio_achieved
                    fit_procedure = calibrated.fit_procedure
                    fit_limits_applied = calibrated.fit_limits_applied
        effective_params = {**raw_params, **calibrated_params}
    else:
        effective_params = dict(raw_params)

    try:
        fitted_modulus, fitted_damping = _material_preview_curves(
            material,
            effective_params,
            strain,
        )
    except ValueError as exc:
        warnings.append(str(exc))
        return LayerCalibrationPreviewResponse(
            available=False,
            material=material.value,
            source=source,
            target_available=target_available,
            warnings=warnings,
        )
    if gqh_mode is None and material == MaterialType.GQH:
        gqh_mode = gqh_mode_from_params(effective_params)

    fit_rmse: float | None = None
    if target_modulus.size:
        pred = np.clip(fitted_modulus, 1.0e-6, 1.0)
        obs = np.clip(target_modulus, 1.0e-6, 1.0)
        fit_rmse = float(np.sqrt(np.mean(np.square(np.log(pred) - np.log(obs)))))

    loop_strain: list[float] = []
    loop_stress: list[float] = []
    loop_strain_amplitude: float | None = None
    loop_energy: float | None = None
    try:
        gamma_ref = float(effective_params.get("gamma_ref", 0.0))
        loop_amp = float(
            np.clip(
                max(gamma_ref * 2.0, strain.min() * 5.0),
                strain.min(),
                min(strain.max(), 0.01),
            )
        )
        loop = generate_masing_loop(
            material,
            effective_params,
            strain_amplitude=loop_amp,
            n_points_per_branch=80,
        )
        loop_strain = loop.strain.astype(float).tolist()
        loop_stress = loop.stress.astype(float).tolist()
        loop_strain_amplitude = loop.strain_amplitude
        loop_energy = loop.energy_dissipation
    except ValueError as exc:
        warnings.append(f"Single-element preview unavailable: {exc}")

    implied_strength = None
    normalized_strength = None
    implied_phi = None
    if sigma_mid_eff is not None and sigma_mid_eff > 0.0:
        preview_layer = {
            "name": layer.name,
            "material": material.value,
            "thickness_m": layer.thickness_m,
            "unit_weight_kN_m3": layer.unit_weight_kn_m3,
            "vs_m_s": layer.vs_m_s,
            "material_params": effective_params,
        }
        diags = compute_profile_diagnostics(
            [preview_layer],
            water_table_depth_m=None,
            strain=strain,
        )
        if diags:
            implied_strength = diags[0].implied_strength_kpa
            normalized_strength = diags[0].normalized_implied_strength
            implied_phi = diags[0].implied_friction_angle_deg
    if implied_strength is not None and sigma_mid_eff is not None and sigma_mid_eff > 0.0:
        normalized_strength = float(implied_strength / sigma_mid_eff)
        implied_phi = float(np.degrees(np.arctan(normalized_strength)))

    return LayerCalibrationPreviewResponse(
        available=True,
        material=material.value,
        source=source,
        target_available=target_available,
        strain=strain.astype(float).tolist(),
        target_modulus_reduction=target_modulus.astype(float).tolist(),
        fitted_modulus_reduction=fitted_modulus.astype(float).tolist(),
        target_damping_ratio=target_damping.astype(float).tolist(),
        fitted_damping_ratio=fitted_damping.astype(float).tolist(),
        material_params={k: float(v) for k, v in effective_params.items()},
        calibrated_material_params={k: float(v) for k, v in calibrated_params.items()},
        fit_rmse=fit_rmse,
        modulus_rmse=modulus_rmse,
        damping_rmse=damping_rmse,
        strength_ratio_achieved=strength_ratio_achieved,
        fit_procedure=fit_procedure,
        fit_limits_applied=fit_limits_applied,
        fit_stale=fit_stale,
        gqh_mode=gqh_mode,
        sigma_v_eff_mid_kpa=sigma_mid_eff,
        implied_strength_kpa=implied_strength,
        normalized_implied_strength=normalized_strength,
        implied_friction_angle_deg=implied_phi,
        loop_strain=loop_strain,
        loop_stress=loop_stress,
        loop_strain_amplitude=loop_strain_amplitude,
        loop_energy=loop_energy,
        warnings=warnings,
    )


def _wizard_defaults_from_project_payload(payload: dict[str, object]) -> dict[str, object]:
    valid_boundary = {e.value for e in BoundaryCondition}
    valid_material = {e.value for e in MaterialType}
    valid_baseline = {e.value for e in BaselineMode}
    valid_scale_mode = {e.value for e in ScaleMode}

    analysis = payload.get("analysis")
    analysis_dict = analysis if isinstance(analysis, dict) else {}
    profile = payload.get("profile")
    profile_dict = profile if isinstance(profile, dict) else {}
    motion = payload.get("motion")
    motion_dict = motion if isinstance(motion, dict) else {}
    output = payload.get("output")
    output_dict = output if isinstance(output, dict) else {}
    water_table_depth_m = _as_non_negative_float_or_none(
        profile_dict.get("water_table_depth_m")
    )
    bedrock_in = profile_dict.get("bedrock")
    bedrock_payload: dict[str, object] | None = None
    if isinstance(bedrock_in, dict):
        bedrock_vs = _as_positive_float_or_none(bedrock_in.get("vs_m_s"))
        bedrock_uw = _as_positive_float_or_none(bedrock_in.get("unit_weight_kN_m3"))
        bedrock_damping = _as_non_negative_float_or_none(bedrock_in.get("damping_ratio"))
        if bedrock_vs is not None and bedrock_uw is not None:
            bedrock_payload = {
                "name": str(bedrock_in.get("name", "Bedrock")),
                "vs_m_s": bedrock_vs,
                "unit_weight_kN_m3": bedrock_uw,
                "damping_ratio": (
                    min(float(bedrock_damping), 0.5) if bedrock_damping is not None else 0.0
                ),
            }

    layers_raw = profile_dict.get("layers")
    layers_in = layers_raw if isinstance(layers_raw, list) else []
    layers_out: list[dict[str, object]] = []
    for idx, item in enumerate(layers_in):
        if not isinstance(item, dict):
            continue
        material_raw = str(item.get("material", "mkz")).strip().lower()
        material = material_raw if material_raw in valid_material else "mkz"
        calibration_payload = _darendeli_payload(item.get("calibration"))
        layers_out.append(
            {
                "name": str(item.get("name", f"Layer-{idx + 1}")),
                "thickness_m": _as_non_negative_float(item.get("thickness_m"), 1.0),
                "unit_weight_kN_m3": _as_non_negative_float(
                    item.get("unit_weight_kN_m3"), 18.0
                ),
                "vs_m_s": _as_non_negative_float(item.get("vs_m_s"), 150.0),
                "material": material,
                "reference_curve": (
                    str(item.get("reference_curve"))
                    if item.get("reference_curve") is not None
                    else ("darendeli" if calibration_payload is not None else None)
                ),
                "fit_stale": bool(item.get("fit_stale", False)),
                "material_params": _numeric_dict(item.get("material_params")),
                "material_optional_args": _numeric_list(
                    item.get("material_optional_args")
                ),
                "calibration": calibration_payload,
            }
        )
    if not layers_out:
        layers_out = [
            {
                "name": "Layer-1",
                "thickness_m": 5.0,
                "unit_weight_kN_m3": 18.0,
                "vs_m_s": 180.0,
                "material": "mkz",
                "fit_stale": False,
                "material_params": {"gmax": 60000.0, "gamma_ref": 0.001},
                "material_optional_args": [],
                "calibration": None,
            }
        ]

    boundary_raw = str(
        payload.get(
            "boundary_condition",
            BoundaryCondition.RIGID.value,
        )
    )
    boundary = (
        boundary_raw
        if boundary_raw in valid_boundary
        else BoundaryCondition.RIGID.value
    )

    baseline_raw = str(motion_dict.get("baseline", BaselineMode.REMOVE_MEAN.value))
    baseline = (
        baseline_raw if baseline_raw in valid_baseline else BaselineMode.REMOVE_MEAN.value
    )

    scale_mode_raw = str(motion_dict.get("scale_mode", ScaleMode.NONE.value))
    scale_mode = (
        scale_mode_raw if scale_mode_raw in valid_scale_mode else ScaleMode.NONE.value
    )

    backend_raw = str(analysis_dict.get("solver_backend", "nonlinear"))
    if backend_raw not in {"linear", "eql", "nonlinear"}:
        backend_raw = "nonlinear"

    damping_mode_raw = str(analysis_dict.get("damping_mode", "frequency_independent"))
    damping_mode = (
        damping_mode_raw
        if damping_mode_raw in {"frequency_independent", "rayleigh"}
        else "frequency_independent"
    )
    rayleigh_mode_1 = _as_positive_float_or_none(analysis_dict.get("rayleigh_mode_1_hz"))
    rayleigh_mode_2 = _as_positive_float_or_none(analysis_dict.get("rayleigh_mode_2_hz"))
    rayleigh_update = bool(analysis_dict.get("rayleigh_update_matrix", False))

    wizard_payload = {
        "analysis_step": {
            "project_name": str(payload.get("project_name", "wizard-project")),
            "boundary_condition": boundary,
            "solver_backend": backend_raw,
        },
        "profile_step": {
            "water_table_depth_m": water_table_depth_m,
            "bedrock": bedrock_payload,
            "layers": layers_out,
        },
        "motion_step": {
            "units": str(motion_dict.get("units", "m/s2")),
            "input_type": str(motion_dict.get("input_type", "outcrop")),
            "dt_override": _as_positive_float_or_none(motion_dict.get("dt_override")),
            "baseline": baseline,
            "scale_mode": scale_mode,
            "scale_factor": _as_positive_float_or_none(motion_dict.get("scale_factor")),
            "target_pga": _as_positive_float_or_none(motion_dict.get("target_pga")),
            "motion_path": "",
        },
        "damping_step": {
            "mode": damping_mode,
            "update_matrix": rayleigh_update,
            "mode_1": rayleigh_mode_1 if rayleigh_mode_1 is not None else 1.0,
            "mode_2": rayleigh_mode_2 if rayleigh_mode_2 is not None else 5.0,
        },
        "control_step": {
            "dt": _as_positive_float_or_none(analysis_dict.get("dt")),
            "f_max": _as_non_negative_float(analysis_dict.get("f_max"), 25.0),
            "timeout_s": _as_int(analysis_dict.get("timeout_s"), 180, minimum=1),
            "retries": _as_int(analysis_dict.get("retries"), 1, minimum=0),
            "write_hdf5": bool(output_dict.get("write_hdf5", True)),
            "write_sqlite": bool(output_dict.get("write_sqlite", True)),
            "parquet_export": bool(output_dict.get("parquet_export", False)),
            "output_dir": "out/web",
            "config_output_dir": "",
            "config_file_name": "",
        },
    }
    model = WizardConfigRequest.model_validate(wizard_payload)
    return cast(dict[str, object], model.model_dump(mode="json", by_alias=True))


def _build_wizard_schema() -> dict[str, object]:
    template_names = list(available_config_templates())
    template_defaults: dict[str, dict[str, object]] = {}
    for name in template_names:
        payload = get_config_template_payload(name)
        template_defaults[name] = _wizard_defaults_from_project_payload(payload)
    default_template = (
        "mkz-gqh-nonlinear"
        if "mkz-gqh-nonlinear" in template_defaults
        else (template_names[0] if template_names else "")
    )
    default_wizard = template_defaults.get(default_template)
    if default_wizard is None:
        default_wizard = _wizard_defaults_from_project_payload(
            get_config_template_payload("mkz-gqh-nonlinear")
        )

    # Filter materials to native solvers only (mkz, gqh, elastic)
    native_materials = ["mkz", "gqh", "elastic"]

    return {
        "steps": [
            {"id": "analysis_step", "title": "Analysis Type"},
            {"id": "profile_step", "title": "Soil Profile"},
            {"id": "motion_step", "title": "Input Motion"},
            {"id": "damping_step", "title": "Damping"},
            {"id": "control_step", "title": "Analysis Control"},
        ],
        "fields": {
            "analysis_step": [
                "project_name",
                "boundary_condition",
                "solver_backend",
            ],
            "profile_step": ["water_table_depth_m", "bedrock", "layers[]", "layers[].calibration"],
            "motion_step": [
                "motion_path",
                "units",
                "input_type",
                "dt_override",
                "baseline",
                "scale_mode",
                "scale_factor",
                "target_pga",
            ],
            "damping_step": ["mode", "update_matrix", "mode_1", "mode_2"],
            "control_step": [
                "dt",
                "f_max",
                "timeout_s",
                "retries",
                "write_hdf5",
                "write_sqlite",
                "parquet_export",
                "output_dir",
                "config_output_dir",
                "config_file_name",
            ],
        },
        "defaults": default_wizard,
        "default_template": default_template,
        "config_templates": template_names,
        "template_defaults": template_defaults,
        "enum_options": {
            "boundary_condition": [e.value for e in BoundaryCondition],
            "solver_backend": ["linear", "eql", "nonlinear"],
            "baseline": [e.value for e in BaselineMode],
            "scale_mode": [e.value for e in ScaleMode],
            "material": native_materials,
        },
        "constraints": {
            "dt": {"gt": 0.0},
            "f_max": {"gt": 0.0},
            "thickness_m": {"gt": 0.0},
            "unit_weight_kN_m3": {"gt": 0.0},
            "vs_m_s": {"gt": 0.0},
        },
    }


def _wizard_to_config_payload(req: WizardConfigRequest) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    mode_1 = (
        float(req.damping_step.mode_1)
        if req.damping_step.mode_1 is not None
        else 1.0
    )
    mode_2 = (
        float(req.damping_step.mode_2)
        if req.damping_step.mode_2 is not None
        else 5.0
    )
    if mode_2 <= mode_1:
        mode_2 = mode_1 + 1.0e-6

    layers: list[dict[str, object]] = []
    for layer in req.profile_step.layers:
        layers.append(
            {
                "name": layer.name,
                "thickness_m": layer.thickness_m,
                "unit_weight_kN_m3": layer.unit_weight_kn_m3,
                "vs_m_s": layer.vs_m_s,
                "material": layer.material.value,
                "material_params": layer.material_params,
                "material_optional_args": layer.material_optional_args,
                "calibration": (
                    layer.calibration.model_dump(mode="json")
                    if layer.calibration is not None
                    else None
                ),
            }
        )

    payload: dict[str, object] = {
        "project_name": req.analysis_step.project_name,
        "profile": {
            "water_table_depth_m": req.profile_step.water_table_depth_m,
            "bedrock": (
                req.profile_step.bedrock.model_dump(mode="json", by_alias=True)
                if req.profile_step.bedrock is not None
                else None
            ),
            "layers": layers,
        },
        "boundary_condition": req.analysis_step.boundary_condition.value,
        "analysis": {
            "dt": req.control_step.dt,
            "f_max": req.control_step.f_max,
            "solver_backend": req.analysis_step.solver_backend,
            "damping_mode": req.damping_step.mode,
            "rayleigh_mode_1_hz": mode_1,
            "rayleigh_mode_2_hz": mode_2,
            "rayleigh_update_matrix": req.damping_step.update_matrix,
            "timeout_s": req.control_step.timeout_s,
            "retries": req.control_step.retries,
        },
        "motion": {
            "units": req.motion_step.units,
            "input_type": req.motion_step.input_type,
            "baseline": req.motion_step.baseline.value,
            "scale_mode": req.motion_step.scale_mode.value,
            "scale_factor": req.motion_step.scale_factor,
            "target_pga": req.motion_step.target_pga,
            "processing": (
                req.motion_step.processing.model_dump(mode="json", exclude_none=True)
                if req.motion_step.processing is not None
                else None
            ),
        },
        "output": {
            "write_hdf5": req.control_step.write_hdf5,
            "write_sqlite": req.control_step.write_sqlite,
            "parquet_export": req.control_step.parquet_export,
        },
    }
    return payload, warnings


def _safe_duration_5_95(arias: np.ndarray, dt: float) -> float:
    if arias.size < 2 or dt <= 0.0:
        return 0.0
    total = float(arias[-1])
    if total <= 0.0:
        return 0.0
    t = np.arange(arias.size, dtype=np.float64) * dt
    i5 = int(np.searchsorted(arias, 0.05 * total, side="left"))
    i95 = int(np.searchsorted(arias, 0.95 * total, side="left"))
    i5 = min(max(i5, 0), t.size - 1)
    i95 = min(max(i95, 0), t.size - 1)
    return float(max(0.0, t[i95] - t[i5]))


def _interp_period_value(
    periods: np.ndarray,
    values: np.ndarray,
    period_s: float,
) -> float | None:
    if periods.size < 2 or values.size < 2:
        return None
    x = np.asarray(periods, dtype=np.float64)
    y = np.asarray(values, dtype=np.float64)
    mask = np.isfinite(x) & np.isfinite(y)
    if int(np.count_nonzero(mask)) < 2:
        return None
    x = x[mask]
    y = y[mask]
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    return float(np.interp(float(period_s), x, y))


def _surface_displacement_series_cm(
    *,
    time: np.ndarray,
    acc_surface_m_s2: np.ndarray,
) -> np.ndarray:
    t = np.asarray(time, dtype=np.float64)
    acc = np.asarray(acc_surface_m_s2, dtype=np.float64)
    n = int(min(t.size, acc.size))
    if n <= 1:
        return np.array([], dtype=np.float64)
    t = t[:n]
    acc = acc[:n]
    dt = float(np.median(np.diff(t)))
    if not np.isfinite(dt) or dt <= 0.0:
        return np.array([], dtype=np.float64)
    vel = np.cumsum(acc, dtype=np.float64) * dt
    disp = np.cumsum(vel, dtype=np.float64) * dt
    # Remove long-period drift so animation remains interpretable in the UI.
    trend = np.linspace(disp[0], disp[-1], disp.size, dtype=np.float64)
    disp = disp - trend
    return np.asarray(disp * 100.0, dtype=np.float64)


def _approximate_profile_displacement_shape(
    *,
    depth: np.ndarray,
    layers: list[ResultProfileLayerRow],
    total_depth: float,
) -> np.ndarray:
    if depth.size == 0 or total_depth <= 0.0 or not layers:
        return np.array([], dtype=np.float64)

    boundary_depths = [0.0]
    boundary_shape = [1.0]
    layer_compliance: list[float] = []
    for row in layers:
        thickness = max(float(row.z_bottom_m) - float(row.z_top_m), 1.0e-9)
        vs = max(float(row.vs_m_s), 1.0)
        unit_weight = max(float(row.unit_weight_kn_m3), 1.0e-6)
        rho = unit_weight / 9.81
        gmax = max(rho * vs * vs, 1.0e-9)
        layer_compliance.append(thickness / gmax)

    total_compliance = float(np.sum(layer_compliance))
    if not np.isfinite(total_compliance) or total_compliance <= 0.0:
        return np.clip(1.0 - (depth / total_depth), 0.0, 1.0)

    cumulative = 0.0
    for row, compliance in zip(layers, layer_compliance, strict=True):
        cumulative += compliance
        boundary_depths.append(float(row.z_bottom_m))
        boundary_shape.append(float(max(0.0, 1.0 - (cumulative / total_compliance))))

    return np.asarray(
        np.interp(
            np.asarray(depth, dtype=np.float64),
            np.asarray(boundary_depths, dtype=np.float64),
            np.asarray(boundary_shape, dtype=np.float64),
        ),
        dtype=np.float64,
    )


def _build_displacement_animation_response(
    *,
    run_id: str,
    run_dir: Path,
    result_store: ResultStore,
    sqlite_path: Path,
    frame_count: int,
    max_depth_points: int,
) -> DisplacementAnimationResponse:
    if (
        result_store.node_depth_m.size >= 2
        and result_store.nodal_displacement_m.ndim == 2
        and result_store.nodal_displacement_m.shape[0] == result_store.node_depth_m.size
        and result_store.nodal_displacement_m.shape[1] >= 2
    ):
        node_depth = np.asarray(result_store.node_depth_m, dtype=np.float64)
        nodal_disp_cm = np.asarray(result_store.nodal_displacement_m, dtype=np.float64) * 100.0
        n = int(min(nodal_disp_cm.shape[1], result_store.time.size))
        if n >= 2:
            time = np.asarray(result_store.time[:n], dtype=np.float64)
            nodal_disp_cm = nodal_disp_cm[:, :n]
            relative_nodal_disp_cm = nodal_disp_cm - nodal_disp_cm[-1:, :]
            target_frames = int(max(20, min(frame_count, n)))
            frame_idx = np.linspace(0, n - 1, target_frames, dtype=np.int64)
            frame_time = time[frame_idx]
            if node_depth.size > max_depth_points:
                depth = np.linspace(
                    float(node_depth[0]),
                    float(node_depth[-1]),
                    max_depth_points,
                    dtype=np.float64,
                )
                displacement_frames = [
                    np.interp(depth, node_depth, nodal_disp_cm[:, idx]).astype(float).tolist()
                    for idx in frame_idx
                ]
                relative_displacement_frames = [
                    np.interp(depth, node_depth, relative_nodal_disp_cm[:, idx]).astype(float).tolist()
                    for idx in frame_idx
                ]
            else:
                depth = node_depth
                displacement_frames = [
                    nodal_disp_cm[:, idx].astype(float).tolist()
                    for idx in frame_idx
                ]
                relative_displacement_frames = [
                    relative_nodal_disp_cm[:, idx].astype(float).tolist()
                    for idx in frame_idx
                ]
            return DisplacementAnimationResponse(
                run_id=run_id,
                approximate=False,
                depth_m=depth.astype(float).tolist(),
                frame_time_s=frame_time.astype(float).tolist(),
                displacement_cm=displacement_frames,
                relative_displacement_cm=relative_displacement_frames,
                peak_surface_displacement_cm=float(np.max(np.abs(nodal_disp_cm[0, :]))),
                peak_profile_displacement_cm=float(np.max(np.abs(nodal_disp_cm))),
                peak_surface_relative_displacement_cm=float(
                    np.max(np.abs(relative_nodal_disp_cm[0, :]))
                ),
                peak_profile_relative_displacement_cm=float(
                    np.max(np.abs(relative_nodal_disp_cm))
                ),
                note="Recorded nodal displacement history from the solver response.",
            )

    layers = _read_profile_layer_summary(sqlite_path, run_dir=run_dir)
    if not layers:
        return DisplacementAnimationResponse(
            run_id=run_id,
            approximate=True,
            note="No layer mesh/profile information is available for displacement animation.",
        )
    depth_boundaries = [0.0]
    for row in layers:
        depth_boundaries.append(float(row.z_bottom_m))
    total_depth = float(max(depth_boundaries))
    if total_depth <= 0.0:
        return DisplacementAnimationResponse(
            run_id=run_id,
            approximate=True,
            note="Profile depth is zero. Displacement animation is unavailable.",
        )

    if len(depth_boundaries) > max_depth_points:
        depth = np.linspace(0.0, total_depth, max_depth_points, dtype=np.float64)
    else:
        depth = np.asarray(depth_boundaries, dtype=np.float64)

    disp_surface_cm = _surface_displacement_series_cm(
        time=result_store.time,
        acc_surface_m_s2=result_store.acc_surface,
    )
    n = int(min(disp_surface_cm.size, result_store.time.size))
    if n <= 1:
        return DisplacementAnimationResponse(
            run_id=run_id,
            approximate=True,
            depth_m=depth.astype(float).tolist(),
            note="Surface acceleration series is unavailable for displacement animation.",
        )
    time = np.asarray(result_store.time[:n], dtype=np.float64)
    disp_surface_cm = np.asarray(disp_surface_cm[:n], dtype=np.float64)

    target_frames = int(max(20, min(frame_count, n)))
    frame_idx = np.linspace(0, n - 1, target_frames, dtype=np.int64)
    frame_time = time[frame_idx]
    frame_surface_disp = disp_surface_cm[frame_idx]

    shape = _approximate_profile_displacement_shape(
        depth=depth,
        layers=layers,
        total_depth=total_depth,
    )
    displacement_frames = [
        (float(u) * shape).astype(float).tolist() for u in frame_surface_disp
    ]
    relative_displacement_frames = [
        (np.asarray(frame, dtype=np.float64) - float(frame[-1])).astype(float).tolist()
        if frame
        else []
        for frame in displacement_frames
    ]
    relative_peak_profile_cm = float(
        np.max(np.abs(np.asarray(relative_displacement_frames, dtype=np.float64)))
    ) if relative_displacement_frames else 0.0
    relative_peak_surface_cm = float(
        np.max(np.abs(np.asarray([frame[0] for frame in relative_displacement_frames if frame], dtype=np.float64)))
    ) if relative_displacement_frames else 0.0

    return DisplacementAnimationResponse(
        run_id=run_id,
        approximate=True,
        depth_m=depth.astype(float).tolist(),
        frame_time_s=frame_time.astype(float).tolist(),
        displacement_cm=displacement_frames,
        relative_displacement_cm=relative_displacement_frames,
        peak_surface_displacement_cm=float(np.max(np.abs(disp_surface_cm))),
        peak_profile_displacement_cm=float(np.max(np.abs(np.asarray(displacement_frames, dtype=np.float64)))),
        peak_surface_relative_displacement_cm=relative_peak_surface_cm,
        peak_profile_relative_displacement_cm=relative_peak_profile_cm,
        note=(
            "Approximate depth animation uses integrated surface displacement with a "
            "bedrock-anchored stiffness-weighted shape function. It is not nodal solver "
            "displacement output."
        ),
    )


def _build_response_spectra_summary_response(
    *,
    run_id: str,
    result_store: ResultStore,
) -> ResponseSpectraSummaryResponse:
    summary_periods = _web_spectra_periods()
    surface_dt_s = float(result_store.dt_s)
    input_dt_s = (
        float(result_store.input_dt_s)
        if np.isfinite(result_store.input_dt_s) and result_store.input_dt_s > 0.0
        else surface_dt_s
    )
    surface_spectra = compute_spectra(
        np.asarray(result_store.acc_surface, dtype=np.float64),
        dt=surface_dt_s,
        damping=0.05,
        periods=summary_periods,
    )
    surface_periods = np.asarray(surface_spectra.periods, dtype=np.float64)
    surface_psa = np.asarray(surface_spectra.psa, dtype=np.float64)
    input_psa: np.ndarray | None = None
    if result_store.acc_input.size > 1:
        try:
            spectra_input = compute_spectra(
                np.asarray(result_store.acc_input, dtype=np.float64),
                dt=input_dt_s,
                damping=0.05,
                periods=summary_periods,
            )
            input_psa = np.asarray(spectra_input.psa, dtype=np.float64)
        except Exception:
            input_psa = None

    rows: list[SpectraSummaryRow] = []
    max_surface: float | None = None
    max_ratio: float | None = None
    for period_s in SPECTRA_STANDARD_PERIODS:
        surf = _interp_period_value(surface_periods, surface_psa, period_s)
        inp = (
            _interp_period_value(surface_periods, input_psa, period_s)
            if input_psa is not None
            else None
        )
        ratio = None
        if inp is not None and inp > 1.0e-9 and surf is not None:
            ratio = float(surf / inp)
        if surf is not None:
            max_surface = float(max(max_surface or surf, surf))
        if ratio is not None:
            max_ratio = float(max(max_ratio or ratio, ratio))
        rows.append(
            SpectraSummaryRow(
                period_s=float(period_s),
                frequency_hz=float(1.0 / period_s),
                surface_psa_m_s2=surf,
                surface_psa_g=(float(surf / 9.81) if surf is not None else None),
                input_psa_m_s2=inp,
                amplification_ratio=ratio,
            )
        )

    return ResponseSpectraSummaryResponse(
        run_id=run_id,
        damping_ratio=0.05,
        row_count=len(rows),
        rows=rows,
        max_surface_psa_m_s2=max_surface,
        max_amplification_ratio=max_ratio,
    )


def _downsample_np(
    x: np.ndarray,
    y: np.ndarray,
    max_points: int = 2000,
) -> tuple[np.ndarray, np.ndarray]:
    n = int(min(x.size, y.size))
    if n <= max_points:
        return x[:n], y[:n]
    step = max(1, n // max_points)
    return x[:n:step], y[:n:step]


def _downsample_pair(
    x: list[float],
    y: list[float],
    *,
    max_points: int,
) -> tuple[list[float], list[float]]:
    n = min(len(x), len(y))
    if n <= max_points:
        return x[:n], y[:n]
    step = max(1, n // max_points)
    return x[:n:step], y[:n:step]


def _cumtrapz_np(values: np.ndarray, dt: float) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return np.asarray([], dtype=np.float64)
    out = np.zeros(arr.size, dtype=np.float64)
    if arr.size > 1:
        increments = 0.5 * (arr[1:] + arr[:-1]) * float(dt)
        out[1:] = np.cumsum(increments, dtype=np.float64)
    return out


def _spectral_triplet(psa_m_s2: np.ndarray, periods_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    psa = np.asarray(psa_m_s2, dtype=np.float64)
    periods = np.asarray(periods_s, dtype=np.float64)
    psv = np.zeros_like(psa, dtype=np.float64)
    psd = np.zeros_like(psa, dtype=np.float64)
    valid = periods > 0.0
    psv[valid] = psa[valid] * periods[valid] / (2.0 * np.pi)
    psd[valid] = psa[valid] * periods[valid] ** 2 / (4.0 * np.pi**2)
    return psv, psd


def _estimate_dt(time_axis: np.ndarray) -> float:
    if time_axis.size > 1:
        dt = float(np.median(np.diff(time_axis)))
        if np.isfinite(dt) and dt > 0.0:
            return dt
    return 1.0


def _wizard_sanity_report(payload: WizardConfigRequest) -> WizardSanityResponse:
    checks: list[WizardSanityCheckItem] = []
    blockers: list[str] = []
    warnings: list[str] = []
    derived: dict[str, object] = {
        "requested_backend": payload.analysis_step.solver_backend,
        "f_max_hz": float(payload.control_step.f_max),
    }
    motion_path_resolved: Path | None = None

    cfg: ProjectConfig | None = None
    try:
        cfg_payload, cfg_warnings = _wizard_to_config_payload(payload)
        cfg = ProjectConfig.model_validate(cfg_payload)
        checks.append(
            WizardSanityCheckItem(
                name="config_validation",
                status="ok",
                message="Wizard configuration is valid.",
            )
        )
        warnings.extend(cfg_warnings)
    except (ValidationError, ValueError) as exc:
        msg = f"Wizard config validation failed: {exc}"
        checks.append(
            WizardSanityCheckItem(name="config_validation", status="blocker", message=msg)
        )
        blockers.append(msg)

    motion_path_text = payload.motion_step.motion_path.strip()
    if not motion_path_text:
        msg = "Motion path is empty."
        checks.append(WizardSanityCheckItem(name="motion_path", status="blocker", message=msg))
        blockers.append(msg)
    else:
        try:
            motion_path = _resolve_input_path(motion_path_text, label="Motion file")
            checks.append(
                WizardSanityCheckItem(
                    name="motion_path",
                    status="ok",
                    message=f"Motion file resolved: {motion_path}",
                )
            )
            motion_path_resolved = motion_path
            derived["motion_path"] = str(motion_path)
        except (FileNotFoundError, ValueError) as exc:
            msg = str(exc)
            checks.append(
                WizardSanityCheckItem(name="motion_path", status="blocker", message=msg)
            )
            blockers.append(msg)

    output_root = _resolve_output_root(payload.control_step.output_dir)
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        checks.append(
            WizardSanityCheckItem(
                name="output_dir",
                status="ok",
                message=f"Output directory ready: {output_root}",
            )
        )
        derived["output_root"] = str(output_root)
    except OSError as exc:
        msg = f"Output directory not writable: {output_root} ({exc})"
        checks.append(WizardSanityCheckItem(name="output_dir", status="blocker", message=msg))
        blockers.append(msg)

    f_max = float(payload.control_step.f_max)
    dt_recommended = (1.0 / (20.0 * f_max)) if f_max > 0.0 else None
    dt_used = (
        float(payload.control_step.dt)
        if payload.control_step.dt is not None
        else (float(dt_recommended) if dt_recommended is not None else None)
    )
    derived["dt_recommended_s"] = dt_recommended
    derived["dt_used_s"] = dt_used
    if dt_used is None:
        msg = "Unable to derive time step from dt/f_max."
        checks.append(WizardSanityCheckItem(name="time_step", status="blocker", message=msg))
        blockers.append(msg)
    elif dt_recommended is not None and dt_used > (1.25 * dt_recommended):
        msg = (
            f"dt={dt_used:.6g}s is coarse relative to recommended "
            f"{dt_recommended:.6g}s (1/(20*f_max))."
        )
        checks.append(WizardSanityCheckItem(name="time_step", status="warning", message=msg))
        warnings.append(msg)
    else:
        checks.append(
            WizardSanityCheckItem(
                name="time_step",
                status="ok",
                message=f"dt={dt_used:.6g}s (recommended~{(dt_recommended or dt_used):.6g}s).",
            )
        )

    requested_backend = payload.analysis_step.solver_backend
    checks.append(
        WizardSanityCheckItem(
            name="backend_material_compatibility",
            status="ok",
            message=f"Backend '{requested_backend}' accepts MKZ/GQH/elastic materials.",
        )
    )

    if cfg is not None:
        derived["config_backend"] = cfg.analysis.solver_backend
    return WizardSanityResponse(
        ok=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        checks=checks,
        derived=derived,
    )


def _apply_runtime_backend(
    requested: RunBackendMode,
) -> tuple[ResolvedBackend, str]:
    if requested in {"linear", "eql", "nonlinear"}:
        return requested, f"{requested} (forced)"

    raise HTTPException(status_code=400, detail=f"Unsupported backend mode: {requested}")


def create_app() -> FastAPI:
    import mimetypes
    mimetypes.add_type("application/javascript", ".mjs")

    app = FastAPI(title="GeoWave Web API", version="0.1.0")
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    PLAN_LIMITS = {"free": 3, "starter": 10, "pro": 999999}

    def _count_today_runs(output_root: Path) -> int:
        """Count runs created today."""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        count = 0
        if not output_root.is_dir():
            return 0
        for d in output_root.iterdir():
            if not d.is_dir() or not d.name.startswith("run-"):
                continue
            meta_path = d / "run_meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    ts = meta.get("timestamp_utc", "")
                    if ts.startswith(today_str):
                        count += 1
                except Exception:
                    pass
        return count

    @app.get("/api/plan")
    def get_plan(
        plan: str = Query(default="free"),
        output_root: str = Query(default=""),
    ) -> dict[str, object]:
        """Return plan info with today's run count."""
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        today_runs = _count_today_runs(root)
        limit = PLAN_LIMITS.get(plan, 3)
        return {
            "plan": plan,
            "runs_today": today_runs,
            "runs_per_day": limit,
            "can_run": today_runs < limit,
            "demo_mode": True,
        }

    @app.get("/api/config/templates")
    def list_config_templates() -> dict[str, list[str]]:
        return {"templates": list(available_config_templates())}

    @app.post("/api/config/template", response_model=ConfigTemplateResponse)
    def create_config_template(payload: ConfigTemplateRequest) -> ConfigTemplateResponse:
        out_root = (
            _safe_real_path(payload.output_dir)
            if payload.output_dir.strip()
            else _default_config_root()
        )
        out_root.mkdir(parents=True, exist_ok=True)
        file_name = payload.file_name.strip() or f"{payload.template}.yml"
        if not file_name.lower().endswith((".yml", ".yaml")):
            file_name = f"{file_name}.yml"
        out_path = out_root / file_name
        written = write_config_template(out_path, template=payload.template)
        return ConfigTemplateResponse(
            template=payload.template,
            config_path=str(written),
            status="ok",
            message="Config template created.",
        )

    @app.get("/api/wizard/schema")
    def get_wizard_schema() -> dict[str, object]:
        return _build_wizard_schema()

    @app.post("/api/config/from-wizard", response_model=WizardConfigResponse)
    def create_config_from_wizard(payload: WizardConfigRequest) -> WizardConfigResponse:
        try:
            cfg_payload, warnings = _wizard_to_config_payload(payload)
            validated = ProjectConfig.model_validate(cfg_payload)
            rendered = yaml.safe_dump(
                validated.model_dump(mode="json", by_alias=True),
                sort_keys=False,
                allow_unicode=True,
            )
            out_root = (
                _safe_real_path(payload.control_step.config_output_dir)
                if payload.control_step.config_output_dir.strip()
                else _default_config_root()
            )
            out_root.mkdir(parents=True, exist_ok=True)
            file_name = payload.control_step.config_file_name.strip() or "wizard_generated.yml"
            if not file_name.lower().endswith((".yml", ".yaml")):
                file_name = f"{file_name}.yml"
            out_path = out_root / file_name
            out_path.write_text(rendered, encoding="utf-8")
            return WizardConfigResponse(
                config_path=str(out_path),
                config_yaml=rendered,
                warnings=warnings,
                status="ok",
            )
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/api/wizard/layer-calibration-preview",
        response_model=LayerCalibrationPreviewResponse,
    )
    def wizard_layer_calibration_preview(
        payload: LayerCalibrationPreviewRequest,
    ) -> LayerCalibrationPreviewResponse:
        try:
            sigma_v_eff_mid_kpa: float | None = None
            if payload.layers and payload.layer_index is not None:
                states = compute_layer_stress_states(
                    payload.layers,
                    water_table_depth_m=payload.water_table_depth_m,
                )
                if 0 <= payload.layer_index < len(states):
                    sigma_v_eff_mid_kpa = states[payload.layer_index].sigma_v_eff_mid_kpa
            return _build_layer_calibration_preview(
                payload.layer,
                sigma_v_eff_mid_kpa=sigma_v_eff_mid_kpa,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/profile-diagnostics", response_model=ProfileDiagnosticsResponse)
    def wizard_profile_diagnostics(
        payload: ProfileDiagnosticsRequest,
    ) -> ProfileDiagnosticsResponse:
        try:
            diagnostics = compute_profile_diagnostics(
                payload.profile_step.layers,
                water_table_depth_m=payload.profile_step.water_table_depth_m,
            )
            rows = [
                ProfileDiagnosticsLayerRow(
                    idx=int(row.index),
                    name=row.name,
                    material=row.material,
                    thickness_m=row.thickness_m,
                    unit_weight_kn_m3=row.unit_weight_kn_m3,
                    vs_m_s=row.vs_m_s,
                    z_top_m=row.z_top_m,
                    z_bottom_m=row.z_bottom_m,
                    sigma_v0_mid_kpa=row.sigma_v0_mid_kpa,
                    sigma_v_eff_mid_kpa=row.sigma_v_eff_mid_kpa,
                    pore_water_pressure_kpa=row.pore_water_pressure_kpa,
                    small_strain_damping_ratio=row.small_strain_damping_ratio,
                    max_frequency_hz=row.max_frequency_hz,
                    implied_strength_kpa=row.implied_strength_kpa,
                    normalized_implied_strength=row.normalized_implied_strength,
                    implied_friction_angle_deg=row.implied_friction_angle_deg,
                    gqh_mode=row.gqh_mode,
                )
                for row in diagnostics
            ]
            total_thickness = float(
                sum(max(0.0, float(layer.thickness_m)) for layer in payload.profile_step.layers)
            )
            return ProfileDiagnosticsResponse(
                layer_count=len(rows),
                total_thickness_m=total_thickness,
                water_table_depth_m=payload.profile_step.water_table_depth_m,
                layers=rows,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/wizard/sanity-check", response_model=WizardSanityResponse)
    def wizard_sanity_check(payload: WizardConfigRequest) -> WizardSanityResponse:
        return _wizard_sanity_report(payload)

    @app.post("/api/motion/import/peer-at2", response_model=MotionImportResponse)
    def motion_import_peer_at2(payload: MotionImportRequest) -> MotionImportResponse:
        try:
            source_path = _resolve_input_path(payload.path, label="AT2 motion file")
            output_dir = _safe_motion_output_dir(payload.output_dir)
            output_name = payload.output_name.strip() or None
            result = import_peer_at2_to_csv(
                source_path,
                output_dir=output_dir,
                units_hint=payload.units_hint,
                dt_override=payload.dt_override,
                output_name=output_name,
            )
            return MotionImportResponse(
                converted_csv_path=str(result.csv_path),
                npts=result.npts,
                dt_s=result.dt_s,
                pga_si=result.pga_si,
                status="ok",
            )
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/motion/upload/csv", response_model=MotionUploadResponse)
    def motion_upload_csv(payload: MotionUploadCsvRequest) -> MotionUploadResponse:
        source_name = payload.file_name or "uploaded_motion.csv"
        stem = _safe_upload_stem(payload.output_name, source_name)
        out_dir = _safe_motion_output_dir(payload.output_dir)
        out_path = out_dir / f"{stem}.csv"
        try:
            data = base64.b64decode(payload.content_base64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 payload.") from exc
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")
        out_path.write_bytes(data)
        return MotionUploadResponse(
            uploaded_path=str(out_path),
            file_name=Path(source_name).name,
            nbytes=len(data),
            status="ok",
        )

    @app.post("/api/motion/upload/peer-at2", response_model=MotionImportResponse)
    def motion_upload_peer_at2(payload: MotionUploadPeerAT2Request) -> MotionImportResponse:
        source_name = payload.file_name or "uploaded_motion.at2"
        stem = _safe_upload_stem(payload.output_name, source_name)
        out_dir = _safe_motion_output_dir(payload.output_dir)
        at2_path = out_dir / f"{stem}.at2"
        try:
            data = base64.b64decode(payload.content_base64, validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 payload.") from exc
        if not data:
            raise HTTPException(status_code=400, detail="Uploaded AT2 file is empty.")
        at2_path.write_bytes(data)
        result = import_peer_at2_to_csv(
            at2_path,
            output_dir=out_dir,
            units_hint=payload.units_hint,
            dt_override=payload.dt_override,
            output_name=f"{stem}_from_upload",
        )
        return MotionImportResponse(
            converted_csv_path=str(result.csv_path),
            npts=result.npts,
            dt_s=result.dt_s,
            pga_si=result.pga_si,
            status="ok",
        )

    @app.post("/api/motion/process", response_model=MotionProcessResponse)
    def motion_process(payload: MotionProcessRequest) -> MotionProcessResponse:
        try:
            motion_path = _resolve_input_path(payload.motion_path, label="Motion file")
            fallback_dt = (
                float(payload.fallback_dt)
                if payload.fallback_dt is not None
                else 1.0 / (20.0 * 25.0)
            )
            t_raw, acc_raw = load_motion_series(
                motion_path,
                dt_override=payload.dt_override,
                fallback_dt=fallback_dt,
                **_motion_parse_kwargs_from_model(payload),
            )
            dt_s = _estimate_dt(np.asarray(t_raw, dtype=np.float64))
            factor = accel_factor_to_si(payload.units_hint)
            acc_si = np.asarray(acc_raw, dtype=np.float64) * factor

            cfg = _motion_config_from_model(
                payload,
                baseline_mode=payload.baseline_mode,
                scale_mode=payload.scale_mode,
                scale_factor=payload.scale_factor,
                target_pga=payload.target_pga,
            )
            mot = Motion(
                dt=float(dt_s),
                acc=acc_si,
                unit="m/s2",
                source=motion_path,
            )
            processed = preprocess_motion(mot, cfg)
            processed_components = process_motion_components(mot, cfg)
            acc_proc = np.asarray(processed_components["acc_processed"], dtype=np.float64)
            vel = np.asarray(processed_components["vel_processed"], dtype=np.float64)
            disp = np.asarray(processed_components["disp_processed"], dtype=np.float64)
            t_proc = np.arange(acc_proc.size, dtype=np.float64) * float(processed.dt)

            out_root = _safe_motion_output_dir(payload.output_dir)
            stem = payload.output_name.strip() or f"{motion_path.stem}_processed"
            csv_path = out_root / f"{stem}.csv"
            np.savetxt(
                csv_path,
                np.column_stack([t_proc, acc_proc]),
                delimiter=",",
                header="time_s,acc_m_s2",
                comments="",
            )

            arias = (
                np.cumsum(acc_proc**2, dtype=np.float64)
                * float(processed.dt)
                * np.pi
                / (2.0 * 9.80665)
            )
            metrics = {
                "pga": float(np.max(np.abs(acc_proc))) if acc_proc.size > 0 else 0.0,
                "arias": float(arias[-1]) if arias.size > 0 else 0.0,
                "duration_5_95": _safe_duration_5_95(arias, float(processed.dt)),
                "dt_s": float(processed.dt),
                "npts": float(acc_proc.size),
                "pgv_m_s": float(np.max(np.abs(vel))) if vel.size > 0 else 0.0,
                "pgd_m": float(np.max(np.abs(disp))) if disp.size > 0 else 0.0,
            }
            metrics_path = out_root / f"{stem}_metrics.json"
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            preview = _motion_preview_payload(
                motion_path=motion_path,
                units_hint=payload.units_hint,
                format_hint=payload.format_hint,
                raw_time_s=np.asarray(t_raw, dtype=np.float64),
                raw_acc_si=acc_si,
                processed_dt_s=float(processed.dt),
                processed_components=processed_components,
                spectrum_damping_ratio=float(payload.spectrum_damping_ratio),
                show_uncorrected_preview=bool(payload.show_uncorrected_preview),
                max_points=2400,
            )

            return MotionProcessResponse(
                processed_motion_path=str(csv_path),
                metrics_path=str(metrics_path),
                metrics=metrics,
                spectra_preview=preview,
                status="ok",
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/api/motion/tools/timestep-reduction",
        response_model=MotionTimeStepReductionResponse,
    )
    def motion_tools_timestep_reduction(
        payload: MotionTimeStepReductionRequest,
    ) -> MotionTimeStepReductionResponse:
        try:
            motion_path = _resolve_input_path(payload.motion_path, label="Motion file")
            t_raw, acc_raw = load_motion_series(
                motion_path,
                dt_override=payload.dt_override,
                fallback_dt=0.01,
                **_motion_parse_kwargs_from_model(payload),
            )
            t_arr = np.asarray(t_raw, dtype=np.float64)
            dt_original = _estimate_dt(t_arr)
            if not np.isfinite(dt_original) or dt_original <= 0.0:
                raise ValueError("Unable to infer original time step from motion series.")

            if payload.target_dt is not None:
                reduction_factor = max(2, int(np.ceil(float(payload.target_dt) / dt_original)))
            else:
                reduction_factor = int(payload.reduction_factor)
            dt_reduced = float(dt_original * reduction_factor)

            acc_si = np.asarray(acc_raw, dtype=np.float64) * accel_factor_to_si(payload.units_hint)
            if acc_si.size < 8:
                raise ValueError("Motion requires at least 8 points for time-step reduction preview.")

            # Anti-aliasing via moving-average before decimation.
            kernel = np.ones(reduction_factor, dtype=np.float64) / float(reduction_factor)
            filtered = np.convolve(acc_si, kernel, mode="same")
            original_on_reduced = np.asarray(acc_si[::reduction_factor], dtype=np.float64)
            reduced = np.asarray(filtered[::reduction_factor], dtype=np.float64)
            time_reduced = np.asarray(t_arr[::reduction_factor], dtype=np.float64)

            time_reduced, original_on_reduced = _downsample_np(
                time_reduced,
                original_on_reduced,
                max_points=payload.max_points,
            )
            _, reduced = _downsample_np(
                time_reduced,
                reduced[: time_reduced.size],
                max_points=payload.max_points,
            )

            return MotionTimeStepReductionResponse(
                dt_original=float(dt_original),
                dt_reduced=float(dt_reduced),
                reduction_factor=int(reduction_factor),
                pga_original_m_s2=float(np.max(np.abs(acc_si))) if acc_si.size else 0.0,
                pga_reduced_m_s2=float(np.max(np.abs(reduced))) if reduced.size else 0.0,
                time_s=time_reduced.astype(float).tolist(),
                acc_original_m_s2=original_on_reduced.astype(float).tolist(),
                acc_reduced_m_s2=reduced.astype(float).tolist(),
                note=(
                    "Reduced series uses moving-average anti-aliasing plus decimation. "
                    "Use this preview to choose a stable analysis dt."
                ),
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/motion/tools/kappa", response_model=MotionKappaResponse)
    def motion_tools_kappa(payload: MotionKappaRequest) -> MotionKappaResponse:
        try:
            motion_path = _resolve_input_path(payload.motion_path, label="Motion file")
            t_raw, acc_raw = load_motion_series(
                motion_path,
                dt_override=payload.dt_override,
                fallback_dt=0.01,
                **_motion_parse_kwargs_from_model(payload),
            )
            t_arr = np.asarray(t_raw, dtype=np.float64)
            dt = _estimate_dt(t_arr)
            if not np.isfinite(dt) or dt <= 0.0:
                raise ValueError("Unable to infer dt for kappa estimation.")

            acc_si = np.asarray(acc_raw, dtype=np.float64) * accel_factor_to_si(payload.units_hint)
            if acc_si.size < 8:
                raise ValueError("At least 8 samples are required for kappa estimation.")

            n_fft = int(2 ** np.ceil(np.log2(acc_si.size)))
            fft_complex = np.fft.rfft(acc_si, n=n_fft)
            freq = np.fft.rfftfreq(n_fft, d=dt)
            fas = np.abs(fft_complex) * dt

            freq_nonzero = np.asarray(freq[1:], dtype=np.float64)
            fas_nonzero = np.asarray(fas[1:], dtype=np.float64)
            mask = (
                (freq_nonzero >= float(payload.freq_min_hz))
                & (freq_nonzero <= float(payload.freq_max_hz))
                & (fas_nonzero > 0.0)
            )
            if int(np.count_nonzero(mask)) < 5:
                return MotionKappaResponse(
                    freq_hz=[],
                    fas_amplitude=[],
                    note=(
                        "Insufficient high-frequency points in selected range for stable κ fit. "
                        "Try a wider frequency band."
                    ),
                )

            x = freq_nonzero[mask]
            y = np.log(fas_nonzero[mask])
            x_mean = float(np.mean(x))
            y_mean = float(np.mean(y))
            denom = float(np.sum((x - x_mean) ** 2))
            if denom <= 1.0e-18:
                return MotionKappaResponse(
                    note="Kappa estimator is ill-conditioned for the selected frequency range.",
                )

            slope = float(np.sum((x - x_mean) * (y - y_mean)) / denom)
            intercept = float(y_mean - (slope * x_mean))
            kappa = float(max(-slope / np.pi, 0.0))

            y_hat = slope * x + intercept
            ss_res = float(np.sum((y - y_hat) ** 2))
            ss_tot = float(np.sum((y - y_mean) ** 2))
            r2 = float(1.0 - (ss_res / max(ss_tot, 1.0e-30)))

            fit_freq = np.array(
                [float(payload.freq_min_hz), float(payload.freq_max_hz)],
                dtype=np.float64,
            )
            fit_amp = np.exp((slope * fit_freq) + intercept)

            freq_plot, fas_plot = _downsample_np(
                freq_nonzero,
                fas_nonzero,
                max_points=payload.max_points,
            )
            return MotionKappaResponse(
                kappa=kappa,
                kappa_r2=r2,
                freq_hz=freq_plot.astype(float).tolist(),
                fas_amplitude=fas_plot.astype(float).tolist(),
                fit_freq_hz=fit_freq.astype(float).tolist(),
                fit_amplitude=fit_amp.astype(float).tolist(),
                note="Estimated from ln(FAS) linear fit: ln(A)=c−πκf.",
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/runs", response_model=list[RunSummary])
    def list_runs(output_root: str = Query(default="")) -> list[RunSummary]:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        items: list[RunSummary] = []
        for run_dir in reversed(_collect_runs(root)):
            meta = _read_run_meta(run_dir)
            sqlite_path = run_dir / "results.sqlite"
            metrics = _read_metrics(sqlite_path)
            health = _run_health_summary(sqlite_path, run_dir=run_dir)
            input_motion = meta.get("input_motion", "")
            items.append(
                RunSummary(
                    run_id=run_dir.name,
                    output_dir=str(run_dir),
                    timestamp_utc=meta.get("timestamp_utc", ""),
                    solver_backend=meta.get("solver_backend", "unknown"),
                    status=meta.get("status", "unknown"),
                    message=meta.get("message", ""),
                    project_name=_read_project_name(sqlite_path),
                    input_motion=input_motion,
                    motion_name=Path(input_motion).name if input_motion else "",
                    pga=metrics.get("pga"),
                    ru_max=metrics.get("ru_max"),
                    delta_u_max=metrics.get("delta_u_max"),
                    sigma_v_eff_min=metrics.get("sigma_v_eff_min"),
                    convergence_mode=str(health["convergence_mode"]),
                    convergence_severity=str(health["convergence_severity"]),
                    converged=cast(bool | None, health["converged"]),
                    solver_warning_count=cast(int | None, health["solver_warning_count"]),
                    solver_failed_converge_count=cast(
                        int | None, health["solver_failed_converge_count"]
                    ),
                    solver_analyze_failed_count=cast(
                        int | None, health["solver_analyze_failed_count"]
                    ),
                    solver_divide_by_zero_count=cast(
                        int | None, health["solver_divide_by_zero_count"]
                    ),
                    solver_dynamic_fallback_failed_count=cast(
                        int | None, health["solver_dynamic_fallback_failed_count"]
                    ),
                )
            )
        return items

    @app.delete("/api/runs/{run_id}")
    def delete_run(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> dict[str, str]:
        """Delete a run directory permanently."""
        import re
        import shutil

        if not re.match(r"^run-[a-f0-9]{12}$", run_id):
            raise HTTPException(status_code=400, detail=f"Invalid run_id format: {run_id}")
        run_dir = _resolve_run_dir(run_id, output_root)
        if not run_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Run directory not found: {run_id}")
        shutil.rmtree(run_dir, ignore_errors=True)
        return {"status": "deleted", "run_id": run_id}

    @app.get("/api/runs/tree")
    def runs_tree(output_root: str = Query(default="")) -> dict[str, object]:
        root = _safe_real_path(output_root) if output_root else _default_output_root()
        grouped: dict[str, dict[str, list[dict[str, str]]]] = {}
        for run_dir in reversed(_collect_runs(root)):
            meta = _read_run_meta(run_dir)
            health = _run_health_summary(run_dir / "results.sqlite", run_dir=run_dir)
            project_name = _read_project_name(run_dir / "results.sqlite") or "unknown-project"
            input_motion = meta.get("input_motion", "")
            motion_name = Path(input_motion).name if input_motion else "unknown-motion"
            grouped.setdefault(project_name, {}).setdefault(motion_name, []).append(
                {
                    "run_id": run_dir.name,
                    "output_dir": str(run_dir),
                    "status": meta.get("status", "unknown"),
                    "solver_backend": meta.get("solver_backend", "unknown"),
                    "convergence_mode": str(health["convergence_mode"]),
                    "convergence_severity": str(health["convergence_severity"]),
                }
            )
        return {"tree": grouped}

    @app.get("/api/runs/{run_id}/signals")
    def run_signals(
        run_id: str,
        output_root: str = Query(default=""),
        max_points: int = Query(default=4000, ge=200, le=40000),
        max_spectral_points: int = Query(default=2400, ge=100, le=40000),
    ) -> dict[str, object]:
        run_dir = _resolve_run_dir(run_id, output_root)
        rs = _load_result_or_409(run_dir)
        time = rs.time
        acc = rs.acc_surface
        n = int(min(time.size, acc.size))
        if n <= 1:
            raise HTTPException(status_code=400, detail="Run has insufficient signal samples.")
        time_list = [float(v) for v in time[:n]]
        acc_list = [float(v) for v in acc[:n]]
        time_list, acc_list = _downsample_pair(time_list, acc_list, max_points=max_points)

        dt_s = _estimate_dt(rs.time)
        input_dt_s = float(rs.input_dt_s) if np.isfinite(rs.input_dt_s) and rs.input_dt_s > 0.0 else float(dt_s)
        viewer_periods = _web_spectra_periods()
        spectra_live = compute_spectra(
            np.asarray(rs.acc_surface, dtype=np.float64),
            dt=dt_s,
            damping=0.05,
            periods=viewer_periods,
        )
        period_list = [float(v) for v in spectra_live.periods]
        psa_list = [float(v) for v in spectra_live.psa]
        period_list, psa_list = _downsample_pair(
            period_list,
            psa_list,
            max_points=max_spectral_points,
        )

        freq_list = [float(v) for v in rs.transfer_freq_hz]
        tf_list = [float(v) for v in rs.transfer_abs]
        freq_list, tf_list = _downsample_pair(freq_list, tf_list, max_points=max_spectral_points)

        # Fourier Amplitude Spectrum (surface)
        n_fft = int(2 ** np.ceil(np.log2(rs.acc_surface.size))) if rs.acc_surface.size > 1 else 2
        fas_complex = np.fft.rfft(rs.acc_surface, n=n_fft)
        fas_freq = np.fft.rfftfreq(n_fft, d=dt_s)
        fas_amp = np.abs(fas_complex) * dt_s  # amplitude spectrum
        fas_freq_list = [float(v) for v in fas_freq[1:]]  # skip DC
        fas_amp_list = [float(v) for v in fas_amp[1:]]
        fas_freq_list, fas_amp_list = _downsample_pair(fas_freq_list, fas_amp_list, max_points=max_spectral_points)

        def make_time_axis(size: int) -> list[float]:
            if size <= 0:
                return []
            if rs.ru_time.size >= size:
                return [float(v) for v in rs.ru_time[:size]]
            if rs.time.size >= size:
                return [float(v) for v in rs.time[:size]]
            if rs.time.size > 1:
                dt_guess = float(rs.time[1] - rs.time[0])
                return [float(i) * dt_guess for i in range(size)]
            return [float(i) for i in range(size)]

        n_ru = int(rs.ru.size)
        ru_list = [float(v) for v in rs.ru[:n_ru]]
        ru_time_list = make_time_axis(n_ru)
        if n_ru > max_points:
            step = max(1, n_ru // max_points)
            ru_time_list = ru_time_list[::step]
            ru_list = ru_list[::step]

        n_du = int(rs.delta_u.size)
        delta_u_list = [float(v) for v in rs.delta_u[:n_du]]
        delta_u_time_list = make_time_axis(n_du)
        if n_du > max_points:
            step = max(1, n_du // max_points)
            delta_u_time_list = delta_u_time_list[::step]
            delta_u_list = delta_u_list[::step]

        n_sig = int(rs.sigma_v_eff.size)
        sigma_v_eff_list = [float(v) for v in rs.sigma_v_eff[:n_sig]]
        sigma_time_list = make_time_axis(n_sig)
        if n_sig > max_points:
            step = max(1, n_sig // max_points)
            sigma_time_list = sigma_time_list[::step]
            sigma_v_eff_list = sigma_v_eff_list[::step]

        # Input motion (base acceleration)
        input_acc_list: list[float] = []
        input_psa_list: list[float] = []
        input_period_list: list[float] = []
        applied_input_acc_list: list[float] = []
        applied_input_psa_list: list[float] = []
        applied_input_time_list: list[float] = []
        if rs.acc_input.size > 1:
            raw_input = [float(v) for v in rs.acc_input]
            raw_input_t = [float(v) for v in rs.input_time] if rs.input_time.size else [float(i) * input_dt_s for i in range(len(raw_input))]
            raw_input_t, raw_input = _downsample_pair(raw_input_t, raw_input, max_points=max_points)
            input_time_list = raw_input_t
            input_acc_list = raw_input
            spectra_input = compute_spectra(
                np.asarray(rs.acc_input, dtype=np.float64),
                dt=input_dt_s,
                damping=0.05,
                periods=viewer_periods,
            )
            input_period_list = [float(v) for v in spectra_input.periods]
            input_psa_list = [float(v) for v in spectra_input.psa]
            input_period_list, input_psa_list = _downsample_pair(
                input_period_list, input_psa_list, max_points=max_spectral_points
            )
            applied_input = (
                np.asarray(rs.acc_applied_input, dtype=np.float64)
                if rs.acc_applied_input.size > 1
                else np.asarray(rs.acc_input, dtype=np.float64)
            )
            applied_input_t = (
                [float(v) for v in rs.input_time]
                if rs.input_time.size
                else [float(i) * input_dt_s for i in range(int(applied_input.size))]
            )
            applied_input_t, applied_input_acc_list = _downsample_pair(
                applied_input_t,
                [float(v) for v in applied_input],
                max_points=max_points,
            )
            applied_input_time_list = applied_input_t
            spectra_applied_input = compute_spectra(
                applied_input,
                dt=input_dt_s,
                damping=0.05,
                periods=viewer_periods,
            )
            applied_input_period_list = [float(v) for v in spectra_applied_input.periods]
            applied_input_psa_list = [float(v) for v in spectra_applied_input.psa]
            _, applied_input_psa_list = _downsample_pair(
                applied_input_period_list,
                applied_input_psa_list,
                max_points=max_spectral_points,
            )
        else:
            input_time_list = []

        pga = float(np.max(np.abs(acc))) if acc.size > 0 else 0.0
        pga_input = float(np.max(np.abs(rs.acc_input))) if rs.acc_input.size > 0 else 0.0
        ru_max = float(np.max(rs.ru)) if rs.ru.size > 0 else 0.0
        delta_u_max = float(np.max(rs.delta_u)) if rs.delta_u.size > 0 else 0.0
        sigma_v_eff_min = float(np.min(rs.sigma_v_eff)) if rs.sigma_v_eff.size > 0 else 0.0

        # ── Pro Features ─────────────────────────────────

        # B1: Site Period T₀ = 4H / Vs_avg
        site_period_s: float | None = None
        vs_avg_m_s: float | None = None
        try:
            cfg_path = run_dir / "config_snapshot.json"
            cfg_snap: dict[str, object] = {}
            if cfg_path.exists():
                cfg_snap = json.loads(cfg_path.read_text(encoding="utf-8"))
            prof_layers = cfg_snap.get("profile", {}).get("layers", [])
            if prof_layers:
                total_h = sum(float(la.get("thickness_m", 0)) for la in prof_layers)
                travel_time = sum(
                    float(la.get("thickness_m", 0)) / max(float(la.get("vs_m_s", 100)), 1.0)
                    for la in prof_layers
                )
                if travel_time > 0 and total_h > 0:
                    vs_avg_m_s = float(total_h / travel_time)
                    site_period_s = float(4.0 * total_h / vs_avg_m_s)
        except Exception:
            pass

        # B2: PSV + PSD from PSA
        psv_list = [float(psa_list[i] * period_list[i] / (2.0 * np.pi)) for i in range(len(psa_list))]
        psd_list = [float(psa_list[i] * period_list[i] ** 2 / (4.0 * np.pi ** 2)) for i in range(len(psa_list))]

        # B3: Kappa (κ) estimator — linear regression on FAS log-log slope
        kappa_val: float | None = None
        kappa_r2: float | None = None
        kappa_fit_freq: list[float] = []
        kappa_fit_amp: list[float] = []
        try:
            fas_f_full = np.array(fas_freq[1:], dtype=np.float64)
            fas_a_full = np.array(fas_amp[1:], dtype=np.float64)
            mask = (fas_f_full >= 10.0) & (fas_f_full <= 40.0) & (fas_a_full > 0)
            if int(np.count_nonzero(mask)) >= 5:
                log_f = np.log(fas_f_full[mask])
                log_a = np.log(fas_a_full[mask])
                n_pts = log_f.size
                sum_x = float(np.sum(log_f))
                sum_y = float(np.sum(log_a))
                sum_xy = float(np.sum(log_f * log_a))
                sum_x2 = float(np.sum(log_f ** 2))
                denom = n_pts * sum_x2 - sum_x ** 2
                if abs(denom) > 1e-15:
                    slope = (n_pts * sum_xy - sum_x * sum_y) / denom
                    intercept = (sum_y - slope * sum_x) / n_pts
                    kappa_val = float(-slope / np.pi)  # κ = -slope / π
                    # R²
                    ss_res = float(np.sum((log_a - (slope * log_f + intercept)) ** 2))
                    ss_tot = float(np.sum((log_a - np.mean(log_a)) ** 2))
                    kappa_r2 = float(1.0 - ss_res / max(ss_tot, 1e-30))
                    # Fitted line for visualization
                    fit_f = np.array([10.0, 40.0])
                    fit_a = np.exp(slope * np.log(fit_f) + intercept)
                    kappa_fit_freq = [float(v) for v in fit_f]
                    kappa_fit_amp = [float(v) for v in fit_a * dt_s]
        except Exception:
            pass

        # B4: Konno-Ohmachi smoothed transfer function
        tf_smooth_list: list[float] = []
        try:
            if len(freq_list) > 10:
                tf_arr = np.array(tf_list, dtype=np.float64)
                f_arr = np.array(freq_list, dtype=np.float64)
                bandwidth = 40.0
                smoothed = np.zeros_like(tf_arr)
                log_f = np.log10(np.maximum(f_arr, 1e-10))
                for i in range(len(f_arr)):
                    if f_arr[i] <= 0:
                        smoothed[i] = tf_arr[i]
                        continue
                    diff = log_f - log_f[i]
                    with np.errstate(divide="ignore", invalid="ignore"):
                        arg = bandwidth * diff
                        w = np.where(
                            np.abs(arg) < 1e-6,
                            1.0,
                            (np.sin(arg * np.log(10)) / (arg * np.log(10))) ** 4,
                        )
                    w_sum = float(np.sum(w))
                    smoothed[i] = float(np.sum(w * tf_arr) / max(w_sum, 1e-30))
                tf_smooth_list = [float(v) for v in smoothed]
        except Exception:
            pass

        return {
            "run_id": run_id,
            "time_s": time_list,
            "surface_acc_m_s2": acc_list,
            "input_time_s": input_time_list,
            "input_acc_m_s2": input_acc_list,
            "applied_input_time_s": applied_input_time_list,
            "applied_input_acc_m_s2": applied_input_acc_list,
            "period_s": period_list,
            "psa_m_s2": psa_list,
            "input_period_s": input_period_list,
            "input_psa_m_s2": input_psa_list,
            "applied_input_psa_m_s2": applied_input_psa_list,
            "spectra_source": "recomputed_from_surface_acc",
            "dt_s": float(dt_s),
            "input_dt_s": float(input_dt_s),
            "delta_t": float(dt_s),
            "delta_t_s": float(dt_s),
            "freq_hz": freq_list,
            "transfer_abs": tf_list,
            "fas_freq_hz": fas_freq_list,
            "fas_amplitude": fas_amp_list,
            "psv_m_s": psv_list,
            "psd_m": psd_list,
            "site_period_s": site_period_s,
            "vs_avg_m_s": vs_avg_m_s,
            "kappa": kappa_val,
            "kappa_r2": kappa_r2,
            "kappa_fit_freq": kappa_fit_freq,
            "kappa_fit_amp": kappa_fit_amp,
            "transfer_abs_smooth": tf_smooth_list,
            "ru_time_s": ru_time_list,
            "ru_t": ru_time_list,
            "ru": ru_list,
            "delta_u_time_s": delta_u_time_list,
            "delta_u_t": delta_u_time_list,
            "delta_u": delta_u_list,
            "sigma_v_eff_time_s": sigma_time_list,
            "sigma_v_eff_t": sigma_time_list,
            "sigma_v_eff": sigma_v_eff_list,
            "sigma_v_ref": float(rs.sigma_v_ref),
            "pga": float(pga),
            "pga_input": float(pga_input),
            "ru_max": float(ru_max),
            "delta_u_max": float(delta_u_max),
            "sigma_v_eff_min": float(sigma_v_eff_min),
        }

    @app.get("/api/runs/{run_id}/results/summary", response_model=ResultSummaryResponse)
    def run_results_summary(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> ResultSummaryResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        meta = _read_run_meta(run_dir)
        sqlite_path = run_dir / "results.sqlite"
        return ResultSummaryResponse(
            run_id=run_id,
            status=meta.get("status", "unknown"),
            solver_backend=meta.get("solver_backend", "unknown"),
            project_name=_read_project_name(sqlite_path),
            input_motion=meta.get("input_motion", ""),
            metrics=_read_metrics(sqlite_path),
            convergence=_read_convergence(sqlite_path, run_dir=run_dir),
            output_layers=_read_output_layers(sqlite_path),
            artifacts=_read_artifacts(sqlite_path),
            solver_notes=meta.get("message", ""),
        )

    @app.get("/api/runs/{run_id}/results/hysteresis", response_model=ResultHysteresisResponse)
    def run_results_hysteresis(
        run_id: str,
        output_root: str = Query(default=""),
        max_points: int = Query(default=700, ge=120, le=5000),
    ) -> ResultHysteresisResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        sqlite_path = run_dir / "results.sqlite"
        return _build_hysteresis_response(
            run_id=run_id,
            run_dir=run_dir,
            sqlite_path=sqlite_path,
            max_points=max_points,
        )

    @app.get(
        "/api/runs/{run_id}/results/profile-summary",
        response_model=ResultProfileSummaryResponse,
    )
    def run_results_profile_summary(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> ResultProfileSummaryResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        sqlite_path = run_dir / "results.sqlite"
        layer_rows = _read_profile_layer_summary(sqlite_path, run_dir=run_dir)
        metrics = _read_metrics(sqlite_path)
        total_thickness_m = float(sum(max(0.0, layer.thickness_m) for layer in layer_rows))
        return ResultProfileSummaryResponse(
            run_id=run_id,
            layer_count=len(layer_rows),
            total_thickness_m=total_thickness_m,
            ru_max=metrics.get("ru_max"),
            delta_u_max=metrics.get("delta_u_max"),
            sigma_v_eff_min=metrics.get("sigma_v_eff_min"),
            layers=layer_rows,
        )

    @app.post(
        "/api/results/displacement-animation",
        response_model=DisplacementAnimationResponse,
    )
    def results_displacement_animation(
        payload: DisplacementAnimationRequest,
    ) -> DisplacementAnimationResponse:
        run_dir = _resolve_run_dir(payload.run_id, payload.output_root)
        result_store = _load_result_or_409(run_dir)
        sqlite_path = run_dir / "results.sqlite"
        return _build_displacement_animation_response(
            run_id=payload.run_id,
            run_dir=run_dir,
            result_store=result_store,
            sqlite_path=sqlite_path,
            frame_count=payload.frame_count,
            max_depth_points=payload.max_depth_points,
        )

    @app.get(
        "/api/results/response-spectra-summary",
        response_model=ResponseSpectraSummaryResponse,
    )
    def results_response_spectra_summary(
        run_id: str = Query(..., min_length=1),
        output_root: str = Query(default=""),
    ) -> ResponseSpectraSummaryResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        result_store = _load_result_or_409(run_dir)
        return _build_response_spectra_summary_response(
            run_id=run_id,
            result_store=result_store,
        )

    @app.get("/api/runs/{run_id}/profile-summary.csv")
    def download_profile_summary_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        sqlite_path = run_dir / "results.sqlite"
        layer_rows = _read_profile_layer_summary(sqlite_path, run_dir=run_dir)
        metrics = _read_metrics(sqlite_path)
        total_thickness_m = float(sum(max(0.0, layer.thickness_m) for layer in layer_rows))
        summary = ResultProfileSummaryResponse(
            run_id=run_id,
            layer_count=len(layer_rows),
            total_thickness_m=total_thickness_m,
            ru_max=metrics.get("ru_max"),
            delta_u_max=metrics.get("delta_u_max"),
            sigma_v_eff_min=metrics.get("sigma_v_eff_min"),
            layers=layer_rows,
        )
        payload = _profile_summary_csv_text(summary)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}_profile_summary.csv"'}
        return PlainTextResponse(payload, media_type="text/csv", headers=headers)

    @app.get("/api/runs/{run_id}/surface-acc.csv")
    def download_surface_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        rs = _load_result_or_409(run_dir)
        n = int(min(rs.time.size, rs.acc_surface.size))
        if n <= 1:
            raise HTTPException(status_code=400, detail="Run has insufficient signal samples.")
        dt_s = _estimate_dt(rs.time)
        lines = ["time_s,acc_m_s2,delta_t_s"]
        for t, a in zip(rs.time[:n], rs.acc_surface[:n], strict=False):
            lines.append(f"{float(t):.8f},{float(a):.10e},{dt_s:.8e}")
        payload = "\n".join(lines)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}_surface_acc.csv"'}
        return PlainTextResponse(payload, media_type="text/csv", headers=headers)

    @app.get("/api/runs/{run_id}/pwp-effective.csv")
    def download_pwp_effective_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        rs = _load_result_or_409(run_dir)
        n = int(rs.ru.size)
        if n <= 0:
            raise HTTPException(status_code=400, detail="Run has no PWP/ru samples.")
        if rs.ru_time.size >= n:
            t_series = rs.ru_time[:n]
        elif rs.time.size >= n:
            t_series = rs.time[:n]
        else:
            t_series = np.arange(n, dtype=np.float64) * float(rs.dt_s)
        dt_s = _estimate_dt(t_series)
        lines = ["time_s,ru,delta_u,sigma_v_eff,delta_t_s"]
        for i in range(n):
            t = float(t_series[i])
            ru = float(rs.ru[i]) if i < rs.ru.size else float("nan")
            du = float(rs.delta_u[i]) if i < rs.delta_u.size else float("nan")
            sig = float(rs.sigma_v_eff[i]) if i < rs.sigma_v_eff.size else float("nan")
            lines.append(f"{t:.8f},{ru:.10e},{du:.10e},{sig:.10e},{dt_s:.8e}")
        payload = "\n".join(lines)
        headers = {"Content-Disposition": f'attachment; filename="{run_id}_pwp_effective.csv"'}
        return PlainTextResponse(payload, media_type="text/csv", headers=headers)

    @app.get("/api/runs/{run_id}/download/{artifact}")
    def download_artifact(
        run_id: str,
        artifact: str,
        output_root: str = Query(default=""),
    ) -> FileResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        allowed = {
            "results.h5": "results.h5",
            "results.sqlite": "results.sqlite",
            "surface_acc.out": "surface_acc.out",
            "surface_acc.csv": "surface_acc.csv",
            "pwp_effective.csv": "pwp_effective.csv",
            "run_meta.json": "run_meta.json",
        }
        if artifact not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported artifact: {artifact}")
        path = run_dir / allowed[artifact]
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact}")
        return FileResponse(path)

    @app.post("/api/run", response_model=RunResponse)
    def execute_run(payload: RunRequest) -> RunResponse:
        try:
            config_path = _resolve_input_path(payload.config_path, label="Config file")
            output_root = _resolve_output_root(payload.output_root)

            cfg = load_project_config(config_path)

            # motion_path: use request value, fall back to config
            raw_motion = payload.motion_path.strip() if payload.motion_path else ""
            if not raw_motion:
                raw_motion = str(cfg.motion.filepath) if cfg.motion.filepath else ""
            if not raw_motion:
                raise HTTPException(status_code=400, detail="No motion_path provided and config has no motion.filepath.")
            motion_path = _resolve_input_path(raw_motion, label="Motion file")
            backend, backend_note = _apply_runtime_backend(payload.backend)
            cfg.analysis.solver_backend = backend

            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            result = run_analysis(cfg, motion, output_dir=output_root)
            result_output_root = result.output_dir.parent.resolve()
            return RunResponse(
                run_id=result.run_id,
                output_dir=str(result.output_dir),
                output_root=str(result_output_root),
                status=result.status,
                message=f"{backend_note} | {result.message}",
                backend=backend,
            )
        except HTTPException:
            raise
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Run failed: {type(exc).__name__}: {exc}",
            ) from exc

    @app.post("/api/run-batch", response_model=RunBatchResponse)
    def execute_run_batch(payload: RunBatchRequest) -> RunBatchResponse:
        try:
            config_path = _resolve_input_path(payload.config_path, label="Config file")
            output_root = _resolve_output_root(payload.output_root)

            cfg = load_project_config(config_path)
            backend, backend_note = _apply_runtime_backend(payload.backend)
            cfg.analysis.solver_backend = backend

            raw_motion_paths = [item.strip() for item in payload.motion_paths if item and item.strip()]
            if not raw_motion_paths:
                fallback = str(cfg.motion.filepath) if cfg.motion.filepath else ""
                if not fallback:
                    raise HTTPException(
                        status_code=400,
                        detail="No motion_paths provided and config has no motion.filepath.",
                    )
                raw_motion_paths = [fallback]

            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motions: list[Motion] = []
            for raw_motion in raw_motion_paths:
                motion_path = _resolve_input_path(raw_motion, label="Motion file")
                motions.append(load_motion(motion_path, dt=dt, unit=cfg.motion.units))

            batch = run_batch(
                cfg,
                motions,
                output_dir=output_root,
                n_jobs=min(payload.n_jobs, max(len(motions), 1)),
            )
            result_output_root = output_root.resolve()
            results = [
                RunResponse(
                    run_id=result.run_id,
                    output_dir=str(result.output_dir),
                    output_root=str(result_output_root),
                    status=result.status,
                    message=result.message,
                    backend=backend,
                )
                for result in batch.results
            ]
            statuses = {result.status for result in results}
            status = "ok" if statuses == {"ok"} else ("partial" if "ok" in statuses else "error")
            unique_run_count = len({result.run_id for result in results})
            return RunBatchResponse(
                output_root=str(result_output_root),
                backend=backend,
                status=status,
                message=(
                    f"{backend_note} | Completed {len(results)} motion(s) "
                    f"with {min(payload.n_jobs, max(len(motions), 1))} worker(s)."
                ),
                motion_count=len(results),
                unique_run_count=unique_run_count,
                n_jobs=min(payload.n_jobs, max(len(motions), 1)),
                results=results,
            )
        except HTTPException:
            raise
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Batch run failed: {type(exc).__name__}: {exc}",
            ) from exc

    @app.get("/api/reference-curves")
    def reference_curves(
        curve_type: str = Query("seed_idriss_mean"),
        plasticity_index: float = Query(0.0, ge=0.0),
    ) -> dict[str, object]:
        from dsra1d.calibration import get_reference_curves
        try:
            curves = get_reference_curves(curve_type, plasticity_index=plasticity_index)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "name": curves.name,
            "source": curves.source,
            "strain": curves.strain.astype(float).tolist(),
            "modulus_reduction": curves.modulus_reduction.astype(float).tolist(),
            "damping_ratio": curves.damping_ratio.astype(float).tolist(),
        }

    @app.get("/api/reference-curves/types")
    def reference_curve_types() -> list[dict[str, str]]:
        return [
            {"id": "seed_idriss_upper", "name": "Seed-Idriss Sand (Upper)", "source": "Seed & Idriss (1970)"},
            {"id": "seed_idriss_mean", "name": "Seed-Idriss Sand (Mean)", "source": "Seed & Idriss (1970)"},
            {"id": "vucetic_dobry", "name": "Vucetic-Dobry", "source": "Vucetic & Dobry (1991)", "pi_dependent": "true"},
        ]

    @app.post("/api/single-element-test")
    def single_element_test(
        material: str = Query(...),
        strain_amplitude: float = Query(0.01, gt=0.0, le=0.5),
        gmax: float = Query(100000.0, gt=0.0),
        gamma_ref: float = Query(0.001, gt=0.0),
        damping_min: float = Query(0.01, ge=0.0, le=0.5),
        damping_max: float = Query(0.15, ge=0.0, le=0.5),
        reload_factor: float = Query(2.0, ge=1.0, le=5.0),
        g_reduction_min: float = Query(0.0, ge=0.0, le=0.5),
        a1: float = Query(1.0, gt=0.0),
        a2: float = Query(0.0, ge=0.0),
        m: float = Query(1.0, gt=0.0),
        tau_max: float | None = Query(default=None, gt=0.0),
        theta1: float | None = Query(default=None),
        theta2: float | None = Query(default=None),
        theta3: float | None = Query(default=None, gt=0.0),
        theta4: float | None = Query(default=None, gt=0.0),
        theta5: float | None = Query(default=None, gt=0.0),
    ) -> dict[str, object]:
        from dsra1d.materials.hysteretic import generate_masing_loop

        mat_type = MaterialType(material) if material in {e.value for e in MaterialType} else MaterialType.MKZ
        params: dict[str, float] = {
            "gmax": gmax,
            "gamma_ref": gamma_ref,
            "damping_min": damping_min,
            "damping_max": damping_max,
            "reload_factor": reload_factor,
            "g_reduction_min": g_reduction_min,
        }
        if mat_type == MaterialType.GQH:
            params.update({"a1": a1, "a2": a2, "m": m})
            if (
                tau_max is not None
                and theta1 is not None
                and theta2 is not None
                and theta3 is not None
                and theta4 is not None
                and theta5 is not None
            ):
                params.update(
                    {
                        "tau_max": tau_max,
                        "theta1": float(theta1),
                        "theta2": float(theta2),
                        "theta3": float(theta3),
                        "theta4": float(theta4),
                        "theta5": float(theta5),
                    }
                )

        try:
            loop = generate_masing_loop(
                mat_type, params,
                strain_amplitude=strain_amplitude,
                n_points_per_branch=100,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        strains_check = np.array([strain_amplitude], dtype=np.float64)
        d_masing = compute_masing_damping_ratio(mat_type, params, strains_check)

        if mat_type == MaterialType.GQH:
            g_red = float(gqh_modulus_reduction_from_params(strains_check, params)[0])
        else:
            g_red = float(mkz_modulus_reduction(
                strains_check, gamma_ref=gamma_ref, g_reduction_min=g_reduction_min,
            )[0])

        return {
            "material": mat_type.value,
            "strain_amplitude": strain_amplitude,
            "loop_strain": loop.strain.astype(float).tolist(),
            "loop_stress": loop.stress.astype(float).tolist(),
            "loop_energy": loop.energy_dissipation,
            "masing_damping_ratio": float(d_masing[0]),
            "g_reduction": g_red,
            "secant_modulus": float(np.max(np.abs(loop.stress))) / strain_amplitude if strain_amplitude > 0 else 0.0,
            "peak_stress": float(np.max(np.abs(loop.stress))),
            "params": params,
        }

    # ── Excel Export ──────────────────────────────────────────────

    @app.get("/api/runs/{run_id}/export/xlsx")
    def export_run_xlsx(
        run_id: str,
        output_root: str = Query("out/web"),
        tier: str = Query(default="pro"),
    ) -> FileResponse:
        from dsra1d.export.excel import export_run_to_xlsx

        run_dir = _resolve_run_dir(run_id, output_root)
        include_pro = tier == "pro"
        try:
            xlsx_path = export_run_to_xlsx(run_dir, include_pro_sheets=include_pro)
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Excel export failed: {exc}") from exc
        return FileResponse(
            path=str(xlsx_path),
            filename=f"{run_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ── Motion Library (scan directories for earthquake records) ──

    @app.get("/api/motions/library")
    def list_motion_library(extra_dir: list[str] | None = Query(default=None)) -> list[dict[str, str]]:
        """Scan only the explicitly provided directories for earthquake motion files."""
        return _scan_motion_library(_resolve_motion_library_dirs(extra_dir or []))

    @app.post("/api/motions/generated/clear", response_model=MotionGeneratedClearResponse)
    def clear_generated_motion_outputs() -> MotionGeneratedClearResponse:
        """Delete uploaded/converted/generated motion files kept under the default UI motion cache."""
        return _clear_generated_motion_dir()

    @app.get("/api/motion/preview")
    def motion_preview(
        path: str = Query(..., min_length=1),
        max_points: int = Query(default=1200, ge=100, le=10000),
        units_hint: str = Query(default="m/s2"),
        dt_override: float | None = Query(default=None, gt=0.0),
        format_hint: Literal["auto", "time_acc", "single", "numeric_stream"] = Query(default="auto"),
        delimiter: str | None = Query(default=None),
        skip_rows: int = Query(default=0, ge=0, le=5000),
        time_col: int = Query(default=0, ge=0, le=100),
        acc_col: int = Query(default=1, ge=0, le=100),
        has_time: bool = Query(default=True),
        scale_mode: ScaleMode = Query(default=ScaleMode.NONE),
        scale_factor: float | None = Query(default=None),
        target_pga: float | None = Query(default=None),
        processing_order: Literal["filter_first", "baseline_first"] = Query(default="filter_first"),
        baseline_on: bool = Query(default=False),
        baseline_method: str = Query(default="poly4"),
        baseline_degree: int = Query(default=4, ge=0, le=10),
        filter_on: bool = Query(default=False),
        filter_domain: Literal["time", "frequency"] = Query(default="time"),
        filter_config: str = Query(default="bandpass"),
        filter_type: Literal["butter", "cheby", "bessel"] = Query(default="butter"),
        f_low: float = Query(default=0.1, ge=0.0),
        f_high: float = Query(default=25.0, ge=0.0),
        filter_order: int = Query(default=4, ge=1, le=16),
        acausal: bool = Query(default=True),
        window_on: bool = Query(default=False),
        window_type: str = Query(default="hanning"),
        window_param: float = Query(default=0.1, ge=0.0),
        window_duration: float | None = Query(default=None, gt=0.0),
        window_apply_to: Literal["start", "end", "both"] = Query(default="both"),
        trim_start: float = Query(default=0.0, ge=0.0),
        trim_end: float = Query(default=0.0, ge=0.0),
        trim_taper: bool = Query(default=False),
        pad_front: float = Query(default=0.0, ge=0.0),
        pad_end: float = Query(default=0.0, ge=0.0),
        pad_method: str = Query(default="zeros"),
        pad_method_front: str | None = Query(default=None),
        pad_method_end: str | None = Query(default=None),
        pad_smooth: bool = Query(default=False),
        residual_fix: bool = Query(default=False),
        spectrum_damping_ratio: float = Query(default=0.05, gt=0.0, lt=1.0),
        show_uncorrected_preview: bool = Query(default=True),
    ) -> dict[str, object]:
        """Read a motion file and return unit-aware preview data plus derived response spectra."""
        motion_path = Path(path)
        if not motion_path.is_file():
            raise HTTPException(status_code=404, detail=f"Motion file not found: {path}")
        try:
            from dsra1d.motion.io import load_motion_series
            time_arr, acc_raw = load_motion_series(
                str(motion_path),
                dt_override=dt_override,
                fallback_dt=0.01,
                format_hint=format_hint,
                delimiter=delimiter,
                skip_rows=skip_rows,
                time_col=time_col,
                acc_col=acc_col,
                has_time=has_time,
            )
            factor = accel_factor_to_si(units_hint)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Cannot parse motion file: {exc}") from exc

        acc_si = np.asarray(acc_raw, dtype=np.float64) * factor
        time_arr = np.asarray(time_arr, dtype=np.float64)
        dt = _estimate_dt(time_arr) if time_arr.size > 1 else 0.01
        cfg = _motion_config_from_model(
            {
                "units_hint": units_hint,
                "scale_mode": scale_mode,
                "scale_factor": scale_factor,
                "target_pga": target_pga,
                "processing_order": processing_order,
                "baseline_on": baseline_on,
                "baseline_method": baseline_method,
                "baseline_degree": baseline_degree,
                "filter_on": filter_on,
                "filter_domain": filter_domain,
                "filter_config": filter_config,
                "filter_type": filter_type,
                "f_low": f_low,
                "f_high": f_high,
                "filter_order": filter_order,
                "acausal": acausal,
                "window_on": window_on,
                "window_type": window_type,
                "window_param": window_param,
                "window_duration": window_duration,
                "window_apply_to": window_apply_to,
                "trim_start": trim_start,
                "trim_end": trim_end,
                "trim_taper": trim_taper,
                "pad_front": pad_front,
                "pad_end": pad_end,
                "pad_method": pad_method,
                "pad_method_front": pad_method_front,
                "pad_method_end": pad_method_end,
                "pad_smooth": pad_smooth,
                "residual_fix": residual_fix,
                "spectrum_damping_ratio": spectrum_damping_ratio,
                "show_uncorrected_preview": show_uncorrected_preview,
            },
            scale_mode=scale_mode,
            scale_factor=scale_factor,
            target_pga=target_pga,
            force_processing=True,
        )
        motion = Motion(dt=float(dt), acc=acc_si, unit="m/s2", source=motion_path)
        processed_components = process_motion_components(motion, cfg)
        return _motion_preview_payload(
            motion_path=motion_path,
            units_hint=units_hint,
            format_hint=format_hint,
            raw_time_s=time_arr,
            raw_acc_si=acc_si,
            processed_dt_s=float(dt),
            processed_components=processed_components,
            spectrum_damping_ratio=float(spectrum_damping_ratio),
            show_uncorrected_preview=bool(show_uncorrected_preview),
            max_points=max_points,
        )

    @app.get("/api/examples")
    def list_examples() -> list[dict[str, str]]:
        examples_dir = Path(__file__).resolve().parent.parent.parent.parent / "examples" / "native"
        if not examples_dir.is_dir():
            return []
        results = []
        for yml in sorted(examples_dir.glob("*.yml")):
            results.append({
                "id": yml.stem,
                "name": yml.stem.replace("_", " ").title(),
                "path": str(yml),
            })
        return results

    @app.post("/api/examples/{example_id}/load")
    def load_example(example_id: str) -> dict[str, object]:
        """Load an example config and return wizard-compatible state."""
        examples_dir = Path(__file__).resolve().parent.parent.parent.parent / "examples" / "native"
        yml_path = examples_dir / f"{example_id}.yml"
        if not yml_path.is_file():
            raise HTTPException(status_code=404, detail=f"Example '{example_id}' not found.")
        try:
            cfg = load_project_config(yml_path)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        layers = []
        for layer in cfg.profile.layers:
            layer_dict: dict[str, object] = {
                "name": layer.name,
                "thickness": float(layer.thickness_m),
                "thickness_m": float(layer.thickness_m),
                "vs": float(layer.vs_m_s),
                "vs_m_s": float(layer.vs_m_s),
                "unit_weight": float(layer.unit_weight_kn_m3),
                "unit_weight_kN_m3": float(layer.unit_weight_kn_m3),
                "material": layer.material.value,
                "material_params": {k: float(v) for k, v in layer.material_params.items()},
            }
            if layer.calibration is not None:
                layer_dict["calibration"] = {
                    "plasticity_index": layer.calibration.plasticity_index,
                    "ocr": layer.calibration.ocr,
                    "mean_effective_stress_kpa": layer.calibration.mean_effective_stress_kpa,
                    "k0": layer.calibration.k0,
                    "frequency_hz": layer.calibration.frequency_hz,
                    "num_cycles": layer.calibration.num_cycles,
                    "strain_min": layer.calibration.strain_min,
                    "strain_max": layer.calibration.strain_max,
                    "fit_strain_min": layer.calibration.fit_strain_min,
                    "fit_strain_max": layer.calibration.fit_strain_max,
                    "target_strength_kpa": layer.calibration.target_strength_kpa,
                    "target_strength_ratio": layer.calibration.target_strength_ratio,
                    "target_strength_strain": layer.calibration.target_strength_strain,
                    "n_points": layer.calibration.n_points,
                    "reload_factor": layer.calibration.reload_factor,
                    "fit_procedure": layer.calibration.fit_procedure,
                    "fit_limits": (
                        layer.calibration.fit_limits.model_dump(exclude_none=True)
                        if layer.calibration.fit_limits is not None
                        else None
                    ),
                    "auto_refit_on_reference_change": layer.calibration.auto_refit_on_reference_change,
                }
                layer_dict["reference_curve"] = "darendeli"
                layer_dict["plasticity_index"] = layer.calibration.plasticity_index
            layers.append(layer_dict)

        return {
            "project_name": cfg.project_name or example_id,
            "solver_backend": cfg.analysis.solver_backend,
            "boundary_condition": cfg.boundary_condition,
            "damping_mode": cfg.analysis.damping_mode or "frequency_independent",
            "dt": cfg.analysis.dt or 0.005,
            "f_max": cfg.analysis.f_max,
            "max_iterations": getattr(cfg.analysis, "max_iterations", 15),
            "convergence_tol": getattr(cfg.analysis, "convergence_tol", 0.03),
            "strain_ratio": getattr(cfg.analysis, "strain_ratio", 0.65),
            "nonlinear_substeps": getattr(cfg.analysis, "nonlinear_substeps", 4),
            "viscous_damping_update": False,
            "motion_path": "",
            "motion_units": cfg.motion.units if cfg.motion else "m/s2",
            "motion_input_type": cfg.motion.input_type if cfg.motion else "within",
            "scale_mode": "none",
            "timeout_s": getattr(cfg.analysis, "timeout_s", 180),
            "retries": getattr(cfg.analysis, "retries", 1),
            "bedrock": (
                cfg.profile.bedrock.model_dump(mode="json", by_alias=True)
                if cfg.profile.bedrock is not None
                else None
            ),
            "layers": layers,
        }

    @app.get("/")
    def web_root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app


app = create_app()
