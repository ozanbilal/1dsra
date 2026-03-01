from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

from dsra1d.store.result_store import ResultStore


def write_report(result: ResultStore, out_dir: Path, formats: list[str]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    periods = result.spectra_periods
    psa = result.spectra_psa
    pga = float(np.max(np.abs(result.acc_surface)))

    if "html" in formats:
        html = out_dir / "report.html"
        html.write_text(
            "\n".join(
                [
                    "<html><body>",
                    f"<h1>1DSRA Report: {result.run_id}</h1>",
                    f"<p>PGA(surface): {pga:.6f} m/s^2</p>",
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
        written.append(pdf_path)

    return written
