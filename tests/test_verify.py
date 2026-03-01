import sqlite3
from pathlib import Path

from dsra1d.config import load_project_config
from dsra1d.motion import load_motion
from dsra1d.pipeline import run_analysis
from dsra1d.verify import verify_run


def test_verify_run_passes_for_fresh_output(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    report = verify_run(result.output_dir)
    assert report.ok is True


def test_verify_run_detects_metric_tamper(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    result = run_analysis(cfg, motion, output_dir=tmp_path)
    with sqlite3.connect(result.sqlite_path) as conn:
        conn.execute(
            "UPDATE metrics SET value = value + 1.0 WHERE name = 'pga'"
        )
        conn.commit()

    report = verify_run(result.output_dir)
    assert report.ok is False
    assert report.checks["metrics_pga_match"] is False
