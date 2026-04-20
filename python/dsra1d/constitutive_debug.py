from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from dsra1d.config import BedrockProperties, BoundaryCondition, ProjectConfig, load_project_config
from dsra1d.deepsoil_compare import (
    _interpolate_series,
    _load_profile_from_run,
    _load_run_config_snapshot,
    _metric_nrmse as _compare_metric_nrmse,
    _time_history_metrics,
)
from dsra1d.deepsoil_excel import import_deepsoil_excel_bundle
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.materials.mrdf import mrdf_coefficients_from_params
from dsra1d.motion import (
    build_boundary_excitation,
    effective_input_acceleration,
    load_motion,
)
from dsra1d.newmark_nonlinear import solve_nonlinear_implicit_newmark
from dsra1d.nonlinear import _ElementConstitutiveState, _element_backbone_stress
from dsra1d.post import compute_spectra
from dsra1d.store import load_result


@dataclass(slots=True)
class ConstitutiveReplayArtifacts:
    output_dir: Path
    replay_csv: Path
    summary_json: Path
    reference_hysteresis_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "replay_csv": str(self.replay_csv),
            "summary_json": str(self.summary_json),
            "reference_hysteresis_csv": str(self.reference_hysteresis_csv),
        }


@dataclass(slots=True)
class ConstitutiveReplaySummary:
    point_count: int
    stress_path_nrmse: float | None
    secant_path_nrmse: float | None
    secant_envelope_nrmse: float | None
    tau_peak_pct_diff: float | None
    gamma_peak_pct_diff: float | None
    loop_energy_pct_diff: float | None
    branch_switch_count: int
    max_branch_id: int | None
    reason_counts: dict[str, int]
    branch_kind_counts: dict[str, int]
    final_gamma_m_global: float | None
    max_gamma_m_global: float | None
    f_mrdf_min: float | None
    f_mrdf_max: float | None


@dataclass(slots=True)
class ConstitutiveReplayResult:
    config_path: Path
    layer_index: int
    material: str
    g0_kpa: float
    mrdf_reference_mode_code: float
    artifacts: ConstitutiveReplayArtifacts
    summary: ConstitutiveReplaySummary

    def to_dict(self) -> dict[str, object]:
        return {
            "config_path": str(self.config_path),
            "layer_index": self.layer_index,
            "material": self.material,
            "g0_kpa": self.g0_kpa,
            "mrdf_reference_mode_code": self.mrdf_reference_mode_code,
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class SolverTangentAuditArtifacts:
    output_dir: Path
    audit_csv: Path
    summary_json: Path
    motion_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "audit_csv": str(self.audit_csv),
            "summary_json": str(self.summary_json),
            "motion_csv": str(self.motion_csv),
        }


@dataclass(slots=True)
class SolverTangentAuditSummary:
    row_count: int
    max_branch_id: int | None
    reason_counts: dict[str, int]
    branch_kind_counts: dict[str, int]
    gamma_abs_max: float | None
    tau_abs_max: float | None
    kt_min_kpa: float | None
    kt_max_kpa: float | None
    gamma_m_global_max: float | None
    f_mrdf_min: float | None
    f_mrdf_max: float | None
    g_ref_min_kpa: float | None
    g_ref_max_kpa: float | None
    g_t_ref_min_kpa: float | None
    g_t_ref_max_kpa: float | None


@dataclass(slots=True)
class SolverTangentAuditResult:
    config_path: Path
    motion_csv: Path
    layer_index: int
    mrdf_reference_mode_code: float
    artifacts: SolverTangentAuditArtifacts
    summary: SolverTangentAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "config_path": str(self.config_path),
            "motion_csv": str(self.motion_csv),
            "layer_index": self.layer_index,
            "mrdf_reference_mode_code": self.mrdf_reference_mode_code,
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class ElasticBoundaryAuditArtifacts:
    output_dir: Path
    audit_csv: Path
    summary_json: Path
    motion_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "audit_csv": str(self.audit_csv),
            "summary_json": str(self.summary_json),
            "motion_csv": str(self.motion_csv),
        }


@dataclass(slots=True)
class ElasticBoundaryAuditSummary:
    row_count: int
    raw_input_pga_m_s2: float | None
    applied_input_pga_m_s2: float | None
    incident_force_abs_max: float | None
    dashpot_force_abs_max: float | None
    net_boundary_force_abs_max: float | None
    reconstructed_boundary_force_abs_max: float | None
    assembled_boundary_force_abs_max: float | None
    incident_force_rms: float | None
    dashpot_force_rms: float | None
    net_boundary_force_rms: float | None
    reconstructed_boundary_force_rms: float | None
    assembled_boundary_force_rms: float | None
    dashpot_to_incident_rms_ratio: float | None
    net_to_incident_rms_ratio: float | None
    dashpot_incident_corr: float | None
    assembled_vs_reconstructed_force_nrmse: float | None
    base_relative_velocity_abs_max: float | None
    base_relative_displacement_abs_max: float | None
    surface_acc_abs_max: float | None
    surface_acc_std_m_s2: float | None
    impedance_c: float | None


@dataclass(slots=True)
class ElasticBoundaryAuditResult:
    config_path: Path
    motion_csv: Path
    boundary_condition: str
    motion_input_type: str
    artifacts: ElasticBoundaryAuditArtifacts
    summary: ElasticBoundaryAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "config_path": str(self.config_path),
            "motion_csv": str(self.motion_csv),
            "boundary_condition": self.boundary_condition,
            "motion_input_type": self.motion_input_type,
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class ElasticBoundaryFrequencyAuditArtifacts:
    output_dir: Path
    summary_json: Path
    summary_md: Path
    source_audit_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "summary_json": str(self.summary_json),
            "summary_md": str(self.summary_md),
            "source_audit_csv": str(self.source_audit_csv),
        }


@dataclass(slots=True)
class ElasticBoundaryFrequencyAuditSummary:
    row_count: int
    dt_s: float | None
    dominant_surface_frequency_hz: float | None
    dominant_surface_period_s: float | None
    dominant_net_force_frequency_hz: float | None
    dominant_net_force_period_s: float | None
    dominant_incident_force_frequency_hz: float | None
    dominant_incident_force_period_s: float | None
    net_to_incident_amplitude_ratio_at_surface_peak: float | None
    net_to_surface_amplitude_ratio_at_surface_peak: float | None
    incident_to_surface_amplitude_ratio_at_surface_peak: float | None
    net_surface_phase_diff_deg_at_surface_peak: float | None
    incident_surface_phase_diff_deg_at_surface_peak: float | None
    net_incident_phase_diff_deg_at_surface_peak: float | None


@dataclass(slots=True)
class ElasticBoundaryFrequencyAuditResult:
    source_audit_csv: Path
    artifacts: ElasticBoundaryFrequencyAuditArtifacts
    summary: ElasticBoundaryFrequencyAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "source_audit_csv": str(self.source_audit_csv),
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class LayerComplianceContribution:
    profile_layer_index: int
    profile_layer_name: str
    element_count: int
    mean_compliance_fraction: float | None
    max_compliance_fraction: float | None
    mean_kt_kpa: float | None
    min_kt_kpa: float | None
    max_kt_kpa: float | None
    gamma_abs_max: float | None
    tau_abs_max: float | None
    gamma_m_global_max: float | None
    f_mrdf_min: float | None
    f_mrdf_max: float | None
    g_ref_min_kpa: float | None
    g_ref_max_kpa: float | None
    g_t_ref_min_kpa: float | None
    g_t_ref_max_kpa: float | None
    reason_counts: dict[str, int]
    branch_kind_counts: dict[str, int]


@dataclass(slots=True)
class LayerSweepAuditArtifacts:
    output_dir: Path
    audit_csv: Path
    summary_json: Path
    layer_summary_csv: Path
    motion_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "audit_csv": str(self.audit_csv),
            "summary_json": str(self.summary_json),
            "layer_summary_csv": str(self.layer_summary_csv),
            "motion_csv": str(self.motion_csv),
        }


@dataclass(slots=True)
class LayerSweepAuditSummary:
    row_count: int
    state_count: int
    equivalent_stiffness_min: float | None
    equivalent_stiffness_max: float | None
    dominant_layer_by_mean_compliance: int | None
    dominant_layer_mean_compliance: float | None
    layers: list[LayerComplianceContribution]


@dataclass(slots=True)
class LayerSweepAuditResult:
    config_path: Path
    motion_csv: Path
    mrdf_reference_mode_code: float
    artifacts: LayerSweepAuditArtifacts
    summary: LayerSweepAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "config_path": str(self.config_path),
            "motion_csv": str(self.motion_csv),
            "mrdf_reference_mode_code": self.mrdf_reference_mode_code,
            "artifacts": self.artifacts.to_dict(),
            "summary": {
                "row_count": self.summary.row_count,
                "state_count": self.summary.state_count,
                "equivalent_stiffness_min": self.summary.equivalent_stiffness_min,
                "equivalent_stiffness_max": self.summary.equivalent_stiffness_max,
                "dominant_layer_by_mean_compliance": self.summary.dominant_layer_by_mean_compliance,
                "dominant_layer_mean_compliance": self.summary.dominant_layer_mean_compliance,
                "layers": [asdict(layer) for layer in self.summary.layers],
            },
        }


def _load_reference_hysteresis_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames:
            strain: list[float] = []
            stress: list[float] = []
            for row in reader:
                gamma_raw = row.get("strain") or row.get("gamma") or row.get("shear_strain")
                tau_raw = row.get("stress") or row.get("tau") or row.get("shear_stress")
                if gamma_raw is None or tau_raw is None:
                    continue
                try:
                    gamma = float(gamma_raw)
                    tau = float(tau_raw)
                except ValueError:
                    continue
                if np.isfinite(gamma) and np.isfinite(tau):
                    strain.append(gamma)
                    stress.append(tau)
            if len(strain) >= 8:
                return np.asarray(strain, dtype=np.float64), np.asarray(stress, dtype=np.float64)

    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        tokens = [token.strip() for token in text.replace(";", ",").split(",")]
        if len(tokens) < 2:
            tokens = text.split()
        try:
            values = [float(token) for token in tokens if token]
        except ValueError:
            continue
        if len(values) >= 2:
            rows.append(values)
    if len(rows) < 8:
        raise ValueError(f"Reference hysteresis CSV requires at least 8 numeric rows: {path}")
    table = np.asarray(rows, dtype=np.float64)
    return table[:, 0], table[:, 1]


def _estimate_gmax_kpa(vs_m_s: float, unit_weight_kn_m3: float) -> float:
    unit_weight = unit_weight_kn_m3 if unit_weight_kn_m3 > 0.0 else 18.0
    rho_kg_m3 = (unit_weight * 1000.0) / 9.81
    return float(max((rho_kg_m3 * vs_m_s * vs_m_s) / 1000.0, 1.0))


def _metric_nrmse(lhs: np.ndarray, rhs: np.ndarray) -> float | None:
    mask = np.isfinite(lhs) & np.isfinite(rhs)
    if int(np.count_nonzero(mask)) == 0:
        return None
    lhs_use = np.asarray(lhs[mask], dtype=np.float64)
    rhs_use = np.asarray(rhs[mask], dtype=np.float64)
    ref_peak = float(np.max(np.abs(rhs_use))) if rhs_use.size > 0 else 0.0
    if ref_peak <= 0.0:
        return None
    return float(np.sqrt(np.mean((lhs_use - rhs_use) ** 2)) / ref_peak)


