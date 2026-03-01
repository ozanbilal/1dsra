from __future__ import annotations

# ruff: noqa: E402
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import plotly.graph_objects as go
import streamlit as st

PYTHON_SRC_ROOT = Path(__file__).resolve().parents[2]
if str(PYTHON_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC_ROOT))

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import load_project_config
from dsra1d.interop.opensees import render_tcl, validate_tcl_script
from dsra1d.materials import (
    bounded_damping_from_reduction,
    gqh_modulus_reduction,
    mkz_modulus_reduction,
)
from dsra1d.motion import load_motion, preprocess_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import render_summary_markdown, summarize_campaign, write_report
from dsra1d.verify import verify_batch


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


def _run_benchmark_with_optional_override(
    suite: str,
    output_dir: Path,
    opensees_executable: str,
) -> dict[str, Any]:
    env_key = "DSRA1D_OPENSEES_EXE_OVERRIDE"
    old_value = os.environ.get(env_key)
    try:
        exe = opensees_executable.strip()
        if exe:
            os.environ[env_key] = exe
        return run_benchmark_suite(suite=suite, output_dir=output_dir)
    finally:
        if opensees_executable.strip():
            if old_value is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = old_value


def _run_campaign_bundle(
    suite: str,
    campaign_dir: Path,
    *,
    opensees_executable: str,
    verify_require_runs: int,
    require_opensees: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign_dir.mkdir(parents=True, exist_ok=True)
    benchmark_report = _run_benchmark_with_optional_override(
        suite=suite,
        output_dir=campaign_dir,
        opensees_executable=opensees_executable,
    )
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
    benchmark_path = campaign_dir / f"benchmark_{suite}.json"
    benchmark_path.write_text(json.dumps(benchmark_report, indent=2), encoding="utf-8")

    verify_report = verify_batch(
        campaign_dir,
        require_runs=verify_require_runs,
    ).as_dict()
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
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=periods,
            y=psa,
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
            }
        )
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


def _render_run_outputs(run_dir: Path) -> None:
    h5_path = run_dir / "results.h5"
    sqlite_path = run_dir / "results.sqlite"
    if not (h5_path.exists() and sqlite_path.exists()):
        st.warning("Result files are missing for the selected run.")
        return

    rs = load_result(run_dir)

    with h5py.File(h5_path, "r") as h5:
        mesh_dz = np.array(h5["/mesh/dz"], dtype=np.float64) if "/mesh/dz" in h5 else np.array([])

    time = rs.time
    acc = rs.acc_surface
    periods = rs.spectra_periods
    psa = rs.spectra_psa
    ru_time = rs.ru_time
    ru = rs.ru
    delta_u = rs.delta_u
    sigma_v_eff = rs.sigma_v_eff

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

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.plotly_chart(_make_acc_plot(time, acc), use_container_width=True)
    with pcol2:
        st.plotly_chart(_make_spectra_plot(periods, psa), use_container_width=True)
    pcol3, pcol4 = st.columns(2)
    with pcol3:
        st.plotly_chart(_make_ru_plot(ru_time, ru), use_container_width=True)
    with pcol4:
        st.plotly_chart(
            _make_effective_stress_plot(ru_time, delta_u, sigma_v_eff),
            use_container_width=True,
        )


