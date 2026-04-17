from __future__ import annotations

import csv
import json
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
from dsra1d.motion import effective_input_acceleration, load_motion
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
    incident_force_rms: float | None
    dashpot_force_rms: float | None
    net_boundary_force_rms: float | None
    dashpot_to_incident_rms_ratio: float | None
    net_to_incident_rms_ratio: float | None
    dashpot_incident_corr: float | None
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
    applied_input = raw_input.copy()

    def _column(values: list[float]) -> tuple[float | None, float | None]:
        if not values:
            return None, None
        arr = np.asarray(values, dtype=np.float64)
        return float(np.max(np.abs(arr))), float(np.sqrt(np.mean(arr * arr)))

    incident = []
    dashpot = []
    net_force = []
    base_velocity = []
    base_disp = []
    surface_acc = []
    impedance = []
    for row in rows:
        for raw, target in (
            (row.get("incident_force"), incident),
            (row.get("dashpot_force"), dashpot),
            (row.get("net_boundary_force"), net_force),
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
        incident_force_rms=incident_rms,
        dashpot_force_rms=dashpot_rms,
        net_boundary_force_rms=net_rms,
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
    surface_pga_g_a: float | None
    surface_pga_g_b: float | None
    surface_pga_ratio_b_over_a: float | None
    surface_psa_nrmse: float | None
    surface_psa_peak_g_a: float | None
    surface_psa_peak_g_b: float | None
    surface_psa_peak_ratio_b_over_a: float | None
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
    peak_period_shift_pct = _safe_pct_shift(peak_period_b, peak_period_a)
    return nrmse, peak_a, peak_b, peak_period_a, peak_period_b if peak_period_shift_pct is None else peak_period_b


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

    raw_input_psa_nrmse = None
    if store_a.acc_input.size > 1 and store_b.acc_input.size > 1:
        periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
        psa_a = compute_spectra(store_a.acc_input, store_a.input_dt_s, damping=damping, periods=periods).psa
        psa_b = compute_spectra(store_b.acc_input, store_b.input_dt_s, damping=damping, periods=periods).psa
        raw_input_psa_nrmse = _compare_metric_nrmse(np.asarray(psa_a), np.asarray(psa_b))

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
        surface_pga_g_a=surface_pga_g_a,
        surface_pga_g_b=surface_pga_g_b,
        surface_pga_ratio_b_over_a=_safe_ratio(surface_pga_g_b, surface_pga_g_a),
        surface_psa_nrmse=surface_psa_nrmse,
        surface_psa_peak_g_a=surface_psa_peak_g_a,
        surface_psa_peak_g_b=surface_psa_peak_g_b,
        surface_psa_peak_ratio_b_over_a=_safe_ratio(surface_psa_peak_g_b, surface_psa_peak_g_a),
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
                "",
                "## Surface Response",
                f"- Surface history NRMSE: `{summary.surface_history_nrmse}`",
                f"- Surface history corrcoef: `{summary.surface_history_corrcoef}`",
                f"- Surface PGA (g): `{summary.surface_pga_g_a}` -> `{summary.surface_pga_g_b}`",
                f"- Surface PGA ratio B/A: `{summary.surface_pga_ratio_b_over_a}`",
                f"- Surface PSA peak (g): `{summary.surface_psa_peak_g_a}` -> `{summary.surface_psa_peak_g_b}`",
                f"- Surface PSA peak ratio B/A: `{summary.surface_psa_peak_ratio_b_over_a}`",
                f"- Surface peak period (s): `{summary.surface_peak_period_s_a}` -> `{summary.surface_peak_period_s_b}`",
                f"- Surface peak period shift B vs A (%): `{summary.surface_peak_period_shift_pct_b_vs_a}`",
                f"- Surface PSA NRMSE: `{summary.surface_psa_nrmse}`",
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
