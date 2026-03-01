from pathlib import Path

from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.post import write_report


def test_report_includes_effective_stress_metrics(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    run = run_analysis(cfg, motion, output_dir=tmp_path / "runs")

    result = load_result(run.output_dir)
    written = write_report(result, out_dir=run.output_dir, formats=["html", "pdf"])

    html_path = run.output_dir / "report.html"
    pdf_path = run.output_dir / "report.pdf"
    assert html_path in written
    assert pdf_path in written
    assert html_path.exists()
    assert pdf_path.exists()

    html = html_path.read_text(encoding="utf-8")
    assert "ru_max:" in html
    assert "delta_u_max:" in html
    assert "sigma_v_eff_min:" in html