def _monotonic_envelope(
    strain: np.ndarray,
    stress: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    gamma_abs = np.abs(np.asarray(strain, dtype=np.float64))
    tau_abs = np.abs(np.asarray(stress, dtype=np.float64))
    mask = np.isfinite(gamma_abs) & np.isfinite(tau_abs) & (gamma_abs > 0.0)
    if int(np.count_nonzero(mask)) < 8:
        raise ValueError("Need at least 8 finite nonzero points for a hysteresis envelope.")
    gamma_sorted = gamma_abs[mask][np.argsort(gamma_abs[mask])]
    tau_sorted = tau_abs[mask][np.argsort(gamma_abs[mask])]
    tau_env = np.maximum.accumulate(tau_sorted)
    unique_gamma, unique_idx = np.unique(gamma_sorted, return_index=True)
    return unique_gamma.astype(np.float64), tau_env[unique_idx].astype(np.float64)


def _build_layer_state(
    config: ProjectConfig,
    *,
    layer_index: int,
    mode_code_override: float | None,
) -> tuple[_ElementConstitutiveState, dict[str, float], float]:
    layer = config.profile.layers[layer_index]
    params = {key: float(value) for key, value in layer.material_params.items()}
    g0_kpa = float(params.get("gmax", _estimate_gmax_kpa(float(layer.vs_m_s), float(layer.unit_weight_kn_m3))))
    if mode_code_override is not None:
        params["mrdf_reference_mode_code"] = float(mode_code_override)
    reload_factor = float(np.clip(params.get("reload_factor", 2.0), 0.5, 4.0))
    state = _ElementConstitutiveState(
        material=layer.material,
        params=params,
        gmax_fallback=g0_kpa,
        reload_factor=reload_factor,
        mrdf_coeffs=mrdf_coefficients_from_params(params),
    )
    return state, params, g0_kpa


def replay_reference_hysteresis(
    config_path: str | Path,
    reference_hysteresis_csv: str | Path,
    output_dir: str | Path,
    *,
    layer_index: int = 0,
    mode_code_override: float | None = None,
) -> ConstitutiveReplayResult:
    config_file = Path(config_path)
    reference_file = Path(reference_hysteresis_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_project_config(config_file)
    state, params, g0_kpa = _build_layer_state(
        config,
        layer_index=layer_index,
        mode_code_override=mode_code_override,
    )
    ref_gamma, ref_tau = _load_reference_hysteresis_csv(reference_file)
    replay_csv = out_dir / f"layer_{layer_index + 1}_constitutive_replay.csv"
    summary_json = out_dir / f"layer_{layer_index + 1}_constitutive_replay_summary.json"

    reason_counts = {"0": 0, "1": 0, "2": 0}
    branch_kind_counts: dict[str, int] = {}
    branch_switch_count = 0
    prev_branch_id: int | None = None
    max_branch_id: int | None = None
    gamma_m_values: list[float] = []
    f_mrdf_values: list[float] = []
    model_tau_values: list[float] = []
    model_secant_values: list[float] = []
    ref_secant_values: list[float] = []

    headers = [
        "step",
        "gamma",
        "tau_ref_kpa",
        "tau_model_kpa",
        "tau_backbone_kpa",
        "tau_error_kpa",
        "kt_exact_kpa",
        "secant_ref_g_over_gmax",
        "secant_model_g_over_gmax",
        "branch_id",
        "reason_code",
        "branch_kind",
        "gamma_m_global",
        "f_mrdf",
        "g_ref_kpa",
        "g_t_ref_kpa",
        "reload_factor",
        "direction",
    ]
    rows: list[list[object]] = []

    for idx, (gamma, tau_target) in enumerate(zip(ref_gamma, ref_tau, strict=True)):
        tau_model = state.update_stress(float(gamma))
        tau_predict, kt_exact, branch_id, reason_code, branch_state = state.peek_branch_response(float(gamma))
        tau_backbone = _element_backbone_stress(
            state.material,
            params,
            float(gamma),
            gmax_fallback=g0_kpa,
        )
        gamma_abs = abs(float(gamma))
        secant_ref = (
            abs(float(tau_target)) / max(gamma_abs * g0_kpa, 1.0e-12)
            if gamma_abs > 0.0
            else float("nan")
        )
        secant_model = (
            abs(float(tau_model)) / max(gamma_abs * g0_kpa, 1.0e-12)
            if gamma_abs > 0.0
            else float("nan")
        )
        if branch_id is not None:
            max_branch_id = branch_id if max_branch_id is None else max(max_branch_id, branch_id)
        if prev_branch_id is not None and branch_id is not None and branch_id != prev_branch_id:
            branch_switch_count += 1
        prev_branch_id = branch_id if branch_id is not None else prev_branch_id
        reason_counts[str(reason_code)] = reason_counts.get(str(reason_code), 0) + 1
        branch_kind = branch_state.branch_kind if branch_state is not None else "backbone"
        branch_kind_counts[branch_kind] = branch_kind_counts.get(branch_kind, 0) + 1
        gamma_m_global = float(branch_state.gamma_m_global) if branch_state is not None else float("nan")
        f_mrdf = float(branch_state.f_mrdf) if branch_state is not None else float("nan")
        g_ref = float(branch_state.g_ref) if branch_state is not None else float("nan")
        g_t_ref = float(branch_state.g_t_ref) if branch_state is not None else float("nan")
        reload_factor = float(branch_state.reload_factor) if branch_state is not None else float("nan")
        direction = int(branch_state.direction) if branch_state is not None else 0
        if np.isfinite(gamma_m_global):
            gamma_m_values.append(gamma_m_global)
        if np.isfinite(f_mrdf):
            f_mrdf_values.append(f_mrdf)
        model_tau_values.append(float(tau_model))
        model_secant_values.append(float(secant_model))
        ref_secant_values.append(float(secant_ref))
        rows.append(
            [
                idx,
                float(gamma),
                float(tau_target),
                float(tau_model),
                float(tau_backbone),
                float(tau_model - tau_target),
                float(kt_exact),
                float(secant_ref),
                float(secant_model),
                "" if branch_id is None else int(branch_id),
                int(reason_code),
                branch_kind,
                "" if not np.isfinite(gamma_m_global) else gamma_m_global,
                "" if not np.isfinite(f_mrdf) else f_mrdf,
                "" if not np.isfinite(g_ref) else g_ref,
                "" if not np.isfinite(g_t_ref) else g_t_ref,
                "" if not np.isfinite(reload_factor) else reload_factor,
                direction,
            ]
        )
        if not np.isfinite(tau_predict) or not np.isclose(tau_predict, tau_model, rtol=1.0e-8, atol=1.0e-8):
            raise ValueError("peek_branch_response and update_stress diverged during constitutive replay.")

    with replay_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)

    model_tau = np.asarray(model_tau_values, dtype=np.float64)
    ref_tau_arr = np.asarray(ref_tau, dtype=np.float64)
    ref_gamma_arr = np.asarray(ref_gamma, dtype=np.float64)
    stress_path_nrmse = _metric_nrmse(model_tau, ref_tau_arr)
    secant_path_nrmse = _metric_nrmse(
        np.asarray(model_secant_values, dtype=np.float64),
        np.asarray(ref_secant_values, dtype=np.float64),
    )
    model_gamma_peak = float(np.max(np.abs(ref_gamma_arr))) if ref_gamma_arr.size > 0 else 0.0
    ref_gamma_peak = float(np.max(np.abs(ref_gamma_arr))) if ref_gamma_arr.size > 0 else 0.0
    model_tau_peak = float(np.max(np.abs(model_tau))) if model_tau.size > 0 else 0.0
    ref_tau_peak = float(np.max(np.abs(ref_tau_arr))) if ref_tau_arr.size > 0 else 0.0
    gamma_peak_pct_diff = (
        float(100.0 * (model_gamma_peak - ref_gamma_peak) / ref_gamma_peak)
        if ref_gamma_peak > 0.0
        else None
    )
    tau_peak_pct_diff = (
        float(100.0 * (model_tau_peak - ref_tau_peak) / ref_tau_peak)
        if ref_tau_peak > 0.0
        else None
    )
    model_energy = float(abs(np.trapezoid(model_tau, ref_gamma_arr)))
    ref_energy = float(abs(np.trapezoid(ref_tau_arr, ref_gamma_arr)))
    loop_energy_pct_diff = (
        float(100.0 * (model_energy - ref_energy) / ref_energy)
        if ref_energy > 0.0
        else None
    )

    secant_envelope_nrmse: float | None
    try:
        gamma_env_ref, tau_env_ref = _monotonic_envelope(ref_gamma_arr, ref_tau_arr)
        gamma_env_model, tau_env_model = _monotonic_envelope(ref_gamma_arr, model_tau)
        gamma_lo = max(float(np.min(gamma_env_ref)), float(np.min(gamma_env_model)))
        gamma_hi = min(float(np.max(gamma_env_ref)), float(np.max(gamma_env_model)))
        if np.isfinite(gamma_lo) and np.isfinite(gamma_hi) and gamma_hi > gamma_lo:
            gamma_common = np.logspace(np.log10(gamma_lo), np.log10(gamma_hi), 48, dtype=np.float64)
            tau_env_ref_common = np.interp(gamma_common, gamma_env_ref, tau_env_ref).astype(np.float64)
            tau_env_model_common = np.interp(gamma_common, gamma_env_model, tau_env_model).astype(np.float64)
            secant_env_ref = tau_env_ref_common / np.maximum(gamma_common * g0_kpa, 1.0e-12)
            secant_env_model = tau_env_model_common / np.maximum(gamma_common * g0_kpa, 1.0e-12)
            secant_envelope_nrmse = _metric_nrmse(secant_env_model, secant_env_ref)
        else:
            secant_envelope_nrmse = None
    except ValueError:
        secant_envelope_nrmse = None

    summary = ConstitutiveReplaySummary(
        point_count=int(ref_gamma_arr.size),
        stress_path_nrmse=stress_path_nrmse,
        secant_path_nrmse=secant_path_nrmse,
        secant_envelope_nrmse=secant_envelope_nrmse,
        tau_peak_pct_diff=tau_peak_pct_diff,
        gamma_peak_pct_diff=gamma_peak_pct_diff,
        loop_energy_pct_diff=loop_energy_pct_diff,
        branch_switch_count=branch_switch_count,
        max_branch_id=max_branch_id,
        reason_counts=reason_counts,
        branch_kind_counts=branch_kind_counts,
        final_gamma_m_global=(gamma_m_values[-1] if gamma_m_values else None),
        max_gamma_m_global=(max(gamma_m_values) if gamma_m_values else None),
        f_mrdf_min=(min(f_mrdf_values) if f_mrdf_values else None),
        f_mrdf_max=(max(f_mrdf_values) if f_mrdf_values else None),
    )
    artifacts = ConstitutiveReplayArtifacts(
        output_dir=out_dir,
        replay_csv=replay_csv,
        summary_json=summary_json,
        reference_hysteresis_csv=reference_file,
    )
    result = ConstitutiveReplayResult(
        config_path=config_file,
        layer_index=layer_index,
        material=config.profile.layers[layer_index].material.value,
        g0_kpa=g0_kpa,
        mrdf_reference_mode_code=float(params.get("mrdf_reference_mode_code", 0.0)),
        artifacts=artifacts,
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


def replay_workbook_reference_hysteresis(
    config_path: str | Path,
    workbook_path: str | Path,
    output_dir: str | Path,
    *,
    layer_index: int = 0,
    mode_code_override: float | None = None,
) -> ConstitutiveReplayResult:
    out_dir = Path(output_dir)
    bundle_dir = out_dir / "_deepsoil_bundle"
    bundle = import_deepsoil_excel_bundle(workbook_path, bundle_dir)
    if bundle.hysteresis_csv is None:
        raise ValueError(f"Workbook did not produce a hysteresis CSV: {workbook_path}")
    return replay_reference_hysteresis(
        config_path,
        bundle.hysteresis_csv,
        out_dir,
        layer_index=layer_index,
        mode_code_override=mode_code_override,
    )


def run_solver_tangent_audit(
    config_path: str | Path,
    motion_csv: str | Path,
    output_dir: str | Path,
    *,
    layer_index: int = 0,
    mode_code_override: float | None = None,
) -> SolverTangentAuditResult:
    config_file = Path(config_path)
    motion_file = Path(motion_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_csv = out_dir / f"layer_{layer_index + 1}_tangent_audit.csv"
    summary_json = out_dir / f"layer_{layer_index + 1}_tangent_audit_summary.json"

    config = load_project_config(config_file)
    if mode_code_override is not None:
        for layer in config.profile.layers:
            layer.material_params["mrdf_reference_mode_code"] = float(mode_code_override)
    dt = config.analysis.dt or (1.0 / (20.0 * config.analysis.f_max))
    motion = load_motion(motion_file, dt=dt, unit=config.motion.units)
    solve_nonlinear_implicit_newmark(
        config,
        motion,
        _tangent_audit_layer=layer_index,
        _tangent_audit_path=audit_csv,
    )

    with audit_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    reason_counts: dict[str, int] = {}
    branch_kind_counts: dict[str, int] = {}
    branch_ids: list[int] = []
    gamma_values: list[float] = []
    tau_values: list[float] = []
    kt_values: list[float] = []
    gamma_m_values: list[float] = []
    f_values: list[float] = []
    g_ref_values: list[float] = []
    g_t_ref_values: list[float] = []

    for row in rows:
        reason = str(row.get("reason_code", ""))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        branch_kind = str(row.get("branch_kind", "") or "none")
        branch_kind_counts[branch_kind] = branch_kind_counts.get(branch_kind, 0) + 1
        branch_raw = row.get("branch_id", "").strip()
        if branch_raw:
            branch_ids.append(int(branch_raw))
        for raw, target in (
            (row.get("gamma", ""), gamma_values),
            (row.get("tau", ""), tau_values),
            (row.get("kt_exact", ""), kt_values),
            (row.get("gamma_m_global", ""), gamma_m_values),
            (row.get("f_mrdf", ""), f_values),
            (row.get("g_ref", ""), g_ref_values),
            (row.get("g_t_ref", ""), g_t_ref_values),
        ):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if np.isfinite(value):
                target.append(value)

    summary = SolverTangentAuditSummary(
        row_count=len(rows),
        max_branch_id=(max(branch_ids) if branch_ids else None),
        reason_counts=reason_counts,
        branch_kind_counts=branch_kind_counts,
        gamma_abs_max=(float(np.max(np.abs(gamma_values))) if gamma_values else None),
        tau_abs_max=(float(np.max(np.abs(tau_values))) if tau_values else None),
        kt_min_kpa=(float(np.min(kt_values)) if kt_values else None),
        kt_max_kpa=(float(np.max(kt_values)) if kt_values else None),
        gamma_m_global_max=(float(np.max(gamma_m_values)) if gamma_m_values else None),
        f_mrdf_min=(float(np.min(f_values)) if f_values else None),
        f_mrdf_max=(float(np.max(f_values)) if f_values else None),
        g_ref_min_kpa=(float(np.min(g_ref_values)) if g_ref_values else None),
        g_ref_max_kpa=(float(np.max(g_ref_values)) if g_ref_values else None),
        g_t_ref_min_kpa=(float(np.min(g_t_ref_values)) if g_t_ref_values else None),
        g_t_ref_max_kpa=(float(np.max(g_t_ref_values)) if g_t_ref_values else None),
    )
    result = SolverTangentAuditResult(
        config_path=config_file,
        motion_csv=motion_file,
        layer_index=layer_index,
        mrdf_reference_mode_code=float(
            config.profile.layers[layer_index].material_params.get("mrdf_reference_mode_code", 0.0)
        ),
        artifacts=SolverTangentAuditArtifacts(
            output_dir=out_dir,
            audit_csv=audit_csv,
            summary_json=summary_json,
            motion_csv=motion_file,
        ),
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


def run_elastic_boundary_force_audit(
    config_path: str | Path,
    motion_csv: str | Path,
    output_dir: str | Path,
    *,
    motion_input_type: str = "outcrop",
    bedrock_vs_m_s: float = 760.0,
    bedrock_unit_weight_kn_m3: float = 25.0,
    bedrock_damping_ratio: float = 0.02,
) -> ElasticBoundaryAuditResult:
    config_file = Path(config_path)
    motion_file = Path(motion_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_csv = out_dir / "elastic_boundary_force_audit.csv"
    summary_json = out_dir / "elastic_boundary_force_audit_summary.json"

    config = load_project_config(config_file)
    config.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    config.motion.input_type = str(motion_input_type)
    config.profile.bedrock = BedrockProperties(
        name="Audit halfspace",
        vs_m_s=float(bedrock_vs_m_s),
        unit_weight_kN_m3=float(bedrock_unit_weight_kn_m3),
        damping_ratio=float(bedrock_damping_ratio),
    )

    dt = config.analysis.dt or (1.0 / (20.0 * config.analysis.f_max))
    motion = load_motion(motion_file, dt=dt, unit=config.motion.units)
    solve_nonlinear_implicit_newmark(
        config,
        motion,
        _boundary_audit_path=audit_csv,
    )

    rows = _load_audit_rows(audit_csv)
    raw_input = np.asarray(motion.acc, dtype=np.float64)
    excitation = build_boundary_excitation(config, motion.acc)
    applied_input = np.asarray(
        excitation.applied_acceleration(config.boundary_condition),
        dtype=np.float64,
    )

    def _column(values: list[float]) -> tuple[float | None, float | None]:
        if not values:
            return None, None
        arr = np.asarray(values, dtype=np.float64)
        return float(np.max(np.abs(arr))), float(np.sqrt(np.mean(arr * arr)))

    incident = []
    dashpot = []
    net_force = []
    reconstructed_force = []
    assembled_force = []
    base_velocity = []
    base_disp = []
    surface_acc = []
    impedance = []
    for row in rows:
        for raw, target in (
            (row.get("incident_force"), incident),
            (row.get("dashpot_force"), dashpot),
            (row.get("net_boundary_force"), net_force),
            (row.get("reconstructed_net_boundary_force"), reconstructed_force),
            (row.get("assembled_boundary_force"), assembled_force),
            (row.get("base_relative_velocity_m_s"), base_velocity),
            (row.get("base_relative_displacement_m"), base_disp),
            (row.get("surface_acceleration_m_s2"), surface_acc),
            (row.get("impedance_c"), impedance),
        ):
            value = _parse_optional_float(raw)
            if value is not None:
                target.append(value)

    incident_abs_max, incident_rms = _column(incident)
    dashpot_abs_max, dashpot_rms = _column(dashpot)
    net_abs_max, net_rms = _column(net_force)
    reconstructed_abs_max, reconstructed_rms = _column(reconstructed_force)
    assembled_abs_max, assembled_rms = _column(assembled_force)
    base_vel_abs_max, _ = _column(base_velocity)
    base_disp_abs_max, _ = _column(base_disp)
    surface_abs_max, _ = _column(surface_acc)
    surface_std = (
        float(np.std(np.asarray(surface_acc, dtype=np.float64)))
        if surface_acc
        else None
    )
    dashpot_incident_corr = None
    if incident and dashpot and len(incident) == len(dashpot):
        inc_arr = np.asarray(incident, dtype=np.float64)
        dash_arr = np.asarray(dashpot, dtype=np.float64)
        if (
            inc_arr.size >= 2
            and float(np.std(inc_arr)) > 0.0
            and float(np.std(dash_arr)) > 0.0
        ):
            dashpot_incident_corr = float(np.corrcoef(inc_arr, dash_arr)[0, 1])
    assembled_vs_reconstructed_force_nrmse = None
    if assembled_force and reconstructed_force and len(assembled_force) == len(reconstructed_force):
        assembled_arr = np.asarray(assembled_force, dtype=np.float64)
        reconstructed_arr = np.asarray(reconstructed_force, dtype=np.float64)
        assembled_vs_reconstructed_force_nrmse = _metric_nrmse(
            assembled_arr,
            reconstructed_arr,
        )

    summary = ElasticBoundaryAuditSummary(
        row_count=len(rows),
        raw_input_pga_m_s2=(
            float(np.max(np.abs(raw_input))) if raw_input.size else None
        ),
        applied_input_pga_m_s2=(
            float(np.max(np.abs(applied_input))) if applied_input.size else None
        ),
        incident_force_abs_max=incident_abs_max,
        dashpot_force_abs_max=dashpot_abs_max,
        net_boundary_force_abs_max=net_abs_max,
        reconstructed_boundary_force_abs_max=reconstructed_abs_max,
        assembled_boundary_force_abs_max=assembled_abs_max,
        incident_force_rms=incident_rms,
        dashpot_force_rms=dashpot_rms,
        net_boundary_force_rms=net_rms,
        reconstructed_boundary_force_rms=reconstructed_rms,
        assembled_boundary_force_rms=assembled_rms,
        dashpot_to_incident_rms_ratio=(
            float(dashpot_rms / incident_rms)
            if incident_rms is not None and dashpot_rms is not None and incident_rms > 0.0
            else None
        ),
        net_to_incident_rms_ratio=(
            float(net_rms / incident_rms)
            if incident_rms is not None and net_rms is not None and incident_rms > 0.0
            else None
        ),
        dashpot_incident_corr=dashpot_incident_corr,
        assembled_vs_reconstructed_force_nrmse=assembled_vs_reconstructed_force_nrmse,
        base_relative_velocity_abs_max=base_vel_abs_max,
        base_relative_displacement_abs_max=base_disp_abs_max,
        surface_acc_abs_max=surface_abs_max,
        surface_acc_std_m_s2=surface_std,
        impedance_c=(
            float(np.max(np.asarray(impedance, dtype=np.float64))) if impedance else None
        ),
    )
    result = ElasticBoundaryAuditResult(
        config_path=config_file,
        motion_csv=motion_file,
        boundary_condition=str(config.boundary_condition),
        motion_input_type=str(config.motion.input_type),
        artifacts=ElasticBoundaryAuditArtifacts(
            output_dir=out_dir,
            audit_csv=audit_csv,
            summary_json=summary_json,
            motion_csv=motion_file,
        ),
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


def _load_audit_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _parse_optional_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return float(value) if np.isfinite(value) else None


def _dominant_fft_frequency(time_s: np.ndarray, signal: np.ndarray) -> tuple[float | None, float | None]:
    if time_s.size < 2 or signal.size != time_s.size:
        return None, None
    dt = float(np.median(np.diff(time_s)))
    if not np.isfinite(dt) or dt <= 0.0:
        return None, None
    centered = _detrend_signal(time_s, signal)
    if not np.any(np.isfinite(centered)) or float(np.std(centered)) <= 0.0:
        return None, None
    freq = np.fft.rfftfreq(centered.size, d=dt)
    spec = np.fft.rfft(centered)
    if freq.size <= 1:
        return None, None
    amp = np.abs(spec)
    amp[0] = 0.0
    idx = int(np.argmax(amp))
    dom_freq = float(freq[idx])
    if not np.isfinite(dom_freq) or dom_freq <= 0.0:
        return None, None
    return dom_freq, float(1.0 / dom_freq)


def _fft_amplitude_phase_at_frequency(
    time_s: np.ndarray,
    signal: np.ndarray,
    target_frequency_hz: float,
) -> tuple[float | None, float | None]:
    if (
        time_s.size < 2
        or signal.size != time_s.size
        or not np.isfinite(target_frequency_hz)
        or target_frequency_hz <= 0.0
    ):
        return None, None
    dt = float(np.median(np.diff(time_s)))
    if not np.isfinite(dt) or dt <= 0.0:
        return None, None
    centered = _detrend_signal(time_s, signal)
    if not np.any(np.isfinite(centered)):
        return None, None
    freq = np.fft.rfftfreq(centered.size, d=dt)
    spec = np.fft.rfft(centered)
    if freq.size == 0:
        return None, None
    idx = int(np.argmin(np.abs(freq - target_frequency_hz)))
    amplitude = float(np.abs(spec[idx]))
    phase_deg = float(np.degrees(np.angle(spec[idx])))
    return amplitude, phase_deg


def _wrap_phase_deg(phase_deg: float | None) -> float | None:
    if phase_deg is None or not np.isfinite(phase_deg):
        return None
    wrapped = ((float(phase_deg) + 180.0) % 360.0) - 180.0
    return float(wrapped)


def _detrend_signal(time_s: np.ndarray, signal: np.ndarray) -> np.ndarray:
    values = np.asarray(signal, dtype=np.float64)
    times = np.asarray(time_s, dtype=np.float64)
    if values.size != times.size or values.size == 0:
        return values.astype(np.float64)
    centered = values - float(np.mean(values))
    if values.size < 3:
        return centered.astype(np.float64)
    t0 = times - float(np.mean(times))
    try:
        slope, intercept = np.polyfit(t0, centered, 1)
    except (TypeError, np.linalg.LinAlgError, ValueError):
        return centered.astype(np.float64)
    trend = slope * t0 + intercept
    return (centered - trend).astype(np.float64)


def analyze_elastic_boundary_force_audit(
    audit_csv: str | Path,
    output_dir: str | Path,
) -> ElasticBoundaryFrequencyAuditResult:
    audit_file = Path(audit_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "elastic_boundary_frequency_audit_summary.json"
    summary_md = out_dir / "elastic_boundary_frequency_audit_summary.md"

    rows = _load_audit_rows(audit_file)
    time_vals: list[float] = []
    incident_vals: list[float] = []
    net_vals: list[float] = []
    surface_vals: list[float] = []
    for row in rows:
        time_v = _parse_optional_float(row.get("time_s"))
        incident_v = _parse_optional_float(row.get("incident_force"))
        net_v = _parse_optional_float(row.get("net_boundary_force"))
        surface_v = _parse_optional_float(row.get("surface_acceleration_m_s2"))
        if None in {time_v, incident_v, net_v, surface_v}:
            continue
        time_vals.append(float(time_v))
        incident_vals.append(float(incident_v))
        net_vals.append(float(net_v))
        surface_vals.append(float(surface_v))

    time_arr = np.asarray(time_vals, dtype=np.float64)
    incident_arr = np.asarray(incident_vals, dtype=np.float64)
    net_arr = np.asarray(net_vals, dtype=np.float64)
    surface_arr = np.asarray(surface_vals, dtype=np.float64)
    dt_s = (
        float(np.median(np.diff(time_arr)))
        if time_arr.size >= 2 and np.all(np.isfinite(np.diff(time_arr)))
        else None
    )

    surface_freq, surface_period = _dominant_fft_frequency(time_arr, surface_arr)
    net_freq, net_period = _dominant_fft_frequency(time_arr, net_arr)
    incident_freq, incident_period = _dominant_fft_frequency(time_arr, incident_arr)

    surface_amp, surface_phase = _fft_amplitude_phase_at_frequency(
        time_arr, surface_arr, surface_freq if surface_freq is not None else float("nan")
    )
    net_amp, net_phase = _fft_amplitude_phase_at_frequency(
        time_arr, net_arr, surface_freq if surface_freq is not None else float("nan")
    )
    incident_amp, incident_phase = _fft_amplitude_phase_at_frequency(
        time_arr, incident_arr, surface_freq if surface_freq is not None else float("nan")
    )

    summary = ElasticBoundaryFrequencyAuditSummary(
        row_count=int(time_arr.size),
        dt_s=dt_s,
        dominant_surface_frequency_hz=surface_freq,
        dominant_surface_period_s=surface_period,
        dominant_net_force_frequency_hz=net_freq,
        dominant_net_force_period_s=net_period,
        dominant_incident_force_frequency_hz=incident_freq,
        dominant_incident_force_period_s=incident_period,
        net_to_incident_amplitude_ratio_at_surface_peak=(
            float(net_amp / incident_amp)
            if net_amp is not None and incident_amp is not None and incident_amp > 0.0
            else None
        ),
        net_to_surface_amplitude_ratio_at_surface_peak=(
            float(net_amp / surface_amp)
            if net_amp is not None and surface_amp is not None and surface_amp > 0.0
            else None
        ),
        incident_to_surface_amplitude_ratio_at_surface_peak=(
            float(incident_amp / surface_amp)
            if incident_amp is not None and surface_amp is not None and surface_amp > 0.0
            else None
        ),
        net_surface_phase_diff_deg_at_surface_peak=(
            _wrap_phase_deg(net_phase - surface_phase)
            if net_phase is not None and surface_phase is not None
            else None
        ),
        incident_surface_phase_diff_deg_at_surface_peak=(
            _wrap_phase_deg(incident_phase - surface_phase)
            if incident_phase is not None and surface_phase is not None
            else None
        ),
        net_incident_phase_diff_deg_at_surface_peak=(
            _wrap_phase_deg(net_phase - incident_phase)
            if net_phase is not None and incident_phase is not None
            else None
        ),
    )
    result = ElasticBoundaryFrequencyAuditResult(
        source_audit_csv=audit_file,
        artifacts=ElasticBoundaryFrequencyAuditArtifacts(
            output_dir=out_dir,
            summary_json=summary_json,
            summary_md=summary_md,
            source_audit_csv=audit_file,
        ),
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    lines = [
        "# Elastic Boundary Frequency Audit",
        "",
        f"- Source audit: `{audit_file}`",
        "",
        "## Summary",
        f"- row count: `{summary.row_count}`",
        f"- dt: `{summary.dt_s}` s",
        f"- dominant surface frequency: `{summary.dominant_surface_frequency_hz}` Hz",
        f"- dominant surface period: `{summary.dominant_surface_period_s}` s",
        f"- dominant net-force frequency: `{summary.dominant_net_force_frequency_hz}` Hz",
        f"- dominant net-force period: `{summary.dominant_net_force_period_s}` s",
        f"- dominant incident-force frequency: `{summary.dominant_incident_force_frequency_hz}` Hz",
        f"- dominant incident-force period: `{summary.dominant_incident_force_period_s}` s",
        f"- net / incident amplitude ratio at surface peak: `{summary.net_to_incident_amplitude_ratio_at_surface_peak}`",
        f"- net / surface amplitude ratio at surface peak: `{summary.net_to_surface_amplitude_ratio_at_surface_peak}`",
        f"- incident / surface amplitude ratio at surface peak: `{summary.incident_to_surface_amplitude_ratio_at_surface_peak}`",
        f"- net - surface phase diff at surface peak: `{summary.net_surface_phase_diff_deg_at_surface_peak}` deg",
        f"- incident - surface phase diff at surface peak: `{summary.incident_surface_phase_diff_deg_at_surface_peak}` deg",
        f"- net - incident phase diff at surface peak: `{summary.net_incident_phase_diff_deg_at_surface_peak}` deg",
    ]
    summary_md.write_text("\n".join(lines), encoding="utf-8")
    return result


def run_solver_layer_sweep_audit(
    config_path: str | Path,
    motion_csv: str | Path,
    output_dir: str | Path,
    *,
    mode_code_override: float | None = None,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> LayerSweepAuditResult:
    config_file = Path(config_path)
    motion_file = Path(motion_csv)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_csv = out_dir / "all_layers_tangent_audit.csv"
    summary_json = out_dir / "all_layers_tangent_audit_summary.json"
    layer_summary_csv = out_dir / "layer_compliance_summary.csv"

    config = load_project_config(config_file)
    if mode_code_override is not None:
        for layer in config.profile.layers:
            layer.material_params["mrdf_reference_mode_code"] = float(mode_code_override)
    dt = config.analysis.dt or (1.0 / (20.0 * config.analysis.f_max))
    motion = load_motion(motion_file, dt=dt, unit=config.motion.units)
    solve_nonlinear_implicit_newmark(
        config,
        motion,
        points_per_wavelength=points_per_wavelength,
        min_dz_m=min_dz_m,
        _tangent_audit_path=audit_csv,
    )

    rows = _load_audit_rows(audit_csv)
    layer_slices = build_layer_slices(
        config,
        points_per_wavelength=points_per_wavelength,
        min_dz_m=min_dz_m,
    )
    element_slices = build_element_slices(layer_slices)
    area = 1.0
    element_meta = {
        elem.index - 1: {
            "profile_layer_index": elem.layer_index,
            "profile_layer_name": elem.layer_name,
            "dz_m": float(elem.dz_m),
        }
        for elem in element_slices
    }

    per_layer_values: dict[int, dict[str, object]] = {}
    per_state_entries: dict[tuple[int, int], list[tuple[int, float]]] = {}
    equivalent_stiffness_values: list[float] = []

    def _layer_bucket(profile_layer_index: int, profile_layer_name: str) -> dict[str, object]:
        bucket = per_layer_values.get(profile_layer_index)
        if bucket is None:
            bucket = {
                "profile_layer_name": profile_layer_name,
                "element_ids": set(),
                "compliance_fractions": [],
                "kt_values": [],
                "gamma_values": [],
                "tau_values": [],
                "gamma_m_values": [],
                "f_values": [],
                "g_ref_values": [],
                "g_t_ref_values": [],
                "reason_counts": {},
                "branch_kind_counts": {},
            }
            per_layer_values[profile_layer_index] = bucket
        return bucket

    for row in rows:
        elem_idx_raw = row.get("layer_index", "")
        try:
            elem_idx = int(elem_idx_raw)
        except ValueError:
            continue
        meta = element_meta.get(elem_idx)
        if meta is None:
            continue
        profile_layer_index = int(meta["profile_layer_index"])
        profile_layer_name = str(meta["profile_layer_name"])
        bucket = _layer_bucket(profile_layer_index, profile_layer_name)
        bucket["element_ids"].add(elem_idx)

        step = int(row.get("step", "-1"))
        substep = int(row.get("substep", "-1"))
        kt_exact = _parse_optional_float(row.get("kt_exact"))
        if kt_exact is not None:
            bucket["kt_values"].append(kt_exact)
            dz_m = float(meta["dz_m"])
            k_elem = max(kt_exact * area / max(dz_m, 1.0e-12), 1.0e-12)
            per_state_entries.setdefault((step, substep), []).append((elem_idx, k_elem))
        for key, target in (
            ("gamma", bucket["gamma_values"]),
            ("tau", bucket["tau_values"]),
            ("gamma_m_global", bucket["gamma_m_values"]),
            ("f_mrdf", bucket["f_values"]),
            ("g_ref", bucket["g_ref_values"]),
            ("g_t_ref", bucket["g_t_ref_values"]),
        ):
            value = _parse_optional_float(row.get(key))
            if value is not None:
                target.append(value)
        reason = str(row.get("reason_code", "")).strip()
        if reason:
            counts = bucket["reason_counts"]
            counts[reason] = counts.get(reason, 0) + 1
        branch_kind = str(row.get("branch_kind", "") or "none").strip()
        counts = bucket["branch_kind_counts"]
        counts[branch_kind] = counts.get(branch_kind, 0) + 1

    for _, entries in per_state_entries.items():
        total_compliance = 0.0
        compliance_by_elem: list[tuple[int, float]] = []
        for elem_idx, k_elem in entries:
            compliance = 1.0 / max(k_elem, 1.0e-12)
            compliance_by_elem.append((elem_idx, compliance))
            total_compliance += compliance
        if total_compliance <= 0.0:
            continue
        equivalent_stiffness_values.append(1.0 / total_compliance)
        layer_fraction_by_state: dict[int, float] = {}
        for elem_idx, compliance in compliance_by_elem:
            meta = element_meta[elem_idx]
            profile_layer_index = int(meta["profile_layer_index"])
            layer_fraction_by_state[profile_layer_index] = (
                layer_fraction_by_state.get(profile_layer_index, 0.0)
                + (compliance / total_compliance)
            )
        for profile_layer_index, fraction in layer_fraction_by_state.items():
            bucket = per_layer_values[profile_layer_index]
            bucket["compliance_fractions"].append(float(fraction))

    layer_rows: list[LayerComplianceContribution] = []
    for profile_layer_index in sorted(per_layer_values):
        bucket = per_layer_values[profile_layer_index]
        compliance_fractions = list(bucket["compliance_fractions"])
        kt_values = list(bucket["kt_values"])
        gamma_values = list(bucket["gamma_values"])
        tau_values = list(bucket["tau_values"])
        gamma_m_values = list(bucket["gamma_m_values"])
        f_values = list(bucket["f_values"])
        g_ref_values = list(bucket["g_ref_values"])
        g_t_ref_values = list(bucket["g_t_ref_values"])
        layer_rows.append(
            LayerComplianceContribution(
                profile_layer_index=profile_layer_index,
                profile_layer_name=str(bucket["profile_layer_name"]),
                element_count=len(bucket["element_ids"]),
                mean_compliance_fraction=(
                    float(np.mean(compliance_fractions)) if compliance_fractions else None
                ),
                max_compliance_fraction=(
                    float(np.max(compliance_fractions)) if compliance_fractions else None
                ),
                mean_kt_kpa=(float(np.mean(kt_values)) if kt_values else None),
                min_kt_kpa=(float(np.min(kt_values)) if kt_values else None),
                max_kt_kpa=(float(np.max(kt_values)) if kt_values else None),
                gamma_abs_max=(float(np.max(np.abs(gamma_values))) if gamma_values else None),
                tau_abs_max=(float(np.max(np.abs(tau_values))) if tau_values else None),
                gamma_m_global_max=(float(np.max(gamma_m_values)) if gamma_m_values else None),
                f_mrdf_min=(float(np.min(f_values)) if f_values else None),
                f_mrdf_max=(float(np.max(f_values)) if f_values else None),
                g_ref_min_kpa=(float(np.min(g_ref_values)) if g_ref_values else None),
                g_ref_max_kpa=(float(np.max(g_ref_values)) if g_ref_values else None),
                g_t_ref_min_kpa=(float(np.min(g_t_ref_values)) if g_t_ref_values else None),
                g_t_ref_max_kpa=(float(np.max(g_t_ref_values)) if g_t_ref_values else None),
                reason_counts=dict(bucket["reason_counts"]),
                branch_kind_counts=dict(bucket["branch_kind_counts"]),
            )
        )

    dominant_layer = None
    dominant_fraction = None
    if layer_rows:
        dominant = max(
            layer_rows,
            key=lambda row: row.mean_compliance_fraction if row.mean_compliance_fraction is not None else float("-inf"),
        )
        dominant_layer = dominant.profile_layer_index
        dominant_fraction = dominant.mean_compliance_fraction

    with layer_summary_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "profile_layer_index",
                "profile_layer_name",
                "element_count",
                "mean_compliance_fraction",
                "max_compliance_fraction",
                "mean_kt_kpa",
                "min_kt_kpa",
                "max_kt_kpa",
                "gamma_abs_max",
                "tau_abs_max",
                "gamma_m_global_max",
                "f_mrdf_min",
                "f_mrdf_max",
                "g_ref_min_kpa",
                "g_ref_max_kpa",
                "g_t_ref_min_kpa",
                "g_t_ref_max_kpa",
                "reason_counts",
                "branch_kind_counts",
            ]
        )
        for row in layer_rows:
            writer.writerow(
                [
                    row.profile_layer_index,
                    row.profile_layer_name,
                    row.element_count,
                    row.mean_compliance_fraction,
                    row.max_compliance_fraction,
                    row.mean_kt_kpa,
                    row.min_kt_kpa,
                    row.max_kt_kpa,
                    row.gamma_abs_max,
                    row.tau_abs_max,
                    row.gamma_m_global_max,
                    row.f_mrdf_min,
                    row.f_mrdf_max,
                    row.g_ref_min_kpa,
                    row.g_ref_max_kpa,
                    row.g_t_ref_min_kpa,
                    row.g_t_ref_max_kpa,
                    json.dumps(row.reason_counts, ensure_ascii=True, sort_keys=True),
                    json.dumps(row.branch_kind_counts, ensure_ascii=True, sort_keys=True),
                ]
            )

    result = LayerSweepAuditResult(
        config_path=config_file,
        motion_csv=motion_file,
        mrdf_reference_mode_code=float(
            config.profile.layers[0].material_params.get("mrdf_reference_mode_code", 0.0)
        ),
        artifacts=LayerSweepAuditArtifacts(
            output_dir=out_dir,
            audit_csv=audit_csv,
            summary_json=summary_json,
            layer_summary_csv=layer_summary_csv,
            motion_csv=motion_file,
        ),
        summary=LayerSweepAuditSummary(
            row_count=len(rows),
            state_count=len(per_state_entries),
            equivalent_stiffness_min=(
                float(np.min(equivalent_stiffness_values)) if equivalent_stiffness_values else None
            ),
            equivalent_stiffness_max=(
                float(np.max(equivalent_stiffness_values)) if equivalent_stiffness_values else None
            ),
            dominant_layer_by_mean_compliance=dominant_layer,
            dominant_layer_mean_compliance=dominant_fraction,
            layers=layer_rows,
        ),
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


@dataclass(slots=True)
class BoundarySensitivityArtifacts:
    output_dir: Path
    summary_json: Path
    summary_md: Path
    layer_delta_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "summary_json": str(self.summary_json),
            "summary_md": str(self.summary_md),
            "layer_delta_csv": str(self.layer_delta_csv),
        }


@dataclass(slots=True)
class BoundarySensitivityConfigSummary:
    project_name_a: str
    project_name_b: str
    solver_backend_a: str
    solver_backend_b: str
    boundary_condition_a: str
    boundary_condition_b: str
    motion_input_type_a: str
    motion_input_type_b: str
    damping_mode_a: str
    damping_mode_b: str
    same_project_name: bool | None
    same_solver_backend: bool | None
    same_damping_mode: bool | None
    same_layer_count: bool | None
    same_upper_layers: bool | None
    last_layer_changed: bool | None
    bedrock_changed: bool | None
    only_last_layer_or_boundary_changed: bool | None
    upper_layer_count: int


@dataclass(slots=True)
class BoundarySensitivitySummary:
    run_a_id: str
    run_b_id: str
    label_a: str
    label_b: str
    config: BoundarySensitivityConfigSummary
    raw_input_history_nrmse: float | None
    raw_input_psa_nrmse: float | None
    applied_input_history_nrmse: float | None
    applied_input_psa_nrmse: float | None
    surface_history_nrmse: float | None
    surface_history_corrcoef: float | None
    input_pga_g_a: float | None
    input_pga_g_b: float | None
    input_psa_peak_g_a: float | None
    input_psa_peak_g_b: float | None
    surface_pga_g_a: float | None
    surface_pga_g_b: float | None
    surface_pga_ratio_b_over_a: float | None
    surface_pgd_m_a: float | None
    surface_pgd_m_b: float | None
    surface_pgd_ratio_b_over_a: float | None
    surface_psa_nrmse: float | None
    surface_psa_peak_g_a: float | None
    surface_psa_peak_g_b: float | None
    surface_psa_peak_ratio_b_over_a: float | None
    surface_to_input_pga_amp_a: float | None
    surface_to_input_pga_amp_b: float | None
    surface_to_input_peak_psa_amp_a: float | None
    surface_to_input_peak_psa_amp_b: float | None
    surface_peak_period_s_a: float | None
    surface_peak_period_s_b: float | None
    surface_peak_period_shift_pct_b_vs_a: float | None
    profile_depth_points: int
    gamma_max_nrmse: float | None
    pga_profile_nrmse: float | None
    max_displacement_nrmse: float | None
    max_strain_nrmse: float | None
    max_stress_ratio_nrmse: float | None
    effective_stress_nrmse: float | None
    tau_peak_nrmse: float | None
    secant_g_over_gmax_nrmse: float | None
    warnings: list[str]


@dataclass(slots=True)
class BoundarySensitivityResult:
    run_a_dir: Path
    run_b_dir: Path
    artifacts: BoundarySensitivityArtifacts
    summary: BoundarySensitivitySummary

    def to_dict(self) -> dict[str, object]:
        return {
            "run_a_dir": str(self.run_a_dir),
            "run_b_dir": str(self.run_b_dir),
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class BoundaryDeltaComparisonArtifacts:
    output_dir: Path
    summary_json: Path
    summary_md: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "summary_json": str(self.summary_json),
            "summary_md": str(self.summary_md),
        }


@dataclass(slots=True)
class BoundaryDeltaComparisonSummary:
    reference_label: str
    candidate_label: str
    reference_peak_ratio: float | None
    candidate_peak_ratio: float | None
    peak_ratio_delta: float | None
    peak_ratio_abs_rel_error: float | None
    reference_peak_period_shift_pct: float | None
    candidate_peak_period_shift_pct: float | None
    peak_period_shift_delta_pct: float | None
    peak_period_shift_abs_rel_error: float | None
    reference_surface_pga_ratio: float | None
    candidate_surface_pga_ratio: float | None
    surface_pga_ratio_delta: float | None
    surface_pga_ratio_abs_rel_error: float | None
    reference_surface_pgd_ratio: float | None
    candidate_surface_pgd_ratio: float | None
    surface_pgd_ratio_delta: float | None
    surface_pgd_ratio_abs_rel_error: float | None
    direction_match_peak_ratio: bool | None
    direction_match_peak_period: bool | None
    direction_match_surface_pga: bool | None
    direction_match_surface_pgd: bool | None
    directional_gate_passed: bool | None
    mean_abs_rel_error: float | None
    worst_metric_by_abs_rel_error: str | None


@dataclass(slots=True)
class BoundaryDeltaComparisonResult:
    reference_source: Path
    candidate_source: Path
    artifacts: BoundaryDeltaComparisonArtifacts
    summary: BoundaryDeltaComparisonSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "reference_source": str(self.reference_source),
            "candidate_source": str(self.candidate_source),
            "artifacts": self.artifacts.to_dict(),
            "summary": asdict(self.summary),
        }


@dataclass(slots=True)
class CaseTruthLayerAuditArtifacts:
    output_dir: Path
    summary_json: Path
    summary_md: Path
    layer_csv: Path
    motion_csv: Path
    layer_sweep_summary_json: Path
    layer_sweep_summary_csv: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "output_dir": str(self.output_dir),
            "summary_json": str(self.summary_json),
            "summary_md": str(self.summary_md),
            "layer_csv": str(self.layer_csv),
            "motion_csv": str(self.motion_csv),
            "layer_sweep_summary_json": str(self.layer_sweep_summary_json),
            "layer_sweep_summary_csv": str(self.layer_sweep_summary_csv),
        }


@dataclass(slots=True)
class CaseTruthLayerAuditRow:
    profile_layer_index: int
    depth_m: float
    geowave_gamma_max: float | None
    deepsoil_gamma_max: float | None
    gamma_max_ratio_geo_over_ref: float | None
    geowave_pga_g: float | None
    deepsoil_pga_g: float | None
    pga_g_ratio_geo_over_ref: float | None
    geowave_max_displacement_m: float | None
    deepsoil_max_displacement_m: float | None
    max_displacement_ratio_geo_over_ref: float | None
    geowave_max_strain_pct: float | None
    deepsoil_max_strain_pct: float | None
    max_strain_ratio_geo_over_ref: float | None
    geowave_max_stress_ratio: float | None
    deepsoil_max_stress_ratio: float | None
    max_stress_ratio_geo_over_ref: float | None
    geowave_effective_stress_kpa: float | None
    deepsoil_effective_stress_kpa: float | None
    effective_stress_ratio_geo_over_ref: float | None
    geowave_stress_proxy_kpa: float | None
    deepsoil_stress_proxy_kpa: float | None
    stress_proxy_ratio_geo_over_ref: float | None
    geowave_secant_proxy_kpa: float | None
    deepsoil_secant_proxy_kpa: float | None
    secant_proxy_ratio_geo_over_ref: float | None
    tau_peak_proxy_ratio_geo_over_ref: float | None
    mean_kt_ratio_geo_over_ref_secant: float | None
    min_kt_ratio_geo_over_ref_secant: float | None
    mean_compliance_fraction: float | None
    max_compliance_fraction: float | None
    mean_kt_kpa: float | None
    min_kt_kpa: float | None
    max_kt_kpa: float | None
    gamma_abs_max: float | None
    tau_abs_max: float | None
    gamma_m_global_max: float | None
    f_mrdf_min: float | None
    f_mrdf_max: float | None
    g_ref_min_kpa: float | None
    g_ref_max_kpa: float | None
    g_t_ref_min_kpa: float | None
    g_t_ref_max_kpa: float | None
    reason_counts: dict[str, int]
    branch_kind_counts: dict[str, int]


@dataclass(slots=True)
class CaseTruthLayerAuditSummary:
    label: str
    layer_count: int
    gamma_max_nrmse: float | None
    pga_profile_nrmse: float | None
    max_displacement_nrmse: float | None
    max_strain_nrmse: float | None
    max_stress_ratio_nrmse: float | None
    effective_stress_nrmse: float | None
    stress_proxy_nrmse: float | None
    secant_proxy_nrmse: float | None
    gamma_max_mean_ratio_geo_over_ref: float | None
    pga_profile_mean_ratio_geo_over_ref: float | None
    max_displacement_mean_ratio_geo_over_ref: float | None
    max_strain_mean_ratio_geo_over_ref: float | None
    max_stress_ratio_mean_ratio_geo_over_ref: float | None
    effective_stress_mean_ratio_geo_over_ref: float | None
    stress_proxy_mean_ratio_geo_over_ref: float | None
    secant_proxy_mean_ratio_geo_over_ref: float | None
    tau_peak_proxy_mean_ratio_geo_over_ref: float | None
    mean_kt_ratio_geo_over_ref_secant_mean: float | None
    min_kt_ratio_geo_over_ref_secant_mean: float | None
    worst_layer_by_mean_kt_ratio_geo_over_ref_secant: int | None
    worst_layer_mean_kt_ratio_geo_over_ref_secant: float | None
    equivalent_stiffness_min: float | None
    equivalent_stiffness_max: float | None
    dominant_layer_by_mean_compliance: int | None
    dominant_layer_mean_compliance: float | None
    warnings: list[str]
    layers: list[CaseTruthLayerAuditRow]


@dataclass(slots=True)
class CaseTruthLayerAuditResult:
    geowave_run_dir: Path
    deepsoil_db_path: Path
    artifacts: CaseTruthLayerAuditArtifacts
    summary: CaseTruthLayerAuditSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "geowave_run_dir": str(self.geowave_run_dir),
            "deepsoil_db_path": str(self.deepsoil_db_path),
            "artifacts": self.artifacts.to_dict(),
            "summary": {
                **asdict(self.summary),
                "layers": [asdict(layer) for layer in self.summary.layers],
            },
        }


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if not np.isfinite(numerator) or not np.isfinite(denominator) or abs(denominator) <= 1.0e-20:
        return None
    return float(numerator / denominator)


def _safe_pct_shift(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None:
        return None
    if not np.isfinite(current) or not np.isfinite(baseline) or abs(baseline) <= 1.0e-20:
        return None
    return float(100.0 * (current - baseline) / baseline)


def _safe_abs_rel_error(reference: float | None, candidate: float | None) -> float | None:
    if reference is None or candidate is None:
        return None
    if not np.isfinite(reference) or not np.isfinite(candidate) or abs(reference) <= 1.0e-20:
        return None
    return float(abs(candidate - reference) / abs(reference))


@dataclass(slots=True)
class _DeepSoilBoundaryCase:
    run_dir: Path
    db_path: Path
    project_name: str
    solver_backend: str
    boundary_condition: str
    motion_input_type: str
    damping_mode: str
    time: np.ndarray
    dt_s: float
    input_time: np.ndarray
    input_dt_s: float
    acc_surface: np.ndarray
    acc_input: np.ndarray
    acc_applied_input: np.ndarray
    profile: dict[str, np.ndarray]
    surface_pgd_m: float | None


def _parse_deepsoil_input_blob(
    payload: bytes | str | None,
) -> tuple[float | None, np.ndarray, str | None]:
    if payload is None:
        return None, np.array([], dtype=np.float64), None
    text = payload.decode("utf-8", errors="ignore") if isinstance(payload, bytes) else str(payload)
    dt_match = re.search(r"\[TIME_STEP\]:\[(.*?)\]", text)
    dt_value = float(dt_match.group(1)) if dt_match is not None else None
    accel_values = [float(match) for match in re.findall(r"\[ACCEL\]:\[(.*?)\]", text)]
    halfspace_match = re.search(r"\[HALFSPACE\]:\[(.*?)\]", text)
    halfspace_value = halfspace_match.group(1).strip().lower() if halfspace_match is not None else None
    return dt_value, np.asarray(accel_values, dtype=np.float64), halfspace_value


def _load_deepsoil_db_profile(
    conn: sqlite3.Connection,
) -> tuple[dict[str, np.ndarray], float | None]:
    rows = conn.execute(
        "SELECT DEPTH_LAYER_MID, PGA_TOTAL, MIN_DISP_RELATIVE, MAX_DISP_RELATIVE, "
        "INITIAL_EFFECTIVE_STRESS, MAX_STRAIN, MAX_STRESS_RATIO "
        "FROM PROFILES ORDER BY DEPTH_LAYER_MID ASC"
    ).fetchall()
    if not rows:
        empty = np.array([], dtype=np.float64)
        return {
            "depth_m": empty,
            "gamma_max": empty,
            "pga_g": empty,
            "max_displacement_m": empty,
            "max_strain_pct": empty,
            "max_stress_ratio": empty,
            "effective_stress_kpa": empty,
            "tau_peak_kpa": empty,
            "secant_g_over_gmax": empty,
        }, None

    depth_m: list[float] = []
    gamma_max: list[float] = []
    pga_g: list[float] = []
    max_displacement_m: list[float] = []
    max_strain_pct: list[float] = []
    max_stress_ratio: list[float] = []
    effective_stress_kpa: list[float] = []
    for depth, pga_total, min_disp, max_disp, sigma_eff, strain_pct, stress_ratio in rows:
        depth_m.append(float(depth))
        pga_g.append(float(pga_total))
        max_displacement_m.append(float(max(abs(float(min_disp)), abs(float(max_disp)))))
        max_strain_pct.append(float(strain_pct))
        gamma_max.append(float(strain_pct) / 100.0)
        max_stress_ratio.append(float(stress_ratio))
        effective_stress_kpa.append(float(sigma_eff))

    surface_pgd_m = float(max_displacement_m[0]) if max_displacement_m else None
    nan_column = np.full(len(depth_m), np.nan, dtype=np.float64)
    return {
        "depth_m": np.asarray(depth_m, dtype=np.float64),
        "gamma_max": np.asarray(gamma_max, dtype=np.float64),
        "pga_g": np.asarray(pga_g, dtype=np.float64),
        "max_displacement_m": np.asarray(max_displacement_m, dtype=np.float64),
        "max_strain_pct": np.asarray(max_strain_pct, dtype=np.float64),
        "max_stress_ratio": np.asarray(max_stress_ratio, dtype=np.float64),
        "effective_stress_kpa": np.asarray(effective_stress_kpa, dtype=np.float64),
        "tau_peak_kpa": nan_column.copy(),
        "secant_g_over_gmax": nan_column.copy(),
    }, surface_pgd_m


def _load_deepsoil_db_case(
    run_dir: str | Path,
    *,
    boundary_condition: str,
    motion_input_type: str,
    solver_backend: str = "nonlinear",
    damping_mode: str = "frequency_independent",
) -> _DeepSoilBoundaryCase:
    run_path = Path(run_dir)
    db_path = run_path if run_path.suffix.lower() == ".db3" else (run_path / "deepsoilout.db3")
    if not db_path.exists():
        raise FileNotFoundError(f"DeepSoil DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        th_rows = conn.execute(
            "SELECT TIME, LAYER1_ACCEL, LAYER1_DISP FROM TIME_HISTORIES ORDER BY TIME ASC"
        ).fetchall()
        input_row = conn.execute("SELECT INPUT FROM INPUT LIMIT 1").fetchone()
        profile, surface_pgd_m = _load_deepsoil_db_profile(conn)
    finally:
        conn.close()

    if not th_rows:
        raise ValueError(f"TIME_HISTORIES is empty in DeepSoil DB: {db_path}")

    time = np.asarray([float(row[0]) for row in th_rows], dtype=np.float64)
    dt_s = (
        float(np.median(np.diff(time)))
        if time.size >= 2 and np.all(np.isfinite(np.diff(time)))
        else 0.0
    )
    acc_surface = 9.81 * np.asarray([float(row[1]) for row in th_rows], dtype=np.float64)
    disp_surface = np.asarray([float(row[2]) for row in th_rows], dtype=np.float64)
    if surface_pgd_m is None and disp_surface.size > 0:
        surface_pgd_m = float(np.max(np.abs(disp_surface)))

    input_dt_s, input_acc_g, parsed_halfspace = _parse_deepsoil_input_blob(
        input_row[0] if input_row is not None else None
    )
    if input_dt_s is None:
        input_dt_s = dt_s
    input_time = np.arange(input_acc_g.size, dtype=np.float64) * float(input_dt_s)
    acc_input = 9.81 * np.asarray(input_acc_g, dtype=np.float64)
    acc_applied_input = acc_input.copy()

    project_name = f"deepsoil_db_{run_path.name}"
    if parsed_halfspace:
        project_name = f"{project_name}_{parsed_halfspace}"

    return _DeepSoilBoundaryCase(
        run_dir=run_path,
        db_path=db_path,
        project_name=project_name,
        solver_backend=solver_backend,
        boundary_condition=str(boundary_condition),
        motion_input_type=str(motion_input_type),
        damping_mode=damping_mode,
        time=time,
        dt_s=float(dt_s),
        input_time=input_time,
        input_dt_s=float(input_dt_s),
        acc_surface=acc_surface,
        acc_input=acc_input,
        acc_applied_input=acc_applied_input,
        profile=profile,
        surface_pgd_m=surface_pgd_m,
    )


def _normalize_signature_value(value: object) -> object:
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, dict):
        return {
            str(key): _normalize_signature_value(value[key])
            for key in sorted(value.keys(), key=lambda item: str(item))
        }
    if isinstance(value, list):
        return [_normalize_signature_value(item) for item in value]
    return value


def _layer_signature(layer: object) -> object:
    model_dump = getattr(layer, "model_dump", None)
    if callable(model_dump):
        payload = model_dump(by_alias=True, exclude_none=True)
    else:
        payload = layer
    return _normalize_signature_value(payload)


def _config_signature_summary(
    cfg_a: ProjectConfig | None,
    cfg_b: ProjectConfig | None,
) -> BoundarySensitivityConfigSummary:
    project_name_a = cfg_a.project_name if cfg_a is not None else ""
    project_name_b = cfg_b.project_name if cfg_b is not None else ""
    solver_backend_a = cfg_a.analysis.solver_backend if cfg_a is not None else ""
    solver_backend_b = cfg_b.analysis.solver_backend if cfg_b is not None else ""
    boundary_condition_a = (
        cfg_a.boundary_condition.value if cfg_a is not None else ""
    )
    boundary_condition_b = (
        cfg_b.boundary_condition.value if cfg_b is not None else ""
    )
    motion_input_type_a = cfg_a.motion.input_type if cfg_a is not None else ""
    motion_input_type_b = cfg_b.motion.input_type if cfg_b is not None else ""
    damping_mode_a = cfg_a.analysis.damping_mode if cfg_a is not None else ""
    damping_mode_b = cfg_b.analysis.damping_mode if cfg_b is not None else ""

    same_project_name = (
        bool(project_name_a == project_name_b)
        if cfg_a is not None and cfg_b is not None
        else None
    )
    same_solver_backend = (
        bool(solver_backend_a == solver_backend_b)
        if cfg_a is not None and cfg_b is not None
        else None
    )
    same_damping_mode = (
        bool(damping_mode_a == damping_mode_b)
        if cfg_a is not None and cfg_b is not None
        else None
    )
    same_layer_count = (
        bool(len(cfg_a.profile.layers) == len(cfg_b.profile.layers))
        if cfg_a is not None and cfg_b is not None
        else None
    )
    same_upper_layers: bool | None = None
    last_layer_changed: bool | None = None
    bedrock_changed: bool | None = None
    only_last_layer_or_boundary_changed: bool | None = None
    upper_layer_count = 0

    if cfg_a is not None and cfg_b is not None:
        layers_a = list(cfg_a.profile.layers)
        layers_b = list(cfg_b.profile.layers)
        common_count = min(len(layers_a), len(layers_b))
        upper_layer_count = max(common_count - 1, 0)
        if common_count > 1:
            upper_a = [_layer_signature(layer) for layer in layers_a[:-1]]
            upper_b = [_layer_signature(layer) for layer in layers_b[:-1]]
            same_upper_layers = bool(upper_a == upper_b)
        elif common_count == 1:
            same_upper_layers = True
        last_layer_changed = (
            bool(_layer_signature(layers_a[-1]) != _layer_signature(layers_b[-1]))
            if layers_a and layers_b
            else None
        )
        bedrock_changed = (
            bool(
                _normalize_signature_value(
                    cfg_a.profile.bedrock.model_dump(by_alias=True, exclude_none=True)
                )
                != _normalize_signature_value(
                    cfg_b.profile.bedrock.model_dump(by_alias=True, exclude_none=True)
                )
            )
            if cfg_a.profile.bedrock is not None and cfg_b.profile.bedrock is not None
            else bool((cfg_a.profile.bedrock is None) != (cfg_b.profile.bedrock is None))
        )
        if same_layer_count is not None and same_upper_layers is not None and last_layer_changed is not None:
            only_last_layer_or_boundary_changed = bool(
                same_layer_count
                and same_upper_layers
                and (
                    last_layer_changed
                    or bedrock_changed
                    or boundary_condition_a != boundary_condition_b
                )
            )

    return BoundarySensitivityConfigSummary(
        project_name_a=project_name_a,
        project_name_b=project_name_b,
        solver_backend_a=solver_backend_a,
        solver_backend_b=solver_backend_b,
        boundary_condition_a=boundary_condition_a,
        boundary_condition_b=boundary_condition_b,
        motion_input_type_a=motion_input_type_a,
        motion_input_type_b=motion_input_type_b,
        damping_mode_a=damping_mode_a,
        damping_mode_b=damping_mode_b,
        same_project_name=same_project_name,
        same_solver_backend=same_solver_backend,
        same_damping_mode=same_damping_mode,
        same_layer_count=same_layer_count,
        same_upper_layers=same_upper_layers,
        last_layer_changed=last_layer_changed,
        bedrock_changed=bedrock_changed,
        only_last_layer_or_boundary_changed=only_last_layer_or_boundary_changed,
        upper_layer_count=upper_layer_count,
    )


def _signal_history_metrics(
    time_a: np.ndarray,
    values_a: np.ndarray,
    dt_a: float,
    time_b: np.ndarray,
    values_b: np.ndarray,
    dt_b: float,
) -> tuple[float | None, float | None, list[str]]:
    if (
        time_a.size <= 1
        or time_b.size <= 1
        or values_a.size <= 1
        or values_b.size <= 1
    ):
        return None, None, []
    (
        _overlap_duration,
        _overlap_samples,
        _rmse,
        nrmse,
        corrcoef,
        warnings,
    ) = _time_history_metrics(
        time_a,
        values_a,
        time_b,
        values_b,
        dt_a,
        dt_b,
    )
    return nrmse, corrcoef, warnings


def _spectra_peak_metrics(
    signal_a: np.ndarray,
    dt_a: float,
    signal_b: np.ndarray,
    dt_b: float,
    *,
    periods: np.ndarray,
    damping: float,
) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    if signal_a.size <= 1 or signal_b.size <= 1:
        return None, None, None, None, None
    spectra_a = compute_spectra(signal_a, dt_a, damping=damping, periods=periods)
    spectra_b = compute_spectra(signal_b, dt_b, damping=damping, periods=periods)
    psa_a = np.asarray(spectra_a.psa, dtype=np.float64)
    psa_b = np.asarray(spectra_b.psa, dtype=np.float64)
    if psa_a.size == 0 or psa_b.size == 0:
        return None, None, None, None, None
    nrmse = _compare_metric_nrmse(psa_a, psa_b)
    peak_idx_a = int(np.argmax(np.abs(psa_a)))
    peak_idx_b = int(np.argmax(np.abs(psa_b)))
    peak_a = float(psa_a[peak_idx_a] / 9.81)
    peak_b = float(psa_b[peak_idx_b] / 9.81)
    peak_period_a = float(periods[peak_idx_a])
    peak_period_b = float(periods[peak_idx_b])
    return nrmse, peak_a, peak_b, peak_period_a, peak_period_b


def _surface_spectra_metrics(
    store_a: object,
    store_b: object,
    *,
    damping: float,
) -> tuple[
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
    float | None,
]:
    periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
    spectra_a = compute_spectra(store_a.acc_surface, store_a.dt_s, damping=damping, periods=periods)
    spectra_b = compute_spectra(store_b.acc_surface, store_b.dt_s, damping=damping, periods=periods)
    psa_a = np.asarray(spectra_a.psa, dtype=np.float64)
    psa_b = np.asarray(spectra_b.psa, dtype=np.float64)
    nrmse = _compare_metric_nrmse(psa_a, psa_b)
    if psa_a.size == 0 or psa_b.size == 0:
        return nrmse, None, None, None, None, None
    peak_idx_a = int(np.argmax(np.abs(psa_a)))
    peak_idx_b = int(np.argmax(np.abs(psa_b)))
    peak_a = float(psa_a[peak_idx_a] / 9.81)
    peak_b = float(psa_b[peak_idx_b] / 9.81)
    peak_period_a = float(periods[peak_idx_a])
    peak_period_b = float(periods[peak_idx_b])
    peak_shift_pct = _safe_pct_shift(peak_period_b, peak_period_a)
    return nrmse, peak_a, peak_b, peak_period_a, peak_period_b, peak_shift_pct


def _surface_pgd_from_store(store: object) -> float | None:
    disp = np.asarray(getattr(store, "nodal_displacement_m", np.array([])), dtype=np.float64)
    if disp.ndim == 2 and disp.shape[0] >= 1 and disp.shape[1] >= 1:
        rel = disp - disp[-1:, :]
        return float(np.max(np.abs(rel[0, :])))
    return None


def _surface_pgd_from_profile(
    profile: dict[str, np.ndarray],
) -> float | None:
    depth = np.asarray(profile.get("depth_m", np.array([])), dtype=np.float64)
    max_disp = np.asarray(profile.get("max_displacement_m", np.array([])), dtype=np.float64)
    mask = np.isfinite(depth) & np.isfinite(max_disp)
    if int(np.count_nonzero(mask)) < 1:
        return None
    order = np.argsort(depth[mask])
    max_disp_use = max_disp[mask][order]
    if max_disp_use.size < 1:
        return None
    return float(max_disp_use[0])


def _common_profile_axis(
    depth_a: np.ndarray,
    depth_b: np.ndarray,
) -> np.ndarray:
    arr_a = np.asarray(depth_a, dtype=np.float64)
    arr_b = np.asarray(depth_b, dtype=np.float64)
    mask_a = np.isfinite(arr_a)
    mask_b = np.isfinite(arr_b)
    if int(np.count_nonzero(mask_a)) < 1 or int(np.count_nonzero(mask_b)) < 1:
        return np.array([], dtype=np.float64)
    valid_a = arr_a[mask_a]
    valid_b = arr_b[mask_b]
    lo = max(float(np.min(valid_a)), float(np.min(valid_b)))
    hi = min(float(np.max(valid_a)), float(np.max(valid_b)))
    if hi < lo:
        return np.array([], dtype=np.float64)
    common = valid_a[(valid_a >= lo - 1.0e-9) & (valid_a <= hi + 1.0e-9)]
    if common.size >= 2:
        return np.asarray(common, dtype=np.float64)
    point_count = max(min(valid_a.size, valid_b.size), 2)
    return np.linspace(lo, hi, point_count, dtype=np.float64)


def _profile_metric_on_common_depth(
    profile_a: dict[str, np.ndarray],
    profile_b: dict[str, np.ndarray],
    key: str,
    common_depth: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float | None]:
    values_a = _interpolate_series(profile_a["depth_m"], profile_a[key], common_depth)
    values_b = _interpolate_series(profile_b["depth_m"], profile_b[key], common_depth)
    return values_a, values_b, _compare_metric_nrmse(values_a, values_b)


def _write_boundary_layer_delta_csv(
    path: Path,
    common_depth: np.ndarray,
    paired_metrics: dict[str, tuple[np.ndarray, np.ndarray]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_names = list(paired_metrics.keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        header = ["depth_m"]
        for name in metric_names:
            header.extend(
                [
                    f"{name}_a",
                    f"{name}_b",
                    f"{name}_diff",
                    f"{name}_ratio_b_over_a",
                ]
            )
        writer.writerow(header)
        for idx, depth in enumerate(common_depth):
            row: list[object] = [float(depth)]
            for name in metric_names:
                values_a, values_b = paired_metrics[name]
                value_a = float(values_a[idx]) if idx < values_a.size else float("nan")
                value_b = float(values_b[idx]) if idx < values_b.size else float("nan")
                diff = value_b - value_a if np.isfinite(value_a) and np.isfinite(value_b) else float("nan")
                ratio = (
                    value_b / value_a
                    if np.isfinite(value_a) and np.isfinite(value_b) and abs(value_a) > 1.0e-20
                    else float("nan")
                )
                row.extend([value_a, value_b, diff, ratio])
            writer.writerow(row)


def _metric_mean_ratio(lhs: np.ndarray, rhs: np.ndarray) -> float | None:
    lhs_use = np.asarray(lhs, dtype=np.float64)
    rhs_use = np.asarray(rhs, dtype=np.float64)
    mask = np.isfinite(lhs_use) & np.isfinite(rhs_use) & (np.abs(rhs_use) > 1.0e-20)
    if int(np.count_nonzero(mask)) == 0:
        return None
    return float(np.mean(lhs_use[mask] / rhs_use[mask]))


def _derive_stress_proxy(
    stress_ratio: np.ndarray,
    effective_stress_kpa: np.ndarray,
) -> np.ndarray:
    stress_ratio_use = np.asarray(stress_ratio, dtype=np.float64)
    effective_stress_use = np.asarray(effective_stress_kpa, dtype=np.float64)
    mask = np.isfinite(stress_ratio_use) & np.isfinite(effective_stress_use)
    derived = np.full(stress_ratio_use.shape, np.nan, dtype=np.float64)
    derived[mask] = stress_ratio_use[mask] * effective_stress_use[mask]
    return derived


def _derive_secant_proxy(
    stress_proxy_kpa: np.ndarray,
    gamma_max: np.ndarray,
) -> np.ndarray:
    stress_proxy_use = np.asarray(stress_proxy_kpa, dtype=np.float64)
    gamma_use = np.asarray(gamma_max, dtype=np.float64)
    mask = np.isfinite(stress_proxy_use) & np.isfinite(gamma_use) & (np.abs(gamma_use) > 1.0e-20)
    derived = np.full(stress_proxy_use.shape, np.nan, dtype=np.float64)
    derived[mask] = stress_proxy_use[mask] / gamma_use[mask]
    return derived


def _mean_optional(values: list[float | None]) -> float | None:
    valid = [float(value) for value in values if value is not None and np.isfinite(value)]
    if not valid:
        return None
    return float(np.mean(np.asarray(valid, dtype=np.float64)))


def _write_motion_csv_from_run_input(
    run_dir: Path,
    output_csv: Path,
) -> Path:
    store = load_result(run_dir)
    time = np.asarray(store.input_time, dtype=np.float64)
    acc = np.asarray(store.acc_input, dtype=np.float64)
    if time.size == 0 and acc.size > 0:
        dt = float(getattr(store, "input_dt_s", 0.0) or 0.0)
        if dt <= 0.0:
            raise ValueError(f"Run input history has no valid time axis: {run_dir}")
        time = np.arange(acc.size, dtype=np.float64) * dt
    if time.size != acc.size or acc.size == 0:
        raise ValueError(f"Run input history is unavailable for layer sweep audit: {run_dir}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time_s", "acc_m_s2"])
        for time_v, acc_v in zip(time, acc, strict=True):
            writer.writerow([float(time_v), float(acc_v)])
    return output_csv


def _write_case_truth_layer_audit_csv(
    path: Path,
    rows: list[CaseTruthLayerAuditRow],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "profile_layer_index",
                "depth_m",
                "geowave_gamma_max",
                "deepsoil_gamma_max",
                "gamma_max_ratio_geo_over_ref",
                "geowave_pga_g",
                "deepsoil_pga_g",
                "pga_g_ratio_geo_over_ref",
                "geowave_max_displacement_m",
                "deepsoil_max_displacement_m",
                "max_displacement_ratio_geo_over_ref",
                "geowave_max_strain_pct",
                "deepsoil_max_strain_pct",
                "max_strain_ratio_geo_over_ref",
                "geowave_max_stress_ratio",
                "deepsoil_max_stress_ratio",
                "max_stress_ratio_geo_over_ref",
                "geowave_effective_stress_kpa",
                "deepsoil_effective_stress_kpa",
                "effective_stress_ratio_geo_over_ref",
                "geowave_stress_proxy_kpa",
                "deepsoil_stress_proxy_kpa",
                "stress_proxy_ratio_geo_over_ref",
                "geowave_secant_proxy_kpa",
                "deepsoil_secant_proxy_kpa",
                "secant_proxy_ratio_geo_over_ref",
                "tau_peak_proxy_ratio_geo_over_ref",
                "mean_kt_ratio_geo_over_ref_secant",
                "min_kt_ratio_geo_over_ref_secant",
                "mean_compliance_fraction",
                "max_compliance_fraction",
                "mean_kt_kpa",
                "min_kt_kpa",
                "max_kt_kpa",
                "gamma_abs_max",
                "tau_abs_max",
                "gamma_m_global_max",
                "f_mrdf_min",
                "f_mrdf_max",
                "g_ref_min_kpa",
                "g_ref_max_kpa",
                "g_t_ref_min_kpa",
                "g_t_ref_max_kpa",
                "reason_counts",
                "branch_kind_counts",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.profile_layer_index,
                    row.depth_m,
                    row.geowave_gamma_max,
                    row.deepsoil_gamma_max,
                    row.gamma_max_ratio_geo_over_ref,
                    row.geowave_pga_g,
                    row.deepsoil_pga_g,
                    row.pga_g_ratio_geo_over_ref,
                    row.geowave_max_displacement_m,
                    row.deepsoil_max_displacement_m,
                    row.max_displacement_ratio_geo_over_ref,
                    row.geowave_max_strain_pct,
                    row.deepsoil_max_strain_pct,
                    row.max_strain_ratio_geo_over_ref,
                    row.geowave_max_stress_ratio,
                    row.deepsoil_max_stress_ratio,
                    row.max_stress_ratio_geo_over_ref,
                    row.geowave_effective_stress_kpa,
                    row.deepsoil_effective_stress_kpa,
                    row.effective_stress_ratio_geo_over_ref,
                    row.geowave_stress_proxy_kpa,
                    row.deepsoil_stress_proxy_kpa,
                    row.stress_proxy_ratio_geo_over_ref,
                    row.geowave_secant_proxy_kpa,
                    row.deepsoil_secant_proxy_kpa,
                    row.secant_proxy_ratio_geo_over_ref,
                    row.tau_peak_proxy_ratio_geo_over_ref,
                    row.mean_kt_ratio_geo_over_ref_secant,
                    row.min_kt_ratio_geo_over_ref_secant,
                    row.mean_compliance_fraction,
                    row.max_compliance_fraction,
                    row.mean_kt_kpa,
                    row.min_kt_kpa,
                    row.max_kt_kpa,
                    row.gamma_abs_max,
                    row.tau_abs_max,
                    row.gamma_m_global_max,
                    row.f_mrdf_min,
                    row.f_mrdf_max,
                    row.g_ref_min_kpa,
                    row.g_ref_max_kpa,
                    row.g_t_ref_min_kpa,
                    row.g_t_ref_max_kpa,
                    json.dumps(row.reason_counts, sort_keys=True),
                    json.dumps(row.branch_kind_counts, sort_keys=True),
                ]
            )


def compare_boundary_sensitivity_runs(
    run_a_dir: str | Path,
    run_b_dir: str | Path,
    output_dir: str | Path,
    *,
    label_a: str | None = None,
    label_b: str | None = None,
    damping: float = 0.05,
) -> BoundarySensitivityResult:
    run_path_a = Path(run_a_dir)
    run_path_b = Path(run_b_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "boundary_sensitivity_compare.json"
    summary_md = out_dir / "boundary_sensitivity_compare.md"
    layer_delta_csv = out_dir / "boundary_sensitivity_profile_delta.csv"

    store_a = load_result(run_path_a)
    store_b = load_result(run_path_b)
    cfg_a = _load_run_config_snapshot(run_path_a)
    cfg_b = _load_run_config_snapshot(run_path_b)
    config_summary = _config_signature_summary(cfg_a, cfg_b)

    name_a = label_a or run_path_a.name
    name_b = label_b or run_path_b.name
    warnings: list[str] = []

    raw_input_history_nrmse, _raw_input_corr, raw_input_warnings = _signal_history_metrics(
        store_a.input_time,
        np.asarray(store_a.acc_input, dtype=np.float64),
        float(store_a.input_dt_s),
        store_b.input_time,
        np.asarray(store_b.acc_input, dtype=np.float64),
        float(store_b.input_dt_s),
    )
    warnings.extend(f"Raw input: {item}" for item in raw_input_warnings)

    input_pga_g_a = (
        float(np.max(np.abs(np.asarray(store_a.acc_input, dtype=np.float64))) / 9.81)
        if store_a.acc_input.size > 0
        else None
    )
    input_pga_g_b = (
        float(np.max(np.abs(np.asarray(store_b.acc_input, dtype=np.float64))) / 9.81)
        if store_b.acc_input.size > 0
        else None
    )
    input_psa_peak_g_a = None
    input_psa_peak_g_b = None
    raw_input_psa_nrmse = None
    if store_a.acc_input.size > 1 and store_b.acc_input.size > 1:
        periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
        psa_a = compute_spectra(store_a.acc_input, store_a.input_dt_s, damping=damping, periods=periods).psa
        psa_b = compute_spectra(store_b.acc_input, store_b.input_dt_s, damping=damping, periods=periods).psa
        raw_input_psa_nrmse = _compare_metric_nrmse(np.asarray(psa_a), np.asarray(psa_b))
        if len(psa_a) > 0:
            input_psa_peak_g_a = float(np.max(np.abs(np.asarray(psa_a, dtype=np.float64))) / 9.81)
        if len(psa_b) > 0:
            input_psa_peak_g_b = float(np.max(np.abs(np.asarray(psa_b, dtype=np.float64))) / 9.81)

    applied_a = np.asarray(store_a.acc_applied_input, dtype=np.float64)
    applied_b = np.asarray(store_b.acc_applied_input, dtype=np.float64)
    if applied_a.size <= 1 and cfg_a is not None and store_a.acc_input.size > 1:
        applied_a = np.asarray(effective_input_acceleration(cfg_a, store_a.acc_input), dtype=np.float64)
    if applied_b.size <= 1 and cfg_b is not None and store_b.acc_input.size > 1:
        applied_b = np.asarray(effective_input_acceleration(cfg_b, store_b.acc_input), dtype=np.float64)
    applied_input_history_nrmse, _applied_corr, applied_input_warnings = _signal_history_metrics(
        store_a.input_time,
        applied_a,
        float(store_a.input_dt_s),
        store_b.input_time,
        applied_b,
        float(store_b.input_dt_s),
    )
    warnings.extend(f"Applied input: {item}" for item in applied_input_warnings)

    applied_input_psa_nrmse = None
    if applied_a.size > 1 and applied_b.size > 1:
        periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
        psa_a = compute_spectra(applied_a, store_a.input_dt_s, damping=damping, periods=periods).psa
        psa_b = compute_spectra(applied_b, store_b.input_dt_s, damping=damping, periods=periods).psa
        applied_input_psa_nrmse = _compare_metric_nrmse(np.asarray(psa_a), np.asarray(psa_b))

    (
        surface_history_nrmse,
        surface_history_corrcoef,
        surface_history_warnings,
    ) = _signal_history_metrics(
        store_a.time,
        np.asarray(store_a.acc_surface, dtype=np.float64),
        float(store_a.dt_s),
        store_b.time,
        np.asarray(store_b.acc_surface, dtype=np.float64),
        float(store_b.dt_s),
    )
    warnings.extend(f"Surface response: {item}" for item in surface_history_warnings)

    (
        surface_psa_nrmse,
        surface_psa_peak_g_a,
        surface_psa_peak_g_b,
        surface_peak_period_s_a,
        surface_peak_period_s_b,
        surface_peak_period_shift_pct_b_vs_a,
    ) = _surface_spectra_metrics(store_a, store_b, damping=damping)

    profile_a = _load_profile_from_run(run_path_a)
    profile_b = _load_profile_from_run(run_path_b)
    common_depth = _common_profile_axis(profile_a["depth_m"], profile_b["depth_m"])
    if common_depth.size <= 1:
        warnings.append("Profile overlap is too short for robust boundary verification.")

    paired_metrics: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    metric_nrmse: dict[str, float | None] = {}
    for key in (
        "gamma_max",
        "pga_g",
        "max_displacement_m",
        "max_strain_pct",
        "max_stress_ratio",
        "effective_stress_kpa",
        "tau_peak_kpa",
        "secant_g_over_gmax",
    ):
        if common_depth.size > 0:
            values_a, values_b, metric_value = _profile_metric_on_common_depth(
                profile_a,
                profile_b,
                key,
                common_depth,
            )
        else:
            values_a = np.array([], dtype=np.float64)
            values_b = np.array([], dtype=np.float64)
            metric_value = None
        paired_metrics[key] = (values_a, values_b)
        metric_nrmse[key] = metric_value

    _write_boundary_layer_delta_csv(layer_delta_csv, common_depth, paired_metrics)

    surface_pga_g_a = (
        float(np.max(np.abs(np.asarray(store_a.acc_surface, dtype=np.float64))) / 9.81)
        if store_a.acc_surface.size > 0
        else None
    )
    surface_pga_g_b = (
        float(np.max(np.abs(np.asarray(store_b.acc_surface, dtype=np.float64))) / 9.81)
        if store_b.acc_surface.size > 0
        else None
    )
    surface_pgd_m_a = _surface_pgd_from_profile(profile_a)
    if surface_pgd_m_a is None:
        surface_pgd_m_a = _surface_pgd_from_store(store_a)
    surface_pgd_m_b = _surface_pgd_from_profile(profile_b)
    if surface_pgd_m_b is None:
        surface_pgd_m_b = _surface_pgd_from_store(store_b)

    summary = BoundarySensitivitySummary(
        run_a_id=run_path_a.name,
        run_b_id=run_path_b.name,
        label_a=name_a,
        label_b=name_b,
        config=config_summary,
        raw_input_history_nrmse=raw_input_history_nrmse,
        raw_input_psa_nrmse=raw_input_psa_nrmse,
        applied_input_history_nrmse=applied_input_history_nrmse,
        applied_input_psa_nrmse=applied_input_psa_nrmse,
        surface_history_nrmse=surface_history_nrmse,
        surface_history_corrcoef=surface_history_corrcoef,
        input_pga_g_a=input_pga_g_a,
        input_pga_g_b=input_pga_g_b,
        input_psa_peak_g_a=input_psa_peak_g_a,
        input_psa_peak_g_b=input_psa_peak_g_b,
        surface_pga_g_a=surface_pga_g_a,
        surface_pga_g_b=surface_pga_g_b,
        surface_pga_ratio_b_over_a=_safe_ratio(surface_pga_g_b, surface_pga_g_a),
        surface_pgd_m_a=surface_pgd_m_a,
        surface_pgd_m_b=surface_pgd_m_b,
        surface_pgd_ratio_b_over_a=_safe_ratio(surface_pgd_m_b, surface_pgd_m_a),
        surface_psa_nrmse=surface_psa_nrmse,
        surface_psa_peak_g_a=surface_psa_peak_g_a,
        surface_psa_peak_g_b=surface_psa_peak_g_b,
        surface_psa_peak_ratio_b_over_a=_safe_ratio(surface_psa_peak_g_b, surface_psa_peak_g_a),
        surface_to_input_pga_amp_a=_safe_ratio(surface_pga_g_a, input_pga_g_a),
        surface_to_input_pga_amp_b=_safe_ratio(surface_pga_g_b, input_pga_g_b),
        surface_to_input_peak_psa_amp_a=_safe_ratio(surface_psa_peak_g_a, input_psa_peak_g_a),
        surface_to_input_peak_psa_amp_b=_safe_ratio(surface_psa_peak_g_b, input_psa_peak_g_b),
        surface_peak_period_s_a=surface_peak_period_s_a,
        surface_peak_period_s_b=surface_peak_period_s_b,
        surface_peak_period_shift_pct_b_vs_a=surface_peak_period_shift_pct_b_vs_a,
        profile_depth_points=int(common_depth.size),
        gamma_max_nrmse=metric_nrmse["gamma_max"],
        pga_profile_nrmse=metric_nrmse["pga_g"],
        max_displacement_nrmse=metric_nrmse["max_displacement_m"],
        max_strain_nrmse=metric_nrmse["max_strain_pct"],
        max_stress_ratio_nrmse=metric_nrmse["max_stress_ratio"],
        effective_stress_nrmse=metric_nrmse["effective_stress_kpa"],
        tau_peak_nrmse=metric_nrmse["tau_peak_kpa"],
        secant_g_over_gmax_nrmse=metric_nrmse["secant_g_over_gmax"],
        warnings=warnings,
    )
    result = BoundarySensitivityResult(
        run_a_dir=run_path_a,
        run_b_dir=run_path_b,
        artifacts=BoundarySensitivityArtifacts(
            output_dir=out_dir,
            summary_json=summary_json,
            summary_md=summary_md,
            layer_delta_csv=layer_delta_csv,
        ),
        summary=summary,
    )

    warning_block = [f"- {message}" for message in warnings] if warnings else ["- none"]
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    summary_md.write_text(
        "\n".join(
            [
                "# Boundary Sensitivity Verification",
                "",
                f"- Case A: `{name_a}` (`{run_path_a.name}`)",
                f"- Case B: `{name_b}` (`{run_path_b.name}`)",
                "",
                "## Config",
                f"- Boundary: `{config_summary.boundary_condition_a}` -> `{config_summary.boundary_condition_b}`",
                f"- Motion input type: `{config_summary.motion_input_type_a}` -> `{config_summary.motion_input_type_b}`",
                f"- Same upper layers: `{config_summary.same_upper_layers}`",
                f"- Only last layer or boundary changed: `{config_summary.only_last_layer_or_boundary_changed}`",
                "",
                "## Input",
                f"- Raw input history NRMSE: `{summary.raw_input_history_nrmse}`",
                f"- Raw input PSA NRMSE: `{summary.raw_input_psa_nrmse}`",
                f"- Applied input history NRMSE: `{summary.applied_input_history_nrmse}`",
                f"- Applied input PSA NRMSE: `{summary.applied_input_psa_nrmse}`",
                f"- Raw input PGA (g): `{summary.input_pga_g_a}` -> `{summary.input_pga_g_b}`",
                f"- Raw input PSA peak (g): `{summary.input_psa_peak_g_a}` -> `{summary.input_psa_peak_g_b}`",
                "",
                "## Surface Response",
                f"- Surface history NRMSE: `{summary.surface_history_nrmse}`",
                f"- Surface history corrcoef: `{summary.surface_history_corrcoef}`",
                f"- Surface PGA (g): `{summary.surface_pga_g_a}` -> `{summary.surface_pga_g_b}`",
                f"- Surface PGA ratio B/A: `{summary.surface_pga_ratio_b_over_a}`",
                f"- Surface PGD (m): `{summary.surface_pgd_m_a}` -> `{summary.surface_pgd_m_b}`",
                f"- Surface PGD ratio B/A: `{summary.surface_pgd_ratio_b_over_a}`",
                f"- Surface PSA peak (g): `{summary.surface_psa_peak_g_a}` -> `{summary.surface_psa_peak_g_b}`",
                f"- Surface PSA peak ratio B/A: `{summary.surface_psa_peak_ratio_b_over_a}`",
                f"- Surface peak period (s): `{summary.surface_peak_period_s_a}` -> `{summary.surface_peak_period_s_b}`",
                f"- Surface peak period shift B vs A (%): `{summary.surface_peak_period_shift_pct_b_vs_a}`",
                f"- Surface PSA NRMSE: `{summary.surface_psa_nrmse}`",
                "",
                "## Case-Local Amplification",
                f"- Surface/Input PGA amplification: `{summary.surface_to_input_pga_amp_a}` -> `{summary.surface_to_input_pga_amp_b}`",
                f"- Surface/Input peak PSA amplification: `{summary.surface_to_input_peak_psa_amp_a}` -> `{summary.surface_to_input_peak_psa_amp_b}`",
                "",
                "## Profile",
                f"- Depth points: `{summary.profile_depth_points}`",
                f"- gamma_max NRMSE: `{summary.gamma_max_nrmse}`",
                f"- PGA profile NRMSE: `{summary.pga_profile_nrmse}`",
                f"- max displacement NRMSE: `{summary.max_displacement_nrmse}`",
                f"- max strain NRMSE: `{summary.max_strain_nrmse}`",
                f"- max stress ratio NRMSE: `{summary.max_stress_ratio_nrmse}`",
                f"- effective stress NRMSE: `{summary.effective_stress_nrmse}`",
                f"- tau_peak NRMSE: `{summary.tau_peak_nrmse}`",
                f"- secant G/Gmax NRMSE: `{summary.secant_g_over_gmax_nrmse}`",
                "",
                "## Warnings",
                *warning_block,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return result


def compare_boundary_sensitivity_deepsoil_db_pair(
    run_a_dir: str | Path,
    run_b_dir: str | Path,
    output_dir: str | Path,
    *,
    label_a: str = "rigid_within",
    label_b: str = "elastic_halfspace_outcrop",
    boundary_condition_a: str = "rigid",
    boundary_condition_b: str = "elastic_halfspace",
    motion_input_type_a: str = "within",
    motion_input_type_b: str = "outcrop",
    damping: float = 0.05,
) -> BoundarySensitivityResult:
    case_a = _load_deepsoil_db_case(
        run_a_dir,
        boundary_condition=boundary_condition_a,
        motion_input_type=motion_input_type_a,
    )
    case_b = _load_deepsoil_db_case(
        run_b_dir,
        boundary_condition=boundary_condition_b,
        motion_input_type=motion_input_type_b,
    )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "boundary_sensitivity_compare.json"
    summary_md = out_dir / "boundary_sensitivity_compare.md"
    layer_delta_csv = out_dir / "boundary_sensitivity_profile_delta.csv"
    warnings: list[str] = []

    config_summary = BoundarySensitivityConfigSummary(
        project_name_a=case_a.project_name,
        project_name_b=case_b.project_name,
        solver_backend_a=case_a.solver_backend,
        solver_backend_b=case_b.solver_backend,
        boundary_condition_a=case_a.boundary_condition,
        boundary_condition_b=case_b.boundary_condition,
        motion_input_type_a=case_a.motion_input_type,
        motion_input_type_b=case_b.motion_input_type,
        damping_mode_a=case_a.damping_mode,
        damping_mode_b=case_b.damping_mode,
        same_project_name=False,
        same_solver_backend=True,
        same_damping_mode=True,
        same_layer_count=None,
        same_upper_layers=None,
        last_layer_changed=None,
        bedrock_changed=None,
        only_last_layer_or_boundary_changed=None,
        upper_layer_count=0,
    )

    raw_input_history_nrmse, _raw_input_corr, raw_input_warnings = _signal_history_metrics(
        case_a.input_time,
        case_a.acc_input,
        case_a.input_dt_s,
        case_b.input_time,
        case_b.acc_input,
        case_b.input_dt_s,
    )
    warnings.extend(f"Raw input: {item}" for item in raw_input_warnings)

    input_pga_g_a = float(np.max(np.abs(case_a.acc_input)) / 9.81) if case_a.acc_input.size else None
    input_pga_g_b = float(np.max(np.abs(case_b.acc_input)) / 9.81) if case_b.acc_input.size else None
    input_psa_peak_g_a = None
    input_psa_peak_g_b = None
    raw_input_psa_nrmse = None
    if case_a.acc_input.size > 1 and case_b.acc_input.size > 1:
        periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
        psa_a = compute_spectra(case_a.acc_input, case_a.input_dt_s, damping=damping, periods=periods).psa
        psa_b = compute_spectra(case_b.acc_input, case_b.input_dt_s, damping=damping, periods=periods).psa
        raw_input_psa_nrmse = _compare_metric_nrmse(np.asarray(psa_a), np.asarray(psa_b))
        if len(psa_a) > 0:
            input_psa_peak_g_a = float(np.max(np.abs(np.asarray(psa_a, dtype=np.float64))) / 9.81)
        if len(psa_b) > 0:
            input_psa_peak_g_b = float(np.max(np.abs(np.asarray(psa_b, dtype=np.float64))) / 9.81)

    applied_input_history_nrmse, _applied_corr, applied_warnings = _signal_history_metrics(
        case_a.input_time,
        case_a.acc_applied_input,
        case_a.input_dt_s,
        case_b.input_time,
        case_b.acc_applied_input,
        case_b.input_dt_s,
    )
    warnings.extend(f"Applied input: {item}" for item in applied_warnings)

    applied_input_psa_nrmse = None
    if case_a.acc_applied_input.size > 1 and case_b.acc_applied_input.size > 1:
        periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
        psa_a = compute_spectra(case_a.acc_applied_input, case_a.input_dt_s, damping=damping, periods=periods).psa
        psa_b = compute_spectra(case_b.acc_applied_input, case_b.input_dt_s, damping=damping, periods=periods).psa
        applied_input_psa_nrmse = _compare_metric_nrmse(np.asarray(psa_a), np.asarray(psa_b))

    surface_history_nrmse, surface_history_corrcoef, surface_history_warnings = _signal_history_metrics(
        case_a.time,
        case_a.acc_surface,
        case_a.dt_s,
        case_b.time,
        case_b.acc_surface,
        case_b.dt_s,
    )
    warnings.extend(f"Surface response: {item}" for item in surface_history_warnings)

    periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
    spectra_a = compute_spectra(case_a.acc_surface, case_a.dt_s, damping=damping, periods=periods)
    spectra_b = compute_spectra(case_b.acc_surface, case_b.dt_s, damping=damping, periods=periods)
    psa_a = np.asarray(spectra_a.psa, dtype=np.float64)
    psa_b = np.asarray(spectra_b.psa, dtype=np.float64)
    surface_psa_nrmse = _compare_metric_nrmse(psa_a, psa_b)
    peak_idx_a = int(np.argmax(np.abs(psa_a))) if psa_a.size else 0
    peak_idx_b = int(np.argmax(np.abs(psa_b))) if psa_b.size else 0
    surface_psa_peak_g_a = float(psa_a[peak_idx_a] / 9.81) if psa_a.size else None
    surface_psa_peak_g_b = float(psa_b[peak_idx_b] / 9.81) if psa_b.size else None
    surface_peak_period_s_a = float(periods[peak_idx_a]) if psa_a.size else None
    surface_peak_period_s_b = float(periods[peak_idx_b]) if psa_b.size else None
    surface_peak_period_shift_pct_b_vs_a = _safe_pct_shift(
        surface_peak_period_s_b,
        surface_peak_period_s_a,
    )

    common_depth = _common_profile_axis(case_a.profile["depth_m"], case_b.profile["depth_m"])
    paired_metrics: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    metric_nrmse: dict[str, float | None] = {}
    for key in (
        "gamma_max",
        "pga_g",
        "max_displacement_m",
        "max_strain_pct",
        "max_stress_ratio",
        "effective_stress_kpa",
        "tau_peak_kpa",
        "secant_g_over_gmax",
    ):
        if common_depth.size > 0:
            values_a, values_b, metric_value = _profile_metric_on_common_depth(
                case_a.profile,
                case_b.profile,
                key,
                common_depth,
            )
        else:
            values_a = np.array([], dtype=np.float64)
            values_b = np.array([], dtype=np.float64)
            metric_value = None
        paired_metrics[key] = (values_a, values_b)
        metric_nrmse[key] = metric_value
    _write_boundary_layer_delta_csv(layer_delta_csv, common_depth, paired_metrics)

    surface_pga_g_a = float(np.max(np.abs(case_a.acc_surface)) / 9.81) if case_a.acc_surface.size else None
    surface_pga_g_b = float(np.max(np.abs(case_b.acc_surface)) / 9.81) if case_b.acc_surface.size else None

    summary = BoundarySensitivitySummary(
        run_a_id=case_a.run_dir.name,
        run_b_id=case_b.run_dir.name,
        label_a=label_a,
        label_b=label_b,
        config=config_summary,
        raw_input_history_nrmse=raw_input_history_nrmse,
        raw_input_psa_nrmse=raw_input_psa_nrmse,
        applied_input_history_nrmse=applied_input_history_nrmse,
        applied_input_psa_nrmse=applied_input_psa_nrmse,
        surface_history_nrmse=surface_history_nrmse,
        surface_history_corrcoef=surface_history_corrcoef,
        input_pga_g_a=input_pga_g_a,
        input_pga_g_b=input_pga_g_b,
        input_psa_peak_g_a=input_psa_peak_g_a,
        input_psa_peak_g_b=input_psa_peak_g_b,
        surface_pga_g_a=surface_pga_g_a,
        surface_pga_g_b=surface_pga_g_b,
        surface_pga_ratio_b_over_a=_safe_ratio(surface_pga_g_b, surface_pga_g_a),
        surface_pgd_m_a=case_a.surface_pgd_m,
        surface_pgd_m_b=case_b.surface_pgd_m,
        surface_pgd_ratio_b_over_a=_safe_ratio(case_b.surface_pgd_m, case_a.surface_pgd_m),
        surface_psa_nrmse=surface_psa_nrmse,
        surface_psa_peak_g_a=surface_psa_peak_g_a,
        surface_psa_peak_g_b=surface_psa_peak_g_b,
        surface_psa_peak_ratio_b_over_a=_safe_ratio(surface_psa_peak_g_b, surface_psa_peak_g_a),
        surface_to_input_pga_amp_a=_safe_ratio(surface_pga_g_a, input_pga_g_a),
        surface_to_input_pga_amp_b=_safe_ratio(surface_pga_g_b, input_pga_g_b),
        surface_to_input_peak_psa_amp_a=_safe_ratio(surface_psa_peak_g_a, input_psa_peak_g_a),
        surface_to_input_peak_psa_amp_b=_safe_ratio(surface_psa_peak_g_b, input_psa_peak_g_b),
        surface_peak_period_s_a=surface_peak_period_s_a,
        surface_peak_period_s_b=surface_peak_period_s_b,
        surface_peak_period_shift_pct_b_vs_a=surface_peak_period_shift_pct_b_vs_a,
        profile_depth_points=int(common_depth.size),
        gamma_max_nrmse=metric_nrmse["gamma_max"],
        pga_profile_nrmse=metric_nrmse["pga_g"],
        max_displacement_nrmse=metric_nrmse["max_displacement_m"],
        max_strain_nrmse=metric_nrmse["max_strain_pct"],
        max_stress_ratio_nrmse=metric_nrmse["max_stress_ratio"],
        effective_stress_nrmse=metric_nrmse["effective_stress_kpa"],
        tau_peak_nrmse=metric_nrmse["tau_peak_kpa"],
        secant_g_over_gmax_nrmse=metric_nrmse["secant_g_over_gmax"],
        warnings=warnings,
    )
    result = BoundarySensitivityResult(
        run_a_dir=case_a.run_dir,
        run_b_dir=case_b.run_dir,
        artifacts=BoundarySensitivityArtifacts(
            output_dir=out_dir,
            summary_json=summary_json,
            summary_md=summary_md,
            layer_delta_csv=layer_delta_csv,
        ),
        summary=summary,
    )
    warning_block = [f"- {message}" for message in warnings] if warnings else ["- none"]
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    summary_md.write_text(
        "\n".join(
            [
                "# Boundary Sensitivity Verification",
                "",
                f"- Case A: `{label_a}` (`{case_a.run_dir.name}`)",
                f"- Case B: `{label_b}` (`{case_b.run_dir.name}`)",
                "",
                "## Config",
                f"- Boundary: `{config_summary.boundary_condition_a}` -> `{config_summary.boundary_condition_b}`",
                f"- Motion input type: `{config_summary.motion_input_type_a}` -> `{config_summary.motion_input_type_b}`",
                "",
                "## Input",
                f"- Raw input history NRMSE: `{summary.raw_input_history_nrmse}`",
                f"- Raw input PSA NRMSE: `{summary.raw_input_psa_nrmse}`",
                f"- Applied input history NRMSE: `{summary.applied_input_history_nrmse}`",
                f"- Applied input PSA NRMSE: `{summary.applied_input_psa_nrmse}`",
                f"- Raw input PGA (g): `{summary.input_pga_g_a}` -> `{summary.input_pga_g_b}`",
                f"- Raw input PSA peak (g): `{summary.input_psa_peak_g_a}` -> `{summary.input_psa_peak_g_b}`",
                "",
                "## Surface Response",
                f"- Surface history NRMSE: `{summary.surface_history_nrmse}`",
                f"- Surface history corrcoef: `{summary.surface_history_corrcoef}`",
                f"- Surface PGA (g): `{summary.surface_pga_g_a}` -> `{summary.surface_pga_g_b}`",
                f"- Surface PGA ratio B/A: `{summary.surface_pga_ratio_b_over_a}`",
                f"- Surface PGD (m): `{summary.surface_pgd_m_a}` -> `{summary.surface_pgd_m_b}`",
                f"- Surface PGD ratio B/A: `{summary.surface_pgd_ratio_b_over_a}`",
                f"- Surface PSA peak (g): `{summary.surface_psa_peak_g_a}` -> `{summary.surface_psa_peak_g_b}`",
                f"- Surface PSA peak ratio B/A: `{summary.surface_psa_peak_ratio_b_over_a}`",
                f"- Surface peak period (s): `{summary.surface_peak_period_s_a}` -> `{summary.surface_peak_period_s_b}`",
                f"- Surface peak period shift B vs A (%): `{summary.surface_peak_period_shift_pct_b_vs_a}`",
                "",
                "## Case-Local Amplification",
                f"- Surface/Input PGA amplification: `{summary.surface_to_input_pga_amp_a}` -> `{summary.surface_to_input_pga_amp_b}`",
                f"- Surface/Input peak PSA amplification: `{summary.surface_to_input_peak_psa_amp_a}` -> `{summary.surface_to_input_peak_psa_amp_b}`",
                "",
                "## Profile",
                f"- gamma_max NRMSE: `{summary.gamma_max_nrmse}`",
                f"- PGA profile NRMSE: `{summary.pga_profile_nrmse}`",
                f"- max displacement NRMSE: `{summary.max_displacement_nrmse}`",
                f"- max strain NRMSE: `{summary.max_strain_nrmse}`",
                f"- max stress ratio NRMSE: `{summary.max_stress_ratio_nrmse}`",
                f"- effective stress NRMSE: `{summary.effective_stress_nrmse}`",
                "",
                "## Warnings",
                *warning_block,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return result


def compare_boundary_delta_signatures(
    reference: BoundarySensitivityResult,
    candidate: BoundarySensitivityResult,
    output_dir: str | Path,
    *,
    reference_label: str | None = None,
    candidate_label: str | None = None,
) -> BoundaryDeltaComparisonResult:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "boundary_delta_comparison.json"
    summary_md = out_dir / "boundary_delta_comparison.md"

    ref_label = reference_label or reference.summary.label_b
    cand_label = candidate_label or candidate.summary.label_b
    direction_match_peak_ratio = (
        None
        if reference.summary.surface_psa_peak_ratio_b_over_a is None or candidate.summary.surface_psa_peak_ratio_b_over_a is None
        else bool((reference.summary.surface_psa_peak_ratio_b_over_a < 1.0) == (candidate.summary.surface_psa_peak_ratio_b_over_a < 1.0))
    )
    direction_match_peak_period = (
        None
        if reference.summary.surface_peak_period_shift_pct_b_vs_a is None or candidate.summary.surface_peak_period_shift_pct_b_vs_a is None
        else bool((reference.summary.surface_peak_period_shift_pct_b_vs_a < 0.0) == (candidate.summary.surface_peak_period_shift_pct_b_vs_a < 0.0))
    )
    direction_match_surface_pga = (
        None
        if reference.summary.surface_pga_ratio_b_over_a is None or candidate.summary.surface_pga_ratio_b_over_a is None
        else bool((reference.summary.surface_pga_ratio_b_over_a < 1.0) == (candidate.summary.surface_pga_ratio_b_over_a < 1.0))
    )
    direction_match_surface_pgd = (
        None
        if reference.summary.surface_pgd_ratio_b_over_a is None or candidate.summary.surface_pgd_ratio_b_over_a is None
        else bool((reference.summary.surface_pgd_ratio_b_over_a < 1.0) == (candidate.summary.surface_pgd_ratio_b_over_a < 1.0))
    )
    peak_ratio_abs_rel_error = _safe_abs_rel_error(
        reference.summary.surface_psa_peak_ratio_b_over_a,
        candidate.summary.surface_psa_peak_ratio_b_over_a,
    )
    peak_period_shift_abs_rel_error = _safe_abs_rel_error(
        reference.summary.surface_peak_period_shift_pct_b_vs_a,
        candidate.summary.surface_peak_period_shift_pct_b_vs_a,
    )
    surface_pga_ratio_abs_rel_error = _safe_abs_rel_error(
        reference.summary.surface_pga_ratio_b_over_a,
        candidate.summary.surface_pga_ratio_b_over_a,
    )
    surface_pgd_ratio_abs_rel_error = _safe_abs_rel_error(
        reference.summary.surface_pgd_ratio_b_over_a,
        candidate.summary.surface_pgd_ratio_b_over_a,
    )
    magnitude_items = {
        "peak_ratio": peak_ratio_abs_rel_error,
        "peak_period_shift_pct": peak_period_shift_abs_rel_error,
        "surface_pga_ratio": surface_pga_ratio_abs_rel_error,
        "surface_pgd_ratio": surface_pgd_ratio_abs_rel_error,
    }
    finite_items = {key: value for key, value in magnitude_items.items() if value is not None and np.isfinite(value)}
    mean_abs_rel_error = (
        float(np.mean(np.asarray(list(finite_items.values()), dtype=np.float64)))
        if finite_items
        else None
    )
    worst_metric_by_abs_rel_error = (
        max(finite_items.items(), key=lambda item: float(item[1]))[0]
        if finite_items
        else None
    )
    directional_gate_passed = (
        None
        if None in (
            direction_match_peak_ratio,
            direction_match_peak_period,
            direction_match_surface_pga,
            direction_match_surface_pgd,
        )
        else bool(
            direction_match_peak_ratio
            and direction_match_peak_period
            and direction_match_surface_pga
            and direction_match_surface_pgd
        )
    )
    summary = BoundaryDeltaComparisonSummary(
        reference_label=ref_label,
        candidate_label=cand_label,
        reference_peak_ratio=reference.summary.surface_psa_peak_ratio_b_over_a,
        candidate_peak_ratio=candidate.summary.surface_psa_peak_ratio_b_over_a,
        peak_ratio_delta=(
            None
            if reference.summary.surface_psa_peak_ratio_b_over_a is None or candidate.summary.surface_psa_peak_ratio_b_over_a is None
            else float(candidate.summary.surface_psa_peak_ratio_b_over_a - reference.summary.surface_psa_peak_ratio_b_over_a)
        ),
        peak_ratio_abs_rel_error=peak_ratio_abs_rel_error,
        reference_peak_period_shift_pct=reference.summary.surface_peak_period_shift_pct_b_vs_a,
        candidate_peak_period_shift_pct=candidate.summary.surface_peak_period_shift_pct_b_vs_a,
        peak_period_shift_delta_pct=(
            None
            if reference.summary.surface_peak_period_shift_pct_b_vs_a is None or candidate.summary.surface_peak_period_shift_pct_b_vs_a is None
            else float(candidate.summary.surface_peak_period_shift_pct_b_vs_a - reference.summary.surface_peak_period_shift_pct_b_vs_a)
        ),
        peak_period_shift_abs_rel_error=peak_period_shift_abs_rel_error,
        reference_surface_pga_ratio=reference.summary.surface_pga_ratio_b_over_a,
        candidate_surface_pga_ratio=candidate.summary.surface_pga_ratio_b_over_a,
        surface_pga_ratio_delta=(
            None
            if reference.summary.surface_pga_ratio_b_over_a is None or candidate.summary.surface_pga_ratio_b_over_a is None
            else float(candidate.summary.surface_pga_ratio_b_over_a - reference.summary.surface_pga_ratio_b_over_a)
        ),
        surface_pga_ratio_abs_rel_error=surface_pga_ratio_abs_rel_error,
        reference_surface_pgd_ratio=reference.summary.surface_pgd_ratio_b_over_a,
        candidate_surface_pgd_ratio=candidate.summary.surface_pgd_ratio_b_over_a,
        surface_pgd_ratio_delta=(
            None
            if reference.summary.surface_pgd_ratio_b_over_a is None or candidate.summary.surface_pgd_ratio_b_over_a is None
            else float(candidate.summary.surface_pgd_ratio_b_over_a - reference.summary.surface_pgd_ratio_b_over_a)
        ),
        surface_pgd_ratio_abs_rel_error=surface_pgd_ratio_abs_rel_error,
        direction_match_peak_ratio=direction_match_peak_ratio,
        direction_match_peak_period=direction_match_peak_period,
        direction_match_surface_pga=direction_match_surface_pga,
        direction_match_surface_pgd=direction_match_surface_pgd,
        directional_gate_passed=directional_gate_passed,
        mean_abs_rel_error=mean_abs_rel_error,
        worst_metric_by_abs_rel_error=worst_metric_by_abs_rel_error,
    )
    result = BoundaryDeltaComparisonResult(
        reference_source=reference.artifacts.summary_json,
        candidate_source=candidate.artifacts.summary_json,
        artifacts=BoundaryDeltaComparisonArtifacts(
            output_dir=out_dir,
            summary_json=summary_json,
            summary_md=summary_md,
        ),
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    summary_md.write_text(
        "\n".join(
            [
                "# Boundary Delta Comparison",
                "",
                f"- Reference: `{ref_label}`",
                f"- Candidate: `{cand_label}`",
                "",
                "## Directional Signature",
                f"- Peak RS ratio: `{summary.reference_peak_ratio}` vs `{summary.candidate_peak_ratio}`",
                f"- Peak RS direction match: `{summary.direction_match_peak_ratio}`",
                f"- Peak-period shift (%): `{summary.reference_peak_period_shift_pct}` vs `{summary.candidate_peak_period_shift_pct}`",
                f"- Peak-period direction match: `{summary.direction_match_peak_period}`",
                f"- Surface PGA ratio: `{summary.reference_surface_pga_ratio}` vs `{summary.candidate_surface_pga_ratio}`",
                f"- Surface PGA direction match: `{summary.direction_match_surface_pga}`",
                f"- Surface PGD ratio: `{summary.reference_surface_pgd_ratio}` vs `{summary.candidate_surface_pgd_ratio}`",
                f"- Surface PGD direction match: `{summary.direction_match_surface_pgd}`",
                "",
                "## Magnitude Closure",
                f"- Directional gate passed: `{summary.directional_gate_passed}`",
                f"- Peak RS abs relative error: `{summary.peak_ratio_abs_rel_error}`",
                f"- Peak-period shift abs relative error: `{summary.peak_period_shift_abs_rel_error}`",
                f"- Surface PGA ratio abs relative error: `{summary.surface_pga_ratio_abs_rel_error}`",
                f"- Surface PGD ratio abs relative error: `{summary.surface_pgd_ratio_abs_rel_error}`",
                f"- Mean abs relative error: `{summary.mean_abs_rel_error}`",
                f"- Worst metric by abs relative error: `{summary.worst_metric_by_abs_rel_error}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return result


def compare_case_truth_profile_and_tangent_audit(
    geowave_run_dir: str | Path,
    deepsoil_db_dir: str | Path,
    output_dir: str | Path,
    *,
    label: str = "rigid_within_case_truth",
    boundary_condition: str = "rigid",
    motion_input_type: str = "within",
    mode_code_override: float | None = None,
    points_per_wavelength: float = 10.0,
    min_dz_m: float = 0.25,
) -> CaseTruthLayerAuditResult:
    run_dir = Path(geowave_run_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "case_truth_compare.json"
    summary_md = out_dir / "case_truth_compare.md"
    layer_csv = out_dir / "case_truth_layers.csv"
    motion_csv = out_dir / "audit_motion.csv"
    layer_sweep_dir = out_dir / "layer_sweep"

    deepsoil_case = _load_deepsoil_db_case(
        deepsoil_db_dir,
        boundary_condition=boundary_condition,
        motion_input_type=motion_input_type,
    )
    geowave_profile = _load_profile_from_run(run_dir)
    common_depth = _common_profile_axis(geowave_profile["depth_m"], deepsoil_case.profile["depth_m"])
    if common_depth.size == 0:
        raise ValueError("No overlapping profile depth grid for case-truth compare.")

    paired_metric_names = (
        "gamma_max",
        "pga_g",
        "max_displacement_m",
        "max_strain_pct",
        "max_stress_ratio",
        "effective_stress_kpa",
    )
    metric_pairs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    metric_nrmse: dict[str, float | None] = {}
    metric_mean_ratio: dict[str, float | None] = {}
    for key in paired_metric_names:
        values_geo, values_ref, nrmse = _profile_metric_on_common_depth(
            geowave_profile,
            deepsoil_case.profile,
            key,
            common_depth,
        )
        metric_pairs[key] = (values_geo, values_ref)
        metric_nrmse[key] = nrmse
        metric_mean_ratio[key] = _metric_mean_ratio(values_geo, values_ref)

    stress_proxy_geo = _derive_stress_proxy(
        metric_pairs["max_stress_ratio"][0],
        metric_pairs["effective_stress_kpa"][0],
    )
    stress_proxy_ref = _derive_stress_proxy(
        metric_pairs["max_stress_ratio"][1],
        metric_pairs["effective_stress_kpa"][1],
    )
    metric_pairs["stress_proxy_kpa"] = (stress_proxy_geo, stress_proxy_ref)
    metric_nrmse["stress_proxy_kpa"] = _compare_metric_nrmse(stress_proxy_geo, stress_proxy_ref)
    metric_mean_ratio["stress_proxy_kpa"] = _metric_mean_ratio(stress_proxy_geo, stress_proxy_ref)

    secant_proxy_geo = _derive_secant_proxy(stress_proxy_geo, metric_pairs["gamma_max"][0])
    secant_proxy_ref = _derive_secant_proxy(stress_proxy_ref, metric_pairs["gamma_max"][1])
    metric_pairs["secant_proxy_kpa"] = (secant_proxy_geo, secant_proxy_ref)
    metric_nrmse["secant_proxy_kpa"] = _compare_metric_nrmse(secant_proxy_geo, secant_proxy_ref)
    metric_mean_ratio["secant_proxy_kpa"] = _metric_mean_ratio(secant_proxy_geo, secant_proxy_ref)

    motion_csv = _write_motion_csv_from_run_input(run_dir, motion_csv)
    layer_sweep = run_solver_layer_sweep_audit(
        run_dir / "config_snapshot.json",
        motion_csv,
        layer_sweep_dir,
        mode_code_override=mode_code_override,
        points_per_wavelength=points_per_wavelength,
        min_dz_m=min_dz_m,
    )
    sweep_by_layer = {int(row.profile_layer_index): row for row in layer_sweep.summary.layers}
    sweep_layer_offset = 0 if 0 in sweep_by_layer else 1
    geo_depth = np.asarray(geowave_profile["depth_m"], dtype=np.float64)
    layer_rows: list[CaseTruthLayerAuditRow] = []
    warnings: list[str] = []
    if np.isnan(np.asarray(deepsoil_case.profile.get("tau_peak_kpa", np.array([])), dtype=np.float64)).all():
        warnings.append("DeepSoil DB profile does not expose tau_peak_kpa or secant_g_over_gmax; tangent metrics are GeoWave-only in this report.")

    for idx, depth in enumerate(common_depth):
        if geo_depth.size == 0:
            profile_layer_index = idx
        else:
            profile_layer_index = int(np.argmin(np.abs(geo_depth - float(depth))))
        sweep_row = sweep_by_layer.get(profile_layer_index + sweep_layer_offset)
        gamma_geo, gamma_ref = metric_pairs["gamma_max"][0][idx], metric_pairs["gamma_max"][1][idx]
        pga_geo, pga_ref = metric_pairs["pga_g"][0][idx], metric_pairs["pga_g"][1][idx]
        disp_geo, disp_ref = metric_pairs["max_displacement_m"][0][idx], metric_pairs["max_displacement_m"][1][idx]
        strain_geo, strain_ref = metric_pairs["max_strain_pct"][0][idx], metric_pairs["max_strain_pct"][1][idx]
        stress_geo, stress_ref = metric_pairs["max_stress_ratio"][0][idx], metric_pairs["max_stress_ratio"][1][idx]
        eff_geo, eff_ref = metric_pairs["effective_stress_kpa"][0][idx], metric_pairs["effective_stress_kpa"][1][idx]
        stress_proxy_geo, stress_proxy_ref = metric_pairs["stress_proxy_kpa"][0][idx], metric_pairs["stress_proxy_kpa"][1][idx]
        secant_proxy_geo, secant_proxy_ref = metric_pairs["secant_proxy_kpa"][0][idx], metric_pairs["secant_proxy_kpa"][1][idx]
        tau_peak_proxy_ratio = _safe_ratio(
            sweep_row.tau_abs_max if sweep_row is not None else None,
            float(stress_proxy_ref) if np.isfinite(stress_proxy_ref) else None,
        )
        mean_kt_ratio = _safe_ratio(
            sweep_row.mean_kt_kpa if sweep_row is not None else None,
            float(secant_proxy_ref) if np.isfinite(secant_proxy_ref) else None,
        )
        min_kt_ratio = _safe_ratio(
            sweep_row.min_kt_kpa if sweep_row is not None else None,
            float(secant_proxy_ref) if np.isfinite(secant_proxy_ref) else None,
        )
        layer_rows.append(
            CaseTruthLayerAuditRow(
                profile_layer_index=profile_layer_index,
                depth_m=float(depth),
                geowave_gamma_max=float(gamma_geo) if np.isfinite(gamma_geo) else None,
                deepsoil_gamma_max=float(gamma_ref) if np.isfinite(gamma_ref) else None,
                gamma_max_ratio_geo_over_ref=_safe_ratio(
                    float(gamma_geo) if np.isfinite(gamma_geo) else None,
                    float(gamma_ref) if np.isfinite(gamma_ref) else None,
                ),
                geowave_pga_g=float(pga_geo) if np.isfinite(pga_geo) else None,
                deepsoil_pga_g=float(pga_ref) if np.isfinite(pga_ref) else None,
                pga_g_ratio_geo_over_ref=_safe_ratio(
                    float(pga_geo) if np.isfinite(pga_geo) else None,
                    float(pga_ref) if np.isfinite(pga_ref) else None,
                ),
                geowave_max_displacement_m=float(disp_geo) if np.isfinite(disp_geo) else None,
                deepsoil_max_displacement_m=float(disp_ref) if np.isfinite(disp_ref) else None,
                max_displacement_ratio_geo_over_ref=_safe_ratio(
                    float(disp_geo) if np.isfinite(disp_geo) else None,
                    float(disp_ref) if np.isfinite(disp_ref) else None,
                ),
                geowave_max_strain_pct=float(strain_geo) if np.isfinite(strain_geo) else None,
                deepsoil_max_strain_pct=float(strain_ref) if np.isfinite(strain_ref) else None,
                max_strain_ratio_geo_over_ref=_safe_ratio(
                    float(strain_geo) if np.isfinite(strain_geo) else None,
                    float(strain_ref) if np.isfinite(strain_ref) else None,
                ),
                geowave_max_stress_ratio=float(stress_geo) if np.isfinite(stress_geo) else None,
                deepsoil_max_stress_ratio=float(stress_ref) if np.isfinite(stress_ref) else None,
                max_stress_ratio_geo_over_ref=_safe_ratio(
                    float(stress_geo) if np.isfinite(stress_geo) else None,
                    float(stress_ref) if np.isfinite(stress_ref) else None,
                ),
                geowave_effective_stress_kpa=float(eff_geo) if np.isfinite(eff_geo) else None,
                deepsoil_effective_stress_kpa=float(eff_ref) if np.isfinite(eff_ref) else None,
                effective_stress_ratio_geo_over_ref=_safe_ratio(
                    float(eff_geo) if np.isfinite(eff_geo) else None,
                    float(eff_ref) if np.isfinite(eff_ref) else None,
                ),
                geowave_stress_proxy_kpa=float(stress_proxy_geo) if np.isfinite(stress_proxy_geo) else None,
                deepsoil_stress_proxy_kpa=float(stress_proxy_ref) if np.isfinite(stress_proxy_ref) else None,
                stress_proxy_ratio_geo_over_ref=_safe_ratio(
                    float(stress_proxy_geo) if np.isfinite(stress_proxy_geo) else None,
                    float(stress_proxy_ref) if np.isfinite(stress_proxy_ref) else None,
                ),
                geowave_secant_proxy_kpa=float(secant_proxy_geo) if np.isfinite(secant_proxy_geo) else None,
                deepsoil_secant_proxy_kpa=float(secant_proxy_ref) if np.isfinite(secant_proxy_ref) else None,
                secant_proxy_ratio_geo_over_ref=_safe_ratio(
                    float(secant_proxy_geo) if np.isfinite(secant_proxy_geo) else None,
                    float(secant_proxy_ref) if np.isfinite(secant_proxy_ref) else None,
                ),
                tau_peak_proxy_ratio_geo_over_ref=tau_peak_proxy_ratio,
                mean_kt_ratio_geo_over_ref_secant=mean_kt_ratio,
                min_kt_ratio_geo_over_ref_secant=min_kt_ratio,
                mean_compliance_fraction=sweep_row.mean_compliance_fraction if sweep_row is not None else None,
                max_compliance_fraction=sweep_row.max_compliance_fraction if sweep_row is not None else None,
                mean_kt_kpa=sweep_row.mean_kt_kpa if sweep_row is not None else None,
                min_kt_kpa=sweep_row.min_kt_kpa if sweep_row is not None else None,
                max_kt_kpa=sweep_row.max_kt_kpa if sweep_row is not None else None,
                gamma_abs_max=sweep_row.gamma_abs_max if sweep_row is not None else None,
                tau_abs_max=sweep_row.tau_abs_max if sweep_row is not None else None,
                gamma_m_global_max=sweep_row.gamma_m_global_max if sweep_row is not None else None,
                f_mrdf_min=sweep_row.f_mrdf_min if sweep_row is not None else None,
                f_mrdf_max=sweep_row.f_mrdf_max if sweep_row is not None else None,
                g_ref_min_kpa=sweep_row.g_ref_min_kpa if sweep_row is not None else None,
                g_ref_max_kpa=sweep_row.g_ref_max_kpa if sweep_row is not None else None,
                g_t_ref_min_kpa=sweep_row.g_t_ref_min_kpa if sweep_row is not None else None,
                g_t_ref_max_kpa=sweep_row.g_t_ref_max_kpa if sweep_row is not None else None,
                reason_counts=dict(sweep_row.reason_counts) if sweep_row is not None else {},
                branch_kind_counts=dict(sweep_row.branch_kind_counts) if sweep_row is not None else {},
            )
        )

    worst_mean_kt_row = min(
        (
            row
            for row in layer_rows
            if row.mean_kt_ratio_geo_over_ref_secant is not None
        ),
        key=lambda row: float(row.mean_kt_ratio_geo_over_ref_secant),
        default=None,
    )
    _write_case_truth_layer_audit_csv(layer_csv, layer_rows)
    summary = CaseTruthLayerAuditSummary(
        label=label,
        layer_count=len(layer_rows),
        gamma_max_nrmse=metric_nrmse["gamma_max"],
        pga_profile_nrmse=metric_nrmse["pga_g"],
        max_displacement_nrmse=metric_nrmse["max_displacement_m"],
        max_strain_nrmse=metric_nrmse["max_strain_pct"],
        max_stress_ratio_nrmse=metric_nrmse["max_stress_ratio"],
        effective_stress_nrmse=metric_nrmse["effective_stress_kpa"],
        stress_proxy_nrmse=metric_nrmse["stress_proxy_kpa"],
        secant_proxy_nrmse=metric_nrmse["secant_proxy_kpa"],
        gamma_max_mean_ratio_geo_over_ref=metric_mean_ratio["gamma_max"],
        pga_profile_mean_ratio_geo_over_ref=metric_mean_ratio["pga_g"],
        max_displacement_mean_ratio_geo_over_ref=metric_mean_ratio["max_displacement_m"],
        max_strain_mean_ratio_geo_over_ref=metric_mean_ratio["max_strain_pct"],
        max_stress_ratio_mean_ratio_geo_over_ref=metric_mean_ratio["max_stress_ratio"],
        effective_stress_mean_ratio_geo_over_ref=metric_mean_ratio["effective_stress_kpa"],
        stress_proxy_mean_ratio_geo_over_ref=metric_mean_ratio["stress_proxy_kpa"],
        secant_proxy_mean_ratio_geo_over_ref=metric_mean_ratio["secant_proxy_kpa"],
        tau_peak_proxy_mean_ratio_geo_over_ref=_mean_optional(
            [row.tau_peak_proxy_ratio_geo_over_ref for row in layer_rows]
        ),
        mean_kt_ratio_geo_over_ref_secant_mean=_mean_optional(
            [row.mean_kt_ratio_geo_over_ref_secant for row in layer_rows]
        ),
        min_kt_ratio_geo_over_ref_secant_mean=_mean_optional(
            [row.min_kt_ratio_geo_over_ref_secant for row in layer_rows]
        ),
        worst_layer_by_mean_kt_ratio_geo_over_ref_secant=(
            None if worst_mean_kt_row is None else int(worst_mean_kt_row.profile_layer_index + 1)
        ),
        worst_layer_mean_kt_ratio_geo_over_ref_secant=(
            None if worst_mean_kt_row is None else worst_mean_kt_row.mean_kt_ratio_geo_over_ref_secant
        ),
        equivalent_stiffness_min=layer_sweep.summary.equivalent_stiffness_min,
        equivalent_stiffness_max=layer_sweep.summary.equivalent_stiffness_max,
        dominant_layer_by_mean_compliance=layer_sweep.summary.dominant_layer_by_mean_compliance,
        dominant_layer_mean_compliance=layer_sweep.summary.dominant_layer_mean_compliance,
        warnings=warnings,
        layers=layer_rows,
    )
    result = CaseTruthLayerAuditResult(
        geowave_run_dir=run_dir,
        deepsoil_db_path=deepsoil_case.db_path,
        artifacts=CaseTruthLayerAuditArtifacts(
            output_dir=out_dir,
            summary_json=summary_json,
            summary_md=summary_md,
            layer_csv=layer_csv,
            motion_csv=motion_csv,
            layer_sweep_summary_json=layer_sweep.artifacts.summary_json,
            layer_sweep_summary_csv=layer_sweep.artifacts.layer_summary_csv,
        ),
        summary=summary,
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    warning_lines = [f"- {item}" for item in warnings] if warnings else ["- none"]
    layer_lines = [
        (
            f"- Layer {row.profile_layer_index + 1} @ `{row.depth_m:.3f}` m: "
            f"gamma ratio `{row.gamma_max_ratio_geo_over_ref}`, "
            f"PGA ratio `{row.pga_g_ratio_geo_over_ref}`, "
            f"stress-ratio `{row.max_stress_ratio_geo_over_ref}`, "
            f"stress proxy `{row.stress_proxy_ratio_geo_over_ref}`, "
            f"secant proxy `{row.secant_proxy_ratio_geo_over_ref}`, "
            f"tau peak proxy `{row.tau_peak_proxy_ratio_geo_over_ref}`, "
            f"mean kt/ref secant `{row.mean_kt_ratio_geo_over_ref_secant}`, "
            f"mean compliance `{row.mean_compliance_fraction}`, "
            f"mean kt `{row.mean_kt_kpa}` kPa"
        )
        for row in layer_rows
    ]
    summary_md.write_text(
        "\n".join(
            [
                "# Case Truth Compare",
                "",
                f"- Label: `{label}`",
                f"- GeoWave run: `{run_dir}`",
                f"- DeepSoil DB: `{deepsoil_case.db_path}`",
                f"- Layer sweep summary: `{layer_sweep.artifacts.summary_json}`",
                "",
                "## Profile Truth",
                f"- gamma_max NRMSE: `{summary.gamma_max_nrmse}`",
                f"- gamma_max mean ratio Geo/Ref: `{summary.gamma_max_mean_ratio_geo_over_ref}`",
                f"- PGA profile NRMSE: `{summary.pga_profile_nrmse}`",
                f"- PGA mean ratio Geo/Ref: `{summary.pga_profile_mean_ratio_geo_over_ref}`",
                f"- max displacement NRMSE: `{summary.max_displacement_nrmse}`",
                f"- max displacement mean ratio Geo/Ref: `{summary.max_displacement_mean_ratio_geo_over_ref}`",
                f"- max strain NRMSE: `{summary.max_strain_nrmse}`",
                f"- max strain mean ratio Geo/Ref: `{summary.max_strain_mean_ratio_geo_over_ref}`",
                f"- max stress ratio NRMSE: `{summary.max_stress_ratio_nrmse}`",
                f"- max stress ratio mean ratio Geo/Ref: `{summary.max_stress_ratio_mean_ratio_geo_over_ref}`",
                f"- effective stress NRMSE: `{summary.effective_stress_nrmse}`",
                f"- effective stress mean ratio Geo/Ref: `{summary.effective_stress_mean_ratio_geo_over_ref}`",
                f"- stress proxy NRMSE: `{summary.stress_proxy_nrmse}`",
                f"- stress proxy mean ratio Geo/Ref: `{summary.stress_proxy_mean_ratio_geo_over_ref}`",
                f"- secant proxy NRMSE: `{summary.secant_proxy_nrmse}`",
                f"- secant proxy mean ratio Geo/Ref: `{summary.secant_proxy_mean_ratio_geo_over_ref}`",
                f"- tau peak proxy mean ratio Geo/Ref: `{summary.tau_peak_proxy_mean_ratio_geo_over_ref}`",
                f"- mean kt / ref secant mean ratio: `{summary.mean_kt_ratio_geo_over_ref_secant_mean}`",
                f"- min kt / ref secant mean ratio: `{summary.min_kt_ratio_geo_over_ref_secant_mean}`",
                "",
                "## Layer Sweep",
                f"- equivalent stiffness min: `{summary.equivalent_stiffness_min}`",
                f"- equivalent stiffness max: `{summary.equivalent_stiffness_max}`",
                f"- dominant layer by mean compliance: `{summary.dominant_layer_by_mean_compliance}`",
                f"- dominant layer mean compliance: `{summary.dominant_layer_mean_compliance}`",
                f"- worst layer by mean kt / ref secant: `{summary.worst_layer_by_mean_kt_ratio_geo_over_ref_secant}`",
                f"- worst layer mean kt / ref secant ratio: `{summary.worst_layer_mean_kt_ratio_geo_over_ref_secant}`",
                "",
                "## Layer Rows",
                *layer_lines,
                "",
                "## Warnings",
                *warning_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return result