def main() -> None:
    root = _repo_root()
    default_cfg = root / "examples" / "configs" / "effective_stress.yml"
    strict_plus_cfg = root / "examples" / "configs" / "effective_stress_strict_plus.yml"
    mkz_cfg = root / "examples" / "configs" / "mkz_gqh_mock.yml"
    default_motion = root / "examples" / "motions" / "sample_motion.csv"
    default_out = root / "out" / "ui"
    config_presets = {
        "effective-stress": default_cfg,
        "effective-stress-strict-plus": strict_plus_cfg,
        "mkz-gqh-mock": mkz_cfg,
    }

    st.set_page_config(
        page_title="1DSRA Studio",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()

    st.markdown(
        """
        <div class="hero">
          <h1>1DSRA Studio</h1>
          <p>Run effective-stress and MKZ/GQH prototyping workflows from one control panel.</p>
          <span class="chip">Validate</span>
          <span class="chip">Run</span>
          <span class="chip">Benchmark</span>
          <span class="chip">Report</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Run Control")
    if "cfg_path" not in st.session_state:
        st.session_state["cfg_path"] = str(default_cfg)
    preset = st.sidebar.selectbox(
        "Config Preset",
        options=list(config_presets.keys()),
        index=0,
    )
    if st.sidebar.button("Apply Preset Config", use_container_width=True):
        st.session_state["cfg_path"] = str(config_presets[preset])
        st.rerun()
    cfg_path = Path(st.sidebar.text_input("Config Path", key="cfg_path"))
    motion_path = Path(st.sidebar.text_input("Motion Path", str(default_motion)))
    out_dir = Path(st.sidebar.text_input("Output Directory", str(default_out)))
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = _find_run_dirs(out_dir)

    st.sidebar.header("Campaign Control")
    campaign_suite = st.sidebar.selectbox(
        "Benchmark Suite",
        options=["core-es", "core-hyst", "opensees-parity"],
        index=0,
    )
    opensees_executable = st.sidebar.text_input(
        "OpenSees Executable (optional)",
        "",
    )
    require_opensees = st.sidebar.checkbox(
        "Require OpenSees (parity)",
        value=(campaign_suite == "opensees-parity"),
    )
    verify_require_runs = int(
        st.sidebar.number_input(
            "Verify Require Runs",
            min_value=1,
            value=3 if campaign_suite == "core-es" else 1,
            step=1,
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

    act1, act2, act3, act4, act5, act6 = st.columns(6)

    if act1.button("Validate Config", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            st.success(f"Valid config: {cfg.project_name}")
        except Exception as exc:
            st.error(str(exc))

    if act2.button("Run Analysis", type="primary", use_container_width=True):
        try:
            cfg = load_project_config(cfg_path)
            dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
            motion = load_motion(motion_path, dt=dt, unit=cfg.motion.units)
            result = run_analysis(cfg, motion, output_dir=out_dir)
            st.session_state["run_dir"] = str(result.output_dir)
            run_dir = result.output_dir
            if result.status != "ok":
                st.error(result.message)
            else:
                st.success(f"Run completed: {result.output_dir}")
        except Exception as exc:
            st.error(str(exc))

    if act3.button("Run Campaign", use_container_width=True):
        try:
            benchmark_report, verify_report, summary = _run_campaign_bundle(
                suite=campaign_suite,
                campaign_dir=campaign_root,
                opensees_executable=opensees_executable,
                verify_require_runs=verify_require_runs,
                require_opensees=require_opensees,
            )
            st.session_state["campaign_dir"] = str(campaign_root)
            st.success(f"Campaign completed: {campaign_root}")
            with st.expander("Campaign Summary", expanded=True):
                st.markdown(render_summary_markdown(summary))
            benchmark_meta = summary.get("benchmark")
            if isinstance(benchmark_meta, dict):
                m1, m2, m3 = st.columns(3)
                m1.metric("Backend Ready", str(benchmark_meta.get("backend_ready", "")))
                m2.metric("Skipped Backend", int(benchmark_meta.get("skipped_backend", 0)))
                m3.metric(
                    "Exec Coverage",
                    f"{float(benchmark_meta.get('execution_coverage', 0.0)):.3f}",
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
            summary_rows = [
                {
                    "Layer": str(curve["label"]),
                    "gamma_ref": f"{float(curve['gamma_ref']):.4e}",
                    "damping_min": f"{float(curve['damping_min']):.4f}",
                    "damping_max": f"{float(curve['damping_max']):.4f}",
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
