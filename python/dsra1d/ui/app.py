from __future__ import annotations

# ruff: noqa: E402
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import yaml

PYTHON_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(PYTHON_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC_ROOT))

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import BoundaryCondition, MaterialType, ProjectConfig, load_project_config
from dsra1d.config.io import write_config_template
from dsra1d.interop.opensees import (
    probe_opensees_executable,
    render_tcl,
    resolve_opensees_executable,
    validate_backend_probe_requirements,
    validate_tcl_script,
)
from dsra1d.materials import (
    bounded_damping_from_reduction,
    generate_masing_loop,
    gqh_modulus_reduction,
    mkz_modulus_reduction,
)
from dsra1d.motion import load_motion, preprocess_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import compute_spectra, render_summary_markdown, summarize_campaign, write_report
from dsra1d.verify import verify_batch, verify_run


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Playfair+Display:wght@600;800&display=swap');
        :root {
          --ink: #1f1d1a;
          --paper: #f4f1e7;
          --copper: #8b4d2a;
          --slate: #2f3a42;
          --mint: #2d6a6a;
        }
        .stApp {
          background:
            radial-gradient(1200px 600px at 90% -20%, rgba(139, 77, 42, 0.24), transparent 60%),
            radial-gradient(1100px 500px at -10% -30%, rgba(45, 106, 106, 0.22), transparent 55%),
            var(--paper);
          color: var(--ink);
        }
        h1, h2, h3, h4, h5 {
          font-family: 'Playfair Display', serif !important;
          letter-spacing: 0.2px;
        }
        .stMarkdown, .stTextInput label, .stButton button, .stSelectbox label {
          font-family: 'IBM Plex Mono', monospace !important;
        }
        .hero {
          background: rgba(255,255,255,0.66);
          border: 1px solid rgba(31, 29, 26, 0.15);
          border-radius: 18px;
          padding: 16px 18px;
          margin-bottom: 12px;
          box-shadow: 0 18px 40px rgba(47, 58, 66, 0.12);
        }
        .chip {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 999px;
          margin-right: 6px;
          margin-top: 6px;
          background: rgba(47, 58, 66, 0.12);
          color: var(--slate);
          font-size: 12px;
        }
        .hero h4 {
          margin: 0 0 8px 0;
          font-size: 20px;
        }
        .hero p {
          margin: 0 0 8px 0;
          word-break: break-all;
          font-size: 12px;
          opacity: 0.85;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_metrics(sqlite_path: Path) -> dict[str, float]:
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = conn.execute("SELECT name, value FROM metrics").fetchall()
    finally:
        conn.close()
    return {name: float(value) for name, value in rows}


def _find_run_dirs(output_root: Path) -> list[Path]:
    if not output_root.exists() or not output_root.is_dir():
        return []
    runs: list[Path] = []
    for p in sorted(output_root.iterdir()):
        if (
            p.is_dir()
            and (p / "results.h5").exists()
            and (p / "results.sqlite").exists()
            and (p / "run_meta.json").exists()
        ):
            runs.append(p)
    return runs


def _status_chip(ok: bool, label_ok: str, label_bad: str) -> str:
    color = "#2d6a6a" if ok else "#8b2d2d"
    text = label_ok if ok else label_bad
    return (
        f"<span style='display:inline-block;padding:3px 10px;border-radius:999px;"
        f"background:{color};color:#fff;font-size:11px;font-family:IBM Plex Mono, monospace;'>"
        f"{text}</span>"
    )


def _render_quick_status(
    *,
    cfg_path: Path,
    motion_path: Path,
    out_dir: Path,
) -> None:
    cfg_ok = cfg_path.exists()
    motion_ok = motion_path.exists()
    out_ok = out_dir.exists() and out_dir.is_dir()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            (
                "<div class='hero'><h4>Config</h4>"
                f"<p>{cfg_path}</p>{_status_chip(cfg_ok, 'Ready', 'Missing')}</div>"
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            (
                "<div class='hero'><h4>Motion</h4>"
                f"<p>{motion_path}</p>{_status_chip(motion_ok, 'Ready', 'Missing')}</div>"
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            (
                "<div class='hero'><h4>Output</h4>"
                f"<p>{out_dir}</p>{_status_chip(out_ok, 'Ready', 'Missing')}</div>"
            ),
            unsafe_allow_html=True,
        )


_MATERIAL_PARAM_DEFAULTS: dict[str, dict[str, float]] = {
    "pm4sand": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
    "pm4silt": {"Su": 35.0, "Su_Rat": 0.25, "G_o": 500.0, "h_po": 0.6},
    "mkz": {
        "gmax": 70000.0,
        "gamma_ref": 0.0012,
        "damping_min": 0.01,
        "damping_max": 0.10,
        "reload_factor": 2.0,
    },
    "gqh": {
        "gmax": 110000.0,
        "gamma_ref": 0.0010,
        "a1": 1.0,
        "a2": 0.45,
        "m": 2.0,
        "damping_min": 0.01,
        "damping_max": 0.12,
        "reload_factor": 1.6,
    },
    "elastic": {"nu": 0.30},
}


def _new_layer_template(index: int) -> dict[str, Any]:
    return {
        "name": f"Layer-{index}",
        "thickness_m": 5.0,
        "unit_weight_kN_m3": 18.0,
        "vs_m_s": 180.0,
        "material": "pm4sand",
        "material_params": dict(_MATERIAL_PARAM_DEFAULTS["pm4sand"]),
        "material_optional_args": [],
    }


def _load_editor_payload_from_path(cfg_path: Path) -> dict[str, Any]:
    cfg = load_project_config(cfg_path)
    payload = cfg.model_dump(mode="json", by_alias=True)
    profile = payload.setdefault("profile", {})
    layers = profile.setdefault("layers", [])
    if not isinstance(layers, list):
        profile["layers"] = []
    return payload


def _write_editor_payload(cfg_path: Path, payload: dict[str, Any]) -> ProjectConfig:
    validated = ProjectConfig.model_validate(payload)
    normalized = validated.model_dump(mode="json", by_alias=True)
    suffix = cfg_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        cfg_path.write_text(yaml.safe_dump(normalized, sort_keys=False), encoding="utf-8")
    elif suffix == ".json":
        cfg_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    else:
        raise ValueError("Config path must end with .yml/.yaml/.json")
    return validated


def _render_visual_config_editor(cfg_path: Path) -> None:
    editor_payload_key = "cfg_editor_payload"
    editor_source_key = "cfg_editor_source"
    source_marker = str(cfg_path)
    with st.expander("Visual Config Editor", expanded=False):
        if st.button("Load Current Config", key="cfg_editor_load", use_container_width=True):
            try:
                st.session_state[editor_payload_key] = _load_editor_payload_from_path(cfg_path)
                st.session_state[editor_source_key] = source_marker
                st.success("Config loaded into visual editor.")
            except Exception as exc:
                st.error(str(exc))

        if (
            editor_payload_key not in st.session_state
            or st.session_state.get(editor_source_key) != source_marker
        ):
            try:
                st.session_state[editor_payload_key] = _load_editor_payload_from_path(cfg_path)
                st.session_state[editor_source_key] = source_marker
            except Exception as exc:
                st.warning(f"Editor initialization failed: {exc}")
                return

        payload_raw = st.session_state.get(editor_payload_key)
        if not isinstance(payload_raw, dict):
            st.warning("Editor payload unavailable.")
            return
        payload = payload_raw

        payload["project_name"] = st.text_input(
            "Project Name",
            str(payload.get("project_name", "StrataWave-project")),
            key="cfg_editor_project_name",
        )

        boundary_options = [bc.value for bc in BoundaryCondition]
        boundary_current = str(payload.get("boundary_condition", boundary_options[0]))
        if boundary_current not in boundary_options:
            boundary_current = boundary_options[0]
        payload["boundary_condition"] = st.selectbox(
            "Boundary Condition",
            options=boundary_options,
            index=boundary_options.index(boundary_current),
            key="cfg_editor_boundary_condition",
        )

        analysis = payload.setdefault("analysis", {})
        motion = payload.setdefault("motion", {})
        analysis_options = ["opensees", "mock", "linear", "eql", "nonlinear"]
        backend_current = str(analysis.get("solver_backend", "opensees"))
        if backend_current not in analysis_options:
            backend_current = "opensees"
        analysis["solver_backend"] = st.selectbox(
            "Solver Backend",
            options=analysis_options,
            index=analysis_options.index(backend_current),
            key="cfg_editor_solver_backend",
        )
        analysis["f_max"] = float(
            st.number_input(
                "f_max (Hz)",
                min_value=1.0,
                value=float(analysis.get("f_max", 25.0)),
                step=1.0,
                key="cfg_editor_fmax",
            )
        )
        analysis["dt"] = float(
            st.number_input(
                "dt (s)",
                min_value=1.0e-5,
                value=float(analysis.get("dt", 0.002)),
                step=0.0005,
                format="%.6f",
                key="cfg_editor_dt",
            )
        )
        motion_units = ["m/s2", "g", "gal", "cm/s2"]
        current_units = str(motion.get("units", "m/s2"))
        if current_units not in motion_units:
            current_units = "m/s2"
        motion["units"] = st.selectbox(
            "Motion Units",
            options=motion_units,
            index=motion_units.index(current_units),
            key="cfg_editor_motion_units",
        )

        profile = payload.setdefault("profile", {})
        layers_raw = profile.setdefault("layers", [])
        if not isinstance(layers_raw, list):
            layers_raw = []
            profile["layers"] = layers_raw
        layers: list[dict[str, Any]] = [layer for layer in layers_raw if isinstance(layer, dict)]
        profile["layers"] = layers

        st.markdown("#### Layers")
        add_col, _ = st.columns([1, 4])
        with add_col:
            if st.button("Add Layer", key="cfg_editor_add_layer", use_container_width=True):
                layers.append(_new_layer_template(len(layers) + 1))
                st.rerun()

        remove_idx: int | None = None
        material_options = [m.value for m in MaterialType]
        for idx, layer in enumerate(layers):
            layer_name = str(layer.get("name", f"Layer-{idx + 1}"))
            with st.expander(f"{idx + 1}. {layer_name}", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    layer["name"] = st.text_input(
                        "name",
                        layer_name,
                        key=f"cfg_editor_layer_{idx}_name",
                    )
                with c2:
                    layer["thickness_m"] = float(
                        st.number_input(
                            "thickness_m",
                            min_value=0.05,
                            value=float(layer.get("thickness_m", 5.0)),
                            step=0.1,
                            key=f"cfg_editor_layer_{idx}_thickness",
                        )
                    )
                with c3:
                    layer["unit_weight_kN_m3"] = float(
                        st.number_input(
                            "unit_weight_kN_m3",
                            min_value=5.0,
                            value=float(layer.get("unit_weight_kN_m3", 18.0)),
                            step=0.1,
                            key=f"cfg_editor_layer_{idx}_gamma",
                        )
                    )
                with c4:
                    layer["vs_m_s"] = float(
                        st.number_input(
                            "vs_m_s",
                            min_value=20.0,
                            value=float(layer.get("vs_m_s", 180.0)),
                            step=5.0,
                            key=f"cfg_editor_layer_{idx}_vs",
                        )
                    )

                material_current = str(layer.get("material", "pm4sand")).lower()
                if material_current not in material_options:
                    material_current = "pm4sand"
                layer["material"] = st.selectbox(
                    "material",
                    options=material_options,
                    index=material_options.index(material_current),
                    key=f"cfg_editor_layer_{idx}_material",
                )
                material = str(layer["material"]).lower()
                params_defaults = _MATERIAL_PARAM_DEFAULTS.get(
                    material,
                    _MATERIAL_PARAM_DEFAULTS["elastic"],
                )
                material_params_raw = layer.get("material_params")
                if not isinstance(material_params_raw, dict):
                    material_params_raw = {}
                material_params = {
                    key: float(material_params_raw.get(key, default))
                    for key, default in params_defaults.items()
                }
                layer["material_params"] = material_params

                for param_key, param_default in params_defaults.items():
                    material_params[param_key] = float(
                        st.number_input(
                            f"{param_key}",
                            value=float(material_params.get(param_key, param_default)),
                            key=f"cfg_editor_layer_{idx}_param_{param_key}",
                            format="%.6f",
                        )
                    )

                optional_raw = layer.get("material_optional_args", [])
                optional_vals = (
                    [float(v) for v in optional_raw]
                    if isinstance(optional_raw, list)
                    else []
                )
                optional_text_default = ", ".join(f"{v:g}" for v in optional_vals)
                optional_text = st.text_input(
                    "material_optional_args (comma-separated)",
                    optional_text_default,
                    key=f"cfg_editor_layer_{idx}_optional",
                )
                parsed_optional: list[float] = []
                parse_failed = False
                for piece in [p.strip() for p in optional_text.split(",") if p.strip()]:
                    try:
                        parsed_optional.append(float(piece))
                    except ValueError:
                        parse_failed = True
                        break
                if parse_failed:
                    st.warning("material_optional_args contains non-numeric value(s).")
                else:
                    layer["material_optional_args"] = parsed_optional

                if st.button("Remove Layer", key=f"cfg_editor_layer_{idx}_remove"):
                    remove_idx = idx

        if remove_idx is not None:
            layers.pop(remove_idx)
            st.rerun()

        save_col, validate_col = st.columns(2)
        with validate_col:
            if st.button("Validate Editor Payload", use_container_width=True):
                try:
                    ProjectConfig.model_validate(payload)
                    st.success("Editor payload is valid.")
                except Exception as exc:
                    st.error(str(exc))
        with save_col:
            if st.button("Save Config File", type="primary", use_container_width=True):
                try:
                    validated = _write_editor_payload(cfg_path, payload)
                    st.session_state[editor_payload_key] = validated.model_dump(
                        mode="json",
                        by_alias=True,
                    )
                    st.success(f"Config saved: {cfg_path}")
                except Exception as exc:
                    st.error(str(exc))


def _run_benchmark_with_optional_override(
    suite: str,
    output_dir: Path,
    opensees_executable: str,
    require_backend_version_regex: str,
    require_backend_sha256: str,
) -> dict[str, Any]:
    env_key = "DSRA1D_OPENSEES_EXE_OVERRIDE"
    old_value = os.environ.get(env_key)
    try:
        exe = opensees_executable.strip()
        if exe:
            os.environ[env_key] = exe
        return run_benchmark_suite(
            suite=suite,
            output_dir=output_dir,
            require_backend_version_regex=require_backend_version_regex.strip() or None,
            require_backend_sha256=require_backend_sha256.strip().lower() or None,
        )
    finally:
        if opensees_executable.strip():
            if old_value is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old_value


def _apply_runtime_backend(
    cfg: ProjectConfig,
    *,
    backend_mode: str,
    opensees_executable: str,
) -> tuple[ProjectConfig, str]:
    cfg_run = cfg.model_copy(deep=True)
    exe_override = opensees_executable.strip()
    if exe_override:
        cfg_run.opensees.executable = exe_override

    if backend_mode == "mock":
        cfg_run.analysis.solver_backend = "mock"
        return cfg_run, "mock (forced)"

    if backend_mode == "linear":
        cfg_run.analysis.solver_backend = "linear"
        return cfg_run, "linear (forced)"

    if backend_mode == "eql":
        cfg_run.analysis.solver_backend = "eql"
        return cfg_run, "eql (forced)"

    if backend_mode == "nonlinear":
        cfg_run.analysis.solver_backend = "nonlinear"
        return cfg_run, "nonlinear (forced)"

    if backend_mode == "opensees":
        cfg_run.analysis.solver_backend = "opensees"
        resolved = resolve_opensees_executable(cfg_run.opensees.executable)
        if resolved is None:
            raise RuntimeError(
                f"OpenSees executable not found: {cfg_run.opensees.executable}. "
                "Use backend mode 'auto' for fallback."
            )
        cfg_run.opensees.executable = str(resolved)
        return cfg_run, f"opensees ({resolved})"

    if backend_mode == "auto":
        if cfg_run.analysis.solver_backend == "opensees":
            resolved = resolve_opensees_executable(cfg_run.opensees.executable)
            if resolved is None:
                cfg_run.analysis.solver_backend = "mock"
                return cfg_run, "mock (auto-fallback: OpenSees missing)"
            cfg_run.opensees.executable = str(resolved)
            return cfg_run, f"opensees ({resolved})"
        return cfg_run, str(cfg_run.analysis.solver_backend)

    # config mode
    if cfg_run.analysis.solver_backend == "opensees":
        resolved = resolve_opensees_executable(cfg_run.opensees.executable)
        if resolved is None:
            raise RuntimeError(
                f"OpenSees executable not found: {cfg_run.opensees.executable}. "
                "Use backend mode 'auto' or 'mock'."
            )
        cfg_run.opensees.executable = str(resolved)
        return cfg_run, f"opensees ({resolved})"
    return cfg_run, str(cfg_run.analysis.solver_backend)


def _annotate_verify_policy(
    verify_report: dict[str, Any],
    *,
    require_runs: int,
) -> None:
    policy_raw = verify_report.get("policy")
    policy: dict[str, Any] = dict(policy_raw) if isinstance(policy_raw, dict) else {}
    conditions_raw = policy.get("conditions")
    conditions: dict[str, bool] = (
        {str(k): bool(v) for k, v in conditions_raw.items()}
        if isinstance(conditions_raw, dict)
        else {}
    )
    total_runs = int(verify_report.get("total_runs", 0) or 0)
    failed_runs = int(verify_report.get("failed_runs", 0) or 0)
    conditions["verify_ok"] = bool(verify_report.get("ok", False))
    conditions["no_failed_runs"] = failed_runs == 0
    conditions["require_runs_ok"] = total_runs >= require_runs
    policy["require_runs"] = require_runs
    policy["conditions"] = conditions
    policy["passed"] = all(bool(v) for v in conditions.values())
    verify_report["policy"] = policy


def _run_campaign_bundle(
    suite: str,
    campaign_dir: Path,
    *,
    opensees_executable: str,
    require_backend_version_regex: str,
    require_backend_sha256: str,
    verify_require_runs: int,
    require_opensees: bool,
    min_execution_coverage: float,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign_dir.mkdir(parents=True, exist_ok=True)
    benchmark_report = _run_benchmark_with_optional_override(
        suite=suite,
        output_dir=campaign_dir,
        opensees_executable=opensees_executable,
        require_backend_version_regex=require_backend_version_regex,
        require_backend_sha256=require_backend_sha256,
    )
    benchmark_report["policy"] = {
        "fail_on_skip": False,
        "require_runs": 0,
        "require_opensees": require_opensees,
        "min_execution_coverage": min_execution_coverage,
        "require_backend_version_regex": require_backend_version_regex,
        "require_backend_sha256": require_backend_sha256.strip().lower(),
    }
    backend_ready = bool(benchmark_report.get("backend_ready", True))
    skipped_backend_raw = benchmark_report.get("skipped_backend", 0)
    if isinstance(skipped_backend_raw, (int, float, str)):
        skipped_backend = int(skipped_backend_raw)
    else:
        skipped_backend = 0
    if (
        require_opensees
        and suite == "opensees-parity"
        and (not backend_ready or skipped_backend > 0)
    ):
        raise RuntimeError(
            "OpenSees backend is required for parity campaign but some cases were skipped "
            f"(backend_ready={backend_ready}, skipped_backend={skipped_backend})."
        )
    execution_coverage_raw = benchmark_report.get("execution_coverage", 0.0)
    if isinstance(execution_coverage_raw, (int, float)):
        execution_coverage = float(execution_coverage_raw)
    elif isinstance(execution_coverage_raw, str):
        try:
            execution_coverage = float(execution_coverage_raw)
        except ValueError:
            execution_coverage = 0.0
    else:
        execution_coverage = 0.0
    if execution_coverage < min_execution_coverage:
        raise RuntimeError(
            "Execution coverage policy failed for campaign: "
            f"execution_coverage={execution_coverage:.3f}, "
            f"min_execution_coverage={min_execution_coverage:.3f}"
        )
    benchmark_path = campaign_dir / f"benchmark_{suite}.json"
    benchmark_path.write_text(json.dumps(benchmark_report, indent=2), encoding="utf-8")

    verify_report = verify_batch(
        campaign_dir,
        require_runs=verify_require_runs,
    ).as_dict()
    _annotate_verify_policy(verify_report, require_runs=verify_require_runs)
    verify_path = campaign_dir / "verify_batch_report.json"
    verify_path.write_text(json.dumps(verify_report, indent=2), encoding="utf-8")

    summary = summarize_campaign(benchmark_report, verify_report)
    summary_json = campaign_dir / "campaign_summary.json"
    summary_md = campaign_dir / "campaign_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(render_summary_markdown(summary), encoding="utf-8")
    return benchmark_report, verify_report, summary


def _make_acc_plot(time: np.ndarray, acc: np.ndarray) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time,
            y=acc,
            mode="lines",
            line={"width": 1.6, "color": "#8b4d2a"},
            name="Surface Acc",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Surface Acceleration",
        xaxis_title="Time (s)",
        yaxis_title="Acceleration (m/s²)",
        height=340,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    return fig


def _make_spectra_plot(periods: np.ndarray, psa: np.ndarray) -> go.Figure:
    p = np.asarray(periods, dtype=np.float64)
    s = np.asarray(psa, dtype=np.float64)
    mask = np.isfinite(p) & np.isfinite(s) & (p > 0.0)
    p = p[mask]
    s = np.maximum(s[mask], 0.0)
    if p.size > 1:
        order = np.argsort(p)
        p = p[order]
        s = s[order]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=p,
            y=s,
            mode="lines",
            line={"width": 1.8, "color": "#2d6a6a"},
            name="PSA",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Pseudo Spectral Acceleration (5%)",
        xaxis_title="Period (s)",
        yaxis_title="PSA (m/s²)",
        height=340,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    fig.update_xaxes(type="log")
    if s.size > 0:
        y_max = float(np.max(s))
        fig.update_yaxes(range=[0.0, max(1.0e-4, y_max * 1.1)])
    return fig


def _make_transfer_plot(freq_hz: np.ndarray, transfer_abs: np.ndarray) -> go.Figure:
    f = np.asarray(freq_hz, dtype=np.float64)
    h = np.asarray(transfer_abs, dtype=np.float64)
    mask = np.isfinite(f) & np.isfinite(h) & (f > 0.0)
    f = f[mask]
    h = np.maximum(h[mask], 0.0)
    if f.size > 1:
        order = np.argsort(f)
        f = f[order]
        h = h[order]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=f,
            y=h,
            mode="lines",
            line={"width": 1.8, "color": "#4b3f72"},
            name="|H(f)|",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Transfer Function |H(f)|",
        xaxis_title="Frequency (Hz)",
        yaxis_title="Amplification",
        height=340,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    if f.size > 0:
        f_max = float(np.max(f))
        x_max = min(25.0, f_max)
        fig.update_xaxes(range=[0.0, max(0.5, x_max)])
        h_max = float(np.max(h))
        fig.update_yaxes(range=[0.0, max(0.1, h_max * 1.1)])
        h_mean = float(np.mean(h))
        h_std = float(np.std(h))
        if h_mean > 0.0 and (h_std / h_mean) < 0.02:
            fig.add_annotation(
                xref="paper",
                yref="paper",
                x=0.99,
                y=0.98,
                text="Near-flat |H(f)| (possible mock/scaled output)",
                showarrow=False,
                font={"size": 11, "color": "#7a5d00"},
                bgcolor="rgba(255, 245, 205, 0.9)",
                bordercolor="rgba(122, 93, 0, 0.35)",
                borderwidth=1,
            )
    else:
        fig.update_xaxes(range=[0.0, 1.0])
    return fig


def _make_ru_plot(time: np.ndarray, ru: np.ndarray) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=time,
            y=ru,
            mode="lines",
            line={"width": 1.6, "color": "#2f3a42"},
            name="ru",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title="Pore Pressure Ratio (ru)",
        xaxis_title="Time (s)",
        yaxis_title="ru",
        height=300,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    return fig


def _make_effective_stress_plot(
    time: np.ndarray,
    delta_u: np.ndarray,
    sigma_v_eff: np.ndarray,
) -> go.Figure:
    fig = go.Figure()
    if time.size == delta_u.size and delta_u.size > 0:
        fig.add_trace(
            go.Scatter(
                x=time,
                y=delta_u,
                mode="lines",
                line={"width": 1.5, "color": "#555555"},
                name="delta_u",
            )
        )
    if time.size == sigma_v_eff.size and sigma_v_eff.size > 0:
        fig.add_trace(
            go.Scatter(
                x=time,
                y=sigma_v_eff,
                mode="lines",
                line={"width": 1.6, "color": "#2d6a6a"},
                name="sigma_v_eff",
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="Effective Stress Proxies",
        xaxis_title="Time (s)",
        yaxis_title="kPa (proxy)",
        height=300,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    return fig


def _collect_hysteretic_curves(config_path: Path) -> list[dict[str, Any]]:
    cfg = load_project_config(config_path)
    strain = np.logspace(-6, -1, 180, dtype=np.float64)
    curves: list[dict[str, Any]] = []
    for layer in cfg.profile.layers:
        material_name = str(getattr(layer.material, "value", layer.material)).lower()
        if material_name not in {"mkz", "gqh"}:
            continue
        gamma_ref = float(layer.material_params.get("gamma_ref", 0.001))
        damping_min = float(layer.material_params.get("damping_min", 0.01))
        damping_max = float(layer.material_params.get("damping_max", 0.12))
        if material_name == "mkz":
            reduction = mkz_modulus_reduction(strain, gamma_ref=gamma_ref)
            model_name = "MKZ"
        else:
            reduction = gqh_modulus_reduction(
                strain,
                gamma_ref=gamma_ref,
                a1=float(layer.material_params.get("a1", 1.0)),
                a2=float(layer.material_params.get("a2", 0.0)),
                m=float(layer.material_params.get("m", 1.0)),
            )
            model_name = "GQH"
        damping = bounded_damping_from_reduction(
            reduction,
            damping_min=damping_min,
            damping_max=damping_max,
        )
        curves.append(
            {
                "label": f"{layer.name} ({model_name})",
                "strain": strain,
                "reduction": reduction,
                "damping": damping,
                "gamma_ref": gamma_ref,
                "damping_min": damping_min,
                "damping_max": damping_max,
                "material_name": material_name,
                "material_params": layer.material_params,
            }
        )
    for curve in curves:
        material_name = str(curve["material_name"]).lower()
        if material_name == "mkz":
            material = MaterialType.MKZ
        else:
            material = MaterialType.GQH
        loop_amplitude = float(
            np.clip(
                5.0 * float(curve["gamma_ref"]),
                2.5e-4,
                2.0e-2,
            )
        )
        loop = generate_masing_loop(
            material=material,
            material_params=curve["material_params"],
            strain_amplitude=loop_amplitude,
            n_points_per_branch=140,
        )
        curve["loop_strain"] = loop.strain
        curve["loop_stress"] = loop.stress
        curve["loop_energy"] = loop.energy_dissipation
        curve["loop_strain_amplitude"] = loop.strain_amplitude
    return curves


def _make_hysteretic_reduction_plot(curves: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    for curve in curves:
        fig.add_trace(
            go.Scatter(
                x=curve["strain"],
                y=curve["reduction"],
                mode="lines",
                line={"width": 1.8},
                name=str(curve["label"]),
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="MKZ/GQH G/Gmax Curves",
        xaxis_title="Shear Strain, gamma",
        yaxis_title="G/Gmax",
        height=320,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    fig.update_xaxes(type="log")
    fig.update_yaxes(range=[0.0, 1.05])
    return fig


def _make_hysteretic_damping_plot(curves: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    for curve in curves:
        fig.add_trace(
            go.Scatter(
                x=curve["strain"],
                y=curve["damping"],
                mode="lines",
                line={"width": 1.8},
                name=str(curve["label"]),
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="MKZ/GQH Damping Proxy Curves",
        xaxis_title="Shear Strain, gamma",
        yaxis_title="Damping Ratio",
        height=320,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    fig.update_xaxes(type="log")
    fig.update_yaxes(range=[0.0, 0.5])
    return fig


def _make_hysteretic_loop_plot(curves: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    for curve in curves:
        fig.add_trace(
            go.Scatter(
                x=curve["loop_strain"],
                y=curve["loop_stress"],
                mode="lines",
                line={"width": 1.8},
                name=f"{curve['label']} @ gamma_a={float(curve['loop_strain_amplitude']):.2e}",
            )
        )
    fig.update_layout(
        template="plotly_white",
        title="MKZ/GQH Masing Hysteresis Loops",
        xaxis_title="Shear Strain, gamma",
        yaxis_title="Shear Stress, tau (proxy)",
        height=360,
        margin={"l": 30, "r": 20, "t": 55, "b": 35},
    )
    return fig


def _render_run_outputs(run_dir: Path) -> None:
    h5_path = run_dir / "results.h5"
    sqlite_path = run_dir / "results.sqlite"
    if not (h5_path.exists() and sqlite_path.exists()):
        st.warning("Result files are missing for the selected run.")
        return

    rs = load_result(run_dir)

    with h5py.File(h5_path, "r") as h5:
        mesh_dz = np.array(h5["/mesh/dz"], dtype=np.float64) if "/mesh/dz" in h5 else np.array([])
    run_meta_path = run_dir / "run_meta.json"
    run_meta: dict[str, Any] = {}
    if run_meta_path.exists():
        try:
            run_meta = json.loads(run_meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            run_meta = {}

    time = rs.time
    acc = rs.acc_surface
    if time.size > 1:
        dt_s = float(np.median(np.diff(time)))
    else:
        dt_s = 1.0
    if np.isfinite(dt_s) and dt_s > 0.0 and acc.size > 1:
        live_spectra = compute_spectra(
            np.asarray(acc, dtype=np.float64),
            dt=dt_s,
            damping=0.05,
        )
        periods = live_spectra.periods
        psa = live_spectra.psa
    else:
        periods = rs.spectra_periods
        psa = rs.spectra_psa
    transfer_freq_hz = rs.transfer_freq_hz
    transfer_abs = rs.transfer_abs
    ru_time = rs.ru_time
    ru = rs.ru
    delta_u = rs.delta_u
    sigma_v_eff = rs.sigma_v_eff
    solver_backend = str(run_meta.get("solver_backend", "unknown")).strip() or "unknown"
    run_status = str(run_meta.get("status", "unknown")).strip() or "unknown"
    run_message = str(run_meta.get("message", "")).strip()

    metrics = _load_metrics(sqlite_path)
    delta_u_max_default = float(np.max(delta_u)) if delta_u.size > 0 else float("nan")
    sigma_v_eff_min_default = (
        float(np.min(sigma_v_eff)) if sigma_v_eff.size > 0 else float("nan")
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("PGA (m/s²)", f"{metrics.get('pga', float(np.max(np.abs(acc)))):.5f}")
    c2.metric(
        "ru_max",
        f"{metrics.get('ru_max', float(np.max(ru)) if ru.size > 0 else float('nan')):.5f}",
    )
    c3.metric("Mesh slices", int(mesh_dz.size) if mesh_dz.size else "-")
    c4.metric(
        "delta_u_max",
        f"{metrics.get('delta_u_max', delta_u_max_default):.5f}",
    )
    c5.metric(
        "sigma_v_eff_min",
        f"{metrics.get('sigma_v_eff_min', sigma_v_eff_min_default):.5f}",
    )
    if run_status != "ok":
        st.error(
            f"Run status: {run_status} | backend: {solver_backend}. "
            f"{run_message or 'Pipeline fallback may have produced proxy outputs.'}"
        )
    elif solver_backend == "mock":
        st.warning(
            "This run used the `mock` backend. PSA/transfer curves are proxy-level and "
            "not physical OpenSees effective-stress results."
        )
    else:
        st.caption(f"Backend: `{solver_backend}` | Status: `{run_status}`")

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.plotly_chart(_make_acc_plot(time, acc), use_container_width=True)
    with pcol2:
        st.plotly_chart(_make_spectra_plot(periods, psa), use_container_width=True)
    if transfer_freq_hz.size > 1 and transfer_freq_hz.size == transfer_abs.size:
        st.plotly_chart(
            _make_transfer_plot(transfer_freq_hz, transfer_abs),
            use_container_width=True,
        )
    pcol3, pcol4 = st.columns(2)
    with pcol3:
        st.plotly_chart(_make_ru_plot(ru_time, ru), use_container_width=True)
    with pcol4:
        st.plotly_chart(
            _make_effective_stress_plot(ru_time, delta_u, sigma_v_eff),
            use_container_width=True,
        )

    st.markdown("#### Export")
    surface_out_path = run_dir / "surface_acc.out"
    surface_csv_lines = ["time_s,acc_m_s2,delta_t_s"]
    if time.size == acc.size and time.size > 0:
        for t, a in zip(time, acc, strict=False):
            surface_csv_lines.append(f"{float(t):.8f},{float(a):.10e},{dt_s:.8e}")
    else:
        for idx, a in enumerate(acc):
            surface_csv_lines.append(
                f"{float(idx):.8f},{float(a):.10e},{dt_s:.8e}"
            )
    surface_csv = "\n".join(surface_csv_lines)

    n_pwp = int(min(ru_time.size, ru.size))
    pwp_csv_lines = ["time_s,ru,delta_u,sigma_v_eff,delta_t_s"]
    if n_pwp > 0:
        dt_ru = float(np.median(np.diff(ru_time))) if ru_time.size > 1 else dt_s
        for i in range(n_pwp):
            t = float(ru_time[i])
            ru_i = float(ru[i]) if i < ru.size else float("nan")
            du_i = float(delta_u[i]) if i < delta_u.size else float("nan")
            sig_i = float(sigma_v_eff[i]) if i < sigma_v_eff.size else float("nan")
            pwp_csv_lines.append(f"{t:.8f},{ru_i:.10e},{du_i:.10e},{sig_i:.10e},{dt_ru:.8e}")
    pwp_csv = "\n".join(pwp_csv_lines)

    ex1, ex2, ex3, ex4 = st.columns(4)
    with ex1:
        st.download_button(
            "Download surface_acc.csv",
            data=surface_csv,
            file_name=f"{run_dir.name}_surface_acc.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with ex2:
        if surface_out_path.exists():
            st.download_button(
                "Download surface_acc.out",
                data=surface_out_path.read_bytes(),
                file_name=f"{run_dir.name}_surface_acc.out",
                mime="text/plain",
                use_container_width=True,
            )
        else:
            st.button(
                "surface_acc.out missing",
                disabled=True,
                use_container_width=True,
                key=f"{run_dir.name}_surface_out_missing",
            )
    with ex3:
        st.download_button(
            "Download results.h5",
            data=h5_path.read_bytes(),
            file_name=f"{run_dir.name}_results.h5",
            mime="application/x-hdf5",
            use_container_width=True,
        )
    with ex4:
        st.download_button(
            "Download pwp_effective.csv",
            data=pwp_csv,
            file_name=f"{run_dir.name}_pwp_effective.csv",
            mime="text/csv",
            use_container_width=True,
        )


def main() -> None:
    root = _repo_root()
    default_cfg = root / "examples" / "configs" / "effective_stress.yml"
    strict_plus_cfg = root / "examples" / "configs" / "effective_stress_strict_plus.yml"
    mkz_cfg = root / "examples" / "configs" / "mkz_gqh_mock.yml"
    mkz_eql_cfg = root / "examples" / "configs" / "mkz_gqh_eql.yml"
    mkz_nl_cfg = root / "examples" / "configs" / "mkz_gqh_nonlinear.yml"
    default_motion = root / "examples" / "motions" / "sample_motion.csv"
    default_out = root / "out" / "ui"
    config_presets = {
        "effective-stress": default_cfg,
        "effective-stress-strict-plus": strict_plus_cfg,
        "mkz-gqh-mock": mkz_cfg,
        "mkz-gqh-eql": mkz_eql_cfg,
        "mkz-gqh-nonlinear": mkz_nl_cfg,
    }

    st.set_page_config(
        page_title="StrataWave Studio",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    st.markdown(
        """
        <div class="hero">
          <h1>StrataWave Studio</h1>
          <p>Run effective-stress and MKZ/GQH prototyping workflows from one control panel.</p>
          <span class="chip">Validate</span>
          <span class="chip">Run</span>
          <span class="chip">Quickstart</span>
          <span class="chip">Benchmark</span>
          <span class="chip">Report</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Run Control")
    if "cfg_path" not in st.session_state:
        st.session_state["cfg_path"] = str(default_cfg)
    if "motion_path" not in st.session_state:
        st.session_state["motion_path"] = str(default_motion)
    if "out_dir" not in st.session_state:
        st.session_state["out_dir"] = str(default_out)
    preset = st.sidebar.selectbox(
        "Config Preset",
        options=list(config_presets.keys()),
        index=0,
    )
    if st.sidebar.button("Apply Preset Config", use_container_width=True):
        st.session_state["cfg_path"] = str(config_presets[preset])
        st.rerun()
    cfg_path = Path(
        st.sidebar.text_input(
            "Config Path",
            key="cfg_path",
            autocomplete="off",
        )
    )
    motion_path = Path(
        st.sidebar.text_input(
            "Motion Path",
            key="motion_path",
            autocomplete="off",
        )
    )
    out_dir = Path(
        st.sidebar.text_input(
            "Output Directory",
            key="out_dir",
            autocomplete="off",
        )
    )
    template_map = {
        "effective-stress": "effective-stress",
        "effective-stress-strict-plus": "effective-stress-strict-plus",
        "mkz-gqh-mock": "mkz-gqh-mock",
        "mkz-gqh-eql": "mkz-gqh-eql",
        "mkz-gqh-nonlinear": "mkz-gqh-nonlinear",
    }
    with st.sidebar.expander("Project Setup", expanded=False):
        bootstrap_dir = Path(
            st.text_input(
                "Starter Folder",
                str(out_dir / "starter"),
                autocomplete="off",
            )
        )
        if st.button("Create Starter Case", use_container_width=True):
            try:
                bootstrap_dir.mkdir(parents=True, exist_ok=True)
                template_name = template_map[preset]
                starter_cfg = write_config_template(
                    bootstrap_dir / "config.yml",
                    template=template_name,
                )
                starter_motion = bootstrap_dir / "motion.csv"
                shutil.copy2(default_motion, starter_motion)
                st.session_state["cfg_path"] = str(starter_cfg)
                st.session_state["motion_path"] = str(starter_motion)
                st.session_state["out_dir"] = str(bootstrap_dir / "runs")
                st.success(f"Starter case ready: {bootstrap_dir}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = _find_run_dirs(out_dir)

    st.sidebar.header("Campaign Control")
    campaign_suite = st.sidebar.selectbox(
        "Benchmark Suite",
        options=["core-es", "core-hyst", "core-linear", "core-eql", "opensees-parity"],
        index=0,
    )
    opensees_executable = st.sidebar.text_input(
        "OpenSees Executable (optional)",
        "",
        autocomplete="off",
    )
    run_backend_mode = st.sidebar.selectbox(
        "Run Backend Mode",
        options=["config", "auto", "opensees", "mock", "linear", "eql", "nonlinear"],
        index=1,
    )
    run_opensees_executable = st.sidebar.text_input(
        "Run OpenSees Executable (optional)",
        "",
        autocomplete="off",
    )
    require_backend_version_regex = st.sidebar.text_input(
        "Backend Version Regex (optional)",
        "",
        autocomplete="off",
    )
    require_backend_sha256 = st.sidebar.text_input(
        "Backend SHA256 (optional)",
        "",
        autocomplete="off",
    )
    require_opensees = st.sidebar.checkbox(
        "Require OpenSees (parity)",
        value=(campaign_suite == "opensees-parity"),
    )
    min_execution_coverage = float(
        st.sidebar.number_input(
            "Min Execution Coverage",
            min_value=0.0,
            max_value=1.0,
            value=1.0 if campaign_suite == "opensees-parity" else 0.0,
            step=0.05,
            format="%.2f",
        )
    )
    verify_require_runs = int(
        st.sidebar.number_input(
            "Verify Require Runs",
            min_value=1,
            value=(
                6
                if campaign_suite == "opensees-parity"
                else (3 if campaign_suite == "core-es" else 1)
            ),
            step=1,
        )
    )
    with st.sidebar.expander("Backend Health", expanded=False):
        probe_target = (
            run_opensees_executable.strip()
            or opensees_executable.strip()
            or "OpenSees"
        )
        if st.button("Check OpenSees Backend", use_container_width=True):
            probe = probe_opensees_executable(probe_target)
            errors = validate_backend_probe_requirements(
                probe,
                require_version_regex=require_backend_version_regex.strip() or None,
                require_binary_sha256=require_backend_sha256.strip().lower() or None,
            )
            if probe.available and not errors:
                st.success("Backend check passed.")
            else:
                st.error("Backend check failed.")
            st.code(
                json.dumps(
                    {
                        "target": probe_target,
                        "available": probe.available,
                        "resolved": str(probe.resolved) if probe.resolved else "",
                        "version": probe.version,
                        "binary_sha256": probe.binary_sha256,
                        "errors": errors,
                    },
                    indent=2,
                )
            )
    campaign_root = out_dir / "campaign" / campaign_suite

    run_dir_raw = st.session_state.get("run_dir")
    run_dir: Path | None
    if isinstance(run_dir_raw, str) and run_dir_raw:
        run_dir = Path(run_dir_raw)
    else:
        run_dir = run_dirs[-1] if run_dirs else None

    if run_dirs:
        options = [p.name for p in run_dirs]
        current_name = (
            run_dir.name
            if run_dir is not None and run_dir.name in options
            else options[-1]
        )
        selected_name = st.selectbox(
            "Select Run Directory",
            options=options,
            index=options.index(current_name),
        )
        run_dir = out_dir / selected_name
        st.session_state["run_dir"] = str(run_dir)

    _render_quick_status(cfg_path=cfg_path, motion_path=motion_path, out_dir=out_dir)
    _render_visual_config_editor(cfg_path)

    act1, act2, act3, act4, act5, act6, act7 = st.columns(7)

    if act1.button("Validate Config", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            st.success(f"Valid config: {cfg.project_name}")
        except Exception as exc:
            st.error(str(exc))

    if act2.button("Run Analysis", type="primary", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            cfg, backend_note = _apply_runtime_backend(
                cfg,
                backend_mode=run_backend_mode,
                opensees_executable=run_opensees_executable,
            )
            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            result = run_analysis(cfg, motion, output_dir=out_dir)
            st.session_state["run_dir"] = str(result.output_dir)
            run_dir = result.output_dir
            if result.status != "ok":
                st.error(result.message)
            else:
                st.caption(f"Backend: {backend_note}")
                st.success(f"Run completed: {result.output_dir}")
        except Exception as exc:
            st.error(str(exc))

    if act3.button("Run Campaign", use_container_width=True):
        try:
            benchmark_report, verify_report, summary = _run_campaign_bundle(
                suite=campaign_suite,
                campaign_dir=campaign_root,
                opensees_executable=opensees_executable,
                require_backend_version_regex=require_backend_version_regex,
                require_backend_sha256=require_backend_sha256,
                verify_require_runs=verify_require_runs,
                require_opensees=require_opensees,
                min_execution_coverage=min_execution_coverage,
            )
            st.session_state["campaign_dir"] = str(campaign_root)
            st.success(f"Campaign completed: {campaign_root}")
            with st.expander("Campaign Summary", expanded=True):
                st.markdown(render_summary_markdown(summary))
            benchmark_meta = summary.get("benchmark")
            if isinstance(benchmark_meta, dict):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Backend Ready", str(benchmark_meta.get("backend_ready", "")))
                m2.metric("Skipped Backend", int(benchmark_meta.get("skipped_backend", 0)))
                m3.metric(
                    "Exec Coverage",
                    f"{float(benchmark_meta.get('execution_coverage', 0.0)):.3f}",
                )
                m4.metric(
                    "Fingerprint OK",
                    str(benchmark_meta.get("backend_fingerprint_ok", "")),
                )
                missing_cases = benchmark_meta.get("backend_missing_cases", [])
                if isinstance(missing_cases, list) and missing_cases:
                    with st.expander("Backend Missing Cases", expanded=False):
                        for case_name in missing_cases:
                            st.write(f"- `{case_name}`")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Benchmark Report")
                st.json(benchmark_report)
            with c2:
                st.caption("Verify Batch Report")
                st.json(verify_report)
        except Exception as exc:
            st.error(str(exc))

    if act4.button("Generate Report", use_container_width=True):
        if not run_dir:
            st.warning("Run analysis first.")
        else:
            try:
                rs = load_result(run_dir)
                written = write_report(rs, out_dir=run_dir, formats=["html", "pdf"])
                st.success(f"Report files: {', '.join(str(p) for p in written)}")
            except Exception as exc:
                st.error(str(exc))

    if act5.button("Refresh Runs", use_container_width=True):
        st.rerun()

    if act6.button("Render Tcl", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            processed = preprocess_motion(motion, cfg.motion)

            tcl_out_dir = out_dir / "tcl_preview"
            tcl_out_dir.mkdir(parents=True, exist_ok=True)
            motion_out = tcl_out_dir / "motion_processed.csv"
            np.savetxt(motion_out, processed.acc, delimiter=",")

            script = render_tcl(cfg, motion_file=motion_out, output_dir=tcl_out_dir)
            validate_tcl_script(script)
            tcl_path = tcl_out_dir / "model.tcl"
            tcl_path.write_text(script, encoding="utf-8")

            st.session_state["tcl_path"] = str(tcl_path)
            st.session_state["tcl_motion_path"] = str(motion_out)
            st.success(f"Tcl generated: {tcl_path}")
        except Exception as exc:
            st.error(str(exc))

    if act7.button("Quickstart", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            cfg, backend_note = _apply_runtime_backend(
                cfg,
                backend_mode=run_backend_mode,
                opensees_executable=run_opensees_executable,
            )
            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            result = run_analysis(cfg, motion, output_dir=out_dir)
            st.session_state["run_dir"] = str(result.output_dir)
            run_dir = result.output_dir
            verify = verify_run(result.output_dir)
            rs = load_result(result.output_dir)
            written = write_report(rs, out_dir=result.output_dir, formats=["html"])
            if result.status != "ok":
                st.error(result.message)
            else:
                st.caption(f"Backend: {backend_note}")
                st.success(f"Quickstart completed: {result.output_dir}")
                st.info(
                    " | ".join(
                        [
                            f"verify_ok={verify.ok}",
                            f"report={', '.join(str(p.name) for p in written)}",
                        ]
                    )
                )
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("OpenSees Tcl Preview")
    tcl_path_raw = st.session_state.get("tcl_path")
    tcl_motion_raw = st.session_state.get("tcl_motion_path")
    tcl_path = (
        Path(tcl_path_raw)
        if isinstance(tcl_path_raw, str) and tcl_path_raw
        else out_dir / "tcl_preview" / "model.tcl"
    )
    tcl_motion_path = (
        Path(tcl_motion_raw)
        if isinstance(tcl_motion_raw, str) and tcl_motion_raw
        else out_dir / "tcl_preview" / "motion_processed.csv"
    )

    if tcl_path.exists():
        tcl_text = tcl_path.read_text(encoding="utf-8")
        st.code(str(tcl_path))
        with st.expander("model.tcl", expanded=False):
            st.code(tcl_text, language="tcl")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            st.download_button(
                "Download model.tcl",
                data=tcl_text,
                file_name="model.tcl",
                mime="text/plain",
                use_container_width=True,
            )
        with dcol2:
            if tcl_motion_path.exists():
                st.download_button(
                    "Download motion_processed.csv",
                    data=tcl_motion_path.read_bytes(),
                    file_name="motion_processed.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                st.button(
                    "Download motion_processed.csv",
                    disabled=True,
                    use_container_width=True,
                )
    else:
        st.info("No Tcl preview yet. Use Render Tcl.")

    st.divider()
    st.subheader("MKZ/GQH Curve Inspector")
    try:
        curves = _collect_hysteretic_curves(cfg_path)
        if curves:
            hcol1, hcol2 = st.columns(2)
            with hcol1:
                st.plotly_chart(
                    _make_hysteretic_reduction_plot(curves),
                    use_container_width=True,
                )
            with hcol2:
                st.plotly_chart(
                    _make_hysteretic_damping_plot(curves),
                    use_container_width=True,
                )
            st.plotly_chart(
                _make_hysteretic_loop_plot(curves),
                use_container_width=True,
            )
            summary_rows = [
                {
                    "Layer": str(curve["label"]),
                    "gamma_ref": f"{float(curve['gamma_ref']):.4e}",
                    "damping_min": f"{float(curve['damping_min']):.4f}",
                    "damping_max": f"{float(curve['damping_max']):.4f}",
                    "loop_gamma_a": f"{float(curve['loop_strain_amplitude']):.4e}",
                    "loop_energy": f"{float(curve['loop_energy']):.4e}",
                }
                for curve in curves
            ]
            st.table(summary_rows)
        else:
            st.info("Selected config has no MKZ/GQH layers.")
    except Exception as exc:
        st.info(f"Curve inspector available after valid config load: {exc}")

    st.divider()
    st.subheader("Latest Run")
    if run_dir and run_dir.exists():
        st.code(str(run_dir))
        _render_run_outputs(run_dir)
    else:
        st.info("No run selected yet. Start with Validate/Run.")

    st.divider()
    st.subheader("Latest Campaign")
    campaign_raw = st.session_state.get("campaign_dir")
    campaign_dir = (
        Path(campaign_raw)
        if isinstance(campaign_raw, str) and campaign_raw
        else campaign_root
    )
    summary_md = campaign_dir / "campaign_summary.md"
    summary_json = campaign_dir / "campaign_summary.json"
    if summary_md.exists() and summary_json.exists():
        st.code(str(campaign_dir))
        st.markdown(summary_md.read_text(encoding="utf-8"))
    else:
        st.info("No campaign summary yet. Use Run Campaign.")


if __name__ == "__main__":
    main()

