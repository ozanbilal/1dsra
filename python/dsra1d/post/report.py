from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from dsra1d.post.spectra import compute_spectra
from dsra1d.store.result_store import ResultStore


def _safe_max_abs(values: np.ndarray) -> float:
    return float(np.max(np.abs(values))) if values.size > 0 else float("nan")


def _safe_max(values: np.ndarray) -> float:
    return float(np.max(values)) if values.size > 0 else float("nan")


def _safe_min(values: np.ndarray) -> float:
    return float(np.min(values)) if values.size > 0 else float("nan")


def _fmt(value: float) -> str:
    if np.isnan(value):
        return "n/a"
    return f"{value:.6f}"


def write_report(result: ResultStore, out_dir: Path, formats: list[str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if result.time.size > 1 and result.acc_surface.size > 1:
        dt_s = float(np.median(np.diff(result.time)))
        live = compute_spectra(result.acc_surface, dt=dt_s, damping=0.05)
        periods = live.periods
        psa = live.psa
    else:
        periods = result.spectra_periods
        psa = result.spectra_psa
    pga = _safe_max_abs(result.acc_surface)
    ru_max = _safe_max(result.ru)
    delta_u_max = _safe_max(result.delta_u)
    sigma_v_eff_min = _safe_min(result.sigma_v_eff)
    sigma_v_ref = result.sigma_v_ref
    transfer_max = _safe_max(result.transfer_abs)
    eql_iterations = result.eql_iterations
    eql_converged = result.eql_converged
    eql_max_change_last = (
        float(result.eql_max_change_history[-1])
        if result.eql_max_change_history.size > 0
        else float("nan")
    )
    eql_iterations_text = (
        str(eql_iterations) if eql_iterations is not None else "n/a"
    )

    if "html" in formats:
        html = out_dir / "report.html"
        html.write_text(
            "\n".join(
                [
                    "<html><body>",
                    f"<h1>1DSRA Report: {result.run_id}</h1>",
                    f"<p>PGA(surface): {_fmt(pga)} m/s^2</p>",
                    f"<p>ru_max: {_fmt(ru_max)}</p>",
                    f"<p>delta_u_max: {_fmt(delta_u_max)} kPa (proxy units)</p>",
                    f"<p>sigma_v_ref: {_fmt(sigma_v_ref)} kPa (proxy units)</p>",
                    f"<p>sigma_v_eff_min: {_fmt(sigma_v_eff_min)} kPa (proxy units)</p>",
                    f"<p>transfer_abs_max: {_fmt(transfer_max)}</p>",
                    f"<p>EQL iterations: {eql_iterations_text}</p>",
                    (
                        f"<p>EQL converged: {eql_converged}</p>"
                        if eql_converged is not None
                        else "<p>EQL converged: n/a</p>"
                    ),
                    f"<p>EQL max_change_last: {_fmt(eql_max_change_last)}</p>",
                    f"<p>Spectra points: {len(periods)}</p>",
                    "</body></html>",
                ]
            ),
            encoding="utf-8",
        )
        written.append(html)

    if "pdf" in formats:
        pdf_path = out_dir / "report.pdf"
        with PdfPages(pdf_path) as pdf:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.plot(periods, psa, lw=1.7)
            ax.set_title(f"1DSRA PSA - {result.run_id}")
            ax.set_xlabel("Period (s)")
            ax.set_ylabel("PSA (m/s^2)")
            ax.grid(True, alpha=0.3)
            pdf.savefig(fig)
            plt.close(fig)

            fig2, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=False)
            time_acc = result.time
            if time_acc.size == result.acc_surface.size and time_acc.size > 0:
                axes[0].plot(time_acc, result.acc_surface, lw=1.2, color="#8b4d2a")
            else:
                axes[0].plot(result.acc_surface, lw=1.2, color="#8b4d2a")
            axes[0].set_title("Surface Acceleration")
            axes[0].set_ylabel("Acc (m/s^2)")
            axes[0].grid(True, alpha=0.3)

            if result.ru_time.size == result.ru.size and result.ru.size > 0:
                axes[1].plot(result.ru_time, result.ru, lw=1.2, color="#2f3a42")
            else:
                axes[1].plot(result.ru, lw=1.2, color="#2f3a42")
            axes[1].set_title("Pore Pressure Ratio (ru)")
            axes[1].set_ylabel("ru")
            axes[1].grid(True, alpha=0.3)

            sigma_time = result.ru_time
            plotted_sigma = False
            if result.sigma_v_eff.size > 0 and sigma_time.size == result.sigma_v_eff.size:
                axes[2].plot(sigma_time, result.sigma_v_eff, lw=1.2, color="#2d6a6a")
                plotted_sigma = True
            if result.delta_u.size > 0 and result.ru_time.size == result.delta_u.size:
                axes[2].plot(result.ru_time, result.delta_u, lw=1.0, color="#555555")
            if plotted_sigma:
                axes[2].set_title("Effective Stress and Delta-u")
                axes[2].set_xlabel("Time (s)")
            else:
                axes[2].set_title("Delta-u")
            axes[2].set_ylabel("kPa (proxy)")
            axes[2].grid(True, alpha=0.3)

            fig2.tight_layout()
            pdf.savefig(fig2)
            plt.close(fig2)

            if (
                result.transfer_freq_hz.size > 1
                and result.transfer_freq_hz.size == result.transfer_abs.size
            ):
                fig3, ax3 = plt.subplots(figsize=(8, 4.5))
                ax3.plot(result.transfer_freq_hz, result.transfer_abs, lw=1.2, color="#4b3f72")
                ax3.set_title("Transfer Function |H(f)|")
                ax3.set_xlabel("Frequency (Hz)")
                ax3.set_ylabel("Amplification")
                ax3.set_xlim(left=0.0)
                ax3.grid(True, alpha=0.3)
                pdf.savefig(fig3)
                plt.close(fig3)

            if result.eql_max_change_history.size > 0:
                fig4, ax4 = plt.subplots(figsize=(8, 4.5))
                idx = np.arange(1, result.eql_max_change_history.size + 1, dtype=np.int64)
                ax4.plot(idx, result.eql_max_change_history, marker="o", lw=1.2, color="#2f3a42")
                ax4.set_title("EQL Convergence History")
                ax4.set_xlabel("Iteration")
                ax4.set_ylabel("Max Relative Vs Change")
                ax4.grid(True, alpha=0.3)
                pdf.savefig(fig4)
                plt.close(fig4)
        written.append(pdf_path)

    return written
