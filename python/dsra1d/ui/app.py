from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import h5py
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dsra1d.benchmark import run_benchmark_suite
from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import write_report


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
    default_motion = root / "examples" / "motions" / "sample_motion.csv"
    default_out = root / "out" / "ui"

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
          <p>Run effective-stress 1D site response workflows from one control panel.</p>
          <span class="chip">Validate</span>
          <span class="chip">Run</span>
          <span class="chip">Benchmark</span>
          <span class="chip">Report</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Run Control")
    cfg_path = Path(st.sidebar.text_input("Config Path", str(default_cfg)))
    motion_path = Path(st.sidebar.text_input("Motion Path", str(default_motion)))
    out_dir = Path(st.sidebar.text_input("Output Directory", str(default_out)))
    out_dir.mkdir(parents=True, exist_ok=True)

    act1, act2, act3, act4 = st.columns(4)
    run_dir: Path | None = st.session_state.get("run_dir")

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
            st.session_state["run_dir"] = result.output_dir
            run_dir = result.output_dir
            if result.status != "ok":
                st.error(result.message)
            else:
                st.success(f"Run completed: {result.output_dir}")
        except Exception as exc:
            st.error(str(exc))

    if act3.button("Run Benchmark", use_container_width=True):
        try:
            report = run_benchmark_suite("core-es", out_dir / "benchmarks")
            report_path = out_dir / "benchmarks" / "benchmark_core-es.json"
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            st.success(f"Benchmark report written: {report_path}")
            st.json(report)
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

    st.divider()
    st.subheader("Latest Run")
    if run_dir and run_dir.exists():
        st.code(str(run_dir))
        _render_run_outputs(run_dir)
    else:
        st.info("No run selected yet. Start with Validate/Run.")


if __name__ == "__main__":
    main()
