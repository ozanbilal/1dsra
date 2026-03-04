from __future__ import annotations

import base64
import json
import os
import sqlite3
from pathlib import Path
from typing import Literal, cast

import numpy as np
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from dsra1d.config import (
    available_config_templates,
    get_config_template_payload,
    load_project_config,
    write_config_template,
)
from dsra1d.config.models import (
    BaselineMode,
    BoundaryCondition,
    MaterialType,
    MotionConfig,
    ProjectConfig,
    ScaleMode,
)
from dsra1d.interop.opensees import probe_opensees_executable, resolve_opensees_executable
from dsra1d.materials import (
    bounded_damping_from_reduction,
    generate_masing_loop,
    gqh_modulus_reduction,
    mkz_modulus_reduction,
)
from dsra1d.motion import import_peer_at2_to_csv, load_motion, load_motion_series, preprocess_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import compute_spectra, compute_transfer_function
from dsra1d.types import Motion
from dsra1d.units import accel_factor_to_si

RunBackendMode = Literal["config", "auto", "opensees", "mock", "linear", "eql", "nonlinear"]
ResolvedBackend = Literal["opensees", "mock", "linear", "eql", "nonlinear"]
OPENSEES_EXE_ENV = "DSRA1D_OPENSEES_EXE_OVERRIDE"


class RunRequest(BaseModel):
    config_path: str
    motion_path: str
    output_root: str = "out/web"
    backend: RunBackendMode = "config"
    opensees_executable: str | None = None


class RunResponse(BaseModel):
    run_id: str
    output_dir: str
    status: str
    message: str
    backend: str


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


class ConfigTemplateRequest(BaseModel):
    template: Literal[
        "effective-stress",
        "effective-stress-strict-plus",
        "pm4sand-calibration",
        "pm4silt-calibration",
        "mkz-gqh-mock",
        "mkz-gqh-eql",
        "mkz-gqh-nonlinear",
    ] = "effective-stress"
    output_dir: str = ""
    file_name: str = ""


class ConfigTemplateResponse(BaseModel):
    template: str
    config_path: str
    status: str
    message: str


class WizardAnalysisStep(BaseModel):
    project_name: str = "wizard-project"
    boundary_condition: BoundaryCondition = BoundaryCondition.ELASTIC_HALFSPACE
    solver_backend: RunBackendMode = "opensees"
    pm4_validation_profile: Literal["basic", "strict", "strict_plus"] = "basic"


class WizardLayer(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    thickness_m: float = Field(gt=0.0)
    unit_weight_kn_m3: float = Field(gt=0.0, alias="unit_weight_kN_m3")
    vs_m_s: float = Field(gt=0.0)
    material: MaterialType
    material_params: dict[str, float] = Field(default_factory=dict)
    material_optional_args: list[float] = Field(default_factory=list)


class WizardProfileStep(BaseModel):
    layers: list[WizardLayer] = Field(default_factory=list)


class WizardMotionStep(BaseModel):
    units: str = "m/s2"
    dt_override: float | None = Field(default=None, gt=0.0)
    baseline: BaselineMode = BaselineMode.REMOVE_MEAN
    scale_mode: ScaleMode = ScaleMode.NONE
    scale_factor: float | None = None
    target_pga: float | None = None
    motion_path: str = ""


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
    opensees_executable: str = "OpenSees"
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


class MotionProcessRequest(BaseModel):
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
    spectra_preview: dict[str, list[float]]
    status: str


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


class ParitySuiteStatus(BaseModel):
    suite: str
    all_passed: bool
    ran: int
    total_cases: int
    skipped: int
    skipped_backend: int
    execution_coverage: float
    backend_ready: bool
    backend_fingerprint_ok: bool
    binary_fingerprint: str = ""
    block_reasons: list[str] = Field(default_factory=list)
    skip_reasons: dict[str, int] = Field(default_factory=dict)


class ParityLatestResponse(BaseModel):
    found: bool
    report_path: str = ""
    suite: str = ""
    generated_utc: str = ""
    suites: list[ParitySuiteStatus] = Field(default_factory=list)


class ScientificConfidenceRow(BaseModel):
    suite: str
    case_count: int
    reference_basis: str
    tolerance_policy: str
    binary_fingerprint: str
    last_verified_utc: str
    confidence_tier: str
    status_notes: str = ""


class ScientificConfidenceResponse(BaseModel):
    source_path: str
    last_updated: str = ""
    rows: list[ScientificConfidenceRow] = Field(default_factory=list)


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


class ResultProfileSummaryResponse(BaseModel):
    run_id: str
    layer_count: int
    total_thickness_m: float
    ru_max: float | None = None
    delta_u_max: float | None = None
    sigma_v_eff_min: float | None = None
    layers: list[ResultProfileLayerRow] = Field(default_factory=list)


class BackendProbeResponse(BaseModel):
    requested: str
    resolved: str | None = None
    available: bool
    version: str = ""
    error: str = ""
    binary_sha256: str | None = None


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


def _discover_opensees_executable() -> Path | None:
    override = os.getenv(OPENSEES_EXE_ENV, "").strip()
    if override:
        resolved = resolve_opensees_executable(override)
        if resolved is not None:
            return resolved.resolve()

    resolved_default = resolve_opensees_executable("OpenSees")
    if resolved_default is not None:
        return resolved_default.resolve()

    home = Path.home()
    candidate_roots = [home / "tools" / "opensees", _repo_root() / ".tools" / "opensees"]
    for root in candidate_roots:
        if not root.exists():
            continue
        candidates = sorted(root.glob("**/OpenSees.exe"))
        if candidates:
            return candidates[0].resolve()
    return None


def _effective_opensees_executable(raw_value: str | None) -> str:
    raw = (raw_value or "").strip()
    if len(raw) >= 2 and ((raw[0] == raw[-1] == '"') or (raw[0] == raw[-1] == "'")):
        raw = raw[1:-1].strip()
    raw = raw.strip("\"'") or "OpenSees"
    if raw != "OpenSees":
        return raw
    discovered = _discover_opensees_executable()
    if discovered is not None:
        return str(discovered)
    return raw


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


def _resolve_output_root(raw: str) -> Path:
    text = raw.strip()
    if not text:
        return _default_output_root()
    out = Path(text).expanduser()
    if out.is_absolute():
        return out.resolve()
    return (_repo_root() / out).resolve()


def _collect_runs(output_root: Path) -> list[Path]:
    if not output_root.exists() or not output_root.is_dir():
        return []
    runs: list[Path] = []
    for p in sorted(output_root.iterdir()):
        if not p.is_dir():
            continue
        if (
            (p / "results.h5").exists()
            and (p / "results.sqlite").exists()
            and (p / "run_meta.json").exists()
        ):
            runs.append(p)
    return runs


def _looks_like_run_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return (
        (path / "run_meta.json").exists()
        and (path / "results.h5").exists()
        and (path / "results.sqlite").exists()
    )


def _resolve_run_dir(run_id: str, output_root: str) -> Path:
    if output_root.strip():
        preferred = _safe_real_path(output_root) / run_id
    else:
        preferred = _default_output_root() / run_id
    if _looks_like_run_dir(preferred):
        return preferred

    out_root = _repo_root() / "out"
    candidates: list[Path] = []
    if out_root.exists():
        for candidate in out_root.rglob(run_id):
            if _looks_like_run_dir(candidate):
                candidates.append(candidate.resolve())
    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    if preferred.exists() and preferred.is_dir():
        return preferred
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


def _extract_suite_reports(report: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    suite = str(report.get("suite", "")).strip()
    if suite == "release-signoff":
        sub_raw = report.get("subreports")
        if isinstance(sub_raw, dict):
            out: list[tuple[str, dict[str, object]]] = []
            for key, value in sub_raw.items():
                if isinstance(value, dict):
                    out.append((str(key), dict(value)))
            if out:
                return out
    return [(suite or "unknown", report)]


def _suite_skip_reasons(cases: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        if str(case.get("status", "")).strip().lower() != "skipped":
            continue
        skip_kind = str(case.get("skip_kind", "")).strip()
        reason = str(case.get("reason", "")).strip()
        key = skip_kind or reason or "unknown_skip"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _suite_parity_status(suite: str, report: dict[str, object]) -> ParitySuiteStatus:
    cases_raw = report.get("cases")
    cases = [c for c in cases_raw if isinstance(c, dict)] if isinstance(cases_raw, list) else []
    skip_reasons = _suite_skip_reasons(cases)
    backend_probe = report.get("backend_probe")
    backend_probe_dict = backend_probe if isinstance(backend_probe, dict) else {}
    binary_fingerprint = str(backend_probe_dict.get("binary_sha256", "")).strip().lower()

    all_passed = bool(report.get("all_passed", False))
    skipped = _as_int(report.get("skipped", 0), 0)
    skipped_backend = _as_int(report.get("skipped_backend", 0), 0)
    backend_ready = bool(report.get("backend_ready", True))
    backend_fingerprint_ok = bool(report.get("backend_fingerprint_ok", True))
    block_reasons: list[str] = []
    if not all_passed:
        block_reasons.append("all_passed=false")
    if skipped > 0:
        block_reasons.append("skipped>0")
    if skipped_backend > 0:
        block_reasons.append("skipped_backend>0")
    if not backend_ready:
        block_reasons.append("backend_ready=false")
    if not backend_fingerprint_ok:
        block_reasons.append("backend_fingerprint_ok=false")

    return ParitySuiteStatus(
        suite=suite,
        all_passed=all_passed,
        ran=_as_int(report.get("ran", 0), 0),
        total_cases=_as_int(report.get("total_cases", len(cases)), 0),
        skipped=skipped,
        skipped_backend=skipped_backend,
        execution_coverage=_as_float(report.get("execution_coverage", 0.0), 0.0),
        backend_ready=backend_ready,
        backend_fingerprint_ok=backend_fingerprint_ok,
        binary_fingerprint=binary_fingerprint,
        block_reasons=block_reasons,
        skip_reasons=skip_reasons,
    )


def _is_parity_report(report: dict[str, object]) -> bool:
    suite = str(report.get("suite", "")).strip()
    if suite in {"opensees-parity", "release-signoff"}:
        return True
    sub_raw = report.get("subreports")
    if isinstance(sub_raw, dict) and "opensees-parity" in sub_raw:
        return True
    return False


def _find_latest_parity_report(output_root: Path) -> tuple[Path, dict[str, object]] | None:
    if not output_root.exists() or not output_root.is_dir():
        return None
    candidates = sorted(
        output_root.rglob("benchmark_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        report = _json_mapping(path)
        if report and _is_parity_report(report):
            return path, report
    return None


def _parse_scientific_confidence_matrix(path: Path) -> tuple[str, list[ScientificConfidenceRow]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    last_updated = ""
    for line in lines:
        if line.lower().startswith("last updated:"):
            last_updated = line.split(":", 1)[1].strip()
            break

    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 3:
        return last_updated, []
    header = [c.strip().lower() for c in table_lines[0].strip().strip("|").split("|")]
    rows: list[ScientificConfidenceRow] = []
    for line in table_lines[2:]:
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) != len(header):
            continue
        row_map = {header[i]: cols[i] for i in range(len(header))}
        suite = row_map.get("suite", "").strip()
        if not suite:
            continue
        case_count_raw = row_map.get("case_count", row_map.get("case count", "0"))
        case_count = _as_int(case_count_raw.replace("`", ""), 0)
        rows.append(
            ScientificConfidenceRow(
                suite=suite,
                case_count=case_count,
                reference_basis=row_map.get("reference_basis", row_map.get("reference basis", "")),
                tolerance_policy=row_map.get(
                    "tolerance_policy", row_map.get("tolerance policy", "")
                ),
                binary_fingerprint=row_map.get(
                    "binary_fingerprint", row_map.get("binary fingerprint", "")
                ),
                last_verified_utc=row_map.get(
                    "last_verified_utc", row_map.get("last verified utc", "")
                ),
                confidence_tier=row_map.get(
                    "confidence_tier", row_map.get("confidence tier", "")
                ),
                status_notes=row_map.get("status_notes", row_map.get("status notes", "")),
            )
        )
    return last_updated, rows


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


def _read_profile_layer_summary(sqlite_path: Path) -> list[ResultProfileLayerRow]:
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
        if _table_exists(conn, "eql_layers"):
            eql_rows = conn.execute(
                "SELECT layer_idx, gamma_max FROM eql_layers ORDER BY layer_idx ASC"
            ).fetchall()
            for idx, gamma in eql_rows:
                try:
                    gamma_by_idx[int(idx)] = float(gamma)
                except (TypeError, ValueError):
                    continue

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
            gamma_max = gamma_by_idx.get(layer_idx)
            if gamma_max is None:
                gamma_max = gamma_by_idx.get(layer_idx + 1)

            layers.append(
                ResultProfileLayerRow(
                    idx=layer_idx,
                    name=layer_name,
                    material=str(material),
                    thickness_m=t_m,
                    unit_weight_kn_m3=float(unit_weight),
                    vs_m_s=float(vs),
                    z_top_m=float(z_top_m),
                    z_bottom_m=float(z_bottom_m),
                    n_sub=max(1, int(n_sub)),
                    gamma_max=float(gamma_max) if gamma_max is not None else None,
                )
            )
        return layers
    finally:
        conn.close()


def _read_convergence(sqlite_path: Path, run_dir: Path | None = None) -> dict[str, object]:
    if not sqlite_path.exists():
        if run_dir is None:
            return {"available": False}
        meta_raw = _read_run_meta_raw(run_dir)
        diag_raw = meta_raw.get("opensees_diagnostics")
        if isinstance(diag_raw, dict):
            diag = dict(diag_raw)
            diag["available"] = True
            diag.setdefault("source", "opensees_logs")
            return diag
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
            if run_dir is not None:
                meta_raw = _read_run_meta_raw(run_dir)
                diag_raw = meta_raw.get("opensees_diagnostics")
                if isinstance(diag_raw, dict):
                    diag = dict(diag_raw)
                    diag["available"] = True
                    diag.setdefault("source", "opensees_logs")
                    return diag
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

    # PM4/effective-stress layers are shown with an MKZ proxy until true stress-strain
    # recorder channels are available from backend outputs.
    gamma_ref = 0.0012 if material == MaterialType.PM4SAND else 0.0018
    if material == MaterialType.ELASTIC:
        gamma_ref = 0.0005
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
        proxy_used = proxy_used or is_proxy

        gamma_ref = float(loop_params.get("gamma_ref", 0.001))
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
        tau_peak = float(np.max(np.abs(loop.stress))) if loop.stress.size > 0 else 0.0
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
                gqh_modulus_reduction(
                    np.array([gamma_a], dtype=np.float64),
                    gamma_ref=gamma_ref,
                    a1=float(loop_params.get("a1", 1.0)),
                    a2=float(loop_params.get("a2", 0.0)),
                    m=float(loop_params.get("m", 1.0)),
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
                strain_amplitude=float(loop.strain_amplitude),
                loop_energy=float(loop.energy_dissipation),
                mobilized_strength_ratio=mobilized_ratio,
                g_over_gmax=g_over_gmax,
                damping_proxy=damping_proxy,
                strain=_downsample_series(loop.strain, max_points=max_points),
                stress=_downsample_series(loop.stress, max_points=max_points),
            )
        )

    if cfg is None:
        note_parts.append("Config snapshot not found; using sqlite layer fallback.")
    if proxy_used:
        note_parts.append(
            "PM4/elastic layers shown as MKZ proxies until native recorder channels are added."
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
    opensees = payload.get("opensees")
    opensees_dict = opensees if isinstance(opensees, dict) else {}

    layers_raw = profile_dict.get("layers")
    layers_in = layers_raw if isinstance(layers_raw, list) else []
    layers_out: list[dict[str, object]] = []
    for idx, item in enumerate(layers_in):
        if not isinstance(item, dict):
            continue
        material_raw = str(item.get("material", "pm4sand")).strip().lower()
        material = material_raw if material_raw in valid_material else "pm4sand"
        layers_out.append(
            {
                "name": str(item.get("name", f"Layer-{idx + 1}")),
                "thickness_m": _as_non_negative_float(item.get("thickness_m"), 1.0),
                "unit_weight_kN_m3": _as_non_negative_float(
                    item.get("unit_weight_kN_m3"), 18.0
                ),
                "vs_m_s": _as_non_negative_float(item.get("vs_m_s"), 150.0),
                "material": material,
                "material_params": _numeric_dict(item.get("material_params")),
                "material_optional_args": _numeric_list(
                    item.get("material_optional_args")
                ),
            }
        )
    if not layers_out:
        layers_out = [
            {
                "name": "Layer-1",
                "thickness_m": 5.0,
                "unit_weight_kN_m3": 18.0,
                "vs_m_s": 180.0,
                "material": "pm4sand",
                "material_params": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
                "material_optional_args": [],
            }
        ]

    boundary_raw = str(
        payload.get(
            "boundary_condition",
            BoundaryCondition.ELASTIC_HALFSPACE.value,
        )
    )
    boundary = (
        boundary_raw
        if boundary_raw in valid_boundary
        else BoundaryCondition.ELASTIC_HALFSPACE.value
    )

    baseline_raw = str(motion_dict.get("baseline", BaselineMode.REMOVE_MEAN.value))
    baseline = (
        baseline_raw if baseline_raw in valid_baseline else BaselineMode.REMOVE_MEAN.value
    )

    scale_mode_raw = str(motion_dict.get("scale_mode", ScaleMode.NONE.value))
    scale_mode = (
        scale_mode_raw if scale_mode_raw in valid_scale_mode else ScaleMode.NONE.value
    )

    pm4_profile_raw = str(analysis_dict.get("pm4_validation_profile", "basic"))
    pm4_profile = (
        pm4_profile_raw if pm4_profile_raw in {"basic", "strict", "strict_plus"} else "basic"
    )

    backend_raw = str(analysis_dict.get("solver_backend", "opensees"))
    if backend_raw not in {"config", "auto", "opensees", "mock", "linear", "eql", "nonlinear"}:
        backend_raw = "opensees"

    damping_mode_raw = str(analysis_dict.get("damping_mode", "frequency_independent"))
    damping_mode = (
        damping_mode_raw
        if damping_mode_raw in {"frequency_independent", "rayleigh"}
        else "frequency_independent"
    )
    rayleigh_mode_1 = _as_positive_float_or_none(analysis_dict.get("rayleigh_mode_1_hz"))
    rayleigh_mode_2 = _as_positive_float_or_none(analysis_dict.get("rayleigh_mode_2_hz"))
    rayleigh_update = bool(analysis_dict.get("rayleigh_update_matrix", False))

    requested_opensees_executable = str(opensees_dict.get("executable", "OpenSees"))

    wizard_payload = {
        "analysis_step": {
            "project_name": str(payload.get("project_name", "wizard-project")),
            "boundary_condition": boundary,
            "solver_backend": backend_raw,
            "pm4_validation_profile": pm4_profile,
        },
        "profile_step": {"layers": layers_out},
        "motion_step": {
            "units": str(motion_dict.get("units", "m/s2")),
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
            "opensees_executable": _effective_opensees_executable(
                requested_opensees_executable
            ),
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
        "effective-stress"
        if "effective-stress" in template_defaults
        else (template_names[0] if template_names else "")
    )
    default_wizard = template_defaults.get(default_template)
    if default_wizard is None:
        default_wizard = _wizard_defaults_from_project_payload(
            get_config_template_payload("effective-stress")
        )

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
                "pm4_validation_profile",
            ],
            "profile_step": ["layers[]"],
            "motion_step": [
                "motion_path",
                "units",
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
                "opensees_executable",
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
            "solver_backend": ["config", "auto", "opensees", "mock", "linear", "eql", "nonlinear"],
            "baseline": [e.value for e in BaselineMode],
            "scale_mode": [e.value for e in ScaleMode],
            "material": [e.value for e in MaterialType],
            "pm4_validation_profile": ["basic", "strict", "strict_plus"],
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
            }
        )

    payload: dict[str, object] = {
        "project_name": req.analysis_step.project_name,
        "profile": {"layers": layers},
        "boundary_condition": req.analysis_step.boundary_condition.value,
        "analysis": {
            "dt": req.control_step.dt,
            "f_max": req.control_step.f_max,
            "solver_backend": req.analysis_step.solver_backend,
            "pm4_validation_profile": req.analysis_step.pm4_validation_profile,
            "damping_mode": req.damping_step.mode,
            "rayleigh_mode_1_hz": mode_1,
            "rayleigh_mode_2_hz": mode_2,
            "rayleigh_update_matrix": req.damping_step.update_matrix,
            "timeout_s": req.control_step.timeout_s,
            "retries": req.control_step.retries,
        },
        "motion": {
            "units": req.motion_step.units,
            "baseline": req.motion_step.baseline.value,
            "scale_mode": req.motion_step.scale_mode.value,
            "scale_factor": req.motion_step.scale_factor,
            "target_pga": req.motion_step.target_pga,
        },
        "output": {
            "write_hdf5": req.control_step.write_hdf5,
            "write_sqlite": req.control_step.write_sqlite,
            "parquet_export": req.control_step.parquet_export,
        },
        "opensees": {
            "executable": _effective_opensees_executable(req.control_step.opensees_executable),
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
                message=f"dt={dt_used:.6g}s (recommended≈{(dt_recommended or dt_used):.6g}s).",
            )
        )

    requested_backend = payload.analysis_step.solver_backend
    requested_executable = _effective_opensees_executable(payload.control_step.opensees_executable)
    derived["opensees_requested"] = requested_executable
    if requested_backend in {"opensees", "auto"}:
        probe = probe_opensees_executable(requested_executable)
        derived["opensees_resolved"] = (
            str(probe.resolved) if probe.resolved is not None else None
        )
        derived["opensees_available"] = bool(probe.available)
        if probe.available:
            checks.append(
                WizardSanityCheckItem(
                    name="backend_probe",
                    status="ok",
                    message=f"OpenSees available: {probe.resolved}",
                )
            )
        else:
            msg = f"OpenSees executable not available ({requested_executable})."
            if requested_backend == "opensees":
                checks.append(
                    WizardSanityCheckItem(name="backend_probe", status="blocker", message=msg)
                )
                blockers.append(msg)
            else:
                checks.append(
                    WizardSanityCheckItem(name="backend_probe", status="warning", message=msg)
                )
                warnings.append(f"{msg} Auto backend may fall back to mock.")

    layer_materials = [layer.material.value for layer in payload.profile_step.layers]
    if requested_backend == "opensees":
        unsupported = sorted({m for m in layer_materials if m in {"mkz", "gqh"}})
        if unsupported:
            msg = (
                "OpenSees backend currently supports pm4sand/pm4silt/elastic in v1; "
                f"found unsupported materials: {', '.join(unsupported)}."
            )
            checks.append(
                WizardSanityCheckItem(
                    name="backend_material_compatibility",
                    status="blocker",
                    message=msg,
                )
            )
            blockers.append(msg)
        else:
            checks.append(
                WizardSanityCheckItem(
                    name="backend_material_compatibility",
                    status="ok",
                    message="Layer materials are compatible with OpenSees v1 backend.",
                )
            )
    else:
        checks.append(
            WizardSanityCheckItem(
                name="backend_material_compatibility",
                status="ok",
                message=f"Backend '{requested_backend}' does not require PM4-only material gate.",
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
    *,
    config_backend: str,
    executable: str,
) -> tuple[ResolvedBackend, str]:
    def normalize(raw: str) -> ResolvedBackend:
        if raw not in {"opensees", "mock", "linear", "eql", "nonlinear"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported config solver backend: {raw}",
            )
        return cast(ResolvedBackend, raw)

    if requested == "config":
        if config_backend == "auto":
            resolved = resolve_opensees_executable(executable)
            if resolved is None:
                return "mock", "mock (config:auto fallback: OpenSees missing)"
            return "opensees", f"opensees ({resolved})"
        normalized = normalize(config_backend)
        return normalized, normalized

    if requested == "auto":
        if config_backend in {"auto", "opensees"}:
            resolved = resolve_opensees_executable(executable)
            if resolved is None:
                return "mock", "mock (auto-fallback: OpenSees missing)"
            return "opensees", f"opensees ({resolved})"
        normalized = normalize(config_backend)
        return normalized, normalized

    if requested == "opensees":
        resolved = resolve_opensees_executable(executable)
        if resolved is None:
            raise HTTPException(
                status_code=400,
                detail=f"OpenSees executable not found: {executable}",
            )
        return "opensees", f"opensees ({resolved})"

    if requested in {"mock", "linear", "eql", "nonlinear"}:
        return requested, f"{requested} (forced)"

    raise HTTPException(status_code=400, detail=f"Unsupported backend mode: {requested}")


def create_app() -> FastAPI:
    app = FastAPI(title="StrataWave Web API", version="0.1.0")
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/backend/opensees/probe", response_model=BackendProbeResponse)
    def backend_probe_opensees(
        executable: str = Query(default="OpenSees"),
    ) -> BackendProbeResponse:
        effective_executable = _effective_opensees_executable(executable)
        probe = probe_opensees_executable(effective_executable)
        return BackendProbeResponse(
            requested=effective_executable,
            resolved=str(probe.resolved) if probe.resolved is not None else None,
            available=bool(probe.available),
            version=str(probe.version or ""),
            error=str(probe.stderr or ""),
            binary_sha256=probe.binary_sha256 or None,
        )

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
            )
            dt_s = _estimate_dt(np.asarray(t_raw, dtype=np.float64))
            factor = accel_factor_to_si(payload.units_hint)
            acc_si = np.asarray(acc_raw, dtype=np.float64) * factor

            cfg = MotionConfig(
                units=payload.units_hint,
                baseline=payload.baseline_mode,
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
            acc_proc = np.asarray(processed.acc, dtype=np.float64)
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

            vel = np.cumsum(acc_proc, dtype=np.float64) * float(processed.dt)
            disp = np.cumsum(vel, dtype=np.float64) * float(processed.dt)
            arias = (
                np.cumsum(acc_proc**2, dtype=np.float64)
                * float(processed.dt)
                * np.pi
                / (2.0 * 9.80665)
            )
            spectra = compute_spectra(acc_proc, dt=float(processed.dt), damping=0.05)
            freq_hz, fas_ratio = compute_transfer_function(acc_si, acc_proc, dt=float(processed.dt))
            n = int(acc_proc.size)
            fft_raw = (
                np.abs(np.fft.rfft(acc_si[:n])) if n > 1 else np.array([0.0], dtype=np.float64)
            )
            fft_proc = (
                np.abs(np.fft.rfft(acc_proc[:n])) if n > 1 else np.array([0.0], dtype=np.float64)
            )
            freq_fft = (
                np.fft.rfftfreq(n, d=float(processed.dt))
                if n > 1
                else np.array([0.0], dtype=np.float64)
            )

            metrics = {
                "pga": float(np.max(np.abs(acc_proc))) if acc_proc.size > 0 else 0.0,
                "arias": float(arias[-1]) if arias.size > 0 else 0.0,
                "duration_5_95": _safe_duration_5_95(arias, float(processed.dt)),
                "dt_s": float(processed.dt),
                "npts": float(acc_proc.size),
            }
            metrics_path = out_root / f"{stem}_metrics.json"
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

            t_d, acc_d = _downsample_np(t_proc, acc_proc, max_points=2400)
            _, vel_d = _downsample_np(t_proc, vel, max_points=2400)
            _, disp_d = _downsample_np(t_proc, disp, max_points=2400)
            _, arias_d = _downsample_np(t_proc, arias, max_points=2400)
            p_d, psa_d = _downsample_np(spectra.periods, spectra.psa, max_points=800)
            f_d, fr_d = _downsample_np(freq_hz, fas_ratio, max_points=1200)
            ff_d, raw_d = _downsample_np(freq_fft, fft_raw, max_points=1200)
            _, proc_d = _downsample_np(freq_fft, fft_proc, max_points=1200)

            preview = {
                "time_s": [float(v) for v in t_d],
                "acc_m_s2": [float(v) for v in acc_d],
                "vel_m_s": [float(v) for v in vel_d],
                "disp_m": [float(v) for v in disp_d],
                "arias": [float(v) for v in arias_d],
                "period_s": [float(v) for v in p_d],
                "psa_m_s2": [float(v) for v in psa_d],
                "freq_hz": [float(v) for v in f_d],
                "fas_ratio": [float(v) for v in fr_d],
                "fas_raw": [float(v) for v in raw_d],
                "fas_processed": [float(v) for v in proc_d],
                "fas_freq_hz": [float(v) for v in ff_d],
            }

            return MotionProcessResponse(
                processed_motion_path=str(csv_path),
                metrics_path=str(metrics_path),
                metrics=metrics,
                spectra_preview=preview,
                status="ok",
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
                )
            )
        return items

    @app.get("/api/parity/latest", response_model=ParityLatestResponse)
    def parity_latest(output_root: str = Query(default="")) -> ParityLatestResponse:
        root = _safe_real_path(output_root) if output_root else (_repo_root() / "out")
        latest = _find_latest_parity_report(root)
        if latest is None:
            return ParityLatestResponse(found=False)
        path, report = latest
        suite_name = str(report.get("suite", "")).strip()
        generated_utc = str(report.get("generated_utc", "")).strip()
        suite_rows = [
            _suite_parity_status(sub_suite, sub_report)
            for sub_suite, sub_report in _extract_suite_reports(report)
        ]
        return ParityLatestResponse(
            found=True,
            report_path=str(path),
            suite=suite_name,
            generated_utc=generated_utc,
            suites=suite_rows,
        )

    @app.get("/api/science/confidence", response_model=ScientificConfidenceResponse)
    def science_confidence() -> ScientificConfidenceResponse:
        matrix_path = _repo_root() / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
        if not matrix_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Scientific confidence matrix not found: {matrix_path}",
            )
        last_updated, rows = _parse_scientific_confidence_matrix(matrix_path)
        return ScientificConfidenceResponse(
            source_path=str(matrix_path),
            last_updated=last_updated,
            rows=rows,
        )

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
        rs = load_result(run_dir)
        time = rs.time
        acc = rs.acc_surface
        n = int(min(time.size, acc.size))
        if n <= 1:
            raise HTTPException(status_code=400, detail="Run has insufficient signal samples.")
        time_list = [float(v) for v in time[:n]]
        acc_list = [float(v) for v in acc[:n]]
        time_list, acc_list = _downsample_pair(time_list, acc_list, max_points=max_points)

        dt_s = _estimate_dt(rs.time)
        spectra_live = compute_spectra(
            np.asarray(rs.acc_surface, dtype=np.float64),
            dt=dt_s,
            damping=0.05,
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

        pga = float(np.max(np.abs(acc))) if acc.size > 0 else 0.0
        ru_max = float(np.max(rs.ru)) if rs.ru.size > 0 else 0.0
        delta_u_max = float(np.max(rs.delta_u)) if rs.delta_u.size > 0 else 0.0
        sigma_v_eff_min = float(np.min(rs.sigma_v_eff)) if rs.sigma_v_eff.size > 0 else 0.0
        return {
            "run_id": run_id,
            "time_s": time_list,
            "surface_acc_m_s2": acc_list,
            "period_s": period_list,
            "psa_m_s2": psa_list,
            "spectra_source": "recomputed_from_surface_acc",
            "dt_s": float(dt_s),
            "delta_t": float(dt_s),
            "delta_t_s": float(dt_s),
            "freq_hz": freq_list,
            "transfer_abs": tf_list,
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
        layer_rows = _read_profile_layer_summary(sqlite_path)
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

    @app.get("/api/runs/{run_id}/surface-acc.csv")
    def download_surface_csv(
        run_id: str,
        output_root: str = Query(default=""),
    ) -> PlainTextResponse:
        run_dir = _resolve_run_dir(run_id, output_root)
        rs = load_result(run_dir)
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
        rs = load_result(run_dir)
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
            motion_path = _resolve_input_path(payload.motion_path, label="Motion file")
            output_root = _resolve_output_root(payload.output_root)

            cfg = load_project_config(config_path)
            if payload.opensees_executable:
                cfg.opensees.executable = payload.opensees_executable
            cfg.opensees.executable = _effective_opensees_executable(cfg.opensees.executable)
            backend, backend_note = _apply_runtime_backend(
                payload.backend,
                config_backend=cfg.analysis.solver_backend,
                executable=cfg.opensees.executable,
            )
            cfg.analysis.solver_backend = backend
            if backend == "opensees":
                resolved = resolve_opensees_executable(cfg.opensees.executable)
                if resolved is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"OpenSees executable not found: {cfg.opensees.executable}",
                    )
                cfg.opensees.executable = str(resolved)

            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            result = run_analysis(cfg, motion, output_dir=output_root)
            return RunResponse(
                run_id=result.run_id,
                output_dir=str(result.output_dir),
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

    @app.get("/")
    def web_root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    return app


app = create_app()

